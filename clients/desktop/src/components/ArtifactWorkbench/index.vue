<template>
  <el-dialog
    :visible.sync="dialogVisible"
    fullscreen
    :show-close="false"
    custom-class="artifact-workbench-dialog"
    @closed="handleClosed"
  >
    <div class="awb-layout">
      <div class="awb-toolbar">
        <div class="awb-toolbar-left">
          <el-tag size="small" type="info">{{ kindLabel }}</el-tag>
          <span class="awb-filename">{{ currentName || fallbackTitle }}</span>
          <span class="awb-meta">{{ currentRoot }}</span>
        </div>
        <div class="awb-toolbar-right">
          <el-button size="small" icon="el-icon-refresh" @click="refreshTree">刷新</el-button>
          <el-button v-if="canDownload" size="small" icon="el-icon-download" @click="downloadCurrent">下载</el-button>
          <el-button v-if="canExportZip" size="small" icon="el-icon-folder-opened" @click="exportZip">导出 ZIP</el-button>
          <el-button v-if="canExportZip" size="small" icon="el-icon-document-checked" @click="openSelectiveExport">选择导出</el-button>
          <el-button v-if="canCrop" size="small" type="primary" icon="el-icon-crop" @click="enterCropMode">
            {{ isCropping ? '继续裁剪' : '裁剪' }}
          </el-button>
          <el-button v-if="canEdit" size="small" type="primary" icon="el-icon-edit" @click="editMode = true">编辑</el-button>
          <el-button v-if="editMode" size="small" icon="el-icon-close" @click="editMode = false">退出编辑</el-button>
          <el-button size="small" icon="el-icon-close" @click="dialogVisible = false">关闭</el-button>
        </div>
      </div>

      <div class="awb-body">
        <aside class="awb-tree">
          <div class="awb-tree-header">
            <span class="awb-tree-title">文件</span>
            <span class="awb-tree-root">{{ currentRoot }}</span>
          </div>
          <div v-if="treeLoading" class="awb-tree-loading">
            <i class="el-icon-loading" /> 加载目录中...
          </div>
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
            <span slot-scope="scope" class="awb-tree-node">
              <i :class="scope.data.type === 'directory' ? 'el-icon-folder' : fileIcon(scope.data.path)"></i>
              <span class="awb-tree-label">{{ scope.data.name }}</span>
            </span>
          </el-tree>
        </aside>

        <section class="awb-main">
          <div v-if="editMode && previewType === 'html'" class="awb-editor-wrap">
            <HtmlPageEditor
              embedded
              :visible="true"
              :content="textContent"
              :file-name="currentName"
              :file-path="currentPath"
              :session-id="sessionId"
              :base-href="currentBaseHref"
              @saved="handleSaved"
              @close-request="editMode = false"
            />
          </div>

          <div v-else-if="editMode && (previewType === 'text' || previewType === 'code')" class="awb-editor-wrap">
            <CodeEditor
              embedded
              :visible="true"
              :content="textContent"
              :language="currentLanguage"
              :file-name="currentName"
              :file-path="currentPath"
              :session-id="sessionId"
              @saved="handleSaved"
              @close-request="editMode = false"
            />
          </div>

          <div v-else-if="editMode && previewType === 'table'" class="awb-table-wrap">
            <div class="awb-table-toolbar">
              <el-button size="small" icon="el-icon-plus" @click="addTableRow">加行</el-button>
              <el-button size="small" type="primary" icon="el-icon-check" :loading="savingTable" @click="saveTable">保存</el-button>
            </div>
            <el-table v-if="tableHeaders.length" :data="tableEditRows" border size="small" style="width: 100%">
              <el-table-column
                v-for="(header, index) in tableHeaders"
                :key="'edit-' + index"
                :label="header"
                :prop="'col_' + index"
                min-width="120"
              >
                <template slot-scope="scope">
                  <el-input v-model="scope.row['col_' + index]" size="mini" />
                </template>
              </el-table-column>
              <el-table-column label="操作" width="84" fixed="right">
                <template slot-scope="scope">
                  <el-button type="text" size="mini" @click="deleteTableRow(scope.$index)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div v-else class="awb-empty"><i class="el-icon-document"></i><span>空表格</span></div>
          </div>

          <div v-else-if="isCropping && previewType === 'image'" class="awb-editor-wrap">
            <ImageCropper embedded :image-url="previewUrl" :visible="true" @save="onCropSaved" @cancel="exitCropMode" />
          </div>

          <div v-else-if="!currentPath" class="awb-empty">
            <i class="el-icon-folder-opened"></i>
            <span>从左侧选择文件查看内容</span>
          </div>

          <div v-else-if="previewType === 'html'" class="awb-frame-wrap">
            <iframe v-if="previewUrl" :src="previewUrl" class="awb-frame" sandbox="allow-scripts allow-same-origin"></iframe>
            <div v-else class="awb-loading"><i class="el-icon-loading" /> 加载中...</div>
          </div>

          <div v-else-if="previewType === 'image'" class="awb-image-wrap">
            <img :src="previewUrl" class="awb-image" :alt="currentName" />
          </div>

          <div v-else-if="previewType === 'pdf'" class="awb-frame-wrap">
            <iframe v-if="previewUrl" :src="previewUrl" class="awb-frame"></iframe>
            <div v-else class="awb-loading"><i class="el-icon-loading" /> 加载中...</div>
          </div>

          <div v-else-if="previewType === 'table'" class="awb-table-wrap">
            <el-table v-if="tableHeaders.length" :data="tableRows" border size="small" style="width: 100%">
              <el-table-column
                v-for="(header, index) in tableHeaders"
                :key="'view-' + index"
                :label="header"
                :prop="'col_' + index"
                min-width="120"
              />
            </el-table>
            <div v-else class="awb-empty"><i class="el-icon-document"></i><span>空表格</span></div>
          </div>

          <div v-else-if="previewType === 'diff' && currentArtifact" class="awb-diff">
            <DiffViewCard class="awb-diff-card" :element="currentArtifact.element || currentArtifact" :session-id="sessionId" @applied="handleDiffApplied" />
          </div>

          <pre v-else class="awb-code"><code>{{ textContent }}</code></pre>

          <div v-if="previewLoading" class="awb-loading"><i class="el-icon-loading" /> 加载中...</div>
        </section>
      </div>
    </div>

    <div v-if="exportDialogVisible" class="awb-export-overlay" @click.self="exportDialogVisible = false">
      <div class="awb-export-modal">
        <div class="awb-export-modal-header">
          <span>选择导出文件</span>
          <el-button type="text" @click="exportDialogVisible = false">关闭</el-button>
        </div>
        <div class="awb-export-panel">
          <div class="awb-export-hint">勾选要导出的文件或文件夹，ZIP 会保留当前目录下的文件夹层级。</div>
          <el-tree
            ref="exportTree"
            :data="exportTreeData"
            node-key="path"
            show-checkbox
            :props="treeProps"
            :default-expanded-keys="expandedKeys"
            class="awb-export-tree"
          >
            <span slot-scope="scope" class="awb-tree-node">
              <i :class="scope.data.type === 'directory' ? 'el-icon-folder' : fileIcon(scope.data.path)"></i>
              <span class="awb-tree-label">{{ scope.data.name }}</span>
            </span>
          </el-tree>
        </div>
        <div class="awb-export-actions">
          <el-button @click="exportDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="exportingZip" @click="exportSelectedZip">导出所选</el-button>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script>
import CodeEditor from '@/components/CodeEditor/index.vue'
import DiffViewCard from '@/components/DiffViewCard/index.vue'
import HtmlPageEditor from '@/components/HtmlPageEditor/index.vue'
import ImageCropper from '@/components/ImageCropper/index.vue'
import { getFileTree, getSessionDownloadUrl, getSessionRawFileUrl, getSessionZipExportUrl, getWorkspaceFileUrl, readSessionRawFile, writeFile } from '@/services/sandbox'
import { getAccessToken } from '@/services/session'

var CODE_RE = /\.(css|scss|less|js|jsx|ts|tsx|py|md|sql|json|xml|yaml|yml|toml|vue|java|c|h|cpp|cc|cxx|hpp|cs|go|rs|php|rb|sh|bat|ps1|kt|swift|dart)$/i
var IMG_RE = /\.(png|jpe?g|gif|webp|svg|bmp)$/i

export default {
  name: 'DesktopArtifactWorkbench',
  components: { CodeEditor, DiffViewCard, HtmlPageEditor, ImageCropper },
  props: {
    visible: Boolean,
    sessionId: String,
    initialRoot: { type: String, default: '/workspace' },
    initialPath: String,
    initialAgentId: String,
    initialArtifact: Object,
  },
  data: function() {
    return {
      dialogVisible: this.visible,
      treeLoading: false,
      previewLoading: false,
      treeData: [],
      expandedKeys: [],
      currentRoot: this.initialRoot || '/workspace',
      currentPath: '',
      currentAgentId: '',
      currentArtifact: null,
      previewType: 'text',
      previewUrl: '',
      textContent: '',
      editMode: false,
      isCropping: false,
      tableHeaders: [],
      tableRows: [],
      tableEditRows: [],
      savingTable: false,
      objectUrls: [],
      exportDialogVisible: false,
      exportingZip: false,
      treeProps: { label: 'name', children: 'children' },
    }
  },
  computed: {
    fallbackTitle: function() { return '工作台' },
    currentName: function() { return (this.currentPath || '').split('/').filter(Boolean).pop() || '' },
    currentLanguage: function() { return this.getExt(this.currentPath) || 'text' },
    currentBaseHref: function() {
      if (!this.previewUrl) return ''
      var index = this.previewUrl.lastIndexOf('/')
      return index >= 0 ? this.previewUrl.slice(0, index + 1) : this.previewUrl
    },
    kindLabel: function() {
      if (this.previewType === 'diff') return 'Diff'
      if (!this.currentPath) return this.fallbackTitle
      if (this.previewType === 'html') return 'HTML'
      if (this.previewType === 'image') return 'Image'
      if (this.previewType === 'table') return 'CSV 表格'
      if (this.previewType === 'pdf') return 'PDF'
      return CODE_RE.test(this.currentPath) ? '代码' : '文本'
    },
    canDownload: function() { return !!this.sessionId && !!this.currentPath },
    canExportZip: function() { return !!this.sessionId && !!this.currentRoot },
    canEdit: function() { return !!this.sessionId && !!this.currentPath && ['text', 'code', 'html', 'table'].includes(this.previewType) },
    canCrop: function() { return this.previewType === 'image' && !!this.currentPath },
    zipExportFilename: function() {
      var name = String(this.currentRoot || '').split('/').filter(Boolean).pop() || 'export'
      return /\.zip$/i.test(name) ? name : name + '.zip'
    },
    exportTreeData: function() {
      return this.filterExportTree(this.treeData)
    },
  },
  watch: {
    visible: function(value) {
      this.dialogVisible = value
      if (value) this.initializeWorkbench()
    },
    dialogVisible: function(value) {
      this.$emit('update:visible', value)
    },
    initialPath: function(value) {
      if (this.dialogVisible && value) this.previewFile(value)
    },
    initialArtifact: {
      deep: true,
      handler: function(value) {
        if (this.dialogVisible && value) this.previewArtifact(value)
      },
    },
  },
  mounted: function() {
    if (this.visible) this.initializeWorkbench()
  },
  beforeDestroy: function() {
    this.revokeObjectUrls()
  },
  methods: {
    initializeWorkbench: async function() {
      this.currentRoot = this.initialRoot || '/workspace'
      this.currentAgentId = this.initialAgentId || ''
      this.currentArtifact = this.initialArtifact || null
      this.editMode = false
      this.isCropping = false
      this.exportDialogVisible = false
      await this.loadTree(this.currentRoot)
      if (this.currentArtifact && this.currentArtifact.type === 'diff') {
        this.previewArtifact(this.currentArtifact)
      } else if (this.initialPath) {
        await this.previewFile(this.initialPath)
      } else {
        this.currentPath = ''
        this.previewUrl = ''
        this.textContent = ''
        this.previewType = 'text'
      }
    },
    handleClosed: function() {
      this.editMode = false
      this.isCropping = false
      this.exportDialogVisible = false
    },
    refreshTree: async function() {
      await this.loadTree(this.currentRoot)
      if (this.currentPath) await this.previewFile(this.currentPath)
    },
    loadTree: async function(root) {
      if (!this.sessionId || !root) return
      this.treeLoading = true
      try {
        var response = await getFileTree(this.sessionId, root)
        this.treeData = response && response.data && response.data.tree ? [response.data.tree] : []
        this.currentRoot = root
        this.expandedKeys = [root]
      } finally {
        this.treeLoading = false
      }
    },
    handleNodeClick: async function(node) {
      if (!node) return
      if (node.type === 'directory') {
        await this.loadTree(node.path)
        return
      }
      await this.previewFile(node.path)
    },
    previewArtifact: async function(artifact) {
      var data = artifact && artifact.data ? artifact.data : {}
      this.currentArtifact = artifact
      this.currentPath = data.path || artifact.path || ''
      this.currentAgentId = artifact.agent_id || artifact.agentId || this.currentAgentId
      if (artifact.type === 'diff') {
        this.previewType = 'diff'
        this.previewUrl = ''
        this.textContent = ''
        this.editMode = false
        return
      }
      if (this.currentPath) await this.previewFile(this.currentPath)
    },
    previewFile: async function(filePath) {
      if (!filePath || !this.sessionId) return
      this.isCropping = false
      this.currentArtifact = null
      this.currentPath = filePath
      this.previewLoading = true
      this.previewType = 'text'
      this.previewUrl = ''
      this.textContent = ''
      this.editMode = false
      try {
        this.revokeObjectUrls()
        if (IMG_RE.test(filePath)) {
          this.previewType = 'image'
          this.previewUrl = await this.createAuthorizedObjectUrl(await getSessionRawFileUrl(this.sessionId, filePath))
          return
        }
        if (/\.csv$/i.test(filePath)) {
          this.previewType = 'table'
          var raw = await readSessionRawFile(this.sessionId, filePath)
          if (typeof raw === 'string') {
            var parsed = this.parseCsv(raw)
            this.tableHeaders = parsed.headers
            this.tableRows = parsed.rows
            this.tableEditRows = parsed.rows.map(function(row) { return Object.assign({}, row) })
          }
          return
        }
        if (/\.html?$/i.test(filePath)) {
          this.previewType = 'html'
          this.previewUrl = await getWorkspaceFileUrl(this.sessionId, filePath)
          var html = await readSessionRawFile(this.sessionId, filePath)
          this.textContent = typeof html === 'string' ? html : ''
          return
        }
        if (/\.pdf$/i.test(filePath)) {
          this.previewType = 'pdf'
          this.previewUrl = await this.createAuthorizedObjectUrl(await getSessionRawFileUrl(this.sessionId, filePath))
          return
        }
        if (CODE_RE.test(filePath)) this.previewType = 'code'
        var content = await readSessionRawFile(this.sessionId, filePath)
        this.textContent = typeof content === 'string' ? content : '无法读取文件'
      } catch (error) {
        this.textContent = error && error.message ? error.message : '加载文件失败'
      } finally {
        this.previewLoading = false
      }
    },
    createAuthorizedObjectUrl: async function(url) {
      var headers = {}
      var token = getAccessToken()
      if (token) headers.Authorization = 'Bearer ' + token
      var response = await fetch(url, { headers: headers })
      if (!response.ok) throw new Error('HTTP ' + response.status)
      var blob = await response.blob()
      var objectUrl = URL.createObjectURL(blob)
      this.objectUrls.push(objectUrl)
      return objectUrl
    },
    revokeObjectUrls: function() {
      while (this.objectUrls.length) {
        URL.revokeObjectURL(this.objectUrls.pop())
      }
    },
    saveRemoteFile: async function(url, filename) {
      if (window.weagentDesktopDownload && typeof window.weagentDesktopDownload.save === 'function') {
        try {
          return await window.weagentDesktopDownload.save({
            url: url,
            filename: filename,
            token: getAccessToken(),
          })
        } catch (error) {
          if (/No handler registered|download bridge|unavailable/i.test(String((error && error.message) || ''))) {
            return this.downloadViaRenderer(url, filename)
          }
          throw error
        }
      }
      return this.downloadViaRenderer(url, filename)
    },
    downloadViaRenderer: async function(url, filename) {
      var headers = {}
      var token = getAccessToken()
      if (token) headers.Authorization = 'Bearer ' + token
      var response = await fetch(url, { headers: headers })
      if (!response.ok) throw new Error('HTTP ' + response.status)
      var blob = await response.blob()
      var objectUrl = URL.createObjectURL(blob)
      this.objectUrls.push(objectUrl)
      var link = document.createElement('a')
      link.href = objectUrl
      link.download = filename || 'download'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      return { canceled: false }
    },
    downloadCurrent: async function() {
      if (!this.canDownload) return
      try {
        var result = await this.saveRemoteFile(await getSessionDownloadUrl(this.sessionId, this.currentPath), this.currentName || 'download')
        if (!result || result.canceled) return
        this.$message.success('下载完成')
      } catch (error) {
        this.$message.error(error && error.message ? error.message : '下载失败')
      }
    },
    exportZip: async function() {
      if (!this.canExportZip) return
      try {
        var result = await this.saveRemoteFile(
          await getSessionZipExportUrl(this.sessionId, this.currentRoot, 'auto'),
          this.zipExportFilename
        )
        if (!result || result.canceled) return
        this.$message.success('ZIP 导出完成')
      } catch (error) {
        this.$message.error(error && error.message ? error.message : 'ZIP 导出失败')
      }
    },
    openSelectiveExport: function() {
      this.exportDialogVisible = true
      var self = this
      this.$nextTick(function() {
        if (self.$refs.exportTree) self.$refs.exportTree.setCheckedKeys([])
      })
    },
    exportSelectedZip: async function() {
      if (!this.$refs.exportTree) return
      var selectedPaths = this.$refs.exportTree.getCheckedKeys()
      if (!selectedPaths || !selectedPaths.length) {
        this.$message.warning('请至少选择一个文件或文件夹')
        return
      }
      this.exportingZip = true
      try {
        var result = await this.saveRemoteFile(
          await getSessionZipExportUrl(this.sessionId, this.currentRoot, 'auto', selectedPaths),
          this.zipExportFilename
        )
        if (!result || result.canceled) return
        this.exportDialogVisible = false
        this.$message.success('已导出所选文件')
      } catch (error) {
        this.$message.error(error && error.message ? error.message : '导出所选文件失败')
      } finally {
        this.exportingZip = false
      }
    },
    handleSaved: function(payload) {
      this.textContent = payload && payload.content ? payload.content : this.textContent
      this.editMode = false
      if (this.previewType === 'html' && this.previewUrl) {
        this.previewUrl = this.previewUrl.split('?')[0] + '?t=' + Date.now()
      }
      this.$emit('saved', payload)
    },
    handleDiffApplied: function(payload) {
      this.$emit('saved', payload)
    },
    enterCropMode: function() {
      if (this.canCrop) this.isCropping = true
    },
    exitCropMode: function() {
      this.isCropping = false
    },
    onCropSaved: async function(payload) {
      this.isCropping = false
      if (!payload || !payload.base64 || !this.currentPath || !this.sessionId) return
      try {
        await writeFile(this.sessionId, this.currentPath, payload.base64)
        await this.previewFile(this.currentPath)
        this.$emit('saved', { path: this.currentPath, content: payload.base64 })
        this.$message.success('图片已保存')
      } catch (error) {
        this.$message.error(error && error.message ? error.message : '图片保存失败')
      }
    },
    parseCsv: function(text) {
      var rows = this.parseCsvRows(text)
      if (!rows.length) return { headers: [], rows: [] }
      var headers = (rows[0] || []).map(function(item) { return String(item == null ? '' : item).trim() })
      var normalizedRows = []
      for (var i = 1; i < rows.length; i++) {
        var values = rows[i] || []
        var row = {}
        for (var j = 0; j < headers.length; j++) row['col_' + j] = String(values[j] == null ? '' : values[j])
        normalizedRows.push(row)
      }
      return { headers: headers, rows: normalizedRows }
    },
    parseCsvRows: function(text) {
      var source = String(text || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n')
      var rows = []
      var row = []
      var cell = ''
      var inQuotes = false
      for (var i = 0; i < source.length; i++) {
        var char = source[i]
        var next = source[i + 1]
        if (char === '"') {
          if (inQuotes && next === '"') {
            cell += '"'
            i += 1
          } else {
            inQuotes = !inQuotes
          }
        } else if (char === ',' && !inQuotes) {
          row.push(cell)
          cell = ''
        } else if (char === '\n' && !inQuotes) {
          row.push(cell)
          if (row.some(function(item) { return item !== '' })) rows.push(row)
          row = []
          cell = ''
        } else {
          cell += char
        }
      }
      row.push(cell)
      if (row.some(function(item) { return item !== '' })) rows.push(row)
      return rows
    },
    escapeCsvCell: function(value) {
      var text = String(value == null ? '' : value)
      if (/[",\n]/.test(text)) return '"' + text.replace(/"/g, '""') + '"'
      return text
    },
    addTableRow: function() {
      var row = {}
      for (var i = 0; i < this.tableHeaders.length; i++) row['col_' + i] = ''
      this.tableEditRows.push(row)
    },
    deleteTableRow: function(index) {
      this.tableEditRows.splice(index, 1)
    },
    saveTable: async function() {
      this.savingTable = true
      try {
        var self = this
        var lines = this.tableEditRows.map(function(row) {
          var values = []
          for (var i = 0; i < self.tableHeaders.length; i++) values.push(self.escapeCsvCell(row['col_' + i]))
          return values.join(',')
        })
        var csv = [this.tableHeaders.map(function(header) { return self.escapeCsvCell(header) }).join(',')].concat(lines).join('\n')
        await writeFile(this.sessionId, this.currentPath, csv)
        this.tableRows = this.tableEditRows.map(function(row) { return Object.assign({}, row) })
        this.editMode = false
        this.$emit('saved', { path: this.currentPath, content: csv })
        this.$message.success('CSV 已保存')
      } catch (error) {
        this.$message.error(error && error.message ? error.message : 'CSV 保存失败')
      } finally {
        this.savingTable = false
      }
    },
    getExt: function(path) {
      var match = String(path || '').match(/\.([^./]+)$/)
      return match ? match[1] : ''
    },
    fileIcon: function(path) {
      var value = String(path || '').toLowerCase()
      if (IMG_RE.test(value)) return 'el-icon-picture-outline'
      if (/\.(zip|rar|7z|tar|gz)$/i.test(value)) return 'el-icon-folder'
      if (CODE_RE.test(value)) return 'el-icon-document-copy'
      return 'el-icon-document'
    },
    filterExportTree: function(nodes) {
      var self = this
      return (Array.isArray(nodes) ? nodes : []).reduce(function(result, node) {
        if (!node) return result
        if (node.type === 'file' && node.name === 'CLAUDE.md') return result
        var nextNode = Object.assign({}, node)
        if (Array.isArray(node.children)) {
          nextNode.children = self.filterExportTree(node.children)
        }
        result.push(nextNode)
        return result
      }, [])
    },
  },
}
</script>

<style scoped>
:deep(.artifact-workbench-dialog .el-dialog) { margin-top: 0 !important; }
:deep(.artifact-workbench-dialog .el-dialog__header) { display: none; }
:deep(.artifact-workbench-dialog .el-dialog__body) { padding: 0; }

.awb-layout { display: flex; flex-direction: column; height: 100vh; background: #f7f9fc; }
.awb-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 16px; background: rgba(255,255,255,0.96); border-bottom: 1px solid #dbe3f0; }
.awb-toolbar-left, .awb-toolbar-right { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.awb-filename { font-size: 14px; font-weight: 600; color: #0f172a; }
.awb-meta { font-size: 12px; color: #64748b; }
.awb-body { display: flex; flex: 1; min-height: 0; }
.awb-tree { width: 280px; min-width: 240px; display: flex; flex-direction: column; border-right: 1px solid #e2e8f0; background: #fff; }
.awb-tree-header { padding: 14px 14px 10px; border-bottom: 1px solid #eef2f7; }
.awb-tree-title { display: block; font-size: 13px; font-weight: 600; color: #334155; }
.awb-tree-root { display: block; margin-top: 4px; font-size: 12px; color: #64748b; word-break: break-all; }
.awb-tree-loading { padding: 18px 14px; color: #64748b; }
.awb-tree-panel { flex: 1; min-height: 0; overflow: auto; }
.awb-tree-node { display: inline-flex; align-items: center; gap: 8px; }
.awb-tree-label { overflow: hidden; text-overflow: ellipsis; }
.awb-main { position: relative; flex: 1; min-width: 0; min-height: 0; display: flex; flex-direction: column; background: #f8fafc; }
.awb-empty, .awb-loading { display: flex; flex: 1; align-items: center; justify-content: center; gap: 8px; color: #64748b; }
.awb-frame-wrap, .awb-image-wrap, .awb-code, .awb-diff, .awb-editor-wrap, .awb-table-wrap { flex: 1; min-height: 0; }
.awb-frame { width: 100%; height: 100%; border: 0; background: #fff; }
.awb-image-wrap { display: flex; align-items: center; justify-content: center; padding: 24px; }
.awb-image { max-width: 100%; max-height: 100%; object-fit: contain; }
.awb-code { margin: 0; padding: 18px; overflow: auto; font-family: Consolas, "SFMono-Regular", Menlo, monospace; font-size: 13px; line-height: 1.65; color: #0f172a; white-space: pre-wrap; word-break: break-word; }
.awb-editor-wrap { overflow: auto; }
.awb-table-wrap { padding: 16px; overflow: auto; background: #fff; }
.awb-table-toolbar { display: flex; gap: 8px; margin-bottom: 12px; }
.awb-diff-card { margin: 0; }
.awb-export-overlay { position: absolute; inset: 0; z-index: 30; display: flex; align-items: center; justify-content: center; background: rgba(15, 23, 42, 0.42); }
.awb-export-modal { width: min(620px, calc(100vw - 40px)); max-height: min(78vh, 760px); display: flex; flex-direction: column; background: #fff; border-radius: 16px; box-shadow: 0 20px 60px rgba(15, 23, 42, 0.24); overflow: hidden; }
.awb-export-modal-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 18px; border-bottom: 1px solid #e2e8f0; font-size: 16px; font-weight: 600; color: #0f172a; }
.awb-export-panel { display: flex; flex-direction: column; padding: 16px 18px; min-height: 0; }
.awb-export-hint { margin-bottom: 12px; font-size: 13px; line-height: 1.5; color: #475569; }
.awb-export-tree { flex: 1; min-height: 260px; max-height: 50vh; overflow: auto; border: 1px solid #e2e8f0; border-radius: 10px; padding: 10px; background: #fff; }
.awb-export-actions { display: flex; justify-content: flex-end; gap: 8px; padding: 14px 18px 18px; border-top: 1px solid #e2e8f0; }
</style>
