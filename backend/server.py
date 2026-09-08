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
        discrepancies, lines_audited, estimated_overbilling, summary_by_severity = analyze_invoice(data_dir, invoice_path)
        
        # Draft email
        email_draft = draft_email_with_llm(discrepancies, metadata)
        
        return {
            "discrepancies": discrepancies,
            "lines_audited": lines_audited,
            "estimated_overbilling": estimated_overbilling,
            "summary_by_severity": summary_by_severity,
            "email_draft": email_draft
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/send_email")
def send_dispute_email(req: EmailRequest):
    try:
        result = send_email(
            to="ap@corridorline.example",
            subject=f"Disputed Lines - Invoice {req.invoice_no}",
            body=req.email_body,
            attachment_csv=req.csv_data.encode('utf-8'),
            attachment_filename=f"audit_report_{req.invoice_no}.csv"
        )
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
