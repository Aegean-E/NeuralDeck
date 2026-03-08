import requests
import sys
import json

def test_connection():
    # The README states the bridge restricts to 127.0.0.1
    url = "http://127.0.0.1:5005/get_decks"
    print(f"Attempting to connect to {url}...")
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print("✅ SUCCESS: Connected to Anki add-on!")
            print("Decks found:", response.text[:100], "...")
            
            # Test POST (Add Cards)
            print("\nTesting POST request (Add Cards)...")
            post_url = "http://127.0.0.1:5005/add_cards"
            payload = {
                "deck_name": "Default",
                "cards": [], # Empty list just to check connectivity
                "model_name": "AI Generated Model"
            }
            post_response = requests.post(post_url, json=payload, timeout=5)
            if post_response.status_code == 200:
                print("✅ SUCCESS: POST request accepted!")
            else:
                print(f"⚠️ FAILURE: POST returned {post_response.status_code}")
                print(post_response.text)
        else:
            print(f"⚠️ FAILURE: Connected but got status {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ ERROR: Could not connect. {e}")
        print("\nTroubleshooting Steps:")
        print("1. Open Anki -> Tools -> Add-ons. Ensure 'NeuralDeckBridge' is enabled.")
        print("2. If the folder name in addons21 is not 'NeuralDeckBridge', rename it and restart Anki.")
        print("3. Check if port 5005 is used by another app (run 'netstat -an | grep 5005').")

if __name__ == "__main__":
    test_connection()