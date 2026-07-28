<template>
  <section v-if="run" class="product-agent-run" data-testid="product-agent-run">
    <header class="run-heading">
      <div class="run-mark">
        <span :class="['pulse', run.status]"></span>
        <i class="el-icon-cpu"></i>
      </div>
      <div>
        <span class="eyebrow">AGENT TEAM · DURABLE ACTIONS</span>
        <h3>{{ run.workflow_name }}</h3>
        <p>{{ statusDescription }}</p>
      </div>
      <el-tag :type="statusType" size="small">{{ statusLabel }}</el-tag>
      <el-button
        v-if="!isRunning"
        type="text"
        icon="el-icon-close"
        aria-label="收起 Agent 运行"
        @click="$emit('close')"
      />
    </header>

    <div class="node-track">
      <article
        v-for="(node, index) in agentNodes"
        :key="node.id"
        class="agent-node"
        data-testid="product-agent-node"
      >
        <div class="node-index">
          <span>{{ index + 1 }}</span>
          <i v-if="index < agentNodes.length - 1"></i>
        </div>
        <div class="node-body">
          <header>
            <div>
              <b>{{ node.agent_name || roleLabel(node.agent_role) }}</b>
              <small>{{ roleLabel(node.agent_role) }}</small>
            </div>
            <span :class="['node-status', node.status]">
              {{ nodeStatusLabel(node.status) }}
            </span>
          </header>

          <p v-if="outputSummary(node)" class="node-output">
            {{ outputSummary(node) }}
          </p>
          <div v-if="node.tool_calls && node.tool_calls.length" class="business-calls">
            <div
              v-for="call in node.tool_calls"
              :key="call.id"
              :class="['business-call', call.status]"
            >
              <i :class="isWrite(call.tool_name) ? 'el-icon-coin' : 'el-icon-view'"></i>
              <span>
                <b>{{ toolLabel(call.tool_name) }}</b>
                <small>{{ callSummary(call) }}</small>
              </span>
              <el-tag
                size="mini"
                :type="call.status === 'completed' ? 'success' : 'danger'"
              >
                {{ call.status === 'completed' && isWrite(call.tool_name)
                  ? '已写入 Education'
                  : call.status === 'completed' ? '读取完成' : '执行失败' }}
              </el-tag>
            </div>
          </div>
        </div>
      </article>
    </div>

    <el-alert
      v-if="run.error_summary"
      :title="run.error_summary"
      type="error"
      :closable="false"
      show-icon
    />
    <footer>
      <i class="el-icon-lock"></i>
      <span>课程、用户和角色由服务端授权；临时沙箱删除后，已采纳结果仍保存在 Education 数据库。</span>
    </footer>
  </section>
</template>

<script>
const TERMINAL_STATUSES = ['completed', 'awaiting_approval', 'partial', 'failed', 'cancelled']

export default {
  name: 'ProductAgentRunPanel',
  props: {
    run: {
      type: Object,
      default: null,
    },
  },
  data() {
    return {
      pollTimer: null,
      refreshing: false,
      emittedTerminalId: '',
    }
  },
  computed: {
    agentNodes() {
      return (this.run && this.run.nodes || []).filter(node => node.type === 'agent_task')
    },
    isRunning() {
      return Boolean(this.run && ['pending', 'running'].includes(this.run.status))
    },
    statusLabel() {
      const labels = {
        pending: '准备中',
        running: '协作中',
        completed: '已完成',
        awaiting_approval: '等待确认',
        partial: '部分完成',
        failed: '运行失败',
        cancelled: '已取消',
      }
      return labels[this.run && this.run.status] || '未知状态'
    },
    statusType() {
      if (!this.run) return 'info'
      if (['completed', 'awaiting_approval'].includes(this.run.status)) return 'success'
      if (['partial', 'failed', 'cancelled'].includes(this.run.status)) return 'danger'
      return 'warning'
    },
    statusDescription() {
      if (!this.run) return ''
      if (this.run.status === 'pending') return '正在创建隔离运行环境并投递任务。'
      if (this.run.status === 'running') return 'Agent 正在读取授权课程信息并执行受控业务工具。'
      if (this.run.status === 'completed') return 'Agent 已结束协作，业务写入结果可在当前页面继续使用。'
      if (this.run.status === 'awaiting_approval') return '草稿已生成，发布仍需要教师明确确认。'
      if (this.run.status === 'partial') return '保留已完成产物；未完成节点可重新运行。'
      if (this.run.status === 'failed') return '运行未完成，普通课程功能不受影响。'
      return '运行状态已更新。'
    },
  },
  watch: {
    run: {
      immediate: true,
      deep: true,
      handler(value) {
        this.syncPolling(value)
      },
    },
  },
  beforeDestroy() {
    this.stopPolling()
  },
  methods: {
    syncPolling(run) {
      if (!run) {
        this.stopPolling()
        return
      }
      if (['pending', 'running'].includes(run.status)) {
        if (!this.pollTimer) {
          this.pollTimer = window.setInterval(this.refresh, 2500)
        }
        return
      }
      this.stopPolling()
      if (TERMINAL_STATUSES.includes(run.status) && this.emittedTerminalId !== run.id) {
        this.emittedTerminalId = run.id
        this.$emit('terminal', run)
      }
    },
    async refresh() {
      if (!this.run || !this.run.id || this.refreshing) return
      this.refreshing = true
      try {
        await this.$store.dispatch('education/refreshProductAgentRun', this.run.id)
      } catch (error) {
        this.stopPolling()
        this.$emit('poll-error', error)
      } finally {
        this.refreshing = false
      }
    },
    stopPolling() {
      if (this.pollTimer) {
        window.clearInterval(this.pollTimer)
        this.pollTimer = null
      }
    },
    nodeStatusLabel(status) {
      const labels = {
        pending: '等待',
        running: '处理中',
        done: '完成',
        failed: '失败',
        skipped: '跳过',
      }
      return labels[status] || status || '等待'
    },
    roleLabel(role) {
      const labels = {
        course_designer: '课程设计',
        courseware_maker: '课件制作',
        exercise_generator: '习题生成',
        learning_analyst: '学情分析',
        learning_planner: '学习规划',
        practice_coach: '练习教练',
        note_organizer: '笔记整理',
        research_worker: '资料研究',
        teaching_reviewer: '教学审校',
      }
      return labels[role] || role || 'Education Agent'
    },
    outputSummary(node) {
      const output = node.output || {}
      if (typeof output === 'string') return output.slice(0, 240)
      return String(output.summary || output.text || '').slice(0, 240)
    },
    isWrite(name) {
      return ![
        'edu.course.list',
        'edu.course.members.list',
        'edu.course.context.get',
        'edu.question_bank.search',
        'edu.knowledge.search',
      ].includes(name)
    },
    toolLabel(name) {
      const labels = {
        'edu.course.members.list': '读取课程成员',
        'edu.course.context.get': '读取课程上下文',
        'edu.question_bank.search': '检索课程题库',
        'edu.knowledge.search': '检索课程知识资料',
        'edu.courseware.create': '保存课件草稿',
        'edu.student_insight.refresh': '刷新学生画像',
        'edu.mock_exam.create': '创建模拟考试',
        'edu.weakness.analyze': '生成弱点分析',
        'edu.mind_map.create': '创建课程思维导图',
      }
      return labels[name] || name
    },
    callSummary(call) {
      if (call.status !== 'completed') {
        return call.error_message || call.error_code || '工具执行失败'
      }
      const summary = call.result_summary || {}
      if (typeof summary.item_count === 'number') return `${summary.item_count} 项结果`
      if (summary.data_state) return `数据状态：${summary.data_state}`
      if (summary.id) return '业务对象已创建'
      return '服务端已记录完整审计'
    },
  },
}
</script>

<style scoped>
.product-agent-run {
  margin: 16px 0;
  overflow: hidden;
  border: 1px solid #d7e5e2;
  border-radius: 15px;
  background: linear-gradient(145deg, #fbfdfc, #f5faf8);
  box-shadow: 0 12px 32px rgba(43, 86, 77, .06);
}
.run-heading {
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 12px;
  padding: 16px 18px;
  border-bottom: 1px solid #e2ebe9;
  background: rgba(255, 255, 255, .72);
}
.run-mark {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  position: relative;
  background: #e6f2ef;
  color: #287c72;
  font-size: 18px;
}
.pulse {
  width: 8px;
  height: 8px;
  position: absolute;
  right: -2px;
  top: -2px;
  border: 2px solid #fff;
  border-radius: 50%;
  background: #98a6a3;
}
.pulse.pending, .pulse.running { background: #df9f3f; box-shadow: 0 0 0 4px rgba(223, 159, 63, .14); }
.pulse.completed, .pulse.awaiting_approval { background: #38a478; }
.pulse.failed, .pulse.partial { background: #ce6258; }
.eyebrow { color: #38857b; font-size: 8px; font-weight: 800; letter-spacing: .14em; }
.run-heading h3 { margin: 4px 0 2px; color: #2e433f; font-size: 14px; }
.run-heading p { margin: 0; color: #83908d; font-size: 10px; }
.node-track { display: grid; padding: 8px 18px 10px; }
.agent-node { display: grid; grid-template-columns: 28px minmax(0, 1fr); gap: 10px; }
.node-index { display: flex; flex-direction: column; align-items: center; }
.node-index span {
  width: 23px; height: 23px; display: grid; place-items: center;
  border: 1px solid #bcd5d0; border-radius: 50%; background: #fff;
  color: #3c8178; font-family: Georgia, serif; font-size: 10px;
}
.node-index i { width: 1px; flex: 1; min-height: 16px; background: #d8e5e2; }
.node-body { padding: 5px 0 13px; }
.node-body > header { display: flex; justify-content: space-between; gap: 10px; }
.node-body header b, .node-body header small { display: block; }
.node-body header b { color: #344a45; font-size: 12px; }
.node-body header small { margin-top: 2px; color: #94a09d; font-size: 8px; }
.node-status { color: #879591; font-size: 9px; }
.node-status.running { color: #c0822c; }
.node-status.done { color: #308368; }
.node-status.failed { color: #bf514b; }
.node-output { margin: 7px 0 0; color: #667873; font-size: 10px; line-height: 1.55; }
.business-calls { display: grid; gap: 6px; margin-top: 8px; }
.business-call {
  display: grid; grid-template-columns: 25px minmax(0, 1fr) auto;
  align-items: center; gap: 8px; padding: 8px 9px;
  border: 1px solid #dce9e6; border-radius: 8px; background: #fff;
}
.business-call > i { color: #3b8479; }
.business-call span b, .business-call span small { display: block; }
.business-call span b { color: #39514c; font-size: 10px; }
.business-call span small { margin-top: 2px; color: #899793; font-size: 8px; }
.business-call.failed { border-color: #edd9d6; background: #fffafa; }
.product-agent-run > .el-alert { margin: 0 18px 12px; }
.product-agent-run > footer {
  display: flex; gap: 7px; padding: 9px 18px;
  border-top: 1px solid #e3ebe9; color: #899793; font-size: 8px;
}
@media (max-width: 640px) {
  .run-heading { grid-template-columns: 42px 1fr auto; }
  .run-heading > .el-tag { display: none; }
  .run-heading > .el-button { grid-column: 3; grid-row: 1; }
  .business-call { grid-template-columns: 23px 1fr; }
  .business-call .el-tag { grid-column: 2; justify-self: start; }
}
</style>
