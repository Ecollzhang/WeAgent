<template>
  <div class="dashboard">
    <!-- 第一栏：全局侧边导航栏 -->
    <AppSidebar />

    <!-- 无工作空间时的空状态引导 -->
    <div class="workspace-empty" v-if="!hasWorkspace">
      <div class="empty-card">
        <div class="empty-icon">
          <i class="el-icon-s-data"></i>
        </div>
        <h3>欢迎使用 WeAgent</h3>
        <p>请先创建一个工作空间，然后开始协作</p>
        <div class="empty-domains">
          <div
            v-for="d in [
              { key: 'rd', name: '智能研发', desc: '编码、测试、数据分析', icon: 'el-icon-monitor' },
              { key: 'edu', name: '智慧教育', desc: '课程设计、习题生成、学情分析', icon: 'el-icon-reading' },
              { key: 'office', name: '智慧办公', desc: '公文撰写、会议纪要、报表分析', icon: 'el-icon-s-home' },
            ]"
            :key="d.key"
            class="domain-card"
            @click="quickCreateWorkspace(d.key)"
          >
            <i :class="d.icon"></i>
            <div class="domain-info">
              <strong>{{ d.name }}</strong>
              <span>{{ d.desc }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 有工作空间时显示正常布局 -->
    <template v-else>

    <!-- 第二栏：会话列表栏 -->
    <div class="conversation-panel">
      <ConversationList
        :conversations="conversations"
        :currentId="currentConversation?.id"
        :loading="convLoading"
        :userAvatar="userAvatar"
        @select="handleSelectConversation"
        @create-conversation="openCreateConversation"
      />
    </div>

    <!-- 第三栏：主聊天内容区 -->
    <div class="chat-panel">
      <EducationChatContext
        v-if="educationContext || educationContextLoading"
        :context="educationContext"
        :loading="educationContextLoading"
      />
      <ChatWindow
        :key="currentConversation?.id || 'empty-chat'"
        :conversation="currentConversation"
        :messages="currentMessages"
        :userId="userId"
        :agentResponding="isAgentResponding"
        :sessionAgents="currentSessionAgents"
        :allAgents="agents"
        @send-message="handleSendMessage"
        @pin-message="handlePinMessage"
        @delete-conversation="handleDeleteConversation"
        @search-messages="handleSearchMessages"
        @open-attachment="handleOpenAttachment"
        @toggle-star="handleToggleStar"
        @open-history="handleOpenHistory"
        @stop-agent="handleStopAgent"
        @open-workspace="handleOpenWorkspace"
        @open-file="handleOpenFile"
        @open-attachments="handleOpenAttachments"
        @open-services="handleOpenServices"
        @open-migration="handleOpenMigration"
      />
    </div>

    <ArtifactWorkbench
      :visible.sync="artifactWorkbenchVisible"
      :artifact="currentWorkbenchArtifact"
      :session-id="currentSessionId"
    />

    <FileMigrationDialog
      :visible.sync="migrationDialogVisible"
      :source-conversation="currentConversation"
      :conversations="conversations"
      @refresh-conversations="$store.dispatch('conversation/fetchConversations', activeWorkspaceId)"
      @open-target="handleOpenMigrationTarget"
    />

    <el-dialog
      :title="previewTitle"
      :visible.sync="previewVisible"
      width="78%"
      top="5vh"
      custom-class="file-preview-dialog"
    >
      <div v-loading="previewLoading" class="file-browser-body">
        <div class="file-tree-panel">
          <div class="file-scope-tabs">
            <el-button size="mini" :type="fileScope === 'workspace' ? 'primary' : 'text'" @click="switchFileScope('workspace')">全部</el-button>
            <el-button size="mini" :type="fileScope === 'shared' ? 'primary' : 'text'" @click="switchFileScope('shared')">公共</el-button>
            <el-dropdown trigger="click" @command="switchFileScope">
              <el-button size="mini" :type="fileScope.startsWith('agent:') ? 'primary' : 'text'">
                Agent<i class="el-icon-arrow-down el-icon--right" />
              </el-button>
              <el-dropdown-menu slot="dropdown">
                <el-dropdown-item
                  v-for="ag in currentSessionAgents"
                  :key="ag.agent_id"
                  :command="`agent:${ag.agent_id}`"
                >
                  {{ ag.role || ag.name || ag.agent_id }}
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
            @node-click="handleFileNodeClick"
          >
            <span slot-scope="{ node, data }" class="file-tree-node">
              <i :class="data.type === 'directory' ? 'el-icon-folder' : getFileIcon(data.path)" />
              <span>{{ node.label }}</span>
              <span v-if="data.size" class="tree-file-size">{{ formatFileSize(data.size) }}</span>
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

    <el-drawer
      title="上传文件"
      :visible.sync="attachmentsVisible"
      direction="rtl"
      size="360px"
      custom-class="attachments-drawer"
    >
      <div class="attachments-body">
        <el-upload
          drag
          action=""
          :auto-upload="false"
          :show-file-list="false"
          :on-change="handleAttachmentPicked"
          class="attachment-upload"
        >
          <i class="el-icon-upload"></i>
          <div class="el-upload__text">拖拽文件到这里，或点击选择</div>
          <div class="el-upload__tip" slot="tip">支持图片、PDF、代码、文本等文件</div>
        </el-upload>

        <div class="attachment-list-header">
          <span>已上传</span>
          <el-button size="mini" type="text" @click="loadAttachments">刷新</el-button>
        </div>

        <div v-loading="attachmentsLoading" class="attachment-list">
          <div v-if="attachments.length === 0" class="attachment-empty">暂无上传文件</div>
          <div v-for="file in attachments" :key="file.path" class="attachment-item">
            <i :class="getFileIcon(file.path)"></i>
            <div class="attachment-info">
              <button class="attachment-name" @click="handleOpenFile(file)">{{ file.name }}</button>
              <span>{{ formatFileSize(file.size) }}</span>
            </div>
            <el-button size="mini" type="text" icon="el-icon-delete" @click="handleDeleteAttachment(file)"></el-button>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- 新建会话对话框 -->
    <el-drawer
      title="预览服务"
      :visible.sync="servicesVisible"
      direction="rtl"
      size="420px"
      custom-class="services-drawer"
    >
      <div class="services-body">
        <el-form label-position="top" size="small">
          <el-form-item label="Agent">
            <el-select v-model="serviceForm.agent_id" placeholder="选择 Agent" style="width: 100%" @change="syncServiceCwd">
              <el-option
                v-for="ag in currentSessionAgents"
                :key="ag.agent_id"
                :label="ag.name || ag.role || ag.agent_id"
                :value="ag.agent_id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="端口">
            <el-select v-model="serviceForm.port" style="width: 100%" @change="syncServiceCommand">
              <el-option label="Vite / Vue3: 5173" :value="5173" />
              <el-option label="Vue CLI: 8081" :value="8081" />
              <el-option label="React / Node: 3000" :value="3000" />
              <el-option label="静态文件: 8000" :value="8000" />
              <el-option label="其他: 9000" :value="9000" />
            </el-select>
          </el-form-item>
          <el-form-item label="工作目录">
            <el-input v-model="serviceForm.cwd" />
          </el-form-item>
          <el-form-item label="启动命令">
            <el-input v-model="serviceForm.command" type="textarea" :rows="3" />
          </el-form-item>
          <el-button type="primary" size="small" :loading="serviceStarting" @click="handleStartService">
            启动服务
          </el-button>
          <el-button size="small" @click="loadServices">刷新</el-button>
        </el-form>

        <div class="service-tip">
          Vue/Vite 服务必须监听 0.0.0.0，否则只能在容器内访问。
        </div>

        <div class="service-list" v-loading="servicesLoading">
          <div v-if="services.length === 0" class="service-empty">暂无服务</div>
          <div v-for="svc in services" :key="svc.id || svc.service_id || svc.port" class="service-item">
            <div class="service-main">
              <div class="service-title">
                <span>{{ svc.name || svc.id || '预览服务' }}</span>
                <el-tag size="mini" :type="serviceStatusType(svc.status)">
                  {{ serviceStatusLabel(svc.status) }}
                </el-tag>
              </div>
              <div class="service-submeta">
                <span v-if="svc.port">端口 {{ svc.port }}</span>
                <span v-if="svc.type">{{ svc.type }}</span>
                <span v-if="svc.preview_token_expires_at">Token {{ formatServiceExpiry(svc.preview_token_expires_at) }}</span>
              </div>
              <a v-if="serviceUrl(svc)" :href="serviceUrl(svc)" target="_blank" rel="noopener" class="service-url">
                {{ serviceUrl(svc) }}
              </a>
              <div v-if="svc.command" class="service-command">{{ svc.command }}</div>
            </div>
            <div class="service-actions">
              <el-button v-if="serviceUrl(svc)" size="mini" type="text" @click="openServiceUrl(svc)">打开</el-button>
              <el-button v-if="serviceUrl(svc)" size="mini" type="text" @click="copyServiceUrl(serviceUrl(svc))">复制</el-button>
              <el-button size="mini" type="text" @click="showServiceLogs(svc)">日志</el-button>
              <el-button size="mini" type="text" @click="handleRestartService(svc)">重启</el-button>
              <el-button size="mini" type="text" class="service-stop-btn" @click="handleStopService(svc)">停止</el-button>
            </div>
          </div>
        </div>
      </div>
    </el-drawer>

    <el-dialog
      title="服务日志"
      :visible.sync="serviceLogsVisible"
      width="760px"
      top="8vh"
      custom-class="service-logs-dialog"
    >
      <div class="service-logs-body" v-loading="serviceLogsLoading">
        <div class="service-logs-meta" v-if="serviceLogsData">
          <el-tag size="mini">{{ serviceLogsData.service_id }}</el-tag>
          <el-tag size="mini" :type="serviceStatusType(serviceLogsData.status)">{{ serviceStatusLabel(serviceLogsData.status) }}</el-tag>
        </div>
        <div class="service-log-section">
          <div class="service-log-title">stdout</div>
          <pre>{{ serviceLogsData?.stdout_tail || '暂无输出' }}</pre>
        </div>
        <div class="service-log-section">
          <div class="service-log-title">stderr</div>
          <pre>{{ serviceLogsData?.stderr_tail || '暂无错误输出' }}</pre>
        </div>
      </div>
    </el-dialog>

    <el-dialog title="新建会话" :visible.sync="showCreateDialog" width="680px" custom-class="create-conv-dialog" top="6vh">
      <div class="create-conv-body">
        <div class="conv-field">
          <label class="field-label">会话标题</label>
          <el-input
            v-model="newConversation.title"
            placeholder="自动生成标题"
            size="medium"
          >
            <i slot="prefix" class="el-icon-edit-outline"></i>
          </el-input>
        </div>

        <div v-if="isEducationWorkspace" class="education-conversation-scope">
          <div class="scope-heading">
            <span class="scope-icon"><i class="el-icon-reading"></i></span>
            <div>
              <strong>关联教学课程</strong>
              <small>课程身份和 Agent 权限由系统自动确认</small>
            </div>
          </div>
          <div class="scope-grid">
            <div class="conv-field">
              <label class="field-label">课程 <span class="field-required">必选</span></label>
              <el-select
                v-model="newConversation.courseId"
                placeholder="选择一门课程"
                style="width: 100%"
                :loading="educationCoursesLoading"
                @change="loadEducationOptions"
              >
                <el-option
                  v-for="course in educationCourses"
                  :key="course.id"
                  :label="course.title"
                  :value="course.id"
                />
              </el-select>
            </div>
            <div class="conv-field">
              <label class="field-label">当前身份</label>
              <div class="membership-role" :class="educationOptions.membership_role || 'pending'">
                <i :class="educationOptions.membership_role === 'teacher' ? 'el-icon-s-custom' : 'el-icon-user'"></i>
                {{ educationRoleLabel }}
                <small>来自课程成员关系，不可手动切换</small>
              </div>
            </div>
          </div>
          <div class="scope-grid">
            <div class="conv-field">
              <label class="field-label">课时 <span class="field-hint">（可选）</span></label>
              <el-select
                v-model="newConversation.lessonId"
                placeholder="整门课程，或选择具体课时"
                clearable
                style="width: 100%"
                :disabled="!newConversation.courseId"
              >
                <el-option
                  v-for="lesson in educationOptions.lessons || []"
                  :key="lesson.id"
                  :label="lesson.title"
                  :value="lesson.id"
                />
              </el-select>
            </div>
            <div class="conv-field">
              <label class="field-label">资料范围</label>
              <el-select v-model="newConversation.materialPolicy" style="width: 100%">
                <el-option
                  v-for="policy in educationOptions.material_policies || []"
                  :key="policy.value"
                  :label="policy.label"
                  :value="policy.value"
                />
              </el-select>
            </div>
          </div>
          <div v-if="educationCapabilitySummary.length" class="capability-summary">
            <span>本次 Agent 能力</span>
            <el-tag v-for="item in educationCapabilitySummary" :key="item" size="mini">{{ item }}</el-tag>
          </div>
        </div>

        <div class="conv-field">
          <label class="field-label">选择 Agent <span class="field-hint">（点击复选框选择，支持多选）</span></label>
          <div class="agent-tree-wrapper" v-loading="treeLoading">
            <el-tree
              ref="agentTree"
              :data="agentTreeData"
              :props="treeProps"
              show-checkbox
              node-key="id"
              default-expand-all
              highlight-current
              @check-change="handleTreeCheckChange"
              class="agent-tree"
            >
              <span class="tree-node" slot-scope="{ node, data }">
                <span v-if="data.isLeaf" class="node-agent">
                  <span class="node-avatar" :style="{ background: data.agentColor || '#4080ff' }">
                    <img v-if="data.agentAvatar" :src="data.agentAvatar" class="node-avatar-img" />
                    <span v-else class="node-avatar-letter">{{ data.label?.charAt(0) || '?' }}</span>
                  </span>
                  <span class="node-name">{{ data.label }}</span>
                  <span class="node-badge">{{ data.adapterLabel }}</span>
                </span>
                <span v-else class="node-category">
                  <i :class="data.icon || 'el-icon-folder-opened'"></i>
                  <span>{{ data.label }}</span>
                  <span class="node-count">{{ data.children?.length || 0 }}个Agent</span>
                </span>
              </span>
            </el-tree>
          </div>
        </div>

        <!-- 领域服务选择 -->
        <div v-if="!isEducationWorkspace && chatServicesVisible" class="conv-field">
          <label class="field-label">选择领域服务 <span class="field-hint">（多选，Agent将能调用对应服务的API）</span></label>
          <div class="service-checkboxes">
            <label class="service-checkbox" :class="{ checked: newConversation.services.includes('rd') }">
              <input type="checkbox" value="rd" v-model="newConversation.services" />
              <span class="svc-icon"><i class="el-icon-monitor"></i></span>
              <span class="svc-info">
                <strong>智能研发</strong>
                <em>RD</em>
              </span>
            </label>
            <label class="service-checkbox" :class="{ checked: newConversation.services.includes('rag') }">
              <input type="checkbox" value="rag" v-model="newConversation.services" />
              <span class="svc-icon rag"><i class="el-icon-collection"></i></span>
              <span class="svc-info">
                <strong>知识库</strong>
                <em>RAG</em>
              </span>
            </label>
            <label class="service-checkbox disabled">
              <input type="checkbox" disabled />
              <span class="svc-icon office"><i class="el-icon-s-home"></i></span>
              <span class="svc-info">
                <strong>智慧办公</strong>
                <em>OFFICE · 待上线</em>
              </span>
            </label>
          </div>
        </div>

        <!-- RD 项目选择（选 RD 时展示） -->
        <div class="conv-field" v-if="showProjectSelector">
          <label class="field-label">关联项目 <span class="field-hint">（可选，不选=全局视角）</span></label>
          <el-select
            v-model="newConversation.projectId"
            placeholder="选择项目或留空"
            clearable
            style="width: 100%"
            :loading="projectsLoading"
            size="medium"
          >
            <el-option
              v-for="p in projectList"
              :key="p.id"
              :label="p.name"
              :value="p.id"
            >
              <span>{{ p.name }}</span>
              <span style="float:right;color:#94a3b8;font-size:12px">{{ p.tech_stack?.frontend || p.tech_stack?.backend || '' }}</span>
            </el-option>
          </el-select>
        </div>

        <!-- RAG 知识库配置（选 RAG 时展示） -->
        <div class="conv-field" v-if="showKbConfig">
          <label class="field-label">知识库领域</label>
          <el-select v-model="newConversation.kbDomain" placeholder="选择知识库领域或留空" clearable style="width: 100%" size="medium">
            <el-option label="继承工作空间" value="" />
            <el-option label="全部领域" value="all" />
            <el-option label="智能研发 (RD)" value="rd" />
            <el-option label="智慧教育 (EDU)" value="edu" />
            <el-option label="智慧办公 (OFFICE)" value="office" />
          </el-select>
        </div>

        <div class="conv-preview" v-if="selectedAgentList.length > 0">
          <div class="preview-avatars">
            <!-- 用户头像 -->
            <div class="preview-avatar user-avatar-mini" :title="currentUser?.username || '用户'">
              <img v-if="userAvatar" :src="userAvatar" class="avatar-img" />
              <i v-else class="el-icon-user-solid"></i>
            </div>
            <span class="preview-plus" v-if="selectedAgentList.length > 0">+</span>
            <!-- Agent头像 -->
            <div
              v-for="agent in selectedAgentList"
              :key="agent.id"
              class="preview-avatar"
              :style="{ background: agent.color || '#4080ff' }"
              :title="agent.name"
            >
              <img v-if="agent.avatar" :src="agent.avatar" class="avatar-img" />
              <span v-else class="avatar-letter">{{ agent.name?.charAt(0) || '?' }}</span>
            </div>
          </div>
          <div class="preview-type">
            <el-tag size="mini" :type="selectedAgentList.length > 1 ? 'success' : 'primary'">
              {{ selectedAgentList.length > 1 ? '群聊' : '单聊' }}
            </el-tag>
          </div>
        </div>

        <!-- 上下文预览 -->
        <div class="conv-context-preview" v-if="newConversation.services.length > 0 || newConversation.projectId || newConversation.kbDomain">
          <div class="context-chips">
            <span v-if="newConversation.services.includes('rd')" class="context-chip rd">
              <i class="el-icon-monitor"></i> 智能研发
            </span>
            <span v-if="newConversation.projectId" class="context-chip project">
              <i class="el-icon-folder-opened"></i> {{ projectList.find(p => p.id === newConversation.projectId)?.name || '项目' }}
            </span>
            <span v-if="newConversation.services.includes('rag')" class="context-chip rag">
              <i class="el-icon-collection"></i> 知识库{{ newConversation.kbDomain ? ' · ' + kbDomainLabel(newConversation.kbDomain) : '' }}
            </span>
          </div>
        </div>
      </div>
      <span slot="footer" class="dialog-footer">
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreateConversation" :loading="creating" class="create-btn">
          创建会话
        </el-button>
      </span>
    </el-dialog>
    </template>
  </div>
</template>

<script>
import AppSidebar from '../components/Sidebar/index.vue'
import ArtifactWorkbench from '../components/ArtifactWorkbench/index.vue'
import ConversationList from '../components/ConversationList/index.vue'
import ChatWindow from '../components/ChatWindow/index.vue'
import FileMigrationDialog from '../components/FileMigrationDialog/index.vue'
import EducationChatContext from '../components/education/EducationChatContext.vue'
import { checkVisible } from '../store/modules/grayscale'
import { getCategories, getAgents } from '../api/agent'
import {
  bootstrapEducationConversation,
  getCourses,
  getEducationConversationContext,
  getEducationConversationOptions,
} from '../api/education'
import { sendMessage as apiSendMessage } from '../api/message'
import {
  getConversation,
  stopConversationAgent,
  getConversationAttachments,
  uploadConversationAttachment,
  deleteConversationAttachment,
} from '../api/conversation'
import {
  getFileTree,
  readAgentFile,
  getSessionRawFileUrl,
  getWorkspaceFileUrl,
  getSessionDownloadUrl,
  listServices,
  startService,
  stopService,
  restartService,
  getServiceLogs,
} from '../api/sandbox'
import socketClient from '../utils/socket'

// ---------- localStorage helpers ----------
function loadAgentMeta() {
  try { return JSON.parse(localStorage.getItem('agent_meta') || '{}') } catch (e) { return {} }
}
function getAgentMeta(agentId) {
  const meta = loadAgentMeta()
  return meta[agentId] || {}
}

export default {
  name: 'Dashboard',
  components: {
    AppSidebar,
    ArtifactWorkbench,
    ConversationList,
    ChatWindow,
    FileMigrationDialog,
    EducationChatContext,
  },
  data() {
    return {
      showCreateDialog: false,
      creating: false,
      treeLoading: false,
      agentTreeData: [],
      treeProps: { children: 'children', label: 'label' },
      newConversation: {
        title: '',
        type: 'single',
        selectedAgents: [],
        services: [],        // ['rd', 'rag']
        courseId: '',
        lessonId: '',
        materialPolicy: 'course_only',
        projectId: '',       // RD项目ID（可选）
        kbDomain: '',        // RAG知识库域
        kbDocumentIds: [],   // RAG限定文档
      },
      educationCourses: [],
      educationCoursesLoading: false,
      educationOptions: {
        membership_role: '',
        lessons: [],
        agents: [],
        material_policies: [],
      },
      projectList: [],
      projectsLoading: false,
      socketHandlers: [],
      isAgentResponding: false,
      previewVisible: false,
      previewTitle: '',
      previewContent: '',
      previewLoading: false,
      previewType: 'text',
      previewUrl: '',
      selectedFilePath: '',
      artifactWorkbenchVisible: false,
      currentWorkbenchArtifact: null,
      migrationDialogVisible: false,
      fileTreeData: [],
      fileTreeRoot: '/workspace',
      fileScope: 'workspace',
      fileTreeProps: { children: 'children', label: 'name' },
      attachmentsVisible: false,
      attachments: [],
      attachmentsLoading: false,
      servicesVisible: false,
      servicesLoading: false,
      serviceStarting: false,
      services: [],
      serviceLogsVisible: false,
      serviceLogsLoading: false,
      serviceLogsData: null,
      educationContext: null,
      educationContextLoading: false,
      educationContextRequestId: 0,
      serviceForm: {
        agent_id: '',
        port: 5173,
        cwd: '',
        command: 'npm run dev -- --host 0.0.0.0 --port 5173',
      },
      messageRefreshTimer: null,
    }
  },
  computed: {
    currentUser() {
      return this.$store.state.user.user
    },
    userId() {
      return this.$store.getters['user/userId']
    },
    conversations() {
      return this.$store.state.conversation.conversations
    },
    currentConversation() {
      return this.$store.state.conversation.currentConversation
    },
    convLoading() {
      return this.$store.state.conversation.loading
    },
    currentMessages() {
      const convId = this.currentConversation?.id
      if (!convId) return []
      return this.$store.getters['message/getMessagesByConversation'](convId)
    },
    agents() {
      return this.$store.state.agent.agents
    },
    allAvailableAgents() {
      // API agents already include user copies of public presets
      return this.agents.map(a => ({
        ...a,
        avatar: a.avatar_url || a.avatar || '',
        color: a.avatar_color || getAgentMeta(a.id).color || '#4080ff',
      }))
    },
    userAvatar() {
      return this.currentUser?.avatar || localStorage.getItem('user_avatar') || ''
    },
    activeWorkspaceId() {
      return this.$store.getters['workspace/activeWorkspaceId']
    },
    activeDomain() {
      return this.$store.getters['workspace/activeDomain']
    },
    isEducationWorkspace() {
      return this.activeDomain === 'edu'
    },
    educationRoleLabel() {
      const labels = { teacher: '教师', student: '学生' }
      return labels[this.educationOptions.membership_role] || '选择课程后自动确认'
    },
    educationCapabilitySummary() {
      const selected = new Set(this.newConversation.selectedAgents || [])
      const labels = []
      for (const agent of this.educationOptions.agents || []) {
        if (!selected.has(agent.id)) continue
        for (const label of agent.capability_summary || []) {
          if (label && !labels.includes(label)) labels.push(label)
        }
      }
      return labels
    },
    hasWorkspace() {
      return this.$store.getters['workspace/workspacesByDomain'](this.activeDomain).length > 0
    },
    chatServicesVisible() {
      return checkVisible(this.$store.state.grayscale, this.activeDomain, 'ui.chat.services')
    },
    educationManualCreateVisible() {
      return checkVisible(
        this.$store.state.grayscale,
        'edu',
        'feature.education.chat.manual_create'
      )
    },
    showProjectSelector() {
      return this.newConversation.services.includes('rd')
    },
    showKbConfig() {
      return this.newConversation.services.includes('rag')
    },
    selectedAgentList() {
      return this.newConversation.selectedAgents
        .map(id => this.findAgentWithMeta(id))
        .filter(Boolean)
    },
    currentSessionId() {
      return this.currentConversation?.sandbox_session_id || this.currentConversation?.id || ''
    },
    currentSessionAgents() {
      const participants = this.currentConversation?.participants_info || []
      return participants
        .filter(p => p.participant_type === 'agent')
        .map(p => ({
          agent_id: p.participant_id,
          role: p.name,
          name: p.name,
          workspace_name: this.safeWorkspaceName(p.name || p.participant_id),
          avatar: p.avatar,
          color: p.color,
        }))
    },
  },
  async created() {
    socketClient.connect()
    this.registerSocketHandlers()

    // 初始化工作空间和灰度配置
    await this.$store.dispatch('workspace/fetchWorkspaces')
    const workspaces = this.$store.state.workspace.workspaces
    if (workspaces.length > 0) {
      const requestedDomain = String(this.$route.query.domain || '')
      const requestedWorkspace = requestedDomain
        ? workspaces.find(item => item.domain === requestedDomain)
        : null
      const active = this.$store.getters['workspace/activeWorkspace']
      if (requestedWorkspace) {
        this.$store.dispatch('workspace/selectWorkspace', requestedWorkspace)
      } else if (!active || !active.id) {
        this.$store.dispatch('workspace/selectWorkspace', workspaces[0])
      }
      const domain = this.$store.getters['workspace/activeDomain']
      await this.$store.dispatch('grayscale/loadDomainConfig', domain)
    }

    const wsId = this.$store.getters['workspace/activeWorkspaceId']
    await Promise.all([
      this.$store.dispatch('conversation/fetchConversations', wsId),
      this.$store.dispatch('agent/fetchAgents'),
    ])
    await this.selectConversationFromRoute()
    if (!this.currentConversation) {
      this.restoreConversationSelection(wsId)
    }
    this.handleProjectFromRoute()
  },
    beforeDestroy() {
      if (this.currentConversation?.id) {
        socketClient.leaveConversation(this.currentConversation.id)
      }
      this.stopMessageRefresh()
      this.unregisterSocketHandlers()
    },
  watch: {
    showCreateDialog(open) {
      if (open) {
        this.$nextTick(async () => {
          if (this.isEducationWorkspace) {
            await this.loadEducationCourses()
          } else {
            await this.buildAgentTree()
          }
        })
      } else {
        this.resetNewConversation()
      }
    },
    'newConversation.services'(val) {
      if (!val.includes('rd')) this.newConversation.projectId = ''
      if (!val.includes('rag')) {
        this.newConversation.kbDomain = ''
        this.newConversation.kbDocumentIds = []
      }
      if (val.includes('rd') && this.projectList.length === 0) {
        this.fetchProjects()
      }
    },
    'newConversation.selectedAgents': function(ids) {
      if (ids.length === 0) {
        this.newConversation.title = ''
        this.newConversation.type = 'single'
        return
      }
      // Auto-update title
      const userName = this.currentUser?.username || '用户'
      const agentNames = ids.map(id => {
        const agent = this.findAgentWithMeta(id)
        return agent?.name || id
      })
      this.newConversation.title = [userName, ...agentNames].join('、')
      // Update type
      this.newConversation.type = ids.length > 1 ? 'group' : 'single'
    },
    '$route.query.conversation_id'() {
      void this.selectConversationFromRoute()
    },
    '$route.query.project_id'(newVal) {
      if (newVal) this.handleProjectFromRoute()
    },
    activeWorkspaceId(newId, oldId) {
      if (newId && newId !== oldId) {
        this.$store.commit('conversation/SET_CURRENT_CONVERSATION', null)
        this.$store.dispatch('conversation/fetchConversations', newId)
          .then(() => this.restoreConversationSelection(newId))
      }
    },
  },
  methods: {
    openCreateConversation() {
      if (this.isEducationWorkspace && !this.educationManualCreateVisible) {
        this.$message.info('智慧教育新建会话当前处于灰度关闭状态')
        return
      }
      this.showCreateDialog = true
    },
    async selectConversationFromRoute() {
      const conversationId = this.$route.query.conversation_id
      if (!conversationId) return
      let conversation = this.conversations.find(item => item.id === conversationId)
      if (!conversation) {
        try {
          const response = await getConversation(conversationId)
          if (response?.code !== 200 || !response.data) return
          conversation = response.data
          this.$store.commit('conversation/ADD_CONVERSATION', conversation)
        } catch (error) {
          return
        }
      }
      if (!conversation) return
      if (
        conversation.workspace_id &&
        conversation.workspace_id !== this.activeWorkspaceId
      ) {
        const targetWorkspace = this.$store.state.workspace.workspaces.find(
          item => item.id === conversation.workspace_id
        )
        if (targetWorkspace) {
          await this.$store.dispatch('workspace/selectWorkspace', targetWorkspace)
          await this.$store.dispatch(
            'grayscale/loadDomainConfig',
            targetWorkspace.domain
          )
          await this.$store.dispatch(
            'conversation/fetchConversations',
            targetWorkspace.id
          )
        }
      }
      if (this.currentConversation?.id === conversationId) {
        this.loadEducationContext(conversationId)
        return
      }
      this.handleSelectConversation(conversation)
    },

    async handleProjectFromRoute() {
      const projectId = this.$route.query.project_id
      if (!projectId) return
      // Clear the query so it doesn't re-trigger on refresh
      if (this.$route.query.project_id) {
        const q = { ...this.$route.query }
        delete q.project_id
        this.$router.replace({ query: q }).catch(() => {})
      }
      // Pre-fetch projects so the name shows in preview
      await this.fetchProjects()
      if (!this.projectList.find(p => p.id === projectId)) {
        this.$message.warning('未找到该项目，请确认项目存在')
        return
      }
      // Pre-fill: RD service + project, domain from active workspace
      this.newConversation.services = ['rd']
      this.newConversation.projectId = projectId
      this.showCreateDialog = true
    },

    handleSelectConversation(conversation) {
      const oldId = this.currentConversation?.id
      if (oldId && oldId !== conversation.id) {
        socketClient.leaveConversation(oldId)
      }
      this.stopMessageRefresh()
      this.$store.commit('conversation/SET_CURRENT_CONVERSATION', conversation)
      this.rememberConversationSelection(conversation)
      this.isAgentResponding = false
      socketClient.joinConversation(conversation.id)
      this.$store.dispatch('message/fetchMessages', {
        conversationId: conversation.id,
      })
      this.loadEducationContext(conversation.id)
    },

    conversationSelectionKey(workspaceId) {
      return `weagent.web.lastConversation.${workspaceId || ''}`
    },

    rememberConversationSelection(conversation) {
      const workspaceId = conversation?.workspace_id || this.activeWorkspaceId
      if (!workspaceId || !conversation?.id) return
      try {
        window.localStorage.setItem(
          this.conversationSelectionKey(workspaceId),
          conversation.id
        )
      } catch (error) {
        // The current chat remains usable when browser storage is unavailable.
      }
    },

    restoreConversationSelection(workspaceId) {
      if (!workspaceId) return false
      let conversationId = ''
      try {
        conversationId = window.localStorage.getItem(
          this.conversationSelectionKey(workspaceId)
        ) || ''
      } catch (error) {
        return false
      }
      if (!conversationId) return false
      const conversation = this.conversations.find(item => (
        item.id === conversationId && item.workspace_id === workspaceId
      ))
      if (!conversation) {
        window.localStorage.removeItem(this.conversationSelectionKey(workspaceId))
        return false
      }
      if (this.currentConversation?.id !== conversation.id) {
        this.handleSelectConversation(conversation)
      }
      return true
    },

    async loadEducationContext(conversationId) {
      const requestId = ++this.educationContextRequestId
      this.educationContext = null
      this.educationContextLoading = true
      try {
        const response = await getEducationConversationContext(conversationId)
        if (requestId !== this.educationContextRequestId) return
        this.educationContext = response && response.data !== undefined
          ? response.data
          : response
      } catch (error) {
        if (requestId !== this.educationContextRequestId) return
        this.educationContext = null
      } finally {
        if (requestId === this.educationContextRequestId) {
          this.educationContextLoading = false
        }
      }
    },

    async handleSendMessage(payload) {
      if (!this.currentConversation) return
      const convId = this.currentConversation.id
      const content = typeof payload === 'string' ? payload : payload?.content
      const targetAgentIds = Array.isArray(payload?.target_agent_ids) ? payload.target_agent_ids : []
      const mentions = Array.isArray(payload?.mentions) ? payload.mentions : []
      const agentConfigs = payload?.agent_configs || {}
      const workflow = payload?.workflow || null
      if (!content) return
      const messageMeta = {}
      if (targetAgentIds.length) {
        messageMeta.dispatch_mode = 'direct'
        messageMeta.mentions = mentions
      }
      if (workflow) {
        messageMeta.selected_workflow = this.selectedWorkflowMeta(workflow)
      }

      // === Optimistic UI: show user message immediately ===
      const tempId = 'temp_' + Date.now()
      this.$store.commit('message/APPEND_MESSAGE', {
        conversationId: convId,
        message: {
          id: tempId,
          conversation_id: convId,
          sender_type: 'user',
          sender_id: this.userId,
          content: content,
          message_type: 'text',
          created_at: this.localDateTimeString(),
          meta: Object.keys(messageMeta).length ? messageMeta : undefined,
        },
      })

      this.isAgentResponding = true

      try {
        const requestData = {
          conversation_id: convId,
          content: content,
          message_type: 'text',
        }
        if (targetAgentIds.length) {
          requestData.target_agent_ids = targetAgentIds
        }
        if (Object.keys(agentConfigs).length) {
          requestData.agent_configs = agentConfigs
        }
        if (workflow) {
          requestData.workflow = workflow
        }
        const res = await apiSendMessage(requestData)

        if (res.code === 201) {
          // Replace temp ID with real ID from server
          this.$store.commit('message/UPDATE_MESSAGE_ID', {
            conversationId: convId,
            tempId,
            realId: res.data.id,
          })

          this.$store.dispatch('conversation/fetchConversations', this.activeWorkspaceId)
          this.startMessageRefresh(convId)
        }
      } catch (e) {
        this.$message.error('发送失败')
        this.isAgentResponding = false
        this.stopMessageRefresh()
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

    registerSocketHandlers() {
      this.unregisterSocketHandlers()
      const onCreated = (message) => {
        const convId = message.conversation_id
        this.$store.commit('message/UPSERT_MESSAGE', {
          conversationId: convId,
          message,
        })
        this.isAgentResponding = this.hasStreamingMessages(convId)
        this.$store.dispatch('conversation/fetchConversations', this.activeWorkspaceId)
      }
      const onDelta = (event) => {
        const patch = {
          content: event.content,
          elements: event.elements,
          raw_output: event.raw_output,
          status: event.status,
          replace_elements: event.replace_elements,
          clear_raw_output: event.clear_raw_output,
        }
        if (event.sender_name) {
          patch.sender_name = event.sender_name
        }
        this.$store.commit('message/UPDATE_MESSAGE', {
          conversationId: event.conversation_id,
          messageId: event.message_id,
          patch,
        })
        this.isAgentResponding = this.hasStreamingMessages(event.conversation_id)
      }
      const onElement = (event) => {
        const patch = {
          content: event.content,
          raw_output: event.raw_output,
          status: event.status,
        }
        if (event.sender_name) {
          patch.sender_name = event.sender_name
        }
        this.$store.commit('message/APPEND_MESSAGE_ELEMENT', {
          conversationId: event.conversation_id,
          messageId: event.message_id,
          element: event.element,
          patch,
        })
        this.$store.commit('message/ADD_MESSAGE_EVENT', {
          conversationId: event.conversation_id,
          messageId: event.message_id,
          events: event.events,
        })
      }
      const onStep = (event) => {
        this.$store.commit('message/ADD_MESSAGE_EVENT', {
          conversationId: event.conversation_id,
          messageId: event.message_id,
          event: event.event,
          events: event.events,
        })
      }
      const onElementStream = onElement
      const onStatus = (event) => {
        const patch = {
          content: event.content,
          elements: event.elements,
          raw_output: event.raw_output,
          status: event.status,
          replace_elements: event.replace_elements,
          clear_raw_output: event.clear_raw_output,
        }
        if (event.sender_name) {
          patch.sender_name = event.sender_name
        }
        if (event.events) {
          patch.meta = { events: event.events }
        }
        this.$store.commit('message/UPDATE_MESSAGE', {
          conversationId: event.conversation_id,
          messageId: event.message_id,
          patch,
        })
        this.isAgentResponding = this.hasStreamingMessages(event.conversation_id)
        this.$store.dispatch('conversation/fetchConversations', this.activeWorkspaceId)
        if (!this.isAgentResponding) {
          this.stopMessageRefresh()
        }
      }

      this.socketHandlers = [
        ['conversation_message_created', onCreated],
        ['conversation_message_delta', onDelta],
        ['conversation_message_element_stream', onElementStream],
        ['conversation_message_step', onStep],
        ['conversation_message_status', onStatus],
      ]
      this.socketHandlers.forEach(([event, handler]) => socketClient.on(event, handler))
    },

    unregisterSocketHandlers() {
      this.socketHandlers.forEach(([event, handler]) => socketClient.off(event, handler))
      this.socketHandlers = []
    },

    hasStreamingMessages(conversationId) {
      const msgs = this.$store.getters['message/getMessagesByConversation'](conversationId)
      return msgs.some(m => m.sender_type === 'agent' && ['pending', 'streaming'].includes(m.status))
    },

    startMessageRefresh(conversationId) {
      this.stopMessageRefresh()
      let ticks = 0
      this.messageRefreshTimer = setInterval(async () => {
        ticks += 1
        if (!this.currentConversation || this.currentConversation.id !== conversationId) {
          this.stopMessageRefresh()
          return
        }
        await this.$store.dispatch('message/fetchMessages', { conversationId })
        this.isAgentResponding = this.hasStreamingMessages(conversationId)
        if (!this.isAgentResponding || ticks >= 120) {
          this.stopMessageRefresh()
        }
      }, 2000)
    },

    stopMessageRefresh() {
      if (this.messageRefreshTimer) {
        clearInterval(this.messageRefreshTimer)
        this.messageRefreshTimer = null
      }
    },

    async handlePinMessage(messageId) {
      await this.$store.dispatch('message/togglePin', messageId)
    },

    async handleDeleteConversation() {
      if (!this.currentConversation) return
      try {
        await this.$confirm('确认删除该会话？', '提示', {
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          type: 'warning',
        })
        await this.$store.dispatch('conversation/deleteConversation', this.currentConversation.id)
        this.$message.success('会话已删除')
      } catch (e) {}
    },

    async handleStopAgent(message) {
      if (!this.currentConversation || !message?.sender_id) return
      try {
        await stopConversationAgent(this.currentConversation.id, message.sender_id)
      } catch (e) {
        this.$message.error('停止 Agent 失败')
      }
    },

    async handleOpenWorkspace(scope = 'workspace') {
      if (!this.currentConversation) return
      let root = '/workspace'
      if (scope && scope.startsWith('agent:')) {
        const agentId = scope.split(':')[1]
        const agent = this.currentSessionAgents.find(item => item.agent_id === agentId)
        root = `/workspace/agents/${agent?.workspace_name || this.safeWorkspaceName(agent?.role || agentId)}`
      } else if (scope === 'shared') {
        root = '/workspace/shared'
      }
      this.currentWorkbenchArtifact = {
        path: '',
        root,
        type: 'workspace',
        name: '工作台',
      }
      this.artifactWorkbenchVisible = true
    },

    async handleOpenFile(file) {
      if (!this.currentConversation || !file?.path) return
      const path = this.normalizeWorkspacePath(file.path)
      this.currentWorkbenchArtifact = this.buildWorkbenchArtifact({
        ...file,
        path,
      })
      this.artifactWorkbenchVisible = true
    },

    handleSearchMessages() {
      this.$message.info('搜索功能即将上线')
    },

    handleOpenAttachment() {
      this.handleOpenWorkspace('workspace')
    },

    handleToggleStar() {
      if (!this.currentConversation) return
      const nextValue = !this.currentConversation.is_favorite
      this.$store.dispatch('conversation/toggleConversationFavorite', {
        conversationId: this.currentConversation.id,
        isFavorite: nextValue,
      }).then(response => {
        if (response.code === 200) {
          this.$message.success(nextValue ? '已收藏' : '已取消收藏')
        } else {
          this.$message.error(response.message || '收藏操作失败')
        }
      }).catch(() => {
        this.$message.error('收藏操作失败')
      })
    },

    handleOpenHistory() {
      this.$message.info('历史记录功能即将上线')
    },

    async handleOpenAttachments() {
      if (!this.currentConversation) return
      this.attachmentsVisible = true
      await this.loadAttachments()
    },

    async handleOpenServices() {
      if (!this.currentConversation) return
      this.servicesVisible = true
      if (!this.serviceForm.agent_id && this.currentSessionAgents.length) {
        const worker = this.currentSessionAgents.find(a => a.agent_id !== 'moderator') || this.currentSessionAgents[0]
        this.serviceForm.agent_id = worker.agent_id
        this.syncServiceCwd()
      }
      this.syncServiceCommand()
      await this.loadServices()
    },

    handleOpenMigration() {
      if (!this.currentConversation) return
      this.migrationDialogVisible = true
    },

    handleOpenMigrationTarget(conversationId) {
      const target = this.conversations.find(item => item.id === conversationId)
      if (target) {
        this.handleSelectConversation(target)
        return
      }
      this.$store.dispatch('conversation/fetchConversations', this.activeWorkspaceId).then(() => {
        const next = this.conversations.find(item => item.id === conversationId)
        if (next) this.handleSelectConversation(next)
      })
    },

    async loadServices() {
      if (!this.currentSessionId) return
      this.servicesLoading = true
      try {
        const res = await listServices(this.currentSessionId)
        if (res.code === 200) {
          this.services = res.data?.services || []
        }
      } catch (e) {
        this.$message.error(e?.message || '获取服务列表失败')
      } finally {
        this.servicesLoading = false
      }
    },

    async handleStartService() {
      if (!this.currentSessionId) return
      if (!this.serviceForm.agent_id) {
        this.$message.warning('请选择 Agent')
        return
      }
      this.serviceStarting = true
      try {
        const port = Number(this.serviceForm.port)
        const command = this.normalizeServiceCommandPort(this.serviceForm.command, port)
        this.serviceForm.command = command
        const res = await startService(this.currentSessionId, {
          agent_id: this.serviceForm.agent_id,
          port,
          cwd: this.serviceForm.cwd,
          command,
        })
        if (res.code === 200) {
          const service = res.data?.service || {}
          const url = this.serviceUrl(service)
          this.$message.success(url ? `服务已启动：${url}` : '服务已启动')
          await this.loadServices()
          if (url) window.open(url, '_blank')
        }
      } catch (e) {
        this.$message.error(e?.message || '启动服务失败')
      } finally {
        this.serviceStarting = false
      }
    },

    normalizeServiceCommandPort(command, port) {
      const nextPort = Number(port)
      let next = String(command || '').trim()
      if (!next || !nextPort) return next
      if (/(^|\s)--port=\d{2,5}(?=\s|$)/.test(next)) {
        return next.replace(/(^|\s)--port=\d{2,5}(?=\s|$)/, `$1--port=${nextPort}`)
      }
      if (/(^|\s)--port\s+\d{2,5}(?=\s|$)/.test(next)) {
        return next.replace(/(^|\s)--port\s+\d{2,5}(?=\s|$)/, `$1--port ${nextPort}`)
      }
      if (/(^|\s)-p\s+\d{2,5}(?=\s|$)/.test(next)) {
        return next.replace(/(^|\s)-p\s+\d{2,5}(?=\s|$)/, `$1-p ${nextPort}`)
      }
      if (/\bhttp\.server\s+\d{2,5}(?=\s|$)/.test(next)) {
        return next.replace(/\bhttp\.server\s+\d{2,5}(?=\s|$)/, `http.server ${nextPort}`)
      }
      return next
    },

    syncServiceCwd() {
      const agent = this.currentSessionAgents.find(a => a.agent_id === this.serviceForm.agent_id)
      if (!agent) return
      this.serviceForm.cwd = `/workspace/agents/${agent.workspace_name || this.safeWorkspaceName(agent.name || agent.role || agent.agent_id)}`
    },

    syncServiceCommand() {
      const port = Number(this.serviceForm.port)
      if (port === 5173) {
        this.serviceForm.command = 'npm run dev -- --host 0.0.0.0 --port 5173'
      } else if (port === 8081) {
        this.serviceForm.command = 'npm run serve -- --host 0.0.0.0 --port 8081'
      } else if (port === 3000) {
        this.serviceForm.command = 'npm start -- --host 0.0.0.0 --port 3000'
      } else if (port === 8000) {
        this.serviceForm.command = 'python3 -m http.server 8000 --bind 0.0.0.0'
      }
    },

    async copyServiceUrl(url) {
      try {
        await navigator.clipboard.writeText(url)
        this.$message.success('已复制访问链接')
      } catch (e) {
        this.$message.info(url)
      }
    },

    serviceId(svc) {
      return svc?.service_id || svc?.id || ''
    },

    serviceUrl(svc) {
      const urls = [svc?.proxy_url, svc?.url].filter(url => typeof url === 'string' && url.trim())
      return urls.find(url => /[?&]token=/.test(url)) || urls[0] || ''
    },

    serviceStatusLabel(status) {
      const key = String(status || 'unknown').toLowerCase()
      return {
        running: '运行中',
        starting: '启动中',
        stopped: '已停止',
        stopping: '停止中',
        failed: '失败',
        exited: '已退出',
        open: '运行中',
        closed: '已关闭',
        unknown: '未知',
      }[key] || status
    },

    serviceStatusType(status) {
      const key = String(status || '').toLowerCase()
      if (['running', 'open'].includes(key)) return 'success'
      if (['starting', 'stopping'].includes(key)) return 'warning'
      if (['failed', 'exited'].includes(key)) return 'danger'
      return 'info'
    },

    formatServiceExpiry(value) {
      if (!value) return ''
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return ''
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    },

    openServiceUrl(svc) {
      const url = this.serviceUrl(svc)
      if (url) window.open(url, '_blank', 'noopener')
    },

    async showServiceLogs(svc) {
      const id = this.serviceId(svc)
      if (!this.currentSessionId || !id) return
      this.serviceLogsVisible = true
      this.serviceLogsLoading = true
      try {
        const res = await getServiceLogs(this.currentSessionId, id)
        if (res.code === 200) {
          this.serviceLogsData = res.data || {}
        }
      } catch (e) {
        this.$message.error(e?.message || '获取服务日志失败')
      } finally {
        this.serviceLogsLoading = false
      }
    },

    async handleStopService(svc) {
      const id = this.serviceId(svc)
      if (!this.currentSessionId || !id) return
      try {
        const res = await stopService(this.currentSessionId, id)
        if (res.code === 200) {
          this.$message.success('服务已停止')
          await this.loadServices()
        }
      } catch (e) {
        this.$message.error(e?.message || '停止服务失败')
      }
    },

    async handleRestartService(svc) {
      const id = this.serviceId(svc)
      if (!this.currentSessionId || !id) return
      try {
        const res = await restartService(this.currentSessionId, id)
        if (res.code === 200) {
          this.$message.success('服务已重启')
          await this.loadServices()
        }
      } catch (e) {
        this.$message.error(e?.message || '重启服务失败')
      }
    },

    async loadAttachments() {
      if (!this.currentConversation) return
      this.attachmentsLoading = true
      try {
        const res = await getConversationAttachments(this.currentConversation.id)
        if (res.code === 200) {
          this.attachments = res.data.files || []
        }
      } catch (e) {
        this.$message.error('获取上传文件失败')
      } finally {
        this.attachmentsLoading = false
      }
    },

    async handleAttachmentPicked(file) {
      if (!this.currentConversation || !file?.raw) return
      this.attachmentsLoading = true
      try {
        await uploadConversationAttachment(this.currentConversation.id, file.raw)
        this.$message.success('文件已上传到 Agent 工作目录')
        await this.loadAttachments()
      } catch (e) {
        this.$message.error(e?.response?.data?.message || e?.message || '上传失败')
      } finally {
        this.attachmentsLoading = false
      }
    },

    async handleDeleteAttachment(file) {
      if (!this.currentConversation || !file?.path) return
      try {
        await this.$confirm(`删除 ${file.name}？`, '提示', {
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          type: 'warning',
        })
        await deleteConversationAttachment(this.currentConversation.id, file.path, file.agent_id)
        this.$message.success('文件已删除')
        await this.loadAttachments()
      } catch (e) {}
    },

    async switchFileScope(scope) {
      if (!this.currentSessionId) return
      let root = '/workspace'
      let title = '全部文件'
      if (scope === 'shared') {
        root = '/workspace/shared'
        title = '公共目录'
      } else if (scope && scope.startsWith('agent:')) {
        const agentId = scope.slice('agent:'.length)
        const agent = this.currentSessionAgents.find(a => a.agent_id === agentId)
        root = `/workspace/agents/${agent?.workspace_name || this.safeWorkspaceName(agent?.role || agentId)}`
        title = `${agent?.role || agentId} 文件`
      }
      this.fileScope = scope || 'workspace'
      this.previewTitle = title
      this.previewContent = ''
      this.previewType = 'text'
      this.previewUrl = ''
      this.selectedFilePath = ''
      await this.loadFileTree(root)
    },

    async loadFileTree(root) {
      if (!this.currentSessionId) return
      this.previewLoading = true
      try {
        const res = await getFileTree(this.currentSessionId, root)
        if (res.code === 200 && res.data?.tree) {
          this.fileTreeData = [res.data.tree]
          this.fileTreeRoot = root
        }
      } catch (e) {
        this.$message.error('获取文件树失败')
      } finally {
        this.previewLoading = false
      }
    },

    handleFileNodeClick(data) {
      if (data.type === 'directory') {
        this.selectedFilePath = ''
        this.previewContent = ''
        this.previewType = 'text'
        this.previewUrl = ''
        this.loadFileTree(data.path)
        return
      }
      this.previewFile(data.path)
    },

    previewFile(filePath) {
      if (!this.currentSessionId || !filePath) return
      this.previewLoading = true
      this.previewVisible = true
      this.previewTitle = filePath
      this.previewContent = ''
      this.previewUrl = ''
      this.selectedFilePath = filePath

      const ext = this.getExt(filePath)
      if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'].includes(ext)) {
        this.previewType = 'image'
        this.previewUrl = getSessionRawFileUrl(this.currentSessionId, filePath)
        this.previewLoading = false
        return
      }
      if (ext === 'pdf') {
        this.previewType = 'pdf'
        this.previewUrl = getSessionRawFileUrl(this.currentSessionId, filePath)
        this.previewLoading = false
        return
      }
      if (this.isHtmlFile(filePath)) {
        this.previewType = 'html'
        this.previewUrl = getWorkspaceFileUrl(this.currentSessionId, filePath)
        this.previewLoading = false
        return
      }
      if (!['txt', 'md', 'json', 'js', 'css', 'vue', 'html', 'htm', 'py', 'yml', 'yaml', 'xml', 'csv', 'log'].includes(ext)) {
        this.previewType = 'binary'
        this.previewLoading = false
        return
      }

      const agentId = this.currentSessionAgents[0]?.agent_id || ''
      this.previewType = 'text'
      readAgentFile(this.currentSessionId, agentId, filePath)
        .then(res => {
          this.previewContent = res.code === 200 && res.data?.content !== undefined
            ? res.data.content
            : '无法读取文件'
        })
        .catch(e => {
          this.previewContent = '加载失败: ' + (e?.message || '未知错误')
        })
        .finally(() => { this.previewLoading = false })
    },

    openContainingFolder(path) {
      if (!path) return
      const normalized = path.replace(/\\/g, '/')
      const idx = normalized.lastIndexOf('/')
      if (idx > 0) this.loadFileTree(normalized.slice(0, idx))
    },

    openWorkspaceFile(filePath) {
      if (!this.currentSessionId) return
      window.open(getWorkspaceFileUrl(this.currentSessionId, filePath), '_blank')
    },

    buildWorkbenchArtifact(file) {
      const path = this.normalizeWorkspacePath(file?.path || '')
      return {
        path,
        name: file?.name || path.split('/').pop() || '',
        type: file?.type || this.inferArtifactType(path),
        diffElement: file?.diffElement || null,
        imageUrl: file?.imageUrl || '',
        codeContent: file?.codeContent || '',
        tableHeaders: Array.isArray(file?.tableHeaders) ? file.tableHeaders : [],
        tableRows: Array.isArray(file?.tableRows) ? file.tableRows : [],
      }
    },

    inferArtifactType(path) {
      const ext = this.getExt(path)
      if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'].includes(ext)) return 'image'
      if (ext === 'csv') return 'table'
      if (['html', 'htm'].includes(ext)) return 'webpage'
      if (['txt', 'log'].includes(ext)) return 'text'
      if (['md', 'json', 'js', 'css', 'vue', 'py', 'yml', 'yaml', 'xml', 'sql', 'ts', 'tsx', 'jsx', 'java', 'go', 'rs', 'php', 'rb', 'sh', 'bat', 'ps1', 'kt', 'swift', 'dart', 'c', 'h', 'cpp', 'cc', 'cxx', 'hpp', 'cs', 'toml', 'scss', 'less'].includes(ext)) {
        return 'code'
      }
      return 'file'
    },

    downloadFile(path) {
      if (!this.currentSessionId || !path) return
      window.open(getSessionDownloadUrl(this.currentSessionId, path), '_blank')
    },

    copyFilePath(path) {
      navigator.clipboard?.writeText(path)
      this.$message.success('已复制路径')
    },

    localDateTimeString() {
      const date = new Date()
      const pad = n => String(n).padStart(2, '0')
      return [
        date.getFullYear(),
        pad(date.getMonth() + 1),
        pad(date.getDate()),
      ].join('-') + 'T' + [
        pad(date.getHours()),
        pad(date.getMinutes()),
        pad(date.getSeconds()),
      ].join(':')
    },

    getExt(path) {
      const clean = (path || '').split('?')[0].split('#')[0]
      const idx = clean.lastIndexOf('.')
      return idx >= 0 ? clean.slice(idx + 1).toLowerCase() : ''
    },

    isHtmlFile(path) {
      return ['html', 'htm'].includes(this.getExt(path))
    },

    getFileIcon(path) {
      const ext = this.getExt(path)
      if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext)) return 'el-icon-picture'
      if (['html', 'htm'].includes(ext)) return 'el-icon-monitor'
      if (['js', 'css', 'vue', 'py', 'json', 'md'].includes(ext)) return 'el-icon-document'
      return 'el-icon-document'
    },

    formatFileSize(bytes) {
      if (!bytes) return ''
      const units = ['B', 'KB', 'MB', 'GB']
      let i = 0
      let size = bytes
      while (size >= 1024 && i < units.length - 1) {
        size /= 1024
        i++
      }
      return size.toFixed(1) + ' ' + units[i]
    },

    normalizeWorkspacePath(path) {
      if (!path) return ''
      const clean = String(path).replace(/\\/g, '/').replace(/^\/+/, '')
      return clean.startsWith('workspace/') ? `/${clean}` : `/workspace/${clean}`
    },

    safeWorkspaceName(name) {
      return String(name || 'agent')
        .trim()
        .replace(/[\\/:*?"<>|\x00-\x1f]/g, '_')
        .replace(/\s+/g, '_')
        .replace(/^[._ ]+|[._ ]+$/g, '')
        .slice(0, 80) || 'agent'
    },

    // ====== 新建会话 ======
    resetNewConversation() {
      this.newConversation = {
        title: '',
        type: 'single',
        selectedAgents: [],
        services: [],
        projectId: '',
        kbDomain: '',
        kbDocumentIds: [],
        courseId: '',
        lessonId: '',
        materialPolicy: 'course_only',
      }
      this.educationOptions = {
        membership_role: '',
        lessons: [],
        agents: [],
        material_policies: [],
      }
      this.agentTreeData = []
    },
    async loadEducationCourses() {
      this.educationCoursesLoading = true
      try {
        const response = await getCourses()
        this.educationCourses = response?.items || []
        const requestedCourseId = String(
          this.$route.query.courseId || this.$route.query.course_id || ''
        )
        const preferred = this.educationCourses.find(
          course => course.id === requestedCourseId
        )
        if (preferred) {
          this.newConversation.courseId = preferred.id
          await this.loadEducationOptions(preferred.id)
        } else if (this.educationCourses.length === 1) {
          this.newConversation.courseId = this.educationCourses[0].id
          await this.loadEducationOptions(this.educationCourses[0].id)
        }
      } catch (error) {
        this.educationCourses = []
        this.$message.error('智慧教育服务暂不可用，请稍后重试')
      } finally {
        this.educationCoursesLoading = false
      }
    },
    async loadEducationOptions(courseId) {
      this.newConversation.lessonId = ''
      this.newConversation.selectedAgents = []
      this.agentTreeData = []
      if (!courseId) {
        this.educationOptions = {
          membership_role: '',
          lessons: [],
          agents: [],
          material_policies: [],
        }
        return
      }
      this.treeLoading = true
      try {
        const response = await getEducationConversationOptions(courseId)
        this.educationOptions = response || {
          membership_role: '',
          lessons: [],
          agents: [],
          material_policies: [],
        }
        if (
          !(this.educationOptions.material_policies || [])
            .some(item => item.value === this.newConversation.materialPolicy)
        ) {
          this.newConversation.materialPolicy =
            this.educationOptions.material_policies?.[0]?.value || 'course_only'
        }
        await this.buildAgentTree()
      } catch (error) {
        this.$message.error('无法读取该课程的会话权限')
      } finally {
        this.treeLoading = false
      }
    },
    async buildAgentTree() {
      this.treeLoading = true
      const treeData = []

      try {
        if (this.isEducationWorkspace) {
          this.agentTreeData = this.buildEducationAgentTree()
          this.treeLoading = false
          return
        }
        // Fetch categories + agents for current domain only
        const domain = this.activeDomain
        const [catRes, agentRes] = await Promise.all([
          getCategories(domain),
          getAgents(null, domain),
        ])
        const cats = catRes.code === 200 ? catRes.data : []
        let agents = agentRes.code === 200
          ? agentRes.data.filter(agent => agent.id !== 'moderator')
          : []
        for (const cat of cats) {
          const children = []
          for (const agent of agents) {
            if (agent.class_id === cat.id) {
              children.push({
                id: agent.id,
                label: agent.name,
                isLeaf: true,
                agentColor: agent.avatar_color || '#4080ff',
                agentAvatar: agent.avatar_url || '',
                adapterLabel: { claude: 'Claude', codex: 'Codex', opencode: 'OpenCode', mock: 'Mock' }[agent.adapter_name] || agent.adapter_name,
              })
            }
          }
          if (children.length > 0) {
            treeData.push({
              id: cat.id,
              label: cat.name,
              icon: cat.icon || 'el-icon-folder-opened',
              children,
            })
          }
        }

        // Uncategorized agents
        const uncategorized = agents.filter(a => !a.class_id)
        if (uncategorized.length > 0) {
          const children = uncategorized.map(agent => ({
            id: agent.id,
            label: agent.name,
            isLeaf: true,
            agentColor: agent.avatar_color || '#4080ff',
            agentAvatar: agent.avatar_url || '',
            adapterLabel: { claude: 'Claude', codex: 'Codex', opencode: 'OpenCode', mock: 'Mock' }[agent.adapter_name] || agent.adapter_name,
          }))
          treeData.push({
            id: '_uncategorized',
            label: '其他',
            icon: 'el-icon-folder-opened',
            children,
          })
        }
      } catch (e) {
        this.$message.error('加载Agent列表失败')
      }
      this.agentTreeData = treeData
      this.treeLoading = false
    },
    buildEducationAgentTree() {
      const groups = new Map()
      for (const agent of this.educationOptions.agents || []) {
        const categoryId = agent.category_id || '_education'
        if (!groups.has(categoryId)) {
          groups.set(categoryId, {
            id: categoryId,
            label: agent.category_name || 'Education Agent',
            icon: agent.category_icon || 'el-icon-folder-opened',
            children: [],
          })
        }
        groups.get(categoryId).children.push({
          id: agent.id,
          label: agent.name || agent.id,
          isLeaf: true,
          agentColor: agent.avatar_color || '#267d71',
          agentAvatar: agent.avatar_url || '',
          adapterLabel: {
            claude: 'Claude',
            codex: 'Codex',
            opencode: 'OpenCode',
            mock: 'Mock',
          }[agent.adapter_name] || agent.adapter_name || '',
        })
      }
      return Array.from(groups.values())
    },
    findAgentWithMeta(id) {
      const agent = this.allAvailableAgents.find(a => a.id === id) ||
        (this.educationOptions.agents || []).find(a => a.id === id)
      if (!agent) return null
      // Merge any locally-stored overrides (backward compat)
      const meta = getAgentMeta(id)
      return {
        ...agent,
        avatar: agent.avatar_url || agent.avatar || '',
        color: agent.avatar_color || agent.color || '#267d71',
        ...meta,
      }
    },
    async quickCreateWorkspace(domain) {
      const names = { rd: '我的研发空间', edu: '我的教育空间', office: '我的办公空间' }
      try {
        const res = await this.$store.dispatch('workspace/createWorkspace', {
          name: names[domain] || '我的工作空间',
          domain,
          description: '',
        })
        if (res.code === 201) {
          this.$message.success('工作空间已创建')
          this.$store.dispatch('grayscale/loadDomainConfig', domain)
        }
      } catch {
        this.$message.error('创建失败，请重试')
      }
    },

    async fetchProjects() {
      if (this.projectList.length > 0) return  // already loaded
      this.projectsLoading = true
      try {
        const { getProjects } = await import('../api/rd')
        const res = await getProjects()
        if (res.code === 200) {
          this.projectList = res.data?.items || []
        }
      } catch (e) {
        // RD service may not be running — silently skip, dropdown shows empty
        this.projectList = []
      } finally {
        this.projectsLoading = false
      }
    },

    handleTreeCheckChange() {
      if (this.$refs.agentTree) {
        const checkedAgents = this.$refs.agentTree.getCheckedNodes(true)
          .filter(node => node.isLeaf && node.id !== 'moderator')
          .map(node => node.id)
        this.newConversation.selectedAgents = checkedAgents
      }
    },

    kbDomainLabel(domain) {
      const map = { rd: '智能研发', edu: '智慧教育', office: '智慧办公', all: '全部领域' }
      return map[domain] || domain || '继承工作空间'
    },

    async handleCreateConversation() {
      if (this.isEducationWorkspace && !this.newConversation.courseId) {
        this.$message.warning('请选择课程')
        return
      }
      if (this.newConversation.selectedAgents.length === 0) {
        this.$message.warning('请至少选择一个 Agent')
        return
      }
      if (!this.newConversation.title) {
        this.$message.warning('请输入标题')
        return
      }
      this.creating = true
      try {
        if (this.isEducationWorkspace) {
          const result = await bootstrapEducationConversation({
            course_id: this.newConversation.courseId,
            lesson_id: this.newConversation.lessonId || undefined,
            agent_ids: this.newConversation.selectedAgents,
            material_policy: this.newConversation.materialPolicy,
            title: this.newConversation.title,
            source_route: {
              path: this.$route.path,
              query: { ...this.$route.query },
            },
          })
          const conversation = result?.conversation
          if (!conversation?.id) {
            throw new Error('Education bootstrap did not return a conversation')
          }
          this.$store.commit('conversation/ADD_CONVERSATION', conversation)
          this.$message.success('Education 会话创建成功')
          this.showCreateDialog = false
          this.resetNewConversation()
          this.handleSelectConversation(conversation)
          await this.$store.dispatch(
            'conversation/fetchConversations',
            conversation.workspace_id || this.activeWorkspaceId
          )
          return
        }
        const participantIds = this.newConversation.selectedAgents
          .filter(id => id)
          .map(id => `agent_${id}`)
        const response = await this.$store.dispatch('conversation/createConversation', {
          title: this.newConversation.title,
          type: this.newConversation.type,
          participant_ids: participantIds,
          workspace_id: this.activeWorkspaceId || undefined,
          services: this.newConversation.services,
          project_id: this.newConversation.projectId || undefined,
          kb_domain: this.newConversation.kbDomain || '',
          kb_document_ids: this.newConversation.kbDocumentIds,
        })
        if (response.code === 201) {
          this.$message.success('会话创建成功')
          this.showCreateDialog = false
          this.resetNewConversation()
          this.handleSelectConversation(response.data)
        } else {
          this.$message.error(response.message || '创建会话失败')
        }
      } finally {
        this.creating = false
      }
    },
  },
}
</script>

<style scoped>
.dashboard {
  display: flex;
  gap: 12px;
  padding: 12px;
  height: 100vh;
  background: linear-gradient(135deg, #e8f0ff 0%, #f0f5ff 50%, #f5f7fa 100%);
  overflow: hidden;
}

/* 第二栏：会话列表 - 固定 300px 圆角卡片 */
.conversation-panel {
  width: 250px;
  flex-shrink: 0;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 第三栏：主聊天区 - 自适应剩余宽度 圆角卡片 */
.chat-panel {
  flex: 1;
  min-width: 600px;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  overflow: hidden;
}

.no-agents-hint {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}

/* ===== 新建会话对话框 ===== */
.create-conv-body {
  padding: 0 4px;
}
.conv-field {
  margin-bottom: 20px;
}
.field-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 8px;
}
.field-hint {
  font-weight: 400;
  font-size: 12px;
  color: #94a3b8;
}
.conv-field .el-input__inner {
  border-radius: 10px;
  height: 40px;
}
.conv-field .el-input__inner:focus {
  border-color: #4080ff;
}

/* Agent 树 */
.agent-tree-wrapper {
  border: 1px solid #e8eaed;
  border-radius: 12px;
  padding: 8px 4px;
  max-height: 300px;
  overflow-y: auto;
  background: #fafbfc;
}
.agent-tree-wrapper::-webkit-scrollbar { width: 4px; }
.agent-tree-wrapper::-webkit-scrollbar-thumb { background: #dcdde1; border-radius: 4px; }
.agent-tree {
  background: transparent;
}
.agent-tree :deep(.el-tree-node__content) {
  height: 38px;
  border-radius: 8px;
  padding-left: 8px !important;
}
.agent-tree :deep(.el-tree-node__content:hover) {
  background: rgba(64,128,255,0.06);
}
.agent-tree :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: #4080ff;
  border-color: #4080ff;
}
.agent-tree :deep(.el-checkbox__input.is-indeterminate .el-checkbox__inner) {
  background-color: #4080ff;
  border-color: #4080ff;
}
.tree-node {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
}
.node-category {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: #1e293b;
}
.node-category i {
  font-size: 15px;
  color: #4080ff;
}
.node-count {
  font-size: 11px;
  color: #94a3b8;
  margin-left: 4px;
}
.node-agent {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}
.node-avatar {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.node-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 6px;
}
.node-avatar-letter {
  font-size: 11px;
  font-weight: 700;
  color: #fff;
}
.node-name {
  font-size: 13px;
  color: #1e293b;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.node-badge {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  background: #f0f5ff;
  color: #4080ff;
  flex-shrink: 0;
  line-height: 18px;
}

/* 预览头像区 */
.conv-preview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid #e8eaed;
}
.preview-avatars {
  display: flex;
  align-items: center;
  gap: 4px;
}
.preview-avatar {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: #4080ff;
  color: #fff;
  font-size: 13px;
  border: 2px solid #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.preview-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 6px;
}
.preview-avatar i {
  font-size: 14px;
}
.user-avatar-mini {
  background: #e8eaed;
  color: #64748b;
}
.preview-plus {
  color: #94a3b8;
  font-size: 16px;
  font-weight: 300;
  margin: 0 2px;
}
.preview-type {
  flex-shrink: 0;
}

/* 领域服务选择卡片 */
.service-checkboxes {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.education-conversation-scope {
  margin: 4px 0 18px;
  padding: 16px;
  border: 1px solid #d9ebe7;
  border-radius: 14px;
  background:
    radial-gradient(circle at 92% 8%, rgba(51, 142, 126, .10), transparent 34%),
    #f7fbfa;
}

.scope-heading {
  display: flex;
  align-items: center;
  gap: 11px;
  margin-bottom: 14px;
}

.scope-heading > div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.scope-heading strong {
  color: #173f38;
  font-size: 15px;
}

.scope-heading small {
  color: #78938e;
  font-size: 12px;
}

.scope-icon {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border-radius: 11px;
  background: #267d71;
  color: #fff;
}

.scope-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.membership-role {
  display: flex;
  min-height: 38px;
  align-items: center;
  gap: 7px;
  box-sizing: border-box;
  padding: 0 11px;
  border: 1px solid #d8e5e2;
  border-radius: 7px;
  background: #fff;
  color: #2b6259;
  font-weight: 600;
}

.membership-role small {
  margin-left: auto;
  color: #8da09c;
  font-size: 10px;
  font-weight: 400;
}

.membership-role.pending {
  color: #83928f;
  font-weight: 400;
}

.field-required {
  margin-left: 4px;
  color: #c45d48;
  font-size: 11px;
}

.capability-summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
  color: #6e8782;
  font-size: 12px;
}

.service-checkbox {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1.5px solid #e8eaed;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  background: #fafbfc;
}
.service-checkbox:hover {
  border-color: #c0d3f0;
  background: #f8faff;
}
.service-checkbox.checked {
  border-color: #4080ff;
  background: #f0f5ff;
  box-shadow: 0 0 0 2px rgba(64,128,255,0.12);
}
.service-checkbox.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.service-checkbox.disabled:hover {
  border-color: #e8eaed;
  background: #fafbfc;
}
.service-checkbox input[type="checkbox"] {
  display: none;
}
.svc-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  background: #e8f0ff;
  color: #4080ff;
  flex-shrink: 0;
}
.svc-icon.rag {
  background: #e8f5e9;
  color: #4caf50;
}
.svc-icon.edu {
  background: #fff3e0;
  color: #ff9800;
}
.svc-icon.office {
  background: #f3e5f5;
  color: #9c27b0;
}
.svc-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.svc-info strong {
  font-size: 13px;
  color: #1e293b;
}
.svc-info em {
  font-size: 11px;
  color: #94a3b8;
  font-style: normal;
}

/* 上下文预览芯片 */
.conv-context-preview {
  margin-top: 4px;
  padding: 8px 0;
}
.context-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.context-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}
.context-chip.rd {
  background: #e8f0ff;
  color: #4080ff;
}
.context-chip.rag {
  background: #e8f5e9;
  color: #4caf50;
}
.context-chip.project {
  background: #fff3e0;
  color: #e65100;
}

/* 底部按钮 */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.create-btn {
  border: none;
  border-radius: 8px;
  background: #4080ff;
  padding: 8px 20px;
}

/* 无工作空间空状态 */
.workspace-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-card {
  text-align: center;
  padding: 60px 80px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  max-width: 600px;
}

.empty-icon {
  margin-bottom: 18px;
}

.empty-icon i {
  font-size: 64px;
  color: #4080ff;
}

.empty-card h3 {
  margin: 0 0 8px;
  font-size: 24px;
  font-weight: 700;
  color: #1e293b;
}

.empty-card p {
  margin: 0 0 30px;
  font-size: 15px;
  color: #94a3b8;
}

.empty-domains {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.domain-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
  border: 1px solid #e8eaed;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}

.domain-card:hover {
  border-color: #4080ff;
  background: #f8faff;
  box-shadow: 0 2px 8px rgba(64,128,255,0.1);
}

.domain-card i {
  font-size: 28px;
  color: #4080ff;
  flex-shrink: 0;
}

.domain-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.domain-info strong {
  font-size: 15px;
  color: #1e293b;
}

.domain-info span {
  font-size: 12px;
  color: #94a3b8;
}

.file-browser-body {
  display: flex;
  gap: 12px;
  height: 70vh;
  overflow: hidden;
}

.file-tree-panel {
  width: 280px;
  flex-shrink: 0;
  overflow: auto;
  padding: 10px;
  background: #1a2332;
  border: 1px solid #334155;
  border-radius: 8px;
}

.file-scope-tabs {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid #334155;
}

.file-scope-tabs .el-button {
  padding: 4px 8px;
}

.file-tree-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #94a3b8;
  font-size: 12px;
  margin-bottom: 8px;
}

.file-tree-panel :deep(.el-tree) {
  background: transparent;
  color: #cbd5e1;
}

.file-tree-panel :deep(.el-tree-node__content:hover),
.file-tree-panel :deep(.el-tree-node:focus > .el-tree-node__content) {
  background: #0f1f3a;
}

.file-tree-node {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  min-width: 0;
}

.tree-file-size {
  color: #64748b;
  font-size: 10px;
  margin-left: 4px;
}

.file-preview-panel {
  flex: 1;
  min-width: 0;
  overflow: auto;
}

.file-preview-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  color: #94a3b8;
  font-size: 12px;
}

.selected-file-path {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-preview-empty {
  height: 62vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #64748b;
  background: #1a2332;
  border: 1px dashed #334155;
  border-radius: 8px;
}

.file-preview-empty i {
  font-size: 34px;
}

.image-preview-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 360px;
  background: #1a2332;
  border: 1px solid #334155;
  border-radius: 8px;
}

.image-preview {
  max-width: 100%;
  max-height: 62vh;
  object-fit: contain;
}

.pdf-preview,
.html-preview {
  width: 100%;
  height: 62vh;
  border: 1px solid #334155;
  border-radius: 8px;
  background: #fff;
}

.binary-preview {
  text-align: center;
  padding: 80px 20px;
  color: #94a3b8;
  background: #1a2332;
  border: 1px solid #334155;
  border-radius: 8px;
}

.file-preview-content {
  margin: 0;
  padding: 16px;
  background: #1a2332;
  border: 1px solid #334155;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.6;
  color: #cbd5e1;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
}

.attachments-body {
  padding: 0 18px 18px;
}

.attachment-upload {
  margin-bottom: 18px;
}

.attachment-upload :deep(.el-upload),
.attachment-upload :deep(.el-upload-dragger) {
  width: 100%;
}

.attachment-list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #334155;
}

.attachment-list {
  min-height: 160px;
}

.attachment-empty {
  padding: 28px 0;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
}

.attachment-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid #f1f5f9;
}

.attachment-item i {
  color: #4080ff;
  font-size: 18px;
}

.attachment-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.attachment-info span {
  color: #94a3b8;
  font-size: 11px;
}

.attachment-name {
  border: none;
  background: transparent;
  padding: 0;
  color: #1e293b;
  text-align: left;
  font-size: 13px;
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attachment-name:hover {
  color: #4080ff;
}

.services-body {
  padding: 0 18px 18px;
}

.service-tip {
  margin: 12px 0;
  padding: 8px 10px;
  border-radius: 6px;
  background: #f8fafc;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

.service-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 120px;
}

.service-empty {
  padding: 24px 0;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
}

.service-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
  padding: 10px;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  background: #fff;
}

.service-main {
  flex: 1;
  min-width: 0;
}

.service-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;
  color: #1e293b;
  margin-bottom: 4px;
}

.service-submeta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 5px;
  color: #64748b;
  font-size: 11px;
}

.service-url {
  display: block;
  color: #4080ff;
  font-size: 13px;
  text-decoration: none;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.service-command {
  margin-top: 4px;
  color: #64748b;
  font-size: 11px;
  font-family: Consolas, monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.service-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.service-stop-btn {
  color: #f56c6c;
}

.service-logs-dialog .el-dialog__body {
  padding: 14px 18px 18px;
}

.service-logs-meta {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

.service-log-section + .service-log-section {
  margin-top: 12px;
}

.service-log-title {
  font-size: 12px;
  font-weight: 700;
  color: #475569;
  margin-bottom: 5px;
}

.service-log-section pre {
  margin: 0;
  padding: 10px;
  min-height: 90px;
  max-height: 240px;
  overflow: auto;
  border-radius: 7px;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
}
</style>

<style>
/* 新建会话弹窗圆角 */
.create-conv-dialog {
  border-radius: 16px !important;
  overflow: hidden;
}
.create-conv-dialog .el-dialog__header {
  padding: 20px 24px 0;
}
.create-conv-dialog .el-dialog__title {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
}
.create-conv-dialog .el-dialog__body {
  padding: 16px 24px 10px;
  max-height: 68vh;
  overflow-y: auto;
}
.create-conv-dialog .el-dialog__body::-webkit-scrollbar {
  width: 5px;
}
.create-conv-dialog .el-dialog__body::-webkit-scrollbar-thumb {
  background: #d0d5dd;
  border-radius: 4px;
}
.create-conv-dialog .el-dialog__footer {
  padding: 0 24px 20px;
  border-top: none;
}

.file-preview-dialog .el-dialog__header {
  background: #1e293b;
  border-bottom: 1px solid #334155;
}

.file-preview-dialog .el-dialog__title {
  color: #e2e8f0;
  font-size: 14px;
}

.file-preview-dialog .el-dialog__body {
  background: #0f172a;
  padding: 16px;
}

.file-preview-dialog .el-dialog__headerbtn .el-dialog__close {
  color: #64748b;
}
</style>
