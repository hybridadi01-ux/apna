# Development

Backend: `cd backend && python -m uvicorn server:app --reload --port 8001`.
Frontend: `cd frontend && yarn start`.
Backend syntax check: `python -m py_compile backend/server.py`.
Frontend production check: `cd frontend && yarn build`.

Keep API calls on `REACT_APP_BACKEND_URL`. Do not place credentials in source control. Use the seed users only for local testing.