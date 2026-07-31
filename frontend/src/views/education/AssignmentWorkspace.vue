<template>
  <EducationShell
    :title="assignment ? assignment.title : '作业空间'"
    :subtitle="isTeacher ? '先看全班进度，再进入单份批改工作台' : '完成作业、保存草稿并正式提交'"
    :back-to="`/education/courses/${courseId}`"
  >
    <template #actions>
      <el-tag v-if="assignment">{{ statusLabel(assignment.status) }}</el-tag>
      <el-button
        v-if="isTeacher && assignment && assignment.status === 'draft'"
        data-testid="publish-assignment"
        type="primary"
        @click="handlePublishAssignment"
      >发布作业</el-button>
      <el-button
        v-if="isTeacher && nextReviewSubmission"
        type="primary"
        icon="el-icon-edit-outline"
        @click="openReview(nextReviewSubmission)"
      >批改下一份</el-button>
    </template>

    <el-skeleton v-if="!assignment" :rows="9" animated />

    <template v-else-if="isTeacher">
      <nav class="overview-tabs" aria-label="作业模块">
        <button
          v-for="tab in overviewTabs"
          :key="tab.key"
          type="button"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >{{ tab.label }}</button>
      </nav>

      <section v-if="activeTab === 'submissions'" class="overview-panel">
        <div
          class="overview-metrics"
          data-testid="assignment-overview-metrics"
        >
          <article v-for="metric in metricCards" :key="metric.key">
            <span>{{ metric.label }}</span>
            <b>{{ metric.value }}</b>
            <small>{{ metric.note }}</small>
          </article>
        </div>

        <div class="submission-toolbar">
          <el-input
            v-model.trim="studentQuery"
            clearable
            prefix-icon="el-icon-search"
            placeholder="搜索课程姓名"
          />
          <el-select v-model="statusFilter">
            <el-option label="全部状态" value="" />
            <el-option label="未提交" value="unsubmitted" />
            <el-option label="待批改" value="pending" />
            <el-option label="已批改" value="graded" />
            <el-option label="要求订正" value="revision_requested" />
          </el-select>
          <el-select v-model="sortMode">
            <el-option label="待批优先" value="pending" />
            <el-option label="提交时间" value="time" />
            <el-option label="姓名" value="name" />
            <el-option label="分数" value="score" />
          </el-select>
        </div>

        <el-table
          :data="filteredStudents"
          stripe
          data-testid="assignment-submission-table"
        >
          <el-table-column label="学生" min-width="150">
            <template #default="{ row }">
              <div class="student-cell">
                <span>{{ initials(row.display_name) }}</span>
                <b>{{ row.display_name }}</b>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <el-tag size="mini" :type="submissionTagType(row.status)">
                {{ submissionStatus(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="提交时间" min-width="170">
            <template #default="{ row }">{{ formatDate(row.submitted_at) }}</template>
          </el-table-column>
          <el-table-column label="版本" width="85">
            <template #default="{ row }">{{ row.version_number ? `v${row.version_number}` : '—' }}</template>
          </el-table-column>
          <el-table-column label="内容" width="120">
            <template #default="{ row }">
              {{ row.word_count }} 字 · {{ row.artifact_count }} 附件
            </template>
          </el-table-column>
          <el-table-column label="得分" width="90">
            <template #default="{ row }">{{ scoreLabel(row.score) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="130" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="row.submission_id"
                type="text"
                @click="openReview(row)"
              >{{ row.status === 'graded' ? '查看批改' : '开始批改' }}</el-button>
              <el-button v-else type="text" @click="remindStudent(row)">提醒</el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <section v-else-if="activeTab === 'content'" class="overview-panel content-view">
        <h2>作业内容</h2>
        <p class="instruction">{{ instructionText }}</p>
        <div
          v-if="assignment.source_assets && assignment.source_assets.length"
          class="assignment-source-assets"
          data-testid="assignment-source-assets"
        >
          <button
            v-for="asset in assignment.source_assets"
            :key="asset.id"
            type="button"
            @click="downloadAssignmentAsset(asset)"
          >
            <i class="el-icon-document"></i>
            <span>{{ asset.title || asset.original_filename }}</span>
            <i class="el-icon-download"></i>
          </button>
        </div>
        <h3>评分标准</h3>
        <div class="rubric-list">
          <div v-for="item in readableRubric" :key="item.label">
            <span>{{ item.label }}</span><b>{{ item.score }} 分</b>
          </div>
        </div>
        <details v-if="teacherReference">
          <summary>教师参考答案 / 说明</summary>
          <p>{{ teacherReference }}</p>
        </details>
      </section>

      <section v-else-if="activeTab === 'settings'" class="overview-panel settings-view">
        <h2>发布设置</h2>
        <dl>
          <div><dt>发布状态</dt><dd>{{ statusLabel(assignment.status) }}</dd></div>
          <div><dt>最大提交次数</dt><dd>{{ assignment.max_attempts }}</dd></div>
          <div><dt>反馈后订正</dt><dd>{{ assignment.allow_revision_after_feedback ? '允许' : '不允许' }}</dd></div>
          <div><dt>满分</dt><dd>{{ assignment.max_score }}</dd></div>
        </dl>
      </section>

      <section v-else class="overview-panel analytics-view">
        <h2>作业分析</h2>
        <div class="score-summary">
          <div><span>最高分</span><b>{{ metricValue('highest_score') }}</b></div>
          <div><span>最低分</span><b>{{ metricValue('lowest_score') }}</b></div>
          <div><span>平均分</span><b>{{ metricValue('average_score') }}</b></div>
        </div>
        <p>成绩发布后自动汇总；AI 建议不会直接写入正式成绩。</p>
      </section>
    </template>

    <div v-else class="student-assignment">
      <section class="assignment-brief">
        <div class="brief-label">任务要求</div>
        <p>{{ instructionText }}</p>
        <dl>
          <div><dt>任务类型</dt><dd>{{ kindLabel(assignment.kind) }}</dd></div>
          <div><dt>截止时间</dt><dd>长期有效</dd></div>
          <div><dt>最多提交</dt><dd>{{ assignment.max_attempts }} 次</dd></div>
        </dl>
        <div
          v-if="assignment.source_assets && assignment.source_assets.length"
          class="assignment-source-assets"
          data-testid="assignment-source-assets"
        >
          <b>作业附件</b>
          <button
            v-for="asset in assignment.source_assets"
            :key="asset.id"
            type="button"
            @click="downloadAssignmentAsset(asset)"
          >
            <i class="el-icon-document"></i>
            <span>{{ asset.title || asset.original_filename }}</span>
            <i class="el-icon-download"></i>
          </button>
        </div>
      </section>

      <section class="student-work">
        <div class="section-title">
          <div><h2>我的作答</h2><p>保存草稿后可跨设备继续，正式提交会生成不可变版本。</p></div>
          <span>{{ answer.length }} 字</span>
        </div>
        <el-input
          v-model="answer"
          data-testid="student-submission-editor"
          type="textarea"
          :rows="18"
          placeholder="在这里完成阅读回答或写作任务……"
          :disabled="submissionLocked"
        />
        <div class="submission-actions">
          <el-button
            data-testid="save-submission"
            :disabled="!answer || submissionLocked"
            @click="handleSaveSubmission"
          >保存草稿</el-button>
          <el-button
            data-testid="submit-assignment"
            type="primary"
            :disabled="!answer || submissionLocked"
            @click="handleSubmitAssignment"
          >正式提交</el-button>
        </div>
        <div v-if="studentFeedback" class="feedback-card" data-testid="released-feedback">
          <div><i class="el-icon-chat-line-square"></i><b>学习反馈</b></div>
          <p>{{ studentFeedback.content }}</p>
          <small v-if="studentFeedback.next_step">下一步：{{ studentFeedback.next_step }}</small>
        </div>
      </section>
    </div>
  </EducationShell>
</template>

<script>
import EducationShell from '../../components/education/EducationShell.vue'

export default {
  name: 'EducationAssignmentWorkspace',
  components: { EducationShell },
  data() {
    return {
      activeTab: 'submissions',
      studentQuery: '',
      statusFilter: '',
      sortMode: 'pending',
      answer: '',
      ownSubmissionRecord: null,
      releasedFeedback: [],
      overviewTabs: [
        { key: 'submissions', label: '提交与批改' },
        { key: 'content', label: '作业内容' },
        { key: 'settings', label: '发布设置' },
        { key: 'analytics', label: '作业分析' },
      ],
    }
  },
  computed: {
    courseId() { return this.$route.params.courseId },
    assignmentId() { return this.$route.params.assignmentId },
    course() { return this.$store.getters['education/activeCourse'] || {} },
    assignment() { return this.$store.state.education.activeAssignment },
    overview() { return this.$store.getters['education/assignmentOverview'] || {} },
    metrics() { return this.overview.metrics || {} },
    students() { return this.overview.students || [] },
    isTeacher() { return this.$store.getters['education/isTeacher'] },
    instructionText() {
      const value = this.assignment.instruction_json
      return typeof value === 'string'
        ? value
        : (value && (value.text || value.instructions)) || '暂无文字要求，请查看作业附件。'
    },
    readableRubric() {
      const rubric = this.assignment.evaluation_json && this.assignment.evaluation_json.rubric
      if (!rubric || typeof rubric !== 'object' || Array.isArray(rubric)) return []
      return Object.entries(rubric).map(([label, score]) => ({ label, score }))
    },
    teacherReference() {
      const evaluation = this.assignment.evaluation_json || {}
      const value = evaluation.answer_notes || evaluation.answer_key || evaluation.exemplar
      if (Array.isArray(value)) return value.join('；')
      return typeof value === 'object' ? '' : value
    },
    metricCards() {
      return [
        { key: 'expected', label: '应交', value: this.metrics.expected || 0, note: '课程学生' },
        { key: 'submitted', label: '已交', value: this.metrics.submitted || 0, note: `未交 ${this.metrics.unsubmitted || 0}` },
        { key: 'pending_review', label: '待批改', value: this.metrics.pending_review || 0, note: '按提交时间排序' },
        { key: 'graded', label: '已批改', value: this.metrics.graded || 0, note: `订正 ${this.metrics.revision_requested || 0}` },
        { key: 'average_score', label: '平均分', value: this.metricValue('average_score'), note: `满分 ${this.assignment.max_score}` },
      ]
    },
    filteredStudents() {
      const query = this.studentQuery.toLowerCase()
      const pending = row => !['graded', 'revision_requested', 'unsubmitted'].includes(row.status)
      const rows = this.students.filter(row => {
        if (query && !String(row.display_name || '').toLowerCase().includes(query)) return false
        if (this.statusFilter === 'pending') return pending(row)
        return !this.statusFilter || row.status === this.statusFilter
      }).slice()
      const statusRank = row => (pending(row) ? 0 : row.status === 'revision_requested' ? 1 : row.status === 'graded' ? 2 : 3)
      rows.sort((a, b) => {
        if (this.sortMode === 'name') return String(a.display_name).localeCompare(String(b.display_name), 'zh-CN')
        if (this.sortMode === 'time') return String(a.submitted_at || '').localeCompare(String(b.submitted_at || ''))
        if (this.sortMode === 'score') return Number(b.score === null ? -1 : b.score) - Number(a.score === null ? -1 : a.score)
        return statusRank(a) - statusRank(b)
      })
      return rows
    },
    nextReviewSubmission() {
      return this.students.find(row => row.submission_id && !['graded', 'revision_requested'].includes(row.status)) || null
    },
    ownSubmission() {
      return this.ownSubmissionRecord || null
    },
    submissionLocked() {
      if (!this.ownSubmission) return false
      if (this.ownSubmission.status === 'revision_requested') return false
      if (this.ownSubmission.status === 'graded') {
        return !this.assignment.allow_revision_after_feedback
      }
      return ['submitted', 'reviewing'].includes(this.ownSubmission.status)
    },
    studentFeedback() {
      const latest = this.releasedFeedback[this.releasedFeedback.length - 1]
      if (!latest || !latest.feedback_json) return null
      const value = latest.feedback_json
      const lines = []
      if (value.comment || value.content) lines.push(value.comment || value.content)
      for (const [label, items] of [
        ['做得好', value.strengths],
        ['需要加强', value.issues || value.weaknesses],
      ]) {
        const values = Array.isArray(items) ? items : (items ? [items] : [])
        if (values.length) lines.push(`${label}：${values.join('；')}`)
      }
      const next = Array.isArray(value.next_steps)
        ? value.next_steps.join('；')
        : value.next_step || ''
      return { content: lines.join('\n') || '教师已发布本次反馈。', next_step: next }
    },
    draftKey() { return `education_submission_draft:${this.assignmentId}` },
  },
  async created() {
    try {
      if (!this.course.id) await this.$store.dispatch('education/selectCourse', this.courseId)
      if (this.isTeacher) {
        await this.$store.dispatch('education/fetchAssignmentOverview', this.assignmentId)
      } else {
        await this.$store.dispatch('education/fetchAssignment', {
          assignmentId: this.assignmentId,
          courseId: this.courseId,
        })
        const recovery = await this.loadStudentSubmissionState()
        const latestVersion = recovery.versions && recovery.versions[recovery.versions.length - 1]
        const content = (recovery.draft && recovery.draft.answer_json)
          || (latestVersion && latestVersion.answer_json)
        this.answer = this.answerText(content) || localStorage.getItem(this.draftKey) || ''
      }
    } catch (error) {
      this.$message.error('作业加载失败或你无权访问')
      this.$router.replace(`/education/courses/${this.courseId}`)
    }
  },
  methods: {
    statusLabel(value) {
      return ({ draft: '草稿', published: '进行中', closed: '已截止', archived: '已归档' })[value] || value
    },
    submissionStatus(value) {
      return ({
        unsubmitted: '未提交',
        submitted: '待批改',
        revised: '已重新提交',
        reviewing: '批改中',
        graded: '已批改',
        revision_requested: '要求订正',
      })[value] || value
    },
    submissionTagType(value) {
      if (value === 'graded') return 'success'
      if (value === 'revision_requested') return 'warning'
      if (value === 'unsubmitted') return 'info'
      return ''
    },
    kindLabel(value) {
      return ({ quiz: '阅读练习', writing: '写作', mixed: '阅读与写作' })[value] || value
    },
    initials(value) { return String(value || '学生').slice(0, 2) },
    metricValue(key) {
      const value = this.metrics[key]
      return value === null || value === undefined ? '—' : value
    },
    scoreLabel(value) {
      return value === null || value === undefined ? '—' : `${value}/${this.assignment.max_score}`
    },
    formatDate(value) {
      if (!value) return '尚未提交'
      return new Date(value).toLocaleString('zh-CN')
    },
    answerText(value) {
      if (typeof value === 'string') return value
      return value && (value.text || value.writing || value.response) || ''
    },
    openReview(row) {
      if (!row || !row.submission_id) return
      this.$router.push(
        `/education/courses/${this.courseId}/assignments/${this.assignmentId}/review/${row.submission_id}`
      )
    },
    remindStudent(row) {
      this.$message.success(`已记录对 ${row.display_name} 的提醒；消息通知通道将在后续接入。`)
    },
    async handlePublishAssignment() {
      try {
        await this.$store.dispatch('education/publishAssignment', this.assignmentId)
        await this.$store.dispatch('education/fetchAssignmentOverview', this.assignmentId)
        this.$message.success('作业已发布')
      } catch (error) {
        this.$message.error('作业发布失败')
      }
    },
    async downloadAssignmentAsset(asset) {
      try {
        const blob = await this.$store.dispatch('education/downloadAsset', asset)
        const objectUrl = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = objectUrl
        link.download = asset.original_filename || asset.title || '作业附件'
        link.click()
        URL.revokeObjectURL(objectUrl)
      } catch (error) {
        this.$message.error('作业附件下载失败')
      }
    },
    async loadStudentSubmissionState() {
      const recovery = await this.$store.dispatch('education/fetchMySubmission', this.assignmentId)
      this.ownSubmissionRecord = recovery.submission || null
      this.releasedFeedback = this.ownSubmissionRecord
        ? await this.$store.dispatch('education/fetchFeedback', this.ownSubmissionRecord.id)
        : []
      return recovery
    },
    async handleSaveSubmission() {
      try {
        const recovery = await this.$store.dispatch('education/saveSubmissionDraft', {
          assignmentId: this.assignmentId,
          answerJson: { text: this.answer },
        })
        this.ownSubmissionRecord = recovery.submission || this.ownSubmissionRecord
        localStorage.removeItem(this.draftKey)
        this.$message.success('草稿已保存，可在其他设备继续')
      } catch (error) {
        localStorage.setItem(this.draftKey, this.answer)
        this.$message.warning('服务端暂不可用，草稿已临时保存在本机')
      }
    },
    async handleSubmitAssignment() {
      try {
        await this.$confirm('正式提交后将生成一个不可变版本，确认提交？', '提交作业')
        await this.$store.dispatch('education/saveSubmissionDraft', {
          assignmentId: this.assignmentId,
          answerJson: { text: this.answer },
        })
        await this.$store.dispatch('education/submitAssignment', {
          assignmentId: this.assignmentId,
          submission: {},
        })
        localStorage.removeItem(this.draftKey)
        await this.loadStudentSubmissionState()
        this.$message.success('作业已提交')
      } catch (error) {
        if (error !== 'cancel') this.$message.error('作业提交失败')
      }
    },
  },
}
</script>

<style scoped>
.overview-tabs { display: flex; gap: 6px; margin-bottom: 16px; padding: 5px; border: 1px solid #e1e8ed; border-radius: 11px; background: #f5f8fa; }
.overview-tabs button { padding: 9px 17px; border: 0; border-radius: 8px; background: transparent; color: #6c7888; cursor: pointer; }
.overview-tabs button.active { background: #fff; color: #247d73; font-weight: 700; box-shadow: 0 2px 8px rgba(35,55,64,.08); }
.overview-panel { min-height: 360px; padding: 18px; border: 1px solid #e1e8ed; border-radius: 12px; background: #fff; }
.overview-metrics { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: 18px; }
.overview-metrics article { padding: 15px; border: 1px solid #e1e9e6; border-radius: 10px; background: linear-gradient(145deg, #f8fbfa, #fff); }
.overview-metrics span, .overview-metrics b, .overview-metrics small { display: block; }
.overview-metrics span { color: #778494; font-size: 11px; }
.overview-metrics b { margin-top: 6px; color: #236f67; font-size: 24px; }
.overview-metrics small { margin-top: 4px; color: #98a2ae; font-size: 10px; }
.submission-toolbar { display: grid; grid-template-columns: 1fr 150px 150px; gap: 10px; margin-bottom: 12px; }
.student-cell { display: flex; align-items: center; gap: 9px; }
.student-cell span { width: 32px; height: 32px; display: grid; place-items: center; border-radius: 10px; background: #e1f0ec; color: #27786f; font-size: 10px; }
.content-view { max-width: 900px; }
.content-view h2, .content-view h3, .settings-view h2, .analytics-view h2 { color: #273548; }
.instruction { padding: 16px; border-radius: 9px; background: #f6f8fa; color: #4d5a6b; line-height: 1.8; white-space: pre-wrap; }
.rubric-list { display: grid; gap: 8px; }
.rubric-list div { display: flex; justify-content: space-between; padding: 11px 13px; border: 1px solid #e5ebef; border-radius: 8px; }
.content-view details { margin-top: 16px; padding: 12px; border: 1px solid #e6e9ed; border-radius: 8px; }
.settings-view dl { max-width: 620px; }
dl { margin: 14px 0 0; }
dl div { display: grid; grid-template-columns: 140px 1fr; padding: 11px 0; border-bottom: 1px solid #edf1f4; }
dt { color: #8b96a5; font-size: 11px; }
dd { margin: 0; color: #364456; font-size: 13px; }
.score-summary { display: grid; grid-template-columns: repeat(3, minmax(140px, 220px)); gap: 12px; }
.score-summary div { padding: 18px; border-radius: 10px; background: #eef7f5; }
.score-summary span, .score-summary b { display: block; }
.score-summary span { color: #6d817d; font-size: 11px; }
.score-summary b { margin-top: 7px; color: #24766d; font-size: 24px; }
.student-assignment { display: grid; grid-template-columns: minmax(250px, 30%) 1fr; gap: 18px; }
.assignment-brief, .student-work { padding: 19px; border: 1px solid #e1e8ee; border-radius: 11px; background: #fff; align-self: start; }
.brief-label { color: #27887e; font-size: 12px; font-weight: 700; }
.assignment-brief > p { color: #536273; line-height: 1.8; white-space: pre-wrap; }
.assignment-source-assets { display: grid; gap: 7px; margin-top: 17px; }
.assignment-source-assets > b { color: #435164; font-size: 12px; }
.assignment-source-assets button { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 8px; padding: 10px; border: 1px solid #dce7e4; border-radius: 8px; background: #f5faf9; color: #2f716a; text-align: left; cursor: pointer; }
.section-title { display: flex; justify-content: space-between; margin-bottom: 14px; }
.section-title h2 { margin: 0; color: #283647; font-size: 17px; }
.section-title p, .section-title > span { margin: 4px 0 0; color: #8490a0; font-size: 11px; }
.submission-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 13px; }
.feedback-card { margin-top: 18px; padding: 17px; border: 1px solid #bfe0da; border-radius: 10px; background: #eff9f7; }
.feedback-card div { display: flex; gap: 8px; color: #247b72; }
.feedback-card p { color: #48645f; white-space: pre-wrap; line-height: 1.7; }
@media (max-width: 1050px) {
  .overview-metrics { grid-template-columns: repeat(2, 1fr); }
  .student-assignment { grid-template-columns: 1fr; }
}
</style>
