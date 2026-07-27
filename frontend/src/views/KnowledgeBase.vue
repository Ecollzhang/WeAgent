<template>
  <div class="kb-page">
    <AppSidebar />
    <div class="kb-main">
      <div class="page-header">
        <div class="page-header-top">
          <h2>知识库</h2>
          <span v-if="serviceStatus" class="status-badge" :class="serviceStatus.status">
            <i :class="statusIcon" />
            {{ statusLabel }}
          </span>
        </div>
        <span class="page-subtitle">上传文档、网页、链接，Agent 在对话中可检索知识库内容</span>
      </div>

      <el-tabs v-model="activeDomain" @tab-click="onDomainChange">
        <el-tab-pane label="全部领域" name="all"></el-tab-pane>
        <el-tab-pane label="智能研发" name="rd"></el-tab-pane>
        <el-tab-pane label="智慧教育" name="edu"></el-tab-pane>
        <el-tab-pane label="智慧办公" name="office"></el-tab-pane>
      </el-tabs>

      <div class="toolbar">
        <div class="toolbar-left">
          <el-button size="small" type="primary" icon="el-icon-upload2" @click="openUploadDialog">
            上传文档
          </el-button>
          <el-button size="small" icon="el-icon-link" @click="openFetchDialog">
            从链接下载
          </el-button>
          <el-button size="small" icon="el-icon-share" @click="openScrapeDialog">
            爬取网页
          </el-button>
        </div>
        <div class="toolbar-right">
          <el-input
            v-model="searchText"
            size="small"
            placeholder="搜索文档名称"
            clearable
            prefix-icon="el-icon-search"
            style="width: 240px"
          />
          <el-button size="small" icon="el-icon-refresh" @click="loadDocuments" style="margin-left: 8px">
            刷新
          </el-button>
        </div>
      </div>

      <el-table
        :data="filteredDocuments"
        v-loading="loading"
        border
        stripe
        size="small"
        class="doc-table"
        row-key="id"
      >
        <el-table-column prop="name" label="文档名称" min-width="200" show-overflow-tooltip />
        <el-table-column label="来源" width="90" align="center">
          <template slot-scope="{ row }">
            <el-tag size="mini" :type="sourceTag(row.source_type)">
              {{ sourceLabel(row.source_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="file_type" label="类型" width="80" align="center" />
        <el-table-column label="大小" width="90" align="center">
          <template slot-scope="{ row }">
            {{ formatSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template slot-scope="{ row }">
            <el-tag size="mini" :type="statusTag(row.status)">
              {{ docStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="分块" width="80" align="center">
          <template slot-scope="{ row }">
            {{ row.chunk_count || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="domain" label="领域" width="80" align="center">
          <template slot-scope="{ row }">
            {{ domainLabel(row.domain) }}
          </template>
        </el-table-column>
        <el-table-column label="上传时间" width="160" align="center">
          <template slot-scope="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230" align="center" fixed="right">
          <template slot-scope="{ row }">
            <el-button
              v-if="row.status === 'pending'"
              size="mini"
              type="primary"
              plain
              @click="openPreview(row)"
            >
              预览确认
            </el-button>
            <el-button
              v-if="row.status === 'ready'"
              size="mini"
              type="info"
              plain
              @click="openPreview(row)"
            >
              查看
            </el-button>
            <el-button
              v-if="row.status === 'error'"
              size="mini"
              type="info"
              plain
              @click="openPreview(row)"
            >
              查看
            </el-button>
            <el-button
              v-if="row.status === 'error'"
              size="mini"
              type="warning"
              plain
              :loading="reprocessing === row.id"
              @click="handleReprocess(row)"
            >
              重新处理
            </el-button>
            <span v-if="row.status === 'processing'" class="processing-hint">
              <i class="el-icon-loading" /> 处理中
            </span>
            <el-button
              size="mini"
              type="danger"
              plain
              icon="el-icon-delete"
              @click="handleDelete(row)"
            />
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!loading && documents.length === 0" class="empty-hint">
        暂无文档，点击「上传文档」或「从链接下载」添加知识库内容
      </div>

      <el-pagination
        v-if="total > perPage"
        class="pagination"
        background
        layout="total, prev, pager, next"
        :total="total"
        :page-size="perPage"
        :current-page.sync="page"
        @current-change="loadDocuments"
      />

      <el-divider />

      <!-- 检索测试 -->
      <div class="search-test-section">
        <h3 class="section-title">知识库检索测试</h3>
        <div class="search-bar">
          <el-input
            v-model="searchQuery"
            size="small"
            placeholder="输入搜索内容，测试知识库检索..."
            clearable
            @keyup.enter.native="handleSearchTest"
            style="flex: 1"
          >
            <el-select
              v-model="searchDomain"
              slot="prepend"
              size="small"
              placeholder="领域"
              style="width: 110px"
            >
              <el-option label="全部" value="" />
              <el-option label="研发" value="rd" />
              <el-option label="教育" value="edu" />
              <el-option label="办公" value="office" />
            </el-select>
          </el-input>
          <el-button
            type="primary"
            size="small"
            icon="el-icon-search"
            :loading="searchLoading"
            @click="handleSearchTest"
            style="margin-left: 8px"
          >
            搜索
          </el-button>
        </div>
        <div v-if="searchResults.length > 0" class="search-results">
          <div
            v-for="(r, idx) in searchResults"
            :key="idx"
            class="search-result-item"
          >
            <div class="result-header">
              <el-tag size="mini" type="success">
                相关度: {{ (r.score * 100).toFixed(1) }}%
              </el-tag>
              <span class="result-doc" v-if="r.document">
                {{ r.document.name }}
              </span>
              <span class="result-index">#{{ idx + 1 }}</span>
            </div>
            <div class="result-content">{{ r.content }}</div>
          </div>
        </div>
        <div v-if="searchDone && searchResults.length === 0" class="search-empty">
          未找到相关内容
        </div>
      </div>
    </div>

    <!-- 上传对话框 -->
    <el-dialog
      title="上传文档"
      :visible.sync="uploadVisible"
      width="480px"
      top="12vh"
      :close-on-click-modal="false"
      @closed="resetUploadForm"
    >
      <el-form label-position="top" size="small">
        <el-form-item label="选择文件">
          <el-upload
            ref="uploadRef"
            drag
            action=""
            :auto-upload="false"
            :limit="1"
            :on-change="onFileChange"
            :file-list="uploadFileList"
          >
            <i class="el-icon-upload" />
            <div class="el-upload__text">将文件拖到此处，或<em>点击上传</em></div>
            <div class="el-upload__tip" slot="tip">
              支持 PDF、Word、TXT、Markdown、代码文件、CSV、HTML，最大 20MB
            </div>
          </el-upload>
        </el-form-item>
        <el-form-item label="所属领域">
          <el-select v-model="uploadDomain" style="width: 100%">
            <el-option label="智能研发" value="rd" />
            <el-option label="智慧教育" value="edu" />
            <el-option label="智慧办公" value="office" />
          </el-select>
        </el-form-item>
        <el-form-item label="工作空间（可选）">
          <el-input v-model="uploadWorkspaceId" placeholder="留空则全局可用" clearable />
        </el-form-item>
      </el-form>
      <span slot="footer">
        <el-button @click="uploadVisible = false" :disabled="uploading">取消</el-button>
        <el-button type="primary" @click="handleUpload" :loading="uploading" :disabled="!uploadFile">
          上传
        </el-button>
      </span>
    </el-dialog>

    <!-- URL 对话框（下载 / 爬取共用） -->
    <el-dialog
      :title="urlDialogMode === 'fetch' ? '从链接下载文档' : '爬取网页内容'"
      :visible.sync="urlVisible"
      width="500px"
      top="12vh"
      :close-on-click-modal="false"
      @closed="resetUrlForm"
    >
      <el-form label-position="top" size="small">
        <el-form-item label="URL 地址">
          <el-input
            v-model="urlInput"
            placeholder="https://example.com/document.pdf"
            clearable
          />
        </el-form-item>
        <el-form-item label="所属领域">
          <el-select v-model="urlDomain" style="width: 100%">
            <el-option label="智能研发" value="rd" />
            <el-option label="智慧教育" value="edu" />
            <el-option label="智慧办公" value="office" />
          </el-select>
        </el-form-item>
        <el-form-item label="工作空间（可选）">
          <el-input v-model="urlWorkspaceId" placeholder="留空则全局可用" clearable />
        </el-form-item>
      </el-form>
      <span slot="footer">
        <el-button @click="urlVisible = false" :disabled="urlLoading">取消</el-button>
        <el-button type="primary" @click="handleUrlSubmit" :loading="urlLoading" :disabled="!urlInput">
          {{ urlDialogMode === 'fetch' ? '下载' : '爬取' }}
        </el-button>
      </span>
    </el-dialog>

    <!-- 预览确认对话框 -->
    <el-dialog
      :title="previewDoc ? previewDoc.name : '文档预览'"
      :visible.sync="previewVisible"
      width="700px"
      top="6vh"
      :close-on-click-modal="false"
    >
      <div v-if="previewLoading" class="preview-loading">
        <i class="el-icon-loading" /><span>加载中...</span>
      </div>
      <div v-else-if="previewData" class="preview-body">
        <div class="preview-meta">
          <el-tag size="small" :type="sourceTag(previewData.source_type)">
            {{ sourceLabel(previewData.source_type) }}
          </el-tag>
          <el-tag size="small">{{ previewData.file_type }}</el-tag>
          <span class="meta-text">总字数: {{ previewData.text_length }}</span>
          <span v-if="previewData.page_count" class="meta-text">页数: {{ previewData.page_count }}</span>
          <span v-if="previewData.title" class="meta-text">标题: {{ previewData.title }}</span>
        </div>
        <div class="preview-content">
          <pre>{{ previewData.preview }}</pre>
          <p v-if="previewData.has_more" class="preview-more">
            ... 仅显示前 2000 字，确认存储后将进行分块和向量化处理
          </p>
        </div>
        <div v-if="previewData.status === 'ready'" class="preview-chunks">
          <el-divider content-position="left">已分块信息</el-divider>
          <p>分块数: {{ previewDoc.chunk_count }}，Token 总数: {{ previewDoc.total_tokens }}</p>
        </div>
      </div>
      <span slot="footer" v-if="previewData && previewData.status === 'pending'">
        <el-button @click="previewVisible = false">取消</el-button>
        <el-button type="primary" @click="handleConfirm" :loading="confirming">
          确认存储到知识库
        </el-button>
      </span>
      <span slot="footer" v-else>
        <el-button @click="previewVisible = false">关闭</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import {
  uploadDocument,
  fetchFromUrl,
  scrapeFromUrl,
  previewDocument,
  confirmDocument,
  deleteDocument,
  reprocessDocument,
  listDocuments,
  semanticSearch,
  getRagStatus,
} from '../api/knowledge'
import AppSidebar from '../components/Sidebar/index.vue'

export default {
  name: 'KnowledgeBase',

  components: {
    AppSidebar,
  },

  data() {
    return {
      activeDomain: 'all',
      loading: false,
      documents: [],
      total: 0,
      page: 1,
      perPage: 20,
      searchText: '',

      // upload
      uploadVisible: false,
      uploadFile: null,
      uploadFileList: [],
      uploadDomain: 'rd',
      uploadWorkspaceId: '',
      uploading: false,

      // URL dialog (shared)
      urlVisible: false,
      urlDialogMode: 'fetch', // 'fetch' | 'scrape'
      urlInput: '',
      urlDomain: 'rd',
      urlWorkspaceId: '',
      urlLoading: false,

      // preview
      previewVisible: false,
      previewDoc: null,
      previewData: null,
      previewLoading: false,
      confirming: false,

      // search test
      searchQuery: '',
      searchDomain: '',
      searchLoading: false,
      searchDone: false,
      searchResults: [],

      // service status
      serviceStatus: null,

      // auto-refresh for processing documents
      processingTimer: null,
      reprocessing: null,  // doc id being re-processed
    }
  },

  computed: {
    statusIcon() {
      if (!this.serviceStatus) return 'el-icon-warning'
      if (this.serviceStatus.status === 'healthy') return 'el-icon-success'
      if (this.serviceStatus.status === 'degraded') return 'el-icon-warning'
      return 'el-icon-error'
    },
    statusLabel() {
      if (!this.serviceStatus) return '检测中...'
      if (this.serviceStatus.status === 'healthy') return '服务正常'
      if (this.serviceStatus.status === 'degraded') return '部分可用'
      return '服务异常'
    },

    filteredDocuments() {
      if (!this.searchText) return this.documents
      const s = this.searchText.toLowerCase()
      return this.documents.filter(d => d.name.toLowerCase().includes(s))
    },

    hasProcessingDocuments() {
      return this.documents.some(d => d.status === 'processing')
    },
  },

  watch: {
    hasProcessingDocuments(val) {
      if (val) {
        this.startProcessingPoll()
      } else {
        this.stopProcessingPoll()
      }
    },
  },

  methods: {
    sourceLabel(type) {
      const map = { upload: '上传', url: '下载', scrape: '爬取' }
      return map[type] || type
    },
    sourceTag(type) {
      const map = { upload: '', url: 'warning', scrape: 'info' }
      return map[type] || ''
    },
    docStatusLabel(status) {
      const map = {
        pending: '待确认',
        processing: '处理中',
        ready: '已就绪',
        error: '失败',
      }
      return map[status] || status
    },
    statusTag(status) {
      const map = {
        pending: 'warning',
        processing: 'info',
        ready: 'success',
        error: 'danger',
      }
      return map[status] || ''
    },
    domainLabel(domain) {
      const map = { rd: '研发', edu: '教育', office: '办公' }
      return map[domain] || domain || '-'
    },
    formatSize(bytes) {
      if (!bytes && bytes !== 0) return '-'
      if (bytes < 1024) return bytes + ' B'
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
      return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    },
    formatTime(ts) {
      if (!ts) return '-'
      try {
        const d = new Date(ts)
        const pad = n => String(n).padStart(2, '0')
        return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
      } catch {
        return ts
      }
    },

    // ── 列表加载 ──
    async loadDocuments() {
      this.loading = true
      try {
        const params = {
          page: this.page,
          per_page: this.perPage,
        }
        if (this.activeDomain && this.activeDomain !== 'all') params.domain = this.activeDomain
        if (this.searchText) params.search = this.searchText

        console.log('[KB] loadDocuments params:', params)
        const res = await listDocuments(params)
        console.log('[KB] loadDocuments res:', res)
        if (res.code === 200) {
          this.documents = res.data.items || []
          this.total = res.data.total || 0
          console.log('[KB] documents loaded:', this.documents.length, 'total:', this.total)
        } else {
          console.error('[KB] loadDocuments failed:', res.message)
          this.$message.error(res.message || '加载失败')
        }
      } catch (e) {
        console.error('[KB] loadDocuments error:', e)
        this.$message.error('加载文档列表失败')
      } finally {
        this.loading = false
      }
    },

    onDomainChange() {
      this.searchText = ''
      this.page = 1
      this.loadDocuments()
    },

    // ── 上传 ──
    openUploadDialog() {
      this.uploadDomain = this.activeDomain !== 'all' ? this.activeDomain : 'rd'
      this.uploadVisible = true
    },

    onFileChange(file) {
      this.uploadFile = file.raw
      this.uploadFileList = [file]
    },

    resetUploadForm() {
      this.uploadFile = null
      this.uploadFileList = []
      this.uploadWorkspaceId = ''
    },

    async handleUpload() {
      if (!this.uploadFile) {
        this.$message.warning('请选择文件')
        return
      }
      this.uploading = true
      try {
        const formData = new FormData()
        formData.append('file', this.uploadFile)
        formData.append('domain', this.uploadDomain)
        if (this.uploadWorkspaceId) {
          formData.append('workspace_id', this.uploadWorkspaceId)
        }

        console.log('[KB] handleUpload domain:', this.uploadDomain)
        const res = await uploadDocument(formData)
        console.log('[KB] handleUpload res:', res)
        if (res.code === 201) {
          this.$message.success('文档上传成功，请预览确认后存储')
          this.uploadVisible = false
          await this.loadDocuments()
        } else {
          console.error('[KB] handleUpload failed:', res.message)
          this.$message.error(res.message || '上传失败')
        }
      } catch (e) {
        console.error('[KB] handleUpload error:', e)
        this.$message.error('上传失败')
      } finally {
        this.uploading = false
      }
    },

    // ── URL 下载 / 爬取 ──
    openFetchDialog() {
      this.urlDialogMode = 'fetch'
      this.urlDomain = this.activeDomain !== 'all' ? this.activeDomain : 'rd'
      this.urlVisible = true
    },

    openScrapeDialog() {
      this.urlDialogMode = 'scrape'
      this.urlDomain = this.activeDomain !== 'all' ? this.activeDomain : 'rd'
      this.urlVisible = true
    },

    resetUrlForm() {
      this.urlInput = ''
      this.urlWorkspaceId = ''
    },

    async handleUrlSubmit() {
      if (!this.urlInput.trim()) {
        this.$message.warning('请输入 URL')
        return
      }
      this.urlLoading = true
      try {
        const data = {
          url: this.urlInput.trim(),
          domain: this.urlDomain,
        }
        if (this.urlWorkspaceId) {
          data.workspace_id = this.urlWorkspaceId
        }

        const apiFn = this.urlDialogMode === 'fetch' ? fetchFromUrl : scrapeFromUrl
        const res = await apiFn(data)
        if (res.code === 201) {
          this.$message.success(
            this.urlDialogMode === 'fetch'
              ? '文档下载成功，请预览确认后存储'
              : '网页爬取成功，请预览确认后存储'
          )
          this.urlVisible = false
          this.loadDocuments()
        } else {
          this.$message.error(res.message || '操作失败')
        }
      } catch {
        this.$message.error('操作失败')
      } finally {
        this.urlLoading = false
      }
    },

    // ── 预览 & 确认 ──
    async openPreview(row) {
      this.previewDoc = row
      this.previewData = null
      this.previewLoading = true
      this.previewVisible = true
      try {
        const res = await previewDocument(row.id)
        if (res.code === 200) {
          this.previewData = res.data
        } else {
          this.$message.error(res.message || '加载预览失败')
          this.previewVisible = false
        }
      } catch {
        this.$message.error('加载预览失败')
        this.previewVisible = false
      } finally {
        this.previewLoading = false
      }
    },

    async handleConfirm() {
      if (!this.previewDoc) return
      this.confirming = true
      try {
        const res = await confirmDocument(this.previewDoc.id)
        if (res.code === 200) {
          if (res.data.status === 'processing') {
            this.$message.success('文档已提交后台处理，请稍候...')
          } else {
            this.$message.success(`已确认存储，分块数: ${res.data.chunk_count}`)
          }
          this.previewVisible = false
          this.loadDocuments()
        } else {
          this.$message.error(res.message || '确认存储失败')
        }
      } catch {
        this.$message.error('确认存储失败')
      } finally {
        this.confirming = false
      }
    },

    // ── 检索测试 ──
    async handleSearchTest() {
      if (!this.searchQuery.trim()) {
        this.$message.warning('请输入搜索内容')
        return
      }
      this.searchLoading = true
      this.searchDone = false
      this.searchResults = []
      try {
        const data = { query: this.searchQuery.trim(), top_k: 5 }
        if (this.searchDomain) data.domain = this.searchDomain
        const res = await semanticSearch(data)
        if (res.code === 200) {
          this.searchResults = res.data.results || []
          this.searchDone = true
        } else {
          this.$message.error(res.message || '搜索失败')
        }
      } catch {
        this.$message.error('检索请求失败，请确认 RAG 服务已启动')
      } finally {
        this.searchLoading = false
      }
    },

    // ── 删除 ──
    async handleDelete(row) {
      try {
        await this.$confirm(
          `确认删除文档「${row.name}」？所有分块和向量数据将被永久移除。`,
          '提示',
          { type: 'warning' }
        )
        const res = await deleteDocument(row.id)
        if (res.code === 200) {
          this.$message.success('已删除')
          this.loadDocuments()
        } else {
          this.$message.error(res.message || '删除失败')
        }
      } catch {
        // cancelled
      }
    },

    // ── 自动刷新处理中的文档 ──
    startProcessingPoll() {
      if (this.processingTimer) return
      this.processingTimer = setInterval(() => {
        this.loadDocuments()
      }, 5000)
    },

    stopProcessingPoll() {
      if (this.processingTimer) {
        clearInterval(this.processingTimer)
        this.processingTimer = null
      }
    },

    // ── 重新处理 ──
    async handleReprocess(row) {
      this.reprocessing = row.id
      try {
        const res = await reprocessDocument(row.id)
        if (res.code === 200) {
          this.$message.success(`重新处理成功，分块数: ${res.data.chunk_count}`)
          this.loadDocuments()
        } else {
          this.$message.error(res.message || '重新处理失败')
        }
      } catch {
        this.$message.error('重新处理失败')
      } finally {
        this.reprocessing = null
      }
    },

    // ── 服务状态检查 ──
    async checkServiceStatus() {
      try {
        const res = await getRagStatus()
        if (res.code === 200) {
          this.serviceStatus = res.data
        }
      } catch {
        this.serviceStatus = { status: 'unreachable', components: {} }
      }
    },
  },

  mounted() {
    console.log('[KB] mounted, activeDomain:', this.activeDomain)
    this.loadDocuments()
    this.checkServiceStatus()
    // 如果加载后已有处理中的文档，启动轮询
    this.$nextTick(() => {
      if (this.hasProcessingDocuments) {
        this.startProcessingPoll()
      }
    })
  },

  beforeDestroy() {
    this.stopProcessingPoll()
  },
}
</script>

<style scoped>
.kb-page {
  display: flex;
  gap: 12px;
  padding: 12px;
  height: 100vh;
  background: linear-gradient(135deg, #e8f0ff 0%, #f0f5ff 50%, #f5f7fa 100%);
  overflow: hidden;
}
.kb-main {
  flex: 1;
  background: #fff;
  border-radius: 12px;
  padding: 28px 32px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  overflow-y: auto;
}
.page-header {
  margin-bottom: 22px;
}
.page-header-top {
  display: flex;
  align-items: center;
  gap: 12px;
}
.page-header h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: #1e293b;
}
.status-badge {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.status-badge.healthy {
  background: #ecfdf5;
  color: #059669;
}
.status-badge.degraded, .status-badge.unreachable {
  background: #fef3c7;
  color: #d97706;
}
.page-subtitle {
  font-size: 13px;
  color: #94a3b8;
  margin-top: 4px;
  display: block;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.toolbar-right {
  display: flex;
  align-items: center;
}

.doc-table {
  font-size: 13px;
}

.empty-hint {
  text-align: center;
  padding: 40px;
  color: #94a3b8;
  font-size: 14px;
}

.pagination {
  margin-top: 16px;
  text-align: right;
}

.preview-loading {
  text-align: center;
  padding: 40px;
  color: #94a3b8;
}
.preview-loading i {
  margin-right: 8px;
}

.preview-body {
  max-height: 60vh;
  overflow-y: auto;
}

.preview-meta {
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.meta-text {
  font-size: 12px;
  color: #94a3b8;
}

.processing-hint {
  font-size: 12px;
  color: #909399;
  margin-right: 6px;
}
.processing-hint i {
  margin-right: 2px;
}

.preview-content pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  background: #f8f9fb;
  padding: 16px;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.7;
  max-height: 400px;
  overflow-y: auto;
}
.preview-more {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 8px;
}

.preview-chunks {
  margin-top: 16px;
  font-size: 13px;
  color: #475569;
}

.search-test-section {
  margin-top: 8px;
}
.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 12px;
}
.search-bar {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}
.search-results {
  margin-top: 12px;
}
.search-result-item {
  padding: 12px 16px;
  background: #f8f9fb;
  border-radius: 8px;
  margin-bottom: 10px;
}
.result-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.result-doc {
  font-size: 13px;
  color: #475569;
}
.result-index {
  margin-left: auto;
  font-size: 12px;
  color: #94a3b8;
}
.result-content {
  font-size: 13px;
  line-height: 1.7;
  color: #334155;
  white-space: pre-wrap;
  word-wrap: break-word;
}
.search-empty {
  text-align: center;
  padding: 24px;
  color: #94a3b8;
  font-size: 13px;
}
</style>
