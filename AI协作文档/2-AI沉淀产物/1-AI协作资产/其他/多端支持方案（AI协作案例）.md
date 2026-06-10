# 多端支持方案（AI协作案例）

## 1\. 需求复述

当前目标是在不破坏现有 Web 端功能的前提下，为项目实现多端支持：

- Web 端：作为现有稳定版本，功能和页面行为保持不动，只做必要的兼容性回归验证。

- Desktop 桌面端：做全量迁移，尽量覆盖 Web 端核心业务功能，并支持独立配置外部后端地址。

- Android 端：做主要功能迁移，优先覆盖登录注册、会话、消息、Agent、个人设置等主要工作流，不追求一次性迁移全部高级功能。

该方案采用分阶段协作方式推进：每个阶段都有明确目标、验收标准、测试方式和可能影响功能的回归测试。

## 2\. 默认假设

- Web 端现有功能视为基准版本，不主动改动 Web 页面结构和交互。

- Desktop 和 Android 使用独立客户端目录，不直接复用 Web 页面文件，避免多端需求相互污染。

- 后端未来部署公网，但当前需要支持局域网测试。

- Desktop 只连接外部后端，不内置后端服务。

- Android 只实现 Android，不处理 iOS。

- 多端共享后端接口、认证逻辑、会话数据、Agent 数据、消息数据和文件/产物数据。

- 如必须修改后端或共享 API，需要同步做 Web 回归测试。

## 3\. 待确认问题

1. Desktop 是否以 Electron 为最终打包方案？

    - 默认选择 Electron，因为生态成熟，适合快速打包 Windows/macOS/Linux。

2. Android 是否以 Capacitor \+ Vue 为最终方案？

    - 默认选择 Capacitor，因为可以复用 Vue 技术栈，并通过 Android WebView 快速落地。

3. Android 首版主要功能范围是否为：

    - 登录 / 注册

    - 会话列表

    - 会话详情

    - 消息发送和展示

    - Agent 列表和基础编辑

    - 个人设置

    - 基础文件/产物查看

4. Desktop 是否要求覆盖全部 Web 端核心功能？

    - 默认是，包括会话、Agent、设置、收藏、搜索、历史、产物、文件、日志、工作流占位等。

5. 是否允许后端为多端兼容新增字段或接口？

    - 默认允许，但必须保证 Web 端兼容。

## 4\. 技术选型

### 4\.1 Desktop

推荐方案：Electron \+ 独立 Vue 客户端。

目录建议：

```Plain Text
clients/desktop
```

核心能力：

- 独立桌面客户端。

- 可配置后端地址。

- 支持 Windows 打包。

- 后续可扩展系统通知、文件选择、托盘、自动更新等桌面能力。

不采用直接打包 Web 端的原因：

- Web 端要求保持稳定，不适合持续承担桌面端差异化交互。

- 桌面端后续可能有独立页面和功能布局。

- 独立客户端可以避免桌面端 UI 需求影响 Web。

### 4\.2 Android

推荐方案：Capacitor \+ 独立 Vue 客户端。

目录建议：

```Plain Text
clients/android
```

核心能力：

- Vue 写主要业务界面。

- Capacitor 生成 Android 工程外壳。

- Android Studio 负责真机调试、模拟器调试和 APK 构建。

- 首版只做主要功能迁移，不追求完整桌面级能力。

不直接使用原生 Java/Kotlin 重写业务界面的原因

- 当前阶段目标是快速迁移和验证多端能力。

- 项目已有 Vue 经验和组件逻辑。

- Capacitor 可以降低首版实现成本。

## 5\. 用户故事

### 5\.1 Desktop 用户

```Plain Text
作为桌面端用户，
我希望可以通过 WeAgent 桌面应用登录、管理 Agent、创建会话、发送消息、查看产物和文件，
以便不依赖浏览器也能完成完整工作流。
```

### 5\.2 Android 用户

```Plain Text
作为 Android 用户，
我希望可以在手机上登录、查看会话、发送消息、查看 Agent 和个人设置，
以便在移动场景下使用 WeAgent 的主要功能。
```

### 5\.3 Web 用户

```Plain Text
作为 Web 用户，
我希望多端支持开发不会破坏现有 Web 功能，
以便原有工作流继续稳定可用。
```

## 6\. 总体验收条件

### 6\.1 Web 稳定性

```Plain Text
Given Web 端是现有基准版本
When 多端支持开发完成任一阶段
Then Web 端核心功能应保持可用
And 登录、注册、会话、消息、Agent、设置等主要路径不应出现回归
```

### 6\.2 Desktop 全量迁移

```Plain Text
Given 用户打开 Desktop 客户端
When 用户配置后端地址并登录
Then 用户应能完成 Web 端核心业务工作流
And 桌面端应能独立打包运行
```

### 6\.3 Android 主要功能迁移

```Plain Text
Given 用户在 Android 设备或模拟器中打开应用
When 用户配置局域网后端地址并登录
Then 用户应能完成主要移动端工作流
And 首版未迁移的高级功能应有明确边界
```

## 7\. 分阶段实施方案

## 阶段 1：项目结构和多端基础工程

目标：

- 建立 Desktop 和 Android 独立客户端目录。

- 保证 Web 端不被直接改动。

- 建立多端统一后端地址配置方式。

范围：

- `clients/desktop`

- `clients/android`

- 多端 README 或说明文档

- 环境变量示例文件

验收标准：

- Desktop 客户端可以启动开发环境。

- Android 客户端可以生成 Capacitor Android 工程。

- 两端都可以配置后端地址。

- Web 构建不受影响。

测试方式：

- Desktop：运行开发服务或构建命令。

- Android：运行 Capacitor sync，确认 Android 工程生成。

- Web 回归：运行 Web 构建。

回归测试：

- Web 登录页可正常构建。

- Web 路由不受新客户端目录影响。

- 根目录依赖和脚本不破坏已有启动方式。

## 阶段 2：登录注册迁移

目标：

- Desktop 和 Android 实现登录、注册、退出登录。

- 支持配置局域网后端地址。

范围：

- 登录页

- 注册页

- 认证 API

- token/session 存储

- 后端地址配置页或配置入口

验收标准：

```Plain Text
Given 用户配置了正确后端地址
When 输入正确账号密码登录
Then 应进入主界面

Given 用户输入错误账号密码
When 点击登录
Then 应显示错误提示

Given 用户注册新账号
When 后端返回成功
Then 应能使用该账号登录
```

测试方式：

- API 请求验证。

- 登录成功/失败手动测试。

- token 持久化测试。

回归测试：

- Web 登录/注册仍可用。

- 后端 auth 接口返回结构不变。

- token 失效或 401 时 Web/Desktop/Android 都能正确处理。

## 阶段 3：Desktop 会话全量迁移

目标：

- Desktop 实现完整会话工作流。

范围：

- 会话列表

- 新建会话

- 删除会话

- 收藏会话

- 会话搜索

- 会话历史

- 单 Agent / 多 Agent 会话

- 消息发送

- 消息实时更新

- Markdown 渲染

- 进度、进度历史、产物、Raw output 展示

验收标准：

```Plain Text
Given 用户在 Desktop 中打开会话
When 发送消息
Then 用户消息应立即显示在右侧
And Agent 回复应显示在用户消息之后
And 刷新后消息顺序和内容保持一致

Given Agent 返回进度、表格、文件、图片或服务产物
When Desktop 收到实时事件
Then 应正确分类和渲染
And 刷新后产物不丢失
```

测试方式：

- Desktop 构建测试。

- Socket 实时消息手动验证。

- 消息刷新后状态验证。

- Markdown、表格、文件、图片、服务产物手动验证。

回归测试：

- Web 会话列表不变。

- Web 消息发送和实时更新不变。

- 后端消息接口兼容原 Web payload。

- 多 Agent 主持逻辑不影响单 Agent 会话。

## 阶段 4：Desktop Agent 和个人设置全量迁移

目标：

- Desktop 实现 Agent 管理和个人设置。

范围：

- 我的 Agent 列表

- Agent 创建、编辑、保存、重置、删除

- Agent 头像颜色选择

- 工具下拉选择

- 个人信息

- 头像上传

- 模型配置

验收标准：

```Plain Text
Given 用户进入 Desktop 我的 Agent
When 编辑 Agent 名称、系统提示词、skill、工具等信息
Then 保存后再次进入应保持更新

Given 用户上传头像
When 上传成功
Then Desktop 和 Web 获取用户信息时都应显示新头像
```

测试方式：

- Agent API 手动验证。

- 头像上传手动验证。

- 表单保存后刷新验证。

回归测试：

- Web Agent 管理功能仍可用。

- Web 个人设置仍可上传头像。

- 后端 Agent schema 兼容原字段。

- 上传接口兼容 Web/Desktop。

## 阶段 5：Desktop 文件、产物、日志和工作流入口

目标：

- Desktop 实现文件和产物相关高级工作流。

范围：

- 上传文件到容器

- 查看容器文件夹

- 点击文件产物查看内容

- 表格产物内置预览

- HTML 产物预览

- 产物抽屉分类

- 产物操作：查看、运行、停止、复制等

- 容器 app 日志

- 工作流全屏弹窗占位

验收标准：

```Plain Text
Given 会话中存在文件产物
When 用户点击查看
Then 应打开文件列表并定位或预览对应文件

Given 会话中存在没有文件路径的表格产物
When 用户点击查看
Then 应使用产物内置 headers/rows 渲染表格

Given 会话中存在服务产物
When 用户点击运行或停止
Then 应调用对应服务接口并更新状态
```

测试方式：

- 文件上传手动测试。

- 文件列表打开即加载测试。

- 表格无文件路径预览测试。

- HTML 预览样式测试。

- 服务运行/停止接口测试。

回归测试：

- Web 产物展示不变。

- Web 文件预览不变。

- 后端文件路径解析兼容历史路径。

- 刷新后产物、进度、raw output 不丢失。

## 阶段 6：Desktop 打包和发布

目标：

- Desktop 可以打包成安装程序。

范围：

- Electron 打包配置

- 应用名称

- 应用 logo

- 安装包输出目录

- 环境变量配置

验收标准：

```Plain Text
Given 用户运行桌面端打包命令
When 构建完成
Then 应生成 WeAgent 桌面应用安装包
And 应使用指定 logo
And 安装后可以配置后端并登录
```

测试方式：

- 运行 Desktop build。

- 本机安装或解压运行测试。

- 登录、会话、Agent、设置冒烟测试。

回归测试：

- Desktop dev 模式仍可运行。

- Web 构建不受 Electron 配置影响。

- 环境变量示例不泄露真实密钥。

## 阶段 7：Android 登录注册和基础壳

目标：

- Android 客户端可以运行、配置后端、登录注册。

范围：

- Capacitor 初始化

- Android 工程

- 登录页

- 注册页

- 后端地址配置

- HTTP 明文局域网访问配置

验收标准：

```Plain Text
Given Android 设备和后端在同一局域网
When 用户配置后端 IP 和端口
Then 登录请求应能到达后端
And 登录成功后进入主界面
```

测试方式

- Android Studio 模拟器测试。

- 真机局域网测试。

- 后端日志确认请求来源。

回归测试：

- Web/Desktop 登录不受 Android 网络配置影响。

- 后端 CORS 和认证逻辑不破坏已有客户端。

- Android 清缓存/重装后仍可重新配置后端。

## 阶段 8：Android 主要功能迁移

目标：

- Android 实现主要使用路径。

范围：

- 会话列表

- 会话详情

- 新建会话

- 发送消息

- Agent 回复展示

- Agent 列表和基础查看/编辑

- 个人设置

- 基础产物展示

验收标准：

```Plain Text
Given 用户在 Android 会话详情页发送消息
When 后端返回 Agent 回复
Then 回复应显示在用户消息之后
And 用户消息靠右，Agent 消息靠左
And 刷新或重新进入会话时应定位到最新消息
```

测试方式：

- Android 真机或模拟器手动测试。

- 会话创建测试。

- 消息实时/轮询测试。

- Agent 和个人设置保存测试。

回归测试：

- Desktop 会话功能不受 Android 改动影响。

- Web 会话功能不受 Android 改动影响。

- 后端消息排序和分页兼容三端。

- 头像、图片、文件链接在 Android 明文 HTTP 场景下可访问或有明确降级策略。

## 阶段 9：多端一致性和回归测试

目标：

- 验证 Web、Desktop、Android 三端共享数据一致。

范围：

- 登录状态

- 用户信息

- Agent 数据

- 会话数据

- 消息数据

- 产物数据

- 文件数据

- 收藏状态

验收标准：

```Plain Text
Given 用户在 Desktop 修改 Agent skill
When Web 和 Android 重新进入相关页面
Then 应看到一致数据，除非该配置明确为会话级配置

Given 用户在 Web 收藏会话
When Desktop 打开收藏列表
Then 应显示该会话
```

测试方式：

- 三端冒烟测试。

- 后端数据库状态检查。

- API 响应一致性检查。

回归测试：

- Web 主流程完整回归。

- Desktop 主流程完整回归。

- Android 主流程完整回归。

- 后端接口兼容性回归。

## 8\. 回归测试矩阵

|改动类型|必须回归的功能|
|---|---|
|后端认证|Web/Desktop/Android 登录、注册、退出、401 处理|
|会话接口|会话列表、新建、删除、收藏、搜索、历史|
|消息接口|发送、实时更新、刷新后顺序、单 Agent、多 Agent|
|Agent 配置|全局 Agent、会话级 Agent 配置、skill、system prompt|
|产物渲染|Markdown、代码块、表格、文件、图片、HTML、Raw output|
|文件接口|上传、列表、下载、预览、路径解析|
|Socket/Event|实时进度、状态替换、刷新后状态一致|
|CSS/布局|Web 主要页面、Desktop 主要页面、Android 会话页|
|打包配置|Desktop 安装包、Android APK、环境变量|

## 9\. 推荐测试脚本和命令

### Web

```Bash
cd frontend
npm run build
```

### Desktop

```Bash
cd clients/desktop
npm run build
```

### Android

```Bash
cd clients/android
npm run build
npx cap sync android
```

### Backend

```Bash
cd backend
python -m py_compile app/services/message_service.py app/controllers/message_controller.py app/schemas/message_schema.py
```

如存在单元测试：

```Bash
cd backend
python -m unittest
```

## 10\. 风险和处理策略

### 风险 1：Web 被多端改动影响

处理：

- Web 页面不直接复用 Desktop/Android 页面。

- 后端接口改动必须兼容旧字段。

- 每阶段跑 Web 构建和关键路径回归。

### 风险 2：Desktop 和 Web 功能出现行为差异

处理：

- Desktop 以 Web 作为业务行为基准。

- 对消息、产物、Agent 配置等共享逻辑建立回归清单。

- 差异必须写入阶段说明，不隐式偏离。

### 风险 3：Android WebView 网络和资源访问问题

处理：

- 明确局域网后端地址配置。

- 开发阶段允许 HTTP 明文访问。

- 图片、头像、文件链接需要单独验证。

- 真机和模拟器分别测试。

### 风险 4：实时状态和刷新后状态不一致

处理：

- Socket event 和数据库持久化都要验证。

- 每个消息/产物相关阶段必须测试实时显示和刷新后显示。

- 对 replace/merge 类事件要做回归。

### 风险 5：产物没有文件实体

处理：

- 表格等结构化产物优先使用内置数据渲染。

- 文件产物才走容器文件路径。

- 产物抽屉操作根据产物类型决定。

## 11\. 最终交付标准

多端支持完成时，应满足：

- Web 端原功能保持可用。

- Desktop 完成全量迁移并可打包。

- Android 完成主要功能迁移并可真机运行。

- 后端接口兼容三端。

- 会话、Agent、用户、消息、产物核心数据在多端一致。

- 每个阶段有测试记录和回归记录。

- 未迁移或暂缓功能有明确说明。



