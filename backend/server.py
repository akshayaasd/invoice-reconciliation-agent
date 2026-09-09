import hashlib
import hmac
import secrets

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os

from reconciliation import analyze_invoice
from llm import draft_email_with_llm
from tools import send_email

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
invoice_path = os.path.join(data_dir, "CorridorLine_Invoice_MAR2026.csv")
metadata = {
    "vendor": "Corridor Line Construction LLC",
    "invoice_no": "CLC-26-0342",
    "period": "March 2026",
    "bill_to": "Riverton Broadband Partners",
    "po_ref": "PO-2026-0117",
    "contact": "ap@corridorline.example"
}

# ---------------------------------------------------------------------------
# Structural approval gate
# The architectural gate (LLM never gets a tool schema) is the primary defence.
# This structural gate ensures the same guarantee holds if tool access is ever
# added: send_email cannot run without a token bound to the exact message a
# human approved.
# ---------------------------------------------------------------------------

_PENDING_APPROVALS: dict[str, str] = {}  # token -> SHA-256 digest of (to, subject, body)


def _digest(to: str, subject: str, body: str) -> str:
    import json
    payload = json.dumps({"to": to, "subject": subject, "body": body},
                         sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class EmailRequest(BaseModel):
    email_body: str
    invoice_no: str
    csv_data: str


@app.get("/api/metadata")
def get_metadata():
    return metadata


@app.post("/api/analyze")
def analyze():
    try:
        discrepancies, lines_audited, estimated_overbilling, summary_by_severity, disputed_overbilling = analyze_invoice(data_dir, invoice_path)

        # Draft email — LLM only sees Disputed lines, not Needs review.
        email_draft = draft_email_with_llm(discrepancies, metadata)

        # Mint an approval token bound to the exact draft message.
        # The frontend must send this token back to /api/send_email.
        to = metadata["contact"]
        subject = f"Invoice {metadata['invoice_no']} — Dispute Notice"
        token = secrets.token_urlsafe(16)
        _PENDING_APPROVALS[token] = _digest(to, subject, email_draft)

        return {
            "discrepancies": discrepancies,
            "lines_audited": lines_audited,
            "estimated_overbilling": estimated_overbilling,
            "disputed_overbilling": disputed_overbilling,
            "summary_by_severity": summary_by_severity,
            "email_draft": email_draft,
            "approval_token": token,
            "email_subject": subject,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SendRequest(BaseModel):
    email_body: str
    invoice_no: str
    csv_data: str
    approval_token: str
    email_subject: str


@app.post("/api/send_email")
def send_dispute_email(req: SendRequest):
    """Dispatch the vendor email only after verifying the approval token.

    The token is bound to the exact (to, subject, body) the human approved.
    Editing the body in the UI after approval invalidates the token.
    Tokens are single-use: consumed here and removed from the pending set.
    """
    to = "ap@corridorline.example"
    subject = req.email_subject

    expected_digest = _PENDING_APPROVALS.pop(req.approval_token, None)
    if expected_digest is None:
        raise HTTPException(
            status_code=403,
            detail="Invalid or already-used approval token. A human must approve this specific message before it can be sent."
        )

    actual_digest = _digest(to, subject, req.email_body)
    if not hmac.compare_digest(expected_digest, actual_digest):
        raise HTTPException(
            status_code=403,
            detail="Message content has changed since approval. Re-run the audit or re-approve the edited draft."
        )

    try:
        result = send_email(
            to=to,
            subject=subject,
            body=req.email_body,
            attachment_csv=req.csv_data.encode('utf-8'),
            attachment_filename=f"audit_report_{req.invoice_no}.csv"
        )
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
