# OneQueue UI Guide

The dashboard is served at **http://<VPS‑IP>:8081/ui**.

## How it works
- The page loads the model catalog from `/v1/models` and populates the drop‑down.
- Submitting the form creates a new task via `POST /tasks`.
- The task table refreshes every 5 seconds showing status and result.

## Visual design
- Dark background with neon green accent (`#00ff99`).
- Simple layout using native HTML elements – no heavy JavaScript frameworks.
- Styles are defined in `frontend_ui/style.css`.

## Extending
- Add more sections by editing `frontend_ui/index.html` and corresponding JS in `frontend_ui/main.js`.
- The static files are mounted by FastAPI at `/ui` (see `app/main.py`).

## Development
```bash
# From the repository root on the VPS
npm install   # (optional, only needed if you want to use the React Vite UI)
# The vanilla UI lives in frontend_ui and does not require a build step.
```

## Testing
Run the automated UI test script:
```bash
python -m pytest tests/test_ui_flow.py
```
It verifies that the dashboard loads, a task can be created, and the task completes.
