# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Keep the README current

Update `README.md` whenever an entry point, flag, dependency, or user-visible
behavior changes.

## Reuse shared helpers

Check `src/polytool/_utils.py` before adding cross-platform code. It owns:

- TTY- and Windows-aware color logging
- external binary detection and install hints
- Python package bootstrap
- macOS, Windows, and Linux clipboard dispatch
- the append-only Git sync used by `vcadd`

Keep OS-specific behavior in this module instead of duplicating it in commands.

## Commands

This project uses `uv` and the lockfile is committed.

```sh
uv sync --locked
uv run pytest
uv run ruff check .
uv build
uv tool install --editable .
```

Run an entry point without installing it with `uv run <command> --help`.
