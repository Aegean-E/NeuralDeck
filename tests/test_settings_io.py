import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import settings_io
from settings_io import (
    APP_DIR,
    CONFIG_DEFAULTS,
    application_dir,
    cleanup_stale_temp_files,
    ensure_parent_directory,
    normalize_config,
    normalize_session_data,
    parse_float_setting,
    parse_int_setting,
    quarantine_corrupt_file,
    read_json_file,
    resolve_app_path,
    write_json_file,
)


class TestApplicationDir(unittest.TestCase):
    def test_source_checkout_uses_the_module_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            module_file = Path(temp_dir) / "app" / "settings_io.py"
            self.assertEqual(application_dir(module_file=module_file, frozen=False), module_file.parent.resolve())

    def test_frozen_build_uses_the_executable_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            exe = Path(temp_dir) / "NeuralDeck.exe"
            bundled_module = Path(temp_dir) / "_MEI123" / "settings_io.py"
            self.assertEqual(
                application_dir(module_file=bundled_module, frozen=True, executable=exe),
                exe.parent.resolve(),
            )

    def test_frozen_build_falls_back_when_no_executable_is_available(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            bundled_module = Path(temp_dir) / "_MEI123" / "settings_io.py"
            self.assertEqual(
                application_dir(module_file=bundled_module, frozen=True, executable=""),
                bundled_module.parent.resolve(),
            )


class TestResolveAppPath(unittest.TestCase):
    def test_defaults_to_the_application_directory(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(resolve_app_path("config.json", "NEURALDECK_CONFIG"), APP_DIR / "config.json")

    def test_honours_an_absolute_environment_override(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            override = Path(temp_dir) / "custom-config.json"
            with patch.dict(os.environ, {"NEURALDECK_CONFIG": str(override)}, clear=True):
                self.assertEqual(resolve_app_path("config.json", "NEURALDECK_CONFIG"), override)

    def test_resolves_a_relative_override_against_the_application_directory(self):
        with patch.dict(os.environ, {"NEURALDECK_LOG": "logs/session.log"}, clear=True):
            self.assertEqual(resolve_app_path("session.log", "NEURALDECK_LOG"), APP_DIR / "logs" / "session.log")

    def test_an_empty_override_falls_back_to_the_default(self):
        with patch.dict(os.environ, {"NEURALDECK_CONFIG": "   "}, clear=True):
            self.assertEqual(resolve_app_path("config.json", "NEURALDECK_CONFIG"), APP_DIR / "config.json")


class TestQuarantineCorruptFile(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.path = Path(self.temp_dir.name) / "config.json"

    def test_moves_a_corrupt_file_and_preserves_its_content(self):
        self.path.write_text("{ broken", encoding="utf-8")
        quarantined = quarantine_corrupt_file(self.path)
        self.assertIsNotNone(quarantined)
        self.assertFalse(self.path.exists())
        self.assertTrue(quarantined.name.startswith("config.json.corrupt_"))
        self.assertEqual(quarantined.read_text(encoding="utf-8"), "{ broken")

    def test_returns_none_when_the_file_is_missing(self):
        self.assertIsNone(quarantine_corrupt_file(self.path))

    def test_read_quarantines_malformed_input_when_requested(self):
        self.path.write_text("{ broken", encoding="utf-8")
        errors = []
        data = read_json_file(self.path, {}, on_error=errors.append, quarantine_on_error=True)
        self.assertEqual(data, {})
        self.assertFalse(self.path.exists())
        self.assertEqual(len(list(self.path.parent.glob("config.json.corrupt_*"))), 1)
        self.assertEqual(len(errors), 1)

    def test_read_keeps_a_valid_file_when_quarantine_is_requested(self):
        self.path.write_text(json.dumps({"theme": "darkly"}), encoding="utf-8")
        data = read_json_file(self.path, {}, quarantine_on_error=True)
        self.assertEqual(data, {"theme": "darkly"})
        self.assertTrue(self.path.exists())


class TestCleanupStaleTempFiles(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.dir = Path(self.temp_dir.name)
        self.target = self.dir / "config.json"

    def test_removes_only_old_matching_temp_files(self):
        old_temp = self.dir / ".config.json.old.tmp"
        fresh_temp = self.dir / ".config.json.fresh.tmp"
        replace_temp = self.dir / "config.json~RF1234.TMP"
        unrelated = self.dir / "notes.tmp"
        old_temp.write_text("old", encoding="utf-8")
        fresh_temp.write_text("fresh", encoding="utf-8")
        replace_temp.write_text("replace", encoding="utf-8")
        unrelated.write_text("keep", encoding="utf-8")
        old_time = 1_000_000
        os.utime(old_temp, (old_time, old_time))
        os.utime(replace_temp, (old_time, old_time))
        os.utime(unrelated, (old_time, old_time))

        removed = cleanup_stale_temp_files(self.target, max_age_seconds=3600, now=old_time + 7200)

        self.assertEqual(removed, 2)
        self.assertFalse(old_temp.exists())
        self.assertFalse(replace_temp.exists())
        self.assertTrue(fresh_temp.exists())
        self.assertTrue(unrelated.exists())

    def test_returns_zero_when_the_parent_does_not_exist(self):
        self.assertEqual(cleanup_stale_temp_files(self.dir / "missing" / "config.json"), 0)


class TestReadJsonFile(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.path = Path(self.temp_dir.name) / "settings.json"

    def test_returns_the_default_when_the_file_is_missing(self):
        errors = []
        self.assertEqual(read_json_file(self.path, {"theme": "darkly"}, on_error=errors.append), {"theme": "darkly"})
        self.assertEqual(errors, [])

    def test_returns_the_default_when_the_file_is_malformed(self):
        self.path.write_text("{ not json", encoding="utf-8")
        errors = []
        self.assertEqual(read_json_file(self.path, {}, on_error=errors.append), {})
        self.assertEqual(len(errors), 1)

    def test_returns_the_default_when_the_json_type_does_not_match(self):
        self.path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        errors = []
        self.assertEqual(read_json_file(self.path, {}, on_error=errors.append), {})
        self.assertEqual(len(errors), 1)

    def test_returns_parsed_content_for_a_matching_type(self):
        self.path.write_text(json.dumps({"theme": "cyborg"}), encoding="utf-8")
        self.assertEqual(read_json_file(self.path, {}), {"theme": "cyborg"})

    def test_a_transient_open_error_does_not_quarantine_a_valid_file(self):
        self.path.write_text(json.dumps({"theme": "cyborg"}), encoding="utf-8")
        errors = []
        with patch.object(Path, "open", side_effect=PermissionError("locked")):
            result = read_json_file(self.path, {}, on_error=errors.append, quarantine_on_error=True)
        self.assertEqual(result, {})
        self.assertEqual(len(errors), 1)
        self.assertTrue(self.path.exists())
        self.assertEqual(list(self.path.parent.glob("settings.json.corrupt_*")), [])


class TestNormalizeConfig(unittest.TestCase):
    def test_wrong_types_fall_back_to_documented_defaults(self):
        result = normalize_config({
            "theme": 1,
            "language": None,
            "max_tokens": "many",
            "context_window": "not-a-number",
            "temperature": "hot",
            "selected_decks": "not-a-list",
            "debug_mode": "yes",
        })
        self.assertEqual(result["theme"], "darkly")
        self.assertEqual(result["language"], "English")
        self.assertEqual(result["max_tokens"], -1)
        self.assertEqual(result["context_window"], 4096)
        self.assertEqual(result["temperature"], 0.7)
        self.assertEqual(result["selected_decks"], [])
        self.assertIs(result["debug_mode"], False)

    def test_numeric_strings_are_parsed_and_clamped(self):
        result = normalize_config({
            "concurrency": "3",
            "context_window": "999999",
            "temperature": "1.2",
            "max_tokens": "2048",
        })
        self.assertEqual(result["concurrency"], 3)
        self.assertEqual(result["context_window"], 131072)
        self.assertEqual(result["temperature"], 1.0)
        self.assertEqual(result["max_tokens"], 2048)

    def test_density_is_restricted_and_deck_names_are_strings(self):
        result = normalize_config({
            "card_density": "Extreme",
            "selected_decks": ["Deck A", 7, None, "Deck B"],
        })
        self.assertEqual(result["card_density"], "Medium")
        self.assertEqual(result["selected_decks"], ["Deck A", "Deck B"])

    def test_unknown_keys_are_preserved(self):
        result = normalize_config({"custom_future_key": "kept"})
        self.assertEqual(result["custom_future_key"], "kept")


class TestNormalizeSessionData(unittest.TestCase):
    def test_valid_cards_are_normalized(self):
        result = normalize_session_data([
            {"question": "Q", "answer": "A", "deck": "D", "approved": True, "quote": "source"}
        ])
        self.assertEqual(result, [{"question": "Q", "answer": "A", "deck": "D", "approved": True, "quote": "source"}])

    def test_optional_fields_get_safe_defaults(self):
        result = normalize_session_data([{"question": "Q", "answer": "A"}])
        self.assertEqual(result, [{"question": "Q", "answer": "A", "deck": "Default", "approved": False, "quote": ""}])

    def test_non_list_or_non_object_entries_are_rejected(self):
        self.assertIsNone(normalize_session_data({"question": "Q", "answer": "A"}))
        self.assertIsNone(normalize_session_data(["not a card"]))
        self.assertIsNone(normalize_session_data([{"question": "Q"}]))


class TestWriteJsonFile(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.dir = Path(self.temp_dir.name)

    def _leftovers(self):
        return [p.name for p in self.dir.iterdir() if p.name not in {"config.json", ".config.json.lock"}]

    def test_creates_parent_directories_and_round_trips(self):
        target = self.dir / "nested" / "config.json"
        write_json_file(target, {"language": "Türkçe"})
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"language": "Türkçe"})

    def test_leaves_no_temporary_file_behind(self):
        target = self.dir / "config.json"
        write_json_file(target, {"theme": "darkly"})
        self.assertEqual(self._leftovers(), [])

    def test_replaces_existing_content_in_one_step(self):
        target = self.dir / "config.json"
        write_json_file(target, {"theme": "darkly"})
        write_json_file(target, {"theme": "cyborg", "concurrency": 2})
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"theme": "cyborg", "concurrency": 2})

    def test_honours_the_requested_indent(self):
        target = self.dir / "config.json"
        write_json_file(target, {"theme": "darkly"}, indent=4)
        self.assertIn('\n    "theme"', target.read_text(encoding="utf-8"))

    def test_rejects_a_directory_target_without_leaving_temporary_files(self):
        target = self.dir / "config.json"
        target.mkdir()
        with self.assertRaises(IsADirectoryError):
            write_json_file(target, {"theme": "darkly"})
        self.assertEqual(self._leftovers(), [])

    def test_preserves_an_existing_restrictive_mode(self):
        if os.name == "nt":
            self.skipTest("Windows does not expose POSIX file modes")
        target = self.dir / "config.json"
        target.write_text("{}", encoding="utf-8")
        os.chmod(target, 0o600)
        write_json_file(target, {"theme": "darkly"})
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    @unittest.skipUnless(os.name == "nt", "Windows preserves file attributes through ReplaceFileW")
    def test_preserves_windows_file_attributes(self):
        import ctypes

        target = self.dir / "config.json"
        write_json_file(target, {"old": True})
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.SetFileAttributesW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32]
        kernel32.SetFileAttributesW.restype = ctypes.c_int
        kernel32.GetFileAttributesW.argtypes = [ctypes.c_wchar_p]
        kernel32.GetFileAttributesW.restype = ctypes.c_uint32
        hidden = 0x2
        self.assertTrue(kernel32.SetFileAttributesW(str(target), hidden))

        write_json_file(target, {"old": False})

        self.assertTrue(kernel32.GetFileAttributesW(str(target)) & hidden)

    def test_removes_the_temp_file_when_serialization_fails(self):
        target = self.dir / "config.json"
        write_json_file(target, {"old": True})
        with self.assertRaises(TypeError):
            write_json_file(target, {"bad": object()})
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"old": True})
        self.assertEqual(self._leftovers(), [])

    def test_recovers_from_a_transient_replace_failure(self):
        target = self.dir / "config.json"
        write_json_file(target, {"old": True})
        real_replace = settings_io._replace_once
        calls = []

        def flaky_replace(source, destination):
            calls.append((source, destination))
            if len(calls) == 1:
                raise PermissionError("transient")
            return real_replace(source, destination)

        with patch("settings_io._replace_once", side_effect=flaky_replace):
            write_json_file(target, {"new": True})

        self.assertEqual(len(calls), 2)
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"new": True})
        self.assertEqual(self._leftovers(), [])

    def test_failed_replace_retries_and_keeps_the_old_file(self):
        target = self.dir / "config.json"
        write_json_file(target, {"old": True})
        with patch("settings_io._replace_once", side_effect=PermissionError("busy")) as replace:
            with self.assertRaises(PermissionError):
                write_json_file(target, {"new": True})
        self.assertEqual(replace.call_count, 10)
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"old": True})
        self.assertEqual(self._leftovers(), [])

    def test_concurrent_writers_do_not_share_a_temp_file(self):
        target = self.dir / "config.json"
        errors = []
        start = threading.Barrier(4)

        def writer(number):
            try:
                start.wait(timeout=5)
                for _ in range(25):
                    write_json_file(target, {"writer": number})
            except Exception as exc:  # noqa: BLE001 - collected for the assertion
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(number,)) for number in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        self.assertEqual(errors, [])
        self.assertIn("writer", json.loads(target.read_text(encoding="utf-8")))
        self.assertEqual(self._leftovers(), [])


class TestEnsureParentDirectory(unittest.TestCase):
    def test_creates_a_nested_parent_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "logs" / "nested" / "session.log"
            ensure_parent_directory(target)
            self.assertTrue(target.parent.is_dir())


class TestParseIntSetting(unittest.TestCase):
    def test_parses_valid_integers(self):
        self.assertEqual(parse_int_setting("4096", 1024), 4096)

    def test_accepts_surrounding_whitespace(self):
        self.assertEqual(parse_int_setting("  -1  ", 0), -1)

    def test_returns_the_default_for_blank_or_invalid_input(self):
        self.assertEqual(parse_int_setting("", 7), 7)
        self.assertEqual(parse_int_setting(None, 7), 7)
        self.assertEqual(parse_int_setting("many", 7), 7)

    def test_clamps_to_the_declared_range(self):
        self.assertEqual(parse_int_setting("0", 1, minimum=1), 1)
        self.assertEqual(parse_int_setting("99", 1, maximum=10), 10)

    def test_keeps_in_range_values_untouched(self):
        self.assertEqual(parse_int_setting("5", 1, minimum=1, maximum=10), 5)


class TestParseFloatSetting(unittest.TestCase):
    def test_parses_valid_floats(self):
        self.assertEqual(parse_float_setting("0.35", 0.7), 0.35)

    def test_accepts_surrounding_whitespace(self):
        self.assertEqual(parse_float_setting("  1.0  ", 0.7), 1.0)

    def test_returns_the_default_for_blank_or_invalid_input(self):
        self.assertEqual(parse_float_setting("", 0.7), 0.7)
        self.assertEqual(parse_float_setting(None, 0.7), 0.7)
        self.assertEqual(parse_float_setting("hot", 0.7), 0.7)

    def test_clamps_to_the_declared_range(self):
        self.assertEqual(parse_float_setting("-0.5", 0.7, minimum=0.0, maximum=1.0), 0.0)
        self.assertEqual(parse_float_setting("2", 0.7, minimum=0.0, maximum=1.0), 1.0)

    def test_rejects_non_finite_values(self):
        self.assertEqual(parse_float_setting("nan", 0.7, minimum=0.0, maximum=1.0), 0.7)
        self.assertEqual(parse_float_setting("inf", 0.7, minimum=0.0, maximum=1.0), 0.7)


class TestExampleConfig(unittest.TestCase):
    def test_example_config_matches_the_documented_defaults(self):
        example = Path(__file__).resolve().parent.parent / "config.example.json"
        data = json.loads(example.read_text(encoding="utf-8"))
        self.assertIsInstance(data, dict)
        self.assertEqual(set(data), set(CONFIG_DEFAULTS))
        self.assertEqual(data.get("selected_decks"), [])

    def test_runtime_requirements_are_pinned(self):
        requirements = Path(__file__).resolve().parent.parent / "requirements.txt"
        lines = [
            line.strip()
            for line in requirements.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertTrue(lines)
        self.assertTrue(all("==" in line for line in lines), lines)


if __name__ == "__main__":
    unittest.main()
