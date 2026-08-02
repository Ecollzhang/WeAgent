<template>
  <div class="req-detail-page">
    <AppSidebar />
    <main class="req-detail-content">
      <!-- 顶部导航 -->
      <header class="detail-topbar">
        <div class="topbar-left">
          <el-button type="text" icon="el-icon-arrow-left" @click="goBack">返回</el-button>
          <div class="topbar-id">
            <span class="id-label">{{ req.id ? req.id.substring(0,8) : '' }}</span>
            <el-tag :type="typeTag" size="mini" effect="plain">{{ typeLabel }}</el-tag>
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
              <h2 v-if="!editMode">{{ req.title }}</h2>
              <el-input v-else v-model="editForm.title" size="large" class="title-input" />
              <div class="priority-badge" :class="'pri-' + req.priority">{{ priorityLabel }}</div>
            </div>
          </div>

          <!-- 描述 -->
          <section class="content-section">
            <div class="section-label">
              <i class="el-icon-document"></i> 描述
            </div>
            <div v-if="!editMode" class="markdown-body desc-box" v-html="renderMarkdown(req.description || '暂无描述')"></div>
            <el-input v-else v-model="editForm.description" type="textarea" :rows="6" placeholder="需求描述 (支持 Markdown)" />
          </section>

          <!-- 验收标准 -->
          <section class="content-section">
            <div class="section-label">
              <i class="el-icon-circle-check"></i> 验收标准
            </div>
            <div v-if="!editMode" class="markdown-body acceptance" v-html="renderMarkdown(req.acceptance_criteria || '暂无验收标准')"></div>
            <el-input v-else v-model="editForm.acceptance_criteria" type="textarea" :rows="4" placeholder="验收标准 (支持 Markdown 列表)" />
          </section>

          <!-- 子需求 -->
          <section class="content-section" v-if="subRequirements.length > 0">
            <div class="section-label">
              <i class="el-icon-s-operation"></i> 子需求 ({{ subRequirements.length }})
            </div>
            <div class="subreq-list">
              <div v-for="sr in subRequirements" :key="sr.id" class="subreq-card" @click="goToRequirement(req.project_id, sr.id)">
                <span class="subreq-status" :class="'status-' + sr.status"></span>
                <span class="subreq-title">{{ sr.title }}</span>
                <el-tag size="mini" effect="plain">{{ statusLabel(sr.status) }}</el-tag>
                <span class="subreq-sp">{{ sr.story_points }} pts</span>
              </div>
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
                      <span class="wf-node-desc">{{ wfStageDesc(stage.key) }}</span>
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

          <!-- 开发进度：分支 + 提交 -->
          <section class="content-section">
            <div class="section-label">
              <i class="el-icon-share"></i> 开发进度
            </div>
            <div class="progress-block">
              <div class="progress-header">
                <span class="progress-count">{{ reqBranches.length }} 个分支</span>
                <el-button size="mini" type="primary" plain icon="el-icon-plus" @click="showCreateBranch = true">创建分支</el-button>
              </div>
              <div v-if="reqBranches.length === 0" class="progress-empty">暂无关联分支，点击创建分支开始开发</div>
              <div v-for="br in reqBranches" :key="br.id" class="branch-item">
                <div class="branch-info">
                  <i class="el-icon-share branch-icon"></i>
                  <a :href="getBranchUrl(br)" target="_blank" class="branch-name-link" :title="'在 GitHub 中查看分支'">
                    <code class="branch-name">{{ br.branch_name }}</code>
                  </a>
                  <el-tag size="mini" :type="br.status === 'merged' ? 'success' : br.status === 'active' ? 'info' : 'info'">
                    {{ br.status === 'merged' ? '已合并' : '活跃' }}
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
              <i class="el-icon-chat-line-round"></i> 评论 ({{ reqComments.length }})
            </div>
            <CommentEditor v-model="newComment" placeholder="写下你的评论... (支持 Markdown)" @submit="handleAddComment" />
            <CommentList
              :comments="reqComments"
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
              <el-option v-for="s in reqStatusFlow" :key="s" :label="reqStatusLabels[s]" :value="s" />
            </el-select>
          </div>

          <!-- 基本信息 -->
          <div class="sidebar-card">
            <div class="card-title">基本信息</div>
            <div class="info-grid">
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
                <label>类型</label>
                <el-select v-model="editForm.type" size="small" style="width:100%" @change="val => saveField('type', val)">
                  <el-option label="新功能" value="feature" />
                  <el-option label="优化增强" value="enhancement" />
                  <el-option label="问题修复" value="bugfix" />
                  <el-option label="技术债务" value="tech_debt" />
                  <el-option label="技术研究" value="research" />
                </el-select>
              </div>
              <div class="info-item">
                <label>规模点</label>
                <el-input-number v-model="editForm.story_points" :min="0" :max="100" size="small" style="width:100%" @change="val => saveField('story_points', val)" />
              </div>
              <div class="info-item">
                <label>所属迭代</label>
                <el-select v-model="editForm.iteration_id" size="small" clearable style="width:100%" placeholder="选择迭代" @change="val => saveField('iteration_id', val)">
                  <el-option v-for="i in projectIterations" :key="i.id" :label="i.name" :value="i.id" />
                </el-select>
              </div>
            </div>
          </div>

          <!-- 开发人员 -->
          <div class="sidebar-card">
            <div class="card-title">开发人员</div>
            <AssigneeSelector
              v-model="editForm.assignees"
              :developers="allDevelopers"
              :roleLabels="{primary:'主开发',reviewer:'审查',tester:'测试'}"
              @input="saveAssignees"
            />
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
                @close="editForm.labels.splice(idx,1)"
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
            <ActivityTimeline :activities="reqActivities.slice(0, 10)" :developers="allDevelopers" />
          </div>
        </aside>
      </div>
    </main>

    <!-- 创建分支弹窗 -->
    <el-dialog title="创建开发分支" :visible.sync="showCreateBranch" width="480px" :close-on-click-modal="false" @open="onBranchDialogOpen">
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
  </div>
</template>

<script>
import AppSidebar from '@/components/Sidebar/index.vue'
import AssigneeSelector from '@/components/rd/AssigneeSelector.vue'
import CommentEditor from '@/components/rd/CommentEditor.vue'
import CommentList from '@/components/rd/CommentList.vue'
import ActivityTimeline from '@/components/rd/ActivityTimeline.vue'
import { getRequirement, updateRequirement, deleteRequirement, createComment, updateComment, deleteComment, getComments, addRequirementAssignee, removeRequirementAssignee, getActivities, createBranch, deleteBranch, getProjectBranches, getRepos, getRepoBranches, getRepoCommits, getIterations } from '@/api/rd'
import { getUsers } from '@/api/auth'
import {
  developers, demoProjects, demoIterations, demoRequirements, demoBugs,
  demoBranches, demoCommits, demoRepos, demoComments, demoActivities,
} from './demoData'

const WF_STAGES = [
  { key: 'backlog', label: '待规划', icon: 'el-icon-edit-outline', order: 0, desc: '需求梳理' },
  { key: 'todo', label: '待开发', icon: 'el-icon-s-order', order: 1, desc: '准备开发' },
  { key: 'in_progress', label: '开发中', icon: 'el-icon-cpu', order: 2, desc: '编码实现' },
  { key: 'in_review', label: '审查中', icon: 'el-icon-view', order: 3, desc: '代码审查' },
  { key: 'done', label: '已完成', icon: 'el-icon-circle-check', order: 4, desc: '已交付' },
]

const STATUS_TO_ORDER = {
  backlog: 0, todo: 1,
  design: 1, testing: 3,
  in_progress: 2,
  in_review: 3,
  done: 4, closed: 4,
}

export default {
  name: 'RdRequirementDetail',
  components: { AppSidebar, AssigneeSelector, CommentEditor, CommentList, ActivityTimeline },
  data() {
    return {
      req: {},
      editMode: false,
      saving: false,
      editForm: {},
      showCreateBranch: false,
      creatingBranch: false,
      branchForm: { branch_name: '', base_branch: '', repo_id: '' },
      repoBranches: [],
      loadingBranches: false,
      showLabelInput: false,
      newLabel: '',
      newComment: '',
      allDevelopers: developers,
      allUsers: [],
      // 复制演示数据到本地响应式数组
      comments: [],
      activities: JSON.parse(JSON.stringify(demoActivities)),
      branches: [],
      branchCommits: {},
      repos: [],
      iterations: [],
      reqStatusFlow: ['backlog', 'todo', 'in_progress', 'in_review', 'done', 'closed'],
      reqStatusLabels: {
        backlog: '待规划', todo: '待办', in_progress: '进行中',
        in_review: '审查中', done: '已完成', closed: '已关闭',
      },
      wfAllStages: WF_STAGES,
    }
  },
  computed: {
    projectId() { return this.$route.params.id },
    reqId() { return this.$route.params.rid },
    currentUserId() {
      const user = JSON.parse(localStorage.getItem('user') || '{}')
      return user.id || ''
    },
    priorityLabel() {
      return ({ p0: 'P0 紧急', p1: 'P1 高', p2: 'P2 中', p3: 'P3 低' })[this.req.priority] || ''
    },
    typeLabel() {
      return ({ feature: '新功能', enhancement: '优化', bugfix: '修复', tech_debt: '技术债务', research: '研究' })[this.req.type] || ''
    },
    typeTag() {
      return ({ feature: '', enhancement: 'success', bugfix: 'warning', tech_debt: 'info', research: '' })[this.req.type] || ''
    },
    subRequirements() {
      return (demoRequirements || []).filter(r => r.parent_id === this.req.id)
    },
    reqBranches() {
      return (this.branches || []).filter(b => b.source_type === 'requirement' && b.source_id === this.req.id)
    },
    reqComments() {
      const rid = this.reqId
      console.log(this.reqId,this.comments)
      const all = (this.comments || []).filter(c =>
        c.target_type === 'requirement' && c.target_id === rid && !c.is_deleted && !c.deleted_at
      )
      console.log('[reqComments] rid:', rid, 'comments length:', (this.comments || []).length, 'filtered:', all.length)
      return this._nestComments(all)
    },
    reqActivities() {
      return (this.activities || []).filter(a => a.target_type === 'requirement' && a.target_id === this.req.id)
    },
    projectIterations() {
      return (this.iterations || []).length ? this.iterations : (demoIterations || []).filter(i => i.project_id === this.projectId)
    },
    projectRepos() {
      return (this.repos || [])
    },
    branchPrefix() {
      const sid = this.req.id ? this.req.id.replace(/-/g, '').substring(0, 6).toUpperCase() : 'XXX'
      return `feature/REQ-${sid}-`
    },
  },
  created() {
    this.loadData()
  },
  watch: {
    '$route.params.rid'() {
      this.loadData()
    },
  },
  methods: {
    async loadData() {
      // 1. 先加载用户列表（显示名字和开发者选择都需要）
      try {
        const usersRes = await getUsers()
        if (usersRes.code === 200) {
          this.allUsers = usersRes.data.items || []
          this.allDevelopers = (usersRes.data.items || []).map(u => ({
            id: u.id, name: u.username, role: u.role, avatar: u.avatar_url,
          }))
        }
      } catch (e) { /* fallback to demo */ }

      // 2. 加载需求详情
      try {
        const res = await getRequirement(this.reqId)
        if (res.code === 200 && res.data) {
          this.req = res.data
          this.editForm = JSON.parse(JSON.stringify(res.data))
          if (!this.editForm.labels) this.editForm.labels = []
          if (!this.editForm.assignees) this.editForm.assignees = []
        }
      } catch (e) {
        const req = demoRequirements.find(r => r.id === this.reqId)
        if (req) {
          this.req = JSON.parse(JSON.stringify(req))
          this.editForm = JSON.parse(JSON.stringify(req))
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

      // 3. 最后加载评论（防止异步覆盖用户新添加的评论）
      if (this.projectId && this.reqId) {
        try {
          const res = await getComments(this.projectId, { target_type: 'requirement', target_id: this.reqId })
          console.log('[loadData] getComments res:', res.code, 'items:', (res.data?.items || []).length, 'reqId:', this.reqId)
          if (res.code === 200) {
            this.comments = (res.data.items || []).map(c => ({
              ...c,
              author_name: this.getDevName(c.author_id),
              replies: (c.replies || []).map(r => ({
                ...r,
                author_name: this.getDevName(r.author_id),
              })),
            }))
            console.log('[loadData] comments set, length:', this.comments.length, 'first:', this.comments[0])
          }
        } catch (e) {
          console.error('[loadData] getComments error:', e)
        }
      }

      // 4. 加载活动日志
      if (this.projectId && this.reqId) {
        try {
          const res = await getActivities(this.projectId, { target_type: 'requirement', target_id: this.reqId })
          if (res.code === 200) {
            this.activities = (res.data.items || []).map(a => ({
              ...a,
              actor_id: a.actor_id || a.user_id,
              target_type: a.target_type || 'requirement',
              target_id: a.target_id || this.reqId,
            }))
          }
        } catch (e) {
          console.error('[loadData] getActivities error:', e)
        }
      }

      // 5. 加载分支列表
      if (this.projectId) {
        try {
          const res = await getProjectBranches(this.projectId, { source_type: 'requirement', source_id: this.reqId })
          if (res.code === 200) {
            this.branches = res.data.items || []
          }
        } catch (e) { /* fallback to demo */ }
      }

      // 5b. 加载每个分支的提交记录
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

      // 6. 加载项目关联的仓库
      if (this.projectId) {
        try {
          const res = await getRepos(this.projectId)
          if (res.code === 200) {
            this.repos = res.data.items || []
          }
        } catch (e) { /* fallback to demo */ }
      }
    },
    goBack() {
      const pId = this.projectId
      this.$router.push(`/projects/${pId}`).catch(() => {})
    },
    goToRequirement(projectId, reqId) {
      this.$router.push(`/projects/${projectId}/requirements/${reqId}`).catch(() => {})
    },
    statusLabel(s) {
      return this.reqStatusLabels[s] || s
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
    changeStatus(newStatus) {
      this.editForm.status = newStatus
      this.req.status = newStatus
      updateRequirement(this.req.id, { status: newStatus }).then(res => {
        if (res.code === 200) {
          this.$message.success('状态已更新为 ' + this.statusLabel(newStatus))
        }
      }).catch(() => {
        this.$message.error('状态更新失败')
      })
    },
    saveField(field, val) {
      this.editForm[field] = val
      this.req[field] = val
      const data = { [field]: val }
      updateRequirement(this.req.id, data).then(res => {
        if (res.code === 200) {
          this.$message.success('已更新')
        }
      }).catch(() => {
        this.$message.error('更新失败')
      })
    },

    // ── 工作流方法 ──
    wfCurrentOrder() {
      const status = this.req.status
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
    wfStageDesc(stageKey) {
      const stage = WF_STAGES.find(s => s.key === stageKey)
      return stage ? stage.desc : ''
    },
    advanceToStage(stage) {
      if (stage.order >= this.wfCurrentOrder()) {
        const orderToStatus = ['backlog', 'todo', 'in_progress', 'in_review', 'done']
        const newStatus = orderToStatus[stage.order]
        if (newStatus && newStatus !== this.req.status) {
          this.editForm.status = newStatus
          this.req.status = newStatus
          this.saveEdit()
        }
      }
    },
    saveEdit() {
      this.saving = true
      // 排除 assignees，它由 saveAssignees 单独处理
      const { assignees, ...data } = this.editForm
      updateRequirement(this.req.id, data).then(res => {
        if (res.code === 200) {
          this.req = { ...this.req, ...data }
          this.$message.success('需求已更新')
        }
        this.editMode = false
        this.saving = false
      }).catch(() => {
        this.req = { ...this.req, ...data }
        this.editMode = false
        this.saving = false
        this.$message.success('需求已更新（本地）')
      })
    },
    handleDelete() {
      this.$confirm('确定删除此需求？', '确认', { type: 'warning' }).then(() => {
        deleteRequirement(this.req.id).then(res => {
          if (res.code === 200) this.$message.success('需求已删除')
          this.goBack()
        }).catch(() => {
          this.$message.success('需求已删除（本地）')
          this.goBack()
        })
      }).catch(() => {})
    },
    handleAddComment(content) {
      if (!content.trim()) return
      const pid = this.projectId
      const rid = this.reqId
      const data = {
        target_type: 'requirement',
        target_id: rid,
        content: content.trim(),
      }
      createComment(pid, data).then(res => {
        if (res.code === 201 || res.code === 200) {
          const cm = { ...res.data, author_name: this.getDevName(res.data.author_id) }
          this.comments.unshift(cm)
          this.$message.success('评论已添加')
        } else {
          this.$message.error('评论添加失败: ' + (res.message || '未知错误'))
        }
      }).catch(err => {
        this.comments.unshift({
          id: 'cm-new-' + Date.now(),
          target_type: 'requirement', target_id: rid,
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
      const rid = this.reqId
      const data = {
        target_type: 'requirement',
        target_id: rid,
        parent_id: parentId,
        content: content.trim(),
      }
      createComment(pid, data).then(res => {
        if (res.code === 201 || res.code === 200) {
          const cm = { ...res.data, author_name: this.getDevName(res.data.author_id) }
          this.comments.push(cm)
          this.$message.success('回复已添加')
        } else {
          this.$message.error('回复添加失败: ' + (res.message || '未知错误'))
        }
      }).catch(err => {
        this.comments.push({
          id: 'cm-reply-' + Date.now(),
          target_type: 'requirement', target_id: rid,
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
    saveAssignees(assignees) {
      const oldAssignees = this.editForm.assignees || []
      const oldIds = oldAssignees.map(a => a.user_id)
      const newIds = (assignees || []).map(a => a.user_id)

      const added = (assignees || []).filter(a => !oldIds.includes(a.user_id))
      const removed = oldAssignees.filter(a => !newIds.includes(a.user_id))

      this.editForm.assignees = assignees

      const pid = this.projectId
      const promises = []
      added.forEach(a => {
        promises.push(
          addRequirementAssignee(pid, this.req.id, a.user_id, a.role || 'primary').catch(() => {})
        )
      })
      removed.forEach(a => {
        promises.push(
          removeRequirementAssignee(pid, this.req.id, a.user_id).catch(() => {})
        )
      })
      if (promises.length > 0) {
        Promise.all(promises).then(() => {
          this.$message.success('开发人员已更新')
        })
      }
    },
    addLabel() {
      const label = this.newLabel.trim()
      if (label && !this.editForm.labels.includes(label)) {
        this.editForm.labels.push(label)
      }
      this.newLabel = ''
      this.showLabelInput = false
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
    getDevName(id) {
      if (!id) return '未知用户'
      const dev = this.allDevelopers.find(d => d.id === id)
      if (dev) return dev.name
      const u = (this.allUsers || []).find(u => u.id === id)
      if (u) return u.username
      return id.substring(0, 8)
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
      const branchName = this.branchForm.branch_name || (this.branchPrefix + 'feature')
      try {
        const res = await createBranch(this.projectId, {
          branch_name: branchName,
          base_branch: this.branchForm.base_branch,
          repo_id: this.branchForm.repo_id,
          source_type: 'requirement',
          source_id: this.req.id,
        })
        if (res.code === 201) {
          this.$message.success(`分支 ${branchName} 创建成功`)
          this.showCreateBranch = false
          // 重新加载分支列表
          const brRes = await getProjectBranches(this.projectId, { source_type: 'requirement', source_id: this.req.id })
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
.req-detail-page {
  display: flex;
  gap: 12px;
  padding: 12px;
  height: 100vh;
  background: linear-gradient(135deg, #e8f0ff 0%, #f0f5ff 50%, #f5f7fa 100%);
  overflow: hidden;
}
.req-detail-content {
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

.status-flow { margin-top: 4px; }

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
.markdown-body.acceptance {
  background: #f0fdf4; border-left: 3px solid #67c23a;
  padding: 14px 18px; border-radius: 0 8px 8px 0;
}
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

/* sub requirements */
.subreq-list { display: flex; flex-direction: column; gap: 6px; }
.subreq-card {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px; background: #f8fafc; border-radius: 8px;
  cursor: pointer; transition: all 0.15s; border: 1px solid #e2e8f0;
}
.subreq-card:hover { background: #f0f5ff; border-color: #bfd4f7; }
.subreq-status { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.subreq-status.status-done, .subreq-status.status-closed { background: #67c23a; }
.subreq-status.status-in_progress { background: #409eff; }
.subreq-status.status-todo { background: #e6a23c; }
.subreq-status.status-backlog { background: #c0c4cc; }
.subreq-title { flex: 1; font-size: 13px; color: #334155; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.subreq-sp { font-size: 12px; color: #94a3b8; }

/* branches */
.progress-block { background: #f8fafc; border-radius: 10px; padding: 16px; border: 1px solid #e2e8f0; }
.progress-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.progress-count { font-size: 13px; font-weight: 600; color: #475569; }
.progress-empty { font-size: 13px; color: #94a3b8; text-align: center; padding: 20px; }
.branch-item { margin-bottom: 12px; }
.branch-info { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.branch-icon { color: #409eff; font-size: 15px; }
.branch-name { font-size: 13px; font-weight: 600; color: #1e293b; background: #e8f4fd; padding: 2px 8px; border-radius: 4px; }
.branch-name-link { text-decoration: none; }
.branch-name-link:hover .branch-name { background: #d0e8fa; color: #0d6efd; }
.branch-actions { margin-left: auto; display: flex; align-items: center; gap: 2px; }
.branch-commits { margin-left: 24px; border-left: 2px solid #e2e8f0; padding-left: 14px; }
.commit-mini { display: flex; align-items: center; gap: 8px; padding: 4px 0; font-size: 12px; }
.cm-hash { font-family: monospace; color: #409eff; font-size: 11px; }
.cm-hash-link { text-decoration: none; }
.cm-hash-link:hover .cm-hash { text-decoration: underline; color: #0d6efd; }
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
.label-chips { display: flex; flex-wrap: wrap; align-items: center; }

/* ── 工作流进度图 ── */
.workflow-box {
  background: #fafbfc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 24px 20px;
  overflow-x: auto;
}
.wf-horizontal-flow {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 600px;
}
.wf-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  width: 100px;
  flex-shrink: 0;
  cursor: pointer;
  transition: transform 0.2s;
}
.wf-node:hover {
  transform: translateY(-2px);
}
.wf-node-pending {
  opacity: 0.45;
}
.wf-node-dot {
  width: 40px; height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  background: #e2e8f0;
  color: #94a3b8;
  transition: all 0.3s;
}
.wf-node-done .wf-node-dot {
  background: #67c23a;
  color: #fff;
  box-shadow: 0 2px 8px rgba(103, 194, 58, 0.3);
}
.wf-node-active .wf-node-dot {
  background: #409eff;
  color: #fff;
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.35);
  animation: wf-pulse 2s infinite;
}
@keyframes wf-pulse {
  0%, 100% { box-shadow: 0 4px 16px rgba(64, 158, 255, 0.35); }
  50% { box-shadow: 0 4px 24px rgba(64, 158, 255, 0.55); }
}
.wf-node-info {
  text-align: center;
}
.wf-node-label {
  display: block;
  font-size: 13px;
  font-weight: 700;
  color: #475569;
}
.wf-node-done .wf-node-label { color: #67c23a; }
.wf-node-active .wf-node-label { color: #409eff; }
.wf-node-pending .wf-node-label { color: #c0c4cc; }
.wf-node-desc {
  display: block;
  font-size: 11px;
  color: #94a3b8;
  margin-top: 2px;
}
.wf-connector {
  flex: 1;
  display: flex;
  align-items: center;
  padding: 0 4px;
  padding-bottom: 28px;
  min-width: 30px;
}
.wf-conn-line {
  flex: 1;
  height: 3px;
  background: #e2e8f0;
  border-radius: 2px;
  transition: background 0.3s;
}
.wf-connector.done .wf-conn-line {
  background: #67c23a;
}
</style>
