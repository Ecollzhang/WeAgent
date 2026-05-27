<template>
  <div class="settings-page">
    <AppSidebar />

    <div class="settings-content">
      <!-- 左侧设置列表 -->
      <div class="settings-list">
        <div class="list-header">
          <h3>设置</h3>
        </div>
        <div class="list-items">
          <div
            v-for="item in settingsItems"
            :key="item.key"
            class="settings-item"
            :class="{ active: activeSetting === item.key }"
            @click="activeSetting = item.key"
          >
            <i :class="item.icon"></i>
            <span>{{ item.label }}</span>
          </div>
        </div>
      </div>

      <!-- 右侧设置详情 -->
      <div class="settings-detail">
        <!-- 模型设置 -->
        <div v-if="activeSetting === 'model'" class="detail-panel">
          <h2>模型设置</h2>
          <p class="detail-desc">配置 AI 模型相关参数</p>
          <el-form label-position="top" class="settings-form">
            <el-form-item label="API Key">
              <el-input
                v-model="modelConfig.api_key"
                type="password"
                show-password
                placeholder="输入您的 API Key"
              ></el-input>
            </el-form-item>
            <el-form-item label="模型名称">
              <el-select v-model="modelConfig.model" style="width: 100%">
                <el-option label="deepseek-v4-pro" value="deepseek-v4-pro"></el-option>
                <el-option label="doubao-seed-2-0-lite-260215" value="doubao-seed-2-0-lite-260215"></el-option>
                <el-option label="qwen-plus" value="qwen-plus"></el-option>
                <el-option label="GPT-4o-mini" value="gpt-4o-mini"></el-option>
                <el-option label="DeepSeek V3" value="deepseek-v3"></el-option>
                <el-option label="DeepSeek R1" value="deepseek-r1"></el-option>
                <el-option label="自定义" value="custom"></el-option>
              </el-select>
            </el-form-item>
            <el-form-item label="API Base URL" v-if="modelConfig.model === 'custom'">
              <el-input v-model="modelConfig.base_url" placeholder="https://api.example.com/v1"></el-input>
            </el-form-item>
            <el-form-item label="API Base URL" v-else>
              <el-input v-model="modelConfig.base_url" placeholder="https://api.openai.com/v1"></el-input>
            </el-form-item>
            <el-form-item label="Temperature">
              <el-slider
                v-model="modelConfig.temperature"
                :min="0"
                :max="2"
                :step="0.1"
                show-input
              ></el-slider>
            </el-form-item>
            <el-form-item label="最大 Token 数">
              <el-input-number v-model="modelConfig.max_tokens" :min="256" :max="32768" :step="256"></el-input-number>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSaveModel" :loading="saving">
                保存模型配置
              </el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- 个人信息 -->
        <div v-if="activeSetting === 'profile'" class="detail-panel">
          <h2>个人信息</h2>
          <p class="detail-desc">管理您的账户信息</p>

          <!-- 头像上传 -->
          <div class="avatar-section">
            <div class="avatar-wrapper" @click="triggerUpload">
              <img v-if="profile.avatar" :src="profile.avatar" class="avatar-img" />
              <i v-else class="el-icon-user-solid avatar-placeholder"></i>
              <div class="avatar-overlay">
                <i class="el-icon-camera"></i>
                <span>更换头像</span>
              </div>
            </div>
            <input
              ref="fileInput"
              type="file"
              accept="image/png,image/jpeg,image/gif,image/webp"
              style="display:none"
              @change="handleAvatarChange"
            />
            <div class="avatar-info">
              <span class="avatar-name">{{ profile.username || '用户' }}</span>
              <span class="avatar-hint">点击头像上传，支持 JPG/PNG/GIF/WebP</span>
            </div>
          </div>

          <el-form label-position="top" class="settings-form">
            <el-form-item label="用户名">
              <el-input v-model="profile.username" placeholder="用户名"></el-input>
            </el-form-item>
            <el-form-item label="邮箱">
              <el-input v-model="profile.email" placeholder="邮箱地址"></el-input>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSaveProfile" :loading="saving">
                保存个人信息
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import AppSidebar from '../components/Sidebar/index.vue'
import { uploadFile } from '../api/upload'
import { updateProfile } from '../api/settings'

export default {
  name: 'Settings',
  components: { AppSidebar },
  data() {
    return {
      activeSetting: 'model',
      saving: false,
      settingsItems: [
        { key: 'model', label: '模型设置', icon: 'el-icon-connection' },
        { key: 'profile', label: '个人信息', icon: 'el-icon-user' },
      ],
      modelConfig: {
        api_key: '',
        model: 'claude-3.5-sonnet',
        base_url: '',
        temperature: 0.7,
        max_tokens: 4096,
      },
      profile: {
        username: '',
        email: '',
        avatar: '',
      },
    }
  },
  async created() {
    // Load model config from store
    const saved = this.$store.state.settings.modelConfig
    if (saved) {
      this.modelConfig = { ...this.modelConfig, ...saved }
    }
    await this.$store.dispatch('settings/fetchModelConfig')
    const remoteSaved = this.$store.state.settings.modelConfig
    if (remoteSaved) {
      this.modelConfig = { ...this.modelConfig, ...remoteSaved }
    }
    // Load user profile
    const user = this.$store.state.user.user
    if (user) {
      this.profile.username = user.username || ''
      this.profile.email = user.email || ''
      this.profile.avatar = user.avatar || localStorage.getItem('user_avatar') || ''
    }
  },
  methods: {
    async handleSaveModel() {
      this.saving = true
      try {
        await this.$store.dispatch('settings/saveModelConfig', this.modelConfig)
        this.$message.success('模型配置已保存')
      } finally {
        this.saving = false
      }
    },
    triggerUpload() {
      this.$refs.fileInput.click()
    },
    async handleAvatarChange(e) {
      const file = e.target.files[0]
      if (!file) return

      // Validate file size (max 2MB)
      if (file.size > 2 * 1024 * 1024) {
        this.$message.warning('图片大小不能超过 2MB')
        return
      }

      try {
        const res = await uploadFile(file)
        if (res.code === 200) {
          this.profile.avatar = res.data.url
        } else {
          this.$message.error(res.message || '上传头像失败')
        }
      } catch (err) {
        this.$message.error('上传头像失败，请重试')
      }
      e.target.value = ''
    },
    async handleSaveProfile() {
      this.saving = true
      try {
        const res = await updateProfile({
          username: this.profile.username,
          email: this.profile.email,
          avatar_url: this.profile.avatar,
        })
        if (res.code === 200) {
          // Update user store
          const userData = {
            ...this.$store.state.user.user,
            username: this.profile.username,
            email: this.profile.email,
            avatar: this.profile.avatar,
          }
          this.$store.commit('user/SET_USER', userData)
          this.$message.success('个人信息已保存')
        } else {
          this.$message.error(res.message || '保存失败')
        }
      } catch (e) {
        this.$message.error('保存失败')
      } finally {
        this.saving = false
      }
    },
  },
}
</script>

<style scoped>
.settings-page {
  display: flex;
  gap: 12px;
  padding: 12px;
  height: 100vh;
  background: linear-gradient(135deg, #e8f0ff 0%, #f0f5ff 50%, #f5f7fa 100%);
  overflow: hidden;
}

.settings-content {
  flex: 1;
  display: flex;
  gap: 12px;
  min-width: 0;
}

/* 左侧设置列表 */
.settings-list {
  width: 220px;
  flex-shrink: 0;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.list-header {
  padding: 16px 16px 12px;
}

.list-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 500;
  color: #1e293b;
}

.list-items {
  flex: 1;
  padding: 4px 8px;
}

.settings-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 12px;
  cursor: pointer;
  border-radius: 8px;
  font-size: 14px;
  color: #333;
  transition: all 0.15s;
}

.settings-item:hover {
  background: #f5f6f7;
}

.settings-item.active {
  background: #f0f5ff;
  color: #4080ff;
  font-weight: 500;
}

.settings-item i {
  font-size: 18px;
  width: 20px;
  text-align: center;
}

/* 右侧设置详情 */
.settings-detail {
  flex: 1;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  padding: 32px 40px;
  overflow-y: auto;
  min-width: 0;
}

.detail-panel {
  max-width: 640px;
}

.detail-panel h2 {
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 600;
  color: #1e293b;
}

.detail-desc {
  margin: 0 0 28px;
  font-size: 14px;
  color: #86909c;
}

.settings-form {
  max-width: 480px;
}

.settings-form .el-button--primary {
  background: #4080ff;
  border: none;
  border-radius: 8px;
  margin-top: 8px;
}

/* 头像区域 */
.avatar-section {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 1px solid #f0f0f0;
}

.avatar-wrapper {
  position: relative;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  overflow: hidden;
  cursor: pointer;
  background: #f2f3f5;
  flex-shrink: 0;
  border: 2px solid #e8eaed;
  transition: border-color 0.2s;
}

.avatar-wrapper:hover {
  border-color: #4080ff;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-placeholder {
  font-size: 36px;
  color: #c0c4cc;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,0.5);
  color: #fff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
  font-size: 12px;
  gap: 2px;
}

.avatar-wrapper:hover .avatar-overlay {
  opacity: 1;
}

.avatar-overlay i {
  font-size: 20px;
}

.avatar-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.avatar-name {
  font-size: 16px;
  font-weight: 500;
  color: #1e293b;
}

.avatar-hint {
  font-size: 12px;
  color: #86909c;
}
</style>
