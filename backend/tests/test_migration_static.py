import posixpath
import unittest


# ── Pure logic extracted from DockerContainerManager static methods ──

def _normalize_workspace_path(path, allowed_root="/workspace"):
    normalized = "/" + str(path or "").replace("\\", "/").lstrip("/")
    normalized = posixpath.normpath(normalized)
    allowed = posixpath.normpath(allowed_root or "/workspace")
    if allowed == "/workspace":
        if normalized != allowed and not normalized.startswith(allowed + "/"):
            raise ValueError("Path must stay under /workspace/")
        return normalized
    if normalized != allowed and not normalized.startswith(allowed + "/"):
        raise ValueError(f"Path must stay under {allowed}")
    return normalized


_MIGRATION_EXCLUDED_PARTS = {
    ".session", ".weagent", ".weagent_history", ".weagent_claude_session",
    "__pycache__", "node_modules", ".git",
}


def _should_exclude_migration_path(path, include_hidden=False):
    parts = [p for p in str(path or "").split("/") if p]
    if not include_hidden and any(p.startswith(".") for p in parts):
        return True
    return any(p in _MIGRATION_EXCLUDED_PARTS for p in parts)


def _source_workspace_prefix(source_path):
    parts = [p for p in str(source_path or "").split("/") if p]
    if len(parts) >= 3 and parts[0] == "workspace" and parts[1] == "agents":
        return f"/workspace/agents/{parts[2]}"
    return ""


def _is_ascii_name(text):
    try:
        str(text or "").encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def _map_target_path(source_path, resolved_mapping):
    normalized_source = "/" + str(source_path or "").replace("\\", "/").lstrip("/")
    normalized_source = posixpath.normpath(normalized_source)
    for source_prefix in sorted(resolved_mapping.keys(), key=len, reverse=True):
        if normalized_source == source_prefix or normalized_source.startswith(source_prefix + "/"):
            suffix = normalized_source[len(source_prefix):].lstrip("/")
            target_prefix = resolved_mapping[source_prefix].rstrip("/")
            return target_prefix if not suffix else f"{target_prefix}/{suffix}"
    return normalized_source


# ── Tests ──

class TestNormalizeWorkspacePath(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(_normalize_workspace_path("/workspace/agents/foo"), "/workspace/agents/foo")

    def test_exact_allowed(self):
        self.assertEqual(_normalize_workspace_path("/workspace"), "/workspace")

    def test_backslash_normalization(self):
        self.assertEqual(_normalize_workspace_path("\\workspace\\agents\\foo"), "/workspace/agents/foo")

    def test_outside_workspace_rejected(self):
        with self.assertRaises(ValueError):
            _normalize_workspace_path("/etc/passwd")

    def test_traversal_attack(self):
        with self.assertRaises(ValueError):
            _normalize_workspace_path("/workspace/../../etc/passwd")

    def test_dot_segments_normalized(self):
        self.assertEqual(_normalize_workspace_path("/workspace/agents/foo/./bar/../baz"), "/workspace/agents/foo/baz")

    def test_narrower_allowed_root(self):
        self.assertEqual(_normalize_workspace_path("/workspace/agents/myagent/src", "/workspace/agents"), "/workspace/agents/myagent/src")

    def test_outside_narrower_root(self):
        with self.assertRaises(ValueError):
            _normalize_workspace_path("/workspace/shared", "/workspace/agents")

    def test_empty_path(self):
        with self.assertRaises(ValueError):
            _normalize_workspace_path("")

    def test_none_path(self):
        with self.assertRaises(ValueError):
            _normalize_workspace_path(None)

    def test_root_itself_allowed(self):
        self.assertEqual(_normalize_workspace_path("/workspace"), "/workspace")

    def test_root_without_trailing_slash(self):
        self.assertEqual(_normalize_workspace_path("/workspace/agents"), "/workspace/agents")


class TestShouldExcludeMigrationPath(unittest.TestCase):
    def test_hidden_directory_excluded(self):
        self.assertTrue(_should_exclude_migration_path("/workspace/agents/.session/foo"))
    def test_hidden_file_excluded(self):
        self.assertTrue(_should_exclude_migration_path("/workspace/agents/.config.yaml"))
    def test_node_modules_excluded(self):
        self.assertTrue(_should_exclude_migration_path("/workspace/agents/frontend/node_modules/lodash/index.js"))
    def test_git_excluded(self):
        self.assertTrue(_should_exclude_migration_path("/workspace/agents/.git/HEAD"))
    def test_pycache_excluded(self):
        self.assertTrue(_should_exclude_migration_path("/workspace/agents/backend/__pycache__/foo.pyc"))
    def test_normal_file_not_excluded(self):
        self.assertFalse(_should_exclude_migration_path("/workspace/agents/frontend/src/main.py"))
    def test_include_hidden_allows_dot_files(self):
        self.assertFalse(_should_exclude_migration_path("/workspace/agents/.env", include_hidden=True))
    def test_excluded_still_excluded_with_hidden(self):
        self.assertTrue(_should_exclude_migration_path("/workspace/agents/.session/foo", include_hidden=True))
    def test_mixed_segments(self):
        self.assertTrue(_should_exclude_migration_path("/workspace/agents/src/__pycache__/main.cpython-311.pyc"))
    def test_agents_not_excluded(self):
        self.assertFalse(_should_exclude_migration_path("/workspace/agents"))


class TestSourceWorkspacePrefix(unittest.TestCase):
    def test_normal_agent_path(self):
        self.assertEqual(_source_workspace_prefix("/workspace/agents/frontend/src/main.py"), "/workspace/agents/frontend")
    def test_direct_agent_path(self):
        self.assertEqual(_source_workspace_prefix("/workspace/agents/frontend"), "/workspace/agents/frontend")
    def test_non_agent_path(self):
        self.assertEqual(_source_workspace_prefix("/workspace/shared/data"), "")
    def test_outside_workspace(self):
        self.assertEqual(_source_workspace_prefix("/etc/config"), "")
    def test_empty_path(self):
        self.assertEqual(_source_workspace_prefix(""), "")


class TestIsAsciiName(unittest.TestCase):
    def test_ascii_name(self):
        self.assertTrue(_is_ascii_name("frontend"))
    def test_kebab_case(self):
        self.assertTrue(_is_ascii_name("my-agent"))
    def test_unicode_name(self):
        self.assertFalse(_is_ascii_name("前端"))
    def test_empty_name(self):
        self.assertTrue(_is_ascii_name(""))
    def test_none_name(self):
        self.assertTrue(_is_ascii_name(None))
    def test_mixed_ascii_and_unicode(self):
        self.assertFalse(_is_ascii_name("agent-前端"))


class TestMapTargetPath(unittest.TestCase):
    def test_direct_map(self):
        mapping = {"/workspace/agents/frontend": "/workspace/agents/frontend-v2"}
        self.assertEqual(_map_target_path("/workspace/agents/frontend", mapping), "/workspace/agents/frontend-v2")

    def test_subpath_mapped(self):
        mapping = {"/workspace/agents/frontend": "/workspace/agents/frontend-v2"}
        self.assertEqual(_map_target_path("/workspace/agents/frontend/src/main.py", mapping), "/workspace/agents/frontend-v2/src/main.py")

    def test_no_mapping_found(self):
        self.assertEqual(_map_target_path("/workspace/agents/other/file.py", {}), "/workspace/agents/other/file.py")

    def test_longest_prefix_wins(self):
        mapping = {"/workspace/agents/frontend": "/workspace/agents/fe", "/workspace/agents/frontend/src": "/workspace/agents/fe-src"}
        self.assertEqual(_map_target_path("/workspace/agents/frontend/src/main.py", mapping), "/workspace/agents/fe-src/main.py")

    def test_longer_prefix_not_shorter(self):
        mapping = {"/workspace/agents/frontend": "/workspace/agents/fe", "/workspace/agents/frontend-extra": "/workspace/agents/fe-extra"}
        self.assertEqual(_map_target_path("/workspace/agents/frontend-extra/src", mapping), "/workspace/agents/fe-extra/src")

    def test_backslash_in_source(self):
        mapping = {"/workspace/agents/frontend": "/workspace/agents/fe"}
        self.assertEqual(_map_target_path("\\workspace\\agents\\frontend\\src\\app.js", mapping), "/workspace/agents/fe/src/app.js")


if __name__ == "__main__":
    unittest.main()
