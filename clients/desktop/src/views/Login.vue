<template>
  <div class="auth-page">
    <div class="left-chat-group">
      <div class="gc-bubbles">
        <div class="gc-bubble gc-right" style="--i: 0"><span class="gc-name">你</span>大家来看这个需求</div>
        <div class="gc-bubble gc-left" style="--i: 1"><span class="gc-name">Claude</span>我来分析架构</div>
        <div class="gc-bubble gc-left" style="--i: 2"><span class="gc-name">Codex</span>代码逻辑没问题</div>
        <div class="gc-bubble gc-right" style="--i: 3"><span class="gc-name">你</span>好，开始开发</div>
        <div class="gc-bubble gc-left" style="--i: 4"><span class="gc-name">OpenCode</span>PR 已创建</div>
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
        <div class="oo-bubble oo-right" style="--i: 0">能帮我审查代码吗？</div>
        <div class="oo-bubble oo-left" style="--i: 1">好的，马上看</div>
        <div class="oo-bubble oo-right" style="--i: 2">有要改的吗？</div>
        <div class="oo-bubble oo-left" style="--i: 3">没问题，通过</div>
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
              <h2>欢迎回来</h2>
              <p>登录以继续使用</p>
            </div>
            <button class="server-link" type="button" @click="$router.push('/server')">服务器设置</button>
          </div>

          <form class="auth-form" @submit.prevent="submit">
            <label class="glow-field">
              <span class="field-icon">U</span>
              <input v-model.trim="form.username" placeholder="用户名" autocomplete="username" />
            </label>
            <label class="glow-field">
              <span class="field-icon">L</span>
              <input v-model="form.password" type="password" placeholder="密码" autocomplete="current-password" />
            </label>

            <div class="form-options">
              <label class="checkbox-line"><input v-model="rememberMe" type="checkbox" />记住我</label>
              <button class="forgot-link" type="button">忘记密码？</button>
            </div>

            <p v-if="error" class="form-error">{{ error }}</p>

            <button class="primary-auth-btn" type="submit" :disabled="loading">
              {{ loading ? '登录中...' : '登录' }}
            </button>
          </form>

          <div class="divider"><span>或使用以下方式登录</span></div>
            <div class="social-login">
            <button class="social-btn" type="button"><i class="el-icon-share"></i></button>
            <button class="social-btn" type="button"><i class="el-icon-message"></i></button>
            <button class="social-btn" type="button"><i class="el-icon-monitor"></i></button>
          </div>
          <div class="switch-link">
            <span>还没有账号？</span>
            <router-link to="/register">立即注册</router-link>
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
import { login } from '../services/api'

export default {
  name: 'Login',
  data() {
    return {
      loading: false,
      error: '',
      rememberMe: false,
      form: { username: '', password: '' },
      currentSlide: 0,
      slideTimer: null,
      slideDir: 'slide-next',
      slides: [
        {
          badge: 'AI 聊天',
          title: '多智能体对话',
          desc: '与多个 AI 助手在同一会话中协作',
          color: 'linear-gradient(135deg, #3b82f6, #2563eb)',
          posters: [
            { icon: 'el-icon-chat-dot-round', label: 'Claude' }, { icon: 'el-icon-cpu', label: 'Codex' }, { icon: 'el-icon-monitor', label: 'OpenCode' }, { icon: 'el-icon-brush', label: '设计师' },
            { icon: 'el-icon-document', label: 'Python' }, { icon: 'el-icon-connection', label: 'Rust' }, { icon: 'el-icon-data-analysis', label: '分析师' }, { icon: 'el-icon-view', label: '审查员' },
            { icon: 'el-icon-notebook-2', label: '文档助手' }, { icon: 'el-icon-finished', label: '测试员' }, { icon: 'el-icon-cloudy', label: '运维' }, { icon: 'el-icon-user', label: '顾问' },
          ],
        },
        {
          badge: '代码生成',
          title: 'AI 智能编程',
          desc: '用 AI 生成、审查和优化代码',
          color: 'linear-gradient(135deg, #6366f1, #4f46e5)',
          posters: [
            { icon: 'el-icon-files', label: 'React' }, { icon: 'el-icon-orange', label: 'Vue' }, { icon: 'el-icon-tickets', label: 'TypeScript' }, { icon: 'el-icon-document-copy', label: 'JavaScript' },
            { icon: 'el-icon-folder-opened', label: 'Python' }, { icon: 'el-icon-guide', label: 'Go' }, { icon: 'el-icon-s-operation', label: 'Rust' }, { icon: 'el-icon-edit-outline', label: 'C++' },
            { icon: 'el-icon-mobile-phone', label: 'Kotlin' }, { icon: 'el-icon-goblet-full', label: 'Ruby' }, { icon: 'el-icon-coffee-cup', label: 'Java' }, { icon: 'el-icon-position', label: 'Swift' },
          ],
        },
        {
          badge: '智能产物',
          title: '实时预览部署',
          desc: '实时预览和部署你的产品原型',
          color: 'linear-gradient(135deg, #0ea5e9, #0284c7)',
          posters: [
            { icon: 'el-icon-discover', label: '网页' }, { icon: 'el-icon-mobile', label: '移动端' }, { icon: 'el-icon-s-data', label: '仪表盘' }, { icon: 'el-icon-document', label: '文档' },
            { icon: 'el-icon-video-play', label: '演示文稿' }, { icon: 'el-icon-pie-chart', label: '图表' }, { icon: 'el-icon-picture-outline', label: '设计稿' }, { icon: 'el-icon-box', label: '组件库' },
            { icon: 'el-icon-setting', label: '配置' }, { icon: 'el-icon-postcard', label: '表单' }, { icon: 'el-icon-link', label: 'API 文档' }, { icon: 'el-icon-upload', label: '部署' },
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
      if (!this.form.username || !this.form.password) {
        this.error = '请输入用户名和密码'
        return
      }
      this.loading = true
      try {
        const response = await login(this.form)
        if (response.code === 200) this.$router.replace('/conversations')
        else this.error = response.message || '登录失败'
      } catch (error) {
        this.error = error?.response?.data?.message || '登录失败，请检查账号或服务器地址'
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
