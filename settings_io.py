"""Environment-aware paths and crash-safe persistence for NeuralDeck settings."""

import contextlib
import json
import math
import os
import stat
import sys
import tempfile
import threading
import time
from pathlib import Path

if os.name == "nt":
    import ctypes
    import msvcrt

    _KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _REPLACE_FILE_W = _KERNEL32.ReplaceFileW
    _REPLACE_FILE_W.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    _REPLACE_FILE_W.restype = ctypes.c_int
else:
    import fcntl

    ctypes = None
    _REPLACE_FILE_W = None

REPLACEFILE_IGNORE_MERGE_ERRORS = 0x00000002


def application_dir(module_file=None, frozen=None, executable=None):
    """Return the persistent application directory, including for frozen builds."""
    if frozen is None:
        frozen = bool(getattr(sys, "frozen", False))

    if frozen:
        executable_path = executable if executable is not None else sys.executable
        if executable_path:
            return Path(executable_path).resolve().parent

    source_file = module_file if module_file is not None else __file__
    return Path(source_file).resolve().parent


APP_DIR = application_dir()


def resolve_app_path(default_name, env_var):
    """Resolve a file beside the application unless an environment variable overrides it."""
    override = os.environ.get(env_var, "").strip()
    if not override:
        return APP_DIR / default_name

    path = Path(override).expanduser()
    if not path.is_absolute():
        path = APP_DIR / path
    return path


def ensure_parent_directory(path):
    """Create the parent directory for a file path when it does not exist yet."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def quarantine_corrupt_file(path):
    """Move an unreadable state file aside so defaults never overwrite its evidence."""
    target = Path(path)
    if not target.is_file():
        return None

    stamp = time.strftime("%Y%m%d-%H%M%S")
    candidate = target.with_name(f"{target.name}.corrupt_{stamp}")
    counter = 1
    while candidate.exists():
        candidate = target.with_name(f"{target.name}.corrupt_{stamp}_{counter}")
        counter += 1

    try:
        target.replace(candidate)
    except OSError:
        return None
    return candidate


def _report_read_error(path, exc, on_error, quarantine_on_error):
    if quarantine_on_error:
        quarantined = quarantine_corrupt_file(path)
        if quarantined is not None:
            exc = ValueError(f"{exc}; moved to {quarantined}")
    if on_error is not None:
        on_error(exc)


def read_json_file(path, default, on_error=None, quarantine_on_error=False):
    """Read JSON from path, returning default when the file is missing, malformed or mistyped."""
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return default
    except ValueError as exc:
        _report_read_error(path, exc, on_error, quarantine_on_error)
        return default
    except (OSError, TypeError) as exc:
        if on_error is not None:
            on_error(exc)
        return default

    if type(data) is not type(default):
        _report_read_error(
            path,
            ValueError(f"{path} contains {type(data).__name__}, expected {type(default).__name__}"),
            on_error,
            quarantine_on_error,
        )
        return default
    return data


def cleanup_stale_temp_files(path, max_age_seconds=86400, now=None):
    """Remove crashed temporary siblings older than the age threshold."""
    target = Path(path)
    parent = target.parent
    if not parent.is_dir():
        return 0

    cutoff = (time.time() if now is None else now) - max_age_seconds
    prefix = f".{target.name}."
    replace_prefix = f"{target.name}~RF"
    removed = 0
    for candidate in parent.iterdir():
        is_writer_temp = candidate.name.startswith(prefix) and candidate.name.endswith(".tmp")
        is_replace_temp = candidate.name.startswith(replace_prefix) and candidate.name.upper().endswith(".TMP")
        if not (is_writer_temp or is_replace_temp):
            continue
        try:
            if candidate.is_file() and candidate.stat().st_mtime < cutoff:
                candidate.unlink()
                removed += 1
        except OSError:  # hygiene: allow one stale temp file may vanish while scanning
            continue
    return removed


def _replace_once(source, target):
    """Replace target while preserving Windows ACLs and attributes when possible."""
    if _REPLACE_FILE_W is not None and target.exists():
        if _REPLACE_FILE_W(str(target), str(source), None, REPLACEFILE_IGNORE_MERGE_ERRORS, None, None):
            return
        error = ctypes.get_last_error()
        if not target.exists():
            os.replace(source, target)
            return
        if error in (1, 50):
            os.replace(source, target)
            return
        raise ctypes.WinError(error)
    os.replace(source, target)


def _replace_with_retries(source, target, attempts=10, delay=0.02):
    """Retry a replace that briefly collides with another writer."""
    for attempt in range(attempts):
        try:
            _replace_once(source, target)
            return
        except OSError as exc:
            retryable = isinstance(exc, PermissionError) or getattr(exc, "winerror", None) in (2, 1175, 1176, 1177)
            if not retryable or attempt == attempts - 1:
                raise
            time.sleep(delay)


_WRITE_LOCK = threading.Lock()


@contextlib.contextmanager
def _cross_process_lock(target):
    """Serialize writes across processes so ReplaceFileW is not used concurrently."""
    lock_path = target.with_name(f".{target.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as handle:  # hygiene: allow binary lock file holds one byte and has no encoding
        if os.name == "nt":
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()

        deadline = time.monotonic() + 3.0
        while True:
            try:
                if os.name == "nt":
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"Timed out waiting for settings lock: {lock_path}")
                time.sleep(0.02)

        try:
            yield
        finally:
            try:
                if os.name == "nt":
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:  # hygiene: allow lock release during teardown must not mask the write result
                pass


def write_json_file(path, data, indent=2):
    """Write JSON atomically so a crash cannot leave a truncated settings file."""
    target = Path(path)
    with _WRITE_LOCK:
        with _cross_process_lock(target):
            _write_json_file(target, data, indent)


def _write_json_file(path, data, indent):
    target = Path(path)
    if target.is_dir():
        raise IsADirectoryError(f"Cannot write JSON to a directory: {target}")

    ensure_parent_directory(target)
    existing_mode = None
    if os.name != "nt":
        try:
            existing_mode = stat.S_IMODE(target.stat().st_mode)
        except OSError:
            existing_mode = None

    descriptor = -1
    temp_path = None
    try:
        descriptor, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
        temp_path = Path(temp_name)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = -1
            json.dump(data, handle, ensure_ascii=False, indent=indent)
            handle.flush()
            os.fsync(handle.fileno())

        if existing_mode is not None:
            os.chmod(temp_path, existing_mode)
        _replace_with_retries(temp_path, target)
        temp_path = None
    finally:
        if descriptor != -1:
            os.close(descriptor)
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:  # hygiene: allow cleanup failure must not mask the write result
                pass


def parse_int_setting(raw_value, default, minimum=None, maximum=None):
    """Parse a numeric entry, clamping it to the declared range and falling back to default."""
    try:
        value = int(str(raw_value).strip())
    except (TypeError, ValueError):
        return default

    if minimum is not None and value < minimum:
        return minimum
    if maximum is not None and value > maximum:
        return maximum
    return value


def parse_float_setting(raw_value, default, minimum=None, maximum=None):
    """Parse a decimal entry, rejecting non-finite values and clamping it to the range."""
    try:
        value = float(str(raw_value).strip())
    except (TypeError, ValueError):
        return default

    if not math.isfinite(value):
        return default
    if minimum is not None and value < minimum:
        return minimum
    if maximum is not None and value > maximum:
        return maximum
    return value


CONFIG_DEFAULTS = {
    "theme": "darkly",
    "language": "English",
    "api_url": "http://localhost:1234/v1/chat/completions",
    "api_key": "lm-studio",
    "model": "local-model",
    "temperature": 0.7,
    "max_tokens": -1,
    "context_window": 4096,
    "card_density": "Medium",
    "concurrency": 1,
    "filter_yes_no": True,
    "exclude_trivia": True,
    "smart_deck_match": True,
    "ai_refinement": False,
    "prompt_style": "",
    "selected_decks": [],
    "deterministic_mode": False,
    "debug_mode": False,
}

_INT_LIMITS = {
    "context_window": (1000, 131072),
    "concurrency": (1, 10),
}


def normalize_config(raw):
    """Normalize persisted config values to the documented types and ranges."""
    source = dict(raw) if isinstance(raw, dict) else {}
    result = dict(CONFIG_DEFAULTS)
    result.update({key: value for key, value in source.items() if key not in CONFIG_DEFAULTS})

    for key, default in CONFIG_DEFAULTS.items():
        value = source.get(key, default)
        if isinstance(default, bool):
            result[key] = value if isinstance(value, bool) else default
        elif isinstance(default, int):
            if isinstance(value, bool):
                result[key] = default
            else:
                minimum, maximum = _INT_LIMITS.get(key, (None, None))
                result[key] = parse_int_setting(value, default, minimum, maximum)
        elif isinstance(default, float):
            result[key] = parse_float_setting(value, default, 0.0, 1.0)
        elif isinstance(default, list):
            result[key] = [item for item in value if isinstance(item, str)] if isinstance(value, list) else list(default)
        else:
            result[key] = value if isinstance(value, str) else default

    if result["card_density"] not in ("Low", "Medium", "High"):
        result["card_density"] = "Medium"
    return result


def normalize_session_data(data):
    """Return safe card dictionaries, or None when the session shape is unusable."""
    if not isinstance(data, list):
        return None

    cards = []
    for item in data:
        if not isinstance(item, dict):
            return None
        question = item.get("question")
        answer = item.get("answer")
        if not isinstance(question, str) or not isinstance(answer, str):
            return None

        deck = item.get("deck", "Default")
        approved = item.get("approved", False)
        quote = item.get("quote", "")
        cards.append({
            "question": question,
            "answer": answer,
            "deck": deck if isinstance(deck, str) else "Default",
            "approved": approved if isinstance(approved, bool) else False,
            "quote": quote if isinstance(quote, str) else "",
        })
    return cards
