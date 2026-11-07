"""Student-controlled, pseudonymous learning portfolio for the LectureLoop demo.

No real name or student ID is collected. Profiles are accessed with a high-entropy
recovery secret; only its SHA-256 digest is stored. This is a prototype, not a
production authorization or GDPR solution. No automated hiring scores are made.
"""

import hashlib
import html
import json
import secrets
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


ENTRY_TYPES = (
    "Research question", "Experiment", "Iteration / failed attempt",
    "Project", "Collaboration", "Reflection", "Academic milestone",
)


def _timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect(db_path):
    conn = sqlite3.connect(str(db_path), timeout=15)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_portfolio(db_path):
    with _connect(db_path) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS private_profiles (
            key_hash TEXT PRIMARY KEY, created_at TEXT NOT NULL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS private_portfolio_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_hash TEXT NOT NULL REFERENCES private_profiles(key_hash) ON DELETE CASCADE,
            happened_at TEXT NOT NULL, class_code TEXT NOT NULL,
            kind TEXT NOT NULL, topic TEXT NOT NULL DEFAULT '',
            score INTEGER, stage TEXT NOT NULL DEFAULT '',
            detail TEXT NOT NULL DEFAULT '', evidence_url TEXT NOT NULL DEFAULT ''
        )""")
        conn.execute("""CREATE INDEX IF NOT EXISTS idx_private_events_key_date
            ON private_portfolio_events(key_hash, happened_at)""")


def _digest(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_profile(db_path):
    """Returns a newly generated recovery token and digest; only digest is persisted."""
    init_portfolio(db_path)
    token = secrets.token_urlsafe(32)
    digest = _digest(token)
    with _connect(db_path) as conn:
        conn.execute("INSERT INTO private_profiles VALUES (?, ?)", (digest, _timestamp()))
    return token, digest


def restore_profile(db_path, token):
    token = token.strip()
    if len(token) < 36 or len(token) > 100:
        return None
    digest = _digest(token)
    with _connect(db_path) as conn:
        row = conn.execute("SELECT 1 FROM private_profiles WHERE key_hash=?", (digest,)).fetchone()
    return digest if row else None


def profile_exists(db_path, digest):
    if not digest:
        return False
    with _connect(db_path) as conn:
        row = conn.execute("SELECT 1 FROM private_profiles WHERE key_hash=?", (digest,)).fetchone()
    return bool(row)


def _safe_url(url):
    url = url.strip()
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme not in ("https", "http") or not parsed.netloc:
        raise ValueError("Evidence URL must start with https:// or http://")
    if len(url) > 400:
        raise ValueError("Evidence URL is too long")
    return url


def add_event(db_path, digest, *, class_code, kind, topic="", score=None,
              stage="", detail="", evidence_url=""):
    if not profile_exists(db_path, digest):
        raise ValueError("Unlock a valid private profile first")
    if kind not in ("question_topic", "assessment", "evidence"):
        raise ValueError("Unknown event type")
    if not isinstance(class_code, str) or not (3 <= len(class_code) <= 20):
        raise ValueError("Invalid class code")
    if kind == "assessment" and (not isinstance(score, int) or not 0 <= score <= 100):
        raise ValueError("Assessment score must be 0–100")
    evidence_url = _safe_url(evidence_url)
    with _connect(db_path) as conn:
        conn.execute("""INSERT INTO private_portfolio_events
            (key_hash,happened_at,class_code,kind,topic,score,stage,detail,evidence_url)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (digest, _timestamp(), class_code, kind, topic[:160], score, stage[:60],
             detail[:1200], evidence_url))


def get_events(db_path, digest, *, kind=None, class_code=None, topic=None):
    if not profile_exists(db_path, digest):
        return []
    sql = """SELECT happened_at, class_code, kind, topic, score, stage, detail, evidence_url
             FROM private_portfolio_events WHERE key_hash=?"""
    params = [digest]
    if kind:
        sql += " AND kind=?"
        params.append(kind)
    if class_code:
        sql += " AND class_code=?"
        params.append(class_code)
    if topic:
        sql += " AND topic=?"
        params.append(topic)
    sql += " ORDER BY happened_at ASC, id ASC"
    with _connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def delete_profile(db_path, digest):
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM private_profiles WHERE key_hash=?", (digest,))


def make_report(events):
    """Transparent summary of recorded evidence; NO employability or aptitude score."""
    quizzes = [e for e in events if e["kind"] == "assessment"]
    topics = [e for e in events if e["kind"] == "question_topic"]
    evidence = [e for e in events if e["kind"] == "evidence"]
    by_course = sorted(set(e["class_code"] for e in events))
    by_topic = Counter(e["topic"] for e in topics)
    evidence_kinds = Counter(e["stage"] for e in evidence)
    per_concept = {}
    for event in quizzes:
        key = (event["class_code"], event["topic"])
        per_concept.setdefault(key, []).append(event["score"])
    trends = [
        {"course": course, "topic": topic, "attempts": len(scores),
         "first_score": scores[0], "latest_score": scores[-1],
         "change_points": scores[-1] - scores[0]}
        for (course, topic), scores in sorted(per_concept.items())
    ]
    chronological = sorted(events, key=lambda e: e["happened_at"])
    return {
        "generated_at": _timestamp(),
        "covered_period": {"first": chronological[0]["happened_at"] if chronological else None,
                           "last": chronological[-1]["happened_at"] if chronological else None},
        "classes": by_course,
        "total_recorded_assessments": len(quizzes),
        "assessment_scores": [{"date": e["happened_at"], "course": e["class_code"],
                               "topic": e["topic"], "score": e["score"],
                               "assessment_stage": e["stage"],
                               "practice_misconceptions": e["detail"]} for e in quizzes],
        "per_concept_practice_progress": trends,
        "recorded_question_topics": dict(by_topic),
        "research_and_learning_evidence_counts": dict(evidence_kinds),
        "evidence_entries": [{"date": e["happened_at"], "course": e["class_code"],
                              "kind": e["stage"], "title": e["topic"],
                              "description": e["detail"], "evidence_url": e["evidence_url"]}
                             for e in evidence],
        "scope": "Student-selected local portfolio records, not a complete academic transcript.",
        "verification": "Student-entered evidence is self-reported; short practice quizzes are not official grades.",
        "decision_notice": "For human review only; not an automated employment, admission, ranking, or PhD suitability decision.",
    }


def report_html(report):
    """Standalone HTML suitable for student download and manual PDF printing."""
    esc = lambda x: html.escape(str(x), quote=True)
    def cell(t):
        return f"<td>{esc(t)}</td>"
    quiz_rows = "".join("<tr>" + "".join(cell(row[k]) for k in
        ("date", "course", "topic", "score", "assessment_stage")) + "</tr>"
        for row in report["assessment_scores"])
    evidence_rows = ""
    for row in report["evidence_entries"]:
        link = (f'<a href="{esc(row["evidence_url"])}" rel="noopener noreferrer">Evidence link</a>'
                if row["evidence_url"] else "—")
        evidence_rows += "<tr>" + "".join(cell(row[k]) for k in
            ("date", "course", "kind", "title", "description")) + f"<td>{link}</td></tr>"
    trend_rows = "".join("<tr>" + "".join(cell(row[k]) for k in
        ("course", "topic", "attempts", "first_score", "latest_score", "change_points")) + "</tr>"
        for row in report["per_concept_practice_progress"])
    topics = ", ".join(f"{esc(k)} ({v})" for k, v in report["recorded_question_topics"].items()) or "No topics recorded"
    kinds = ", ".join(f"{esc(k)} ({v})" for k, v in report["research_and_learning_evidence_counts"].items()) or "No evidence entries yet"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>LectureLoop — Learning evidence portfolio</title>
    <style>body{{font-family:Arial,sans-serif;max-width:1000px;margin:35px auto;line-height:1.5;color:#17233b;padding:0 16px}}
    h1,h2{{color:#124e80}}table{{border-collapse:collapse;width:100%;margin:16px 0}}
    th,td{{border:1px solid #c9d5e3;padding:8px;vertical-align:top;text-align:left;overflow-wrap:anywhere}}
    th{{background:#edf5fc}}.notice{{background:#fff6dc;padding:12px;border-radius:8px}}
    .sub{{color:#4f627a}}@media print{{body{{margin:8mm auto}}}}</style></head><body>
    <h1>LectureLoop — Learning Evidence Portfolio</h1>
    <p class="sub">Student-controlled export · Generated {esc(report['generated_at'])}</p>
    <p class="notice"><strong>Not a hiring score or PhD aptitude prediction.</strong> {esc(report['decision_notice'])}</p>
    <h2>Learning timeline</h2>
    <p>Recorded period: {esc(report['covered_period']['first'] or 'Not yet recorded')} to {esc(report['covered_period']['last'] or 'Not yet recorded')}<br>
    Class codes: {esc(', '.join(report['classes']) or 'None')}<br>
    Recorded assessments: {report['total_recorded_assessments']}</p>
    <h2>Questions explored</h2><p>{topics}</p>
    <h2>Research and project evidence</h2><p>{kinds}</p>
    <table><thead><tr><th>Date (UTC)</th><th>Class</th><th>Evidence category</th><th>Title</th><th>Student explanation</th><th>Link</th></tr></thead>
    <tbody>{evidence_rows or '<tr><td colspan="6">No evidence yet.</td></tr>'}</tbody></table>
    <h2>Recorded concept practice trends</h2>
    <table><thead><tr><th>Class</th><th>Topic</th><th>Attempts</th><th>First (%)</th><th>Latest (%)</th><th>Change (points)</th></tr></thead>
    <tbody>{trend_rows or '<tr><td colspan="6">No assessments yet.</td></tr>'}</tbody></table>
    <h2>Assessment attempts</h2>
    <table><thead><tr><th>Date (UTC)</th><th>Class</th><th>Topic</th><th>Score (%)</th><th>Stage</th></tr></thead>
    <tbody>{quiz_rows or '<tr><td colspan="5">No assessments recorded yet.</td></tr>'}</tbody></table>
    <p class="notice">{esc(report['scope'])} {esc(report['verification'])} Human reviewers must verify evidence independently.</p>
    <p class="sub">Prepared for voluntary sharing by the student with professors, supervisors, or prospective employers.</p>
    </body></html>"""


def report_json(report):
    return json.dumps(report, ensure_ascii=False, indent=2)
