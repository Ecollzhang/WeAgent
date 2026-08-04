<template>
  <div class="chat-window">
    <div class="chat-header" v-if="conversation">
      <div class="header-left">
        <h3>{{ conversation.title }}</h3>
        <span class="participant-count">
          {{ participantCount }} 个参与者
        </span>
        <el-tag
          v-if="conversation.kb_domain"
          size="mini"
          :type="kbDomainTagType"
          effect="plain"
          class="kb-domain-badge"
        >
          <i class="el-icon-collection"></i> {{ kbDomainLabel }}
        </el-tag>
      </div>
      <div class="header-actions">
        <el-button size="mini" icon="el-icon-search" type="text" @click="toggleSearchPanel" title="搜索"></el-button>
        <el-button v-if="chatWorkspaceVisible" size="mini" icon="el-icon-folder-opened" type="text" @click="$emit('open-workspace', 'workspace')" title="工作目录"></el-button>
        <el-button v-if="chatServicesVisible" size="mini" icon="el-icon-monitor" type="text" @click="$emit('open-services')" title="预览服务"></el-button>
        <el-button v-if="chatAttachmentsVisible" size="mini" icon="el-icon-upload2" type="text" @click="$emit('open-attachments')" title="上传文件"></el-button>
        <el-button
          size="mini"
          :icon="favoriteActive ? 'el-icon-star-on' : 'el-icon-star-off'"
          type="text"
          :class="{ 'favorite-active': favoriteActive }"
          @click="$emit('toggle-star')"
          title="收藏"
        ></el-button>
        <el-button size="mini" icon="el-icon-time" type="text" @click="toggleHistoryPanel" title="历史"></el-button>
        <el-dropdown trigger="click" @command="handleMoreCommand">
          <el-button size="mini" icon="el-icon-more" type="text" title="更多"></el-button>
          <el-dropdown-menu slot="dropdown">
            <el-dropdown-item command="migrate" v-if="conversation.owner_id === userId">
              <i class="el-icon-copy-document"></i> 迁移文件
            </el-dropdown-item>
            <el-dropdown-item command="delete" v-if="conversation.owner_id === userId">
              <i class="el-icon-delete"></i> 删除会话
            </el-dropdown-item>
          </el-dropdown-menu>
        </el-dropdown>
      </div>
    </div>

    <div class="chat-header" v-else>
      <div class="header-left">
        <h3 class="text-primary">WeAgent</h3>
        <span class="participant-count">请选择或创建一个会话</span>
      </div>
      <div class="header-actions">
        <el-button size="mini" icon="el-icon-search" type="text" title="搜索"></el-button>
        <el-button size="mini" icon="el-icon-paperclip" type="text" title="附件"></el-button>
        <el-button size="mini" icon="el-icon-star-off" type="text" title="收藏"></el-button>
        <el-button size="mini" icon="el-icon-time" type="text" title="历史"></el-button>
        <el-button size="mini" icon="el-icon-more" type="text" title="更多"></el-button>
      </div>
    </div>

    <!-- 服务/项目上下文栏 -->
    <div class="context-bar" v-if="conversation && (conversation.services?.length || conversation.project_id || conversation.kb_domain)">
      <div class="context-bar-left">
        <span class="context-label">上下文</span>
        <span v-if="conversation.services?.includes('rd')" class="ctx-chip rd" title="智能研发服务已启用">
          <span class="ctx-dot rd"></span> RD
        </span>
        <span v-if="conversation.project_id" class="ctx-chip project" :title="'关联项目: ' + (projectName || conversation.project_id)" @click="openProject">
          <i class="el-icon-folder-opened"></i>
          {{ projectName || conversation.project_id.slice(0, 8) + '...' }}
        </span>
        <span v-if="conversation.services?.includes('rag')" class="ctx-chip rag" title="知识库服务已启用">
          <span class="ctx-dot rag"></span> RAG
          <span v-if="conversation.kb_domain" class="ctx-sub">· {{ kbDomainLabel }}</span>
        </span>
      </div>
    </div>

    <div class="detail-panel" v-if="panelVisible">
      <div class="detail-panel__head">
        <div class="detail-panel__title">
          <i :class="panelMode === 'search' ? 'el-icon-search' : 'el-icon-time'"></i>
          <span>{{ panelMode === 'search' ? '搜索消息' : '对话历史' }}</span>
        </div>
        <el-button type="text" icon="el-icon-close" class="panel-close" @click="closePanel"></el-button>
      </div>
      <div class="detail-panel__body" v-if="panelMode === 'search'">
        <el-input
          ref="panelInput"
          v-model="searchQuery"
          size="small"
          clearable
          placeholder="输入关键词搜索消息"
          @input="handleSearchInput"
          @keydown.enter.native.prevent="jumpToFirstSearchResult"
        />
        <div class="panel-meta">
          {{ searchResults.length }} 条结果
        </div>
        <div class="panel-list" v-if="searchResults.length">
          <button
            v-for="item in searchResults"
            :key="item.message.id"
            type="button"
            class="panel-item"
            @click="jumpToMessage(item.message.id)"
          >
            <div class="panel-item__title">{{ item.title }}</div>
            <div class="panel-item__snippet">{{ item.snippet }}</div>
          </button>
        </div>
        <div v-else class="panel-empty">没有匹配的消息</div>
      </div>
      <div class="detail-panel__body" v-else>
        <div class="panel-list" v-if="historyItems.length">
          <button
            v-for="item in historyItems"
            :key="item.message.id"
            type="button"
            class="panel-item"
            @click="jumpToMessage(item.message.id)"
          >
            <div class="panel-item__title">{{ item.title }}</div>
            <div class="panel-item__snippet">{{ item.snippet }}</div>
          </button>
        </div>
        <div v-else class="panel-empty">暂无用户问题</div>
      </div>
    </div>

    <div class="messages-container" ref="messagesContainer">
      <template v-if="messages && messages.length > 0">
        <div
          v-for="msg in messages"
          :key="msg.id"
          :ref="'message-' + msg.id"
          class="message-wrapper"
          :class="{ highlighted: highlightedMessageId === msg.id }"
        >
          <MessageBubble
            :message="msg"
            :isOwn="msg.sender_type === 'user' && msg.sender_id === userId"
            :sessionId="sessionId"
            @pin="$emit('pin-message', msg.id)"
            @stop-agent="$emit('stop-agent', msg)"
            @open-file="$emit('open-file', $event)"
            @preview-workflow="openWorkflowPreview"
          />
        </div>
      </template>

      <div v-else-if="conversation" class="empty-messages">
        <i class="el-icon-chat-dot-round"></i>
        <p>发送一条消息开始对话！</p>
      </div>

      <!-- Agent typing indicator -->
      <div v-if="agentResponding" class="typing-indicator">
        <div class="typing-dots">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </div>
        <span class="typing-text">智能体正在响应...</span>
      </div>

      <div v-else-if="!conversation" class="empty-messages">
        <i class="el-icon-s-promotion"></i>
        <h2>欢迎使用 WeAgent</h2>
        <p>多智能体协作平台</p>
        <p class="hint">创建或选择会话开始聊天</p>
      </div>
    </div>

    <div v-if="conversation && sidePanelVisible" class="functional-side-backdrop" @click.self="closeFunctionalSidePanel">
      <aside class="functional-side-panel">
        <header class="functional-side-header">
          <div>
            <h3>{{ sidePanelTitle }}</h3>
            <p>{{ sidePanelSubtitle }}</p>
          </div>
          <el-button type="text" icon="el-icon-close" @click="closeFunctionalSidePanel"></el-button>
        </header>

        <section v-if="sidePanelMode === 'agent_config'" class="functional-side-body">
          <div v-if="currentAgentConfigs.length === 0" class="side-empty">
            <i class="el-icon-user"></i>
            <span>当前会话没有 Agent</span>
          </div>
          <article v-for="agent in currentAgentConfigs" v-else :key="agent.agent_id" class="session-agent-card">
            <div class="session-agent-head">
              <span class="session-agent-avatar" :style="{ background: agent.color || '#4080ff' }">
                <img v-if="agent.avatar" :src="agent.avatar" />
                <span v-else>{{ firstLetter(agent.name || agent.role || agent.agent_id) }}</span>
              </span>
              <div class="session-agent-title">
                <strong>{{ agent.name || agent.role || agent.agent_id }}</strong>
                <small>{{ agent.adapter_name || 'default' }}</small>
              </div>
              <el-switch v-model="agent.enabled" size="mini" :disabled="singleAgentConfigLocked"></el-switch>
            </div>
            <label class="session-config-field">
              <span>会话角色名</span>
              <el-input v-model.trim="agent.role" size="mini" placeholder="当前会话中的展示名称" />
            </label>
            <label class="session-config-field">
              <span>系统提示词</span>
              <el-input v-model="agent.system_prompt" type="textarea" :rows="4" placeholder="仅在当前会话中生效，不更新全局 Agent" />
            </label>
            <label class="session-config-field">
              <span>技能 / 工作方式</span>
              <el-input v-model="agent.skill" type="textarea" :rows="3" placeholder="填写该 Agent 在当前会话的工作方式" />
            </label>
            <div class="session-card-actions">
              <el-button size="mini" @click="resetSessionAgentConfig(agent.agent_id)">重置</el-button>
            </div>
          </article>
          <div v-if="currentAgentConfigs.length" class="side-actions">
            <el-button size="mini" type="primary" @click="saveSessionAgentConfigs">保存会话配置</el-button>
          </div>
        </section>

        <section v-else-if="sidePanelMode === 'artifacts'" class="functional-side-body">
          <div v-if="conversationArtifacts.length === 0" class="side-empty">
            <i class="el-icon-folder-opened"></i>
            <span>当前会话暂无产物</span>
          </div>
          <template v-else>
            <div v-for="group in artifactGroups" :key="group.key" class="artifact-group">
              <div class="artifact-group-header">
                <div>
                  <strong>{{ group.label }}</strong>
                  <span>{{ group.hint }}</span>
                </div>
                <em>{{ group.items.length }}</em>
              </div>
              <article
                v-for="artifact in group.items"
                :key="artifact.id"
                class="side-artifact-item"
                @click="viewArtifact(artifact)"
              >
                <span class="artifact-card-icon">
                  <i :class="artifactIcon(artifact)"></i>
                </span>
                <div class="artifact-card-main">
                  <div class="artifact-card-head">
                    <strong>{{ artifactTitle(artifact) }}</strong>
                    <em>{{ artifactTypeLabel(artifact) }}</em>
                  </div>
                  <span class="artifact-card-subtitle">{{ artifactSubtitle(artifact) }}</span>
                  <p v-if="artifactPreviewText(artifact)" class="artifact-card-preview">{{ artifactPreviewText(artifact) }}</p>
                  <div class="artifact-card-meta">
                    <span>{{ artifact.message.sender_name || 'Agent' }}</span>
                    <span>{{ formatArtifactTime(artifact.message.created_at) }}</span>
                  </div>
                  <div class="artifact-card-actions" @click.stop>
                    <el-button size="mini" type="text" @click="viewArtifact(artifact)">查看</el-button>
                    <el-button v-if="artifact.type === 'service'" size="mini" type="text" @click="runArtifactService(artifact)">运行</el-button>
                    <el-button v-if="artifact.type === 'service'" size="mini" type="text" class="danger-action" @click="stopArtifactService(artifact)">停止</el-button>
                    <el-button v-else size="mini" type="text" @click="copyArtifactReference(artifact)">复制</el-button>
                  </div>
                </div>
              </article>
            </div>
          </template>
        </section>

        <section v-else-if="sidePanelMode === 'logs'" class="functional-side-body">
          <div class="side-log-toolbar">
            <el-select v-model="selectedServiceId" size="mini" placeholder="选择 app 服务" @change="loadSelectedServiceLogs">
              <el-option
                v-for="service in sandboxServices"
                :key="service.id"
                :label="`${service.name || service.id} · ${service.status || 'unknown'}`"
                :value="service.id"
              />
            </el-select>
            <el-button size="mini" icon="el-icon-refresh" :loading="serviceLogsLoading" @click="loadSandboxServices"></el-button>
          </div>
          <div v-if="serviceLogsLoading" class="side-empty">
            <i class="el-icon-loading"></i>
            <span>正在读取容器日志...</span>
          </div>
          <div v-else-if="!sandboxServices.length" class="side-empty">
            <i class="el-icon-monitor"></i>
            <span>暂无运行中的 app 日志</span>
          </div>
          <pre v-else class="side-log-output">{{ formattedServiceLogs || '暂无日志输出' }}</pre>
        </section>
      </aside>
    </div>

    <!-- 底部标签切换栏 -->
    <div class="chat-tabs" v-if="conversation">
      <span
        v-for="tab in visibleTabs"
        :key="tab.key"
        class="tab-item"
        :class="{ active: activeTab === tab.key }"
        @click="handleTabSwitch(tab.key)"
      >{{ tab.label }}</span>
      <!-- 知识库入口 -->
      <span
        v-if="kbTabVisible"
        class="tab-item kb-tab"
        :class="{ active: kbDialogVisible }"
        @click="openKbDialog"
      >知识库</span>
    </div>
    <!-- KB selected document chips row (between tabs and input) -->
    <div class="kb-doc-chips-row" v-if="conversation && selectedKbDocs.length">
      <span class="kb-doc-chips-label">知识库文档：</span>
      <span
        v-for="doc in visibleKbDocs"
        :key="doc.id"
        class="kb-doc-chip"
      >{{ doc.name }}</span>
      <span v-if="selectedKbDocs.length > 3" class="kb-doc-more">
        +{{ selectedKbDocs.length - 3 }}
      </span>
    </div>
    <!-- 隐藏的知识库选择器 (控制弹窗) -->
    <KbDocumentSelector
      ref="kbDocSelector"
      :conversation="conversation"
      :hideTrigger="true"
      @documents-change="onKbDocumentsChange"
    />

    <div class="message-input" v-if="conversation">
      <div v-if="selectedWorkflowLabel" class="selected-workflow-chip">
        <span>已选工作流：{{ selectedWorkflowLabel }}</span>
        <button type="button" @click="clearSelectedWorkflow">×</button>
      </div>
      <div class="input-wrapper">
        <el-input
          type="text"
          placeholder="输入消息..."
          v-model="inputText"
          @input="handleInputChange"
          @keydown.native="handleInputKeydown"
          class="feishu-input"
        >
        </el-input>
        <div v-if="mentionVisible && mentionCandidates.length" class="mention-menu">
          <button
            v-for="(agent, index) in mentionCandidates"
            :key="agent.agent_id"
            class="mention-item"
            :class="{ active: index === mentionIndex }"
            @mousedown.prevent="selectMention(agent)"
          >
            <span class="mention-avatar" :style="{ background: agent.color || '#4080ff' }">
              <img v-if="agent.avatar" :src="agent.avatar" />
              <span v-else>{{ mentionName(agent).charAt(0) }}</span>
            </span>
            <span class="mention-name">{{ mentionName(agent) }}</span>
          </button>
        </div>
        <el-button type="text" class="send-btn" @click="handleSend" :disabled="!inputText.trim()">
          <i class="el-icon-position"></i>
        </el-button>
      </div>
    </div>

    <div v-if="workflowVisible" class="workflow-overlay" @click.self="closeWorkflow">
      <section class="workflow-dialog">
        <header>
          <div>
            <h3>工作流图</h3>
            <p>{{ workflowDraft ? workflowDraft.name : '选择或创建当前会话的工作流图' }}</p>
          </div>
          <el-button type="text" icon="el-icon-close" @click="closeWorkflow"></el-button>
        </header>
        <div class="workflow-editor">
          <aside class="workflow-library">
            <div class="workflow-library-head">
              <strong>工作流产物</strong>
              <el-button size="mini" type="text" @click="createWorkflowDraft">新建</el-button>
            </div>
            <button
              v-for="workflow in displayWorkflows"
              :key="workflow.id"
              type="button"
              class="workflow-list-item"
              :class="{ active: workflowDraft && workflowDraft.id === workflow.id }"
              @click="selectWorkflow(workflow)"
            >
              <strong>{{ workflow.name }}</strong>
              <span>{{ workflow.nodes.length }} 节点 · {{ workflow.edges.length }} 连线</span>
            </button>
            <div v-if="!allWorkflows.length" class="workflow-empty">暂无工作流产物</div>
          </aside>
          <section class="workflow-main">
            <div class="workflow-toolbar">
              <input v-if="workflowDraft" v-model="workflowDraft.name" placeholder="工作流名称" />
              <input v-else disabled placeholder="工作流名称" />
              <el-button size="mini" @click="addWorkflowNode" :disabled="!workflowDraft">新增节点</el-button>
              <el-button size="mini" @click="copyWorkflowDraft" :disabled="!workflowDraft">复制</el-button>
              <el-button size="mini" type="danger" plain @click="deleteWorkflowDraft" :disabled="!workflowDraft">删除</el-button>
              <el-button size="mini" type="primary" @click="saveWorkflowDraft" :disabled="!workflowDraft">保存并使用</el-button>
              <el-button size="mini" type="success" @click="useWorkflowDraft" :disabled="!workflowDraft">使用该图</el-button>
            </div>
            <div class="workflow-view-tabs">
              <button type="button" :class="{ active: workflowViewMode === 'graph' }" @click="setWorkflowViewMode('graph')">图</button>
              <button type="button" :class="{ active: workflowViewMode === 'json' }" @click="setWorkflowViewMode('json')">JSON</button>
            </div>
            <div
              v-if="workflowViewMode === 'graph'"
              class="workflow-canvas"
              @mousemove="dragWorkflowNode"
              @mouseup="stopWorkflowDrag"
              @mouseleave="stopWorkflowDrag"
            >
              <svg class="workflow-edges">
                <line
                  v-for="edge in workflowEdgesForRender"
                  :key="`${edge.from}-${edge.to}`"
                  :x1="edge.x1"
                  :y1="edge.y1"
                  :x2="edge.x2"
                  :y2="edge.y2"
                />
              </svg>
              <article
                v-for="node in workflowDraftNodes"
                :key="node.id"
                class="workflow-node"
                :style="{ left: node.x + 'px', top: node.y + 'px' }"
                @mousedown.prevent="startWorkflowDrag(node, $event)"
              >
                <input v-model="node.title" placeholder="节点标题" @mousedown.stop />
                <select v-model="node.agent_id" @mousedown.stop>
                  <option value="">自动选择 Agent</option>
                  <option v-for="agent in enabledSessionAgents" :key="agent.agent_id" :value="agent.agent_id">
                    {{ mentionName(agent) }}
                  </option>
                </select>
                <textarea v-model="node.instruction" rows="3" placeholder="任务说明" @mousedown.stop></textarea>
                <div class="workflow-node-actions" @mousedown.stop>
                  <button type="button" @click="setWorkflowConnectFrom(node.id)">
                    {{ workflowConnectFrom === node.id ? '起点已选' : '设为起点' }}
                  </button>
                  <button type="button" :disabled="!workflowConnectFrom || workflowConnectFrom === node.id" @click="connectWorkflowNode(node.id)">连到此</button>
                  <button type="button" class="danger-action" @click="deleteWorkflowNode(node.id)">删除</button>
                </div>
              </article>
              <div v-if="!workflowDraftNodes.length" class="workflow-placeholder">
                <i class="el-icon-share"></i>
                <span>新建节点或从左侧选择工作流产物</span>
              </div>
            </div>
            <div v-else class="workflow-json-panel">
              <div class="workflow-json-head">
                <span>实时 JSON</span>
                <button type="button" @click="copyWorkflowJson" :disabled="!workflowDraft">复制</button>
              </div>
              <textarea
                class="workflow-json-preview"
                :class="{ invalid: workflowJsonError }"
                v-model="workflowJsonText"
                spellcheck="false"
                :disabled="!workflowDraft"
                @input="handleWorkflowJsonInput"
              ></textarea>
              <div v-if="workflowJsonError" class="workflow-json-error">{{ workflowJsonError }}</div>
            </div>
          </section>
        </div>
      </section>
    </div>

    <div v-if="artifactPreviewVisible" class="artifact-preview-overlay" @click.self="closeArtifactPreview">
      <section class="artifact-preview-dialog">
        <header>
          <div>
            <h3>{{ artifactTitle(artifactPreviewArtifact) }}</h3>
            <p>{{ artifactTypeLabel(artifactPreviewArtifact) }} · {{ artifactSubtitle(artifactPreviewArtifact) }}</p>
          </div>
          <el-button type="text" icon="el-icon-close" @click="closeArtifactPreview"></el-button>
        </header>
        <div class="artifact-preview-body">
          <div
            v-if="artifactPreviewArtifact && artifactPreviewArtifact.type === 'table' && artifactTableHeaders(artifactPreviewArtifact).length"
            class="artifact-preview-table-wrap"
          >
            <table class="artifact-preview-table">
              <thead>
                <tr>
                  <th v-for="(header, index) in artifactTableHeaders(artifactPreviewArtifact)" :key="index">{{ header }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, rowIndex) in artifactTableRows(artifactPreviewArtifact)" :key="rowIndex">
                  <td v-for="(header, colIndex) in artifactTableHeaders(artifactPreviewArtifact)" :key="colIndex">
                    {{ row['col' + colIndex] }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <pre v-else class="artifact-preview-code">{{ artifactPreviewContent(artifactPreviewArtifact) }}</pre>
        </div>
      </section>
    </div>
  </div>
</template>

<script>
import MessageBubble from '../MessageBubble/index.vue'
import KbDocumentSelector from '../KbDocumentSelector/index.vue'
import { checkVisible } from '../../store/modules/grayscale'
import { listServices, getServiceLogs, restartService, stopService } from '../../api/sandbox'

export default {
  name: 'ChatWindow',
  components: { MessageBubble, KbDocumentSelector },
  props: {
    conversation: Object,
    messages: Array,
    userId: String,
    agentResponding: { type: Boolean, default: false },
    sessionAgents: { type: Array, default: () => [] },
    allAgents: { type: Array, default: () => [] },
  },
  data() {
    return {
      inputText: '',
      mentionVisible: false,
      mentionQuery: '',
      mentionIndex: 0,
      selectedMentions: [],
      activeTab: 'chat',
      sidePanelVisible: false,
      sidePanelMode: '',
      sessionAgentConfigs: {},
      workflowVisible: false,
      workflowDraft: null,
      savedWorkflows: [],
      deletedWorkflowIds: [],
      selectedWorkflowId: '',
      workflowViewMode: 'graph',
      workflowJsonText: '{}',
      workflowJsonError: '',
      syncingWorkflowJson: false,
      workflowDrag: null,
      workflowConnectFrom: '',
      artifactPreviewVisible: false,
      artifactPreviewArtifact: null,
      sandboxServices: [],
      selectedServiceId: '',
      serviceLogsData: null,
      serviceLogsLoading: false,
      stickToBottom: true,
      selectedKbDocs: [],
      kbDialogVisible: false,
      projectName: '',
      projectNameLoading: false,
      panelVisible: false,
      panelMode: 'search',
      searchQuery: '',
      highlightedMessageId: '',
      tabs: [
        { key: 'chat', label: '对话' },
        { key: 'agent_config', label: '智能体配置' },
        { key: 'artifacts', label: '产物' },
        { key: 'logs', label: '日志' },
        { key: 'workflow', label: '工作流图' },
      ],
    }
  },
  computed: {
    favoriteActive() {
      return !!this.conversation?.is_favorite
    },
    activeDomain() {
      return this.$store.getters['workspace/activeDomain']
    },
    chatWorkspaceVisible() {
      return checkVisible(this.$store.state.grayscale, this.activeDomain, 'ui.chat.workspace')
    },
    chatServicesVisible() {
      return checkVisible(this.$store.state.grayscale, this.activeDomain, 'ui.chat.services')
    },
    chatAttachmentsVisible() {
      return checkVisible(this.$store.state.grayscale, this.activeDomain, 'ui.chat.attachments')
    },
    participantCount() {
      if (!this.conversation || !this.conversation.participant_ids) return 0
      return this.conversation.participant_ids.length
    },
    kbDomainLabel() {
      const map = { rd: '智能研发', edu: '智慧教育', office: '智慧办公', all: '全部领域' }
      return map[this.conversation?.kb_domain] || this.conversation?.kb_domain || ''
    },
    kbDomainTagType() {
      const map = { rd: '', edu: 'success', office: 'warning', all: 'info' }
      return map[this.conversation?.kb_domain] || ''
    },
    sessionId() {
      return this.conversation?.sandbox_session_id || this.conversation?.id || ''
    },
    mentionCandidates() {
      const query = String(this.mentionQuery || '').toLowerCase()
      const agents = (this.sessionAgents || []).filter(agent => agent?.agent_id && this.isSessionAgentEnabled(agent.agent_id))
      const filtered = query
        ? agents.filter(agent => {
          const name = this.mentionName(agent).toLowerCase()
          const id = String(agent.agent_id || '').toLowerCase()
          return name.includes(query) || id.includes(query)
        })
        : agents
      return filtered.slice(0, 8)
    },
    searchResults() {
      const query = this.searchQuery.trim().toLowerCase()
      if (!query) return []
      return (this.messages || [])
        .map(message => {
          const text = this.collectMessageText(message)
          return { message, text }
        })
        .filter(item => item.text.toLowerCase().includes(query))
        .map(item => ({
          message: item.message,
          title: this.buildMessageTitle(item.message),
          snippet: this.buildSearchSnippet(item.text, query),
        }))
        .slice(0, 50)
    },
    historyItems() {
      return (this.messages || [])
        .filter(message => message.sender_type === 'user')
        .map(message => ({
          message,
          title: this.buildMessageTitle(message),
          snippet: this.buildSearchSnippet(this.collectMessageText(message), ''),
        }))
    },
    currentAgentConfigs() {
      if (!this.conversation?.id) return []
      return this.sessionAgentConfigs[this.conversation.id] || []
    },
    singleAgentConfigLocked() {
      return this.currentAgentConfigs.length <= 1
    },
    enabledSessionAgents() {
      return (this.sessionAgents || []).filter(agent => agent?.agent_id && this.isSessionAgentEnabled(agent.agent_id))
    },
    workflowArtifacts() {
      const workflows = []
      ;(this.messages || []).forEach(message => {
        const elements = Array.isArray(message.elements) ? message.elements : []
        elements.forEach(element => {
          if (!element || element.type !== 'workflow') return
          workflows.push(this.normalizeWorkflow(this.elementData(element), message))
        })
      })
      return workflows.filter(Boolean)
    },
    allWorkflows() {
      const map = new Map()
      ;[...this.savedWorkflows, ...this.workflowArtifacts].forEach(workflow => {
        if (workflow && workflow.id) map.set(workflow.id, workflow)
      })
      const deleted = new Set(this.deletedWorkflowIds)
      return Array.from(map.values()).filter(workflow => !deleted.has(workflow.id))
    },
    displayWorkflows() {
      if (!this.workflowDraft || !this.workflowDraft.id) return this.allWorkflows
      return this.allWorkflows.map(workflow => (
        workflow.id === this.workflowDraft.id ? this.activeWorkflowPayload() || this.workflowDraft : workflow
      ))
    },
    selectedWorkflowLabel() {
      const workflow = this.allWorkflows.find(item => item.id === this.selectedWorkflowId) || this.workflowDraft
      return workflow && this.selectedWorkflowId ? workflow.name : ''
    },
    workflowDraftNodes() {
      return this.workflowDraft && Array.isArray(this.workflowDraft.nodes) ? this.workflowDraft.nodes : []
    },
    workflowEdgesForRender() {
      if (!this.workflowDraft) return []
      const nodeMap = new Map(this.workflowDraftNodes.map(node => [node.id, node]))
      return (this.workflowDraft.edges || [])
        .map(edge => {
          const from = nodeMap.get(edge.from)
          const to = nodeMap.get(edge.to)
          if (!from || !to) return null
          return {
            ...edge,
            x1: from.x + 232,
            y1: from.y + 62,
            x2: to.x,
            y2: to.y + 62,
          }
        })
        .filter(Boolean)
    },
    workflowJsonPreview() {
      if (!this.workflowDraft) return '{}'
      const workflow = this.cloneWorkflow(this.workflowDraft)
      workflow.parallel_groups = this.deriveWorkflowParallelGroups(workflow.nodes)
      workflow.edges = this.deriveWorkflowEdges(workflow.nodes, workflow.edges)
      return JSON.stringify(workflow, null, 2)
    },
    conversationArtifacts() {
      const artifacts = []
      const seen = new Set()
      ;(this.messages || []).forEach(message => {
        const elements = Array.isArray(message.elements) ? message.elements : []
        elements.forEach(element => {
          if (!element || !['code', 'table', 'image', 'file', 'service'].includes(element.type)) return
          if (this.isModeratorPlanArtifact(element)) return
          const data = this.elementData(element)
          const content = this.elementContent(element)
          const key = [
            element.type,
            data.path || data.file_path || data.url || data.name || data.filename || '',
            data.title || content || '',
          ].join('|')
          if (seen.has(key)) return
          seen.add(key)
          artifacts.push({
            id: key || `${message.id}_${artifacts.length}`,
            message,
            element,
            type: element.type,
            data,
          })
        })
      })
      return artifacts
    },
    artifactGroups() {
      const groups = [
        { key: 'service', label: 'App 服务', hint: '预览服务、运行中的页面或应用', types: ['service'] },
        { key: 'file', label: '文件与图片', hint: '生成的文档、图片、HTML、资源文件', types: ['file', 'image'] },
        { key: 'table', label: '表格', hint: '结构化表格和数据结果', types: ['table'] },
        { key: 'code', label: '代码', hint: '代码片段和脚本产物', types: ['code'] },
      ]
      return groups
        .map(group => ({
          ...group,
          items: this.conversationArtifacts.filter(artifact => group.types.includes(artifact.type)),
        }))
        .filter(group => group.items.length)
    },
    formattedServiceLogs() {
      if (!this.serviceLogsData) return ''
      const stdout = this.serviceLogsData.stdout_tail || ''
      const stderr = this.serviceLogsData.stderr_tail || ''
      return [
        stdout ? `# stdout\n${stdout}` : '',
        stderr ? `# stderr\n${stderr}` : '',
      ].filter(Boolean).join('\n\n')
    },
    sidePanelTitle() {
      if (this.sidePanelMode === 'agent_config') return '智能体配置'
      if (this.sidePanelMode === 'artifacts') return '产物'
      if (this.sidePanelMode === 'logs') return '日志'
      return ''
    },
    visibleTabs() {
      const state = this.$store.state.grayscale
      const domain = this.activeDomain
      return this.tabs.filter(tab => {
        if (tab.key === 'chat') return true
        return checkVisible(state, domain, 'ui.chat.tabs.' + tab.key)
      })
    },
    kbTabVisible() {
      return checkVisible(
        this.$store.state.grayscale,
        this.activeDomain,
        'ui.chat.tabs.knowledge_base'
      )
    },
    visibleKbDocs() {
      return this.selectedKbDocs.slice(0, 3)
    },
    sidePanelSubtitle() {
      if (this.sidePanelMode === 'agent_config') return '只影响当前会话，不更新全局 Agent'
      if (this.sidePanelMode === 'artifacts') return `当前会话 ${this.conversationArtifacts.length} 个产物`
      if (this.sidePanelMode === 'logs') return '容器中 app 服务的 stdout / stderr'
      return ''
    },
  },
  watch: {
    messages() {
      const shouldScroll = this.isNearBottom()
      this.$nextTick(() => this.scrollToBottom(shouldScroll))
    },
    conversation() {
      this.closePanel()
      this.closeFunctionalSidePanel()
      this.sandboxServices = []
      this.selectedServiceId = ''
      this.serviceLogsData = null
      this.projectName = ''
      this.ensureSessionAgentConfigs()
      this.loadSavedWorkflows()
      if (this.conversation?.project_id) {
        this.fetchProjectName(this.conversation.project_id)
      }
      this.$nextTick(() => this.scrollToBottom(true))
    },
    workflowDraft: {
      deep: true,
      handler() {
        if (this.syncingWorkflowJson) return
        this.refreshWorkflowJsonText()
      },
    },
  },
  mounted() {
    this.ensureSessionAgentConfigs()
    this.loadSavedWorkflows()
    const container = this.$refs.messagesContainer
    if (container) {
      container.addEventListener('scroll', this.handleMessagesScroll, { passive: true })
      this.stickToBottom = this.isNearBottom()
    }
  },
  beforeDestroy() {
    const container = this.$refs.messagesContainer
    if (container) {
      container.removeEventListener('scroll', this.handleMessagesScroll)
    }
  },
  methods: {
    handleSend() {
      if (!this.inputText.trim()) return
      const payload = this.buildMessagePayload()
      this.$emit('send-message', payload)
      this.inputText = ''
      this.mentionVisible = false
      this.mentionQuery = ''
      this.mentionIndex = 0
      this.selectedMentions = []
      this.$nextTick(() => this.scrollToBottom(true))
    },
    handleInputChange() {
      this.syncMentionState()
      this.syncSelectedMentions()
    },
    handleInputKeydown(event) {
      if (this.mentionVisible && this.mentionCandidates.length) {
        if (event.key === 'ArrowDown') {
          event.preventDefault()
          this.mentionIndex = (this.mentionIndex + 1) % this.mentionCandidates.length
          return
        }
        if (event.key === 'ArrowUp') {
          event.preventDefault()
          this.mentionIndex = (this.mentionIndex - 1 + this.mentionCandidates.length) % this.mentionCandidates.length
          return
        }
        if (event.key === 'Enter' || event.key === 'Tab') {
          event.preventDefault()
          this.selectMention(this.mentionCandidates[this.mentionIndex])
          return
        }
        if (event.key === 'Escape') {
          this.mentionVisible = false
          return
        }
      }
      if (event.key === 'Enter') {
        event.preventDefault()
        this.handleSend()
      }
    },
    syncMentionState() {
      const match = /@([^\s@，,：:；;]*)$/.exec(this.inputText)
      if (!match) {
        this.mentionVisible = false
        this.mentionQuery = ''
        this.mentionIndex = 0
        return
      }
      this.mentionQuery = match[1] || ''
      this.mentionVisible = true
      if (this.mentionIndex >= this.mentionCandidates.length) this.mentionIndex = 0
    },
    selectMention(agent) {
      if (!agent || !this.isSessionAgentEnabled(agent.agent_id)) return
      const name = this.mentionName(agent)
      this.inputText = this.inputText.replace(/@([^\s@，,：:；;]*)$/, `@${name} `)
      if (!this.selectedMentions.some(item => item.agent_id === agent.agent_id)) {
        this.selectedMentions.push({
          agent_id: agent.agent_id,
          name,
        })
      }
      this.mentionVisible = false
      this.mentionQuery = ''
      this.mentionIndex = 0
    },
    syncSelectedMentions() {
      this.selectedMentions = this.selectedMentions.filter(item => {
        return this.inputText.includes(`@${item.name}`) && this.isSessionAgentEnabled(item.agent_id)
      })
    },
    buildMessagePayload() {
      this.syncSelectedMentions()
      const targetIds = this.selectedMentions.map(item => item.agent_id)
      return {
        content: this.inputText.trim(),
        target_agent_ids: targetIds,
        mentions: this.selectedMentions.slice(),
        agent_configs: this.sessionAgentConfigPayload(),
        workflow: this.activeWorkflowPayload(),
      }
    },
    sessionAgentConfigPayload() {
      return this.currentAgentConfigs.reduce((payload, agent) => {
        if (!agent || !agent.agent_id) return payload
        payload[agent.agent_id] = {
          agent_id: agent.agent_id,
          role: agent.role,
          system_prompt: agent.system_prompt,
          skill: agent.skill,
          adapter_name: agent.adapter_name,
          enabled: this.singleAgentConfigLocked ? true : agent.enabled !== false,
        }
        return payload
      }, {})
    },
    workflowStorageKey() {
      return `weagent.web.workflows.${this.conversation?.id || ''}`
    },
    workflowSelectionStorageKey() {
      return `weagent.web.selectedWorkflow.${this.conversation?.id || ''}`
    },
    workflowDeletedStorageKey() {
      return `weagent.web.deletedWorkflows.${this.conversation?.id || ''}`
    },
    loadSavedWorkflows() {
      if (!this.conversation?.id) {
        this.savedWorkflows = []
        this.deletedWorkflowIds = []
        this.workflowDraft = null
        return
      }
      try {
        const saved = JSON.parse(localStorage.getItem(this.workflowStorageKey()) || '[]')
        this.savedWorkflows = Array.isArray(saved) ? saved.map(item => this.normalizeWorkflow(item)).filter(Boolean) : []
      } catch (e) {
        this.savedWorkflows = []
      }
      try {
        const deleted = JSON.parse(localStorage.getItem(this.workflowDeletedStorageKey()) || '[]')
        this.deletedWorkflowIds = Array.isArray(deleted) ? deleted.map(String) : []
      } catch (e) {
        this.deletedWorkflowIds = []
      }
      const selectedId = localStorage.getItem(this.workflowSelectionStorageKey()) || ''
      const selected = this.allWorkflows.find(item => item.id === selectedId) || this.allWorkflows[0]
      if (!this.workflowDraft && selected) {
        this.selectWorkflow(selected)
      }
    },
    normalizeWorkflow(workflow, message = null) {
      if (!workflow || typeof workflow !== 'object') return null
      const nodes = Array.isArray(workflow.nodes) ? workflow.nodes : []
      const normalizedNodes = nodes.map((node, index) => ({
        id: String(node.id || node.task_id || `node-${index + 1}`),
        task_id: String(node.task_id || node.id || `node-${index + 1}`),
        title: node.title || node.name || `节点 ${index + 1}`,
        instruction: node.instruction || node.content || '',
        agent_id: node.agent_id || '',
        x: Number.isFinite(Number(node.x)) ? Number(node.x) : 80 + index * 220,
        y: Number.isFinite(Number(node.y)) ? Number(node.y) : 80,
      }))
      const nodeIds = new Set(normalizedNodes.map(node => node.id))
      const edges = (Array.isArray(workflow.edges) ? workflow.edges : [])
        .filter(edge => edge && nodeIds.has(String(edge.from)) && nodeIds.has(String(edge.to)))
        .map(edge => ({ from: String(edge.from), to: String(edge.to) }))
      return {
        id: String(workflow.id || `workflow-${message?.id || Date.now()}`),
        name: workflow.name || workflow.summary || '未命名工作流',
        summary: workflow.summary || '',
        nodes: normalizedNodes,
        edges,
        parallel_groups: Array.isArray(workflow.parallel_groups) ? workflow.parallel_groups : [],
        source: workflow.source || (message ? 'message' : 'saved'),
      }
    },
    cloneWorkflow(workflow) {
      return JSON.parse(JSON.stringify(workflow))
    },
    refreshWorkflowJsonText() {
      this.workflowJsonText = this.workflowJsonPreview
      this.workflowJsonError = ''
    },
    setWorkflowViewMode(mode) {
      this.workflowViewMode = mode
      if (mode === 'json') {
        this.refreshWorkflowJsonText()
      }
    },
    handleWorkflowJsonInput() {
      if (!this.workflowDraft) return
      let parsed
      try {
        parsed = JSON.parse(this.workflowJsonText)
      } catch (error) {
        this.workflowJsonError = `JSON 格式错误：${error.message}`
        return
      }
      const normalized = this.normalizeWorkflow(parsed)
      if (!normalized) {
        this.workflowJsonError = 'JSON 内容必须是工作流对象'
        return
      }
      if (!Array.isArray(parsed.nodes)) {
        this.workflowJsonError = 'JSON 内容缺少 nodes 数组'
        return
      }
      this.workflowJsonError = ''
      this.syncingWorkflowJson = true
      this.workflowDraft = normalized
      this.selectedWorkflowId = normalized.id
      this.$nextTick(() => {
        this.syncingWorkflowJson = false
      })
    },
    createWorkflowDraft() {
      this.workflowDraft = {
        id: `workflow-${Date.now()}`,
        name: '新建工作流图',
        summary: '',
        nodes: [],
        edges: [],
        parallel_groups: [],
        source: 'saved',
      }
    },
    selectWorkflow(workflow) {
      const normalized = this.normalizeWorkflow(workflow)
      if (!normalized) return
      this.workflowDraft = this.cloneWorkflow(normalized)
      this.selectedWorkflowId = normalized.id
      if (this.conversation?.id) localStorage.setItem(this.workflowSelectionStorageKey(), normalized.id)
    },
    openWorkflowPreview(workflow) {
      this.selectWorkflow(workflow)
      this.workflowVisible = true
      this.activeTab = 'workflow'
    },
    activeWorkflowPayload() {
      if (!this.workflowDraft || !this.selectedWorkflowId) return null
      const workflow = this.cloneWorkflow(this.workflowDraft)
      workflow.parallel_groups = this.deriveWorkflowParallelGroups(workflow.nodes)
      workflow.edges = this.deriveWorkflowEdges(workflow.nodes, workflow.edges)
      return workflow
    },
    saveWorkflowDraft() {
      if (!this.workflowDraft) return
      const workflow = this.activeWorkflowPayload() || this.workflowDraft
      const next = [workflow, ...this.savedWorkflows.filter(item => item.id !== workflow.id)]
      this.savedWorkflows = next
      localStorage.setItem(this.workflowStorageKey(), JSON.stringify(next))
      this.selectedWorkflowId = workflow.id
      localStorage.setItem(this.workflowSelectionStorageKey(), workflow.id)
      this.$message.success('工作流图已保存并设为本轮默认')
    },
    useWorkflowDraft() {
      if (!this.workflowDraft) return
      const workflow = this.activeWorkflowPayload() || this.workflowDraft
      this.selectedWorkflowId = workflow.id
      if (this.conversation?.id) localStorage.setItem(this.workflowSelectionStorageKey(), workflow.id)
      this.workflowVisible = false
      this.activeTab = 'chat'
      if (!this.inputText.trim()) {
        this.inputText = '请根据这个图来分配工作来完成任务：'
      }
    },
    clearSelectedWorkflow() {
      this.selectedWorkflowId = ''
      if (this.conversation?.id) localStorage.removeItem(this.workflowSelectionStorageKey())
    },
    copyWorkflowDraft() {
      if (!this.workflowDraft) return
      const copy = this.cloneWorkflow(this.workflowDraft)
      copy.id = `workflow-${Date.now()}`
      copy.name = `${copy.name || '工作流图'} 副本`
      this.workflowDraft = copy
      this.selectedWorkflowId = copy.id
    },
    deleteWorkflowDraft() {
      if (!this.workflowDraft) return
      const name = this.workflowDraft.name || '当前工作流图'
      if (!window.confirm(`确定删除「${name}」吗？`)) return
      const id = this.workflowDraft.id
      this.savedWorkflows = this.savedWorkflows.filter(item => item.id !== id)
      if (this.conversation?.id) {
        localStorage.setItem(this.workflowStorageKey(), JSON.stringify(this.savedWorkflows))
      }
      if (id && !this.deletedWorkflowIds.includes(id)) {
        this.deletedWorkflowIds = [...this.deletedWorkflowIds, id]
        if (this.conversation?.id) {
          localStorage.setItem(this.workflowDeletedStorageKey(), JSON.stringify(this.deletedWorkflowIds))
        }
      }
      if (this.selectedWorkflowId === id) {
        this.clearSelectedWorkflow()
      }
      const next = this.allWorkflows.find(item => item.id !== id)
      this.workflowDraft = next ? this.cloneWorkflow(next) : null
      if (next) {
        this.selectedWorkflowId = next.id
        if (this.conversation?.id) localStorage.setItem(this.workflowSelectionStorageKey(), next.id)
      }
      this.workflowConnectFrom = ''
      this.$message.success('工作流图已删除')
    },
    copyWorkflowJson() {
      this.copyTextToClipboard(this.workflowJsonText || this.workflowJsonPreview)
        .then(() => this.$message.success('JSON 已复制'))
        .catch(() => this.$message.error('复制失败'))
    },
    copyTextToClipboard(text) {
      if (navigator.clipboard && window.isSecureContext) {
        return navigator.clipboard.writeText(text)
      }
      return new Promise((resolve, reject) => {
        const textarea = document.createElement('textarea')
        textarea.value = text
        textarea.setAttribute('readonly', '')
        textarea.style.position = 'fixed'
        textarea.style.left = '-9999px'
        document.body.appendChild(textarea)
        textarea.select()
        try {
          document.execCommand('copy') ? resolve() : reject(new Error('copy failed'))
        } catch (error) {
          reject(error)
        } finally {
          document.body.removeChild(textarea)
        }
      })
    },
    addWorkflowNode() {
      if (!this.workflowDraft) this.createWorkflowDraft()
      const index = this.workflowDraft.nodes.length + 1
      this.workflowDraft.nodes.push({
        id: `node-${Date.now()}`,
        task_id: `task-${index}`,
        title: `任务节点 ${index}`,
        instruction: '',
        agent_id: '',
        x: 80 + (index - 1) * 60,
        y: 80 + (index - 1) * 38,
      })
    },
    deleteWorkflowNode(nodeId) {
      if (!this.workflowDraft) return
      this.workflowDraft.nodes = this.workflowDraft.nodes.filter(node => node.id !== nodeId)
      this.workflowDraft.edges = (this.workflowDraft.edges || []).filter(edge => edge.from !== nodeId && edge.to !== nodeId)
      if (this.workflowConnectFrom === nodeId) this.workflowConnectFrom = ''
    },
    setWorkflowConnectFrom(nodeId) {
      this.workflowConnectFrom = this.workflowConnectFrom === nodeId ? '' : nodeId
    },
    connectWorkflowNode(nodeId) {
      if (!this.workflowDraft || !this.workflowConnectFrom || this.workflowConnectFrom === nodeId) return
      const edge = { from: this.workflowConnectFrom, to: nodeId }
      const exists = (this.workflowDraft.edges || []).some(item => item.from === edge.from && item.to === edge.to)
      if (!exists) this.workflowDraft.edges.push(edge)
      this.workflowConnectFrom = ''
    },
    startWorkflowDrag(node, event) {
      this.workflowDrag = {
        node,
        offsetX: event.offsetX,
        offsetY: event.offsetY,
      }
    },
    dragWorkflowNode(event) {
      if (!this.workflowDrag) return
      const rect = event.currentTarget.getBoundingClientRect()
      this.workflowDrag.node.x = Math.max(12, event.clientX - rect.left - this.workflowDrag.offsetX)
      this.workflowDrag.node.y = Math.max(12, event.clientY - rect.top - this.workflowDrag.offsetY)
    },
    stopWorkflowDrag() {
      this.workflowDrag = null
    },
    deriveWorkflowParallelGroups(nodes) {
      const groups = new Map()
      ;(nodes || []).forEach(node => {
        const stage = Math.round(Number(node.x || 0) / 220)
        if (!groups.has(stage)) groups.set(stage, [])
        groups.get(stage).push(node.task_id || node.id)
      })
      return Array.from(groups.keys()).sort((a, b) => a - b).map(key => groups.get(key))
    },
    deriveWorkflowEdges(nodes, explicitEdges = []) {
      if (explicitEdges && explicitEdges.length) return explicitEdges
      const groups = this.deriveWorkflowParallelGroups(nodes)
      const edges = []
      for (let index = 0; index < groups.length - 1; index++) {
        groups[index].forEach(from => {
          groups[index + 1].forEach(to => edges.push({ from, to }))
        })
      }
      return edges
    },
    mentionName(agent) {
      return agent?.role || agent?.name || agent?.agent_id || ''
    },
    isSessionAgentEnabled(agentId) {
      if (this.singleAgentConfigLocked) return true
      const config = this.currentAgentConfigs.find(item => String(item.agent_id) === String(agentId))
      return !config || config.enabled !== false
    },
    handleMessagesScroll() {
      this.stickToBottom = this.isNearBottom()
    },
    toggleSearchPanel() {
      if (this.panelVisible && this.panelMode === 'search') {
        this.closePanel()
        return
      }
      this.panelMode = 'search'
      this.panelVisible = true
      this.$nextTick(() => {
        const input = this.$refs.panelInput
        if (input && input.focus) input.focus()
      })
    },
    toggleHistoryPanel() {
      if (this.panelVisible && this.panelMode === 'history') {
        this.closePanel()
        return
      }
      this.panelMode = 'history'
      this.panelVisible = true
    },
    closePanel() {
      this.panelVisible = false
      this.searchQuery = ''
    },
    handleSearchInput() {
      if (this.searchResults.length) {
        this.highlightedMessageId = this.searchResults[0].message.id
      }
    },
    jumpToFirstSearchResult() {
      if (this.searchResults.length) {
        this.jumpToMessage(this.searchResults[0].message.id)
      }
    },
    jumpToMessage(messageId) {
      const ref = this.$refs[`message-${messageId}`]
      const target = Array.isArray(ref) ? ref[0] : ref
      if (target && target.scrollIntoView) {
        this.highlightedMessageId = messageId
        this.panelVisible = false
        this.$nextTick(() => {
          target.scrollIntoView({ behavior: 'smooth', block: 'center' })
          setTimeout(() => {
            if (this.highlightedMessageId === messageId) {
              this.highlightedMessageId = ''
            }
          }, 2500)
        })
      }
    },
    buildMessageTitle(message) {
      const raw = String(message?.content || message?.raw_output || '').trim()
      if (!raw) {
        return message?.sender_name || '消息'
      }
      const firstLine = raw.split(/\r?\n/).find(line => line.trim()) || raw
      return firstLine
        .replace(/^#{1,6}\s*/, '')
        .replace(/^[-*+]\s*/, '')
        .replace(/^>\s*/, '')
        .trim()
    },
    buildSearchSnippet(text, query) {
      const plain = String(text || '').replace(/\s+/g, ' ').trim()
      if (!plain) return '无可预览内容'
      if (!query) return plain.slice(0, 96)
      const index = plain.toLowerCase().indexOf(query)
      if (index === -1) return plain.slice(0, 96)
      const start = Math.max(0, index - 22)
      const end = Math.min(plain.length, index + query.length + 42)
      return `${start > 0 ? '...' : ''}${plain.slice(start, end)}${end < plain.length ? '...' : ''}`
    },
    collectMessageText(message) {
      const parts = []
      const push = value => {
        if (value === undefined || value === null) return
        const text = typeof value === 'string' ? value : JSON.stringify(value)
        if (text) parts.push(text)
      }
      push(message?.content)
      push(message?.raw_output)
      const elements = Array.isArray(message?.elements) ? message.elements : []
      elements.forEach(element => {
        if (!element) return
        push(element.title)
        push(element.content)
        push(element.text)
        push(element.name)
        push(element.path)
        push(element.url)
        push(element.message)
        push(element.data)
        push(element.detail)
      })
      return parts.join(' ')
    },
    onKbDocumentsChange(docs) {
      this.selectedKbDocs = docs || []
    },
    openKbDialog() {
      this.kbDialogVisible = true
      this.$refs.kbDocSelector.openDialog()
      // sync dialog state back when it closes
      this.$nextTick(() => {
        const selector = this.$refs.kbDocSelector
        const unwatch = this.$watch(
          function () { return selector && selector.visible },
          function (v) {
            if (!v) {
              this.kbDialogVisible = false
              unwatch()
            }
          }
        )
      })
    },
    isNearBottom() {
      const container = this.$refs.messagesContainer
      if (!container) return true
      const distance = container.scrollHeight - container.scrollTop - container.clientHeight
      return distance <= 80
    },
    scrollToBottom(force = false) {
      const container = this.$refs.messagesContainer
      if (container && (force || this.stickToBottom)) {
        container.scrollTop = container.scrollHeight
      }
    },
    handleMoreCommand(command) {
      if (command === 'migrate') {
        this.$emit('open-migration')
      } else if (command === 'delete') {
        this.$emit('delete-conversation')
      }
    },
    handleTabSwitch(key) {
      this.activeTab = key
      if (key === 'chat') {
        this.closeFunctionalSidePanel()
        return
      }
      if (key === 'workflow') {
        this.sidePanelVisible = false
        this.sidePanelMode = ''
        this.workflowVisible = true
        return
      }
      this.sidePanelMode = key
      this.sidePanelVisible = true
      if (key === 'agent_config') {
        this.ensureSessionAgentConfigs()
      } else if (key === 'logs') {
        this.loadSandboxServices()
      }
    },
    closeFunctionalSidePanel() {
      this.sidePanelVisible = false
      this.sidePanelMode = ''
      if (this.activeTab !== 'workflow') this.activeTab = 'chat'
    },
    closeWorkflow() {
      this.workflowVisible = false
      this.activeTab = 'chat'
    },
    sessionConfigStorageKey() {
      return `weagent.web.sessionAgentConfigs.${this.conversation?.id || ''}`
    },
    ensureSessionAgentConfigs() {
      if (!this.conversation?.id) return
      let saved = []
      try {
        saved = JSON.parse(localStorage.getItem(this.sessionConfigStorageKey()) || '[]')
      } catch (e) {
        saved = []
      }
      const savedMap = new Map((Array.isArray(saved) ? saved : []).map(item => [String(item.agent_id), item]))
      const configs = (this.sessionAgents || []).map(agent => {
        const globalAgent = (this.allAgents || []).find(item => String(item.id) === String(agent.agent_id)) || {}
        const savedItem = savedMap.get(String(agent.agent_id)) || {}
        return {
          agent_id: agent.agent_id,
          name: agent.name || globalAgent.name || agent.agent_id,
          role: savedItem.role || agent.role || globalAgent.name || agent.agent_id,
          avatar: agent.avatar || globalAgent.avatar_url || globalAgent.avatar || '',
          color: agent.color || globalAgent.avatar_color || '#4080ff',
          adapter_name: savedItem.adapter_name || globalAgent.adapter_name || globalAgent.agent_type || '',
          system_prompt: savedItem.system_prompt || globalAgent.system_prompt || '',
          skill: savedItem.skill || globalAgent.skill || '',
          enabled: (this.sessionAgents || []).length <= 1 ? true : savedItem.enabled !== false,
        }
      })
      this.$set(this.sessionAgentConfigs, this.conversation.id, configs)
    },
    saveSessionAgentConfigs() {
      if (!this.conversation?.id) return
      const configs = this.currentAgentConfigs.map(item => ({ ...item }))
      localStorage.setItem(this.sessionConfigStorageKey(), JSON.stringify(configs))
      this.$message.success('当前会话的智能体配置已保存')
    },
    resetSessionAgentConfig(agentId) {
      if (!this.conversation?.id || !agentId) return
      let saved = []
      try {
        saved = JSON.parse(localStorage.getItem(this.sessionConfigStorageKey()) || '[]')
      } catch (e) {
        saved = []
      }
      localStorage.setItem(
        this.sessionConfigStorageKey(),
        JSON.stringify((Array.isArray(saved) ? saved : []).filter(item => String(item.agent_id) !== String(agentId)))
      )
      this.ensureSessionAgentConfigs()
    },
    firstLetter(value) {
      return String(value || '?').charAt(0).toUpperCase()
    },
    elementData(element) {
      const data = element && element.data
      return data && typeof data === 'object' && !Array.isArray(data) ? data : {}
    },
    elementContent(element) {
      const data = this.elementData(element)
      const value = (element && element.content) || data.content || data.text || data.message || ''
      if (value && typeof value === 'object') {
        try {
          return JSON.stringify(value)
        } catch (e) {
          return String(value)
        }
      }
      return String(value || '')
    },
    isModeratorPlanArtifact(element) {
      if (!element || element.type === 'workflow') return false
      const data = this.elementData(element)
      const values = [
        data.path,
        data.file_path,
        data.filePath,
        data.file,
        data.url,
        data.src,
        data.name,
        data.filename,
        data.title,
        this.elementContent(element),
      ]
      return values.some(value => String(value || '').toLowerCase().includes('moderator-plan.json'))
    },
    artifactIcon(artifact) {
      const type = artifact?.type
      if (type === 'table') return 'el-icon-s-grid'
      if (type === 'image') return 'el-icon-picture-outline'
      if (type === 'code') return 'el-icon-tickets'
      if (type === 'service') return 'el-icon-monitor'
      return 'el-icon-document'
    },
    artifactTypeLabel(artifact) {
      const map = {
        code: '代码',
        table: '表格',
        image: '图片',
        file: '文件',
        service: '服务',
      }
      return map[artifact?.type] || '产物'
    },
    artifactTitle(artifact) {
      const data = artifact?.data || {}
      return data.title || data.name || data.filename || data.path || this.elementContent(artifact?.element) || '产物'
    },
    artifactSubtitle(artifact) {
      if (!artifact) return ''
      const data = artifact.data || {}
      if (artifact.type === 'table') {
        const headers = Array.isArray(data.headers) ? data.headers.length : 0
        const rows = Array.isArray(data.rows) ? data.rows.length : 0
        return `${headers} 列 · ${rows} 行`
      }
      if (artifact.type === 'service') return data.url || data.proxy_url || data.port || 'app 服务'
      return data.path || data.url || artifact.type
    },
    artifactPreviewText(artifact) {
      return this.elementContent(artifact?.element).replace(/\s+/g, ' ').slice(0, 96)
    },
    artifactTablePayload(artifact) {
      const element = artifact?.element || {}
      const data = artifact?.data || this.elementData(element)
      const candidates = [data, data?.data]
      const content = this.elementContent(element)
      if (content) {
        try {
          const parsed = JSON.parse(content)
          candidates.push(parsed, parsed?.data)
        } catch (e) {}
      }
      return candidates.find(item => {
        if (!item || typeof item !== 'object') return false
        return Array.isArray(item.headers) || Array.isArray(item.columns) || Array.isArray(item.rows) || Array.isArray(item.data)
      }) || {}
    },
    artifactTableHeaders(artifact) {
      const payload = this.artifactTablePayload(artifact)
      const rows = Array.isArray(payload.rows) ? payload.rows : (Array.isArray(payload.data) ? payload.data : [])
      const headers = Array.isArray(payload.headers) ? payload.headers : payload.columns
      if (Array.isArray(headers) && headers.length) return headers.map(header => String(header || ''))
      const first = rows[0]
      if (first && typeof first === 'object' && !Array.isArray(first)) return Object.keys(first)
      if (Array.isArray(first)) return first.map((_, index) => `列 ${index + 1}`)
      return []
    },
    artifactTableRows(artifact) {
      const payload = this.artifactTablePayload(artifact)
      const headers = this.artifactTableHeaders(artifact)
      const rows = Array.isArray(payload.rows) ? payload.rows : (Array.isArray(payload.data) ? payload.data : [])
      if (!headers.length) return []
      return rows.map(row => {
        const cells = Array.isArray(row) ? row : headers.map(header => row?.[header])
        const item = {}
        headers.forEach((header, index) => {
          const value = cells[index]
          item['col' + index] = value === undefined || value === null ? '' : String(value)
        })
        return item
      })
    },
    artifactPreviewContent(artifact) {
      if (!artifact) return ''
      const content = this.elementContent(artifact.element)
      if (content) return content
      const data = artifact.data || {}
      try {
        return JSON.stringify(data, null, 2)
      } catch (e) {
        return String(data || '')
      }
    },
    openArtifactPreview(artifact) {
      this.artifactPreviewArtifact = artifact
      this.artifactPreviewVisible = true
    },
    closeArtifactPreview() {
      this.artifactPreviewVisible = false
      this.artifactPreviewArtifact = null
    },
    formatArtifactTime(value) {
      if (!value) return ''
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return ''
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    },
    artifactFilePayload(artifact) {
      const data = artifact?.data || {}
      const raw = data.path || data.file_path || data.filePath || data.file || data.url || data.src || this.elementContent(artifact?.element)
      return {
        path: raw,
        raw,
        name: data.name || data.filename || data.title || raw || '产物',
        agent_id: data.agent_id || data.agentId || data.owner_agent_id || '',
        type: artifact?.type || 'file',
        data,
      }
    },
    artifactReference(artifact) {
      const data = artifact?.data || {}
      return data.path || data.url || data.proxy_url || data.name || data.filename || this.elementContent(artifact?.element) || this.artifactTitle(artifact)
    },
    serviceInfoFromArtifact(artifact) {
      const data = artifact?.data || {}
      const nested = data.service && typeof data.service === 'object' ? data.service : {}
      return {
        id: data.service_id || data.id || nested.service_id || nested.id || '',
        url: data.proxy_url || nested.proxy_url || data.url || nested.url || '',
      }
    },
    viewArtifact(artifact) {
      if (artifact?.type === 'code' && artifact.data?.workflow) {
        this.openWorkflowPreview(artifact.data.workflow)
        return
      }
      if (artifact?.type === 'service') {
        const url = this.serviceInfoFromArtifact(artifact).url
        if (url) window.open(url, '_blank', 'noopener')
        return
      }
      if (artifact?.type === 'table' || (!this.artifactFilePayload(artifact).path && this.artifactPreviewContent(artifact))) {
        this.openArtifactPreview(artifact)
        return
      }
      this.$emit('open-file', this.artifactFilePayload(artifact))
    },
    async copyArtifactReference(artifact) {
      const text = this.artifactReference(artifact)
      if (!text || !navigator.clipboard) return
      await navigator.clipboard.writeText(text)
      this.$message.success('已复制产物引用')
    },
    async runArtifactService(artifact) {
      const id = this.serviceInfoFromArtifact(artifact).id
      if (!this.sessionId || !id) {
        this.$message.warning('未找到服务 ID')
        return
      }
      const res = await restartService(this.sessionId, id)
      if (res.code === 200) {
        this.$message.success('服务已运行')
        await this.loadSandboxServices()
      }
    },
    async stopArtifactService(artifact) {
      const id = this.serviceInfoFromArtifact(artifact).id
      if (!this.sessionId || !id) {
        this.$message.warning('未找到服务 ID')
        return
      }
      const res = await stopService(this.sessionId, id)
      if (res.code === 200) {
        this.$message.success('服务已停止')
        await this.loadSandboxServices()
      }
    },
    async loadSandboxServices() {
      if (!this.sessionId) return
      this.serviceLogsLoading = true
      try {
        const res = await listServices(this.sessionId)
        this.sandboxServices = res.code === 200 ? (res.data?.services || []) : []
        if (!this.selectedServiceId && this.sandboxServices.length) {
          this.selectedServiceId = this.sandboxServices[0].id
        }
        if (this.selectedServiceId) await this.loadSelectedServiceLogs()
      } catch (e) {
        this.$message.error(e?.message || '加载容器服务失败')
      } finally {
        this.serviceLogsLoading = false
      }
    },

    async fetchProjectName(projectId) {
      if (!projectId) return
      this.projectNameLoading = true
      try {
        const { getProject } = await import('../../api/rd')
        const res = await getProject(projectId)
        if (res.code === 200 && res.data) {
          this.projectName = res.data.name || ''
        }
      } catch (e) {
        // Silently fail — will show truncated ID instead
      } finally {
        this.projectNameLoading = false
      }
    },

    openProject() {
      if (!this.conversation?.project_id) return
      this.$router.push(`/rd/projects/${this.conversation.project_id}`)
    },
    async loadSelectedServiceLogs() {
      if (!this.sessionId || !this.selectedServiceId) {
        this.serviceLogsData = null
        return
      }
      this.serviceLogsLoading = true
      try {
        const res = await getServiceLogs(this.sessionId, this.selectedServiceId)
        this.serviceLogsData = res.code === 200 ? (res.data || {}) : null
      } catch (e) {
        this.$message.error(e?.message || '读取容器日志失败')
      } finally {
        this.serviceLogsLoading = false
      }
    },
  },
};
</script>

<style scoped>
.chat-window {
  display: flex;
  flex-direction: column;
  height: 100%;
  position: relative;
}

.chat-header {
  height: 60px;
  padding: 0 20px;
  border-bottom: 1px solid #eef1f6;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
  background: #ffffff;
}

.header-left h3 {
  margin: 0;
  font-size: 16px;
  color: #1e293b;
}

.header-left .text-primary {
  color: #4080ff;
}

.participant-count {
  font-size: 12px;
  color: #94a3b8;
}

.kb-domain-badge {
  margin-left: 8px;
  font-size: 11px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #86909c;
}

.header-actions .el-button--text {
  font-size: 16px;
  color: #86909c;
  padding: 6px;
}

.header-actions .el-button--text:hover {
  color: #4080ff;
}

.header-actions .favorite-active {
  color: #e6a23c;
}

.detail-panel {
  position: absolute;
  top: 60px;
  right: 20px;
  width: 340px;
  max-height: calc(100% - 80px);
  background: #ffffff;
  border: 1px solid #e8edf5;
  border-radius: 10px;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.14);
  z-index: 20;
  overflow: hidden;
}

.detail-panel__head {
  height: 48px;
  padding: 0 12px 0 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #eef2f7;
  background: #fbfdff;
}

.detail-panel__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #1f2937;
}

.panel-close {
  padding: 4px;
}

.detail-panel__body {
  padding: 12px;
}

.panel-meta {
  margin: 10px 0 8px;
  font-size: 12px;
  color: #94a3b8;
}

.panel-list {
  max-height: 52vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.panel-list::-webkit-scrollbar,
.messages-container::-webkit-scrollbar {
  width: 4px;
}

.panel-list::-webkit-scrollbar-thumb,
.messages-container::-webkit-scrollbar-thumb {
  background: #d8e0ea;
  border-radius: 999px;
}

.panel-item {
  width: 100%;
  padding: 10px 12px;
  text-align: left;
  border: 1px solid #e8edf5;
  border-radius: 8px;
  background: #ffffff;
  appearance: none;
  font: inherit;
  color: inherit;
  cursor: pointer;
}

.panel-item:hover {
  border-color: #bfd3ff;
  background: #f8fbff;
}

.panel-item__title {
  font-size: 13px;
  line-height: 1.4;
  color: #1f2937;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.panel-item__snippet {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.45;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.panel-empty {
  padding: 24px 0 8px;
  text-align: center;
  font-size: 12px;
  color: #94a3b8;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  background: #f7f8fa;
}

.messages-container::-webkit-scrollbar {
  width: 5px;
}

.messages-container::-webkit-scrollbar-track {
  background: transparent;
}

.messages-container::-webkit-scrollbar-thumb {
  background: #d5dbe3;
  border-radius: 999px;
}

.messages-container::-webkit-scrollbar-thumb:hover {
  background: #c0c8d4;
}

.message-wrapper {
  margin-bottom: 16px;
  animation: messageSlideIn 0.25s ease-out;
}

@keyframes messageSlideIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.message-wrapper.highlighted {
  border-radius: 10px;
  box-shadow: 0 0 0 3px rgba(64, 128, 255, 0.18);
  transition: box-shadow 0.3s ease-out;
}

.empty-messages {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #94a3b8;
}

.empty-messages i {
  font-size: 56px;
  margin-bottom: 16px;
  color: #d5dce6;
}

.empty-messages h2 {
  font-size: 22px;
  color: #1e293b;
  margin-bottom: 6px;
  font-weight: 700;
}

.empty-messages p {
  font-size: 14px;
  color: #94a3b8;
  margin: 0;
}

.empty-messages .hint {
  font-size: 13px;
  margin-top: 12px;
  color: #bcc4d2;
}

/* 服务/项目上下文栏 */
.context-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 20px;
  background: #f8fafc;
  border-bottom: 1px solid #f0f0f0;
  min-height: 34px;
  flex-shrink: 0;
}
.context-bar-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.context-label {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 500;
  margin-right: 2px;
}
.ctx-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 5px;
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
}
.ctx-chip.rd {
  background: #e8f0ff;
  color: #4080ff;
}
.ctx-chip.rag {
  background: #e8f5e9;
  color: #4caf50;
}
.ctx-chip.project {
  background: #fff3e0;
  color: #e65100;
  cursor: pointer;
}
.ctx-chip.project:hover {
  background: #ffe0b2;
}
.ctx-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}
.ctx-dot.rd {
  background: #4080ff;
}
.ctx-dot.rag {
  background: #4caf50;
}
.ctx-sub {
  font-weight: 400;
  opacity: 0.8;
}

/* 底部标签栏 */
.chat-tabs {
  height: 42px;
  border-top: 1px solid #eef1f6;
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 6px;
  background: #fafbfc;
  flex-shrink: 0;
}

.tab-item {
  padding: 5px 14px;
  border-radius: 7px;
  font-size: 12px;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;
  font-weight: 500;
}

.tab-item:hover {
  background: #eef2f7;
  color: #334155;
}

.tab-item.active {
  background: #4080ff;
  color: #fff;
  box-shadow: 0 1px 3px rgba(64, 128, 255, 0.3);
}

.kb-tab {
  display: inline-flex !important;
  align-items: center;
  gap: 6px;
}

.kb-doc-chips-row {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 16px;
  border-top: 1px solid #f0f0f0;
  background: #fafafa;
  flex-shrink: 0;
  flex-wrap: wrap;
}

.kb-doc-chips-label {
  font-size: 11px;
  color: #909399;
  margin-right: 2px;
  white-space: nowrap;
}

.kb-doc-chip {
  display: inline-block;
  max-width: 100px;
  padding: 1px 7px;
  background: #ecf5ff;
  color: #409eff;
  border-radius: 4px;
  font-size: 11px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.kb-doc-more {
  display: inline-block;
  padding: 1px 6px;
  background: #f0f0f0;
  color: #909399;
  border-radius: 4px;
  font-size: 11px;
  white-space: nowrap;
}

/* 输入框 */
.message-input {
  min-height: 68px;
  padding: 12px 16px;
  border-top: 1px solid #eef1f6;
  flex-shrink: 0;
  background: #ffffff;
}

.selected-workflow-chip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 6px 10px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 12px;
}

.selected-workflow-chip button {
  border: 0;
  background: transparent;
  color: #1d4ed8;
  cursor: pointer;
  font-size: 16px;
  opacity: 0.7;
  transition: opacity 0.15s;
}

.selected-workflow-chip button:hover {
  opacity: 1;
}

.input-wrapper {
  display: flex;
  align-items: center;
  background: #f2f4f7;
  border-radius: 10px;
  padding: 0 14px;
  height: 44px;
  position: relative;
  transition: background 0.2s, box-shadow 0.2s;
}

.input-wrapper:focus-within {
  background: #eef2f7;
  box-shadow: 0 0 0 2px rgba(64, 128, 255, 0.12);
}

.input-wrapper .feishu-input :deep(.el-input__inner) {
  border: none;
  background: transparent;
  font-size: 14px;
  height: 44px;
  padding: 0;
  color: #1e293b;
}

.input-wrapper .feishu-input :deep(.el-input__inner::placeholder) {
  color: #a0aec0;
}

.input-wrapper .feishu-input :deep(.el-input__inner:focus) {
  box-shadow: none;
}

.input-wrapper .feishu-input {
  flex: 1;
}

.send-btn {
  font-size: 20px;
  color: #4080ff;
  padding: 6px;
  transition: transform 0.15s;
}

.send-btn:not(:disabled):hover {
  transform: scale(1.15);
}

.send-btn:disabled {
  color: #cbd5e0;
}

.mention-menu {
  position: absolute;
  left: 8px;
  bottom: 50px;
  width: 240px;
  max-height: 260px;
  overflow-y: auto;
  padding: 6px;
  border: 1px solid #e8eaed;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
  z-index: 10;
}

.mention-item {
  width: 100%;
  height: 38px;
  border: none;
  background: transparent;
  border-radius: 6px;
  padding: 0 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  text-align: left;
}

.mention-item:hover,
.mention-item.active {
  background: #f0f5ff;
}

.mention-avatar {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
  overflow: hidden;
}

.mention-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.mention-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  color: #1e293b;
}

/* Typing indicator */
.typing-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 0;
  animation: fadeInUp 0.3s ease-out;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.typing-dots {
  display: flex;
  align-items: center;
  gap: 5px;
}

.dot {
  width: 8px;
  height: 8px;
  background: #a0c4f0;
  border-radius: 50%;
  animation: typingBounce 1.4s ease-in-out infinite;
}

.dot:nth-child(1) { animation-delay: 0s; }
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes typingBounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; background: #a0c4f0; }
  30% { transform: translateY(-7px); opacity: 1; background: #4080ff; }
}

.typing-text {
  font-size: 12px;
  color: #8b9ab8;
  font-weight: 500;
}

.functional-side-backdrop {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  justify-content: flex-end;
  background: rgba(15, 23, 42, 0.24);
  backdrop-filter: blur(2px);
}

.functional-side-panel {
  width: min(480px, 92vw);
  height: 100vh;
  display: flex;
  flex-direction: column;
  border-left: 1px solid #e5ebf5;
  background: #ffffff;
  box-shadow: -14px 0 32px rgba(15, 23, 42, 0.12);
}

.functional-side-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 18px;
  border-bottom: 1px solid #eef2f7;
}

.functional-side-header h3 {
  margin: 0;
  color: #0f172a;
  font-size: 16px;
}

.functional-side-header p {
  margin: 5px 0 0;
  color: #64748b;
  font-size: 12px;
}

.functional-side-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 14px;
}

.side-empty {
  min-height: 260px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 10px;
  color: #94a3b8;
  font-size: 13px;
}

.side-empty i {
  font-size: 32px;
}

.session-agent-card {
  border: 1px solid #e8edf5;
  border-radius: 8px;
  padding: 12px;
  background: #f8fafc;
}

.session-agent-card + .session-agent-card {
  margin-top: 10px;
}

.session-agent-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.session-agent-avatar {
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 8px;
  color: #ffffff;
  font-size: 13px;
  font-weight: 800;
}

.session-agent-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.session-agent-title {
  flex: 1;
  min-width: 0;
}

.session-agent-title strong,
.session-agent-title small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-agent-title strong {
  color: #1e293b;
  font-size: 13px;
}

.session-agent-title small {
  color: #94a3b8;
  font-size: 11px;
}

.session-config-field {
  display: grid;
  gap: 6px;
  margin-top: 10px;
}

.session-config-field span {
  color: #475569;
  font-size: 11px;
  font-weight: 700;
}

.side-actions {
  position: sticky;
  bottom: -15px;
  z-index: 2;
  margin: 12px -14px -14px;
  padding: 12px 14px;
  border-top: 1px solid #eef2f7;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.88) 0%, #ffffff 45%);
  box-shadow: 0 -8px 18px rgba(15, 23, 42, 0.05);
}

.session-card-actions,
.side-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.side-artifact-item {
  width: 100%;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  border: 1px solid #e8edf5;
  border-radius: 10px;
  padding: 14px;
  background: #ffffff;
  text-align: left;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
  transition: all 0.2s ease;
}

.side-artifact-item:hover {
  border-color: #bfd3ff;
  box-shadow: 0 4px 12px rgba(64, 128, 255, 0.08);
  transform: translateY(-1px);
}

.side-artifact-item + .side-artifact-item {
  margin-top: 10px;
}

.artifact-group + .artifact-group {
  margin-top: 18px;
}

.artifact-group-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.artifact-group-header div {
  min-width: 0;
  display: grid;
  gap: 2px;
}

.artifact-group-header strong {
  color: #0f172a;
  font-size: 13px;
}

.artifact-group-header span {
  overflow: hidden;
  color: #94a3b8;
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.artifact-group-header em {
  min-width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: #eef5ff;
  color: #2563eb;
  font-size: 11px;
  font-style: normal;
  font-weight: 800;
}

.side-artifact-item:hover {
  border-color: #cfe0ff;
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.09);
  transform: translateY(-1px);
}

.artifact-card-icon {
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: #eef5ff;
  color: #2563eb;
  font-size: 17px;
}

.artifact-card-main {
  flex: 1;
  min-width: 0;
  display: grid;
  gap: 5px;
}

.artifact-card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.artifact-card-head strong,
.artifact-card-subtitle,
.artifact-card-preview,
.artifact-card-meta span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.artifact-card-head strong {
  flex: 1;
  min-width: 0;
  color: #1e293b;
  font-size: 13px;
  font-weight: 700;
}

.artifact-card-head em {
  flex-shrink: 0;
  border-radius: 999px;
  padding: 2px 7px;
  background: #eef5ff;
  color: #2563eb;
  font-size: 10px;
  font-style: normal;
  font-weight: 700;
}

.artifact-card-subtitle {
  color: #64748b;
  font-size: 11px;
}

.artifact-card-preview {
  margin: 0;
  color: #475569;
  font-size: 12px;
  line-height: 1.45;
}

.artifact-card-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #94a3b8;
  font-size: 11px;
}

.artifact-card-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 2px;
}

.artifact-card-actions :deep(.el-button) {
  padding: 0;
  font-size: 11px;
}

.artifact-card-actions .danger-action {
  color: #f56c6c;
}

.side-log-toolbar {
  display: grid;
  grid-template-columns: 1fr 34px;
  gap: 8px;
  margin-bottom: 10px;
}

.side-log-output {
  min-height: 360px;
  margin: 0;
  border: 1px solid #e8edf5;
  border-radius: 8px;
  padding: 12px;
  overflow: auto;
  background: #0f172a;
  color: #dbeafe;
  font-size: 11px;
  line-height: 1.55;
  white-space: pre-wrap;
}

.workflow-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 14px;
  background: rgba(15, 23, 42, 0.34);
  backdrop-filter: blur(4px);
}

.workflow-dialog {
  width: min(1280px, calc(100vw - 28px));
  height: min(820px, calc(100vh - 28px));
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 10px;
  background: #ffffff;
  box-shadow: 0 24px 80px rgba(15, 23, 42, 0.28);
}

.workflow-dialog header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid #eef2f7;
}

.workflow-dialog h3 {
  margin: 0;
  color: #0f172a;
  font-size: 18px;
}

.workflow-dialog p {
  margin: 5px 0 0;
  color: #64748b;
  font-size: 12px;
}

.workflow-placeholder {
  flex: 1;
  min-height: 0;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 12px;
  color: #94a3b8;
  font-size: 14px;
}

.workflow-placeholder i {
  font-size: 44px;
}

.workflow-editor {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 260px 1fr;
}

.workflow-library {
  min-height: 0;
  overflow: auto;
  border-right: 1px solid #eef2f7;
  padding: 12px;
  background: #f8fafc;
}

.workflow-library-head,
.workflow-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.workflow-library-head {
  margin-bottom: 10px;
}

.workflow-list-item {
  width: 100%;
  display: grid;
  gap: 4px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px;
  background: #ffffff;
  color: #334155;
  text-align: left;
  cursor: pointer;
}

.workflow-list-item + .workflow-list-item {
  margin-top: 8px;
}

.workflow-list-item.active {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12);
}

.workflow-list-item strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.workflow-list-item span,
.workflow-empty {
  color: #94a3b8;
  font-size: 12px;
}

.workflow-main {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.workflow-toolbar {
  padding: 12px;
  border-bottom: 1px solid #eef2f7;
}

.workflow-toolbar input {
  flex: 1;
  min-width: 0;
  border: 1px solid #dbe4f0;
  border-radius: 7px;
  padding: 8px 10px;
  color: #1e293b;
}

.workflow-view-tabs {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-bottom: 1px solid #eef2f7;
  background: #fbfdff;
}

.workflow-view-tabs button {
  height: 28px;
  border: 1px solid transparent;
  border-radius: 7px;
  padding: 0 14px;
  background: transparent;
  color: #64748b;
  font-size: 12px;
  cursor: pointer;
}

.workflow-view-tabs button.active {
  border-color: #bfdbfe;
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 700;
}

.workflow-toolbar .danger-action,
.workflow-toolbar :deep(.el-button--danger.is-plain) {
  border-color: #fecdd3;
  color: #be123c;
  background: #fff1f2;
}

.workflow-canvas {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow: auto;
  background: linear-gradient(#eef2f7 1px, transparent 1px), linear-gradient(90deg, #eef2f7 1px, transparent 1px);
  background-size: 28px 28px;
}

.workflow-edges {
  position: absolute;
  inset: 0;
  width: 1600px;
  height: 1000px;
  pointer-events: none;
}

.workflow-edges line {
  stroke: #60a5fa;
  stroke-width: 2.4;
  stroke-linecap: round;
}

.workflow-node {
  position: absolute;
  width: 232px;
  display: grid;
  gap: 7px;
  border: 1px solid #d8e4f5;
  border-top: 3px solid #2563eb;
  border-radius: 8px;
  padding: 10px;
  background: linear-gradient(180deg, #ffffff 0%, #f9fbff 100%);
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.12);
  cursor: grab;
}

.workflow-node:hover {
  border-color: #93c5fd;
  box-shadow: 0 18px 40px rgba(37, 99, 235, 0.16);
}

.workflow-node input,
.workflow-node select,
.workflow-node textarea {
  width: 100%;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 6px 8px;
  background: #ffffff;
  color: #1e293b;
  font-size: 12px;
}

.workflow-node input {
  border-color: transparent;
  padding: 2px 0 4px;
  background: transparent;
  color: #0f172a;
  font-size: 13px;
  font-weight: 700;
}

.workflow-node select {
  height: 30px;
  background: #f8fafc;
  color: #475569;
}

.workflow-node textarea {
  min-height: 66px;
  line-height: 1.45;
  resize: vertical;
}

.workflow-node-actions {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 6px;
}

.workflow-node button {
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 5px 7px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
}

.workflow-node button:hover:not(:disabled) {
  border-color: #bfdbfe;
  background: #dbeafe;
}

.workflow-node button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.workflow-node .danger-action {
  background: #fff1f2;
  color: #be123c;
}

.workflow-json-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #0f172a;
}

.workflow-json-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.24);
  color: #cbd5e1;
  font-size: 12px;
  font-weight: 700;
}

.workflow-json-head button {
  height: 26px;
  border: 1px solid rgba(147, 197, 253, 0.5);
  border-radius: 6px;
  padding: 0 10px;
  background: rgba(37, 99, 235, 0.18);
  color: #bfdbfe;
  font-size: 12px;
  cursor: pointer;
}

.workflow-json-head button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.workflow-json-preview {
  flex: 1;
  min-height: 0;
  margin: 0;
  padding: 16px 18px;
  overflow: auto;
  border: 1px solid transparent;
  background: #0f172a;
  color: #dbeafe;
  font-family: Consolas, 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.65;
  white-space: pre;
  resize: none;
  outline: none;
}

.workflow-json-preview:focus {
  border-color: rgba(147, 197, 253, 0.55);
}

.workflow-json-preview.invalid {
  border-color: #fb7185;
}

.workflow-json-error {
  padding: 8px 14px;
  border-top: 1px solid rgba(248, 113, 113, 0.35);
  background: #2a1118;
  color: #fecdd3;
  font-size: 12px;
  line-height: 1.4;
}

.artifact-preview-overlay {
  position: fixed;
  inset: 0;
  z-index: 2100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 18px;
  background: rgba(15, 23, 42, 0.36);
  backdrop-filter: blur(4px);
}

.artifact-preview-dialog {
  width: min(980px, calc(100vw - 36px));
  max-height: min(760px, calc(100vh - 36px));
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 24px 80px rgba(15, 23, 42, 0.28);
}

.artifact-preview-dialog header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  padding: 16px 18px;
  border-bottom: 1px solid #eef2f7;
}

.artifact-preview-dialog h3 {
  margin: 0;
  color: #0f172a;
  font-size: 16px;
  line-height: 1.35;
}

.artifact-preview-dialog p {
  margin: 5px 0 0;
  color: #64748b;
  font-size: 12px;
}

.artifact-preview-body {
  min-height: 0;
  overflow: auto;
  padding: 16px;
  background: #f8fafc;
}

.artifact-preview-table-wrap {
  overflow: auto;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
}

.artifact-preview-table {
  width: 100%;
  min-width: 520px;
  border-collapse: collapse;
  color: #1e293b;
  font-size: 12px;
  text-align: left;
}

.artifact-preview-table th,
.artifact-preview-table td {
  border-bottom: 1px solid #e2e8f0;
  padding: 9px 11px;
  vertical-align: top;
  white-space: pre-wrap;
}

.artifact-preview-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #f1f5f9;
  color: #334155;
  font-weight: 700;
}

.artifact-preview-table tr:last-child td {
  border-bottom: 0;
}

.artifact-preview-code {
  margin: 0;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 14px;
  overflow: auto;
  background: #fff;
  color: #334155;
  font-size: 12px;
  line-height: 1.6;
  text-align: left;
  white-space: pre-wrap;
}
</style>
