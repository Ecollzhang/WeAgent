<template>
  <div class="message-bubble" :class="{ own: isOwn }">
    <div class="bubble-sender" v-if="message.sender_type === 'agent'">
      <span class="agent-tag">{{ getSenderName() }}</span>
      <span v-if="providerLabel" class="provider-tag">{{ providerLabel }}</span>
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
      <div v-if="currentProgress" class="current-progress">
        <span class="progress-dot" :class="'progress-' + (currentProgress.status || 'running')"></span>
        <span class="current-progress-label">当前进度</span>
        <span class="current-progress-text">{{ elementContent(currentProgress) }}</span>
      </div>

      <div v-if="visibleRawOutput" class="raw-rendered">
        <div class="raw-rendered-content" v-html="renderMarkdown(visibleRawOutput)"></div>
      </div>

      <div v-else-if="contentElements.length" class="bubble-elements content-section">
        <div
          v-for="(el, i) in contentElements"
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

          <div v-else-if="el.type === 'error'" class="el-error">
            <div class="error-title">
              <i class="el-icon-warning-outline"></i>
              <span>{{ elementData(el).title || '错误' }}</span>
            </div>
            <div class="error-content" v-html="renderText(elementContent(el))"></div>
          </div>

          <div v-else-if="el.type === 'result'" class="el-result">
            <div class="result-title">
              <i class="el-icon-finished"></i>
              <span>{{ elementData(el).title || '执行结果' }}</span>
            </div>
            <div class="result-content" v-html="renderText(elementContent(el))"></div>
          </div>

          <div v-else-if="el.type === 'summary'" class="el-result">
            <div class="result-title">
              <i class="el-icon-finished"></i>
              <span>{{ elementData(el).title || '完成摘要' }}</span>
            </div>
            <div class="result-content" v-html="renderText(elementContent(el))"></div>
          </div>

        </div>
      </div>

      <!-- Artifact rendering -->
      <div v-if="artifactElements.length" class="bubble-elements artifact-section">
        <div class="section-title">产物</div>
        <div
          v-for="(el, i) in artifactElements"
          :key="i"
          class="el-block"
          :class="'el-' + el.type"
          >
          <div v-if="el.type === 'code'" class="artifact-block code-card">
            <div class="artifact-header">
              <i class="el-icon-tickets"></i>
              <span>{{ elementData(el).title || elementData(el).filename || '代码产物' }}</span>
              <span class="artifact-meta">{{ elementData(el).language || 'code' }}</span>
              <div class="code-actions">
                <el-button size="mini" type="text" @click="copyCode(elementContent(el))">复制</el-button>
                <el-button size="mini" type="text" @click="previewCode(normalizeElementForPreview(el))">预览</el-button>
              </div>
            </div>
            <pre class="code-body"><code>{{ elementContent(el) }}</code></pre>
          </div>

          <div v-else-if="el.type === 'table'" class="artifact-block table-block">
            <div class="artifact-header">
              <i class="el-icon-s-grid"></i>
              <span>{{ elementData(el).title || '表格产物' }}</span>
              <span class="artifact-meta">{{ tableHeaders(el).length }} 列</span>
            </div>
            <div class="table-scroll">
              <el-table
                v-if="tableHeaders(el).length"
                :data="normalizeTable(el)"
                size="small"
                border
                stripe
                style="width: 100%"
              >
                <el-table-column
                  v-for="(h, hi) in tableHeaders(el)"
                  :key="hi"
                  :prop="'col' + hi"
                  :label="h"
                  min-width="120"
                ></el-table-column>
              </el-table>
              <div v-else class="el-text" v-html="renderText(elementContent(el))"></div>
            </div>
          </div>

          <div v-else-if="el.type === 'image'" class="artifact-block image-block">
            <div class="artifact-header">
              <i class="el-icon-picture-outline"></i>
              <button
                v-if="imagePath(el)"
                class="artifact-title-btn"
                @click="openFilePath(imagePath(el))"
              >
                {{ elementData(el).name || elementData(el).alt || imagePath(el) }}
              </button>
              <span v-else>{{ elementData(el).name || elementData(el).alt || '图片' }}</span>
              <span class="artifact-meta">image</span>
            </div>
            <div class="image-frame">
              <img
                class="artifact-image"
                :src="imageSrc(el)"
                :alt="elementData(el).alt || elementData(el).name || ''"
                @click="previewImage(imageSrc(el))"
              />
            </div>
          </div>

          <div v-else-if="el.type === 'file' && isImageElement(el)" class="artifact-block image-block">
            <div class="artifact-header">
              <i class="el-icon-picture-outline"></i>
              <button class="artifact-title-btn" @click="openFileElement(elementData(el))">
                {{ elementData(el).name || elementContent(el) }}
              </button>
              <span class="artifact-meta">image</span>
            </div>
            <div class="image-frame">
              <img
                class="artifact-image"
                :src="imageSrc(el)"
                :alt="elementData(el).name || ''"
                @click="previewImage(imageSrc(el))"
              />
            </div>
          </div>

          <div v-else-if="el.type === 'file'" class="artifact-block file-card" @click="openFileElement(elementData(el))">
            <div class="file-icon"><i :class="fileIcon(el)"></i></div>
            <div class="file-main">
              <button class="file-link-btn">{{ elementData(el).name || elementContent(el) }}</button>
              <span class="file-path">{{ elementData(el).path || elementData(el).url || elementContent(el) }}</span>
            </div>
            <span v-if="elementData(el).size" class="file-size">{{ formatFileSize(elementData(el).size) }}</span>
          </div>

          <div v-else-if="el.type === 'service'" class="artifact-block service-card">
            <div class="service-card-header">
              <div class="service-icon"><i class="el-icon-monitor"></i></div>
              <div class="service-title-wrap">
                <div class="service-card-title">{{ serviceTitle(el) }}</div>
                <div class="service-subtitle">
                  <span v-if="serviceInfo(el).port">端口 {{ serviceInfo(el).port }}</span>
                  <span v-if="serviceInfo(el).type">{{ serviceInfo(el).type }}</span>
                  <span v-if="serviceInfo(el).id">{{ serviceInfo(el).id }}</span>
                </div>
              </div>
              <el-tag size="mini" :type="serviceStatusType(serviceInfo(el).status)">
                {{ serviceStatusLabel(serviceInfo(el).status) }}
              </el-tag>
            </div>
            <div v-if="elementContent(el)" class="service-description" v-html="renderText(elementContent(el))"></div>
            <div class="service-url-row" v-if="serviceUrl(el)">
              <i class="el-icon-link"></i>
              <a :href="serviceUrl(el)" target="_blank" rel="noopener">{{ serviceUrl(el) }}</a>
            </div>
            <div v-if="serviceInfo(el).cwd || serviceInfo(el).command" class="service-meta-grid">
              <div v-if="serviceInfo(el).cwd" class="service-meta-item">
                <span>目录</span>
                <code>{{ serviceInfo(el).cwd }}</code>
              </div>
              <div v-if="serviceInfo(el).command" class="service-meta-item">
                <span>命令</span>
                <code>{{ serviceInfo(el).command }}</code>
              </div>
            </div>
            <div class="service-actions">
              <el-button
                size="mini"
                type="primary"
                plain
                icon="el-icon-position"
                :disabled="!serviceUrl(el)"
                @click="openService(el)"
              >打开</el-button>
              <el-button
                size="mini"
                icon="el-icon-view"
                :disabled="!serviceUrl(el)"
                @click="previewService(el)"
              >预览</el-button>
              <el-button
                size="mini"
                icon="el-icon-document-copy"
                :disabled="!serviceUrl(el)"
                @click="copyServiceUrl(serviceUrl(el))"
              >复制</el-button>
              <el-button
                size="mini"
                icon="el-icon-document"
                :loading="serviceBusyKey === serviceActionKey(el, 'logs')"
                @click="loadServiceLogs(el)"
              >日志</el-button>
              <el-button
                size="mini"
                icon="el-icon-refresh"
                :loading="serviceBusyKey === serviceActionKey(el, 'restart')"
                @click="restartServiceCard(el)"
              >重启</el-button>
              <el-button
                size="mini"
                type="danger"
                plain
                icon="el-icon-video-pause"
                :loading="serviceBusyKey === serviceActionKey(el, 'stop')"
                @click="stopServiceCard(el)"
              >停止</el-button>
            </div>
          </div>
        </div>
      </div>

      <el-collapse v-if="historySteps.length" class="steps-collapse">
        <el-collapse-item :title="`进度（${historySteps.length}）`" name="steps">
          <div class="steps-panel">
            <div v-for="(step, index) in historySteps" :key="index" class="step-item">
              <span class="step-dot" :class="'step-' + step.statusClass"></span>
              <div class="step-main">
                <div class="step-title">{{ step.title }}</div>
                <button
                  v-if="step.path"
                  class="step-file"
                  @click="openFilePath(step.path)"
                >
                  {{ normalizeWorkspacePath(step.path) }}
                </button>
              </div>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>

      <!-- Fallback: render content as HTML (backward compat) -->
      <div v-if="!visibleRawOutput && !contentElements.length && !artifactElements.length" class="bubble-content" v-html="renderedContent"></div>

      <!-- Meta bar -->
      <el-collapse v-if="message.sender_type === 'agent' && message.raw_output && showRawSource" class="raw-collapse">
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
    <el-dialog
      title="服务预览"
      :visible.sync="servicePreviewVisible"
      width="86%"
      top="5vh"
      custom-class="service-preview-dialog"
    >
      <div class="service-preview-toolbar">
        <span>{{ servicePreviewUrl }}</span>
        <el-button size="mini" type="text" icon="el-icon-position" @click="openUrl(servicePreviewUrl)">新窗口打开</el-button>
      </div>
      <iframe v-if="servicePreviewUrl" class="service-preview-frame" :src="servicePreviewUrl"></iframe>
    </el-dialog>
    <el-dialog
      title="服务日志"
      :visible.sync="serviceLogsVisible"
      width="760px"
      top="8vh"
      custom-class="service-logs-dialog"
    >
      <div class="service-logs-body" v-loading="serviceLogsLoading">
        <div class="service-logs-meta" v-if="serviceLogsData">
          <el-tag size="mini">{{ serviceLogsData.service_id }}</el-tag>
          <el-tag size="mini" :type="serviceStatusType(serviceLogsData.status)">{{ serviceStatusLabel(serviceLogsData.status) }}</el-tag>
        </div>
        <div class="service-log-section">
          <div class="service-log-title">stdout</div>
          <pre>{{ serviceLogsData?.stdout_tail || '暂无输出' }}</pre>
        </div>
        <div class="service-log-section">
          <div class="service-log-title">stderr</div>
          <pre>{{ serviceLogsData?.stderr_tail || '暂无错误输出' }}</pre>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { formatTime } from '../../utils/format'
import { getServiceLogs, restartService, stopService } from '../../api/sandbox'

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
      servicePreviewVisible: false,
      servicePreviewUrl: '',
      serviceLogsVisible: false,
      serviceLogsLoading: false,
      serviceLogsData: null,
      serviceBusyKey: '',
    }
  },
  computed: {
    hasElements() {
      return this.message && Array.isArray(this.message.elements) && this.message.elements.length > 0
    },
    providerLabel() {
      const provider = this.message?.meta?.provider || this.latestEventProvider()
      if (!provider) return ''
      const key = String(provider).toLowerCase()
      if (key === 'codex') return 'Codex'
      if (key === 'opencode') return 'OpenCode'
      if (key === 'claude' || key === 'claude_code') return 'Claude Code'
      return provider
    },
    renderedElements() {
      const elements = Array.isArray(this.message?.elements) ? this.message.elements : []
      const merged = []
      elements.forEach(el => {
        if (this.shouldHideRawTextElement(el)) {
          return
        }
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
    contentElements() {
      return this.renderedElements.filter(el => ['text', 'summary', 'result', 'error'].includes(el?.type))
    },
    progressElements() {
      return this.renderedElements.filter(el => el?.type === 'progress')
    },
    currentProgress() {
      const list = this.progressElements
      const latestEventProgress = this.latestEventProgress
      if (!list.length) return latestEventProgress
      const latest = list[list.length - 1]
      if (this.isPlaceholderProgress(latest) && latestEventProgress) {
        return latestEventProgress
      }
      return latest
    },
    latestEventProgress() {
      const events = this.executionEvents
      for (let i = events.length - 1; i >= 0; i--) {
        const event = events[i] || {}
        const title = event.title || event.data?.message || event.data?.content || ''
        if (title && title !== '正在处理...') {
          return {
            type: 'progress',
            content: title,
            status: this.eventProgressStatus(event),
            data: event.data || {},
          }
        }
      }
      return null
    },
    artifactElements() {
      const artifacts = this.renderedElements.filter(el => ['code', 'table', 'image', 'file', 'service'].includes(el?.type))
      const seen = new Set()
      return artifacts.filter(el => {
        const key = this.artifactKey(el)
        if (seen.has(key)) return false
        seen.add(key)
        return true
      })
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
    visibleRawOutput() {
      if (!this.message || this.message.sender_type !== 'agent') return ''
      const raw = String(this.message.raw_output || '').trim()
      if (!raw) return ''
      const content = String(this.message.content || '').trim()
      if (content && content === raw) return ''
      if (this.contentElements.some(el => this.normalizeDisplayText(this.elementContent(el)) === this.normalizeDisplayText(raw))) {
        return ''
      }
      return this.artifactElements.some(el => el?.type === 'table') ? this.stripMarkdownTables(raw) : raw
    },
    showRawSource() {
      return false
    },
    executionEvents() {
      return this.message?.meta?.events || []
    },
    completedProgressElements() {
      return this.progressElements.filter(el => (el.status || 'running') !== 'running')
    },
    historySteps() {
      const progressSteps = this.completedProgressElements.map(el => ({
        title: this.elementContent(el) || this.elementData(el).title || '步骤完成',
        statusClass: el.status || 'done',
        path: this.elementData(el).path || this.elementData(el).file || '',
      }))
      const eventSteps = this.executionEvents
        .filter(event => event?.type !== 'agent_progress')
        .map(event => ({
          title: event.title || event.type || '执行步骤',
          statusClass: event.type || 'event',
          path: event.data?.file || event.data?.path || '',
        }))
      return [...progressSteps, ...eventSteps]
    },
  },
  methods: {
    formatTime,
    isPlaceholderProgress(el) {
      const text = this.normalizeDisplayText(this.elementContent(el))
      return text === '正在处理' || text === '正在处理...'
    },
    eventProgressStatus(event) {
      const type = event?.type || ''
      if (type.includes('completed') || type === 'provider_output' || type === 'claude_output') return 'done'
      if (type.includes('error')) return 'error'
      if (type.includes('stopped')) return 'stopped'
      return 'running'
    },
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
    latestEventProvider() {
      const events = Array.isArray(this.message?.meta?.events) ? this.message.meta.events : []
      for (let i = events.length - 1; i >= 0; i--) {
        const event = events[i] || {}
        const provider = event.provider || event.data?.provider
        if (provider) return provider
      }
      return ''
    },
    showArtifact() {
      this.$emit('show-artifact', this.message.artifact)
    },
    artifactKey(el) {
      const data = this.elementData(el)
      return [
        el?.type || '',
        data.url || '',
        data.proxy_url || '',
        data.service_id || '',
        data.id || '',
        data.path || '',
        data.file || '',
        data.name || '',
        data.title || '',
        this.elementContent(el).slice(0, 160),
      ].join('|')
    },
    normalizeDisplayText(text) {
      return String(text || '').replace(/\s+/g, ' ').trim()
    },
    renderText(content) {
      return this.renderMarkdown(content)
    },
    renderMarkdown(content) {
      if (!content) return ''

      const blocks = []
      let html = this.escapeHtml(this.normalizeMarkdown(String(content)))

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
        const nextIndex = this.nextNonEmptyLineIndex(lines, i + 1)
        const nextLine = nextIndex === -1 ? '' : lines[nextIndex]

        if (this.isMarkdownTableRow(line) && this.isMarkdownTableSeparator(nextLine)) {
          flushList()
          const headers = this.parseMarkdownTableRow(line)
          const rows = []
          i = nextIndex + 1

          while (i < lines.length) {
            if (lines[i].trim() === '') {
              i += 1
              continue
            }
            if (!this.isMarkdownTableRow(lines[i])) break
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
    normalizeMarkdown(content) {
      const lines = String(content || '').replace(/\r\n/g, '\n').split('\n')
      const normalized = []
      for (let i = 0; i < lines.length; i++) {
        const current = lines[i]
        const trimmed = current.trim()
        if (/^-{3,}$/.test(trimmed)) {
          const prev = this.lastNonEmptyLine(normalized)
          const nextIndex = this.nextNonEmptyLineIndex(lines, i + 1)
          const next = nextIndex === -1 ? '' : lines[nextIndex]
          if (this.isMarkdownTableRow(prev) || this.isMarkdownTableRow(next)) {
            continue
          }
          normalized.push(current)
          continue
        }
        if (trimmed === '') {
          const prev = this.lastNonEmptyLine(normalized)
          const nextIndex = this.nextNonEmptyLineIndex(lines, i + 1)
          const next = nextIndex === -1 ? '' : lines[nextIndex]
          if (
            this.isMarkdownTableRow(prev) &&
            (this.isMarkdownTableRow(next) || this.isMarkdownTableSeparator(next))
          ) {
            continue
          }
        }
        normalized.push(current)
      }
      return normalized.join('\n')
    },
    lastNonEmptyLine(lines) {
      for (let i = lines.length - 1; i >= 0; i--) {
        if (String(lines[i] || '').trim() !== '') return lines[i]
      }
      return ''
    },
    nextNonEmptyLineIndex(lines, start) {
      for (let i = start; i < lines.length; i++) {
        if (String(lines[i] || '').trim() !== '') return i
      }
      return -1
    },
    stripMarkdownTables(content) {
      const lines = String(content || '').split(/\r?\n/)
      const kept = []
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]
        const nextIndex = this.nextNonEmptyLineIndex(lines, i + 1)
        const nextLine = nextIndex === -1 ? '' : lines[nextIndex]
        if (this.isMarkdownTableRow(line) && this.isMarkdownTableSeparator(nextLine)) {
          i = nextIndex + 1
          while (i < lines.length) {
            if (String(lines[i] || '').trim() === '') {
              i += 1
              continue
            }
            if (!this.isMarkdownTableRow(lines[i])) break
            i += 1
          }
          i -= 1
          continue
        }
        kept.push(line)
      }
      return kept.join('\n').trim()
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
      return cells.length >= 2 && cells.every(cell => /^:?-{2,}:?$/.test(cell.replace(/\s+/g, '')))
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
    tablePayload(el) {
      const data = this.elementData(el)
      if (Array.isArray(data.headers) || Array.isArray(data.rows)) return data
      if (data.data && (Array.isArray(data.data.headers) || Array.isArray(data.data.rows))) return data.data
      const content = this.elementContent(el)
      if (content) {
        try {
          const parsed = JSON.parse(content)
          if (parsed && (Array.isArray(parsed.headers) || Array.isArray(parsed.rows))) return parsed
          if (parsed?.data && (Array.isArray(parsed.data.headers) || Array.isArray(parsed.data.rows))) return parsed.data
        } catch (e) {}
      }
      return {}
    },
    tableHeaders(el) {
      const payload = this.tablePayload(el)
      return Array.isArray(payload.headers) ? payload.headers.map(h => String(h || '')) : []
    },
    normalizeTable(el) {
      const payload = this.tablePayload(el)
      const headers = this.tableHeaders(el)
      const rows = Array.isArray(payload.rows) ? payload.rows : []
      if (!headers.length) return []
      return rows.map(row => {
        const cells = Array.isArray(row) ? row : headers.map(h => row?.[h])
        const obj = {}
        headers.forEach((h, i) => {
          obj['col' + i] = cells[i] === undefined || cells[i] === null ? '' : String(cells[i])
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
    shouldHideRawTextElement(el) {
      if (!el || el.type !== 'text') return false
      const content = this.elementContent(el)
      if (!content || content.length < 1200) return false
      const fileDumpCount = (content.match(/##\s+\/workspace\/agents\//g) || []).length
      const fenceCount = (content.match(/```/g) || []).length
      return fileDumpCount >= 1 || fenceCount >= 4
    },
    normalizeElementForPreview(el) {
      return {
        ...this.elementData(el),
        content: this.elementContent(el),
      }
    },
    imageSrc(el) {
      const data = this.elementData(el)
      const candidate = data.url || data.src || data.path || data.file || data.name || this.elementContent(el)
      return this.resolveFileUrl(candidate)
    },
    imagePath(el) {
      const data = this.elementData(el)
      return data.path || data.file || this.pathFromUrl(data.url || data.src) || this.workspacePathFromContent(this.elementContent(el)) || ''
    },
    isImageElement(el) {
      const data = this.elementData(el)
      const value = data.path || data.file || data.url || data.src || data.name || this.elementContent(el)
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
    serviceInfo(el) {
      const data = this.elementData(el)
      const nested = data.service || data.data || {}
      return {
        ...data,
        ...nested,
        id: data.service_id || data.id || nested.service_id || nested.id || '',
        service_id: data.service_id || data.id || nested.service_id || nested.id || '',
        proxy_url: this.pickServiceUrl(data.proxy_url, nested.proxy_url, data.url, nested.url),
        url: this.pickServiceUrl(data.proxy_url, nested.proxy_url, data.url, nested.url),
      }
    },
    serviceTitle(el) {
      const svc = this.serviceInfo(el)
      return svc.title || svc.name || this.elementData(el).title || this.elementContent(el) || '预览服务'
    },
    pickServiceUrl(...urls) {
      const valid = urls.filter(url => typeof url === 'string' && url.trim())
      return valid.find(url => /[?&]token=/.test(url)) || valid[0] || ''
    },
    serviceUrl(el) {
      const svc = this.serviceInfo(el)
      return this.pickServiceUrl(svc.proxy_url, svc.url)
    },
    serviceStatusLabel(status) {
      const key = String(status || 'unknown').toLowerCase()
      return {
        running: '运行中',
        starting: '启动中',
        stopped: '已停止',
        stopping: '停止中',
        failed: '失败',
        exited: '已退出',
        open: '运行中',
        closed: '已关闭',
        unknown: '未知',
      }[key] || status
    },
    serviceStatusType(status) {
      const key = String(status || '').toLowerCase()
      if (['running', 'open'].includes(key)) return 'success'
      if (['starting', 'stopping'].includes(key)) return 'warning'
      if (['failed', 'exited'].includes(key)) return 'danger'
      return 'info'
    },
    serviceActionKey(el, action) {
      const id = this.serviceInfo(el).service_id || this.serviceInfo(el).id || 'unknown'
      return `${id}:${action}`
    },
    setServiceElement(el, patch) {
      if (!el.data) this.$set(el, 'data', {})
      Object.keys(patch || {}).forEach(key => this.$set(el.data, key, patch[key]))
    },
    openService(el) {
      this.openUrl(this.serviceUrl(el))
    },
    openUrl(url) {
      if (!url) return
      window.open(url, '_blank', 'noopener')
    },
    previewService(el) {
      const url = this.serviceUrl(el)
      if (!url) return
      this.servicePreviewUrl = url
      this.servicePreviewVisible = true
    },
    async copyServiceUrl(url) {
      if (!url) return
      try {
        await navigator.clipboard.writeText(url)
        this.$message.success('已复制服务链接')
      } catch (e) {
        this.$message.info(url)
      }
    },
    async loadServiceLogs(el) {
      const svc = this.serviceInfo(el)
      if (!this.sessionId || !svc.service_id) return
      this.serviceBusyKey = this.serviceActionKey(el, 'logs')
      this.serviceLogsLoading = true
      this.serviceLogsVisible = true
      try {
        const res = await getServiceLogs(this.sessionId, svc.service_id)
        if (res.code === 200) {
          this.serviceLogsData = res.data || {}
        }
      } catch (e) {
        this.$message.error(e?.message || '获取服务日志失败')
      } finally {
        this.serviceLogsLoading = false
        this.serviceBusyKey = ''
      }
    },
    async stopServiceCard(el) {
      const svc = this.serviceInfo(el)
      if (!this.sessionId || !svc.service_id) return
      this.serviceBusyKey = this.serviceActionKey(el, 'stop')
      try {
        const res = await stopService(this.sessionId, svc.service_id)
        if (res.code === 200) {
          const service = res.data?.service || {}
          this.setServiceElement(el, { ...service, status: service.status || 'stopped' })
          this.$message.success('服务已停止')
        }
      } catch (e) {
        this.$message.error(e?.message || '停止服务失败')
      } finally {
        this.serviceBusyKey = ''
      }
    },
    async restartServiceCard(el) {
      const svc = this.serviceInfo(el)
      if (!this.sessionId || !svc.service_id) return
      this.serviceBusyKey = this.serviceActionKey(el, 'restart')
      try {
        const res = await restartService(this.sessionId, svc.service_id)
        if (res.code === 200) {
          const service = res.data?.service || {}
          this.setServiceElement(el, { ...service, status: service.status || 'starting' })
          this.$message.success('服务已重启')
        }
      } catch (e) {
        this.$message.error(e?.message || '重启服务失败')
      } finally {
        this.serviceBusyKey = ''
      }
    },
    fileIcon(el) {
      const value = String(this.elementData(el).path || this.elementData(el).name || this.elementContent(el) || '').toLowerCase()
      if (/\.(html?|vue)$/.test(value)) return 'el-icon-monitor'
      if (/\.(md|txt|pdf|docx?)$/.test(value)) return 'el-icon-document'
      if (/\.(css|js|ts|tsx|jsx|json|py|java|go|rs)$/.test(value)) return 'el-icon-tickets'
      return 'el-icon-folder-opened'
    },
    openFileElement(data) {
      if (!data) return
      const path = data.path || data.file || this.pathFromUrl(data.url) || this.pathFromUrl(data.src) || this.workspacePathFromContent(data.content) || data.name
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
    workspacePathFromContent(content) {
      const text = String(content || '').trim()
      if (!text) return ''
      if (text.startsWith('/workspace/') || text.startsWith('workspace/')) return text
      return ''
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

.provider-tag {
  font-size: 11px;
  line-height: 18px;
  padding: 0 6px;
  border-radius: 4px;
  background: #eef2ff;
  color: #475569;
  border: 1px solid #dbe3ff;
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
  padding: 12px 14px;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
  border: 1px solid #e8edf5;
}

.own .bubble-inner {
  background: #f0f5ff;
  border-color: #e0ebff;
}

/* ===== Elements ===== */
.bubble-elements {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.artifact-section {
  margin-top: 10px;
}

.content-section + .artifact-section,
.raw-rendered + .artifact-section {
  margin-top: 12px;
}

.section-title {
  font-size: 12px;
  line-height: 1;
  color: #64748b;
  font-weight: 600;
  margin-bottom: -2px;
}

.current-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  margin-bottom: 10px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #f8fbff;
  color: #334155;
  font-size: 12px;
}

.current-progress-label {
  color: #2563eb;
  font-weight: 600;
  white-space: nowrap;
}

.current-progress-text {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.el-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  background: #f8fbff;
  border: 1px solid #e2ecf8;
  border-radius: 6px;
  font-size: 12px;
  color: #475569;
}

.el-result {
  padding: 10px 12px;
  border: 1px solid #d7e8ff;
  border-radius: 8px;
  background: #f8fbff;
  max-width: 100%;
}

.el-error {
  padding: 10px 12px;
  border: 1px solid #fde2e2;
  border-radius: 8px;
  background: #fff5f5;
}

.error-title {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  color: #dc2626;
  font-size: 12px;
  font-weight: 600;
}

.error-content {
  font-size: 13px;
  line-height: 1.6;
  color: #7f1d1d;
}

.result-title {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  color: #2563eb;
  font-size: 12px;
  font-weight: 600;
}

.result-content {
  font-size: 13px;
  line-height: 1.68;
  color: #1e293b;
  max-width: 100%;
}

.result-content :deep(p) {
  margin: 0 0 6px;
}

.result-content :deep(p:last-child) {
  margin-bottom: 0;
}

.result-content :deep(h1),
.result-content :deep(h2),
.result-content :deep(h3) {
  margin: 10px 0 7px;
  line-height: 1.35;
  color: #0f172a;
}

.result-content :deep(h1) {
  font-size: 18px;
}

.result-content :deep(h2) {
  font-size: 16px;
}

.result-content :deep(h3) {
  font-size: 15px;
}

.result-content :deep(ul) {
  margin: 4px 0 8px;
  padding-left: 20px;
}

.result-content :deep(li) {
  margin: 2px 0;
}

.result-content :deep(blockquote) {
  margin: 8px 0;
  padding: 7px 10px;
  border-left: 3px solid #93c5fd;
  background: #f8fafc;
  color: #475569;
}

.result-content :deep(pre) {
  background: #111827;
  color: #e5e7eb;
  padding: 12px;
  border-radius: 7px;
  overflow: auto;
  max-height: 420px;
  font-size: 12px;
  margin: 8px 0;
  border: 1px solid #1f2937;
}

.result-content :deep(code) {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  color: #b45309;
}

.result-content :deep(pre code) {
  background: transparent;
  padding: 0;
  color: inherit;
}

.result-content :deep(.markdown-table-wrap) {
  overflow-x: auto;
  margin: 8px 0;
}

.result-content :deep(.markdown-table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  background: #fff;
}

.result-content :deep(.markdown-table th),
.result-content :deep(.markdown-table td) {
  border: 1px solid #e2e8f0;
  padding: 7px 9px;
  text-align: left;
  vertical-align: top;
}

.result-content :deep(.markdown-table th) {
  background: #f8fafc;
  font-weight: 600;
  color: #334155;
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
  overflow: auto;
  max-height: 360px;
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
  background: #111827;
  color: #e5e7eb;
  font-size: 12px;
  line-height: 1.5;
  overflow-x: auto;
  max-height: 360px;
  overflow-y: auto;
}

.code-body code {
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  white-space: pre;
}

/* Artifacts */
.artifact-block {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fbfdff;
  overflow: hidden;
}

.artifact-header {
  min-height: 34px;
  padding: 8px 11px;
  display: flex;
  align-items: center;
  gap: 7px;
  border-bottom: 1px solid #e8edf5;
  color: #334155;
  font-size: 12px;
  font-weight: 600;
  background: #f8fafc;
}

.artifact-header i {
  color: #4080ff;
  font-size: 15px;
}

.artifact-meta {
  padding: 1px 7px;
  border-radius: 999px;
  background: #eef2ff;
  color: #64748b;
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
}

.artifact-title-btn {
  border: none;
  background: transparent;
  padding: 0;
  min-width: 0;
  color: #2563eb;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.artifact-title-btn:hover {
  text-decoration: underline;
}

.table-scroll {
  overflow-x: auto;
  padding: 10px;
}

.table-block :deep(.el-table) {
  border-radius: 6px;
  overflow: hidden;
}

.table-block :deep(.el-table th.el-table__cell) {
  background: #f1f5f9;
  color: #334155;
  font-weight: 600;
}

.image-frame {
  padding: 10px;
  background: #ffffff;
}

.artifact-image {
  display: block;
  max-width: 100%;
  max-height: 420px;
  object-fit: contain;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
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

.file-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.file-card:hover {
  border-color: #9fc7ff;
  background: #f7fbff;
}

.file-icon {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #eaf3ff;
  color: #2563eb;
  flex-shrink: 0;
}

.file-icon i {
  font-size: 18px;
}

.file-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.file-link-btn {
  border: none;
  background: transparent;
  padding: 0;
  color: #1e293b;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-path {
  color: #94a3b8;
  font-size: 11px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  font-size: 11px;
  color: #94a3b8;
  margin-left: auto;
}

.service-card {
  padding: 0;
  background: #ffffff;
}

.service-card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-bottom: 1px solid #e8edf5;
  background: #f8fbff;
}

.service-icon {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #eaf3ff;
  color: #2563eb;
  flex-shrink: 0;
}

.service-title-wrap {
  min-width: 0;
  flex: 1;
}

.service-card-title {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.service-subtitle {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 3px;
  color: #64748b;
  font-size: 11px;
}

.service-description {
  padding: 10px 12px 0;
  font-size: 13px;
  line-height: 1.6;
  color: #334155;
}

.service-description :deep(p) {
  margin: 0 0 6px;
}

.service-url-row {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 10px 12px 0;
  padding: 8px 10px;
  border: 1px solid #dbeafe;
  border-radius: 7px;
  background: #f8fbff;
  font-size: 12px;
}

.service-url-row i {
  color: #4080ff;
}

.service-url-row a {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #2563eb;
  text-decoration: none;
}

.service-meta-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 7px;
  margin: 10px 12px 0;
}

.service-meta-item {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  font-size: 12px;
}

.service-meta-item span {
  width: 34px;
  color: #64748b;
  flex-shrink: 0;
}

.service-meta-item code {
  min-width: 0;
  flex: 1;
  padding: 5px 7px;
  border-radius: 6px;
  background: #f1f5f9;
  color: #475569;
  font-size: 11px;
  word-break: break-all;
}

.service-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  padding: 12px;
}

.steps-collapse {
  margin-top: 10px;
  border-top: 1px solid #f0f0f0;
  border-bottom: none;
}

.steps-collapse :deep(.el-collapse-item__header) {
  height: 32px;
  line-height: 32px;
  font-size: 12px;
  color: #64748b;
  border-bottom: none;
}

.steps-collapse :deep(.el-collapse-item__wrap) {
  border-bottom: none;
}

.steps-panel {
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
  overflow: auto;
  max-height: 360px;
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

.raw-rendered {
  margin-top: 10px;
  padding: 12px 13px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
}

.raw-rendered-content {
  font-size: 14px;
  line-height: 1.68;
  color: #1e293b;
  word-wrap: break-word;
}

.raw-rendered-content :deep(p) {
  margin: 0 0 8px;
}

.raw-rendered-content :deep(p:last-child) {
  margin-bottom: 0;
}

.raw-rendered-content :deep(pre) {
  background: #111827;
  color: #e5e7eb;
  padding: 12px;
  border-radius: 7px;
  overflow: auto;
  max-height: 420px;
  font-size: 12px;
  margin: 8px 0;
  border: 1px solid #1f2937;
}

.raw-rendered-content :deep(code) {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  color: #b45309;
}

.raw-rendered-content :deep(pre code) {
  background: transparent;
  padding: 0;
  color: inherit;
}

.raw-rendered-content :deep(.markdown-table-wrap) {
  overflow-x: auto;
  margin: 8px 0;
}

.raw-rendered-content :deep(.markdown-table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  background: #fff;
}

.raw-rendered-content :deep(.markdown-table th),
.raw-rendered-content :deep(.markdown-table td) {
  border: 1px solid #e2e8f0;
  padding: 7px 9px;
  text-align: left;
  vertical-align: top;
}

.raw-rendered-content :deep(.markdown-table th) {
  background: #f8fafc;
  font-weight: 600;
  color: #334155;
}

.raw-rendered-content :deep(h1),
.raw-rendered-content :deep(h2),
.raw-rendered-content :deep(h3) {
  margin: 10px 0 7px;
  line-height: 1.35;
  color: #0f172a;
}

.raw-rendered-content :deep(h1) {
  font-size: 18px;
}

.raw-rendered-content :deep(h2) {
  font-size: 16px;
}

.raw-rendered-content :deep(h3) {
  font-size: 15px;
}

.raw-rendered-content :deep(ul) {
  margin: 4px 0 8px;
  padding-left: 20px;
}

.raw-rendered-content :deep(blockquote) {
  margin: 8px 0;
  padding: 7px 10px;
  border-left: 3px solid #93c5fd;
  background: #f8fafc;
  color: #475569;
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

.service-preview-dialog :deep(.el-dialog) {
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.24);
}

.service-preview-dialog :deep(.el-dialog__header) {
  padding: 16px 18px 14px;
  border-bottom: 1px solid #e8edf5;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
}

.service-preview-dialog :deep(.el-dialog__title) {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.service-preview-dialog :deep(.el-dialog__headerbtn) {
  top: 16px;
}

.service-preview-dialog :deep(.el-dialog__body) {
  padding: 0;
  background: #f8fafc;
}

.service-preview-toolbar {
  min-height: 48px;
  padding: 0 16px;
  border-bottom: 1px solid #e8edf5;
  display: flex;
  align-items: center;
  gap: 10px;
  background: #ffffff;
}

.service-preview-toolbar span {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  color: #475569;
}

.service-preview-frame {
  display: block;
  width: 100%;
  height: 74vh;
  border: none;
  background: #ffffff;
}

.service-logs-dialog :deep(.el-dialog__body) {
  padding: 14px 18px 18px;
}

.service-logs-meta {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

.service-log-section + .service-log-section {
  margin-top: 12px;
}

.service-log-title {
  font-size: 12px;
  font-weight: 700;
  color: #475569;
  margin-bottom: 5px;
}

.service-log-section pre {
  margin: 0;
  padding: 10px;
  min-height: 90px;
  max-height: 240px;
  overflow: auto;
  border-radius: 7px;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
}
</style>
