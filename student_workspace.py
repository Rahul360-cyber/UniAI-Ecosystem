"""
Student workspace module for a Streamlit university-learning app.

Usage in the main app:
    from student_workspace import render_student_workspace

    if workspace == "Student":
        render_student_workspace(
            explain_with_gemini=explain_with_gemini,
            save_feedback=save_feedback,
            api_key=API_KEY,
        )

Dependencies:
    pip install streamlit requests
"""

import json
import re
from typing import Any, Callable, Dict, Optional
import os
from dotenv import load_dotenv

load_dotenv()

import streamlit as st
from interactive_labs import render_interactive_labs
from assessment import render_assessment
from portfolio_ui import render_portfolio
from teaching_copilot import show_board
from prompt_engine import PRESET_PROMPTS
from storage import (
    prompt_storage_allowed, consent_prompt_storage, list_custom_prompts,
    save_custom_prompt, delete_custom_prompt,
)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

COURSES = ["Internet of Things (IoT)", "Computer Engineering"]

LEVELS = [
    "Bachelor's 1st Year",
    "Bachelor's 2nd Year",
    "Bachelor's 3rd Year",
    "Bachelor's 4th Year",
    "Master's 1st Year",
    "Master's 2nd Year",
]



def _gemini_json(prompt: str, api_key: str, model: str = None):
    """Use the same official Gemini SDK configuration as the rest of ClassPair."""
    from ai_service import generate_json
    return generate_json(prompt)


def _make_course_map(course: str, level: str, description: str, api_key: str) -> Dict[str, Any]:
    prompt = f"""
You are an expert university curriculum designer and learning-science tutor.

Create a compact, accurate concept map for this university course.
Course: {course}
Student level: {level}
Course description / syllabus:
{description}

Return ONLY valid JSON with this exact structure:
{{
  "course_summary": "2-3 sentence overview",
  "nodes": [
    {{"id":"n1","label":"Concept name","kind":"foundation|core|advanced"}}
  ],
  "edges": [
    {{"from":"n1","to":"n2","relation":"prerequisite|builds_on|applied_in"}}
  ],
  "topics": ["topic names"],
  "diagnostic_questions": [
    {{
      "topic": "A topic from nodes",
      "question": "A short question that tests understanding, not memorisation",
      "expected_ideas": ["idea 1", "idea 2"],
      "foundation_ids": ["n1"]
    }}
  ]
}}

Requirements:
- Include 8-14 useful concept nodes, not every word in the description.
- Use stable IDs such as n1, n2, n3.
- An edge from A to B means A is needed to understand or apply B.
- Use prerequisite for a genuine dependency; do not imply every relationship is a strict prerequisite.
- Include 5-8 diagnostic questions across important concepts.
- Questions should be suitable for the specified student level.
- Identify foundational concepts separately from core and advanced concepts.
- Do not invent course-specific requirements that are unsupported by the description.
"""
    result = _gemini_json(prompt, api_key)
    _validate_map(result)
    return result


def _validate_map(course_map: Dict[str, Any]) -> None:
    nodes = course_map.get("nodes", [])
    edges = course_map.get("edges", [])
    questions = course_map.get("diagnostic_questions", [])
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("The generated mind map did not contain any concepts.")
    valid_ids = {str(node.get("id")) for node in nodes if isinstance(node, dict)}
    for edge in edges:
        if edge.get("from") not in valid_ids or edge.get("to") not in valid_ids:
            raise ValueError("The generated mind map contains an invalid relationship.")
    if not isinstance(questions, list):
        raise ValueError("The generated diagnostic questions were not valid.")


def _evaluate_diagnostic(
    course: str,
    level: str,
    selected_topic: str,
    questions_and_answers: list,
    course_map: Dict[str, Any],
    api_key: str,
) -> Dict[str, Any]:
    # Only send the selected learning area and nearby foundational concepts,
    # not the entire map or unrelated course topics.
    selected_nodes = [n for n in course_map.get("nodes", [])
                      if str(n.get("label", "")).casefold() == selected_topic.casefold()]
    chosen_ids = {str(n.get("id")) for n in selected_nodes}
    related_edges = [e for e in course_map.get("edges", [])
                     if str(e.get("to")) in chosen_ids or str(e.get("from")) in chosen_ids]
    chosen_ids.update(str(e.get("from")) for e in related_edges)
    chosen_ids.update(str(e.get("to")) for e in related_edges)
    context_map = {
        "nodes": [n for n in course_map.get("nodes", []) if str(n.get("id")) in chosen_ids][:7],
        "edges": related_edges[:8],
    }
    prompt = f"""
Act as a supportive university tutor. Evaluate the student's understanding using
the supplied questions, answers, and course concept map.

Course: {course}
Level: {level}
Selected difficult topic: {selected_topic}
Concept map:
{json.dumps(context_map, ensure_ascii=False)}
Student answers:
{json.dumps(questions_and_answers, ensure_ascii=False)}

Return ONLY valid JSON:
{{
  "overall": "one of: Strong, Developing, Needs foundational review",
  "feedback": "Brief, constructive explanation of the student's current understanding",
  "gaps": [
    {{
      "concept": "specific missing or weak foundation",
      "reason": "evidence from the student's answer",
      "priority": "High|Medium|Low"
    }}
  ],
  "learning_path": [
    {{
      "step": 1,
      "concept": "concept to revisit",
      "action": "specific action or practice suggestion"
    }}
  ],
  "next_question": "One useful follow-up question"
}}

Be evidence-based. Do not claim a student has a gap unless their answers provide evidence.
If the answers are insufficient, say so and recommend a clarifying question.
"""
    return _gemini_json(prompt, api_key)


def _dot_escape(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def _render_mind_map(course_map: Dict[str, Any]) -> None:
    """Render a concept map using Streamlit's built-in Graphviz support."""
    nodes = course_map.get("nodes", [])
    edges = course_map.get("edges", [])
    lines = [
        "digraph CourseMap {",
        'graph [rankdir="LR", bgcolor="transparent", pad="0.25", nodesep="0.45", ranksep="0.75"];',
        'node [shape="box", style="rounded,filled", fontname="Arial", fontsize="10", color="#64748b", fillcolor="#e0f2fe", margin="0.16,0.10"];',
        'edge [fontname="Arial", fontsize="8", color="#64748b", arrowsize="0.7"];',
    ]
    for node in nodes:
        kind = str(node.get("kind", "core")).lower()
        fill = {"foundation": "#dcfce7", "core": "#dbeafe", "advanced": "#f3e8ff"}.get(kind, "#e2e8f0")
        node_id = _dot_escape(node.get("id", ""))
        label = _dot_escape(node.get("label", "Concept"))
        lines.append(f'"{node_id}" [label="{label}", fillcolor="{fill}"];')
    for edge in edges:
        source = _dot_escape(edge.get("from", ""))
        target = _dot_escape(edge.get("to", ""))
        relation = _dot_escape(edge.get("relation", "related"))
        lines.append(f'"{source}" -> "{target}" [label="{relation}"];')
    lines.append("}")
    st.graphviz_chart("\n".join(lines), use_container_width=True)


def render_prompt_library(student_id: int, course: str) -> list[dict]:
    """Only this student sees these templates; persistent saving is an explicit opt-in."""
    st.caption("Built-in study prompts are always available. Personal prompts are optional and private.")
    with st.expander("📌 My saved prompts · optional local storage", expanded=False):
        if not prompt_storage_allowed(student_id):
            st.info("Personal prompt storage is OFF. Presets still work without saving anything.")
            with st.form(f"prompt_consent_{student_id}"):
                agree = st.checkbox("I consent to storing my custom prompt templates in the local demo database. I can delete them anytime.")
                if st.form_submit_button("Enable private prompt saving"):
                    if agree:
                        consent_prompt_storage(student_id, True)
                        st.rerun()
                    else:
                        st.warning("Choose the consent option to enable saving.")
            return []
        st.success("Private prompt storage enabled for this student account.")
        with st.form(f"new_prompt_{student_id}_{course}"):
            title = st.text_input("Prompt title", max_chars=65, placeholder="Explain with a memory diagram")
            content = st.text_area("Instructions for your tutor", max_chars=320,
                                   placeholder="Show a 4-step worked example, then ask a check question.")
            if st.form_submit_button("Save / update my prompt"):
                if save_custom_prompt(student_id, course, title, content):
                    st.success("Your prompt template was saved locally.")
                    st.rerun()
                else:
                    st.error("Provide a title and instructions, and check consent.")
        prompts = list_custom_prompts(student_id, course)
        if prompts:
            names = {f"{x['title']} (#{x['id']})": x for x in prompts}
            selected_label = st.selectbox("Manage an existing template", list(names), key=f"prompt_delete_choice_{student_id}_{course}")
            st.caption(names[selected_label]["instruction"])
            if st.button("Delete selected template", key=f"prompt_delete_{student_id}_{course}"):
                delete_custom_prompt(student_id, course, names[selected_label]["id"])
                st.rerun()
        if st.button("Revoke permission and delete ALL saved prompts", key=f"prompt_revoke_{student_id}"):
            consent_prompt_storage(student_id, False)
            st.rerun()
    return list_custom_prompts(student_id, course)


def render_student_workspace(
    explain_with_gemini: Callable,
    save_feedback: Callable,
    api_key: Optional[str] = None,
    active_course: str = "Computer Engineering",
    student_id: int = 0,
    cloud_ack: bool = False,
) -> None:
    """
    Render the Student workspace.

    Existing callbacks are injected from the main app so this module can reuse
    the current private tutor and anonymous topic-reporting behaviour.
    """
    st.subheader("Your AI-powered student workspace")
    tutor_tab, map_tab, labs_tab, exam_tab, classroom_tab, portfolio_tab = st.tabs([
        "💬 AI tutor", "🧠 Interactive mind map", "🔬 Interactive labs",
        "🎓 Practice & oral viva", "📺 Classroom catch-up", "📈 My portfolio"
    ])

    
    with tutor_tab:
        st.markdown("### Token-smart AI tutor")
        st.caption("Prompt templates are short reusable instructions. Only relevant course excerpts are sent to the LLM; no names, accessibility settings or portfolio history.")
        custom_prompts = render_prompt_library(student_id, active_course)
        custom_lookup = {f"My prompt: {row['title']}": row['instruction'] for row in custom_prompts}
        options = list(PRESET_PROMPTS) + list(custom_lookup) + ["Write a one-time instruction"]
        history_key = f"tutor_history_{student_id}_{active_course}"
        with st.form("question_form"):
            selected = st.selectbox("Choose a saved / built-in prompt", options,
                                    key=f"selected_tutor_prompt_{student_id}_{active_course}")
            one_time = st.text_input("One-time instruction (not saved)", max_chars=320,
                                     placeholder="Explain it with a short analogy") if selected == "Write a one-time instruction" else ""
            include_course_material = st.checkbox("Include only relevant professor-uploaded course excerpts", value=True)
            include_history = st.checkbox("Include last two exchanges from this session", value=False)
            input_budget = st.slider("Estimated input token budget", 450, 2500, 1100, 100,
                                     help="A heuristic based on text length, not an exact Gemini token cap.")
            question = st.text_area("What did you not understand?", max_chars=750, height=130,
                placeholder="For linked lists, why is inserting at the head O(1)?")
            api_ack = st.checkbox(
                "I acknowledge my question and selected course excerpts will be sent to Google Gemini.",
                value=False,
            ) if api_key else True
            share_topic = st.checkbox(
                "Optionally contribute the detected topic to aggregate professor statistics",
                value=False,
            )
            submitted = st.form_submit_button("Ask concise AI tutor", type="primary")

        if submitted:
            if not question.strip():
                st.warning("Enter a question first.")
            elif api_key and not api_ack:
                st.warning("Acknowledge the cloud API transfer before sending your question.")
            else:
                instruction = (one_time if selected == "Write a one-time instruction" else
                               custom_lookup.get(selected, PRESET_PROMPTS.get(selected, "")))
                recent = st.session_state.get(history_key, [])[-2:] if include_history else []
                with st.spinner("Selecting context and generating a concise explanation..."):
                    topic, explanation, source, error_message, stats = explain_with_gemini(
                        question.strip(), instruction, input_budget, include_course_material, recent
                    )
                st.session_state[f"latest_result_{student_id}_{active_course}"] = (topic, explanation, source, error_message, stats)
                if not error_message:
                    if include_history:
                        # Optional, per-account/session only; never written to SQLite.
                        turns = st.session_state.setdefault(history_key, [])
                        turns.append({"question": question.strip()[:750], "answer": explanation[:750]})
                        st.session_state[history_key] = turns[-2:]
                    else:
                        st.session_state.pop(history_key, None)
                    if share_topic:
                        save_feedback(topic)
                        st.success("Topic contribution saved separately; professor cannot see this conversation.")
                else:
                    st.error("AI request failed; nothing was contributed to professor statistics.")

        result_key = f"latest_result_{student_id}_{active_course}"
        if result_key in st.session_state:
            topic, explanation, source, error_message, stats = st.session_state[result_key]
            st.markdown("### Tutor explanation")
            st.write(explanation)
            st.caption(f"Topic: {topic} · Source: {source}")
            if error_message:
                st.error(f"Model/API problem: {error_message}")
            col1, col2, col3 = st.columns(3)
            col1.metric("Estimated input tokens", f"~{stats.get('estimated_input_tokens', 0)}")
            col2.metric("Gemini input tokens", stats.get('prompt_tokens') if stats.get('prompt_tokens') is not None else "N/A")
            col3.metric("Gemini total tokens", stats.get('total_tokens') if stats.get('total_tokens') is not None else "N/A")
            if stats.get("cache_hit"):
                st.success("Identical context found in this session: reused previous response with 0 additional Gemini tokens.")
                st.caption("Usage numbers above refer to the original request, not this cache hit.")
            st.caption("Counts from Gemini reflect the actual request when available. Estimated tokens are approximate; "
                       "no carbon-emissions reduction is claimed or measured. "
                       f"Course excerpt: {stats.get('course_reference_chars', 0)} characters; "
                       f"recent-history included: {'yes' if stats.get('history_included') else 'no'}.")

    # ------------------------------------------------------------------
    # Course selection, AI concept map, and evidence-based gap checking.
    # ------------------------------------------------------------------
    with map_tab:
        st.markdown("### Build your course mind map")
        st.caption(
            "Choose your programme and level, then provide the course description "
            "or paste the relevant syllabus section."
        )

        with st.form("course_map_form"):
            col1, col2 = st.columns(2)
            with col1:
                course = st.selectbox("Course", COURSES, key="mindmap_course")
            with col2:
                level = st.selectbox("Study level", LEVELS, index=2, key="mindmap_level")

            description = st.text_area(
                "Course description / syllabus",
                placeholder=(
                    "Paste the course description, learning outcomes, or syllabus topics. "
                    "For example: embedded systems, sensors, networking protocols, "
                    "microcontrollers, data acquisition..."
                ),
                height=170,
                max_chars=12000,
                key="mindmap_description",
            )
            map_api_ack = st.checkbox(
                "I understand this course description will be sent to Google Gemini to generate the mind map and diagnostic questions.",
                value=False,
            ) if api_key else True
            generate = st.form_submit_button("✨ Generate my mind map", type="primary")

        if generate:
            if not description.strip():
                st.warning("Please add a course description or syllabus first.")
            elif api_key and not map_api_ack:
                st.warning("Please acknowledge that the course description will be sent to Gemini.")
            elif not api_key:
                st.error("Gemini API mode is not configured. Add your API key to generate the AI mind map.")
            else:
                try:
                    with st.spinner("Analysing the syllabus and building your concept map..."):
                        course_map = _make_course_map(course, level, description.strip(), api_key)
                    st.session_state["student_course_map"] = course_map
                    st.session_state["student_course_context"] = {
                        "course": course, "level": level, "description": description.strip()
                    }
                    st.session_state.pop("foundation_result", None)
                    st.success("Your course mind map is ready.")
                except Exception as exc:
                    st.error(f"Could not generate the mind map: {exc}")

        course_map = st.session_state.get("student_course_map")
        context = st.session_state.get("student_course_context")
        if course_map and context:
            st.divider()
            st.markdown(f"#### {context['course']} · {context['level']}")
            st.write(course_map.get("course_summary", ""))
            st.markdown("**Concept map**")
            _render_mind_map(course_map)

            with st.expander("Understand the map colours and connections"):
                st.markdown(
                    "- 🟩 **Foundation:** concepts that support later learning\n"
                    "- 🟦 **Core:** central topics in the course\n"
                    "- 🟪 **Advanced:** higher-level or applied topics\n\n"
                    "Arrows show the direction of dependency or progression. "
                    "The relationship label distinguishes prerequisites from broader applications."
                )

            nodes = course_map.get("nodes", [])
            topic_labels = [str(n.get("label")) for n in nodes if n.get("label")]
            if topic_labels:
                st.markdown("### Find out what is holding you back")
                selected_topic = st.selectbox(
                    "Which topic are you struggling with?",
                    topic_labels,
                    key="gap_selected_topic",
                )

                question_bank = [
                    q for q in course_map.get("diagnostic_questions", [])
                    if q.get("topic") == selected_topic
                ]
                if not question_bank:
                    question_bank = [
                        q for q in course_map.get("diagnostic_questions", [])
                        if q.get("question")
                    ][:3]

                if question_bank:
                    with st.form("foundation_diagnostic_form"):
                        st.write("Answer these short questions in your own words. It's okay if you're unsure.")
                        answers = []
                        for index, item in enumerate(question_bank[:3]):
                            answer = st.text_area(
                                item.get("question", f"Question {index + 1}"),
                                key=f"foundation_answer_{index}_{selected_topic}",
                                height=90,
                            )
                            answers.append({
                                "question": item.get("question", ""),
                                "answer": answer.strip(),
                            })
                        diag_api_ack = st.checkbox(
                            "I agree to send my diagnostic answers to Google Gemini for this check.",
                            value=False,
                        )
                        diagnose = st.form_submit_button("Check my foundations", type="primary")

                    if diagnose:
                        if not any(item["answer"] for item in answers):
                            st.warning("Answer at least one question so the tutor has evidence to assess.")
                        elif not api_key:
                            st.error("Gemini API mode is required for foundation-gap analysis.")
                        elif not diag_api_ack:
                            st.warning("Please consent to sending these diagnostic answers to Gemini.")
                        else:
                            try:
                                with st.spinner("Checking your understanding and tracing possible foundation gaps..."):
                                    result = _evaluate_diagnostic(
                                        context["course"], context["level"], selected_topic,
                                        answers, course_map, api_key
                                    )
                                st.session_state["foundation_result"] = result
                            except Exception as exc:
                                st.error(f"Could not complete the foundation check: {exc}")
                else:
                    st.info("No diagnostic questions were generated for this map. Try regenerating it.")

            result = st.session_state.get("foundation_result")
            if result:
                st.divider()
                st.markdown("### Your foundation check")
                st.subheader(result.get("overall", "Learning review"))
                st.write(result.get("feedback", ""))

                gaps = result.get("gaps", [])
                if gaps:
                    st.markdown("**Foundations to revisit**")
                    for gap in gaps:
                        priority = gap.get("priority", "Medium")
                        st.markdown(
                            f"- **{gap.get('concept', 'Concept')}** · {priority} priority  \n"
                            f"  {gap.get('reason', '')}"
                        )
                else:
                    st.success("No specific foundation gap was established from these answers.")

                path = result.get("learning_path", [])
                if path:
                    st.markdown("**Suggested learning path**")
                    for step in path:
                        st.markdown(
                            f"{step.get('step', '')}. **{step.get('concept', 'Review')}** — "
                            f"{step.get('action', '')}"
                        )
                if result.get("next_question"):
                    with st.expander("Continue learning"):
                        st.write(result["next_question"])
    with labs_tab:
        st.markdown("### Interactive Labs")         
        render_interactive_labs()                      

    with exam_tab:
        render_assessment(active_course, student_id, cloud_ack)

    with classroom_tab:
        st.markdown("### Professor-approved classroom feed")
        st.caption("Read approved concepts, cleaned code and catch-up notes without racing to copy the whiteboard.")
        show_board(active_course, bold=st.session_state.get("bold_terms", False))
        st.button("Refresh published materials", key="refresh_board")

    with portfolio_tab:
        render_portfolio(student_id, active_course)
