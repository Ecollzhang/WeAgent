<template>
  <div class="message-bubble" :class="{ own: isOwn }">
    <div class="bubble-sender" v-if="message.sender_type === 'agent'">
      <span class="agent-tag">{{ getSenderName() }}</span>
      <span v-if="message.status" class="status-tag" :class="'status-' + message.status">
        {{ statusLabel(message.status) }}
      </span>
      <el-button
        v-if="canStop"
        type="text"
        size="mini"
        icon="el-icon-close"
        class="stop-btn"
        @click="$emit('stop-agent')"
        title="停止 Agent"
      ></el-button>
    </div>
    <div class="bubble-inner">
      <!-- Elements-based rendering -->
      <div v-if="hasElements" class="bubble-elements">
        <div
          v-for="(el, i) in renderedElements"
          :key="i"
          class="el-block"
          :class="'el-' + el.type"
          >
          <!-- Text element -->
          <div v-if="el.type === 'text'" class="el-text" v-html="renderText(elementContent(el))"></div>

          <!-- Progress element -->
          <div v-else-if="el.type === 'progress'" class="el-progress">
            <span class="progress-dot" :class="'progress-' + (el.status || 'running')"></span>
            <span>{{ elementContent(el) }}</span>
          </div>

          <!-- Code element -->
          <div v-else-if="el.type === 'code'" class="el-code">
            <div class="code-header">
              <span class="code-lang">{{ elementData(el).language || 'code' }}</span>
              <div class="code-actions">
                <el-button size="mini" type="text" @click="copyCode(elementContent(el))">复制</el-button>
                <el-button size="mini" type="text" @click="previewCode(normalizeElementForPreview(el))">预览</el-button>
              </div>
            </div>
            <pre class="code-body"><code>{{ elementContent(el) }}</code></pre>
          </div>

          <!-- Table element -->
          <div v-else-if="el.type === 'table'" class="el-table-wrap">
            <el-table
              :data="normalizeTable(elementData(el))"
              size="small"
              border
              stripe
              style="width: 100%"
            >
              <el-table-column
                v-for="(h, hi) in (elementData(el).headers || [])"
                :key="hi"
                :prop="'col' + hi"
                :label="h"
                min-width="100"
              ></el-table-column>
            </el-table>
          </div>

          <!-- Image element -->
          <div v-else-if="el.type === 'image'" class="el-image-wrap">
            <img
              class="artifact-image"
              :src="imageSrc(el)"
              :alt="elementData(el).alt || elementData(el).name || ''"
              @click="previewImage(imageSrc(el))"
            />
            <button
              v-if="imagePath(el)"
              class="image-file-link"
              @click="openFilePath(imagePath(el))"
            >
              {{ elementData(el).name || elementData(el).alt || imagePath(el) }}
            </button>
          </div>

          <!-- File element -->
          <div v-else-if="el.type === 'file' && isImageElement(el)" class="el-image-wrap">
            <img
              class="artifact-image"
              :src="imageSrc(el)"
              :alt="elementData(el).name || ''"
              @click="previewImage(imageSrc(el))"
            />
            <button class="image-file-link" @click="openFileElement(elementData(el))">
              {{ elementData(el).name || elementContent(el) }}
            </button>
          </div>

          <div v-else-if="el.type === 'file'" class="el-file">
            <i class="el-icon-document"></i>
            <button class="file-link-btn" @click="openFileElement(elementData(el))">{{ elementData(el).name || elementContent(el) }}</button>
            <span v-if="elementData(el).size" class="file-size">{{ formatFileSize(elementData(el).size) }}</span>
          </div>
        </div>
      </div>

      <div v-if="executionEvents.length" class="steps-panel">
        <div class="steps-title">执行步骤</div>
        <div v-for="(event, index) in executionEvents" :key="index" class="step-item">
          <span class="step-dot" :class="'step-' + event.type"></span>
          <div class="step-main">
            <div class="step-title">{{ event.title || event.type }}</div>
            <button
              v-if="event.type === 'file_write' && event.data && event.data.file"
              class="step-file"
              @click="openFilePath(event.data.file)"
            >
              {{ normalizeWorkspacePath(event.data.file) }}
            </button>
          </div>
        </div>
      </div>

      <!-- Fallback: render content as HTML (backward compat) -->
      <div v-else class="bubble-content" v-html="renderedContent"></div>

      <!-- Meta bar -->
      <el-collapse v-if="message.sender_type === 'agent' && message.raw_output" class="raw-collapse">
        <el-collapse-item title="Raw output" name="raw">
          <pre class="raw-output">{{ message.raw_output }}</pre>
        </el-collapse-item>
      </el-collapse>

      <div v-if="message.status === 'streaming'" class="streaming-line">
        <i class="el-icon-loading"></i>
        <span>输出中...</span>
      </div>

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

    <el-dialog
      title="图片预览"
      :visible.sync="imagePreviewVisible"
      width="78%"
      top="5vh"
      custom-class="image-preview-dialog"
    >
      <div class="image-preview-body">
        <img v-if="previewImageUrl" :src="previewImageUrl" class="preview-image" />
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
    sessionId: { type: String, default: '' },
  },
  data() {
    return {
      codePreviewVisible: false,
      previewData: null,
      imagePreviewVisible: false,
      previewImageUrl: '',
    }
  },
  computed: {
    hasElements() {
      return this.message && Array.isArray(this.message.elements) && this.message.elements.length > 0
    },
    renderedElements() {
      const elements = Array.isArray(this.message?.elements) ? this.message.elements : []
      const merged = []
      elements.forEach(el => {
        const last = merged[merged.length - 1]
        if (el?.type === 'text' && last?.type === 'text') {
          const content = this.elementContent(last) + this.elementContent(el)
          merged[merged.length - 1] = {
            ...last,
            content,
            data: {
              ...(last.data || {}),
              content,
            },
          }
        } else {
          merged.push(el)
        }
      })
      return merged
    },
    isTempMessage() {
      return this.message && typeof this.message.id === 'string' && this.message.id.startsWith('temp_')
    },
    canStop() {
      return this.message
        && this.message.sender_type === 'agent'
        && ['pending', 'streaming'].includes(this.message.status)
        && this.message.sender_id !== 'system'
    },
    renderedContent() {
      if (!this.message || !this.message.content) return ''
      return this.renderMarkdown(this.message.content)
    },
    executionEvents() {
      return this.message?.meta?.events || []
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
      return this.message.sender_name || this.message.sender?.name || this.message.sender_id || '智能体'
    },
    statusLabel(status) {
      return {
        pending: '等待中',
        streaming: '执行中',
        done: '完成',
        error: '错误',
        stopped: '已停止',
      }[status] || status
    },
    showArtifact() {
      this.$emit('show-artifact', this.message.artifact)
    },
    renderText(content) {
      return this.renderMarkdown(content)
    },
    renderMarkdown(content) {
      if (!content) return ''

      const blocks = []
      let html = this.escapeHtml(String(content))

      html = html.replace(/```([a-zA-Z0-9_+-]*)\n?([\s\S]*?)```/g, (match, lang, code) => {
        const token = `@@CODE_BLOCK_${blocks.length}@@`
        blocks.push(`<pre><code class="language-${lang || 'text'}">${code.trim()}</code></pre>`)
        return token
      })

      const lines = html.split(/\r?\n/)
      const rendered = []
      let listBuffer = []

      const flushList = () => {
        if (listBuffer.length) {
          rendered.push(`<ul>${listBuffer.join('')}</ul>`)
          listBuffer = []
        }
      }

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]
        const nextLine = lines[i + 1] || ''

        if (this.isMarkdownTableRow(line) && this.isMarkdownTableSeparator(nextLine)) {
          flushList()
          const headers = this.parseMarkdownTableRow(line)
          const rows = []
          i += 2

          while (i < lines.length && this.isMarkdownTableRow(lines[i]) && lines[i].trim() !== '') {
            rows.push(this.parseMarkdownTableRow(lines[i]))
            i += 1
          }
          i -= 1

          rendered.push(this.renderMarkdownTable(headers, rows))
          continue
        }

        if (/^\s*[-*+]\s+/.test(line)) {
          listBuffer.push(`<li>${this.renderInlineMarkdown(line.replace(/^\s*[-*+]\s+/, ''))}</li>`)
          continue
        }
        flushList()
        if (/^###\s+/.test(line)) {
          rendered.push(`<h3>${this.renderInlineMarkdown(line.replace(/^###\s+/, ''))}</h3>`)
        } else if (/^##\s+/.test(line)) {
          rendered.push(`<h2>${this.renderInlineMarkdown(line.replace(/^##\s+/, ''))}</h2>`)
        } else if (/^#\s+/.test(line)) {
          rendered.push(`<h1>${this.renderInlineMarkdown(line.replace(/^#\s+/, ''))}</h1>`)
        } else if (/^>\s?/.test(line)) {
          rendered.push(`<blockquote>${this.renderInlineMarkdown(line.replace(/^>\s?/, ''))}</blockquote>`)
        } else if (line.trim() === '') {
          rendered.push('')
        } else if (this.isWorkspaceImagePathLine(line)) {
          const src = this.resolveFileUrl(line.trim().replace(/^`|`$/g, ''))
          rendered.push(`<p><img class="inline-markdown-image" src="${this.escapeHtml(src)}" alt=""></p>`)
        } else {
          rendered.push(`<p>${this.renderInlineMarkdown(line)}</p>`)
        }
      }
      flushList()

      html = rendered.join('')
      blocks.forEach((block, index) => {
        html = html.replace(`@@CODE_BLOCK_${index}@@`, block)
      })
      return html
    },
    renderInlineMarkdown(text) {
      let html = text || ''
      html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
      html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>')
      html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
      return html
    },
    isMarkdownTableRow(line) {
      const text = String(line || '').trim()
      if (!text || !text.includes('|')) return false
      return this.parseMarkdownTableRow(text).length >= 2
    },
    isMarkdownTableSeparator(line) {
      if (!this.isMarkdownTableRow(line)) return false
      const cells = this.parseMarkdownTableRow(line)
      return cells.length >= 2 && cells.every(cell => /^:?-{3,}:?$/.test(cell.replace(/\s+/g, '')))
    },
    parseMarkdownTableRow(line) {
      let text = String(line || '').trim()
      if (text.startsWith('|')) text = text.slice(1)
      if (text.endsWith('|')) text = text.slice(0, -1)
      return text.split('|').map(cell => cell.trim())
    },
    renderMarkdownTable(headers, rows) {
      const thead = headers
        .map(header => `<th>${this.renderInlineMarkdown(header)}</th>`)
        .join('')
      const body = rows
        .map(row => {
          const cells = headers.map((_, index) => `<td>${this.renderInlineMarkdown(row[index] || '')}</td>`).join('')
          return `<tr>${cells}</tr>`
        })
        .join('')
      return `<div class="markdown-table-wrap"><table class="markdown-table"><thead><tr>${thead}</tr></thead><tbody>${body}</tbody></table></div>`
    },
    isWorkspaceImagePathLine(line) {
      const text = String(line || '').trim().replace(/^`|`$/g, '')
      return /^\/?workspace\/.+\.(png|jpe?g|gif|webp|svg|bmp)$/i.test(text)
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
    elementData(el) {
      return el?.data || {}
    },
    elementContent(el) {
      if (!el) return ''
      if (el.content !== undefined && el.content !== null) return el.content
      return el.data?.content || ''
    },
    normalizeElementForPreview(el) {
      return {
        ...this.elementData(el),
        content: this.elementContent(el),
      }
    },
    imageSrc(el) {
      const data = this.elementData(el)
      const candidate = data.url || data.src || data.path || this.elementContent(el)
      return this.resolveFileUrl(candidate)
    },
    imagePath(el) {
      const data = this.elementData(el)
      return data.path || this.pathFromUrl(data.url || data.src) || ''
    },
    isImageElement(el) {
      const data = this.elementData(el)
      const value = data.path || data.url || data.src || data.name || this.elementContent(el)
      return /\.(png|jpe?g|gif|webp|svg|bmp)$/i.test(String(value || '').split('?')[0])
    },
    resolveFileUrl(value) {
      if (!value) return ''
      const text = String(value)
      if (/^(data:|blob:|https?:\/\/|\/api\/)/i.test(text)) return text
      if (text.startsWith('/workspace') || text.startsWith('workspace/')) {
        if (!this.sessionId) return text
        const path = this.normalizeWorkspacePath(text)
        return `/api/sandbox/sessions/${encodeURIComponent(this.sessionId)}/files/raw?path=${encodeURIComponent(path)}`
      }
      return text
    },
    previewImage(url) {
      if (!url) return
      this.previewImageUrl = url
      this.imagePreviewVisible = true
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
    openFileElement(data) {
      if (!data) return
      const path = data.path || this.pathFromUrl(data.url) || data.name
      this.openFilePath(path)
    },
    openFilePath(path) {
      this.$emit('open-file', { path: this.normalizeWorkspacePath(path) })
    },
    normalizeWorkspacePath(path) {
      if (!path) return ''
      const clean = String(path).replace(/\\/g, '/').replace(/^\/+/, '')
      return clean.startsWith('workspace/') ? `/${clean}` : `/workspace/${clean}`
    },
    pathFromUrl(url) {
      if (!url) return ''
      const marker = '/workspace/'
      const idx = url.indexOf(marker)
      if (idx === -1) return ''
      return decodeURIComponent(url.slice(idx + marker.length))
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
  display: flex;
  align-items: center;
  gap: 8px;
}

.agent-tag {
  font-size: 12px;
  color: #4080ff;
  font-weight: 500;
}

.status-tag {
  font-size: 11px;
  line-height: 18px;
  padding: 0 6px;
  border-radius: 4px;
  background: #f1f5f9;
  color: #64748b;
}

.status-streaming,
.status-pending {
  background: #ecf5ff;
  color: #4080ff;
}

.status-done {
  background: #f0f9eb;
  color: #67c23a;
}

.status-error {
  background: #fef0f0;
  color: #f56c6c;
}

.status-stopped {
  background: #f4f4f5;
  color: #909399;
}

.stop-btn {
  padding: 0;
  color: #f56c6c;
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

.el-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 9px;
  background: #f8fafc;
  border: 1px solid #edf0f5;
  border-radius: 6px;
  font-size: 12px;
  color: #475569;
}

.progress-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #4080ff;
  flex-shrink: 0;
}

.progress-done {
  background: #67c23a;
}

.progress-error {
  background: #f56c6c;
}

.progress-stopped {
  background: #909399;
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

.el-text :deep(p),
.bubble-content :deep(p) {
  margin: 0 0 8px;
}

.el-text :deep(p:last-child),
.bubble-content :deep(p:last-child) {
  margin-bottom: 0;
}

.el-text :deep(h1),
.el-text :deep(h2),
.el-text :deep(h3),
.bubble-content :deep(h1),
.bubble-content :deep(h2),
.bubble-content :deep(h3) {
  margin: 8px 0 6px;
  line-height: 1.35;
  color: #0f172a;
}

.el-text :deep(h1),
.bubble-content :deep(h1) {
  font-size: 18px;
}

.el-text :deep(h2),
.bubble-content :deep(h2) {
  font-size: 16px;
}

.el-text :deep(h3),
.bubble-content :deep(h3) {
  font-size: 15px;
}

.el-text :deep(ul),
.bubble-content :deep(ul) {
  margin: 4px 0 8px;
  padding-left: 20px;
}

.el-text :deep(li),
.bubble-content :deep(li) {
  margin: 2px 0;
}

.el-text :deep(blockquote),
.bubble-content :deep(blockquote) {
  margin: 6px 0;
  padding: 6px 10px;
  border-left: 3px solid #c7d2fe;
  background: #f8fafc;
  color: #475569;
}

.el-text :deep(a),
.bubble-content :deep(a) {
  color: #4080ff;
  text-decoration: none;
}

.el-text :deep(a:hover),
.bubble-content :deep(a:hover) {
  text-decoration: underline;
}

.el-text :deep(.markdown-table-wrap),
.bubble-content :deep(.markdown-table-wrap) {
  overflow-x: auto;
  margin: 8px 0;
}

.el-text :deep(.markdown-table),
.bubble-content :deep(.markdown-table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  background: #fff;
}

.el-text :deep(.markdown-table th),
.el-text :deep(.markdown-table td),
.bubble-content :deep(.markdown-table th),
.bubble-content :deep(.markdown-table td) {
  border: 1px solid #e2e8f0;
  padding: 7px 9px;
  text-align: left;
  vertical-align: top;
}

.el-text :deep(.markdown-table th),
.bubble-content :deep(.markdown-table th) {
  background: #f8fafc;
  font-weight: 600;
  color: #334155;
}

.el-text :deep(.markdown-table tr:nth-child(even) td),
.bubble-content :deep(.markdown-table tr:nth-child(even) td) {
  background: #fbfdff;
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
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: flex-start;
  border-radius: 8px;
  overflow: hidden;
}

.artifact-image {
  display: block;
  max-width: 100%;
  max-height: 400px;
  object-fit: contain;
  border: 1px solid #e8eaed;
  border-radius: 8px;
  background: #f8fafc;
  cursor: zoom-in;
}

.el-text :deep(.inline-markdown-image),
.bubble-content :deep(.inline-markdown-image) {
  display: block;
  max-width: 100%;
  max-height: 400px;
  object-fit: contain;
  border: 1px solid #e8eaed;
  border-radius: 8px;
  background: #f8fafc;
}

.image-file-link {
  border: none;
  background: transparent;
  padding: 0;
  color: #4080ff;
  font-size: 12px;
  cursor: pointer;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.image-file-link:hover {
  text-decoration: underline;
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

.file-link-btn {
  border: none;
  background: transparent;
  padding: 0;
  color: #4080ff;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}

.file-link-btn:hover {
  text-decoration: underline;
}

.file-size {
  font-size: 11px;
  color: #94a3b8;
  margin-left: auto;
}

.steps-panel {
  margin-top: 10px;
  padding: 8px 10px;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  background: #fbfcff;
}

.steps-title {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 6px;
  font-weight: 600;
}

.step-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 5px 0;
}

.step-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 6px;
  background: #94a3b8;
  flex-shrink: 0;
}

.step-agent_task_started {
  background: #4080ff;
}

.step-file_write {
  background: #67c23a;
}

.step-agent_task_completed {
  background: #22c55e;
}

.step-error {
  background: #f56c6c;
}

.step-main {
  min-width: 0;
}

.step-title {
  font-size: 12px;
  color: #334155;
  line-height: 1.5;
}

.step-file {
  display: block;
  border: none;
  background: transparent;
  padding: 1px 0;
  color: #4080ff;
  font-size: 12px;
  cursor: pointer;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

.raw-collapse {
  margin-top: 10px;
  border-top: 1px solid #f0f0f0;
  border-bottom: none;
}

.raw-collapse :deep(.el-collapse-item__header) {
  height: 32px;
  line-height: 32px;
  font-size: 12px;
  color: #64748b;
  border-bottom: none;
}

.raw-collapse :deep(.el-collapse-item__wrap) {
  border-bottom: none;
}

.raw-output {
  margin: 0;
  padding: 10px;
  max-height: 260px;
  overflow: auto;
  background: #0f172a;
  color: #e2e8f0;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
}

.streaming-line {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  font-size: 12px;
  color: #4080ff;
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

.image-preview-dialog :deep(.el-dialog__body) {
  padding: 12px;
  background: #0f172a;
}

.image-preview-body {
  min-height: 60vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-image {
  max-width: 100%;
  max-height: 76vh;
  object-fit: contain;
}
</style>
