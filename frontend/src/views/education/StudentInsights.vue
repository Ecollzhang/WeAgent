<template>
  <EducationShell
    title="学生画像与评估"
    :subtitle="course ? `${course.title} · 只依据提交、考试与评分证据` : '选择一门教师课程'"
  >
    <template #actions>
      <el-button
        icon="el-icon-refresh"
        :loading="refreshing"
        :disabled="!course"
        @click="refresh"
      >仅刷新证据</el-button>
      <el-button
        type="primary"
        icon="el-icon-cpu"
        :loading="agentRunning"
        :disabled="!course"
        @click="startInsightAgent"
      >AI 分析建议</el-button>
    </template>

    <el-alert
      v-if="roleError"
      title="当前没有教师课程"
      type="warning"
      :closable="false"
      show-icon
    />
    <template v-else-if="course">
      <EmbeddedAgentRecord
        :run="productAgentRun"
        @preview="previewAdoptedArtifact"
        title="AI 分析记录"
        @terminal="handleAgentTerminal"
        @poll-error="$message.error('Agent 运行状态暂时无法刷新')"
        @close="closeAgentRun"
      />

      <div class="insight-mode-switch" data-testid="student-insight-mode-switch">
        <button type="button" :class="{ active: mode === 'grades' }" @click="mode = 'grades'">成绩总览</button>
        <button type="button" :class="{ active: mode === 'profiles' }" @click="mode = 'profiles'">学生画像</button>
      </div>

      <section v-if="mode === 'grades'" class="class-overview" data-testid="student-insight-overview">
        <header>
          <div>
            <span>ONE ASSIGNMENT · ONE DISTRIBUTION</span>
            <h2>按作业查看班级成绩</h2>
            <p>分布只统计当前选中作业；课程趋势按已发布作业排列，不混入模拟考试。</p>
          </div>
          <el-select v-model="selectedAssignmentId" class="assignment-selector" placeholder="选择作业" @change="loadGradeOverview">
            <el-option v-for="assignment in overview.assignment_catalog || []" :key="assignment.id" :label="assignment.title" :value="assignment.id" />
          </el-select>
          <el-tag v-if="overview.pending_review_count" type="warning" size="small">
            {{ overview.pending_review_count }} 份待教师确认
          </el-tag>
        </header>
        <div class="official-metrics">
          <article><span>最高分</span><b>{{ scoreMetric('highest_score') }}</b><small>百分制</small></article>
          <article><span>最低分</span><b>{{ scoreMetric('lowest_score') }}</b><small>百分制</small></article>
          <article><span>平均分</span><b>{{ scoreMetric('average_score') }}</b><small>{{ overview.graded_count || 0 }} 人已批改</small></article>
          <article><span>中位数</span><b>{{ scoreMetric('median_score') }}</b><small>降低极端值影响</small></article>
          <article><span>提交率</span><b>{{ percent(overview.submission_rate) }}</b><small>当前作业</small></article>
        </div>
        <div class="analytics-charts">
          <article>
            <h3>{{ overview.selected_assignment ? overview.selected_assignment.title : '当前作业' }} · 成绩分布</h3>
            <ScoreDistributionChart :distribution="overview.score_distribution || []" />
          </article>
          <article>
            <h3>课程作业平均分趋势</h3>
            <ScoreDistributionChart mode="trend" :trend="overview.course_assignment_trend || []" />
          </article>
        </div>
      </section>

      <section v-if="mode === 'profiles'" class="evidence-banner">
        <div class="banner-seal"><i class="el-icon-data-board"></i></div>
        <div>
          <span>Evidence-first learner profile</span>
          <h2>画像不是性格标签，而是一张可回到原始学习行为的证据索引</h2>
          <p>正确率、知识点薄弱项和教学建议只来自作业提交、模拟考试与教师评分。没有证据时明确显示“数据不足”。</p>
        </div>
        <dl>
          <div><dt>学生</dt><dd>{{ studentRows.length }}</dd></div>
          <div><dt>有证据</dt><dd>{{ readyCount }}</dd></div>
          <div><dt>待积累</dt><dd>{{ studentRows.length - readyCount }}</dd></div>
        </dl>
      </section>

      <section
        v-if="mode === 'profiles'"
        v-loading="loading"
        class="insight-list"
        data-testid="student-insight-list"
      >
        <article v-for="row in visibleStudentRows" :key="row.user_id" ref="profileCards" class="insight-card" @click="openEvidence(row)">
          <header>
            <span class="student-avatar">{{ initials(row.display_name) }}</span>
            <div>
              <h3>{{ row.display_name || row.user_id }}</h3>
              <p>{{ row.profile && row.profile.username ? row.profile.username : '课程成员' }}</p>
            </div>
            <el-tag
              size="mini"
              :type="row.insight && row.insight.data_state === 'ready' ? 'success' : 'info'"
            >
              {{ row.insight && row.insight.data_state === 'ready' ? '证据已更新' : '数据不足' }}
            </el-tag>
          </header>

          <template v-if="row.insight && row.insight.data_state === 'ready'">
            <div class="insight-metrics">
              <div>
                <span>正式均分</span>
                <b>{{ scoreValue(row.insight.summary.official_average_score) }}</b>
              </div>
              <div>
                <span>作业完成</span>
                <b>{{ percent(row.insight.summary.assignment_completion_rate) }}</b>
              </div>
              <div>
                <span>正式证据</span>
                <b>{{ row.insight.summary.official_score_count || 0 }}</b>
              </div>
            </div>
            <div class="weakness-strip">
              <span>需要关注</span>
              <el-tag
                v-for="weakness in (row.insight.weaknesses || []).slice(0, 3)"
                :key="weakness.knowledge_point"
                size="mini"
                type="warning"
              >{{ weakness.knowledge_point }}</el-tag>
              <small v-if="!row.insight.weaknesses.length">当前证据中未发现错误聚集</small>
            </div>
            <button type="button" class="evidence-link" @click="openEvidence(row)">
              查看 {{ row.insight.evidence.length }} 条来源证据
              <i class="el-icon-arrow-right"></i>
            </button>
          </template>
          <div v-else class="insufficient">
            <i class="el-icon-time"></i>
            <p>
              <b>{{ row.insight && row.insight.data_state === 'pending_review' ? '待教师确认' : '数据不足' }}</b>
              <span>{{ row.insight && row.insight.data_state === 'pending_review' ? '已有提交，但尚未进入正式班级统计。' : '学生完成已发布作业或模拟考试后，这里才会形成可解释画像。' }}</span>
            </p>
          </div>
        </article>
        <div v-if="!loading && !studentRows.length" class="empty-roster">
          <i class="el-icon-user"></i>
          <h3>课程中还没有学生</h3>
          <p>回到教学空间，通过邀请码或 Agent 名单工具添加学生。</p>
        </div>
        <button v-if="visibleStudentCount < studentRows.length" type="button" class="load-more-profiles" @click="loadMoreProfiles">
          加载更多（剩余 {{ studentRows.length - visibleStudentCount }} 人）
        </button>
      </section>
    </template>

    <el-drawer
      title="画像证据"
      :visible.sync="evidenceDrawer"
      size="520px"
    >
      <div v-if="selectedRow" class="drawer-content">
        <h3>{{ selectedRow.display_name }}的证据轨迹</h3>
        <article
          v-for="evidence in selectedRow.insight.evidence"
          :key="evidence.object_id"
          class="evidence-row"
        >
          <span><i class="el-icon-document-checked"></i></span>
          <div>
            <b>{{ evidence.object_type === 'assignment_submission' ? evidence.assessment_title : '模拟考试' }}</b>
            <small>{{ dateLabel(evidence.submitted_at) }}</small>
            <p>得分 {{ scoreLabel(evidence.score, evidence.max_score) }} · 百分制 {{ scoreValue(evidence.normalized_score) }}</p>
          </div>
        </article>
        <h4>建议动作</h4>
        <p
          v-for="recommendation in selectedRow.insight.recommendations"
          :key="recommendation.knowledge_point"
          class="recommendation"
        >{{ recommendation.action }}</p>
      </div>
    </el-drawer>

    <el-dialog
      title="最新学情分析产物"
      :visible.sync="adoptedPreviewDialog"
      width="760px"
      data-testid="student-insight-adopted-preview"
    >
      <div class="insight-product-summary">
        <div><span>最高分</span><b>{{ scoreMetric('highest_score') }}</b></div>
        <div><span>最低分</span><b>{{ scoreMetric('lowest_score') }}</b></div>
        <div><span>平均分</span><b>{{ scoreMetric('average_score') }}</b></div>
        <div><span>提交率</span><b>{{ percent(overview.submission_rate) }}</b></div>
      </div>
      <div class="insight-product-list">
        <article v-for="row in studentRows" :key="row.user_id">
          <b>{{ row.display_name || row.user_id }}</b>
          <span v-if="row.insight && row.insight.data_state === 'ready'">
            正式均分 {{ scoreValue(row.insight.summary.official_average_score) }}；
            {{ (row.insight.recommendations || []).map(item => item.action).join('；') || '当前没有额外建议' }}
          </span>
          <span v-else>数据不足，需继续积累正式作业或模拟考试证据。</span>
        </article>
      </div>
    </el-dialog>
  </EducationShell>
</template>

<script>
import EducationShell from '../../components/education/EducationShell.vue'
import EmbeddedAgentRecord from '../../components/education/EmbeddedAgentRecord.vue'
import ScoreDistributionChart from '../../components/education/ScoreDistributionChart.vue'

export default {
  name: 'StudentInsights',
  components: { EducationShell, EmbeddedAgentRecord, ScoreDistributionChart },
  data() {
    return {
      mode: 'grades',
      visibleStudentCount: 3,
      selectedAssignmentId: '',
      roleError: false,
      loading: false,
      refreshing: false,
      evidenceDrawer: false,
      selectedRow: null,
      adoptedPreviewDialog: false,
    }
  },
  computed: {
    course() { return this.$store.getters['education/activeCourse'] },
    members() { return this.$store.getters['education/members'] || [] },
    insights() { return this.$store.getters['education/studentInsights'] || [] },
    overview() { return this.$store.getters['education/gradeOverview'] || {} },
    studentRows() {
      return this.members
        .filter(member => member.role === 'student')
        .map(member => ({
          ...member,
          insight: this.insights.find(item => item.student_user_id === member.user_id) || null,
        }))
    },
    visibleStudentRows() { return this.studentRows.slice(0, this.visibleStudentCount) },
    readyCount() {
      return this.studentRows.filter(row => row.insight && row.insight.data_state === 'ready').length
    },
    productAgentRun() { return this.$store.getters['education/productAgentRun'] },
    agentRunning() {
      return Boolean(this.productAgentRun && ['pending', 'running'].includes(this.productAgentRun.status))
    },
  },
  watch: {
    'course.id'(next, previous) {
      if (next && next !== previous) this.load(next)
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
          role: 'teacher',
        })
        await this.load(course.id)
      } catch (error) {
        this.roleError = true
      }
    },
    async load(courseId) {
      this.loading = true
      this.roleError = false
      try {
        await Promise.all([
          this.$store.dispatch('education/fetchCourseOverview', courseId),
          this.$store.dispatch('education/fetchStudentInsights', courseId),
          this.$store.dispatch('education/fetchGradeOverview', { courseId, assignmentId: this.selectedAssignmentId }),
        ])
        if (!this.selectedAssignmentId && this.overview.selected_assignment) this.selectedAssignmentId = this.overview.selected_assignment.id
        await this.$store.dispatch('education/restoreProductAgentRun', {
          courseId,
          productCode: 'student_insight',
        })
      } catch (error) {
        this.$message.error('学生画像加载失败')
      } finally {
        this.loading = false
      }
    },
    async refresh() {
      this.refreshing = true
      try {
        await this.$store.dispatch('education/refreshStudentInsights', this.course.id)
        await this.loadGradeOverview()
        this.$message.success('画像已按最新学习证据刷新')
      } catch (error) {
        this.$message.error('画像刷新失败')
      } finally {
        this.refreshing = false
      }
    },
    async startInsightAgent() {
      try {
        await this.$store.dispatch('education/startProductAgentRun', {
          course_id: this.course.id,
          product_code: 'student_insight',
          options: {},
        })
        this.$message.success('学情分析 Agent 团队已启动')
      } catch (error) {
        const detail = error.response && error.response.data && error.response.data.error
        this.$message.error(detail || '学情 Agent 启动失败')
      }
    },
    async handleAgentTerminal(run) {
      if (run.status === 'completed') {
        await this.$store.dispatch('education/fetchStudentInsights', this.course.id)
        this.$message.success('Agent 已按真实学习证据刷新画像')
      }
    },
    closeAgentRun() {
      this.$store.commit('education/SET_PRODUCT_AGENT_RUN', null)
    },
    previewAdoptedArtifact({ adoptedObject }) {
      if (!adoptedObject || adoptedObject.object_type !== 'student_insight_report') return
      this.adoptedPreviewDialog = true
    },
    openEvidence(row) {
      this.selectedRow = row
      this.evidenceDrawer = true
    },
    async loadGradeOverview() {
      if (!this.course) return
      const result = await this.$store.dispatch('education/fetchGradeOverview', { courseId: this.course.id, assignmentId: this.selectedAssignmentId })
      if (!this.selectedAssignmentId && result.selected_assignment) this.selectedAssignmentId = result.selected_assignment.id
    },
    loadMoreProfiles() {
      const previous = this.visibleStudentCount
      this.visibleStudentCount = Math.min(this.studentRows.length, previous + 3)
      this.$nextTick(() => {
        const cards = this.$refs.profileCards || []
        const target = Array.isArray(cards) ? cards[previous] : null
        if (target && target.scrollIntoView) target.scrollIntoView({ behavior: 'smooth', block: 'center' })
      })
    },
    initials(name) {
      const value = String(name || '学')
      return value.slice(-2)
    },
    percent(value) {
      return typeof value === 'number' ? `${Math.round(value * 100)}%` : '—'
    },
    scoreMetric(key) {
      return this.scoreValue(this.overview[key])
    },
    scoreValue(value) {
      return typeof value === 'number' ? value.toFixed(1).replace('.0', '') : '—'
    },
    scoreLabel(score, maxScore) {
      return typeof score === 'number' ? `${score}/${maxScore}` : '待教师评阅'
    },
    dateLabel(value) {
      return value ? new Date(value).toLocaleString('zh-CN') : '时间未记录'
    },
  },
}
</script>

<style scoped>
.insight-mode-switch { width: fit-content; display: grid; grid-template-columns: repeat(2, minmax(120px, 1fr)); gap: 4px; margin-bottom: 16px; padding: 4px; border-radius: 12px; background: #e9f1ef; }
.insight-mode-switch button { padding: 9px 18px; border: 0; border-radius: 9px; background: transparent; color: #70817d; cursor: pointer; }
.insight-mode-switch button.active { background: #fff; color: #276f66; font-weight: 700; box-shadow: 0 4px 12px rgba(44, 85, 78, .08); }
.assignment-selector { min-width: 260px; }
.class-overview {
  margin-bottom: 18px; padding: 22px; border: 1px solid #d8e5e2;
  border-radius: 16px; background: linear-gradient(135deg, #fff 0%, #f5faf8 72%, #edf6f3 100%);
  box-shadow: 0 14px 34px rgba(41, 84, 76, .06);
  animation: insight-enter 320ms cubic-bezier(.2,.8,.2,1) both;
}
.class-overview > header { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; margin-bottom: 17px; }
.class-overview > header span { color: #2f8277; font-size: 9px; font-weight: 800; letter-spacing: .14em; }
.class-overview > header h2 { margin: 5px 0 5px; color: #263d39; font-family: 'Noto Serif SC', 'Songti SC', SimSun, serif; font-size: 20px; }
.class-overview > header p { margin: 0; color: #7c8d89; font-size: 10px; }
.official-metrics { display: grid; grid-template-columns: repeat(5, 1fr); gap: 9px; }
.official-metrics article { padding: 13px; border: 1px solid #e0e9e7; border-radius: 11px; background: rgba(255,255,255,.82); }
.official-metrics span, .official-metrics b, .official-metrics small { display: block; }
.official-metrics span { color: #7e8f8b; font-size: 9px; }.official-metrics b { margin-top: 6px; color: #286e65; font-family: Georgia, serif; font-size: 25px; }
.official-metrics small { margin-top: 4px; color: #a0aaa7; font-size: 8px; }
.analytics-charts { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px; }
.analytics-charts > article { min-width: 0; padding: 13px 14px 6px; border: 1px solid #e4ecea; border-radius: 12px; background: #fff; }
.analytics-charts h3 { margin: 0; color: #596e69; font-size: 10px; font-weight: 700; }
@keyframes insight-enter { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
.evidence-banner {
  display: grid; grid-template-columns: 62px minmax(0, 1fr) auto; align-items: center;
  gap: 18px; margin-bottom: 18px; padding: 22px 26px; border: 1px solid #dbe6e8;
  border-radius: 15px; background: linear-gradient(100deg, #f8fbfb, #eef5f4);
}
.banner-seal {
  width: 58px; height: 58px; display: grid; place-items: center; border-radius: 50%;
  border: 1px solid #c5dbd6; background: #fff; color: #2f8278; font-size: 24px;
  box-shadow: 0 7px 20px rgba(42, 105, 95, .09);
}
.evidence-banner span { color: #348278; font-size: 9px; font-weight: 800; letter-spacing: .13em; text-transform: uppercase; }
.evidence-banner h2 { margin: 5px 0 6px; color: #263b38; font-family: 'Noto Serif SC', 'Songti SC', SimSun, serif; font-size: 19px; }
.evidence-banner p { margin: 0; color: #758581; font-size: 11px; line-height: 1.6; }
.evidence-banner dl { display: flex; gap: 8px; margin: 0; }
.evidence-banner dl div { min-width: 68px; padding: 10px; border-left: 1px solid #d7e3e0; text-align: center; }
.evidence-banner dt { color: #8b9996; font-size: 9px; }
.evidence-banner dd { margin: 4px 0 0; color: #2d746b; font-family: Georgia, serif; font-size: 22px; }
.insight-list { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; min-height: 300px; }
.insight-card { padding: 17px; border: 1px solid #e0e8e6; border-radius: 13px; background: #fff; box-shadow: 0 8px 24px rgba(40, 73, 68, .04); cursor: pointer; transition: transform .18s ease, box-shadow .18s ease; }
.insight-card:hover { transform: translateY(-2px); box-shadow: 0 13px 30px rgba(40, 73, 68, .09); }
.load-more-profiles { grid-column: 1 / -1; padding: 12px; border: 1px dashed #bad0ca; border-radius: 11px; background: #f7fbfa; color: #34796f; cursor: pointer; }
.insight-card header { display: grid; grid-template-columns: 42px 1fr auto; align-items: center; gap: 10px; padding-bottom: 13px; border-bottom: 1px solid #edf1f0; }
.student-avatar { width: 40px; height: 40px; display: grid; place-items: center; border-radius: 12px; background: #e7f1ee; color: #286f67; font-size: 12px; font-weight: 700; }
.insight-card h3 { margin: 0; color: #31433f; font-size: 14px; }
.insight-card header p { margin: 4px 0 0; color: #95a19f; font-size: 9px; }
.insight-metrics { display: grid; grid-template-columns: repeat(3, 1fr); margin: 14px 0 12px; }
.insight-metrics div { padding: 4px 10px; border-right: 1px solid #e7edeb; }
.insight-metrics div:last-child { border: 0; }
.insight-metrics span, .insight-metrics b { display: block; }
.insight-metrics span { color: #879591; font-size: 9px; }
.insight-metrics b { margin-top: 4px; color: #2c655e; font-family: Georgia, serif; font-size: 19px; }
.weakness-strip { min-height: 52px; padding: 10px; border-radius: 9px; background: #faf8f2; }
.weakness-strip > span { display: block; margin-bottom: 7px; color: #938162; font-size: 9px; }
.weakness-strip .el-tag { margin-right: 5px; }
.weakness-strip small { color: #9a9d98; }
.evidence-link { width: 100%; margin-top: 10px; padding: 8px; border: 0; background: transparent; color: #347f75; font-size: 10px; cursor: pointer; text-align: right; }
.insufficient { min-height: 126px; display: flex; align-items: center; justify-content: center; gap: 11px; color: #91a09c; }
.insufficient i { font-size: 22px; }
.insufficient p { margin: 0; }
.insufficient b, .insufficient span { display: block; }
.insufficient b { color: #677a76; font-size: 12px; }
.insufficient span { max-width: 250px; margin-top: 4px; font-size: 10px; line-height: 1.5; }
.empty-roster { grid-column: 1 / -1; min-height: 260px; display: grid; place-content: center; text-align: center; color: #869692; }
.empty-roster i { font-size: 30px; }.empty-roster h3 { margin: 10px 0 4px; }.empty-roster p { margin: 0; font-size: 11px; }
.drawer-content { padding: 0 24px 24px; }
.drawer-content h3 { color: #30433f; }.drawer-content h4 { margin-top: 24px; color: #566b67; font-size: 12px; }
.evidence-row { display: grid; grid-template-columns: 34px 1fr; gap: 10px; padding: 13px 0; border-bottom: 1px solid #edf1f0; }
.evidence-row > span { width: 32px; height: 32px; display: grid; place-items: center; border-radius: 9px; background: #e8f2ef; color: #347e74; }
.evidence-row b, .evidence-row small { display: block; }.evidence-row b { color: #3c504c; font-size: 12px; }.evidence-row small { margin-top: 3px; color: #9aa6a3; font-size: 9px; }
.evidence-row p, .recommendation { margin: 7px 0 0; color: #71817d; font-size: 10px; line-height: 1.6; }
.recommendation { padding: 10px; border-radius: 8px; background: #f4f8f7; }
.insight-product-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 16px;
}
.insight-product-summary div { padding: 14px; border-radius: 10px; background: #eef6f4; }
.insight-product-summary span, .insight-product-summary b { display: block; }
.insight-product-summary span { color: #7b8d89; font-size: 10px; }
.insight-product-summary b { margin-top: 6px; color: #2e746b; font-size: 20px; }
.insight-product-list { display: grid; gap: 8px; max-height: 440px; overflow: auto; }
.insight-product-list article { padding: 12px 14px; border: 1px solid #e1eae7; border-radius: 10px; }
.insight-product-list b, .insight-product-list span { display: block; }
.insight-product-list b { color: #344b46; font-size: 12px; }
.insight-product-list span { margin-top: 5px; color: #71837f; font-size: 11px; line-height: 1.6; }
@media (max-width: 860px) {
  .official-metrics { grid-template-columns: repeat(2, 1fr); }
  .analytics-charts { grid-template-columns: 1fr; }
  .evidence-banner { grid-template-columns: 52px 1fr; }
  .evidence-banner dl { display: none; }
  .insight-list { grid-template-columns: 1fr; }
}
@media (min-width: 861px) and (max-width: 1180px) { .insight-list { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (prefers-reduced-motion: reduce) {
  .class-overview { animation: none; }
  .insight-card { transition: none; }
}
</style>
