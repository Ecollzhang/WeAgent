<template>
  <div class="message-bubble" :class="{ own: isOwn }">
    <div class="bubble-sender" v-if="message.sender_type === 'agent'">
      <span class="agent-tag">{{ getSenderName() }}</span>
    </div>
    <div class="bubble-inner">
      <!-- Elements-based rendering -->
      <div v-if="hasElements" class="bubble-elements">
        <div
          v-for="(el, i) in message.elements"
          :key="i"
          class="el-block"
          :class="'el-' + el.type"
        >
          <!-- Text element -->
          <div v-if="el.type === 'text'" class="el-text" v-html="renderText(el.data.content)"></div>

          <!-- Code element -->
          <div v-else-if="el.type === 'code'" class="el-code">
            <div class="code-header">
              <span class="code-lang">{{ el.data.language || 'code' }}</span>
              <div class="code-actions">
                <el-button size="mini" type="text" @click="copyCode(el.data.content)">复制</el-button>
                <el-button size="mini" type="text" @click="previewCode(el.data)">预览</el-button>
              </div>
            </div>
            <pre class="code-body"><code>{{ el.data.content }}</code></pre>
          </div>

          <!-- Table element -->
          <div v-else-if="el.type === 'table'" class="el-table-wrap">
            <el-table
              :data="normalizeTable(el.data)"
              size="small"
              border
              stripe
              style="width: 100%"
            >
              <el-table-column
                v-for="(h, hi) in el.data.headers"
                :key="hi"
                :prop="'col' + hi"
                :label="h"
                min-width="100"
              ></el-table-column>
            </el-table>
          </div>

          <!-- Image element -->
          <div v-else-if="el.type === 'image'" class="el-image-wrap">
            <el-image
              style="max-width: 100%; max-height: 400px;"
              :src="el.data.url"
              :alt="el.data.alt || ''"
              fit="contain"
              :preview-src-list="[el.data.url]"
            ></el-image>
          </div>

          <!-- File element -->
          <div v-else-if="el.type === 'file'" class="el-file">
            <i class="el-icon-document"></i>
            <a :href="el.data.url" target="_blank" rel="noopener">{{ el.data.name }}</a>
            <span v-if="el.data.size" class="file-size">{{ formatFileSize(el.data.size) }}</span>
          </div>
        </div>
      </div>

      <!-- Fallback: render content as HTML (backward compat) -->
      <div v-else class="bubble-content" v-html="renderedContent"></div>

      <!-- Meta bar -->
      <div class="bubble-meta">
        <span class="bubble-time">{{ formatTime(message.created_at) }}</span>
        <span v-if="isTempMessage" class="bubble-sending">
          <i class="el-icon-loading"></i> 发送中...
        </span>
        <el-button
          type="text"
          size="mini"
          icon="el-icon-rank"
          @click="$emit('pin')"
          :title="message.is_pinned ? '取消置顶' : '置顶'"
          :class="{ pinned: message.is_pinned }"
        ></el-button>
      </div>
    </div>

    <!-- Artifact link -->
    <div v-if="message.artifact" class="artifact-link">
      <el-tag size="mini" type="success" @click="showArtifact">
        {{ message.artifact.artifact_type }}: {{ message.artifact.title }}
      </el-tag>
    </div>

    <!-- Code Preview Dialog -->
    <el-dialog
      title="代码预览"
      :visible.sync="codePreviewVisible"
      width="700px"
      top="5vh"
      custom-class="code-preview-dialog"
    >
      <div class="code-preview-body">
        <div class="preview-meta" v-if="previewData">
          <span class="preview-filename" v-if="previewData.filename">
            <i class="el-icon-document"></i> {{ previewData.filename }}
          </span>
          <el-tag size="mini" type="primary" v-if="previewData.language">
            {{ previewData.language }}
          </el-tag>
        </div>
        <pre class="preview-code"><code>{{ previewData?.content }}</code></pre>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { formatTime } from '../../utils/format'

export default {
  name: 'MessageBubble',
  props: {
    message: Object,
    isOwn: Boolean,
  },
  data() {
    return {
      codePreviewVisible: false,
      previewData: null,
    }
  },
  computed: {
    hasElements() {
      return this.message && Array.isArray(this.message.elements) && this.message.elements.length > 0
    },
    isTempMessage() {
      return this.message && typeof this.message.id === 'string' && this.message.id.startsWith('temp_')
    },
    renderedContent() {
      if (!this.message || !this.message.content) return ''
      let content = this.message.content
      content = content.replace(/```(\w*)\n?([\s\S]*?)```/g, (match, lang, code) => {
        return `<pre><code class="language-${lang}">${this.escapeHtml(code)}</code></pre>`
      })
      content = content.replace(/`([^`]+)`/g, '<code>$1</code>')
      content = content.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      content = content.replace(/\n/g, '<br>')
      return content
    },
  },
  methods: {
    formatTime,
    escapeHtml(text) {
      const div = document.createElement('div')
      div.textContent = text
      return div.innerHTML
    },
    getSenderName() {
      return this.message.sender_id || '智能体'
    },
    showArtifact() {
      this.$emit('show-artifact', this.message.artifact)
    },
    renderText(content) {
      if (!content) return ''
      let html = content
      html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (match, lang, code) => {
        return `<pre><code class="language-${lang}">${this.escapeHtml(code)}</code></pre>`
      })
      html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
      html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      html = html.replace(/\n/g, '<br>')
      return html
    },
    normalizeTable(data) {
      if (!data || !data.headers || !data.rows) return []
      return data.rows.map(row => {
        const obj = {}
        data.headers.forEach((h, i) => {
          obj['col' + i] = row[i] || ''
        })
        return obj
      })
    },
    async copyCode(content) {
      try {
        await navigator.clipboard.writeText(content)
        this.$message.success('已复制到剪贴板')
      } catch (e) {
        // Fallback
        const textarea = document.createElement('textarea')
        textarea.value = content
        document.body.appendChild(textarea)
        textarea.select()
        document.execCommand('copy')
        document.body.removeChild(textarea)
        this.$message.success('已复制到剪贴板')
      }
    },
    previewCode(data) {
      this.previewData = data
      this.codePreviewVisible = true
    },
    formatFileSize(bytes) {
      if (!bytes) return ''
      const units = ['B', 'KB', 'MB', 'GB']
      let i = 0
      let size = bytes
      while (size >= 1024 && i < units.length - 1) {
        size /= 1024
        i++
      }
      return size.toFixed(1) + ' ' + units[i]
    },
  },
}
</script>

<style scoped>
.message-bubble {
  display: flex;
  flex-direction: column;
  max-width: 78%;
}

.message-bubble.own {
  align-items: flex-end;
  margin-left: auto;
}

.bubble-sender {
  margin-bottom: 4px;
}

.agent-tag {
  font-size: 12px;
  color: #4080ff;
  font-weight: 500;
}

.bubble-inner {
  background: #ffffff;
  padding: 10px 14px;
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.06);
  border: 1px solid #f0f0f0;
}

.own .bubble-inner {
  background: #f0f5ff;
  border-color: #e0ebff;
}

/* ===== Elements ===== */
.bubble-elements {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.el-block {
  width: 100%;
}

/* Text element — inline rendering */
.el-text {
  font-size: 14px;
  line-height: 1.6;
  color: #1e293b;
  word-wrap: break-word;
}

.el-text :deep(pre) {
  background: #f8f9fa;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 13px;
  margin: 8px 0;
}

.el-text :deep(code) {
  background: #f8f9fa;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  color: #e96900;
}

.el-text :deep(pre code) {
  background: none;
  padding: 0;
  color: inherit;
}

/* Code element */
.el-code {
  border: 1px solid #e8eaed;
  border-radius: 8px;
  overflow: hidden;
}

.code-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background: #f8f9fa;
  border-bottom: 1px solid #e8eaed;
}

.code-lang {
  font-size: 11px;
  color: #666;
  font-weight: 500;
  text-transform: uppercase;
}

.code-actions {
  display: flex;
  gap: 4px;
}

.code-actions .el-button--mini {
  font-size: 11px;
  padding: 2px 8px;
  color: #4080ff;
}

.code-body {
  padding: 12px;
  margin: 0;
  background: #1e293b;
  color: #e2e8f0;
  font-size: 12px;
  line-height: 1.5;
  overflow-x: auto;
  max-height: 300px;
  overflow-y: auto;
}

.code-body code {
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  white-space: pre;
}

/* Table element */
.el-table-wrap {
  overflow-x: auto;
}

/* Image element */
.el-image-wrap {
  border-radius: 8px;
  overflow: hidden;
}

/* File element */
.el-file {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f8f9fa;
  border-radius: 8px;
  font-size: 13px;
}

.el-file i {
  font-size: 20px;
  color: #4080ff;
}

.el-file a {
  color: #4080ff;
  text-decoration: none;
  font-weight: 500;
}

.el-file a:hover {
  text-decoration: underline;
}

.file-size {
  font-size: 11px;
  color: #94a3b8;
  margin-left: auto;
}

/* Fallback content */
.bubble-content {
  font-size: 14px;
  line-height: 1.6;
  color: #1e293b;
  word-wrap: break-word;
}

.bubble-content :deep(pre) {
  background: #f8f9fa;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 13px;
  margin: 8px 0;
}

.bubble-content :deep(code) {
  background: #f8f9fa;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  color: #e96900;
}

.bubble-content :deep(pre code) {
  background: none;
  padding: 0;
  color: inherit;
}

/* Meta */
.bubble-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  font-size: 11px;
  color: #c0c4cc;
}

.bubble-time {
  flex: 1;
}

.bubble-sending {
  color: #4080ff;
  font-size: 11px;
}

.bubble-meta .el-button {
  padding: 0;
  margin-left: auto;
  color: #c0c4cc;
}

.bubble-meta .pinned {
  color: #e6a23c;
}

.artifact-link {
  margin-top: 4px;
}

/* Code Preview Dialog */
.code-preview-dialog :deep(.el-dialog__body) {
  padding: 16px 20px;
}

.preview-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.preview-filename {
  font-size: 13px;
  color: #1e293b;
  font-weight: 500;
}

.preview-code {
  margin: 0;
  padding: 16px;
  background: #1e293b;
  color: #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.5;
  overflow-x: auto;
  max-height: 60vh;
  overflow-y: auto;
}

.preview-code code {
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  white-space: pre;
}
</style>
