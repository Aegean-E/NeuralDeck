import json
import urllib.request
import urllib.error

def check_anki_connection(port=5005):
    """Simple check to see if the Anki add-on server is running."""
    url = f"http://localhost:{port}/"
    try:
        # Try a quick connection. Even a 404 means the server is up.
        with urllib.request.urlopen(url, timeout=1):
            return True
    except urllib.error.HTTPError:
        # Server responded with an error (e.g. 404), so it is running.
        return True
    except Exception:
        return False

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
        try:
            error_body = e.read().decode('utf-8')
        except Exception:
            error_body = ""

        try:
            error_json = json.loads(error_body)
            # Some APIs return 'error' key instead of 'message'
            error_msg = error_json.get("message") or error_json.get("error") or error_body
            if "traceback" in error_json:
                error_msg += f"\nTraceback:\n{error_json['traceback']}"
        except Exception:
            error_msg = error_body or str(e)
            
        full_msg = f"Anki Server Error ({e.code}): {error_msg}"
        if log_callback:
            log_callback(full_msg)
        raise Exception(full_msg)
    except urllib.error.URLError as e:
        if log_callback:
            log_callback(f"Connection Error: {e}")
        raise ConnectionError("Could not connect to Anki. Please ensure Anki is open and the 'NeuralDeck Bridge' add-on is installed.")
