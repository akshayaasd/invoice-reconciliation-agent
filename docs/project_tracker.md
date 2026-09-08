# Project Tracker

## Status

| Task | Status | Notes |
|---|---|---|\
| Analyze brief and data files | ✅ Done | Read all CSVs, found ID normalization requirement and status/date trap |
| ID normalization | ✅ Done | `normalize_job_ref` handles `04401`, `4432-R2` → `JOB-04401`, `JOB-04432` |
| Reconciliation engine | ✅ Done | Returns structured dicts with `severity`, `dollar_impact`, `allowed` |
| Needs review bucket | ✅ Done | Jobs with contradicting status/completion dates held out of dispute email |
| LLM email drafting | ✅ Done | Ollama with deterministic fallback from findings object |
| FastAPI backend | ✅ Done | `/api/metadata`, `/api/analyze`, `/api/send_email` |
| React + Tailwind frontend | ✅ Done | Agentic thinking loop, computed KPIs, editable draft, approval gate |
| Resend email dispatch | ✅ Done | Real delivery, attachment included |
| Human approval gate | ✅ Done | Button is the only code path to send_email |
| Submission note | ✅ Done | Covers what broke, what's stubbed, what's next, AI usage |
| Record demo video | ⬜ Todo | 5-minute narrated walkthrough |
