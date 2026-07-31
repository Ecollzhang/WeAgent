<template>
  <EducationShell
    :title="review ? review.student.display_name : '批改工作台'"
    :subtitle="reviewSubtitle"
    :back-to="overviewPath"
  >
    <template #actions>
      <el-button icon="el-icon-back" @click="$router.push(overviewPath)">返回作业总览</el-button>
      <el-button
        :disabled="!previousSubmissionId"
        @click="openSibling(previousSubmissionId)"
      >上一位</el-button>
      <el-button
        :disabled="!nextSubmissionId"
        @click="openSibling(nextSubmissionId)"
      >下一位</el-button>
      <el-button type="primary" :loading="saving" @click="saveAndNext">
        保存并进入下一份
      </el-button>
    </template>

    <el-skeleton v-if="!review" :rows="12" animated />
    <template v-else>
      <div class="review-meta">
        <el-tag>{{ submissionStatus(review.submission.status) }}</el-tag>
        <span>{{ formatDate(review.submission.submitted_at) }}</span>
        <span>v{{ review.version.version_number }}</span>
        <span>{{ evidenceLength }} 字</span>
        <span>{{ review.evidence.artifacts.length }} 个附件</span>
      </div>

      <EmbeddedAgentRecord
        v-if="productAgentRun"
        title="AI 批改建议记录"
        :run="productAgentRun"
        @terminal="handleAgentTerminal"
        @poll-error="$message.warning('AI 建议状态暂时无法刷新，教师批改不受影响')"
        @close="closeAgentRun"
      />

      <main class="review-workbench">
        <aside class="review-rubric-column">
          <div class="column-heading">
            <span>01</span><div><h2>作业与评分依据</h2><p>量规只用于教师确认</p></div>
          </div>
          <section>
            <h3>作业要求</h3>
            <p class="pre-wrap">{{ instructionText }}</p>
          </section>
          <section>
            <h3>任务信息</h3>
            <dl>
              <div><dt>学科</dt><dd>{{ course.subject_code }}</dd></div>
              <div><dt>学段</dt><dd>{{ course.grade_band }}</dd></div>
              <div><dt>类型</dt><dd>{{ kindLabel(review.assignment.kind) }}</dd></div>
              <div><dt>满分</dt><dd>{{ review.assignment.max_score }}</dd></div>
            </dl>
          </section>
          <section>
            <h3>量规维度</h3>
            <div class="rubric-reference">
              <div v-for="item in review.rubric" :key="item.id">
                <span>{{ item.label }}</span><b>{{ item.max_score }} 分</b>
              </div>
            </div>
          </section>
          <details v-if="teacherReference">
            <summary>教师参考答案 / 典型说明</summary>
            <p class="pre-wrap">{{ teacherReference }}</p>
          </details>
        </aside>

        <section class="review-evidence-column">
          <div class="column-heading">
            <span>02</span><div><h2>学生学习证据</h2><p>当前提交版本，不显示原始 JSON</p></div>
          </div>
          <div v-if="review.evidence.kind === 'items'" class="answer-items">
            <article v-for="item in review.evidence.items" :key="item.index">
              <small>第 {{ item.index }} 题</small>
              <b>{{ item.prompt || '题目' }}</b>
              <p>{{ item.answer || '无作答' }}</p>
            </article>
          </div>
          <article v-else-if="review.evidence.text" class="writing-evidence">
            <div class="paper-header"><span>学生正文</span><small>可选取原文添加批注</small></div>
            <p>{{ review.evidence.text }}</p>
          </article>
          <div v-else class="empty-evidence">
            {{ review.evidence.kind === 'attachments' ? '本次提交仅包含附件' : '本次提交无正文' }}
          </div>

          <section v-if="review.evidence.artifacts.length" class="submission-artifacts">
            <h3>提交附件</h3>
            <button
              v-for="asset in review.evidence.artifacts"
              :key="asset.id"
              type="button"
              @click="downloadArtifact(asset)"
            >
              <i class="el-icon-document"></i>
              <span>{{ asset.title || asset.original_filename }}</span>
              <i class="el-icon-download"></i>
            </button>
          </section>

          <section class="annotation-editor">
            <h3>锚定批注</h3>
            <div v-for="(annotation, index) in draft.annotations" :key="index">
              <el-input v-model="annotation.quote" placeholder="引用学生原文" />
              <el-input v-model="annotation.comment" placeholder="批注内容" />
              <el-button icon="el-icon-delete" @click="draft.annotations.splice(index, 1)" />
            </div>
            <el-button plain icon="el-icon-plus" @click="addAnnotation">添加批注</el-button>
          </section>
        </section>

        <aside class="review-feedback-column">
          <div class="column-heading">
            <span>03</span><div><h2>评分与反馈</h2><p>教师确认后才会发布</p></div>
          </div>

          <section class="score-editor">
            <div v-for="item in review.rubric" :key="item.id">
              <span>{{ item.label }}</span>
              <el-input-number
                v-model="draft.rubric_scores[item.id]"
                :min="0"
                :max="item.max_score"
                :step="0.5"
                controls-position="right"
              />
            </div>
            <footer><span>总分</span><b>{{ totalScore }} / {{ review.assignment.max_score }}</b></footer>
          </section>

          <section class="ai-suggestion">
            <div class="section-heading">
              <h3>AI 批改建议</h3>
              <el-tag size="mini" :type="analysisTagType">{{ analysisStateLabel }}</el-tag>
            </div>
            <template v-if="analysis">
              <p>{{ analysis.summary }}</p>
              <div v-for="(issue, index) in analysis.issues || []" :key="index" class="ai-issue">
                <small>证据：“{{ issue.evidence }}”</small>
                <b>{{ issue.concern }}</b>
                <span>{{ issue.suggestion }}</span>
              </div>
              <el-button size="mini" plain @click="adoptAnalysis">采纳到反馈</el-button>
            </template>
            <template v-else>
              <p>AI 正在后台读取当前版本和量规；你可以立即评分与编辑。</p>
              <el-button
                v-if="!agentRunning"
                size="mini"
                plain
                @click="startReviewAgent"
              >重新分析</el-button>
            </template>
          </section>

          <el-form label-position="top" class="feedback-form">
            <el-form-item label="做得好的地方">
              <el-input v-model="feedbackStrengths" type="textarea" :rows="3" />
            </el-form-item>
            <el-form-item label="关键问题">
              <el-input v-model="feedbackIssues" type="textarea" :rows="3" />
            </el-form-item>
            <el-form-item label="下一步建议">
              <el-input v-model="feedbackNextSteps" type="textarea" :rows="3" />
            </el-form-item>
            <el-form-item label="教师反馈">
              <el-input
                v-model="feedbackComment"
                data-testid="teacher-feedback-editor"
                type="textarea"
                :rows="4"
                placeholder="写给学生的完整反馈"
              />
            </el-form-item>
            <el-checkbox v-model="draft.revision_requested">要求学生订正后重新提交</el-checkbox>
            <div class="review-actions">
              <el-button
                data-testid="save-review-draft"
                :loading="saving"
                @click="saveDraft"
              >保存批改草稿</el-button>
              <el-button
                data-testid="publish-review"
                type="primary"
                :loading="publishing"
                :disabled="!canPublish"
                @click="publishReview"
              >发布成绩与反馈</el-button>
            </div>
          </el-form>
        </aside>
      </main>
    </template>
  </EducationShell>
</template>

<script>
import EducationShell from '../../components/education/EducationShell.vue'
import EmbeddedAgentRecord from '../../components/education/EmbeddedAgentRecord.vue'

const emptyDraft = () => ({
  rubric_scores: {},
  feedback_json: {},
  annotations: [],
  revision_requested: false,
})

export default {
  name: 'EducationSubmissionReviewWorkspace',
  components: { EducationShell, EmbeddedAgentRecord },
  data() {
    return {
      draft: emptyDraft(),
      feedbackStrengths: '',
      feedbackIssues: '',
      feedbackNextSteps: '',
      feedbackComment: '',
      saving: false,
      publishing: false,
    }
  },
  computed: {
    courseId() { return this.$route.params.courseId },
    assignmentId() { return this.$route.params.assignmentId },
    submissionId() { return this.$route.params.submissionId },
    overviewPath() {
      return `/education/courses/${this.courseId}/assignments/${this.assignmentId}`
    },
    course() { return this.$store.getters['education/activeCourse'] || {} },
    review() { return this.$store.getters['education/submissionReview'] },
    productAgentRun() { return this.$store.getters['education/productAgentRun'] },
    previousSubmissionId() {
      return this.review && this.review.navigation.previous_submission_id
    },
    nextSubmissionId() {
      return this.review && this.review.navigation.next_submission_id
    },
    reviewSubtitle() {
      if (!this.review) return '正在读取学生提交'
      return `${this.review.assignment.title} · 当前提交 v${this.review.version.version_number}`
    },
    instructionText() {
      const value = this.review && this.review.assignment.instruction_json
      return typeof value === 'string' ? value : (value && (value.text || value.instructions)) || '暂无文字要求'
    },
    teacherReference() {
      const value = this.review && this.review.assignment.evaluation_json
      const reference = value && (value.answer_notes || value.answer_key || value.exemplar)
      if (Array.isArray(reference)) return reference.join('；')
      return typeof reference === 'object' ? '' : reference
    },
    evidenceLength() {
      return this.review && this.review.evidence.text
        ? this.review.evidence.text.length
        : 0
    },
    totalScore() {
      return Object.values(this.draft.rubric_scores || {})
        .reduce((sum, value) => sum + Number(value || 0), 0)
    },
    canPublish() {
      return Boolean(
        this.totalScore >= 0
        && (this.feedbackComment.trim()
          || this.feedbackStrengths.trim()
          || this.feedbackIssues.trim()
          || this.feedbackNextSteps.trim())
      )
    },
    analysis() {
      return this.review && this.review.analysis
        ? this.review.analysis.analysis_json
        : null
    },
    analysisStateLabel() {
      const state = this.review && this.review.analysis_state
      return ({ ready: '可采纳', stale: '已过期', missing: '生成中' })[state] || '生成中'
    },
    analysisTagType() {
      return this.review && this.review.analysis_state === 'ready' ? 'success' : 'warning'
    },
    agentRunning() {
      return Boolean(this.productAgentRun && ['pending', 'running'].includes(this.productAgentRun.status))
    },
  },
  watch: {
    submissionId() { this.loadReview() },
  },
  async created() {
    if (!this.course.id) await this.$store.dispatch('education/selectCourse', this.courseId)
    await this.loadReview()
  },
  methods: {
    async loadReview() {
      try {
        const review = await this.$store.dispatch('education/fetchSubmissionReview', this.submissionId)
        this.hydrateDraft(review.review_draft)
        const runs = await this.$store.dispatch('education/fetchProductAgentRuns', {
          courseId: this.courseId,
          productCode: 'submission_review',
        })
        const currentRun = runs.find(
          item => item.input_payload
            && item.input_payload.options
            && item.input_payload.options.submission_id === this.submissionId
            && item.input_payload.options.submission_version_id
              === review.analysis_cache_key.submission_version_id
            && item.input_payload.options.evaluation_checksum
              === review.analysis_cache_key.evaluation_checksum
        ) || null
        this.$store.commit('education/SET_PRODUCT_AGENT_RUN', currentRun)
        if (review.analysis_state !== 'ready' && !currentRun) {
          await this.startReviewAgent()
        }
      } catch (error) {
        this.$message.error('批改内容加载失败或你无权访问')
        this.$router.replace(this.overviewPath)
      }
    },
    hydrateDraft(value) {
      const source = value || emptyDraft()
      this.draft = {
        rubric_scores: { ...(source.rubric_scores || {}) },
        feedback_json: { ...(source.feedback_json || {}) },
        annotations: (source.annotations || []).map(item => ({ ...item })),
        revision_requested: Boolean(source.revision_requested),
      }
      const feedback = source.feedback_json || {}
      this.feedbackStrengths = this.listText(feedback.strengths)
      this.feedbackIssues = this.listText(feedback.issues)
      this.feedbackNextSteps = this.listText(feedback.next_steps)
      this.feedbackComment = feedback.comment || feedback.content || ''
      for (const item of this.review.rubric || []) {
        if (this.draft.rubric_scores[item.id] === undefined) {
          this.$set(this.draft.rubric_scores, item.id, 0)
        }
      }
    },
    listText(value) {
      return Array.isArray(value) ? value.join('\n') : String(value || '')
    },
    lines(value) {
      return String(value || '').split(/\r?\n/).map(item => item.trim()).filter(Boolean)
    },
    buildDraft() {
      return {
        rubric_scores: { ...this.draft.rubric_scores },
        feedback_json: {
          strengths: this.lines(this.feedbackStrengths),
          issues: this.lines(this.feedbackIssues),
          next_steps: this.lines(this.feedbackNextSteps),
          comment: this.feedbackComment.trim(),
        },
        annotations: this.draft.annotations,
        revision_requested: this.draft.revision_requested,
      }
    },
    submissionStatus(value) {
      return ({
        submitted: '待批改',
        revised: '已重新提交',
        reviewing: '批改中',
        graded: '已批改',
        revision_requested: '要求订正',
      })[value] || value
    },
    kindLabel(value) {
      return ({ quiz: '阅读练习', writing: '写作', mixed: '阅读与写作' })[value] || value
    },
    formatDate(value) {
      return value ? new Date(value).toLocaleString('zh-CN') : '时间未记录'
    },
    addAnnotation() {
      this.draft.annotations.push({ quote: '', comment: '' })
    },
    adoptAnalysis() {
      if (!this.analysis) return
      this.feedbackStrengths = this.listText(this.analysis.strengths)
      this.feedbackIssues = (this.analysis.issues || [])
        .map(item => `${item.concern}：${item.suggestion}`)
        .join('\n')
      this.feedbackNextSteps = this.listText(this.analysis.next_steps)
      this.feedbackComment = this.feedbackComment || this.analysis.summary || ''
      this.$message.success('AI 建议已复制到草稿，请教师继续修改确认')
    },
    async startReviewAgent() {
      if (this.agentRunning) return
      try {
        await this.$store.dispatch('education/startProductAgentRun', {
          course_id: this.courseId,
          product_code: 'submission_review',
          options: { submission_id: this.submissionId },
        })
      } catch (error) {
        this.$message.warning('AI 建议暂时无法启动，仍可继续人工批改')
      }
    },
    async handleAgentTerminal(run) {
      if (run.status === 'completed') {
        const refreshed = await this.$store.dispatch(
          'education/fetchSubmissionReview',
          this.submissionId
        )
        if (refreshed.review_draft) this.hydrateDraft(refreshed.review_draft)
      }
    },
    closeAgentRun() {
      this.$store.commit('education/SET_PRODUCT_AGENT_RUN', null)
    },
    async saveDraft(showMessage = true) {
      this.saving = true
      try {
        const saved = await this.$store.dispatch('education/saveSubmissionReviewDraft', {
          submissionId: this.submissionId,
          draft: this.buildDraft(),
        })
        if (showMessage) this.$message.success('批改草稿已保存')
        return saved
      } catch (error) {
        this.$message.error('批改草稿保存失败')
        throw error
      } finally {
        this.saving = false
      }
    },
    async publishReview() {
      this.publishing = true
      try {
        await this.saveDraft(false)
        await this.$store.dispatch('education/publishSubmissionReview', this.submissionId)
        this.$message.success('成绩与反馈已发布')
        await this.$store.dispatch('education/fetchSubmissionReview', this.submissionId)
      } catch (error) {
        this.$message.error('发布失败，请检查评分和反馈')
      } finally {
        this.publishing = false
      }
    },
    async saveAndNext() {
      try {
        await this.saveDraft(false)
        if (this.nextSubmissionId) this.openSibling(this.nextSubmissionId)
        else this.$router.push(this.overviewPath)
      } catch (error) {
        // saveDraft already reports the actionable error.
      }
    },
    openSibling(submissionId) {
      if (!submissionId) return
      this.$router.push(
        `/education/courses/${this.courseId}/assignments/${this.assignmentId}/review/${submissionId}`
      )
    },
    async downloadArtifact(asset) {
      try {
        const blob = await this.$store.dispatch('education/downloadAsset', asset)
        const objectUrl = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = objectUrl
        link.download = asset.original_filename || asset.title || '提交附件'
        link.click()
        URL.revokeObjectURL(objectUrl)
      } catch (error) {
        this.$message.error('提交附件下载失败')
      }
    },
  },
}
</script>

<style scoped>
.review-meta { display: flex; align-items: center; gap: 12px; margin: -4px 0 14px; color: #7d8997; font-size: 11px; }
.review-workbench { display: grid; grid-template-columns: minmax(220px, 24%) minmax(360px, 1fr) minmax(290px, 30%); gap: 12px; align-items: start; }
.review-workbench > aside, .review-workbench > section { min-width: 0; padding: 17px; border: 1px solid #e1e7eb; border-radius: 12px; background: #fff; }
.column-heading { display: flex; align-items: center; gap: 10px; padding-bottom: 13px; border-bottom: 1px solid #e7ecef; }
.column-heading > span { width: 30px; height: 30px; display: grid; place-items: center; border-radius: 9px; background: #e5f2ef; color: #25766d; font-size: 10px; font-weight: 700; }
.column-heading h2, .column-heading p { margin: 0; }
.column-heading h2 { color: #293648; font-size: 15px; }
.column-heading p { margin-top: 3px; color: #8c97a3; font-size: 9px; }
.review-workbench h3 { margin: 18px 0 9px; color: #465466; font-size: 12px; }
.pre-wrap { color: #586678; line-height: 1.75; white-space: pre-wrap; }
dl { margin: 0; }
dl div { display: flex; justify-content: space-between; padding: 7px 0; border-bottom: 1px solid #eef1f3; }
dt { color: #8d98a5; font-size: 10px; }
dd { margin: 0; color: #3c4b5c; font-size: 11px; }
.rubric-reference { display: grid; gap: 6px; }
.rubric-reference div { display: flex; justify-content: space-between; padding: 8px 9px; border-radius: 7px; background: #f6f8fa; color: #5c6978; font-size: 11px; }
.review-rubric-column details { margin-top: 16px; color: #657282; font-size: 11px; }
.writing-evidence { min-height: 360px; padding: 24px 28px; border: 1px solid #e3ddd0; border-radius: 8px; background: #fffdf8; box-shadow: 0 8px 22px rgba(62,53,40,.06); }
.paper-header { display: flex; justify-content: space-between; padding-bottom: 10px; border-bottom: 1px solid #e8e0d2; color: #987957; font-size: 10px; }
.writing-evidence > p { color: #2f3947; font-family: Georgia, 'Times New Roman', serif; font-size: 16px; line-height: 2; white-space: pre-wrap; }
.answer-items { display: grid; gap: 10px; }
.answer-items article { padding: 14px; border: 1px solid #e4e9ed; border-radius: 9px; }
.answer-items small, .answer-items b, .answer-items p { display: block; }
.answer-items small { color: #2a7a71; }
.answer-items b { margin-top: 6px; color: #3c4959; }
.answer-items p { color: #566576; }
.empty-evidence { min-height: 250px; display: grid; place-items: center; border: 1px dashed #d6dfe4; border-radius: 9px; color: #8d98a4; }
.submission-artifacts, .annotation-editor { margin-top: 16px; }
.submission-artifacts button { width: 100%; display: grid; grid-template-columns: auto 1fr auto; gap: 8px; padding: 9px; border: 1px solid #dce7e4; border-radius: 8px; background: #f6faf9; color: #31756e; text-align: left; cursor: pointer; }
.annotation-editor > div { display: grid; grid-template-columns: 1fr 1.3fr auto; gap: 6px; margin-bottom: 6px; }
.score-editor { margin-top: 14px; }
.score-editor > div, .score-editor footer { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 8px 0; }
.score-editor footer { margin-top: 5px; border-top: 1px solid #dfe7e5; color: #286f68; }
.score-editor footer b { font-size: 18px; }
.ai-suggestion { margin-top: 14px; padding: 12px; border: 1px solid #cfe2dd; border-radius: 9px; background: #f4faf8; }
.section-heading { display: flex; justify-content: space-between; align-items: center; }
.section-heading h3 { margin: 0; color: #2b746c; }
.ai-suggestion > p { color: #58706b; font-size: 11px; line-height: 1.6; }
.ai-issue { display: grid; gap: 3px; margin: 8px 0; padding: 8px; border-radius: 7px; background: #fff; }
.ai-issue small { color: #8a725b; }
.ai-issue b { color: #485864; font-size: 11px; }
.ai-issue span { color: #64747d; font-size: 10px; }
.feedback-form { margin-top: 15px; }
.review-actions { display: flex; justify-content: flex-end; gap: 7px; margin-top: 14px; }
@media (max-width: 1250px) {
  .review-workbench { grid-template-columns: 220px 1fr; }
  .review-feedback-column { grid-column: 1 / -1; }
}
</style>
