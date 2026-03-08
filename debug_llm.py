import requests
import json

def test_llm_generation():
    # Standard LM Studio endpoint
    url = "http://localhost:1234/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    
    print(f"Connecting to LLM at {url}...")
    
    # A prompt designed to mimic the app's request
    payload = {
        "model": "local-model",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant. Output a JSON list of 2 QA pairs."},
            {"role": "user", "content": "Generate 2 flashcards about the human brain."}
        ],
        "temperature": 0.7,
        "max_tokens": 500,
        "stream": False
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            content = data['choices'][0]['message']['content']
            
            print("\n--- RAW AI OUTPUT START ---")
            print(content)
            print("--- RAW AI OUTPUT END ---\n")
            
            # Diagnosis
            if "```json" in content:
                print("⚠️ DIAGNOSIS: The AI is using Markdown code blocks. The parser needs to strip '```json'.")
            elif content.strip().startswith("[") is False:
                print("⚠️ DIAGNOSIS: The AI output contains conversational text before the JSON.")
            else:
                print("✅ Output looks like clean JSON. The issue might be internal logic.")
        else:
            print(f"❌ Error from LLM: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    test_llm_generation()