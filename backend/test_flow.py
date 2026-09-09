import uvicorn
from server import app
import threading
import time
import requests
import json
import hashlib

def test_flow():
    base_url = "http://localhost:8001"
    time.sleep(2)  # Wait for server to start
    
    print("Calling /api/analyze...")
    resp = requests.post(f"{base_url}/api/analyze")
    if not resp.ok:
        print("Failed analyze:", resp.text)
        return
        
    data = resp.json()
    email_draft = data["email_draft"]
    approval_token = data["approval_token"]
    email_subject = data["email_subject"]
    
    print(f"Original digest input length: {len(email_draft)}")
    
    payload = {
        "email_body": email_draft,
        "invoice_no": "CLC-26-0342",
        "csv_data": "dummy",
        "approval_token": approval_token,
        "email_subject": email_subject
    }
    
    print("Calling /api/send_email with exact draft...")
    resp2 = requests.post(f"{base_url}/api/send_email", json=payload)
    print("Status:", resp2.status_code)
    if not resp2.ok:
        print("Response:", resp2.text)

if __name__ == "__main__":
    t = threading.Thread(target=uvicorn.run, args=(app,), kwargs={"host": "127.0.0.1", "port": 8001})
    t.daemon = True
    t.start()
    test_flow()
