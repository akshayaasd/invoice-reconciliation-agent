# Invoice Reconciliation Agent — Implementation

## Architecture

**Backend:** Python + FastAPI. A single `POST /api/analyze` endpoint loads the three CSVs, runs the reconciliation engine, calls the LLM, and returns structured JSON. A `POST /api/send_email` endpoint dispatches via Resend after human approval. 

**Frontend:** Next.js 16 + Tailwind CSS. Single-page React app. Fetches from the FastAPI backend on the same machine.

**LLM:** Ollama (local, `llama3` by default). No API key required. If unreachable, falls back to deterministic templating from the findings object. The fallback is not a canned string, it reconstructs the logic perfectly based on the findings.

## Stack choices & Best Practices

- **Python + pandas** for reconciliation: fast, auditable, no hallucination risk.
- **Decimal Arithmetic:** Float math is unreliable for currency (e.g. `2.15` vs `14.50`). All rate/qty math uses `decimal.Decimal` quantized to cents.
- **Dynamic Header Parsing:** Hardcoding row offsets (`skiprows=6`) is fragile. The backend dynamically searches for the 'Job Ref' column header so changes to the vendor's preamble won't break the parse.

## Data findings & Nuance

- **ID normalization required:** Invoice uses `04401`, `4432-R2`. Sitetracker uses `JOB-04401`, `JOB-04432`. Solution: `normalize_job_ref` regex extracts first digit group, zero-pads to 5, prefixes `JOB-`.
- **Invoice CSV footer row:** `INVOICE TOTAL` in Rate column breaks parsers. Solution: drop rows with null `Job Ref` or 'total' strings before coercion.
- **Status / completion date contradiction:** `JOB-04433` and `JOB-04434` are `In Progress` but have `Actual_End` and `Job_Completion_Date` populated. These are routed to `Needs review`, not `Disputed`. This keeps $10,472.50 out of the dispute email to protect the vendor relationship against our own messy data.

## Tier-Aware Email Prompting

The LLM logic splits the "Disputed" items into two distinct legal postures:
1. **Confirmed Discrepancies:** (Cancelled, Scheduled, Overbilled). The LLM is instructed to aggressively assert these as facts.
2. **Items Pending Completion:** (In Progress, no completion date). The LLM is strictly instructed *not* to say the work was never performed (the crew may be on site today), but merely that it is "not recorded as complete and therefore not yet billable."

## Human-in-the-loop: The Structural Approval Gate

The approval step is not a UX nicety — it is a cryptographic firewall.
The LLM has read access to the findings object and nothing else. It is never given a tool to send emails. When `/api/analyze` runs, the server mints a single-use SHA-256 token mathematically bound to the exact `(to, subject, body)` text of the drafted email. The `/api/send_email` route refuses to execute without that exact token. If an LLM tried to bypass the frontend, or if the text was tampered with, the digest wouldn't match and the tool would fail.
