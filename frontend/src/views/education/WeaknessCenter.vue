<template>
  <EducationShell
    title="作业弱点"
    :subtitle="course ? `${course.title} · 用具体错题证据解释需要复习的内容` : '选择一门学生课程'"
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
        @click="analyzeWithAgent"
      >Agent 分析弱点</el-button>
    </template>

    <el-alert
      v-if="roleError"
      title="当前没有学生课程"
      type="warning"
      :closable="false"
      show-icon
    />

    <template v-else-if="course">
      <ProductAgentRunPanel
        :run="productAgentRun"
        @terminal="handleAgentTerminal"
        @poll-error="$message.error('Agent 运行状态暂时无法刷新')"
        @close="closeAgentRun"
      />

      <section class="weakness-header">
        <div class="header-copy">
          <span>TRACEABLE LEARNING DIAGNOSIS</span>
          <h2>{{ ready ? '这些是当前证据支持的复习重点' : '完成练习后，再形成你的弱点分析' }}</h2>
          <p>系统不会根据聊天内容推测能力。每一项弱点都列出作答次数、错误次数和原始题目版本。</p>
        </div>
        <div class="evidence-count">
          <b>{{ evidence.length }}</b>
          <span>条作答证据</span>
        </div>
      </section>

      <div v-if="ready" class="weakness-layout">
        <section class="weakness-column">
          <header><b>复习优先级</b><span>{{ weaknesses.length }} 个知识点</span></header>
          <article
            v-for="(item, index) in weaknesses"
            :key="item.knowledge_point"
            class="weakness-card"
          >
            <span class="priority">{{ String(index + 1).padStart(2, '0') }}</span>
            <div class="weakness-main">
              <header>
                <h3>{{ item.knowledge_point }}</h3>
                <b>{{ Math.round(item.error_rate * 100) }}%</b>
              </header>
              <el-progress
                :percentage="Math.round(item.error_rate * 100)"
                :show-text="false"
                :stroke-width="7"
                color="#c98264"
              />
              <footer>
                <span>尝试 {{ item.attempted_count }} 次</span>
                <span>错误 {{ item.wrong_count }} 次</span>
                <span>{{ evidenceCount(item) }} 个题目版本</span>
              </footer>
            </div>
          </article>
          <div v-if="!weaknesses.length" class="all-clear">
            <i class="el-icon-circle-check"></i>
            <div><b>当前没有错误聚集</b><p>继续完成更多练习，分析会随证据更新。</p></div>
          </div>
        </section>

        <section class="action-column">
          <header><b>下一步怎么学</b><span>基于同一批证据</span></header>
          <article
            v-for="recommendation in recommendations"
            :key="recommendation.knowledge_point"
            class="action-card"
          >
            <span><i class="el-icon-guide"></i></span>
            <div>
              <b>{{ recommendation.knowledge_point }}</b>
              <p>{{ recommendation.action }}</p>
              <small>建议补练 {{ recommendation.recommended_question_count }} 题</small>
            </div>
          </article>
          <button type="button" class="new-exam" @click="openMockExam">
            <i class="el-icon-document-checked"></i>
            <span><b>生成一份针对性模拟考试</b><small>从课程已发布题库继续练习</small></span>
            <i class="el-icon-right"></i>
          </button>
        </section>
      </div>

      <section
        v-if="ready"
        class="evidence-ledger"
        data-testid="weakness-evidence"
      >
        <header><div><h3>证据账本</h3><p>点击查看每次作答与参考解析，不隐藏弱点结论的来源。</p></div></header>
        <article v-for="(row, index) in evidence" :key="`${row.attempt_id}-${row.item_version_id}`">
          <span :class="['result-mark', row.correct ? 'correct' : 'wrong']">
            <i :class="row.correct ? 'el-icon-check' : 'el-icon-close'"></i>
          </span>
          <div>
            <b>题目证据 {{ index + 1 }}</b>
            <p>{{ (row.knowledge_points || []).join(' · ') || '未标注知识点' }}</p>
          </div>
          <span>{{ row.difficulty === 'easy' ? '简单' : row.difficulty === 'hard' ? '困难' : '中等' }}</span>
          <span>{{ row.submitted_answer || '未作答' }} → {{ row.correct_answer }}</span>
          <el-popover placement="left" width="340" trigger="click">
            <p>{{ row.explanation || '暂无解析' }}</p>
            <small>题目版本：{{ row.item_version_id }}</small>
            <el-button slot="reference" size="mini" type="text">查看解析</el-button>
          </el-popover>
        </article>
      </section>

      <section v-if="!ready" class="insufficient-panel">
        <div class="empty-orbit"><span></span><i class="el-icon-data-analysis"></i></div>
        <h2>数据不足</h2>
        <p>至少完成一份模拟考试或已发布作业后，系统才能从真实错误中提取弱点。</p>
        <el-button type="primary" @click="openMockExam">去完成模拟考试</el-button>
      </section>
    </template>
  </EducationShell>
</template>

<script>
import EducationShell from '../../components/education/EducationShell.vue'
import ProductAgentRunPanel from '../../components/education/ProductAgentRunPanel.vue'

export default {
  name: 'WeaknessCenter',
  components: { EducationShell, ProductAgentRunPanel },
  data() {
    return {
      roleError: false,
      refreshing: false,
    }
  },
  computed: {
    course() { return this.$store.getters['education/activeCourse'] },
    weakness() { return this.$store.getters['education/weakness'] || {} },
    ready() { return this.weakness.data_state === 'ready' },
    evidence() { return this.weakness.evidence || [] },
    weaknesses() { return this.weakness.weaknesses || [] },
    recommendations() { return this.weakness.recommendations || [] },
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
          role: 'student',
        })
        await this.load(course.id)
      } catch (error) {
        this.roleError = true
      }
    },
    async load(courseId) {
      try {
        await this.$store.dispatch('education/fetchWeakness', courseId)
        await this.$store.dispatch('education/restoreProductAgentRun', {
          courseId,
          productCode: 'weakness_analysis',
        })
      } catch (error) {
        this.$message.error('弱点分析加载失败')
      }
    },
    async refresh() {
      this.refreshing = true
      try {
        await this.$store.dispatch('education/refreshWeakness', this.course.id)
        this.$message.success('已按最新学习证据重新分析')
      } catch (error) {
        this.$message.error('分析失败')
      } finally {
        this.refreshing = false
      }
    },
    async analyzeWithAgent() {
      try {
        await this.$store.dispatch('education/startProductAgentRun', {
          course_id: this.course.id,
          product_code: 'weakness_analysis',
          options: {},
        })
        this.$message.success('练习教练与学习规划 Agent 已启动')
      } catch (error) {
        const detail = error.response && error.response.data && error.response.data.error
        this.$message.error(detail || '弱点分析 Agent 启动失败')
      }
    },
    async handleAgentTerminal(run) {
      if (run.status === 'completed') {
        await this.$store.dispatch('education/fetchWeakness', this.course.id)
        this.$message.success('Agent 已按最新证据完成弱点分析')
      }
    },
    closeAgentRun() {
      this.$store.commit('education/SET_PRODUCT_AGENT_RUN', null)
    },
    evidenceCount(item) {
      // The API exposes immutable references as evidence_item_version_ids.
      return (item.evidence_item_version_ids || []).length
    },
    openMockExam() {
      this.$router.push({
        path: '/education/student/mock-exams',
        query: { courseId: this.course.id },
      })
    },
  },
}
</script>

<style scoped>
.weakness-header { display: grid; grid-template-columns: 1fr auto; align-items: center; gap: 20px; margin-bottom: 15px; padding: 22px 26px; border: 1px solid #e5dfd7; border-radius: 15px; background: linear-gradient(105deg, #fdfbf8, #f7f1ea); }
.header-copy > span { color: #a07155; font-size: 9px; font-weight: 800; letter-spacing: .14em; }.header-copy h2 { margin: 6px 0; color: #4b3e37; font-family: 'Noto Serif SC', 'Songti SC', SimSun, serif; font-size: 19px; }.header-copy p { margin: 0; color: #8d8079; font-size: 10px; line-height: 1.55; }
.evidence-count { min-width: 96px; padding-left: 22px; border-left: 1px solid #e1d7cc; text-align: center; }.evidence-count b, .evidence-count span { display: block; }.evidence-count b { color: #a26047; font-family: Georgia, serif; font-size: 28px; }.evidence-count span { color: #9a8c83; font-size: 9px; }
.weakness-layout { display: grid; grid-template-columns: 1.25fr .75fr; gap: 14px; margin-bottom: 14px; }
.weakness-column, .action-column, .evidence-ledger { padding: 18px; border: 1px solid #e3e9e7; border-radius: 13px; background: #fff; }
.weakness-column > header, .action-column > header { display: flex; justify-content: space-between; margin-bottom: 11px; color: #52645f; font-size: 11px; }.weakness-column > header span, .action-column > header span { color: #97a29f; font-size: 9px; }
.weakness-card { display: grid; grid-template-columns: 34px 1fr; gap: 11px; padding: 14px 3px; border-bottom: 1px solid #edf1f0; }.priority { color: #be7357; font-family: Georgia, serif; font-size: 13px; }
.weakness-main > header { display: flex; justify-content: space-between; margin-bottom: 8px; }.weakness-main h3 { margin: 0; color: #3f514d; font-size: 12px; }.weakness-main header b { color: #bb7055; font-family: Georgia, serif; }
.weakness-main footer { display: flex; gap: 13px; margin-top: 7px; color: #929e9b; font-size: 8px; }
.all-clear { min-height: 150px; display: flex; align-items: center; justify-content: center; gap: 12px; color: #4c9270; }.all-clear i { font-size: 24px; }.all-clear b { color: #49645c; }.all-clear p { margin: 3px 0 0; color: #93a09c; font-size: 9px; }
.action-card { display: grid; grid-template-columns: 33px 1fr; gap: 9px; padding: 12px 0; border-bottom: 1px solid #edf1f0; }.action-card > span { width: 31px; height: 31px; display: grid; place-items: center; border-radius: 9px; background: #edf4f2; color: #3c8176; }.action-card b { color: #475b56; font-size: 11px; }.action-card p { margin: 5px 0; color: #7b8986; font-size: 9px; line-height: 1.55; }.action-card small { color: #a07155; font-size: 8px; }
.new-exam { width: 100%; display: grid; grid-template-columns: 34px 1fr auto; align-items: center; gap: 9px; margin-top: 13px; padding: 13px; border: 1px solid #d5e5e1; border-radius: 10px; background: #f4f9f7; color: #367c72; cursor: pointer; text-align: left; }.new-exam span b, .new-exam span small { display: block; }.new-exam span b { color: #405751; font-size: 10px; }.new-exam span small { margin-top: 3px; color: #8d9b97; font-size: 8px; }
.evidence-ledger > header { padding-bottom: 12px; border-bottom: 1px solid #edf1f0; }.evidence-ledger h3 { margin: 0; color: #425651; font-size: 13px; }.evidence-ledger header p { margin: 4px 0 0; color: #909c99; font-size: 9px; }
.evidence-ledger > article { display: grid; grid-template-columns: 30px 1fr 60px 100px 60px; align-items: center; gap: 10px; padding: 11px 3px; border-bottom: 1px solid #f0f3f2; color: #74837f; font-size: 9px; }.result-mark { width: 26px; height: 26px; display: grid; place-items: center; border-radius: 50%; background: #f7e9e4; color: #b8664e; }.result-mark.correct { background: #e7f4ec; color: #3b8964; }.evidence-ledger article b { color: #435650; font-size: 10px; }.evidence-ledger article p { margin: 3px 0 0; color: #929e9b; font-size: 8px; }
.insufficient-panel { min-height: 430px; display: flex; flex-direction: column; align-items: center; justify-content: center; border: 1px dashed #d4dfdc; border-radius: 14px; background: #fafcfb; text-align: center; }.empty-orbit { width: 90px; height: 90px; display: grid; place-items: center; border: 1px solid #cbdcd7; border-radius: 50%; position: relative; color: #4d8c82; font-size: 28px; }.empty-orbit span { position: absolute; width: 112px; height: 50px; border: 1px solid #dce7e4; border-radius: 50%; transform: rotate(-25deg); }.insufficient-panel h2 { margin: 18px 0 7px; color: #536963; font-family: 'Noto Serif SC', 'Songti SC', SimSun, serif; }.insufficient-panel p { max-width: 430px; margin: 0 0 17px; color: #8c9996; font-size: 10px; line-height: 1.6; }
@media (max-width: 940px) { .weakness-layout { grid-template-columns: 1fr; } }
@media (max-width: 700px) { .evidence-ledger > article { grid-template-columns: 30px 1fr auto; }.evidence-ledger > article > span:nth-of-type(n+2) { display: none; } }
</style>
