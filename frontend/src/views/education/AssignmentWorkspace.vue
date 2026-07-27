<template>
  <EducationShell
    :title="assignment ? assignment.title : '作业空间'"
    :subtitle="isTeacher ? '查看提交、复核 AI 建议并发布反馈' : '完成阅读与写作任务，保存后再正式提交'"
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
    </template>

    <el-skeleton v-if="!assignment" :rows="9" animated />
    <div v-else class="assignment-layout">
      <section class="assignment-brief">
        <div class="brief-label">任务要求</div>
        <p>{{ instructionText }}</p>
        <dl>
          <div><dt>任务类型</dt><dd>{{ assignment.kind || assignment.assignment_type || '阅读与写作' }}</dd></div>
          <div><dt>截止时间</dt><dd>{{ dueLabel }}</dd></div>
          <div v-if="assignment.evaluation_json"><dt>评价标准</dt><dd>{{ rubricText }}</dd></div>
        </dl>
      </section>

      <section v-if="!isTeacher" class="student-work">
        <div class="section-title">
            <div><h2>我的作答</h2><p>本机草稿便于中断恢复；正式提交后写入课程并由教师复核。</p></div>
          <span>{{ answer.length }} 字符</span>
        </div>
        <el-input
          v-model="answer"
          data-testid="student-submission-editor"
          type="textarea"
          :rows="16"
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
          <p>{{ studentFeedback.content || studentFeedback.comment }}</p>
          <small v-if="studentFeedback.next_step">下一步：{{ studentFeedback.next_step }}</small>
        </div>
      </section>

      <section v-else class="teacher-review">
        <div class="submission-list">
          <div class="section-title"><div><h2>学生提交</h2><p>{{ submissions.length }} 份记录</p></div></div>
          <button
            v-for="submission in submissions"
            :key="submission.id"
            type="button"
            :class="{ active: selectedSubmission && selectedSubmission.id === submission.id }"
            :data-testid="`submission-${submission.id}`"
            @click="selectSubmission(submission)"
          >
            <span class="avatar">{{ initials(submission.student_user_id || submission.user_id) }}</span>
            <span><b>{{ submission.student_name || submission.student_user_id || submission.user_id }}</b><small>{{ submissionStatus(submission.status) }}</small></span>
            <i class="el-icon-arrow-right"></i>
          </button>
          <div v-if="!submissions.length" class="no-submission">还没有学生提交。</div>
        </div>
        <div class="review-editor">
          <template v-if="selectedSubmission">
            <div class="section-title"><div><h2>作答与反馈</h2><p>AI 建议仅供参考，反馈由教师确认发布。</p></div></div>
            <div class="answer-preview">{{ submissionText }}</div>
            <el-form label-position="top">
              <el-form-item label="教师反馈">
                <el-input
                  v-model="feedback.content"
                  data-testid="teacher-feedback-editor"
                  type="textarea"
                  :rows="6"
                  placeholder="指出做得好的地方、关键问题和可执行改进建议"
                />
              </el-form-item>
              <el-form-item label="下一步学习建议">
                <el-input v-model="feedback.next_step" />
              </el-form-item>
              <el-button
                data-testid="release-feedback"
                type="primary"
                :disabled="!feedback.content"
                @click="handleReleaseFeedback"
              >发布反馈</el-button>
            </el-form>
          </template>
          <div v-else class="select-hint">选择一份提交开始复核。</div>
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
      answer: '',
      selectedSubmission: null,
      feedback: { content: '', next_step: '' },
    }
  },
  computed: {
    courseId() { return this.$route.params.courseId },
    assignmentId() { return this.$route.params.assignmentId },
    course() { return this.$store.getters['education/activeCourse'] || {} },
    assignment() { return this.$store.state.education.activeAssignment },
    submissions() { return this.$store.state.education.submissions || [] },
    isTeacher() { return this.$store.getters['education/isTeacher'] },
    dueLabel() {
      return this.assignment.due_at ? new Date(this.assignment.due_at).toLocaleString() : '长期有效'
    },
    rubricText() {
      return typeof this.assignment.evaluation_json === 'string'
        ? this.assignment.evaluation_json
        : JSON.stringify(this.assignment.evaluation_json)
    },
    instructionText() {
      const value = this.assignment.instruction_json
      return typeof value === 'string' ? value : (value && (value.text || value.instructions)) || ''
    },
    ownSubmission() {
      return this.submissions[0] || this.assignment.submission || this.assignment.current_submission || null
    },
    submissionLocked() {
      return this.ownSubmission && ['submitted', 'reviewed'].includes(this.ownSubmission.status)
    },
    studentFeedback() {
      const released = this.$store.state.education.feedback || []
      const latest = released[released.length - 1]
      if (latest && latest.feedback_json) return latest.feedback_json
      return this.ownSubmission && (this.ownSubmission.feedback || this.assignment.feedback)
    },
    draftKey() {
      return `education_submission_draft:${this.assignmentId}`
    },
    submissionText() {
      const value = this.selectedSubmission.answer_json || this.selectedSubmission.content || this.selectedSubmission.answer || {}
      return typeof value === 'string' ? value : value.text || JSON.stringify(value, null, 2)
    },
  },
  async created() {
    try {
      if (!this.course.id) {
        await this.$store.dispatch('education/selectCourse', this.courseId)
      }
      const assignment = await this.$store.dispatch('education/fetchAssignment', {
        assignmentId: this.assignmentId,
        courseId: this.courseId,
      })
      if (this.isTeacher) {
        const submissions = await this.$store.dispatch('education/fetchSubmissions', this.assignmentId)
        if (submissions.length) this.selectSubmission(submissions[0])
      } else {
        const submissions = await this.$store.dispatch('education/fetchSubmissions', this.assignmentId)
        const submission = submissions[0] || assignment.submission || assignment.current_submission
        if (submission) {
          await this.$store.dispatch('education/fetchFeedback', submission.id)
        }
        const content = submission && (submission.content || submission.answer)
        const localDraft = localStorage.getItem(this.draftKey)
        this.answer = typeof content === 'string' ? content : (content && content.text) || localDraft || ''
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
      return ({ draft: '草稿', submitted: '待复核', reviewed: '已反馈' })[value] || value
    },
    initials(value) {
      return String(value || '学').slice(0, 2).toUpperCase()
    },
    selectSubmission(submission) {
      this.selectedSubmission = submission
      const existing = submission.feedback || {}
      this.feedback = { content: existing.content || '', next_step: existing.next_step || '' }
    },
    async handleSaveSubmission() {
      localStorage.setItem(this.draftKey, this.answer)
      this.$message.success('草稿已保存在本机')
    },
    async handleSubmitAssignment() {
      try {
        await this.$confirm('正式提交后将进入反馈流程，确认提交？', '提交作业')
        await this.$store.dispatch('education/submitAssignment', {
          assignmentId: this.assignmentId,
          submission: { answer_json: { text: this.answer } },
        })
        localStorage.removeItem(this.draftKey)
        this.$message.success('作业已提交')
        await this.$store.dispatch('education/fetchAssignment', {
          assignmentId: this.assignmentId,
          courseId: this.courseId,
        })
      } catch (error) {
        if (error !== 'cancel') this.$message.error('作业提交失败')
      }
    },
    async handlePublishAssignment() {
      try {
        await this.$store.dispatch('education/publishAssignment', this.assignmentId)
        this.$message.success('作业已发布')
        await this.$store.dispatch('education/fetchAssignment', this.assignmentId)
      } catch (error) {
        this.$message.error('作业发布失败')
      }
    },
    async handleReleaseFeedback() {
      try {
        await this.$store.dispatch('education/releaseFeedback', {
          submissionId: this.selectedSubmission.id,
          feedback: { feedback_json: this.feedback },
        })
        this.$message.success('反馈已发布给学生')
        await this.$store.dispatch('education/fetchSubmissions', this.assignmentId)
      } catch (error) {
        this.$message.error('反馈发布失败')
      }
    },
  },
}
</script>

<style scoped>
.assignment-layout { display: grid; grid-template-columns: minmax(240px, 30%) 1fr; gap: 18px; }
.assignment-brief, .student-work, .teacher-review { border: 1px solid #e1e8ee; border-radius: 11px; background: #fff; }
.assignment-brief { padding: 19px; align-self: start; }
.brief-label { color: #27887e; font-size: 12px; font-weight: 700; }
.assignment-brief > p { color: #536273; line-height: 1.8; white-space: pre-wrap; }
dl { margin: 18px 0 0; border-top: 1px solid #e8edf1; }
dl div { padding: 11px 0; border-bottom: 1px solid #edf1f4; }
dt { color: #8b96a5; font-size: 11px; }
dd { margin: 4px 0 0; color: #364456; font-size: 13px; }
.student-work { padding: 20px; }
.section-title { display: flex; justify-content: space-between; align-items: start; margin-bottom: 14px; }
.section-title h2 { margin: 0; color: #283647; font-size: 17px; }
.section-title p, .section-title > span { margin: 4px 0 0; color: #8490a0; font-size: 11px; }
.submission-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 13px; }
.feedback-card { margin-top: 18px; padding: 17px; border: 1px solid #bfe0da; border-radius: 10px; background: #eff9f7; }
.feedback-card div { display: flex; gap: 8px; color: #247b72; }
.feedback-card p { color: #48645f; white-space: pre-wrap; line-height: 1.7; }
.feedback-card small { color: #647b76; }
.teacher-review { display: grid; grid-template-columns: 250px 1fr; overflow: hidden; }
.submission-list { padding: 17px; border-right: 1px solid #e5ebf0; }
.submission-list button {
  width: 100%; display: grid; grid-template-columns: 36px 1fr auto; gap: 9px; align-items: center;
  padding: 10px; border: 0; border-radius: 8px; background: transparent; text-align: left; cursor: pointer;
}
.submission-list button.active { background: #edf7f5; }
.avatar { width: 34px; height: 34px; display: grid; place-items: center; border-radius: 10px; background: #dcefea; color: #277d74; font-size: 11px; }
.submission-list b, .submission-list small { display: block; overflow: hidden; text-overflow: ellipsis; }
.submission-list b { color: #334155; }
.submission-list small { margin-top: 3px; color: #8290a1; }
.review-editor { padding: 20px; min-width: 0; }
.answer-preview { max-height: 240px; margin-bottom: 18px; padding: 14px; overflow-y: auto; border-radius: 9px; background: #f7f9fb; color: #4d5c6d; line-height: 1.7; white-space: pre-wrap; }
.select-hint, .no-submission { min-height: 160px; display: grid; place-items: center; color: #909bab; font-size: 12px; }
@media (max-width: 1000px) { .assignment-layout { grid-template-columns: 1fr; } }
</style>
