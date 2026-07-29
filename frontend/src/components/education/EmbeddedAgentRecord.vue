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
    <el-collapse-transition>
      <div v-show="expanded" class="record-detail">
        <ProductAgentRunPanel
          :run="run"
          @terminal="$emit('terminal', $event)"
          @poll-error="$emit('poll-error', $event)"
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
    return { expanded: false }
  },
  computed: {
    statusLabel() {
      const labels = {
        pending: '等待中', running: '进行中', completed: '已完成',
        failed: '需要处理', cancelled: '已取消',
      }
      return labels[this.run && this.run.status] || '已记录'
    },
    statusText() {
      if (!this.run) return ''
      if (this.run.status === 'completed') return '产物已写入 Education，可展开复核来源与工具调用。'
      if (this.run.status === 'failed') return '保留已有产物和失败信息，可展开查看。'
      return '后台 Agent 正在通过受控 Education 工具处理。'
    },
    statusType() {
      if (this.run && this.run.status === 'completed') return 'success'
      if (this.run && this.run.status === 'failed') return 'danger'
      return 'info'
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
.record-summary b { font-size: 11px; }.record-summary small { margin-top: 3px; color: #8b9a97; font-size: 9px; }
.record-detail { padding-top: 8px; }
@media (prefers-reduced-motion: reduce) {
  .record-summary { transition: none; }
  .record-summary:hover { transform: none; }
}
</style>
