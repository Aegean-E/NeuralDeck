import json
import urllib.request
import urllib.error

def get_deck_names(log_callback=None):
    """Fetches the list of deck names from the Anki add-on."""
    url = "http://localhost:5005/get_decks"
    if log_callback:
        log_callback(f"Connecting to Anki at {url}...")
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            result = json.loads(response.read().decode('utf-8'))
            decks = result.get("decks", [])
            if log_callback:
                log_callback(f"Connected. Found {len(decks)} decks.")
            return decks
    except Exception as e:
        if log_callback:
            log_callback(f"Failed to connect to Anki: {e}")
        return []

def create_anki_deck(deck_name, qa_pairs, log_callback=None):
    """
    Sends Q&A pairs to the custom Anki Add-on running on localhost:5005.
    """
    url = "http://localhost:5005/add_cards"
    
    # Format data for the add-on
    cards = [{"question": q, "answer": a} for q, a in qa_pairs]
    payload = {
        "deck_name": deck_name,
        "cards": cards
    }
    
    if log_callback:
        log_callback(f"Sending {len(cards)} cards to deck '{deck_name}'...")

    req = urllib.request.Request(
        url, 
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            count = result.get("count", 0)
            if log_callback:
                log_callback(f"Success! Added {count} cards to '{deck_name}'.")
            return count
    except urllib.error.HTTPError as e:
        # Read the error message from the server
        error_body = e.read().decode('utf-8')
        try:
            error_json = json.loads(error_body)
            error_msg = error_json.get("message", error_body)
            if "traceback" in error_json:
                error_msg += f"\nTraceback:\n{error_json['traceback']}"
        except:
            error_msg = error_body
            
        if log_callback:
            log_callback(f"Anki Server Error (500): {error_msg}")
        raise Exception(f"Anki Server Error: {error_msg}")
    except urllib.error.URLError as e:
        if log_callback:
            log_callback(f"Connection Error: {e}")
        raise ConnectionError("Could not connect to Anki. Please ensure Anki is open and the 'AI Anki Cards Bridge' add-on is installed.")
