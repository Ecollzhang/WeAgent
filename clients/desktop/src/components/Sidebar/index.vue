<template>
  <aside class="app-sidebar">
    <div class="sidebar-logo">W</div>
    <nav class="sidebar-nav">
      <button
        class="sidebar-btn"
        :class="{ active: isActive('/conversations') }"
        title="会话"
        @click="$router.push('/conversations')"
      >
        <i class="el-icon-chat-dot-round"></i>
      </button>
      <button
        class="sidebar-btn"
        :class="{ active: isActive('/agents') }"
        title="Agent"
        @click="$router.push('/agents')"
      >
        <i class="el-icon-user"></i>
      </button>
      <button
        class="sidebar-btn"
        :class="{ active: isActive('/tools') }"
        title="工具集"
        @click="$router.push('/tools')"
      >
        <i class="el-icon-s-tools"></i>
      </button>
      <button
        class="sidebar-btn"
        :class="{ active: isActive('/settings') }"
        title="设置"
        @click="$router.push('/settings')"
      >
        <i class="el-icon-setting"></i>
      </button>
    </nav>
    <button class="sidebar-user" title="退出登录" @click="logout">
      <i class="el-icon-switch-button"></i>
    </button>
  </aside>
</template>

<script>
import { clearAuth } from '../../services/session'

export default {
  name: 'AppSidebar',
  methods: {
    isActive(path) {
      return this.$route && this.$route.path === path
    },
    logout() {
      clearAuth()
      this.$router.replace('/login')
    },
  },
}
</script>
