# Invoice Reconciliation Agent — Sitetracker AI Demo Engineer Exercise

**The short version:** $56,178.00 of Corridor Line's March invoice does not hold up. 32.5% of it is billing for work Sitetracker says has not been completed. This agent finds it in seconds, explains every line, drafts a dispute notice, and requires a human to approve before anything leaves the building.

---

## What it does

1. Loads the invoice and Sitetracker CSVs, normalizes mismatched job IDs (`4432-R2` → `JOB-04432`), and runs five reconciliation rules across all 40 invoice lines.
2. Classifies each discrepancy as **Disputed** (bill this back) or **Needs review** (status contradicts completion dates — verify before disputing).
3. Passes the disputed lines to a local LLM (Ollama) to draft a professional dispute email. If Ollama is unreachable, a deterministic f-string template builds the email from the same findings object — no canned strings.
4. Presents everything in a React dashboard. The draft is editable. Nothing sends until a human clicks **Approve & Send to Vendor**.

---

## Project structure

```
invoice-reconciliation-agent/
├── backend/
│   ├── server.py           # FastAPI — /api/metadata, /api/analyze, /api/send_email
│   ├── reconciliation.py   # Pandas join + five reconciliation rules
│   ├── llm.py              # Ollama call + deterministic fallback
│   ├── tools.py            # send_email via Resend
│   ├── requirements.txt
│   └── .env.example        # Copy to .env, add RESEND_API_KEY
├── web-ui/                 # Next.js 16 + Tailwind
├── data/
│   ├── CorridorLine_Invoice_MAR2026.csv
│   ├── sitetracker_jobs_export.csv
│   ├── sitetracker_po_lines_export.csv
│   ├── AI_Demo_Engineer_TakeHome_Brief.md
│   └── send_email_tool_spec.md
├── docs/
│   ├── submission_note.md  # What broke, what's stubbed, what's next, AI usage
│   ├── implementation.md   # Architecture, stack choices, reconciliation rules
│   └── project_tracker.md
└── prompt.txt              # Plain-text prompt sent to the LLM
```

---

## Running it

### 1. Backend

```bash
cd backend
pip3 install -r requirements.txt

# Optional: copy .env.example to .env and add your Resend key for real email delivery
cp .env.example .env

python3 -m uvicorn server:app --reload --host 127.0.0.1 --port 8000
```

### 2. Frontend

```bash
cd web-ui
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### 3. LLM (optional)

If you have Ollama installed:
```bash
ollama pull llama3
ollama serve
```

If not, the fallback generates a deterministic email from the findings. The demo works either way.

---

## The numbers

| Finding | Amount |
|---|---|
| Billed on jobs not marked Completed | $45,705.50 |
| Overbilled quantity vs PO | $5,653.50 |
| Status contradicts completion dates (Needs review) | $10,472.50 |
| **Total exposure** | **$56,178.00** |
| Share of $172,929.50 invoice | **32.5%** |

---

## Design decisions worth noting

**Why the LLM only sees Disputed lines, not Needs review:** The two `Needs review` jobs (`JOB-04433`, `JOB-04434`) have `In Progress` status but have completion dates populated — almost certainly a coordinator who forgot to flip the status. Disputing those with a vendor without a phone call first is how you damage a relationship. They're surfaced in the audit table with a yellow badge, held out of the draft email.

**Why the approval gate is structural, not prompted:** The brief says "the agent must not be able to route around it." We did not write "ask before sending" into a system prompt. The LLM has no tool to call `send_email`. The only call site is a FastAPI route triggered by a button a human clicks. There is no code path around it.

**Why the fallback is f-strings, not a canned string:** A canned string stays accurate for the March data and becomes a confident lie the moment April's invoice loads. The f-string fallback rebuilds from the same findings dict used for the UI table, so it is always in sync.
