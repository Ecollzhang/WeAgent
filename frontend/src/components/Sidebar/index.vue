<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <div class="logo">WeAgent</div>
    </div>
    <div class="sidebar-nav">
      <router-link to="/dashboard" class="nav-item" :class="{ active: $route.path === '/dashboard' }">
        <i class="el-icon-chat-dot-round"></i>
        <span>聊天</span>
      </router-link>
      <router-link to="/agents" class="nav-item" :class="{ active: $route.path === '/agents' }">
        <i class="el-icon-monitor"></i>
        <span>我的Agent</span>
      </router-link>
      <router-link to="/tools" class="nav-item" :class="{ active: $route.path === '/tools' }">
        <i class="el-icon-s-tools"></i>
        <span>工具集</span>
      </router-link>
      <router-link to="/favorites" class="nav-item" :class="{ active: $route.path === '/favorites' }">
        <i class="el-icon-collection-tag"></i>
        <span>我的收藏</span>
      </router-link>
      <router-link to="/settings" class="nav-item" :class="{ active: $route.path === '/settings' }">
        <i class="el-icon-setting"></i>
        <span>设置</span>
      </router-link>
    </div>
    <div class="sidebar-footer" @click="handleLogout">
      <div class="user-info">
        <div class="user-avatar">
          <img v-if="userAvatar" :src="userAvatar" class="avatar-img" />
          <i v-else class="el-icon-user-solid"></i>
        </div>
        <span class="username">{{ currentUser?.username || '用户' }}</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AppSidebar',
  computed: {
    currentUser() {
      return this.$store.state.user.user
    },
    userAvatar() {
      return this.currentUser?.avatar || localStorage.getItem('user_avatar') || ''
    },
  },
  methods: {
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
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-radius: 12px;
  background: linear-gradient(180deg, #e8f0ff 0%, #f0f5ff 100%);
}

.sidebar-header {
  padding: 24px 20px 16px;
}

.logo {
  font-size: 20px;
  font-weight: 700;
  color: #1e293b;
  letter-spacing: -0.5px;
}

.sidebar-nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 8px 12px;
  gap: 2px;
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

.nav-item:hover {
  background: rgba(255,255,255,0.5);
  color: #1e293b;
}

.nav-item.active {
  background: rgba(64,128,255,0.15);
  color: #4080ff;
  font-weight: 600;
}

.nav-item i {
  font-size: 18px;
  width: 20px;
  text-align: center;
}

.sidebar-footer {
  padding: 12px;
  border-top: 1px solid rgba(59,130,246,0.12);
  cursor: pointer;
}

.sidebar-footer .user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  transition: background 0.2s;
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
