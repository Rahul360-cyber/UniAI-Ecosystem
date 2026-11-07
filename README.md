# ClassPair — Hackathon Demo

ClassPair is a **prototype**, not a university-approved service or a certified GDPR/EU AI Act implementation. The demo uses two **fictional** course templates: Computer Engineering and Internet of Things (IoT). It preserves the provided coding execution tracer and interactive IoT breadboard simulator.

## Installation (Windows / PowerShell)

Use Python 3.11 or 3.12. **Streamlit is pinned to exactly 1.37.0.**

```powershell
cd "C:\Users\rahul\Desktop\hackathon ai"
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Copy the key/value lines from `.env.example` into your **existing** `.env`. **Do not overwrite your existing Gemini key.** Set the four `DEMO_*` variables and a random `FEEDBACK_HMAC_SECRET`. Passwords must be at least 12 characters. Demo account values in `.env.example`:

| Workspace | Email | Demo password |
|---|---|---|
| Student | `student@ClassPair.demo` | `StudentDemo2026!` |
| Professor | `professor@ClassPair.demo` | `ProfessorDemo2026!` |

**Change these passwords before showing a publicly accessible demonstration.** Accounts are created on the first launch and stored as salted PBKDF2 password hashes in `ClassPair_demo.db`. Changing `.env` passwords later does not overwrite existing accounts; for a clean fictional demo you may stop the app and delete **only** the new `ClassPair_demo.db`, but **preserve** your previous `learning_space.db`, which this package does not modify.

Run:

```powershell
python -m streamlit run app.py
```

## Student Portal

- Private AI questions, concept maps, evidence-based foundation checks and both original interactive labs
- **Practice & oral viva**: subject-specific 3-turn adaptive question-and-response simulation (typed), plus written practice; follows professor-configured exam formats/rubrics
- Professor-approved classroom catch-up: cleaned code, text captions, visual concept map
- Session-only focus mode, comfortable text, reduced motion, bold terms; preferences are **never stored** or sent to the professor
- Explicitly opt-in longitudinal learning portfolio, editable research/activity records, student-owned JSON career/research export, permanent deletion
- Optional per-topic class contribution, one pseudonymous contribution per account/topic; professor sees only sufficiently large aggregates

## Professor Portal

- Fictional or opt-in class-level topic analytics with small-group suppression
- Edit oral format, written format, rubric and syllabus per course
- Upload/paste authorized `.txt`, `.md`, text-based `.pdf` material, which is stored locally
- On-demand, multimodal *classroom* ingestion: pasted transcript, audio recording and whiteboard image (Gemini needed for media)
- Three specialist agents called in parallel: code synchronizer, visual abstractor, catch-up/subtitle summary generator
- Fourth on-demand edge-case code example agent
- Professor explicitly approves which outputs are published to students
- Manual review of a **student-voluntarily-uploaded** JSON portfolio report; no automated PhD/job ranking and no direct private-history access

## What's not implemented

**Not** continuous background streaming, automatic speech-to-text live captions, real-time camera capture, advanced embedding/RAG infrastructure, access control suitable for a public university, or official/automated final grading. Oral simulation accepts a typed answer or an uploaded short audio recording (transcribed on demand with consent), rather than a live microphone session. The professor's uploaded class recording can be transcribed on demand. The retrieval library is deliberately small lexical retrieval, not a vector database.

## Privacy and legal limitations

- The app uses role checks but demo authentication and SQLite are **not** production ready.
- A persistent login means student actions are **pseudonymous**, not completely anonymous to the server operator. Professor dashboard sees no identity or individual conversation.
- The 5-contributor threshold reduces small-cohort disclosure but does **not** guarantee GDPR anonymization.
- A learner must explicitly consent before any longitudinal tracking, and can delete data. Accessibility settings are session-only.
- No neurodivergence labels, cognitive/attention/emotion biometrics or inference. No automatic official grades, candidate suitability scores or hiring recommendations.
- **Google Gemini is an external cloud processor.** If enabled, the specific messages, course materials or authorized media sent through the API leave the server. A checkbox alone is not enough to establish organizational GDPR compliance. Use invented demonstration data until the institution performs a DPIA, selects a suitable legal basis, meets processor/transfer requirements, and puts appropriate agreements and security in place.
- No actual Politecnico di Torino logo is shipped. A neutral campus watermark is included. An authorized `assets/polito_logo.png` can be supplied by the developer with appropriate permission; do not imply the university endorses the prototype.
- Students can voluntarily export a research/career evidence report; the application never sends it to employers, supervisors or partners. Any use in recruitment requires additional governance and human review.

## Tests

```powershell
python -m pip install pytest
python -m pytest -q tests
```

## GitHub push

Do **not** add `.env`, virtual environments, or `*.db` to Git. After testing your app:

```powershell
git status
git add app.py auth.py ai_service.py assessment.py courses.py professor_workspace.py portfolio_ui.py student_workspace.py teaching_copilot.py storage.py ui_theme.py interactive_labs.py breadboard_lab.py requirements.txt README.md .env.example .gitignore .streamlit/config.toml assets/torino_campus_mark.svg tests/test_core.py
git diff --cached --stat
git commit -m "Build ClassPair student and professor portals with adaptive exams"
git pull --rebase origin main
git push origin main
```

## Safety / compatibility notes

- Existing `student_workspace(1).py` from the attachment has been included as canonical `student_workspace.py` after merging the full IoT lab tab and Gemini SDK adaptor.
- `interactive_labs.py` and `breadboard_lab.py` were preserved from the uploaded originals.
- Your previous database and private portfolio files are left untouched. The new demo uses `ClassPair_demo.db`.
- A professor can edit a course's content, but users cannot create or elevate their role themselves.
- This is intentionally a **hackathon MVP**. Have a human professor evaluate outputs and verify every demo example.
