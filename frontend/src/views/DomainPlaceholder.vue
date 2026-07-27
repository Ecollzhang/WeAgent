<template>
  <div class="domain-placeholder-page">
    <AppSidebar />
    <div class="placeholder-main">
      <div class="placeholder-card">
        <i :class="iconClass"></i>
        <h3>{{ title }}</h3>
        <p>该功能模块正在开发中，敬请期待。</p>
        <el-button type="primary" size="small" @click="$router.push('/dashboard')">
          返回聊天
        </el-button>
      </div>
    </div>
  </div>
</template>

<script>
import AppSidebar from '../components/Sidebar/index.vue'

const META = {
  courses: { title: '课程管理', icon: 'el-icon-document' },
  assignments: { title: '作业系统', icon: 'el-icon-edit-outline' },
  resources: { title: '教学资源', icon: 'el-icon-folder-opened' },
  students: { title: '学生画像', icon: 'el-icon-user' },
  grades: { title: '成绩管理', icon: 'el-icon-data-line' },
  documents: { title: '公文管理', icon: 'el-icon-document' },
  meetings: { title: '会议管理', icon: 'el-icon-date' },
  approvals: { title: '审批流程', icon: 'el-icon-check' },
  reports: { title: '报表服务', icon: 'el-icon-data-line' },
  schedules: { title: '日程管理', icon: 'el-icon-time' },
}

export default {
  name: 'DomainPlaceholder',
  components: { AppSidebar },
  computed: {
    pageKey() {
      return this.$route.name || ''
    },
    meta() {
      return META[this.pageKey] || { title: '功能模块', icon: 'el-icon-menu' }
    },
    title() {
      return this.meta.title
    },
    iconClass() {
      return this.meta.icon
    },
  },
}
</script>

<style scoped>
.domain-placeholder-page {
  display: flex;
  gap: 12px;
  padding: 12px;
  height: 100vh;
  background: linear-gradient(135deg, #e8f0ff 0%, #f0f5ff 50%, #f5f7fa 100%);
  overflow: hidden;
}

.placeholder-main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.placeholder-card {
  text-align: center;
  padding: 60px 80px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}

.placeholder-card i {
  font-size: 56px;
  color: #4080ff;
  margin-bottom: 18px;
  display: block;
}

.placeholder-card h3 {
  margin: 0 0 10px;
  font-size: 20px;
  color: #1e293b;
}

.placeholder-card p {
  margin: 0 0 22px;
  font-size: 14px;
  color: #94a3b8;
}
</style>
