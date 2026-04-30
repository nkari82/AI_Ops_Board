from __future__ import annotations

import pytest

from backend.services.template_manager import TemplateManager


def test_validate_required_files_opencode_missing_file_raises() -> None:
    manager = TemplateManager()
    bundle = {
        ".opencode/AGENTS.md": "x",
        ".opencode/Rule.md": "x",
        ".opencode/commands/start-work.md": "x",
    }

    with pytest.raises(RuntimeError) as exc:
        manager._validate_required_files(bundle, "OpenCode")

    assert "opencode.jsonc" in str(exc.value)


def test_validate_required_files_claude_missing_file_raises() -> None:
    manager = TemplateManager()
    bundle = {
        ".claude/CLAUDE.md": "x",
        ".claude/Rule.md": "x",
        ".claude/commands/start-work.md": "x",
    }

    with pytest.raises(RuntimeError) as exc:
        manager._validate_required_files(bundle, "ClaudeCode")

    assert ".claude/settings.json" in str(exc.value)


def test_validate_required_files_opencode_passes_with_minimum_set() -> None:
    manager = TemplateManager()
    bundle = {
        "opencode.jsonc": "{}",
        ".opencode/AGENTS.md": "x",
        ".opencode/Rule.md": "x",
        ".opencode/commands/start-work.md": "x",
    }

    manager._validate_required_files(bundle, "OpenCode")
