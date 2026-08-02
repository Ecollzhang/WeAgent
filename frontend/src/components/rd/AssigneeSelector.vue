<template>
  <div class="assignee-selector">
    <!-- Selected Assignees -->
    <div class="selected-assignees">
      <span
        v-for="(assignee, index) in localAssignees"
        :key="assignee.user_id"
        class="assignee-chip"
      >
        <el-avatar
          :size="24"
          :src="getDeveloperAvatar(assignee.user_id)"
          :style="{ backgroundColor: avatarColor(getDeveloperName(assignee.user_id)) }"
          class="chip-avatar"
        >
          {{ avatarInitials(getDeveloperName(assignee.user_id)) }}
        </el-avatar>
        <span class="chip-name">{{ getDeveloperName(assignee.user_id) }}</span>
        <span class="chip-role" :style="{ backgroundColor: roleColor(assignee.role) }">
          {{ roleLabel(assignee.role) }}
        </span>
        <i
          class="el-icon-close chip-remove"
          @click="removeAssignee(index)"
        ></i>
      </span>
      <el-popover
        v-model="pickerVisible"
        placement="bottom-start"
        width="280"
        trigger="click"
        :visible-arrow="false"
      >
        <div class="picker-header">
          <span class="picker-title">选择开发人员</span>
        </div>
        <div class="picker-search">
          <el-input
            v-model="searchKeyword"
            size="small"
            placeholder="搜索人员..."
            prefix-icon="el-icon-search"
            clearable
          />
        </div>
        <div class="picker-role-select">
          <span class="picker-label">角色：</span>
          <el-radio-group v-model="selectedRole" size="small">
            <el-radio-button
              v-for="role in availableRoles"
              :key="role.value"
              :label="role.value"
            >{{ role.label }}</el-radio-button>
          </el-radio-group>
        </div>
        <div class="picker-list">
          <div
            v-for="dev in filteredDevelopers"
            :key="dev.id"
            class="picker-item"
            :class="{ disabled: isAssigned(dev.id) }"
            @click="addAssignee(dev)"
          >
            <el-avatar
              :size="30"
              :src="dev.avatar"
              :style="{ backgroundColor: avatarColor(dev.name) }"
            >
              {{ avatarInitials(dev.name) }}
            </el-avatar>
            <div class="picker-item-info">
              <span class="picker-item-name">{{ dev.name }}</span>
              <span class="picker-item-role">{{ dev.role || '开发' }}</span>
            </div>
            <i v-if="isAssigned(dev.id)" class="el-icon-check picker-check"></i>
          </div>
          <div v-if="filteredDevelopers.length === 0" class="picker-empty">
            暂无可选人员
          </div>
        </div>
        <span slot="reference" class="add-btn">
          <i class="el-icon-plus"></i> 添加
        </span>
      </el-popover>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AssigneeSelector',
  props: {
    value: {
      type: Array,
      default: () => [],
    },
    developers: {
      type: Array,
      default: () => [],
    },
    roleLabels: {
      type: Object,
      default: () => ({
        primary: '主开发',
        reviewer: '审查',
        tester: '测试',
      }),
    },
  },
  data() {
    return {
      localAssignees: [],
      pickerVisible: false,
      searchKeyword: '',
      selectedRole: 'primary',
    }
  },
  computed: {
    availableRoles() {
      return [
        { value: 'primary', label: this.roleLabels.primary || '主开发' },
        { value: 'reviewer', label: this.roleLabels.reviewer || '审查' },
        { value: 'tester', label: this.roleLabels.tester || '测试' },
      ]
    },
    filteredDevelopers() {
      if (!this.searchKeyword) {
        return this.developers || []
      }
      const keyword = this.searchKeyword.toLowerCase()
      return (this.developers || []).filter(
        dev =>
          dev.name.toLowerCase().includes(keyword) ||
          (dev.role && dev.role.toLowerCase().includes(keyword))
      )
    },
  },
  watch: {
    value: {
      immediate: true,
      handler(val) {
        this.localAssignees = (val || []).map(a => ({ ...a }))
      },
    },
  },
  methods: {
    avatarInitials(name) {
      if (!name) return '?'
      const parts = name.trim().split(/\s+/)
      if (parts.length >= 2) {
        return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
      }
      return name.slice(0, 2).toUpperCase()
    },
    avatarColor(name) {
      const colors = [
        '#409eff', '#67c23a', '#e6a23c', '#f56c6c',
        '#909399', '#b37feb', '#5cdbd3', '#ff85c0',
      ]
      if (!name) return colors[0]
      let hash = 0
      for (let i = 0; i < name.length; i++) {
        hash = name.charCodeAt(i) + ((hash << 5) - hash)
      }
      return colors[Math.abs(hash) % colors.length]
    },
    roleLabel(role) {
      return this.roleLabels[role] || role || '未知'
    },
    roleColor(role) {
      const colors = {
        primary: '#409eff',
        reviewer: '#e6a23c',
        tester: '#67c23a',
      }
      return colors[role] || '#909399'
    },
    isAssigned(userId) {
      return this.localAssignees.some(a => a.user_id === userId)
    },
    getDeveloperName(userId) {
      const dev = (this.developers || []).find(d => d.id === userId)
      return dev ? dev.name : userId
    },
    getDeveloperAvatar(userId) {
      const dev = (this.developers || []).find(d => d.id === userId)
      return dev ? dev.avatar : ''
    },
    addAssignee(dev) {
      if (this.isAssigned(dev.id)) return
      this.localAssignees.push({
        user_id: dev.id,
        role: this.selectedRole,
      })
      this.emitInput()
      this.searchKeyword = ''
    },
    removeAssignee(index) {
      this.localAssignees.splice(index, 1)
      this.emitInput()
    },
    emitInput() {
      this.$emit('input', this.localAssignees.map(a => ({ ...a })))
    },
  },
}
</script>

<style scoped>
.assignee-selector {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}

.selected-assignees {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.assignee-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px 4px 4px;
  background: #f0f2f5;
  border-radius: 20px;
  border: 1px solid #e4e7ed;
  font-size: 13px;
  transition: all 0.2s;
}

.assignee-chip:hover {
  border-color: #c0c4cc;
  background: #e8eaef;
}

.chip-avatar {
  flex-shrink: 0;
}

.chip-name {
  color: #303133;
  font-weight: 500;
  white-space: nowrap;
}

.chip-role {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 8px;
  font-size: 11px;
  color: #fff;
  white-space: nowrap;
  line-height: 1.4;
}

.chip-remove {
  font-size: 12px;
  color: #c0c4cc;
  cursor: pointer;
  transition: color 0.2s;
  margin-left: 2px;
}

.chip-remove:hover {
  color: #f56c6c;
}

.add-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  border: 1px dashed #dcdfe6;
  border-radius: 20px;
  font-size: 13px;
  color: #909399;
  cursor: pointer;
  transition: all 0.2s;
}

.add-btn:hover {
  border-color: #4080ff;
  color: #4080ff;
  background: #f0f5ff;
}

.picker-header {
  padding-bottom: 8px;
  margin-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}

.picker-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.picker-search {
  margin-bottom: 10px;
}

.picker-role-select {
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.picker-label {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
}

.picker-list {
  max-height: 200px;
  overflow-y: auto;
}

.picker-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.picker-item:hover:not(.disabled) {
  background: #f0f5ff;
}

.picker-item.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.picker-item-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.picker-item-name {
  font-size: 13px;
  color: #303133;
  font-weight: 500;
}

.picker-item-role {
  font-size: 11px;
  color: #909399;
}

.picker-check {
  color: #67c23a;
  font-size: 14px;
}

.picker-empty {
  text-align: center;
  padding: 20px 0;
  font-size: 13px;
  color: #c0c4cc;
}
</style>
