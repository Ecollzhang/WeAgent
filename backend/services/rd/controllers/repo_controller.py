"""代码仓库 API — GitHub OAuth + 仓库 CRUD + 代理 API."""
import urllib.parse
from flask import Blueprint, request, jsonify, redirect
from flask_jwt_extended import jwt_required, get_jwt_identity

from database import db
from services.github_service import GitHubService
from services.github_service import encrypt_token as _enc, decrypt_token as _dec
from services.repo_service import repo_service

repo_bp = Blueprint('rd_repos', __name__)


def _user_id():
    return get_jwt_identity()


def _ok(data=None, msg='ok', code=200):
    return jsonify({'code': code, 'message': msg, 'data': data or {}}), code


def _error(msg, code=400):
    return jsonify({'code': code, 'message': msg}), code


def _get_token_for_user(uid):
    """获取用户 GitHub token，未授权返回 None."""
    token = repo_service.get_token(uid)
    if not token:
        return None
    return token


def _get_oauth_config():
    """从数据库读取 GitHub OAuth App 配置."""
    from models.repo import RdGithubOAuthConfig
    cfg = RdGithubOAuthConfig.query.first()
    if not cfg:
        return None
    try:
        secret = _dec(cfg.client_secret)
    except Exception:
        secret = ''
    return {
        'client_id': cfg.client_id,
        'client_secret': secret,
        'redirect_uri': cfg.redirect_uri,
    }


# ══════════════════════════════════════════════════════════════
#  GitHub OAuth App 配置 (用户通过前端设置)
# ══════════════════════════════════════════════════════════════

@repo_bp.route('/api/rd/github/oauth-config', methods=['GET'])
@jwt_required()
def get_oauth_config():
    from models.repo import RdGithubOAuthConfig
    cfg = RdGithubOAuthConfig.query.first()
    if not cfg:
        return _ok({'configured': False, 'redirect_uri': _default_redirect_uri()})
    return _ok({
        'configured': True,
        'client_id': cfg.client_id,
        'redirect_uri': cfg.redirect_uri,
    })


@repo_bp.route('/api/rd/github/oauth-config', methods=['PUT'])
@jwt_required()
def save_oauth_config():
    from models.repo import RdGithubOAuthConfig
    data = request.get_json(silent=True) or {}
    if not data.get('client_id') or not data.get('client_secret'):
        return _error('Client ID 和 Client Secret 不能为空')

    cfg = RdGithubOAuthConfig.query.first()
    if not cfg:
        cfg = RdGithubOAuthConfig(id='default')
        db.session.add(cfg)
    cfg.client_id = data['client_id'].strip()
    cfg.client_secret = _enc(data['client_secret'].strip())
    cfg.redirect_uri = data.get('redirect_uri', '').strip() or _default_redirect_uri()
    db.session.commit()
    return _ok(msg='OAuth 配置已保存')


def _default_redirect_uri():
    """根据当前请求自动生成默认的 redirect_uri."""
    try:
        return request.host_url.rstrip('/') + '/api/rd/github/callback'
    except Exception:
        return 'http://localhost:5101/api/rd/github/callback'


# ══════════════════════════════════════════════════════════════
#  GitHub OAuth 授权
# ══════════════════════════════════════════════════════════════

@repo_bp.route('/api/rd/github/auth-url', methods=['GET'])
@jwt_required()
def github_auth_url():
    oauth = _get_oauth_config()
    if not oauth:
        return _error('请先在"代码仓库"Tab配置 GitHub OAuth App 凭证', 400)
    state = request.args.get('state', '')
    url = GitHubService.get_auth_url(oauth['client_id'], oauth['redirect_uri'])
    if state:
        url += '&state=' + state
    return _ok({'url': url})


@repo_bp.route('/api/rd/github/callback', methods=['GET'])
def github_callback():
    """OAuth 回调 — GitHub 带着 code 重定向回来."""
    oauth = _get_oauth_config()
    if not oauth:
        return _error('OAuth 未配置', 400)

    code = request.args.get('code')
    state = request.args.get('state', '')
    if not code:
        return _error('缺少 authorization code')

    try:
        token_data = GitHubService.exchange_token(
            code, oauth['client_id'], oauth['client_secret']
        )
    except Exception as e:
        return _error(f'换取 token 失败: {str(e)}')

    # 用新 token 获取 GitHub 用户信息
    gh = GitHubService(token_data['access_token'])
    try:
        user_info = gh.get_user()
    except Exception as e:
        return _error(f'获取 GitHub 用户信息失败: {str(e)}')

    # 将 token 信息编码后重定向到前端
    params = urllib.parse.urlencode({
        'access_token': token_data.get('access_token', ''),
        'token_type': token_data.get('token_type', 'bearer'),
        'scope': token_data.get('scope', ''),
        'github_user': user_info.get('login', ''),
        'github_id': user_info.get('id', ''),
        'avatar_url': user_info.get('avatar_url', ''),
    })
    frontend_url = 'http://localhost:8080/rd/callback'
    if state:
        frontend_url += '?state=' + state + '&' + params
    else:
        frontend_url += '?' + params
    return redirect(frontend_url)


@repo_bp.route('/api/rd/github/save-token', methods=['POST'])
@jwt_required()
def github_save_token():
    """前端 OAuth 回调后将 token 保存到后端（加密存储）."""
    data = request.get_json(silent=True) or {}
    if not data.get('access_token'):
        return _error('缺少 access_token')
    repo_service.save_token(_user_id(), data)
    return _ok(msg='Token 已保存')


@repo_bp.route('/api/rd/github/status', methods=['GET'])
@jwt_required()
def github_status():
    return _ok(repo_service.get_token_status(_user_id()))


@repo_bp.route('/api/rd/github/revoke', methods=['DELETE'])
@jwt_required()
def github_revoke():
    repo_service.revoke_token(_user_id())
    return _ok(msg='授权已撤销')


@repo_bp.route('/api/rd/github/repos', methods=['GET'])
@jwt_required()
def list_github_repos():
    """获取当前用户的 GitHub 仓库列表（用于选择关联）."""
    token = _get_token_for_user(_user_id())
    if not token:
        return _error('未连接 GitHub，请先授权', 400)

    gh = GitHubService(token)
    page = request.args.get('page', 1, type=int)
    try:
        repos = gh.list_user_repos(page=page)
    except Exception as e:
        return _error(f'获取 GitHub 仓库列表失败: {str(e)}')

    # 精简字段返回
    items = [{
        'github_id': r.get('id'),
        'owner': r.get('owner', {}).get('login', ''),
        'repo_name': r.get('name', ''),
        'full_name': r.get('full_name', ''),
        'description': r.get('description', ''),
        'default_branch': r.get('default_branch', 'main'),
        'language': r.get('language', ''),
        'html_url': r.get('html_url', ''),
        'clone_url': r.get('clone_url', ''),
        'private': r.get('private', False),
    } for r in repos]
    return _ok({'items': items})


# ══════════════════════════════════════════════════════════════
#  仓库 CRUD (项目 ↔ GitHub 仓库关联)
# ══════════════════════════════════════════════════════════════

@repo_bp.route('/api/rd/projects/<project_id>/repos', methods=['GET'])
@jwt_required()
def list_repos(project_id):
    items = repo_service.list_repos(project_id)
    return _ok({'items': items, 'total': len(items)})


@repo_bp.route('/api/rd/projects/<project_id>/repos', methods=['POST'])
@jwt_required()
def create_repo(project_id):
    data = request.get_json(silent=True) or {}
    if not data.get('full_name'):
        return _error('请选择要关联的仓库')
    try:
        repo = repo_service.create_repo(project_id, data)
        return _ok(repo, '仓库已关联', 201)
    except Exception as e:
        return _error(f'关联失败: {str(e)}')


@repo_bp.route('/api/rd/repos', methods=['GET'])
@jwt_required()
def list_all_repos():
    """获取当前用户所有项目的仓库列表，可按 project_id 过滤."""
    project_id = request.args.get('project_id', '').strip() or None
    items = repo_service.list_all_repos_for_user(_user_id(), project_id=project_id)
    return _ok({'items': items, 'total': len(items)})


@repo_bp.route('/api/rd/repos/<repo_id>', methods=['GET'])
@jwt_required()
def get_repo(repo_id):
    r = repo_service.get_repo(repo_id)
    if not r:
        return _error('仓库不存在', 404)
    return _ok(r)


@repo_bp.route('/api/rd/projects/<project_id>/repos/<repo_id>', methods=['DELETE'])
@jwt_required()
def delete_repo(project_id, repo_id):
    ok = repo_service.delete_repo(repo_id)
    if not ok:
        return _error('仓库不存在', 404)
    return _ok(msg='已取消关联')


# ══════════════════════════════════════════════════════════════
#  代码数据代理 API (后端 → GitHub API → 前端)
# ══════════════════════════════════════════════════════════════

def _get_repo_and_gh(repo_id):
    """获取仓库信息 + 用户的 GitHubService 实例."""
    repo = repo_service.get_repo(repo_id)
    if not repo:
        return None, None, _error('仓库不存在', 404)

    # 获取项目关联用户的 token（取仓库所属项目的第一个有 token 的成员）
    from models.repo import RdRepo, RdGithubToken
    from models.project import RdProjectMember
    # 简化：查找关联项目的成员中有 GitHub token 的
    # 实际场景：取当前用户的 token
    token = _get_token_for_user(_user_id())
    if not token:
        return None, None, _error('未连接 GitHub，请先授权', 400)

    return repo, GitHubService(token), None


@repo_bp.route('/api/rd/repos/<repo_id>/branches', methods=['GET'])
@jwt_required()
def get_repo_branches(repo_id):
    repo, gh, err = _get_repo_and_gh(repo_id)
    if err:
        return err
    try:
        branches = gh.list_branches(repo['owner'], repo['repo_name'])
        items = [{'name': b['name'], 'sha': b['commit']['sha']} for b in branches]
        return _ok({'items': items})
    except Exception as e:
        return _error(f'获取分支失败: {str(e)}')


@repo_bp.route('/api/rd/repos/<repo_id>/branches', methods=['POST'])
@jwt_required()
def create_repo_branch(repo_id):
    repo, gh, err = _get_repo_and_gh(repo_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    if not name:
        return _error('分支名不能为空')
    from_branch = data.get('from_branch', repo.get('default_branch', 'main'))
    try:
        result = gh.create_branch(repo['owner'], repo['repo_name'], name, from_branch)
        return _ok(result, '分支创建成功', 201)
    except Exception as e:
        return _error(f'创建分支失败: {str(e)}')


@repo_bp.route('/api/rd/repos/<repo_id>/commits', methods=['GET'])
@jwt_required()
def get_repo_commits(repo_id):
    repo, gh, err = _get_repo_and_gh(repo_id)
    if err:
        return err
    branch = request.args.get('branch', repo.get('default_branch', 'main'))
    per_page = request.args.get('per_page', 30, type=int)
    try:
        commits = gh.list_commits(
            repo['owner'], repo['repo_name'], branch=branch, per_page=per_page
        )
        items = []
        for c in commits:
            commit_data = c.get('commit', {})
            sha = c.get('sha', '')
            # 获取单个 commit 详情以拿到 stats
            additions = 0
            deletions = 0
            files_changed = 0
            try:
                detail = gh.get_commit(repo['owner'], repo['repo_name'], sha)
                stats = detail.get('stats', {})
                additions = stats.get('additions', 0)
                deletions = stats.get('deletions', 0)
                files_changed = len(detail.get('files', []))
            except Exception:
                pass  # stats 获取失败时保持 0
            items.append({
                'sha': sha,
                'message': (commit_data.get('message', '') or '').split('\n')[0],
                'author': {
                    'name': commit_data.get('author', {}).get('name', ''),
                    'email': commit_data.get('author', {}).get('email', ''),
                    'date': commit_data.get('author', {}).get('date', ''),
                },
                'html_url': c.get('html_url', ''),
                'additions': additions,
                'deletions': deletions,
                'files_changed': files_changed,
            })
        return _ok({'items': items})
    except Exception as e:
        return _error(f'获取提交记录失败: {str(e)}')


@repo_bp.route('/api/rd/repos/<repo_id>/tree', methods=['GET'])
@jwt_required()
def get_repo_tree(repo_id):
    repo, gh, err = _get_repo_and_gh(repo_id)
    if err:
        return err
    branch = request.args.get('branch', repo.get('default_branch', 'main'))
    path = request.args.get('path', '')
    try:
        tree = gh.get_tree(repo['owner'], repo['repo_name'], branch=branch, path=path)
        if isinstance(tree, list):
            # 从 git/trees 返回
            items = [{
                'path': t.get('path', ''),
                'type': t.get('type', 'blob'),  # blob | tree
                'size': t.get('size'),
                'sha': t.get('sha', ''),
            } for t in tree]
        else:
            # 从 contents API 返回
            if isinstance(tree, dict):
                tree = [tree]
            items = [{
                'path': t.get('path', t.get('name', '')),
                'type': t.get('type', 'file'),  # file | dir
                'size': t.get('size', 0),
                'sha': t.get('sha', ''),
            } for t in tree]
        return _ok({'items': items})
    except Exception as e:
        return _error(f'获取文件树失败: {str(e)}')


@repo_bp.route('/api/rd/repos/<repo_id>/commits/<sha>/diff', methods=['GET'])
@jwt_required()
def get_commit_diff(repo_id, sha):
    """获取某次提交的 diff（unified diff 格式），供代码审查使用."""
    repo, gh, err = _get_repo_and_gh(repo_id)
    if err:
        return err
    try:
        detail = gh.get_commit(repo['owner'], repo['repo_name'], sha)
        files = detail.get('files', [])
        # 构造 unified diff
        diff_parts = []
        file_list = []
        for f in files:
            file_list.append({
                'filename': f.get('filename', ''),
                'status': f.get('status', 'modified'),
                'additions': f.get('additions', 0),
                'deletions': f.get('deletions', 0),
                'changes': f.get('changes', 0),
            })
            patch = f.get('patch', '')
            if patch:
                diff_parts.append(f"diff --git a/{f['filename']} b/{f['filename']}")
                diff_parts.append(f"--- a/{f['filename']}")
                diff_parts.append(f"+++ b/{f['filename']}")
                diff_parts.append(patch)
                diff_parts.append('')

        commit_info = {
            'sha': detail.get('sha', sha),
            'message': (detail.get('commit', {}).get('message', '') or ''),
            'author': detail.get('commit', {}).get('author', {}).get('name', ''),
            'date': detail.get('commit', {}).get('author', {}).get('date', ''),
        }
        return _ok({
            'commit': commit_info,
            'files': file_list,
            'diff': '\n'.join(diff_parts),
            'stats': detail.get('stats', {}),
        })
    except Exception as e:
        return _error(f'获取提交 diff 失败: {str(e)}')


@repo_bp.route('/api/rd/repos/<repo_id>/file', methods=['GET'])
@jwt_required()
def get_repo_file(repo_id):
    repo, gh, err = _get_repo_and_gh(repo_id)
    if err:
        return err
    branch = request.args.get('branch', repo.get('default_branch', 'main'))
    path = request.args.get('path', '')
    if not path:
        return _error('缺少文件路径参数 path')
    try:
        content = gh.get_file_content(repo['owner'], repo['repo_name'], path, branch)
        return _ok({'path': path, 'content': content, 'branch': branch})
    except Exception as e:
        return _error(f'获取文件内容失败: {str(e)}')
