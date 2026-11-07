# LectureLoop — Gemini hackathon version

## Quick start (Windows + VS Code)

1. Copy these files into your existing `hackathon-ai` folder. Replace `app.py` and `requirements.txt`.
2. Create a file called `.env` in the same folder. Use `.env.example` as a template and paste your actual Gemini API key locally.
3. With your existing Python virtual environment activated, run:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

4. Ask a fictional learning question in Student mode, check the cloud API acknowledgement, optionally opt in to an aggregate topic report, and switch to the Professor dashboard.
5. If the dashboard shows no local topics, choose **Sample classroom (demo)** to display fictional counts.

## Notes

- Uses the official `google-genai` package, not `google-generativeai`.
- The model is set using `GEMINI_MODEL` in `.env` (default `gemini-3.5-flash-lite`); your API key needs access to the selected model.
- If the API isn't configured, the app uses clearly labeled scripted demo explanations.
- If Gemini fails, the actual error is displayed and fallback content is labeled as scripted.
- The `.env` and `learning_space.db` files are excluded from git by `.gitignore`.
- Questions are sent to Google Gemini in API mode. Do not use confidential questions or actual student submissions without appropriate consent and data-use review; Google's free tier has different privacy terms from paid services.
- Topic counts are stored locally only if opted in. Raw questions and names are not stored in SQLite, but questions and responses pass through Streamlit memory in the live session.
- This prototype is not production-safe. There are no class membership controls or professor authentication; the count suppression threshold only hides low-volume categories and does not guarantee anonymity. Counts are **reports**, not **unique students**.
