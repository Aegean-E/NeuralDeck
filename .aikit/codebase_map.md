# Codebase Map & Symbol Catalog 🗺️

> **AUTO-GENERATED & VERIFIED BY `scripts/update_knowledge_base.py`**
> This document provides an automated, up-to-date registry of all modules, classes, and exported functions across this repository.

---

## 📊 Codebase Metrics
- **Total Python Modules**: `23`
- **Total Classes**: `47`
- **Total Top-Level Functions**: `40`
- **Total Class Methods**: `217`
- **Total Source Lines**: `4740`

---

## 📦 Modules & Exported Symbols

### [`anki_addon/__init__.py`](anki_addon/__init__.py)
**Size**: `247` lines (`9787` bytes)

**Classes:**
- `class AnkiBridgeHandler`
  - Method `.log_message(format, *args)`
  - Method `._set_cors_headers()`
  - Method `.do_OPTIONS()`
  - Method `.do_GET()`
  - Method `.do_POST()`
  - Method `.add_cards_to_anki(deck_name, cards, model_name, media_files)`

**Functions:**
- `def run_server()`
- `def stop_server()`

---

### [`anki_integration.py`](anki_integration.py)
**Size**: `94` lines (`3644` bytes)

**Functions:**
- `def _get_no_proxy_opener()`
- `def check_anki_connection(port)` - *Simple check to see if the Anki add-on server is running.*
- `def get_deck_names(log_callback)` - *Fetches the list of deck names from the Anki add-on.*
- `def create_anki_deck(deck_name, qa_pairs, log_callback)` - *Sends Q&A pairs to the custom Anki Add-on running on 127.0.0.1:5005.*

---

### [`debug_anki.py`](debug_anki.py)
**Size**: `41` lines (`1724` bytes)

**Functions:**
- `def test_connection()`

---

### [`debug_llm.py`](debug_llm.py)
**Size**: `46` lines (`1724` bytes)

**Functions:**
- `def test_llm_generation()`

---

### [`document_processor.py`](document_processor.py)
**Size**: `939` lines (`41537` bytes)

**Functions:**
- `def extract_text_from_pdf(file_path, log_callback)` - *Extracts text from a PDF file.*
- `def _extract_text_from_docx(file_path)` - *Extracts text from a .docx file.*
- `def _extract_text_from_pptx(file_path)` - *Extracts text from a .pptx file.*
- `def _extract_text_from_txt(file_path)` - *Extracts text from a .txt file.*
- `def extract_text_from_document(file_path, log_callback)` - *Extracts text from a supported document file.*
- `def check_llm_server(api_url, api_key)` - *Checks if the LLM server is reachable.*
- `def call_lm_studio(prompt, system_instruction, api_url, api_key, model, temperature, max_tokens, stop_callback, timeout)` - *Calls the local LM Studio server (OpenAI compatible API).*
- `def smart_chunk_text(text, max_chars, min_chars)` - *Splits text into chunks respecting paragraph boundaries.*
- `def robust_parse_objects(text)` - *Scans the text for JSON objects and extracts them individually.*
- `def refine_generated_cards(cards, deck_names, target_language, api_url, api_key, model, temperature, log_callback, stop_callback)` - *Sends the generated cards back to the AI for a second pass to fix errors, *
- `def filter_and_process_cards(raw_data_list, deck_names, smart_deck_match, filter_yes_no)` - *Helper to clean, filter, and assign decks to a list of raw card objects.*
- `def _process_chunk_task(i, chunk, total_chunks, stop_callback, log_callback, max_tokens, system_prompt, context_window, api_url, api_key, model, temperature, ai_refinement, deck_names, target_language, filter_yes_no, smart_deck_match, pipeline_stats, failure_logger)` - *Helper function to process a single chunk in a thread.*
- `def generate_qa_pairs(text, deck_names, target_language, log_callback, api_url, api_key, model, temperature, max_tokens, prompt_style, context_window, concurrency, card_density, partial_result_callback, stop_callback, filter_yes_no, exclude_trivia, smart_deck_match, ai_refinement, deterministic_mode, pipeline_stats)` - *Generates Q&A pairs from the given text using a Local LLM.*

---

### [`main.py`](main.py)
**Size**: `8` lines (`129` bytes)

**Functions:**
- `def main()`

---

### [`pipeline_utils.py`](pipeline_utils.py)
**Size**: `144` lines (`4696` bytes)

**Classes:**
- `class PipelineStats`
  - Method `.__init__()`
  - Method `.record_extraction_time(duration)`
  - Method `.record_chunking_time(duration)`
  - Method `.add_llm_time(duration)`
  - Method `.increment_chunk_count()`
  - Method `.increment_processed_chunk()`
  - Method `.increment_failed_chunk()`
  - Method `.add_generated_cards(count)`
  - Method `.add_rejected_cards(count)`
  - Method `.finish()`
  - Method `.get_summary()`
- `class FailureLogger`
  - Method `.__init__(run_id)`
  - Method `.log_failed_chunk(chunk_index, chunk_text, error)`
  - Method `.log_rejected_card(card, reason)`
  - Method `._append_to_log(filepath, entry)` - *Appends a single JSON entry as a new line (JSONL format).*
- `class CardValidator`
  - Method `.validate(card, min_len, max_len)` - *Validates a card dictionary.*
- `class ResourceGuard`
  - Method `.check_file_size(filepath)`
  - Method `.check_chunk_count(count)`

---

### [`settings_io.py`](settings_io.py)
> *Environment-aware paths and crash-safe persistence for NeuralDeck settings.*

**Size**: `378` lines (`12486` bytes)

**Functions:**
- `def application_dir(module_file, frozen, executable)` - *Return the persistent application directory, including for frozen builds.*
- `def resolve_app_path(default_name, env_var)` - *Resolve a file beside the application unless an environment variable overrides it.*
- `def ensure_parent_directory(path)` - *Create the parent directory for a file path when it does not exist yet.*
- `def quarantine_corrupt_file(path)` - *Move an unreadable state file aside so defaults never overwrite its evidence.*
- `def _report_read_error(path, exc, on_error, quarantine_on_error)`
- `def read_json_file(path, default, on_error, quarantine_on_error)` - *Read JSON from path, returning default when the file is missing, malformed or mistyped.*
- `def cleanup_stale_temp_files(path, max_age_seconds, now)` - *Remove crashed temporary siblings older than the age threshold.*
- `def _replace_once(source, target)` - *Replace target while preserving Windows ACLs and attributes when possible.*
- `def _replace_with_retries(source, target, attempts, delay)` - *Retry a replace that briefly collides with another writer.*
- `def _cross_process_lock(target)` - *Serialize writes across processes so ReplaceFileW is not used concurrently.*
- `def write_json_file(path, data, indent)` - *Write JSON atomically so a crash cannot leave a truncated settings file.*
- `def _write_json_file(path, data, indent)`
- `def parse_int_setting(raw_value, default, minimum, maximum)` - *Parse a numeric entry, clamping it to the declared range and falling back to default.*
- `def parse_float_setting(raw_value, default, minimum, maximum)` - *Parse a decimal entry, rejecting non-finite values and clamping it to the range.*
- `def normalize_config(raw)` - *Normalize persisted config values to the documented types and ranges.*
- `def normalize_session_data(data)` - *Return safe card dictionaries, or None when the session shape is unusable.*

---

### [`tests/mocks.py`](tests/mocks.py)
**Size**: `26` lines (`798` bytes)

**Classes:**
- `class MockLLM`
  - Method `.__init__(response_map)`
  - Method `.call(prompt, system_instruction, **kwargs)`
- `class MockAnki`
  - Method `.__init__()`
  - Method `.add_cards(deck_name, cards)`
  - Method `.get_decks()`

---

### [`tests/run_tests.py`](tests/run_tests.py)
**Size**: `14` lines (`324` bytes)

---

### [`tests/test_anki_addon_logic.py`](tests/test_anki_addon_logic.py)
**Size**: `133` lines (`4090` bytes)

**Classes:**
- `class MockNote`
  - Method `.__init__(col, model)`
  - Method `.__setitem__(key, value)`
  - Method `.__getitem__(key)`
- `class TestAnkiAddonLogic`
  - Method `.setUp()`
  - Method `.test_add_cards_to_anki_legacy_api()`
  - Method `.test_add_cards_to_anki_modern_api()`

---

### [`tests/test_anki_addon_media.py`](tests/test_anki_addon_media.py)
**Size**: `227` lines (`7995` bytes)

**Classes:**
- `class MockNote`
  - Method `.__init__(col, model)`
  - Method `.__setitem__(key, value)`
  - Method `.__getitem__(key)`
- `class TestAnkiAddonMediaHandling`
  - Method `.setUp()`
  - Method `.test_add_cards_with_media_files(mock_abspath)`
  - Method `.test_add_cards_media_path_traversal_blocked(mock_abspath)`
- `class TestAnkiAddonCORS`
  - Method `.setUp()`
  - Method `.test_cors_headers_localhost()`
  - Method `.test_cors_headers_127_0_0_1()`
  - Method `.test_cors_headers_external_rejected()`
- `class TestAnkiAddonOPTIONS`
  - Method `.setUp()`
  - Method `.test_options_returns_200()`
- `class TestAnkiAddonGET`
  - Method `.setUp()`
  - Method `.test_get_decks_success(mock_run_on_main, mock_future)`
- `class TestAnkiAddonPOST`
  - Method `.setUp()`
  - Method `.test_post_add_cards_success(mock_add_cards, mock_run_on_main, mock_future)`
  - Method `.test_post_invalid_path()`

---

### [`tests/test_anki_integration.py`](tests/test_anki_integration.py)
**Size**: `75` lines (`3206` bytes)

**Classes:**
- `class TestAnkiIntegration`
  - Method `.test_check_anki_connection_success(mock_get_opener)`
  - Method `.test_check_anki_connection_failure(mock_get_opener)`
  - Method `.test_create_anki_deck_success(mock_get_opener)`
  - Method `.test_create_anki_deck_connection_error(mock_get_opener)`
  - Method `.test_create_anki_deck_http_error(mock_get_opener)`
  - Method `.test_create_anki_deck_http_error_malformed(mock_get_opener)`

**Functions:**
- `def _opener_returning(response)`

---

### [`tests/test_anki_integration_get_deck_names.py`](tests/test_anki_integration_get_deck_names.py)
**Size**: `90` lines (`3284` bytes)

**Classes:**
- `class TestGetDeckNames`
  - Method `.test_get_deck_names_success(mock_get_opener)`
  - Method `.test_get_deck_names_empty(mock_get_opener)`
  - Method `.test_get_deck_names_with_log_callback(mock_print, mock_get_opener)`
  - Method `.test_get_deck_names_connection_error(mock_print, mock_get_opener)`
  - Method `.test_get_deck_names_http_error(mock_get_opener)`
  - Method `.test_get_deck_names_missing_decks_key(mock_get_opener)`

**Functions:**
- `def _opener_returning(response)`

---

### [`tests/test_deterministic.py`](tests/test_deterministic.py)
**Size**: `83` lines (`3855` bytes)

**Classes:**
- `class TestDeterministicMode`
  - Method `.test_determinism_output_order(mock_chunk, mock_llm, mock_check)`
  - Method `.test_determinism_random_seeding(mock_chunk, mock_llm, mock_check)`
  - Method `.test_nondeterministic_behavior(mock_chunk, mock_llm, mock_check)`

---

### [`tests/test_document_processor.py`](tests/test_document_processor.py)
**Size**: `301` lines (`11860` bytes)

**Classes:**
- `class TestDocumentProcessor`
  - Method `.test_robust_parse_objects_standard()`
  - Method `.test_robust_parse_objects_markdown()`
  - Method `.test_robust_parse_objects_markdown_with_nested_code()`
  - Method `.test_robust_parse_objects_multiple_objects()`
  - Method `.test_robust_parse_objects_wrapper()`
  - Method `.test_robust_parse_objects_nested()`
  - Method `.test_robust_parse_objects_with_text()`
  - Method `.test_filter_and_process_cards_basic()`
  - Method `.test_filter_and_process_cards_yes_no()`
  - Method `.test_filter_and_process_cards_capitalized()`
  - Method `.test_filter_and_process_cards_whitespace()`
  - Method `.test_smart_chunk_text_strict()`
  - Method `.test_smart_chunk_text_sentences()`
  - Method `.test_extract_text_empty(mock_pypdf2, mock_open)`
  - Method `.test_extract_text_image_only(mock_pypdf2, mock_open)`
  - Method `.test_extract_text_partial_success(mock_pypdf2, mock_open)`
  - Method `.test_extract_text_success(mock_pypdf2, mock_open)`
  - Method `.test_extract_text_page_error(mock_pypdf2, mock_open)`
  - Method `.test_retry_success(mock_sleep, mock_urlopen)`
  - Method `.test_call_lm_studio_malformed_chunk(mock_urlopen)`
  - Method `.test_retry_failure(mock_sleep, mock_urlopen)`
  - Method `.test_concurrency_limit(mock_executor, mock_cpu_count, mock_as_completed, mock_check_server)`
  - Method `.test_stop_callback_stops_generation(mock_executor, mock_as_completed, mock_chunk, mock_check_server)`

---

### [`tests/test_document_processor_extra.py`](tests/test_document_processor_extra.py)
**Size**: `187` lines (`7167` bytes)

**Classes:**
- `class TestExtractTextFromDocument`
  - Method `.test_extract_docx(mock_docx)`
  - Method `.test_extract_pptx(mock_pptx)`
  - Method `.test_extract_txt(mock_txt)`
  - Method `.test_extract_pdf(mock_pdf)`
  - Method `.test_unsupported_format()`
- `class TestExtractTextFromDocx`
  - Method `.test_docx_success(mock_document)`
- `class TestExtractTextFromPptx`
  - Method `.test_pptx_success(mock_pres)`
  - Method `.test_pptx_empty(mock_pres)`
- `class TestExtractTextFromTxt`
  - Method `.test_txt_success(mock_file)`
- `class TestCheckLlmServer`
  - Method `.test_check_llm_server_success(mock_urlopen)`
  - Method `.test_check_llm_server_connection_error(mock_urlopen, mock_socket)`
  - Method `.test_check_llm_server_timeout(mock_urlopen, mock_socket)`
  - Method `.test_check_llm_server_http_error(mock_urlopen, mock_socket)`
- `class TestExtractTextFromPdfEdgeCases`
  - Method `.test_pdf_encrypted(mock_pypdf2, mock_open)`
  - Method `.test_pdf_file_not_found(mock_pypdf2, mock_open)`

---

### [`tests/test_failure_isolation.py`](tests/test_failure_isolation.py)
**Size**: `73` lines (`3000` bytes)

**Classes:**
- `class TestFailureIsolation`
  - Method `.test_single_chunk_failure(mock_chunk, mock_llm, mock_check)`
  - Method `.test_malformed_json_partial(mock_chunk, mock_llm, mock_check)`

---

### [`tests/test_pipeline.py`](tests/test_pipeline.py)
**Size**: `95` lines (`3680` bytes)

**Classes:**
- `class TestFullPipeline`
  - Method `.test_full_pipeline_success(mock_anki_opener, mock_lm_studio, mock_check_server, mock_open, mock_pypdf2)`
  - Method `.test_pipeline_extraction_failure(mock_lm_studio, mock_check_server, mock_open, mock_pypdf2)`
  - Method `.test_pipeline_llm_malformed_response(mock_lm_studio, mock_check_server)`

---

### [`tests/test_pipeline_utils.py`](tests/test_pipeline_utils.py)
**Size**: `194` lines (`7642` bytes)

**Classes:**
- `class TestPipelineStats`
  - Method `.setUp()`
  - Method `.test_init()`
  - Method `.test_record_times()`
  - Method `.test_increments()`
  - Method `.test_finish(mock_time)`
  - Method `.test_get_summary()`
  - Method `.test_thread_safety()`
- `class TestCardValidator`
  - Method `.test_validate_success()`
  - Method `.test_validate_empty()`
  - Method `.test_validate_too_short()`
  - Method `.test_validate_too_long()`
  - Method `.test_validate_identical()`
- `class TestResourceGuard`
  - Method `.test_check_file_size(mock_getsize)`
  - Method `.test_check_chunk_count()`
- `class TestFailureLogger`
  - Method `.test_log_failed_chunk(mock_file)`
  - Method `.test_log_rejected_card(mock_file)`

---

### [`tests/test_settings_io.py`](tests/test_settings_io.py)
**Size**: `433` lines (`18842` bytes)

**Classes:**
- `class TestApplicationDir`
  - Method `.test_source_checkout_uses_the_module_directory()`
  - Method `.test_frozen_build_uses_the_executable_directory()`
  - Method `.test_frozen_build_falls_back_when_no_executable_is_available()`
- `class TestResolveAppPath`
  - Method `.test_defaults_to_the_application_directory()`
  - Method `.test_honours_an_absolute_environment_override()`
  - Method `.test_resolves_a_relative_override_against_the_application_directory()`
  - Method `.test_an_empty_override_falls_back_to_the_default()`
- `class TestQuarantineCorruptFile`
  - Method `.setUp()`
  - Method `.test_moves_a_corrupt_file_and_preserves_its_content()`
  - Method `.test_returns_none_when_the_file_is_missing()`
  - Method `.test_read_quarantines_malformed_input_when_requested()`
  - Method `.test_read_keeps_a_valid_file_when_quarantine_is_requested()`
- `class TestCleanupStaleTempFiles`
  - Method `.setUp()`
  - Method `.test_removes_only_old_matching_temp_files()`
  - Method `.test_returns_zero_when_the_parent_does_not_exist()`
- `class TestReadJsonFile`
  - Method `.setUp()`
  - Method `.test_returns_the_default_when_the_file_is_missing()`
  - Method `.test_returns_the_default_when_the_file_is_malformed()`
  - Method `.test_returns_the_default_when_the_json_type_does_not_match()`
  - Method `.test_returns_parsed_content_for_a_matching_type()`
  - Method `.test_a_transient_open_error_does_not_quarantine_a_valid_file()`
- `class TestNormalizeConfig`
  - Method `.test_wrong_types_fall_back_to_documented_defaults()`
  - Method `.test_numeric_strings_are_parsed_and_clamped()`
  - Method `.test_density_is_restricted_and_deck_names_are_strings()`
  - Method `.test_unknown_keys_are_preserved()`
- `class TestNormalizeSessionData`
  - Method `.test_valid_cards_are_normalized()`
  - Method `.test_optional_fields_get_safe_defaults()`
  - Method `.test_non_list_or_non_object_entries_are_rejected()`
- `class TestWriteJsonFile`
  - Method `.setUp()`
  - Method `._leftovers()`
  - Method `.test_creates_parent_directories_and_round_trips()`
  - Method `.test_leaves_no_temporary_file_behind()`
  - Method `.test_replaces_existing_content_in_one_step()`
  - Method `.test_honours_the_requested_indent()`
  - Method `.test_rejects_a_directory_target_without_leaving_temporary_files()`
  - Method `.test_preserves_an_existing_restrictive_mode()`
  - Method `.test_preserves_windows_file_attributes()`
  - Method `.test_removes_the_temp_file_when_serialization_fails()`
  - Method `.test_recovers_from_a_transient_replace_failure()`
  - Method `.test_failed_replace_retries_and_keeps_the_old_file()`
  - Method `.test_concurrent_writers_do_not_share_a_temp_file()`
- `class TestEnsureParentDirectory`
  - Method `.test_creates_a_nested_parent_directory()`
- `class TestParseIntSetting`
  - Method `.test_parses_valid_integers()`
  - Method `.test_accepts_surrounding_whitespace()`
  - Method `.test_returns_the_default_for_blank_or_invalid_input()`
  - Method `.test_clamps_to_the_declared_range()`
  - Method `.test_keeps_in_range_values_untouched()`
- `class TestParseFloatSetting`
  - Method `.test_parses_valid_floats()`
  - Method `.test_accepts_surrounding_whitespace()`
  - Method `.test_returns_the_default_for_blank_or_invalid_input()`
  - Method `.test_clamps_to_the_declared_range()`
  - Method `.test_rejects_non_finite_values()`
- `class TestExampleConfig`
  - Method `.test_example_config_matches_the_documented_defaults()`
  - Method `.test_runtime_requirements_are_pinned()`

---

### [`tests/test_ui_themes.py`](tests/test_ui_themes.py)
**Size**: `21` lines (`553` bytes)

**Classes:**
- `class TestThemeAllowlist`
  - Method `.test_allowlist_matches_the_installed_ttkbootstrap_themes()`

---

### [`ui.py`](ui.py)
**Size**: `891` lines (`41777` bytes)

**Classes:**
- `class TextWidgetHandler` - *Custom logging handler that writes to a Tkinter ScrolledText widget thread-safely.*
  - Method `.__init__(text_widget, root)`
  - Method `.emit(record)`
  - Method `.append_log(msg)`
- `class CardReviewRow` - *A row representing a single generated card for review.*
  - Method `.__init__(parent, question, answer, assigned_deck, available_decks, quote, on_remove)`
  - Method `.get_data()`
  - Method `.show_source()`
  - Method `.remove_row()`
- `class AnkiGeneratorUI`
  - Method `.__init__()`
  - Method `.setup_logging()`
  - Method `.setup_main_tab()`
  - Method `.setup_settings_tab()`
  - Method `.load_config()`
  - Method `._read_int(var, default, minimum, maximum)` - *Read a numeric Tk variable without letting an empty field crash the UI.*
  - Method `._read_float(var, default, minimum, maximum)` - *Read a decimal Tk variable without letting an empty field crash the UI.*
  - Method `.save_settings_ui()`
  - Method `.save_config()`
  - Method `.apply_theme(event)`
  - Method `.fetch_decks()`
  - Method `._fetch_decks_thread()`
  - Method `.update_deck_list_ui()`
  - Method `.save_deck_selection()`
  - Method `.select_file()`
  - Method `.start_processing()`
  - Method `.run_process(file_path, target_lang, api_url, api_key, model, temperature, max_tokens, prompt_style, deck_names, context_window, concurrency, card_density, filter_yes_no, exclude_trivia, smart_deck_match, ai_refinement, deterministic_mode)`
  - Method `.clear_review_area()`
  - Method `.add_manual_card()` - *Adds a blank card row for manual authoring.*
  - Method `.append_cards_to_review(new_cards)`
  - Method `.remove_card_row(row)`
  - Method `.save_session()` - *Saves the current state of generated cards to a JSON file.*
  - Method `.load_session()` - *Restores cards from the session cache file.*
  - Method `.stop_processing()`
  - Method `.on_close()` - *Handle window closing event to ensure all threads are killed.*
  - Method `.clear_all_cards()`
  - Method `.toggle_all_approvals(state)`
  - Method `.bulk_assign_deck()` - *Assigns the selected deck to all checked cards.*
  - Method `.sync_to_anki()`

---
