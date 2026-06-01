<template>
  <main class="screen center-screen">
    <section class="panel server-panel">
      <p class="eyebrow">WeAgent Desktop</p>
      <h1>连接后端服务</h1>
      <p class="muted">请输入公网或局域网后端地址，例如 http://192.168.1.100:5002。</p>

      <form class="form" @submit.prevent="save">
        <label>
          <span>服务器地址</span>
          <input v-model.trim="serverUrl" placeholder="http://127.0.0.1:5002" autocomplete="off" />
        </label>

        <p v-if="error" class="error">{{ error }}</p>
        <p v-if="success" class="success">{{ success }}</p>

        <div class="actions">
          <button class="secondary" type="button" :disabled="loading" @click="test">测试连接</button>
          <button type="submit" :disabled="loading">{{ loading ? '保存中...' : '保存并继续' }}</button>
        </div>
      </form>
    </section>
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
    async test() {
      this.error = ''
      this.success = ''
      if (!this.serverUrl) {
        this.error = '请先输入服务器地址'
        return false
      }
      this.loading = true
      try {
        await testServer(this.serverUrl)
        this.success = '连接成功'
        return true
      } catch (error) {
        this.error = '连接失败，请检查地址、网络和后端端口'
        return false
      } finally {
        this.loading = false
      }
    },
    async save() {
      const ok = await this.test()
      if (!ok) return
      await setServerUrl(this.serverUrl)
      this.$router.replace(this.$route.query.redirect || '/login')
    },
  },
}
</script>
