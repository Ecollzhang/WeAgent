<template>
  <main class="dashboard-shell">
    <aside class="app-sidebar">
      <div class="sidebar-logo">W</div>
      <nav class="sidebar-nav">
        <button class="sidebar-btn active" title="会话"><i class="el-icon-chat-dot-round"></i></button>
        <button class="sidebar-btn" title="智能体" @click="$router.push('/agents')"><i class="el-icon-user"></i></button>
        <button class="sidebar-btn" title="工具" disabled><i class="el-icon-s-tools"></i></button>
        <button class="sidebar-btn" title="我的收藏" @click="$router.push('/favorites')"><i class="el-icon-collection-tag"></i></button>
        <button class="sidebar-btn" title="设置" @click="$router.push('/settings')"><i class="el-icon-setting"></i></button>
      </nav>
      <button class="sidebar-user" title="退出登录" @click="logout"><i class="el-icon-switch-button"></i></button>
    </aside>

    <section class="conversation-panel">
      <div class="list-header">
        <h3>会话</h3>
        <button class="create-circle" :disabled="creating" @click="openCreateDialog">+</button>
      </div>

      <div class="search-box">
        <i class="el-icon-search"></i>
        <input v-model.trim="searchQuery" placeholder="搜索..." />
      </div>

      <div class="list-items">
        <div v-if="convLoading" class="list-state">
          <i class="el-icon-loading"></i>
          <span>正在加载会话...</span>
        </div>
        <div
          v-for="conv in filteredConversations"
          v-else
          :key="conv.id"
          class="conversation-item"
          :class="{ active: currentId === conv.id }"
          role="button"
          tabindex="0"
          @click="selectConversation(conv)"
          @keydown.enter.prevent="selectConversation(conv)"
        >
          <div class="item-avatar" :style="convAvatarBg(conv)">
            <template v-if="avatarParticipants(conv).length === 0">
              <i class="el-icon-chat-dot-round"></i>
            </template>
            <template v-else-if="avatarParticipants(conv).length === 1">
              <img
                v-if="participantAvatar(avatarParticipants(conv)[0])"
                :src="participantAvatar(avatarParticipants(conv)[0])"
                class="avatar-img"
              />
              <span v-else class="avatar-letter-sm">{{ firstLetter(avatarParticipants(conv)[0].name) }}</span>
            </template>
            <template v-else>
              <div class="composite-avatar">
                <div
                  v-for="(p, i) in avatarParticipants(conv).slice(0, 3)"
                  :key="i"
                  class="composite-item"
                  :style="participantAvatar(p) ? {} : { background: participantColor(p) }"
                >
                  <img v-if="participantAvatar(p)" :src="participantAvatar(p)" class="composite-img" />
                  <span v-else class="composite-text">{{ firstLetter(p.name) }}</span>
                </div>
                <div v-if="avatarParticipants(conv).length > 3" class="composite-item composite-more">
                  <span class="composite-text">+{{ avatarParticipants(conv).length - 3 }}</span>
                </div>
              </div>
            </template>
          </div>
          <div class="item-content">
            <div class="item-title-row">
              <div class="item-title">{{ conv.title || '未命名会话' }}</div>
              <i v-if="conv.is_favorite" class="el-icon-star-on item-favorite"></i>
            </div>
            <div class="item-preview">
              <span v-if="conv.last_message">{{ conv.last_message.content }}</span>
              <span v-else class="no-messages">暂无消息</span>
            </div>
          </div>
          <div class="item-time">{{ formatTime((conv.last_message && conv.last_message.created_at) || conv.updated_at || conv.created_at) }}</div>
        </div>
        <div v-if="!convLoading && filteredConversations.length === 0" class="list-state">
          <i class="el-icon-chat-dot-round"></i>
          <span>{{ searchQuery ? '没有匹配的会话' : '暂无会话' }}</span>
        </div>
      </div>
    </section>

    <section class="chat-panel">
      <header class="chat-header">
        <div>
          <h3>{{ currentConversation ? currentConversation.title : 'WeAgent' }}</h3>
          <span>{{ currentConversation ? participantCount(currentConversation) + ' 个参与者' : '请选择或创建一个会话' }}</span>
        </div>
        <div class="header-actions">
          <button :disabled="!currentConversation" title="搜索消息" @click="toggleSearchPanel"><i class="el-icon-search"></i></button>
          <button :disabled="!currentConversation" title="工作目录" @click="handleOpenWorkspace()"><i class="el-icon-folder-opened"></i></button>
          <button disabled><i class="el-icon-monitor"></i></button>
          <button :disabled="!currentConversation" title="上传文件" @click="handleOpenAttachments()"><i class="el-icon-upload2"></i></button>
          <button
            :disabled="!currentConversation"
            :class="{ 'favorite-active': currentConversation && currentConversation.is_favorite }"
            title="收藏"
            @click="toggleFavorite"
          >
            <i :class="currentConversation && currentConversation.is_favorite ? 'el-icon-star-on' : 'el-icon-star-off'"></i>
          </button>
          <button :disabled="!currentConversation" title="历史" @click="toggleHistoryPanel"><i class="el-icon-time"></i></button>
          <div class="more-menu-wrap">
            <button :disabled="!currentConversation" @click="showMoreMenu = !showMoreMenu"><i class="el-icon-more"></i></button>
            <div v-if="showMoreMenu && currentConversation" class="more-menu">
              <button type="button" @click="handleDeleteConversation(currentConversation)">
                <i class="el-icon-delete"></i>
                <span>删除会话</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      <div v-if="detailPanelVisible" class="desktop-detail-panel">
        <div class="desktop-detail-head">
          <div>
            <i :class="detailPanelMode === 'search' ? 'el-icon-search' : 'el-icon-time'"></i>
            <span>{{ detailPanelMode === 'search' ? '搜索消息' : '对话历史' }}</span>
          </div>
          <button type="button" @click="closeDetailPanel"><i class="el-icon-close"></i></button>
        </div>
        <div v-if="detailPanelMode === 'search'" class="desktop-detail-body">
          <div class="desktop-panel-search">
            <i class="el-icon-search"></i>
            <input
              ref="messageSearchInput"
              v-model.trim="messageSearchQuery"
              placeholder="输入关键词搜索消息"
              @keydown.enter.prevent="jumpToFirstSearchResult"
            />
          </div>
          <div class="desktop-panel-meta">{{ messageSearchResults.length }} 条结果</div>
          <div v-if="messageSearchResults.length" class="desktop-panel-list">
            <button
              v-for="item in messageSearchResults"
              :key="item.message.id"
              type="button"
              class="desktop-panel-item"
              @click="jumpToMessage(item.message.id)"
            >
              <strong>{{ item.title }}</strong>
              <span>{{ item.snippet }}</span>
            </button>
          </div>
          <div v-else class="desktop-panel-empty">没有匹配的消息</div>
        </div>
        <div v-else class="desktop-detail-body">
          <div v-if="historyItems.length" class="desktop-panel-list">
            <button
              v-for="item in historyItems"
              :key="item.message.id"
              type="button"
              class="desktop-panel-item"
              @click="jumpToMessage(item.message.id)"
            >
              <strong>{{ item.title }}</strong>
              <span>{{ item.snippet }}</span>
            </button>
          </div>
          <div v-else class="desktop-panel-empty">暂无用户问题</div>
        </div>
      </div>

      <div ref="messagesContainer" class="messages-container live-messages">
        <div v-if="messagesLoading" class="empty-messages">
          <i class="el-icon-loading"></i>
          <h2>正在加载消息</h2>
          <p>稍等一下，桌面端正在读取当前会话。</p>
        </div>

        <div v-else-if="!currentConversation" class="empty-messages">
          <i class="el-icon-s-promotion"></i>
          <h2>欢迎使用 WeAgent</h2>
          <p>创建或选择会话后，就可以在桌面端发送消息。</p>
        </div>

        <div v-else-if="currentMessages.length === 0" class="empty-messages">
          <i class="el-icon-chat-line-round"></i>
          <h2>发送第一条消息</h2>
          <p>会话已关联 Agent，消息会按 Web 端同样的逻辑分发。</p>
        </div>

        <div v-else class="message-list">
          <div
            v-for="message in currentMessages"
            :key="message.id"
            :ref="'message-' + message.id"
            class="message-row desktop-message-row"
            :class="{ own: isOwnMessage(message), highlighted: highlightedMessageId === message.id }"
          >
            <div class="message-avatar" :style="messageAvatarStyle(message)">
              <img v-if="messageAvatar(message)" :src="messageAvatar(message)" class="message-avatar-img" />
              <span v-else>{{ firstLetter(senderName(message)) }}</span>
            </div>
            <MessageBubble
              class="desktop-message-bubble"
              :message="message"
              :is-own="isOwnMessage(message)"
              :server-url="serverUrl"
              @open-file="handleOpenMessageFile"
              @preview-workflow="openWorkflowPreview"
            />
          </div>
        </div>
      </div>

      <div v-if="currentConversation && sidePanelVisible" class="conversation-side-backdrop" @click.self="closeSidePanel">
        <aside class="conversation-inspector">
          <header class="inspector-header">
            <div>
              <h3>{{ sidePanelTitle }}</h3>
              <p>{{ sidePanelSubtitle }}</p>
            </div>
            <button type="button" @click="closeSidePanel"><i class="el-icon-close"></i></button>
          </header>

          <section v-if="sidePanelMode === 'agent_config'" class="inspector-body">
            <div v-if="currentAgentConfigs.length === 0" class="inspector-empty">
              <i class="el-icon-user"></i>
              <span>当前会话没有 Agent</span>
            </div>
            <article v-for="agent in currentAgentConfigs" v-else :key="agent.agent_id" class="session-agent-card">
              <div class="session-agent-head">
                <span class="session-agent-avatar" :style="{ background: agent.color || '#4080ff' }">
                  <img v-if="agent.avatar" :src="agent.avatar" />
                  <span v-else>{{ firstLetter(agent.name || agent.role || agent.agent_id) }}</span>
                </span>
                <div>
                  <strong>{{ agent.name || agent.role || agent.agent_id }}</strong>
                  <small>{{ agent.adapter_name || 'default' }}</small>
                </div>
                <label class="session-agent-toggle">
                  <input v-model="agent.enabled" type="checkbox" :disabled="singleAgentConfigLocked" />
                  <span>启用</span>
                </label>
              </div>
              <label class="session-config-field">
                <span>会话角色名</span>
                <input v-model.trim="agent.role" placeholder="当前会话中的展示名称" />
              </label>
              <label class="session-config-field">
                <span>系统提示词</span>
                <textarea v-model="agent.system_prompt" rows="4" placeholder="仅在当前会话中记录，不更新全局 Agent"></textarea>
              </label>
              <label class="session-config-field">
                <span>技能 / 工作方式</span>
                <textarea v-model="agent.skill" rows="3" placeholder="填写该 Agent 在当前会话的工作方式"></textarea>
              </label>
              <div class="session-card-actions">
                <button type="button" @click="resetSessionAgentConfig(agent.agent_id)">重置</button>
              </div>
            </article>
            <div v-if="currentAgentConfigs.length" class="inspector-actions">
              <button type="button" class="workspace-primary" @click="saveSessionAgentConfigs">保存会话配置</button>
            </div>
          </section>

          <section v-else-if="sidePanelMode === 'artifacts'" class="inspector-body">
            <div v-if="conversationArtifacts.length === 0" class="inspector-empty">
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
                  class="artifact-list-item"
                  @click="openConversationArtifact(artifact)"
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
                      <span>{{ formatTime(artifact.message.created_at) }}</span>
                    </div>
                    <div class="artifact-card-actions" @click.stop>
                      <button type="button" @click="openConversationArtifact(artifact)">查看</button>
                      <button v-if="artifact.type === 'service'" type="button" @click="runArtifactService(artifact)">运行</button>
                      <button v-if="artifact.type === 'service'" type="button" class="danger-action" @click="stopArtifactService(artifact)">停止</button>
                      <button v-else type="button" @click="copyArtifactReference(artifact)">复制</button>
                    </div>
                  </div>
                </article>
              </div>
            </template>
          </section>

          <section v-else-if="sidePanelMode === 'logs'" class="inspector-body logs-inspector">
            <div class="logs-toolbar">
              <select v-model="selectedServiceId" @change="loadSelectedServiceLogs">
                <option value="">选择 app 服务</option>
                <option v-for="service in sandboxServices" :key="service.id" :value="service.id">
                  {{ service.name || service.id }} · {{ service.status || 'unknown' }}
                </option>
              </select>
              <button type="button" :disabled="serviceLogsLoading" @click="loadSandboxServices">
                <i :class="serviceLogsLoading ? 'el-icon-loading' : 'el-icon-refresh'"></i>
              </button>
            </div>
            <div v-if="serviceLogsLoading" class="inspector-empty">
              <i class="el-icon-loading"></i>
              <span>正在读取容器日志...</span>
            </div>
            <div v-else-if="!sandboxServices.length" class="inspector-empty">
              <i class="el-icon-monitor"></i>
              <span>暂无运行中的 app 日志</span>
            </div>
            <pre v-else class="service-log-output">{{ formattedServiceLogs || '暂无日志输出' }}</pre>
          </section>
        </aside>
      </div>

      <div v-if="currentConversation" class="chat-tabs">
        <span
          v-for="tab in tabs"
          :key="tab.key"
          class="tab-item"
          :class="{ active: activeTab === tab.key }"
          @click="handleTabSwitch(tab.key)"
        >{{ tab.label }}</span>
      </div>

      <form class="message-input" @submit.prevent="handleSendMessage">
        <div v-if="selectedWorkflowLabel" class="selected-workflow-chip">
          <span>已选工作流：{{ selectedWorkflowLabel }}</span>
          <button type="button" @click="clearSelectedWorkflow">×</button>
        </div>
        <div class="input-wrapper">
          <input
            v-model="draft"
            :disabled="!currentConversation || sending"
            :placeholder="currentConversation ? '输入消息...' : '请先选择或创建会话'"
            @input="handleInputChange"
            @keydown="handleInputKeydown"
          />
          <div v-if="mentionVisible && mentionCandidates.length" class="mention-menu">
            <button
              v-for="(agent, index) in mentionCandidates"
              :key="agent.agent_id"
              type="button"
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
          <button class="send-button" :disabled="!currentConversation || sending || !draft.trim()" type="submit">
            <i :class="sending ? 'el-icon-loading' : 'el-icon-position'"></i>
          </button>
        </div>
      </form>

      <div v-if="error" class="desktop-toast" :class="{ 'success-toast': isSuccessToast }">
        {{ error }}
      </div>
    </section>

    <div v-if="workflowVisible" class="desktop-modal-backdrop workflow-backdrop" @click.self="closeWorkflow">
      <section class="desktop-modal workflow-modal">
        <header class="desktop-modal-header">
          <div>
            <h2>工作流图</h2>
            <p>{{ workflowDraft ? workflowDraft.name : '选择或创建当前会话的工作流图' }}</p>
          </div>
          <button class="icon-close" @click="closeWorkflow"><i class="el-icon-close"></i></button>
        </header>
        <div class="workflow-editor">
          <aside class="workflow-library">
            <div class="workflow-library-head">
              <strong>工作流产物</strong>
              <button type="button" @click="createWorkflowDraft">新建</button>
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
              <button type="button" :disabled="!workflowDraft" @click="addWorkflowNode">新增节点</button>
              <button type="button" :disabled="!workflowDraft" @click="copyWorkflowDraft">复制</button>
              <button type="button" class="danger-action" :disabled="!workflowDraft" @click="deleteWorkflowDraft">删除</button>
              <button type="button" class="workspace-primary" :disabled="!workflowDraft" @click="saveWorkflowDraft">保存并使用</button>
              <button type="button" class="workspace-primary" :disabled="!workflowDraft" @click="useWorkflowDraft">使用该图</button>
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

    <div v-if="artifactPreviewVisible" class="desktop-modal-backdrop artifact-preview-backdrop" @click.self="closeArtifactPreview">
      <section class="desktop-modal artifact-preview-modal">
        <header class="desktop-modal-header">
          <div>
            <h2>{{ artifactTitle(artifactPreviewArtifact) }}</h2>
            <p>{{ artifactTypeLabel(artifactPreviewArtifact) }} · {{ artifactSubtitle(artifactPreviewArtifact) }}</p>
          </div>
          <button class="icon-close" @click="closeArtifactPreview"><i class="el-icon-close"></i></button>
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

    <div v-if="attachmentsVisible" class="desktop-modal-backdrop drawer-backdrop" @click.self="attachmentsVisible = false">
      <section class="desktop-drawer attachments-drawer">
        <header class="desktop-modal-header">
          <div>
            <h2>上传文件</h2>
            <p>文件会上传到 Agent 容器的 userInput 目录。</p>
          </div>
          <button class="icon-close" @click="attachmentsVisible = false"><i class="el-icon-close"></i></button>
        </header>
        <div class="attachment-body">
          <label v-if="currentSessionAgents.length > 1" class="dialog-field inline-field">
            <span>目标 Agent</span>
            <select v-model="attachmentAgentId" @change="loadAttachments">
              <option v-for="agent in currentSessionAgents" :key="agent.agent_id" :value="agent.agent_id">
                {{ mentionName(agent) }}
              </option>
            </select>
          </label>
          <label class="upload-drop">
            <i class="el-icon-upload"></i>
            <span>{{ selectedUploadFile ? selectedUploadFile.name : '点击选择文件' }}</span>
            <small>支持图片、PDF、代码、文本等文件</small>
            <input ref="attachmentInput" type="file" @change="handleAttachmentFileChange" />
          </label>
          <div class="desktop-modal-actions">
            <button class="workspace-secondary" @click="loadAttachments">刷新</button>
            <button class="workspace-primary" :disabled="attachmentsLoading || !selectedUploadFile" @click="handleAttachmentUpload">
              {{ attachmentsLoading ? '上传中...' : '上传到容器' }}
            </button>
          </div>
          <div class="attachment-list">
            <div v-if="attachmentsLoading" class="mini-state"><i class="el-icon-loading"></i> 正在加载...</div>
            <div v-else-if="attachments.length === 0" class="mini-state">暂无上传文件</div>
            <div v-for="file in attachments" v-else :key="file.path" class="attachment-item">
              <i class="el-icon-document"></i>
              <div>
                <strong>{{ file.name || file.path }}</strong>
                <span>{{ file.path }}</span>
              </div>
              <button type="button" @click="previewAttachment(file)">查看</button>
              <button type="button" class="text-danger" @click="handleDeleteAttachment(file)">删除</button>
            </div>
          </div>
        </div>
      </section>
    </div>

    <div v-if="workspaceVisible" class="desktop-modal-backdrop" @click.self="workspaceVisible = false">
      <section class="desktop-modal workspace-modal">
        <header class="desktop-modal-header">
          <div>
            <h2>容器文件夹</h2>
            <p>{{ fileTreeRoot }}</p>
          </div>
          <button class="icon-close" @click="workspaceVisible = false"><i class="el-icon-close"></i></button>
        </header>
        <div class="workspace-browser">
          <aside class="workspace-tree">
            <div class="workspace-tree-actions">
              <button @click="switchFileScope('workspace')">全部</button>
              <button @click="switchFileScope('shared')">公共</button>
              <button
                v-for="agent in currentSessionAgents"
                :key="agent.agent_id"
                @click="switchFileScope(`agent:${agent.agent_id}`)"
              >{{ mentionName(agent) }}</button>
            </div>
            <button class="workspace-refresh" @click="loadFileTree(fileTreeRoot)">
              <i class="el-icon-refresh"></i>
              刷新
            </button>
            <div v-if="previewLoading" class="mini-state"><i class="el-icon-loading"></i> 正在读取...</div>
            <div v-else class="file-tree-list">
              <button
                v-for="node in flatFileTree"
                :key="node.path"
                class="file-tree-row"
                :style="{ paddingLeft: `${8 + node.depth * 16}px` }"
                @click="handleFileNodeClick(node)"
              >
                <i :class="node.type === 'directory' ? 'el-icon-folder' : getFileIcon(node.path)"></i>
                <span>{{ node.name }}</span>
              </button>
            </div>
          </aside>
          <section class="workspace-preview">
            <div v-if="selectedFilePath" class="file-preview-toolbar">
              <span>{{ selectedFilePath }}</span>
              <button @click="copyFilePath(selectedFilePath)">复制路径</button>
              <button @click="openWorkspaceFile(selectedFilePath)">打开</button>
            </div>
            <div v-if="!selectedFilePath" class="file-preview-empty">
              <i class="el-icon-folder-opened"></i>
              <span>选择左侧文件查看内容</span>
            </div>
            <iframe v-else-if="previewType === 'html' || previewType === 'pdf'" class="file-preview-frame" :src="previewUrl"></iframe>
            <div v-else-if="previewType === 'image'" class="file-preview-image-wrap">
              <img :src="previewUrl" class="file-preview-image" />
            </div>
            <pre v-else class="file-preview-code">{{ previewContent }}</pre>
          </section>
        </div>
      </section>
    </div>

    <div v-if="showCreate" class="desktop-modal-backdrop" @click.self="cancelCreate">
      <section class="desktop-modal create-agent-dialog">
        <header class="desktop-modal-header">
          <div>
            <h2>新建会话</h2>
            <p>选择一个或多个 Agent，桌面端会按 Web 端相同规则创建单聊或群聊。</p>
          </div>
          <button class="icon-close" @click="cancelCreate"><i class="el-icon-close"></i></button>
        </header>

        <label class="dialog-field">
          <span>会话标题</span>
          <input v-model.trim="newConversation.title" placeholder="选择 Agent 后自动生成" />
        </label>

        <div class="agent-picker">
          <div class="agent-picker-header">
            <span>选择 Agent</span>
            <small>已选择 {{ newConversation.selectedAgents.length }} 个</small>
          </div>
          <div v-if="agentsLoading" class="picker-state">
            <i class="el-icon-loading"></i>
            <span>正在加载 Agent...</span>
          </div>
          <label
            v-for="agent in agents"
            v-else
            :key="agent.id"
            class="agent-pick-item"
            :class="{ selected: newConversation.selectedAgents.includes(agent.id) }"
          >
            <input type="checkbox" :value="agent.id" v-model="newConversation.selectedAgents" />
            <span class="agent-pick-avatar" :style="agentAvatarStyle(agent)">
              <img v-if="agentAvatar(agent)" :src="agentAvatar(agent)" />
              <span v-else>{{ firstLetter(agent.name) }}</span>
            </span>
            <span class="agent-pick-main">
              <strong>{{ agent.name }}</strong>
              <small>{{ agent.adapter_name || agent.agent_type || 'custom' }}</small>
            </span>
            <i class="el-icon-check"></i>
          </label>
          <div v-if="!agentsLoading && agents.length === 0" class="picker-state">
            <i class="el-icon-user"></i>
            <span>暂无 Agent，请先到“我的 Agent”创建。</span>
          </div>
        </div>

        <footer class="desktop-modal-actions">
          <button class="workspace-secondary" @click="cancelCreate">取消</button>
          <button class="workspace-primary" :disabled="creating || newConversation.selectedAgents.length === 0" @click="handleCreateConversation">
            {{ creating ? '创建中...' : '创建' }}
          </button>
        </footer>
      </section>
    </div>
  </main>
</template>

<script>
import {
  createConversation,
  deleteConversation,
  deleteConversationAttachment,
  getConversationAttachments,
  getAgentFileUrl,
  getAgents,
  getConversations,
  getFileTree,
  getSandboxServiceLogs,
  getMessages,
  getProfile,
  getWorkspaceFileUrl,
  listSandboxServices,
  readAgentFile,
  restartSandboxService,
  sendMessage,
  stopSandboxService,
  updateConversationFavorite,
  uploadConversationAttachment,
} from '../services/api'
import { backendUrl, getServerUrl } from '../services/config'
import { clearAuth } from '../services/session'
import socketClient from '../services/socket'
import MessageBubble from '../components/MessageBubble.vue'

export default {
  name: 'Conversations',
  components: {
    MessageBubble,
  },
  data() {
    return {
      conversations: [],
      messagesByConversation: {},
      agents: [],
      profile: {},
      serverUrl: '',
      searchQuery: '',
      currentId: '',
      newConversation: {
        title: '',
        selectedAgents: [],
      },
      draft: '',
      showCreate: false,
      convLoading: false,
      messagesLoading: false,
      agentsLoading: false,
      creating: false,
      sending: false,
      error: '',
      showMoreMenu: false,
      activeTab: 'chat',
      sidePanelVisible: false,
      sidePanelMode: '',
      conversationAgentConfigs: {},
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
      serviceLogs: null,
      serviceLogsLoading: false,
      mentionVisible: false,
      mentionQuery: '',
      mentionIndex: 0,
      selectedMentions: [],
      detailPanelVisible: false,
      detailPanelMode: 'search',
      messageSearchQuery: '',
      highlightedMessageId: '',
      highlightTimer: null,
      attachmentsVisible: false,
      attachmentsLoading: false,
      attachments: [],
      selectedUploadFile: null,
      attachmentAgentId: '',
      workspaceVisible: false,
      previewLoading: false,
      fileTreeData: [],
      fileTreeRoot: '/workspace',
      fileScope: 'workspace',
      selectedFilePath: '',
      previewAgentId: '',
      previewContent: '',
      previewType: 'text',
      previewUrl: '',
      tabs: [
        { key: 'chat', label: '对话' },
        { key: 'agent_config', label: '智能体配置' },
        { key: 'artifacts', label: '产物' },
        { key: 'logs', label: '日志' },
        { key: 'workflow', label: '工作流图' },
      ],
      socketHandlers: [],
    }
  },
  computed: {
    filteredConversations() {
      if (!this.searchQuery) return this.conversations
      const query = this.searchQuery.toLowerCase()
      return this.conversations.filter(item => String(item.title || '').toLowerCase().includes(query))
    },
    currentConversation() {
      return this.conversations.find(item => item.id === this.currentId) || null
    },
    currentMessages() {
      return this.messagesByConversation[this.currentId] || []
    },
    messageSearchResults() {
      const query = this.messageSearchQuery.trim().toLowerCase()
      if (!query) return []
      return this.currentMessages
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
      return this.currentMessages
        .filter(message => message.sender_type === 'user')
        .map(message => ({
          message,
          title: this.buildMessageTitle(message),
          snippet: this.buildSearchSnippet(this.collectMessageText(message), ''),
        }))
    },
    currentSessionAgents() {
      const participants = (this.currentConversation && this.currentConversation.participants_info) || []
      return participants
        .filter(p => p.participant_type === 'agent')
        .map(p => ({
          agent_id: p.participant_id,
          role: p.name,
          name: p.name,
          workspace_name: this.safeWorkspaceName(p.name || p.participant_id),
          avatar: this.participantAvatar(p),
          color: this.participantColor(p),
        }))
    },
    currentAgentConfigs() {
      if (!this.currentId) return []
      return this.conversationAgentConfigs[this.currentId] || []
    },
    singleAgentConfigLocked() {
      return this.currentAgentConfigs.length <= 1
    },
    enabledSessionAgents() {
      return (this.currentSessionAgents || []).filter(agent => agent && agent.agent_id && this.isSessionAgentEnabled(agent.agent_id))
    },
    conversationArtifacts() {
      const artifacts = []
      const seen = new Set()
      this.currentMessages.forEach(message => {
        const elements = Array.isArray(message.elements) ? message.elements : []
        elements.forEach(element => {
          if (!element || !['code', 'table', 'image', 'file', 'service'].includes(element.type)) return
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
    workflowArtifacts() {
      const workflows = []
      this.currentMessages.forEach(message => {
        const elements = Array.isArray(message.elements) ? message.elements : []
        elements.forEach(element => {
          if (!element || element.type !== 'workflow') return
          const workflow = this.normalizeWorkflow(this.elementData(element), message)
          if (workflow) workflows.push(workflow)
        })
      })
      return workflows
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
          return { ...edge, x1: from.x + 232, y1: from.y + 62, x2: to.x, y2: to.y + 62 }
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
    selectedService() {
      return this.sandboxServices.find(service => String(service.id) === String(this.selectedServiceId)) || null
    },
    formattedServiceLogs() {
      if (!this.serviceLogs) return ''
      const stdout = this.serviceLogs.stdout_tail || ''
      const stderr = this.serviceLogs.stderr_tail || ''
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
    sidePanelSubtitle() {
      if (this.sidePanelMode === 'agent_config') return '只影响当前会话，不更新全局 Agent'
      if (this.sidePanelMode === 'artifacts') return `当前会话 ${this.conversationArtifacts.length} 个产物`
      if (this.sidePanelMode === 'logs') return '容器中 app 服务的 stdout / stderr'
      return ''
    },
    isSuccessToast() {
      return [
        '当前会话的智能体配置已保存',
        '已复制产物引用',
        '服务已运行',
        '服务已停止',
        '工作流图已保存并设为本轮默认',
      ].includes(this.error)
    },
    mentionCandidates() {
      const query = String(this.mentionQuery || '').toLowerCase()
      const agents = (this.currentSessionAgents || []).filter(agent => agent && agent.agent_id && this.isSessionAgentEnabled(agent.agent_id))
      const filtered = query
        ? agents.filter(agent => {
          const name = this.mentionName(agent).toLowerCase()
          const id = String(agent.agent_id || '').toLowerCase()
          return name.includes(query) || id.includes(query)
        })
        : agents
      return filtered.slice(0, 8)
    },
    currentSessionId() {
      return (this.currentConversation && (this.currentConversation.sandbox_session_id || this.currentConversation.id)) || ''
    },
    flatFileTree() {
      const rows = []
      const visit = (node, depth = 0) => {
        if (!node) return
        rows.push({ ...node, depth })
        ;(node.children || []).forEach(child => visit(child, depth + 1))
      }
      this.fileTreeData.forEach(node => visit(node, 0))
      return rows
    },
  },
  watch: {
    'newConversation.selectedAgents': function updateTitle() {
      const names = this.newConversation.selectedAgents
        .map(id => this.agents.find(agent => agent.id === id))
        .filter(Boolean)
        .map(agent => agent.name)
      this.newConversation.title = [this.profile.username || '我', ...names].join('、')
    },
    '$route.query.conversation_id': function handleConversationQueryChange() {
      this.selectConversationFromRoute()
    },
    workflowDraft: {
      deep: true,
      handler() {
        if (this.syncingWorkflowJson) return
        this.refreshWorkflowJsonText()
      },
    },
  },
  async created() {
    this.serverUrl = await getServerUrl()
    await socketClient.connect()
    this.registerSocketHandlers()
    await Promise.all([this.loadProfile(), this.loadAgents(), this.loadConversations()])
  },
  beforeDestroy() {
    if (this.currentId) socketClient.leaveConversation(this.currentId)
    window.clearTimeout(this.highlightTimer)
    this.unregisterSocketHandlers()
  },
  methods: {
    async loadProfile() {
      try {
        const response = await getProfile()
        this.profile = response.data || {}
      } catch (error) {
        this.handleRequestError(error, '加载个人信息失败')
      }
    },
    async loadAgents() {
      this.agentsLoading = true
      try {
        const response = await getAgents()
        this.agents = Array.isArray(response.data) ? response.data : []
      } catch (error) {
        this.handleRequestError(error, '加载 Agent 失败')
      } finally {
        this.agentsLoading = false
      }
    },
    async loadConversations() {
      this.error = ''
      this.convLoading = true
      try {
        const response = await getConversations()
        this.conversations = Array.isArray(response.data) ? response.data : []
        if (await this.selectConversationFromRoute()) return
        if (!this.currentId && this.conversations.length) {
          await this.selectConversation(this.conversations[0])
        }
      } catch (error) {
        this.handleRequestError(error, '加载会话失败')
      } finally {
        this.convLoading = false
      }
    },
    openCreateDialog() {
      this.showCreate = true
      if (!this.agents.length) this.loadAgents()
    },
    async handleCreateConversation() {
      if (!this.newConversation.selectedAgents.length || this.creating) return
      this.error = ''
      this.creating = true
      try {
        const participantIds = this.newConversation.selectedAgents.map(id => `agent_${id}`)
        const response = await createConversation({
          title: this.newConversation.title || '新建会话',
          type: participantIds.length > 1 ? 'group' : 'single',
          participant_ids: participantIds,
        })
        if (response.code === 201 && response.data) {
          this.conversations = [response.data, ...this.conversations]
          this.cancelCreate()
          await this.selectConversation(response.data)
        } else {
          this.error = response.message || '创建会话失败'
        }
      } catch (error) {
        this.handleRequestError(error, '创建会话失败')
      } finally {
        this.creating = false
      }
    },
    async handleDeleteConversation(conversation) {
      if (!conversation || !conversation.id) return
      if (!window.confirm(`删除会话「${conversation.title || '未命名会话'}」？`)) return
      this.error = ''
      try {
        if (this.currentId === conversation.id) {
          socketClient.leaveConversation(conversation.id)
        }
        const response = await deleteConversation(conversation.id)
        if (response.code && ![200, 204].includes(response.code)) {
          this.error = response.message || '删除会话失败'
          return
        }
        this.$delete(this.messagesByConversation, conversation.id)
        this.conversations = this.conversations.filter(item => item.id !== conversation.id)
        if (this.currentId === conversation.id) {
          this.currentId = ''
          const next = this.conversations[0]
          if (next) await this.selectConversation(next)
        }
        this.showMoreMenu = false
      } catch (error) {
        this.handleRequestError(error, '删除会话失败')
      }
    },
    cancelCreate() {
      this.showCreate = false
      this.newConversation = { title: '', selectedAgents: [] }
    },
    async selectConversation(conversation) {
      if (!conversation || !conversation.id) return
      if (this.currentId && this.currentId !== conversation.id) {
        socketClient.leaveConversation(this.currentId)
      }
      this.currentId = conversation.id
      this.activeTab = 'chat'
      this.showMoreMenu = false
      this.closeDetailPanel()
      this.closeSidePanel()
      this.sandboxServices = []
      this.selectedServiceId = ''
      this.serviceLogs = null
      this.ensureConversationAgentConfigs(conversation)
      this.loadSavedWorkflows()
      this.resetMentionState()
      socketClient.joinConversation(conversation.id)
      await this.loadMessages(conversation.id)
    },
    async selectConversationFromRoute() {
      const id = this.$route && this.$route.query && this.$route.query.conversation_id
      if (!id) return false
      const target = this.conversations.find(item => String(item.id) === String(id))
      if (!target) return false
      if (String(this.currentId) !== String(target.id)) {
        await this.selectConversation(target)
      }
      return true
    },
    updateLocalConversation(conversation) {
      if (!conversation || !conversation.id) return
      const index = this.conversations.findIndex(item => String(item.id) === String(conversation.id))
      if (index >= 0) {
        this.$set(this.conversations, index, { ...this.conversations[index], ...conversation })
      }
    },
    async toggleFavorite() {
      if (!this.currentConversation) return
      const previous = Boolean(this.currentConversation.is_favorite)
      const nextValue = !previous
      const optimistic = { ...this.currentConversation, is_favorite: nextValue }
      this.updateLocalConversation(optimistic)
      this.error = ''
      try {
        const response = await updateConversationFavorite(this.currentConversation.id, nextValue)
        const payload = response && response.data && (response.data.conversation || response.data)
        const saved = payload && payload.id ? payload : optimistic
        if (saved.is_favorite === undefined) saved.is_favorite = nextValue
        this.updateLocalConversation(saved)
      } catch (error) {
        this.updateLocalConversation({ ...optimistic, is_favorite: previous })
        this.handleRequestError(error, nextValue ? '收藏会话失败' : '取消收藏失败')
      }
    },
    toggleSearchPanel() {
      if (!this.currentConversation) return
      if (this.detailPanelVisible && this.detailPanelMode === 'search') {
        this.closeDetailPanel()
        return
      }
      this.detailPanelMode = 'search'
      this.detailPanelVisible = true
      this.$nextTick(() => {
        if (this.$refs.messageSearchInput) this.$refs.messageSearchInput.focus()
      })
    },
    toggleHistoryPanel() {
      if (!this.currentConversation) return
      if (this.detailPanelVisible && this.detailPanelMode === 'history') {
        this.closeDetailPanel()
        return
      }
      this.detailPanelMode = 'history'
      this.detailPanelVisible = true
    },
    closeDetailPanel() {
      this.detailPanelVisible = false
      this.highlightedMessageId = ''
    },
    jumpToFirstSearchResult() {
      if (this.messageSearchResults.length) {
        this.jumpToMessage(this.messageSearchResults[0].message.id)
      }
    },
    jumpToMessage(messageId) {
      if (!messageId) return
      this.$nextTick(() => {
        const ref = this.$refs[`message-${messageId}`]
        const element = Array.isArray(ref) ? ref[0] : ref
        if (!element) return
        element.scrollIntoView({ behavior: 'smooth', block: 'center' })
        this.highlightedMessageId = messageId
        window.clearTimeout(this.highlightTimer)
        this.highlightTimer = window.setTimeout(() => {
          if (this.highlightedMessageId === messageId) this.highlightedMessageId = ''
        }, 1800)
      })
    },
    collectMessageText(message) {
      if (!message) return ''
      const chunks = [
        message.content,
        message.raw_output,
        message.sender_name,
        message.status,
      ]
      const visit = value => {
        if (value === null || value === undefined) return
        if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
          chunks.push(String(value))
          return
        }
        if (Array.isArray(value)) {
          value.forEach(visit)
          return
        }
        if (typeof value === 'object') {
          ;['title', 'name', 'filename', 'path', 'url', 'content', 'text', 'summary', 'status'].forEach(key => {
            if (value[key] !== undefined) visit(value[key])
          })
          if (value.data) visit(value.data)
          if (value.detail) visit(value.detail)
        }
      }
      visit(message.elements)
      visit(message.meta && message.meta.events)
      return chunks.filter(Boolean).join('\n')
    },
    buildMessageTitle(message) {
      const prefix = this.isOwnMessage(message) ? '我' : this.senderName(message)
      const text = this.collectMessageText(message).replace(/\s+/g, ' ').trim()
      return `${prefix}: ${text ? text.slice(0, 32) : '空消息'}${text.length > 32 ? '...' : ''}`
    },
    buildSearchSnippet(text, query) {
      const value = String(text || '').replace(/\s+/g, ' ').trim()
      if (!value) return '暂无可预览内容'
      if (!query) return `${value.slice(0, 80)}${value.length > 80 ? '...' : ''}`
      const lower = value.toLowerCase()
      const index = lower.indexOf(String(query || '').toLowerCase())
      if (index < 0) return `${value.slice(0, 80)}${value.length > 80 ? '...' : ''}`
      const start = Math.max(0, index - 24)
      const end = Math.min(value.length, index + String(query).length + 56)
      return `${start > 0 ? '...' : ''}${value.slice(start, end)}${end < value.length ? '...' : ''}`
    },
    async loadMessages(conversationId) {
      if (!conversationId) return
      this.error = ''
      this.messagesLoading = true
      try {
        const response = await getMessages(conversationId, { page: 1, per_page: 80 })
        const items = this.sortMessages((response.data && response.data.items) || [])
        this.$set(this.messagesByConversation, conversationId, items)
        this.$nextTick(this.scrollToBottom)
      } catch (error) {
        this.handleRequestError(error, '加载消息失败')
      } finally {
        this.messagesLoading = false
      }
    },
    async handleSendMessage() {
      const content = this.draft.trim()
      if (!this.currentConversation || !content || this.sending) return
      const payload = this.buildMessagePayload()
      this.error = ''
      this.sending = true
      const messageMeta = {}
      if (payload.target_agent_ids.length) {
        messageMeta.dispatch_mode = 'direct'
        messageMeta.mentions = payload.mentions
      }
      if (payload.workflow) {
        messageMeta.selected_workflow = this.selectedWorkflowMeta(payload.workflow)
      }

      const temp = {
        id: `temp_${Date.now()}`,
        conversation_id: this.currentConversation.id,
        sender_type: 'user',
        sender_id: this.profile.id,
        content,
        message_type: 'text',
        created_at: new Date().toISOString(),
        meta: Object.keys(messageMeta).length ? messageMeta : undefined,
      }
        this.$set(this.messagesByConversation, this.currentConversation.id, this.sortMessages([
          ...this.currentMessages,
          temp,
        ]))
      this.draft = ''
      this.resetMentionState()
      this.$nextTick(this.scrollToBottom)

      try {
        const requestData = {
          conversation_id: this.currentConversation.id,
          content: payload.content,
          message_type: 'text',
        }
        if (payload.target_agent_ids.length) {
          requestData.target_agent_ids = payload.target_agent_ids
        }
        if (payload.agent_configs && Object.keys(payload.agent_configs).length) {
          requestData.agent_configs = payload.agent_configs
        }
        if (payload.workflow) {
          requestData.workflow = payload.workflow
        }
        const response = await sendMessage(requestData)
        if (response.code === 201) {
          await this.loadMessages(this.currentConversation.id)
          await this.loadConversations()
        } else {
          this.error = response.message || '发送失败'
        }
      } catch (error) {
        this.handleRequestError(error, '发送失败')
        await this.loadMessages(this.currentConversation.id)
      } finally {
        this.sending = false
      }
    },
    selectedWorkflowMeta(workflow) {
      return {
        id: workflow?.id || '',
        name: workflow?.name || '未命名工作流',
        nodes: Array.isArray(workflow?.nodes) ? workflow.nodes : [],
        edges: Array.isArray(workflow?.edges) ? workflow.edges : [],
        parallel_groups: Array.isArray(workflow?.parallel_groups) ? workflow.parallel_groups : [],
      }
    },
    avatarParticipants(conversation) {
      if (!conversation || !conversation.participants_info) return []
      if (conversation.type === 'single') {
        return conversation.participants_info.filter(p => p.participant_type !== 'user').slice(0, 1)
      }
      return conversation.participants_info
    },
    convAvatarBg(conversation) {
      const infos = this.avatarParticipants(conversation)
      if (infos.length !== 1 || this.participantAvatar(infos[0])) return {}
      return { background: this.participantColor(infos[0]) }
    },
    participantAvatar(participant) {
      const avatar = participant && (participant.avatar || participant.avatar_url)
      return avatar ? backendUrl(this.serverUrl, avatar) : ''
    },
    participantColor(participant) {
      return (participant && (participant.color || participant.avatar_color)) || '#4080ff'
    },
    safeWorkspaceName(name) {
      return String(name || 'agent')
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9\u4e00-\u9fa5_-]+/gi, '-')
        .replace(/^-+|-+$/g, '')
        .slice(0, 80) || 'agent'
    },
    agentAvatar(agent) {
      return agent && agent.avatar_url ? backendUrl(this.serverUrl, agent.avatar_url) : ''
    },
    agentAvatarStyle(agent) {
      return this.agentAvatar(agent) ? {} : { background: (agent && agent.avatar_color) || '#4080ff' }
    },
    participantCount(conversation) {
      return ((conversation && conversation.participants_info) || (conversation && conversation.participant_ids) || []).length
    },
    isOwnMessage(message) {
      return message && message.sender_type === 'user'
    },
    senderName(message) {
      if (message && message.sender_name) return message.sender_name
      return this.isOwnMessage(message) ? (this.profile.username || '我') : '智能体'
    },
    senderParticipant(message) {
      const participants = (this.currentConversation && this.currentConversation.participants_info) || []
      if (!message) return null
      return participants.find(p =>
        (p.participant_type === message.sender_type && String(p.participant_id) === String(message.sender_id))
        || (message.sender_name && p.name === message.sender_name)
      ) || null
    },
    messageAvatar(message) {
      if (this.isOwnMessage(message)) {
        return this.profile.avatar_url ? backendUrl(this.serverUrl, this.profile.avatar_url) : ''
      }
      return this.participantAvatar(this.senderParticipant(message))
    },
    messageAvatarStyle(message) {
      const avatar = this.messageAvatar(message)
      if (avatar) return {}
      const participant = this.senderParticipant(message)
      return { background: this.isOwnMessage(message) ? '#4080ff' : this.participantColor(participant) }
    },
    firstLetter(value) {
      return String(value || '?').charAt(0).toUpperCase()
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
        this.handleSendMessage()
      }
    },
    syncMentionState() {
      const match = /@([^\s@，,：:；;]*)$/.exec(this.draft)
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
      this.draft = this.draft.replace(/@([^\s@，,：:；;]*)$/, `@${name} `)
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
        return this.draft.includes(`@${item.name}`) && this.isSessionAgentEnabled(item.agent_id)
      })
    },
    buildMessagePayload() {
      this.syncSelectedMentions()
      const targetIds = this.selectedMentions.map(item => item.agent_id)
      return {
        content: this.draft.trim(),
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
      return `weagent.desktop.workflows.${this.currentId || ''}`
    },
    workflowSelectionStorageKey() {
      return `weagent.desktop.selectedWorkflow.${this.currentId || ''}`
    },
    workflowDeletedStorageKey() {
      return `weagent.desktop.deletedWorkflows.${this.currentId || ''}`
    },
    loadSavedWorkflows() {
      if (!this.currentId) {
        this.savedWorkflows = []
        this.deletedWorkflowIds = []
        this.workflowDraft = null
        return
      }
      try {
        const saved = JSON.parse(localStorage.getItem(this.workflowStorageKey()) || '[]')
        this.savedWorkflows = Array.isArray(saved) ? saved.map(item => this.normalizeWorkflow(item)).filter(Boolean) : []
      } catch (error) {
        this.savedWorkflows = []
      }
      try {
        const deleted = JSON.parse(localStorage.getItem(this.workflowDeletedStorageKey()) || '[]')
        this.deletedWorkflowIds = Array.isArray(deleted) ? deleted.map(String) : []
      } catch (error) {
        this.deletedWorkflowIds = []
      }
      const selectedId = localStorage.getItem(this.workflowSelectionStorageKey()) || ''
      const selected = this.allWorkflows.find(item => item.id === selectedId) || this.allWorkflows[0]
      if (!this.workflowDraft && selected) this.selectWorkflow(selected)
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
        id: String(workflow.id || `workflow-${message && message.id ? message.id : Date.now()}`),
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
      if (this.currentId) localStorage.setItem(this.workflowSelectionStorageKey(), normalized.id)
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
      this.error = '工作流图已保存并设为本轮默认'
      window.setTimeout(() => {
        if (this.error === '工作流图已保存并设为本轮默认') this.error = ''
      }, 1600)
    },
    useWorkflowDraft() {
      if (!this.workflowDraft) return
      const workflow = this.activeWorkflowPayload() || this.workflowDraft
      this.selectedWorkflowId = workflow.id
      if (this.currentId) localStorage.setItem(this.workflowSelectionStorageKey(), workflow.id)
      this.workflowVisible = false
      this.activeTab = 'chat'
      if (!this.draft.trim()) {
        this.draft = '请根据这个图来分配工作来完成任务：'
      }
    },
    clearSelectedWorkflow() {
      this.selectedWorkflowId = ''
      if (this.currentId) localStorage.removeItem(this.workflowSelectionStorageKey())
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
      if (this.currentId) {
        localStorage.setItem(this.workflowStorageKey(), JSON.stringify(this.savedWorkflows))
      }
      if (id && !this.deletedWorkflowIds.includes(id)) {
        this.deletedWorkflowIds = [...this.deletedWorkflowIds, id]
        if (this.currentId) {
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
        if (this.currentId) localStorage.setItem(this.workflowSelectionStorageKey(), next.id)
      }
      this.workflowConnectFrom = ''
      this.error = '工作流图已删除'
      window.setTimeout(() => {
        if (this.error === '工作流图已删除') this.error = ''
      }, 1600)
    },
    copyWorkflowJson() {
      this.copyTextToClipboard(this.workflowJsonText || this.workflowJsonPreview)
        .then(() => {
          this.error = 'JSON 已复制'
          window.setTimeout(() => {
            if (this.error === 'JSON 已复制') this.error = ''
          }, 1600)
        })
        .catch(() => {
          this.error = '复制失败'
        })
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
      this.workflowDrag = { node, offsetX: event.offsetX, offsetY: event.offsetY }
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
    resetMentionState() {
      this.mentionVisible = false
      this.mentionQuery = ''
      this.mentionIndex = 0
      this.selectedMentions = []
    },
    mentionName(agent) {
      return (agent && (agent.role || agent.name || agent.agent_id)) || ''
    },
    isSessionAgentEnabled(agentId) {
      if (this.singleAgentConfigLocked) return true
      const config = this.currentAgentConfigs.find(item => String(item.agent_id) === String(agentId))
      return !config || config.enabled !== false
    },
    handleTabSwitch(key) {
      this.activeTab = key
      this.error = ''
      if (key === 'chat') {
        this.closeSidePanel()
        return
      }
      if (key === 'workflow') {
        this.sidePanelVisible = false
        this.sidePanelMode = ''
        this.workflowVisible = true
        this.activeTab = 'workflow'
        return
      }
      this.sidePanelMode = key
      this.sidePanelVisible = true
      if (key === 'agent_config') {
        this.ensureConversationAgentConfigs(this.currentConversation)
      } else if (key === 'logs') {
        this.loadSandboxServices()
      }
    },
    closeSidePanel() {
      this.sidePanelVisible = false
      this.sidePanelMode = ''
      if (this.activeTab !== 'workflow') this.activeTab = 'chat'
    },
    closeWorkflow() {
      this.workflowVisible = false
      this.activeTab = 'chat'
    },
    sessionConfigStorageKey(conversationId) {
      return `weagent.desktop.sessionAgentConfigs.${conversationId}`
    },
    ensureConversationAgentConfigs(conversation) {
      if (!conversation || !conversation.id) return
      const storageKey = this.sessionConfigStorageKey(conversation.id)
      let saved = []
      try {
        saved = JSON.parse(localStorage.getItem(storageKey) || '[]')
      } catch (error) {
        saved = []
      }
      const savedMap = new Map((Array.isArray(saved) ? saved : []).map(item => [String(item.agent_id), item]))
      const configs = this.currentSessionAgents.map(agent => {
        const globalAgent = this.agents.find(item => String(item.id) === String(agent.agent_id)) || {}
        const savedItem = savedMap.get(String(agent.agent_id)) || {}
        return {
          agent_id: agent.agent_id,
          name: agent.name || globalAgent.name || agent.agent_id,
          role: savedItem.role || agent.role || globalAgent.name || agent.agent_id,
          avatar: agent.avatar || this.agentAvatar(globalAgent),
          color: agent.color || globalAgent.avatar_color || '#4080ff',
          adapter_name: savedItem.adapter_name || globalAgent.adapter_name || globalAgent.agent_type || '',
          system_prompt: savedItem.system_prompt || globalAgent.system_prompt || '',
          skill: savedItem.skill || globalAgent.skill || '',
          enabled: this.currentSessionAgents.length <= 1 ? true : savedItem.enabled !== false,
        }
      })
      this.$set(this.conversationAgentConfigs, conversation.id, configs)
    },
    saveSessionAgentConfigs() {
      if (!this.currentId) return
      const configs = this.currentAgentConfigs.map(item => ({ ...item }))
      localStorage.setItem(this.sessionConfigStorageKey(this.currentId), JSON.stringify(configs))
      this.error = '当前会话的智能体配置已保存'
      window.setTimeout(() => {
        if (this.error === '当前会话的智能体配置已保存') this.error = ''
      }, 1600)
    },
    resetSessionAgentConfig(agentId) {
      if (!this.currentConversation || !agentId) return
      const storageKey = this.sessionConfigStorageKey(this.currentConversation.id)
      let saved = []
      try {
        saved = JSON.parse(localStorage.getItem(storageKey) || '[]')
      } catch (error) {
        saved = []
      }
      localStorage.setItem(storageKey, JSON.stringify((Array.isArray(saved) ? saved : []).filter(item => String(item.agent_id) !== String(agentId))))
      this.ensureConversationAgentConfigs(this.currentConversation)
    },
    artifactIcon(artifact) {
      const type = artifact && artifact.type
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
      return map[(artifact && artifact.type) || ''] || '产物'
    },
    artifactTitle(artifact) {
      const data = (artifact && artifact.data) || {}
      return data.title || data.name || data.filename || data.path || this.elementContent(artifact.element) || '产物'
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
      if (!artifact) return ''
      const data = artifact.data || {}
      const content = this.elementContent(artifact.element)
      return String(content || '').replace(/\s+/g, ' ').slice(0, 96)
    },
    artifactTablePayload(artifact) {
      const element = (artifact && artifact.element) || {}
      const data = (artifact && artifact.data) || this.elementData(element)
      const candidates = [data, data && data.data]
      const content = this.elementContent(element)
      if (content) {
        try {
          const parsed = JSON.parse(content)
          candidates.push(parsed, parsed && parsed.data)
        } catch (error) {}
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
        const cells = Array.isArray(row) ? row : headers.map(header => row && row[header])
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
      } catch (error) {
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
    openConversationArtifact(artifact) {
      if (!artifact) return
      if (artifact.type === 'code' && artifact.data && artifact.data.workflow) {
        this.openWorkflowPreview(artifact.data.workflow)
        return
      }
      if (artifact.type === 'service') {
        const url = this.serviceInfoFromArtifact(artifact).url
        if (url) window.open(url, '_blank')
        return
      }
      if (artifact.type === 'table') {
        this.openArtifactPreview(artifact)
        return
      }
      const data = artifact.data || {}
      const raw = data.path || data.file_path || data.filePath || data.file || data.url || data.src || this.elementContent(artifact.element)
      const path = this.normalizeWorkspaceFilePath(raw)
      if (path) {
        this.handleOpenMessageFile({
          path,
          raw,
          name: data.name || data.filename || data.title || path,
          agent_id: data.agent_id || data.agentId || data.owner_agent_id || '',
          type: artifact.type,
        })
      } else if (this.artifactPreviewContent(artifact)) {
        this.openArtifactPreview(artifact)
      }
    },
    artifactReference(artifact) {
      const data = (artifact && artifact.data) || {}
      return data.path || data.url || data.proxy_url || data.name || data.filename || this.elementContent(artifact && artifact.element) || this.artifactTitle(artifact)
    },
    serviceInfoFromArtifact(artifact) {
      const data = (artifact && artifact.data) || {}
      const nested = data.service && typeof data.service === 'object' ? data.service : {}
      return {
        id: data.service_id || data.id || nested.service_id || nested.id || '',
        url: data.proxy_url || nested.proxy_url || data.url || nested.url || '',
      }
    },
    async copyArtifactReference(artifact) {
      const text = this.artifactReference(artifact)
      if (!text || !navigator.clipboard) return
      await navigator.clipboard.writeText(text)
      this.error = '已复制产物引用'
      window.setTimeout(() => {
        if (this.error === '已复制产物引用') this.error = ''
      }, 1400)
    },
    async runArtifactService(artifact) {
      const id = this.serviceInfoFromArtifact(artifact).id
      if (!this.currentSessionId || !id) {
        this.error = '未找到服务 ID'
        return
      }
      try {
        const response = await restartSandboxService(this.currentSessionId, id)
        if (!response.code || response.code === 200) {
          this.error = '服务已运行'
          await this.loadSandboxServices()
        }
      } catch (error) {
        this.handleRequestError(error, '运行服务失败')
      }
    },
    async stopArtifactService(artifact) {
      const id = this.serviceInfoFromArtifact(artifact).id
      if (!this.currentSessionId || !id) {
        this.error = '未找到服务 ID'
        return
      }
      try {
        const response = await stopSandboxService(this.currentSessionId, id)
        if (!response.code || response.code === 200) {
          this.error = '服务已停止'
          await this.loadSandboxServices()
        }
      } catch (error) {
        this.handleRequestError(error, '停止服务失败')
      }
    },
    async loadSandboxServices() {
      if (!this.currentSessionId) return
      this.serviceLogsLoading = true
      this.error = ''
      try {
        const response = await listSandboxServices(this.currentSessionId)
        const services = (response.data && response.data.services) || response.services || []
        this.sandboxServices = Array.isArray(services) ? services : []
        if (!this.selectedServiceId && this.sandboxServices.length) {
          this.selectedServiceId = this.sandboxServices[0].id
        }
        if (this.selectedServiceId) await this.loadSelectedServiceLogs()
      } catch (error) {
        this.handleRequestError(error, '加载容器服务失败')
      } finally {
        this.serviceLogsLoading = false
      }
    },
    async loadSelectedServiceLogs() {
      if (!this.currentSessionId || !this.selectedServiceId) {
        this.serviceLogs = null
        return
      }
      this.serviceLogsLoading = true
      try {
        const response = await getSandboxServiceLogs(this.currentSessionId, this.selectedServiceId)
        this.serviceLogs = (response.data && (response.data.logs || response.data)) || response.logs || response
      } catch (error) {
        this.handleRequestError(error, '读取容器日志失败')
      } finally {
        this.serviceLogsLoading = false
      }
    },
    sortMessages(messages) {
      return [...(messages || [])].sort((a, b) => {
        const at = new Date(a.created_at || 0).getTime() || 0
        const bt = new Date(b.created_at || 0).getTime() || 0
        if (at !== bt) return at - bt
        if (a.sender_type !== b.sender_type) {
          if (a.sender_type === 'user') return -1
          if (b.sender_type === 'user') return 1
        }
        return String(a.id || '').localeCompare(String(b.id || ''))
      })
    },
    async handleOpenAttachments() {
      if (!this.currentConversation) return
      this.attachmentsVisible = true
      if (!this.attachmentAgentId && this.currentSessionAgents.length) {
        this.attachmentAgentId = this.currentSessionAgents[0].agent_id
      }
      await this.loadAttachments({ silent: true })
    },
    async loadAttachments(options = {}) {
      if (!this.currentConversation) return
      this.attachmentsLoading = true
      if (!options.silent) this.error = ''
      try {
        const response = await getConversationAttachments(
          this.currentConversation.id,
          this.currentSessionAgents.length > 1 ? this.attachmentAgentId : ''
        )
        this.attachments = (response.data && response.data.files) || []
        if (response.data && response.data.agent_id) this.attachmentAgentId = response.data.agent_id
      } catch (error) {
        if (!options.silent) this.handleRequestError(error, '加载附件失败')
      } finally {
        this.attachmentsLoading = false
      }
    },
    handleAttachmentFileChange(event) {
      this.selectedUploadFile = event.target.files && event.target.files[0] ? event.target.files[0] : null
    },
    async handleAttachmentUpload() {
      if (!this.currentConversation || !this.selectedUploadFile) return
      this.attachmentsLoading = true
      this.error = ''
      try {
        const response = await uploadConversationAttachment(
          this.currentConversation.id,
          this.selectedUploadFile,
          this.currentSessionAgents.length > 1 ? this.attachmentAgentId : ''
        )
        const uploaded = response && response.data
        this.selectedUploadFile = null
        if (this.$refs.attachmentInput) this.$refs.attachmentInput.value = ''
        if (uploaded && uploaded.path && !this.attachments.some(item => item.path === uploaded.path)) {
          this.attachments = [uploaded, ...this.attachments]
        }
        await this.loadAttachments({ silent: true })
      } catch (error) {
        this.handleRequestError(error, '上传文件失败')
      } finally {
        this.attachmentsLoading = false
      }
    },
    async handleDeleteAttachment(file) {
      if (!file || !file.path) return
      if (!window.confirm(`删除文件「${file.name || file.path}」？`)) return
      this.attachmentsLoading = true
      try {
        await deleteConversationAttachment(this.currentConversation.id, file.path, file.agent_id || this.attachmentAgentId)
        await this.loadAttachments()
      } catch (error) {
        this.handleRequestError(error, '删除文件失败')
      } finally {
        this.attachmentsLoading = false
      }
    },
    previewAttachment(file) {
      if (!file || !file.path) return
      this.previewAgentId = file.agent_id || this.attachmentAgentId || ''
      this.previewFile(file.path)
    },
    async handleOpenMessageFile(file) {
      const filePath = this.normalizeWorkspaceFilePath(file && (file.path || file.url || file.raw || file.name))
      if (!filePath) return
      const agentId = (file && (file.agent_id || file.agentId)) || this.inferAgentIdFromFilePath(filePath) || ''
      this.workspaceVisible = true
      this.previewAgentId = agentId
      this.fileScope = agentId ? `agent:${agentId}` : 'workspace'
      await this.loadFileTree(this.fileRootForPath(filePath))
      await this.previewFile(filePath)
    },
    normalizeWorkspaceFilePath(value) {
      let path = String(value || '').trim()
      if (!path) return ''
      try {
        if (/^https?:\/\//i.test(path)) {
          const url = new URL(path)
          const queryPath = url.searchParams.get('path') || url.searchParams.get('file') || url.searchParams.get('file_path')
          const urlPath = decodeURIComponent(url.pathname || '')
          path = queryPath || (urlPath.includes('/workspace/') ? urlPath : '')
        }
      } catch (error) {
        // Keep the original value when URL parsing is not possible.
      }
      const workspaceIndex = path.indexOf('/workspace/')
      if (workspaceIndex >= 0) return path.slice(workspaceIndex)
      if (path.indexOf('workspace/') === 0) return `/${path}`
      return path
    },
    fileRootForPath(filePath) {
      const path = String(filePath || '')
      const lastSlash = path.lastIndexOf('/')
      if (lastSlash <= 0) return '/workspace'
      return path.slice(0, lastSlash) || '/workspace'
    },
    inferAgentIdFromFilePath(filePath) {
      const match = String(filePath || '').match(/\/workspace\/agents\/([^/]+)/)
      if (!match) return ''
      const workspaceName = decodeURIComponent(match[1])
      const agent = this.currentSessionAgents.find(item => {
        const names = [
          item.workspace_name,
          this.safeWorkspaceName(item.role),
          this.safeWorkspaceName(item.name),
          this.safeWorkspaceName(item.agent_id),
        ].filter(Boolean)
        return names.includes(workspaceName)
      })
      return agent ? agent.agent_id : ''
    },
    async handleOpenWorkspace(scope = 'workspace') {
      if (!this.currentConversation) return
      const nextScope = typeof scope === 'string' ? scope : 'workspace'
      this.workspaceVisible = true
      this.fileTreeData = []
      await this.switchFileScope(nextScope)
    },
    async switchFileScope(scope) {
      scope = typeof scope === 'string' ? scope : 'workspace'
      let root = '/workspace'
      if (scope === 'shared') {
        root = '/workspace/shared'
      } else if (scope && scope.startsWith('agent:')) {
        const agentId = scope.slice('agent:'.length)
        const agent = this.currentSessionAgents.find(item => item.agent_id === agentId)
        root = `/workspace/agents/${(agent && agent.workspace_name) || this.safeWorkspaceName((agent && agent.role) || agentId)}`
      }
      this.fileScope = scope || 'workspace'
      this.selectedFilePath = ''
      this.previewContent = ''
      this.previewType = 'text'
      this.previewUrl = ''
      this.previewAgentId = scope && scope.startsWith('agent:') ? scope.slice('agent:'.length) : ''
      await this.loadFileTree(root)
    },
    async loadFileTree(root = '/workspace') {
      if (!this.currentSessionId) return
      this.previewLoading = true
      this.error = ''
      try {
        const response = await getFileTree(this.currentSessionId, root)
        this.fileTreeData = response.code === 200 && response.data && response.data.tree
          ? [response.data.tree]
          : []
        this.fileTreeRoot = root
      } catch (error) {
        this.handleRequestError(error, '加载容器文件夹失败')
      } finally {
        this.previewLoading = false
      }
    },
    handleFileNodeClick(node) {
      if (!node) return
      if (node.type === 'directory') {
        this.selectedFilePath = ''
        this.previewContent = ''
        this.previewType = 'text'
        this.previewUrl = ''
        this.loadFileTree(node.path)
        return
      }
      this.previewFile(node.path)
    },
    async previewFile(filePath) {
      if (!filePath || !this.currentSessionId) return
      this.workspaceVisible = true
      this.selectedFilePath = filePath
      this.previewLoading = true
      this.previewContent = ''
      this.previewType = 'text'
      this.previewUrl = ''
      try {
        const agentId = this.previewAgentId || (this.currentSessionAgents[0] && this.currentSessionAgents[0].agent_id) || ''
        if (this.isHtmlFile(filePath)) {
          this.previewType = 'html'
          this.previewUrl = await getWorkspaceFileUrl(this.currentSessionId, filePath)
          return
        }
        if (this.isImageFile(filePath)) {
          this.previewType = 'image'
          this.previewUrl = agentId
            ? await getAgentFileUrl(this.currentSessionId, agentId, filePath)
            : await getWorkspaceFileUrl(this.currentSessionId, filePath)
          return
        }
        if (this.isPdfFile(filePath)) {
          this.previewType = 'pdf'
          this.previewUrl = agentId
            ? await getAgentFileUrl(this.currentSessionId, agentId, filePath)
            : await getWorkspaceFileUrl(this.currentSessionId, filePath)
          return
        }
        const response = await readAgentFile(this.currentSessionId, agentId, filePath)
        this.previewContent = response.code === 200 && response.data && response.data.content !== undefined
          ? response.data.content
          : '无法读取文件'
      } catch (error) {
        this.previewContent = (error && error.message) || '加载失败'
      } finally {
        this.previewLoading = false
      }
    },
    isHtmlFile(path) {
      return /\.html?$/i.test(String(path || ''))
    },
    isImageFile(path) {
      return /\.(png|jpe?g|gif|webp|svg)$/i.test(String(path || ''))
    },
    isPdfFile(path) {
      return /\.pdf$/i.test(String(path || ''))
    },
    getFileIcon(path) {
      const value = String(path || '').toLowerCase()
      if (/\.(png|jpe?g|gif|webp|svg)$/.test(value)) return 'el-icon-picture-outline'
      if (/\.(js|vue|ts|css|html|py|json|md|txt|csv|yaml|yml)$/.test(value)) return 'el-icon-document'
      return 'el-icon-document'
    },
    async openWorkspaceFile(filePath) {
      if (!this.currentSessionId || !filePath) return
      const agentId = this.previewAgentId || (this.currentSessionAgents[0] && this.currentSessionAgents[0].agent_id) || ''
      const url = this.isHtmlFile(filePath)
        ? await getWorkspaceFileUrl(this.currentSessionId, filePath)
        : agentId
        ? await getAgentFileUrl(this.currentSessionId, agentId, filePath)
        : await getWorkspaceFileUrl(this.currentSessionId, filePath)
      window.open(url, '_blank')
    },
    async copyFilePath(path) {
      if (navigator.clipboard && path) await navigator.clipboard.writeText(path)
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
        } catch (error) {
          return String(value)
        }
      }
      return String(value || '')
    },
    elementKey(element) {
      if (!element || typeof element !== 'object') return ''
      const data = this.elementData(element)
      const detail = element.detail && typeof element.detail === 'object' && !Array.isArray(element.detail) ? element.detail : {}
      const title = data.title || detail.title || element.title || ''
      const content = element.content || data.content || detail.content || ''
      const stable = data.url || data.path || data.name || data.filename || detail.path || element.step_id || data.progress_key || detail.progress_key
      return stable || [element.type || '', element.status || '', title, String(content).slice(0, 240)].join('|')
    },
    mergeElements(existing = [], incoming = []) {
      const merged = []
      ;(Array.isArray(existing) ? existing : []).forEach(element => {
        const key = this.elementKey(element)
        if (!key || !merged.some(item => this.elementKey(item) === key)) merged.push(element)
      })
      ;(Array.isArray(incoming) ? incoming : []).forEach(element => {
        const key = this.elementKey(element)
        const progressKey = element && (element.data?.progress_key || element.detail?.progress_key || element.step_id)
        const replaceIndex = progressKey
          ? merged.findIndex(item => (item.data?.progress_key || item.detail?.progress_key || item.step_id) === progressKey)
          : -1
        if (replaceIndex >= 0) {
          this.$set(merged, replaceIndex, element)
        } else if (!key || !merged.some(item => this.elementKey(item) === key)) {
          merged.push(element)
        }
      })
      return merged
    },
    mergeMessage(oldMessage = {}, incoming = {}) {
      const replaceElements = Boolean(incoming.replace_elements)
      const clearRawOutput = Boolean(incoming.clear_raw_output)
      const cleanIncoming = { ...incoming }
      delete cleanIncoming.replace_elements
      delete cleanIncoming.clear_raw_output
      if (clearRawOutput) cleanIncoming.raw_output = ''
      const next = { ...oldMessage, ...cleanIncoming }
      if (!cleanIncoming.raw_output && oldMessage.raw_output && !replaceElements && !clearRawOutput) next.raw_output = oldMessage.raw_output
      if (Array.isArray(oldMessage.elements) && oldMessage.elements.length && !replaceElements) {
        next.elements = Array.isArray(cleanIncoming.elements) && cleanIncoming.elements.length
          ? this.mergeElements(oldMessage.elements, cleanIncoming.elements)
          : oldMessage.elements
      }
      if (oldMessage.meta || cleanIncoming.meta) {
        next.meta = { ...(oldMessage.meta || {}), ...(cleanIncoming.meta || {}) }
      }
      return next
    },
    addMessageEvent(conversationId, messageId, event, events) {
      const list = this.messagesByConversation[conversationId] || []
      const next = list.map(item => {
        if (item.id !== messageId) return item
        const meta = { ...(item.meta || {}) }
        if (Array.isArray(events)) {
          meta.events = events
        } else if (event) {
          const current = Array.isArray(meta.events) ? meta.events.slice() : []
          current.push(event)
          meta.events = current
        }
        return { ...item, meta }
      })
      this.$set(this.messagesByConversation, conversationId, next)
    },
    registerSocketHandlers() {
      this.unregisterSocketHandlers()
      const upsertMessage = message => {
        if (!message || !message.conversation_id) return
        const list = this.messagesByConversation[message.conversation_id] || []
        const index = list.findIndex(item => item.id === message.id)
        const next = this.sortMessages(index >= 0
          ? list.map(item => (item.id === message.id ? this.mergeMessage(item, message) : item))
          : [...list, message])
        this.$set(this.messagesByConversation, message.conversation_id, next)
        if (message.conversation_id === this.currentId) this.$nextTick(this.scrollToBottom)
        this.loadConversations()
      }
      const patchMessage = event => {
        if (!event || !event.conversation_id || !event.message_id) return
        const list = this.messagesByConversation[event.conversation_id] || []
        const next = list.map(item => {
          if (item.id !== event.message_id) return item
          return this.mergeMessage(item, {
            content: event.content == null ? item.content : event.content,
            elements: event.elements,
            raw_output: event.raw_output,
            status: event.status == null ? item.status : event.status,
            sender_name: event.sender_name == null ? item.sender_name : event.sender_name,
            meta: event.events ? { events: event.events } : undefined,
            replace_elements: event.replace_elements,
            clear_raw_output: event.clear_raw_output,
          })
        })
        this.$set(this.messagesByConversation, event.conversation_id, next)
        if (event.conversation_id === this.currentId) this.$nextTick(this.scrollToBottom)
      }
      const appendElement = event => {
        if (!event || !event.conversation_id || !event.message_id || !event.element) return
        const list = this.messagesByConversation[event.conversation_id] || []
        const next = list.map(item => {
          if (item.id !== event.message_id) return item
          return this.mergeMessage(item, {
            content: event.content,
            raw_output: event.raw_output,
            status: event.status,
            sender_name: event.sender_name,
            elements: this.mergeElements(item.elements || [], [event.element]),
          })
        })
        this.$set(this.messagesByConversation, event.conversation_id, next)
        this.addMessageEvent(event.conversation_id, event.message_id, null, event.events)
        if (event.conversation_id === this.currentId) this.$nextTick(this.scrollToBottom)
      }
      const addStep = event => {
        if (!event || !event.conversation_id || !event.message_id) return
        this.addMessageEvent(event.conversation_id, event.message_id, event.event, event.events)
      }
      this.socketHandlers = [
        ['new_message', upsertMessage],
        ['conversation_message_created', upsertMessage],
        ['conversation_message_delta', patchMessage],
        ['conversation_message_element_stream', appendElement],
        ['conversation_message_step', addStep],
        ['conversation_message_status', patchMessage],
      ]
      this.socketHandlers.forEach(([event, handler]) => socketClient.on(event, handler))
    },
    unregisterSocketHandlers() {
      this.socketHandlers.forEach(([event, handler]) => socketClient.off(event, handler))
      this.socketHandlers = []
    },
    formatTime(value) {
      if (!value) return ''
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return ''
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    },
    scrollToBottom() {
      const el = this.$refs.messagesContainer
      if (el) el.scrollTop = el.scrollHeight
    },
    handleRequestError(error, fallback) {
      this.error = (error && error.response && error.response.data && error.response.data.message) || (error && error.message) || fallback
      if (error && error.response && error.response.status === 401) {
        clearAuth()
        this.$router.replace('/login')
      }
    },
    logout() {
      clearAuth()
      this.$router.replace('/login')
    },
  },
}
</script>
