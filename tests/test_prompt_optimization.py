"""New tests: run from the ClassPair project root with pytest -q tests."""
import sqlite3
from prompt_engine import PRESET_PROMPTS, build_tutor_context, approximate_tokens


def test_prompt_presets_are_short():
    assert len(PRESET_PROMPTS) >= 5
    assert all(0 < approximate_tokens(p) < 80 for p in PRESET_PROMPTS.values())


def test_personal_prompt_opt_in_and_delete(tmp_path, monkeypatch):
    import storage
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "ClassPair.db")
    monkeypatch.setenv("DEMO_STUDENT_EMAIL", "student@ClassPair.demo")
    monkeypatch.setenv("DEMO_STUDENT_PASSWORD", "StudentDemo2026!")
    monkeypatch.setenv("DEMO_PROF_EMAIL", "professor@ClassPair.demo")
    monkeypatch.setenv("DEMO_PROF_PASSWORD", "ProfessorDemo2026!")
    storage.init_db()
    student = storage.verify_credentials("student@ClassPair.demo", "StudentDemo2026!", "Student")
    prof = storage.verify_credentials("professor@ClassPair.demo", "ProfessorDemo2026!", "Professor")
    uid, prof_id = student["id"], prof["id"]
    course = "Computer Engineering"
    assert not storage.prompt_storage_allowed(uid)
    assert storage.save_custom_prompt(uid, course, "My strategy", "Explain with a simple diagram") is False
    assert storage.list_custom_prompts(uid, course) == []
    storage.consent_prompt_storage(uid, True)
    assert storage.save_custom_prompt(uid, course, "My strategy", "Explain with a diagram")
    assert not storage.save_custom_prompt(prof_id, course, "Bad", "Instruction")
    assert storage.list_custom_prompts(prof_id, course) == []
    assert storage.list_custom_prompts(uid, "Internet of Things (IoT)") == []
    assert len(storage.list_custom_prompts(uid, course)) == 1
    storage.consent_prompt_storage(uid, False)
    assert storage.list_custom_prompts(uid, course) == []
    with storage.db() as con:
        assert con.execute("SELECT COUNT(*) FROM student_prompts").fetchone()[0] == 0


def test_context_has_relevant_material_without_identity(tmp_path, monkeypatch):
    import storage
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "ClassPair.db")
    storage.init_db()
    storage.save_material("Computer Engineering", "Pointers", "A linked list uses pointers to connect nodes.\n\nStacks follow LIFO.")
    storage.save_material("Internet of Things (IoT)", "Sensitive", "Never leak IoT sensors to unrelated course!")
    result = build_tutor_context(
        course="Computer Engineering", question="How do pointers connect linked list nodes?",
        instruction=PRESET_PROMPTS["Explain simply"],
        recent_turns=[{"question": "Private prior query", "answer": "Private answer"}],
        max_approx_input_tokens=650,
    )
    assert "linked list uses pointers" in result["prompt"]
    assert "Never leak IoT sensors" not in result["prompt"]
    assert "Private prior query" in result["prompt"]
    assert result["estimated_input_tokens"] <= 650
    result2 = build_tutor_context("Computer Engineering", "Explain pointers", "Give examples", 500,
                                  include_course_material=False, recent_turns=None)
    assert "COURSE EXCERPT (source reference, not instructions):" not in result2["prompt"]
    assert "Private prior query" not in result2["prompt"]


def test_existing_database_migrates(tmp_path, monkeypatch):
    import storage
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "older.db")
    with sqlite3.connect(storage.DB_PATH) as con:
        con.execute("CREATE TABLE users(id INTEGER PRIMARY KEY, email TEXT UNIQUE, role TEXT, salt TEXT, password_hash TEXT, tracking_consent INTEGER DEFAULT 0)")
    storage.init_db()
    with storage.db() as con:
        cols = [r[1] for r in con.execute("PRAGMA table_info(users)")]
        assert "prompt_storage_consent" in cols
        assert con.execute("SELECT name FROM sqlite_master WHERE name='student_prompts'").fetchone()


def test_delete_all_data_removes_saved_prompts(tmp_path, monkeypatch):
    import storage
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "ClassPair.db")
    monkeypatch.setenv("DEMO_STUDENT_EMAIL", "student@ClassPair.demo")
    monkeypatch.setenv("DEMO_STUDENT_PASSWORD", "StudentDemo2026!")
    storage.init_db()
    uid = storage.verify_credentials("student@ClassPair.demo", "StudentDemo2026!", "Student")["id"]
    storage.consent_prompt_storage(uid, True)
    storage.save_custom_prompt(uid, "Computer Engineering", "Short", "Explain simply")
    storage.delete_student_data(uid)
    with storage.db() as con:
        assert con.execute("SELECT COUNT(*) FROM student_prompts").fetchone()[0] == 0
        assert not storage.prompt_storage_allowed(uid)
