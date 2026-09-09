import requests

def test_api():
    base_url = "http://localhost:8001"
    
    # Analyze
    print("Calling /api/analyze...")
    resp = requests.post(f"{base_url}/api/analyze")
    if not resp.ok:
        print("Failed analyze:", resp.text)
        return
        
    data = resp.json()
    email_draft = data["email_draft"]
    approval_token = data["approval_token"]
    email_subject = data["email_subject"]
    invoice_no = "CLC-26-0342" # hardcoded from metadata
    
    print(f"Token: {approval_token}")
    
    # Send Email
    payload = {
        "email_body": email_draft,
        "invoice_no": invoice_no,
        "csv_data": "dummy,csv\n1,2",
        "approval_token": approval_token,
        "email_subject": email_subject
    }
    
    print("Calling /api/send_email...")
    resp2 = requests.post(f"{base_url}/api/send_email", json=payload)
    print("Status:", resp2.status_code)
    print("Response:", resp2.text)

if __name__ == "__main__":
    test_api()
