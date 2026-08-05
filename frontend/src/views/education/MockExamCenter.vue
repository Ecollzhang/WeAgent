<template>
  <EducationShell
    title="模拟考试"
    :subtitle="course ? `${course.title} · 从已发布题库生成个人试卷` : '选择一门学生课程'"
  >
    <template #actions>
      <el-button
        v-if="activeAttempt && activeAttempt.status === 'in_progress'"
        icon="el-icon-document-checked"
        :loading="saving"
        @click="saveMockExamAnswers"
      >保存进度</el-button>
      <el-button
        v-if="activeAttempt && activeAttempt.status === 'in_progress'"
        type="primary"
        icon="el-icon-finished"
        :loading="submitting"
        @click="confirmSubmit"
      >交卷</el-button>
    </template>

    <el-alert
      v-if="roleError"
      title="当前没有学生课程"
      description="请使用课程邀请码加入一门课程，再生成模拟考试。"
      type="warning"
      :closable="false"
      show-icon
    />

    <template v-else-if="course">
      <EmbeddedAgentRecord
        :run="productAgentRun"
        @terminal="handleAgentTerminal"
        @poll-error="$message.error('Agent 运行状态暂时无法刷新')"
        @close="closeAgentRun"
      />

      <section class="exam-layout">
        <aside class="exam-sidebar">
          <div class="generator-card" data-testid="mock-exam-generator">
            <span class="card-kicker">PERSONAL MOCK</span>
            <h2>生成一份新试卷</h2>
            <p>只从教师已发布的题目中抽取，提交后会成为作业弱点的证据。</p>
            <el-form label-position="top" size="small">
              <el-form-item label="试卷名称">
                <el-input v-model.trim="blueprint.title" />
              </el-form-item>
              <div class="generator-row">
                <el-form-item label="题目数">
                  <el-input-number v-model="blueprint.question_count" :min="1" :max="30" controls-position="right" />
                </el-form-item>
                <el-form-item label="时长">
                  <el-input-number v-model="blueprint.duration_minutes" :min="5" :max="180" controls-position="right" />
                </el-form-item>
              </div>
              <el-button
                type="primary"
                class="generate-button"
                :loading="agentRunning"
                @click="generateWithAgent"
              ><i class="el-icon-cpu"></i> Agent 协作生成</el-button>
              <el-button
                class="fallback-button"
                :loading="generating"
                @click="generateExam"
              >规则快速生成</el-button>
            </el-form>
          </div>

          <div class="attempt-history">
            <header><b>考试记录</b><span>{{ attempts.length }}</span></header>
            <button
              v-for="attempt in attempts"
              :key="attempt.id"
              type="button"
              :class="{ active: activeAttempt && activeAttempt.id === attempt.id }"
              @click="selectAttempt(attempt)"
            >
              <span :class="['attempt-status', attempt.status]"></span>
              <span>
                <b>{{ attemptTitle(attempt) }}</b>
                <small>{{ attemptStatus(attempt.status) }} · {{ dateLabel(attempt.created_at) }}</small>
              </span>
              <strong>{{ attempt.accuracy == null ? '—' : `${Math.round(attempt.accuracy * 100)}%` }}</strong>
            </button>
            <p v-if="!attempts.length" class="no-history">还没有考试记录</p>
          </div>
        </aside>

        <main class="exam-paper">
          <template v-if="activeAttempt">
            <header class="paper-header">
              <div>
                <span>WEAGENT EDUCATION · MOCK EXAM</span>
                <h2>{{ attemptTitle(activeAttempt) }}</h2>
                <p>
                  共 {{ activeAttempt.questions.length }} 题 ·
                  状态 {{ attemptStatus(activeAttempt.status) }}
                </p>
              </div>
              <div v-if="activeAttempt.status !== 'in_progress'" class="paper-score">
                <b>{{ scoreLabel(activeAttempt) }}</b>
                <span>正确率 {{ percent(activeAttempt.accuracy) }}</span>
              </div>
              <div v-else class="paper-progress">
                <b>{{ answeredCount }}/{{ activeAttempt.questions.length }}</b>
                <span>已作答</span>
              </div>
            </header>

            <div class="question-paper">
              <article
                v-for="(question, index) in activeAttempt.questions"
                :key="question.id"
                :class="{ reviewed: activeAttempt.status !== 'in_progress' }"
              >
                <header>
                  <span>{{ index + 1 }}</span>
                  <div>
                    <el-tag size="mini">{{ typeLabel(question.question_type) }}</el-tag>
                    <el-tag size="mini" type="info">{{ difficultyLabel(question.difficulty) }}</el-tag>
                    <small>{{ question.score }} 分</small>
                  </div>
                </header>
                <h3>{{ question.prompt }}</h3>
                <el-radio-group
                  v-if="question.question_type === 'single_choice'"
                  v-model="answers[question.id]"
                  :disabled="activeAttempt.status !== 'in_progress'"
                  @change="dirty = true"
                >
                  <el-radio
                    v-for="(option, optionIndex) in question.options"
                    :key="optionIndex"
                    :label="optionLetter(optionIndex)"
                    border
                  >
                    <b>{{ optionLetter(optionIndex) }}</b>
                    <span>{{ option }}</span>
                  </el-radio>
                </el-radio-group>
                <el-input
                  v-else
                  v-model="answers[question.id]"
                  type="textarea"
                  :rows="4"
                  :disabled="activeAttempt.status !== 'in_progress'"
                  @input="dirty = true"
                />
                <div
                  v-if="activeAttempt.status !== 'in_progress'"
                  :class="['review-note', evidenceFor(question).correct ? 'correct' : 'wrong']"
                >
                  <i :class="evidenceFor(question).correct ? 'el-icon-circle-check' : 'el-icon-circle-close'"></i>
                  <div>
                    <b>{{ evidenceFor(question).correct ? '回答正确' : '需要复习' }}</b>
                    <p>你的答案：{{ evidenceFor(question).submitted_answer || '未作答' }} · 参考答案：{{ evidenceFor(question).correct_answer }}</p>
                    <small>{{ evidenceFor(question).explanation }}</small>
                  </div>
                </div>
              </article>
            </div>
          </template>
          <div v-else class="blank-paper">
            <div class="blank-page">
              <span>01</span>
              <i class="el-icon-document-checked"></i>
              <h2>准备好后，生成第一份模拟考试</h2>
              <p>试卷会引用课程题库的固定版本；答题与评分记录会持久保留。</p>
            </div>
          </div>
        </main>
      </section>
    </template>
  </EducationShell>
</template>

<script>
import EducationShell from '../../components/education/EducationShell.vue'
import EmbeddedAgentRecord from '../../components/education/EmbeddedAgentRecord.vue'

export default {
  name: 'MockExamCenter',
  components: { EducationShell, EmbeddedAgentRecord },
  data() {
    return {
      roleError: false,
      generating: false,
      saving: false,
      submitting: false,
      dirty: false,
      answers: {},
      blueprint: {
        title: '我的课程诊断',
        question_count: 5,
        duration_minutes: 30,
      },
    }
  },
  computed: {
    course() { return this.$store.getters['education/activeCourse'] },
    attempts() { return this.$store.getters['education/mockExams'] || [] },
    activeAttempt() { return this.$store.getters['education/activeMockExam'] },
    productAgentRun() { return this.$store.getters['education/productAgentRun'] },
    agentRunning() {
      return Boolean(this.productAgentRun && ['pending', 'running'].includes(this.productAgentRun.status))
    },
    answeredCount() {
      return Object.values(this.answers).filter(value => value !== '' && value != null).length
    },
  },
  watch: {
    'course.id'(next, previous) {
      if (next && next !== previous) this.load(next)
    },
    activeAttempt: {
      immediate: true,
      handler(attempt) {
        this.answers = { ...((attempt && attempt.answers) || {}) }
        this.dirty = false
      },
    },
  },
  created() {
    this.bootstrap()
  },
  methods: {
    async bootstrap() {
      try {
        const course = await this.$store.dispatch('education/ensureRoleCourse', {
          courseId: this.$route.query.courseId,
          role: 'student',
        })
        await this.load(course.id)
      } catch (error) {
        this.roleError = true
      }
    },
    async load(courseId) {
      try {
        const attempts = await this.$store.dispatch('education/fetchMockExams', courseId)
        const current = attempts.find(item => item.status === 'in_progress') || attempts[0] || null
        this.$store.commit('education/SET_ACTIVE_MOCK_EXAM', current)
        await this.$store.dispatch('education/restoreProductAgentRun', {
          courseId,
          productCode: 'mock_exam',
        })
      } catch (error) {
        this.$message.error('考试记录加载失败')
      }
    },
    async generateExam() {
      this.generating = true
      try {
        await this.$store.dispatch('education/createMockExam', {
          courseId: this.course.id,
          blueprint: this.blueprint,
        })
        this.$message.success('模拟考试已生成')
      } catch (error) {
        const code = error.response && error.response.data && error.response.data.error_code
        this.$message.error(
          code === 'insufficient_questions'
            ? '课程题库中已发布题目不足，请联系教师补充题目'
            : '模拟考试生成失败'
        )
      } finally {
        this.generating = false
      }
    },
    async generateWithAgent() {
      try {
        await this.$store.dispatch('education/startProductAgentRun', {
          course_id: this.course.id,
          product_code: 'mock_exam',
          options: { ...this.blueprint },
        })
        this.$message.success('学习规划与练习教练 Agent 已启动')
      } catch (error) {
        const detail = error.response && error.response.data && error.response.data.error
        this.$message.error(detail || '模拟考试 Agent 启动失败')
      }
    },
    async handleAgentTerminal(run) {
      if (run.status !== 'completed') return
      const previousIds = new Set(this.attempts.map(item => item.id))
      const attempts = await this.$store.dispatch('education/fetchMockExams', this.course.id)
      const created = attempts.find(item => !previousIds.has(item.id)) || attempts[0]
      if (created) {
        this.$store.commit('education/SET_ACTIVE_MOCK_EXAM', created)
        this.$message.success('Agent 已创建模拟考试，可以开始答题')
      } else {
        this.$message.warning('Agent 已结束，但未创建试卷；可查看协作记录或使用规则生成')
      }
    },
    closeAgentRun() {
      this.$store.commit('education/SET_PRODUCT_AGENT_RUN', null)
    },
    selectAttempt(attempt) {
      if (this.dirty) {
        this.$confirm('当前答题进度尚未保存，仍要切换吗？', '未保存进度', {
          type: 'warning',
        }).then(() => {
          this.$store.commit('education/SET_ACTIVE_MOCK_EXAM', attempt)
        }).catch(() => {})
        return
      }
      this.$store.commit('education/SET_ACTIVE_MOCK_EXAM', attempt)
    },
    async saveMockExamAnswers() {
      if (!this.activeAttempt) return
      this.saving = true
      try {
        await this.$store.dispatch('education/saveMockExamAnswers', {
          attemptId: this.activeAttempt.id,
          answers: this.answers,
        })
        this.dirty = false
        this.$message.success('答题进度已保存')
      } catch (error) {
        this.$message.error('答题进度保存失败')
      } finally {
        this.saving = false
      }
    },
    confirmSubmit() {
      this.$confirm(
        `已作答 ${this.answeredCount}/${this.activeAttempt.questions.length} 题。交卷后答案不可修改。`,
        '确认交卷',
        { type: 'warning', confirmButtonText: '保存并交卷' }
      ).then(() => this.submit()).catch(() => {})
    },
    async submit() {
      this.submitting = true
      try {
        await this.$store.dispatch('education/saveMockExamAnswers', {
          attemptId: this.activeAttempt.id,
          answers: this.answers,
        })
        await this.$store.dispatch('education/submitMockExam', {
          courseId: this.course.id,
          attemptId: this.activeAttempt.id,
        })
        this.dirty = false
        this.$message.success('交卷完成，结果已进入学习证据')
      } catch (error) {
        this.$message.error('交卷失败')
      } finally {
        this.submitting = false
      }
    },
    evidenceFor(question) {
      return (this.activeAttempt.evidence || []).find(row => row.item_version_id === question.id) || {}
    },
    optionLetter(index) { return String.fromCharCode(65 + index) },
    typeLabel(value) { return ({ single_choice: '单选题', multiple_choice: '多选题', short_answer: '简答题', writing: '写作题' })[value] || '练习题' },
    difficultyLabel(value) { return ({ easy: '简单', medium: '中等', hard: '困难' })[value] || value },
    attemptStatus(value) { return ({ in_progress: '作答中', submitted: '已评分', pending_review: '待教师评阅' })[value] || value },
    attemptTitle(attempt) {
      return attempt && attempt.questions && attempt.questions.length
        ? `${attempt.questions.length} 题模拟考试`
        : '模拟考试'
    },
    percent(value) { return typeof value === 'number' ? `${Math.round(value * 100)}%` : '待评阅' },
    scoreLabel(attempt) {
      return typeof attempt.score === 'number' ? `${attempt.score}/${attempt.max_score}` : '待评阅'
    },
    dateLabel(value) {
      if (!value) return '刚刚'
      return new Date(value).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
    },
  },
}
</script>

<style scoped>
.exam-layout { display: grid; grid-template-columns: 278px minmax(0, 1fr); gap: 15px; min-height: 620px; }
.exam-sidebar { display: flex; flex-direction: column; gap: 12px; }
.generator-card { padding: 19px; border: 1px solid #d9e6e2; border-radius: 14px; background: linear-gradient(150deg, #f7fbf9, #edf5f2); }
.card-kicker { color: #2d8176; font-size: 9px; font-weight: 800; letter-spacing: .15em; }
.generator-card h2 { margin: 7px 0 6px; color: #2b403c; font-family: 'Noto Serif SC', 'Songti SC', SimSun, serif; font-size: 17px; }
.generator-card > p { margin: 0 0 16px; color: #7e8d89; font-size: 10px; line-height: 1.6; }
.generator-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }.generator-row :deep(.el-input-number) { width: 100%; }
.generate-button { width: 100%; margin-top: 2px; }
.fallback-button { width: 100%; margin: 8px 0 0; }
.attempt-history { flex: 1; padding: 14px; border: 1px solid #e1e8e6; border-radius: 13px; background: #fff; }
.attempt-history > header { display: flex; justify-content: space-between; padding: 2px 3px 10px; color: #526762; font-size: 11px; }.attempt-history > header span { color: #329083; }
.attempt-history button { width: 100%; display: grid; grid-template-columns: 8px 1fr auto; align-items: center; gap: 8px; padding: 10px 7px; border: 0; border-radius: 9px; background: transparent; cursor: pointer; text-align: left; }
.attempt-history button:hover, .attempt-history button.active { background: #eff6f4; }
.attempt-status { width: 6px; height: 6px; border-radius: 50%; background: #9aa7a4; }.attempt-status.in_progress { background: #d49a42; }.attempt-status.submitted { background: #4c9a78; }
.attempt-history button b, .attempt-history button small { display: block; }.attempt-history button b { color: #41534f; font-size: 10px; }.attempt-history button small { margin-top: 3px; color: #9ba6a3; font-size: 8px; }
.attempt-history button strong { color: #2e746b; font-family: Georgia, serif; font-size: 12px; }.no-history { padding: 24px 0; color: #9ba6a3; font-size: 10px; text-align: center; }
.exam-paper { min-width: 0; border: 1px solid #dfe6e4; border-radius: 14px; background: #fff; box-shadow: 0 12px 34px rgba(42, 69, 64, .05); }
.paper-header { min-height: 112px; display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 22px 28px; border-bottom: 1px solid #e6ecea; background: linear-gradient(100deg, #fcfdfd, #f5f9f8); }
.paper-header > div > span { color: #37877c; font-size: 8px; font-weight: 800; letter-spacing: .13em; }.paper-header h2 { margin: 6px 0 4px; color: #2d3f3b; font-family: Georgia, 'Noto Serif SC', serif; font-size: 20px; }.paper-header p { margin: 0; color: #8b9794; font-size: 9px; }
.paper-score, .paper-progress { min-width: 86px; padding-left: 20px; border-left: 1px solid #dbe5e2; text-align: center; }.paper-score b, .paper-score span, .paper-progress b, .paper-progress span { display: block; }.paper-score b, .paper-progress b { color: #2d786f; font-family: Georgia, serif; font-size: 22px; }.paper-score span, .paper-progress span { margin-top: 4px; color: #8a9794; font-size: 9px; }
.question-paper { padding: 2px 28px 30px; }.question-paper > article { padding: 24px 0; border-bottom: 1px solid #edf1f0; }.question-paper > article:last-child { border: 0; }
.question-paper article > header { display: flex; align-items: center; gap: 10px; }.question-paper article > header > span { width: 31px; height: 31px; display: grid; place-items: center; border-radius: 50%; background: #edf4f2; color: #397c72; font-family: Georgia, serif; }.question-paper article header div { display: flex; align-items: center; gap: 5px; }.question-paper article header small { color: #8e9a97; font-size: 9px; }
.question-paper h3 { margin: 13px 0 14px; color: #34433f; font-size: 13px; line-height: 1.65; }
.question-paper :deep(.el-radio-group) { width: 100%; display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
.question-paper :deep(.el-radio.is-bordered) { width: 100%; height: auto; min-height: 41px; margin: 0; padding: 10px 12px; white-space: normal; }.question-paper :deep(.el-radio__label) { display: inline-flex; gap: 8px; color: #596966; font-size: 10px; line-height: 1.45; }
.review-note { display: grid; grid-template-columns: 24px 1fr; gap: 8px; margin-top: 12px; padding: 11px; border-radius: 9px; background: #fdf4f1; color: #b46250; }.review-note.correct { background: #eff8f3; color: #397e5e; }.review-note > i { font-size: 17px; }.review-note b { font-size: 10px; }.review-note p, .review-note small { display: block; margin: 4px 0 0; color: #6f7d7a; font-size: 9px; line-height: 1.5; }
.blank-paper { min-height: 610px; display: grid; place-items: center; background: repeating-linear-gradient(0deg, #fff 0 29px, #f6f8f7 30px); }.blank-page { max-width: 370px; text-align: center; color: #85938f; }.blank-page > span { display: block; color: #c4cfcc; font-family: Georgia, serif; font-size: 50px; }.blank-page i { margin: 8px 0; color: #6e9d94; font-size: 32px; }.blank-page h2 { margin: 8px 0; color: #536a65; font-family: 'Noto Serif SC', 'Songti SC', SimSun, serif; font-size: 17px; }.blank-page p { margin: 0; font-size: 10px; line-height: 1.6; }
@media (max-width: 1050px) { .exam-layout { grid-template-columns: 235px 1fr; } }
@media (max-width: 760px) { .exam-layout { grid-template-columns: 1fr; }.attempt-history { display: none; }.question-paper :deep(.el-radio-group) { grid-template-columns: 1fr; } }
</style>
