# Contributing to OneQueue

Thank you for your interest in contributing to OneQueue — a local-first AI workbench for solo builders.

## Project Overview

OneQueue is a task queue system for managing Ollama AI model generation requests safely on local hardware. It consists of:

- **Backend**: FastAPI + SQLModel + SQLite
- **Frontend**: React 19 + Vite
- **Worker**: Background task processing with system resource monitoring

## The WE Philosophy

OneQueue is built with the **"WE"** philosophy — collaborative building with testing at every step. The user considers AI agents as partners, not tools. This means:

1. **Always test your changes** — Run the application and verify functionality before considering work complete
2. **Test-first development** — Write tests before implementing features
3. **Transparent communication** — Report what you tried, what worked, and what didn't
4. **Respect the user** — The user controls the launch script; no hidden background processes

## Project Workflow

### Branch Naming

All work happens on feature branches following the convoy pattern:

```
convoy/<feature-name>/<convoy-id>/head
```

### Development Cycle

1. **Pick up a bead** — Work items are assigned via the Gastown orchestration system
2. **Make commits frequently** — Small, focused commits with descriptive messages
3. **Push after every commit** — The container is ephemeral; unpushed work is lost
4. **Call gt_done when complete** — The Refinery handles merging

### Commit Messages

- Use clear, concise messages that explain the "why"
- Reference the bead ID if applicable
- Examples: "add sustained load guardrail to prevent RAM spikes", "fix await on fetch calls"

## Multi-Agent Collaboration

OneQueue uses the Gastown orchestration system for multi-agent collaboration:

- **Convoys**: Group related beads into a single feature delivery
- **Beads**: Individual work items (issues, bugs, tasks)
- **Polecats**: Agents that pick up and execute beads
- **Refinery**: Agent that reviews and merges completed work

### Coordination

- Check for undelivered mail with `gt_mail_check`
- Send updates to other agents with `gt_mail_send`
- Use `gt_nudge` for time-sensitive coordination

## Setup for Contributors

### Prerequisites

- Python 3.13+
- Node.js 20+
- Ollama running locally on port 11434

### Local Development Setup

1. **Clone the repository**

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install frontend dependencies**
   ```bash
   cd frontend
   npm install
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` to confirm:
   - `OLLAMA_BASE_URL=http://localhost:11434`
   - `DATABASE_URL=sqlite:///./data/onequeue.db`

5. **Start the backend**
   ```bash
   python -m app.main
   ```

6. **Start the frontend**
   ```bash
   cd frontend
   npm run dev
   ```

7. **Verify with a test task**
   - Open http://localhost:5173
   - Create a task with a simple prompt (e.g., "Hello, world!")
   - Confirm the task completes successfully

### Using the Launch Scripts

On Windows, use the provided PowerShell scripts:

```powershell
# Start OneQueue
.\start-onequeue.ps1

# Stop OneQueue
.\stop-onequeue.ps1
```

### Running Tests

```bash
# Backend tests
python -m pytest

# Frontend tests
cd frontend
npm run test
```

## Code Standards

### Python

- Use Pydantic for data validation
- Use SQLModel for database models
- Type hints on all function signatures
- No secrets in code (use environment variables)

### JavaScript/React

- Functional components with hooks
- ESLint configuration enabled
- TypeScript recommended for new components

### General

- No console.log in production code
- Use the logging service for application logs
- Test at every step — verify before considering done

## Getting Help

- Check PROGRESS.md for the current project state
- Review docs/specs/onequeue-mvp.md for the specification
- Use `gt_mail_send` to coordinate with other agents

## Security Considerations

- Never commit secrets or API keys
- Use `.env` for sensitive configuration
- The `.env` file is in `.gitignore`
- If you find a security issue, report it through proper channels