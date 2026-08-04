"""GitHub API 服务 — OAuth + REST API 封装."""
import base64
import requests
from flask import current_app, request


GITHUB_API = 'https://api.github.com'
GITHUB_OAUTH = 'https://github.com'


class GitHubService:
    """封装 GitHub REST API，通过用户 token 访问仓库数据."""

    def __init__(self, access_token=None):
        self.token = access_token

    @property
    def _headers(self):
        h = {
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
        }
        if self.token:
            h['Authorization'] = f'Bearer {self.token}'
        return h

    def _get(self, path, params=None):
        r = requests.get(f'{GITHUB_API}{path}', headers=self._headers,
                         params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def _post(self, path, json=None):
        r = requests.post(f'{GITHUB_API}{path}', headers=self._headers,
                          json=json, timeout=30)
        r.raise_for_status()
        return r.json()

    def _delete(self, path):
        r = requests.delete(f'{GITHUB_API}{path}', headers=self._headers,
                            timeout=30)
        if r.status_code != 204:
            r.raise_for_status()

    # ── OAuth ──────────────────────────────────────────────

    @staticmethod
    def get_auth_url(client_id, redirect_uri):
        """生成 GitHub OAuth 授权 URL."""
        return (
            f'{GITHUB_OAUTH}/login/oauth/authorize'
            f'?client_id={client_id}'
            f'&redirect_uri={redirect_uri}'
            f'&scope=repo,read:org'
        )

    @staticmethod
    def exchange_token(code, client_id, client_secret):
        """用 authorization code 换取 access token."""
        r = requests.post(
            f'{GITHUB_OAUTH}/login/oauth/access_token',
            json={
                'client_id': client_id,
                'client_secret': client_secret,
                'code': code,
            },
            headers={'Accept': 'application/json'},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        if 'error' in data:
            raise ValueError(data.get('error_description', data['error']))
        return data  # { access_token, token_type, scope }

    # ── 用户 ───────────────────────────────────────────────

    def get_user(self):
        """获取当前授权用户信息."""
        return self._get('/user')

    # ── 仓库 ───────────────────────────────────────────────

    def list_user_repos(self, page=1, per_page=100):
        """获取用户有权限的所有仓库."""
        return self._get('/user/repos', {
            'per_page': per_page,
            'page': page,
            'sort': 'updated',
            'type': 'owner',
        })

    def get_repo(self, owner, repo):
        """获取单个仓库信息."""
        return self._get(f'/repos/{owner}/{repo}')

    # ── 分支 ───────────────────────────────────────────────

    def list_branches(self, owner, repo):
        return self._get(f'/repos/{owner}/{repo}/branches')

    def get_branch(self, owner, repo, branch):
        return self._get(f'/repos/{owner}/{repo}/branches/{branch}')

    def create_branch(self, owner, repo, name, from_branch='main'):
        """创建分支：先拿 from_branch 的 SHA，再创建."""
        base = self.get_branch(owner, repo, from_branch)
        sha = base['commit']['sha']
        return self._post(f'/repos/{owner}/{repo}/git/refs', {
            'ref': f'refs/heads/{name}',
            'sha': sha,
        })

    # ── 提交记录 ───────────────────────────────────────────

    def list_commits(self, owner, repo, branch='main', per_page=30):
        return self._get(f'/repos/{owner}/{repo}/commits', {
            'sha': branch,
            'per_page': per_page,
        })

    def get_commit(self, owner, repo, sha):
        return self._get(f'/repos/{owner}/{repo}/commits/{sha}')

    # ── 文件树 ─────────────────────────────────────────────

    def get_tree(self, owner, repo, branch='main', path=''):
        """递归获取文件树."""
        if path:
            return self._get(f'/repos/{owner}/{repo}/contents/{path}', {
                'ref': branch,
            })
        branch_data = self.get_branch(owner, repo, branch)
        tree_sha = branch_data['commit']['commit']['tree']['sha']
        resp = requests.get(
            f'{GITHUB_API}/repos/{owner}/{repo}/git/trees/{tree_sha}',
            headers=self._headers,
            params={'recursive': '1'},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get('tree', [])

    # ── 文件内容 ───────────────────────────────────────────

    def get_file_content(self, owner, repo, path, branch='main'):
        resp = requests.get(
            f'{GITHUB_API}/repos/{owner}/{repo}/contents/{path}',
            headers=self._headers,
            params={'ref': branch},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data  # 目录列表
        if data.get('encoding') == 'base64':
            content = data.get('content', '')
            # GitHub 返回的 base64 可能有换行符
            return base64.b64decode(content).decode('utf-8', errors='replace')
        return None

    # ── Pull Request ───────────────────────────────────────

    def list_pull_requests(self, owner, repo, state='open'):
        return self._get(f'/repos/{owner}/{repo}/pulls', {'state': state})

    # ── GitHub Actions ─────────────────────────────────────

    def _get_text(self, path, params=None):
        """GET 请求，返回纯文本（用于日志等非 JSON 响应）."""
        r = requests.get(f'{GITHUB_API}{path}', headers=self._headers,
                         params=params, timeout=30)
        r.raise_for_status()
        return r.text

    def list_workflows(self, owner, repo):
        """列出仓库的 GitHub Actions workflow."""
        data = self._get(f'/repos/{owner}/{repo}/actions/workflows')
        return data.get('workflows', [])

    def get_workflow(self, owner, repo, workflow_id):
        """获取单个 workflow 详情."""
        return self._get(f'/repos/{owner}/{repo}/actions/workflows/{workflow_id}')

    def dispatch_workflow(self, owner, repo, workflow_id, ref, inputs=None):
        """触发 workflow_dispatch 事件."""
        body = {'ref': ref}
        if inputs:
            body['inputs'] = inputs
        r = requests.post(
            f'{GITHUB_API}/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches',
            headers=self._headers,
            json=body,
            timeout=30,
        )
        if r.status_code != 204:
            r.raise_for_status()

    def get_workflow_runs(self, owner, repo, workflow_id, per_page=10, branch=None, status=None):
        """获取 workflow 的运行历史."""
        params = {'per_page': per_page}
        if branch:
            params['branch'] = branch
        if status:
            params['status'] = status
        data = self._get(
            f'/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs',
            params,
        )
        return data.get('workflow_runs', [])

    def get_run(self, owner, repo, run_id):
        """获取单个 workflow run 详情."""
        return self._get(f'/repos/{owner}/{repo}/actions/runs/{run_id}')

    def get_run_jobs(self, owner, repo, run_id):
        """获取 workflow run 的 jobs 列表."""
        data = self._get(f'/repos/{owner}/{repo}/actions/runs/{run_id}/jobs')
        return data.get('jobs', [])

    def get_job_logs(self, owner, repo, job_id):
        """获取 job 的日志（纯文本）."""
        return self._get_text(f'/repos/{owner}/{repo}/actions/jobs/{job_id}/logs')

    def list_run_artifacts(self, owner, repo, run_id):
        """获取 workflow run 的 artifacts 列表."""
        data = self._get(f'/repos/{owner}/{repo}/actions/runs/{run_id}/artifacts')
        return data.get('artifacts', [])

    def cancel_run(self, owner, repo, run_id):
        """取消正在运行的 workflow run."""
        r = requests.post(
            f'{GITHUB_API}/repos/{owner}/{repo}/actions/runs/{run_id}/cancel',
            headers=self._headers,
            timeout=30,
        )
        if r.status_code not in (202, 200):
            r.raise_for_status()
        return r.json() if r.text else {}

    def get_artifact_download_url(self, owner, repo, artifact_id):
        """获取 artifact 的下载 URL（GitHub 返回 302 重定向）."""
        r = requests.get(
            f'{GITHUB_API}/repos/{owner}/{repo}/actions/artifacts/{artifact_id}/zip',
            headers=self._headers,
            allow_redirects=False,
            timeout=30,
        )
        if r.status_code in (302, 301, 307, 308):
            return r.headers.get('Location', '')
        r.raise_for_status()
        # fallback: follow redirect and return final URL
        r2 = requests.get(
            f'{GITHUB_API}/repos/{owner}/{repo}/actions/artifacts/{artifact_id}/zip',
            headers=self._headers,
            timeout=30,
        )
        return r2.url


# ── Token 编解码工具 ───────────────────────────────────────

def _derive_key():
    """从 SECRET_KEY 派生 Fernet 兼容的 key."""
    from cryptography.fernet import Fernet
    import hashlib
    secret = current_app.config.get('SECRET_KEY', 'fallback-key').encode()
    return base64.urlsafe_b64encode(hashlib.sha256(secret).digest())


def encrypt_token(plain: str) -> str:
    from cryptography.fernet import Fernet
    f = Fernet(_derive_key())
    return f.encrypt(plain.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    from cryptography.fernet import Fernet
    f = Fernet(_derive_key())
    return f.decrypt(encrypted.encode()).decode()
