<template>
  <div class="bug-detail-page">
    <AppSidebar />
    <main class="bug-detail-content">
      <!-- 顶部导航 -->
      <header class="detail-topbar">
        <div class="topbar-left">
          <el-button type="text" icon="el-icon-arrow-left" @click="goBack">返回</el-button>
          <div class="topbar-id">
            <span class="id-label">{{ bug.id ? bug.id.substring(0, 8) : '' }}</span>
            <el-tag :type="severityTag" size="mini" effect="dark">{{ severityLabel }}</el-tag>
          </div>
        </div>
        <div class="topbar-actions">
          <el-button size="small" icon="el-icon-edit" @click="editMode = true" v-if="!editMode">编辑</el-button>
          <el-button size="small" type="primary" icon="el-icon-check" @click="saveEdit" v-if="editMode" :loading="saving">保存</el-button>
          <el-button size="small" icon="el-icon-share" @click="showCreateBranch = true">创建分支</el-button>
          <el-button size="small" icon="el-icon-delete" type="danger" plain @click="handleDelete">删除</el-button>
        </div>
      </header>

      <div class="detail-layout">
        <!-- 左侧主内容 -->
        <div class="detail-main">
          <!-- 标题 -->
          <div class="main-header">
            <div class="title-row">
              <h2 v-if="!editMode">{{ bug.title }}</h2>
              <el-input v-else v-model="editForm.title" size="large" class="title-input" />
              <div class="priority-badge" :class="'pri-' + bug.priority">{{ priorityLabel }}</div>
            </div>
          </div>

          <!-- 描述 -->
          <section class="content-section">
            <div class="section-label">
              <i class="el-icon-warning-outline"></i> 问题描述
            </div>
            <div v-if="!editMode" class="markdown-body desc-box" v-html="renderMarkdown(bug.description || '暂无描述')"></div>
            <el-input v-else v-model="editForm.description" type="textarea" :rows="6" placeholder="缺陷描述 (支持 Markdown)" />
          </section>

          <!-- 期望 vs 实际 -->
          <section class="content-section">
            <div class="section-label">
              <i class="el-icon-document"></i> 期望与实际行为
            </div>
            <div v-if="!editMode" class="expect-actual">
              <div class="expect-block" v-if="bug.expected_behavior">
                <div class="ea-label success">期望行为</div>
                <div class="markdown-body" v-html="renderMarkdown(bug.expected_behavior)"></div>
              </div>
              <div class="actual-block" v-if="bug.actual_behavior">
                <div class="ea-label danger">实际行为</div>
                <div class="markdown-body" v-html="renderMarkdown(bug.actual_behavior)"></div>
              </div>
              <span v-if="!bug.expected_behavior && !bug.actual_behavior" class="text-muted">暂无</span>
            </div>
            <div v-else class="edit-expect-actual">
              <el-input v-model="editForm.expected_behavior" type="textarea" :rows="3" placeholder="期望行为" style="margin-bottom:8px" />
              <el-input v-model="editForm.actual_behavior" type="textarea" :rows="3" placeholder="实际行为" />
            </div>
          </section>

          <!-- 环境信息 -->
          <section class="content-section">
            <div class="section-label">
              <i class="el-icon-monitor"></i> 环境信息
            </div>
            <div v-if="!editMode" class="env-grid">
              <div class="env-item" v-if="bug.environment">
                <label>运行环境</label>
                <span>{{ bug.environment }}</span>
              </div>
              <div class="env-item" v-if="bug.browser_info">
                <label>浏览器</label>
                <span>{{ bug.browser_info }}</span>
              </div>
              <div class="env-item" v-if="bug.os_info">
                <label>操作系统</label>
                <span>{{ bug.os_info }}</span>
              </div>
              <span v-if="!bug.environment && !bug.browser_info && !bug.os_info" class="text-muted">暂无环境信息</span>
            </div>
            <div v-else class="edit-env">
              <el-row :gutter="12">
                <el-col :span="8">
                  <label class="mini-label">运行环境</label>
                  <el-input v-model="editForm.environment" size="small" placeholder="如 production" />
                </el-col>
                <el-col :span="8">
                  <label class="mini-label">浏览器</label>
                  <el-input v-model="editForm.browser_info" size="small" placeholder="如 Chrome 120" />
                </el-col>
                <el-col :span="8">
                  <label class="mini-label">操作系统</label>
                  <el-input v-model="editForm.os_info" size="small" placeholder="如 macOS 14" />
                </el-col>
              </el-row>
            </div>
          </section>

          <!-- 附件 -->
          <section class="content-section" v-if="bug.attachments && bug.attachments.length > 0">
            <div class="section-label">
              <i class="el-icon-paperclip"></i> 附件 ({{ bug.attachments.length }})
            </div>
            <div class="attachment-list">
              <a v-for="(att, idx) in bug.attachments" :key="idx" class="attachment-item" :href="att" target="_blank">
                <i class="el-icon-link"></i>
                <span>{{ att.split('/').pop() }}</span>
              </a>
            </div>
          </section>

          <!-- 关联需求 -->
          <section class="content-section">
            <div class="section-label">
              <i class="el-icon-connection"></i> 关联需求
              <el-button type="text" size="mini" icon="el-icon-plus" @click="showLinkReq = true" style="margin-left:8px">添加</el-button>
            </div>
            <div v-if="linkedReqs.length === 0" class="text-muted" style="padding:8px 0">暂无关联需求</div>
            <div v-for="lr in linkedReqs" :key="lr.id" class="linked-card">
              <span class="linked-type">需求</span>
              <span class="linked-title" @click="goToRequirement(bug.project_id, lr.id)">{{ lr.title }}</span>
              <el-tag size="mini" effect="plain">{{ statusLabel(lr.status) }}</el-tag>
              <el-button type="text" size="mini" icon="el-icon-close" style="color:#f56c6c;margin-left:auto" @click="removeLinkedReq(lr.id)" title="取消关联"></el-button>
            </div>
          </section>

          <!-- 工作流阶段 -->
          <section class="content-section">
            <div class="section-label">
              <i class="el-icon-s-operation"></i> 工作流进度
            </div>
            <div class="workflow-box">
              <div class="wf-horizontal-flow">
                <template v-for="(stage, idx) in wfAllStages">
                  <div
                    :key="stage.key"
                    class="wf-node"
                    :class="wfNodeClass(stage)"
                    @click="advanceToStage(stage)"
                  >
                    <div class="wf-node-dot">
                      <i v-if="isWfDone(stage)" class="el-icon-check"></i>
                      <i v-else :class="stage.icon"></i>
                    </div>
                    <div class="wf-node-info">
                      <span class="wf-node-label">{{ stage.label }}</span>
                      <span class="wf-node-desc">{{ stage.desc }}</span>
                    </div>
                  </div>
                  <div
                    v-if="idx < wfAllStages.length - 1"
                    :key="'conn-' + idx"
                    class="wf-connector"
                    :class="{ done: isWfDone(wfAllStages[idx]) }"
                  >
                    <div class="wf-conn-line"></div>
                  </div>
                </template>
              </div>
            </div>
          </section>

          <!-- 修复进度：分支 + 提交 -->
          <section class="content-section" v-if="bugBranches.length > 0 || showCreateBranch">
            <div class="section-label">
              <i class="el-icon-share"></i> 修复进度
            </div>
            <div class="progress-block">
              <div class="progress-header">
                <span class="progress-count">{{ bugBranches.length }} 个分支</span>
                <el-button size="mini" type="primary" plain icon="el-icon-plus" @click="showCreateBranch = true">创建分支</el-button>
              </div>
              <div v-if="bugBranches.length === 0" class="progress-empty">暂无修复分支，点击创建分支开始修复</div>
              <div v-for="br in bugBranches" :key="br.id" class="branch-item">
                <div class="branch-info">
                  <i class="el-icon-share branch-icon bug-icon"></i>
                  <a :href="getBranchUrl(br)" target="_blank" class="branch-name-link" :title="'在 GitHub 中查看分支'">
                    <code class="branch-name">{{ br.branch_name }}</code>
                  </a>
                  <el-tag size="mini" :type="br.status === 'merged' ? 'success' : br.status === 'active' ? 'warning' : 'info'">
                    {{ br.status === 'merged' ? '已合并' : br.status === 'active' ? '活跃' : br.status }}
                  </el-tag>
                  <span class="branch-actions">
                    <el-button type="text" size="mini" icon="el-icon-document-copy" title="复制分支名" @click="copyBranchName(br.branch_name)"></el-button>
                    <el-button type="text" size="mini" icon="el-icon-delete" title="删除分支" style="color:#f56c6c" @click="handleDeleteBranch(br)"></el-button>
                  </span>
                </div>
                <div class="branch-commits">
                  <div v-for="cm in getBranchCommitsForBranch(br.id)" :key="cm.id" class="commit-mini">
                    <a :href="cm.html_url" target="_blank" class="cm-hash-link" :title="'在 GitHub 中查看提交'">
                      <code class="cm-hash">{{ cm.commit_hash.substring(0,7) }}</code>
                    </a>
                    <span class="cm-msg">{{ cm.message.split('\n')[0].substring(0, 60) }}</span>
                    <span class="cm-author">{{ cm.author_name }}</span>
                    <span class="cm-time">{{ formatRelative(cm.committed_at) }}</span>
                  </div>
                  <span v-if="getBranchCommitsForBranch(br.id).length === 0" class="no-commits">暂无提交</span>
                </div>
              </div>
            </div>
          </section>

          <!-- 评论 -->
          <section class="content-section">
            <div class="section-label">
              <i class="el-icon-chat-line-round"></i> 评论 ({{ bugComments.length }})
            </div>
            <CommentEditor v-model="newComment" placeholder="写下你的评论... (支持 Markdown)" @submit="handleAddComment" />
            <CommentList
              :comments="bugComments"
              :currentUserId="currentUserId"
              @reply="handleReply"
              @edit="handleEditComment"
              @delete="handleDeleteComment"
              class="comment-section"
            />
          </section>
        </div>

        <!-- 右侧信息面板 -->
        <aside class="detail-sidebar">
          <!-- 状态切换 -->
          <div class="sidebar-card">
            <div class="card-title">状态</div>
            <el-select v-model="editForm.status" size="small" style="width:100%" @change="val => changeStatus(val)">
              <el-option v-for="s in bugStatusFlow" :key="s" :label="bugStatusLabels[s]" :value="s" />
            </el-select>
          </div>

          <!-- 基本信息 -->
          <div class="sidebar-card">
            <div class="card-title">基本信息</div>
            <div class="info-grid">
              <div class="info-item">
                <label>严重程度</label>
                <el-select v-model="editForm.severity" size="small" style="width:100%" @change="val => saveField('severity', val)">
                  <el-option label="阻塞" value="blocker" />
                  <el-option label="致命" value="critical" />
                  <el-option label="严重" value="major" />
                  <el-option label="一般" value="minor" />
                  <el-option label="轻微" value="trivial" />
                </el-select>
              </div>
              <div class="info-item">
                <label>优先级</label>
                <el-select v-model="editForm.priority" size="small" style="width:100%" @change="val => saveField('priority', val)">
                  <el-option label="P0 紧急" value="p0" />
                  <el-option label="P1 高" value="p1" />
                  <el-option label="P2 中" value="p2" />
                  <el-option label="P3 低" value="p3" />
                </el-select>
              </div>
              <div class="info-item">
                <label>所属迭代</label>
                <el-select v-model="editForm.iteration_id" size="small" clearable style="width:100%" placeholder="选择迭代" @change="val => saveField('iteration_id', val)">
                  <el-option v-for="i in projectIterations" :key="i.id" :label="i.name" :value="i.id" />
                </el-select>
              </div>
            </div>
          </div>

          <!-- 人员分配 -->
          <div class="sidebar-card">
            <div class="card-title">人员分配</div>
            <div class="info-grid">
              <div class="info-item">
                <label>开发人员</label>
                <el-select v-model="editForm.developer_id" size="small" clearable style="width:100%" placeholder="选择开发人员" @change="val => saveField('developer_id', val)">
                  <el-option v-for="u in allDevelopers" :key="u.id" :label="u.name" :value="u.id" />
                </el-select>
              </div>
              <div class="info-item">
                <label>设计人员</label>
                <el-select v-model="editForm.designer_id" size="small" clearable style="width:100%" placeholder="选择设计人员" @change="val => saveField('designer_id', val)">
                  <el-option v-for="u in allDevelopers" :key="u.id" :label="u.name" :value="u.id" />
                </el-select>
              </div>
              <div class="info-item">
                <label>测试人员</label>
                <el-select v-model="editForm.tester_id" size="small" clearable style="width:100%" placeholder="选择测试人员" @change="val => saveField('tester_id', val)">
                  <el-option v-for="u in allDevelopers" :key="u.id" :label="u.name" :value="u.id" />
                </el-select>
              </div>
            </div>
          </div>

          <!-- 修复人员 -->
          <div class="sidebar-card">
            <div class="card-title">协作成员</div>
            <AssigneeSelector
              v-model="editForm.assignees"
              :developers="allDevelopers"
              :roleLabels="{fixer:'修复',reviewer:'审查',tester:'测试'}"
              @input="saveAssignees"
            />
          </div>

          <!-- 时间计划 -->
          <div class="sidebar-card">
            <div class="card-title">时间计划</div>
            <div class="info-grid">
              <div class="info-item">
                <label>开始日期</label>
                <el-date-picker v-model="editForm.start_date" type="date" size="small" value-format="yyyy-MM-dd" style="width:100%" placeholder="计划开始" @change="val => saveField('start_date', val)" />
              </div>
              <div class="info-item">
                <label>截止日期</label>
                <el-date-picker v-model="editForm.due_date" type="date" size="small" value-format="yyyy-MM-dd" style="width:100%" placeholder="计划完成" @change="val => saveField('due_date', val)" />
              </div>
            </div>
          </div>

          <!-- 时间记录 -->
          <div class="sidebar-card">
            <div class="card-title">时间记录</div>
            <div class="info-grid">
              <div class="info-item">
                <label>创建时间</label>
                <span class="info-value">{{ formatDate(bug.created_at) }}</span>
              </div>
              <div class="info-item" v-if="bug.fixed_at">
                <label>修复时间</label>
                <span class="info-value success">{{ formatDate(bug.fixed_at) }}</span>
              </div>
              <div class="info-item" v-if="bug.verified_at">
                <label>验证时间</label>
                <span class="info-value success">{{ formatDate(bug.verified_at) }}</span>
              </div>
            </div>
          </div>

          <!-- 标签 -->
          <div class="sidebar-card">
            <div class="card-title">标签</div>
            <div class="label-chips">
              <el-tag
                v-for="(lb, idx) in editForm.labels"
                :key="idx"
                closable
                size="small"
                effect="plain"
                style="margin:0 6px 6px 0"
                @close="removeLabel(idx)"
              >{{ lb }}</el-tag>
              <el-input
                v-if="showLabelInput"
                ref="labelInput"
                v-model="newLabel"
                size="mini"
                style="width:100px"
                @blur="addLabel"
                @keyup.enter.native="addLabel"
              />
              <el-button v-else size="mini" icon="el-icon-plus" circle @click="showLabelInput = true" />
            </div>
          </div>

          <!-- 活动日志 -->
          <div class="sidebar-card">
            <div class="card-title">活动日志</div>
            <ActivityTimeline :activities="bugActivities.slice(0, 10)" :developers="allDevelopers" />
          </div>
        </aside>
      </div>
    </main>

    <!-- 创建分支弹窗 -->
    <el-dialog title="创建修复分支" :visible.sync="showCreateBranch" width="480px" :close-on-click-modal="false" @open="onBranchDialogOpen">
      <el-form label-width="90px" size="small">
        <el-form-item label="目标仓库">
          <el-select v-model="branchForm.repo_id" style="width:100%" placeholder="选择代码仓库" @change="onRepoChange">
            <el-option v-for="r in projectRepos" :key="r.id" :label="r.full_name || r.repo_name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="基于分支">
          <el-select v-model="branchForm.base_branch" style="width:100%" :loading="loadingBranches" placeholder="先选择目标仓库">
            <el-option v-for="br in repoBranches" :key="br.name" :label="br.name" :value="br.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="分支名称">
          <el-input v-model="branchForm.branch_name" placeholder="自动生成或手动输入">
            <template slot="prepend">{{ branchPrefix }}</template>
          </el-input>
        </el-form-item>
      </el-form>
      <span slot="footer">
        <el-button size="small" @click="showCreateBranch = false">取消</el-button>
        <el-button size="small" type="primary" @click="handleCreateBranch" :loading="creatingBranch">创建分支</el-button>
      </span>
    </el-dialog>

    <!-- 关联需求弹窗 -->
    <el-dialog title="关联需求" :visible.sync="showLinkReq" width="500px" :close-on-click-modal="false">
      <el-select v-model="linkReqId" placeholder="选择要关联的需求" filterable style="width:100%" size="medium">
        <el-option v-for="r in unlinkedReqs" :key="r.id" :label="r.title" :value="r.id">
          <span>{{ r.title }}</span>
          <span style="float:right;color:#909399;font-size:12px">{{ statusLabel(r.status) }}</span>
        </el-option>
      </el-select>
      <span slot="footer">
        <el-button size="small" @click="showLinkReq = false">取消</el-button>
        <el-button size="small" type="primary" @click="handleLinkReq" :disabled="!linkReqId">关联</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import AppSidebar from '@/components/Sidebar/index.vue'
import AssigneeSelector from '@/components/rd/AssigneeSelector.vue'
import CommentEditor from '@/components/rd/CommentEditor.vue'
import CommentList from '@/components/rd/CommentList.vue'
import ActivityTimeline from '@/components/rd/ActivityTimeline.vue'
import { getBug, updateBug, deleteBug, createComment, updateComment, deleteComment, getComments, addBugAssignee, removeBugAssignee, getActivities, getRequirements, createBranch, deleteBranch, getProjectBranches, getRepos, getRepoBranches, getRepoCommits, getIterations } from '@/api/rd'
import { getUsers } from '@/api/auth'
import {
  developers, demoProjects, demoIterations, demoRequirements, demoBugs,
  demoBranches, demoCommits, demoRepos, demoComments, demoActivities,
} from './demoData'

const WF_STAGES = [
  { key: 'open', label: '待处理', icon: 'el-icon-warning-outline', order: 0, desc: '提交缺陷' },
  { key: 'confirmed', label: '已确认', icon: 'el-icon-check', order: 1, desc: '确认有效' },
  { key: 'in_progress', label: '修复中', icon: 'el-icon-cpu', order: 2, desc: '编码修复' },
  { key: 'fixed', label: '已修复', icon: 'el-icon-circle-check', order: 3, desc: '提交修复' },
  { key: 'verified', label: '已验证', icon: 'el-icon-s-check', order: 4, desc: '验证通过' },
]

const STATUS_TO_ORDER = {
  open: 0, confirmed: 1, in_progress: 2, fixed: 3, verified: 4, closed: 4, reopened: 1,
}

export default {
  name: 'RdBugDetail',
  components: { AppSidebar, AssigneeSelector, CommentEditor, CommentList, ActivityTimeline },
  data() {
    return {
      bug: {},
      editMode: false,
      saving: false,
      editForm: {},
      showCreateBranch: false,
      creatingBranch: false,
      branchForm: { branch_name: '', base_branch: '', repo_id: '' },
      repoBranches: [],
      loadingBranches: false,
      showLinkReq: false,
      linkReqId: '',
      showLabelInput: false,
      newLabel: '',
      newComment: '',
      allDevelopers: developers,
      allUsers: [],
      comments: [],
      activities: JSON.parse(JSON.stringify(demoActivities)),
      branches: [],
      branchCommits: {},
      repos: [],
      iterations: [],
      allRequirements: [],
      bugStatusFlow: ['open', 'confirmed', 'in_progress', 'fixed', 'verified', 'closed', 'reopened'],
      bugStatusLabels: {
        open: '待处理', confirmed: '已确认', in_progress: '修复中',
        fixed: '已修复', verified: '已验证', closed: '已关闭', reopened: '重新打开',
      },
      wfAllStages: WF_STAGES,
    }
  },
  computed: {
    projectId() { return this.$route.params.id },
    bugId() { return this.$route.params.bid },
    currentUserId() {
      const user = JSON.parse(localStorage.getItem('user') || '{}')
      return user.id || ''
    },
    priorityLabel() {
      return ({ p0: 'P0 紧急', p1: 'P1 高', p2: 'P2 中', p3: 'P3 低' })[this.bug.priority] || ''
    },
    severityLabel() {
      return ({ blocker: '阻塞', critical: '致命', major: '严重', minor: '一般', trivial: '轻微' })[this.bug.severity] || ''
    },
    severityTag() {
      return ({ blocker: 'danger', critical: 'danger', major: 'warning', minor: 'info', trivial: '' })[this.bug.severity] || ''
    },
    linkedReqs() {
      if (!this.bug.requirement_ids && !this.bug.requirement_id) return []
      const ids = this.bug.requirement_ids || (this.bug.requirement_id ? [this.bug.requirement_id] : [])
      const source = this.allRequirements.length > 0 ? this.allRequirements : demoRequirements
      return source.filter(r => ids.includes(r.id))
    },
    unlinkedReqs() {
      const linkedIds = this.linkedReqs.map(r => r.id)
      const source = this.allRequirements.length > 0 ? this.allRequirements : demoRequirements
      return source.filter(r => !linkedIds.includes(r.id))
    },
    bugBranches() {
      return (this.branches || []).filter(b => b.source_type === 'bug' && b.source_id === this.bug.id)
    },
    bugComments() {
      const bid = this.bugId
      const all = (this.comments || []).filter(c =>
        c.target_type === 'bug' && c.target_id === bid && !c.is_deleted && !c.deleted_at
      )
      return this._nestComments(all)
    },
    bugActivities() {
      return (this.activities || []).filter(a => a.target_type === 'bug' && a.target_id === this.bug.id)
    },
    projectIterations() {
      return (this.iterations || []).length ? this.iterations : (demoIterations || []).filter(i => i.project_id === this.projectId)
    },
    projectRepos() {
      return (this.repos || [])
    },
    branchPrefix() {
      const sid = this.bug.id ? this.bug.id.replace(/-/g, '').substring(0, 6).toUpperCase() : 'XXX'
      return `fix/BUG-${sid}-`
    },
  },
  created() {
    this.loadData()
  },
  methods: {
    getDevName(uid) {
      if (!uid) return '未知用户'
      const u = this.allUsers.find(u => u.id === uid)
      return u ? u.username : (uid.substring(0, 8))
    },
    async loadData() {
      // 1. 先加载用户列表
      try {
        const usersRes = await getUsers()
        if (usersRes.code === 200) {
          this.allUsers = usersRes.data.items || []
          this.allDevelopers = (usersRes.data.items || []).map(u => ({
            id: u.id, name: u.username, role: u.role, avatar: u.avatar_url,
          }))
        }
      } catch (e) { /* fallback to demo */ }

      // 2. 加载Bug详情
      try {
        const res = await getBug(this.bugId)
        if (res.code === 200 && res.data) {
          this.bug = res.data
          if (!this.bug.requirement_ids) this.$set(this.bug, 'requirement_ids', this.bug.requirement_id ? [this.bug.requirement_id] : [])
          this.editForm = JSON.parse(JSON.stringify(res.data))
          if (!this.editForm.labels) this.editForm.labels = []
          if (!this.editForm.assignees) this.editForm.assignees = []
        }
      } catch (e) {
        const bug = demoBugs.find(b => b.id === this.bugId)
        if (bug) {
          this.bug = JSON.parse(JSON.stringify(bug))
          if (!this.bug.requirement_ids) this.$set(this.bug, 'requirement_ids', this.bug.requirement_id ? [this.bug.requirement_id] : [])
          this.editForm = JSON.parse(JSON.stringify(bug))
          if (!this.editForm.labels) this.editForm.labels = []
          if (!this.editForm.assignees) this.editForm.assignees = []
        }
      }

      // 2.5. 加载真实迭代列表（用于所属迭代下拉）
      if (this.projectId) {
        try {
          const iterRes = await getIterations(this.projectId)
          if (iterRes.code === 200) {
            this.iterations = iterRes.data?.items || iterRes.data || []
          }
        } catch (e) { /* fallback to demo iterations */ }
      }

      // 3. 加载评论
      if (this.projectId && this.bugId) {
        try {
          const res = await getComments(this.projectId, { target_type: 'bug', target_id: this.bugId })
          if (res.code === 200) {
            this.comments = (res.data.items || []).map(c => ({
              ...c,
              author_name: this.getDevName(c.author_id),
              replies: (c.replies || []).map(r => ({
                ...r,
                author_name: this.getDevName(r.author_id),
              })),
            }))
          }
        } catch (e) { /* fallback to demo */ }
      }

      // 4. 加载活动日志
      if (this.projectId && this.bugId) {
        try {
          const res = await getActivities(this.projectId, { target_type: 'bug', target_id: this.bugId })
          if (res.code === 200) {
            this.activities = (res.data.items || []).map(a => ({
              ...a,
              actor_id: a.actor_id || a.user_id,
              target_type: a.target_type || 'bug',
              target_id: a.target_id || this.bugId,
            }))
          }
        } catch (e) {
          console.error('[loadData] getActivities error:', e)
        }
      }

      // 5. 加载项目需求列表（用于关联需求选择器）
      if (this.projectId) {
        try {
          const res = await getRequirements(this.projectId, { per_page: 200 })
          if (res.code === 200) {
            this.allRequirements = (res.data.items || []).map(r => ({
              id: r.id,
              title: r.title,
              status: r.status,
            }))
          }
        } catch (e) {
          console.error('[loadData] getRequirements error:', e)
        }
      }

      // 6. 加载分支列表
      if (this.projectId) {
        try {
          const res = await getProjectBranches(this.projectId, { source_type: 'bug', source_id: this.bugId })
          if (res.code === 200) {
            this.branches = res.data.items || []
          }
        } catch (e) { /* fallback */ }
      }

      // 6b. 加载每个分支的提交记录
      if (this.branches.length > 0) {
        for (const br of this.branches) {
          if (!br.repo_id) continue
          try {
            const cr = await getRepoCommits(br.repo_id, { branch: br.branch_name, per_page: 20 })
            if (cr.code === 200) {
              this.$set(this.branchCommits, br.id, (cr.data.items || []).map(c => ({
                id: c.sha,
                commit_hash: c.sha,
                message: c.message,
                author_name: c.author?.name || '',
                committed_at: c.author?.date || '',
                html_url: c.html_url || '#',
              })))
            }
          } catch (e) { /* ignore */ }
        }
      }

      // 7. 加载项目关联的仓库
      if (this.projectId) {
        try {
          const res = await getRepos(this.projectId)
          if (res.code === 200) {
            this.repos = res.data.items || []
          }
        } catch (e) { /* fallback */ }
      }
    },
    goBack() {
      const pId = this.projectId
      this.$router.push(`/projects/${pId}`).catch(() => {})
    },
    goToRequirement(projectId, reqId) {
      this.$router.push(`/projects/${projectId}/requirements/${reqId}`)
    },
    statusLabel(s) {
      return this.bugStatusLabels[s] || s
    },
    _nestComments(flatList) {
      const map = {}
      const roots = []
      flatList.forEach(c => { map[c.id] = { ...c, replies: [] } })
      flatList.forEach(c => {
        if (c.parent_id && map[c.parent_id]) {
          const reply = map[c.id]
          reply.reply_to_name = map[c.parent_id].author_name
          map[c.parent_id].replies.push(reply)
        } else if (!c.parent_id) {
          roots.push(map[c.id])
        }
      })
      return roots
    },
    renderMarkdown(text) {
      if (!text) return '<span class="text-muted">暂无内容</span>'

      const renderTable = (rows) => {
        if (rows.length === 0) return ''
        const parseRow = (r) => {
          return r.replace(/^\||\|$/g, '').split('|').map(c => c.trim())
        }
        let html = '<table class="md-table"><thead><tr>'
        const headerCells = parseRow(rows[0])
        headerCells.forEach(c => { html += '<th>' + c + '</th>' })
        html += '</tr></thead><tbody>'
        for (let i = 1; i < rows.length; i++) {
          html += '<tr>'
          const cells = parseRow(rows[i])
          cells.forEach(c => { html += '<td>' + c + '</td>' })
          html += '</tr>'
        }
        html += '</tbody></table>'
        return html
      }

      let html = String(text)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

      html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="code-block"><code>$2</code></pre>')
      html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')

      const lines = html.split('\n')
      const result = []
      let inTable = false
      let tableRows = []

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim()
        const isTableLine = /^\|.*\|$/.test(line) || /^\|.*\|\s*$/.test(line)
        const isSepLine = /^\|[\s\-:|]+\|$/.test(line)

        if (isTableLine && !isSepLine) {
          if (!inTable) { inTable = true; tableRows = [] }
          tableRows.push(line)
        } else if (isSepLine && inTable && tableRows.length === 1) {
          // separator row, skip
        } else {
          if (inTable && tableRows.length > 0) {
            result.push(renderTable(tableRows))
            tableRows = []
            inTable = false
          }
          if (line) { result.push(line) } else { result.push('') }
        }
      }
      if (inTable && tableRows.length > 0) {
        result.push(renderTable(tableRows))
      }

      html = result.join('\n')

      html = html.replace(/^### (.+)$/gm, '<h4 class="md-h4">$1</h4>')
      html = html.replace(/^## (.+)$/gm, '<h3 class="md-h3">$1</h3>')
      html = html.replace(/^# (.+)$/gm, '<h2 class="md-h2">$1</h2>')

      html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>')

      html = html.replace(/^- (.+)$/gm, '<li style="margin-left:16px">$1</li>')
      html = html.replace(/^\d+\. (.+)$/gm, '<li style="margin-left:16px">$1</li>')

      html = html.replace(/\n\n/g, '</p><p>')
      html = html.replace(/\n/g, '<br>')

      return html
    },

    // ── 工作流方法 ──
    wfCurrentOrder() {
      const status = this.bug.status
      return STATUS_TO_ORDER[status] != null ? STATUS_TO_ORDER[status] : 0
    },
    isWfDone(stage) {
      return stage.order < this.wfCurrentOrder()
    },
    isWfActive(stage) {
      return stage.order === this.wfCurrentOrder()
    },
    wfNodeClass(stage) {
      return {
        'wf-node-done': this.isWfDone(stage),
        'wf-node-active': this.isWfActive(stage),
        'wf-node-pending': stage.order > this.wfCurrentOrder(),
      }
    },
    advanceToStage(stage) {
      if (stage.order >= this.wfCurrentOrder()) {
        const orderToStatus = ['open', 'confirmed', 'in_progress', 'fixed', 'verified']
        const newStatus = orderToStatus[stage.order]
        if (newStatus && newStatus !== this.bug.status) {
          this.editForm.status = newStatus
          this.bug.status = newStatus
          this.saveEdit()
        }
      }
    },

    changeStatus(newStatus) {
      this.editForm.status = newStatus
      this.bug.status = newStatus
      updateBug(this.bug.id, { status: newStatus }).then(res => {
        if (res.code === 200) {
          this.$message.success('状态已更新为 ' + this.statusLabel(newStatus))
        }
      }).catch(() => {
        this.$message.error('状态更新失败')
      })
    },
    saveField(field, val) {
      this.editForm[field] = val
      this.bug[field] = val
      const data = { [field]: val }
      updateBug(this.bug.id, data).then(res => {
        if (res.code === 200) {
          this.$message.success('已更新')
        }
      }).catch(() => {
        this.$message.error('更新失败')
      })
    },
    saveEdit() {
      this.saving = true
      const { assignees, ...data } = this.editForm
      updateBug(this.bug.id, data).then(res => {
        if (res.code === 200) {
          this.bug = { ...this.bug, ...data }
          this.$message.success('缺陷已更新')
        }
        this.editMode = false
        this.saving = false
      }).catch(() => {
        this.bug = { ...this.bug, ...data }
        this.editMode = false
        this.saving = false
        this.$message.success('缺陷已更新（本地）')
      })
    },
    handleDelete() {
      this.$confirm('确定删除此缺陷？', '确认', { type: 'warning' }).then(() => {
        deleteBug(this.bug.id).then(res => {
          if (res.code === 200) this.$message.success('缺陷已删除')
          this.goBack()
        }).catch(() => {
          this.$message.success('缺陷已删除（本地）')
          this.goBack()
        })
      }).catch(() => {})
    },

    // ── 关联需求 ──
    handleLinkReq() {
      if (!this.linkReqId) return
      const source = this.allRequirements.length > 0 ? this.allRequirements : demoRequirements
      const req = source.find(r => r.id === this.linkReqId)
      if (!req) return
      const currentIds = this.bug.requirement_ids || (this.bug.requirement_id ? [this.bug.requirement_id] : [])
      if (currentIds.includes(this.linkReqId)) {
        this.$message.warning('该需求已关联')
        return
      }
      const newIds = [...currentIds, this.linkReqId]
      updateBug(this.bug.id, { requirement_ids: newIds }).then(res => {
        if (res.code === 200) {
          this.$set(this.bug, 'requirement_ids', newIds)
          this.$message.success('需求已关联')
        }
      }).catch(() => {
        this.$set(this.bug, 'requirement_ids', newIds)
        this.$message.success('需求已关联（本地）')
      })
      this.showLinkReq = false
      this.linkReqId = ''
    },
    removeLinkedReq(reqId) {
      this.$confirm('确定取消关联此需求？', '确认', { type: 'warning' }).then(() => {
        const currentIds = this.bug.requirement_ids || (this.bug.requirement_id ? [this.bug.requirement_id] : [])
        const newIds = currentIds.filter(id => id !== reqId)
        updateBug(this.bug.id, { requirement_ids: newIds }).then(res => {
          if (res.code === 200) {
            this.$set(this.bug, 'requirement_ids', newIds)
            this.$message.success('已取消关联')
          }
        }).catch(() => {
          this.$set(this.bug, 'requirement_ids', newIds)
          this.$message.success('已取消关联（本地）')
        })
      }).catch(() => {})
    },

    // ── 评论 ──
    handleAddComment(content) {
      if (!content.trim()) return
      const pid = this.projectId
      const bid = this.bugId
      const data = { target_type: 'bug', target_id: bid, content: content.trim() }
      createComment(pid, data).then(res => {
        if (res.code === 201 || res.code === 200) {
          const cm = { ...res.data, author_name: this.getDevName(res.data.author_id) }
          this.comments.unshift(cm)
          this.$message.success('评论已添加')
        } else {
          this.$message.error('评论添加失败: ' + (res.message || '未知错误'))
        }
      }).catch(() => {
        this.comments.unshift({
          id: 'cm-new-' + Date.now(),
          target_type: 'bug', target_id: bid,
          content: content.trim(), content_type: 'markdown',
          author_id: this.currentUserId, author_name: '当前用户',
          is_pinned: false, created_at: new Date().toISOString(),
        })
        this.$message.warning('评论已保存到本地（未同步到服务器，刷新后丢失）')
      })
      this.newComment = ''
    },
    handleReply(parentId, content) {
      if (!content.trim()) return
      const pid = this.projectId
      const bid = this.bugId
      const data = { target_type: 'bug', target_id: bid, parent_id: parentId, content: content.trim() }
      createComment(pid, data).then(res => {
        if (res.code === 201 || res.code === 200) {
          const cm = { ...res.data, author_name: this.getDevName(res.data.author_id) }
          this.comments.push(cm)
          this.$message.success('回复已添加')
        } else {
          this.$message.error('回复添加失败: ' + (res.message || '未知错误'))
        }
      }).catch(() => {
        this.comments.push({
          id: 'cm-reply-' + Date.now(),
          target_type: 'bug', target_id: bid,
          parent_id: parentId, content: content.trim(), content_type: 'markdown',
          author_id: this.currentUserId, author_name: '当前用户',
          is_pinned: false, created_at: new Date().toISOString(),
        })
        this.$message.warning('回复已保存到本地（未同步到服务器，刷新后丢失）')
      })
    },
    handleEditComment(commentId, content) {
      const pid = this.projectId
      updateComment(pid, commentId, { content }).then(() => {
        const cm = this.comments.find(c => c.id === commentId)
        if (cm) { cm.content = content; cm.updated_at = new Date().toISOString() }
        this.$message.success('评论已更新')
      }).catch(() => {
        const cm = this.comments.find(c => c.id === commentId)
        if (cm) { cm.content = content; cm.updated_at = new Date().toISOString() }
      })
    },
    handleDeleteComment(commentId) {
      const pid = this.projectId
      deleteComment(pid, commentId).then(() => {
        const cm = this.comments.find(c => c.id === commentId)
        if (cm) cm.deleted_at = new Date().toISOString()
        this.$message.success('评论已删除')
      }).catch(() => {
        const cm = this.comments.find(c => c.id === commentId)
        if (cm) cm.deleted_at = new Date().toISOString()
      })
    },

    // ── 标签 ──
    addLabel() {
      const label = this.newLabel.trim()
      if (label && !this.editForm.labels.includes(label)) {
        this.editForm.labels.push(label)
        this.saveField('labels', this.editForm.labels)
      }
      this.newLabel = ''
      this.showLabelInput = false
    },
    removeLabel(idx) {
      this.editForm.labels.splice(idx, 1)
      this.saveField('labels', this.editForm.labels)
    },

    saveAssignees(assignees) {
      this.editForm.assignees = assignees
    },

    formatDate(iso) {
      if (!iso) return '-'
      const d = new Date(iso)
      return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0')
    },
    formatRelative(iso) {
      if (!iso) return ''
      const diff = Date.now() - new Date(iso).getTime()
      const mins = Math.floor(diff / 60000)
      if (mins < 60) return mins + '分钟前'
      const hours = Math.floor(mins / 60)
      if (hours < 24) return hours + '小时前'
      return Math.floor(hours / 24) + '天前'
    },
    getBranchCommitsForBranch(branchId) {
      return this.branchCommits[branchId] || []
    },
    getBranchUrl(br) {
      const repo = (this.repos || []).find(r => r.id === br.repo_id)
      if (repo && repo.html_url) {
        return repo.html_url + '/tree/' + encodeURIComponent(br.branch_name)
      }
      return '#'
    },
    copyBranchName(name) {
      navigator.clipboard.writeText(name).then(() => {
        this.$message.success('分支名已复制')
      }).catch(() => {
        this.$message.error('复制失败')
      })
    },
    async handleDeleteBranch(br) {
      try {
        await this.$confirm('确定删除分支 ' + br.branch_name + ' 吗？', '确认', { type: 'warning' })
      } catch { return }
      try {
        await deleteBranch(this.projectId, br.id)
        this.branches = this.branches.filter(b => b.id !== br.id)
        this.$message.success('分支已删除')
      } catch (e) {
        this.$message.error('删除失败')
      }
    },
    onBranchDialogOpen() {
      this.branchForm = { branch_name: '', base_branch: '', repo_id: '' }
      this.repoBranches = []
    },
    async onRepoChange(repoId) {
      this.branchForm.base_branch = ''
      this.repoBranches = []
      if (!repoId) return
      this.loadingBranches = true
      try {
        const res = await getRepoBranches(repoId)
        if (res.code === 200) {
          this.repoBranches = res.data.items || []
        }
      } catch (e) { /* ignore */ }
      this.loadingBranches = false
    },
    async handleCreateBranch() {
      if (!this.branchForm.repo_id) {
        this.$message.warning('请选择目标仓库')
        return
      }
      this.creatingBranch = true
      const branchName = this.branchForm.branch_name || (this.branchPrefix + 'fix')
      try {
        const res = await createBranch(this.projectId, {
          branch_name: branchName,
          base_branch: this.branchForm.base_branch,
          repo_id: this.branchForm.repo_id,
          source_type: 'bug',
          source_id: this.bug.id,
        })
        if (res.code === 201) {
          this.$message.success(`分支 ${branchName} 创建成功`)
          this.showCreateBranch = false
          // 重新加载分支列表
          const brRes = await getProjectBranches(this.projectId, { source_type: 'bug', source_id: this.bug.id })
          if (brRes.code === 200) {
            this.branches = brRes.data.items || []
            // 为新分支加载提交记录
            for (const br of this.branches) {
              if (!br.repo_id || this.branchCommits[br.id]) continue
              try {
                const cr = await getRepoCommits(br.repo_id, { branch: br.branch_name, per_page: 20 })
                if (cr.code === 200) {
                  this.$set(this.branchCommits, br.id, (cr.data.items || []).map(c => ({
                    id: c.sha, commit_hash: c.sha, message: c.message,
                    author_name: c.author?.name || '', committed_at: c.author?.date || '',
                    html_url: c.html_url || '#',
                  })))
                }
              } catch (e) { /* ignore */ }
            }
          }
        } else {
          this.$message.error(res.message || '创建分支失败')
        }
      } catch (e) {
        this.$message.error('创建分支失败: ' + (e.message || '网络错误'))
      }
      this.creatingBranch = false
    },
  },
}
</script>

<style scoped>
.bug-detail-page {
  display: flex;
  gap: 12px;
  padding: 12px;
  height: 100vh;
  background: linear-gradient(135deg, #fef2f2 0%, #fdf6f6 50%, #f7fafc 100%);
  overflow: hidden;
}
.bug-detail-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  overflow: hidden;
}

/* top bar */
.detail-topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 22px;
  border-bottom: 1px solid #f0f0f0;
  background: #fafbfc;
  flex-shrink: 0;
}
.topbar-left { display: flex; align-items: center; gap: 12px; }
.topbar-id { display: flex; align-items: center; gap: 6px; }
.id-label { font-family: monospace; font-size: 12px; color: #909399; }
.topbar-actions { display: flex; gap: 8px; }

/* layout */
.detail-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
}
.detail-main {
  flex: 1;
  overflow-y: auto;
  padding: 24px 28px 40px;
}
.detail-sidebar {
  width: 320px;
  flex-shrink: 0;
  overflow-y: auto;
  padding: 20px 16px;
  border-left: 1px solid #f0f0f0;
  background: #fafbfc;
}

/* main header */
.main-header { margin-bottom: 24px; }
.title-row { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.title-row h2 { margin: 0; font-size: 24px; color: #1e293b; font-weight: 700; letter-spacing: -0.3px; }
.title-input { font-size: 20px; font-weight: 600; }
.priority-badge {
  padding: 4px 14px; border-radius: 20px; font-size: 12px; font-weight: 700;
  flex-shrink: 0;
}
.pri-p0 { background: #fde8e8; color: #f56c6c; }
.pri-p1 { background: #fdf6e8; color: #e6a23c; }
.pri-p2 { background: #e8f4fd; color: #409eff; }
.pri-p3 { background: #f0f2f5; color: #909399; }

/* ── 工作流 ──────────────────────────────────────── */
.workflow-box {
  background: #f8fafd;
  border: 1px solid #e8ecf1;
  border-radius: 12px;
  padding: 20px 16px;
}
.wf-horizontal-flow {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0;
}
.wf-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  flex: 1;
  position: relative;
  transition: transform 0.2s;
}
.wf-node:hover { transform: translateY(-2px); }
.wf-node-dot {
  width: 44px; height: 44px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px;
  transition: all 0.25s;
  background: #f0f2f5;
  color: #b0b8c4;
  border: 2px solid #e4e7ed;
}
.wf-node-done .wf-node-dot {
  background: #e8f5e9;
  color: #67c23a;
  border-color: #67c23a;
}
.wf-node-active .wf-node-dot {
  background: #e8f0fe;
  color: #4080ff;
  border-color: #4080ff;
  box-shadow: 0 0 0 4px rgba(64,128,255,0.12);
  animation: wfPulse 2s infinite;
}
.wf-node-pending .wf-node-dot {
  background: #fafbfc;
  color: #c8cfd8;
  border-color: #e8eaed;
}
@keyframes wfPulse {
  0%, 100% { box-shadow: 0 0 0 4px rgba(64,128,255,0.1); }
  50% { box-shadow: 0 0 0 8px rgba(64,128,255,0.05); }
}
.wf-node-info {
  display: flex; flex-direction: column; align-items: center; gap: 2px;
}
.wf-node-label {
  font-size: 12px; font-weight: 600; color: #606266;
}
.wf-node-done .wf-node-label { color: #67c23a; }
.wf-node-active .wf-node-label { color: #4080ff; }
.wf-node-pending .wf-node-label { color: #c0c4cc; }
.wf-node-desc {
  font-size: 10px; color: #909399;
}
.wf-node-pending .wf-node-desc { color: #d0d4d9; }
.wf-connector {
  flex: 0 0 40px;
  display: flex; align-items: center;
  margin-bottom: 28px;
}
.wf-conn-line {
  width: 100%; height: 2px;
  background: #e4e7ed;
  border-radius: 1px;
}
.wf-connector.done .wf-conn-line {
  background: #67c23a;
}

/* sections */
.content-section {
  margin-bottom: 28px;
  padding-bottom: 24px;
  border-bottom: 1px solid #f0f2f5;
}
.section-label {
  font-size: 13px; font-weight: 700; color: #64748b;
  text-transform: uppercase; letter-spacing: 0.5px;
  margin-bottom: 12px; display: flex; align-items: center; gap: 6px;
}
.section-label i { font-size: 15px; }

.markdown-body {
  font-size: 14px; line-height: 1.8; color: #334155;
}
.markdown-body.desc-box {
  background: #f8fafc; border: 1px solid #e8ecf1;
  border-radius: 10px; padding: 16px 20px;
}
.markdown-body p { margin: 0 0 8px; }

.code-block {
  background: #1e293b; color: #e2e8f0; padding: 14px 18px;
  border-radius: 8px; font-size: 13px; line-height: 1.6;
  font-family: 'Consolas', 'Courier New', monospace; overflow-x: auto;
  margin: 8px 0;
}
.inline-code {
  background: #f1f5f9; color: #e11d48; padding: 2px 6px;
  border-radius: 4px; font-size: 13px; font-family: 'Consolas', monospace;
}

/* markdown headings / tables — ::v-deep for v-html penetration */
::v-deep .markdown-body .md-h2 {
  font-size: 18px; font-weight: 700; color: #1e293b;
  margin: 18px 0 8px; padding-bottom: 6px;
  border-bottom: 2px solid #e2e8f0;
}
::v-deep .markdown-body .md-h3 {
  font-size: 16px; font-weight: 700; color: #334155; margin: 14px 0 6px;
}
::v-deep .markdown-body .md-h4 {
  font-size: 14px; font-weight: 700; color: #475569; margin: 10px 0 4px;
}
::v-deep .markdown-body .md-table {
  border-collapse: collapse; width: 100%; margin: 10px 0;
  font-size: 13px;
}
::v-deep .markdown-body .md-table th {
  border: 1px solid #c0ccda; background: #f0f5ff;
  padding: 8px 12px; text-align: left; font-weight: 700; color: #1e293b;
}
::v-deep .markdown-body .md-table td {
  border: 1px solid #d0d7e2; padding: 6px 12px; color: #334155;
}
::v-deep .markdown-body li {
  margin: 0 0 0 16px; line-height: 1.4;
}
::v-deep .markdown-body p {
  margin: 4px 0; line-height: 1.5;
}

/* expect vs actual */
.expect-actual { display: flex; flex-direction: column; gap: 12px; }
.expect-block, .actual-block {
  padding: 14px 18px;
  border-radius: 8px;
  border-left: 4px solid;
}
.expect-block { background: #f0fdf4; border-color: #67c23a; }
.actual-block { background: #fef2f2; border-color: #f56c6c; }
.ea-label {
  font-size: 12px; font-weight: 700; margin-bottom: 6px;
}
.ea-label.success { color: #67c23a; }
.ea-label.danger { color: #f56c6c; }

/* environment */
.env-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
.env-item {
  background: #f8fafc; border: 1px solid #e2e8f0;
  border-radius: 8px; padding: 12px 14px;
}
.env-item label { display: block; font-size: 11px; color: #94a3b8; text-transform: uppercase; margin-bottom: 4px; }
.env-item span { font-size: 13px; color: #334155; }

/* attachments */
.attachment-list { display: flex; flex-wrap: wrap; gap: 8px; }
.attachment-item {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 14px; background: #f8fafc; border: 1px solid #e2e8f0;
  border-radius: 8px; font-size: 13px; color: #409eff; text-decoration: none;
  transition: all 0.15s;
}
.attachment-item:hover { background: #e8f4fd; border-color: #409eff; }

/* linked requirement */
.linked-card {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 16px; background: #f0f5ff; border-radius: 8px;
  cursor: pointer; border: 1px solid #d0e0f7; transition: all 0.15s;
}
.linked-card:hover { background: #e0ecff; border-color: #409eff; }
.linked-type { font-size: 11px; color: #409eff; font-weight: 700; background: #d0e0f7; padding: 2px 8px; border-radius: 4px; }
.linked-title { flex: 1; font-size: 13px; color: #334155; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* branches */
.progress-block { background: #f8fafc; border-radius: 10px; padding: 16px; border: 1px solid #e2e8f0; }
.progress-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.progress-count { font-size: 13px; font-weight: 600; color: #475569; }
.progress-empty { font-size: 13px; color: #94a3b8; text-align: center; padding: 20px; }
.branch-item { margin-bottom: 12px; }
.branch-info { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.branch-icon { color: #409eff; font-size: 15px; }
.branch-icon.bug-icon { color: #f56c6c; }
.branch-name { font-size: 13px; font-weight: 600; color: #1e293b; background: #fef2f2; padding: 2px 8px; border-radius: 4px; }
.branch-name-link { text-decoration: none; }
.branch-name-link:hover .branch-name { background: #fde0e0; color: #dc3545; }
.branch-actions { margin-left: auto; display: flex; align-items: center; gap: 2px; }
.branch-commits { margin-left: 24px; border-left: 2px solid #fecaca; padding-left: 14px; }
.commit-mini { display: flex; align-items: center; gap: 8px; padding: 4px 0; font-size: 12px; }
.cm-hash { font-family: monospace; color: #f56c6c; font-size: 11px; }
.cm-hash-link { text-decoration: none; }
.cm-hash-link:hover .cm-hash { text-decoration: underline; color: #dc3545; }
.cm-msg { flex: 1; color: #475569; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cm-author { color: #64748b; }
.cm-time { color: #94a3b8; white-space: nowrap; }
.no-commits { font-size: 12px; color: #c0c4cc; padding: 8px 0; display: block; }

.comment-section { margin-top: 10px; }

/* sidebar */
.sidebar-card {
  background: #fff; border-radius: 10px; padding: 16px;
  margin-bottom: 12px; border: 1px solid #e2e8f0;
}
.sidebar-card .card-title {
  font-size: 12px; font-weight: 700; color: #94a3b8;
  text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px;
}
.info-grid { display: flex; flex-direction: column; gap: 10px; }
.info-item label {
  display: block; font-size: 12px; color: #64748b; margin-bottom: 4px;
}
.info-value { font-size: 13px; color: #606266; }
.info-value.success { color: #67c23a; }
.label-chips { display: flex; flex-wrap: wrap; align-items: center; }

.edit-expect-actual { display: flex; flex-direction: column; }
.edit-env .mini-label { display: block; font-size: 12px; color: #64748b; margin-bottom: 4px; font-weight: 500; }
</style>
