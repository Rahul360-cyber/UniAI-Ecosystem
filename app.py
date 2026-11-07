"""LectureLoop Gemini hackathon prototype.

Privacy limits: This app sends student questions to Google Gemini if API mode is used.
Only opted-in topic REPORT COUNTS are stored locally in SQLite. Reports are
not deduplicated by student and the professor view is not access-controlled.
Use sample questions only until you have proper safeguards and consent.
"""

import json
import os
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

st.set_page_config(page_title="LectureLoop", page_icon="🎓", layout="wide")

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "learning_space.db"
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MIN_REPORTS = 5

TOPICS = ["Gradient Descent", "Learning Rate", "Backpropagation", "Overfitting", "Other"]
EXAMPLES = {
    "Gradient Descent": "Gradient descent repeatedly changes model parameters to reduce a loss function—like taking measured steps downhill toward a valley.",
    "Learning Rate": "Learning rate controls the size of each parameter update. Small steps may be slow; oversized steps can overshoot or diverge.",
    "Backpropagation": "Backpropagation applies the chain rule to calculate how each neural-network weight affects the final error.",
    "Overfitting": "Overfitting happens when a model learns training-specific patterns and performs poorly on unseen examples. Compare training and validation performance.",
    "Other": "Break down what you understood, what confused you, and one concrete example. A tutor can then explain the precise gap.",
}
RECOMMENDATIONS = {
    "Gradient Descent": "Draw a loss curve and demonstrate two optimization steps.",
    "Learning Rate": "Compare tiny, reasonable and excessive learning rates on a graph.",
    "Backpropagation": "Work through the chain rule on a tiny neural network.",
    "Overfitting": "Compare training and validation curves, then show one regularization technique.",
    "Other": "Collect more targeted, anonymous feedback next lecture.",
}


def setup_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS topic_counts (
                topic TEXT PRIMARY KEY,
                reports INTEGER NOT NULL DEFAULT 0
            )
        """)


def save_feedback(topic):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO topic_counts (topic, reports) VALUES (?, 1)
            ON CONFLICT(topic) DO UPDATE SET reports = reports + 1
        """, (topic,))


def read_feedback():
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query("SELECT topic, reports FROM topic_counts", conn)


def keyword_topic(question):
    text = question.lower()
    for topic, terms in [
        ("Learning Rate", ["learning rate", "step size"]),
        ("Backpropagation", ["backpropagation", "chain rule"]),
        ("Gradient Descent", ["gradient descent", "optimizer", "convergence"]),
        ("Overfitting", ["overfit", "regularization"]),
    ]:
        if any(term in text for term in terms):
            return topic
    return "Other"


def explain_with_gemini(question):
    if not API_KEY:
        topic = keyword_topic(question)
        return topic, EXAMPLES[topic], "Scripted demo (API key not configured)", None

    prompt = (
        "You are a supportive university course tutor. A student asks the following "
        "question. Give a short, accurate explanation and one concrete example. "
        "Also classify the difficulty into exactly one of these topics: "
        f"{', '.join(TOPICS)}. Return only the requested JSON fields. "
        "Do not invent facts about this student's identity or abilities.\n\n"
        f"Student question:\n{question}"
    )
    schema = {
        "type": "OBJECT",
        "properties": {
            "topic": {"type": "STRING", "enum": TOPICS},
            "explanation": {"type": "STRING"},
        },
        "required": ["topic", "explanation"],
    }
    try:
        client = genai.Client(api_key=API_KEY)
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.2,
            ),
        )
        result = json.loads(response.text or "{}")
        topic = result.get("topic", "Other")
        if topic not in TOPICS:
            topic = keyword_topic(question)
        explanation = str(result.get("explanation", "")).strip()
        if not explanation:
            raise ValueError("Gemini returned no explanation")
        return topic, explanation, f"Gemini ({MODEL})", None
    except Exception as exc:
        # Do not claim an AI-generated explanation if the API failed.
        topic = keyword_topic(question)
        return topic, EXAMPLES[topic], "Scripted demo (Gemini request failed)", str(exc)


setup_db()
st.title("🎓 LectureLoop")
st.caption("Student questions → topic insights → more responsive teaching")

with st.sidebar:
    workspace = st.radio("Workspace", ["Student", "Professor"])
    st.write("**AI:**", MODEL if API_KEY else "No key — scripted demo")
    st.caption("Hackathon demonstration: no account system or professor authentication.")

if workspace == "Student":
    st.subheader("Ask your AI tutor privately")
    st.write("Ask about a lecture concept. You can separately choose to contribute just its topic to the class dashboard.")
    with st.form("question_form"):
        question = st.text_area(
            "What did you not understand?",
            placeholder="Why does a high learning rate make gradient descent unstable?",
            max_chars=750,
            height=130,
        )
        api_ack = st.checkbox(
            "I understand my question will be sent to Google Gemini when API mode is enabled.",
            value=False,
        ) if API_KEY else True
        share_topic = st.checkbox(
            "Also add the detected topic to aggregate professor statistics (optional)",
            value=False,
        )
        submitted = st.form_submit_button("Ask tutor", type="primary")

    if submitted:
        if not question.strip():
            st.warning("Enter a question first.")
        elif API_KEY and not api_ack:
            st.warning("To use cloud AI, acknowledge that your question is sent to Gemini.")
        else:
            with st.spinner("Creating your explanation..."):
                topic, explanation, source, error_message = explain_with_gemini(question.strip())
            st.session_state["latest_result"] = (topic, explanation, source, error_message)
            if share_topic:
                save_feedback(topic)
                st.success("One anonymous topic report saved locally (no name or original question text).")
            else:
                st.info("No report was saved to the local dashboard.")

    if "latest_result" in st.session_state:
        topic, explanation, source, error_message = st.session_state["latest_result"]
        st.markdown("### Tutor explanation")
        st.write(explanation)
        st.caption(f"Classified topic: {topic} · Response source: {source}")
        if error_message:
            st.error(f"Gemini connection error: {error_message}")

else:
    st.subheader("Professor dashboard")
    data_mode = st.radio("Data", ["Sample classroom (demo)", "Local topic reports"], horizontal=True)
    if data_mode == "Sample classroom (demo)":
        df = pd.DataFrame({
            "topic": ["Gradient Descent", "Learning Rate", "Backpropagation", "Overfitting"],
            "reports": [18, 12, 9, 7],
        })
        st.caption("Fictional demonstration data, not student activity.")
    else:
        df = read_feedback()
        st.caption("Opt-in reports submitted on this computer. Not counts of unique students.")

    visible = df.loc[df["reports"] >= MIN_REPORTS].copy()
    if visible.empty:
        st.info("Not enough reports yet; choose sample classroom to see the visualization.")
    else:
        a, b = st.columns(2)
        a.metric("Difficulty reports (visible topics)", int(visible["reports"].sum()))
        b.metric("Topics needing attention", len(visible))
        st.markdown("### Recurring learning difficulties")
        st.bar_chart(visible.set_index("topic")["reports"])
        st.markdown("### Suggested teaching adjustments")
        for row in visible.sort_values("reports", ascending=False).itertuples():
            st.markdown(f"**{row.topic}** — {int(row.reports)} reports: {RECOMMENDATIONS.get(row.topic, RECOMMENDATIONS['Other'])}")
    st.caption("Privacy limitation: five reports are not necessarily five students. The prototype does not guarantee anonymity, prevent repeated voting, or restrict professor access. Do not deploy with real student data as-is.")
