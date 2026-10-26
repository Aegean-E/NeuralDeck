# Decisions

Why this project is built the way it is, oldest first. One entry per decision that changes a
contract, a dependency, a data format or the architecture; IDs are consecutive and never reused.

<!-- Entry format:
### ADR-NNN: <decision in one line>
- **Date**: YYYY-MM-DD
- **Status**: Accepted
- **Context**: <what forced the decision>
- **Decision**: <what was decided>
- **Consequences**: <what follows, including what it costs>
-->

### ADR-001: Adopt the AIKit project workflow and gate hygiene
- **Date**: 2026-10-20
- **Status**: Accepted
- **Context**: NeuralDeck is now tracked as an AIKit project, so its Phase 4 gates (tests, hygiene, guidelines, secrets) must pass before each commit without changing production behaviour.
- **Decision**: Keep `.aikit/` project memory in the repository except transient lock, backup and temp files; annotate deliberate silent fallbacks inline with `hygiene: allow <reason>` instead of reshaping UI error paths; maintain the README cold-start quick reference and a complete top-level tree.
- **Consequences**: Commits require `python aikit.py check NeuralDeck`; deliberate fallbacks carry an explicit reason; runtime JSONL logs and the session cache stay untracked.

### ADR-002: Resolve settings beside the app and persist them atomically
- **Date**: 2026-10-22
- **Status**: Accepted
- **Context**: The README promised `NEURALDECK_CONFIG` and `NEURALDECK_LOG` overrides, but the code read and wrote `config.json`, `session_cache.json` and `session.log` relative to the current working directory, so launching NeuralDeck from another folder could create new files or lose saved settings. Plain `json.dump` writes could also leave a truncated file after a crash, Generate read context window and concurrency from the last saved config rather than the values visible in the Settings tab, and empty numeric fields raised `TclError`.
- **Decision**: Add `settings_io.py` as the single place that resolves the config and log paths. The default directory is the source module's directory, or the executable's directory in a frozen (`sys.frozen`) build, so a PyInstaller one-file executable does not write into its temporary extraction directory. `NEURALDECK_CONFIG` and `NEURALDECK_LOG` override the paths. JSON is read with a typed fallback and an optional error callback; it is written while holding an in-process lock and a hidden lock-file sibling across processes, through a unique `tempfile.mkstemp` sibling, flushed with `fsync`, and moved with `ReplaceFileW` on Windows NTFS where supported (preserving ACLs and attributes), with an `os.replace` fallback and bounded retries for transient sharing violations on unsupported filesystems. Existing POSIX modes are preserved and new files start at `0600`; the log parent directory is created before FileHandler. Config keeps its four-space indentation while the session keeps two. The session cache lives beside the resolved config file. Malformed or wrong-shaped config and session files are quarantined as `.corrupt_<timestamp>` siblings before defaults are used; a file that cannot be read because of an I/O error is left in place and blocks saving over it until it is removed or the application restarts. Stale temporary siblings older than one day are removed at startup. Config values are normalized to documented types and ranges before the UI uses them, session entries are validated before restoration, and failed config writes are logged while an explicit Settings save reports the failure in a dialog. The UI reads live context window, concurrency, max-token and temperature values on Generate and clamps invalid entries to bounded defaults.
- **Consequences**: The documented environment variables now work, including nested log paths; user data stays with the application regardless of the launch directory and survives a frozen one-file build; an abrupt process termination during a write cannot leave a truncated target; concurrent writers use distinct temp files; a restrictive POSIX mode and Windows NTFS ACLs are not loosened; unsupported filesystems fall back without that metadata guarantee. Generate uses the values the user sees. Deliberately malformed numeric input is corrected silently to the declared default or range instead of raising `TclError`, and an unreadable session cache is logged and preserved for inspection instead of disappearing silently.

### ADR-003: Keep personal configuration out of version control
- **Date**: 2026-10-22
- **Status**: Accepted
- **Context**: The tracked `config.json` mixed application defaults with personal deck names, language and an API-key field. Every settings save dirtied the repository, and a user-customized key could be committed by accident.
- **Decision**: Untrack `config.json`, ignore it, and commit `config.example.json` with the documented defaults and an empty `selected_decks` list. A fresh checkout may copy the example, while the UI creates `config.json` on the first save if it is absent.
- **Consequences**: Personal settings no longer appear in commits or on the remote; the default configuration remains documented and testable; an existing local `config.json` keeps working because untracking does not delete the working file.

## Licensing migration (agpl-final)

- New versions use the Aegean License 1.1 (AL-1.1); versions up to and including `agpl-final` remain under GNU AGPL-3.0.
- Rights holder: AegeanWorks; commercial use under ACL-1.0.
- Counsel review of the 1.1 texts remains pending.

## License notice cleanup (2026-10-26)

- The license-history notes were removed from README.md and COMMERCIAL.md: the project is offered only under the Aegean License 1.1 (AL-1.1), with commercial use under ACL-1.0.
