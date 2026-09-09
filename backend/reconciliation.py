from decimal import Decimal, ROUND_HALF_UP
import pandas as pd
import os
import re

_CENTS = Decimal("0.01")


def _to_money(value) -> Decimal:
    """Quantise to whole cents, rounding half up."""
    return Decimal(str(value)).quantize(_CENTS, rounding=ROUND_HALF_UP)


def normalize_job_ref(ref):
    if pd.isna(ref):
        return ref
    # Extract the first group of digits and zero-pad to 5 — handles both
    # "04435" and "4432-R2" (revision suffix is intentionally ignored).
    match = re.search(r'\d+', str(ref))
    if match:
        return f"JOB-{match.group(0).zfill(5)}"
    return ref


def _find_header_row(path: str) -> int:
    """Locate the line-item header row by looking for a 'Job Ref' column.

    Using skiprows=6 is fragile: one extra line in the preamble silently reads
    metadata as invoice lines. Looking for the header is robust to that.
    """
    with open(path, encoding='utf-8-sig') as f:
        for i, line in enumerate(f):
            if 'job ref' in line.lower():
                return i
    raise ValueError(f"Could not find 'Job Ref' header row in {path}")


def analyze_invoice(data_dir: str, invoice_path: str = None) -> tuple:
    print("Loading datasets...")
    if not invoice_path:
        invoice_path = os.path.join(data_dir, "CorridorLine_Invoice_MAR2026.csv")
    jobs_path = os.path.join(data_dir, "sitetracker_jobs_export.csv")
    po_lines_path = os.path.join(data_dir, "sitetracker_po_lines_export.csv")

    # Locate the header row dynamically rather than assuming a fixed offset.
    header_row = _find_header_row(invoice_path)
    invoice_df = pd.read_csv(invoice_path, skiprows=header_row)
    # Drop rows where 'Job Ref' is NaN (footer/totals row).
    invoice_df = invoice_df.dropna(subset=['Job Ref']).copy()
    # Also drop rows whose Job Ref contains 'total' (footer guard)
    invoice_df = invoice_df[~invoice_df['Job Ref'].astype(str).str.lower().str.contains('total')].copy()

    jobs_df = pd.read_csv(jobs_path)
    po_df = pd.read_csv(po_lines_path)

    # Normalize Invoice Job Refs to match Sitetracker Job Numbers.
    invoice_df['Normalized_Job_Number'] = invoice_df['Job Ref'].apply(normalize_job_ref)

    discrepancies = []
    lines_audited = len(invoice_df)

    for _, row in invoice_df.iterrows():
        job_num = row['Normalized_Job_Number']
        work_item = row['Work Item']
        # Use Decimal for all money arithmetic — float equality on 2.15 / 14.50 is unreliable.
        inv_qty = _to_money(row['Qty'])
        inv_rate = _to_money(row['Rate'])
        original_ref = row['Job Ref']
        line_total = _to_money(row['Line Total'])

        # --- Rule 1: Job exists in Sitetracker ---
        job_match = jobs_df[jobs_df['sitetracker__Job_Number__c'] == job_num]

        if job_match.empty:
            discrepancies.append({
                "job": job_num,
                "work_item": work_item,
                "status": "Not Found",
                "rule": "Job not found in Sitetracker.",
                "severity": "Disputed",
                "billed": float(line_total),
                "allowed": 0.0,
                "dollar_impact": float(line_total),
                "original_ref": original_ref
            })
            continue

        job_status = job_match.iloc[0]['sitetracker__Job_Status__c']
        actual_end = job_match.iloc[0]['sitetracker__Actual_End__c']
        st_comp = job_match.iloc[0]['sitetracker__st_Job_Completion_Date__c']

        # --- Rule 2: Job completion check ---
        if job_status != "Completed":
            if pd.notna(actual_end) or pd.notna(st_comp):
                # Status and completion dates contradict each other.
                # Our own data is inconsistent — do NOT assert non-performance to the vendor.
                # Route to internal review only.
                discrepancies.append({
                    "job": job_num,
                    "work_item": work_item,
                    "status": job_status,
                    "rule": f"Status contradicts completion dates (Status: {job_status}, End: {actual_end})",
                    "severity": "Needs review",
                    "billed": float(line_total),
                    "allowed": 0.0,
                    "dollar_impact": float(line_total),
                    "original_ref": original_ref
                })
            else:
                discrepancies.append({
                    "job": job_num,
                    "work_item": work_item,
                    "status": job_status,
                    "rule": f"Billed for job that is not completed. Current status: '{job_status}'.",
                    "severity": "Disputed",
                    "billed": float(line_total),
                    "allowed": 0.0,
                    "dollar_impact": float(line_total),
                    "original_ref": original_ref
                })
            continue

        # --- PO lookup (for completed jobs) ---
        po_match = po_df[
            (po_df['sitetracker__st_Job__r.sitetracker__Job_Number__c'] == job_num) &
            (po_df['Work_Item_Code__c'] == work_item)
        ]

        if po_match.empty:
            discrepancies.append({
                "job": job_num,
                "work_item": work_item,
                "status": "Completed",
                "rule": "No matching PO line found for this work item on this job.",
                "severity": "Disputed",
                "billed": float(line_total),
                "allowed": 0.0,
                "dollar_impact": float(line_total),
                "original_ref": original_ref
            })
            continue

        # Use Decimal for PO values too — avoids float inequality on exact values like 2.15.
        po_qty = _to_money(po_match.iloc[0]['sitetracker__Quantity__c'])
        po_rate = _to_money(po_match.iloc[0]['sitetracker__Unit_Price__c'])

        # --- Rule 3: Quantity overage — only the excess is disputed ---
        if inv_qty > po_qty:
            excess = inv_qty - po_qty
            dollar_impact = _to_money(excess * inv_rate)
            discrepancies.append({
                "job": job_num,
                "work_item": work_item,
                "status": "Completed",
                "rule": f"Overbilled quantity. Billed {inv_qty}, PO allows {po_qty}.",
                "severity": "Disputed",
                "billed": float(line_total),
                "allowed": float(_to_money(po_qty * inv_rate)),
                "dollar_impact": float(dollar_impact),
                "original_ref": original_ref
            })

        # --- Rule 4: Rate mismatch (Decimal comparison — exact) ---
        if inv_rate != po_rate:
            if inv_rate > po_rate:
                # Only the overage on the authorised quantity is disputed.
                dollar_impact = float(_to_money((inv_rate - po_rate) * min(inv_qty, po_qty)))
                discrepancies.append({
                    "job": job_num,
                    "work_item": work_item,
                    "status": "Completed",
                    "rule": f"Rate mismatch. Billed {inv_rate}, PO specifies {po_rate}.",
                    "severity": "Disputed",
                    "billed": float(line_total),
                    "allowed": float(_to_money(inv_qty * po_rate)),
                    "dollar_impact": dollar_impact,
                    "original_ref": original_ref
                })
            # Under-billing is in Riverton's favour — recorded but not disputed.

    # --- Totals ---
    # disputed_overbilling: only lines that are being actively disputed with the vendor
    # estimated_overbilling: all flagged money (includes Needs review) — kept for internal dashboard
    disputed_overbilling = sum(
        d['dollar_impact'] for d in discrepancies if d['severity'] == 'Disputed'
    )
    estimated_overbilling = sum(d['dollar_impact'] for d in discrepancies)

    summary_by_severity = {}
    for d in discrepancies:
        sev = d['severity']
        summary_by_severity[sev] = summary_by_severity.get(sev, 0.0) + d['dollar_impact']

    return discrepancies, lines_audited, estimated_overbilling, summary_by_severity, disputed_overbilling
