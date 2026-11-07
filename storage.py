"""Local, demo-only data layer. No accessibility settings or raw tutor chats are saved."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from courses import COURSES

DB_PATH = Path(os.getenv("PAIRED_DB", str(Path(__file__).parent / "paired_demo.db")))


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def db():
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def password_digest(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 240_000).hex()


def _create_user(con, email, password, role):
    salt = secrets.token_bytes(16)
    con.execute("INSERT OR IGNORE INTO users(email, role, salt, password_hash) VALUES(?,?,?,?)",
                (email.lower().strip(), role, salt.hex(), password_digest(password, salt)))


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('Student','Professor')),
            salt TEXT NOT NULL, password_hash TEXT NOT NULL,
            tracking_consent INTEGER NOT NULL DEFAULT 0,
            prompt_storage_consent INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS course_settings(
            course TEXT PRIMARY KEY, description TEXT NOT NULL, oral_format TEXT NOT NULL,
            written_format TEXT NOT NULL, rubric TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS course_materials(
            id INTEGER PRIMARY KEY AUTOINCREMENT, course TEXT NOT NULL,
            title TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS anonymous_feedback(
            course TEXT NOT NULL, topic TEXT NOT NULL, blind_student TEXT NOT NULL,
            created_at TEXT NOT NULL, PRIMARY KEY(course,topic,blind_student));
        CREATE TABLE IF NOT EXISTS private_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL,
            course TEXT NOT NULL, kind TEXT NOT NULL, topic TEXT NOT NULL,
            evidence TEXT NOT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS student_prompts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            course TEXT NOT NULL,
            title TEXT NOT NULL,
            instruction TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(student_id, course, title),
            FOREIGN KEY(student_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS published_board(
            course TEXT PRIMARY KEY, code_text TEXT NOT NULL, concept_json TEXT NOT NULL,
            captions TEXT NOT NULL, summary TEXT NOT NULL, updated_at TEXT NOT NULL);
        """)
        # Upgrade existing hackathon databases without losing any previous records.
        columns = {row[1] for row in con.execute("PRAGMA table_info(users)")}
        if "prompt_storage_consent" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN prompt_storage_consent INTEGER NOT NULL DEFAULT 0")
        for name, details in COURSES.items():
            con.execute("INSERT OR IGNORE INTO course_settings VALUES(?,?,?,?,?)",
                        (name, details["description"], details["oral_format"], details["written_format"], details["rubric"]))
        defaults = [
            ("DEMO_STUDENT_EMAIL", "DEMO_STUDENT_PASSWORD", "Student"),
            ("DEMO_PROF_EMAIL", "DEMO_PROF_PASSWORD", "Professor"),
        ]
        for email_var, pwd_var, role in defaults:
            email, password = os.getenv(email_var, "").strip(), os.getenv(pwd_var, "")
            if email and password:
                if len(password) < 12:
                    raise ValueError(f"{pwd_var} must be at least 12 characters")
                _create_user(con, email, password, role)


def verify_credentials(email, password, role):
    with db() as con:
        record = con.execute("SELECT * FROM users WHERE email=? AND role=?",
                             (email.lower().strip(), role)).fetchone()
    if record is None:
        return None
    actual = password_digest(password, bytes.fromhex(record["salt"]))
    if not hmac.compare_digest(actual, record["password_hash"]):
        return None
    return {"id": record["id"], "email": record["email"], "role": record["role"]}


def get_course(course):
    with db() as con:
        row = con.execute("SELECT * FROM course_settings WHERE course=?", (course,)).fetchone()
    return dict(row) if row else None


def update_course(course, description, oral_format, written_format, rubric):
    with db() as con:
        con.execute("UPDATE course_settings SET description=?,oral_format=?,written_format=?,rubric=? WHERE course=?",
                    (description[:12000], oral_format[:3000], written_format[:3000], rubric[:3000], course))


def save_material(course, title, content):
    with db() as con:
        con.execute("INSERT INTO course_materials(course,title,content,created_at) VALUES(?,?,?,?)",
                    (course, title[:140], content[:30000], now()))


def list_materials(course):
    with db() as con:
        rows = con.execute("SELECT * FROM course_materials WHERE course=? ORDER BY id DESC", (course,)).fetchall()
    return [dict(r) for r in rows]


def delete_material(material_id, course):
    with db() as con:
        con.execute("DELETE FROM course_materials WHERE id=? AND course=?", (material_id, course))


def retrieve_material(course, question, limit=3):
    """Tiny lexical retrieval; NOT a full embedding/vector RAG pipeline."""
    import re
    rows = list_materials(course)
    if not rows:
        return COURSES[course]["mini_material"]
    query_terms = set(re.findall(r"\b[a-z]{4,}\b", question.lower()))
    chunks = []
    for row in rows:
        for chunk in [c.strip() for c in row["content"].split("\n\n") if c.strip()][:40]:
            terms = set(re.findall(r"\b[a-z]{4,}\b", chunk.lower()))
            chunks.append((len(query_terms & terms), row["title"], chunk[:1000]))
    chunks.sort(key=lambda r: r[0], reverse=True)
    return "\n\n".join(f"[{title}] {chunk}" for _, title, chunk in chunks[:limit])[:4000]


def _blind_token(user_id: int, course: str) -> str:
    secret = os.getenv("FEEDBACK_HMAC_SECRET", "")
    if not secret:
        # For local demo only. Consistent across reloads; not anonymous to a DB operator.
        secret = "LOCAL_DEMO_ONLY_CHANGE_FOR_DEPLOYMENT"
    return hmac.new(secret.encode(), f"{user_id}:{course}".encode(), hashlib.sha256).hexdigest()


def contribute_topic(user_id, course, topic):
    with db() as con:
        con.execute("INSERT OR IGNORE INTO anonymous_feedback(course,topic,blind_student,created_at) VALUES(?,?,?,?)",
                    (course, topic[:100], _blind_token(user_id, course), now()))


def visible_feedback(course, min_students=5):
    with db() as con:
        rows = con.execute("SELECT topic,COUNT(*) AS students FROM anonymous_feedback WHERE course=? GROUP BY topic HAVING COUNT(*)>=? ORDER BY students DESC", (course, min_students)).fetchall()
    return [dict(r) for r in rows]


def tracking_allowed(student_id):
    with db() as con:
        row = con.execute("SELECT tracking_consent FROM users WHERE id=? AND role='Student'", (student_id,)).fetchone()
    return bool(row and row["tracking_consent"])


def consent_tracking(student_id, enabled):
    with db() as con:
        con.execute("UPDATE users SET tracking_consent=? WHERE id=? AND role='Student'", (int(enabled), student_id))
        if not enabled:
            con.execute("DELETE FROM private_events WHERE student_id=?", (student_id,))
            for course in COURSES:
                con.execute("DELETE FROM anonymous_feedback WHERE course=? AND blind_student=?",
                            (course, _blind_token(student_id, course)))


def save_private_event(student_id, course, kind, topic, evidence):
    if not tracking_allowed(student_id):
        return False
    with db() as con:
        con.execute("INSERT INTO private_events(student_id,course,kind,topic,evidence,created_at) VALUES(?,?,?,?,?,?)",
                    (student_id, course, kind[:50], topic[:150], evidence[:1000], now()))
    return True


def private_timeline(student_id):
    with db() as con:
        rows = con.execute("SELECT id,course,kind,topic,evidence,created_at FROM private_events WHERE student_id=? ORDER BY id DESC", (student_id,)).fetchall()
    return [dict(r) for r in rows]


def prompt_storage_allowed(student_id: int) -> bool:
    with db() as con:
        row = con.execute(
            "SELECT prompt_storage_consent FROM users WHERE id=? AND role='Student'", (student_id,)
        ).fetchone()
    return bool(row and row["prompt_storage_consent"])


def consent_prompt_storage(student_id: int, enabled: bool) -> None:
    """Independent explicit opt-in. Revoking erases all custom templates."""
    with db() as con:
        con.execute("UPDATE users SET prompt_storage_consent=? WHERE id=? AND role='Student'",
                    (int(enabled), student_id))
        if not enabled:
            con.execute("DELETE FROM student_prompts WHERE student_id=?", (student_id,))


def list_custom_prompts(student_id: int, course: str) -> list[dict]:
    if not prompt_storage_allowed(student_id):
        return []
    with db() as con:
        rows = con.execute(
            "SELECT id, title, instruction FROM student_prompts "
            "WHERE student_id=? AND course=? ORDER BY title", (student_id, course)
        ).fetchall()
    return [dict(r) for r in rows]


def save_custom_prompt(student_id: int, course: str, title: str, instruction: str) -> bool:
    if course not in COURSES or not prompt_storage_allowed(student_id):
        return False
    title, instruction = title.strip()[:65], instruction.strip()[:320]
    if not title or not instruction:
        return False
    with db() as con:
        con.execute("""INSERT INTO student_prompts(student_id,course,title,instruction,created_at)
            VALUES(?,?,?,?,?) ON CONFLICT(student_id,course,title)
            DO UPDATE SET instruction=excluded.instruction""",
            (student_id, course, title, instruction, now()))
    return True


def delete_custom_prompt(student_id: int, course: str, prompt_id: int) -> None:
    with db() as con:
        con.execute("DELETE FROM student_prompts WHERE id=? AND student_id=? AND course=?",
                    (prompt_id, student_id, course))


def delete_student_data(student_id):
    consent_tracking(student_id, False)
    consent_prompt_storage(student_id, False)


def publish_board(course, payload):
    with db() as con:
        con.execute("""INSERT INTO published_board VALUES(?,?,?,?,?,?) ON CONFLICT(course) DO UPDATE SET
            code_text=excluded.code_text,concept_json=excluded.concept_json,
            captions=excluded.captions,summary=excluded.summary,updated_at=excluded.updated_at""",
            (course, payload.get("code", "")[:5000], json.dumps(payload.get("concepts", []))[:10000],
             payload.get("captions", "")[:10000], payload.get("summary", "")[:4000], now()))


def read_board(course):
    with db() as con:
        row = con.execute("SELECT * FROM published_board WHERE course=?", (course,)).fetchone()
    if not row:
        return None
    data = dict(row)
    try:
        data["concepts"] = json.loads(data.pop("concept_json"))
    except (ValueError, TypeError):
        data["concepts"] = []
    return data
