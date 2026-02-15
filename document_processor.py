import json
import random
import time
import re
import urllib.request
import urllib.error
import socket
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

def extract_text_from_pdf(file_path):
    """
    Extracts text from a PDF file.
    """
    if PyPDF2 is None:
        raise ImportError("PyPDF2 module not found. Please install it in the add-on 'libs' folder.")
        
    text = ""
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            # Attempt to handle encrypted files with empty password
            if reader.is_encrypted:
                try:
                    reader.decrypt("")
                except:
                    pass
            
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
    except Exception as e:
        raise Exception(f"Failed to read PDF: {e}")
    return text

def extract_text_from_video(file_path):
    """
    Placeholder for video transcription logic.
    Future implementation: Use tools like Whisper to transcribe video to text.
    """
    # TODO: Implement video transcription (e.g., using OpenAI Whisper)
    raise NotImplementedError("Video processing is not yet implemented.")

def call_lm_studio(prompt, system_instruction, api_url="http://localhost:1234/v1/chat/completions", api_key="lm-studio", model="local-model", temperature=0.7, max_tokens=-1, stop_callback=None, timeout=120):
    """
    Calls the local LM Studio server (OpenAI compatible API).
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

                    line = line.decode('utf-8').strip()
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
                        except:
                            pass

            return full_response

        except urllib.error.URLError as e:
            last_exception = ConnectionError(f"Could not connect to AI Server at {api_url}. Ensure the server is running. Details: {e}")
            if attempt < retries - 1:
                time.sleep(2)
                continue
        except socket.timeout:
            last_exception = Exception(f"AI Server timed out after {timeout} seconds.")
            if attempt < retries - 1:
                time.sleep(2)
                continue
        except Exception as e:
            # Don't retry other exceptions (like "Processing stopped by user")
            raise e

    if last_exception:
        raise last_exception
    raise Exception("Unknown error occurred during API call.")

def smart_chunk_text(text, max_chars):
    """
    Splits text into chunks respecting paragraph boundaries to avoid cutting sentences.
    """
    chunks = []
    current_chunk = []
    current_length = 0
    
    # Split by paragraphs (double newline) or single lines
    paragraphs = text.split('\n')
    
    for para in paragraphs:
        para += "\n" # Restore newline
        if current_length + len(para) > max_chars:
            if current_chunk:
                chunks.append("".join(current_chunk))
                current_chunk = []
                current_length = 0
        
        current_chunk.append(para)
        current_length += len(para)
    
    if current_chunk:
        chunks.append("".join(current_chunk))
        
    return chunks

def robust_parse_objects(text):
    """
    Scans the text for JSON objects and extracts them individually.
    This is resilient to malformed arrays, missing commas, or truncated tails.
    """
    decoder = json.JSONDecoder()
    pos = 0
    results = []
    
    while pos < len(text):
        # Find the start of the next object
        start_idx = text.find('{', pos)
        if start_idx == -1:
            break
            
        try:
            # Try to decode a single JSON object starting at start_idx
            obj, end_idx = decoder.raw_decode(text, idx=start_idx)
            results.append(obj)
            pos = end_idx
        except json.JSONDecodeError:
            # If decoding fails (e.g. truncated object or syntax error inside),
            # advance past this '{' to try finding the next one.
            pos = start_idx + 1
            
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
    def score_deck(d_name, q_txt, a_txt):
        # Split by comma to get sub-topics (e.g. "Temel Bilgiler, Anamnez")
        parts = [p.strip().lower() for p in d_name.split(',')]
        score = 0
        for part in parts:
            if not part: continue

            # 1. Full phrase match (Highest priority in Question)
            if part in q_txt:
                score += len(part) * 3
            elif part in a_txt:
                score += len(part) * 1  # Lower weight for answer (avoids "Epilepsy" deck for "Tumor causes epilepsy")

            else:
                # 2. Word match (lower weight) to catch "Muayene" in "Nörolojik Muayene"
                words = part.split()
                for w in words:
                    if len(w) > 3:
                        if w in q_txt: score += len(w) * 1.5
                        elif w in a_txt: score += len(w) * 0.5
        return score

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

            current_score = score_deck(deck, q_lower, a_lower)
            best_match = max(deck_names, key=lambda d: score_deck(d, q_lower, a_lower)) if deck_names else None

            # Only switch if the new match is significantly better (score > 0 and better than current)
            if best_match and score_deck(best_match, q_lower, a_lower) > current_score:
                deck = best_match
                current_score = score_deck(best_match, q_lower, a_lower)

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

def _process_chunk_task(i, chunk, total_chunks, stop_callback, log_callback, max_tokens, system_prompt, context_window, api_url, api_key, model, temperature, ai_refinement, deck_names, target_language, filter_yes_no, smart_deck_match):
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
        if log_callback:
            log_callback(f"Error processing part {i+1}: {e}")
        return []

    return chunk_cards

def generate_qa_pairs(text, deck_names=[], target_language="English", log_callback=None, api_url="http://localhost:1234/v1/chat/completions", api_key="lm-studio", model="local-model", temperature=0.7, max_tokens=-1, prompt_style="", context_window=4096, concurrency=1, card_density="Medium", partial_result_callback=None, stop_callback=None, filter_yes_no=True, exclude_trivia=True, smart_deck_match=True, ai_refinement=False):
    """
    Generates Q&A pairs from the given text using a Local LLM.
    """
    if log_callback:
        log_callback(f"Sending text to LM Studio for Q&A generation in {target_language}...")
    
    if deck_names:
        target_decks = list(deck_names)
        if smart_deck_match:
            # Shuffle decks to prevent LLM from lazily picking the first one (e.g. "Baş Ağrısı")
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

    all_qa_pairs = []
    seen_questions_global = set()
    
    if log_callback:
        log_callback(f"Document split into {len(chunks)} parts in {split_duration:.2f}s.")

    # Parallel Execution
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
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
                smart_deck_match
            ): i for i, chunk in enumerate(chunks)
        }
        
        for future in as_completed(future_to_index):
            if stop_callback and stop_callback():
                break
                
            i = future_to_index[future]
            try:
                new_cards = future.result()
                
                # Deduplicate and Add
                unique_new_cards = []
                for card in new_cards:
                    q_text = card['question']
                    if q_text not in seen_questions_global:
                        seen_questions_global.add(q_text)
                        unique_new_cards.append(card)
                        all_qa_pairs.append(card)
                        
                        if log_callback:
                            quote = card.get('quote', '')
                            quote_fmt = f" | Src: {quote[:60]}..." if quote else ""
                            log_callback(f"  [+] [{card.get('deck')}] Q: {q_text} | A: {card.get('answer')}{quote_fmt}")

                if log_callback:
                    log_callback(f"  > Part {i+1} completed. Added {len(unique_new_cards)} cards.")

                if partial_result_callback and unique_new_cards:
                    partial_result_callback(unique_new_cards)
                    
            except Exception as e:
                if log_callback:
                    log_callback(f"Critical Error in thread {i}: {e}")

    if log_callback:
        log_callback(f"Completed. Generated {len(all_qa_pairs)} total Q&A pairs.")
        
    return all_qa_pairs
