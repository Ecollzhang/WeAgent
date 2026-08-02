<template>
  <div class="register-page">
    <!-- ======== 左侧：多Agent群聊动画 ======== -->
    <div class="left-chat-group">
      <div class="gc-bubbles">
        <div class="gc-bubble gc-right" style="--i: 0">
          <span class="gc-name">你</span> 大家来看这个需求
        </div>
        <div class="gc-bubble gc-left" style="--i: 1">
          <span class="gc-name">Claude</span> 我来分析架构
        </div>
        <div class="gc-bubble gc-left" style="--i: 2">
          <span class="gc-name">Codex</span> 代码逻辑没问题
        </div>
        <div class="gc-bubble gc-right" style="--i: 3">
          <span class="gc-name">你</span> 好，开始开发！
        </div>
        <div class="gc-bubble gc-left" style="--i: 4">
          <span class="gc-name">OpenCode</span> PR 已创建，请审查
        </div>
      </div>
      <div class="gc-characters">
        <div class="gc-char char-robot" style="--pos: 0">
          <div class="cr-head"><div class="cr-face"><div class="cr-eye l"></div><div class="cr-eye r"></div></div></div>
          <div class="cr-body"></div>
        </div>
        <div class="gc-char char-robot" style="--pos: 1">
          <div class="cr-head"><div class="cr-face"><div class="cr-eye l"></div><div class="cr-eye r"></div></div></div>
          <div class="cr-body"></div>
        </div>
        <div class="gc-char char-human" style="--pos: 2">
          <div class="ch-head"><div class="ch-hair"></div><div class="ch-face"><div class="ch-eye l"></div><div class="ch-eye r"></div><div class="ch-smile"></div></div></div>
          <div class="ch-body"></div>
        </div>
        <div class="gc-char char-robot" style="--pos: 3">
          <div class="cr-head"><div class="cr-face"><div class="cr-eye l"></div><div class="cr-eye r"></div></div></div>
          <div class="cr-body"></div>
        </div>
      </div>
    </div>

    <!-- ======== 右侧：1对1单聊动画 ======== -->
    <div class="right-chat-pair">
      <div class="oo-bubbles">
        <div class="oo-bubble oo-right" style="--i: 0">能帮我审查代码吗？</div>
        <div class="oo-bubble oo-left" style="--i: 1">好的，马上看</div>
        <div class="oo-bubble oo-right" style="--i: 2">有要改的吗？</div>
        <div class="oo-bubble oo-left" style="--i: 3">没问题！通过 🎉</div>
      </div>
      <div class="oo-characters">
        <div class="oo-char char-human">
          <div class="ch-head"><div class="ch-hair"></div><div class="ch-face"><div class="ch-eye l"></div><div class="ch-eye r"></div><div class="ch-smile"></div></div></div>
          <div class="ch-body"></div>
        </div>
        <div class="oo-char char-robot">
          <div class="cr-head"><div class="cr-face"><div class="cr-eye l"></div><div class="cr-eye r"></div></div></div>
          <div class="cr-body"></div>
        </div>
      </div>
    </div>

    <div class="particles">
      <div v-for="n in 30" :key="n" class="particle" :style="particleStyle(n)"></div>
    </div>

    <div class="register-container">
      <div class="form-panel">
        <div class="form-card">
          <div class="logo-section">
            <div class="logo-icon">
              <svg viewBox="0 0 48 48" width="48" height="48">
                <defs>
                  <linearGradient id="lg2" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#3b82f6" />
                    <stop offset="100%" stop-color="#2563eb" />
                  </linearGradient>
                  <filter id="glow2">
                    <feGaussianBlur stdDeviation="2" result="blur"/>
                    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
                  </filter>
                </defs>
                <rect x="4" y="4" width="40" height="40" rx="12" fill="url(#lg2)" filter="url(#glow2)" opacity="0.95"/>
                <text x="24" y="31" text-anchor="middle" fill="white" font-size="22" font-weight="bold" font-family="Arial">W</text>
              </svg>
            </div>
            <h1 class="logo-text">WeAgent</h1>
            <p class="logo-subtitle">多智能体协作平台</p>
          </div>

          <div class="form-header">
            <h2>创建账号</h2>
            <p>立即免费注册</p>
          </div>

          <el-form :model="form" :rules="rules" ref="formRef" @submit.native.prevent="handleRegister">
            <el-form-item prop="username" class="anim-item" style="--delay: 0.1s">
              <el-input v-model="form.username" placeholder="用户名" prefix-icon="el-icon-user" size="large" class="glow-input"></el-input>
            </el-form-item>
            <el-form-item prop="email" class="anim-item" style="--delay: 0.2s">
              <el-input v-model="form.email" placeholder="邮箱" prefix-icon="el-icon-message" size="large" class="glow-input"></el-input>
            </el-form-item>
            <el-form-item prop="password" class="anim-item" style="--delay: 0.3s">
              <el-input v-model="form.password" type="password" placeholder="密码" prefix-icon="el-icon-lock" size="large" show-password class="glow-input"></el-input>
            </el-form-item>
            <el-form-item prop="confirmPassword" class="anim-item" style="--delay: 0.4s">
              <el-input v-model="form.confirmPassword" type="password" placeholder="确认密码" prefix-icon="el-icon-lock" size="large" show-password class="glow-input"></el-input>
            </el-form-item>
            <el-form-item class="anim-item" style="--delay: 0.5s">
              <el-checkbox v-model="agreeTerms" class="custom-checkbox">
                我已阅读并同意<a href="#" class="terms-link">服务条款</a>和<a href="#" class="terms-link">隐私政策</a>
              </el-checkbox>
            </el-form-item>
            <el-form-item class="anim-item" style="--delay: 0.6s">
              <el-button type="primary" native-type="submit" :loading="loading" class="register-btn" size="large">
                <span v-if="!loading">创建账号</span>
                <span v-else>创建中...</span>
              </el-button>
            </el-form-item>
          </el-form>

          <div class="divider anim-item" style="--delay: 0.65s"><span>或使用以下方式注册</span></div>
          <div class="social-login anim-item" style="--delay: 0.7s">
            <button class="social-btn github" @click="socialRegister('github')"><i class="el-icon-share"></i></button>
            <button class="social-btn google" @click="socialRegister('google')"><i class="el-icon-message"></i></button>
            <button class="social-btn microsoft" @click="socialRegister('microsoft')"><i class="el-icon-monitor"></i></button>
          </div>
          <div class="login-link anim-item" style="--delay: 0.75s">
            <span>已有账号？</span>
            <router-link to="/login">立即登录</router-link>
          </div>
        </div>
      </div>

      <!-- 右侧轮播 3×4 -->
      <div class="carousel-panel">
        <div class="carousel-container">
          <transition :name="slideDir" mode="out-in">
            <div class="carousel-slide" :key="currentSlide">
              <div class="slide-title-area">
                <span class="slide-badge" :style="{background: slides[currentSlide].color}">{{ slides[currentSlide].badge }}</span>
                <h2 class="slide-title">{{ slides[currentSlide].title }}</h2>
                <p class="slide-desc">{{ slides[currentSlide].desc }}</p>
              </div>
              <div class="poster-grid">
                <div
                  v-for="(item, idx) in slides[currentSlide].posters"
                  :key="idx"
                  class="poster-card"
                  :style="{
                    background: item.color,
                    animationDelay: `${idx * 0.05}s`,
                    transform: `rotate(${(idx % 4 - 1.5) * 1.5}deg)`,
                  }"
                >
                  <div class="poster-icon">{{ item.icon }}</div>
                  <div class="poster-label">{{ item.label }}</div>
                </div>
              </div>
            </div>
          </transition>
          <div class="carousel-controls">
            <button class="carousel-arrow" @click="prevSlide"><i class="el-icon-arrow-left"></i></button>
            <button class="carousel-arrow" @click="nextSlide"><i class="el-icon-arrow-right"></i></button>
          </div>
          <div class="carousel-dots">
            <span v-for="(s, idx) in slides" :key="idx" class="dot" :class="{active:currentSlide===idx}" @click="goToSlide(idx)"><span class="dot-fill"></span></span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Register',
  data() {
    const validateConfirm = (rule, v, cb) => v === this.form.password ? cb() : cb(new Error('Passwords do not match'))
    return {
      form: { username: '', email: '', password: '', confirmPassword: '' },
      rules: {
        username: [{ required: true, message: '请输入用户名', trigger: 'blur' }, { min: 3, max: 80, message: '3-80 个字符', trigger: 'blur' }],
        email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
        password: [{ required: true, message: '请输入密码', trigger: 'blur' }, { min: 6, message: '至少 6 位', trigger: 'blur' }],
        confirmPassword: [{ required: true, message: '请确认密码', trigger: 'blur' }, { validator: validateConfirm, trigger: 'blur' }],
      },
      loading: false, agreeTerms: false,
      currentSlide: 0, slideTimer: null, slideDir: 'slide-next',
      slides: [
        {
          badge: '三大领域',
          title: '覆盖研发全流程',
          desc: '智能研发、智慧教育、智慧办公 — 一个平台搞定',
          color: 'linear-gradient(135deg, #3b82f6, #2563eb)',
          posters: [
            { icon: '💻', label: '智能研发', color: '#ffffff' },
            { icon: '📋', label: '需求管理', color: '#ffffff' },
            { icon: '🐛', label: '缺陷跟踪', color: '#ffffff' },
            { icon: '🔄', label: '迭代规划', color: '#ffffff' },
            { icon: '📚', label: '智慧教育', color: '#ffffff' },
            { icon: '🎓', label: '课程管理', color: '#ffffff' },
            { icon: '📝', label: '作业批改', color: '#ffffff' },
            { icon: '🏢', label: '智慧办公', color: '#ffffff' },
            { icon: '📅', label: '日程管理', color: '#ffffff' },
            { icon: '🔗', label: 'GitHub 集成', color: '#ffffff' },
            { icon: '🐳', label: '沙箱隔离', color: '#ffffff' },
            { icon: '⚙️', label: '服务编排', color: '#ffffff' },
          ],
        },
        {
          badge: 'AI Agent',
          title: '多智能体协作开发',
          desc: '专业 AI Agent 团队自动分工，高效完成复杂开发任务',
          color: 'linear-gradient(135deg, #6366f1, #4f46e5)',
          posters: [
            { icon: '🏗️', label: '全栈架构师', color: '#ffffff' },
            { icon: '🎨', label: '前端专家', color: '#ffffff' },
            { icon: '⚙️', label: '后端专家', color: '#ffffff' },
            { icon: '🔍', label: '代码审查', color: '#ffffff' },
            { icon: '🧪', label: '测试专家', color: '#ffffff' },
            { icon: '📄', label: '文档专家', color: '#ffffff' },
            { icon: '🗄️', label: '数据库 DBA', color: '#ffffff' },
            { icon: '🔒', label: '安全专家', color: '#ffffff' },
            { icon: '☁️', label: 'DevOps', color: '#ffffff' },
            { icon: '📊', label: '数据分析', color: '#ffffff' },
            { icon: '🤖', label: 'Claude', color: '#ffffff' },
            { icon: '⚡', label: 'OpenCode', color: '#ffffff' },
          ],
        },
        {
          badge: '平台能力',
          title: '强大基础设施',
          desc: '知识库 RAG、代码审查、CI/CD、实时预览开箱即用',
          color: 'linear-gradient(135deg, #0ea5e9, #0284c7)',
          posters: [
            { icon: '🧠', label: '知识库 RAG', color: '#ffffff' },
            { icon: '🔎', label: 'AI 代码审查', color: '#ffffff' },
            { icon: '🔨', label: 'CI/CD 构建', color: '#ffffff' },
            { icon: '📦', label: '代码仓库', color: '#ffffff' },
            { icon: '📈', label: '甘特图', color: '#ffffff' },
            { icon: '💬', label: '实时协作', color: '#ffffff' },
            { icon: '🔐', label: 'JWT 安全', color: '#ffffff' },
            { icon: '🐳', label: '容器沙箱', color: '#ffffff' },
            { icon: '🌐', label: '服务发现', color: '#ffffff' },
            { icon: '📊', label: '灰度发布', color: '#ffffff' },
            { icon: '🖥️', label: '实时预览', color: '#ffffff' },
            { icon: '🚀', label: '一键部署', color: '#ffffff' },
          ],
        },
      ],
    }
  },
  computed: { slideTransition() { return this.slideDir } },
  mounted() { this.startAutoPlay() },
  beforeDestroy() { this.stopAutoPlay() },
  methods: {
    async handleRegister() {
      if (!this.agreeTerms) { this.$message.warning('Please agree to the terms'); return }
      const valid = await this.$refs.formRef.validate().catch(() => false)
      if (!valid) return
      this.loading = true
      try {
        const res = await this.$store.dispatch('user/register', { username: this.form.username, email: this.form.email, password: this.form.password })
        if (res.code === 201) { this.$message.success('账号创建成功！'); this.$router.push('/dashboard') }
        else this.$message.error(res.message || 'Registration failed')
      } catch(e) { this.$message.error('Registration failed') }
      finally { this.loading = false }
    },
    socialRegister(p) { this.$message.info(`${p} registration coming soon`) },
    startAutoPlay() { this.slideTimer = setInterval(() => this.nextSlide(), 4500) },
    stopAutoPlay() { if (this.slideTimer) { clearInterval(this.slideTimer); this.slideTimer = null } },
    nextSlide() { this.slideDir='slide-next'; this.currentSlide=(this.currentSlide+1)%this.slides.length },
    prevSlide() { this.slideDir='slide-prev'; this.currentSlide=(this.currentSlide-1+this.slides.length)%this.slides.length },
    goToSlide(i) { this.slideDir=i>this.currentSlide?'slide-next':'slide-prev'; this.currentSlide=i; this.stopAutoPlay(); this.startAutoPlay() },
    particleStyle(n) {
      const size = Math.random()*8+3
      return { width:`${size}px`,height:`${size}px`,left:`${Math.random()*100}%`,top:`${Math.random()*100}%`,animationDelay:`${Math.random()*10}s`,animationDuration:`${8+Math.random()*12}s`,opacity:Math.random()*0.5+0.1 }
    },
  },
}
</script>

<style scoped>
/* =============================================================
   REGISTER PAGE - 白色简约 + 装饰光晕
   ============================================================= */
.register-page {
  position: relative; height: 100vh;
  display: flex; align-items: center; justify-content: center;
  background:
    linear-gradient(to top, #f0f4f8 0%, transparent 50%, transparent 100%),
    url(../assets/bg.png) center bottom / cover no-repeat fixed;
  overflow: hidden;
  font-family: 'Inter', 'Segoe UI', 'Helvetica Neue', sans-serif;
}

/* 装饰性渐变光晕 */
.register-page::before,
.register-page::after {
  content: '';
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
  z-index: 0;
}
.register-page::before {
  width: clamp(300px, 50vw, 600px);
  height: clamp(300px, 50vw, 600px);
  background: radial-gradient(circle, rgba(59,130,246,0.08) 0%, transparent 70%);
  top: -20%;
  right: -10%;
  animation: blobFloat 25s ease-in-out infinite;
}
.register-page::after {
  width: clamp(250px, 40vw, 500px);
  height: clamp(250px, 40vw, 500px);
  background: radial-gradient(circle, rgba(99,102,241,0.06) 0%, transparent 70%);
  bottom: -15%;
  left: -8%;
  animation: blobFloat 30s ease-in-out infinite reverse;
}
@keyframes blobFloat {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -30px) scale(1.05); }
  66% { transform: translate(-20px, 20px) scale(0.95); }
}

/* 粒子 */
.particles { position:absolute; inset:0; pointer-events:none; z-index:0; }
.particle {
  position:absolute; border-radius:50%;
  background:linear-gradient(135deg, rgba(18, 103, 240, 0.2), rgba(65, 68, 212, 0.12));
  animation:particleFloat linear infinite;
}
@keyframes particleFloat {
  0%{transform:translateY(0) translateX(0) scale(1);opacity:0}
  10%{opacity:0.5} 90%{opacity:0.5}
  100%{transform:translateY(-110vh) translateX(120px) scale(0.3);opacity:0}
}

/* 左侧群聊 */
.left-chat-group {
  position:absolute; left:50px; bottom:120px; top:auto; z-index:10;
  display:flex; flex-direction:column; align-items:center;
  transform:scale(0.65); transform-origin:bottom left;
  animation:groupFloat 7s ease-in-out infinite;
  filter:drop-shadow(0 8px 30px rgba(0,0,0,0.06));
}
@keyframes groupFloat { 0%,100%{transform:scale(0.65) translateY(0)} 50%{transform:scale(0.65) translateY(-15px)} }
.gc-bubbles {
  position:relative; display:flex; flex-direction:column; align-items:flex-start;
  gap:6px; margin-bottom:50px; width:18vw;
  background:rgba(255,255,255,0.25);
  backdrop-filter:blur(16px); -webkit-backdrop-filter:blur(16px);
  padding:10px 14px;
  border-radius:16px;
  border:1px solid rgba(255,255,255,0.3);
}
.gc-bubble {
  padding:6px 12px; border-radius:12px; font-size:16px; line-height:1.4;
  color:#334155; pointer-events:none;
  opacity:0; animation:bubbleInOut 15s ease-in-out infinite;
  animation-delay:calc(var(--i,0)*3s); max-width:180px;
  box-shadow:0 2px 8px rgba(0,0,0,0.04);
  backdrop-filter:blur(4px);
}
.gc-bubble.gc-left {
  align-self:flex-start;
  background:rgba(255,255,255,0.85); border:1px solid rgba(226,232,240,0.8);
  border-bottom-left-radius:4px;
}
.gc-bubble.gc-right {
  align-self:flex-end;
  background:rgba(239,246,255,0.85); border:1px solid rgba(191,219,254,0.8);
  border-bottom-right-radius:4px;
}
.gc-name {
  font-weight:600; font-size:10px; color:#3b82f6; display:block; margin-bottom:2px;
}
.gc-bubble.gc-right .gc-name { color:#2563eb; }
@keyframes bubbleInOut {
  0%,100%{opacity:0;transform:translateY(8px) scale(0.9)}
  8%{opacity:1;transform:translateY(0) scale(1)}
  25%{opacity:1;transform:translateY(0) scale(1)}
  33%{opacity:0;transform:translateY(-8px) scale(0.9)}
}
.gc-characters { display:flex; align-items:flex-end; gap:0; position:relative; }
.gc-char:nth-child(1){z-index:1;margin-right:-16px;animation:charBob 4s ease-in-out infinite 0s}
.gc-char:nth-child(2){z-index:2;margin-right:-12px;animation:charBob 4s ease-in-out infinite 0.8s}
.gc-char:nth-child(3){z-index:3;margin-bottom:16px;animation:charBob 4s ease-in-out infinite 1.6s}
.gc-char:nth-child(4){z-index:1;margin-left:-16px;animation:charBob 4s ease-in-out infinite 2.4s}
@keyframes charBob { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-12px)} }

.cr-head {
  width:56px; height:48px;
  background:linear-gradient(135deg,#475569,#64748b);
  border:2px solid rgba(255,255,255,0.8); border-radius:12px;
  display:flex; align-items:center; justify-content:center;
  box-shadow:0 4px 16px rgba(0,0,0,0.08);
}
.cr-face { display:flex; gap:10px; align-items:center; }
.cr-eye {
  width:12px; height:12px; border-radius:50%; background:#f1f5f9;
  border:1.5px solid rgba(0,0,0,0.1);
  display:flex; align-items:center; justify-content:center;
}
.cr-eye::after {
  content:''; width:6px; height:6px; border-radius:50%;
  background:#3b82f6; animation:eyeGlow 2s ease-in-out infinite;
}
.cr-body {
  width:32px; height:28px; margin:0 auto;
  background:linear-gradient(135deg,#475569,#64748b);
  border:2px solid rgba(255,255,255,0.6); border-top:none;
  border-radius:0 0 8px 8px;
}
.ch-head {
  width:48px; height:48px; border-radius:50%;
  background:linear-gradient(135deg,#fbbf24,#f59e0b);
  border:2px solid rgba(255,255,255,0.8); position:relative;
}
.ch-hair { position:absolute; top:-4px; left:50%; transform:translateX(-50%); width:44px; height:20px; background:#92400e; border-radius:50% 50% 0 0; }
.ch-face { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; gap:8px; }
.ch-eye { width:6px; height:6px; border-radius:50%; background:#1c1917; margin-top:6px; }
.ch-smile { position:absolute; bottom:10px; width:16px; height:8px; border-bottom:2px solid #92400e; border-radius:0 0 10px 10px; }
.ch-body { width:28px; height:32px; margin:-4px auto 0; background:linear-gradient(135deg,#93c5fd,#60a5fa); border-radius:0 0 8px 8px; }
@keyframes eyeGlow { 0%,100%{box-shadow:0 0 4px #3b82f6} 50%{box-shadow:0 0 8px #3b82f6,0 0 12px rgba(59,130,246,0.3)} }

/* 右侧1对1 */
.right-chat-pair {
  position:absolute; right:50px; bottom:120px; top:auto; z-index:10;
  display:flex; flex-direction:column; align-items:center;
  transform:scale(0.65); transform-origin:bottom right;
  animation:pairFloat 7s ease-in-out infinite 0.5s;
  filter:drop-shadow(0 8px 30px rgba(0,0,0,0.06));
}
@keyframes pairFloat { 0%,100%{transform:scale(0.65) translateY(0)} 50%{transform:scale(0.65) translateY(-15px)} }
.oo-bubbles {
  position:relative; display:flex; flex-direction:column;
  gap:5px; margin-bottom:50px; width:18vw;
  background:rgba(255,255,255,0.25);
  backdrop-filter:blur(16px); -webkit-backdrop-filter:blur(16px);
  padding:10px 14px;
  border-radius:16px;
  border:1px solid rgba(255,255,255,0.3);
}
.oo-bubble {
  padding:5px 10px; border-radius:10px; font-size:16px; line-height:1.4;
  color:#334155; pointer-events:none;
  opacity:0; animation:bubbleInOut 14s ease-in-out infinite;
  animation-delay:calc(var(--i,0)*3.5s); max-width:160px;
  box-shadow:0 2px 8px rgba(0,0,0,0.04);
  backdrop-filter:blur(4px);
}
.oo-bubble.oo-left{ align-self:flex-start; background:rgba(255,251,235,0.85); border:1px solid rgba(253,230,138,0.8); border-bottom-left-radius:3px; }
.oo-bubble.oo-right{ align-self:flex-end; background:rgba(253,242,248,0.85); border:1px solid rgba(251,207,232,0.8); border-bottom-right-radius:3px; }
.oo-characters { display:flex; align-items:flex-end; gap:40px; }
.oo-char { animation:charPairBob 5s ease-in-out infinite; }
.oo-char:first-child{animation-delay:0s}
.oo-char:last-child{animation-delay:1.5s}
@keyframes charPairBob { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-16px)} }
.oo-char .cr-head { width:64px; height:56px; }
.oo-char .cr-body { width:36px; height:32px; }
.oo-char .cr-eye { width:14px; height:14px; }
.oo-char .cr-eye::after { width:7px; height:7px; }
.oo-char .ch-head { width:56px; height:56px; }
.oo-char .ch-hair { width:52px; height:24px; }
.oo-char .ch-eye { width:7px; height:7px; }
.oo-char .ch-smile { width:20px; height:10px; bottom:12px; }
.oo-char .ch-body { width:32px; height:36px; }

/* 容器 - 玻璃态悬浮卡片 */
.register-container {
  position:relative; z-index:2; display:flex;
  width:60vw; min-height:0; max-height:none;
  border-radius:20px; overflow:hidden;
  opacity: 0.95;
  background:rgba(255,255,255,0.4);
  backdrop-filter:blur(24px); -webkit-backdrop-filter:blur(24px);
  border:1px solid rgba(255,255,255,0.25);
  box-shadow:0 25px 80px rgba(0,0,0,0.06), 0 10px 30px rgba(0,0,0,0.03), inset 0 1px 0 rgba(255,255,255,0.6);
  animation:containerIn 0.9s cubic-bezier(0.16,1,0.3,1);
  margin:20px auto;
}
.register-container::before {
  content:''; position:absolute; inset:0; border-radius:20px; padding:1px;
  background:linear-gradient(135deg, rgba(255,255,255,0.5), rgba(59,130,246,0.08), rgba(255,255,255,0.5));
  -webkit-mask:linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite:xor;
  mask-composite:exclude;
  pointer-events:none; z-index:3;
}
@keyframes containerIn { from{opacity:0;transform:scale(0.92) translateY(30px)} to{opacity:1;transform:scale(1) translateY(0)} }

/* 左侧表单 */
.form-panel {
  flex:0 0 320px; padding:28px 24px;
  display:flex; flex-direction:column; justify-content:center;
  background:transparent;
  border-right:1px solid rgba(0,0,0,0.04);
}
.form-card { max-width:280px; margin:0 auto; width:100%; }
.logo-section { text-align:center; margin-bottom:18px; animation:fadeDown 0.8s ease-out; }
.logo-icon { display:inline-block; margin-bottom:6px; }
.logo-icon svg { width:36px; height:36px; animation:logoPulse 3s ease-in-out infinite; }
@keyframes logoPulse { 0%,100%{filter:drop-shadow(0 0 8px rgba(59,130,246,0.15));transform:scale(1)} 50%{filter:drop-shadow(0 0 20px rgba(59,130,246,0.3));transform:scale(1.03)} }
.logo-text { font-size:22px; font-weight:800; color:#1e293b; margin:0 0 2px; letter-spacing:-0.5px; }
.logo-subtitle { font-size:11px; color:#94a3b8; margin:0; letter-spacing:1.5px; }
.form-header { margin-bottom:16px; }
.form-header h2 { font-size:20px; color:#1e293b; margin:0 0 4px; font-weight:600; }
.form-header p { font-size:13px; color:#94a3b8; margin:0; }

.anim-item { animation:slideIn 0.5s cubic-bezier(0.16,1,0.3,1) both; animation-delay:var(--delay,0s); }
@keyframes slideIn { from{opacity:0;transform:translateX(-24px)} to{opacity:1;transform:translateX(0)} }

.glow-input :deep(.el-input__inner) {
  background:rgba(248,250,252,0.7); border:1px solid rgba(0,0,0,0.06);
  color:#1e293b; height:42px; border-radius:12px; padding-left:40px; font-size:13px;
  transition:all 0.3s ease;
  backdrop-filter:blur(4px);
}
.glow-input :deep(.el-input__inner:hover) {
  border-color:rgba(59,130,246,0.3);
  background:rgba(248,250,252,0.85);
}
.glow-input :deep(.el-input__inner:focus) {
  border-color:#3b82f6;
  box-shadow:0 0 0 3px rgba(59,130,246,0.1), 0 0 20px rgba(59,130,246,0.05);
  background:#ffffff;
}
.glow-input :deep(.el-input__inner::placeholder) { color:#94a3b8; }
.glow-input :deep(.el-input__prefix) { left:14px; }
.glow-input :deep(.el-input__prefix i) { color:#94a3b8; font-size:16px; line-height:42px; }

.terms-link { color:#3b82f6; text-decoration:none; }
.terms-link:hover { text-decoration:underline; }

.register-btn {
  width:100%; height:42px; border-radius:12px;
  font-size:14px; font-weight:600; letter-spacing:0.5px;
  border:none;
  background:linear-gradient(135deg,#3b82f6,#2563eb);
  transition:all 0.3s ease; position:relative; overflow:hidden;
}
.register-btn::before {
  content:''; position:absolute; inset:0;
  background:linear-gradient(135deg,rgba(255,255,255,0.15) 0%,transparent 50%);
  opacity:0; transition:opacity 0.4s;
}
.register-btn:hover::before { opacity:1; }
.register-btn:hover { transform:translateY(-2px); box-shadow:0 12px 40px rgba(59,130,246,0.3), 0 0 60px rgba(59,130,246,0.1); }
.register-btn:active { transform:translateY(0); }
.register-btn :deep(span) { color:#fff; position:relative; z-index:1; }

.divider { display:flex; align-items:center; margin:18px 0; }
.divider::before,.divider::after { content:''; flex:1; height:1px; background:linear-gradient(to right, transparent, #e2e8f0, transparent); }
.divider span { padding:0 14px; font-size:12px; color:#94a3b8; white-space:nowrap; }

.social-login { display:flex; justify-content:center; gap:12px; margin-bottom:18px; }
.social-btn {
  width:46px; height:46px; border-radius:14px;
  border:1px solid rgba(0,0,0,0.06);
  background:rgba(248,250,252,0.7);
  color:#94a3b8; font-size:20px;
  cursor:pointer; transition:all 0.3s ease;
  display:flex; align-items:center; justify-content:center;
  backdrop-filter:blur(4px);
}
.social-btn:hover { background:#ffffff; border-color:#3b82f6; transform:translateY(-3px); color:#3b82f6; box-shadow:0 8px 25px rgba(59,130,246,0.15); }
.social-btn.github:hover{border-color:#333;color:#333;box-shadow:0 8px 25px rgba(51,51,51,0.12)}
.social-btn.google:hover{border-color:#ea4335;color:#ea4335;box-shadow:0 8px 25px rgba(234,67,53,0.12)}
.social-btn.microsoft:hover{border-color:#00a4ef;color:#00a4ef;box-shadow:0 8px 25px rgba(0,164,239,0.12)}

.login-link { text-align:center; font-size:14px; color:#94a3b8; }
.login-link a { color:#3b82f6; text-decoration:none; font-weight:500; margin-left:4px; transition:all 0.3s; }
.login-link a:hover { color:#2563eb; }

/* 右侧轮播 */
.carousel-panel {
  flex:1; display:flex; align-items:center; justify-content:center;
  padding:24px 28px; position:relative;
  background:radial-gradient(ellipse at 30% 30%,rgba(59,130,246,0.04) 0%,transparent 50%),
             radial-gradient(ellipse at 70% 70%,rgba(99,102,241,0.03) 0%,transparent 50%);
}
.carousel-container { width:100%; position:relative; animation:fadeIn 1s ease-out 0.3s both; }
@keyframes fadeIn { from{opacity:0} to{opacity:1} }
.carousel-slide { min-height:320px; display:flex; flex-direction:column; align-items:center; padding:4px 0; }
.slide-title-area { text-align:center; margin-bottom:16px; }
.slide-badge { display:inline-block; padding:3px 14px; border-radius:20px; font-size:10px; font-weight:600; letter-spacing:1px; color:#fff; margin-bottom:6px; }
.slide-title { font-size:18px; font-weight:700; color:#1e293b; margin:0 0 4px; }
.slide-desc { font-size:12px; color:#94a3b8; margin:0; }
.poster-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; width:100%; max-width:380px; }
.poster-card { aspect-ratio:1; border-radius:14px; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:6px; cursor:pointer; transition:all 0.3s cubic-bezier(0.16,1,0.3,1); border:1px solid rgba(0,0,0,0.04); position:relative; overflow:hidden; animation:posterIn 0.5s cubic-bezier(0.16,1,0.3,1) both; background:rgba(255,255,255,0.7); backdrop-filter:blur(4px); }
@keyframes posterIn { from{opacity:0;transform:scale(0.85) translateY(10px)} to{opacity:1;transform:scale(1) translateY(0)} }
.poster-card::before { content:''; position:absolute; inset:0; background:linear-gradient(135deg,rgba(255,255,255,0.5) 0%,transparent 50%); opacity:0; transition:opacity 0.3s; }
.poster-card:hover { transform:translateY(-4px) scale(1.04) !important; box-shadow:0 12px 40px rgba(0,0,0,0.06); border-color:rgba(59,130,246,0.15); }
.poster-card:hover::before { opacity:1; }
.poster-icon { font-size:22px; position:relative; z-index:1; }
.poster-label { font-size:10px; font-weight:500; color:#475569; position:relative; z-index:1; }

.carousel-controls { display:flex; justify-content:space-between; position:absolute; top:42%; left:-16px; right:-16px; pointer-events:none; }
.carousel-arrow { width:38px; height:38px; border-radius:50%; border:1px solid rgba(0,0,0,0.06); background:rgba(255,255,255,0.85); color:#94a3b8; cursor:pointer; display:flex; align-items:center; justify-content:center; transition:all 0.3s ease; pointer-events:auto; box-shadow:0 2px 8px rgba(0,0,0,0.04); backdrop-filter:blur(8px); }
.carousel-arrow:hover { background:#ffffff; border-color:#3b82f6; color:#3b82f6; transform:scale(1.1); box-shadow:0 4px 16px rgba(59,130,246,0.15); }
.carousel-dots { display:flex; justify-content:center; gap:10px; margin-top:20px; }
.dot { width:8px; height:8px; border-radius:50%; background:#d1d5db; cursor:pointer; transition:all 0.4s ease; display:flex; align-items:center; justify-content:center; }
.dot.active { width:28px; border-radius:10px; background:#3b82f6; }
.dot-fill { width:4px; height:4px; border-radius:50%; background:transparent; transition:0.4s; }
.dot.active .dot-fill { background:#fff; }

.slide-next-enter-active,.slide-next-leave-active,.slide-prev-enter-active,.slide-prev-leave-active { transition:all 0.45s cubic-bezier(0.4,0,0.2,1); }
.slide-next-enter{opacity:0;transform:translateX(40px) scale(0.97)}
.slide-next-leave-to{opacity:0;transform:translateX(-40px) scale(0.97)}
.slide-prev-enter{opacity:0;transform:translateX(-40px) scale(0.97)}
.slide-prev-leave-to{opacity:0;transform:translateX(40px) scale(0.97)}

/* =============================================================
   响应式 - 全尺寸覆盖
   ============================================================= */
@media (max-width:1400px){
  .register-container{max-width:760px}
  .form-panel{flex:0 0 300px;padding:24px 20px}
  .carousel-panel{padding:20px 24px}
}
@media (max-width:1200px){
  .register-container{max-width:700px}
  .form-panel{flex:0 0 280px;padding:20px 18px}
  .carousel-panel{padding:18px 20px}
  .carousel-slide{min-height:280px}
  .slide-title{font-size:16px}
}
@media (max-width:1024px){
  .form-panel{flex:0 0 45%;padding:24px 20px}
  .poster-grid{gap:6px;max-width:320px}
  .carousel-arrow{width:30px;height:30px}
  .carousel-controls{left:-6px;right:-6px}
}
@media (max-width:768px){
  .register-container{flex-direction:column;border-radius:16px;width:92vw;max-width:92vw;margin:10px auto}
  .form-panel{flex:none;width:auto;padding:24px 20px;border-right:none;border-bottom:1px solid rgba(0,0,0,0.04)}
  .carousel-panel{padding:20px 16px}
  .carousel-slide{min-height:260px}
  .poster-grid{max-width:340px}
  .slide-title{font-size:16px}
  .left-chat-group,.right-chat-pair,.register-page::before,.register-page::after{display:none}
}
@media (max-width:480px){
  .register-container{border-radius:12px;width:96vw}
  .form-panel{padding:20px 14px}
  .form-card{max-width:100%}
  .logo-section{margin-bottom:14px}
  .logo-icon svg{width:30px;height:30px}
  .logo-text{font-size:20px}
  .form-header h2{font-size:18px}
  .form-header p{font-size:12px}
  .glow-input :deep(.el-input__inner){height:38px;font-size:13px;padding-left:36px}
  .glow-input :deep(.el-input__prefix i){font-size:14px;line-height:38px}
  .register-btn{height:38px;font-size:13px}
  .carousel-panel{padding:16px 12px}
  .carousel-slide{min-height:220px}
  .poster-grid{grid-template-columns:repeat(3,1fr);gap:5px;max-width:260px}
  .slide-title{font-size:15px}
  .slide-desc{font-size:11px}
}
@media (max-width:360px){
  .form-panel{padding:18px 12px}
  .logo-text{font-size:20px}
  .form-header h2{font-size:17px}
  .poster-grid{grid-template-columns:repeat(3,1fr);gap:4px}
  .slide-title{font-size:14px}
  .carousel-slide{min-height:200px}
}

:deep(.el-form-item){margin-bottom:18px}
:deep(.el-checkbox__input.is-checked .el-checkbox__inner){background-color:#3b82f6;border-color:#3b82f6}
:deep(.el-checkbox__inner){background-color:rgba(248,250,252,0.7);border-color:#d1d5db}
:deep(.el-checkbox__label){color:#64748b!important}
</style>
