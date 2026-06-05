<template>
  <main class="mobile-page setup-page">
    <section class="brand-panel">
      <div class="brand-mark">W</div>
      <h1>WeAgent</h1>
      <p>配置后端服务地址后，即可在 Android 端登录使用。</p>
    </section>

    <form class="mobile-card setup-card" @submit.prevent="submit">
      <label class="mobile-field">
        <span>后端地址</span>
        <input v-model.trim="serverUrl" placeholder="http://192.168.1.8:5000" autocomplete="off" />
      </label>

      <div class="hint-box">
        <strong>局域网测试提示</strong>
        <p>真机不要使用 localhost，请填写运行后端电脑的局域网 IP。</p>
      </div>

      <p v-if="error" class="form-error">{{ error }}</p>
      <p v-if="success" class="form-success">{{ success }}</p>

      <button class="primary-btn" type="submit" :disabled="loading">
        {{ loading ? '正在连接...' : '保存并继续' }}
      </button>
    </form>
  </main>
</template>

<script>
import { getServerUrl, setServerUrl } from '../services/config'
import { testServer } from '../services/api'

export default {
  name: 'ServerSetup',
  data() {
    return {
      serverUrl: '',
      loading: false,
      error: '',
      success: '',
    }
  },
  async created() {
    this.serverUrl = await getServerUrl()
  },
  methods: {
    async submit() {
      this.error = ''
      this.success = ''
      if (!this.serverUrl) {
        this.error = '请填写后端地址'
        return
      }
      this.loading = true
      try {
        await testServer(this.serverUrl)
        await setServerUrl(this.serverUrl)
        this.success = '连接成功'
        this.$router.replace(this.$route.query.redirect || '/login')
      } catch (error) {
        this.error = (error && error.message) || '后端连接失败'
      } finally {
        this.loading = false
      }
    },
  },
}
</script>
