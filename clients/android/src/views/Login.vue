<template>
  <main class="mobile-page auth-page">
    <section class="auth-hero">
      <div class="brand-mark">W</div>
      <h1>欢迎回来</h1>
      <p>登录 WeAgent，继续你的多 Agent 协作会话。</p>
    </section>

    <form class="mobile-card auth-card" @submit.prevent="submit">
      <label class="mobile-field">
        <span>用户名或邮箱</span>
        <input v-model.trim="form.username" autocomplete="username" placeholder="请输入用户名或邮箱" />
      </label>

      <label class="mobile-field">
        <span>密码</span>
        <input v-model="form.password" type="password" autocomplete="current-password" placeholder="请输入密码" />
      </label>

      <div class="form-row">
        <label class="check-row">
          <input v-model="rememberMe" type="checkbox" />
          <span>记住我</span>
        </label>
        <button class="link-btn" type="button" @click="$router.push('/server')">后端地址</button>
      </div>

      <p v-if="error" class="form-error">{{ error }}</p>

      <button class="primary-btn" type="submit" :disabled="loading">
        {{ loading ? '正在登录...' : '登录' }}
      </button>

      <p class="switch-copy">
        还没有账号？
        <router-link to="/register">立即注册</router-link>
      </p>
    </form>
  </main>
</template>

<script>
import { login } from '../services/api'

export default {
  name: 'Login',
  data() {
    return {
      loading: false,
      error: '',
      rememberMe: true,
      form: {
        username: '',
        password: '',
      },
    }
  },
  methods: {
    async submit() {
      this.error = ''
      if (!this.form.username || !this.form.password) {
        this.error = '请输入用户名和密码'
        return
      }
      this.loading = true
      try {
        const response = await login(this.form)
        if (response.code !== 200) {
          this.error = response.message || '登录失败'
          return
        }
        this.$router.replace('/home')
      } catch (error) {
        this.error = (error && error.response && error.response.data && error.response.data.message) || (error && error.message) || '登录失败'
      } finally {
        this.loading = false
      }
    },
  },
}
</script>
