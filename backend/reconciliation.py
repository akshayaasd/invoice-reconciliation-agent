import pandas as pd
import os
import re

def normalize_job_ref(ref):
    if pd.isna(ref):
        return ref
    # Extract the first group of digits
    match = re.search(r'\d+', str(ref))
    if match:
        return f"JOB-{match.group(0).zfill(5)}"
    return ref

def analyze_invoice(data_dir: str, invoice_path: str = None) -> tuple:
    print("Loading datasets...")
    if not invoice_path:
        invoice_path = os.path.join(data_dir, "CorridorLine_Invoice_MAR2026.csv")
    jobs_path = os.path.join(data_dir, "sitetracker_jobs_export.csv")
    po_lines_path = os.path.join(data_dir, "sitetracker_po_lines_export.csv")
    
    # Skip the first 6 rows of the invoice which contain header metadata
    invoice_df = pd.read_csv(invoice_path, skiprows=6)
    # Drop rows where 'Job Ref' is NaN (like the footer/totals row)
    invoice_df = invoice_df.dropna(subset=['Job Ref']).copy()
    
    jobs_df = pd.read_csv(jobs_path)
    po_df = pd.read_csv(po_lines_path)
    
    # Normalize Invoice Job Refs to match Sitetracker Job Numbers
    invoice_df['Normalized_Job_Number'] = invoice_df['Job Ref'].apply(normalize_job_ref)
    
    # Reconcile
    discrepancies = []
    lines_audited = len(invoice_df)
    
    for _, row in invoice_df.iterrows():
        job_num = row['Normalized_Job_Number']
        work_item = row['Work Item']
        inv_qty = float(row['Qty'])
        inv_rate = float(row['Rate'])
        original_ref = row['Job Ref']
        line_total = float(row['Line Total'])
        
        # Check against Jobs
        job_match = jobs_df[jobs_df['sitetracker__Job_Number__c'] == job_num]
        
        if job_match.empty:
            discrepancies.append({
                "job": job_num,
                "work_item": work_item,
                "rule": "Job not found in Sitetracker.",
                "severity": "Disputed",
                "billed": line_total,
                "allowed": 0.0,
                "dollar_impact": line_total,
                "original_ref": original_ref
            })
            continue
            
        job_status = job_match.iloc[0]['sitetracker__Job_Status__c']
        actual_end = job_match.iloc[0]['sitetracker__Actual_End__c']
        st_comp = job_match.iloc[0]['sitetracker__st_Job_Completion_Date__c']
        
        if job_status != "Completed":
            # The trap: status is In Progress but completion dates exist
            if pd.notna(actual_end) or pd.notna(st_comp):
                discrepancies.append({
                    "job": job_num,
                    "work_item": work_item,
                    "rule": f"Status contradicts completion dates (Status: {job_status}, End: {actual_end})",
                    "severity": "Needs review",
                    "billed": line_total,
                    "allowed": 0.0,
                    "dollar_impact": line_total,
                    "original_ref": original_ref
                })
            else:
                discrepancies.append({
                    "job": job_num,
                    "work_item": work_item,
                    "rule": f"Billed for job that is not completed. Current status: '{job_status}'.",
                    "severity": "Disputed",
                    "billed": line_total,
                    "allowed": 0.0,
                    "dollar_impact": line_total,
                    "original_ref": original_ref
                })
            continue
            
        # Check against PO Lines
        po_match = po_df[(po_df['sitetracker__st_Job__r.sitetracker__Job_Number__c'] == job_num) & 
                         (po_df['Work_Item_Code__c'] == work_item)]
        
        if po_match.empty:
            discrepancies.append({
                "job": job_num,
                "work_item": work_item,
                "rule": "No matching PO line found for this work item on this job.",
                "severity": "Disputed",
                "billed": line_total,
                "allowed": 0.0,
                "dollar_impact": line_total,
                "original_ref": original_ref
            })
            continue
            
        po_qty = float(po_match.iloc[0]['sitetracker__Quantity__c'])
        po_rate = float(po_match.iloc[0]['sitetracker__Unit_Price__c'])
        
        if inv_qty > po_qty:
            discrepancies.append({
                "job": job_num,
                "work_item": work_item,
                "rule": f"Overbilled quantity. Billed {inv_qty}, PO allows {po_qty}.",
                "severity": "Disputed",
                "billed": line_total,
                "allowed": po_qty * inv_rate,
                "dollar_impact": (inv_qty - po_qty) * inv_rate,
                "original_ref": original_ref
            })
            
        if inv_rate != po_rate:
            if inv_rate > po_rate:
                dollar_impact = (inv_rate - po_rate) * min(inv_qty, po_qty)
            else:
                dollar_impact = 0.0
                
            discrepancies.append({
                "job": job_num,
                "work_item": work_item,
                "rule": f"Rate mismatch. Billed {inv_rate}, PO specifies {po_rate}.",
                "severity": "Disputed",
                "billed": line_total,
                "allowed": inv_qty * po_rate,
                "dollar_impact": dollar_impact,
                "original_ref": original_ref
            })
            
    estimated_overbilling = sum(d['dollar_impact'] for d in discrepancies)
    
    summary_by_severity = {}
    for d in discrepancies:
        severity = d['severity']
        summary_by_severity[severity] = summary_by_severity.get(severity, 0.0) + d['dollar_impact']
            
    return discrepancies, lines_audited, estimated_overbilling, summary_by_severity
