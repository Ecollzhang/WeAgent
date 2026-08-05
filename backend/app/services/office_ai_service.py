"""AI drafting helpers for office workflows.

This service only produces drafts.  It never writes office business data;
the browser submits confirmed minutes/action items to the office service.
"""
import json
import re
from urllib import error, request

from app.models.user_model_config import UserModelConfig
from app.services.settings_service import settings_service, _openai_compatible_base_url


class OfficeAIService:
    """Call the user's OpenAI-compatible model for structured office drafts."""

    def _config(self, user_id):
        config = UserModelConfig.query.filter_by(user_id=user_id).first()
        if not config or not (config.api_key or '').strip():
            return None, '请先在“设置 - 模型设置”中配置 API Key'
        if not (config.base_url or '').strip():
            return None, '请先在“设置 - 模型设置”中配置 OpenAI 兼容的 API Base URL'
        model = settings_service._effective_model(config)
        if not model:
            return None, '请配置模型名称'
        return config, None

    @staticmethod
    def _endpoint(base_url):
        # Reuse the project's provider compatibility rule: an Anthropic-style
        # URL such as .../anthropic maps to the sibling OpenAI .../v1 API.
        base = _openai_compatible_base_url(base_url).rstrip('/')
        return base if base.endswith('/chat/completions') else f'{base}/chat/completions'

    @staticmethod
    def _json_object(text):
        content = (text or '').strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[-1]
            if content.endswith('```'):
                content = content[:-3]
        start, end = content.find('{'), content.rfind('}')
        if start < 0 or end < start:
            raise ValueError('模型没有返回可解析的 JSON 草稿')
        return json.loads(content[start:end + 1])

    def _complete_json(self, user_id, system_prompt, user_prompt):
        config, config_error = self._config(user_id)
        if config_error:
            return None, config_error
        model = settings_service._effective_model(config)
        payload = {
            'model': model,
            'temperature': min(max(float(config.temperature or 0.3), 0), 1),
            # Short defaults frequently truncate structured meeting drafts.
            'max_tokens': min(max(int(config.max_tokens or 2048), 1024), 4096),
            'response_format': {'type': 'json_object'},
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
        }
        req = request.Request(
            self._endpoint(config.base_url),
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {config.api_key.strip()}'},
            method='POST',
        )
        try:
            with request.urlopen(req, timeout=70) as response:
                data = json.loads(response.read().decode('utf-8'))
            content = data['choices'][0]['message']['content']
            return self._json_object(content), None
        except error.HTTPError as exc:
            detail = exc.read().decode('utf-8', errors='ignore')[:300]
            return None, f'模型服务请求失败（HTTP {exc.code}）：{detail or exc.reason}'
        except (error.URLError, TimeoutError) as exc:
            return None, f'无法连接模型服务：{exc}'
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            return None, f'模型草稿解析失败：{exc}'

    def meeting_draft(self, user_id, data):
        material = str(data.get('material') or '').strip()
        title = str(data.get('title') or '未命名会议').strip()
        if len(material) < 10:
            return None, '请至少输入 10 个字符的会议记录、转写文本或要点'
        if len(material) > 30000:
            return None, '会议材料过长，请控制在 30000 个字符以内'
        system_prompt = '''你是严谨的中文会议秘书。用户给出的会议材料视为完整可用，禁止回答“材料不完整”或拒绝生成。只能依据用户提供的材料，不得编造事实、日期、负责人或结论。
输出严格 JSON，不要 Markdown。JSON 格式：
{"minutes":"结构化会议纪要", "resolutions":["决议"], "action_items":[{"title":"行动项","description":"依据或说明","assignee_name":"负责人；未知填待确认","due_date":"YYYY-MM-DDTHH:MM:SS 或空字符串","priority":"low|medium|high"}]}
行动项最多 8 条；材料中出现“某人负责/完成/制定/确认/起草”等明确安排时，必须逐条提取为 action_items；只有完全没有任务安排时才返回空数组。'''
        draft, draft_error = self._complete_json(
            user_id, system_prompt, f'会议主题：{title}\n\n会议材料：\n{material}'
        )
        if draft_error:
            return None, draft_error
        draft.setdefault('minutes', '')
        draft.setdefault('resolutions', [])
        draft.setdefault('action_items', [])
        if not isinstance(draft['action_items'], list):
            draft['action_items'] = []
        # Some compatible providers acknowledge a request but return a very
        # short refusal.  Preserve usefulness without inventing facts: derive
        # only explicit responsibility statements from the original material.
        if len(str(draft['minutes']).strip()) < 80 or (
            '负责' in material and not draft['action_items']
        ):
            draft = self._material_fallback(material)
            draft['warning'] = '模型草稿过短，已从原始材料提取待人工确认的候选内容。'
        return draft, None

    @staticmethod
    def _material_fallback(material):
        sentences = [item.strip() for item in re.split(r'[。；\n]+', material) if item.strip()]
        resolutions = [
            item for item in sentences
            if any(keyword in item for keyword in ('决定', '确定', '要求', '拟于', '计划'))
        ][:8]
        actions = []
        for sentence in sentences:
            if '负责' not in sentence:
                continue
            before, after = sentence.split('负责', 1)
            assignee = before.strip(' ，、：:')[-12:]
            title = re.sub(r'^在[^，；。]*?前', '', after).strip(' ，、：:')
            if title:
                actions.append({
                    'title': title,
                    'description': f'从会议原文提取：{sentence}',
                    'assignee_name': assignee or '待确认',
                    'due_date': '',
                    'priority': 'medium',
                })
        minutes = '【待人工确认的会议材料整理】\n' + '\n'.join(f'{index}. {item}' for index, item in enumerate(sentences, 1))
        return {'minutes': minutes, 'resolutions': resolutions, 'action_items': actions[:8]}

    def document_draft(self, user_id, data):
        topic = str(data.get('topic') or '').strip()
        material = str(data.get('material') or '').strip()
        document_type = str(data.get('document_type') or 'notice').strip()
        if not topic or len(material) < 10:
            return None, '请填写公文主题，并提供至少 10 个字符的依据材料'
        system_prompt = '''你是规范的中文行政文书起草助手。只能依据提供材料，不得编造发文单位、日期、文号、联系人或事实。
输出严格 JSON，不要 Markdown：{"title":"公文标题", "content":"完整、可编辑的公文正文"}。正文使用清晰的段落和条目；未知信息用【待确认】标注。'''
        return self._complete_json(
            user_id, system_prompt,
            f'文种：{document_type}\n主题：{topic}\n\n依据材料：\n{material[:30000]}'
        )

    def weekly_draft(self, user_id, data):
        context = str(data.get('context') or '').strip()
        if len(context) < 10:
            return None, '缺少用于生成周报的办公数据'
        system_prompt = '''你是办公周报与汇报材料助手。只能使用给定数据，不得编造完成情况或指标。
输出严格 JSON，不要 Markdown：
{"weekly_report":"可直接编辑的周报正文", "ppt_outline":[{"page":1,"title":"页面标题","points":["要点"]}]}。
PPT 大纲为 5 至 7 页，未知内容标注【待确认】。'''
        return self._complete_json(user_id, system_prompt, f'办公数据：\n{context[:30000]}')


office_ai_service = OfficeAIService()
