import pytest

from app.services.capability_import_security import (
    ImportSecurityError,
    parse_npx_import_source,
    validate_bundle_files,
)


def test_parse_npx_package_source_accepts_scoped_package():
    parsed = parse_npx_import_source("npx @orchestra-research/ai-research-skills")

    assert parsed == {
        "kind": "npx_package",
        "command": "npx",
        "args": ["@orchestra-research/ai-research-skills"],
        "package": "@orchestra-research/ai-research-skills",
        "source": "",
    }


def test_parse_npx_skills_add_source_accepts_repo_reference():
    parsed = parse_npx_import_source("npx skills add eze-is/web-access")

    assert parsed == {
        "kind": "npx_skills_add",
        "command": "npx",
        "args": ["skills", "add", "--yes", "--global", "eze-is/web-access"],
        "package": "skills",
        "source": "eze-is/web-access",
    }


@pytest.mark.parametrize(
    "command",
    [
        "npx skills add eze-is/web-access && whoami",
        "npx @scope/pkg | powershell",
        "cmd /c npx @scope/pkg",
        "powershell -Command npx @scope/pkg",
        "npx @scope/pkg > out.txt",
        "npx @scope/pkg; rm -rf .",
    ],
)
def test_parse_npx_source_rejects_shell_injection_forms(command):
    with pytest.raises(ImportSecurityError):
        parse_npx_import_source(command)


def test_bundle_file_validation_rejects_dangerous_paths_and_files():
    result = validate_bundle_files(
        [
            {"path": "safe/SKILL.md", "size": 12},
            {"path": "../escape.py", "size": 1},
            {"path": "scripts/run.exe", "size": 100},
            {"path": ".ssh/id_rsa", "size": 100},
            {"path": "node_modules/pkg/index.js", "size": 100},
        ]
    )

    categories = {item["category"] for item in result["blocking_items"]}
    assert "path_traversal" in categories
    assert "binary_executable" in categories
    assert "sensitive_file" in categories
    assert "package_cache" in categories
    assert result["risk_level"] == "high"
