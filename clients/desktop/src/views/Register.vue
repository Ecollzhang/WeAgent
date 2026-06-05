<template>
  <div class="auth-page">
    <div class="left-chat-group">
      <div class="gc-bubbles">
        <div class="gc-bubble gc-right" style="--i: 0"><span class="gc-name">你</span>创建一个新项目</div>
        <div class="gc-bubble gc-left" style="--i: 1"><span class="gc-name">Claude</span>需求拆解好了</div>
        <div class="gc-bubble gc-left" style="--i: 2"><span class="gc-name">Codex</span>我来生成骨架</div>
        <div class="gc-bubble gc-right" style="--i: 3"><span class="gc-name">你</span>开始协作</div>
        <div class="gc-bubble gc-left" style="--i: 4"><span class="gc-name">OpenCode</span>任务队列已准备</div>
      </div>
      <div class="gc-characters">
        <div class="gc-char char-robot"><div class="cr-head"><div class="cr-face"><div class="cr-eye"></div><div class="cr-eye"></div></div></div><div class="cr-body"></div></div>
        <div class="gc-char char-robot"><div class="cr-head"><div class="cr-face"><div class="cr-eye"></div><div class="cr-eye"></div></div></div><div class="cr-body"></div></div>
        <div class="gc-char char-human"><div class="ch-head"><div class="ch-hair"></div><div class="ch-face"><div class="ch-eye"></div><div class="ch-eye"></div><div class="ch-smile"></div></div></div><div class="ch-body"></div></div>
        <div class="gc-char char-robot"><div class="cr-head"><div class="cr-face"><div class="cr-eye"></div><div class="cr-eye"></div></div></div><div class="cr-body"></div></div>
      </div>
    </div>

    <div class="right-chat-pair">
      <div class="oo-bubbles">
        <div class="oo-bubble oo-right" style="--i: 0">能一起做产品吗？</div>
        <div class="oo-bubble oo-left" style="--i: 1">当然，马上开工</div>
        <div class="oo-bubble oo-right" style="--i: 2">需要哪些能力？</div>
        <div class="oo-bubble oo-left" style="--i: 3">会话、工具、产物都齐了</div>
      </div>
      <div class="oo-characters">
        <div class="oo-char char-human"><div class="ch-head"><div class="ch-hair"></div><div class="ch-face"><div class="ch-eye"></div><div class="ch-eye"></div><div class="ch-smile"></div></div></div><div class="ch-body"></div></div>
        <div class="oo-char char-robot"><div class="cr-head"><div class="cr-face"><div class="cr-eye"></div><div class="cr-eye"></div></div></div><div class="cr-body"></div></div>
      </div>
    </div>

    <div class="particles">
      <div v-for="n in 36" :key="n" class="particle" :style="particleStyle(n)"></div>
    </div>

    <div class="auth-container">
      <div class="form-panel">
        <div class="form-card">
          <div class="logo-section">
            <div class="logo-icon">W</div>
            <h1 class="logo-text">WeAgent</h1>
            <p class="logo-subtitle">多智能体协作平台</p>
          </div>

          <div class="form-header">
            <div>
              <h2>创建账号</h2>
              <p>立即免费注册</p>
            </div>
            <button class="server-link" type="button" @click="$router.push('/server')">服务器设置</button>
          </div>

          <form class="auth-form" @submit.prevent="submit">
            <label class="glow-field"><span class="field-icon">U</span><input v-model.trim="form.username" placeholder="用户名" autocomplete="username" /></label>
            <label class="glow-field"><span class="field-icon">M</span><input v-model.trim="form.email" type="email" placeholder="邮箱" autocomplete="email" /></label>
            <label class="glow-field"><span class="field-icon">L</span><input v-model="form.password" type="password" placeholder="密码" autocomplete="new-password" /></label>
            <label class="glow-field"><span class="field-icon">C</span><input v-model="confirmPassword" type="password" placeholder="确认密码" autocomplete="new-password" /></label>

            <label class="checkbox-line terms-line">
              <input v-model="agreeTerms" type="checkbox" />
              <span>我已阅读并同意服务条款和隐私政策</span>
            </label>

            <p v-if="error" class="form-error">{{ error }}</p>

            <button class="primary-auth-btn" type="submit" :disabled="loading">
              {{ loading ? '创建中...' : '创建账号' }}
            </button>
          </form>

          <div class="divider"><span>或使用以下方式注册</span></div>
          <div class="social-login">
            <button class="social-btn" type="button"><i class="el-icon-share"></i></button>
            <button class="social-btn" type="button"><i class="el-icon-message"></i></button>
            <button class="social-btn" type="button"><i class="el-icon-monitor"></i></button>
          </div>
          <div class="switch-link">
            <span>已有账号？</span>
            <router-link to="/login">立即登录</router-link>
          </div>
        </div>
      </div>

      <div class="carousel-panel">
        <div class="carousel-container">
          <transition :name="slideDir" mode="out-in">
            <div class="carousel-slide" :key="currentSlide">
              <div class="slide-title-area">
                <span class="slide-badge" :style="{ background: slides[currentSlide].color }">{{ slides[currentSlide].badge }}</span>
                <h2 class="slide-title">{{ slides[currentSlide].title }}</h2>
                <p class="slide-desc">{{ slides[currentSlide].desc }}</p>
              </div>
              <div class="poster-grid">
                <div v-for="(item, idx) in slides[currentSlide].posters" :key="idx" class="poster-card" :style="{ animationDelay: `${idx * 0.05}s` }">
                  <div class="poster-icon"><i :class="item.icon"></i></div>
                  <div class="poster-label">{{ item.label }}</div>
                </div>
              </div>
            </div>
          </transition>

          <div class="carousel-controls">
            <button class="carousel-arrow" type="button" @click="prevSlide">‹</button>
            <button class="carousel-arrow" type="button" @click="nextSlide">›</button>
          </div>
          <div class="carousel-dots">
            <button v-for="(s, idx) in slides" :key="s.badge" class="dot" :class="{ active: currentSlide === idx }" type="button" @click="goToSlide(idx)"></button>
          </div>
        </div>
      </div>
    </div>
  </div>
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
      form: { username: '', email: '', password: '' },
      currentSlide: 0,
      slideTimer: null,
      slideDir: 'slide-next',
      slides: [
        {
          badge: '功能特色',
          title: '为什么选择 WeAgent？',
          desc: 'AI 驱动开发所需的一切',
          color: 'linear-gradient(135deg, #3b82f6, #2563eb)',
          posters: [
            { icon: 'el-icon-s-custom', label: '多智能体' }, { icon: 'el-icon-chat-line-round', label: '实时聊天' }, { icon: 'el-icon-box', label: '产物管理' }, { icon: 'el-icon-lock', label: '安全可靠' },
            { icon: 'el-icon-lightning', label: '极速响应' }, { icon: 'el-icon-aim', label: '精准输出' }, { icon: 'el-icon-data-analysis', label: '数据分析' }, { icon: 'el-icon-connection', label: '集成能力' },
            { icon: 'el-icon-edit-outline', label: '代码生成' }, { icon: 'el-icon-view', label: '代码审查' }, { icon: 'el-icon-document', label: '文档' }, { icon: 'el-icon-upload', label: '部署' },
          ],
        },
        {
          badge: '团队协作',
          title: '为团队打造',
          desc: '与团队成员和 AI 助手无缝协作',
          color: 'linear-gradient(135deg, #6366f1, #4f46e5)',
          posters: [
            { icon: 'el-icon-user-solid', label: '团队聊天' }, { icon: 'el-icon-s-order', label: '任务管理' }, { icon: 'el-icon-time', label: '进度追踪' }, { icon: 'el-icon-collection-tag', label: '标签' },
            { icon: 'el-icon-bell', label: '通知' }, { icon: 'el-icon-folder-opened', label: '文件共享' }, { icon: 'el-icon-menu', label: '项目管理' }, { icon: 'el-icon-search', label: '全局搜索' },
            { icon: 'el-icon-moon', label: '深色模式' }, { icon: 'el-icon-setting', label: '设置' }, { icon: 'el-icon-magic-stick', label: '自定义' }, { icon: 'el-icon-mobile-phone', label: '移动端' },
          ],
        },
        {
          badge: '开始使用',
          title: '立即加入',
          desc: '连接后端后即可开启协作',
          color: 'linear-gradient(135deg, #0ea5e9, #0284c7)',
          posters: [
            { icon: 'el-icon-present', label: '免费版' }, { icon: 'el-icon-medal', label: '专业版' }, { icon: 'el-icon-office-building', label: '企业版' }, { icon: 'el-icon-reading', label: '学生优惠' },
            { icon: 'el-icon-chat-dot-square', label: '社区' }, { icon: 'el-icon-notebook-2', label: '文档' }, { icon: 'el-icon-video-camera', label: '示例' }, { icon: 'el-icon-film', label: '教程' },
            { icon: 'el-icon-link', label: 'API' }, { icon: 'el-icon-set-up', label: '插件' }, { icon: 'el-icon-cpu', label: 'SDK' }, { icon: 'el-icon-service', label: '支持' },
          ],
        },
      ],
    }
  },
  mounted() {
    this.startAutoPlay()
  },
  beforeDestroy() {
    this.stopAutoPlay()
  },
  methods: {
    async submit() {
      this.error = ''
      if (!this.form.username || !this.form.email || !this.form.password || !this.confirmPassword) {
        this.error = '请完整填写注册信息'
        return
      }
      if (this.form.password !== this.confirmPassword) {
        this.error = '两次输入的密码不一致'
        return
      }
      if (!this.agreeTerms) {
        this.error = '请先同意服务条款和隐私政策'
        return
      }
      this.loading = true
      try {
        const response = await register(this.form)
        if (response.code === 201) this.$router.replace('/conversations')
        else this.error = response.message || '注册失败'
      } catch (error) {
        this.error = error?.response?.data?.message || '注册失败，请检查信息或服务器地址'
      } finally {
        this.loading = false
      }
    },
    startAutoPlay() {
      this.slideTimer = setInterval(() => this.nextSlide(), 4500)
    },
    stopAutoPlay() {
      if (this.slideTimer) clearInterval(this.slideTimer)
      this.slideTimer = null
    },
    nextSlide() {
      this.slideDir = 'slide-next'
      this.currentSlide = (this.currentSlide + 1) % this.slides.length
    },
    prevSlide() {
      this.slideDir = 'slide-prev'
      this.currentSlide = (this.currentSlide - 1 + this.slides.length) % this.slides.length
    },
    goToSlide(index) {
      this.slideDir = index > this.currentSlide ? 'slide-next' : 'slide-prev'
      this.currentSlide = index
      this.stopAutoPlay()
      this.startAutoPlay()
    },
    particleStyle(n) {
      const size = (n % 7) + 3
      return {
        width: `${size}px`,
        height: `${size}px`,
        left: `${(n * 17) % 100}%`,
        top: `${(n * 29) % 100}%`,
        animationDelay: `${(n % 10) * 0.7}s`,
        animationDuration: `${8 + (n % 8)}s`,
      }
    },
  },
}
</script>
