from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_chat_endpoint():
    print("--- Simulating Twilio WhatsApp Message ---")
    
    # Twilio sends data as Form URL-Encoded
    payload = {
        "From": "whatsapp:+1234567890",
        "Body": "I have a headache and feel dizzy", # Simulating general chat / symptom analysis
    }
    
    response = client.post("/api/v1/chat", data=payload)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response XML (TwiML):\n{response.text.encode('utf-8', errors='replace').decode('utf-8')}")

if __name__ == "__main__":
    test_chat_endpoint()
