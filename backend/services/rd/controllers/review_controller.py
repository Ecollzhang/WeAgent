"""代码审查 API — 脚本审查 + AI 审查双引擎."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from services.review_service import review_service
from services.review_engine import review_engine
from services.script_review_engine import script_review_engine
from models.rd_model_config import RdModelConfig
from database import db

review_bp = Blueprint('rd_reviews', __name__)


def _user_id():
    return get_jwt_identity()


def _ok(data=None, msg='ok', code=200):
    return jsonify({'code': code, 'message': msg, 'data': data or {}}), code


def _error(msg, code=400):
    return jsonify({'code': code, 'message': msg}), code


def _do_review(data, project_id, review_type, code_content, language, file_paths):
    """统一审查调度：根据 review_method 选择脚本或 LLM 审查.

    review_method: 'script' (默认) | 'llm'
    """
    review_method = data.get('review_method', 'script')

    if review_method == 'llm':
        return _do_llm_review(data, project_id, review_type, code_content, language, file_paths)
    else:
        return _do_script_review(data, project_id, review_type, code_content, language, file_paths)


def _do_script_review(data, project_id, review_type, code_content, language, file_paths):
    """脚本审查 — 基于规则模式，无需 LLM."""
    title = data.get('title') or f"脚本审查：{'、'.join(file_paths) if file_paths else '代码片段'}"
    review_data = {
        'repo_id': data.get('repo_id') or None,
        'title': title,
        'description': data.get('description', ''),
        'code_content': code_content,
        'file_paths': file_paths,
        'language': language,
        'branch': data.get('branch') or None,
        'commit_sha': data.get('commit_sha', ''),
        'review_method': 'script',
    }
    review = review_service.create_review(project_id, review_data, user_id=_user_id())

    result = script_review_engine.review(
        code_content,
        language=language,
        file_paths=file_paths,
    )

    updated = review_service.update_review(review['id'], {
        'overall_score': result.overall_score,
        'scores': result.scores,
        'summary': result.summary,
        'status': 'completed',
        'issues': result.issues,
    })
    return _ok(updated, '脚本审查完成', 201)


def _do_llm_review(data, project_id, review_type, code_content, language, file_paths):
    """LLM 审查 — 使用用户配置的模型和 API Key."""
    uid = _user_id()
    title = data.get('title') or f"AI 审查：{'、'.join(file_paths) if file_paths else '代码片段'}"
    review_data = {
        'repo_id': data.get('repo_id') or None,
        'title': title,
        'description': data.get('description', ''),
        'code_content': code_content,
        'file_paths': file_paths,
        'language': language,
        'branch': data.get('branch') or None,
        'commit_sha': data.get('commit_sha', ''),
        'review_method': 'llm',
    }
    review = review_service.create_review(project_id, review_data, user_id=uid)

    try:
        if review_type == 'commit':
            result = review_engine.review_diff(
                data.get('diff_content', code_content),
                commit_info=data.get('commit_info', {}),
                file_list=data.get('diff_files', []),
                language=language,
                context=data.get('description') or None,
                user_id=uid,
            )
        else:
            result = review_engine.review_code(
                code_content,
                language=language,
                file_paths=file_paths,
                context=data.get('description') or None,
                user_id=uid,
            )
    except Exception as e:
        review_service.update_review(review['id'], {'status': 'failed'})
        return _error(f'AI 审查失败: {str(e)}', 500)

    updated = review_service.update_review(review['id'], {
        'overall_score': result.overall_score,
        'scores': result.scores,
        'summary': result.summary,
        'status': 'completed' if result.issues or result.overall_score > 0 else 'failed',
        'issues': result.issues,
    })
    return _ok(updated, 'AI 审查完成', 201)


# ══════════════════════════════════════════════════════════════
#  模型配置同步
# ══════════════════════════════════════════════════════════════

@review_bp.route('/api/rd/model-config/sync', methods=['POST'])
@jwt_required()
def sync_model_config():
    """同步用户模型配置到 RD 本地表。由主后端在保存设置时调用。"""
    user_id = _user_id()
    data = request.get_json(silent=True) or {}

    cfg = RdModelConfig.query.filter_by(user_id=user_id).first()
    if not cfg:
        cfg = RdModelConfig(user_id=user_id)
        db.session.add(cfg)

    api_key = data.get('api_key')
    if api_key and '****' not in str(api_key):
        cfg.api_key = api_key

    for field in ('base_url', 'model', 'custom_model', 'temperature', 'max_tokens'):
        if field in data and data[field] is not None:
            setattr(cfg, field, data[field])

    db.session.commit()
    return _ok(cfg.to_dict(), '模型配置已同步')


# ══════════════════════════════════════════════════════════════
#  审查 CRUD
# ══════════════════════════════════════════════════════════════

@review_bp.route('/api/rd/projects/<project_id>/reviews', methods=['GET'])
@jwt_required()
def list_reviews(project_id):
    status = request.args.get('status')
    language = request.args.get('language')
    items = review_service.list_reviews(project_id, status=status, language=language)
    return _ok({'items': items, 'total': len(items)})


@review_bp.route('/api/rd/projects/<project_id>/reviews', methods=['POST'])
@jwt_required()
def create_review(project_id):
    data = request.get_json(silent=True) or {}
    review_type = data.get('review_type', 'file')  # 'file' | 'commit'
    language = data.get('language', '')

    # ── 提交审查 (diff 模式) ──
    if review_type == 'commit':
        diff_content = (data.get('diff_content') or '').strip()
        if not diff_content:
            return _error('请提供代码 diff 内容')
        file_paths = data.get('file_paths', [])
        diff_files = data.get('diff_files', [])
        code_content = diff_content
        # 用 diff 文件列表作为 file_paths
        if not file_paths:
            file_paths = [f['filename'] for f in diff_files]
        return _do_review(data, project_id, review_type, code_content, language, file_paths)

    # ── 文件审查 (文件内容 / 粘贴代码) ──
    code_content = (data.get('code_content') or '').strip()
    if not code_content:
        return _error('请提供代码内容（粘贴代码或选择仓库文件）')
    file_paths = data.get('file_paths', [])
    return _do_review(data, project_id, review_type, code_content, language, file_paths)


@review_bp.route('/api/rd/reviews/<review_id>', methods=['GET'])
@jwt_required()
def get_review(review_id):
    r = review_service.get_review(review_id)
    if not r:
        return _error('审查不存在', 404)
    return _ok(r)


@review_bp.route('/api/rd/reviews/<review_id>', methods=['DELETE'])
@jwt_required()
def delete_review(review_id):
    ok = review_service.delete_review(review_id)
    if not ok:
        return _error('审查不存在', 404)
    return _ok(msg='已删除')


@review_bp.route('/api/rd/reviews/<review_id>/retry', methods=['POST'])
@jwt_required()
def retry_review(review_id):
    """重新触发审查（默认使用脚本审查）."""
    r = review_service.get_review(review_id)
    if not r:
        return _error('审查不存在', 404)

    # 默认使用脚本审查重新执行
    result = script_review_engine.review(
        r.get('code_content', ''),
        language=r.get('language', ''),
        file_paths=r.get('file_paths', []),
    )

    updated = review_service.update_review(review_id, {
        'overall_score': result.overall_score,
        'scores': result.scores,
        'summary': result.summary,
        'status': 'completed',
        'issues': result.issues,
    })
    return _ok(updated, '重新审查完成')


@review_bp.route('/api/rd/reviews/<review_id>/auto-fix', methods=['POST'])
@jwt_required()
def auto_fix_review(review_id):
    """一键修复：基于 fixed_snippet 创建 GitHub 分支."""
    r = review_service.get_review(review_id)
    if not r:
        return _error('审查不存在', 404)

    repo_id = r.get('repo_id')
    if not repo_id:
        return _error('该审查未关联仓库，无法自动修复')

    # 获取仓库信息和 GitHub 服务
    from services.repo_service import repo_service
    from services.github_service import GitHubService, decrypt_token
    from models.repo import RdGithubToken

    repo = repo_service.get_repo(repo_id)
    if not repo:
        return _error('关联仓库不存在', 404)

    token_entry = RdGithubToken.query.filter_by(user_id=_user_id()).first()
    if not token_entry:
        return _error('未连接 GitHub，请先授权', 400)

    gh = GitHubService(decrypt_token(token_entry.access_token))

    # 创建 fix 分支
    base_branch = r.get('branch') or repo.get('default_branch', 'main')
    fix_branch = f"fix/review-{review_id.replace('-', '')[:8]}"
    try:
        gh.create_branch(repo['owner'], repo['repo_name'], fix_branch, base_branch)
    except Exception as e:
        return _error(f'创建修复分支失败: {str(e)}')

    return _ok({
        'branch_name': fix_branch,
        'owner': repo['owner'],
        'repo_name': repo['repo_name'],
        'html_url': f"https://github.com/{repo['owner']}/{repo['repo_name']}/tree/{fix_branch}",
    }, '修复分支已创建')


# ══════════════════════════════════════════════════════════════
#  Issue 管理
# ══════════════════════════════════════════════════════════════

@review_bp.route('/api/rd/reviews/<review_id>/issues/<issue_id>', methods=['PATCH'])
@jwt_required()
def update_issue(review_id, issue_id):
    data = request.get_json(silent=True) or {}
    result = review_service.update_issue(issue_id, data)
    if not result:
        return _error('问题不存在', 404)
    return _ok(result, '已更新')
