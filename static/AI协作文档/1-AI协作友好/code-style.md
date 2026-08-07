# Code Style

> 本文件基于 v1.1.1 实际代码总结。AI 生成代码时应遵守以下约定。

---

## 后端（Python）

### 命名约定

| 元素 | 风格 | 示例 |
|------|------|------|
| 类名 | PascalCase | `class Artifact(BaseModel)` |
| 函数/方法 | snake_case | `def get_user_conversations(user_id)` |
| 变量 | snake_case | `user_id`, `conv_type` |
| 常量 | UPPER_SNAKE_CASE | `__tablename__ = 'messages'` |
| 文件/模块 | snake_case | `orchestrator_service.py` |

### 文件组织

```
app/
  controllers/     # 路由层：Blueprint + 函数视图
  services/        # 业务逻辑：类 + 方法（单例模式）
  models/          # 数据库模型：BaseModel 子类
  repositories/    # 数据访问：BaseRepo 子类
  schemas/         # 序列化：Marshmallow Schema
```

### Controller 模式

```python
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.utils.response import success_response, error_response

bp = Blueprint('resources', __name__)

@bp.route('', methods=['GET'])
@jwt_required()
def list_resources():
    user_id = get_jwt_identity()
    result, error = resource_service.list(user_id)
    if error:
        return error_response(error, code=400)
    return success_response(result)
```

### Service 模式

- 使用单例：`class SomeService: pass` + 模块级实例 `some_service = SomeService()`
- 方法返回 `(result, error)` 元组
- 成功时 error 为 None，失败时 result 为 None

### 响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

### 数据库模型约定

- 所有 Model 继承 `BaseModel`（`app/models/__init__.py`）
- 主键统一用 `id`（String(36)，UUID）
- 时间字段统一用 `created_at` / `updated_at`
- Enum 字段使用 SQLAlchemy Enum 类型

### 日志约定

- 当前使用 `print('[WeAgent] ...')` 输出日志（现状）
- 关键路径打印请求参数和错误信息
- 建议后续迁移到 Python logging 模块，统一日志级别和输出格式

---

## 前端（Vue 2）

### 命名约定

| 元素 | 风格 | 示例 |
|------|------|------|
| 组件名 | PascalCase | `ChatWindow`, `MessageBubble` |
| 文件/目录 | kebab-case / PascalCase | `chat-window` / `ChatWindow/` |
| 变量/函数 | camelCase | `currentUser`, `fetchMessages` |
| Vuex Action | camelCase | `fetchConversations`, `sendMessage` |
| API 函数 | camelCase | `getConversations`, `createConversation` |

### 组件组织

每个功能组件放在同名目录下，目录内为 `index.vue`：

```
components/
  ChatWindow/
    index.vue
  MessageBubble/
    index.vue
```

### Vuex Store 模式

```
store/
  index.js                        # 组装所有 module
  modules/
    conversation.js               # state, getters, mutations, actions
    message.js
    agent.js
    user.js
    settings.js
```

### API 封装模式

```
api/
  axios.js                        # 全局 Axios 实例（baseURL, 拦截器）
  conversation.js                 # 导出函数：getConversations, createConversation...
  message.js
  agent.js
```

### 组件内约定

- 使用 `export default { name: 'ComponentName' }`
- 异步操作通过 Vuex action 派发，不直接在组件内调用 API
- 组件内不直接 `import axios`
- 模板中使用 Element UI 组件：`<el-button>`, `<el-dialog>` 等
- template 缩进使用 2 空格
- style 统一加 `scoped`，避免样式污染

### Vue 文件结构

```vue
<template>
  <!-- 2 空格缩进 -->
</template>

<script>
export default {
  name: 'ComponentName',
}
</script>

<style scoped>
/* 组件内样式 */
</style>
```

### Import 排序约定

顺序：第三方库 → 项目内部模块 → 相对路径。每组之间空一行。

```javascript
import Vue from 'vue'
import { mapState } from 'vuex'

import { getConversations } from '@/api/conversation'
import MessageBubble from '@/components/MessageBubble'

import { formatTime } from '../utils/format'
```

---

## 通用约定

- 函数/方法建议写 docstring 说明功能
- 复杂的业务逻辑写行内注释
- 不要提交无意义注释

### 错误处理

- Controller 捕获 `ValidationError` 后返回 `error_response`
- Service 方法返回 `(result, error)`，由调用方决定如何处理
- 不要吞异常，无法处理时向上抛

---

## 禁止的做法

- 不要在 Service 层返回 HTTP 响应
- 不要在 Controller 层直接调用 Repository
- 不要在 Model 中写业务逻辑
- 不要在前端 Component 中直接调用 API
- 不要把 API Key 硬编码在代码中（存在 config 字段中，通过 API mask）

---

## 自我迭代

> 版本：v1.0 | 最后更新：2026-06-08 | 更新人：zby

### 修改流程

1. 代码风格规范变更时更新本文件
2. 在文件头部更新版本号和日期
3. 修改需至少一人 review 确认

### 触发条件

- 团队约定新的命名或组织规范
- 发现 AI 频繁生成不符合现有风格的代码
- 引入新的框架或工具，需要补充规范
