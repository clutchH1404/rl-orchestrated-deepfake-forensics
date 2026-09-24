# VERITAS frontend

This zero-build frontend implements the supplied tactical-forensics visual direction while using live backend responses only. It does not contain hardcoded forensic claims, source matches, confidence scores, or stock “evidence” images.

Start the backend from the repository root:

```powershell
python -m uvicorn backend.main:app --reload
```

In a second terminal, serve the frontend:

```powershell
python -m http.server 5173 --directory frontend
```

Open `http://localhost:5173`. The default backend is `http://127.0.0.1:8000/api/v1`, which matches the configured CORS origin.
