# Deployment & Demo Guide

## Pre-Deployment Checklist

### Environment
- [ ] `GEMINI_API_KEY` set in deployment platform (Render/Heroku/etc.)
- [ ] `PORT` environment variable respected (app uses `os.getenv("PORT", 8000)`)
- [ ] `.env` file NOT committed (already in `.gitignore`)

### Verification
- [ ] App starts without warnings
- [ ] Missing API key fails fast with clear error
- [ ] All directories auto-create (memory, logs, db)
- [ ] Frontend loads at `/`
- [ ] API docs available at `/docs`

### Render Deployment Steps

1. Create new **Web Service** in Render dashboard
2. Set environment variable: `GEMINI_API_KEY=your_key_here`
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Verify: Check logs for "Application Started" message

---

## Judge / Reviewer Q&A

### ❓ "Why not let the LLM call tools directly?"

**Answer:** "Direct tool calling hides failure modes and makes behavior harder to audit. We separate planning from execution so every action is validated, explainable, and recoverable."

### ❓ "Why do you need a governance agent?"

**Answer:** "LLMs are probabilistic. Rather than assuming perfect formatting, we added a constrained self-healing layer that fixes syntax errors without changing business intent."

### ❓ "Isn't this overkill for a prototype?"

**Answer:** "We intentionally kept the business logic simple, but made the orchestration robust. In enterprise systems, correctness and observability matter more than sophistication."

### ❓ "Why SQLite and file memory?"

**Answer:** "We separated structured enterprise data from conversational context. SQLite models realistic data access, while file-based session memory demonstrates continuity without infrastructure overhead."

### ❓ "What happens if the LLM generates invalid JSON?"

**Answer:** "Our governance agent fixes formatting errors while preserving semantic structure. We enforce strict guardrails: step count must match, action names must match, and intent must be preserved. If governance violates these constraints, we reject its output."

### ❓ "How do you handle LLM timeouts?"

**Answer:** "We set a 15-second timeout on all LLM requests and implement exactly one retry for transient failures. The retry only re-calls the planner, not the entire execution flow."

### ❓ "What about data persistence on Render?"

**Answer:** "We documented that SQLite and session files are ephemeral on Render. This is intentional for a hackathon prototype. For production, we would use PostgreSQL for structured data and Redis for session storage."

### ❓ "How do you ensure the planner doesn't invent tools?"

**Answer:** "We maintain a strict tool catalog. The validator rejects any action not in the catalog. The planner's prompt explicitly lists available tools with required parameters."

### ❓ "How do you prevent governance from changing user intent?"

**Answer:** "We enforce three hard guardrails: step count must match exactly, action names must match exactly, and intent must preserve word overlap. If governance violates any constraint, we reject its output."

---

## Key Talking Points

- ✅ **"It works even when the LLM misbehaves"** - Core differentiator
- ✅ **"Separation of concerns"** - LLM plans, tools execute, governance repairs
- ✅ **"Full observability"** - Every step logged and traceable
- ✅ **"Bounded failure"** - Timeouts, retries, guardrails prevent cascading failures
- ✅ **"Enterprise-ready architecture"** - Proper orchestration, not a toy demo

---

## Known Limitations (Acceptable for Hackathon)

- ✅ SQLite + file memory are ephemeral (documented)
- ✅ Governance intent check is heuristic (acceptable)
- ✅ No concurrency hardening (not needed for demo)
- ✅ Planner quality depends on prompt (mitigated with validation)

These are **intentional tradeoffs** for a prototype, not bugs.

