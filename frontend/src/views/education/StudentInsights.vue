<template>
  <EducationShell
    title="学生画像与评估"
    :subtitle="course ? `${course.title} · 只依据提交、考试与评分证据` : '选择一门教师课程'"
  >
    <template #actions>
      <el-button
        type="primary"
        icon="el-icon-refresh"
        :loading="refreshing"
        :disabled="!course"
        @click="refresh"
      >刷新画像</el-button>
    </template>

    <el-alert
      v-if="roleError"
      title="当前没有教师课程"
      type="warning"
      :closable="false"
      show-icon
    />
    <template v-else-if="course">
      <section class="evidence-banner">
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
        v-loading="loading"
        class="insight-list"
        data-testid="student-insight-list"
      >
        <article v-for="row in studentRows" :key="row.user_id" class="insight-card">
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
                <span>正确率</span>
                <b>{{ percent(row.insight.summary.accuracy) }}</b>
              </div>
              <div>
                <span>证据题</span>
                <b>{{ row.insight.summary.evidence_count || 0 }}</b>
              </div>
              <div>
                <span>模拟考试</span>
                <b>{{ row.insight.summary.attempt_count || 0 }}</b>
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
            <p><b>数据不足</b><span>学生完成已发布作业或模拟考试后，这里才会形成可解释画像。</span></p>
          </div>
        </article>
        <div v-if="!loading && !studentRows.length" class="empty-roster">
          <i class="el-icon-user"></i>
          <h3>课程中还没有学生</h3>
          <p>回到教学空间，通过邀请码或 Agent 名单工具添加学生。</p>
        </div>
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
            <b>模拟考试</b>
            <small>{{ dateLabel(evidence.submitted_at) }}</small>
            <p>得分 {{ scoreLabel(evidence.score, evidence.max_score) }} · 正确率 {{ percent(evidence.accuracy) }}</p>
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
  </EducationShell>
</template>

<script>
import EducationShell from '../../components/education/EducationShell.vue'

export default {
  name: 'StudentInsights',
  components: { EducationShell },
  data() {
    return {
      roleError: false,
      loading: false,
      refreshing: false,
      evidenceDrawer: false,
      selectedRow: null,
    }
  },
  computed: {
    course() { return this.$store.getters['education/activeCourse'] },
    members() { return this.$store.getters['education/members'] || [] },
    insights() { return this.$store.getters['education/studentInsights'] || [] },
    studentRows() {
      return this.members
        .filter(member => member.role === 'student')
        .map(member => ({
          ...member,
          insight: this.insights.find(item => item.student_user_id === member.user_id) || null,
        }))
    },
    readyCount() {
      return this.studentRows.filter(row => row.insight && row.insight.data_state === 'ready').length
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
        ])
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
        this.$message.success('画像已按最新学习证据刷新')
      } catch (error) {
        this.$message.error('画像刷新失败')
      } finally {
        this.refreshing = false
      }
    },
    openEvidence(row) {
      this.selectedRow = row
      this.evidenceDrawer = true
    },
    initials(name) {
      const value = String(name || '学')
      return value.slice(-2)
    },
    percent(value) {
      return typeof value === 'number' ? `${Math.round(value * 100)}%` : '—'
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
.insight-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); gap: 14px; min-height: 300px; }
.insight-card { padding: 17px; border: 1px solid #e0e8e6; border-radius: 13px; background: #fff; box-shadow: 0 8px 24px rgba(40, 73, 68, .04); }
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
@media (max-width: 860px) {
  .evidence-banner { grid-template-columns: 52px 1fr; }
  .evidence-banner dl { display: none; }
}
</style>

