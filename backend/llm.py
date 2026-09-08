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
        
    disputed_items = [d for d in discrepancies if d.get("severity") == "Disputed"]
    
    # Format discrepancies for the prompt
    disc_text = "\n".join([f"- {d['original_ref']} ({d['work_item']}): {d['rule']}" for d in disputed_items])
    
    prompt = f"""
You are an AI assistant acting on behalf of {metadata['bill_to']}.
We received an invoice from our subcontractor, {metadata['vendor']}, but our reconciliation system found several discrepancies against our Sitetracker data.

Discrepancies found:
{disc_text}

Draft a professional but firm email to their billing contact. The output MUST follow exactly this format:

Dear {metadata['vendor']} Team,

We have completed our reconciliation of the {metadata['period']} invoice ({metadata['invoice_no']}) against the corresponding Sitetracker job and purchase order records.

We identified several invoice lines that require clarification or correction before the invoice can be approved:

[List the specific invoice lines for jobs marked In Progress/Scheduled with no completed work]
[List the specific invoice lines for jobs not completed or cancelled]
[List the specific invoice lines where quantities exceed PO limits]

Please review these lines and provide a revised invoice that reflects the current job status and corrects the identified quantity discrepancies.

If any of the flagged items have been completed or otherwise require clarification, please provide the relevant supporting information along with your response.

We look forward to receiving your clarification and revised invoice.

Sincerely,
[Your Name]
{metadata['bill_to']}

Output ONLY the body of the email following the exact structure above. Do not include subject lines or routing info in the body.
"""
    
    # Try calling a local Ollama instance (defaulting to llama3, change model as needed)
    try:
        print("Attempting to connect to local Ollama (llama3)...")
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False
            },
            timeout=30 # wait up to 30 seconds for local generation
        )
        if response.status_code == 200:
            return response.json()["response"].strip()
        else:
            print(f"Ollama returned status {response.status_code}. Falling back to deterministic template.")
    except Exception as e:
        print(f"Could not connect to Ollama ({e}).")
        print("Falling back to deterministic template from findings object (perfect for live demos).")
            
    # Deterministic template fallback — clean plain text, no markdown
    formatted_list = "\n".join([
        f"  • {d['original_ref']} ({d['work_item']}): {d['rule']}"
        for d in disputed_items
    ])
    
    stubbed_response = f"""Dear {metadata['vendor']} Team,

We have completed our reconciliation of the {metadata['period']} invoice ({metadata['invoice_no']}) against the corresponding Sitetracker job and purchase order records.

We identified several invoice lines that require clarification or correction before the invoice can be approved:

{formatted_list}

Please review these lines and provide a revised invoice that reflects the current job status and corrects the identified quantity discrepancies.

If any of the flagged items have been completed or otherwise require clarification, please provide the relevant supporting information along with your response.

We look forward to receiving your clarification and revised invoice.

Sincerely,
[Your Name]
{metadata['bill_to']}"""
    return stubbed_response
