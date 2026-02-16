import json
import random
import time
import os
import re
import urllib.request
import urllib.error
import urllib.parse
import http.client
import socket
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pipeline_utils import PipelineStats, FailureLogger, CardValidator, ResourceGuard

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

def extract_text_from_pdf(file_path, log_callback=None):
    """
    Extracts text from a PDF file.
    """
    if PyPDF2 is None:
        raise ImportError("PyPDF2 module not found. Please install it using 'pip install PyPDF2'.")
        
    text_parts = []
    empty_pages = []
    total_pages = 0

    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            # Attempt to handle encrypted files with empty password
            if reader.is_encrypted:
                try:
                    reader.decrypt("")
                except Exception:
                    pass
            
            # If no pages, raise error
            if not reader.pages:
                raise Exception("PDF appears to be empty or corrupted (0 pages found).")

            total_pages = len(reader.pages)
            for i, page in enumerate(reader.pages):
                try:
                    extracted = page.extract_text()
                    if extracted and extracted.strip():
                        # Append parts to list for O(N) performance instead of O(N^2) string concatenation
                        text_parts.append(extracted)
                        text_parts.append("\n")
                    else:
                        empty_pages.append(i + 1)
                        # Add placeholder for layout preservation context
                        text_parts.append(f"\n[PAGE {i+1}: NO TEXT DETECTED - SCANNED?]\n")
                        msg = f"Warning: Page {i+1} yielded no text (likely scanned or image)."
                        if log_callback: log_callback(msg)
                        else: print(msg)

                except Exception as page_error:
                    # Log warning for specific page failure but continue
                    msg = f"Warning: Failed to extract text from page {i+1}: {page_error}"
                    if log_callback: log_callback(msg)
                    else: print(msg)

                    empty_pages.append(i + 1)
                    text_parts.append(f"\n[PAGE {i+1}: EXTRACTION FAILED]\n")
                    continue

    except FileNotFoundError:
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    except Exception as e:
        raise Exception(f"Failed to read PDF: {e}")

    full_text = "".join(text_parts)

    # If all pages were empty (and we only have placeholders)
    if len(empty_pages) == total_pages:
        raise Exception("No text could be extracted from this PDF. It appears to be entirely scanned images or encrypted. Please use an external OCR tool first.")

    return full_text

def check_llm_server(api_url, api_key="lm-studio"):
    """
    Checks if the LLM server is reachable.
    """
    parsed = urllib.parse.urlparse(api_url)

    # 1. Try hitting the models endpoint (standard OpenAI API)
    try:
        base_url = f"{parsed.scheme}://{parsed.netloc}/v1/models"
        req = urllib.request.Request(base_url, headers={"Authorization": f"Bearer {api_key}"})
        with urllib.request.urlopen(req, timeout=3) as response:
            if response.status == 200:
                return True
    except Exception:
        pass

    # 2. Fallback: Check TCP connection to host:port
    try:
        port = parsed.port if parsed.port else (443 if parsed.scheme == 'https' else 80)
        with socket.create_connection((parsed.hostname, port), timeout=3):
            return True
    except Exception:
        pass

    raise ConnectionError(f"Could not connect to LLM server at {api_url}. Is it running?")

def call_lm_studio(prompt, system_instruction, api_url="http://localhost:1234/v1/chat/completions", api_key="lm-studio", model="local-model", temperature=0.7, max_tokens=-1, stop_callback=None, timeout=120):
    """
    Calls the local LM Studio server (OpenAI compatible API).
    Includes retries with exponential backoff for network issues.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "stream": True
    }
    
    if max_tokens > 0:
        payload["max_tokens"] = int(max_tokens)
    
    req = urllib.request.Request(api_url, data=json.dumps(payload).encode('utf-8'), headers=headers)
    
    retries = 3
    last_exception = None

    for attempt in range(retries):
        full_response = ""
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status != 200:
                    raise Exception(f"HTTP Error {response.status}: {response.reason}")
                
                for line in response:
                    if stop_callback and stop_callback():
                        raise Exception("Processing stopped by user.")

                    try:
                        line = line.decode('utf-8').strip()
                    except Exception:
                        continue # Skip bad lines

                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data_json = json.loads(data_str)
                            if 'choices' in data_json and len(data_json['choices']) > 0:
                                delta = data_json['choices'][0].get('delta', {})
                                content = delta.get('content', '')
                                if content:
                                    full_response += content
                        except json.JSONDecodeError:
                            # Log or ignore bad JSON chunks
                            continue
                        except Exception:
                            # Ignore other minor parsing errors
                            pass

            return full_response

        except (urllib.error.URLError, socket.timeout, http.client.IncompleteRead, ConnectionError) as e:
            # Handle specific connection errors
            if isinstance(e, urllib.error.URLError):
                 err_msg = f"Connection Failed to {api_url}. Details: {e.reason}"
            else:
                 err_msg = f"Network error during AI call: {e}"

            last_exception = Exception(err_msg)

            # Exponential backoff: 1s, 2s, 4s...
            wait_time = 2 ** attempt
            if attempt < retries - 1:
                time.sleep(wait_time)
                continue
        except Exception as e:
            # Don't retry other exceptions (like "Processing stopped by user")
            raise e

    if last_exception:
        raise last_exception
    raise Exception("Unknown error occurred during API call (Retries exhausted).")

def smart_chunk_text(text, max_chars, min_chars=100):
    """
    Splits text into chunks respecting paragraph boundaries.
    If a single paragraph exceeds max_chars, it splits by sentences.
    If a single sentence exceeds max_chars, it hard splits.
    Also attempts to merge very small chunks with neighbors.
    """
    chunks = []
    current_chunk = []
    current_length = 0
    
    paragraphs = text.splitlines(keepends=True)
    
    for para in paragraphs:
        para_len = len(para)

        # If paragraph fits, add it
        if current_length + para_len <= max_chars:
            current_chunk.append(para)
            current_length += para_len
            continue

        # If paragraph is too big for current chunk, flush current chunk
        if current_chunk:
            chunks.append("".join(current_chunk))
            current_chunk = []
            current_length = 0

        # If paragraph fits in a new chunk by itself
        if para_len <= max_chars:
            current_chunk.append(para)
            current_length += para_len
            continue

        # Paragraph is bigger than max_chars -> Split by sentences
        sentences = re.split(r'(?<=[.!?])\s+', para)
        for i, sent in enumerate(sentences):
            if i < len(sentences) - 1:
                sent += " " # Restore spacing
            if not sent: continue

            sent_len = len(sent)

            if current_length + sent_len > max_chars:
                if current_chunk:
                    chunks.append("".join(current_chunk))
                    current_chunk = []
                    current_length = 0

                # Hard split if sentence is still too long
                if sent_len > max_chars:
                    while sent:
                        part = sent[:max_chars]
                        chunks.append(part)
                        sent = sent[max_chars:]
                    continue

            current_chunk.append(sent)
            current_length += sent_len

    if current_chunk:
        chunks.append("".join(current_chunk))

    # Merge small chunks
    if not chunks:
        return []

    merged_chunks = []
    current_merge = chunks[0]

    for i in range(1, len(chunks)):
        next_chunk = chunks[i]
        if len(current_merge) < min_chars and (len(current_merge) + len(next_chunk) <= max_chars):
            current_merge += next_chunk
        else:
            merged_chunks.append(current_merge)
            current_merge = next_chunk
    merged_chunks.append(current_merge)

    return merged_chunks

def robust_parse_objects(text):
    """
    Scans the text for JSON objects and extracts them individually.
    This is resilient to malformed arrays, missing commas, or truncated tails.
    Also extracts nested cards from wrapper objects.

    Args:
        text (str): The text containing JSON objects (possibly with Markdown or other noise).

    Returns:
        list: A list of extracted dictionary objects representing cards.
    """
    # 1. Strip Markdown Code Blocks (common LLM artifact)
    # Only remove if they appear at the very start/end or on their own lines to avoid destroying content
    text = text.strip()
    if text.startswith("```"):
        # Remove first line if it starts with ```
        text = re.sub(r'^```[a-zA-Z]*\s*\n?', '', text, count=1)
        # Remove last line if it is ```
        text = re.sub(r'\n?```\s*$', '', text, count=1)

    decoder = json.JSONDecoder()
    pos = 0
    results = []
    
    def extract_cards(obj):
        """Iteratively extract cards from nested JSON structure."""
        extracted = []
        stack = [obj]
        while stack:
            curr = stack.pop()
            if isinstance(curr, dict):
                # Check if this dict acts as a card
                # Case insensitive check for keys
                keys_lower = {k.lower(): k for k in curr.keys()}
                if 'question' in keys_lower and 'answer' in keys_lower:
                    extracted.append(curr)
                else:
                    # Push values to stack in reverse order to preserve processing order
                    stack.extend(reversed(list(curr.values())))
            elif isinstance(curr, list):
                stack.extend(reversed(curr))
        return extracted

    while pos < len(text):
        # Find the start of the next object
        start_idx = text.find('{', pos)
        if start_idx == -1:
            break
            
        try:
            # Try to decode a single JSON object starting at start_idx
            obj, end_idx = decoder.raw_decode(text, idx=start_idx)

            # Recursively extract cards from the decoded object
            found_cards = extract_cards(obj)
            results.extend(found_cards)

            pos = end_idx
        except json.JSONDecodeError:
            # Optimization: If decoding fails, skip to next '{' instead of iterating char by char
            pos = text.find('{', start_idx + 1)
            if pos == -1:
                break
            
    return results

def refine_generated_cards(cards, deck_names, target_language, api_url, api_key, model, temperature, log_callback=None, stop_callback=None):
    """
    Sends the generated cards back to the AI for a second pass to fix errors, 
    improve phrasing, and ensure deck compliance.
    """
    if not cards:
        return []
        
    cards_json = json.dumps(cards, ensure_ascii=False, indent=2)
    
    system_prompt = (
        f"You are a strict editor for Anki flashcards. Your task is to REVIEW and FIX the provided JSON list of cards.\n"
        f"Language: {target_language}\n"
        f"Allowed Decks: {json.dumps(deck_names)}\n\n"
        f"INSTRUCTIONS:\n"
        f"1. REMOVE cards that are simple 'Yes/No' questions.\n"
        f"2. REMOVE cards that are biographical trivia (who discovered it, birth dates) unless clinically vital.\n"
        f"3. REWRITE questions to be self-contained. (e.g. 'What are the symptoms?' -> 'What are the symptoms of [Disease]?')\n"
        f"4. CORRECT terminology errors (e.g. 'senses' vs 'functions').\n"
        f"5. ENSURE 'deck' is selected from the Allowed Decks list based on the card content.\n"
        f"6. MERGE duplicate or very similar cards.\n"
        f"7. PRESERVE the 'quote' field from the original card. Do not remove it.\n"
        f"8. Output the final list as a raw JSON array."
    )
    
    user_prompt = f"Refine these cards:\n{cards_json}"
    
    try:
        if log_callback:
            log_callback(f"    [Refinement] Sending {len(cards)} cards to AI for review...")
            for card in cards:
                q = card.get('question', 'N/A')
                a = card.get('answer', 'N/A')
                log_callback(f"      [PRE-EDIT] Q: {q} | A: {a}")
            
        response_text = call_lm_studio(user_prompt, system_prompt, api_url=api_url, api_key=api_key, model=model, temperature=temperature, max_tokens=4000, stop_callback=stop_callback)
        
        # Use robust parsing for refinement response as well
        refined_data = robust_parse_objects(response_text)
        
        if log_callback:
            if not refined_data:
                log_callback(f"    [Refinement] Warning: AI returned 0 valid cards. Using originals.")
            else:
                log_callback(f"    [Refinement] AI returned {len(refined_data)} cards.")
            
        # Attempt to restore quotes if lost during refinement
        # Heuristic: Match by question text to preserve metadata even if counts differ
        # We map both Questions and Answers to quotes to handle cases where AI rewrites the question significantly
        q_map = {c['question'].strip().lower(): c.get('quote', '') for c in cards}
        a_map = {c['answer'].strip().lower(): c.get('quote', '') for c in cards}
        
        for r_card in refined_data:
            if not r_card.get('quote'):
                r_q = r_card.get('question', '').strip().lower()
                r_a = r_card.get('answer', '').strip().lower()
                
                # 1. Exact match
                if r_q in q_map:
                    r_card['quote'] = q_map[r_q]
                elif r_a in a_map:
                    r_card['quote'] = a_map[r_a]
                # 2. Fuzzy match (Question)
                else:
                    found = False
                    for orig_q, orig_quote in q_map.items():
                        # If one is a substring of the other (high overlap)
                        if len(orig_q) > 10 and (orig_q in r_q or r_q in orig_q):
                            r_card['quote'] = orig_quote
                            found = True
                            break
                    # 3. Fuzzy match (Answer) - Fallback if question changed too much
                    if not found:
                        for orig_a, orig_quote in a_map.items():
                            if len(orig_a) > 10 and (orig_a in r_a or r_a in orig_a):
                                r_card['quote'] = orig_quote
                                break
        
        if not refined_data:
            return cards

        return refined_data
    except Exception as e:
        if log_callback:
            log_callback(f"Refinement failed: {e}. Using original cards.")
        return cards

def filter_and_process_cards(raw_data_list, deck_names, smart_deck_match, filter_yes_no):
    """Helper to clean, filter, and assign decks to a list of raw card objects."""

    # Helper to score a deck against text based on keywords
    def score_deck_parts(parts_data, q_txt, a_txt):
        score = 0
        for part_info in parts_data:
            part = part_info['text']
            # 1. Full phrase match (Highest priority in Question)
            if part in q_txt:
                score += len(part) * 3
            elif part in a_txt:
                score += len(part) * 1  # Lower weight for answer
            else:
                # 2. Word match (lower weight)
                for w in part_info['words']:
                    if w in q_txt: score += len(w) * 1.5
                    elif w in a_txt: score += len(w) * 0.5
        return score

    # Legacy wrapper for on-the-fly scoring
    def score_deck_raw(d_name, q_txt, a_txt):
        parts = [p.strip().lower() for p in d_name.split(',')]
        parts_data = []
        for part in parts:
            if not part: continue
            words = [w for w in part.split() if len(w) > 3]
            parts_data.append({'text': part, 'words': words})
        return score_deck_parts(parts_data, q_txt, a_txt)

    # Pre-process deck names if smart matching is enabled
    # Optimization: Pre-compute string splits (O(N) setup) to avoid repeated O(N*M) string operations inside the loop.
    processed_decks = []
    if smart_deck_match and deck_names:
        for d_name in deck_names:
            parts = [p.strip().lower() for p in d_name.split(',')]
            parts_data = []
            for part in parts:
                if not part: continue
                words = [w for w in part.split() if len(w) > 3]
                parts_data.append({'text': part, 'words': words})
            processed_decks.append({'name': d_name, 'parts': parts_data})

    processed_entries = [] # Stores {'card': card_dict, 'score': match_score}
    for item in raw_data_list:
        if not isinstance(item, dict):
            continue

        # Robustly handle question/answer fields with capitalization fallback
        q_val = item.get('question') or item.get('Question')
        a_val = item.get('answer') or item.get('Answer')

        if not q_val or not a_val:
            continue

        q_text = " ".join(str(x) for x in q_val).strip() if isinstance(q_val, list) else str(q_val).strip()
        a_text = " ".join(str(x) for x in a_val).strip() if isinstance(a_val, list) else str(a_val).strip()

        # Ensure content is not just whitespace
        if not q_text or not a_text:
            continue

        # Filter: Strictly remove Yes/No answers
        if filter_yes_no:
            a_lower = a_text.lower().strip()
            if a_lower in ['evet', 'evet.', 'hayır', 'hayır.', 'yes', 'yes.', 'no', 'no.']:
                continue
            if a_lower.startswith(('evet,', 'hayır,', 'yes,', 'no,')):
                continue

        deck = item.get('deck', 'Default')
        quote = item.get('quote', '')

        current_score = 0

        # Enforce deck constraints if provided
        if deck_names and deck not in deck_names:
            # 1. Case insensitive match
            match = next((d for d in deck_names if d.lower() == deck.lower()), None)
            if match: deck = match
            else:
                # 2. Substring match
                match = next((d for d in deck_names if d in deck), None)
                if match: deck = match
                else:
                    # 3. Fallback
                    deck = "Default" if "Default" in deck_names else (deck_names[0] if deck_names else "Default")

        # 4. Smart Content-Based Correction
        if smart_deck_match and deck_names:
            q_lower = q_text.lower()
            a_lower = a_text.lower()

            # Calculate score for the currently assigned deck (on-the-fly)
            current_score = score_deck_raw(deck, q_lower, a_lower)

            # Find best match from processed decks (optimized loop)
            best_match_deck = None
            best_match_score = -1

            for d_data in processed_decks:
                s = score_deck_parts(d_data['parts'], q_lower, a_lower)
                if s > best_match_score:
                    best_match_score = s
                    best_match_deck = d_data['name']

            # Only switch if the new match is significantly better (score > 0 and better than current)
            if best_match_deck and best_match_score > 0 and best_match_score > current_score:
                deck = best_match_deck
                current_score = best_match_score

        processed_entries.append({'card': {'question': q_text, 'answer': a_text, 'deck': deck, 'quote': quote}, 'score': current_score})

    # 5. Contextual Deck Correction (Majority Vote)
    # If a card has a weak match (score 0), reassign it to the dominant deck of the chunk.
    if smart_deck_match and processed_entries:
        # Find dominant deck from high-confidence cards (score > 0)
        high_conf_decks = [e['card']['deck'] for e in processed_entries if e['score'] > 0]

        dominant_deck = None
        if high_conf_decks:
            dominant_deck = Counter(high_conf_decks).most_common(1)[0][0]
        elif processed_entries:
            # Fallback: Simple majority of all cards if no keywords matched anywhere
            all_decks = [e['card']['deck'] for e in processed_entries]
            dominant_deck = Counter(all_decks).most_common(1)[0][0]

        if dominant_deck:
            for entry in processed_entries:
                if entry['score'] == 0:
                    entry['card']['deck'] = dominant_deck

    return [e['card'] for e in processed_entries]

def _process_chunk_task(i, chunk, total_chunks, stop_callback, log_callback, max_tokens, system_prompt, context_window, api_url, api_key, model, temperature, ai_refinement, deck_names, target_language, filter_yes_no, smart_deck_match, pipeline_stats=None, failure_logger=None):
    """Helper function to process a single chunk in a thread."""
    if stop_callback and stop_callback():
        return []

    if log_callback:
        log_callback(f"Processing part {i+1}/{total_chunks}... (Sending to AI)")

    chunk_start = time.time()
    user_prompt = f"Generate flashcards from the following text:\n\n{chunk}"

    # Dynamic Max Tokens Logic to prevent infinite loops/context shifts
    request_max_tokens = max_tokens
    if request_max_tokens <= 0:
        # Estimate prompt tokens (conservative)
        est_prompt_tokens = (len(user_prompt) + len(system_prompt)) / 2.5
        # Cap at 4000 to allow for high-density generation on larger contexts.
        request_max_tokens = 4000

        # Ensure we don't exceed context window
        if est_prompt_tokens + request_max_tokens > context_window:
            request_max_tokens = int(context_window - est_prompt_tokens - 100)

        if request_max_tokens < 500: request_max_tokens = 500

    chunk_cards = []
    error_occurred = None
    try:
        response_text = call_lm_studio(user_prompt, system_prompt, api_url=api_url, api_key=api_key, model=model, temperature=temperature, max_tokens=request_max_tokens, stop_callback=stop_callback)
        if log_callback:
            log_callback(f"  > AI Response received for part {i+1} ({len(response_text)} chars).")

        # Use robust parsing instead of fragile JSON array parsing
        data = robust_parse_objects(response_text)

        if not data and log_callback:
            log_callback(f"Warning: No valid cards found in part {i+1}. Response might be malformed or empty.")

        # First Pass: Filter and Clean
        temp_cards = filter_and_process_cards(data, deck_names, smart_deck_match, filter_yes_no)

        # Second Pass: AI Refinement (Optional)
        if ai_refinement and temp_cards:
            if log_callback:
                log_callback(f"  > Refining {len(temp_cards)} cards with AI (Check -> Edit)...")

            # Note: We don't pass log_callback to refinement inside thread to avoid UI race conditions, or we rely on thread-safe logging
            refined_raw = refine_generated_cards(temp_cards, deck_names, target_language, api_url, api_key, model, temperature, log_callback, stop_callback)
            # IMPORTANT: Re-run filter on refined cards to catch any "Yes/No" answers the AI might have re-introduced
            chunk_cards = filter_and_process_cards(refined_raw, deck_names, smart_deck_match, filter_yes_no)
        else:
            chunk_cards = temp_cards

    except Exception as e:
        error_occurred = e
        if log_callback:
            log_callback(f"Error processing part {i+1}: {e}")
        # Log failure if pipeline_stats is available, but better to log in FailureLogger which is usually global or passed.
        # But we don't have global access. We'll rely on the caller or a new FailureLogger here.
        # Ideally, main thread handles logging.
        # Just return empty.

    duration = time.time() - chunk_start
    if pipeline_stats:
        pipeline_stats.add_llm_time(duration)
        if error_occurred:
            pipeline_stats.increment_failed_chunk()
            # We can also log to file if we instantiate FailureLogger here or pass it.
            # Since we didn't pass FailureLogger, we can't easily log to file here without creating new instance or passing it.
            # But let's assume we update stats.
        else:
            pipeline_stats.increment_processed_chunk()

    if error_occurred:
        # Re-raise or return empty?
        # Failure isolation: Return empty, let main loop handle logging if it can.
        # But we want to log the specific error.
        # We'll return a special marker or just empty list.
        # If we return empty list, we lose the error detail for the failure log.
        # Let's attach error to the list? No.
        # Let's rely on logging callback for now, or instantiate FailureLogger here.
        if failure_logger:
            failure_logger.log_failed_chunk(i+1, chunk, error_occurred)
        else:
            FailureLogger().log_failed_chunk(i+1, chunk, error_occurred)
        return []

    return chunk_cards

def generate_qa_pairs(text, deck_names=[], target_language="English", log_callback=None, api_url="http://localhost:1234/v1/chat/completions", api_key="lm-studio", model="local-model", temperature=0.7, max_tokens=-1, prompt_style="", context_window=4096, concurrency=1, card_density="Medium", partial_result_callback=None, stop_callback=None, filter_yes_no=True, exclude_trivia=True, smart_deck_match=True, ai_refinement=False, deterministic_mode=False, pipeline_stats=None):
    """
    Generates Q&A pairs from the given text using a Local LLM.
    """
    if not pipeline_stats:
        pipeline_stats = PipelineStats()

    failure_logger = FailureLogger()

    if deterministic_mode:
        random.seed(42) # Fixed seed for reproducibility
        if log_callback:
            log_callback("Deterministic Mode Enabled: Random seed set to 42, concurrency set to 1, deck shuffling disabled.")

    if log_callback:
        log_callback(f"Sending text to LM Studio for Q&A generation in {target_language}...")

    # 1. Health Check
    try:
        check_llm_server(api_url, api_key)
    except Exception as e:
        if log_callback:
            log_callback(f"Error: Could not connect to LLM Server: {e}")
        return []
    
    if deck_names:
        target_decks = list(deck_names)
        if smart_deck_match and not deterministic_mode:
            # Shuffle decks to prevent LLM from lazily picking the first one
            random.shuffle(target_decks)
            
        deck_instruction = f"You must assign each card to one of the following existing decks: {json.dumps(target_decks)}. Do NOT create new deck names. Analyze the card content carefully and select the deck that matches the specific disease or topic (e.g., if card is about Dementia, select 'Demans')."
    else:
        deck_instruction = "Assign a suitable short deck name for each card. Key: 'deck'."

    density_prompts = {
        "Low": "Focus ONLY on the most critical 'big picture' concepts. Create fewer, higher-quality cards. Avoid minor details.",
        "Medium": "Create a balanced set of cards covering key concepts and important details. Ensure questions are distinct and answers are explanatory.",
        "High": "MODE: EXHAUSTIVE CLINICAL EXTRACTION. Your goal is to create as many valid cards as possible. Extract every single distinct clinical fact, definition, symptom, mechanism, and treatment detail. Do not group multiple facts into one card; split them into separate atomic cards. If a paragraph lists 5 symptoms, create 5 separate cards. Do not summarize. Do not repeat information. Stop immediately when all unique facts are extracted."
    }
    density_instruction = density_prompts.get(card_density, density_prompts["Medium"])

    trivia_instruction = ""
    if exclude_trivia:
        trivia_instruction = f"- EXCLUDE biographical trivia (e.g., birth dates, hobbies, family history, who discovered what) unless it is a specific genetic/clinical risk factor.\n"

    system_prompt = (
        f"You are an expert educational content generator specialized in creating high-quality Anki flashcards. "
        f"Your goal is to extract knowledge from the provided text and format it into a JSON array. "
        f"\n\nUSER INSTRUCTIONS (Tone/Focus):\n{prompt_style}"
        f"\n\nDENSITY SETTING ({card_density}):\n{density_instruction}"
        f"\n\nFORMATTING RULES:\n"
        f"1. Output MUST be a raw JSON array of objects. No Markdown, no code blocks.\n"
        f"2. Each object keys: 'question', 'answer', 'deck', 'quote'.\n"
        f"3. Language: {target_language}.\n"
        f"4. 'quote': The exact text snippet from the source.\n"
        f"5. {deck_instruction}\n"
        f"\n\nQUALITY GUIDELINES (CRITICAL):\n"
        f"- STRICTLY FORBIDDEN: Questions answerable by 'Yes' or 'No'. (e.g., NOT 'Is Alzheimer's common?' -> 'Yes'). Instead ask: 'What is the prevalence of Alzheimer's?'.\n"
        f"- STRICTLY FORBIDDEN: Indirect questions (e.g., 'Parkinson hastalığının belirtileri nelerdir sorusu', 'X hakkında bilgi'). You MUST ask a direct question ending with a question mark (e.g., 'Parkinson hastalığının belirtileri nelerdir?', 'X nedir?').\n"
        f"- USE PRECISE TERMINOLOGY: Do not use 'duyular' (senses) when you mean 'fonksiyonlar' (functions), 'yetenekler' (skills), or 'bulgular' (findings).\n"
        f"- Questions must be SELF-CONTAINED. Do not use pronouns like 'it', 'this', or 'the disease' without specifying what it refers to. (e.g., NOT 'What are the symptoms?' -> 'What are the symptoms of Alzheimer's?').\n"
        f"- Answers must be COMPLETE, GRAMMATICALLY CORRECT sentences. Fix any fragmented text from the source.\n"
        f"- Answers must be SPECIFIC. Avoid tautologies. (e.g., BAD: 'What are the symptoms? A: Symptoms are present.' -> GOOD: 'A: Headache, fever, and rash.').\n"
        f"- Ensure {target_language} grammar is natural and correct. Pay attention to suffixes and sentence structure.\n"
        f"- If the source text is ambiguous or incomplete, DO NOT generate a card for it.\n"
        f"- DO NOT repeat the same question/concept multiple times.\n"
        f"- If the text lists items, ask for the list (e.g., 'What are the causes of...?').\n"
        f"- DO NOT generate cards from the 'References', 'Kaynaklar', or 'Bibliography' sections.\n"
        f"{trivia_instruction}"
        f"\nEXAMPLES:\n"
        f"BAD: Q: Is fever common? A: Yes.\n"
        f"BAD: Q: What is the frequency? A: 85%.\n"
        f"BAD: Q: The question of what the symptoms are. A: Headache.\n"
        f"BAD: Q: Demans yaşlılıkta doğal mıdır? A: Hayır.\n"
        f"GOOD: Q: What is the frequency of fever in this condition? A: Fever is seen in 80% of cases and is usually high-grade.\n"
        f"GOOD: Q: What is the prevalence of Alzheimer's among dementia cases? A: Alzheimer's accounts for approximately 85% of all dementia cases.\n"
        f"GOOD: Q: Demans ile fizyolojik yaşlanma arasındaki ilişki nedir? A: Demans, fizyolojik yaşlanmadan farklı patolojik bir süreçtir."
    )

    # Chunking Logic to handle large files
    # We need to reserve tokens for the System Prompt and the Model's Response.
    # System Prompt ~500 tokens. Expected Response ~1000 tokens.
    RESERVED_TOKENS = 2500 # Increased to ensure plenty of room for response
    
    # Calculate available tokens for input
    available_tokens = context_window - RESERVED_TOKENS
    if available_tokens < 1000:
        available_tokens = 1000 # Minimum floor to prevent errors
        
    # Estimate characters per token. 
    # Adjusted to 1.2 to force smaller chunks and higher granularity.
    chars_per_token = 1.2
    
    # Adjust chunk size based on density to force granularity
    # High density -> Smaller chunks -> Model focuses on details -> More cards
    density_factor = 1.0
    if card_density == "High":
        density_factor = 0.25  # Force even smaller chunks (approx 4x more parts) for high density
    elif card_density == "Medium":
        density_factor = 0.8

    CHUNK_SIZE = int(available_tokens * chars_per_token * density_factor)
    
    start_split = time.time()
    chunks = smart_chunk_text(text, CHUNK_SIZE)
    split_duration = time.time() - start_split

    pipeline_stats.record_chunking_time(split_duration)
    # Update total chunks count in stats
    for _ in chunks: pipeline_stats.increment_chunk_count()
    ResourceGuard.check_chunk_count(len(chunks))

    all_qa_pairs = []
    seen_questions_global = set()
    
    if log_callback:
        log_callback(f"Document split into {len(chunks)} parts in {split_duration:.2f}s.")

    # Safety: Limit concurrency based on system resources
    cpu_count = os.cpu_count() or 1
    # Cap concurrency to avoid system overload (especially memory)
    # Use max(1, cpu_count) just in case
    max_safe_workers = max(1, cpu_count)

    if concurrency > max_safe_workers:
        if log_callback:
            log_callback(f"Warning: Requested concurrency ({concurrency}) exceeds logical CPU count ({max_safe_workers}). Limiting to {max_safe_workers}.")
        concurrency = max_safe_workers

    # Enforce Determinism: Force concurrency=1
    if deterministic_mode:
        concurrency = 1

    # Parallel Execution
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        # If deterministic, we must process in order.
        # But we also want to stream results.
        # We can still use submit, but we must collect results in order.

        future_to_index = {
            executor.submit(
                _process_chunk_task,
                i,
                chunk,
                len(chunks),
                stop_callback,
                log_callback,
                max_tokens,
                system_prompt,
                context_window,
                api_url,
                api_key,
                model,
                temperature,
                ai_refinement,
                deck_names,
                target_language,
                filter_yes_no,
                smart_deck_match,
                pipeline_stats,
                failure_logger
            ): i for i, chunk in enumerate(chunks)
        }
        
        # Iterate over futures as they complete or in order?
        # as_completed yields out of order.
        # If deterministic, we prefer predictable order of output in UI?
        # Actually, if we just want the final list to be deterministic, we can collect all results and sort by index.
        # But we also want to handle partial_result_callback.
        # If concurrency=1, as_completed will yield in order anyway.
        # So we can keep as_completed logic, but we need to ensure we sort at the end if we were running parallel but wanted deterministic output?
        # Deterministic mode forces concurrency=1, so order is guaranteed.

        for future in as_completed(future_to_index):
            if stop_callback and stop_callback():
                break
                
            i = future_to_index[future]
            try:
                new_cards = future.result()
                
                # Deduplicate and Add
                unique_new_cards = []
                for card in new_cards:
                    # Validate
                    valid, reason = CardValidator.validate(card)
                    if not valid:
                        pipeline_stats.add_rejected_cards(1)
                        failure_logger.log_rejected_card(card, reason)
                        continue

                    q_text = card['question']
                    if q_text not in seen_questions_global:
                        seen_questions_global.add(q_text)
                        unique_new_cards.append(card)
                        all_qa_pairs.append(card)
                        
                        if log_callback:
                            quote = card.get('quote', '')
                            quote_fmt = f" | Src: {quote[:60]}..." if quote else ""
                            log_callback(f"  [+] [{card.get('deck')}] Q: {q_text} | A: {card.get('answer')}{quote_fmt}")
                    else:
                        # Duplicate
                         pipeline_stats.add_rejected_cards(1)

                if unique_new_cards:
                    pipeline_stats.add_generated_cards(len(unique_new_cards))

                if log_callback:
                    log_callback(f"  > Part {i+1} completed. Added {len(unique_new_cards)} cards.")

                if partial_result_callback and unique_new_cards:
                    partial_result_callback(unique_new_cards)
                    
            except Exception as e:
                pipeline_stats.increment_failed_chunk()
                if log_callback:
                    log_callback(f"Critical Error in thread {i}: {e}")

    # Final Sort to ensure index order if parallel (for partial determinism even with parallelism, though not guaranteed across runs if race conditions exist)
    # But for deterministic mode, we are single threaded so it's sorted.

    if log_callback:
        log_callback(f"Completed. Generated {len(all_qa_pairs)} total Q&A pairs.")
        
    return all_qa_pairs
