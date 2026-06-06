<template>
  <main class="dashboard-shell">
    <aside class="app-sidebar">
      <div class="sidebar-logo">W</div>
      <nav class="sidebar-nav">
        <button class="sidebar-btn" title="会话" @click="$router.push('/conversations')"><i class="el-icon-chat-dot-round"></i></button>
        <button class="sidebar-btn" title="智能体" @click="$router.push('/agents')"><i class="el-icon-user"></i></button>
        <button class="sidebar-btn" title="工具" @click="$router.push('/tools')"><span class="toolset-wrench-icon"></span></button>
        <button class="sidebar-btn active" title="设置"><i class="el-icon-setting"></i></button>
      </nav>
      <button class="sidebar-user" title="退出登录" @click="logout"><i class="el-icon-switch-button"></i></button>
    </aside>

    <section class="settings-page-panel">
      <aside class="settings-list">
        <div class="list-header">
          <h3>设置</h3>
        </div>
        <div class="list-items">
          <button
            v-for="item in settingsItems"
            :key="item.key"
            class="settings-item"
            :class="{ active: activeSetting === item.key }"
            @click="activeSetting = item.key"
          >
            <i :class="item.icon"></i>
            <span>{{ item.label }}</span>
          </button>
        </div>
        <button class="server-setting-link" @click="$router.push('/server')">
          <i class="el-icon-link"></i>
          服务器设置
        </button>
      </aside>

      <section class="settings-detail">
        <div v-if="activeSetting === 'profile'" class="detail-panel">
          <h2>个人信息</h2>
          <p class="detail-desc">管理你的账号信息和头像。</p>

          <div class="avatar-section">
            <button class="avatar-wrapper" type="button" @click="triggerUpload">
              <img v-if="avatarPreview" :src="avatarPreview" class="avatar-img" />
              <i v-else class="el-icon-user-solid avatar-placeholder"></i>
              <span class="avatar-overlay">
                <i class="el-icon-camera"></i>
                <span>{{ avatarUploading ? '上传中' : '更换头像' }}</span>
              </span>
            </button>
            <input
              ref="fileInput"
              type="file"
              accept="image/png,image/jpeg,image/gif,image/webp"
              class="hidden-file"
              @change="handleAvatarChange"
            />
            <div class="avatar-info">
              <span class="avatar-name">{{ profile.username || '用户' }}</span>
              <span class="avatar-hint">点击头像上传，支持 JPG/PNG/GIF/WebP，最大 2MB。</span>
            </div>
          </div>

          <form class="settings-form" @submit.prevent="saveProfile">
            <label>
              <span>用户名</span>
              <input v-model.trim="profile.username" placeholder="用户名" />
            </label>
            <label>
              <span>邮箱</span>
              <input v-model.trim="profile.email" type="email" placeholder="邮箱地址" />
            </label>
            <button class="workspace-primary" :disabled="profileSaving">
              {{ profileSaving ? '保存中...' : '保存个人信息' }}
            </button>
          </form>
        </div>

        <div v-if="activeSetting === 'model'" class="detail-panel">
          <h2>模型配置</h2>
          <p class="detail-desc">配置 AI 模型相关参数。</p>

          <form class="settings-form" @submit.prevent="saveModel">
            <label>
              <span>API Key</span>
              <input v-model.trim="modelConfig.api_key" type="password" placeholder="输入新的 API Key，留空则保持原 Key" />
            </label>
            <label>
              <span>模型名称</span>
              <select v-model="modelConfig.model">
                <option value="deepseek-v4-pro">deepseek-v4-pro</option>
                <option value="doubao-seed-2-0-lite-260215">doubao-seed-2-0-lite-260215</option>
                <option value="qwen-plus">qwen-plus</option>
                <option value="gpt-4o-mini">GPT-4o-mini</option>
                <option value="deepseek-v3">DeepSeek V3</option>
                <option value="deepseek-r1">DeepSeek R1</option>
                <option value="custom">自定义</option>
              </select>
            </label>
            <label>
              <span>API Base URL</span>
              <input v-model.trim="modelConfig.base_url" :placeholder="modelConfig.model === 'custom' ? 'https://api.example.com/v1' : 'https://api.openai.com/v1'" />
            </label>
            <div class="form-grid two">
              <label>
                <span>Temperature</span>
                <input v-model.number="modelConfig.temperature" type="number" step="0.1" min="0" max="2" />
              </label>
              <label>
                <span>最大 Token 数</span>
                <input v-model.number="modelConfig.max_tokens" type="number" min="256" max="32768" step="256" />
              </label>
            </div>
            <button class="workspace-primary" :disabled="modelSaving">
              {{ modelSaving ? '保存中...' : '保存模型配置' }}
            </button>
          </form>
        </div>

        <div v-if="loading" class="workspace-state overlay-state">
          <i class="el-icon-loading"></i>
          <span>正在加载设置...</span>
        </div>
        <div v-if="message" class="desktop-toast success-toast">{{ message }}</div>
        <div v-if="error" class="desktop-toast">{{ error }}</div>
      </section>
    </section>
  </main>
</template>

<script>
import {
  getModelConfig,
  getProfile,
  saveModelConfig,
  updateProfile,
  uploadFile,
} from '../services/api'
import { backendUrl } from '../services/config'
import { clearAuth } from '../services/session'
import { getServerUrl } from '../services/config'

export default {
  name: 'Settings',
  data() {
    return {
      activeSetting: 'profile',
      settingsItems: [
        { key: 'profile', label: '个人信息', icon: 'el-icon-user' },
        { key: 'model', label: '模型配置', icon: 'el-icon-connection' },
      ],
      loading: false,
      profileSaving: false,
      modelSaving: false,
      avatarUploading: false,
      error: '',
      message: '',
      serverUrl: '',
      profile: {
        username: '',
        email: '',
        avatar_url: '',
      },
      modelConfig: {
        api_key: '',
        model: '',
        base_url: '',
        temperature: 0.7,
        max_tokens: 4096,
      },
    }
  },
  computed: {
    avatarPreview() {
      return this.profile.avatar_url ? backendUrl(this.serverUrl, this.profile.avatar_url) : ''
    },
  },
  async created() {
    this.serverUrl = await getServerUrl()
    await this.loadSettings()
  },
  methods: {
    async loadSettings() {
      this.loading = true
      this.error = ''
      try {
        const [profileRes, modelRes] = await Promise.all([getProfile(), getModelConfig()])
        this.profile = {
          username: profileRes.data?.username || '',
          email: profileRes.data?.email || '',
          avatar_url: profileRes.data?.avatar_url || profileRes.data?.avatar || '',
        }
        this.modelConfig = {
          api_key: '',
          model: modelRes.data?.model || 'claude-3.5-sonnet',
          base_url: modelRes.data?.base_url || '',
          temperature: modelRes.data?.temperature ?? 0.7,
          max_tokens: modelRes.data?.max_tokens || 4096,
        }
      } catch (error) {
        this.handleError(error, '加载设置失败')
      } finally {
        this.loading = false
      }
    },
    triggerUpload() {
      if (!this.avatarUploading) this.$refs.fileInput.click()
    },
    async handleAvatarChange(event) {
      const file = event.target.files?.[0]
      if (!file) return
      if (file.size > 2 * 1024 * 1024) {
        this.error = '图片大小不能超过 2MB'
        event.target.value = ''
        return
      }
      this.error = ''
      this.message = ''
      this.avatarUploading = true
      try {
        const response = await uploadFile(file)
        if (response.code === 200 && response.data?.url) {
          this.profile.avatar_url = response.data.url
          await this.saveProfile()
          this.message = '头像已上传并保存'
        } else {
          this.error = response.message || '上传头像失败'
        }
      } catch (error) {
        this.handleError(error, '上传头像失败')
      } finally {
        this.avatarUploading = false
        event.target.value = ''
      }
    },
    async saveProfile() {
      this.profileSaving = true
      this.error = ''
      this.message = ''
      try {
        await updateProfile({
          username: this.profile.username,
          email: this.profile.email,
          avatar_url: this.profile.avatar_url,
        })
        this.message = this.message || '个人信息已保存'
      } catch (error) {
        this.handleError(error, '保存个人信息失败')
      } finally {
        this.profileSaving = false
      }
    },
    async saveModel() {
      this.modelSaving = true
      this.error = ''
      this.message = ''
      try {
        const payload = { ...this.modelConfig }
        if (!payload.api_key) delete payload.api_key
        await saveModelConfig(payload)
        this.message = '模型配置已保存'
      } catch (error) {
        this.handleError(error, '保存模型配置失败')
      } finally {
        this.modelSaving = false
      }
    },
    handleError(error, fallback) {
      this.error = error?.response?.data?.message || error?.message || fallback
      if (error?.response?.status === 401) this.logout()
    },
    logout() {
      clearAuth()
      this.$router.replace('/login')
    },
  },
}
</script>
