<template>
  <div class="activity-timeline">
    <div v-if="displayedActivities.length === 0" class="timeline-empty">
      <i class="el-icon-time"></i>
      <p>暂无活动记录</p>
    </div>

    <div class="timeline-scroll">
      <!-- Timeline Entries -->
      <div
        v-for="(activity, index) in displayedActivities"
        :key="activity.id"
        class="timeline-entry"
        :class="{ 'is-last': index === displayedActivities.length - 1 }"
      >
        <!-- Dot -->
        <div class="timeline-dot-wrapper">
          <span class="timeline-dot" :style="{ backgroundColor: dotColor(activity.action) }">
            <i :class="dotIcon(activity.action)"></i>
          </span>
          <span v-if="index < displayedActivities.length - 1" class="timeline-line"></span>
        </div>

        <!-- Content -->
        <div class="timeline-content">
          <div class="timeline-header">
            <span class="timeline-actor">
              <el-avatar
                :size="20"
                :style="{ backgroundColor: avatarColor(getActorName(getActorId(activity))) }"
                class="actor-avatar"
              >
                {{ avatarInitials(getActorName(getActorId(activity))) }}
              </el-avatar>
              {{ getActorName(getActorId(activity)) }}
            </span>
            <span class="timeline-time">{{ formatTime(activity.created_at) }}</span>
          </div>
          <div class="timeline-body">
            <span class="action-description">{{ getActionDescription(activity) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Load More -->
    <div v-if="hasMore" class="load-more-wrapper">
      <el-button
        type="text"
        :loading="loadingMore"
        @click="$emit('load-more')"
      >
        <i class="el-icon-bottom"></i> 加载更多
      </el-button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ActivityTimeline',
  props: {
    activities: {
      type: Array,
      default: () => [],
    },
    developers: {
      type: Array,
      default: () => [],
    },
    maxVisible: {
      type: Number,
      default: 0,
    },
    totalCount: {
      type: Number,
      default: 0,
    },
    loadingMore: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    displayedActivities() {
      const list = this.activities || []
      if (this.maxVisible > 0 && list.length > this.maxVisible) {
        return list.slice(0, this.maxVisible)
      }
      return list
    },
    hasMore() {
      if (this.totalCount > 0) {
        return this.displayedActivities.length < this.totalCount
      }
      if (this.maxVisible > 0) {
        return (this.activities || []).length > this.maxVisible
      }
      return false
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
    getActorId(activity) {
      return activity.actor_id || activity.user_id || ''
    },
    getActorName(actorId) {
      if (!actorId) return '系统'
      const dev = (this.developers || []).find(d => d.id === actorId)
      return dev ? dev.name : actorId
    },
    dotColor(action) {
      const colors = {
        created: '#67c23a',
        status_changed: '#409eff',
        assigned: '#e6a23c',
        commented: '#b37feb',
        updated: '#909399',
        deleted: '#f56c6c',
      }
      return colors[action] || '#c0c4cc'
    },
    dotIcon(action) {
      const icons = {
        created: 'el-icon-circle-plus',
        status_changed: 'el-icon-refresh',
        assigned: 'el-icon-user',
        commented: 'el-icon-chat-line-round',
        updated: 'el-icon-edit',
        deleted: 'el-icon-delete',
      }
      return icons[action] || 'el-icon-more'
    },
    formatTime(dateStr) {
      if (!dateStr) return ''
      const date = new Date(dateStr)
      const now = new Date()
      const diff = Math.floor((now.getTime() - date.getTime()) / 1000)
      if (diff < 60) return '刚刚'
      if (diff < 3600) return Math.floor(diff / 60) + ' 分钟前'
      if (diff < 86400) return Math.floor(diff / 3600) + ' 小时前'
      if (diff < 172800) return '昨天 ' + this.padTime(date)
      if (date.getFullYear() === now.getFullYear()) {
        return this.padDate(date)
      }
      return date.getFullYear() + '/' + this.padDate(date)
    },
    padTime(date) {
      const h = String(date.getHours()).padStart(2, '0')
      const m = String(date.getMinutes()).padStart(2, '0')
      return h + ':' + m
    },
    padDate(date) {
      const M = String(date.getMonth() + 1).padStart(2, '0')
      const d = String(date.getDate()).padStart(2, '0')
      return M + '/' + d + ' ' + this.padTime(date)
    },
    getActionDescription(activity) {
      const action = activity.action
      const actor = this.getActorName(this.getActorId(activity))
      const newVal = activity.new_value || {}
      const oldVal = activity.old_value || {}
      // 辅助：从 value 中提取实际字符串值（后端发送的是 JSON 对象如 {status: 'open'}）
      const val = (obj, key) => {
        if (obj == null) return ''
        if (typeof obj === 'string') return obj
        if (key && obj[key] !== undefined) return String(obj[key])
        // 取第一个非空字符串值
        const keys = Object.keys(obj)
        for (const k of keys) {
          const v = obj[k]
          if (v != null && typeof v !== 'object') return String(v)
        }
        return ''
      }

      switch (action) {
        case 'created':
          const typeMap = {
            requirement: '需求',
            bug: '缺陷',
            task: '任务',
            project: '项目',
          }
          const itemType = typeMap[activity.item_type || activity.target_type] || '条目'
          const title = val(newVal, 'title')
          return `${actor} 创建了此${itemType}${title ? '：' + title : ''}`
        case 'status_changed':
          const oldStatus = this.formatStatus(val(oldVal, 'status'))
          const newStatus = this.formatStatus(val(newVal, 'status'))
          return `${actor} 将状态从 ${oldStatus} 改为 ${newStatus}`
        case 'assigned':
          const targetUserId = val(newVal, 'user_id')
          const targetUser = targetUserId ? this.getActorName(targetUserId) : ''
          const role = val(newVal, 'role') || '成员'
          return `${actor} 将 ${targetUser} 添加为 ${this.formatRole(role)}`
        case 'commented':
          return `${actor} 发表了评论`
        case 'updated':
          const fieldName = this.formatField(activity.extra_info)
          const oldV = val(oldVal)
          const newV = val(newVal)
          if (fieldName && oldV && newV) {
            return `${actor} 更新了${fieldName}：从 "${oldV}" 改为 "${newV}"`
          }
          if (fieldName) {
            return `${actor} 更新了${fieldName}`
          }
          return `${actor} 更新了此条目`
        case 'deleted':
          return `${actor} 删除了此条目`
        default:
          return `${actor} 执行了操作`
      }
    },
    formatStatus(status) {
      if (!status) return '未知'
      const labels = {
        draft: '草稿',
        open: '待处理',
        in_progress: '进行中',
        in_review: '审查中',
        testing: '测试中',
        done: '已完成',
        closed: '已关闭',
        rejected: '已拒绝',
        resolved: '已解决',
        reopened: '重新打开',
      }
      return labels[status] || status
    },
    formatRole(role) {
      const labels = {
        primary: '主开发',
        reviewer: '审查',
        tester: '测试',
        assignee: '负责人',
      }
      return labels[role] || role
    },
    formatField(field) {
      if (!field) return ''
      const fieldLabels = {
        title: '标题',
        description: '描述',
        priority: '优先级',
        severity: '严重程度',
        status: '状态',
        assignee: '负责人',
        due_date: '截止日期',
        sprint: '迭代',
        labels: '标签',
        parent: '父需求',
        est_hours: '预估工时',
      }
      return fieldLabels[field] || field
    },
  },
}
</script>

<style scoped>
.activity-timeline {
  width: 100%;
}

.timeline-empty {
  text-align: center;
  padding: 32px 20px;
  color: #c0c4cc;
}

.timeline-empty i {
  font-size: 36px;
  display: block;
  margin-bottom: 8px;
}

.timeline-empty p {
  font-size: 13px;
  margin: 0;
}

.timeline-scroll {
  max-height: 420px;
  overflow-y: auto;
  padding-right: 4px;
}

.timeline-scroll::-webkit-scrollbar {
  width: 2px;
}

.timeline-scroll::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.10);
  border-radius: 1px;
}

.timeline-entry {
  display: flex;
  gap: 12px;
  padding-bottom: 2px;
}

.timeline-entry.is-last {
  padding-bottom: 0;
}

.timeline-dot-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
  width: 28px;
}

.timeline-dot {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  color: #fff;
  font-size: 13px;
  flex-shrink: 0;
  z-index: 1;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
}

.timeline-line {
  width: 2px;
  flex: 1;
  min-height: 18px;
  background: #e4e7ed;
  margin: 4px 0;
}

.timeline-content {
  flex: 1;
  min-width: 0;
  padding-bottom: 16px;
}

.timeline-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
  gap: 8px;
}

.timeline-actor {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

.actor-avatar {
  flex-shrink: 0;
}

.timeline-time {
  font-size: 12px;
  color: #c0c4cc;
  white-space: nowrap;
}

.timeline-body {
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
}

.action-description {
  color: #606266;
}

.load-more-wrapper {
  text-align: center;
  padding: 12px 0 4px;
  border-top: 1px solid #f2f3f5;
  margin-top: 4px;
}

.load-more-wrapper .el-button {
  font-size: 13px;
}
</style>
