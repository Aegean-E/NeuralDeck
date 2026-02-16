import unittest
import sys
import os
import json
import time
import threading
from unittest.mock import MagicMock, patch, mock_open

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pipeline_utils import PipelineStats, FailureLogger, CardValidator, ResourceGuard

class TestPipelineStats(unittest.TestCase):
    def setUp(self):
        self.stats = PipelineStats()

    def test_init(self):
        self.assertIsNotNone(self.stats.metrics["start_time"])
        self.assertIsNone(self.stats.metrics["end_time"])
        self.assertEqual(self.stats.metrics["extraction_time"], 0)
        self.assertEqual(self.stats.metrics["chunking_time"], 0)
        self.assertEqual(self.stats.metrics["llm_processing_time"], 0)
        self.assertEqual(self.stats.metrics["total_chunks"], 0)
        self.assertEqual(self.stats.metrics["processed_chunks"], 0)
        self.assertEqual(self.stats.metrics["failed_chunks"], 0)
        self.assertEqual(self.stats.metrics["cards_generated"], 0)
        self.assertEqual(self.stats.metrics["cards_rejected"], 0)

    def test_record_times(self):
        self.stats.record_extraction_time(1.5)
        self.assertEqual(self.stats.metrics["extraction_time"], 1.5)
        self.stats.record_chunking_time(0.5)
        self.assertEqual(self.stats.metrics["chunking_time"], 0.5)

    def test_increments(self):
        self.stats.add_llm_time(2.0)
        self.assertEqual(self.stats.metrics["llm_processing_time"], 2.0)
        self.stats.add_llm_time(1.5)
        self.assertEqual(self.stats.metrics["llm_processing_time"], 3.5)

        self.stats.increment_chunk_count()
        self.assertEqual(self.stats.metrics["total_chunks"], 1)

        self.stats.increment_processed_chunk()
        self.assertEqual(self.stats.metrics["processed_chunks"], 1)

        self.stats.increment_failed_chunk()
        self.assertEqual(self.stats.metrics["failed_chunks"], 1)

        self.stats.add_generated_cards(5)
        self.assertEqual(self.stats.metrics["cards_generated"], 5)

        self.stats.add_rejected_cards(2)
        self.assertEqual(self.stats.metrics["cards_rejected"], 2)

    @patch('time.time')
    def test_finish(self, mock_time):
        # Setup mock times
        start = 100.0
        end = 105.5
        mock_time.return_value = start
        stats = PipelineStats() # start_time will be 100.0

        mock_time.return_value = end
        metrics = stats.finish()

        self.assertEqual(metrics["end_time"], end)
        self.assertEqual(metrics["total_duration"], 5.5)

    def test_get_summary(self):
        self.stats.increment_chunk_count()
        self.stats.increment_chunk_count()
        self.stats.increment_processed_chunk()
        self.stats.increment_failed_chunk()
        self.stats.add_generated_cards(10)
        self.stats.add_rejected_cards(3)
        self.stats.finish()

        summary = self.stats.get_summary()
        self.assertIn("Chunks: 1/2", summary)
        self.assertIn("(Failed: 1)", summary)
        self.assertIn("Cards: 10 Generated, 3 Rejected.", summary)

    def test_thread_safety(self):
        def worker():
            for _ in range(100):
                self.stats.increment_chunk_count()

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(self.stats.metrics["total_chunks"], 500)

class TestCardValidator(unittest.TestCase):
    def test_validate_success(self):
        card = {"question": "What is the powerhouse of the cell?", "answer": "Mitochondria"}
        is_valid, reason = CardValidator.validate(card)
        self.assertTrue(is_valid)
        self.assertEqual(reason, "")

    def test_validate_empty(self):
        card = {"question": "", "answer": "Mitochondria"}
        is_valid, reason = CardValidator.validate(card)
        self.assertFalse(is_valid)
        self.assertEqual(reason, "Empty Question or Answer")

        card = {"question": "What is?", "answer": "   "}
        is_valid, reason = CardValidator.validate(card)
        self.assertFalse(is_valid)
        self.assertEqual(reason, "Empty Question or Answer")

    def test_validate_too_short(self):
        card = {"question": "Short", "answer": "Mitochondria"}
        is_valid, reason = CardValidator.validate(card)
        self.assertFalse(is_valid)
        self.assertIn("Question too short", reason)

        card = {"question": "This is a long enough question?", "answer": "Mi"}
        is_valid, reason = CardValidator.validate(card)
        self.assertFalse(is_valid)
        self.assertEqual(reason, "Answer too short")

    def test_validate_too_long(self):
        card = {"question": "Q" * 501, "answer": "This is a valid answer length."}
        is_valid, reason = CardValidator.validate(card)
        self.assertFalse(is_valid)
        self.assertEqual(reason, "Content exceeds max length")

        card = {"question": "This is a valid question length.", "answer": "A" * 1001}
        is_valid, reason = CardValidator.validate(card)
        self.assertFalse(is_valid)
        self.assertEqual(reason, "Content exceeds max length")

    def test_validate_identical(self):
        card = {"question": "Mitochondria", "answer": "mitochondria"}
        is_valid, reason = CardValidator.validate(card)
        self.assertFalse(is_valid)
        self.assertEqual(reason, "Question and Answer are identical")

class TestResourceGuard(unittest.TestCase):
    @patch('os.path.getsize')
    def test_check_file_size(self, mock_getsize):
        # Within limit
        mock_getsize.return_value = 10 * 1024 * 1024 # 10MB
        ResourceGuard.check_file_size("dummy.pdf") # Should not raise

        # Exceeds limit
        mock_getsize.return_value = 51 * 1024 * 1024 # 51MB
        with self.assertRaises(Exception) as cm:
            ResourceGuard.check_file_size("large.pdf")
        self.assertIn("File too large", str(cm.exception))

    def test_check_chunk_count(self):
        ResourceGuard.check_chunk_count(500) # Should not raise
        with self.assertRaises(Exception) as cm:
            ResourceGuard.check_chunk_count(501)
        self.assertIn("Too many chunks", str(cm.exception))

class TestFailureLogger(unittest.TestCase):
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='[]')
    @patch('pipeline_utils._file_lock')
    def test_log_failed_chunk(self, mock_lock, mock_file, mock_exists):
        mock_exists.return_value = False
        logger = FailureLogger(run_id=123)
        logger.log_failed_chunk(1, "Some text", "Some error")

        mock_file.assert_called_with("failed_chunks_log.json", 'w', encoding='utf-8')
        # Check that the data written is what we expect
        handle = mock_file()
        written_data = "".join(call.args[0] for call in handle.write.call_args_list)
        data = json.loads(written_data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["run_id"], 123)
        self.assertEqual(data[0]["chunk_index"], 1)
        self.assertEqual(data[0]["error"], "Some error")
        self.assertEqual(data[0]["chunk_preview"], "Some text")

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='[]')
    @patch('pipeline_utils._file_lock')
    def test_log_rejected_card(self, mock_lock, mock_file, mock_exists):
        mock_exists.return_value = False
        logger = FailureLogger(run_id=456)
        logger.log_rejected_card({"question": "Q", "answer": "A"}, "Too short")

        mock_file.assert_called_with("rejected_cards_log.json", 'w', encoding='utf-8')
        handle = mock_file()
        written_data = "".join(call.args[0] for call in handle.write.call_args_list)
        data = json.loads(written_data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["run_id"], 456)
        self.assertEqual(data[0]["card"]["question"], "Q")
        self.assertEqual(data[0]["reason"], "Too short")

if __name__ == '__main__':
    unittest.main()
