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
