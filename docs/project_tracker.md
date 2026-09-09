# Project Tracker

## Status

| Task | Status | Notes |
|---|---|---|
| Analyze brief and data files | ✅ Done | Read all CSVs, found ID normalization requirement and status/date trap |
| ID normalization | ✅ Done | `normalize_job_ref` handles `04401`, `4432-R2` → `JOB-04401`, `JOB-04432` |
| Reconciliation engine | ✅ Done | Returns structured dicts with `severity`, `dollar_impact`, `allowed`, `status` |
| Needs review bucket | ✅ Done | Jobs with contradicting status/completion dates held out of dispute email |
| Float → Decimal arithmetic | ✅ Done | All rate/qty math uses `decimal.Decimal` — no float coin-flip on `2.15`, `14.50` |
| Dynamic header parsing | ✅ Done | `_find_header_row()` replaces `skiprows=6` — robust to vendor format changes |
| Status column in CSV & UI | ✅ Done | Sitetracker status (Cancelled, Scheduled, In Progress…) shown in table and exported |
| LLM email drafting | ✅ Done | Ollama with deterministic fallback; tier-aware language (Confirmed vs Not Yet Billable) |
| Tier-aware email language | ✅ Done | Category 1 asserted as fact; Category 2 as "not yet billable" (crew may be on site) |
| FastAPI backend | ✅ Done | `/api/metadata`, `/api/analyze`, `/api/send_email` |
| React + Tailwind frontend | ✅ Done | Agentic thinking loop, computed KPIs, Status column in table, editable draft |
| `disputed_overbilling` vs `estimated_overbilling` | ✅ Done | API returns both; UI red alert uses `disputed_overbilling` ($45,705.50) |
| Structural SHA-256 approval token | ✅ Done | Token minted at analyze time, consumed at send time, single-use |
| Resend email dispatch | ✅ Done | Real delivery, attachment included, token verified before dispatch |
| Human approval gate | ✅ Done | Architectural gate (LLM has no tool) + structural gate (SHA-256 token) |
| Submission note | ✅ Done | Covers what broke, what's stubbed, what's next, AI usage, all fixes |
| Implementation doc | ✅ Done | Updated with Decimal, dynamic headers, tier-aware prompting, token gate |
| Demo video outline | ✅ Done | Updated with correct $45k/$10k figures, SHA-256 gate, CSV status column |
| Demo video script | ✅ Done | Updated with correct figures and talking points |
| Record demo video | ⬜ Todo | 2-3 minute narrated screen-capture walkthrough |
| Re-zip codebase | ⬜ Todo | Fresh zip of `/invoice-reconciliation-agent` folder for submission |
