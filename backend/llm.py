import requests


def draft_email_with_llm(discrepancies: list, metadata: dict = None) -> str:
    print("\nDrafting email using LLM...")

    if not metadata:
        metadata = {
            "vendor": "Corridor Line Construction LLC",
            "invoice_no": "CLC-26-0342",
            "period": "March 2026",
            "bill_to": "Riverton Broadband Partners",
            "contact": "ap@corridorline.example"
        }

    # Only Disputed lines go to the vendor — Needs review are held internally.
    disputed_items = [d for d in discrepancies if d.get("severity") == "Disputed"]

    # Separate the tiers so the LLM can use the right language for each.
    # Cancelled / Scheduled / Unassigned = assert as confirmed non-performance.
    # In Progress, no completion date = "not yet billable" only, never "not performed".
    confirmed = [
        d for d in disputed_items
        if any(s in d['rule'].lower() for s in ['cancelled', 'not yet assigned', 'scheduled', 'not found', 'no matching po', 'overbilled', 'rate mismatch'])
        and 'in progress' not in d['rule'].lower()
    ]
    not_yet_billable = [
        d for d in disputed_items
        if 'in progress' in d['rule'].lower()
    ]

    confirmed_text = "\n".join(
        f"  - {d['original_ref']} ({d['work_item']}): {d['rule']} — ${d['dollar_impact']:,.2f}"
        for d in confirmed
    ) or "  (none)"

    not_billable_text = "\n".join(
        f"  - {d['original_ref']} ({d['work_item']}): {d['rule']} — ${d['dollar_impact']:,.2f}"
        for d in not_yet_billable
    ) or "  (none)"

    total_disputed = sum(d['dollar_impact'] for d in disputed_items)
    invoice_total = 172929.50
    approved = invoice_total - total_disputed

    prompt = f"""You are drafting an outbound vendor dispute email on behalf of {metadata['bill_to']}.
The recipient is the team at {metadata['vendor']}.
This is an on-the-record business email. Anything you assert must be defensible.

INVOICE UNDER REVIEW
  Invoice: {metadata['invoice_no']}, Period: {metadata['period']}, PO: {metadata.get('po_ref', 'PO-2026-0117')}
  Invoice total as submitted: ${invoice_total:,.2f}
  Approved for payment now: ${approved:,.2f}
  Not approved: ${total_disputed:,.2f} across {len(disputed_items)} line(s)

FINDINGS FOR YOU TO INCLUDE:

CONFIRMED ISSUES: Assert these directly as fact. The job was cancelled,
never started, or the billed quantity exceeds what the purchase order authorises.
{confirmed_text}

NOT YET BILLABLE: These jobs are recorded as still open with no
completion date. Say the work is not recorded as complete and is therefore not
yet billable. Do NOT say or imply the work was never performed — the crew may
be on site today.
{not_billable_text}

WRITE the plain-text body of a professional, firm business email that:
1. Opens by stating we cannot approve the invoice in full as submitted.
2. States the financial position: ${approved:,.2f} approved for payment now, ${total_disputed:,.2f} not approved.
3. Lists the Confirmed Issues and Not Yet Billable items under clear, professional headings 
   (e.g., "Confirmed Discrepancies" and "Items Pending Completion"). 
   Do NOT literally write "Category 1" or "Category 2".
4. Asks for a corrected invoice and invites them to provide backup documentation within 5 business days.
5. Signs off as:
   [Your Name]
   {metadata['bill_to']}

RULES:
- Plain text only. No markdown, no bullet symbols beyond simple hyphens.
- Do not mention Sitetracker, automation, or AI. Refer only to "our job records and purchase order".
- Do not allege fraud or bad faith. Describe the variance, never a motive.
- Do not invent any figures. Use only the amounts supplied above.
- Output the email body only.
"""

    # Try calling a local Ollama instance.
    try:
        print("Attempting to connect to local Ollama (llama3.2:1b)...")
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3.2:1b", "prompt": prompt, "stream": False},
            timeout=30
        )
        if response.status_code == 200:
            return response.json()["response"].strip()
        else:
            print(f"Ollama returned status {response.status_code}. Falling back to deterministic template.")
    except Exception as e:
        print(f"Could not connect to Ollama ({e}). Falling back to deterministic template.")

    # Deterministic template fallback — always in sync with the live findings.
    lines_confirmed = "\n".join(
        f"  - {d['original_ref']} ({d['work_item']}): {d['rule']} (${d['dollar_impact']:,.2f})"
        for d in confirmed
    )
    lines_not_billable = "\n".join(
        f"  - {d['original_ref']} ({d['work_item']}): work not recorded as complete in our job records, not yet billable (${d['dollar_impact']:,.2f})"
        for d in not_yet_billable
    )

    sections = []
    if confirmed:
        sections.append(
            "Work billed against jobs our records show as cancelled, not started, or in excess of the "
            f"agreed purchase order quantity:\n{lines_confirmed}\n"
            f"Subtotal: ${sum(d['dollar_impact'] for d in confirmed):,.2f}"
        )
    if not_yet_billable:
        sections.append(
            "Work billed against jobs that remain open with no completion recorded, and "
            f"which is not yet billable under {metadata.get('po_ref', 'PO-2026-0117')}:\n{lines_not_billable}\n"
            f"Subtotal: ${sum(d['dollar_impact'] for d in not_yet_billable):,.2f}"
        )

    body = "\n\n".join(sections)

    return f"""Dear {metadata['vendor']} Team,

We have reviewed invoice {metadata['invoice_no']} for {metadata['period']} against our job records \
and purchase order {metadata.get('po_ref', 'PO-2026-0117')}, and we are not able to approve it in \
full as submitted.

${approved:,.2f} of the ${invoice_total:,.2f} invoiced is approved and is moving for payment now. \
${total_disputed:,.2f} across {len(disputed_items)} line(s) is not approved, pending the items set out below.

{body}

Please issue a corrected invoice covering the lines listed above. If you believe any line is correct \
as billed, reply to this address with the supporting documentation and we will review it within five \
business days.

Regards,
[Your Name]
{metadata['bill_to']}"""
