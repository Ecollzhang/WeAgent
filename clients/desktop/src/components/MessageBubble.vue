<template>
  <div class="message-bubble web-message-bubble" :class="{ own: isOwn }">
    <div class="bubble-sender" v-if="message.sender_type === 'agent'">
      <span class="agent-tag">{{ getSenderName() }}</span>
      <span v-if="providerLabel" class="provider-tag">{{ providerLabel }}</span>
      <span v-if="message.status" class="status-tag" :class="'status-' + message.status">
        {{ statusLabel(message.status) }}
      </span>
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
          <div v-if="el.type === 'text'" class="el-text" v-html="renderText(elementContent(el))"></div>

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

          <div v-else-if="el.type === 'result' || el.type === 'summary'" class="el-result">
            <div class="result-title">
              <i class="el-icon-finished"></i>
              <span>{{ elementData(el).title || (el.type === 'summary' ? '完成摘要' : '执行结果') }}</span>
            </div>
            <div class="result-content" v-html="renderText(elementContent(el))"></div>
          </div>
        </div>
      </div>

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
                <button type="button" @click="copyCode(elementContent(el))">复制</button>
                <button type="button" @click="previewCode(el)">预览</button>
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
              <table v-if="tableHeaders(el).length" class="artifact-table">
                <thead>
                  <tr>
                    <th v-for="(h, hi) in tableHeaders(el)" :key="hi">{{ h }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, ri) in normalizeTable(el)" :key="ri">
                    <td v-for="(h, hi) in tableHeaders(el)" :key="hi">{{ row['col' + hi] }}</td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="el-text" v-html="renderText(elementContent(el))"></div>
            </div>
          </div>

          <div
            v-else-if="el.type === 'file' || el.type === 'image'"
            class="artifact-block file-card artifact-openable"
            @click="openArtifactFile(el)"
          >
            <div class="file-icon"><i :class="fileIcon(el)"></i></div>
            <div class="file-main">
              <button type="button" class="file-link-btn" @click.stop="openArtifactFile(el)">
                {{ displayFileName(el) }}
              </button>
              <span class="file-path">{{ elementData(el).path || elementData(el).url || elementContent(el) }}</span>
            </div>
            <span v-if="elementData(el).size" class="file-size">{{ formatFileSize(elementData(el).size) }}</span>
          </div>

          <div
            v-else-if="el.type === 'diff'"
            class="artifact-block diff-card artifact-openable"
            @click="openArtifactFile(el)"
          >
            <div class="artifact-header">
              <i class="el-icon-document-checked"></i>
              <span>{{ elementData(el).filename || elementData(el).path || 'Diff 产物' }}</span>
              <span class="artifact-meta">diff</span>
            </div>
            <div class="diff-summary">
              <span class="diff-stat add">+{{ (elementData(el).diff_stat && elementData(el).diff_stat.additions) || 0 }}</span>
              <span class="diff-stat del">-{{ (elementData(el).diff_stat && elementData(el).diff_stat.deletions) || 0 }}</span>
              <span class="diff-path">{{ elementData(el).path || '点击在工作台打开' }}</span>
            </div>
          </div>

          <div
            v-else-if="el.type === 'workflow'"
            class="artifact-block file-card artifact-openable"
            @click="previewWorkflow(el)"
          >
            <div class="file-icon"><i class="el-icon-share"></i></div>
            <div class="file-main">
              <button type="button" class="file-link-btn" @click.stop="previewWorkflow(el)">
                {{ elementData(el).name || '任务分配工作流' }}
              </button>
              <span class="file-path">{{ workflowSubtitle(el) }}</span>
              <pre class="workflow-json-preview" @click.stop>{{ workflowRawJson(el) }}</pre>
            </div>
            <div class="workflow-actions" @click.stop>
              <button type="button" class="workflow-preview-btn" @click="copyCode(workflowRawJson(el))">复制</button>
              <button type="button" class="workflow-preview-btn" @click="previewWorkflow(el)">预览</button>
            </div>
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
              <span class="status-tag" :class="'status-' + serviceInfo(el).status">
                {{ serviceStatusLabel(serviceInfo(el).status) }}
              </span>
            </div>
            <div v-if="elementContent(el)" class="service-description" v-html="renderText(elementContent(el))"></div>
            <div class="service-url-row" v-if="serviceUrl(el)">
              <i class="el-icon-link"></i>
              <a :href="serviceUrl(el)" target="_blank" rel="noopener">{{ serviceUrl(el) }}</a>
            </div>
          </div>
        </div>
      </div>

      <details v-if="historySteps.length" class="steps-collapse">
        <summary>进度（{{ historySteps.length }}）</summary>
        <div class="steps-panel">
          <div v-for="(step, index) in historySteps" :key="index" class="step-item">
            <span class="step-dot" :class="'step-' + step.statusClass"></span>
            <div class="step-main">
              <div class="step-title">{{ step.title }}</div>
              <button v-if="step.path" type="button" class="step-file">{{ normalizeWorkspacePath(step.path) }}</button>
            </div>
          </div>
        </div>
      </details>

      <div v-if="!visibleRawOutput && !contentElements.length && !artifactElements.length" class="bubble-content" v-html="renderedContent"></div>

      <details v-if="message.sender_type === 'agent' && message.raw_output && showRawSource" class="raw-collapse">
        <summary>Raw output</summary>
        <pre class="raw-output">{{ message.raw_output }}</pre>
      </details>

      <div v-if="message.status === 'streaming'" class="streaming-line">
        <i class="el-icon-loading"></i>
        <span>输出中...</span>
      </div>

      <div class="bubble-meta">
        <span class="bubble-time">{{ formatTime(message.created_at) }}</span>
        <span v-if="selectedWorkflowLabel" class="message-workflow-tag">
          工作流：{{ selectedWorkflowLabel }}
        </span>
        <span v-if="isTempMessage" class="bubble-sending">
          <i class="el-icon-loading"></i> 发送中...
        </span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'DesktopMessageBubble',
  props: {
    message: Object,
    isOwn: Boolean,
    serverUrl: { type: String, default: '' },
  },
  computed: {
    providerLabel() {
      const provider = (this.message && this.message.meta && this.message.meta.provider) || this.latestEventProvider()
      if (!provider) return ''
      const key = String(provider).toLowerCase()
      if (key === 'codex') return 'Codex'
      if (key === 'opencode') return 'OpenCode'
      if (key === 'claude' || key === 'claude_code') return 'Claude Code'
      return provider
    },
    renderedElements() {
      const elements = Array.isArray(this.message && this.message.elements) ? this.message.elements : []
      const merged = []
      elements.forEach(el => {
        if (this.shouldHideRawTextElement(el)) return
        const last = merged[merged.length - 1]
        if (el && el.type === 'text' && last && last.type === 'text') {
          const content = this.elementContent(last) + this.elementContent(el)
          merged[merged.length - 1] = {
            ...last,
            content,
            data: { ...(last.data || {}), content },
          }
        } else {
          merged.push(el)
        }
      })
      return merged
    },
    contentElements() {
      return this.renderedElements.filter(el => ['text', 'summary', 'result', 'error'].includes(el && el.type))
    },
    progressElements() {
      return this.renderedElements.filter(el => el && el.type === 'progress')
    },
    currentProgress() {
      const list = this.progressElements
      const latestEventProgress = this.latestEventProgress
      if (!list.length) return latestEventProgress
      const latest = list[list.length - 1]
      if (this.isPlaceholderProgress(latest) && latestEventProgress) return latestEventProgress
      return latest
    },
    latestEventProgress() {
      const events = this.executionEvents
      for (let i = events.length - 1; i >= 0; i--) {
        const event = events[i] || {}
        const title = event.title || (event.data && (event.data.message || event.data.content)) || ''
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
      const artifacts = this.renderedElements.filter(el => {
        if (this.isModeratorPlanArtifact(el)) return false
        return ['code', 'table', 'image', 'file', 'service', 'diff', 'workflow'].includes(el && el.type)
      })
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
    selectedWorkflowLabel() {
      if (!this.message || this.message.sender_type !== 'user') return ''
      const workflow = this.message.meta && this.message.meta.selected_workflow
      if (!workflow || typeof workflow !== 'object') return ''
      const name = workflow.name || '未命名工作流'
      const nodeCount = Array.isArray(workflow.nodes) ? workflow.nodes.length : 0
      const edgeCount = Array.isArray(workflow.edges) ? workflow.edges.length : 0
      return `${name}（${nodeCount} 节点 · ${edgeCount} 连线）`
    },
    renderedContent() {
      if (!this.message || !this.message.content) return ''
      return this.renderMarkdown(this.message.content)
    },
    visibleRawOutput() {
      if (!this.message || this.message.sender_type !== 'agent') return ''
      const raw = String(this.message.raw_output || '').trim()
      if (!raw) return ''
      if (this.contentElements.length) return ''
      if (this.contentElements.some(el => this.normalizeDisplayText(this.elementContent(el)) === this.normalizeDisplayText(raw))) return ''
      const output = this.artifactElements.some(el => el && el.type === 'table') ? this.stripMarkdownTables(raw) : raw
      return this.formatRawOutputForDisplay(output)
    },
    showRawSource() {
      return Boolean(this.visibleRawOutput)
    },
    executionEvents() {
      const events = (this.message && this.message.meta && (this.message.meta.execution_events || this.message.meta.events))
        || (this.message && this.message.execution_events)
        || (this.message && this.message.events)
        || []
      return Array.isArray(events) ? events : []
    },
    historySteps() {
      const progressSteps = this.progressElements.map(el => ({
        title: this.elementContent(el) || this.elementData(el).title || '步骤完成',
        statusClass: el.status || 'running',
        path: this.elementData(el).path || '',
      }))
      const eventSteps = this.executionEvents
        .map(event => ({
          title: event.title || (event.data && (event.data.message || event.data.content || event.data.path)) || event.type || '',
          statusClass: event.status || event.type || 'running',
          path: (event.data && (event.data.path || event.data.file)) || '',
        }))
        .filter(step => step.title)
      return [...progressSteps, ...eventSteps]
    },
  },
  methods: {
    formatRawOutputForDisplay(raw) {
      const text = String(raw || '').trim()
      if (!text) return ''
      if (!this.isModeratorPlanRaw(text)) return text
      return `主持人任务分派 JSON\n\n\`\`\`json\n${text.replace(/```/g, '`\\`\\`')}\n\`\`\``
    },
    isModeratorPlanRaw(text) {
      const raw = String(text || '').trim()
      const lowered = raw.toLowerCase()
      if (!raw.startsWith('{') && !raw.startsWith('```')) return false
      if (!/["']?tasks["']?\s*:/.test(lowered)) return false
      return /["']?type["']?\s*:\s*["']?plan/.test(lowered) ||
        /["']?parallel_groups["']?\s*:/.test(lowered) ||
        /["']?selected_agents["']?\s*:/.test(lowered)
    },
    isModeratorPlanArtifact(el) {
      if (!el || el.type === 'workflow') return false
      const data = this.elementData(el)
      const values = [
        data.path,
        data.file_path,
        data.filePath,
        data.file,
        data.url,
        data.src,
        data.name,
        data.filename,
        data.title,
        this.elementContent(el),
      ]
      return values.some(value => String(value || '').toLowerCase().includes('moderator-plan.json'))
    },
    getSenderName() {
      return (this.message && (this.message.sender_name || this.message.sender_id)) || '智能体'
    },
    previewCode(el) {
      const data = this.elementData(el)
      if (data.workflow) {
        this.$emit('preview-workflow', data.workflow)
        return
      }
      const payload = this.artifactFilePayload(el)
      if (payload.path) {
        this.$emit('open-file', payload)
      } else {
        this.$emit('preview-artifact', {
          id: this.artifactKey(el),
          type: 'code',
          data,
          element: el,
          message: this.message || {},
        })
      }
    },
    previewWorkflow(el) {
      const workflow = this.elementData(el)
      this.$emit('preview-workflow', {
        ...workflow,
        name: workflow.name || '任务分配工作流',
      })
    },
    workflowSubtitle(el) {
      const data = this.elementData(el)
      const nodeCount = Array.isArray(data.nodes) ? data.nodes.length : 0
      const edgeCount = Array.isArray(data.edges) ? data.edges.length : 0
      return `${nodeCount} 节点 · ${edgeCount} 连线`
    },
    workflowRawJson(el) {
      const data = this.elementData(el)
      const raw = data.raw_plan || data.plan || data
      try {
        return JSON.stringify(raw, null, 2)
      } catch (error) {
        return String(raw || '')
      }
    },
    statusLabel(status) {
      const map = {
        pending: '等待中',
        streaming: '输出中',
        done: '已完成',
        completed: '已完成',
        error: '失败',
        stopped: '已停止',
      }
      return map[status] || status
    },
    latestEventProvider() {
      const event = this.executionEvents.find(item => item && (item.provider || (item.data && item.data.provider)))
      return event ? (event.provider || event.data.provider) : ''
    },
    shouldHideRawTextElement(el) {
      if (!el || el.type !== 'text' || !this.message || !this.message.raw_output) return false
      const text = this.normalizeDisplayText(this.elementContent(el))
      const raw = this.normalizeDisplayText(this.message.raw_output)
      return text && raw && text === raw
    },
    isPlaceholderProgress(el) {
      const text = this.normalizeDisplayText(this.elementContent(el))
      return !text || text === '正在处理...'
    },
    eventProgressStatus(event) {
      const status = event.status || (event.data && event.data.status) || ''
      if (status) return status
      if (/error|failed|fail/i.test(event.type || '')) return 'error'
      if (/complete|done|finish/i.test(event.type || '')) return 'done'
      return 'running'
    },
    renderText(content) {
      return this.renderMarkdown(content)
    },
    renderMarkdown(content) {
      if (!content) return ''
      const normalized = this.normalizeMarkdown(String(content))
      const codeBlocks = []
      let html = this.escapeHtml(normalized)
      html = html.replace(/```([\w-]*)\n?([\s\S]*?)```/g, (match, lang, code) => {
        const token = `@@CODE_BLOCK_${codeBlocks.length}@@`
        codeBlocks.push({ lang, code })
        return token
      })
      html = this.renderBlockMarkdown(html)
      codeBlocks.forEach((block, index) => {
        const lang = block.lang ? `<div class="code-lang">${this.escapeHtml(block.lang)}</div>` : ''
        const code = `<pre><code>${this.escapeHtml(block.code.trim())}</code></pre>`
        html = html.replace(`@@CODE_BLOCK_${index}@@`, lang + code)
      })
      return html
    },
    renderBlockMarkdown(content) {
      const lines = content.split(/\n/)
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
          i += 2
          const rows = []
          while (i < lines.length) {
            if (!this.isMarkdownTableRow(lines[i])) break
            rows.push(this.parseMarkdownTableRow(lines[i]))
            i += 1
          }
          i -= 1
          rendered.push(this.renderMarkdownTable(headers, rows))
        } else if (/^\s*[-*+]\s+/.test(line)) {
          listBuffer.push(`<li>${this.renderInlineMarkdown(line.replace(/^\s*[-*+]\s+/, ''))}</li>`)
        } else {
          flushList()
          if (!line.trim()) {
            rendered.push('')
          } else if (/^###\s+/.test(line)) {
            rendered.push(`<h3>${this.renderInlineMarkdown(line.replace(/^###\s+/, ''))}</h3>`)
          } else if (/^##\s+/.test(line)) {
            rendered.push(`<h2>${this.renderInlineMarkdown(line.replace(/^##\s+/, ''))}</h2>`)
          } else if (/^#\s+/.test(line)) {
            rendered.push(`<h1>${this.renderInlineMarkdown(line.replace(/^#\s+/, ''))}</h1>`)
          } else if (/^>\s?/.test(line)) {
            rendered.push(`<blockquote>${this.renderInlineMarkdown(line.replace(/^>\s?/, ''))}</blockquote>`)
          } else if (/^!\[[^\]]*\]\(([^)]+)\)/.test(line)) {
            const src = line.match(/^!\[[^\]]*\]\(([^)]+)\)/)[1]
            rendered.push(`<p><img class="inline-markdown-image" src="${this.resolveUrl(src)}" alt=""></p>`)
          } else {
            rendered.push(`<p>${this.renderInlineMarkdown(line)}</p>`)
          }
        }
      }
      flushList()
      return rendered.join('')
    },
    normalizeMarkdown(content) {
      return content.replace(/\r\n/g, '\n').replace(/\n{3,}/g, '\n\n')
    },
    stripMarkdownTables(content) {
      const lines = String(content || '').split(/\n/)
      const kept = []
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]
        const nextLine = lines[i + 1] || ''
        if (this.isMarkdownTableRow(line) && this.isMarkdownTableSeparator(nextLine)) {
          i += 2
          while (i < lines.length && this.isMarkdownTableRow(lines[i])) i += 1
          i -= 1
        } else {
          kept.push(line)
        }
      }
      return kept.join('\n').trim()
    },
    renderInlineMarkdown(text) {
      return String(text || '')
        .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (m, alt, src) => `<img class="inline-markdown-image" src="${this.resolveUrl(src)}" alt="${this.escapeHtml(alt)}">`)
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    },
    isMarkdownTableRow(line) {
      const text = String(line || '').trim()
      return text.includes('|') && this.parseMarkdownTableRow(text).length >= 2
    },
    isMarkdownTableSeparator(line) {
      if (!this.isMarkdownTableRow(line)) return false
      return this.parseMarkdownTableRow(line).every(cell => /^:?-{3,}:?$/.test(cell.trim()))
    },
    parseMarkdownTableRow(line) {
      return String(line || '').trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(cell => cell.trim())
    },
    renderMarkdownTable(headers, rows) {
      const thead = headers.map(header => `<th>${this.renderInlineMarkdown(header)}</th>`).join('')
      const body = rows
        .map(row => `<tr>${headers.map((_, index) => `<td>${this.renderInlineMarkdown(row[index] || '')}</td>`).join('')}</tr>`)
        .join('')
      return `<div class="markdown-table-wrap"><table class="markdown-table"><thead><tr>${thead}</tr></thead><tbody>${body}</tbody></table></div>`
    },
    normalizeDisplayText(text) {
      return String(text || '').replace(/\s+/g, ' ').trim()
    },
    elementData(el) {
      return (el && el.data) || {}
    },
    elementContent(el) {
      const data = this.elementData(el)
      return String((el && el.content) || data.content || data.text || data.message || '')
    },
    openArtifactFile(el) {
      const payload = this.artifactFilePayload(el)
      if (!payload.path) return
      this.$emit('open-file', payload)
    },
    artifactFilePayload(el) {
      const data = this.elementData(el)
      const raw = data.path || data.file_path || data.filePath || data.file || data.url || data.src || this.elementContent(el)
      const path = this.normalizeArtifactFilePath(raw)
      return {
        path,
        raw,
        name: data.name || data.filename || data.title || this.fileNameFromPath(path || raw),
        agent_id: data.agent_id || data.agentId || data.owner_agent_id || data.ownerAgentId || '',
        type: el && el.type ? el.type : 'file',
        data,
        element: el,
      }
    },
    normalizeArtifactFilePath(value) {
      let path = String(value || '').trim()
      if (!path) return ''
      try {
        if (/^https?:\/\//i.test(path)) {
          const url = new URL(path)
          const queryPath = url.searchParams.get('path') || url.searchParams.get('file') || url.searchParams.get('file_path')
          const urlPath = decodeURIComponent(url.pathname || '')
          path = queryPath || (urlPath.includes('/workspace/') ? urlPath : '')
        }
      } catch (error) {
        // Keep the original value when URL parsing is not possible.
      }
      const workspaceIndex = path.indexOf('/workspace/')
      if (workspaceIndex >= 0) return path.slice(workspaceIndex)
      if (path.indexOf('workspace/') === 0) return `/${path}`
      return path
    },
    fileNameFromPath(value) {
      const parts = String(value || '').split(/[\\/]/).filter(Boolean)
      return parts.length ? parts[parts.length - 1] : String(value || '')
    },
    displayFileName(el) {
      const data = this.elementData(el)
      const preferred = data.name || data.filename || data.title || this.elementContent(el)
      const normalizedPath = data.path || data.file || data.url || preferred
      return this.fileNameFromPath(preferred) || this.fileNameFromPath(normalizedPath) || '文件'
    },
    artifactKey(el) {
      const data = this.elementData(el)
      return [el.type, data.path, data.url, data.name, data.filename, this.elementContent(el).slice(0, 120)].join('|')
    },
    normalizeTable(el) {
      const data = this.elementData(el)
      const rows = Array.isArray(data.rows) ? data.rows : []
      if (rows.length && !Array.isArray(rows[0])) return rows
      return rows.map(row => {
        const item = {}
        row.forEach((value, index) => {
          item[`col${index}`] = value
        })
        return item
      })
    },
    tableHeaders(el) {
      const data = this.elementData(el)
      if (Array.isArray(data.headers)) return data.headers
      const rows = this.normalizeTable(el)
      return rows[0] ? Object.keys(rows[0]) : []
    },
    imageSrc(el) {
      const data = this.elementData(el)
      const candidate = data.url || data.src || data.path || data.file || this.elementContent(el)
      return this.resolveUrl(candidate)
    },
    isImageElement(el) {
      const data = this.elementData(el)
      const value = String(data.path || data.file || data.url || data.src || data.name || this.elementContent(el) || '').toLowerCase()
      return /\.(png|jpe?g|gif|webp|svg)$/.test(value)
    },
    fileIcon(el) {
      const value = String(this.elementData(el).name || this.elementContent(el) || '').toLowerCase()
      if (/\.(png|jpe?g|gif|webp|svg)$/.test(value)) return 'el-icon-picture-outline'
      if (/\.(zip|rar|7z)$/.test(value)) return 'el-icon-folder'
      if (/\.(js|vue|py|java|ts|css|html)$/.test(value)) return 'el-icon-tickets'
      return 'el-icon-document'
    },
    serviceInfo(el) {
      return this.elementData(el).service || this.elementData(el)
    },
    serviceTitle(el) {
      const svc = this.serviceInfo(el)
      return svc.title || svc.name || this.elementData(el).title || this.elementContent(el) || '预览服务'
    },
    serviceUrl(el) {
      const svc = this.serviceInfo(el)
      return svc.url || svc.public_url || ''
    },
    serviceStatusLabel(status) {
      const map = { running: '运行中', stopped: '已停止', error: '异常', starting: '启动中' }
      return map[status] || status || '未知'
    },
    normalizeWorkspacePath(path) {
      return String(path || '').replace(/^\/workspace\//, '')
    },
    formatFileSize(size) {
      const value = Number(size)
      if (!Number.isFinite(value)) return ''
      if (value < 1024) return `${value} B`
      if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
      return `${(value / 1024 / 1024).toFixed(1)} MB`
    },
    formatTime(value) {
      if (!value) return ''
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return ''
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    },
    resolveUrl(value) {
      const clean = String(value || '')
      if (/^(data:|blob:|https?:\/\/)/i.test(clean)) return clean
      if (!clean) return ''
      const base = String(this.serverUrl || '').replace(/\/+$/, '')
      return `${base}${clean.startsWith('/') ? clean : `/${clean}`}`
    },
    escapeHtml(text) {
      return String(text || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;')
    },
    async copyCode(code) {
      if (navigator.clipboard) await navigator.clipboard.writeText(code)
    },
  },
}
</script>

<style scoped>
.workflow-json-preview {
  width: 100%;
  max-height: 180px;
  margin: 8px 0 0;
  padding: 10px 12px;
  border: 1px solid #dde6f2;
  border-radius: 8px;
  background: #f3f6fb;
  color: #111827;
  font-size: 12px;
  line-height: 1.5;
  text-align: left;
  overflow: auto;
  white-space: pre;
  scrollbar-width: thin;
  scrollbar-color: #c7d3e4 transparent;
}

.workflow-json-preview::-webkit-scrollbar,
.code-body::-webkit-scrollbar,
.table-scroll::-webkit-scrollbar,
.raw-output::-webkit-scrollbar {
  width: 3px;
  height: 3px;
}

.workflow-json-preview::-webkit-scrollbar-track,
.code-body::-webkit-scrollbar-track,
.table-scroll::-webkit-scrollbar-track,
.raw-output::-webkit-scrollbar-track {
  background: transparent;
}

.workflow-json-preview::-webkit-scrollbar-thumb,
.code-body::-webkit-scrollbar-thumb,
.table-scroll::-webkit-scrollbar-thumb,
.raw-output::-webkit-scrollbar-thumb {
  background: #c7d3e4;
  border-radius: 999px;
}

.workflow-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.workflow-preview-btn {
  border: 1px solid #d8e6ff;
  border-radius: 999px;
  background: #f8fbff;
  color: #2563eb;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  padding: 6px 12px;
}
</style>
