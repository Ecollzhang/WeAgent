<template>
  <el-dialog
    title="迁移文件"
    :visible.sync="innerVisible"
    width="760px"
    top="6vh"
    custom-class="file-migration-dialog"
    @close="handleClose"
  >
    <div class="migration-body" v-loading="treeLoading || previewLoading || migrateLoading">
      <div class="migration-section">
        <div class="section-title">1. 选择目标会话</div>
        <el-select
          v-model="targetConversationId"
          filterable
          placeholder="请选择目标会话"
          style="width: 100%"
          @change="resetPreview"
        >
          <el-option
            v-for="item in targetConversations"
            :key="item.id"
            :label="buildConversationLabel(item)"
            :value="item.id"
          />
        </el-select>
      </div>

      <div class="migration-section">
        <div class="section-title">2. 选择文件</div>
        <div class="section-tip">默认只展示 `/workspace/agents` 下的工作区文件，请勾选要迁移的目录或文件。</div>
        <el-tree
          ref="tree"
          :data="fileTreeData"
          :props="treeProps"
          show-checkbox
          node-key="path"
          default-expand-all
          class="migration-tree"
        >
          <span slot-scope="{ node, data }" class="migration-tree-node">
            <i :class="data.type === 'directory' ? 'el-icon-folder' : 'el-icon-document'" />
            <span>{{ node.label }}</span>
            <span v-if="data.size" class="node-size">{{ formatFileSize(data.size) }}</span>
          </span>
        </el-tree>
      </div>

      <div class="migration-section">
        <div class="section-title">3. 确认迁移</div>
        <div class="migration-row">
          <el-switch
            v-model="overwrite"
            active-text="覆盖已有文件"
            inactive-text="跳过已有文件"
          />
          <el-button size="mini" @click="handlePreview">预览映射</el-button>
        </div>

        <div v-if="previewData" class="preview-box">
          <div class="preview-meta">
            <span>候选文件：{{ previewData.total_candidates || 0 }}</span>
            <span>冲突预估：{{ (previewData.conflicts || []).length }}</span>
            <span>跳过项：{{ (previewData.skipped || []).length }}</span>
          </div>

          <div class="preview-subtitle">路径映射</div>
          <div class="mapping-list" v-if="mappingEntries.length">
            <div v-for="item in mappingEntries" :key="item.source" class="mapping-item">
              <div class="mapping-source">{{ item.source }}</div>
              <i class="el-icon-right mapping-arrow"></i>
              <div class="mapping-target">{{ item.target }}</div>
              <el-tag size="mini" :type="item.fallback ? 'warning' : 'success'">
                {{ item.fallback ? 'fallback' : 'auto' }}
              </el-tag>
            </div>
          </div>
          <div v-else class="preview-empty">暂无可展示的路径映射</div>

          <div class="preview-subtitle">冲突预估</div>
          <div v-if="(previewData.conflicts || []).length" class="conflict-list">
            <div
              v-for="item in previewData.conflicts.slice(0, 8)"
              :key="`${item.source_path}-${item.target_path}`"
              class="conflict-item"
            >
              <div>{{ item.source_path }}</div>
              <div class="conflict-target">{{ item.target_path }}</div>
            </div>
            <div v-if="previewData.conflicts.length > 8" class="preview-more">
              还有 {{ previewData.conflicts.length - 8 }} 项冲突未展开
            </div>
          </div>
          <div v-else class="preview-empty">没有发现目标侧冲突</div>

          <div class="preview-note">
            本轮只复制文件，不复制旧聊天记录和旧 artifact 卡片。
          </div>
        </div>
      </div>
    </div>

    <span slot="footer" class="dialog-footer">
      <el-button @click="innerVisible = false">取消</el-button>
      <el-button type="primary" :disabled="!previewData" :loading="migrateLoading" @click="handleMigrate">
        执行迁移
      </el-button>
    </span>
  </el-dialog>
</template>

<script>
import { getFileTree, previewMigration, migrateFiles } from '@/api/sandbox'

export default {
  name: 'FileMigrationDialog',
  props: {
    visible: { type: Boolean, default: false },
    sourceConversation: { type: Object, default: null },
    conversations: { type: Array, default: () => [] },
  },
  data() {
    return {
      innerVisible: false,
      targetConversationId: '',
      fileTreeData: [],
      treeLoading: false,
      previewLoading: false,
      migrateLoading: false,
      previewData: null,
      overwrite: false,
      treeProps: { children: 'children', label: 'name' },
    }
  },
  computed: {
    sourceConversationId() {
      return this.sourceConversation?.id || ''
    },
    sourceSessionId() {
      return this.sourceConversation?.sandbox_session_id || this.sourceConversation?.id || ''
    },
    targetConversations() {
      return (this.conversations || []).filter(item => item.id !== this.sourceConversationId)
    },
    mappingEntries() {
      const mapping = this.previewData?.path_mapping || {}
      return Object.keys(mapping).map(source => ({
        source,
        target: mapping[source],
        fallback: String(mapping[source] || '').includes('/migrated_from_'),
      }))
    },
  },
  watch: {
    visible: {
      immediate: true,
      handler(value) {
        this.innerVisible = value
        if (value) this.initialize()
      },
    },
    innerVisible(value) {
      this.$emit('update:visible', value)
    },
  },
  methods: {
    async initialize() {
      this.targetConversationId = ''
      this.previewData = null
      this.overwrite = false
      this.fileTreeData = []
      await this.loadTree()
      this.$nextTick(() => {
        if (this.$refs.tree) this.$refs.tree.setCheckedKeys([])
      })
    },
    async loadTree() {
      if (!this.sourceSessionId) return
      this.treeLoading = true
      try {
        const res = await getFileTree(this.sourceSessionId, '/workspace/agents')
        this.fileTreeData = res?.data?.tree?.children || []
      } catch (e) {
        this.$message.error(e?.message || '加载文件树失败')
      } finally {
        this.treeLoading = false
      }
    },
    buildConversationLabel(item) {
      const participants = item?.participants_info || []
      const agentNames = participants
        .filter(p => p.participant_type === 'agent')
        .map(p => p.name)
        .join(' / ')
      return agentNames ? `${item.title} (${agentNames})` : item.title
    },
    getSelectedPaths() {
      const tree = this.$refs.tree
      if (!tree) return []
      return Array.from(new Set((tree.getCheckedKeys() || []).filter(Boolean)))
    },
    resetPreview() {
      this.previewData = null
    },
    async handlePreview() {
      if (!this.targetConversationId) {
        this.$message.warning('请先选择目标会话')
        return
      }
      const selectedPaths = this.getSelectedPaths()
      if (!selectedPaths.length) {
        this.$message.warning('请至少勾选一个目录或文件')
        return
      }
      this.previewLoading = true
      try {
        const previewRes = await previewMigration(
          this.sourceConversationId,
          this.targetConversationId,
          '/workspace/agents',
          false,
          selectedPaths,
        )
        this.previewData = {
          ...(previewRes?.data || {}),
          selected_paths: selectedPaths,
        }
      } catch (e) {
        this.$message.error(e?.message || '预览映射失败')
      } finally {
        this.previewLoading = false
      }
    },
    async handleMigrate() {
      if (!this.previewData) {
        this.$message.warning('请先预览映射')
        return
      }
      this.migrateLoading = true
      try {
        const payload = {
          target_conversation_id: this.targetConversationId,
          paths: this.previewData.selected_paths || [],
          path_mapping: this.previewData.path_mapping || {},
          overwrite: this.overwrite,
          include_hidden: false,
          root: '/workspace/agents',
        }
        const res = await migrateFiles(this.sourceConversationId, payload)
        const result = res?.data || {}
        this.$message.success(
          `迁移完成：成功 ${result.migrated || 0}，跳过 ${result.skipped || 0}，失败 ${(result.errors || []).length}`
        )
        this.$emit('refresh-conversations')
        this.$emit('open-target', this.targetConversationId)
        this.innerVisible = false
      } catch (e) {
        this.$message.error(e?.message || '执行迁移失败')
      } finally {
        this.migrateLoading = false
      }
    },
    handleClose() {
      this.targetConversationId = ''
      this.previewData = null
    },
    formatFileSize(size) {
      const value = Number(size || 0)
      if (!value) return ''
      if (value < 1024) return `${value} B`
      if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
      return `${(value / (1024 * 1024)).toFixed(1)} MB`
    },
  },
}
</script>

<style scoped>
.migration-body {
  min-height: 360px;
}

.migration-section + .migration-section {
  margin-top: 18px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 10px;
}

.section-tip,
.preview-note {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 10px;
}

.migration-tree {
  max-height: 260px;
  overflow-y: auto;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 8px;
}

.migration-tree-node {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.node-size {
  color: #94a3b8;
  font-size: 12px;
}

.migration-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.preview-box {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px;
  background: #fafcff;
}

.preview-meta {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  font-size: 12px;
  color: #475569;
  margin-bottom: 12px;
}

.preview-subtitle {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
  margin: 10px 0 8px;
}

.mapping-list,
.conflict-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mapping-item,
.conflict-item {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 8px 10px;
  background: #fff;
}

.mapping-source,
.mapping-target,
.conflict-target {
  font-size: 12px;
  color: #475569;
  word-break: break-all;
}

.mapping-arrow {
  color: #94a3b8;
  margin: 4px 0;
}

.preview-empty,
.preview-more {
  font-size: 12px;
  color: #94a3b8;
}
</style>
