<template>
  <span class="kb-doc-selector">
    <!-- 触发按钮 (可隐藏) -->
    <el-button
      v-if="!hideTrigger"
      size="mini"
      icon="el-icon-collection"
      type="text"
      :title="buttonTitle"
      :class="{ 'kb-active': hasSelection }"
      @click="openDialog"
    />

    <!-- 文档选择弹窗 -->
    <el-dialog
      :visible.sync="visible"
      title="选择知识库文档"
      width="520px"
      :close-on-click-modal="true"
      @open="loadDocuments"
    >
      <div class="kb-dialog-body">
        <div class="kb-filter-row">
          <el-select v-model="filterDomain" size="small" placeholder="领域筛选" @change="loadDocuments">
            <el-option label="全部领域" value="" />
            <el-option label="智能研发" value="rd" />
            <el-option label="智慧教育" value="edu" />
            <el-option label="智慧办公" value="office" />
          </el-select>
          <el-input
            v-model="searchText"
            size="small"
            placeholder="搜索文档名称"
            prefix-icon="el-icon-search"
            clearable
            @input="filterDocuments"
          />
        </div>

        <div class="kb-domain-filter">
          <label class="kb-domain-label">检索领域范围：</label>
          <el-radio-group v-model="kbDomain" size="small" @change="onDomainChange">
            <el-radio-button label="">继承工作空间</el-radio-button>
            <el-radio-button label="all">全部</el-radio-button>
            <el-radio-button label="rd">研发</el-radio-button>
            <el-radio-button label="edu">教育</el-radio-button>
            <el-radio-button label="office">办公</el-radio-button>
          </el-radio-group>
        </div>

        <div class="kb-doc-list" v-loading="loading">
          <div v-if="filteredDocs.length === 0" class="kb-empty">
            <i class="el-icon-document"></i>
            <p>暂无可用文档，请先在知识库页面导入文档</p>
          </div>

          <el-checkbox-group v-model="selectedIds" @change="onSelectionChange">
            <div
              v-for="doc in filteredDocs"
              :key="doc.id"
              class="kb-doc-item"
            >
              <el-checkbox :label="doc.id">
                <span class="doc-name">{{ doc.name }}</span>
                <el-tag size="mini" effect="plain" class="doc-domain-tag">
                  {{ domainLabel(doc.domain) }}
                </el-tag>
                <el-tag
                  size="mini"
                  :type="doc.status === 'ready' ? 'success' : 'info'"
                  effect="plain"
                >
                  {{ doc.status === 'ready' ? '就绪' : doc.status }}
                </el-tag>
              </el-checkbox>
            </div>
          </el-checkbox-group>
        </div>
      </div>

      <span slot="footer">
        <el-button size="small" @click="visible = false">关闭</el-button>
        <el-button size="small" type="primary" @click="visible = false">
          确定 ({{ selectedIds.length }} 个文档)
        </el-button>
      </span>
    </el-dialog>
  </span>
</template>

<script>
import { listDocuments } from '@/api/knowledge'
import { updateConversationKb } from '@/api/conversation'

export default {
  name: 'KbDocumentSelector',
  props: {
    conversation: { type: Object, default: null },
    hideTrigger: { type: Boolean, default: false },
  },
  data() {
    return {
      visible: false,
      loading: false,
      filterDomain: '',
      searchText: '',
      kbDomain: '',
      allDocs: [],
      selectedIds: [],
    }
  },
  computed: {
    hasSelection() {
      return (this.conversation?.kb_document_ids?.length || 0) > 0 ||
             (this.selectedIds.length > 0)
    },
    buttonTitle() {
      const count = this.selectedIds.length
      return count > 0
        ? `已选 ${count} 个知识库文档`
        : '选择知识库文档'
    },
    filteredDocs() {
      let docs = this.allDocs
      if (this.searchText) {
        const q = this.searchText.toLowerCase()
        docs = docs.filter(d => (d.name || '').toLowerCase().includes(q))
      }
      return docs
    },
  },
  watch: {
    conversation: {
      immediate: true,
      handler(val) {
        if (val) {
          this.selectedIds = val.kb_document_ids || []
          this.kbDomain = val.kb_domain || ''
        }
      },
    },
  },
  methods: {
    openDialog() {
      this.visible = true
    },
    async loadDocuments() {
      this.loading = true
      try {
        const params = { per_page: 100 }
        if (this.filterDomain) params.domain = this.filterDomain
        const res = await listDocuments(params)
        if (res.code === 200) {
          this.allDocs = (res.data.items || res.data || []).filter(
            d => d.status === 'ready'
          )
        }
      } catch {
        this.allDocs = []
      } finally {
        this.loading = false
      }
    },
    filterDocuments() {
      // 由 computed filteredDocs 自动处理
    },
    domainLabel(domain) {
      const map = { rd: '研发', edu: '教育', office: '办公' }
      return map[domain] || domain || ''
    },
    async onSelectionChange(ids) {
      const selectedDocs = this.allDocs
        .filter(d => ids.includes(d.id))
        .map(d => ({ id: d.id, name: d.name }))
      this.$emit('documents-change', selectedDocs)
      if (!this.conversation?.id) return
      try {
        await updateConversationKb(this.conversation.id, {
          kb_document_ids: ids,
        })
      } catch {
        // ignore
      }
    },
    async onDomainChange(domain) {
      if (!this.conversation?.id) return
      try {
        await updateConversationKb(this.conversation.id, {
          kb_domain: domain || null,
        })
      } catch {
        // ignore
      }
    },
  },
}
</script>

<style scoped>
.kb-doc-selector {
  display: inline-flex;
  align-items: center;
}
.kb-active {
  color: #409eff !important;
}
.kb-dialog-body {
  min-height: 200px;
}
.kb-filter-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.kb-filter-row .el-select {
  width: 140px;
  flex-shrink: 0;
}
.kb-domain-filter {
  margin-bottom: 12px;
  padding: 10px 12px;
  background: #f5f7fa;
  border-radius: 6px;
}
.kb-domain-label {
  font-size: 12px;
  color: #909399;
  display: block;
  margin-bottom: 6px;
}
.kb-doc-list {
  max-height: 280px;
  overflow-y: auto;
}
.kb-empty {
  text-align: center;
  padding: 32px 16px;
  color: #c0c4cc;
}
.kb-empty i {
  font-size: 32px;
  display: block;
  margin-bottom: 8px;
}
.kb-doc-item {
  padding: 6px 0;
  border-bottom: 1px solid #f5f7fa;
}
.doc-name {
  margin: 0 8px;
  font-size: 13px;
}
.doc-domain-tag {
  margin-right: 4px;
}
</style>
