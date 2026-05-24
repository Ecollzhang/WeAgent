<template>
  <div class="deploy-card">
    <div class="deploy-header">
      <span class="deploy-title">
        <i class="el-icon-upload"></i> 部署
        <span class="deploy-id" v-if="localData.deploy_id">#{{ localData.deploy_id.slice(0, 8) }}</span>
      </span>
      <el-tag size="mini" :type="statusTag">{{ statusText }}</el-tag>
    </div>

    <div class="deploy-body">
      <div class="deploy-progress">
        <el-progress :percentage="localData.progress || 0" :status="progressStatus" :stroke-width="8"></el-progress>
      </div>

      <div class="deploy-info" v-if="localData.preview_url && localData.status === 'success'">
        <div class="info-row">
          <span class="info-label">预览地址</span>
          <a :href="localData.preview_url" target="_blank" rel="noopener" class="info-url">{{ localData.preview_url }}</a>
          <el-button size="mini" type="text" @click="copyUrl(localData.preview_url)">复制</el-button>
        </div>
      </div>

      <div class="deploy-logs" v-if="localData.logs && localData.logs.length > 0">
        <div class="logs-header">部署日志</div>
        <div class="logs-body" ref="logsBody">
          <div v-for="(log, i) in localData.logs" :key="i" class="log-line">
            <span class="log-time">{{ formatTime(i) }}</span>
            <span class="log-msg">{{ log }}</span>
          </div>
        </div>
      </div>

      <div class="deploy-error" v-if="localData.error">
        <i class="el-icon-warning"></i> {{ localData.error }}
      </div>
    </div>

    <div class="deploy-footer" v-if="localData.status === 'success'">
      <el-button size="mini" type="primary" @click="openPreview">打开预览</el-button>
    </div>
  </div>
</template>

<script>
import { getDeploy } from '../../api/deploy'

export default {
  name: 'DeployStatusCard',
  props: {
    data: { type: Object, required: true },
  },
  data() {
    return {
      pollTimer: null,
      localData: { ...this.data },
    }
  },
  computed: {
    statusText() {
      const map = { pending: '等待中', deploying: '部署中', success: '已部署', failed: '失败' }
      return map[this.localData.status] || this.localData.status
    },
    statusTag() {
      const map = { pending: 'info', deploying: 'warning', success: 'success', failed: 'danger' }
      return map[this.localData.status] || 'info'
    },
    progressStatus() {
      if (this.localData.status === 'success') return 'success'
      if (this.localData.status === 'failed') return 'exception'
      return ''
    },
  },
  watch: {
    'data.status': {
      immediate: true,
      handler(val) {
        this.localData = { ...this.data }
        if (val === 'pending' || val === 'deploying') {
          this.startPoll()
        } else {
          this.stopPoll()
        }
      },
    },
    'data.progress'(val) { this.localData.progress = val },
    'data.logs': {
      handler(val) {
        if (val) this.localData.logs = [...val]
        this.$nextTick(() => {
          const el = this.$refs.logsBody
          if (el) el.scrollTop = el.scrollHeight
        })
      },
      deep: true,
    },
    'data.preview_url'(val) { if (val) this.localData.preview_url = val },
    'data.status'(val) { this.localData.status = val },
  },
  mounted() {
    if (this.localData.status === 'pending' || this.localData.status === 'deploying') {
      this.startPoll()
    }
  },
  beforeDestroy() { this.stopPoll() },
  methods: {
    startPoll() {
      this.stopPoll()
      this.pollTimer = setInterval(() => this._poll(), 2000)
    },
    stopPoll() {
      if (this.pollTimer) { clearInterval(this.pollTimer); this.pollTimer = null }
    },
    async _poll() {
      if (!this.localData.deploy_id) return
      try {
        const res = await getDeploy(this.localData.deploy_id)
        if (res.code === 200) {
          const d = res.data
          this.localData.status = d.status
          this.localData.progress = d.progress
          if (d.logs) this.localData.logs = d.logs
          if (d.preview_url) this.localData.preview_url = d.preview_url
          if (d.deploy_url) this.localData.deploy_url = d.deploy_url
          if (d.error) this.localData.error = d.error
          if (d.status === 'success' || d.status === 'failed') this.stopPoll()
        }
      } catch (e) {
        // Silently retry
      }
    },
    formatTime(i) {
      const sec = i * 3
      const m = String(Math.floor(sec / 60)).padStart(2, '0')
      const s = String(sec % 60).padStart(2, '0')
      return `${m}:${s}`
    },
    openPreview() {
      if (this.localData.preview_url) window.open(this.localData.preview_url, '_blank')
    },
    async copyUrl(url) {
      try {
        await navigator.clipboard.writeText(url)
        this.$message.success('已复制')
      } catch {
        const ta = document.createElement('textarea')
        ta.value = url; document.body.appendChild(ta); ta.select()
        document.execCommand('copy'); document.body.removeChild(ta)
        this.$message.success('已复制')
      }
    },
  },
}
</script>

<style scoped>
.deploy-card {
  border: 1px solid #e8eaed;
  border-radius: 8px;
  overflow: hidden;
}
.deploy-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f8f9fa;
  border-bottom: 1px solid #e8eaed;
}
.deploy-title { font-size: 12px; color: #1e293b; font-weight: 500; flex: 1; display: flex; align-items: center; gap: 6px; }
.deploy-id { font-size: 10px; color: #94a3b8; font-weight: 400; }
.deploy-title i { margin-right: 4px; color: #4080ff; }
.deploy-body { padding: 12px; }
.deploy-progress { margin-bottom: 12px; }
.deploy-info { margin-bottom: 10px; }
.info-row { display: flex; align-items: center; gap: 8px; font-size: 12px; }
.info-label { color: #64748b; flex-shrink: 0; }
.info-url { color: #4080ff; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; text-decoration: none; }
.info-url:hover { text-decoration: underline; }
.deploy-logs { background: #1e293b; border-radius: 6px; padding: 8px; margin-bottom: 8px; max-height: 120px; overflow: hidden; }
.logs-header { font-size: 11px; color: #94a3b8; margin-bottom: 4px; text-transform: uppercase; }
.logs-body { max-height: 80px; overflow-y: auto; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 11px; }
.log-line { display: flex; gap: 8px; padding: 1px 0; }
.log-time { color: #64748b; flex-shrink: 0; }
.log-msg { color: #e2e8f0; }
.deploy-error { color: #f56c6c; font-size: 12px; display: flex; align-items: center; gap: 4px; }
.deploy-footer { padding: 8px 12px; border-top: 1px solid #e8eaed; background: #f8f9fa; text-align: right; }
</style>
