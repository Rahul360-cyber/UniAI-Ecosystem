# LectureLoop v3 — Anonymous class feedback + student-controlled longitudinal portfolios

A hackathon Streamlit prototype for university learning: student questions and short quizzes inform a professor's **aggregate** class dashboard, while students can separately opt into a **private, persistent pseudonymous evidence portfolio**. Students can voluntarily export their academic/research evidence to professors, prospective PhD supervisors, or industry recruiters. No automated research-aptitude score, candidate ranking, or employment decision is produced.

## Run locally (Windows PowerShell)

1. Extract this archive into your existing `hackathon ai` working folder. Copy all files, including the **new `portfolio.py`**. Keep your existing `.env` and `.venv` files; **do not copy your `.env` into the GitHub repository.**
2. From your existing environment:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Optional Gemini API (requires cloud processing; use fictional content for the demonstration):

```powershell
Copy-Item .env.example .env
# Edit .env to supply a GEMINI_API_KEY locally; do not share it.
```

Without a Gemini key, the interface runs in clearly marked **scripted demo** mode.

## New v3 flow

1. Open **My Learning Portfolio**; accept the local storage notice and click **Create private portfolio**. **Save the recovery key**. It is only shown in your current browser session until you hide it; the application stores its SHA-256 digest, not the key itself.
2. Go to **Student**, ask a question, and explicitly select **Save topic (not my question text) to my private year-long portfolio**. Separately, you may opt in to class-level aggregates; these choices are independent.
3. Go to **Practice & Reassessment**, complete a quiz, and select **Save this result in my private long-term portfolio**. This stores topic, score, stage and simple misconception descriptions. The actual answers are not saved. Repeat later in the same class or another class code.
4. Return to **My Learning Portfolio**. Add a research question, experiment, failed attempt, project, reflection, collaboration or academic milestone, optionally linking a GitHub repository or other public evidence. These entries are **self-reported and unverified**.
5. Review your chronological record, scores across classes, question topic counts, and research evidence. **Download an HTML report** (print to PDF in your browser), or **download JSON** for a voluntary reviewer demonstration.
6. Under **Professor**, load a student-provided JSON file (or `docs/fictional_candidate_example.json` for a clearly labeled fictional demo) in **Voluntary PhD / industry candidate evidence review**. The file is displayed only for that session; it is not added to class data. The professor's regular class dashboard does **not** reveal individual student profiles.
7. Return to My Learning Portfolio to **lock** or **delete** your private data, or use the recovery key to unlock it in a new browser session **on the same server**.

## Original v2 features retained

- Student Gemini tutor (with cloud-data acknowledgement or offline scripted fallback)
- Optional, topic-only anonymous classroom feedback counts; no stored raw question text
- Fixed, objectively scored practice questions, concept maps, learning interventions, and reassessment
- Professor aggregate reports and demonstration data (no individual profiling)
- Classroom Lab: on-demand text/audio/photo processing, code feed, visual nodes, subtitle/catch-up summary, dynamic example generation, and publishing controls
- Original flowchart images and Mermaid source in `docs/`

## Privacy, fairness and practical limitations

- **Pseudonymous is not the same as anonymous:** a year-long portfolio must link events to the same account. Possession of the recovery key grants access in this demonstration. Do not use actual students' data until there is identity management, secure authentication, access control, encryption, lifecycle policy, consent governance, privacy/legal review and a stable database.
- Class-wide anonymous reports and private individual portfolios are **separate**. Students choose independently what to contribute; a reviewer's access requires an **export voluntarily supplied by the student**, not a professor-side search or backdoor.
- A student's report is **not** a hiring or PhD recommendation. Quiz scores cover tiny repeated practice-question sets, so score changes do not establish verified mastery or research aptitude. Project evidence is student-entered and requires validation. Formal admissions or employer criteria may still apply.
- The SQLite database is on the **app server**, not automatically on a student's own device. A shared hosting operator has access to the stored records; this is not end-to-end encrypted. Hosting on a transient service may delete the database on redeploy. Do not promise year-long durability without production storage and backups.
- Gemini is cloud AI; uploaded text/media go to Google. Use mock data until you've determined appropriate consent and data terms.
- Professor is a demo role only; it has **no authentication**. All role controls and shared boards remain unprotected. Counts of 5+ **reports** are not counts of distinct participants or guaranteed anonymous.
- Portfolios can be deleted, but aggregate contributions cannot be retroactively removed per user because they were never linked to the private key. Explain this limitation to students.
- This archive contains **no real API key or real student data**.

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Push updates to GitHub

```powershell
git status
# Verify .env, .venv, *.db are not staged

git add app.py portfolio.py requirements.txt README.md .gitignore .env.example docs/ tests/
git commit -m "Add student-controlled longitudinal portfolio and candidate evidence export"
git pull --rebase origin main
git push origin main
```

If working on a team, a feature branch and pull request is safer than pushing to shared `main`. **Never force-push shared branches.**
