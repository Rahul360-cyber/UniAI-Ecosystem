"""Professor-only portal: aggregate analytics, syllabus/exams, and on-demand 4-agent co-pilot."""
import json
import pandas as pd
import streamlit as st
from courses import COURSES
from storage import (get_course, update_course, save_material, list_materials,
                     delete_material, visible_feedback, retrieve_material, publish_board)
from teaching_copilot import (extract_material, ingest_multimodal, run_agents,
                              edge_case_agent, concept_graph)
from ai_service import ai_ready


def render_professor(course):
    st.header("Professor portal")
    st.caption("Classwide trends only. Student profiles, accessibility settings and raw tutor chats are not available here.")
    overview, materials, copilot, voluntary_review = st.tabs([
        "📊 Learning overview", "📚 Course & exam settings",
        "🤖 Teaching co-pilot", "📁 Voluntary portfolio review"
    ])

    with overview:
        mode = st.radio("Data source", ["Fictional classroom demo", "Local consented feedback"], horizontal=True)
        if mode == "Fictional classroom demo":
            labels = COURSES[course]["topics"][:4]
            data = [{"topic": labels[i], "students": [18, 12, 9, 7][i]} for i in range(len(labels))]
            st.info("All student counts displayed here are fictional demonstration data.")
        else:
            data = visible_feedback(course, min_students=5)
            st.info("Topics below five distinct contributing accounts are hidden. This is pseudonymous aggregation, not a production anonymity guarantee.")
        if data:
            c1, c2, c3 = st.columns(3)
            c1.metric("Visible learning topics", len(data))
            c2.metric("Reported topic-student pairs", sum(d["students"] for d in data))
            c3.metric("Priority topic", max(data, key=lambda d:d["students"])["topic"])
            df = pd.DataFrame(data).set_index("topic")
            st.bar_chart(df["students"])
            st.markdown("### Teaching suggestions")
            for item in data:
                with st.expander(f"{item['topic']} — {item['students']} contributors"):
                    st.write("Revisit the concept using a worked example, a short demonstration, and one optional independent knowledge check.")
        else:
            st.warning("No class-level report meets the five-contributor threshold. Use the fictional demo during the presentation.")
        st.caption("Counts are distinct contributors per concept, not a clinical or ability classification. AI does not issue final grades.")

    with materials:
        settings = get_course(course)
        st.markdown("### Configure the course-specific assessments")
        with st.form("course_admin_" + course):
            description = st.text_area("Syllabus / course overview", settings["description"], height=130)
            oral_format = st.text_area("Professor's oral exam format", settings["oral_format"], height=130)
            written_format = st.text_area("Professor's written assessment format", settings["written_format"], height=130)
            rubric = st.text_area("Professor's assessment criteria", settings["rubric"], height=110)
            saved = st.form_submit_button("Save exam configuration", type="primary")
        if saved:
            update_course(course, description, oral_format, written_format, rubric)
            st.success("Students' next practice sessions will follow these formats.")

        st.markdown("### Add authorized course materials")
        st.caption("Supported: .txt, .md, .pdf with selectable text. No materials are sent to Google during upload.")
        text_title = st.text_input("Material name", value="Lecture notes")
        text_content = st.text_area("Paste syllabus, slides text, or answer rubric", height=140)
        file = st.file_uploader("Or upload lecture text/PDF", type=["txt","md","pdf"], key="prof_material")
        if st.button("Save course material"):
            try:
                content = extract_material(file) if file is not None else text_content
                if not content.strip():
                    st.warning("No readable text found; scanned PDFs require an additional OCR step.")
                else:
                    save_material(course, file.name if file else text_title, content)
                    st.success("Saved to the local course context library.")
            except Exception as exc:
                st.error(f"Could not read document: {exc}")
        docs = list_materials(course)
        st.caption(f"Stored documents for this course: {len(docs)}")
        if docs:
            titles = {f"{d['id']}: {d['title']}":d for d in docs}
            choice = st.selectbox("Review saved material", list(titles))
            doc = titles[choice]
            st.text_area("Stored text preview", doc["content"][:3000], height=130, disabled=True)
            if st.button("Delete selected material"):
                delete_material(doc["id"], course)
                st.success("Deleted from the course library.")
                st.rerun()

    with copilot:
        st.subheader("Classroom multi-agent teaching co-pilot")
        st.caption("On-demand demo: 3 parallel specialist agents + a 4th question-triggered agent. Not continuous live audio streaming.")
        transcript = st.text_area("Pasted lecture transcript / class notes", height=180,
                                  placeholder="Today we compare stack vs heap, with linked-list pointers...")
        ca, cb = st.columns(2)
        with ca:
            audio = st.file_uploader("Optional recorded lecture audio (≤8 MB)", type=["wav","mp3","m4a"], key="prof_audio")
        with cb:
            image = st.file_uploader("Optional whiteboard photo (≤8 MB)", type=["png","jpg","jpeg","webp"], key="prof_board")
        st.warning("Before recording or uploading identifiable voices, verify authorization and participants' informed consent. Do not upload personal student data to this demo.")
        permitted = st.checkbox("I confirm that this course/media is authorized for this demonstration and I understand Google Gemini processes supplied data if enabled.", key="prof_cloud_consent")
        if st.button("Generate class co-pilot outputs", type="primary"):
            if not permitted:
                st.error("Explicit acknowledgment is required before processing teaching content.")
            else:
                try:
                    with st.spinner("Ingesting lecture inputs..."):
                        processed = ingest_multimodal(transcript, audio, image, course)
                    with st.spinner("Running 3 specialist AI agents..."):
                        payload, source = run_agents(course, processed)
                    st.session_state["agent_payload_"+course] = payload
                    st.session_state["agent_source_"+course] = source
                    st.session_state["agent_context_"+course] = processed
                except Exception as exc:
                    st.error(f"Co-pilot processing failed: {exc}")
        payload = st.session_state.get("agent_payload_"+course)
        if payload:
            st.success("Generated by " + st.session_state.get("agent_source_"+course, "demo"))
            t_code, t_visual, t_sub = st.tabs(["Agent 1 · Code", "Agent 2 · Visual", "Agent 3 · Catch-up"])
            with t_code:
                st.code(payload["code"], language="python")
            with t_visual:
                concept_graph(payload["concepts"])
                st.write("Concepts:", ", ".join(payload["concepts"]))
            with t_sub:
                st.markdown("**Catch-up summary**")
                st.write(payload["summary"])
                st.markdown("**Cleaned transcript (not timed live captions)**")
                st.write(payload["captions"])
            st.markdown("### Professor's publication control")
            p1 = st.checkbox("Publish cleaned code", value=True)
            p2 = st.checkbox("Publish concept visual", value=True)
            p3 = st.checkbox("Publish captions & summary", value=True)
            if st.button("Publish selected outputs to Student Portal"):
                selected = {"code":payload["code"] if p1 else "",
                            "concepts":payload["concepts"] if p2 else [],
                            "captions":payload["captions"] if p3 else "",
                            "summary":payload["summary"] if p3 else ""}
                publish_board(course, selected)
                st.success("The approved outputs are available in the student classroom tab.")
        st.divider()
        st.markdown("### Agent 4 — Dynamic edge-case code generator")
        with st.form("edge_question"):
            question = st.text_input("Student's in-class question", max_chars=800)
            generate_edge = st.form_submit_button("Generate teaching example")
        if generate_edge:
            if not permitted:
                st.error("Please confirm the cloud processing acknowledgment above.")
            elif not question.strip():
                st.warning("Enter a question first.")
            else:
                try:
                    with st.spinner("Preparing a focused example..."):
                        text = edge_case_agent(course, st.session_state.get("agent_context_"+course, transcript), question)
                    st.session_state["edge_answer_"+course] = text
                except Exception as exc:
                    st.error(f"Edge-case agent error: {exc}")
        if st.session_state.get("edge_answer_"+course):
            st.write(st.session_state["edge_answer_"+course])
        st.caption("Professor reviews outputs before projection. Generated code is shown as text and never executed by the co-pilot.")

    with voluntary_review:
        st.subheader("Student-shared research / career evidence")
        st.info("A professor may inspect only a report the student deliberately exported and provided. This portal never reads private student portfolios directly.")
        uploaded_report = st.file_uploader("Upload a student-voluntarily-shared ClassPair report", type=["json"], key="review_report")
        if uploaded_report:
            if uploaded_report.size > 512_000:
                st.error("Maximum report size is 500 KB.")
            else:
                try:
                    report = json.loads(uploaded_report.getvalue().decode("utf-8"))
                    if not isinstance(report, dict) or not isinstance(report.get("events"), list):
                        raise ValueError("This does not look like a ClassPair learning report.")
                    entries = report["events"][:120]
                    st.metric("Voluntarily shared evidence items", len(entries))
                    st.write(report.get("disclaimer", "This portfolio has not been verified."))
                    for e in entries:
                        if not isinstance(e, dict):
                            continue
                        with st.expander(f"{str(e.get('created_at',''))[:10]} · {str(e.get('kind','Evidence'))[:60]}"):
                            st.write("**Course:**", str(e.get("course", ""))[:100])
                            st.write("**Topic:**", str(e.get("topic", ""))[:150])
                            st.write("**Evidence:**", str(e.get("evidence", ""))[:1000])
                    st.caption("Do not automatically rank PhD or job applicants by these records. Discuss any claims with the student and assess actual research work independently.")
                except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
                    st.error(f"Could not parse student-shared report: {exc}")
