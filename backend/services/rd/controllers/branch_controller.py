"""分支管理 API."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from services.branch_service import branch_service
from services.repo_service import repo_service
from services.github_service import GitHubService, decrypt_token
from models.repo import RdGithubToken

branch_bp = Blueprint('rd_branches', __name__)


def _get_user_id():
    return get_jwt_identity()


def _error(msg, code=400):
    return jsonify({'code': code, 'message': msg}), code


def _ok(data, msg='ok', code=200):
    return jsonify({'code': code, 'message': msg, 'data': data}), code


def _get_github_service_for_user(user_id):
    """获取用户的 GitHubService 实例，未授权返回 None."""
    token_entry = RdGithubToken.query.filter_by(user_id=user_id).first()
    if not token_entry:
        return None
    return GitHubService(decrypt_token(token_entry.access_token))


@branch_bp.route('/api/rd/projects/<project_id>/branches', methods=['GET'])
@jwt_required()
def list_branches(project_id):
    source_type = request.args.get('source_type')
    source_id = request.args.get('source_id')
    result = branch_service.list_branches(project_id, source_type, source_id)
    return _ok({'items': result, 'total': len(result)})


@branch_bp.route('/api/rd/projects/<project_id>/branches', methods=['POST'])
@jwt_required()
def create_branch(project_id):
    data = request.get_json(silent=True) or {}
    if not data.get('source_type') or not data.get('source_id'):
        return _error('source_type 和 source_id 不能为空')
    if data.get('source_type') not in ('requirement', 'bug'):
        return _error('source_type 必须为 requirement 或 bug')

    # 如果指定了仓库，先在 GitHub 上创建远程分支
    repo_id = data.get('repo_id')
    if repo_id:
        repo = repo_service.get_repo(repo_id)
        if not repo:
            return _error('仓库不存在', 404)

        gh = _get_github_service_for_user(_get_user_id())
        if not gh:
            return _error('未连接 GitHub，请先在项目设置中授权', 400)

        branch_name = data.get('branch_name', '').strip()
        if not branch_name:
            branch_name = branch_service._generate_branch_name(
                data['source_type'], data['source_id']
            )
            if not branch_name:
                return _error('无法自动生成分支名')
            data['branch_name'] = branch_name

        base_branch = data.get('base_branch', repo.get('default_branch', 'main'))
        try:
            gh.create_branch(repo['owner'], repo['repo_name'], branch_name, base_branch)
        except Exception as e:
            return _error(f'GitHub 创建远程分支失败: {str(e)}')

    result, err = branch_service.create_branch(project_id, data, user_id=_get_user_id())
    if err:
        return _error(err)
    return _ok(result, '分支创建成功', 201)


@branch_bp.route('/api/rd/projects/<project_id>/branches/<branch_id>', methods=['PUT'])
@jwt_required()
def update_branch(project_id, branch_id):
    data = request.get_json(silent=True) or {}
    result = branch_service.update_branch(branch_id, data, user_id=_get_user_id())
    if not result:
        return _error('分支不存在', 404)
    return _ok(result, '分支更新成功')


@branch_bp.route('/api/rd/projects/<project_id>/branches/<branch_id>', methods=['DELETE'])
@jwt_required()
def delete_branch(project_id, branch_id):
    ok = branch_service.delete_branch(branch_id, user_id=_get_user_id())
    if not ok:
        return _error('分支不存在', 404)
    return _ok({'id': branch_id}, '分支已删除')
