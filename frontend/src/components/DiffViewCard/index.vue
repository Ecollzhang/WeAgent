<template>
  <div class="diff-view-card">
    <div class="diff-header">
      <span class="diff-filename" v-if="data.filename">
        <i class="el-icon-document"></i> {{ data.filename }}
      </span>
      <el-tag size="mini" type="primary" v-if="data.language">{{ data.language }}</el-tag>
      <div class="diff-toggle">
        <el-switch
          v-model="showDiff"
          active-text="Diff对比"
          inactive-text="代码"
          size="small"
        ></el-switch>
      </div>
    </div>

    <!-- Code view (default) -->
    <div v-if="!showDiff" class="diff-code-view">
      <pre class="code-body"><code>{{ data.after }}</code></pre>
      <div class="diff-actions">
        <el-button size="mini" type="text" @click="copyCode(data.after)">复制代码</el-button>
      </div>
    </div>

    <!-- Diff view -->
    <div v-else class="diff-diff-view">
      <div class="diff-stats">
        <span class="stat-add">+{{ addedLines }}</span>
        <span class="stat-del">-{{ removedLines }}</span>
      </div>
      <div class="diff-lines" ref="diffLines">
        <div
          v-for="(line, i) in parsedDiff"
          :key="i"
          class="diff-line"
          :class="line.type"
        >
          <span class="line-num-old">{{ line.oldNum || '' }}</span>
          <span class="line-num-new">{{ line.newNum || '' }}</span>
          <span class="line-content">{{ line.content }}</span>
        </div>
      </div>
      <div class="diff-actions">
        <el-button size="mini" type="text" @click="copyCode(data.after)">复制修改后代码</el-button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'DiffViewCard',
  props: {
    data: { type: Object, required: true },
  },
  data() {
    return {
      showDiff: false,
    }
  },
  computed: {
    parsedDiff() {
      if (!this.data.diff_text) return []
      const lines = []
      let oldLine = 0
      let newLine = 0

      for (const raw of this.data.diff_text.split('\n')) {
        const line = raw
        if (line.startsWith('@@')) {
          const match = line.match(/@@ -(\d+),?\d* \+(\d+),?\d* @@/)
          if (match) {
            oldLine = parseInt(match[1]) - 1
            newLine = parseInt(match[2]) - 1
          }
          continue
        }
        if (line.startsWith('---') || line.startsWith('+++') || line.startsWith('diff --git')) {
          continue
        }
        if (line.startsWith('-')) {
          oldLine++
          lines.push({ type: 'del', content: line.substring(1), oldNum: oldLine, newNum: '' })
        } else if (line.startsWith('+')) {
          newLine++
          lines.push({ type: 'add', content: line.substring(1), oldNum: '', newNum: newLine })
        } else {
          oldLine++
          newLine++
          lines.push({ type: 'ctx', content: line, oldNum: oldLine, newNum: newLine })
        }
      }
      return lines
    },
    addedLines() {
      return this.parsedDiff.filter(l => l.type === 'add').length
    },
    removedLines() {
      return this.parsedDiff.filter(l => l.type === 'del').length
    },
  },
  methods: {
    async copyCode(text) {
      try {
        await navigator.clipboard.writeText(text)
        this.$message.success('已复制')
      } catch {
        const ta = document.createElement('textarea')
        ta.value = text
        document.body.appendChild(ta)
        ta.select()
        document.execCommand('copy')
        document.body.removeChild(ta)
        this.$message.success('已复制')
      }
    },
  },
}
</script>

<style scoped>
.diff-view-card {
  border: 1px solid #e8eaed;
  border-radius: 8px;
  overflow: hidden;
}

.diff-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f8f9fa;
  border-bottom: 1px solid #e8eaed;
}

.diff-filename {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.diff-filename i {
  margin-right: 4px;
}

.diff-toggle {
  margin-left: auto;
}

.diff-code-view .code-body {
  margin: 0;
  padding: 14px;
  background: #1e293b;
  color: #e2e8f0;
  font-size: 13px;
  line-height: 1.5;
  overflow-x: auto;
  max-height: 360px;
  overflow-y: auto;
}

.diff-code-view .code-body code {
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  white-space: pre;
}

.diff-actions {
  padding: 6px 12px;
  background: #f8f9fa;
  border-top: 1px solid #e8eaed;
  text-align: right;
}

/* Diff view */
.diff-diff-view {
  font-size: 12px;
  line-height: 1.5;
}

.diff-stats {
  padding: 6px 12px;
  background: #f8f9fa;
  border-bottom: 1px solid #e8eaed;
  display: flex;
  gap: 12px;
}

.stat-add {
  color: #28a745;
  font-weight: 600;
}

.stat-del {
  color: #d73a49;
  font-weight: 600;
}

.diff-lines {
  max-height: 400px;
  overflow-y: auto;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
}

.diff-line {
  display: flex;
  min-height: 22px;
}

.diff-line.ctx {
  background: #fff;
  padding: 0 4px;
}

.diff-line.add {
  background: #e6ffec;
  padding: 0 4px;
}

.diff-line.del {
  background: #ffeef0;
  padding: 0 4px;
}

.line-num-old,
.line-num-new {
  width: 40px;
  min-width: 40px;
  text-align: right;
  padding-right: 8px;
  color: #999;
  user-select: none;
  font-size: 11px;
}

.line-content {
  flex: 1;
  white-space: pre;
  padding-left: 4px;
}

.diff-line.add .line-content::before {
  content: '+';
  color: #28a745;
  font-weight: bold;
  margin-right: 4px;
}

.diff-line.del .line-content::before {
  content: '-';
  color: #d73a49;
  font-weight: bold;
  margin-right: 4px;
}
</style>
