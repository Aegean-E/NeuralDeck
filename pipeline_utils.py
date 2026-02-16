import time
import json
import logging
import os
import threading

_file_lock = threading.Lock()

class PipelineStats:
    def __init__(self):
        self.metrics = {
            "start_time": time.time(),
            "end_time": None,
            "extraction_time": 0,
            "chunking_time": 0,
            "llm_processing_time": 0,
            "total_chunks": 0,
            "processed_chunks": 0,
            "failed_chunks": 0,
            "cards_generated": 0,
            "cards_rejected": 0,
            "peak_memory_mb": 0 # Placeholder
        }
        self._lock = threading.Lock()

    def record_extraction_time(self, duration):
        with self._lock:
            self.metrics["extraction_time"] = duration

    def record_chunking_time(self, duration):
        with self._lock:
            self.metrics["chunking_time"] = duration

    def add_llm_time(self, duration):
        with self._lock:
            self.metrics["llm_processing_time"] += duration

    def increment_chunk_count(self):
        with self._lock:
            self.metrics["total_chunks"] += 1

    def increment_processed_chunk(self):
        with self._lock:
            self.metrics["processed_chunks"] += 1

    def increment_failed_chunk(self):
        with self._lock:
            self.metrics["failed_chunks"] += 1

    def add_generated_cards(self, count):
        with self._lock:
            self.metrics["cards_generated"] += count

    def add_rejected_cards(self, count):
        with self._lock:
            self.metrics["cards_rejected"] += count

    def finish(self):
        self.metrics["end_time"] = time.time()
        self.metrics["total_duration"] = self.metrics["end_time"] - self.metrics["start_time"]
        return self.metrics

    def get_summary(self):
        return (
            f"Pipeline Completed in {self.metrics.get('total_duration', 0):.2f}s.\n"
            f"Chunks: {self.metrics['processed_chunks']}/{self.metrics['total_chunks']} "
            f"(Failed: {self.metrics['failed_chunks']})\n"
            f"Cards: {self.metrics['cards_generated']} Generated, {self.metrics['cards_rejected']} Rejected."
        )

class FailureLogger:
    def __init__(self, run_id=None):
        self.run_id = run_id or int(time.time())
        self.failed_chunks_file = "failed_chunks_log.jsonl"
        self.rejected_cards_file = "rejected_cards_log.jsonl"
        self._lock = threading.Lock()

    def log_failed_chunk(self, chunk_index, chunk_text, error):
        entry = {
            "run_id": self.run_id,
            "timestamp": time.time(),
            "chunk_index": chunk_index,
            "error": str(error),
            "chunk_preview": chunk_text[:200]
        }
        self._append_to_log(self.failed_chunks_file, entry)

    def log_rejected_card(self, card, reason):
        entry = {
            "run_id": self.run_id,
            "timestamp": time.time(),
            "card": card,
            "reason": reason
        }
        self._append_to_log(self.rejected_cards_file, entry)

    def _append_to_log(self, filepath, entry):
        """Appends a single JSON entry as a new line (JSONL format)."""
        with _file_lock:
            with open(filepath, 'a', encoding='utf-8') as f:
                json.dump(entry, f, ensure_ascii=False)
                f.write('\n')

class CardValidator:
    @staticmethod
    def validate(card, min_len=10, max_len=500):
        """
        Validates a card dictionary.
        Returns (is_valid, reason)
        """
        q = card.get('question', '').strip()
        a = card.get('answer', '').strip()

        if not q or not a:
            return False, "Empty Question or Answer"

        if len(q) < min_len:
            return False, f"Question too short (<{min_len})"

        if len(a) < 3: # Very short answers are suspicious
             return False, "Answer too short"

        if len(q) > max_len or len(a) > max_len * 2:
            return False, "Content exceeds max length"

        if q.lower() == a.lower():
             return False, "Question and Answer are identical"

        return True, ""

class ResourceGuard:
    MAX_FILE_SIZE_MB = 50
    MAX_CHUNKS = 500

    @staticmethod
    def check_file_size(filepath):
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        if size_mb > ResourceGuard.MAX_FILE_SIZE_MB:
            raise Exception(f"File too large ({size_mb:.2f}MB). Max allowed is {ResourceGuard.MAX_FILE_SIZE_MB}MB.")

    @staticmethod
    def check_chunk_count(count):
        if count > ResourceGuard.MAX_CHUNKS:
             raise Exception(f"Too many chunks ({count}). Max allowed is {ResourceGuard.MAX_CHUNKS}. Try a smaller file or different density.")
