# Submission Note

## What broke, and what we changed to fix it

**ID normalization was the hard problem.** Corridor Line uses their own internal format (`04401`, `4432-R2`). Sitetracker pads and prefixes (`JOB-04401`, `JOB-04432`). A naive join produces zero matches. We wrote `normalize_job_ref` — a regex that extracts the first digit group, zero-pads to 5 digits, and prefixes `JOB-`. All 40 invoice lines resolve cleanly, including the `4432-R2` suffix case.

**The invoice CSV has a footer row** (`INVOICE TOTAL` in the Rate column) that broke float casting. We dropped rows with an empty `Job Ref` before type coercion.

**The AI wrote three contradictory docs.** One said OpenAI API, one said google-genai or Anthropic, the code used Ollama. We caught this by reading every file before shipping. We standardized on Ollama (local, no key needed) with a deterministic f-string fallback — not a canned string, because a canned string decouples the email from the audit and becomes wrong the moment the data changes. The fallback rebuilds from the findings object every time.

**The original `analyze_invoice` returned `list[str]`.** Prose. No amounts, no severity. We refactored it to return structured dicts (`{job, work_item, rule, severity, billed, allowed, dollar_impact}`) so the UI can display real dollar impact per line and sum by severity.

---

## What we stubbed, and why

**`send_email`** is wired to Resend (real API, real delivery) but the recipient is a test address. In production this would be `ap@corridorline.example`. Stubbing the recipient is the right call for a demo: it lets us prove the full path — human approves, email dispatches, attachment attaches — without risking an actual vendor relationship on a demo dataset.

**Sitetracker API** is simulated via the provided CSVs and `pandas`. The brief said "assume any external system is available." CSV processing is faster, more reliable in a demo, and produces identical output to a live API call given the same data.

**LLM generation** uses Ollama locally. If Ollama is not running, the fallback generates the email deterministically from the same findings object used for the audit table. The email is always accurate because it is always computed from the same data, never from a canned string.

---

## What we would build next vs. what we would deliberately never build

**Next:** A severity filter on the dispute email — today the UI surfaces a `Needs review` bucket (jobs whose status says In Progress but have completion dates populated, which likely reflects a coordinator who forgot to flip the status). We hold those out of the dispute email, which is correct. But we would surface them to the reviewer as a "verify before disputing" panel, and let the human promote or demote individual lines before drafting.

**Also next:** Invoice total cross-check (`sum of lines != invoice footer`), duplicate line detection, and rate mismatch flagging — we ran all six on this dataset and they came back clean, but the checks should still appear in the report. "Here are the six things I checked that passed" is a trust signal.

**Never:** An autonomous mode that skips human approval. The approval step is not a UX nicety — it is a legal and relationship firewall. The model sees the audit data but never touches `send_email`. The only code path to dispatch runs through a button a human clicks. We would not change that even at a customer's request.

---

## Where we used AI and how we validated it

AI bootstrapped the reconciliation logic, the FastAPI server, and the React UI. We validated it by:

1. Running `analyze_invoice` against the real CSVs and manually verifying each of the 13 discrepancies against the source data (confirmed `JOB-04438` is `Cancelled`, confirmed `JOB-04435` has PO qty 900 vs billed 1140, etc.).
2. Reading every file the AI produced. That is how we caught the three-way LLM story inconsistency and the hardcoded `$34k` KPI that no arithmetic in the repo could justify.
3. Catching the status/completion-date trap. `JOB-04433` and `JOB-04434` are `In Progress` but both have `sitetracker__Actual_End__c` and `sitetracker__st_Job_Completion_Date__c` populated. The AI classified them identically to `JOB-04430` (Unassigned, no dates). We added the contradiction check and routed them to a separate `Needs review` bucket, keeping them out of the dispute email. That is $10,472.50 of the total that should not be disputed without a phone call first.
