# Invoice Reconciliation Agent — Implementation

## Architecture

**Backend:** Python + FastAPI. A single `POST /api/analyze` endpoint loads the three CSVs, runs the reconciliation engine, calls the LLM, and returns structured JSON. A `POST /api/send_email` endpoint dispatches via Resend after human approval. No state is held on the server — every audit is stateless and reproducible.

**Frontend:** Next.js 16 + Tailwind CSS. Single-page React app. Fetches from the FastAPI backend on the same machine. The approval button is the only path to the send endpoint — there is no other code path.

**LLM:** Ollama (local, `llama3` by default). No API key required. If unreachable, falls back to deterministic f-string templating from the findings object. The fallback is not a canned string.

## Stack choices

- **Python + pandas** for reconciliation: fast, auditable, no hallucination risk on deterministic joins.
- **FastAPI**: minimal boilerplate, automatic JSON serialization, built-in CORS support for local dev.
- **Next.js + Tailwind**: production-quality UI with zero custom CSS. Hot reload makes iteration fast.
- **Resend**: one-line email dispatch, free tier sufficient for demo, real delivery to verify the full path.
- **Ollama**: local LLM, no API cost, no network dependency during demo.

## Data findings

- **ID normalization required:** Invoice uses `04401`, `4432-R2`. Sitetracker uses `JOB-04401`, `JOB-04432`. Solution: `normalize_job_ref` regex extracts first digit group, zero-pads to 5, prefixes `JOB-`.
- **Invoice CSV footer row:** `INVOICE TOTAL` in Rate column breaks float casting. Solution: drop rows with null `Job Ref` before coercion.
- **Status / completion date contradiction:** `JOB-04433` and `JOB-04434` are `In Progress` but have `Actual_End` and `Job_Completion_Date` populated. Every other non-Completed job has those fields blank. These are routed to `Needs review`, not `Disputed`.

## Reconciliation rules

| Rule | Severity | Action |
|---|---|---|
| Job not in Sitetracker | Disputed | Flag full line amount |
| Job status ≠ Completed, no completion dates | Disputed | Flag full line amount |
| Job status ≠ Completed, completion dates present | Needs review | Hold out of dispute email |
| Billed qty > PO qty | Disputed | Flag delta × rate |
| Billed rate ≠ PO rate | Disputed | Flag delta × min(billed qty, PO qty) |

## Human-in-the-loop design

The LLM has read access to the findings object and nothing else. `send_email` is imported only into `server.py` and called only from the `POST /api/send_email` route. That route is triggered only by the frontend button. The model cannot reach the send endpoint — it was never given a tool to call it.
