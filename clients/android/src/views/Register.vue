<template>
  <main class="mobile-page auth-page">
    <section class="auth-hero">
      <div class="brand-mark">W</div>
      <h1>创建账号</h1>
      <p>注册后即可在 Android 端连接 WeAgent 后端。</p>
    </section>

    <form class="mobile-card auth-card" @submit.prevent="submit">
      <label class="mobile-field">
        <span>用户名</span>
        <input v-model.trim="form.username" autocomplete="username" placeholder="请输入用户名" />
      </label>

      <label class="mobile-field">
        <span>邮箱</span>
        <input v-model.trim="form.email" type="email" autocomplete="email" placeholder="请输入邮箱" />
      </label>

      <label class="mobile-field">
        <span>密码</span>
        <input v-model="form.password" type="password" autocomplete="new-password" placeholder="至少 6 位" />
      </label>

      <label class="mobile-field">
        <span>确认密码</span>
        <input v-model="confirmPassword" type="password" autocomplete="new-password" placeholder="再次输入密码" />
      </label>

      <label class="check-row terms-row">
        <input v-model="agreeTerms" type="checkbox" />
        <span>我已阅读并同意使用条款</span>
      </label>

      <p v-if="error" class="form-error">{{ error }}</p>

      <button class="primary-btn" type="submit" :disabled="loading">
        {{ loading ? '正在注册...' : '注册并登录' }}
      </button>

      <p class="switch-copy">
        已有账号？
        <router-link to="/login">立即登录</router-link>
      </p>
    </form>
  </main>
</template>

<script>
import { register } from '../services/api'

export default {
  name: 'Register',
  data() {
    return {
      loading: false,
      error: '',
      agreeTerms: false,
      confirmPassword: '',
      form: {
        username: '',
        email: '',
        password: '',
      },
    }
  },
  methods: {
    async submit() {
      this.error = ''
      if (!this.form.username || !this.form.email || !this.form.password) {
        this.error = '请完整填写注册信息'
        return
      }
      if (this.form.password.length < 6) {
        this.error = '密码至少需要 6 位'
        return
      }
      if (this.form.password !== this.confirmPassword) {
        this.error = '两次输入的密码不一致'
        return
      }
      if (!this.agreeTerms) {
        this.error = '请先同意使用条款'
        return
      }
      this.loading = true
      try {
        const response = await register(this.form)
        if (response.code !== 201) {
          this.error = response.message || '注册失败'
          return
        }
        this.$router.replace('/home')
      } catch (error) {
        this.error = (error && error.response && error.response.data && error.response.data.message) || (error && error.message) || '注册失败'
      } finally {
        this.loading = false
      }
    },
  },
}
</script>
