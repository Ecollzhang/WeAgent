<template>
  <div class="project-file-tree">
    <div class="file-tree-header" v-if="showHeader">
      <span class="header-title">
        <i class="el-icon-folder-opened"></i> 项目文件
        <span class="file-count">({{ files.length }})</span>
      </span>
    </div>

    <div v-if="files.length === 0" class="empty-files">
      <i class="el-icon-document"></i>
      <p>暂无文件，在对话中让 Agent 生成代码后会自动存入项目</p>
    </div>

    <div v-else class="file-list">
      <div
        v-for="file in sortedFiles"
        :key="file.id"
        class="file-item"
        :class="{ active: activeFileId === file.id }"
        @click="$emit('select', file)"
      >
        <span class="file-icon">
          <i :class="fileIcon(file)"></i>
        </span>
        <span class="file-name" :title="file.file_path">{{ file.file_name }}</span>
        <span class="file-type-badge">{{ file.file_type || '-' }}</span>
        <span class="file-size" v-if="file.size">{{ formatSize(file.size) }}</span>
        <el-button
          v-if="showDelete"
 class="file-delete-btn"
          type="text"
          size="mini"
          icon="el-icon-delete"
          @click.stop="$emit('delete', file)"
        />
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ProjectFileTree',
  props: {
    files: { type: Array, default: () => [] },
    activeFileId: { type: String, default: '' },
    showHeader: { type: Boolean, default: true },
    showDelete: { type: Boolean, default: false },
  },
  computed: {
    sortedFiles() {
      return [...this.files].sort((a, b) => a.file_path.localeCompare(b.file_path))
    },
  },
  methods: {
    fileIcon(file) {
      const type = (file.file_type || file.file_name || '').toLowerCase()
      if (/\.(vue|jsx|tsx)$/.test(type)) return 'el-icon-document'
      if (/\.(py)$/.test(type)) return 'el-icon-document'
      if (/\.(sql)$/.test(type)) return 'el-icon-s-data'
      if (/\.(json|ya?ml|toml)$/.test(type)) return 'el-icon-s-tools'
      if (/\.(md|txt)$/.test(type)) return 'el-icon-document'
      if (/\.(css|scss|less)$/.test(type)) return 'el-icon-document'
      return 'el-icon-document'
    },
    formatSize(bytes) {
      if (bytes < 1024) return bytes + ' B'
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
      return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    },
  },
}
</script>

<style scoped>
.project-file-tree {
  background: #fff;
  border-radius: 8px;
}
.file-tree-header {
  padding: 12px 16px 8px;
  border-bottom: 1px solid #ebeef5;
}
.header-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}
.file-count {
  font-weight: 400;
  font-size: 12px;
  color: #909399;
}
.empty-files {
  padding: 32px 16px;
  text-align: center;
  color: #c0c4cc;
}
.empty-files i {
  font-size: 32px;
  display: block;
  margin-bottom: 8px;
}
.empty-files p {
  font-size: 13px;
  color: #909399;
  margin: 0;
}
.file-list {
  padding: 4px 0;
}
.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  cursor: pointer;
  transition: background 0.15s;
  font-size: 13px;
}
.file-item:hover {
  background: #f5f7fa;
}
.file-item.active {
  background: #ecf5ff;
}
.file-icon {
  color: #409eff;
  font-size: 16px;
  flex-shrink: 0;
}
.file-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #303133;
}
.file-type-badge {
  font-size: 11px;
  color: #909399;
  background: #f0f2f5;
  padding: 1px 6px;
  border-radius: 3px;
  flex-shrink: 0;
}
.file-size {
  font-size: 11px;
  color: #c0c4cc;
  flex-shrink: 0;
}
.file-delete-btn {
  padding: 0;
  color: #f56c6c;
  flex-shrink: 0;
}
</style>
