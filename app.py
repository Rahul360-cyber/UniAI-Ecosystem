"""PairEd hackathon demo: two authenticated portals with consent-aware learning workflows.

IMPORTANT: Prototype, not certified GDPR or EU AI Act compliance. Real deployments
require privacy/security review, institutional permission and human examiners.
"""
import os
import hashlib
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent / '.env')

import streamlit as st
from courses import COURSES, classify_topic
from ai_service import ai_ready, explain_question, generate_tutor_text_with_usage, MODEL
from prompt_engine import build_tutor_context
from storage import init_db, contribute_topic, save_private_event
from auth import require_login
from student_workspace import render_student_workspace
from professor_workspace import render_professor
from ui_theme import inject_theme, banner

st.set_page_config(page_title='PairEd — Inclusive AI Campus', page_icon='🎓', layout='wide', initial_sidebar_state='expanded')

try:
    init_db()
except Exception as exc:
    st.error(f'Cannot start local database: {exc}')
    st.stop()

with st.sidebar:
    st.markdown('## 🎓 PairEd')
    st.caption('Inclusive computer engineering learning')
    st.divider()
    st.markdown('**Accessibility · local session only**')
    focus_mode = st.checkbox('Focus mode / simpler presentation', key='focus_mode')
    large_text = st.checkbox('Comfortable reading size', key='large_text')
    reduced_motion = st.checkbox('Reduce UI motion', key='reduced_motion')
    st.checkbox('Bold technical terms', key='bold_terms')
    authorized_logo = st.checkbox('Use authorized university logo (if provided)', key='authorized_logo')
    st.caption('These preferences are not saved or shared with professors.')

inject_theme(focus_mode, large_text, reduced_motion, authorized_logo)
user = require_login()
if not user:
    st.stop()

with st.sidebar:
    st.divider()
    course = st.selectbox('Current course', list(COURSES), key='main_course')
    st.caption('Gemini: ' + (f'Configured ({MODEL})' if ai_ready() else 'Offline demo only'))
    st.caption('This is a fictional academic demonstration, not an official Politecnico service.')

banner(user['role'], course)
if user['role'] == 'Student':
    with st.sidebar:
        st.divider()
        cloud_ack = st.checkbox('I acknowledge that Gemini API requests send text/media to Google.', key='student_cloud_ack') if ai_ready() else False
        st.caption('Cloud AI is optional; never submit sensitive information in this demo.')

    def tutor_callback(question, instruction, max_tokens, include_material, recent_turns):
        # Only the current course and optional recent in-session turns go to Gemini.
        # Never send account ID, accessibility settings or saved portfolio history.
        package = build_tutor_context(
            course=course, question=question, instruction=instruction,
            max_approx_input_tokens=max_tokens,
            include_course_material=include_material, recent_turns=recent_turns,
        )
        topic = classify_topic(question, course)
        cache_key = hashlib.sha256(package["prompt"].encode("utf-8")).hexdigest()
        cache = st.session_state.setdefault(f"tutor_cache_{user['id']}", {})
        if cache_key in cache:
            old = cache[cache_key]
            stats = {**old[4], "cache_hit": True}
            return old[0], old[1], "Local session cache (no API request)", None, stats
        try:
            if ai_ready():
                explanation, usage = generate_tutor_text_with_usage(package["prompt"])
                source = f"Gemini ({MODEL})"
            else:
                _, explanation, source = explain_question(question, course)
                usage = {"prompt_tokens": None, "response_tokens": None, "total_tokens": None}
            stats = {**package, **usage, "cache_hit": False}
            stats.pop("prompt", None)  # Never store raw prompts inside usage statistics.
            # Session-only response caching; automatically cleared on sign-out.
            cache[cache_key] = (topic, explanation, source, None, stats)
            if len(cache) > 20:
                cache.pop(next(iter(cache)))
            # This method is consent-gated by storage.py: no event is saved by default.
            save_private_event(user['id'], course, 'Tutor concept clarification', topic,
                               'Requested a short explanation (question text not retained).')
            return topic, explanation, source, None, stats
        except Exception as exc:
            stats = {**package, "cache_hit": False}
            stats.pop("prompt", None)
            return topic, "Tutor request failed. Try a shorter question or check your API settings.",                 "Request failed", str(exc), stats

    def feedback_callback(topic):
        # Only called after the student explicitly opts in for this topic.
        contribute_topic(user['id'], course, topic)

    render_student_workspace(explain_with_gemini=tutor_callback, save_feedback=feedback_callback,
                             api_key=os.getenv('GEMINI_API_KEY', '').strip(),
                             active_course=course, student_id=user['id'], cloud_ack=cloud_ack)
else:
    render_professor(course)

st.divider()
st.caption('PairEd hackathon prototype · Student practice is formative, never an official final grade. '
           'No facial/emotion/attention tracking. No neurodivergence inference or reporting. '
           'University authorization, GDPR assessment and appropriate service contracts are required before real deployment.')
