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
      <div v-if="artifactCards.length" class="bubble-elements artifact-section">
        <div class="section-title">产物</div>
        <div
          v-for="card in artifactCards"
          :key="card.key"
          class="el-block"
          :class="'artifact-card-' + card.kind"
        >
          <div class="artifact-block file-card" :class="{ 'image-card': !!card.imageElement, 'table-card': !!card.tableElement }">
            <div class="artifact-header">
              <i :class="fileIcon(card.primaryElement || card.diffElement)"></i>
              <button
                v-if="card.path"
                class="artifact-title-btn"
                @click="openArtifactCard(card)"
              >
                {{ card.displayName }}
              </button>
              <span v-else class="artifact-title-text">{{ card.displayName }}</span>
              <span class="artifact-meta">{{ card.metaLabel }}</span>
              <span v-if="card.sizeLabel" class="artifact-meta artifact-size">{{ card.sizeLabel }}</span>
              <div class="artifact-actions">
                <el-button
                  v-if="card.path"
                  size="mini"
                  type="text"
                  icon="el-icon-download"
                  @click.stop="downloadFile(card.path)"
                >下载</el-button>
                <el-button
                  v-if="card.editElement"
                  size="mini"
                  type="text"
                  icon="el-icon-edit"
                  @click.stop="editCode(card.editElement)"
                >编辑</el-button>
                <el-button
                  v-if="card.tableElement && !card.tableElement._editing"
                  size="mini"
                  type="text"
                  icon="el-icon-edit"
                  @click.stop="startEditTable(card.tableElement)"
                >编辑</el-button>
                <template v-if="card.tableElement && card.tableElement._editing">
                  <el-button size="mini" type="text" icon="el-icon-plus" @click.stop="addTableRow(card.tableElement)">加行</el-button>
                  <el-button size="mini" type="success" icon="el-icon-check" @click.stop="saveTable(card.tableElement)">保存</el-button>
                  <el-button size="mini" type="text" icon="el-icon-close" @click.stop="cancelEditTable(card.tableElement)">取消</el-button>
                </template>
                <el-button
                  v-if="card.imageElement"
                  size="mini"
                  type="text"
                  icon="el-icon-crop"
                  @click.stop="cropImage(card.imageElement)"
                >裁剪</el-button>
                <el-button
                  v-if="card.diffElement"
                  size="mini"
                  type="text"
                  @click.stop="toggleDiff(card.diffElement)"
                >{{ card.diffExpanded ? '收起变更' : '查看变更' }}</el-button>
              </div>
            </div>

            <div v-if="card.diffElement" class="file-diff-summary">
              <span class="diff-summary-text">已修改</span>
              <span class="diff-stat diff-add">+{{ diffAdditions(card.diffElement) }}</span>
              <span class="diff-stat diff-del">-{{ diffDeletions(card.diffElement) }}</span>
            </div>

            <div v-if="card.imageElement" class="image-frame">
              <img
                class="artifact-image"
                :src="imageSrc(card.imageElement)"
                :alt="elementData(card.imageElement).alt || elementData(card.imageElement).name || ''"
                @click="openArtifactCard(card)"
              />
            </div>

            <div v-if="card.tableElement" class="table-scroll compact-table-scroll">
              <el-table
                v-if="tableHeaders(card.tableElement).length"
                :data="card.tableElement._editing ? card.tableElement._editRows : tablePreviewRows(card.tableElement)"
                size="small"
                border
                stripe
                style="width: 100%"
              >
                <el-table-column
                  v-for="(h, hi) in tableHeaders(card.tableElement)"
                  :key="hi"
                  :prop="'col' + hi"
                  :label="h"
                  min-width="120"
                >
                  <template slot-scope="scope">
                    <el-input
                      v-if="card.tableElement._editing"
                      v-model="scope.row['col' + hi]"
                      size="mini"
                      placeholder="输入内容"
                    />
                    <span v-else>{{ scope.row['col' + hi] }}</span>
                  </template>
                </el-table-column>
                <el-table-column v-if="card.tableElement._editing" label="操作" width="80" fixed="right">
                  <template slot-scope="scope">
                    <el-button type="text" size="mini" icon="el-icon-delete" style="color: #f56c6c"
                      @click="deleteTableRow(card.tableElement, scope.$index)">删除</el-button>
                  </template>
                </el-table-column>
              </el-table>
              <div v-if="!card.tableElement._editing && tableOverflowCount(card.tableElement) > 0" class="table-preview-hint">
                还有 {{ tableOverflowCount(card.tableElement) }} 行未展开
              </div>
              <div v-else-if="!tableHeaders(card.tableElement).length" class="el-text" v-html="renderText(elementContent(card.tableElement))"></div>
            </div>

            <DiffViewCard
              v-if="card.diffElement && card.diffExpanded"
              :element="card.diffElement"
              :session-id="sessionId"
              @applied="onDiffApplied(card.diffElement, $event)"
            />
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

    <CodeEditor
      v-if="editorVisible && editorMode === 'code'"
      :visible.sync="editorVisible"
      :content="editorData.content"
      :language="editorData.language"
      :file-name="editorData.fileName"
      :file-path="editorData.filePath"
      :session-id="sessionId"
      @saved="onEditorSaved"
    />

    <HtmlPageEditor
      v-if="editorVisible && editorMode === 'html-page'"
      :visible.sync="editorVisible"
      :content="editorData.content"
      :file-name="editorData.fileName"
      :file-path="editorData.filePath"
      :session-id="sessionId"
      @saved="onEditorSaved"
    />

    <ImageCropper
      v-if="cropVisible"
      :visible.sync="cropVisible"
      :image-url="cropImageUrl"
      @save="onImageCropSaved"
    />

    <ArtifactWorkbench
      v-if="workbenchVisible && workbenchArtifact"
      :visible.sync="workbenchVisible"
      :artifact="workbenchArtifact"
      :session-id="sessionId"
      @download="downloadFile"
      @edit="openWorkbenchEditor"
      @saved="onEditorSaved"
      @diff-applied="onWorkbenchDiffApplied"
    />
  </div>
</template>

<script>
import { formatTime } from '../../utils/format'
import { writeFile, debugLog } from '@/api/sandbox'
import ArtifactWorkbench from '@/components/ArtifactWorkbench/index.vue'
import CodeEditor from '@/components/CodeEditor/index.vue'
import HtmlPageEditor from '@/components/HtmlPageEditor/index.vue'
import DiffViewCard from '@/components/DiffViewCard/index.vue'
import ImageCropper from '@/components/ImageCropper/index.vue'

const CODE_FILE_RE = /\.(css|scss|less|js|jsx|ts|tsx|py|md|sql|json|xml|yaml|yml|toml|vue|java|c|h|cpp|cc|cxx|hpp|cs|go|rs|php|rb|sh|bat|ps1|kt|swift|dart)($|\?)/i

export default {
  name: 'MessageBubble',
  components: { ArtifactWorkbench, CodeEditor, HtmlPageEditor, DiffViewCard, ImageCropper },
  props: {
    message: Object,
    isOwn: Boolean,
    sessionId: { type: String, default: '' },
  },
  mounted() {
  },
  watch: {
    'message.elements': {
      immediate: true,
      deep: true,
      handler(val) {
        const list = Array.isArray(val) ? val : []
        const types = list.map(item => item && item.type).filter(Boolean)
        const diffCount = list.filter(item => item && item.type === 'diff').length
        console.log('[DEBUG P4] MessageBubble elements update:', {
          messageId: this.message && this.message.id,
          total: list.length,
          diffCount,
          types,
          artifactTypes: this.artifactElements.map(item => item && item.type),
        })
      },
    },
  },
  data() {
    return {
      imagePreviewVisible: false,
      previewImageUrl: '',
      editorMode: null,
      editorVisible: false,
      editorData: {
        content: '', language: 'text', fileName: '', filePath: '',
      },
      editingElement: null,
      cropVisible: false,
      cropImageUrl: '',
      cropElement: null,
      workbenchVisible: false,
      workbenchArtifact: null,
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
      return list.length ? list[list.length - 1] : null
    },
    artifactElements() {
      const artifacts = this.renderedElements.filter(el => ['code', 'diff', 'table', 'image', 'file', 'webpage'].includes(el?.type))
      const seen = new Set()
      return artifacts.filter(el => {
        const key = this.artifactKey(el)
        if (seen.has(key)) return false
        seen.add(key)
        return true
      })
    },
    artifactCards() {
      const cards = []
      const byKey = new Map()
      const ensureCard = (key, path = '') => {
        if (!byKey.has(key)) {
          const card = {
            key,
            path,
            fileElement: null,
            codeElement: null,
            htmlElement: null,
            imageElement: null,
            tableElement: null,
            diffElement: null,
          }
          byKey.set(key, card)
          cards.push(card)
        }
        const card = byKey.get(key)
        if (path && !card.path) card.path = path
        return card
      }

      this.artifactElements.forEach(el => {
        const path = this.resolveArtifactPath(el)
        const key = path || `artifact|${this.artifactKey(el)}`
        const card = ensureCard(key, path)
        if (el.type === 'diff') {
          card.diffElement = card.diffElement || el
          return
        }
        if (el.type === 'file') {
          card.fileElement = card.fileElement || el
        }
        if (el.type === 'table') {
          card.tableElement = el
        }
        if (el.type === 'image' || this.isImageElement(el)) {
          card.imageElement = card.imageElement || el
        }
        if (el.type === 'webpage' || this.isHtmlElement(el)) {
          card.htmlElement = card.htmlElement || el
        }
        if (this.isCodeArtifact(el)) {
          card.codeElement = card.codeElement || el
        }
      })

      return cards.map(card => {
        const primaryElement = this.primaryArtifactElement(card)
        const data = this.elementData(primaryElement || card.diffElement)
        return {
          ...card,
          primaryElement,
          displayName: this.artifactCardName(card),
          metaLabel: this.artifactCardMeta(card),
          sizeLabel: data.size ? this.formatFileSize(data.size) : '',
          editElement: this.artifactCardEditElement(card),
          diffExpanded: !!(card.diffElement && card.diffElement._expanded),
          kind: this.artifactCardKind(card),
          imageUrl: card.imageElement ? this.imageSrc(card.imageElement) : '',
          codeContent: card.codeElement ? (card.codeElement.content || this.elementData(card.codeElement).content || '') : '',
          tableHeaders: card.tableElement ? this.tableHeaders(card.tableElement) : [],
          tableRows: card.tableElement ? this.normalizeTable(card.tableElement) : [],
        }
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
      const allSteps = [...progressSteps, ...eventSteps]
        .filter(step => !this.isInternalWorkspacePath(step.path))
      const seen = new Set()
      return allSteps.filter(step => {
        const key = `${step.title}|${this.normalizeWorkspacePath(step.path || '')}`
        if (seen.has(key)) return false
        seen.add(key)
        return true
      })
    },
  },
  watch: {
    'message.elements': {
      handler(newElements, oldElements) {
      },
      deep: true,
      immediate: false,
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
      const canonicalPath = this.normalizeWorkspacePath(data.path || data.file || '')
      if (canonicalPath) {
        return [
          el?.type || '',
          data.subtype || '',
          canonicalPath,
        ].join('|')
      }
      return [
        el?.type || '',
        data.url || '',
        data.path || '',
        data.file || '',
        data.name || '',
        data.title || '',
        this.elementContent(el).slice(0, 160),
      ].join('|')
    },
    resolveArtifactPath(el) {
      const data = this.elementData(el)
      return this.normalizeWorkspacePath(
        data.path
          || data.file
          || this.pathFromUrl(data.url || data.src)
          || this.workspacePathFromContent(this.elementContent(el))
          || ''
      )
    },
    isCodeArtifact(el) {
      if (!el) return false
      if (el.type === 'code') return true
      const data = this.elementData(el)
      const subtype = data.subtype || ''
      const filename = `${data.filename || data.title || data.name || ''} ${data.path || ''} ${data.url || ''}`.toLowerCase()
      return subtype === 'code_preview'
        || CODE_FILE_RE.test(filename)
    },
    primaryArtifactElement(card) {
      return card.fileElement
        || card.imageElement
        || card.tableElement
        || card.htmlElement
        || card.codeElement
        || card.diffElement
        || null
    },
    artifactCardKind(card) {
      if (card.imageElement) return 'image'
      if (card.tableElement) return 'table'
      if (card.htmlElement) return 'html'
      if (card.codeElement) return 'code'
      if (card.diffElement) return 'diff'
      return 'file'
    },
    artifactCardName(card) {
      const primary = this.primaryArtifactElement(card)
      const data = this.elementData(primary || card.diffElement)
      return data.name
        || data.filename
        || data.title
        || (card.path ? card.path.split('/').pop() : '')
        || this.elementContent(primary || card.diffElement)
        || '产物文件'
    },
    artifactCardMeta(card) {
      if (card.imageElement) return 'image'
      if (card.tableElement) {
        return `${this.normalizeTable(card.tableElement).length} 行 ${this.tableHeaders(card.tableElement).length} 列`
      }
      if (card.htmlElement) return 'webpage'
      if (card.codeElement) {
        const data = this.elementData(card.codeElement)
        return data.language || 'code'
      }
      if (card.diffElement) return 'file'
      return 'file'
    },
    artifactCardEditElement(card) {
      if (card.tableElement || card.imageElement) return null
      return card.htmlElement || card.codeElement || null
    },
    openArtifactCard(card) {
      console.log('[DEBUG AWB] openArtifactCard source:', {
        key: card.key,
        path: card.path,
        displayName: card.displayName,
        hasEditElement: !!card.editElement,
        hasImageElement: !!card.imageElement,
        hasHtmlElement: !!card.htmlElement,
        hasCodeElement: !!card.codeElement,
        hasTableElement: !!card.tableElement,
        kind: card.kind,
      })
      this.workbenchArtifact = {
        ...card,
        downloadPath: card.path || '',
        canDownload: !!card.path,
        canEdit: !!card.editElement,
        canCrop: !!card.imageElement,
        imageUrl: card.imageElement ? this.imageSrc(card.imageElement) : '',
        codeContent: card.codeElement ? (card.codeElement.content || this.elementData(card.codeElement).content || '') : '',
        tableHeaders: card.tableElement ? this.tableHeaders(card.tableElement) : [],
        tableRows: card.tableElement ? this.normalizeTable(card.tableElement) : [],
      }
      console.log('[DEBUG AWB] workbenchArtifact payload:', this.workbenchArtifact)
      this.workbenchVisible = true
    },
    openWorkbenchEditor(card) {
      this.workbenchVisible = false
      if (card && card.editElement) this.editCode(card.editElement)
    },
    onWorkbenchDiffApplied(payload) {
      if (this.workbenchArtifact && this.workbenchArtifact.diffElement) {
        this.onDiffApplied(this.workbenchArtifact.diffElement, payload)
      }
    },
    downloadFile(path) {
      if (!this.sessionId || !path) return
      const normalized = this.normalizeWorkspacePath(path)
      const href = `/api/sandbox/sessions/${encodeURIComponent(this.sessionId)}/files/download?path=${encodeURIComponent(normalized)}`
      const link = document.createElement('a')
      link.href = href
      link.target = '_blank'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    },
    diffAdditions(el) {
      return this.elementData(el).diff_stat?.additions || 0
    },
    diffDeletions(el) {
      return this.elementData(el).diff_stat?.deletions || 0
    },
    toggleDiff(el) {
      this.$set(el, '_expanded', !el._expanded)
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
    tablePreviewRows(el) {
      if (!el || el._editing) return this.normalizeTable(el)
      return this.normalizeTable(el).slice(0, 3)
    },
    tableOverflowCount(el) {
      const rows = this.normalizeTable(el)
      return Math.max(0, rows.length - 3)
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
      if (data.local_preview_url) return data.local_preview_url
      const candidate = data.url || data.src || data.path || data.file || data.name || this.elementContent(el)
      const resolved = this.resolveFileUrl(candidate)
      if (!resolved) return ''
      if (!data.url_ts) return resolved
      return `${resolved}${resolved.includes('?') ? '&' : '?'}ts=${data.url_ts}`
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
    isHtmlElement(el) {
      const subtype = (el.data && el.data.subtype) || ''
      if (subtype === 'webpage') return true
      const name = ((el.data && el.data.name) || '').toLowerCase()
      return name.endsWith('.html') || name.endsWith('.htm')
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
    cropImage(el) {
      const imageUrl = this.imageSrc(el)
      if (!imageUrl) {
        this.$message.warning('图片地址不存在')
        return
      }
      this.cropElement = el
      this.cropImageUrl = imageUrl
      this.cropVisible = true
      console.log('[DEBUG P5] cropImage open:', {
        path: this.imagePath(el),
        url: imageUrl,
      })
    },
    async onImageCropSaved({ base64, width, height }) {
      const target = this.cropElement
      if (!target) return
      const path = this.imagePath(target)
      if (!path) {
        this.$message.warning('缺少图片文件路径')
        return
      }
      if (!this.sessionId) {
        this.$message.error('无法获取会话 ID')
        return
      }
      const data = this.elementData(target)
      const rollbackData = { ...data }
      this.$set(target, 'data', {
        ...data,
        local_preview_url: base64,
        width,
        height,
      })
      try {
        console.log('[DEBUG P5] onImageCropSaved:', { path, width, height })
        await writeFile(this.sessionId, path, base64)
        this.$set(target, 'data', {
          ...this.elementData(target),
          url_ts: Date.now(),
        })
        this.cropElement = null
        this.cropImageUrl = ''
        this.$message.success('图片已保存')
      } catch (error) {
        this.$set(target, 'data', rollbackData)
        this.$message.error(`保存失败: ${error.message || '未知错误'}`)
      }
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
    async editCode(el) {
      const data = el.data || {}
      const lang = (data.language || '').toLowerCase()
      const filePath = data.path || el.path || ''
      const fallbackName = filePath ? filePath.split('/').pop() : ''
      const filename = (data.filename || data.title || data.name || fallbackName || '').toLowerCase()
      const subtype = data.subtype || ''
      debugLog("P3X", `editCode entry: type=${el.type}, lang="${lang}", filename="${filename}", subtype="${subtype}"`)
      debugLog("P3X", `el.data keys: ${Object.keys(data).join(',') || '(empty)'}`)
      debugLog("P3X", `el.data raw: ${JSON.stringify(data).substring(0, 200)}`)
      const pathForMatch = `${filename} ${filePath} ${data.url || ''}`.toLowerCase()
      const isHtml = subtype === 'webpage'
        || lang === 'html'
        || lang === 'htmlmixed'
        || /\.html?($|\?)/i.test(pathForMatch)
      const isCodeFile = el.type === 'code'
        || (el.type === 'file' && subtype === 'code_preview')
        || (el.type === 'file' && CODE_FILE_RE.test(pathForMatch))
      debugLog("P3X", `isHtml=${isHtml}, isCodeFile=${isCodeFile}, filePath=${filePath || '(空)'}`)
      console.log('[DEBUG P3X] editCode 触发, type:', el.type, 'subtype:', subtype, 'isHtml:', isHtml, 'isCodeFile:', isCodeFile, 'filePath:', filePath || '(空!)')

      if (!isHtml && !isCodeFile) {
        debugLog("P3X", "skip: no match")
        console.log('[DEBUG P3X] 元素类型不匹配编辑器, 跳过')
        return
      }

      const inlineContent = el.type === 'code' ? (el.content || data.content || '') : (data.content || '')
      let content = inlineContent
      if (el.type === 'file') {
        const fetchUrl = data.url || this.resolveFileUrl(filePath)
        if (fetchUrl) {
          try {
            debugLog("P3X", `fetching file content from ${fetchUrl}`)
            const response = await fetch(fetchUrl)
            if (!response.ok) throw new Error(`HTTP ${response.status}`)
            content = await response.text()
            this.$set(el, 'content', content)
            this.$set(el, 'data', { ...data, content })
            debugLog("P3X", `fetched content length=${content.length}`)
          } catch (e) {
            debugLog("P3X", `fetch content failed: ${e.message || e}`)
            this.$message.warning('文件内容读取失败，编辑器将以空白内容打开')
          }
        }
      }

      this.editorData = {
        content,
        language: lang || (isHtml ? 'html' : 'text'),
        fileName: data.filename || data.title || data.name || fallbackName || 'code',
        filePath: filePath,
      }

      this.editorMode = isHtml ? 'html-page' : 'code'
      debugLog("P3X", `routing to ${this.editorMode}`)
      console.log('[DEBUG P3X] 路由到', this.editorMode === 'html-page' ? 'HtmlPageEditor' : 'CodeEditor')
      this.editingElement = el
      this.editorVisible = true
      debugLog("P3X", "editorVisible set to true")
    },

    onEditorSaved({ path, content }) {
      console.log('[DEBUG P3X] onEditorSaved, path:', path)
      if (this.editingElement) {
        this.$set(this.editingElement, 'content', content)
        const d = this.editingElement.data || {}
        this.$set(this.editingElement, 'data', { ...d, content })
        this.editingElement = null
      }
      if (this.workbenchArtifact && this.workbenchArtifact.path === path) {
        this.workbenchArtifact = {
          ...this.workbenchArtifact,
          codeContent: content,
          imageUrl: typeof content === 'string' && content.startsWith('data:image/') ? content : this.workbenchArtifact.imageUrl,
          _imageVersion: Date.now(),
          _htmlVersion: /\.(html?|svg)$/i.test(String(path || '')) ? Date.now() : this.workbenchArtifact._htmlVersion,
        }
      }
      if (path) {
        this.artifactElements.forEach(el => {
          if (!this.isImageElement(el)) return
          if (this.imagePath(el) !== path) return
          const data = this.elementData(el)
          this.$set(el, 'data', {
            ...data,
            local_preview_url: typeof content === 'string' && content.startsWith('data:image/') ? content : data.local_preview_url,
            url_ts: Date.now(),
          })
        })
      }
      this.$message.success('文件已保存')
    },
    onDiffApplied(el, { path, content }) {
      const data = this.elementData(el)
      this.$set(el, 'data', {
        ...data,
        after: content,
        path,
        applied: true,
      })
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
    fileIcon(el) {
      const value = String(this.elementData(el).path || this.elementData(el).name || this.elementContent(el) || '').toLowerCase()
      if (/\.(html?|vue)$/.test(value)) return 'el-icon-monitor'
      if (/\.(md|txt|pdf|docx?)$/.test(value)) return 'el-icon-document'
      if (/\.(css|scss|less|js|ts|tsx|jsx|json|py|java|c|h|cpp|cc|cxx|hpp|cs|go|rs|php|rb|sh|bat|ps1|kt|swift|dart|sql|xml|yaml|yml|toml)$/.test(value)) return 'el-icon-tickets'
      return 'el-icon-folder-opened'
    },

    // ===== 表格编辑方法 =====


    startEditTable(el) {
      const rows = this.normalizeTable(el)
      this.$set(el, '_editing', true)
      this.$set(el, '_editRows', rows.map(row => ({ ...row })))
      this.$set(el, '_originalRows', rows.map(row => ({ ...row })))
    },

    cancelEditTable(el) {
      this.$set(el, '_editing', false)
      this.$set(el, '_editRows', [])
      this.$set(el, '_originalRows', [])
    },

    addTableRow(el) {
      const headers = this.tableHeaders(el)
      const newRow = {}
      headers.forEach((h, i) => { newRow['col' + i] = '' })
      el._editRows.push(newRow)
    },

    deleteTableRow(el, index) {
      if (el._editRows.length <= 1) {
        this.$message.warning('至少保留一行数据')
        return
      }
      el._editRows.splice(index, 1)
    },

    async saveTable(el) {
      const headers = this.tableHeaders(el)
      const rows = el._editRows.map(r => {
        const row = []
        headers.forEach((h, i) => { row.push(r['col' + i] || '') })
        return row
      })

      const csvContent = [headers, ...rows]
        .map(row => row.map(cell => {
          const s = String(cell)
          if (s.includes(',') || s.includes('"') || s.includes('\n')) {
            return '"' + s.replace(/"/g, '""') + '"'
          }
          return s
        }).join(','))
        .join('\n')

      const path = (el.data && el.data.path) || el.path || ''
      if (!path) {
        this.$message.error('表格没有关联文件路径，无法保存')
        return
      }

      const sessionId = this.sessionId
      if (!sessionId) { this.$message.error('无法获取会话 ID'); return }

      try {
        await writeFile(sessionId, path, csvContent)
        this.$set(el, '_editing', false)
        el.data = el.data || {}
        el.data.headers = headers
        el.data.rows = rows
        if (!el.data.path) el.data.path = path
        el._editRows = []
        el._originalRows = []
        this.$message.success('表格已保存')
      } catch (e) {
        this.$message.error('保存失败: ' + (e.message || '未知错误'))
      }
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
    isInternalWorkspacePath(path) {
      const normalized = this.normalizeWorkspacePath(path || '')
      if (!normalized) return false
      return normalized.includes('/.weagent_history/')
        || normalized.endsWith('/.weagent_claude_session')
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

.artifact-title-text {
  min-width: 0;
  color: #1e293b;
  font-size: 12px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.artifact-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
}

.artifact-size {
  background: #f8fafc;
}

.file-diff-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 11px;
  border-bottom: 1px solid #edf2f7;
  background: #ffffff;
  font-size: 12px;
}

.diff-summary-text {
  color: #475569;
}

.diff-stat {
  font-weight: 600;
}

.diff-add {
  color: #15803d;
}

.diff-del {
  color: #dc2626;
}

.table-scroll {
  overflow-x: auto;
  padding: 10px;
}

.compact-table-scroll {
  background: #fff;
}

.table-card :deep(.el-table) {
  border-radius: 6px;
  overflow: hidden;
}

.table-card :deep(.el-table th.el-table__cell) {
  background: #f1f5f9;
  color: #334155;
  font-weight: 600;
}

.table-preview-hint {
  padding-top: 8px;
  font-size: 12px;
  color: #64748b;
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
  display: block;
  padding: 0;
  cursor: default;
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

.table-block .table-actions {
  margin-left: auto;
  display: flex;
  gap: 4px;
}
.table-block .table-actions .el-button {
  padding: 4px 8px;
}
.table-scroll .el-input--mini .el-input__inner {
  border: 1px solid #dcdfe6;
  border-radius: 2px;
}
</style>
