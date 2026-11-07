"""Subject-specific LLM-guided oral / written formative assessments."""
import json
import streamlit as st
from ai_service import generate_json, generate_text, ai_ready
from courses import COURSES, classify_topic
from storage import get_course, retrieve_material, save_private_event

MAX_TURNS = 3


def _starting_question(course, mode, settings):
    if not ai_ready():
        return COURSES[course]["sample_questions"][0], "Sample question (offline)"
    format_text = settings["oral_format" if mode == "Oral viva" else "written_format"]
    prompt = ("Act as a university exam PRACTICE simulator, not a real examiner. "
              "Generate one clear subject-specific question, without revealing the answer. "
              "Respect the professor-provided format, rubric and source context. No final grade. "
              "Return JSON {\"question\":\"...\"}. "
              f"Subject: {course}\nFormat: {format_text}\nRubric: {settings['rubric']}\n"
              f"Course material: {retrieve_material(course,'core course topics')[:2300]}")
    result = generate_json(prompt)
    return str(result.get("question", ""))[:1400] or COURSES[course]["sample_questions"][0], "Gemini"


def _review_answer(course, mode, settings, turns, question, answer, number):
    if not ai_ready():
        bank = COURSES[course]["sample_questions"]
        return {
            "feedback": "Offline practice: your answer was recorded for this session but has NOT been assessed. Compare it against the course materials.",
            "topic": classify_topic(question, course),
            "suggested_action": "Revisit the corresponding lab and explain the concept with one example.",
            "next_question": bank[number % len(bank)] if number < MAX_TURNS else "",
        }
    prompt = ("You are conducting a text-based oral exam rehearsal or written exam practice. "
              "Never provide an official grade, a hiring recommendation, a disability diagnosis, "
              "or an automated final decision. Evaluate evidence cautiously. "
              "Return JSON with feedback (specific formative advice), topic (subject concept), "
              "suggested_action (one actionable revision), next_question (one adaptive follow-up; "
              "empty after 3 responses). No numeric final mark. "
              f"Course: {course}. Mode: {mode}. Turn {number}/3.\n"
              f"Exam settings: {json.dumps(settings, ensure_ascii=False)[:3800]}\n"
              f"Relevant material: {retrieve_material(course,question)[:2400]}\n"
              f"Prior turns: {json.dumps(turns, ensure_ascii=False)[:4800]}\n"
              f"Current question: {question[:1600]}\nStudent answer: {answer[:3500]}")
    res = generate_json(prompt)
    return {"feedback":str(res.get("feedback", "No feedback returned"))[:2500],
            "topic":str(res.get("topic", classify_topic(question,course)))[:100],
            "suggested_action":str(res.get("suggested_action", "Review the topic"))[:500],
            "next_question":str(res.get("next_question", ""))[:1500] if number < MAX_TURNS else ""}


def render_assessment(course, student_id, cloud_ack):
    st.subheader("Practice & assessment simulation")
    st.caption("Practice feedback only. An academic examiner must review any actual grade.")
    settings = get_course(course)
    mode = st.radio("Choose a format", ["Oral viva", "Written practice"], horizontal=True)
    st.info(settings["oral_format" if mode == "Oral viva" else "written_format"])
    st.caption("Oral viva = adaptive examiner conversation. Type an answer or upload a short recorded answer; continuous live microphone capture is not available in Streamlit 1.37.")
    key = "exam_" + course.replace(" ", "_") + "_" + mode.replace(" ", "_")
    state = st.session_state.get(key)
    if not state or state.get("done"):
        if st.button("Start new " + mode.lower(), type="primary", key="start_"+key):
            if ai_ready() and not cloud_ack:
                st.warning("Enable cloud AI acknowledgement in your student settings first.")
            else:
                try:
                    with st.spinner("Preparing your subject-specific question..."):
                        question, source = _starting_question(course, mode, settings)
                    st.session_state[key] = {"question":question,"source":source,"turns":[],"done":False,"last":None}
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not start AI simulation: {exc}")
        if state and state.get("done"):
            st.success("Practice session complete. You can start another rehearsal with new questions.")
            for i, step in enumerate(state["turns"], 1):
                with st.expander(f"Question {i}: {step['question'][:65]}"):
                    st.write("**Your answer:**", step["answer"])
                    st.write("**Formative feedback:**", step["feedback"])
                    st.write("**Recommended revision:**", step["suggested_action"])
        return
    current = len(state["turns"]) + 1
    st.progress((current-1) / MAX_TURNS)
    st.markdown(f"**Question {current} of {MAX_TURNS}**")
    st.write(state["question"])
    if state.get("last"):
        with st.expander("Feedback on previous answer", expanded=True):
            st.write(state["last"]["feedback"])
            st.caption(state["last"]["suggested_action"])
    with st.form("exam_answer_" + key):
        answer = st.text_area("Your response", height=160, max_chars=3500,
                              placeholder="Explain your reasoning as you would to your professor...")
        recording = st.file_uploader("Optional spoken answer recording (.wav / .mp3 / .m4a, max 8 MB)",
                                     type=["wav", "mp3", "m4a"], key="exam_recording_"+key) if mode == "Oral viva" else None
        submit = st.form_submit_button("Submit response", type="primary")
    if submit:
        if ai_ready() and not cloud_ack:
            st.warning("Cloud AI acknowledgement is required before sending your answer or recording.")
        elif recording is not None and not ai_ready():
            st.warning("Audio transcription requires Gemini. You can still type your response offline.")
        else:
            try:
                submitted_answer = answer.strip()
                if recording is not None and not submitted_answer:
                    if recording.size > 8 * 1024 * 1024:
                        raise ValueError("Recorded answer exceeds 8 MB")
                    extension = recording.name.rsplit('.', 1)[-1].lower()
                    mime = {"wav":"audio/wav", "mp3":"audio/mpeg", "m4a":"audio/mp4"}[extension]
                    with st.spinner("Transcribing your spoken response (no emotion/identity analysis)..."):
                        submitted_answer = generate_text(
                            "Transcribe the student's academic spoken answer as text faithfully. "
                            "Do not infer any emotional, health, disability or identity traits.",
                            media=[(recording.getvalue(), mime)])[:3500]
                if len(submitted_answer) < 12:
                    st.warning("Please give a longer answer, or upload a spoken response.")
                    return
                with st.spinner("Reviewing reasoning and choosing next question..."):
                    review = _review_answer(course, mode, settings, state["turns"], state["question"], submitted_answer, current)
                step = {"question":state["question"],"answer":submitted_answer,
                        "feedback":review["feedback"],"topic":review["topic"],
                        "suggested_action":review["suggested_action"]}
                state["turns"].append(step)
                state["last"] = review
                if current >= MAX_TURNS:
                    state["done"] = True
                    st.session_state[key] = state
                    # Only the minimal formative topic record, and only with opt-in.
                    save_private_event(student_id, course, "Practice: " + mode, review["topic"],
                                       f"Completed {MAX_TURNS}-question practice round. Review: {review['suggested_action']}")
                else:
                    state["question"] = review["next_question"] or COURSES[course]["sample_questions"][current % len(COURSES[course]["sample_questions"])]
                    st.session_state[key] = state
                st.rerun()
            except Exception as exc:
                st.error(f"Evaluation unavailable: {exc}. Your answer was not submitted for grading.")
