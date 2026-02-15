import json
import threading
import os
import base64
import traceback
from concurrent.futures import Future
from http.server import BaseHTTPRequestHandler, HTTPServer
from aqt import mw
from aqt.utils import showInfo, tooltip
from anki.notes import Note
from anki.hooks import addHook

# Configuration
config = mw.addonManager.getConfig(__name__) or {}
PORT = config.get('port', 5005)
DEFAULT_MODEL = config.get('default_model', "AI Generated Model")

# Global server reference for shutdown
httpd = None

class AnkiBridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence logging to avoid Anki stderr capture
        return

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        if self.path == '/get_decks':
            try:
                # Run on main thread to safely access Anki collection
                future = Future()
                def get_decks_task():
                    try:
                        future.set_result(mw.col.decks.allNames())
                    except Exception as e:
                        future.set_exception(e)
                mw.taskman.run_on_main(get_decks_task)
                decks = future.result()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"decks": decks}).encode('utf-8'))
            except Exception as e:
                traceback.print_exc()
                self.send_error(500, str(e))

    def do_POST(self):
        if self.path == '/add_cards':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data)
                deck_name = data.get("deck_name")
                cards = data.get("cards", [])
                model_name = data.get("model_name", DEFAULT_MODEL)
                media_files = data.get("media", []) # Expects list of {filename, data_base64}
                
                # Operations on Anki collection must run on the main thread
                future = Future()
                def add_cards_task():
                    try:
                        future.set_result(self.add_cards_to_anki(deck_name, cards, model_name, media_files))
                    except Exception as e:
                        future.set_exception(e)
                mw.taskman.run_on_main(add_cards_task)
                count = future.result() # Wait for the operation to complete
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "count": count}).encode('utf-8'))
            except Exception as e:
                traceback.print_exc()
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e), "traceback": traceback.format_exc()}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def add_cards_to_anki(self, deck_name, cards, model_name, media_files):
        col = mw.col
        if col is None:
            raise Exception("Anki collection is not loaded. Please open a profile in Anki.")
            
        if not deck_name:
            raise Exception("Deck name is missing.")
        deck_name = deck_name.strip()
        
        # 0. Process Media (Future proofing for images/audio)
        if media_files:
            media_dir = col.media.dir()
            for mfile in media_files:
                fname = mfile.get("filename")
                b64_data = mfile.get("data")
                if fname and b64_data:
                    # Security Fix: Prevent Path Traversal
                    safe_fname = os.path.basename(fname)
                    path = os.path.join(media_dir, safe_fname)

                    # Double check it is inside media_dir
                    if not os.path.abspath(path).startswith(os.path.abspath(media_dir)):
                        print(f"Security Warning: Attempted path traversal to {path}")
                        continue

                    with open(path, "wb") as f:
                        f.write(base64.b64decode(b64_data))

        # 1. Get/Create Deck
        deck_id = col.decks.id(deck_name)
        
        # 2. Get/Create Model
        model = col.models.by_name(model_name)
        if not model:
            model = col.models.new(model_name)
            
            # Fix for "1 field required" and KeyError issues
            # 1. Ensure basic structure exists and is Standard type (0)
            model['type'] = 0 
            model['flds'] = []
            model['tmpls'] = []
            
            # 2. Create fields using helper
            f1 = col.models.new_field("Question")
            f2 = col.models.new_field("Answer")
            model['flds'].append(f1)
            model['flds'].append(f2)
            
            # 3. Create template using helper
            t = col.models.new_template("Card 1")
            t['qfmt'] = '{{Question}}'
            t['afmt'] = '{{FrontSide}}<hr id="answer">{{Answer}}'
            model['tmpls'].append(t)
            
            # 4. CRITICAL: Clear 'req' (required fields) to force Anki to regenerate it
            # This fixes the "1 field required" validation error caused by stale cache
            if 'req' in model:
                del model['req']
            
            col.models.add(model)
        
        # 3. Add Notes
        count = 0
        for card in cards:
            note = Note(col, model)
            
            # Smart field mapping: Use 'Question'/'Answer' if they exist, otherwise use 1st/2nd fields
            field_names = [f['name'] for f in model['flds']]
            q_field = 'Question' if 'Question' in field_names else field_names[0]
            a_field = 'Answer' if 'Answer' in field_names else (field_names[1] if len(field_names) > 1 else None)
            
            note[q_field] = card['question']
            if a_field:
                note[a_field] = card['answer']
            
            # Support for tags (future-proofing)
            if 'tags' in card and isinstance(card['tags'], list):
                note.tags = card['tags']
                
            note.deck_id = deck_id
            
            # Compatibility for different Anki versions
            if hasattr(col, 'add_note'):
                col.add_note(note, deck_id)
            else:
                col.addNote(note) # Legacy support
            count += 1
            
        col.save()
        tooltip(f"Added {count} cards to '{deck_name}'")
        mw.reset()
        return count

def run_server():
    global httpd
    server_address = ('localhost', PORT)
    try:
        httpd = HTTPServer(server_address, AnkiBridgeHandler)
        print(f"Anki Bridge running on port {PORT}...")
        httpd.serve_forever()
    except OSError:
        msg = f"NeuralDeck Error: Port {PORT} is already in use."
        print(msg)
        mw.taskman.run_on_main(lambda: tooltip(msg))

def stop_server():
    global httpd
    if httpd:
        httpd.shutdown()
        httpd.server_close()

# Start server in a background thread to not block Anki UI
server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

# Ensure clean shutdown when Anki closes
addHook("unloadProfile", stop_server)
