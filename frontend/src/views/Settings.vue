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

        <!-- 关于我们 -->
        <div v-if="activeSetting === 'about'" class="detail-panel about-panel">
          <div class="about-hero">
            <div>
              <span class="about-kicker">WeAgent Platform</span>
              <h2>关于 WeAgent</h2>
              <p class="detail-desc">了解平台能力、快速上手流程和版本迭代记录</p>
            </div>
            <div class="about-version">
              <span>当前版本</span>
              <strong>Beta</strong>
            </div>
          </div>

          <div class="about-tabs">
            <button
              v-for="tab in aboutTabs"
              :key="tab.key"
              type="button"
              class="about-tab"
              :class="{ active: activeAboutTab === tab.key }"
              @click="activeAboutTab = tab.key"
            >
              <i :class="tab.icon"></i>
              <span>{{ tab.label }}</span>
            </button>
          </div>

          <div v-if="activeAboutTab === 'manual'" class="manual-layout">
            <aside class="manual-toc">
              <div class="toc-title">使用手册</div>
              <a
                v-for="section in manualSections"
                :key="section.id"
                :href="'#' + section.id"
                class="toc-link"
              >
                {{ section.title }}
              </a>
            </aside>

            <div class="manual-content">
              <section id="quick-start" class="manual-section">
                <div class="section-heading">
                  <span class="section-index">01</span>
                  <div>
                    <h3>快速开始</h3>
                    <p>完成登录、配置模型、新建 Agent 和发起会话，快速跑通第一条任务链路。</p>
                  </div>
                </div>
                <div class="manual-note-grid">
                  <div class="manual-note">
                    <span>开始前确认</span>
                    <p>后端服务已启动，账号可登录，模型 API Key 和 Base URL 已准备好。</p>
                  </div>
                  <div class="manual-note">
                    <span>完成标志</span>
                    <p>能成功发送一条消息，并在会话中看到 Agent 回复、进度和产物区域。</p>
                  </div>
                </div>
                <div class="step-grid">
                  <div v-for="step in quickStartSteps" :key="step.title" class="step-card">
                    <i :class="step.icon"></i>
                    <h4>{{ step.title }}</h4>
                    <p>{{ step.desc }}</p>
                    <ul class="mini-list">
                      <li v-for="action in step.actions" :key="action">{{ action }}</li>
                    </ul>
                  </div>
                </div>
                <div class="image-placeholder large">
                  <i class="el-icon-picture-outline"></i>
                  <div>
                    <strong>快速开始截图预留位</strong>
                    <span>建议放置登录后首页、模型配置或第一次对话的完整界面截图。</span>
                  </div>
                </div>
              </section>

              <section id="scenarios" class="manual-section">
                <div class="section-heading">
                  <span class="section-index">02</span>
                  <div>
                    <h3>按场景使用</h3>
                    <p>根据任务类型选择单 Agent、多 Agent 或收藏会话，提高任务处理效率。</p>
                  </div>
                </div>
                <div class="scenario-list">
                  <div v-for="scenario in scenarioGuides" :key="scenario.title" class="scenario-item">
                    <div class="scenario-icon"><i :class="scenario.icon"></i></div>
                    <div>
                      <h4>{{ scenario.title }}</h4>
                      <p>{{ scenario.desc }}</p>
                      <div class="scenario-meta">{{ scenario.bestFor }}</div>
                      <ol class="compact-steps">
                        <li v-for="step in scenario.steps" :key="step">{{ step }}</li>
                      </ol>
                    </div>
                  </div>
                </div>
              </section>

              <section id="conversation" class="manual-section">
                <div class="section-heading">
                  <span class="section-index">03</span>
                  <div>
                    <h3>多轮对话</h3>
                    <p>会话会持续保留上下文、进度、产物和历史问题，适合连续推进复杂任务。</p>
                  </div>
                </div>
                <div class="manual-two-column">
                  <div class="guide-block">
                    <h4>建议流程</h4>
                    <ol>
                      <li>先描述目标、约束和验收标准。</li>
                      <li>让 Agent 拆解任务并确认方案。</li>
                      <li>逐轮补充反馈，要求修正或继续下一步。</li>
                      <li>在产物抽屉中查看生成文件、表格和执行结果。</li>
                    </ol>
                  </div>
                  <div class="guide-block">
                    <h4>常用提问模板</h4>
                    <div v-for="tpl in promptTemplates" :key="tpl.title" class="prompt-template">
                      <span>{{ tpl.title }}</span>
                      <p>{{ tpl.content }}</p>
                    </div>
                  </div>
                  <div class="image-placeholder">
                    <i class="el-icon-chat-line-round"></i>
                    <strong>多轮对话截图预留位</strong>
                    <span>建议展示用户消息、Agent 回复、进度和产物。</span>
                  </div>
                </div>
              </section>

              <section id="agents" class="manual-section">
                <div class="section-heading">
                  <span class="section-index">04</span>
                  <div>
                    <h3>Agent 配置</h3>
                    <p>通过能力标签、系统提示词、技能和工具配置，让不同 Agent 负责不同类型任务。</p>
                  </div>
                </div>
                <div class="feature-strip">
                  <span>能力标签</span>
                  <span>系统提示词</span>
                  <span>Skill</span>
                  <span>工具选择</span>
                  <span>会话级配置</span>
                </div>
                <div class="agent-guide-grid">
                  <div v-for="item in agentConfigTips" :key="item.title" class="agent-guide-card">
                    <h4>{{ item.title }}</h4>
                    <p>{{ item.desc }}</p>
                    <span>{{ item.example }}</span>
                  </div>
                </div>
              </section>

              <section id="artifacts" class="manual-section">
                <div class="section-heading">
                  <span class="section-index">05</span>
                  <div>
                    <h3>产物与文件</h3>
                    <p>平台会展示任务执行中产生的文件、表格、日志和 Raw Output，便于追踪结果来源。</p>
                  </div>
                </div>
                <div class="artifact-preview-row">
                  <div class="artifact-preview">
                    <i class="el-icon-document"></i>
                    <div>
                      <strong>文件产物</strong>
                      <span>支持查看 HTML、Markdown、图片等文件内容。</span>
                    </div>
                  </div>
                  <div class="artifact-preview">
                    <i class="el-icon-s-grid"></i>
                    <div>
                      <strong>表格产物</strong>
                      <span>即使不在容器目录中，也可基于产物数据直接查看。</span>
                    </div>
                  </div>
                </div>
                <div class="artifact-manual-list">
                  <div v-for="item in artifactManualItems" :key="item.title" class="artifact-manual-item">
                    <span>{{ item.title }}</span>
                    <p>{{ item.desc }}</p>
                  </div>
                </div>
              </section>

              <section id="faq" class="manual-section">
                <div class="section-heading">
                  <span class="section-index">06</span>
                  <div>
                    <h3>常见问题</h3>
                    <p>遇到模型、会话、文件访问或多端网络问题时，可以先按这里排查。</p>
                  </div>
                </div>
                <div class="faq-list">
                  <div v-for="item in faqItems" :key="item.question" class="faq-item">
                    <h4>{{ item.question }}</h4>
                    <p>{{ item.answer }}</p>
                  </div>
                </div>
              </section>
            </div>
          </div>

          <div v-if="activeAboutTab === 'product'" class="product-overview">
            <div class="product-intro">
              <h3>产品介绍</h3>
              <p>WeAgent 是一个面向多 Agent 协作任务的平台，支持会话管理、Agent 编排、工具调用、产物沉淀和多端使用。</p>
            </div>
            <div class="highlight-grid">
              <div v-for="item in productHighlights" :key="item.title" class="highlight-card">
                <i :class="item.icon"></i>
                <h4>{{ item.title }}</h4>
                <p>{{ item.desc }}</p>
              </div>
            </div>
            <div class="image-placeholder large product-shot">
              <i class="el-icon-monitor"></i>
              <div>
                <strong>产品总览图预留位</strong>
                <span>建议放置 Dashboard、Agent、产物抽屉组合截图。</span>
              </div>
            </div>
          </div>

          <div v-if="activeAboutTab === 'timeline'" class="timeline-panel">
            <h3>迭代历程</h3>
            <p class="timeline-desc">记录平台从 Web 单端到桌面端、Android、多 Agent 协作体验的演进。</p>
            <div class="timeline-list">
              <div v-for="item in timelineItems" :key="item.version" class="timeline-item">
                <div class="timeline-dot"></div>
                <div class="timeline-content">
                  <span class="timeline-version">{{ item.version }}</span>
                  <h4>{{ item.title }}</h4>
                  <p>{{ item.desc }}</p>
                </div>
              </div>
            </div>
          </div>
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
      activeAboutTab: 'manual',
      settingsItems: [
        { key: 'model', label: '模型设置', icon: 'el-icon-connection' },
        { key: 'profile', label: '个人信息', icon: 'el-icon-user' },
        { key: 'about', label: '关于我们', icon: 'el-icon-info' },
      ],
      aboutTabs: [
        { key: 'manual', label: '使用手册', icon: 'el-icon-reading' },
        { key: 'product', label: '产品介绍', icon: 'el-icon-s-platform' },
        { key: 'timeline', label: '迭代历程', icon: 'el-icon-time' },
      ],
      manualSections: [
        { id: 'quick-start', title: '快速开始' },
        { id: 'scenarios', title: '按场景使用' },
        { id: 'conversation', title: '多轮对话' },
        { id: 'agents', title: 'Agent 配置' },
        { id: 'artifacts', title: '产物与文件' },
        { id: 'faq', title: '常见问题' },
      ],
      quickStartSteps: [
        {
          icon: 'el-icon-user',
          title: '登录平台',
          desc: '使用账号进入 WeAgent，并确认服务地址可用。',
          actions: ['输入账号和密码', '登录后进入聊天首页', '如连接失败，先检查后端地址'],
        },
        {
          icon: 'el-icon-connection',
          title: '配置模型',
          desc: '在设置中填写模型、API Key、Base URL 和推理参数。',
          actions: ['进入设置-模型设置', '选择模型或自定义模型', '保存后发一条测试消息'],
        },
        {
          icon: 'el-icon-monitor',
          title: '创建 Agent',
          desc: '配置 Agent 名称、能力标签、Skill、系统提示词和工具。',
          actions: ['进入我的 Agent', '填写能力标签和 Skill', '按任务需要绑定工具'],
        },
        {
          icon: 'el-icon-chat-dot-round',
          title: '发起会话',
          desc: '选择单 Agent 或多 Agent，开始任务对话。',
          actions: ['点击新建会话', '选择参与 Agent', '发送任务目标并查看回复'],
        },
      ],
      scenarioGuides: [
        {
          icon: 'el-icon-edit-outline',
          title: '文档生成',
          desc: '选择文档类 Agent，输入目标结构，让 Agent 生成 README、方案或总结。',
          bestFor: '适合：项目说明、需求文档、阶段总结',
          steps: ['说明文档对象和读者', '给出必须包含的章节', '要求输出 Markdown 或文件产物'],
        },
        {
          icon: 'el-icon-brush',
          title: '前端开发',
          desc: '使用前端 Agent 处理页面实现、样式调整、多端适配和交互优化。',
          bestFor: '适合：Vue 页面、组件、样式、交互修复',
          steps: ['描述目标页面和现有问题', '要求先分析相关代码', '完成后检查构建和关键交互'],
        },
        {
          icon: 'el-icon-s-operation',
          title: '多 Agent 协作',
          desc: '让主持 Agent 根据任务拆分工作，并协调多个 worker Agent 给出结果。',
          bestFor: '适合：跨模块、跨角色、需要拆解的大任务',
          steps: ['选择多个 Agent 创建会话', '让主持 Agent 先给方案', '逐步确认并推进执行结果'],
        },
        {
          icon: 'el-icon-collection-tag',
          title: '收藏复用',
          desc: '收藏重要会话，在我的收藏中快速过滤、进入和取消收藏。',
          bestFor: '适合：长期任务、重要方案、可复查结论',
          steps: ['在会话右上角点击收藏', '到我的收藏筛选会话', '进入会话继续追问或复查产物'],
        },
      ],
      promptTemplates: [
        { title: '需求澄清', content: '请先复述我的需求，列出你需要确认的问题，然后给出分阶段方案。' },
        { title: '实现任务', content: '请先分析相关代码，再实现当前阶段；完成后运行直接测试和可能受影响功能的回归测试。' },
        { title: '问题修复', content: '请定位根因，说明影响范围，给出修复方案，然后只改这个问题相关的代码。' },
      ],
      agentConfigTips: [
        { title: '能力标签', desc: '用于让主持 Agent 理解该 Agent 擅长什么，标签应简短明确。', example: '例如：Vue、接口联调、README、测试' },
        { title: '系统提示词', desc: '定义 Agent 的角色边界、回答风格和执行习惯。', example: '例如：你是前端开发专家，优先阅读代码再实现' },
        { title: 'Skill', desc: '描述 Agent 的具体工作步骤，适合写成可执行流程。', example: '例如：分析需求、定位文件、实现、构建验证' },
        { title: '会话级配置', desc: '只影响当前会话，不会覆盖全局 Agent，适合临时调整任务策略。', example: '例如：本次只关注移动端适配' },
      ],
      artifactManualItems: [
        { title: '文件产物', desc: '点击文件类型产物后，可打开文件列表并定位到对应内容，适合查看 HTML、Markdown、图片和代码文件。' },
        { title: '表格产物', desc: '部分表格不在容器目录中，平台会直接使用产物内置的列和行数据展示。' },
        { title: '进度与历史', desc: '每条 Agent 消息会保留当前进度、进度历史、执行结果和 Raw Output，方便追踪任务过程。' },
        { title: '容器文件', desc: '需要上传资料时，可将文件放入 Agent 的容器工作区，再在会话中让 Agent 使用这些文件。' },
      ],
      faqItems: [
        { question: 'Agent 没有按预期回答怎么办？', answer: '先检查 Agent 的能力标签、系统提示词和 Skill 是否足够明确；复杂任务建议让 Agent 先给方案再执行。' },
        { question: '文件或图片打不开怎么办？', answer: '优先确认后端地址、文件路径和容器文件是否存在；移动端还要确认 HTTP/HTTPS 和局域网访问权限。' },
        { question: '什么时候使用多 Agent？', answer: '当任务需要多个角色协作、跨模块分析或需要主持 Agent 拆解任务时使用多 Agent；简单问题使用单 Agent 更直接。' },
        { question: '会话级 Agent 配置会影响全局 Agent 吗？', answer: '不会。会话级配置只在当前会话生效，适合临时调整某个 Agent 在本次任务中的技能和行为。' },
      ],
      productHighlights: [
        { icon: 'el-icon-chat-line-square', title: '会话驱动', desc: '围绕任务会话沉淀上下文、历史问题、进度和产物。' },
        { icon: 'el-icon-cpu', title: '多 Agent 编排', desc: '支持单 Agent 和多 Agent 协作，按能力完成复杂任务。' },
        { icon: 'el-icon-folder-opened', title: '产物管理', desc: '集中展示文件、表格、日志和执行输出，便于复查和复用。' },
        { icon: 'el-icon-mobile', title: '多端支持', desc: '支持 Web、桌面端和 Android 端分阶段迁移与使用。' },
      ],
      timelineItems: [
        { version: '阶段 1', title: 'Web 基础能力', desc: '完成登录注册、会话列表、Agent 管理、个人设置和模型配置。' },
        { version: '阶段 2', title: '桌面端迁移', desc: '实现桌面端全量功能迁移，支持外部后端配置和桌面应用打包。' },
        { version: '阶段 3', title: 'Android 主要功能', desc: '基于 Capacitor + Vue 实现 Android 登录、会话、Agent 和设置能力。' },
        { version: '阶段 4', title: '产物与协作体验', desc: '完善产物抽屉、会话收藏、搜索定位、历史问题和会话级 Agent 配置。' },
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

/* 关于我们 */
.about-panel {
  max-width: 1120px;
}

.about-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 28px;
  margin-bottom: 18px;
  border-radius: 12px;
  background: linear-gradient(135deg, #f7fbff 0%, #eef5ff 55%, #fff7ed 100%);
  border: 1px solid #e8eef8;
}

.about-kicker {
  display: inline-flex;
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 700;
  color: #4080ff;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.about-hero h2 {
  font-size: 28px;
  margin-bottom: 8px;
}

.about-version {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  padding: 10px 14px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid rgba(64, 128, 255, 0.16);
  color: #64748b;
  font-size: 12px;
  white-space: nowrap;
}

.about-version strong {
  color: #1e293b;
  font-size: 18px;
}

.about-tabs {
  display: flex;
  gap: 8px;
  padding: 6px;
  margin-bottom: 20px;
  width: fit-content;
  border-radius: 10px;
  background: #f5f7fb;
  border: 1px solid #edf1f7;
}

.about-tab {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 34px;
  padding: 0 14px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.15s;
}

.about-tab.active {
  background: #ffffff;
  color: #4080ff;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
}

.manual-layout {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr);
  gap: 22px;
  align-items: flex-start;
}

.manual-toc {
  position: sticky;
  top: 0;
  padding: 14px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid #eef2f7;
}

.toc-title {
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
}

.toc-link {
  display: block;
  padding: 8px 10px;
  border-radius: 7px;
  color: #64748b;
  font-size: 13px;
  text-decoration: none;
}

.toc-link:hover {
  background: #eef5ff;
  color: #4080ff;
}

.manual-content {
  min-width: 0;
}

.manual-section {
  padding: 22px;
  margin-bottom: 16px;
  border: 1px solid #edf1f7;
  border-radius: 12px;
  background: #ffffff;
}

.section-heading {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  margin-bottom: 18px;
}

.section-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 9px;
  background: #eef5ff;
  color: #4080ff;
  font-weight: 700;
  flex-shrink: 0;
}

.section-heading h3,
.product-overview h3,
.timeline-panel h3 {
  margin: 0 0 6px;
  font-size: 20px;
  color: #1e293b;
}

.section-heading p,
.product-intro p,
.timeline-desc {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  color: #64748b;
}

.step-grid,
.highlight-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.step-card,
.highlight-card {
  min-height: 176px;
  padding: 16px;
  border: 1px solid #edf1f7;
  border-radius: 10px;
  background: #fbfdff;
}

.step-card i,
.highlight-card i {
  display: inline-flex;
  margin-bottom: 12px;
  font-size: 22px;
  color: #4080ff;
}

.step-card h4,
.highlight-card h4,
.scenario-item h4,
.guide-block h4 {
  margin: 0 0 7px;
  font-size: 15px;
  color: #1e293b;
}

.step-card p,
.highlight-card p,
.scenario-item p,
.guide-block li,
.mini-list li,
.compact-steps li,
.artifact-preview span {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.65;
}

.manual-note-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.manual-note {
  padding: 14px 16px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid #edf1f7;
}

.manual-note span,
.scenario-meta,
.prompt-template span,
.artifact-manual-item span {
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: 700;
  color: #4080ff;
}

.manual-note p,
.prompt-template p,
.artifact-manual-item p,
.faq-item p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.65;
}

.mini-list,
.compact-steps {
  margin: 10px 0 0;
  padding-left: 18px;
}

.mini-list li + li,
.compact-steps li + li {
  margin-top: 5px;
}

.image-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 8px;
  min-height: 180px;
  padding: 20px;
  border: 1px dashed #b8c7dd;
  border-radius: 12px;
  background: repeating-linear-gradient(
    45deg,
    #f8fbff,
    #f8fbff 10px,
    #f2f7ff 10px,
    #f2f7ff 20px
  );
  text-align: center;
  color: #64748b;
}

.image-placeholder.large {
  min-height: 240px;
  margin-top: 16px;
}

.image-placeholder i {
  font-size: 34px;
  color: #4080ff;
}

.image-placeholder strong {
  display: block;
  margin-bottom: 4px;
  color: #1e293b;
  font-size: 15px;
}

.image-placeholder span {
  display: block;
  max-width: 520px;
  font-size: 13px;
  line-height: 1.6;
}

.scenario-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.scenario-item {
  display: flex;
  gap: 12px;
  padding: 16px;
  border-radius: 10px;
  border: 1px solid #edf1f7;
  background: #fbfdff;
}

.scenario-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: #eef5ff;
  color: #4080ff;
  flex-shrink: 0;
}

.manual-two-column {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.guide-block {
  padding: 18px;
  border-radius: 10px;
  background: #fbfdff;
  border: 1px solid #edf1f7;
}

.guide-block ol {
  margin: 10px 0 0;
  padding-left: 20px;
}

.guide-block li + li {
  margin-top: 7px;
}

.prompt-template {
  padding: 10px 0;
  border-top: 1px solid #edf1f7;
}

.prompt-template:first-of-type {
  border-top: none;
  padding-top: 4px;
}

.feature-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.feature-strip span {
  padding: 9px 12px;
  border-radius: 999px;
  background: #f0f5ff;
  color: #335dbe;
  font-size: 13px;
  font-weight: 600;
}

.agent-guide-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 16px;
}

.agent-guide-card {
  padding: 16px;
  border-radius: 10px;
  background: #fbfdff;
  border: 1px solid #edf1f7;
}

.agent-guide-card h4,
.faq-item h4 {
  margin: 0 0 7px;
  font-size: 15px;
  color: #1e293b;
}

.agent-guide-card p {
  margin: 0 0 10px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.65;
}

.agent-guide-card span {
  display: inline-flex;
  padding: 6px 9px;
  border-radius: 7px;
  background: #f0f5ff;
  color: #335dbe;
  font-size: 12px;
}

.artifact-preview-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.artifact-preview {
  display: flex;
  gap: 12px;
  padding: 16px;
  border-radius: 10px;
  background: #fbfdff;
  border: 1px solid #edf1f7;
}

.artifact-preview i {
  font-size: 24px;
  color: #4080ff;
}

.artifact-preview strong {
  display: block;
  margin-bottom: 5px;
  color: #1e293b;
  font-size: 15px;
}

.artifact-manual-list,
.faq-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.artifact-manual-item,
.faq-item {
  padding: 15px 16px;
  border-radius: 10px;
  border: 1px solid #edf1f7;
  background: #fbfdff;
}

.product-overview,
.timeline-panel {
  padding: 22px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid #edf1f7;
}

.product-intro {
  margin-bottom: 18px;
}

.product-shot {
  margin-top: 16px;
}

.timeline-list {
  position: relative;
  margin-top: 18px;
  padding-left: 24px;
}

.timeline-list::before {
  content: '';
  position: absolute;
  left: 7px;
  top: 8px;
  bottom: 8px;
  width: 2px;
  background: #e5edf8;
}

.timeline-item {
  position: relative;
  display: flex;
  gap: 14px;
  padding-bottom: 20px;
}

.timeline-dot {
  position: absolute;
  left: -23px;
  top: 4px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #4080ff;
  border: 3px solid #e8f0ff;
}

.timeline-content {
  padding: 14px 16px;
  width: 100%;
  border-radius: 10px;
  background: #fbfdff;
  border: 1px solid #edf1f7;
}

.timeline-version {
  display: inline-flex;
  margin-bottom: 7px;
  font-size: 12px;
  font-weight: 700;
  color: #4080ff;
}

.timeline-content h4 {
  margin: 0 0 6px;
  font-size: 15px;
  color: #1e293b;
}

.timeline-content p {
  margin: 0;
  font-size: 13px;
  line-height: 1.65;
  color: #64748b;
}

@media (max-width: 1100px) {
  .manual-layout {
    grid-template-columns: 1fr;
  }

  .manual-toc {
    position: static;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .toc-title {
    width: 100%;
  }

  .step-grid,
  .highlight-grid,
  .manual-two-column {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .about-hero,
  .manual-two-column,
  .scenario-list,
  .artifact-preview-row,
  .manual-note-grid,
  .agent-guide-grid,
  .artifact-manual-list,
  .faq-list {
    grid-template-columns: 1fr;
  }

  .about-hero {
    display: block;
  }

  .about-version {
    align-items: flex-start;
    width: fit-content;
    margin-top: 14px;
  }

  .step-grid,
  .highlight-grid {
    grid-template-columns: 1fr;
  }
}
</style>
