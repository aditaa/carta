# Frontend

React frontend for Carta Arcanum.

## Setup

```bash
cd frontend
npm install
```

## Run

Start the FastAPI backend first:

```bash
uvicorn app.main:app --reload --app-dir backend
```

Then run the frontend:

```bash
cd frontend
npm run dev
```

The app starts at:

```text
http://127.0.0.1:5173
```

Vite proxies `/api` requests to `http://127.0.0.1:8000`.

## Checks

```bash
npm run lint
npm run typecheck
npm test -- --run
npm run build
```
