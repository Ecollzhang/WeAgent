<template>
  <main class="app-page with-bottom-nav settings-page">
    <header class="app-header">
      <div>
        <p class="eyebrow">设置</p>
        <h1>个人设置</h1>
      </div>
      <button class="header-btn" type="button" @click="goServer">后端</button>
    </header>

    <section class="screen-body">
      <div class="mobile-tabs">
        <button
          type="button"
          :class="{ active: activeTab === 'profile' }"
          @click="activeTab = 'profile'"
        >
          个人信息
        </button>
        <button
          type="button"
          :class="{ active: activeTab === 'model' }"
          @click="activeTab = 'model'"
        >
          模型配置
        </button>
      </div>

      <form v-if="activeTab === 'profile'" class="settings-card" @submit.prevent="saveProfile">
        <label class="avatar-uploader">
          <span class="settings-avatar" :style="{ background: avatarBackground }">
            <img v-if="avatarPreview" :src="avatarPreview" alt="avatar" @error="avatarPreview = ''" />
            <span v-else>{{ avatarText }}</span>
          </span>
          <input type="file" accept="image/*" @change="pickAvatar" />
          <span class="avatar-action">更换头像</span>
        </label>

        <label class="mobile-field">
          <span>用户名</span>
          <input v-model.trim="profile.username" autocomplete="username" />
        </label>
        <label class="mobile-field">
          <span>邮箱</span>
          <input v-model.trim="profile.email" inputmode="email" autocomplete="email" />
        </label>

        <p v-if="profileError" class="form-error">{{ profileError }}</p>
        <p v-if="profileSuccess" class="form-success">{{ profileSuccess }}</p>

        <div class="sheet-actions compact-actions">
          <button class="secondary-btn" type="button" @click="loadProfile">重置</button>
          <button class="primary-btn" type="submit" :disabled="savingProfile">
            {{ savingProfile ? '保存中...' : '保存' }}
          </button>
        </div>
      </form>

      <form v-else class="settings-card" @submit.prevent="saveModel">
        <label class="mobile-field">
          <span>API Key</span>
          <input v-model.trim="modelConfig.api_key" type="password" autocomplete="off" />
        </label>
        <label class="mobile-field">
          <span>模型名称</span>
          <input v-model.trim="modelConfig.model" placeholder="gpt-4o-mini" />
        </label>
        <label class="mobile-field">
          <span>Base URL</span>
          <input v-model.trim="modelConfig.base_url" placeholder="https://api.openai.com/v1" />
        </label>
        <div class="settings-grid">
          <label class="mobile-field">
            <span>Temperature</span>
            <input v-model.number="modelConfig.temperature" type="number" min="0" max="2" step="0.1" />
          </label>
          <label class="mobile-field">
            <span>Max Tokens</span>
            <input v-model.number="modelConfig.max_tokens" type="number" min="1" step="1" />
          </label>
        </div>

        <p v-if="modelError" class="form-error">{{ modelError }}</p>
        <p v-if="modelSuccess" class="form-success">{{ modelSuccess }}</p>

        <div class="sheet-actions compact-actions">
          <button class="secondary-btn" type="button" @click="loadModel">重置</button>
          <button class="primary-btn" type="submit" :disabled="savingModel">
            {{ savingModel ? '保存中...' : '保存' }}
          </button>
        </div>
      </form>

      <button class="logout-btn" type="button" @click="logout">退出登录</button>
    </section>

    <BottomNav />
  </main>
</template>

<script>
import BottomNav from '../components/BottomNav.vue'
import { backendUrl, getCurrentServerUrl } from '../services/config'
import { getModelConfig, getProfile, saveModelConfig, updateProfile, uploadFile } from '../services/api'
import { clearAuth, saveCurrentUser } from '../services/session'

function unwrap(response) {
  const payload = response && response.data ? response.data : response
  if (payload && payload.data) return payload.data
  return payload || {}
}

export default {
  name: 'SettingsView',
  components: { BottomNav },
  data() {
    return {
      activeTab: 'profile',
      profile: {
        username: '',
        email: '',
        avatar_url: ''
      },
      avatarPreview: '',
      avatarFile: null,
      savingProfile: false,
      profileError: '',
      profileSuccess: '',
      modelConfig: {
        api_key: '',
        model: '',
        base_url: '',
        temperature: 0.7,
        max_tokens: 4096
      },
      savingModel: false,
      modelError: '',
      modelSuccess: ''
    }
  },
  computed: {
    avatarText() {
      return (this.profile.username || 'U').slice(0, 1).toUpperCase()
    },
    avatarBackground() {
      return this.avatarPreview ? 'transparent' : 'linear-gradient(135deg, #2563eb, #16a34a)'
    }
  },
  created() {
    this.loadProfile()
    this.loadModel()
  },
  methods: {
    async loadProfile() {
      this.profileError = ''
      this.profileSuccess = ''
      try {
        const data = unwrap(await getProfile())
        const user = data.user || data.profile || data
        this.profile = {
          username: user.username || '',
          email: user.email || '',
          avatar_url: user.avatar_url || user.avatar || ''
        }
        this.avatarPreview = this.resolveMediaUrl(this.profile.avatar_url)
        this.avatarFile = null
      } catch (error) {
        this.profileError = '个人信息加载失败'
      }
    },
    async loadModel() {
      this.modelError = ''
      this.modelSuccess = ''
      try {
        const data = unwrap(await getModelConfig())
        const config = data.config || data.model_config || data
        this.modelConfig = {
          api_key: config.api_key || '',
          model: config.model || '',
          base_url: config.base_url || '',
          temperature: config.temperature === undefined ? 0.7 : config.temperature,
          max_tokens: config.max_tokens || 4096
        }
      } catch (error) {
        this.modelError = '模型配置加载失败'
      }
    },
    pickAvatar(event) {
      const file = event.target.files && event.target.files[0]
      if (!file) return

      const reader = new FileReader()
      reader.onload = () => {
        this.avatarPreview = String(reader.result || '')
        this.avatarFile = file
      }
      reader.readAsDataURL(file)
    },
    async saveProfile() {
      this.savingProfile = true
      this.profileError = ''
      this.profileSuccess = ''
      try {
        const payload = {
          username: this.profile.username,
          email: this.profile.email
        }
        if (this.avatarFile) {
          const uploaded = unwrap(await uploadFile(this.avatarFile))
          payload.avatar_url = uploaded.url || uploaded.avatar_url || ''
        }
        const saved = unwrap(await updateProfile(payload))
        const savedUser = saved.user || saved.profile || saved
        if (savedUser && savedUser.id) {
          saveCurrentUser(savedUser)
        }
        if (payload.avatar_url || savedUser.avatar_url || savedUser.avatar) {
          this.profile.avatar_url = payload.avatar_url || savedUser.avatar_url || savedUser.avatar
          this.avatarPreview = this.resolveMediaUrl(this.profile.avatar_url)
        }
        this.profileSuccess = '个人信息已保存'
        this.avatarFile = null
      } catch (error) {
        this.profileError = '个人信息保存失败'
      } finally {
        this.savingProfile = false
      }
    },
    async saveModel() {
      this.savingModel = true
      this.modelError = ''
      this.modelSuccess = ''
      try {
        await saveModelConfig({
          api_key: this.modelConfig.api_key,
          model: this.modelConfig.model,
          base_url: this.modelConfig.base_url,
          temperature: Number(this.modelConfig.temperature),
          max_tokens: Number(this.modelConfig.max_tokens)
        })
        this.modelSuccess = '模型配置已保存'
      } catch (error) {
        this.modelError = '模型配置保存失败'
      } finally {
        this.savingModel = false
      }
    },
    goServer() {
      this.$router.push('/server')
    },
    resolveMediaUrl(url) {
      if (!url) return ''
      if (/^https?:\/\//i.test(url) || /^data:/i.test(url)) return url
      return backendUrl(getCurrentServerUrl(), url)
    },
    logout() {
      clearAuth()
      this.$router.replace('/login')
    }
  }
}
</script>
