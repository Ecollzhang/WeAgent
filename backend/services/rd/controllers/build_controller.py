"""构建管理 API."""
import time
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from services.build_service import build_service
from services.github_service import GitHubService, decrypt_token
from models.repo import RdRepo, RdGithubToken

build_bp = Blueprint('rd_builds', __name__)


def _user_id():
    return get_jwt_identity()


def _ok(data=None, msg='ok', code=200):
    return jsonify({'code': code, 'message': msg, 'data': data or {}}), code


def _error(msg, code=400):
    return jsonify({'code': code, 'message': msg}), code


def _get_gh(user_id):
    """获取用户的 GitHubService 实例."""
    token_entry = RdGithubToken.query.filter_by(user_id=user_id).first()
    if not token_entry:
        return None
    return GitHubService(decrypt_token(token_entry.access_token))


def _get_repo(repo_id):
    """获取仓库记录."""
    return RdRepo.query.filter_by(id=repo_id).first()


# ══════════════════════════════════════════════════════════════
#  构建 CRUD
# ══════════════════════════════════════════════════════════════

@build_bp.route('/api/rd/projects/<project_id>/builds', methods=['GET'])
@jwt_required()
def list_builds(project_id):
    status = request.args.get('status')
    branch = request.args.get('branch')
    items = build_service.list_builds(project_id, status=status, branch=branch)
    return _ok({'items': items, 'total': len(items)})


@build_bp.route('/api/rd/projects/<project_id>/builds', methods=['POST'])
@jwt_required()
def create_build(project_id):
    """创建构建记录（模拟模式）或触发 GitHub Actions 构建."""
    data = request.get_json(silent=True) or {}

    # 如果提供了 repo_id，走 GitHub Actions 真实构建流程
    repo_id = data.get('repo_id')
    if repo_id:
        return _trigger_github_build(project_id, repo_id, data)

    # 否则走模拟/手动模式
    build = build_service.create_build(project_id, data, user_id=_user_id())
    return _ok(build, '构建已创建', 201)


@build_bp.route('/api/rd/builds/<build_id>', methods=['GET'])
@jwt_required()
def get_build(build_id):
    b = build_service.get_build(build_id)
    if not b:
        return _error('构建不存在', 404)
    return _ok(b)


@build_bp.route('/api/rd/builds/<build_id>', methods=['PUT'])
@jwt_required()
def update_build(build_id):
    """更新构建状态（模拟构建流程使用）."""
    data = request.get_json(silent=True) or {}
    b = build_service.update_build(build_id, data)
    if not b:
        return _error('构建不存在', 404)
    return _ok(b, '已更新')


@build_bp.route('/api/rd/builds/<build_id>/log', methods=['GET'])
@jwt_required()
def get_build_log(build_id):
    step_order = request.args.get('step_order', type=int)
    log = build_service.get_build_log(build_id, step_order=step_order)
    if not log:
        return _error('构建不存在', 404)
    return _ok(log)


@build_bp.route('/api/rd/builds/<build_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_build(build_id):
    b = build_service.get_build(build_id)
    if not b:
        return _error('构建不存在', 404)
    # 如果有 GitHub run，尝试取消
    if b.get('github_run_id') and b.get('repo_id'):
        repo = _get_repo(b['repo_id'])
        if repo:
            gh = _get_gh(_user_id())
            if gh:
                try:
                    gh.cancel_run(repo.owner, repo.repo_name, b['github_run_id'])
                except Exception:
                    pass  # 取消失败也继续更新本地状态
    result = build_service.cancel_build(build_id)
    if not result:
        return _error('构建不存在或状态不允许取消', 400)
    return _ok(result, '已取消')


@build_bp.route('/api/rd/builds/<build_id>/artifacts', methods=['GET'])
@jwt_required()
def get_build_artifacts(build_id):
    data = build_service.get_artifacts(build_id)
    if not data:
        return _error('构建不存在', 404)
    return _ok(data)


@build_bp.route('/api/rd/builds/<build_id>/artifacts/<artifact_id>/download', methods=['GET'])
@jwt_required()
def download_artifact(build_id, artifact_id):
    """代理下载 GitHub Actions artifact — 返回重定向 URL."""
    b = build_service.get_build(build_id)
    if not b:
        return _error('构建不存在', 404)

    repo_id = b.get('repo_id')
    if not repo_id:
        return _error('构建未关联仓库', 400)

    repo = _get_repo(repo_id)
    if not repo:
        return _error('关联仓库不存在', 404)

    gh = _get_gh(_user_id())
    if not gh:
        return _error('未授权 GitHub', 401)

    try:
        url = gh.get_artifact_download_url(repo.owner, repo.repo_name, artifact_id)
        return redirect(url)
    except Exception as e:
        return _error(f'获取下载链接失败: {str(e)}', 500)


@build_bp.route('/api/rd/builds/<build_id>', methods=['DELETE'])
@jwt_required()
def delete_build(build_id):
    ok = build_service.delete_build(build_id)
    if not ok:
        return _error('构建不存在', 404)
    return _ok(msg='已删除')


# ══════════════════════════════════════════════════════════════
#  GitHub Actions 集成
# ══════════════════════════════════════════════════════════════

@build_bp.route('/api/rd/repos/<repo_id>/workflows', methods=['GET'])
@jwt_required()
def list_workflows(repo_id):
    """列出仓库可用的 GitHub Actions workflows."""
    repo = _get_repo(repo_id)
    if not repo:
        return _error('仓库不存在', 404)

    gh = _get_gh(_user_id())
    if not gh:
        return _error('未授权 GitHub，请先绑定 GitHub 账号', 401)

    try:
        workflows = gh.list_workflows(repo.owner, repo.repo_name)
        result = []
        for w in workflows:
            result.append({
                'id': w['id'],
                'name': w['name'],
                'path': w['path'],
                'state': w.get('state', 'active'),
                'html_url': w.get('html_url', ''),
            })
        return _ok({'items': result, 'total': len(result)})
    except Exception as e:
        return _error(f'获取 workflows 失败: {str(e)}', 500)


@build_bp.route('/api/rd/builds/<build_id>/sync', methods=['POST'])
@jwt_required()
def sync_build(build_id):
    """从 GitHub 同步构建状态."""
    b = build_service.get_build(build_id)
    if not b:
        return _error('构建不存在', 404)

    github_run_id = b.get('github_run_id')
    repo_id = b.get('repo_id')
    if not github_run_id or not repo_id:
        return _error('该构建未关联 GitHub Actions', 400)

    repo = _get_repo(repo_id)
    if not repo:
        return _error('关联仓库不存在', 404)

    gh = _get_gh(_user_id())
    if not gh:
        return _error('未授权 GitHub', 401)

    try:
        # 获取 run 详情
        run = gh.get_run(repo.owner, repo.repo_name, github_run_id)
        # 获取 jobs
        jobs = gh.get_run_jobs(repo.owner, repo.repo_name, github_run_id)

        # 映射状态
        status_map = {
            'queued': 'pending',
            'in_progress': 'running',
            'completed': 'success' if run.get('conclusion') == 'success' else 'failed',
            'waiting': 'pending',
            'pending': 'pending',
        }
        gh_status = run.get('status', '')
        new_status = status_map.get(gh_status, 'pending')

        if run.get('conclusion') == 'cancelled':
            new_status = 'cancelled'

        # 转换 steps
        steps = []
        for job in jobs:
            status = 'pending'
            if job.get('conclusion') == 'success':
                status = 'success'
            elif job.get('conclusion') == 'failure':
                status = 'failed'
            elif job.get('conclusion') == 'skipped':
                status = 'skipped'
            elif job.get('status') == 'in_progress':
                status = 'running'

            started = job.get('started_at')
            completed = job.get('completed_at')
            duration = None
            if started and completed:
                from datetime import datetime
                try:
                    s = datetime.fromisoformat(started.replace('Z', '+00:00'))
                    e = datetime.fromisoformat(completed.replace('Z', '+00:00'))
                    duration = int((e - s).total_seconds())
                except Exception:
                    pass

            # 获取 job 日志
            log_text = None
            try:
                log_text = gh.get_job_logs(repo.owner, repo.repo_name, job['id'])
                # 截断过长日志
                if len(log_text) > 10000:
                    log_text = log_text[:10000] + '\n... (日志过长，已截断)'
            except Exception:
                pass

            steps.append({
                'step_name': job.get('name', f'Job #{job.get("id")}'),
                'step_order': job.get('run_attempt', 1),
                'status': status,
                'command': f'GitHub Actions Job: {job.get("html_url", "")}',
                'duration_seconds': duration,
                'log': log_text,
            })

        # 计算总耗时
        total_duration = sum(s['duration_seconds'] for s in steps if s['duration_seconds'])

        # 提取 artifacts（含 ID 用于下载）
        artifacts = []
        try:
            arts = gh.list_run_artifacts(repo.owner, repo.repo_name, github_run_id)
            artifacts = [{
                'id': a.get('id'),
                'name': a.get('name', ''),
                'size_bytes': a.get('size_in_bytes', 0),
            } for a in arts]
        except Exception:
            pass

        update_data = {
            'status': new_status,
            'duration_seconds': total_duration or None,
            'error_summary': None,
            'steps': steps,
            'artifacts': artifacts or b.get('artifacts', []),
            'commit_hash': run.get('head_sha', b.get('commit_hash')),
            'commit_message': run.get('head_commit', {}).get('message', b.get('commit_message')),
            'branch': run.get('head_branch', b.get('branch')),
            'preview_url': run.get('html_url', b.get('preview_url')),
        }

        if new_status == 'failed':
            # 找到第一个失败的 step
            failed = next((s for s in steps if s['status'] == 'failed'), None)
            update_data['error_summary'] = (
                f'Job "{failed["step_name"]}" 执行失败'
                if failed else '构建失败，请查看 GitHub Actions 日志'
            )

        updated = build_service.update_build(build_id, update_data)
        return _ok(updated, '已同步')
    except Exception as e:
        return _error(f'同步失败: {str(e)}', 500)


@build_bp.route('/api/rd/projects/<project_id>/repos-for-build', methods=['GET'])
@jwt_required()
def list_repos_for_build(project_id):
    """列出项目下可用于构建的仓库列表（含 workflows 数量）."""
    repos = RdRepo.query.filter_by(project_id=project_id, status='active').all()
    gh = _get_gh(_user_id())

    result = []
    for repo in repos:
        item = repo.to_dict()
        item['workflow_count'] = 0
        if gh:
            try:
                workflows = gh.list_workflows(repo.owner, repo.repo_name)
                item['workflow_count'] = len(workflows)
            except Exception:
                pass
        result.append(item)

    return _ok({'items': result, 'total': len(result)})


# ══════════════════════════════════════════════════════════════
#  内部辅助
# ══════════════════════════════════════════════════════════════

def _trigger_github_build(project_id, repo_id, data):
    """触发 GitHub Actions 构建并创建本地记录."""
    repo = _get_repo(repo_id)
    if not repo:
        return _error('仓库不存在', 404)

    uid = _user_id()
    gh = _get_gh(uid)
    if not gh:
        return _error('未授权 GitHub，请先绑定 GitHub 账号', 401)

    workflow_id = data.get('workflow_id', '')
    branch = data.get('branch', repo.default_branch or 'main')
    inputs = data.get('inputs', None)

    if not workflow_id:
        return _error('请选择 workflow', 400)

    try:
        # 1. 触发 workflow
        gh.dispatch_workflow(repo.owner, repo.repo_name, workflow_id, branch, inputs)

        # 2. 等待并查找新创建的 run（GitHub dispatch 不返回 run ID）
        time.sleep(2)
        runs = gh.get_workflow_runs(
            repo.owner, repo.repo_name, workflow_id,
            per_page=3, branch=branch,
        )

        github_run_id = None
        if runs:
            # 取最新的 run
            github_run_id = runs[0]['id']

        # 3. 创建本地构建记录
        build_data = {
            'build_type': 'manual',
            'status': 'running',
            'branch': branch,
            'commit_hash': None,
            'commit_message': data.get('commit_message', f'手动触发: {repo.full_name} / {workflow_id}'),
            'repo_id': repo_id,
            'workflow_id': str(workflow_id),
            'github_run_id': github_run_id,
            'steps': [],
        }

        build = build_service.create_build(project_id, build_data, user_id=uid)

        # 确保关键字段已持久化（create_build 内部也会设置，此处为保险）
        build_service.update_build(build['id'], {
            'repo_id': repo_id,
            'workflow_id': str(workflow_id),
            'github_run_id': github_run_id,
        })

        # 4. 如果有 run ID，尝试立即同步一次
        if github_run_id:
            try:
                run = gh.get_run(repo.owner, repo.repo_name, github_run_id)
                build['github_run_url'] = run.get('html_url', '')
                build_service.update_build(build['id'], {
                    'preview_url': run.get('html_url', ''),
                    'commit_hash': run.get('head_sha'),
                    'commit_message': run.get('head_commit', {}).get('message', build_data['commit_message']),
                })
                build = build_service.get_build(build['id'])
            except Exception:
                pass

        return _ok(build, '构建已触发', 201)
    except Exception as e:
        return _error(f'触发构建失败: {str(e)}', 500)
