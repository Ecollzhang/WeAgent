"""AI 代码审查引擎 — 结构化 prompt + LLM 调用."""
import json
import re
import os
import logging
import requests

logger = logging.getLogger(__name__)


class ReviewResult:
    """审查结果数据结构."""
    def __init__(self, overall_score=0, summary='', scores=None, issues=None):
        self.overall_score = overall_score
        self.summary = summary
        self.scores = scores or {'security': 0, 'style': 0, 'logic': 0, 'performance': 0}
        self.issues = issues or []


def _get_llm_config(user_id=None):
    """获取 LLM 配置：优先从本地 rd_model_configs 读取，否则回退到环境变量.

    返回的 config 包含：
    - api_key: API 密钥
    - model: 模型名称
    - openai_url: OpenAI 兼容端点 (chat/completions)
    - anthropic_url: Anthropic 兼容端点 (v1/messages)，仅当原始 base_url 以 /anthropic 结尾时可用
    - base_url: 原始 base_url，用于诊断
    """
    def _build(api_key, base_url, model):
        raw_url = (base_url or '').strip().strip('\'"').rstrip('/')
        anthropic_url = ''
        if raw_url.endswith('/anthropic'):
            anthropic_url = raw_url
            openai_url = raw_url[:-len('/anthropic')] + '/v1'
        else:
            openai_url = raw_url or 'https://api.openai.com/v1'
        return {
            'api_key': api_key,
            'model': model,
            'openai_url': openai_url,
            'anthropic_url': anthropic_url,
            'base_url': raw_url,
        }

    if user_id:
        try:
            from models.rd_model_config import RdModelConfig
            cfg = RdModelConfig.query.filter_by(user_id=user_id).first()
            if cfg and cfg.api_key:
                model = cfg.custom_model if (cfg.model == 'custom' and cfg.custom_model) else (cfg.model or 'gpt-4o')
                logger.info(f"LLM config sourced from RdModelConfig for user={user_id}, model={model}, base_url={cfg.base_url}")
                return _build(cfg.api_key, cfg.base_url, model)
        except Exception as e:
            logger.warning(f"RdModelConfig lookup failed: {e}")

        try:
            from app.models.user_model_config import UserModelConfig
            cfg = UserModelConfig.query.filter_by(user_id=user_id).first()
            if cfg and cfg.api_key:
                try:
                    _sync_config_to_local(user_id, cfg)
                except Exception as e:
                    logger.warning(f"Auto-sync to local table failed: {e}")
                model = cfg.custom_model if (cfg.model == 'custom' and cfg.custom_model) else (cfg.model or 'gpt-4o')
                logger.info(f"LLM config sourced from UserModelConfig (auto-synced) for user={user_id}, model={model}")
                return _build(cfg.api_key, cfg.base_url, model)
        except Exception as e:
            logger.warning(f"UserModelConfig fallback lookup failed: {e}")

    api_key = os.getenv('LLM_API_KEY', os.getenv('OPENAI_API_KEY', ''))
    model = os.getenv('LLM_MODEL', 'gpt-4o')
    base_url = os.getenv('LLM_BASE_URL', 'https://api.openai.com/v1')
    logger.info(f"LLM config sourced from env vars (no user config found for user={user_id}). api_key set: {bool(api_key)}")
    return _build(api_key, base_url, model)


def _sync_config_to_local(user_id, cfg):
    """将主数据库的模型配置同步到 RD 本地表."""
    from models.rd_model_config import RdModelConfig
    from database import db as rd_db
    import uuid
    local = RdModelConfig.query.filter_by(user_id=user_id).first()
    if not local:
        local = RdModelConfig(user_id=user_id)
        local.id = str(uuid.uuid4())
        rd_db.session.add(local)
    local.api_key = (cfg.api_key or '').strip().strip('\'"')
    local.base_url = (cfg.base_url or '').strip().strip('\'"')
    local.model = cfg.model or 'gpt-4o'
    local.custom_model = cfg.custom_model or ''
    local.temperature = cfg.temperature or 0.7
    local.max_tokens = cfg.max_tokens or 4096
    rd_db.session.commit()


REVIEW_SYSTEM_PROMPT = """你是一位资深代码审查专家。请从以下四个维度审查代码，并返回严格的 JSON 结果。

## 审查维度

1. **security (安全)**：检查 OWASP Top 10 漏洞、注入攻击（SQL/XSS/命令注入）、敏感信息泄露、不安全的加密、权限绕过、CSRF、路径遍历等
2. **style (规范)**：检查命名规范、代码结构、DRY 原则、注释质量、函数长度、圈复杂度、类型安全等
3. **logic (逻辑)**：检查边界条件、空值/undefined 处理、异常处理、死代码、竞态条件、错误的业务逻辑、类型错误等
4. **performance (性能)**：检查 N+1 查询、内存泄漏、不必要的循环/递归、大对象拷贝、DOM 操作频率、缓存缺失等

## 输出格式

必须返回严格的 JSON，不要带 markdown 代码块标记，直接返回 JSON 对象：

{
  "overall_score": 7.5,
  "summary": "代码整体质量总结，2-4句话概括主要发现",
  "scores": {
    "security": 6.0,
    "style": 7.5,
    "logic": 8.0,
    "performance": 8.5
  },
  "issues": [
    {
      "severity": "critical",
      "category": "security",
      "title": "问题简短标题",
      "description": "问题的详细描述，说明为什么这是一个问题",
      "suggestion": "具体的修复建议",
      "line_start": 42,
      "code_snippet": "有问题的代码片段",
      "fixed_snippet": "修复后的代码片段"
    }
  ]
}

## 规则

- severity 必须是 critical / warning / suggestion
- category 必须是 security / style / logic / performance
- overall_score 和各维度评分范围 0-10
- 只报告真正存在的问题，不要吹毛求疵
- 如果没有发现问题，issues 为空数组
- line_start 是可选的，如果无法确定行号可以不填
- code_snippet 和 fixed_snippet 尽量提供，展示问题代码和修复方案"""


REVIEW_DIFF_SYSTEM_PROMPT = """你是一位资深代码审查专家，专门审查 git diff（代码变更差异）。请从以下四个维度审查本次提交的代码变更，并返回严格的 JSON 结果。

## 审查维度

1. **security (安全)**：变更是否引入 OWASP Top 10 漏洞、注入攻击（SQL/XSS/命令注入）、敏感信息泄露、不安全的加密、权限绕过、CSRF、路径遍历等
2. **style (规范)**：变更是否符合编码规范、命名是否清晰、结构是否合理、是否有不必要的嵌套
3. **logic (逻辑)**：变更是否引入边界条件问题、空值/undefined 处理、异常处理缺失、死代码、竞态条件、错误的业务逻辑
4. **performance (性能)**：变更是否引入 N+1 查询、内存泄漏、不必要的循环/递归、大对象拷贝、缓存缺失等

## 审查重点

- **只审查变更部分（diff 中的 + 行和上下文），不要审查未变更的代码**
- 关注新增代码中可能存在的问题
- 关注删除代码是否可能破坏现有功能
- 如果 diff 较大，聚焦最关键的几个问题

## 输出格式

必须返回严格的 JSON，不要带 markdown 代码块标记：

{
  "overall_score": 7.5,
  "summary": "本次提交代码整体质量总结，2-4句话概括主要发现",
  "scores": {
    "security": 6.0,
    "style": 7.5,
    "logic": 8.0,
    "performance": 8.5
  },
  "issues": [
    {
      "severity": "critical",
      "category": "security",
      "title": "问题简短标题",
      "description": "问题的详细描述，说明为什么这是一个问题",
      "suggestion": "具体的修复建议",
      "line_start": null,
      "code_snippet": "有问题的代码片段（从 diff 中提取）",
      "fixed_snippet": "修复后的代码片段"
    }
  ]
}

## 规则

- severity 必须是 critical / warning / suggestion
- category 必须是 security / style / logic / performance
- overall_score 和各维度评分范围 0-10
- 只报告真正存在的问题，不要吹毛求疵
- 如果没有发现问题，issues 为空数组
- code_snippet 和 fixed_snippet 尽量提供"""


class ReviewEngine:
    """AI 代码审查引擎."""

    def review_code(self, code, language='', file_paths=None, context=None, user_id=None):
        """
        提交代码进行审查。

        Args:
            code: 被审查的代码内容
            language: 编程语言
            file_paths: 文件路径列表
            context: 额外上下文（如项目描述）
            user_id: 用户ID，用于读取用户配置的模型和 API Key

        Returns:
            ReviewResult
        """
        cfg = _get_llm_config(user_id)
        if not cfg['api_key']:
            return ReviewResult(
                overall_score=0,
                summary='AI 审查未配置：请在"设置 → 模型设置"中配置 API Key 和模型',
                issues=[]
            )

        # 构造 user prompt
        parts = [f"请审查以下 {language} 代码" if language else "请审查以下代码"]
        if file_paths:
            parts.append(f"文件：{', '.join(file_paths)}")
        if context:
            parts.append(f"背景：{context}")
        parts.append(f"\n```{language or ''}\n{code}\n```")

        user_prompt = '\n'.join(parts)
        return self._do_review(cfg, user_prompt)

    def review_diff(self, diff_content, commit_info=None, file_list=None, language='', context=None, user_id=None):
        """
        审查 git diff（代码变更差异）。

        Args:
            diff_content: unified diff 格式的代码变更
            commit_info: dict with sha, message, author, date
            file_list: 变更文件列表 [{'filename', 'status', 'additions', 'deletions'}]
            language: 编程语言
            context: 额外上下文
            user_id: 用户ID，用于读取用户配置的模型和 API Key

        Returns:
            ReviewResult
        """
        cfg = _get_llm_config(user_id)
        if not cfg['api_key']:
            return ReviewResult(
                overall_score=0,
                summary='AI 审查未配置：请在"设置 → 模型设置"中配置 API Key 和模型',
                issues=[]
            )

        parts = []
        if commit_info:
            parts.append(f"审查提交：{commit_info.get('sha', '')[:8]}")
            parts.append(f"提交信息：{commit_info.get('message', '').split(chr(10))[0]}")
            parts.append(f"作者：{commit_info.get('author', '')}")
        if file_list:
            summary_lines = [f"  - {f['filename']} ({f['status']}, +{f['additions']}/-{f['deletions']})" for f in file_list[:20]]
            parts.append(f"变更文件（{len(file_list)}个）：\n" + '\n'.join(summary_lines))
        if language:
            parts.append(f"语言：{language}")
        if context:
            parts.append(f"背景：{context}")
        parts.append(f"\n以下是本次提交的 unified diff：\n\n{diff_content}")

        user_prompt = '\n'.join(parts)
        return self._do_review(cfg, user_prompt, system_prompt=REVIEW_DIFF_SYSTEM_PROMPT)

    def _do_review(self, cfg, user_prompt, system_prompt=None):
        """内部通用审查方法."""
        # 检查配置
        if not cfg.get('api_key'):
            return ReviewResult(
                overall_score=0,
                summary='AI 审查未配置 API Key：请在"设置 → 模型设置"中配置 API Key 和模型，然后保存设置即可自动同步到审查服务',
                issues=[]
            )

        # 调用 LLM
        raw_json, errors = self._call_llm(cfg, user_prompt, system_prompt=system_prompt)
        if not raw_json:
            error_detail = '; '.join(errors) if errors else '无错误详情'
            return ReviewResult(
                overall_score=0,
                summary=f'审查失败：LLM 连接错误。\\n\\nmodel={cfg["model"]}, api_key_len={len(cfg["api_key"])}\\n\\n{error_detail}',
                issues=[]
            )

        # 解析 JSON
        try:
            result = self._parse_response(raw_json)
            return result
        except Exception as e:
            # 重试一次
            try:
                retry_prompt = user_prompt + '\n\n注意：上次回复格式不正确，请**只返回 JSON 对象**，不要用 markdown 包裹。'
                raw_json, _ = self._call_llm(cfg, retry_prompt, system_prompt=system_prompt)
                if not raw_json:
                    return ReviewResult(
                        overall_score=0,
                        summary=f'审查结果解析失败（重试后LLM仍返回空）: {str(e)[:200]}',
                        issues=[]
                    )
                return self._parse_response(raw_json)
            except Exception:
                return ReviewResult(
                    overall_score=0,
                    summary=f'审查结果解析失败: {str(e)[:200]}',
                    issues=[]
                )

    def _call_llm(self, cfg, user_prompt, system_prompt=None):
        """调用 LLM API — 先尝试 OpenAI，若失败且配置了 Anthropic 端点则尝试 Anthropic。

        Returns:
            (content, errors) — content 成功时为 LLM 回复文本，失败时为 None；errors 为错误信息列表。
        """
        sys_prompt = system_prompt or REVIEW_SYSTEM_PROMPT
        errors = []

        # 策略1：OpenAI Chat Completions
        result, err = self._call_openai(cfg['openai_url'], cfg['api_key'], cfg['model'], user_prompt, sys_prompt)
        if result is not None:
            return result, []
        errors.append(f"OpenAI({cfg['openai_url']}): {err}")

        # 策略2：Anthropic Messages API（仅当原始 URL 是 /anthropic 时）
        if cfg.get('anthropic_url'):
            logger.info(f"OpenAI failed, trying Anthropic: {cfg['anthropic_url']}")
            result, err = self._call_anthropic(cfg['anthropic_url'], cfg['api_key'], cfg['model'], user_prompt, sys_prompt)
            if result is not None:
                return result, []
            errors.append(f"Anthropic({cfg['anthropic_url']}): {err}")

        return None, errors

    def _call_openai(self, base_url, api_key, model, user_prompt, system_prompt):
        """OpenAI-compatible chat completions API. Returns (content, error_string)."""
        url = f"{base_url.rstrip('/')}/chat/completions"
        payload = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            'temperature': 0.3,
            'max_tokens': 4096,
        }
        headers = {
            'Authorization': f"Bearer {api_key}",
            'Content-Type': 'application/json',
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            content = data['choices'][0]['message']['content']
            if content is None:
                logger.error(f"OpenAI returned null content: {json.dumps(data, ensure_ascii=False)[:500]}")
                return None, '返回 content 为 null'
            return content, None
        except requests.Timeout:
            logger.error(f"OpenAI timeout: {url}")
            return None, '超时(120s)'
        except requests.HTTPError as e:
            status = e.response.status_code if e.response else '?'
            body = e.response.text[:300] if e.response else ''
            logger.error(f"OpenAI HTTP {status}: {body}")
            return None, f'HTTP {status} {body}'
        except requests.ConnectionError as e:
            logger.error(f"OpenAI connection error: {e}")
            return None, f'连接失败: {e}'
        except Exception as e:
            logger.error(f"OpenAI error: {type(e).__name__}: {e}")
            return None, f'{type(e).__name__}: {e}'

    def _call_anthropic(self, base_url, api_key, model, user_prompt, system_prompt):
        """Anthropic-compatible Messages API. Returns (content, error_string)."""
        url = f"{base_url.rstrip('/')}/v1/messages"
        payload = {
            'model': model,
            'system': system_prompt,
            'messages': [
                {'role': 'user', 'content': user_prompt},
            ],
            'max_tokens': 4096,
            'temperature': 0.3,
        }
        headers = {
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'Content-Type': 'application/json',
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            content_blocks = data.get('content', [])
            text = ''.join(b.get('text', '') for b in content_blocks if b.get('type') == 'text')
            if not text:
                logger.error(f"Anthropic no text: {json.dumps(data, ensure_ascii=False)[:500]}")
                return None, '返回无文本内容'
            return text, None
        except requests.Timeout:
            logger.error(f"Anthropic timeout: {url}")
            return None, '超时(120s)'
        except requests.HTTPError as e:
            status = e.response.status_code if e.response else '?'
            body = e.response.text[:300] if e.response else ''
            logger.error(f"Anthropic HTTP {status}: {body}")
            return None, f'HTTP {status} {body}'
        except requests.ConnectionError as e:
            logger.error(f"Anthropic connection error: {e}")
            return None, f'连接失败: {e}'
        except Exception as e:
            logger.error(f"Anthropic error: {type(e).__name__}: {e}")
            return None, f'{type(e).__name__}: {e}'

    def _parse_response(self, raw):
        """从 LLM 回复中提取 JSON 并解析为 ReviewResult."""
        # 去除可能的 markdown 代码块包裹
        text = raw.strip()
        m = re.search(r'```(?:json)?\s*\n?([\s\S]*?)```', text)
        if m:
            text = m.group(1).strip()
        data = json.loads(text)

        result = ReviewResult(
            overall_score=float(data.get('overall_score', 0)),
            summary=data.get('summary', ''),
            scores=data.get('scores', {}),
        )

        for issue in (data.get('issues') or []):
            result.issues.append({
                'severity': issue.get('severity', 'warning'),
                'category': issue.get('category', 'style'),
                'title': issue.get('title', ''),
                'description': issue.get('description', ''),
                'suggestion': issue.get('suggestion', ''),
                'line_start': issue.get('line_start'),
                'code_snippet': issue.get('code_snippet', ''),
                'fixed_snippet': issue.get('fixed_snippet', ''),
            })

        return result


review_engine = ReviewEngine()
