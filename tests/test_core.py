"""Tests do not call external APIs or load Streamlit UI."""
import importlib
import os
from pathlib import Path


def build_storage(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_STUDENT_EMAIL", "student@ClassPair.demo")
    monkeypatch.setenv("DEMO_STUDENT_PASSWORD", "StudentDemo2026!")
    monkeypatch.setenv("DEMO_PROF_EMAIL", "professor@ClassPair.demo")
    monkeypatch.setenv("DEMO_PROF_PASSWORD", "ProfessorDemo2026!")
    monkeypatch.setenv("FEEDBACK_HMAC_SECRET", "very-long-test-only-secret-abc123")
    import storage
    monkeypatch.setattr(storage, 'DB_PATH', tmp_path / 'test.db')
    storage.init_db()
    return storage


def test_role_separation_and_password_hashing(tmp_path, monkeypatch):
    s = build_storage(tmp_path, monkeypatch)
    student = s.verify_credentials("student@ClassPair.demo", "StudentDemo2026!", "Student")
    professor = s.verify_credentials("professor@ClassPair.demo", "ProfessorDemo2026!", "Professor")
    assert student and professor
    assert s.verify_credentials("student@ClassPair.demo", "StudentDemo2026!", "Professor") is None
    assert s.verify_credentials("student@ClassPair.demo", "bad", "Student") is None
    with s.db() as con:
        row = con.execute("SELECT password_hash FROM users WHERE id=?", (student['id'],)).fetchone()
    assert "StudentDemo2026!" not in row["password_hash"]


def test_opt_in_delete_and_no_duplicate_votes(tmp_path, monkeypatch):
    s = build_storage(tmp_path, monkeypatch)
    student = s.verify_credentials("student@ClassPair.demo", "StudentDemo2026!", "Student")
    uid = student["id"]
    assert s.save_private_event(uid, "Computer Engineering", "Project", "Linked lists", "Explained complexity") is False
    s.consent_tracking(uid, True)
    assert s.save_private_event(uid, "Computer Engineering", "Project", "Linked lists", "Explained complexity") is True
    assert len(s.private_timeline(uid)) == 1
    s.contribute_topic(uid, "Computer Engineering", "Pointers")
    s.contribute_topic(uid, "Computer Engineering", "Pointers")
    with s.db() as con:
        n = con.execute("SELECT COUNT(*) FROM anonymous_feedback").fetchone()[0]
    assert n == 1
    assert s.visible_feedback("Computer Engineering", min_students=5) == []
    assert s.visible_feedback("Computer Engineering", min_students=1)[0]["students"] == 1
    s.delete_student_data(uid)
    assert not s.tracking_allowed(uid)
    assert s.private_timeline(uid) == []
    assert s.visible_feedback("Computer Engineering", min_students=1) == []


def test_course_settings_material_and_publication(tmp_path, monkeypatch):
    s = build_storage(tmp_path, monkeypatch)
    course = "Internet of Things (IoT)"
    c = s.get_course(course)
    assert "oral" in c["oral_format".lower()] or c["oral_format"]
    s.update_course(course, "modified description", "3 viva questions", "2 calculations", "scientific rigor")
    assert s.get_course(course)["oral_format"] == "3 viva questions"
    s.save_material(course, "Electronics", "Ohm law: V = I * R. Current needs closed path.")
    assert "Ohm" in s.retrieve_material(course, "Explain Ohm law")
    s.publish_board(course, {"code":"print(1)","concepts":["Voltage","Current"],
                             "captions":"Lecture example", "summary":"Today's topic"})
    assert s.read_board(course)["concepts"] == ["Voltage", "Current"]
    assert s.read_board("Computer Engineering") is None


def test_course_classification():
    from courses import classify_topic
    assert classify_topic("Why is my GPIO pin not working?", "Internet of Things (IoT)") == "GPIO"
    assert classify_topic("How is stack memory allocated?", "Computer Engineering") == "Stack and Heap"
