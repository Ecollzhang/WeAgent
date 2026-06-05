<template>
  <div class="diff-view-card">
    <div class="diff-header">
      <div class="diff-title">
        <i class="el-icon-document"></i>
        <span>{{ fileName }}</span>
      </div>
      <div class="diff-meta">
        <span class="stat stat-add">+{{ additions }}</span>
        <span class="stat stat-del">-{{ deletions }}</span>
        <el-tag v-if="isApplied" size="mini" type="success">已应用</el-tag>
      </div>
    </div>

    <div class="diff-toolbar">
      <el-radio-group v-model="viewMode" size="mini">
        <el-radio-button label="diff">Diff</el-radio-button>
        <el-radio-button label="after">修改后</el-radio-button>
      </el-radio-group>
      <div class="toolbar-actions">
        <el-button size="mini" type="text" @click="copyText(activeText)">复制</el-button>
        <el-button
          v-if="canApply"
          size="mini"
          type="primary"
          :loading="saving"
          @click="applyDiff"
        >应用修改</el-button>
      </div>
    </div>

    <div v-if="viewMode === 'diff'" class="diff-lines">
      <div
        v-for="(line, index) in parsedDiff"
        :key="index"
        class="diff-line"
        :class="line.type"
      >
        <span class="line-num old">{{ line.oldNum || '' }}</span>
        <span class="line-num new">{{ line.newNum || '' }}</span>
        <span class="line-content">{{ line.content }}</span>
      </div>
      <div v-if="!parsedDiff.length" class="empty-state">暂无 diff 内容</div>
    </div>

    <pre v-else class="code-panel"><code>{{ activeText }}</code></pre>
  </div>
</template>

<script>
import { writeFile } from '@/api/sandbox'

export default {
  name: 'DiffViewCard',
  props: {
    element: { type: Object, required: true },
    sessionId: { type: String, default: '' },
  },
  data() {
    return {
      viewMode: 'diff',
      saving: false,
    }
  },
  computed: {
    data() {
      return this.element?.data || {}
    },
    fileName() {
      return this.data.filename || this.data.path || '变更'
    },
    additions() {
      return this.data.diff_stat?.additions || 0
    },
    deletions() {
      return this.data.diff_stat?.deletions || 0
    },
    isApplied() {
      return !!this.data.applied
    },
    canApply() {
      return !!this.sessionId && !!this.data.path && typeof this.data.after === 'string' && !this.isApplied
    },
    activeText() {
      if (this.viewMode === 'diff') return this.data.diff_text || this.element?.content || ''
      return this.data.after_preview || this.data.after || ''
    },
    parsedDiff() {
      const diffText = this.data.diff_text || this.element?.content || ''
      if (!diffText) return []

      const result = []
      let oldLine = 0
      let newLine = 0
      diffText.split('\n').forEach(raw => {
        if (!raw) return
        if (raw.startsWith('@@')) {
          const match = raw.match(/@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/)
          if (match) {
            oldLine = Number(match[1]) - 1
            newLine = Number(match[2]) - 1
          }
          return
        }
        if (raw.startsWith('---') || raw.startsWith('+++')) return
        if (raw.startsWith('-')) {
          oldLine += 1
          result.push({ type: 'del', oldNum: oldLine, newNum: '', content: raw.slice(1) })
          return
        }
        if (raw.startsWith('+')) {
          newLine += 1
          result.push({ type: 'add', oldNum: '', newNum: newLine, content: raw.slice(1) })
          return
        }
        oldLine += 1
        newLine += 1
        result.push({
          type: 'ctx',
          oldNum: oldLine,
          newNum: newLine,
          content: raw.startsWith(' ') ? raw.slice(1) : raw,
        })
      })
      return result
    },
  },
  watch: {
    element: {
      immediate: true,
      deep: true,
      handler() {
        this.logDiffCardDebug('element-change')
      },
    },
  },
  mounted() {
    this.logDiffCardDebug('mounted')
  },
  updated() {
    this.logDiffCardDebug('updated')
  },
  methods: {
    logDiffCardDebug(stage) {
      const stamp = typeof performance !== 'undefined' && performance.now ? performance.now().toFixed(1) : Date.now()
      console.log(`[AWB DEBUG][DiffViewCard][${stamp}] ${stage}`, {
        fileName: this.fileName,
        path: this.data.path || '',
        diffLength: (this.data.diff_text || this.element?.content || '').length,
        parsedLines: this.parsedDiff.length,
        canApply: this.canApply,
        isApplied: this.isApplied,
        viewMode: this.viewMode,
      })
    },
    async copyText(text) {
      try {
        await navigator.clipboard.writeText(text || '')
        this.$message.success('已复制')
      } catch (error) {
        const textarea = document.createElement('textarea')
        textarea.value = text || ''
        document.body.appendChild(textarea)
        textarea.select()
        document.execCommand('copy')
        document.body.removeChild(textarea)
        this.$message.success('已复制')
      }
    },
    async applyDiff() {
      if (!this.canApply) return
      this.saving = true
      try {
        await writeFile(this.sessionId, this.data.path, this.data.after)
        this.$emit('applied', { path: this.data.path, content: this.data.after })
        this.$message.success('Diff 已应用')
      } catch (error) {
        this.$message.error(error?.message || '应用 diff 失败')
      } finally {
        this.saving = false
      }
    },
  },
}
</script>

<style scoped>
.diff-view-card {
  border: 1px solid #d8e2ef;
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
}

.diff-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: #f7faff;
  border-bottom: 1px solid #e6eef8;
}

.diff-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #22324d;
}

.diff-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.stat {
  font-size: 12px;
  font-weight: 600;
}

.stat-add {
  color: #1f9d55;
}

.stat-del {
  color: #d64545;
}

.diff-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #fff;
  border-bottom: 1px solid #edf2f7;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.diff-lines {
  max-height: 360px;
  overflow: auto;
  background: #fbfdff;
}

.diff-line {
  display: flex;
  font-family: Consolas, 'SFMono-Regular', Menlo, monospace;
  font-size: 12px;
  line-height: 1.6;
}

.diff-line.ctx {
  background: #fbfdff;
}

.diff-line.add {
  background: #eefbf3;
}

.diff-line.del {
  background: #fff1f1;
}

.line-num {
  width: 44px;
  min-width: 44px;
  padding: 0 8px 0 0;
  text-align: right;
  color: #8da0b8;
  user-select: none;
}

.line-content {
  flex: 1;
  padding: 0 12px 0 6px;
  white-space: pre;
}

.code-panel {
  margin: 0;
  max-height: 360px;
  overflow: auto;
  padding: 12px;
  background: #f8fbff;
  color: #1f2937;
}

.empty-state {
  padding: 18px 12px;
  text-align: center;
  font-size: 12px;
  color: #8da0b8;
}
</style>
