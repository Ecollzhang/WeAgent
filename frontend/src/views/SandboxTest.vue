<template>
  <div class="sandbox-test">
    <AppSidebar />

    <div class="main-content">
      <div class="page-header">
        <h1><i class="el-icon-s-promotion" style="margin-right:8px"/>多 Agent 协作沙箱</h1>
        <p class="page-desc">1 会话 = 1 Docker 容器 · 主持 Agent 分派任务 · 实时查看各 Agent 进度</p>
      </div>

      <!-- ====== 顶部工具栏 ====== -->
      <div class="toolbar">
        <el-button-group>
          <el-button :type="imageReady ? 'success' : 'warning'" size="small"
            @click="checkImage" :loading="checkingImage">
            <i :class="imageReady ? 'el-icon-check' : 'el-icon-warning'" />
            {{ imageReady ? '镜像就绪' : '检查镜像' }}
          </el-button>
          <el-button size="small" @click="handleBuildImage" :loading="buildingImage" :disabled="imageReady">
            构建镜像
          </el-button>
        </el-button-group>
        <el-button-group style="margin-left:12px">
          <el-button size="small" @click="refreshSessions" :loading="loadingSessions">
            <i class="el-icon-refresh" /> 刷新
          </el-button>
        </el-button-group>
      </div>

      <!-- ====== 主体布局 ====== -->
      <div class="body-layout">
        <!-- ====== 左侧：Agent 配置区 ====== -->
        <div class="left-panel">
          <el-card class="config-card" shadow="never">
            <div slot="header" class="card-header">
              <span><i class="el-icon-setting" /> API 配置</span>
            </div>
            <el-form size="mini" label-width="80px">
              <el-form-item label="API Key">
                <el-input v-model="envVars.ANTHROPIC_API_KEY" type="password" show-password placeholder="sk-..." />
              </el-form-item>
              <el-form-item label="接口地址">
                <el-input v-model="envVars.ANTHROPIC_BASE_URL" placeholder="https://api.deepseek.com/anthropic" />
              </el-form-item>
              <el-form-item label="模型">
                <el-input v-model="envVars.ANTHROPIC_MODEL" placeholder="deepseek-v4-flash" />
              </el-form-item>
            </el-form>
          </el-card>

          <el-card class="config-card" shadow="never">
            <div slot="header" class="card-header">
              <span><i class="el-icon-user" /> Agent 配置</span>
              <el-button size="mini" type="text" @click="addAgent"><i class="el-icon-plus" /> 添加</el-button>
            </div>
            <div class="agent-config-list">
              <div v-for="(ag, idx) in agents" :key="idx" class="agent-config-item"
                   :class="{ 'is-moderator': ag.agent_id === 'moderator' }">
                <div class="agent-config-header">
                  <el-tag :type="ag.agent_id === 'moderator' ? 'warning' : 'info'" size="mini" effect="dark">
                    {{ ag.agent_id === 'moderator' ? '主持' : '成员' }}
                  </el-tag>
                  <el-input v-model="ag.agent_id" size="mini" placeholder="agent-id" style="width:100px;margin:0 4px" />
                  <el-input v-model="ag.role" size="mini" placeholder="角色" style="width:80px;margin-right:4px" />
                  <el-button v-if="idx > 2" size="mini" type="danger" circle icon="el-icon-delete" @click="removeAgent(idx)" />
                </div>
                <el-input v-model="ag.system_prompt" type="textarea" :rows="2" resize="none" class="agent-prompt-input"
                  :placeholder="ag.agent_id === 'moderator' ? '你是主持 Agent...' : '你是专业 Agent...'" />
                <div class="prompt-presets">
                  <el-tag v-if="ag.agent_id === 'moderator'" size="mini" @click="ag.system_prompt = moderatorPreset">默认主持</el-tag>
                  <el-tag v-if="ag.agent_id === 'writer'" size="mini" @click="ag.system_prompt = writerPreset">默认文档</el-tag>
                  <el-tag v-if="ag.agent_id === 'frontend'" size="mini" @click="ag.system_prompt = frontendPreset">默认前端</el-tag>
                </div>
              </div>
            </div>
            <el-button class="start-btn" type="success" @click="handleCreateSession"
              :loading="creatingSession" :disabled="!envVars.ANTHROPIC_API_KEY">
              <i class="el-icon-video-play" /> {{ creatingSession ? '启动中...' : '启动会话' }}
            </el-button>
          </el-card>

          <el-card class="config-card" shadow="never">
            <div slot="header" class="card-header">
              <span><i class="el-icon-s-grid" /> 会话 ({{ sessions.length }})</span>
            </div>
            <div v-loading="loadingSessions">
              <div v-for="s in sessions" :key="s.session_id" class="session-item"
                   :class="{ active: currentSession?.session_id === s.session_id }" @click="selectSession(s)">
                <div class="session-top">
                  <span class="session-id">{{ s.session_id }}</span>
                  <el-tag size="mini" :type="s.alive ? 'success' : 'danger'" effect="plain">
                    {{ s.alive ? '运行中' : '离线' }}
                  </el-tag>
                </div>
                <div class="session-meta">
                  <span>{{ s.agents?.length || 0 }} Agent</span>
                  <span>端口 {{ s.host_port }}</span>
                </div>
              </div>
              <div v-if="sessions.length === 0 && !loadingSessions" class="empty-hint">暂无会话</div>
            </div>
          </el-card>
        </div>

        <!-- ====== 右侧 ====== -->
        <div class="right-panel">
          <template v-if="currentSession">
            <!-- Header -->
            <div class="chat-header">
              <div class="chat-header-left">
                <span class="chat-session-id">{{ currentSession.session_id }}</span>
                <el-tag size="mini" effect="dark" type="success">
                  {{ currentSession.agents?.length || 0 }} Agent
                </el-tag>
              </div>
              <div class="chat-header-actions">
                <el-button size="mini" plain @click="addAgentToCurrentSession">
                  <i class="el-icon-plus" /> 添加 Agent
                </el-button>
                <el-button size="mini" plain @click="refreshServices">
                  <i class="el-icon-link" /> 服务
                </el-button>
                <el-button size="mini" plain @click="handleBrowseFiles()">
                  <i class="el-icon-folder-opened" /> 全部文件
                </el-button>
                <el-button size="mini" type="danger" plain @click="handleDestroySession">
                  <i class="el-icon-delete" /> 销毁
                </el-button>
              </div>
            </div>

            <div v-if="services.length" class="service-bar">
              <span class="service-title"><i class="el-icon-link" /> 服务预览</span>
              <el-tag v-for="svc in services" :key="svc.port" size="mini"
                :type="svc.status === 'open' ? 'success' : 'info'"
                class="service-tag"
                @click="openService(svc)">
                {{ svc.port }} → {{ svc.host_port || '-' }} {{ svc.status || '' }}
              </el-tag>
            </div>

            <!-- ===== Agent 实时状态条 ===== -->
            <div class="agent-status-bar">
              <div v-for="ag in sessionAgents" :key="ag.agent_id" class="agent-status-item"
                   :class="getStatusClass(ag.agent_id)">
                <div class="status-indicator">
                  <span class="status-dot" :class="getStatusDot(ag.agent_id)"></span>
                  <span class="status-role">{{ ag.role || ag.agent_id }}</span>
                </div>
                <div class="status-message" :title="getAgentStatusMsg(ag.agent_id)">
                  {{ getAgentStatusMsg(ag.agent_id) }}
                </div>
                <div class="status-time" v-if="getAgentStatusTime(ag.agent_id)">
                  {{ getAgentStatusTime(ag.agent_id) }}
                </div>
                <el-button
                  class="status-folder-btn"
                  size="mini"
                  type="text"
                  icon="el-icon-folder-opened"
                  @click.stop="handleBrowseFiles(ag.agent_id)" />
              </div>
            </div>

            <!-- 模式切换 -->
            <div class="mode-bar">
              <el-radio-group v-model="sendMode" size="small">
                <el-radio-button label="chain"><i class="el-icon-sort" /> 主持分派</el-radio-button>
                <el-radio-button label="direct"><i class="el-icon-chat-dot-round" /> 直接发送</el-radio-button>
              </el-radio-group>
              <div class="chain-agents" v-if="sendMode === 'chain'">
                <span class="chain-label">链路:</span>
                <template v-for="(ag, i) in chainAgents">
                  <el-tag :key="ag.agent_id" size="mini" :type="ag.agent_id === 'moderator' ? 'warning' : 'info'">
                    {{ ag.role || ag.agent_id }}<i v-if="i < chainAgents.length-1" class="el-icon-arrow-right" />
                  </el-tag>
                </template>
              </div>
              <div v-if="sendMode === 'direct'">
                <el-select v-model="currentAgentId" size="small" style="width:150px" placeholder="选择 Agent">
                  <el-option v-for="a in currentSession.agents || []" :key="a.agent_id"
                    :label="`${a.role || a.agent_id}`" :value="a.agent_id" />
                </el-select>
              </div>
            </div>

            <!-- ===== Agent 任务面板区（替代平铺消息列表） ===== -->
            <div class="agent-panels" ref="chatRef" @scroll="handleChatScroll">
              <!-- 用户最近一条需求 -->
              <div v-if="lastUserMessage" class="user-request-banner">
                <i class="el-icon-user" /> {{ lastUserMessage }}
              </div>

              <!-- Agent 面板网格 -->
              <div class="agent-panels-grid">
                <div v-for="display in agentDisplayList" :key="display.agent_id" class="agent-panel"
                     :class="'panel-' + display.status">
                  <!-- ===== 面板头部 ===== -->
                  <div class="panel-header">
                    <div class="panel-header-left">
                      <span class="panel-role-badge" :style="'background:' + getAgentColor(display.agent_id)">
                        <i :class="getAgentIcon(display.agent_id)" />
                        {{ display.role }}
                      </span>
                      <span class="panel-status-text">{{ display.statusMessage }}</span>
                    </div>
                    <div class="panel-header-right">
                      <span class="panel-status-dot" :class="'dot-' + display.status"></span>
                      <el-button v-if="display.status === 'working' || display.status === 'thinking'"
                        size="mini" type="danger" plain circle icon="el-icon-close"
                        @click="handleStopAgent(display.agent_id)" />
                      <el-button
                        size="mini" type="primary" plain circle icon="el-icon-document"
                        title="进入工作目录"
                        @click="handleBrowseFiles(display.agent_id)" />
                    </div>
                  </div>

                  <!-- ===== 面板主体 ===== -->
                  <div class="panel-body">
                    <!-- Claude Code 真实输出 / 错误 -->
                    <div v-if="display.events.length" class="panel-timeline">
                      <div v-for="(ev, ei) in display.events" :key="ei" class="timeline-item" :class="'tl-' + ev.type">
                        <span class="tl-icon">
                          <i v-if="ev.type === 'claude_output'" class="el-icon-chat-line-square" />
                          <i v-else-if="ev.type === 'claude_error'" class="el-icon-warning-outline" style="color:#f56c6c" />
                          <i v-else-if="ev.type === 'error'" class="el-icon-error" style="color:#f56c6c" />
                          <i v-else class="el-icon-chat-dot-round" />
                        </span>
                        <span class="tl-time">{{ ev.time }}</span>
                        <span class="tl-text">{{ ev.text }}</span>
                      </div>
                    </div>

                    <!-- 空状态 -->
                    <div v-else-if="display.status === 'idle'" class="panel-empty">
                      <i class="el-icon-wait" /> 等待任务...
                    </div>

                    <!-- Agent 回复内容（可折叠） -->
                    <div v-if="display.reply" class="panel-reply">
                      <div class="reply-header" @click="toggleReply(display.agent_id)">
                        <i :class="display.replyExpanded ? 'el-icon-caret-bottom' : 'el-icon-caret-right'" />
                        <span>Claude Code 实时输出</span>
                        <span class="reply-size">{{ display.reply.length }} 字符</span>
                      </div>
                      <pre v-if="display.replyExpanded" class="reply-content">{{ display.reply }}</pre>
                    </div>

                    <!-- 错误信息 -->
                    <div v-if="display.error" class="panel-error">
                      <i class="el-icon-error" /> {{ display.error }}
                    </div>

                    <!-- 文件列表 -->
                    <div v-if="display.files.length" class="panel-files">
                      <div class="files-header"><i class="el-icon-document" /> 新增/修改文件 ({{ display.files.length }})</div>
                      <div class="files-grid">
                        <div v-for="(f, fi) in display.files" :key="fi" class="file-item"
                             @click="openFileInTab(display.agent_id, f.file)">
                          <i class="el-icon-txt" />
                          <span class="file-name">{{ f.file }}</span>
                          <span class="file-change">{{ f.change_type === 'modified' ? '修改' : '新增' }}</span>
                          <span class="file-size">{{ formatSize(f.size) }}</span>
                          <i class="el-icon-top-right file-open-icon" />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <!-- 无会话时显示引导 -->
          <div v-else class="no-session-placeholder">
            <div class="placeholder-icon"><i class="el-icon-s-promotion" /></div>
            <h3>多 Agent 协作沙箱</h3>
            <p>配置左侧 API Key 和 Agent，点击「启动会话」创建容器</p>
            <div class="placeholder-tips">
              <div><i class="el-icon-check" /> 主持 Agent 自动分派任务</div>
              <div><i class="el-icon-check" /> 实时查看每个 Agent 的进度</div>
              <div><i class="el-icon-check" /> 文件写入容器内，不影响宿主系统</div>
            </div>
          </div>

          <!-- ===== 输入区 - 始终显示 ===== -->
          <!-- 文件浏览/预览对话框 -->
          <el-dialog :title="previewTitle" :visible.sync="previewVisible"
            width="78%" top="5vh" :close-on-click-modal="true"
            custom-class="file-preview-dialog">
            <div v-loading="previewLoading" class="file-browser-body">
              <div v-if="fileTreeData" class="file-tree-panel">
                <div class="file-scope-tabs">
                  <el-button
                    size="mini"
                    :type="fileScope === 'workspace' ? 'primary' : 'text'"
                    @click="switchFileScope('workspace')">
                    全部
                  </el-button>
                  <el-button
                    size="mini"
                    :type="fileScope === 'shared' ? 'primary' : 'text'"
                    @click="switchFileScope('shared')">
                    公共
                  </el-button>
                  <el-dropdown trigger="click" @command="switchFileScope">
                    <el-button size="mini" :type="fileScope.startsWith('agent:') ? 'primary' : 'text'">
                      Agent<i class="el-icon-arrow-down el-icon--right" />
                    </el-button>
                    <el-dropdown-menu slot="dropdown">
                      <el-dropdown-item
                        v-for="ag in sessionAgents"
                        :key="ag.agent_id"
                        :command="`agent:${ag.agent_id}`">
                        {{ ag.role || ag.agent_id }} / {{ ag.agent_id }}
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </el-dropdown>
                </div>
                <div class="file-tree-header">
                  <span>{{ fileTreeRoot }}</span>
                  <el-button size="mini" type="text" @click="loadFileTree(fileTreeRoot)">刷新</el-button>
                </div>
                <el-tree
                  :data="fileTreeData"
                  :props="fileTreeProps"
                  node-key="path"
                  default-expand-all
                  @node-click="handleFileNodeClick">
                  <span slot-scope="{ node, data }" class="file-tree-node">
                    <i :class="data.type === 'directory' ? 'el-icon-folder' : getFileIcon(data.path)" />
                    <span>{{ node.label }}</span>
                    <span v-if="data.size" class="tree-file-size">{{ formatSize(data.size) }}</span>
                  </span>
                </el-tree>
              </div>
              <div class="file-preview-panel">
                <div class="file-preview-toolbar" v-if="selectedFilePath">
                  <span class="selected-file-path">{{ selectedFilePath }}</span>
                  <el-button size="mini" type="text" @click="openContainingFolder(selectedFilePath)">所在目录</el-button>
                  <el-button size="mini" type="text" @click="copyFilePath(selectedFilePath)">复制路径</el-button>
                  <el-button size="mini" type="text" @click="downloadFile(selectedFilePath)">下载</el-button>
                  <el-button v-if="isHtmlFile(selectedFilePath)" size="mini" type="text" @click="openWorkspaceFile(selectedFilePath)">打开 HTML</el-button>
                </div>
                <div v-else class="file-preview-empty">
                  <i class="el-icon-folder-opened" />
                  <span>选择左侧文件查看内容</span>
                </div>
                <div v-if="previewType === 'image'" class="image-preview-wrap">
                  <img :src="previewUrl" class="image-preview" />
                </div>
                <iframe v-else-if="previewType === 'html'" :src="previewUrl" class="html-preview" />
                <iframe v-else-if="previewType === 'pdf'" :src="previewUrl" class="pdf-preview" />
                <div v-else-if="previewType === 'binary'" class="binary-preview">
                  <i class="el-icon-document" />
                  <p>该文件为二进制或不支持内嵌预览，请下载查看。</p>
                </div>
                <pre v-else class="file-preview-content">{{ previewContent }}</pre>
              </div>
            </div>
          </el-dialog>
          <div class="chat-input-area">
            <el-input v-model="inputText" type="textarea" :rows="3" resize="none"
              :placeholder="inputPlaceholder"
              @keydown.enter.ctrl="handleSend" :disabled="messageLoading" />
            <div class="input-actions">
              <span class="input-hint">
                <i class="el-icon-info" /> Ctrl+Enter 发送
                <template v-if="!currentSession"> · 请先在左侧「启动会话」</template>
              </span>
              <div class="input-buttons">
                <el-button size="small" @click="inputText = ''" :disabled="messageLoading || !inputText">清空</el-button>
                <el-button v-if="!currentSession" size="small" type="success" @click="triggerCreateSession">
                  <i class="el-icon-video-play" /> 启动会话
                </el-button>
                <el-button v-else type="primary" @click="handleSend" :loading="messageLoading"
                  :disabled="!inputText.trim()" size="small">
                  <i :class="sendMode === 'chain' ? 'el-icon-sort' : 'el-icon-position'" />
                  {{ sendMode === 'chain' ? '分派任务' : '发送' }}
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import AppSidebar from '../components/Sidebar/index.vue'
import socketClient from '../utils/socket'
import {
  getImageStatus, buildImage,
  createSession, listSessions, destroySession,
  sendMessage,
  getAgentEvents,
  addSessionAgent,
  stopAgent, readAgentFile, getAgentFileUrl, getWorkspaceFileUrl,
  getFileTree, getSessionRawFileUrl, getSessionDownloadUrl,
  listServices,
} from '../api/sandbox'

const MODERATOR_PRESET = `你是主持 Agent（Moderator），职责严格限定为：
1. 分析用户需求，拆解为具体任务清单
2. 将任务分派给对应的专业 Agent（writer=文档, frontend=前端）

## 绝对禁止（覆盖下方所有其他指令）
- ❌ 不能写代码、文档或页面
- ❌ 不能输出任何文件内容
- ❌ 不能使用代码块 \\\`\\\`\\\` 输出文件
- ❌ 不能替 writer 或 frontend 完成工作
- ❌ 你的回复必须只包含中文文字描述，不含任何代码块

## 输出格式要求
你只需输出：需求分析 + 任务分派计划。
必须明确告诉各 Agent：
- writer 正式文档只能写入 /workspace/agents/writer/
- frontend 正式前端代码只能写入 /workspace/agents/frontend/
- /workspace/shared/ 只放任务分工、简短摘要、接口约定，不放完整成品，不放重复 HTML/CSS/JS
不要输出任何代码块、文件内容或 ## /workspace/ 前缀。`

const WRITER_PRESET = `你是文档工程师（writer），职责严格限定为：
- 只写技术文档和规范，使用 markdown 格式（.md 文件）
- 输出清晰、结构化的文档
- 正式文档只能写入 /workspace/agents/writer/
- /workspace/shared/ 只允许写简短摘要或协作约定，不能复制完整文档

## 绝对禁止
- ❌ 不能写 HTML/CSS/JS 页面
- ❌ 不能写代码
- ❌ 不能替前端工程师完成工作`

const FRONTEND_PRESET = `你是前端工程师（frontend），职责严格限定为：
- 只写 HTML/CSS/JS 页面，确保美观、响应式
- 包含完整的交互逻辑
- 正式前端文件只能写入 /workspace/agents/frontend/
- 可以读取 /workspace/shared/，但禁止把 HTML/CSS/JS/Vue/React 成品或副本写入 /workspace/shared/

## 绝对禁止
- ❌ 不能写文档（.md 文件）
- ❌ 不能写后端代码
- ❌ 不能替文档工程师完成工作`

export default {
  name: 'SandboxTest',
  components: { AppSidebar },
  data() {
    return {
      imageReady: false, checkingImage: false, buildingImage: false,

      envVars: {
        ANTHROPIC_API_KEY: '',
        ANTHROPIC_BASE_URL: 'https://api.deepseek.com/anthropic',
        ANTHROPIC_MODEL: 'deepseek-v4-flash',
      },

      agents: [
        { agent_id: 'moderator', role: '主持', system_prompt: MODERATOR_PRESET },
        { agent_id: 'writer', role: '文档', system_prompt: WRITER_PRESET },
        { agent_id: 'frontend', role: '前端', system_prompt: FRONTEND_PRESET },
      ],

      sessions: [],
      loadingSessions: false, creatingSession: false,
      currentSession: null,

      // Agent 实时状态: { agent_id: { status, message, time } }
      agentStatus: {},

      sendMode: 'chain',
      currentAgentId: '',
      inputText: '',
      currentMessages: [],
      messageLoading: false,
      loadingAgent: '',

      moderatorPreset: MODERATOR_PRESET,
      writerPreset: WRITER_PRESET,
      frontendPreset: FRONTEND_PRESET,


      // Per-agent display panels (replaces flat message list)
      agentDisplays: {},
      replyExpanded: {}, // { agent_id: true/false }
      agentEventSeq: {},
      eventPollTimer: null,
      chatStickToBottom: true,

      // Add the stopAgent and readAgentFile API functions to the component
      _stopAgentApi: stopAgent,
      _readAgentFileApi: readAgentFile,

      services: [],

      // File preview dialog
      previewVisible: false,
      previewTitle: '',
      previewContent: '',
      previewLoading: false,
      previewType: 'text',
      previewUrl: '',
      selectedFilePath: '',
      fileTreeData: null,
      fileTreeRoot: '/workspace',
      fileScope: 'workspace',
      fileTreeProps: {
        label: 'name',
        children: 'children',
      },
    }
  },

  computed: {
    sessionAgents() {
      return this.currentSession?.agents || this.agents
    },
    chainAgents() {
      return this.currentSession?.agents || this.agents
    },
    agentDisplayList() {
      // Convert agentDisplays object to sorted array for template iteration
      const agents = this.currentSession?.agents || this.agents
      const order = agents.map(a => a.agent_id)
      const list = Object.values(this.agentDisplays)
      list.sort((a, b) => order.indexOf(a.agent_id) - order.indexOf(b.agent_id))
      return list
    },
    lastUserMessage() {
      // Find the most recent user message from currentMessages
      for (let i = this.currentMessages.length - 1; i >= 0; i--) {
        if (this.currentMessages[i].role === 'user') {
          const text = this.currentMessages[i].content
          return text.length > 120 ? text.slice(0, 120) + '...' : text
        }
      }
      return ''
    },
    inputPlaceholder() {
      if (!this.currentSession) return '请先在左侧配置 API Key 并点击「启动会话」...'
      return this.sendMode === 'chain'
        ? '输入需求，主持 Agent 会自动分派...'
        : '输入消息...'
    },
  },

  mounted() {
    this.checkImage()
    this.refreshSessions()
    this.loadSavedEnv()
    this.initSocket()
  },

  beforeDestroy() {
    // Leave session room and disconnect socket
    if (this.currentSession) {
      socketClient.leaveConversation(this.currentSession.session_id)
    }
    this.stopEventPolling()
    socketClient.off('sandbox_event', this.onSandboxEvent)
  },

  methods: {

    // ===== SocketIO =====
    initSocket() {
      socketClient.connect()
      socketClient.on('sandbox_event', this.onSandboxEvent)
    },

    onSandboxEvent(data) {
      // data: { session_id, agent_id, type, data, seq }
      if (data.session_id && this.currentSession && data.session_id !== this.currentSession.session_id) return
      const agentId = data.agent_id
      if (!agentId) return

      if (data.type === 'agent_added') {
        const agent = data.data?.agent
        if (agent && this.currentSession && !(this.currentSession.agents || []).some(a => a.agent_id === agent.agent_id)) {
          this.currentSession.agents = [...(this.currentSession.agents || []), agent]
        this.$set(this.agentDisplays, agent.agent_id, {
            agent_id: agent.agent_id,
            role: agent.role || agent.agent_id,
            status: 'idle',
            statusMessage: '等待任务',
            events: [],
            files: [],
            reply: '',
            error: null,
          })
          this.$set(this.agentEventSeq, agent.agent_id, 0)
          this.updateAgentStatus(agent.agent_id, 'idle', '等待任务')
        }
        return
      }

      if (data.type === 'agent_removed') {
        if (this.currentSession) {
          this.currentSession.agents = (this.currentSession.agents || []).filter(a => a.agent_id !== agentId)
        }
        this.$delete(this.agentDisplays, agentId)
        this.$delete(this.agentStatus, agentId)
        return
      }

      // Forward to displayEvent for rendering
      const ev = {
        type: data.type,
        data: data.data,
        seq: data.seq || 0,
      }
      if (ev.seq) this.$set(this.agentEventSeq, agentId, Math.max(this.agentEventSeq[agentId] || 0, ev.seq))
      this.displayEvent(agentId, ev)
    },
    startEventPolling() {
      this.stopEventPolling()
      this.agentEventSeq = {}
      ;(this.currentSession?.agents || []).forEach(a => {
        this.$set(this.agentEventSeq, a.agent_id, 0)
      })
      this.fetchAgentEvents()
      this.eventPollTimer = window.setInterval(() => this.fetchAgentEvents(), 1000)
    },
    stopEventPolling() {
      if (this.eventPollTimer) {
        window.clearInterval(this.eventPollTimer)
        this.eventPollTimer = null
      }
    },
    async fetchAgentEvents() {
      if (!this.currentSession?.session_id) return
      const sessionId = this.currentSession.session_id
      const agents = this.currentSession.agents || []
      await Promise.all(agents.map(async agent => {
        const agentId = agent.agent_id
        const since = this.agentEventSeq[agentId] || 0
        try {
          const res = await getAgentEvents(sessionId, agentId, since)
          const events = res?.data?.events || []
          events.forEach(ev => {
            const seq = ev.seq || 0
            if (seq <= (this.agentEventSeq[agentId] || 0)) return
            this.$set(this.agentEventSeq, agentId, seq)
            this.displayEvent(agentId, ev)
          })
        } catch (e) {
          // SocketIO remains the primary channel; polling is a silent fallback.
        }
      }))
    },
    // ===== Agent 状态管理 =====
    updateAgentStatus(agentId, status, message = '') {
      this.$set(this.agentStatus, agentId, {
        status, // idle | thinking | working | done | error
        message,
        time: this.now(),
      })
    },
    resetAgentStatuses() {
      const agents = this.currentSession?.agents || this.agents
      agents.forEach(a => {
        this.updateAgentStatus(a.agent_id, 'idle', '等待任务')
      })
    },
    getAgentStatusMsg(agentId) {
      return this.agentStatus[agentId]?.message || '等待任务'
    },
    getAgentStatusTime(agentId) {
      return this.agentStatus[agentId]?.time || ''
    },
    getStatusClass(agentId) {
      const s = this.agentStatus[agentId]?.status
      return s ? `status-${s}` : ''
    },
    getStatusDot(agentId) {
      const s = this.agentStatus[agentId]?.status || 'idle'
      return `dot-${s}`
    },

    // ===== Persist =====
    loadSavedEnv() {
      try {
        const saved = JSON.parse(localStorage.getItem('sandbox_env') || '{}')
        if (saved.ANTHROPIC_API_KEY) this.envVars.ANTHROPIC_API_KEY = saved.ANTHROPIC_API_KEY
        if (saved.ANTHROPIC_BASE_URL) this.envVars.ANTHROPIC_BASE_URL = saved.ANTHROPIC_BASE_URL
        if (saved.ANTHROPIC_MODEL) this.envVars.ANTHROPIC_MODEL = saved.ANTHROPIC_MODEL
      } catch (e) { /* ignore */ }
    },
    saveEnv() {
      try { localStorage.setItem('sandbox_env', JSON.stringify(this.envVars)) } catch (e) { /* ignore */ }
    },
    cleanEnvValue(value) {
      let text = String(value || '').trim()
      return text.replace(/^[\s'"]+|[\s'"]+$/g, '')
    },
    normalizedEnvVars() {
      const env = { ...this.envVars }
      ;['ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_BASE_URL', 'ANTHROPIC_MODEL', 'DEEPSEEK_API_KEY', 'DEEPSEEK_BASE_URL', 'DEEPSEEK_MODEL'].forEach(key => {
        if (env[key]) env[key] = this.cleanEnvValue(env[key])
      })
      if (env.ANTHROPIC_BASE_URL) env.ANTHROPIC_BASE_URL = env.ANTHROPIC_BASE_URL.replace(/\/+$/, '')
      if (env.DEEPSEEK_BASE_URL) env.DEEPSEEK_BASE_URL = env.DEEPSEEK_BASE_URL.replace(/\/+$/, '')
      return env
    },

    // ===== Image =====
    async checkImage() {
      this.checkingImage = true
      try {
        const res = await getImageStatus()
        if (res.code === 200) this.imageReady = res.data.ready
      } catch (e) { /* ignore */ }
      this.checkingImage = false
    },
    async handleBuildImage() {
      this.buildingImage = true
      try {
        const res = await buildImage()
        if (res.code === 200) { this.$message.success('镜像构建成功'); this.imageReady = true }
      } catch (e) { this.$message.error('构建失败: ' + (e.message || '')) }
      this.buildingImage = false
    },

    // ===== Agents =====
    addAgent() { this.agents.push({ agent_id: '', role: '', system_prompt: '' }) },
    removeAgent(i) { this.agents.splice(i, 1) },

    // ===== Sessions =====
    triggerCreateSession() {
      // Scroll the left panel's start button into view
      const btn = this.$el.querySelector('.start-btn')
      if (btn) btn.scrollIntoView({ behavior: 'smooth', block: 'center' })
      this.$message.info('请先在左侧填写 API Key 并点击「启动会话」')
    },
    async refreshSessions() {
      this.loadingSessions = true
      try { const res = await listSessions(); if (res.code === 200) this.sessions = res.data || [] } catch (e) { /* ignore */ }
      this.loadingSessions = false
    },

    async handleCreateSession() {
      const validAgents = this.agents.filter(a => a.agent_id && a.role)
      if (!validAgents.length) return this.$message.warning('至少需要一个 Agent')
      if (!this.envVars.ANTHROPIC_API_KEY) return this.$message.warning('请填写 API Key')
      this.saveEnv()
      this.creatingSession = true
      try {
        const res = await createSession({
          session_id: `session-${Date.now()}`,
          agents: validAgents.map(a => ({
            agent_id: a.agent_id, role: a.role,
            system_prompt: a.system_prompt || `你是一个${a.role}`,
          })),
          env_vars: this.normalizedEnvVars(),
        })
        if (res.code === 201) {
          this.$message.success('会话创建成功')
          this.currentSession = res.data

          // Join socket room for real-time events
          socketClient.joinConversation(res.data.session_id)

          this.currentMessages = []
          this.currentAgentId = validAgents[0]?.agent_id || ''
          this.resetAgentStatuses()
          this.initAgentDisplays()
          this.startEventPolling()
          this.addProgressMsg('system', '会话已启动，容器就绪')
          await this.refreshSessions()
        }
      } catch (e) { this.$message.error('创建失败: ' + (e?.response?.data?.message || e.message)) }
      this.creatingSession = false
    },

    async selectSession(session) {
      const oldId = this.currentSession?.session_id
      if (oldId && oldId !== session.session_id) {
        socketClient.leaveConversation(oldId)
      }
      this.currentSession = session
      socketClient.joinConversation(session.session_id)
      this.currentMessages = []
      this.currentAgentId = session.agents?.[0]?.agent_id || ''
      this.services = []
      this.resetAgentStatuses()
      this.initAgentDisplays()
      this.startEventPolling()
      this.addProgressMsg('system', `已切换到会话: ${session.session_id}`)
      await this.refreshServices(false)
    },

    async handleDestroySession() {
      if (!this.currentSession) return
      try {
        await this.$confirm('销毁容器会丢失所有未保存的文件，确认？', '提示', { type: 'warning' })
        const sessionId = this.currentSession.session_id
        await destroySession(sessionId)
        socketClient.leaveConversation(sessionId)
        this.stopEventPolling()
        this.$message.success('会话已销毁')
        this.currentSession = null; this.currentMessages = []; this.services = []
        await this.refreshSessions()
      } catch (e) { if (e !== 'cancel') this.$message.error('销毁失败') }
    },

    // ===== Send =====
    async handleSend() {
      const text = this.inputText.trim()
      if (!text || !this.currentSession) return
      this.currentMessages.push({ role: 'user', content: text, time: this.now() })
      this.inputText = ''

      if (this.sendMode === 'chain') {
        await this.handleChainSend(text)
      } else {
        await this.handleDirectSend(text)
      }
      this.$nextTick(() => this.scrollChat())
    },

    async handleChainSend(text) {
      this.messageLoading = true
      this.resetAgentStatuses()
      const sessionId = this.currentSession.session_id
      const agents = this.currentSession?.agents || this.agents
      const moderator = agents.find(a => a.agent_id === 'moderator') || agents[0]

      try {
        if (moderator) {
          this.updateAgentStatus(moderator.agent_id, 'thinking', '主持分派中...')
          this.updateAgentDisplay(moderator.agent_id, { status: 'thinking', statusMessage: '等待 Claude Code 回复...' })
        }
        const res = await sendMessage(sessionId, '', text)
        if (res.code === 200 && res.data) {
          const data = res.data
          if (data.status === 'error') {
            const errorText = data.error || data.moderator_result?.error || '主持分派失败'
            if (moderator) {
              this.updateAgentStatus(moderator.agent_id, 'error', errorText)
              this.updateAgentDisplay(moderator.agent_id, { status: 'error', statusMessage: '分派失败', error: errorText })
              this.pushAgentEvent(moderator.agent_id, 'error', errorText)
            }
            this.addProgressMsg('system', '主持分派失败: ' + errorText, 'error')
            return
          }
          if (data.moderator_result?.reply && moderator) {
            this.updateAgentStatus(moderator.agent_id, 'done', '分派完成')
          }
          ;(data.results || []).forEach(item => {
            const agentId = item.agent_id
            const agent = agents.find(a => a.agent_id === agentId) || { role: agentId }
            if (item.reply) {
              this.updateAgentStatus(agentId, 'done', '任务完成')
              this.updateAgentDisplay(agentId, { status: 'done', statusMessage: '已回复' })
            } else if (item.status === 'error') {
              this.updateAgentStatus(agentId, 'error', '执行出错')
              this.updateAgentDisplay(agentId, { status: 'error', statusMessage: '执行出错', error: item.error })
            }
          })
          this.addProgressMsg('system', '后端主持分派已完成', 'done')
        }
      } catch (e) {
        const errorText = e?.data?.error || e?.data?.message || e?.message || '请求失败'
        if (moderator) {
          this.updateAgentStatus(moderator.agent_id, 'error', errorText)
          this.updateAgentDisplay(moderator.agent_id, { status: 'error', statusMessage: '分派失败', error: errorText })
          this.pushAgentEvent(moderator.agent_id, 'error', errorText)
        }
        this.pushAgentMsg(moderator?.agent_id || 'system', 'Error', '分派执行失败: ' + errorText)
      }
      this.messageLoading = false
    },

    // ===== 事件显示 =====
    normalizeProviderEventType(type) {
      return {
        provider_started: 'claude_started',
        provider_output: 'claude_output',
        provider_output_delta: 'claude_output_delta',
        provider_error: 'claude_error',
        provider_error_delta: 'claude_error_delta',
        provider_stopped: 'claude_stopped',
      }[type] || type
    },

    displayEvent(agentId, ev) {
      const type = this.normalizeProviderEventType(ev.type)
      const data = ev.data || {}

      if (type === 'agent_task_started' || type === 'delegation_target_started' || type === 'delegation_started') {
        const d = this.agentDisplays[agentId]
        if (d) {
          d.reply = ''
          d.error = null
          d.files = []
        }
        this.updateAgentStatus(agentId, 'thinking', data.message || '开始处理')
        this.updateAgentDisplay(agentId, { status: 'thinking', statusMessage: data.message || '处理中...' })
      } else if (type === 'claude_started') {
        this.updateAgentStatus(agentId, 'working', 'Claude Code 已启动')
        this.updateAgentDisplay(agentId, { status: 'working', statusMessage: '等待 Claude Code 输出...' })
      } else if (type === 'agent_progress') {
        const message = data.message || 'Agent 正在执行'
        this.updateAgentStatus(agentId, 'working', message)
        this.updateAgentDisplay(agentId, { status: 'working', statusMessage: message })
      } else if (type === 'claude_output') {
        const output = data.output || ''
        this.updateAgentStatus(agentId, 'done', 'Claude Code 已回复')
        this.updateAgentDisplay(agentId, { reply: output, status: 'done', statusMessage: 'Claude Code 已回复' })
        this.$set(this.replyExpanded, agentId, true)
      } else if (type === 'claude_output_delta') {
        const chunk = data.chunk || ''
        const d = this.agentDisplays[agentId]
        if (d && chunk) {
          d.reply = (d.reply || '') + chunk
          d.status = 'working'
          d.statusMessage = 'Claude Code 正在回复...'
        }
        this.updateAgentStatus(agentId, 'working', 'Claude Code 正在回复...')
        this.$set(this.replyExpanded, agentId, true)
        this.$nextTick(() => this.scrollChat())
      } else if (type === 'claude_error') {
        const output = data.output || ''
        this.updateAgentDisplay(agentId, { error: output, statusMessage: 'Claude Code 错误输出' })
        this.pushAgentEvent(agentId, 'claude_error', output)
      } else if (type === 'claude_error_delta') {
        const chunk = data.chunk || ''
        const d = this.agentDisplays[agentId]
        if (d && chunk) {
          d.error = (d.error || '') + chunk
          d.statusMessage = 'Claude Code 错误输出'
        }
        this.$nextTick(() => this.scrollChat())
      } else if (type === 'file_write') {
        const fileInfo = { file: data.file, size: data.size || 0, change_type: data.change_type || 'created' }
        const d = this.agentDisplays[agentId]
        if (d) {
          const existing = d.files.find(f => f.file === data.file)
          if (existing) {
            Object.assign(existing, fileInfo)
          } else {
            d.files.push(fileInfo)
          }
        }
      } else if (type === 'agent_task_completed' || type === 'delegation_complete') {
        this.updateAgentStatus(agentId, 'done', '已完成')
        this.updateAgentDisplay(agentId, { status: 'done', statusMessage: '已完成' })
      } else if (type === 'file_policy') {
        // Keep policy events out of the dialogue; files list reflects the final allowed paths.
      } else if (type === 'error') {
        this.updateAgentStatus(agentId, 'error', data.error || '出错')
        this.updateAgentDisplay(agentId, { status: 'error', statusMessage: '出错', error: data.error })
        this.pushAgentEvent(agentId, 'error', data.error || '出错')
      }
    },

    getAgentRole(agentId) {
      const agents = this.currentSession?.agents || this.agents
      const a = agents.find(x => x.agent_id === agentId)
      return a?.role || agentId
    },

    async handleDirectSend(text) {
      const agentId = this.currentAgentId
      const agent = (this.currentSession?.agents || this.agents).find(a => a.agent_id === agentId)
      if (!agent) return

      this.messageLoading = true
      this.loadingAgent = agent.role || agentId
      this.updateAgentStatus(agentId, 'thinking', '思考中...')
      this.updateAgentDisplay(agentId, { status: 'thinking', statusMessage: '等待 Claude Code 回复...' })

      try {
        const res = await sendMessage(this.currentSession.session_id, agentId, text)
        if (res.code === 200 && res.data?.reply) {
          this.updateAgentStatus(agentId, 'done', '完成')
          this.updateAgentDisplay(agentId, { status: 'done', statusMessage: '已回复' })
        } else if (res.data?.status === 'error') {
          this.updateAgentStatus(agentId, 'error', '执行出错')
          this.pushAgentMsg(agentId, 'Error', '错误: ' + (res.data.error || '执行失败'))
        }
      } catch (e) {
        this.updateAgentStatus(agentId, 'error', '请求失败')
        this.pushAgentMsg(agentId, 'Error', '请求失败: ' + (e?.response?.data?.message || e.message))
      }
      this.messageLoading = false
    },

    // ===== Agent Display Panels =====
    initAgentDisplays() {
      const agents = this.currentSession?.agents || this.agents
      this.agentDisplays = {}
      this.agentEventSeq = {}
      agents.forEach(a => {
        this.$set(this.agentDisplays, a.agent_id, {
          agent_id: a.agent_id,
          role: a.role || a.agent_id,
          status: 'idle',
          statusMessage: '等待任务',
          events: [],
          files: [],
          reply: '',
          error: null,
        })
        this.$set(this.replyExpanded, a.agent_id, false)
        this.$set(this.agentEventSeq, a.agent_id, 0)
      })
    },

    updateAgentDisplay(agentId, updates) {
      const d = this.agentDisplays[agentId]
      if (d) Object.assign(d, updates)
    },

    pushAgentEvent(agentId, type, text, extra = {}) {
      const d = this.agentDisplays[agentId]
      if (!d) return
      const ev = { type, text, time: this.now(), ...extra }
      d.events.push(ev)
      // Auto-scroll when new events arrive
      this.$nextTick(() => this.scrollChat())
    },

    // ===== Stop Agent =====
    async handleStopAgent(agentId) {
      if (!this.currentSession) return
      try {
        const res = await stopAgent(this.currentSession.session_id, agentId)
        if (res.code === 200) {
          this.$message.success(`已停止 ${agentId}`)
          this.updateAgentDisplay(agentId, {
            status: 'stopped',
            statusMessage: '已停止',
          })
        } else {
          this.$message.warning('停止请求已发送')
        }
      } catch (e) {
        this.$message.error('停止失败: ' + (e?.response?.data?.message || e.message))
      }
    },

    // ===== Dynamic agents / services =====
    async addAgentToCurrentSession() {
      if (!this.currentSession) return
      try {
        const { value } = await this.$prompt('格式：agent_id,角色,系统提示词（提示词可省略）', '添加 Agent', {
          confirmButtonText: '添加',
          cancelButtonText: '取消',
          inputPlaceholder: 'designer,设计师,你负责 UI 设计',
        })
        const parts = value.split(',').map(v => v.trim())
        const [agentId, role, prompt] = parts
        if (!agentId || !role) return this.$message.warning('请填写 agent_id 和角色')
        const res = await addSessionAgent(this.currentSession.session_id, {
          agent_id: agentId,
          role,
          system_prompt: prompt || `你是${role}`,
        })
        if (res.code === 201) {
          const agent = res.data?.agent || { agent_id: agentId, role, system_prompt: prompt || `你是${role}` }
          if (!(this.currentSession.agents || []).some(a => a.agent_id === agentId)) {
            this.currentSession.agents = [...(this.currentSession.agents || []), agent]
          }
          this.$set(this.agentDisplays, agentId, {
            agent_id: agentId,
            role,
            status: 'idle',
            statusMessage: '等待任务',
            events: [],
            files: [],
            reply: '',
            error: null,
          })
          this.$set(this.agentEventSeq, agentId, 0)
          this.updateAgentStatus(agentId, 'idle', '等待任务')
          this.currentAgentId = agentId
          this.$message.success('Agent 已添加')
        }
      } catch (e) {
        if (e !== 'cancel') this.$message.error('添加失败: ' + (e?.response?.data?.message || e.message))
      }
    },

    async refreshServices(showMessage = true) {
      if (!this.currentSession) return
      try {
        const res = await listServices(this.currentSession.session_id)
        if (res.code === 200) {
          this.services = res.data?.services || []
          if (showMessage) this.$message.success('服务状态已刷新')
        }
      } catch (e) {
        if (showMessage) this.$message.error('获取服务失败: ' + (e?.response?.data?.message || e.message))
      }
    },

    openService(svc) {
      const url = svc.url || (svc.host_port ? `http://localhost:${svc.host_port}` : '')
      if (url) window.open(url, '_blank')
    },

    // ===== File browsing =====
    async handleBrowseFiles(agentId = '') {
      if (!this.currentSession) return
      const root = agentId ? `/workspace/agents/${agentId}` : '/workspace'
      this.fileScope = agentId ? `agent:${agentId}` : 'workspace'
      this.previewVisible = true
      this.previewTitle = agentId ? `${agentId} 文件` : '全部文件'
      this.fileTreeRoot = root
      this.previewContent = '请选择左侧文件预览'
      this.previewType = 'text'
      this.selectedFilePath = ''
      await this.loadFileTree(root)
    },

    async switchFileScope(scope) {
      if (!this.currentSession) return
      let root = '/workspace'
      let title = '全部文件'
      if (scope === 'shared') {
        root = '/workspace/shared'
        title = '公共目录'
      } else if (scope && scope.startsWith('agent:')) {
        const agentId = scope.slice('agent:'.length)
        root = `/workspace/agents/${agentId}`
        const agent = (this.currentSession.agents || []).find(a => a.agent_id === agentId)
        title = `${agent?.role || agentId} 文件`
      }
      this.fileScope = scope || 'workspace'
      this.previewTitle = title
      this.previewContent = '请选择左侧文件预览'
      this.previewType = 'text'
      this.previewUrl = ''
      this.selectedFilePath = ''
      await this.loadFileTree(root)
    },

    async loadFileTree(root) {
      if (!this.currentSession) return
      this.previewLoading = true
      try {
        const res = await getFileTree(this.currentSession.session_id, root)
        if (res.code === 200 && res.data?.tree) {
          this.fileTreeData = [res.data.tree]
          this.fileTreeRoot = root
        }
      } catch (e) {
        this.$message.error('获取文件树失败: ' + (e?.response?.data?.message || e.message))
      }
      this.previewLoading = false
    },

    handleFileNodeClick(data) {
      if (data.type === 'directory') {
        this.selectedFilePath = ''
        this.previewContent = '请选择左侧文件预览'
        this.previewType = 'text'
        this.previewUrl = ''
        this.loadFileTree(data.path)
        return
      }
      this.previewFile('', data.path)
    },

    openFileInTab(agentId, filePath) {
      if (!this.currentSession) return
      this.previewVisible = true
      this.fileTreeRoot = agentId ? `/workspace/agents/${agentId}` : '/workspace'
      this.fileScope = agentId ? `agent:${agentId}` : 'workspace'
      this.loadFileTree(this.fileTreeRoot)
      this.previewFile(agentId, filePath)
    },

    openContainingFolder(path) {
      if (!path) return
      const normalized = path.replace(/\\/g, '/')
      const idx = normalized.lastIndexOf('/')
      if (idx <= 0) return
      this.loadFileTree(normalized.slice(0, idx))
    },

    openWorkspaceFile(filePath) {
      if (!this.currentSession) return
      window.open(getWorkspaceFileUrl(this.currentSession.session_id, filePath), '_blank')
    },

    previewFile(agentId, filePath) {
      if (!this.currentSession) return
      this.previewLoading = true
      this.previewVisible = true
      this.previewTitle = filePath
      this.previewContent = ''
      this.previewUrl = ''
      this.selectedFilePath = filePath

      const ext = this.getExt(filePath)
      const sessionId = this.currentSession.session_id
      if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'].includes(ext)) {
        this.previewType = 'image'
        this.previewUrl = getSessionRawFileUrl(sessionId, filePath)
        this.previewLoading = false
        return
      }
      if (ext === 'pdf') {
        this.previewType = 'pdf'
        this.previewUrl = getSessionRawFileUrl(sessionId, filePath)
        this.previewLoading = false
        return
      }
      if (this.isHtmlFile(filePath)) {
        this.previewType = 'html'
        this.previewUrl = getWorkspaceFileUrl(sessionId, filePath)
        this.previewLoading = false
        return
      }
      if (!['txt', 'md', 'json', 'js', 'css', 'vue', 'html', 'htm', 'py', 'yml', 'yaml', 'xml', 'csv', 'log'].includes(ext)) {
        this.previewType = 'binary'
        this.previewLoading = false
        return
      }

      this.previewType = 'text'
      readAgentFile(sessionId, agentId || (this.currentSession.agents?.[0]?.agent_id || ''), filePath)
        .then(res => {
          if (res.code === 200 && res.data?.content !== undefined) {
            this.previewContent = res.data.content
          } else {
            this.previewContent = '无法读取文件: ' + (res.data?.error || '未知错误')
          }
        })
        .catch(e => {
          this.previewContent = '加载失败: ' + (e?.response?.data?.message || e.message)
        })
        .finally(() => { this.previewLoading = false })
    },

    downloadFile(path) {
      if (!this.currentSession || !path) return
      window.open(getSessionDownloadUrl(this.currentSession.session_id, path), '_blank')
    },

    copyFilePath(path) {
      if (!path) return
      navigator.clipboard?.writeText(path)
      this.$message.success('路径已复制')
    },

    toggleReply(agentId) {
      this.$set(this.replyExpanded, agentId, !this.replyExpanded[agentId])
    },

    formatSize(bytes) {
      if (!bytes) return ''
      if (bytes < 1024) return bytes + 'B'
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'KB'
      return (bytes / 1024 / 1024).toFixed(1) + 'MB'
    },
    getExt(path) {
      return (path || '').split('.').pop().toLowerCase()
    },
    isHtmlFile(path) {
      return ['html', 'htm'].includes(this.getExt(path))
    },
    getFileIcon(path) {
      const ext = this.getExt(path)
      if (this.isHtmlFile(path)) return 'el-icon-monitor'
      if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'].includes(ext)) return 'el-icon-picture'
      if (ext === 'pdf') return 'el-icon-document'
      return 'el-icon-tickets'
    },

    // ===== Message helpers =====
    pushAgentMsg(agentId, label, content, toolResults) {
      this.currentMessages.push({
        role: 'agent', agent_id: agentId, agent_label: label || agentId,
        content: content, tool_results: toolResults || [], time: this.now(),
      })
      // Also update agent display panel
      this.updateAgentDisplay(agentId, { reply: content })
      this.$set(this.replyExpanded, agentId, true)
      // If there are tool results, add file events
      if (toolResults?.length) {
        toolResults.forEach(tr => {
          if (tr.file) {
            const d = this.agentDisplays[agentId]
            const fileInfo = { file: tr.file, size: tr.size || 0, change_type: tr.change_type || 'created' }
            if (d && !d.files.find(f => f.file === tr.file)) d.files.push(fileInfo)
          }
        })
      }
    },
    addProgressMsg(agentId, text, status = 'done') {
      this.currentMessages.push({
        role: 'progress', agent_id: agentId, content: text, status, time: this.now(),
      })
    },
    now() {
      const d = new Date()
      return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    },
    sleep(ms) { return new Promise(r => setTimeout(r, ms)) },
    handleChatScroll() {
      this.chatStickToBottom = this.isChatNearBottom()
    },
    isChatNearBottom() {
      const el = this.$refs.chatRef
      if (!el) return true
      const distance = el.scrollHeight - el.scrollTop - el.clientHeight
      return distance <= 100
    },
    scrollChat(force = false) {
      const el = this.$refs.chatRef
      if (el && (force || this.chatStickToBottom)) el.scrollTop = el.scrollHeight
    },

    // ===== Styling =====
    getAgentTagType(id) { return { moderator: 'warning', writer: 'success', frontend: 'primary' }[id] || 'info' },
    getAgentColor(id) { return { moderator: '#e6a23c', writer: '#67c23a', frontend: '#409eff' }[id] || '#909399' },
    getAgentIcon(id) { return { moderator: 'el-icon-s-operation', writer: 'el-icon-document', frontend: 'el-icon-monitor' }[id] || 'el-icon-s-platform' },
  },
}
</script>

<style scoped>
.sandbox-test {
  display: flex; gap: 12px; padding: 12px; height: 100vh;
  background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
  overflow: hidden;
}
.main-content { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

.page-header { margin-bottom: 6px; }
.page-header h1 { margin: 0; font-size: 20px; color: #e2e8f0; display: flex; align-items: center; }
.page-desc { margin: 2px 0 0; font-size: 12px; color: #64748b; }
.toolbar { margin-bottom: 6px; }
.toolbar .el-button { border-color: #334155; color: #cbd5e1; background: #1e293b; }
.toolbar .el-button:hover { border-color: #4080ff; color: #4080ff; }

.body-layout { flex: 1; display: flex; gap: 12px; overflow: hidden; }

/* ===== Left ===== */
.left-panel {
  width: 380px; flex-shrink: 0; overflow-y: auto;
  display: flex; flex-direction: column; gap: 6px;
}
.config-card { background: #1e293b; border: 1px solid #334155; border-radius: 10px; }
.config-card :deep(.el-card__header) { padding: 8px 14px; border-bottom: 1px solid #334155; }
.config-card :deep(.el-card__body) { padding: 10px 14px; }
.card-header { display: flex; align-items: center; justify-content: space-between; font-size: 13px; font-weight: 600; color: #e2e8f0; }
.card-header i { margin-right: 4px; }
.card-header .el-button { color: #4080ff; }
.config-card :deep(.el-form-item) { margin-bottom: 6px; }
.config-card :deep(.el-form-item__label) { color: #94a3b8; padding-bottom: 0; }
.config-card :deep(.el-input__inner),
.config-card :deep(.el-textarea__inner) { background: #0f172a; border-color: #334155; color: #e2e8f0; }

.agent-config-list { display: flex; flex-direction: column; gap: 6px; margin-bottom: 8px; }
.agent-config-item { background: #0f172a; border-radius: 8px; padding: 6px 10px; border: 1px solid #334155; }
.agent-config-item.is-moderator { border-color: #e6a23c44; }
.agent-config-header { display: flex; align-items: center; margin-bottom: 4px; }
.agent-prompt-input :deep(.el-textarea__inner) { font-size: 12px; line-height: 1.4; }
.prompt-presets { display: flex; gap: 4px; margin-top: 3px; }
.prompt-presets .el-tag {
  cursor: pointer; font-size: 10px; padding: 0 6px; height: 20px; line-height: 18px;
  border-color: #334155; background: transparent; color: #64748b;
}
.prompt-presets .el-tag:hover { color: #4080ff; border-color: #4080ff; }
.start-btn { width: 100%; }

.session-item { padding: 8px 10px; cursor: pointer; border-radius: 6px; margin-bottom: 2px; border: 1px solid transparent; transition: all 0.15s; }
.session-item:hover { background: #0f172a; border-color: #334155; }
.session-item.active { background: #1e3a5f; border-color: #4080ff; }
.session-top { display: flex; align-items: center; justify-content: space-between; }
.session-id { font-weight: 600; font-size: 12px; color: #e2e8f0; }
.session-meta { display: flex; gap: 12px; font-size: 11px; color: #64748b; margin-top: 2px; }
.empty-hint { text-align: center; padding: 16px; color: #64748b; font-size: 12px; }

/* ===== Right ===== */
.right-panel {
  flex: 1; display: flex; flex-direction: column;
  background: #1e293b; border-radius: 12px; border: 1px solid #334155; overflow: hidden;
}
.chat-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 16px; border-bottom: 1px solid #334155;
}
.chat-header-left { display: flex; align-items: center; gap: 8px; }
.chat-header-actions { display: flex; align-items: center; gap: 6px; }
.chat-header-actions .el-button { background: transparent; border-color: #334155; color: #94a3b8; }
.chat-header-actions .el-button:hover { border-color: #4080ff; color: #4080ff; }
.chat-session-id { font-weight: 600; font-size: 14px; color: #e2e8f0; }
.chat-header-right .el-button { border-color: #dc2626; color: #dc2626; background: transparent; }
.chat-header-right .el-button:hover { background: #dc262622; }
.service-bar {
  display: flex; align-items: center; gap: 6px; padding: 6px 16px;
  border-bottom: 1px solid #334155; background: #111827;
}
.service-title { font-size: 12px; color: #94a3b8; margin-right: 4px; }
.service-tag { cursor: pointer; }

/* ===== Agent 状态条 ===== */
.agent-status-bar {
  display: flex; gap: 6px; padding: 6px 16px;
  border-bottom: 1px solid #1e293b;
  background: #0f172a;
}
.agent-status-item {
  flex: 1; padding: 6px 10px; border-radius: 8px;
  border: 1px solid #334155; background: #1e293b;
  transition: all 0.3s;
}
.agent-status-item.status-thinking { border-color: #e6a23c; background: #2a1f0f; }
.agent-status-item.status-working { border-color: #409eff; background: #0f1f3a; }
.agent-status-item.status-done { border-color: #67c23a; background: #0f1f10; }
.agent-status-item.status-error { border-color: #f56c6c; background: #2a0f0f; }
.status-indicator { display: flex; align-items: center; gap: 6px; }
.status-dot {
  width: 8px; height: 8px; border-radius: 50%; display: inline-block;
  background: #475569; transition: all 0.3s;
}
.dot-thinking { background: #e6a23c; animation: pulse 1s infinite; }
.dot-working { background: #409eff; animation: pulse 0.8s infinite; }
.dot-done { background: #67c23a; }
.dot-error { background: #f56c6c; }
.dot-idle { background: #475569; }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

.status-role { font-size: 12px; font-weight: 600; color: #cbd5e1; }
.status-message { font-size: 10px; color: #64748b; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.status-time { font-size: 9px; color: #475569; margin-top: 1px; }
.status-folder-btn {
  float: right;
  padding: 0;
  margin-top: -18px;
  color: #64748b;
}
.status-folder-btn:hover { color: #4080ff; }

/* ===== Mode bar ===== */
.mode-bar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 6px 16px; border-bottom: 1px solid #334155; flex-wrap: wrap; gap: 4px;
}
.mode-bar :deep(.el-radio-button__inner) {
  background: #0f172a; border-color: #334155; color: #64748b;
  font-size: 12px; padding: 5px 10px;
}
.mode-bar :deep(.el-radio-button__orig-radio:checked + .el-radio-button__inner) {
  background: #4080ff; border-color: #4080ff; color: #fff; box-shadow: none;
}
.chain-label { font-size: 11px; color: #64748b; margin-right: 4px; }
.chain-agents { display: flex; align-items: center; flex-wrap: wrap; gap: 2px; }
.chain-agents .el-tag { font-size: 11px; }
.mode-bar :deep(.el-input__inner) { background: #0f172a; border-color: #334155; color: #e2e8f0; }

/* ===== Agent Panels (替代平铺消息) ===== */
.agent-panels { flex: 1; overflow-y: auto; padding: 8px 16px; display: flex; flex-direction: column; gap: 8px; }
.agent-panels::-webkit-scrollbar { width: 4px; }
.agent-panels::-webkit-scrollbar-thumb { background: #334155; border-radius: 2px; }

/* 用户需求横幅 */
.user-request-banner {
  background: #4080ff22; border: 1px solid #4080ff44; border-radius: 8px;
  padding: 8px 14px; font-size: 13px; color: #93bbff;
  display: flex; align-items: center; gap: 8px;
  flex-shrink: 0;
}
.user-request-banner i { font-size: 16px; }

/* Agent 面板网格 */
.agent-panels-grid { display: flex; flex-direction: column; gap: 10px; flex: 1; }

.agent-panel {
  background: #0f172a; border: 1px solid #334155; border-radius: 10px;
  overflow: hidden; transition: all 0.3s;
}
.agent-panel.panel-thinking { border-color: #e6a23c44; }
.agent-panel.panel-working { border-color: #409eff44; }
.agent-panel.panel-done { border-color: #67c23a44; }
.agent-panel.panel-error { border-color: #f56c6c44; }
.agent-panel.panel-stopped { border-color: #64748b44; opacity: 0.8; }

/* 面板头部 */
.panel-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 6px 10px; background: #1a2332;
  border-bottom: 1px solid #334155;
}
.panel-header-left { display: flex; align-items: center; gap: 8px; }
.panel-header-right { display: flex; align-items: center; gap: 4px; }

.panel-role-badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 10px; border-radius: 4px;
  font-size: 12px; font-weight: 600; color: #fff;
}
.panel-status-text {
  font-size: 11px; color: #64748b;
}
.panel-status-dot {
  width: 7px; height: 7px; border-radius: 50%; display: inline-block;
  background: #475569; transition: all 0.3s;
}

.panel-header-right .el-button--danger.is-circle {
  width: 22px; height: 22px; padding: 0; font-size: 10px;
  background: transparent; border-color: #f56c6c44; color: #f56c6c;
}
.panel-header-right .el-button--danger.is-circle:hover { background: #f56c6c22; }
.panel-header-right .el-button--primary.is-circle {
  width: 22px; height: 22px; padding: 0; font-size: 10px;
  background: transparent; border-color: #4080ff44; color: #4080ff;
}

/* 面板主体 */
.panel-body { padding: 8px 12px; }

/* 时间线 */
.panel-timeline { display: flex; flex-direction: column; gap: 3px; margin-bottom: 6px; }

.timeline-item {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; color: #94a3b8; padding: 2px 4px;
  border-radius: 4px;
}
.timeline-item.tl-plan { color: #e6a23c; }
.timeline-item.tl-progress { color: #409eff; }
.timeline-item.tl-claude_output { align-items: flex-start; color: #cbd5e1; background: #111827; border: 1px solid #334155; }
.timeline-item.tl-claude_error { align-items: flex-start; color: #f56c6c; background: #2a0f0f44; border: 1px solid #f56c6c44; }
.timeline-item.tl-file_write { color: #67c23a; }
.timeline-item.tl-complete { color: #67c23a; }
.timeline-item.tl-error { color: #f56c6c; background: #2a0f0f44; }

.tl-icon { flex-shrink: 0; width: 16px; text-align: center; font-size: 12px; }
.tl-time { font-size: 10px; color: #475569; flex-shrink: 0; min-width: 60px; }
.tl-text { flex: 1; white-space: pre-wrap; word-break: break-word; }
.tl-file {
  color: #4080ff; cursor: pointer; text-decoration: underline;
  font-size: 11px; margin-left: 4px;
}
.tl-file:hover { color: #60a0ff; }

.thinking-text { animation: pulse-text 1.5s infinite; }
@keyframes pulse-text { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

/* 空状态 */
.panel-empty {
  text-align: center; padding: 16px; color: #475569; font-size: 12px;
}
.panel-empty i { font-size: 18px; margin-right: 4px; vertical-align: middle; }

/* Agent 回复 */
.panel-reply { margin-top: 4px; }
.reply-header {
  display: flex; align-items: center; gap: 6px;
  font-size: 11px; color: #64748b; cursor: pointer; padding: 4px 0;
  user-select: none;
}
.reply-header:hover { color: #94a3b8; }
.reply-size { margin-left: auto; font-size: 10px; color: #475569; }
.reply-content {
  margin: 4px 0 0; padding: 8px 10px;
  background: #1a2332; border: 1px solid #334155; border-radius: 6px;
  font-size: 12px; line-height: 1.5; color: #cbd5e1;
  white-space: pre-wrap; word-break: break-word;
  max-height: 300px; overflow-y: auto;
  font-family: 'Cascadia Code', 'Fira Code', monospace;
}

/* 错误 */
.panel-error {
  background: #2a0f0f44; border: 1px solid #f56c6c44; border-radius: 6px;
  padding: 6px 10px; font-size: 12px; color: #f56c6c; margin-top: 4px;
}

/* 文件列表 */
.panel-files { margin-top: 6px; }
.files-header {
  font-size: 11px; color: #67c23a; margin-bottom: 4px;
  display: flex; align-items: center; gap: 4px;
}
.files-grid { display: flex; flex-wrap: wrap; gap: 4px; }

.file-item {
  display: flex; align-items: center; gap: 4px;
  padding: 4px 8px; background: #1a2332; border: 1px solid #334155;
  border-radius: 6px; font-size: 11px; color: #94a3b8;
  cursor: pointer; transition: all 0.15s;
}
.file-item:hover { border-color: #4080ff; color: #4080ff; background: #0f1f3a; }
.file-item i:first-child { color: #64748b; font-size: 14px; }
.file-name { color: #cbd5e1; }
.file-size { color: #475569; font-size: 10px; }
.file-change {
  color: #67c23a; font-size: 10px; border: 1px solid #67c23a55;
  border-radius: 4px; padding: 0 4px;
}
.file-open-icon { margin-left: 4px; font-size: 10px; opacity: 0; transition: opacity 0.15s; }
.file-item:hover .file-open-icon { opacity: 1; }

/* ===== Chat input ===== */
.chat-input-area { padding: 8px 16px; border-top: 1px solid #334155; }
.chat-input-area :deep(.el-textarea__inner) { background: #0f172a; border-color: #334155; color: #e2e8f0; font-size: 13px; }
.chat-input-area :deep(.el-textarea__inner:focus) { border-color: #4080ff; }
.input-actions { display: flex; justify-content: space-between; align-items: center; margin-top: 4px; }
.input-hint { font-size: 11px; color: #475569; }
.input-buttons { display: flex; gap: 6px; }
.input-buttons .el-button { font-size: 12px; }
.input-buttons .el-button--primary { background: #4080ff; border-color: #4080ff; }
.input-buttons .el-button--default { background: transparent; border-color: #334155; color: #94a3b8; }

/* Placeholder */
.no-session-placeholder { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #64748b; padding: 40px; }
.placeholder-icon { font-size: 64px; color: #334155; margin-bottom: 12px; }
.no-session-placeholder h3 { margin: 8px 0 4px; color: #94a3b8; font-size: 18px; }
.no-session-placeholder p { color: #475569; font-size: 13px; }
.placeholder-tips { margin-top: 16px; display: flex; flex-direction: column; gap: 6px; font-size: 12px; color: #475569; }
.placeholder-tips i { color: #67c23a; margin-right: 6px; }

/* ===== File Preview Dialog ===== */
.file-browser-body { display: flex; gap: 12px; height: 70vh; overflow: hidden; }
.file-tree-panel {
  width: 280px; flex-shrink: 0; overflow: auto; padding: 10px;
  background: #1a2332; border: 1px solid #334155; border-radius: 8px;
}
.file-scope-tabs {
  display: flex; align-items: center; gap: 4px; margin-bottom: 8px;
  padding-bottom: 8px; border-bottom: 1px solid #334155;
}
.file-scope-tabs .el-button {
  padding: 4px 8px;
}
.file-tree-header { display: flex; justify-content: space-between; align-items: center; color: #94a3b8; font-size: 12px; margin-bottom: 8px; }
.file-tree-panel :deep(.el-tree) { background: transparent; color: #cbd5e1; }
.file-tree-panel :deep(.el-tree-node__content:hover) { background: #0f1f3a; }
.file-tree-panel :deep(.el-tree-node:focus > .el-tree-node__content) { background: #0f1f3a; }
.file-tree-node { display: flex; align-items: center; gap: 6px; font-size: 12px; min-width: 0; }
.tree-file-size { color: #64748b; font-size: 10px; margin-left: 4px; }
.file-preview-panel { flex: 1; min-width: 0; overflow: auto; }
.file-preview-toolbar {
  display: flex; align-items: center; gap: 8px; margin-bottom: 8px;
  color: #94a3b8; font-size: 12px;
}
.selected-file-path { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-preview-empty {
  height: 62vh; display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 8px; color: #64748b; background: #1a2332; border: 1px dashed #334155; border-radius: 8px;
}
.file-preview-empty i { font-size: 34px; }
.image-preview-wrap { display: flex; align-items: center; justify-content: center; min-height: 360px; background: #1a2332; border: 1px solid #334155; border-radius: 8px; }
.image-preview { max-width: 100%; max-height: 62vh; object-fit: contain; }
.pdf-preview,
.html-preview { width: 100%; height: 62vh; border: 1px solid #334155; border-radius: 8px; background: #fff; }
.binary-preview { text-align: center; padding: 80px 20px; color: #94a3b8; background: #1a2332; border: 1px solid #334155; border-radius: 8px; }
.binary-preview i { font-size: 42px; color: #64748b; }
.file-preview-body { max-height: 70vh; overflow-y: auto; }
.file-preview-dialog :deep(.el-dialog__header) {
  background: #1e293b; border-bottom: 1px solid #334155;
}
.file-preview-dialog :deep(.el-dialog__title) {
  color: #e2e8f0; font-size: 14px;
}
.file-preview-dialog :deep(.el-dialog__body) {
  background: #0f172a; padding: 16px;
}
.file-preview-dialog :deep(.el-dialog__headerbtn .el-dialog__close) { color: #64748b; }
.file-preview-content {
  margin: 0; padding: 16px;
  background: #1a2332; border: 1px solid #334155; border-radius: 8px;
  font-size: 13px; line-height: 1.6; color: #cbd5e1;
  white-space: pre-wrap; word-break: break-word;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
}
</style>
