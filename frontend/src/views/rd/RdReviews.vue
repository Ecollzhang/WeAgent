<template>
  <div class="rd-reviews-page">
    <AppSidebar />

    <main class="rd-content">
      <header class="rd-header">
        <div>
          <h2>代码审查</h2>
          <p>AI 驱动四维审查：安全、规范、逻辑、性能自动评审</p>
        </div>
        <div class="header-actions">
          <el-select v-model="projectId" placeholder="选择项目" size="small" style="width:200px" @change="onProjectChange" filterable>
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
          <el-button type="primary" icon="el-icon-plus" @click="openSubmitDialog" :disabled="!projectId">
            提交审查
          </el-button>
        </div>
      </header>

      <!-- 过滤栏 -->
      <div class="filter-bar">
        <div class="filter-row">
          <el-input
            v-model="searchQuery"
            placeholder="搜索标题、文件、总结..."
            prefix-icon="el-icon-search"
            clearable
            size="small"
            class="filter-search"
          />
          <el-select v-model="filterLanguage" placeholder="语言" size="small" clearable class="filter-sel">
            <el-option label="Vue" value="Vue" />
            <el-option label="Python" value="Python" />
            <el-option label="JavaScript" value="JavaScript" />
            <el-option label="TypeScript" value="TypeScript" />
            <el-option label="Go" value="Go" />
            <el-option label="Java" value="Java" />
          </el-select>
          <el-select v-model="filterStatus" placeholder="状态" size="small" clearable class="filter-sel">
            <el-option label="已完成" value="completed" />
            <el-option label="审查中" value="reviewing" />
            <el-option label="失败" value="failed" />
            <el-option label="待审查" value="pending" />
          </el-select>
          <el-select v-model="filterMethod" placeholder="审查方式" size="small" clearable class="filter-sel">
            <el-option label="AI 审查" value="llm" />
            <el-option label="脚本审查" value="script" />
          </el-select>
          <el-select v-model="sortBy" placeholder="排序" size="small" class="filter-sel" style="width:130px">
            <el-option label="最新优先" value="newest" />
            <el-option label="最高评分" value="score-desc" />
            <el-option label="最低评分" value="score-asc" />
            <el-option label="问题最多" value="issues-desc" />
          </el-select>
          <span class="filter-count" v-if="reviews.length">{{ filteredReviews.length }} / {{ reviews.length }} 条</span>
        </div>
      </div>

      <!-- 审查列表 -->
      <section class="reviews-list" v-loading="loading">
        <template v-if="filteredReviews.length > 0">
          <article
            v-for="review in filteredReviews"
            :key="review.id"
            class="review-card"
            @click="openDetail(review)"
          >
            <div class="review-left">
              <div class="score-ring" v-if="review.score != null" :class="scoreClass(review.score)">
                <svg width="64" height="64" viewBox="0 0 64 64">
                  <circle cx="32" cy="32" r="27" fill="none" stroke="#ebeef5" stroke-width="5" />
                  <circle
                    cx="32" cy="32" r="27"
                    fill="none"
                    :stroke="barColor(review.score)"
                    stroke-width="5"
                    stroke-linecap="round"
                    :stroke-dasharray="2 * Math.PI * 27"
                    :stroke-dashoffset="2 * Math.PI * 27 * (1 - review.score / 10)"
                    transform="rotate(-90 32 32)"
                    class="score-ring-arc"
                  />
                </svg>
                <span class="score-ring-text">{{ review.score }}</span>
              </div>
              <div class="score-ring pending" v-else>
                <svg width="64" height="64" viewBox="0 0 64 64">
                  <circle cx="32" cy="32" r="27" fill="none" stroke="#ebeef5" stroke-width="5" />
                </svg>
                <span class="score-ring-text muted">--</span>
              </div>
            </div>
            <div class="review-body">
              <div class="review-header">
                <h3>{{ review.title }}</h3>
                <div class="review-header-right">
                  <el-tag :type="review.review_method === 'llm' ? 'primary' : ''" size="small" effect="plain">
                    {{ review.review_method === 'llm' ? 'AI审查' : '脚本审查' }}
                  </el-tag>
                  <el-tag :type="statusTagType(review.status)" size="small">
                    {{ statusLabel(review.status) }}
                  </el-tag>
                  <el-button type="text" icon="el-icon-delete" size="mini" style="color:#c0c4cc;margin-left:4px" @click.stop="handleDeleteReview(review)" />
                </div>
              </div>
              <div class="review-summary" v-if="review.summary" v-html="renderSummary(review.summary)"></div>
              <div class="review-meta">
                <span><i class="el-icon-document"></i> {{ (review.file_paths || []).slice(0, 3).join(', ') }}<template v-if="(review.file_paths || []).length > 3"> +{{ review.file_paths.length - 3 }}</template></span>
                <span><i class="el-icon-time"></i> {{ formatRelative(review.created_at) }}</span>
                <span v-if="review.issues && review.issues.length" class="meta-issues">
                  <i class="el-icon-warning-outline"></i> {{ review.issues.length }} 个问题
                  <template v-if="issueBreakdown(review.issues).critical > 0">
                    <span class="sev-dot crit"></span>{{ issueBreakdown(review.issues).critical }}
                  </template>
                  <template v-if="issueBreakdown(review.issues).warning > 0">
                    <span class="sev-dot warn"></span>{{ issueBreakdown(review.issues).warning }}
                  </template>
                </span>
              </div>
              <!-- 四维评分条 -->
              <div class="score-bars" v-if="review.scores">
                <div class="score-bar-item">
                  <span class="sb-label">安全</span>
                  <div class="sb-track"><div class="sb-fill" :style="{width: (review.scores.security * 10) + '%', background: barColor(review.scores.security)}"></div></div>
                  <span class="sb-val">{{ review.scores.security }}</span>
                </div>
                <div class="score-bar-item">
                  <span class="sb-label">规范</span>
                  <div class="sb-track"><div class="sb-fill" :style="{width: (review.scores.style * 10) + '%', background: barColor(review.scores.style)}"></div></div>
                  <span class="sb-val">{{ review.scores.style }}</span>
                </div>
                <div class="score-bar-item">
                  <span class="sb-label">逻辑</span>
                  <div class="sb-track"><div class="sb-fill" :style="{width: (review.scores.logic * 10) + '%', background: barColor(review.scores.logic)}"></div></div>
                  <span class="sb-val">{{ review.scores.logic }}</span>
                </div>
                <div class="score-bar-item">
                  <span class="sb-label">性能</span>
                  <div class="sb-track"><div class="sb-fill" :style="{width: (review.scores.performance * 10) + '%', background: barColor(review.scores.performance)}"></div></div>
                  <span class="sb-val">{{ review.scores.performance }}</span>
                </div>
              </div>
            </div>
          </article>
        </template>

        <div v-else-if="reviews.length === 0" class="empty-state">
          <div class="empty-icon">
            <i class="el-icon-document-checked"></i>
          </div>
          <h3>暂无审查记录</h3>
          <p>选择项目并提交代码审查，让 AI Agent 帮你检查代码质量</p>
        </div>
        <div v-else class="empty-state">
          <div class="empty-icon">
            <i class="el-icon-search"></i>
          </div>
          <h3>没有匹配的审查记录</h3>
          <p>尝试调整搜索条件或清除筛选器</p>
        </div>
      </section>
    </main>

    <!-- ==================== 审查详情侧栏 ==================== -->
    <transition name="drawer-fade">
      <div class="drawer-backdrop" v-if="detailVisible" @click="detailVisible = false" />
    </transition>
    <transition name="drawer-slide">
      <div class="detail-drawer" v-if="detailVisible">
        <div class="drawer-header">
          <div class="drawer-header-left">
            <i class="el-icon-arrow-right" @click="detailVisible = false"></i>
            <h3>{{ selectedReview ? selectedReview.title : '' }}</h3>
          </div>
          <div class="drawer-header-actions">
            <el-tag :type="selectedReview && selectedReview.review_method === 'llm' ? 'primary' : ''" size="small" effect="plain">
              {{ selectedReview && selectedReview.review_method === 'llm' ? 'AI审查' : '脚本审查' }}
            </el-tag>
            <el-tag :type="statusTagType(selectedReview ? selectedReview.status : '')" size="small">
              {{ statusLabel(selectedReview ? selectedReview.status : '') }}
            </el-tag>
            <el-button v-if="selectedReview && selectedReview.status === 'completed'" type="text" icon="el-icon-refresh" size="small" @click="handleRetryReview">重新审查</el-button>
            <el-button v-if="selectedReview && selectedReview.status === 'completed' && selectedReview.repo_id" type="text" icon="el-icon-s-tools" size="small" @click="handleAutoFix">一键修复</el-button>
            <el-dropdown trigger="click" @command="(cmd) => { if (cmd === 'delete') { handleDeleteReview(selectedReview); detailVisible = false } }">
              <el-button type="text" icon="el-icon-more" size="small" style="color:#909399" />
              <el-dropdown-menu slot="dropdown">
                <el-dropdown-item command="delete" icon="el-icon-delete" style="color:#f56c6c">删除审查</el-dropdown-item>
              </el-dropdown-menu>
            </el-dropdown>
          </div>
        </div>

        <div class="drawer-body" v-if="selectedReview">
          <div class="rdd-meta">
            <span><i class="el-icon-document"></i> {{ (selectedReview.file_paths || []).join(', ') }}</span>
            <span><i class="el-icon-time"></i> {{ formatTime(selectedReview.created_at) }}</span>
          </div>

          <!-- 总评 -->
          <div class="rdd-overall" v-if="selectedReview.scores">
            <div class="overall-score" :class="scoreClass(selectedReview.score)">
              <div class="os-num">{{ selectedReview.score }}</div>
              <div class="os-label">总评分</div>
            </div>
            <div class="overall-dimensions">
              <div class="dim-item" v-for="dim in dimensions" :key="dim.key">
                <div class="dim-header">
                  <span class="dim-icon">{{ dim.icon }}</span>
                  <span class="dim-name">{{ dim.label }}</span>
                  <span class="dim-score">{{ selectedReview.scores[dim.key] }}</span>
                </div>
                <div class="dim-bar">
                  <div class="dim-fill" :style="{width: (selectedReview.scores[dim.key] * 10) + '%', background: dim.color}"></div>
                </div>
              </div>
            </div>
          </div>

          <!-- 代码度量 -->
          <div class="rdd-metrics" v-if="selectedReview.metrics && selectedReview.metrics.total_lines">
            <h4>代码度量</h4>
            <div class="metrics-grid">
              <div class="metric-item">
                <span class="metric-val">{{ selectedReview.metrics.total_lines }}</span>
                <span class="metric-label">总行数</span>
              </div>
              <div class="metric-item">
                <span class="metric-val">{{ selectedReview.metrics.code_lines }}</span>
                <span class="metric-label">有效代码行</span>
              </div>
              <div class="metric-item">
                <span class="metric-val">{{ selectedReview.metrics.comment_ratio }}%</span>
                <span class="metric-label">注释率</span>
              </div>
              <div class="metric-item">
                <span class="metric-val">{{ selectedReview.metrics.functions }}</span>
                <span class="metric-label">函数/方法</span>
              </div>
              <div class="metric-item">
                <span class="metric-val">{{ selectedReview.metrics.classes }}</span>
                <span class="metric-label">类/结构体</span>
              </div>
              <div class="metric-item" v-if="selectedReview.metrics.max_indent_level">
                <span class="metric-val">{{ selectedReview.metrics.max_indent_level }}层</span>
                <span class="metric-label">最大嵌套</span>
              </div>
            </div>
          </div>

          <div class="rdd-summary" v-if="selectedReview.summary">
            <h4>审查总结</h4>
            <div class="summary-text" v-html="renderSummary(selectedReview.summary)"></div>
          </div>

          <!-- 问题列表 -->
          <div class="rdd-issues" v-if="selectedReview.issues && selectedReview.issues.length">
            <h4>发现问题（{{ selectedReview.issues.length }}）</h4>
            <div class="issue-card" v-for="issue in selectedReview.issues" :key="issue.id" :class="'issue-sev-' + (issue.severity || 'warning')">
              <div class="issue-header">
                <el-tag :type="issue.severity === 'critical' ? 'danger' : issue.severity === 'warning' ? 'warning' : 'info'" size="small">
                  {{ issue.severity === 'critical' ? '严重' : issue.severity === 'warning' ? '警告' : '建议' }}
                </el-tag>
                <span class="issue-category">{{ categoryLabel(issue.category) }}</span>
                <span class="issue-location" v-if="issue.file_path">
                  <i class="el-icon-document"></i> {{ issue.file_path }}<template v-if="issue.line_start">:{{ issue.line_start }}</template>
                </span>
              </div>
              <h5 class="issue-title">{{ issue.title }}</h5>
              <p class="issue-desc" v-if="issue.description">{{ issue.description }}</p>
              <div class="issue-analysis" v-if="issue.analysis">
                <h6>深度分析</h6>
                <p>{{ issue.analysis }}</p>
              </div>
              <div class="issue-fix" v-if="issue.suggestion">
                <h6>修复建议</h6>
                <p>{{ issue.suggestion }}</p>
              </div>
              <div class="issue-context" v-if="(issue.context_before && issue.context_before.length) || (issue.context_after && issue.context_after.length)">
                <div class="code-label">相关上下文</div>
                <pre><code><template v-for="cb in (issue.context_before || [])">{{ cb.line }}: {{ cb.code }}
</template><span class="hl-line">{{ issue.line_start }}: {{ issue.code_snippet }}</span>
<template v-for="ca in (issue.context_after || [])">{{ ca.line }}: {{ ca.code }}
</template></code></pre>
              </div>
              <div class="issue-code" v-else-if="issue.code_snippet">
                <div class="code-label">问题代码</div>
                <pre><code>{{ issue.code_snippet }}</code></pre>
              </div>
              <div class="issue-code fixed" v-if="issue.fixed_snippet">
                <div class="code-label">建议修复</div>
                <pre><code>{{ issue.fixed_snippet }}</code></pre>
              </div>
            </div>
          </div>
        </div>
        <div class="drawer-empty" v-else>
          <i class="el-icon-loading"></i>
          <p>加载中...</p>
        </div>
      </div>
    </transition>

    <!-- ==================== 提交审查弹窗 ==================== -->
    <el-dialog title="提交代码审查" :visible.sync="showSubmitReview" width="700px" :close-on-click-modal="false">
      <el-form :model="reviewForm" label-width="80px">
        <el-form-item label="审查标题" required>
          <el-input v-model="reviewForm.title" placeholder="如：审查反馈表单组件 / 审查提交 abc1234" />
        </el-form-item>
        <el-form-item label="审查方式">
          <el-radio-group v-model="reviewForm.method">
            <el-radio label="script">脚本审查</el-radio>
            <el-radio label="llm">AI 审查</el-radio>
          </el-radio-group>
          <div class="method-hint">
            <template v-if="reviewForm.method === 'script'">
              <i class="el-icon-info"></i> 基于规则模式（安全/规范/逻辑/性能），即时完成，无需配置
            </template>
            <template v-else>
              <i class="el-icon-info"></i> 使用你在"设置 → 模型设置"中配置的模型和 API Key
            </template>
          </div>
        </el-form-item>
        <el-form-item label="审查内容">
          <el-radio-group v-model="reviewForm.mode">
            <el-radio label="paste">粘贴代码</el-radio>
            <el-radio label="repo">选择文件</el-radio>
            <el-radio label="commit">审查提交</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 粘贴代码模式 -->
        <el-form-item label="代码内容" v-if="reviewForm.mode === 'paste'">
          <el-input v-model="reviewForm.code" type="textarea" :rows="12" placeholder="粘贴要审查的代码..." />
        </el-form-item>

        <!-- 文件模式 -->
        <template v-if="reviewForm.mode === 'repo'">
          <el-form-item label="选择仓库">
            <el-select v-model="reviewForm.repoId" placeholder="选择代码仓库" style="width:100%" @change="onReviewRepoChange" filterable>
              <el-option v-for="r in repos" :key="r.id" :label="r.full_name || r.repo_name" :value="r.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="选择文件" v-if="reviewForm.repoId">
            <el-select v-model="reviewForm.files" multiple placeholder="选择要审查的文件" style="width:100%" @change="onReviewFilesChange" :loading="loadingTree">
              <el-option v-for="f in repoFileOptions" :key="f.path" :label="f.path" :value="f.path" />
            </el-select>
          </el-form-item>
        </template>

        <!-- 提交审查模式 -->
        <template v-if="reviewForm.mode === 'commit'">
          <el-form-item label="选择仓库">
            <el-select v-model="reviewForm.repoId" placeholder="选择代码仓库" style="width:100%" @change="onCommitRepoChange" filterable>
              <el-option v-for="r in repos" :key="r.id" :label="r.full_name || r.repo_name" :value="r.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="选择分支" v-if="reviewForm.repoId">
            <el-select v-model="reviewForm.branch" placeholder="选择分支" style="width:100%" @change="onCommitBranchChange" :loading="loadingBranches">
              <el-option v-for="b in repoBranches" :key="b.name" :label="b.name" :value="b.name" />
            </el-select>
          </el-form-item>
          <el-form-item label="选择提交" v-if="reviewForm.branch">
            <el-select v-model="reviewForm.commitSha" placeholder="选择要审查的提交" style="width:100%" @change="onCommitSelect" :loading="loadingCommits" filterable>
              <el-option v-for="c in repoCommits" :key="c.sha" :label="c.sha.substring(0,8) + ' ' + c.message" :value="c.sha">
                <span style="font-family:monospace;font-weight:600">{{ c.sha.substring(0, 8) }}</span>
                <span style="margin-left:8px;color:#606266">{{ c.message }}</span>
                <span style="float:right;color:#909399;font-size:11px">{{ c.author.name }}</span>
              </el-option>
            </el-select>
          </el-form-item>
          <!-- 显示 diff 摘要 -->
          <el-form-item label="变更概览" v-if="diffFiles.length > 0">
            <div class="diff-summary">
              <div class="diff-stats">
                <span class="diff-stat add">+{{ diffStats.additions }}</span>
                <span class="diff-stat del">-{{ diffStats.deletions }}</span>
                <span class="diff-stat">{{ diffFiles.length }} 个文件</span>
              </div>
              <div class="diff-file-list">
                <div v-for="f in diffFiles.slice(0, 10)" :key="f.filename" class="diff-file-item">
                  <span :class="'file-status ' + f.status">{{ {modified:'M',added:'A',removed:'D',renamed:'R'}[f.status] || f.status }}</span>
                  <span class="file-name">{{ f.filename }}</span>
                  <span class="file-changes">+{{ f.additions }}/-{{ f.deletions }}</span>
                </div>
                <div v-if="diffFiles.length > 10" class="diff-more">... 还有 {{ diffFiles.length - 10 }} 个文件</div>
              </div>
            </div>
          </el-form-item>
        </template>

        <el-form-item label="语言">
          <el-select v-model="reviewForm.language" placeholder="自动检测" clearable style="width:100%">
            <el-option label="Vue" value="Vue" />
            <el-option label="Python" value="Python" />
            <el-option label="JavaScript" value="JavaScript" />
            <el-option label="TypeScript" value="TypeScript" />
            <el-option label="Go" value="Go" />
            <el-option label="Java" value="Java" />
          </el-select>
        </el-form-item>
      </el-form>
      <span slot="footer">
        <el-button @click="showSubmitReview = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitReview" :loading="submitting">提交审查</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import AppSidebar from '@/components/Sidebar/index.vue'
import {
  getProjects, getRepos, getRepoTree, getRepoFile,
  getRepoBranches, getRepoCommits, getCommitDiff,
  getReviews, createReview, deleteReview, retryReview, autoFixReview,
} from '@/api/rd'

function mapReview(r) {
  return {
    ...r,
    score: r.overall_score != null ? r.overall_score : r.score,
  }
}

export default {
  name: 'RdReviews',
  components: { AppSidebar },
  data() {
    return {
      loading: false,
      submitting: false,
      loadingTree: false,
      loadingBranches: false,
      loadingCommits: false,
      showSubmitReview: false,
      detailVisible: false,
      selectedReview: null,
      reviews: [],
      projects: [],
      projectId: '',
      repos: [],
      // 过滤 & 排序
      searchQuery: '',
      filterLanguage: '',
      filterStatus: '',
      filterMethod: '',
      sortBy: 'newest',
      repoFileOptions: [],
      repoBranches: [],
      repoCommits: [],
      diffContent: '',
      diffFiles: [],
      diffStats: { additions: 0, deletions: 0 },
      commitInfo: null,
      reviewForm: {
        title: '', method: 'script', mode: 'paste', code: '', files: [],
        language: '', repoId: '', branch: '', commitSha: '',
      },
      dimensions: [
        { key: 'security', label: '安全审查', icon: '\u{1F512}', color: '#f56c6c' },
        { key: 'style', label: '规范审查', icon: '\u{1F4CF}', color: '#409eff' },
        { key: 'logic', label: '逻辑审查', icon: '\u{1F9E0}', color: '#e6a23c' },
        { key: 'performance', label: '性能审查', icon: '\u{26A1}', color: '#67c23a' },
      ],
    }
  },
  computed: {
    filteredReviews() {
      let list = [...this.reviews]

      // 搜索过滤
      const q = this.searchQuery.trim().toLowerCase()
      if (q) {
        list = list.filter(r => {
          return (
            (r.title || '').toLowerCase().includes(q) ||
            (r.summary || '').toLowerCase().includes(q) ||
            (r.file_paths || []).some(f => f.toLowerCase().includes(q))
          )
        })
      }

      // 语言过滤
      if (this.filterLanguage) {
        list = list.filter(r => (r.language || '') === this.filterLanguage)
      }

      // 状态过滤
      if (this.filterStatus) {
        list = list.filter(r => (r.status || '') === this.filterStatus)
      }

      // 审查方式过滤
      if (this.filterMethod) {
        list = list.filter(r => (r.review_method || 'script') === this.filterMethod)
      }

      // 排序
      if (this.sortBy === 'score-desc') {
        list.sort((a, b) => (b.score ?? -1) - (a.score ?? -1))
      } else if (this.sortBy === 'score-asc') {
        list.sort((a, b) => (a.score ?? 11) - (b.score ?? 11))
      } else if (this.sortBy === 'issues-desc') {
        list.sort((a, b) => (b.issues?.length || 0) - (a.issues?.length || 0))
      } else {
        // newest
        list.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
      }

      return list
    },
  },
  async created() {
    await this.loadProjects()
  },
  methods: {
    async loadProjects() {
      try {
        const res = await getProjects()
        if (res.code === 200) {
          this.projects = res.data.items || []
          if (this.projects.length > 0 && !this.projectId) {
            this.projectId = this.projects[0].id
            await this.loadReviews()
          }
        }
      } catch (e) {
        console.error('加载项目列表失败', e)
      }
    },

    async onProjectChange(pid) {
      this.projectId = pid
      this.reviews = []
      if (pid) {
        await this.loadReviews()
        await this.loadRepos()
      }
    },

    async loadReviews() {
      if (!this.projectId) return
      this.loading = true
      try {
        const res = await getReviews(this.projectId)
        if (res.code === 200) {
          this.reviews = (res.data.items || []).map(mapReview)
        }
      } catch (e) {
        console.error('加载审查列表失败', e)
        this.$message.error('加载审查列表失败')
      } finally {
        this.loading = false
      }
    },

    async loadRepos() {
      if (!this.projectId) return
      try {
        const res = await getRepos(this.projectId)
        if (res.code === 200) {
          this.repos = res.data.items || []
        }
      } catch (e) {
        console.error('加载仓库列表失败', e)
      }
    },

    async onReviewRepoChange(repoId) {
      this.reviewForm.files = []
      this.repoFileOptions = []
      if (!repoId) return
      this.loadingTree = true
      try {
        const res = await getRepoTree(repoId)
        if (res.code === 200) {
          this.repoFileOptions = (res.data.items || [])
            .filter(f => f.type === 'blob' || f.type === 'file')
            .map(f => ({ path: f.path }))
        }
      } catch (e) {
        console.error('加载文件树失败', e)
        this.$message.error('加载文件树失败')
      } finally {
        this.loadingTree = false
      }
    },

    async onReviewFilesChange(files) {
      // When files are selected in repo mode, load their content
      if (!files || files.length === 0) return
      const repoId = this.reviewForm.repoId
      if (!repoId) return
      // Load content for each selected file
      const contents = []
      for (const fpath of files) {
        try {
          const res = await getRepoFile(repoId, { path: fpath })
          if (res.code === 200) {
            const data = res.data
            const content = data.content || ''
            contents.push(`// === ${fpath} ===\n${content}`)
          }
        } catch (e) {
          console.error(`加载文件 ${fpath} 失败`, e)
        }
      }
      this.reviewForm.code = contents.join('\n\n')
    },

    // ── Commit review ──
    async onCommitRepoChange(repoId) {
      this.reviewForm.branch = ''
      this.reviewForm.commitSha = ''
      this.repoBranches = []
      this.repoCommits = []
      this.diffContent = ''
      this.diffFiles = []
      this.diffStats = { additions: 0, deletions: 0 }
      if (!repoId) return
      this.loadingBranches = true
      try {
        const res = await getRepoBranches(repoId)
        if (res.code === 200) {
          this.repoBranches = res.data.items || []
        }
      } catch (e) {
        console.error('加载分支失败', e)
      } finally {
        this.loadingBranches = false
      }
    },

    async onCommitBranchChange(branch) {
      this.reviewForm.commitSha = ''
      this.repoCommits = []
      this.diffContent = ''
      this.diffFiles = []
      this.diffStats = { additions: 0, deletions: 0 }
      if (!branch) return
      this.loadingCommits = true
      try {
        const res = await getRepoCommits(this.reviewForm.repoId, { branch, per_page: 30 })
        if (res.code === 200) {
          this.repoCommits = res.data.items || []
        }
      } catch (e) {
        console.error('加载提交记录失败', e)
      } finally {
        this.loadingCommits = false
      }
    },

    async onCommitSelect(sha) {
      if (!sha) return
      this.loadingCommits = true
      try {
        const res = await getCommitDiff(this.reviewForm.repoId, sha)
        if (res.code === 200) {
          const d = res.data
          this.diffContent = d.diff || ''
          this.diffFiles = d.files || []
          this.commitInfo = d.commit || null
          this.diffStats = d.stats || { additions: 0, deletions: 0 }
          this.reviewForm.code = this.diffContent
          if (!this.reviewForm.title) {
            const msg = (d.commit?.message || '').split('\n')[0]
            this.reviewForm.title = `审查提交：${sha.substring(0, 8)} ${msg}`
          }
        }
      } catch (e) {
        console.error('加载提交 diff 失败', e)
        this.$message.error('加载提交 diff 失败')
      } finally {
        this.loadingCommits = false
      }
    },

    // ── Actions ──
    statusTagType(status) {
      if (status === 'completed') return 'success'
      if (status === 'reviewing') return 'warning'
      if (status === 'failed') return 'danger'
      return 'info'
    },
    statusLabel(status) {
      if (status === 'completed') return '已完成'
      if (status === 'reviewing') return '审查中'
      if (status === 'failed') return '失败'
      return '待审查'
    },
    scoreClass(score) {
      if (score == null) return ''
      if (score >= 8) return 'score-good'
      if (score >= 6) return 'score-ok'
      return 'score-bad'
    },
    barColor(score) {
      if (score >= 8) return '#67c23a'
      if (score >= 6) return '#e6a23c'
      return '#f56c6c'
    },
    issueBreakdown(issues) {
      const counts = { critical: 0, warning: 0, suggestion: 0 }
      for (const iss of issues) {
        const sev = iss.severity || 'warning'
        if (counts[sev] != null) counts[sev]++
      }
      return counts
    },
    categoryLabel(c) {
      return { security: '安全', style: '规范', logic: '逻辑', performance: '性能' }[c] || c
    },
    formatRelative(iso) {
      if (!iso) return ''
      const diff = Date.now() - new Date(iso).getTime()
      const days = Math.floor(diff / 86400000)
      if (days < 1) return '今天'
      if (days < 2) return '昨天'
      if (days < 30) return days + ' 天前'
      return Math.floor(days / 30) + ' 月前'
    },
    formatTime(iso) {
      if (!iso) return ''
      const d = new Date(iso)
      return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0') + ' ' + String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0')
    },
    renderSummary(text) {
      if (!text) return ''
      const escaped = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
      // Split into blocks by double newlines
      const blocks = escaped.split(/\n\n+/)
      return blocks.map(block => {
        const lines = block.split('\n')
        let result = ''
        let inList = false

        for (let i = 0; i < lines.length; i++) {
          let line = lines[i].trim()
          if (!line) continue

          // Headings
          if (/^## (.+)$/.test(line)) {
            if (inList) { result += '</ul>'; inList = false }
            result += `<h5 class="ss-h5">${line.replace(/^## /, '')}</h5>`
            continue
          }
          // List items
          if (/^- (.+)$/.test(line)) {
            if (!inList) { result += '<ul>'; inList = true }
            const item = line.replace(/^- /, '')
            result += `<li>${this._renderInline(item)}</li>`
            continue
          }
          // Non-list line: close list if open
          if (inList) { result += '</ul>'; inList = false }
          result += `<p>${this._renderInline(line)}</p>`
        }
        if (inList) { result += '</ul>' }
        return result
      }).join('')
    },
    _renderInline(text) {
      return text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    },

    openDetail(review) {
      this.selectedReview = { ...review }
      this.detailVisible = true
    },

    async openSubmitDialog() {
      this.reviewForm = {
        title: '', method: 'script', mode: 'paste', code: '', files: [],
        language: '', repoId: '', branch: '', commitSha: '',
      }
      this.repoFileOptions = []
      this.repoBranches = []
      this.repoCommits = []
      this.diffContent = ''
      this.diffFiles = []
      this.diffStats = { additions: 0, deletions: 0 }
      this.commitInfo = null
      if (this.repos.length === 0) await this.loadRepos()
      this.showSubmitReview = true
    },

    async handleSubmitReview() {
      if (!this.reviewForm.title) return this.$message.warning('请输入审查标题')

      const mode = this.reviewForm.mode
      if (mode === 'paste' && !this.reviewForm.code.trim()) {
        return this.$message.warning('请粘贴要审查的代码')
      }
      if (mode === 'repo' && this.reviewForm.files.length === 0) {
        return this.$message.warning('请选择要审查的文件')
      }
      if (mode === 'commit' && !this.diffContent) {
        return this.$message.warning('请选择要审查的提交')
      }

      this.submitting = true
      try {
        const payload = {
          title: this.reviewForm.title,
          language: this.reviewForm.language || '',
          review_method: this.reviewForm.method || 'script',
        }

        if (mode === 'commit') {
          payload.review_type = 'commit'
          payload.diff_content = this.diffContent
          payload.diff_files = this.diffFiles
          payload.commit_info = this.commitInfo || {}
          payload.commit_sha = this.reviewForm.commitSha
          payload.file_paths = this.diffFiles.map(f => f.filename)
          payload.repo_id = this.reviewForm.repoId
          payload.branch = this.reviewForm.branch
        } else if (mode === 'repo') {
          payload.code_content = this.reviewForm.code
          payload.file_paths = this.reviewForm.files
          payload.repo_id = this.reviewForm.repoId
          payload.branch = this.reviewForm.branch || ''
        } else {
          payload.code_content = this.reviewForm.code
          payload.file_paths = ['粘贴代码']
        }

        const res = await createReview(this.projectId, payload)
        if (res.code === 201) {
          this.$message.success('审查完成')
          this.showSubmitReview = false
          this.reviews.unshift(mapReview(res.data))
        } else {
          this.$message.error(res.message || '审查失败')
        }
      } catch (e) {
        console.error('提交审查失败', e)
        this.$message.error('提交审查失败：' + (e.response?.data?.message || e.message))
      } finally {
        this.submitting = false
      }
    },

    async handleDeleteReview(review) {
      try {
        await this.$confirm('确定删除该审查记录吗？', '确认删除', { type: 'warning' })
      } catch { return }
      try {
        const res = await deleteReview(review.id)
        if (res.code === 200) {
          this.reviews = this.reviews.filter(r => r.id !== review.id)
          this.$message.success('已删除')
        } else {
          this.$message.error(res.message || '删除失败')
        }
      } catch (e) {
        this.$message.error('删除失败')
      }
    },

    async handleRetryReview() {
      if (!this.selectedReview) return
      try {
        const res = await retryReview(this.selectedReview.id)
        if (res.code === 200) {
          this.$message.success('重新审查完成')
          const idx = this.reviews.findIndex(r => r.id === this.selectedReview.id)
          if (idx >= 0) {
            this.$set(this.reviews, idx, mapReview(res.data))
          }
          this.selectedReview = mapReview(res.data)
        } else {
          this.$message.error(res.message || '重新审查失败')
        }
      } catch (e) {
        this.$message.error('重新审查失败')
      }
    },

    async handleAutoFix() {
      if (!this.selectedReview) return
      try {
        const res = await autoFixReview(this.selectedReview.id)
        if (res.code === 200) {
          const d = res.data
          this.$message.success(`修复分支已创建：${d.branch_name}`)
          if (d.html_url) {
            this.$notify({
              title: '分支已创建',
              message: `查看分支：${d.html_url}`,
              type: 'success',
              duration: 8000,
            })
          }
        } else {
          this.$message.error(res.message || '自动修复失败')
        }
      } catch (e) {
        this.$message.error('自动修复失败：' + (e.response?.data?.message || e.message))
      }
    },
  },
}
</script>

<style scoped>
.rd-reviews-page {
  display: flex;
  gap: 12px;
  padding: 12px;
  height: 100vh;
  background: linear-gradient(135deg, #edf1f9 0%, #f3f5fa 50%, #f8f9fc 100%);
  overflow: hidden;
}
.rd-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  overflow: hidden;
}
.rd-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0;
  padding: 18px 22px;
  border-bottom: 1px solid #f0f0f0;
  min-height: 76px;
}
.rd-header h2 { margin: 0 0 4px; font-size: 20px; color: #1e293b; }
.rd-header p { margin: 4px 0 0; font-size: 13px; color: #86909c; }
.header-actions { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }

/* ========== 过滤栏 ========== */
.filter-bar {
  padding: 10px 22px;
  border-bottom: 1px solid #f0f0f0;
  background: #fafbfc;
}
.filter-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.filter-search { width: 220px; }
.filter-sel { width: 120px; }
.filter-count {
  font-size: 12px;
  color: #c0c4cc;
  white-space: nowrap;
  margin-left: auto;
}

/* ========== 审查列表 ========== */
.reviews-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px 22px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.review-card {
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e8ecf1;
  padding: 20px 22px;
  display: flex;
  gap: 20px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
}
.review-card::before {
  content: '';
  position: absolute;
  left: 0; top: 12px; bottom: 12px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: transparent;
  transition: background 0.2s;
}
.review-card:hover {
  box-shadow: 0 6px 20px rgba(0,0,0,0.07);
  transform: translateY(-2px);
  border-color: #d0d8e4;
}
.review-card:hover::before { background: #409eff; }
.review-left { flex-shrink: 0; display: flex; align-items: center; }

/* SVG 评分环 */
.score-ring {
  width: 64px; height: 64px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.score-ring svg { position: absolute; top: 0; left: 0; }
.score-ring-arc { transition: stroke-dashoffset 0.8s ease; }
.score-ring-text {
  font-size: 22px;
  font-weight: 700;
  color: #303133;
  z-index: 1;
}
.score-ring-text.muted { color: #c0c4cc; font-size: 16px; }
.score-ring.score-good .score-ring-text { color: #67c23a; }
.score-ring.score-ok .score-ring-text { color: #e6a23c; }
.score-ring.score-bad .score-ring-text { color: #f56c6c; }
.review-body { flex: 1; min-width: 0; }
.review-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.review-header h3 {
  margin: 0;
  font-size: 15px;
  color: #1a1a2e;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
}
.review-header-right { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.review-summary { font-size: 13px; color: #606266; margin: 0 0 10px; line-height: 1.5; }
.review-meta {
  display: flex;
  gap: 18px;
  font-size: 12px;
  color: #909399;
  margin-bottom: 10px;
  align-items: center;
  flex-wrap: wrap;
}
.review-meta span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.review-meta .meta-issues { color: #606266; font-weight: 500; }
.sev-dot {
  display: inline-block;
  width: 7px; height: 7px;
  border-radius: 50%;
  margin-left: 6px;
}
.sev-dot.crit { background: #f56c6c; }
.sev-dot.warn { background: #e6a23c; }

/* 四维评分条 */
.score-bars {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 5px 20px;
}
.score-bar-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}
.sb-label { width: 28px; color: #909399; font-weight: 500; }
.sb-track { flex: 1; height: 5px; background: #ebeef5; border-radius: 3px; overflow: hidden; }
.sb-fill { height: 100%; border-radius: 3px; transition: width 0.5s ease; }
.sb-val { width: 24px; font-weight: 600; color: #303133; text-align: right; font-size: 12px; }

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 72px 16px;
}
.empty-icon {
  width: 80px; height: 80px;
  margin: 0 auto 20px;
  background: linear-gradient(135deg, #f0f4ff 0%, #e8ecf5 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.empty-icon i { font-size: 36px; color: #a0aec0; }
.empty-state h3 { margin: 0 0 8px; color: #606266; font-size: 16px; font-weight: 600; }
.empty-state p { margin: 0; color: #b0b8c4; font-size: 13px; }

/* ==================== 详情侧栏 ==================== */

/* 遮罩 */
.drawer-backdrop {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.35);
  z-index: 1000;
}
.drawer-fade-enter-active, .drawer-fade-leave-active {
  transition: opacity 0.25s ease;
}
.drawer-fade-enter, .drawer-fade-leave-to { opacity: 0; }

/* 侧栏容器 */
.detail-drawer {
  position: fixed; top: 0; right: 0; bottom: 0;
  width: 720px; max-width: 92vw;
  background: #fff;
  z-index: 1001;
  display: flex;
  flex-direction: column;
  box-shadow: -8px 0 30px rgba(0,0,0,0.12);
}
.drawer-slide-enter-active, .drawer-slide-leave-active {
  transition: transform 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}
.drawer-slide-enter, .drawer-slide-leave-to { transform: translateX(100%); }

/* 侧栏头部 */
.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
  min-height: 56px;
}
.drawer-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}
.drawer-header-left i {
  font-size: 18px;
  color: #606266;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  transition: all 0.15s;
  flex-shrink: 0;
}
.drawer-header-left i:hover { background: #f0f2f5; color: #303133; }
.drawer-header-left h3 {
  margin: 0;
  font-size: 16px;
  color: #1a1a2e;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.drawer-header-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

/* 侧栏内容 */
.drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px 32px;
}
.drawer-body::-webkit-scrollbar { width: 6px; }
.drawer-body::-webkit-scrollbar-track { background: transparent; }
.drawer-body::-webkit-scrollbar-thumb { background: #c8ccd4; border-radius: 3px; }
.drawer-body::-webkit-scrollbar-thumb:hover { background: #a0a4ac; }
.drawer-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #c0c4cc;
}
.drawer-empty i { font-size: 36px; margin-bottom: 12px; }
.drawer-empty p { font-size: 14px; }

/* 元信息 */
.rdd-meta { display: flex; gap: 20px; font-size: 13px; color: #909399; margin-bottom: 20px; flex-wrap: wrap; }

/* 总评卡片 */
.rdd-overall {
  display: flex; gap: 28px; margin-bottom: 20px;
  padding: 24px; background: linear-gradient(135deg, #f8f9fc 0%, #f0f2f7 100%);
  border-radius: 14px;
  align-items: center;
}
.overall-score {
  width: 90px; height: 90px; border-radius: 50%;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center; flex-shrink: 0;
  box-shadow: 0 4px 14px rgba(0,0,0,0.06);
  position: relative;
}
.overall-score::after {
  content: '';
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  border: 3px solid transparent;
}
.overall-score.score-good { background: linear-gradient(135deg, #e8f8e8 0%, #d4f0d4 100%); }
.overall-score.score-good::after { border-color: rgba(103,194,58,0.2); }
.overall-score.score-ok { background: linear-gradient(135deg, #fdf6e8 0%, #fcefd0 100%); }
.overall-score.score-ok::after { border-color: rgba(230,162,60,0.2); }
.overall-score.score-bad { background: linear-gradient(135deg, #fde8e8 0%, #fcd0d0 100%); }
.overall-score.score-bad::after { border-color: rgba(245,108,108,0.2); }
.os-num { font-size: 30px; font-weight: 700; letter-spacing: -1px; }
.overall-score.score-good .os-num { color: #4a9e2f; }
.overall-score.score-ok .os-num { color: #d4891a; }
.overall-score.score-bad .os-num { color: #e04949; }
.os-label { font-size: 11px; color: #909399; margin-top: 2px; }
.overall-dimensions { flex: 1; display: flex; flex-direction: column; gap: 10px; justify-content: center; }
.dim-item .dim-header { display: flex; align-items: center; gap: 8px; font-size: 13px; margin-bottom: 4px; }
.dim-icon { font-size: 16px; }
.dim-name { flex: 1; color: #303133; font-weight: 500; }
.dim-score { font-weight: 600; color: #303133; font-size: 14px; }
.dim-bar { height: 6px; background: #e4e7ed; border-radius: 3px; overflow: hidden; }
.dim-fill { height: 100%; border-radius: 3px; transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1); }

/* 章节标题 */
.rdd-summary h4, .rdd-issues h4, .rdd-metrics h4 {
  font-size: 15px; color: #1a1a2e; margin: 20px 0 12px;
  padding-left: 12px; border-left: 3px solid #409eff;
  font-weight: 600;
}

/* 度量指标 */
.metrics-grid { display: flex; flex-wrap: wrap; gap: 10px; }
.metric-item {
  flex: 0 0 auto; min-width: 80px; text-align: center;
  background: linear-gradient(135deg, #f8f9fc 0%, #f3f5f9 100%);
  border-radius: 10px; padding: 12px 16px;
  border: 1px solid #ebeef5;
  transition: box-shadow 0.2s, transform 0.15s;
}
.metric-item:hover { box-shadow: 0 2px 10px rgba(0,0,0,0.05); transform: translateY(-1px); }
.metric-val { display: block; font-size: 20px; font-weight: 700; color: #1a1a2e; letter-spacing: -0.5px; }
.metric-label { display: block; font-size: 11px; color: #909399; margin-top: 3px; font-weight: 500; }

/* 摘要 — Markdown 渲染 */
.summary-text { font-size: 13px; color: #555; line-height: 1.5; }
.summary-text >>> .ss-h5 {
  font-size: 14px; color: #1a1a2e; margin: 10px 0 4px;
  padding: 4px 8px; background: #f8f9fc; border-radius: 6px;
  font-weight: 600;
}
.summary-text >>> ul { margin: 2px 0; padding-left: 18px; }
.summary-text >>> li { margin: 0; color: #555; line-height: 1.5; }
.summary-text >>> strong { color: #303133; font-weight: 600; }
.summary-text >>> p { margin: 0 0 4px; line-height: 1.5; }

/* 问题卡片 */
.issue-card {
  background: #fff; border: 1px solid #ebeef5;
  border-radius: 12px; padding: 16px 18px;
  margin-bottom: 12px;
  border-left: 4px solid #909399;
  transition: box-shadow 0.2s, border-color 0.2s, transform 0.15s;
  position: relative;
}
/* 严重程度左边界颜色 — 由内联 style 或 class 控制 */
.issue-card:hover {
  box-shadow: 0 3px 14px rgba(0,0,0,0.08);
  transform: translateX(2px);
}
.issue-sev-critical { border-left-color: #f56c6c; }
.issue-sev-warning { border-left-color: #e6a23c; }
.issue-sev-suggestion { border-left-color: #409eff; }
.issue-header { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.issue-category { font-size: 12px; color: #909399; background: #f5f7fa; padding: 2px 8px; border-radius: 4px; }
.issue-location { font-size: 12px; color: #606266; font-family: 'Consolas', monospace; }
.issue-title { margin: 0 0 8px; font-size: 15px; color: #1a1a2e; font-weight: 600; }
.issue-desc { font-size: 13px; color: #606266; margin: 0 0 8px; line-height: 1.65; }

/* 深度分析块 */
.issue-analysis { margin-top: 10px; padding: 12px 14px; background: #f0f4ff; border-radius: 8px; border-left: 3px solid #409eff; }
.issue-analysis h6 { margin: 0 0 4px; font-size: 12px; color: #409eff; font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; }
.issue-analysis p { font-size: 13px; color: #555; line-height: 1.65; margin: 0; }

/* 修复建议块 */
.issue-fix { margin-top: 10px; padding: 12px 14px; background: #f0faf2; border-radius: 8px; border-left: 3px solid #67c23a; }
.issue-fix h6 { margin: 0 0 4px; font-size: 12px; color: #67c23a; font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; }
.issue-fix p { font-size: 13px; color: #555; line-height: 1.6; margin: 0; }

/* 代码块 */
.issue-code { margin-top: 10px; }
.issue-code .code-label, .issue-context .code-label {
  font-size: 11px;
  color: #909399;
  margin-bottom: 5px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.issue-code pre, .issue-context pre {
  margin: 0; padding: 12px 16px;
  background: #1e1e2e; color: #cdd6f4;
  border-radius: 8px; font-size: 12px; line-height: 1.6;
  overflow-x: auto; font-family: 'Consolas', 'Fira Code', 'Cascadia Code', monospace;
  border: 1px solid #2a2a3e;
}
.issue-code.fixed pre {
  background: #1a2b1e;
  color: #a8d8a8;
  border-color: #2a3e2a;
}
/* 上下文代码 */
.issue-context { margin-top: 10px; }
.issue-context .hl-line {
  display: inline-block; width: 100%;
  background: rgba(245, 108, 108, 0.15); color: #f38ba8;
  border-radius: 3px; padding: 2px 0;
}

/* 卡片摘要 Markdown — 截断显示 */
.review-summary {
  font-size: 13px; color: #606266; margin: 0 0 8px; line-height: 1.45;
  max-height: 7.2em; overflow: hidden; position: relative;
}
.review-summary::after {
  content: ''; position: absolute; bottom: 0; left: 0; right: 0;
  height: 1.5em; background: linear-gradient(transparent, #fff);
}
.review-summary >>> .ss-h5 { font-size: 13px; color: #303133; margin: 3px 0 1px; font-weight: 600; }
.review-summary >>> ul { margin: 1px 0; padding-left: 16px; }
.review-summary >>> li { margin: 0; font-size: 12px; line-height: 1.45; }
.review-summary >>> strong { color: #303133; font-weight: 600; }
.review-summary >>> p { margin: 0 0 1px; line-height: 1.45; }

/* 提交 diff 摘要 */
.diff-summary {
  background: #f8f9fc;
  border-radius: 10px;
  padding: 12px 16px;
  font-size: 12px;
  border: 1px solid #ebeef5;
}
.diff-stats {
  display: flex;
  gap: 14px;
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid #ebeef5;
}
.diff-stat {
  font-weight: 600;
  color: #303133;
  font-size: 13px;
}
.diff-stat.add { color: #67c23a; }
.diff-stat.del { color: #f56c6c; }
.diff-file-list {
  max-height: 180px;
  overflow-y: auto;
}
.diff-file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 3px 0;
  font-family: 'Consolas', monospace;
  font-size: 12px;
}
.file-status {
  width: 20px; height: 18px;
  text-align: center; line-height: 18px;
  font-weight: 700;
  font-size: 10px;
  border-radius: 3px;
}
.file-status.modified { background: #fdf6e8; color: #e6a23c; }
.file-status.added { background: #e8f8e8; color: #67c23a; }
.file-status.removed { background: #fde8e8; color: #f56c6c; }
.file-status.renamed { background: #e8f0ff; color: #409eff; }
.file-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #303133; }
.file-changes { color: #909399; flex-shrink: 0; font-size: 11px; }
.diff-more { color: #c0c4cc; text-align: center; padding: 4px 0; font-style: italic; }
.method-hint { font-size: 12px; color: #909399; margin-top: 4px; line-height: 1.5; }
.method-hint i { margin-right: 4px; }

/* 列表滚动条 */
.reviews-list::-webkit-scrollbar { width: 6px; }
.reviews-list::-webkit-scrollbar-track { background: transparent; }
.reviews-list::-webkit-scrollbar-thumb { background: #d8dce4; border-radius: 3px; }
.reviews-list::-webkit-scrollbar-thumb:hover { background: #b8bcc4; }

</style>
