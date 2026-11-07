"""Student-only evidence portfolio with opt-in history and local export/deletion."""
import json
from collections import Counter
import streamlit as st
from storage import (tracking_allowed, consent_tracking, save_private_event,
                     private_timeline, delete_student_data)


def render_portfolio(student_id, course):
    st.subheader("My longitudinal learning portfolio")
    st.caption("Private to this student account. Never appears on the professor's classroom dashboard.")
    active = tracking_allowed(student_id)
    if not active:
        st.warning("Long-term learning tracking is OFF. AI tutor use and class participation do not require it.")
        if st.button("Delete any previously shared class-topic contributions", key="clear_optional_topics"):
            delete_student_data(student_id)
            st.success("Any optional topic contributions have been deleted.")
        with st.form("tracking_consent"):
            accepted = st.checkbox("I explicitly consent to storing my optional learning history and evidence in this local demo database. I can delete it at any time.")
            submitted = st.form_submit_button("Enable my private portfolio")
        if submitted:
            if accepted:
                consent_tracking(student_id, True)
                st.success("Tracking enabled.")
                st.rerun()
            else:
                st.error("Select the consent box first.")
        return

    if st.button("Delete all my learning history and revoke consent", key="delete_portfolio"):
        st.session_state["confirm_delete"] = True
    if st.session_state.get("confirm_delete"):
        st.error("This permanently removes saved practice/research events, optional class-topic contributions, and any private custom prompt templates.")
        c1, c2 = st.columns(2)
        if c1.button("Yes, permanently delete", key="delete_confirmed"):
            delete_student_data(student_id)
            for session_key in list(st.session_state.keys()):
                if (session_key.startswith(("exam_", "tutor_cache_", "tutor_history_", "latest_result_"))
                        or session_key in ("latest_result", "foundation_result", "student_course_map", "student_course_context")):
                    st.session_state.pop(session_key, None)
            st.session_state.pop("confirm_delete", None)
            st.success("Your personal learning history, saved prompts and contributions were deleted.")
            st.rerun()
        if c2.button("Cancel deletion", key="delete_cancel"):
            st.session_state.pop("confirm_delete", None)
            st.rerun()

    st.markdown("### Add evidence of progress")
    with st.form("add_evidence"):
        kind = st.selectbox("Evidence type", ["Research question", "Project", "Experiment", "Learning reflection", "Revised misconception", "Achievement"])
        topic = st.text_input("Concept or project title", max_chars=150)
        description = st.text_area("What did you investigate, learn, or improve?", max_chars=1000)
        submit = st.form_submit_button("Save to my private timeline", type="primary")
    if submit:
        if topic.strip() and description.strip():
            save_private_event(student_id, course, kind, topic.strip(), description.strip())
            st.success("Saved privately.")
        else:
            st.warning("Please enter both a title and a description.")

    entries = private_timeline(student_id)
    st.markdown("### My progress over time")
    col1, col2, col3 = st.columns(3)
    col1.metric("Evidence events", len(entries))
    col2.metric("Courses", len(set(x["course"] for x in entries)))
    col3.metric("Research / experiments", sum(x["kind"] in ("Research question","Experiment") for x in entries))
    if entries:
        filter_type = st.selectbox("Filter timeline", ["All"] + sorted(set(e["kind"] for e in entries)))
        for row in entries:
            if filter_type != "All" and filter_type != row["kind"]:
                continue
            with st.expander(f"{row['created_at'][:10]} · {row['kind']} · {row['topic']}"):
                st.write(f"**Course:** {row['course']}")
                st.write(row["evidence"])
    else:
        st.info("No events yet. Complete a practice round or add an investigation above.")

    report = {
        "title":"PairEd — student-controlled learning evidence report",
        "disclaimer":"Self-reported portfolio and AI-assisted practice evidence; not verified grades or an automated suitability decision.",
        "events":entries,
        "summary":dict(Counter(e["kind"] for e in entries)),
        "sharing":"Student must choose whether and with whom to share this export.",
    }
    st.download_button("Download my research / career evidence report (JSON)",
                       data=json.dumps(report, ensure_ascii=False, indent=2),
                       file_name="paired_student_owned_report.json", mime="application/json")
    st.caption("No student report is transmitted to a professor or company by this app. Export and any later sharing are under your control.")
