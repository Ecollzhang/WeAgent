<template>
  <main class="mobile-page home-page">
    <header class="home-header">
      <div>
        <span class="eyebrow">WeAgent Android</span>
        <h1>{{ userName }}</h1>
      </div>
      <button class="ghost-icon-btn" type="button" @click="logout">退出</button>
    </header>

    <section class="mobile-card">
      <h2>登录成功</h2>
      <p>Android 登录/注册链路已经接入后端。下一阶段可以继续实现会话列表、会话详情和 Agent 选择。</p>
    </section>
  </main>
</template>

<script>
import { clearAuth, getCurrentUser } from '../services/session'

export default {
  name: 'Home',
  computed: {
    userName() {
      const user = getCurrentUser()
      return (user && (user.username || user.email)) || '已登录用户'
    },
  },
  methods: {
    logout() {
      clearAuth()
      this.$router.replace('/login')
    },
  },
}
</script>
