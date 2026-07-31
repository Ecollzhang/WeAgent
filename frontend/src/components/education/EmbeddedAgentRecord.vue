<template>
  <section v-if="run" class="embedded-agent-record" data-testid="embedded-agent-record">
    <button type="button" class="record-summary" @click="expanded = !expanded">
      <span class="record-icon"><i class="el-icon-magic-stick"></i></span>
      <span>
        <b>{{ title }}</b>
        <small>{{ statusText }}</small>
      </span>
      <el-tag size="mini" :type="statusType">{{ statusLabel }}</el-tag>
      <i :class="expanded ? 'el-icon-arrow-up' : 'el-icon-arrow-down'"></i>
    </button>
    <div class="record-actions">
      <button type="button" @click="openConversation(run)">
        <i class="el-icon-chat-dot-round"></i> 返回本次聊天
      </button>
      <button v-if="adoptedObject" type="button" @click="previewLatestArtifact">
        <i class="el-icon-view"></i> 预览最新产物
      </button>
      <button v-if="run.business_route" type="button" @click="openBusinessPage">
        <i class="el-icon-link"></i> 返回业务页面
      </button>
      <button type="button" @click="historyExpanded = !historyExpanded">
        <i class="el-icon-time"></i> 协作历史 {{ historyRuns.length }}
      </button>
    </div>
    <el-collapse-transition>
      <div v-show="historyExpanded" class="history-list">
        <button
          v-for="item in historyRuns"
          :key="item.id"
          type="button"
          class="history-item"
          @click="openConversation(item)"
        >
          <span>
            <b>{{ item.workflow_name || title }}</b>
            <small>{{ formatDate(item.started_at || item.created_at) }}</small>
          </span>
          <span>{{ item.completed_agent_count || 0 }}/{{ item.agent_count || 0 }} Agent</span>
          <i class="el-icon-right"></i>
        </button>
      </div>
    </el-collapse-transition>
    <el-collapse-transition>
      <div v-show="expanded" class="record-detail">
        <ProductAgentRunPanel
          :run="run"
          @terminal="$emit('terminal', $event)"
          @poll-error="$emit('poll-error', $event)"
          @recover-draft="$emit('recover-draft', $event)"
          @close="$emit('close')"
        />
      </div>
    </el-collapse-transition>
  </section>
</template>

<script>
import ProductAgentRunPanel from './ProductAgentRunPanel.vue'

export default {
  name: 'EmbeddedAgentRecord',
  components: { ProductAgentRunPanel },
  props: {
    run: { type: Object, default: null },
    title: { type: String, default: 'AI 生成记录' },
  },
  data() {
    return { expanded: false, historyExpanded: false }
  },
  computed: {
    historyRuns() {
      const runs = this.$store.getters['education/productAgentRuns'] || []
      return runs.length ? runs : [this.run]
    },
    adoptedObject() {
      return (this.run && this.run.output && this.run.output.adopted_object) || null
    },
    statusLabel() {
      const labels = {
        pending: '等待中',
        running: '进行中',
        completed: '已完成',
        failed: '需要处理',
        cancelled: '已取消',
      }
      return labels[this.run && this.run.status] || '已记录'
    },
    statusText() {
      if (!this.run) return ''
      if (this.run.status === 'completed') return '产物已写入 Education，可展开复核来源与工具调用。'
      if (this.run.status === 'failed') return '已保留现有产物和失败信息，可展开查看。'
      return '后台 Agent 正在通过受控 Education 工具处理。'
    },
    statusType() {
      if (this.run && this.run.status === 'completed') return 'success'
      if (this.run && this.run.status === 'failed') return 'danger'
      return 'info'
    },
  },
  methods: {
    openConversation(item) {
      if (!item || !item.conversation_id) return
      this.$router.push({
        path: '/dashboard',
        query: { conversation_id: item.conversation_id },
      })
    },
    previewLatestArtifact() {
      if (!this.adoptedObject) return
      this.$emit('preview', { run: this.run, adoptedObject: this.adoptedObject })
    },
    openBusinessPage() {
      if (!this.run || !this.run.business_route) return
      const route = this.run.business_route
      const target = typeof route === 'string'
        ? route
        : this.$router.resolve(route).route.fullPath
      if (this.$route.fullPath !== target) this.$router.push(route)
    },
    formatDate(value) {
      if (!value) return '时间待记录'
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return String(value)
      return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      })
    },
  },
}
</script>

<style scoped>
.embedded-agent-record { margin: 0 0 16px; }
.record-summary {
  width: 100%; display: grid; grid-template-columns: 36px 1fr auto 14px;
  align-items: center; gap: 10px; padding: 10px 13px; border: 1px solid #dfe9e6;
  border-radius: 11px; background: #fbfdfc; color: #3c514d; cursor: pointer;
  text-align: left; transition: border-color 160ms ease, transform 160ms ease;
}
.record-summary:hover { transform: translateY(-1px); border-color: #a8cbc4; }
.record-icon { width: 32px; height: 32px; display: grid; place-items: center; border-radius: 9px; background: #e7f2ef; color: #2e7e73; }
.record-summary b, .record-summary small { display: block; }
.record-summary b { font-size: 11px; }
.record-summary small { margin-top: 3px; color: #8b9a97; font-size: 9px; }
.record-actions { display: flex; flex-wrap: wrap; gap: 7px; padding: 8px 2px 0; }
.record-actions button {
  border: 0; border-radius: 8px; padding: 6px 9px; background: #eef6f4;
  color: #2e746b; font-size: 11px; cursor: pointer;
}
.record-actions button:hover { background: #dfeeea; }
.history-list {
  display: grid; gap: 6px; margin-top: 8px; padding: 8px;
  border: 1px solid #e4ecea; border-radius: 10px; background: #fff;
}
.history-item {
  display: grid; grid-template-columns: 1fr auto 14px; align-items: center; gap: 10px;
  width: 100%; padding: 8px; border: 0; border-radius: 8px; background: #f7faf9;
  text-align: left; color: #48615c; cursor: pointer;
}
.history-item:hover { background: #edf5f3; }
.history-item b, .history-item small { display: block; }
.history-item b { font-size: 11px; }
.history-item small, .history-item > span:last-of-type { margin-top: 2px; color: #8b9a97; font-size: 9px; }
.record-detail { padding-top: 8px; }
@media (prefers-reduced-motion: reduce) {
  .record-summary { transition: none; }
  .record-summary:hover { transform: none; }
}
</style>
