import sys
sys.path.insert(0, r'E:\\华南理工\\研一\\第二学期 2026.3.2-\\3-竞赛\\1-字节全栈挑战赛\\3-WeAgent\\combineartifact_editing_system(base_v1.08)\\WeAgent\\backend')

import posixpath, unittest
from test_migration_static import (
    _normalize_workspace_path, _should_exclude_migration_path,
    _source_workspace_prefix, _is_ascii_name, _map_target_path,
)


def _resolve_migration_path_mapping(source_session, target_session, candidate_paths, path_mapping=None):
    provided = {}
    for src_prefix, tgt_prefix in (path_mapping or {}).items():
        provided[_normalize_workspace_path(src_prefix, '/workspace/agents')] = \
            _normalize_workspace_path(tgt_prefix, '/workspace/agents')
    target_workspaces = {}
    for agent in (target_session.agents_config or []):
        name = str(agent.get('workspace_name') or agent.get('role') or agent.get('agent_id') or '')
        target_workspaces[name] = agent
    resolved = {}
    for source_path in candidate_paths:
        source_prefix = _source_workspace_prefix(source_path)
        if not source_prefix or source_prefix in resolved:
            continue
        if source_prefix in provided:
            resolved[source_prefix] = provided[source_prefix]
            continue
        workspace_name = source_prefix.split('/')[3] if len(source_prefix.split('/')) > 3 else ''
        if workspace_name and _is_ascii_name(workspace_name) and workspace_name in target_workspaces:
            resolved[source_prefix] = '/workspace/agents/' + workspace_name
        else:
            session_id_short = source_session.session_id[:8]
            resolved[source_prefix] = '/workspace/agents/migrated_from_' + session_id_short + '/' + (workspace_name or 'workspace')
    return resolved


def _collect_migration_candidates(mgr, source_session, root, selected_paths=None, include_hidden=False):
    paths = selected_paths or [root]
    candidates = []
    skipped = []
    seen = set()

    def walk(node):
        if not isinstance(node, dict):
            return
        node_path = mgr._normalize_workspace_path(node.get('path') or root, '/workspace')
        if mgr._should_exclude_migration_path(node_path, include_hidden=include_hidden):
            skipped.append({'source_path': node_path, 'reason': 'excluded path'})
            return
        if node.get('type') == 'directory':
            children = node.get('children') or []
            if not children:
                skipped.append({'source_path': node_path, 'reason': 'empty directory'})
                return
            for child in children:
                walk(child)
            return
        if node_path not in seen:
            seen.add(node_path)
            candidates.append(node_path)

    for path in paths:
        tree_result = mgr.get_file_tree(source_session.session_id, root=path, include_hidden=include_hidden, max_depth=32)
        if tree_result.get('error'):
            raise ValueError(tree_result['error'])
        tree = tree_result.get('tree')
        if not tree:
            skipped.append({'source_path': path, 'reason': 'path has no readable tree'})
            continue
        walk(tree)

    return candidates, skipped


class SessionContainer:
    def __init__(self, session_id, agents_config=None, container_id='c1'):
        self.session_id = session_id
        self.agents_config = agents_config or []
        self.container_id = container_id


class TestResolveMigrationPathMapping(unittest.TestCase):

    def test_user_provided_mapping_priority(self):
        src = SessionContainer('src-1', [{'agent_id': 'a1', 'workspace_name': 'frontend'}])
        tgt = SessionContainer('tgt-1', [{'agent_id': 'a1', 'workspace_name': 'frontend-v2'}])
        result = _resolve_migration_path_mapping(src, tgt, ['/workspace/agents/frontend/x.py'],
                                                  {'/workspace/agents/frontend': '/workspace/agents/custom'})
        self.assertEqual(result.get('/workspace/agents/frontend'), '/workspace/agents/custom')

    def test_ascii_auto_map_same(self):
        src = SessionContainer('src-1', [{'agent_id': 'a1', 'workspace_name': 'frontend'}])
        tgt = SessionContainer('tgt-1', [{'agent_id': 'a1', 'workspace_name': 'frontend'}])
        result = _resolve_migration_path_mapping(src, tgt, ['/workspace/agents/frontend/x.py'])
        self.assertEqual(result.get('/workspace/agents/frontend'), '/workspace/agents/frontend')

    def test_fallback_migrated(self):
        src = SessionContainer('src-1234', [{'agent_id': 'a1', 'workspace_name': 'srcws'}])
        tgt = SessionContainer('tgt-9999', [{'agent_id': 'a2', 'workspace_name': 'different'}])
        result = _resolve_migration_path_mapping(src, tgt, ['/workspace/agents/srcws/x.py'])
        self.assertIn('migrated_from_src-1234', result.get('/workspace/agents/srcws', ''))

    def test_unicode_fallback(self):
        src = SessionContainer('src-1', [{'agent_id': 'a1', 'workspace_name': 'frontend'}])
        tgt = SessionContainer('tgt-1', [])
        result = _resolve_migration_path_mapping(src, tgt, ['/workspace/agents/frontend/x.py'])
        self.assertIn('migrated_from', result.get('/workspace/agents/frontend', ''))


class TestCollectMigrationCandidates(unittest.TestCase):

    def test_collects_leaf_files(self):
        mock_tree = {'tree': {'type': 'directory', 'path': '/workspace/agents/frontend', 'children': [
            {'path': '/workspace/agents/frontend/src/main.py', 'type': 'file', 'size': 100},
            {'path': '/workspace/agents/frontend/src/utils.py', 'type': 'file', 'size': 50},
        ]}}

        class MockManager:
            _normalize_workspace_path = staticmethod(_normalize_workspace_path)
            _should_exclude_migration_path = staticmethod(_should_exclude_migration_path)
            def get_file_tree(self, sid, root=None, include_hidden=False, max_depth=32):
                return mock_tree

        mgr = MockManager()
        session = SessionContainer('src-1')
        candidates, skipped = _collect_migration_candidates(mgr, session, '/workspace/agents',
                                                            ['/workspace/agents/frontend'])
        self.assertEqual(len(candidates), 2)
        self.assertIn('/workspace/agents/frontend/src/main.py', candidates)

    def test_skips_node_modules(self):
        mock_tree = {'tree': {'type': 'directory', 'path': '/workspace/agents/frontend', 'children': [
            {'path': '/workspace/agents/frontend/node_modules/lodash/index.js', 'type': 'file'},
        ]}}

        class MockManager:
            _normalize_workspace_path = staticmethod(_normalize_workspace_path)
            _should_exclude_migration_path = staticmethod(_should_exclude_migration_path)
            def get_file_tree(self, sid, root=None, include_hidden=False, max_depth=32):
                return mock_tree

        mgr = MockManager()
        session = SessionContainer('src-1')
        candidates, skipped = _collect_migration_candidates(mgr, session, '/workspace/agents',
                                                            ['/workspace/agents/frontend'])
        self.assertEqual(len(candidates), 0)
        self.assertGreater(len(skipped), 0)

    def test_skips_empty_directory(self):
        mock_tree = {'tree': {'type': 'directory', 'path': '/workspace/agents/frontend', 'children': [
            {'path': '/workspace/agents/frontend/emptydir', 'type': 'directory', 'children': []},
        ]}}

        class MockManager:
            _normalize_workspace_path = staticmethod(_normalize_workspace_path)
            _should_exclude_migration_path = staticmethod(_should_exclude_migration_path)
            def get_file_tree(self, sid, root=None, include_hidden=False, max_depth=32):
                return mock_tree

        mgr = MockManager()
        session = SessionContainer('src-1')
        candidates, skipped = _collect_migration_candidates(mgr, session, '/workspace/agents',
                                                            ['/workspace/agents/frontend'])
        self.assertEqual(len(candidates), 0)
        self.assertTrue(any('empty directory' in str(s) for s in skipped))


if __name__ == '__main__':
    unittest.main()

