<template>
  <div class="sidebar" :class="{ collapsed }">
    <div class="sidebar-header">
      <div class="logo">{{ collapsed ? 'W' : 'WeAgent' }}</div>
    </div>

    <!-- 领域 + 工作空间切换 -->
    <WorkspaceSwitcher v-if="!collapsed" />

    <div class="sidebar-nav">
      <!-- 公共功能 -->
      <div v-if="!collapsed" class="nav-section-label">公共</div>
      <router-link
        v-for="item in commonNavItems"
        :key="item.key"
        :to="item.route"
        class="nav-item"
        :class="{ active: $route.path.startsWith(item.activePath) }"
        :title="item.label"
      >
        <i v-if="item.iconClass" :class="item.iconClass"></i>
        <span v-else-if="item.iconSvg" class="toolset-wrench-icon"></span>
        <span v-show="!collapsed">{{ item.label }}</span>
      </router-link>

      <!-- 分隔线 -->
      <div class="nav-divider"></div>

      <!-- 领域功能 -->
      <div v-if="!collapsed" class="nav-section-label">{{ domainSectionLabel }}</div>
      <router-link
        v-for="item in domainNavItems"
        :key="item.key"
        :to="item.route"
        class="nav-item"
        :class="{ active: isNavActive(item) }"
        :title="item.label"
      >
        <i v-if="item.iconClass" :class="item.iconClass"></i>
        <span v-else-if="item.iconSvg" class="toolset-wrench-icon"></span>
        <span v-show="!collapsed">{{ item.label }}</span>
      </router-link>
    </div>

    <div class="sidebar-footer">
      <div class="collapse-toggle" @click="toggleCollapse" :title="collapsed ? '展开侧边栏' : '收起侧边栏'">
        <span class="toggle-btn">
          <svg viewBox="0 0 1024 1024" width="16" height="16" :class="{ flipped: collapsed }">
            <path d="M960 192h-64v704h64V192z m-579.2 32L109.248 495.552 64 540.8l45.248 45.248 271.552 271.488 45.248-45.248L189.696 576H704V512H183.296l242.752-242.752L380.8 224z" fill="currentColor"/>
          </svg>
        </span>
      </div>
      <div class="user-info" @click="handleLogout">
        <div class="user-avatar">
          <img v-if="userAvatar" :src="userAvatar" class="avatar-img" />
          <i v-else class="el-icon-user-solid"></i>
        </div>
        <span v-show="!collapsed" class="username">{{ currentUser?.username || '用户' }}</span>
      </div>
    </div>
  </div>
</template>

<script>
import WorkspaceSwitcher from '../WorkspaceSwitcher/index.vue'
import { checkVisible } from '../../store/modules/grayscale'

// 公共导航项（所有领域都显示，受灰度控制）
const COMMON_NAV = [
  { key: 'ui.sidebar.agents', label: '我的Agent', route: '/agents', activePath: '/agents', iconClass: 'el-icon-monitor' },
  { key: 'ui.sidebar.tools', label: '工具集', route: '/tools', activePath: '/tools', iconSvg: true },
  { key: 'ui.sidebar.favorites', label: '我的收藏', route: '/favorites', activePath: '/favorites', iconClass: 'el-icon-collection-tag' },
  { key: 'ui.sidebar.knowledge', label: '知识库', route: '/knowledge-base', activePath: '/knowledge-base', iconClass: 'el-icon-files' },
  { key: 'chat', label: '聊天', route: '/dashboard', activePath: '/dashboard', iconClass: 'el-icon-chat-dot-round' },
  { key: 'settings', label: '设置', route: '/settings', activePath: '/settings', iconClass: 'el-icon-setting' },
]

// 领域专属导航项（按 grayscale config_key 控制可见性）
const DOMAIN_NAV = {
  rd: [
    { key: 'ui.sidebar.projects', label: '项目管理', route: '/projects', activePath: '/projects', iconClass: 'el-icon-s-grid' },
    { key: 'ui.sidebar.repos', label: '代码仓库', route: '/repos', activePath: '/repos', iconClass: 'el-icon-folder-opened' },
    { key: 'ui.sidebar.reviews', label: '代码审查', route: '/reviews', activePath: '/reviews', iconClass: 'el-icon-view' },
    { key: 'ui.sidebar.builds', label: '构建管理', route: '/builds', activePath: '/builds', iconClass: 'el-icon-s-tools' },
  ],
  edu: [],
  office: [
    { key: 'ui.sidebar.organization', label: '组织协同', route: '/organization', activePath: '/organization', iconClass: 'el-icon-s-custom' },
    { key: 'ui.sidebar.meetings', label: '\u4f1a\u8bae\u4efb\u52a1', route: '/meetings', activePath: '/meetings', iconClass: 'el-icon-date' },
    { key: 'ui.sidebar.documents', label: '公文审批', route: '/documents', activePath: '/documents', iconClass: 'el-icon-document' },
  ],
}

export default {
  name: 'AppSidebar',
  components: { WorkspaceSwitcher },
  data() {
    return {
      collapsed: localStorage.getItem('sidebar_collapsed') === '1',
      educationContextHydrating: false,
    }
  },
  watch: {
    activeDomain: {
      immediate: true,
      handler(value) {
        if (value === 'edu') this.hydrateEducationContext()
      },
    },
  },
  computed: {
    currentUser() {
      return this.$store.state.user.user
    },
    userAvatar() {
      return this.currentUser?.avatar || localStorage.getItem('user_avatar') || ''
    },
    activeDomain() {
      return this.$store.getters['workspace/activeDomain']
    },
    activeCourse() {
      return this.$store.getters['education/activeCourse']
    },
    membershipRole() {
      return this.activeCourse && this.activeCourse.membership_role
        ? this.activeCourse.membership_role
        : ''
    },
    activeSubRole() {
      return this.$store.getters['workspace/activeSubRole'] || ''
    },
    educationRole() {
      return this.membershipRole || this.activeSubRole
    },
    domainSectionLabel() {
      if (this.activeDomain !== 'edu') return '领域'
      if (this.educationRole === 'student') return '学习领域'
      if (this.educationRole === 'teacher') return '教师领域'
      return '教育领域'
    },
    commonNavItems() {
      const domain = this.activeDomain || 'rd'
      return COMMON_NAV.filter(item => {
        // 聊天和设置始终显示
        if (item.key === 'chat' || item.key === 'settings') return true
        return checkVisible(this.$store.state.grayscale, domain, item.key)
      })
    },
    domainNavItems() {
      const domain = this.activeDomain || 'rd'
      if (domain === 'edu') return this.educationDomainNavItems
      const raw = DOMAIN_NAV[domain] || []
      const items = raw
      return items.filter(item => {
        return checkVisible(this.$store.state.grayscale, domain, item.key)
      })
    },
    educationDomainNavItems() {
      const course = this.activeCourse
      const courseQuery = course ? { courseId: course.id } : {}
      const teachingRoute = course ? `/education/courses/${course.id}` : '/education'
      const teachingSpace = {
        key: 'ui.sidebar.courses',
        module: 'teaching-space',
        label: '教学空间',
        route: { path: teachingRoute, query: courseQuery },
        activePath: '/education/courses',
        iconClass: 'el-icon-reading',
      }
      const helpCenter = {
        key: 'ui.sidebar.education-help',
        module: 'help',
        label: '帮助中心',
        route: { path: '/education/help', query: courseQuery },
        iconClass: 'el-icon-question',
      }
      if (this.educationRole === 'student') {
        return [
          teachingSpace,
          {
            key: 'ui.sidebar.mock-exams',
            module: 'mock-exams',
            label: '模拟考试',
            route: { path: '/education/student/mock-exams', query: courseQuery },
            iconClass: 'el-icon-document-checked',
          },
          {
            key: 'ui.sidebar.mind-maps',
            module: 'mind-maps',
            label: '课程思维导图',
            route: { path: '/education/student/mind-maps', query: courseQuery },
            iconClass: 'el-icon-share',
          },
          helpCenter,
        ]
      }
      if (this.educationRole === 'teacher') {
        return [
          teachingSpace,
          {
            key: 'ui.sidebar.courseware',
            module: 'courseware',
            label: 'PPT 与课件',
            route: { path: '/education/teacher/courseware', query: courseQuery },
            iconClass: 'el-icon-picture-outline',
          },
          {
            key: 'ui.sidebar.insights',
            module: 'insights',
            label: '学生画像与评估',
            route: { path: '/education/teacher/insights', query: courseQuery },
            iconClass: 'el-icon-pie-chart',
          },
          helpCenter,
        ]
      }
      return [teachingSpace, helpCenter]
    },
  },
  methods: {
    async hydrateEducationContext() {
      if (this.activeCourse || this.educationContextHydrating) return
      this.educationContextHydrating = true
      try {
        const courses = await this.$store.dispatch('education/fetchCourses')
        const requestedRole = this.activeSubRole
        const candidate = requestedRole
          ? courses.find(course => course.membership_role === requestedRole)
          : courses[0]
        if (candidate) await this.$store.dispatch('education/selectCourse', candidate.id)
      } catch (error) {
        // Keep the generic Education entry usable when the account has no course yet.
      } finally {
        this.educationContextHydrating = false
      }
    },
    isNavActive(item) {
      if (item.module) {
        return this.$route.meta && this.$route.meta.educationModule === item.module
      }
      return Boolean(item.activePath && this.$route.path.startsWith(item.activePath))
    },
    toggleCollapse() {
      this.collapsed = !this.collapsed
      localStorage.setItem('sidebar_collapsed', this.collapsed ? '1' : '0')
    },
    handleLogout() {
      this.$confirm('确认退出登录？', '提示', {
        confirmButtonText: '退出',
        cancelButtonText: '取消',
        type: 'warning',
      }).then(() => {
        this.$store.dispatch('user/logout')
        this.$router.push('/login')
      }).catch(() => {})
    },
  },
}
</script>

<style scoped>
.sidebar {
  width: 150px;
  min-width: 150px;
  max-width: 150px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-radius: 12px;
  background: linear-gradient(180deg, #e8f0ff 0%, #f0f5ff 100%);
  transition: width 0.25s ease, min-width 0.25s ease, max-width 0.25s ease;
}

.sidebar.collapsed {
  width: 64px;
  min-width: 64px;
  max-width: 64px;
}

.sidebar-header {
  padding: 24px 20px 16px;
}

.sidebar.collapsed .sidebar-header {
  padding: 24px 12px 16px;
  text-align: center;
}

.logo {
  font-size: 20px;
  font-weight: 700;
  color: #1e293b;
  letter-spacing: -0.5px;
  transition: all 0.25s ease;
}

.sidebar-nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  scrollbar-width: none;
  padding: 8px 12px;
  gap: 2px;
}

.sidebar-nav::-webkit-scrollbar {
  display: none;
}

.sidebar.collapsed .sidebar-nav {
  padding: 8px 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 15px 12px;
  color: #64748b;
  text-decoration: none;
  font-size: 14px;
  border-radius: 8px;
  transition: all 0.2s;
}

.sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 15px 0;
}

.nav-item:hover {
  background: rgba(255,255,255,0.5);
  color: #1e293b;
}

.nav-item.active {
  background: rgba(64,128,255,0.15);
  color: #4080ff;
  font-weight: 600;
}

.nav-section-label {
  font-size: 11px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 8px 12px 4px;
}

.nav-divider {
  height: 1px;
  background: rgba(59,130,246,0.1);
  margin: 4px 8px;
}

.nav-item i {
  font-size: 18px;
  width: 20px;
  text-align: center;
  flex-shrink: 0;
}

.toolset-wrench-icon {
  display: inline-block;
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  background: currentColor;
  -webkit-mask: url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2024%2024'%3E%3Cpath%20fill='none'%20stroke='black'%20stroke-linecap='round'%20stroke-linejoin='round'%20stroke-width='2'%20d='M14.7%206.3a1%201%200%200%200%200%201.4l1.6%201.6a1%201%200%200%200%201.4%200l3.1-3.1a6%206%200%200%201-7.9%207.9l-6.9%206.9a2.1%202.1%200%200%201-3-3l6.9-6.9a6%206%200%200%201%207.9-7.9l-3.1%203.1z'/%3E%3C/svg%3E") center / contain no-repeat;
  mask: url("data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2024%2024'%3E%3Cpath%20fill='none'%20stroke='black'%20stroke-linecap='round'%20stroke-linejoin='round'%20stroke-width='2'%20d='M14.7%206.3a1%201%200%200%200%200%201.4l1.6%201.6a1%201%200%200%200%201.4%200l3.1-3.1a6%206%200%200%201-7.9%207.9l-6.9%206.9a2.1%202.1%200%200%201-3-3l6.9-6.9a6%206%200%200%201%207.9-7.9l-3.1%203.1z'/%3E%3C/svg%3E") center / contain no-repeat;
}

.sidebar-footer {
  padding: 0 12px 12px;
}

.collapse-toggle {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding: 4px 4px 8px;
  margin-bottom: 2px;
  border-bottom: 1px solid rgba(59,130,246,0.08);
}

.toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  cursor: pointer;
  color: #bfbfbf;
  background: rgba(255,255,255,0.4);
  transition: all 0.2s ease;
}

.toggle-btn:hover {
  background: rgba(64,128,255,0.12);
  color: #4080ff;
  box-shadow: 0 0 0 3px rgba(64,128,255,0.1);
}

.toggle-btn:active {
  transform: scale(0.92);
}

.toggle-btn svg {
  transition: transform 0.25s ease;
}

.toggle-btn svg.flipped {
  transform: rotate(180deg);
}

.sidebar-footer .user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.sidebar.collapsed .sidebar-footer .user-info {
  justify-content: center;
  padding: 8px;
}

.sidebar-footer .user-info:hover {
  background: rgba(255,255,255,0.5);
}

.sidebar-footer .user-info i:first-child {
  font-size: 18px;
  color: #64748b;
}

.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e8eaed;
  flex-shrink: 0;
}

.user-avatar i {
  font-size: 16px;
  color: #64748b;
}

.user-avatar .avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.sidebar-footer .username {
  flex: 1;
  font-size: 13px;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

</style>
