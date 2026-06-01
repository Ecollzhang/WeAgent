<template>
  <el-dialog
    :visible.sync="dialogVisible"
    fullscreen
    :show-close="false"
    custom-class="artifact-workbench-dialog"
    @closed="onClosed"
  >
    <div class="awb-layout">
      <div class="awb-toolbar">
        <div class="awb-toolbar-left">
          <el-tag size="small" type="info">{{ currentTypeLabel }}</el-tag>
          <span class="awb-filename">{{ currentName }}</span>
          <span v-if="currentMeta" class="awb-meta">{{ currentMeta }}</span>
        </div>
        <div class="awb-toolbar-right">
          <el-button v-if="canGoUp" size="small" icon="el-icon-back" @click="goUp">上级目录</el-button>
          <el-button v-if="canDownload" size="small" icon="el-icon-download" @click="$emit('download', currentPath)">下载</el-button>
          <el-button v-if="canEdit" size="small" type="primary" icon="el-icon-edit" @click="enterEditMode">{{ isEditing ? '继续编辑' : '编辑' }}</el-button>
          <el-button v-if="isEditing" size="small" icon="el-icon-close" @click="exitEditMode">退出编辑</el-button>
          <el-button v-if="canCrop" size="small" type="primary" icon="el-icon-crop" @click="enterCropMode">{{ isCropping ? '继续裁剪' : '裁剪' }}</el-button>
          <el-button size="small" icon="el-icon-close" @click="dialogVisible = false">关闭</el-button>
        </div>
      </div>

      <div class="awb-body">
        <aside class="awb-tree">
          <div class="awb-tree-header">
            <span class="awb-tree-title">产物目录</span>
            <span class="awb-tree-root">{{ currentRoot }}</span>
          </div>
          <div v-if="treeLoading" class="awb-tree-loading"><i class="el-icon-loading" /> 加载目录中...</div>
          <el-tree
            v-else
            :data="treeData"
            node-key="path"
            :props="treeProps"
            :default-expanded-keys="expandedKeys"
            :expand-on-click-node="false"
            :highlight-current="true"
            class="awb-tree-panel"
            @node-click="handleNodeClick"
          >
            <span slot-scope="{ data }" class="awb-tree-node">
              <i :class="data.type === 'directory' ? 'el-icon-folder' : fileIcon(data.path)"></i>
              <span class="awb-tree-label">{{ data.name }}</span>
            </span>
          </el-tree>
        </aside>

        <div class="awb-main">
          <div v-if="isEditing && currentKind === 'code'" class="awb-editor-wrap">
            <CodeEditor
              embedded
              :visible="true"
              :content="textContent"
              :language="currentLanguage"
              :file-name="currentName"
              :file-path="currentPath"
              :session-id="sessionId"
              @saved="onEmbeddedSaved"
              @close-request="exitEditMode"
            />
          </div>

          <div v-else-if="isEditing && currentKind === 'html'" class="awb-editor-wrap">
            <HtmlPageEditor
              embedded
              :visible="true"
              :content="textContent"
              :file-name="currentName"
              :file-path="currentPath"
              :session-id="sessionId"
              @saved="onEmbeddedHtmlSaved"
              @close-request="exitEditMode"
            />
          </div>

          <div v-else-if="currentKind === 'html'" class="awb-frame-wrap">
            <iframe v-if="htmlPreviewUrl" :src="htmlPreviewUrl" class="awb-iframe" sandbox="allow-scripts allow-same-origin"></iframe>
            <div v-else class="awb-empty">无法预览该网页文件</div>
          </div>

          <div v-else-if="isCropping && currentKind === 'image'" class="awb-editor-wrap">
            <ImageCropper
              embedded
              :visible="true"
              :image-url="imageUrl"
              @save="onCropSaved"
              @cancel="exitCropMode"
            />
          </div>

          <div v-else-if="currentKind === 'image'" class="awb-image-wrap">
            <iframe
              v-if="isSvg && imageUrl"
              :src="imageUrl"
              class="awb-image awb-svg-frame"
              sandbox="allow-same-origin"
            ></iframe>
            <img v-else-if="imageUrl" :src="imageUrl" class="awb-image" :alt="currentName">
            <div v-else class="awb-empty">无法加载图片</div>
          </div>

          <div v-else-if="currentKind === 'table' && isEditing" class="awb-table-wrap">
            <div class="awb-table-toolbar">
              <el-button size="small" icon="el-icon-plus" @click="addTableRow">加行</el-button>
              <el-button size="small" type="primary" icon="el-icon-check" :loading="savingTable" @click="saveTable">保存</el-button>
              <el-button size="small" icon="el-icon-close" @click="exitEditMode">取消</el-button>
            </div>
            <el-table
              v-if="tableHeaders.length"
              :data="tableEditRows"
              size="small"
              border
              stripe
              style="width: 100%"
            >
              <el-table-column
                v-for="(header, index) in tableHeaders"
                :key="'edit-' + index"
                :prop="'col' + index"
                :label="header"
                min-width="140"
              >
                <template slot-scope="scope">
                  <el-input v-model="scope.row['col' + index]" size="mini" />
                </template>
              </el-table-column>
              <el-table-column label="操作" width="80" fixed="right">
                <template slot-scope="scope">
                  <el-button type="text" size="mini" style="color:#f56c6c" @click="deleteTableRow(scope.$index)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <div v-else-if="currentKind === 'table'" class="awb-table-wrap">
            <el-table
              v-if="tableHeaders.length"
              :data="tableRows"
              size="small"
              border
              stripe
              style="width: 100%"
            >
              <el-table-column
                v-for="(header, index) in tableHeaders"
                :key="index"
                :prop="'col' + index"
                :label="header"
                min-width="140"
              />
            </el-table>
            <div v-else class="awb-empty">暂无表格内容</div>
          </div>

          <div v-else-if="currentKind === 'code'" class="awb-code-wrap">
            <div v-if="loading" class="awb-loading"><i class="el-icon-loading" /> 加载中...</div>
            <pre v-else class="awb-code"><code>{{ textContent }}</code></pre>
          </div>

          <div v-else-if="currentKind === 'text'" class="awb-code-wrap">
            <div v-if="loading" class="awb-loading"><i class="el-icon-loading" /> 加载中...</div>
            <pre v-else class="awb-code"><code>{{ textContent }}</code></pre>
          </div>

          <div v-else-if="currentKind === 'binary'" class="awb-generic">
            <div class="awb-empty">当前文件暂不支持直接预览，可下载到本地查看。</div>
          </div>

          <div v-else class="awb-generic">
            <div class="awb-empty">请选择左侧文件进行查看。</div>
          </div>
        </div>

        <aside class="awb-side" v-if="currentDiffElement">
          <div class="awb-side-title">变更详情</div>
          <DiffViewCard
            :element="currentDiffElement"
            :session-id="sessionId"
            @applied="payload => $emit('diff-applied', payload)"
          />
        </aside>
      </div>
    </div>
  </el-dialog>
</template>

<script>
import { getFileTree, getSessionRawFileUrl, getWorkspaceFileUrl, writeFile } from '@/api/sandbox'
import CodeEditor from '@/components/CodeEditor/index.vue'
import DiffViewCard from '@/components/DiffViewCard/index.vue'
import HtmlPageEditor from '@/components/HtmlPageEditor/index.vue'
import ImageCropper from '@/components/ImageCropper/index.vue'

const CODE_FILE_RE = /\.(css|scss|less|js|jsx|ts|tsx|py|md|sql|json|xml|yaml|yml|toml|vue|java|c|h|cpp|cc|cxx|hpp|cs|go|rs|php|rb|sh|bat|ps1|kt|swift|dart)$/i
const TEXT_FILE_RE = /\.(txt|log)$/i
const IMAGE_FILE_RE = /\.(png|jpe?g|gif|webp|svg|bmp)$/i
const RASTER_IMAGE_FILE_RE = /\.(png|jpe?g|gif|webp|bmp)$/i

export default {
  name: 'ArtifactWorkbench',
  components: { CodeEditor, DiffViewCard, HtmlPageEditor, ImageCropper },
  props: {
    visible: { type: Boolean, default: false },
    artifact: { type: Object, default: null },
    sessionId: { type: String, default: '' },
  },
  data() {
    return {
      dialogVisible: this.visible,
      treeLoading: false,
      loading: false,
      currentRoot: '/workspace',
      treeData: [],
      expandedKeys: [],
      currentPath: '',
      currentKind: '',
      currentName: '',
      currentMeta: '',
      currentLanguage: 'text',
      textContent: '',
      tableHeaders: [],
      tableRows: [],
      tableEditRows: [],
      isEditing: false,
      isCropping: false,
      savingTable: false,
      imageVersion: 0,
      htmlVersion: 0,
      treeProps: {
        label: 'name',
        children: 'children',
      },
    }
  },
  computed: {
    currentTypeLabel() {
      if (this.currentKind === 'html') return '网页'
      if (this.currentKind === 'image') return '图片'
      if (this.currentKind === 'table') return '表格'
      if (this.currentKind === 'code') return '代码'
      if (this.currentKind === 'text') return '文本'
      if (this.currentKind === 'binary') return '文件'
      return '产物'
    },
    canDownload() {
      return !!this.currentPath
    },
    canEdit() {
      return this.currentKind === 'code' || this.currentKind === 'html' || this.currentKind === 'table'
    },
    canCrop() {
      return this.currentKind === 'image' && !this.isSvg && RASTER_IMAGE_FILE_RE.test((this.currentPath || '').toLowerCase())
    },
    canGoUp() {
      return this.currentRoot && this.currentRoot !== '/workspace'
    },
    currentDiffElement() {
      if (!this.artifact?.diffElement) return null
      return this.currentPath === (this.artifact?.path || '') ? this.artifact.diffElement : null
    },
    imageUrl() {
      if (this.artifact?.path === this.currentPath && this.artifact?.imageUrl) {
        return this.artifact.imageUrl
      }
      if (!this.currentPath || !this.sessionId) return ''
      const baseUrl = getSessionRawFileUrl(this.sessionId, this.currentPath)
      return this.imageVersion ? `${baseUrl}${baseUrl.includes('?') ? '&' : '?'}ts=${this.imageVersion}` : baseUrl
    },
    isSvg() {
      return /\.svg$/i.test(this.currentPath || '')
    },
    htmlPreviewUrl() {
      if (!this.currentPath || !this.sessionId) return ''
      const baseUrl = getWorkspaceFileUrl(this.sessionId, this.currentPath)
      return this.htmlVersion ? `${baseUrl}${baseUrl.includes('?') ? '&' : '?'}ts=${this.htmlVersion}` : baseUrl
    },
  },
  watch: {
    visible(v) {
      this.dialogVisible = v
      if (v) this.initializeWorkbench()
    },
    dialogVisible(v) {
      if (!v) this.$emit('update:visible', false)
    },
    artifact: {
      deep: true,
      handler() {
        if (this.dialogVisible) this.initializeWorkbench()
      },
    },
  },
  mounted() {
    if (this.visible) this.initializeWorkbench()
  },
  methods: {
    async initializeWorkbench() {
      this.currentPath = this.artifact?.path || ''
      this.currentRoot = this.deriveInitialRoot(this.currentPath)
      this.isEditing = false
      this.isCropping = false
      this.imageVersion = this.artifact?._imageVersion || 0
      this.htmlVersion = this.artifact?._htmlVersion || 0
      await this.loadTree(this.currentRoot)
      if (this.currentPath) await this.selectFile(this.currentPath)
    },
    deriveInitialRoot(path) {
      const normalized = String(path || '').replace(/\\/g, '/')
      const match = normalized.match(/^\/workspace\/agents\/[^/]+/)
      if (match) return match[0]
      const parts = normalized.split('/')
      parts.pop()
      return parts.join('/') || '/workspace'
    },
    async loadTree(root) {
      if (!this.sessionId || !root) return
      this.treeLoading = true
      try {
        const res = await getFileTree(this.sessionId, root)
        const tree = res?.data?.tree || null
        this.treeData = tree ? [this.filterTree(tree)] : []
        this.currentRoot = root
        this.expandedKeys = this.buildExpandedKeys(this.currentPath, root)
      } finally {
        this.treeLoading = false
      }
    },
    filterTree(node) {
      if (!node) return null
      const name = node.name || ''
      const path = node.path || ''
      if (this.isInternalPath(path, name)) return null
      const children = Array.isArray(node.children)
        ? node.children.map(child => this.filterTree(child)).filter(Boolean)
        : []
      return {
        ...node,
        children,
      }
    },
    isInternalPath(path, name) {
      const normalized = String(path || '')
      return normalized.includes('/.weagent_history/')
        || normalized.endsWith('/.weagent_claude_session')
        || name === '.weagent_history'
        || name === '.weagent_claude_session'
    },
    buildExpandedKeys(path, root) {
      if (!path || !root || !path.startsWith(root)) return [root]
      const keys = [root]
      const parts = path.replace(root, '').split('/').filter(Boolean)
      let current = root
      parts.slice(0, -1).forEach(part => {
        current = `${current}/${part}`
        keys.push(current)
      })
      return keys
    },
    handleNodeClick(node) {
      if (!node) return
      if (node.type === 'directory') return
      this.selectFile(node.path)
    },
    async selectFile(path) {
      if (!path || !this.sessionId) return
      this.currentPath = path
      this.currentName = path.split('/').pop() || path
      this.currentMeta = ''
      this.isEditing = false
      this.isCropping = false
      this.imageVersion = 0
      this.htmlVersion = 0
      this.loading = false
      this.textContent = ''
      this.tableHeaders = []
      this.tableRows = []
      this.tableEditRows = []
      const ext = this.getExt(path)
      if (IMAGE_FILE_RE.test(`.${ext}`)) {
        this.currentKind = 'image'
        this.currentMeta = ext.toUpperCase()
        return
      }
      if (ext === 'csv') {
        this.currentKind = 'table'
        this.currentMeta = 'CSV'
        await this.loadTable(path)
        return
      }
      if (ext === 'html' || ext === 'htm') {
        this.currentKind = 'html'
        this.currentMeta = 'HTML'
        await this.loadText(path)
        return
      }
      if (CODE_FILE_RE.test(`.${ext}`)) {
        this.currentKind = 'code'
        this.currentLanguage = ext
        this.currentMeta = ext.toUpperCase()
        await this.loadText(path)
        return
      }
      if (TEXT_FILE_RE.test(`.${ext}`)) {
        this.currentKind = 'text'
        this.currentMeta = ext.toUpperCase()
        await this.loadText(path)
        return
      }
      this.currentKind = 'binary'
      this.currentMeta = ext ? ext.toUpperCase() : 'FILE'
    },
    async loadText(path) {
      this.loading = true
      try {
        const response = await fetch(getSessionRawFileUrl(this.sessionId, path))
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        this.textContent = await response.text()
      } catch (error) {
        this.textContent = `加载失败：${error.message || error}`
      } finally {
        this.loading = false
      }
    },
    async loadTable(path) {
      this.loading = true
      try {
        const response = await fetch(getSessionRawFileUrl(this.sessionId, path))
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const text = await response.text()
        const rows = text.split(/\r?\n/).filter(Boolean).map(line => line.split(','))
        const headers = rows[0] || []
        const body = rows.slice(1).map(row => {
          const item = {}
          headers.forEach((header, index) => {
            item[`col${index}`] = row[index] || ''
          })
          return item
        })
        this.tableHeaders = headers
        this.tableRows = body
        this.tableEditRows = body.map(row => ({ ...row }))
      } catch (error) {
        this.tableHeaders = []
        this.tableRows = []
        this.tableEditRows = []
      } finally {
        this.loading = false
      }
    },
    enterEditMode() {
      this.isCropping = false
      if (this.currentKind === 'table') {
        this.tableEditRows = this.tableRows.map(row => ({ ...row }))
      }
      this.isEditing = true
    },
    exitEditMode() {
      this.isEditing = false
      if (this.currentKind === 'table') {
        this.tableEditRows = this.tableRows.map(row => ({ ...row }))
      }
    },
    enterCropMode() {
      if (!this.canCrop) return
      this.isEditing = false
      this.isCropping = true
    },
    exitCropMode() {
      this.isCropping = false
    },
    async onEmbeddedSaved({ path, content }) {
      this.textContent = content
      this.isEditing = false
      this.$emit('saved', { path, content })
    },
    async onEmbeddedHtmlSaved({ path, content }) {
      this.textContent = content
      this.htmlVersion = Date.now()
      this.isEditing = false
      this.$emit('saved', { path, content })
    },
    async onCropSaved({ base64 }) {
      if (!this.sessionId || !this.currentPath) return
      try {
        await writeFile(this.sessionId, this.currentPath, base64)
        this.imageVersion = Date.now()
        this.isCropping = false
        this.$emit('saved', { path: this.currentPath, content: base64 })
        this.$message.success('图片已保存')
      } catch (error) {
        this.$message.error(`保存失败: ${error.message || ''}`)
      }
    },
    addTableRow() {
      const row = {}
      this.tableHeaders.forEach((header, index) => {
        row[`col${index}`] = ''
      })
      this.tableEditRows.push(row)
    },
    deleteTableRow(index) {
      this.tableEditRows.splice(index, 1)
    },
    async saveTable() {
      if (!this.sessionId || !this.currentPath) return
      this.savingTable = true
      try {
        const rows = this.tableEditRows.map(row =>
          this.tableHeaders.map((header, index) => {
            const value = String(row[`col${index}`] || '')
            if (value.includes(',') || value.includes('"') || value.includes('\n')) {
              return `"${value.replace(/"/g, '""')}"`
            }
            return value
          }).join(',')
        )
        const content = [this.tableHeaders.join(','), ...rows].join('\n')
        await writeFile(this.sessionId, this.currentPath, content)
        this.tableRows = this.tableEditRows.map(row => ({ ...row }))
        this.isEditing = false
        this.$emit('saved', { path: this.currentPath, content })
        this.$message.success('表格已保存')
      } catch (error) {
        this.$message.error(`保存失败: ${error.message || ''}`)
      } finally {
        this.savingTable = false
      }
    },
    goUp() {
      if (!this.canGoUp) return
      const parts = this.currentRoot.split('/').filter(Boolean)
      parts.pop()
      const nextRoot = `/${parts.join('/')}` || '/workspace'
      this.loadTree(nextRoot)
    },
    getExt(path) {
      const clean = String(path || '').split('?')[0]
      const ext = clean.includes('.') ? clean.split('.').pop().toLowerCase() : ''
      return ext
    },
    fileIcon(path) {
      const value = String(path || '').toLowerCase()
      if (/\.(html?|vue)$/.test(value)) return 'el-icon-monitor'
      if (IMAGE_FILE_RE.test(value)) return 'el-icon-picture-outline'
      if (/\.csv$/.test(value)) return 'el-icon-data-analysis'
      if (CODE_FILE_RE.test(value)) return 'el-icon-tickets'
      if (/\.(md|txt|pdf|docx?)$/.test(value)) return 'el-icon-document'
      return 'el-icon-document'
    },
    onClosed() {
      this.isEditing = false
      this.isCropping = false
    },
  },
}
</script>

<style scoped>
:deep(.artifact-workbench-dialog .el-dialog) { margin-top: 0 !important; }
:deep(.artifact-workbench-dialog .el-dialog__header) { display: none; }
:deep(.artifact-workbench-dialog .el-dialog__body) { padding: 0; }

.awb-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f6f8fc;
}

.awb-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 16px;
  background: rgba(255, 255, 255, 0.96);
  border-bottom: 1px solid #dbe3f0;
  flex-shrink: 0;
}

.awb-toolbar-left,
.awb-toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.awb-toolbar-left {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.awb-toolbar-right {
  flex-shrink: 0;
}

.awb-filename {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.awb-meta {
  font-size: 12px;
  color: #64748b;
  flex-shrink: 0;
}

.awb-body {
  flex: 1;
  min-height: 0;
  display: flex;
}

.awb-tree {
  width: 280px;
  min-width: 240px;
  border-right: 1px solid #dbe3f0;
  background: #ffffff;
  display: flex;
  flex-direction: column;
}

.awb-tree-header {
  padding: 14px 14px 10px;
  border-bottom: 1px solid #eef2f7;
}

.awb-tree-title {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #22324d;
}

.awb-tree-root {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
  word-break: break-all;
}

.awb-tree-loading {
  padding: 18px 14px;
  color: #64748b;
}

.awb-tree-panel {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 10px 8px 14px;
}

.awb-tree-node {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.awb-tree-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.awb-main {
  flex: 1;
  min-width: 0;
  overflow: auto;
  background:
    radial-gradient(circle at top, rgba(59, 130, 246, 0.08), transparent 26%),
    linear-gradient(180deg, #f8fbff 0%, #edf3fb 100%);
}

.awb-side {
  width: 420px;
  max-width: 36%;
  min-width: 320px;
  border-left: 1px solid #dbe3f0;
  background: #ffffff;
  padding: 16px;
  overflow: auto;
}

.awb-side-title {
  margin-bottom: 12px;
  font-size: 13px;
  font-weight: 600;
  color: #22324d;
}

.awb-editor-wrap,
.awb-frame-wrap,
.awb-image-wrap,
.awb-table-wrap,
.awb-code-wrap,
.awb-generic {
  height: 100%;
  min-height: 0;
  padding: 18px;
  box-sizing: border-box;
}

.awb-editor-wrap {
  padding: 0;
}

.awb-iframe {
  width: 100%;
  height: 100%;
  min-height: 680px;
  border: 1px solid #dbe3f0;
  border-radius: 14px;
  background: #fff;
}

.awb-image-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
}

.awb-image {
  max-width: 100%;
  max-height: calc(100vh - 120px);
  border-radius: 16px;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.12);
  background: #fff;
}

.awb-svg-frame {
  width: 100%;
  height: 100%;
  min-height: 680px;
  border: 1px solid #dbe3f0;
  border-radius: 14px;
  background: #fff;
}

.awb-code {
  margin: 0;
  min-height: calc(100vh - 140px);
  padding: 18px;
  border: 1px solid #dbe3f0;
  border-radius: 14px;
  background: #f8fbff;
  color: #0f172a;
  font-size: 13px;
  line-height: 1.65;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
}

.awb-loading,
.awb-empty {
  min-height: 220px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  font-size: 14px;
  text-align: center;
}

.awb-loading i {
  margin-right: 8px;
}

.awb-table-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
</style>
