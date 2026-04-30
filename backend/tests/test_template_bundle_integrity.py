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


def test_validate_required_content_opencode_passes_with_required_keys() -> None:
    manager = TemplateManager()
    bundle = {
        "opencode.jsonc": """
        {
          "$schema": "https://opencode.ai/config.json",
          "instructions": [".opencode/AGENTS.md"],
          "agent": {"default": "implementer"},
          "command": {"start-work": {"template": "x", "agent": "planner"}},
          "mcp": {"filesystem": {"type": "local", "enabled": true, "command": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "."]}},
          "plugin": ["filesystem"],
          "provider": {"default": "gemini"},
          "permission": {"defaultMode": "acceptEdits"}
        }
        """,
        ".opencode/AGENTS.md": "# AGENTS.md\n",
        ".opencode/commands/start-work.md": "## Goal\n- a\n\n## Steps\n- b\n",
    }

    manager._validate_required_content(bundle, "OpenCode")


def test_validate_required_content_claude_missing_workflow_raises() -> None:
    manager = TemplateManager()
    bundle = {
        ".claude/settings.json": '{"$schema":"https://json.schemastore.org/claude-code-settings.json","permissions":{"mode":"plan"}}',
        ".claude/CLAUDE.md": "# CLAUDE.md\n\n## Goal\n- x\n",
        ".claude/commands/start-work.md": "## Goal\n- a\n\n## Steps\n- b\n",
    }

    with pytest.raises(RuntimeError) as exc:
        manager._validate_required_content(bundle, "ClaudeCode")

    assert "workflow" in str(exc.value).lower()
