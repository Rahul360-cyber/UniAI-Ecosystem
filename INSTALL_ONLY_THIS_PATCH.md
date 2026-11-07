# ClassPair — token-smart student tutor: incremental update

This package is **not** a replacement for the entire ClassPair project. It overlays seven existing/new Python files and one new test file onto the final ClassPair hackathon version.

## What changed

- `prompt_engine.py` **NEW**: short reusable preset prompts, course-scoped lexical retrieval, input context trimming, optional two-turn session context and approximate input-token planning.
- `student_workspace.py` **REPLACE**: student AI tutor now offers six presets, personal saved prompts, explicit private prompt-saving consent, optional context, a configurable estimated token budget and model usage metrics.
- `ai_service.py` **REPLACE**: calls Gemini and reports `usage_metadata` token counts. Caps tutor output at 1,100 tokens (this cap is an API setting; the input token estimate is not a hard provider cap).
- `app.py` **REPLACE**: builds context for the authenticated student and selected course; reuses identical responses from the same student's current session cache; does not store raw questions in SQLite.
- `storage.py` **REPLACE**: adds `student_prompts` and one optional consent column to `users`; automatically upgrades an existing ClassPair database; allows students to delete one/all saved prompt templates.
- `portfolio_ui.py` **REPLACE**: makes clear that delete-all removes saved templates too, and clears student-only in-session tutor context on deletion.
- `tests/test_prompt_optimization.py` **NEW**: tests consent, per-course separation, context trimming, existing database migration and deletion.

## Install: Windows / PowerShell

1. **Back up your existing project**, or commit the current working version to a feature branch first.
2. Extract this ZIP. **Copy only the files and folder listed above** into `C:\Users\rahul\Desktop\hackathon ai`, preserving the relative `tests/` folder.
3. **Do not delete** `.env`, `.git/`, `.venv/`, `paired_demo.db`, `learning_space.db`, or your original interactive labs.
4. No extra Python packages are needed. Streamlit remains pinned at **1.37.0** in your existing `requirements.txt`.
5. In your terminal:

```powershell
cd "C:\Users\rahul\Desktop\hackathon ai"
python -m streamlit run app.py
```

## Test the feature

- Log in as the **Student**, select **Computer Engineering**, and enter the **AI tutor** tab.
- Try “Socratic hints” and “Step-by-step example”. Use identical question/settings twice with *Include last two exchanges* unchecked; the second attempt should show a session-cache hit.
- In “My saved prompts”, enable independent consent, create a prompt, select it in the tutor, delete it, and revoke consent to erase all saved templates.
- Enable “Include only relevant course excerpts” to select small passages from professor-uploaded course materials. Only keyword-matching passages are sent; otherwise the fixed course syllabus is used.
- View estimated input tokens and Gemini-reported real counts if a live Gemini request succeeds.
- In **My portfolio**, choose delete-all to remove private practice records and any custom prompt templates.

Optional automated tests:

```powershell
python -m pip install pytest
python -m pytest -q tests
```

## Push when tested

```powershell
git status
git add app.py ai_service.py student_workspace.py storage.py portfolio_ui.py prompt_engine.py tests/test_prompt_optimization.py
git diff --cached --stat
git commit -m "Optimize student prompts and course-specific AI context"
git pull --rebase origin main
git push origin main
```

**Before pushing**, verify Git does not track `.env` or any `.db` files.

## Important limitations

- Approximate input-token calculations use a character heuristic; **Gemini tokenization is different**. The actual provider-reported counts shown after a successful call are authoritative for that request.
- Shorter prompts and per-session caching **can** reduce repeated API calls and token use. Actual pricing, environmental footprint or emissions reductions have not been measured. It would be inaccurate to claim quantified carbon savings from this prototype.
- Prompts, uploaded materials and questions submitted to Gemini leave the local machine. Use only fictional demo/student-consented content, and review institutional GDPR requirements before real deployment.
- The custom prompt library and private learning portfolio are not visible in the professor portal.
- The login/SQLite storage still is a demonstration, not production-grade security.
