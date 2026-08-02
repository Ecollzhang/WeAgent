<template>
  <div class="rd-builds-page">
    <AppSidebar />

    <main class="rd-content">
      <header class="rd-header">
        <div>
          <h2>构建管理</h2>
          <p>管理项目的构建流水线，支持 GitHub Actions 真实构建</p>
        </div>
        <div class="header-actions">
          <el-select v-model="projectId" placeholder="选择项目" size="small" style="width:200px" @change="onProjectChange" filterable>
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
          <el-button type="primary" icon="el-icon-video-play" @click="openTriggerDialog" :disabled="!projectId">
            触发构建
          </el-button>
          <el-button type="text" icon="el-icon-question" @click="guideVisible = true" title="使用指南">
            使用指南
          </el-button>
        </div>
      </header>

      <!-- 构建列表 -->
      <section class="builds-list" v-loading="loading">
        <template v-if="builds.length > 0">
          <article
            v-for="build in builds"
            :key="build.id"
            class="build-card"
            :class="'card-' + build.status"
            @click="openDetail(build)"
          >
            <div class="build-card-accent" :class="'accent-' + build.status"></div>
            <div class="build-card-left">
              <div class="build-icon-circle" :class="'icon-' + build.status">
                <i v-if="build.status === 'success'" class="el-icon-check"></i>
                <i v-else-if="build.status === 'failed'" class="el-icon-close"></i>
                <i v-else-if="build.status === 'running'" class="el-icon-loading"></i>
                <i v-else-if="build.status === 'cancelled'" class="el-icon-remove-outline"></i>
                <i v-else class="el-icon-time"></i>
              </div>
            </div>
            <div class="build-card-body">
              <div class="build-card-top">
                <div class="build-card-title">
                  <span class="build-num">#{{ build.build_number }}</span>
                  <span class="build-msg">{{ build.commit_message }}</span>
                  <span v-if="build.github_run_id" class="build-gh-badge">
                    <i class="el-icon-s-platform"></i> Actions
                  </span>
                </div>
                <div class="build-card-tags">
                  <span class="build-tag" :class="'tag-' + build.status">{{ statusLabel(build.status) }}</span>
                  <span class="build-tag tag-type">{{ buildTypeLabel(build.build_type) }}</span>
                </div>
              </div>
              <div class="build-card-meta">
                <span class="meta-item"><i class="el-icon-share"></i>{{ build.branch || '—' }}</span>
                <span class="meta-item" v-if="build.commit_hash"><i class="el-icon-edit-outline"></i>{{ build.commit_hash.substring(0, 7) }}</span>
                <span class="meta-item"><i class="el-icon-time"></i>{{ formatDuration(build.duration_seconds) }}</span>
                <span class="meta-item" v-if="build.artifacts && build.artifacts.length"><i class="el-icon-paperclip"></i>{{ build.artifacts.length }} 产物</span>
                <span class="meta-item meta-date">{{ formatTime(build.started_at) }}</span>
              </div>
              <div class="build-card-steps" v-if="build.steps && build.steps.length">
                <div class="steps-bar">
                  <div
                    v-for="step in build.steps"
                    :key="step.step_order"
                    class="steps-bar-seg"
                    :class="'seg-' + step.status"
                    :title="step.step_name"
                  ></div>
                </div>
                <span class="steps-count">{{ build.steps.filter(s => s.status === 'success').length }}/{{ build.steps.length }} 通过</span>
              </div>
              <div class="build-card-step-names" v-if="build.steps && build.steps.length">
                <span
                  v-for="step in build.steps.slice(0, 4)"
                  :key="step.step_order"
                  class="step-name-tag"
                  :class="'snt-' + step.status"
                >{{ step.step_name }}</span>
                <span v-if="build.steps.length > 4" class="step-name-more">+{{ build.steps.length - 4 }}</span>
              </div>
              <div class="build-card-footer">
                <a v-if="build.preview_url" :href="build.preview_url" target="_blank" class="card-gh-link" @click.stop>
                  <i class="el-icon-s-platform"></i> 在 GitHub 查看
                </a>
                <div class="build-card-actions" @click.stop>
                  <el-button v-if="build.github_run_id" type="text" size="small" icon="el-icon-refresh" @click="handleSyncBuild(build)">刷新</el-button>
                  <el-button type="text" size="small" icon="el-icon-delete" style="color:#f56c6c" @click="handleDeleteBuild(build)">删除</el-button>
                </div>
              </div>
            </div>
          </article>
        </template>
        <div v-else class="empty-state">
          <div class="empty-icon"><i class="el-icon-s-tools"></i></div>
          <h3>暂无构建记录</h3>
          <p>关联 GitHub 仓库后，可触发 CI/CD 流水线构建</p>
        </div>
      </section>
    </main>

    <!-- ==================== 构建详情侧栏 ==================== -->
    <transition name="panel-slide">
      <div class="detail-overlay" v-if="detailVisible" @click.self="detailVisible = false">
        <div class="detail-panel">
          <div class="detail-panel-header">
            <div class="detail-panel-title">
              <span class="detail-build-num">#{{ selectedBuild.build_number }}</span>
              <span class="detail-build-msg">{{ selectedBuild.commit_message }}</span>
            </div>
            <div class="detail-panel-header-actions">
              <el-button v-if="selectedBuild.github_run_id" type="text" size="small" icon="el-icon-refresh" @click="handleSyncBuild(selectedBuild)">刷新</el-button>
              <a v-if="selectedBuild.preview_url" :href="selectedBuild.preview_url" target="_blank" class="gh-link-btn">
                <i class="el-icon-s-platform"></i> GitHub
              </a>
              <i class="el-icon-close detail-close-btn" @click="detailVisible = false"></i>
            </div>
          </div>

          <div class="detail-panel-body" v-if="selectedBuild">
            <!-- 状态横幅 -->
            <div class="detail-status-bar" :class="'bar-' + selectedBuild.status">
              <div class="detail-status-icon" :class="'icon-' + selectedBuild.status">
                <i v-if="selectedBuild.status === 'success'" class="el-icon-circle-check"></i>
                <i v-else-if="selectedBuild.status === 'failed'" class="el-icon-circle-close"></i>
                <i v-else-if="selectedBuild.status === 'running'" class="el-icon-loading"></i>
                <i v-else-if="selectedBuild.status === 'cancelled'" class="el-icon-remove-outline"></i>
                <i v-else class="el-icon-time"></i>
              </div>
              <div class="detail-status-info">
                <strong>{{ statusLabel(selectedBuild.status) }}</strong>
                <span v-if="selectedBuild.status === 'success' || selectedBuild.status === 'failed'">耗时 {{ formatDuration(selectedBuild.duration_seconds) }}</span>
                <span v-else-if="selectedBuild.status === 'running'">运行中...</span>
              </div>
            </div>

            <!-- 错误摘要 -->
            <div class="detail-error" v-if="selectedBuild.error_summary">
              <i class="el-icon-warning"></i>
              <span>{{ selectedBuild.error_summary }}</span>
            </div>

            <!-- 信息卡片 -->
            <div class="detail-info-cards">
              <div class="info-card">
                <div class="info-card-icon"><i class="el-icon-share"></i></div>
                <div class="info-card-body">
                  <span class="info-label">分支</span>
                  <span class="info-value mono">{{ selectedBuild.branch || '—' }}</span>
                </div>
              </div>
              <div class="info-card" v-if="selectedBuild.commit_hash">
                <div class="info-card-icon"><i class="el-icon-edit-outline"></i></div>
                <div class="info-card-body">
                  <span class="info-label">提交</span>
                  <span class="info-value mono">{{ selectedBuild.commit_hash.substring(0, 7) }}</span>
                </div>
              </div>
              <div class="info-card">
                <div class="info-card-icon"><i class="el-icon-s-operation"></i></div>
                <div class="info-card-body">
                  <span class="info-label">触发方式</span>
                  <span class="info-value">{{ buildTypeLabel(selectedBuild.build_type) }}</span>
                </div>
              </div>
              <div class="info-card">
                <div class="info-card-icon"><i class="el-icon-time"></i></div>
                <div class="info-card-body">
                  <span class="info-label">时间</span>
                  <span class="info-value">{{ formatTime(selectedBuild.started_at) }}</span>
                </div>
              </div>
            </div>

            <!-- 构建步骤 -->
            <div class="detail-section" v-if="selectedBuild.steps && selectedBuild.steps.length">
              <div class="detail-section-header">
                <h4><i class="el-icon-s-operation"></i> 构建步骤</h4>
                <span class="section-badge">{{ selectedBuild.steps.filter(s => s.status === 'success').length }}/{{ selectedBuild.steps.length }} 通过</span>
              </div>
              <div class="steps-timeline">
                <div class="steps-track"></div>
                <div
                  v-for="(step, idx) in selectedBuild.steps"
                  :key="step.step_order"
                  class="steps-node"
                  :class="'node-' + step.status"
                >
                  <div class="node-indicator">
                    <i v-if="step.status === 'success'" class="el-icon-check"></i>
                    <i v-else-if="step.status === 'failed'" class="el-icon-close"></i>
                    <i v-else-if="step.status === 'running'" class="el-icon-loading"></i>
                    <i v-else-if="step.status === 'skipped'" class="el-icon-minus"></i>
                    <i v-else class="el-icon-more-outline"></i>
                  </div>
                  <div class="node-card">
                    <div class="node-header">
                      <span class="node-name">{{ step.step_order }}. {{ step.step_name }}</span>
                      <span class="node-duration" v-if="step.duration_seconds">{{ step.duration_seconds }}s</span>
                      <span class="node-tag" :class="'tag-' + step.status">{{ stepStatusLabel(step.status) }}</span>
                    </div>
                    <div class="node-command" v-if="step.command">
                      <code>{{ step.command }}</code>
                    </div>
                    <div class="node-log" v-if="step.log" @click.stop>
                      <pre :class="{ 'log-expanded': expandedLogs[step.step_order] }">{{ step.log }}</pre>
                      <el-button
                        v-if="step.log.length > 300"
                        type="text" size="mini"
                        @click="toggleLog(step.step_order)"
                      >{{ expandedLogs[step.step_order] ? '收起日志' : '展开完整日志' }}</el-button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 构建产物 -->
            <div class="detail-section" v-if="selectedBuild.artifacts && selectedBuild.artifacts.length">
              <div class="detail-section-header">
                <h4><i class="el-icon-paperclip"></i> 构建产物</h4>
                <span class="section-badge">{{ selectedBuild.artifacts.length }} 个</span>
              </div>
              <div class="artifacts-grid">
                <div
                  v-for="art in selectedBuild.artifacts"
                  :key="art.id || art.name"
                  class="artifact-card"
                  @click="downloadArtifact(selectedBuild.id, art)"
                >
                  <div class="artifact-icon">
                    <i class="el-icon-folder-opened"></i>
                  </div>
                  <div class="artifact-info">
                    <span class="artifact-name">{{ typeof art === 'string' ? art : art.name }}</span>
                    <span class="artifact-size" v-if="art.size_bytes">{{ formatFileSize(art.size_bytes) }}</span>
                  </div>
                  <div class="artifact-dl-icon">
                    <i class="el-icon-download"></i>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- ==================== 触发构建对话框 ==================== -->
    <el-dialog title="触发构建" :visible.sync="triggerVisible" width="550px" :close-on-click-modal="false">
      <el-form label-width="80px" size="small">
        <el-form-item label="选择仓库">
          <el-select v-model="triggerRepoId" placeholder="选择 GitHub 仓库" style="width:100%" @change="onTriggerRepoChange" filterable>
            <el-option v-for="r in triggerRepos" :key="r.id" :label="r.full_name" :value="r.id">
              <span>{{ r.full_name }}</span>
              <span style="float:right;color:#909399;font-size:12px">{{ r.workflow_count }} workflows</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="选择流水线">
          <el-select v-model="triggerWorkflowId" placeholder="选择 workflow" style="width:100%" :disabled="!triggerRepoId">
            <el-option v-for="w in triggerWorkflows" :key="w.id" :label="w.name" :value="w.id">
              <span>{{ w.name }}</span>
              <span style="float:right;color:#909399;font-size:12px">{{ w.path }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="目标分支">
          <el-input v-model="triggerBranch" placeholder="分支名，默认 main" />
        </el-form-item>
      </el-form>
      <div slot="footer">
        <el-button @click="triggerVisible = false">取消</el-button>
        <el-button type="primary" :loading="triggering" :disabled="!triggerWorkflowId" @click="submitTriggerBuild">
          触发构建
        </el-button>
      </div>
    </el-dialog>

    <!-- ==================== 使用指南对话框 ==================== -->
    <el-dialog :visible.sync="guideVisible" width="780px" :close-on-click-modal="false">
      <div slot="title" class="guide-dialog-title">
        <span class="guide-title-icon"><i class="el-icon-s-opportunity"></i></span>
        <span>GitHub Actions 构建指南</span>
      </div>
      <div class="guide-content">
        <!-- 什么是 GitHub Actions -->
        <section class="guide-section guide-intro">
          <div class="guide-intro-card">
            <div class="guide-intro-icon">
              <i class="el-icon-s-opportunity"></i>
            </div>
            <div class="guide-intro-body">
              <h3>什么是 GitHub Actions</h3>
              <p>GitHub Actions 是 GitHub 内置的 CI/CD 服务，可以通过编写 YAML 配置文件来定义自动化工作流（workflow），实现代码构建、测试、部署等操作。本平台通过调用 GitHub Actions API，直接触发你仓库中已配置的 workflow，并同步运行状态和日志。</p>
            </div>
          </div>
        </section>

        <!-- 第一步：创建 Workflow 文件 -->
        <section class="guide-section">
          <div class="guide-section-header">
            <span class="guide-step-badge">1</span>
            <h3>创建 Workflow 文件</h3>
          </div>
          <p>在你的 GitHub 仓库中创建 <code>.github/workflows/build.yml</code> 文件（文件名可自定义）：</p>
          <div class="guide-code-wrapper">
            <div class="guide-code-header">
              <span class="code-lang-label">YAML</span>
              <span class="code-file-path">.github/workflows/build.yml</span>
              <span class="code-copy-btn" @click="copyGuideCode('main')">
                <i class="el-icon-document-copy"></i> 复制
              </span>
            </div>
            <div class="guide-code">
              <pre><code>name: Build and Test

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  # 关键：允许手动触发
  workflow_dispatch:
    inputs:
      environment:
        description: '部署环境'
        required: false
        default: 'staging'
        type: choice
        options:
          - staging
          - production

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        run: npm ci

      - name: Run tests
        run: npm test

      - name: Build
        run: npm run build

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/</code></pre>
            </div>
          </div>
          <div class="guide-tip">
            <div class="guide-tip-icon">
              <i class="el-icon-warning-outline"></i>
            </div>
            <div class="guide-tip-body">
              <strong>重要提示</strong>
              <p>必须包含 <code>workflow_dispatch</code> 事件，否则平台无法手动触发该 workflow。</p>
            </div>
          </div>
        </section>

        <!-- 第二步：推送到 GitHub -->
        <section class="guide-section">
          <div class="guide-section-header">
            <span class="guide-step-badge">2</span>
            <h3>推送到 GitHub</h3>
          </div>
          <div class="guide-steps">
            <div class="guide-step">
              <div class="guide-step-marker">
                <span class="step-dot-num">1</span>
                <div class="step-connector"></div>
              </div>
              <div class="guide-step-card">
                <div class="guide-step-icon"><i class="el-icon-upload"></i></div>
                <div class="guide-step-text">
                  <strong>提交并推送</strong>
                  <span>将 <code>.github/workflows/build.yml</code> 提交并推送到仓库</span>
                </div>
              </div>
            </div>
            <div class="guide-step">
              <div class="guide-step-marker">
                <span class="step-dot-num">2</span>
                <div class="step-connector"></div>
              </div>
              <div class="guide-step-card">
                <div class="guide-step-icon"><i class="el-icon-view"></i></div>
                <div class="guide-step-text">
                  <strong>确认 Workflow</strong>
                  <span>进入仓库的 <strong>Actions</strong> 标签页确认 workflow 已出现</span>
                </div>
              </div>
            </div>
            <div class="guide-step">
              <div class="guide-step-marker">
                <span class="step-dot-num">3</span>
              </div>
              <div class="guide-step-card">
                <div class="guide-step-icon"><i class="el-icon-video-play"></i></div>
                <div class="guide-step-text">
                  <strong>触发构建</strong>
                  <span>回到本平台，触发构建时即可选择该 workflow</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- 多语言构建示例 -->
        <section class="guide-section">
          <div class="guide-section-header">
            <span class="guide-step-badge guide-step-badge--lang"><i class="el-icon-s-tools"></i></span>
            <h3>多语言构建示例</h3>
          </div>
          <el-tabs type="card" class="guide-tabs">
            <el-tab-pane label="Node.js / 前端">
              <div class="guide-code-wrapper">
                <div class="guide-code-header">
                  <span class="code-lang-label lang-js">Node.js</span>
                </div>
                <div class="guide-code"><pre><code>jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: npm ci && npm run build</code></pre></div>
              </div>
            </el-tab-pane>
            <el-tab-pane label="Python">
              <div class="guide-code-wrapper">
                <div class="guide-code-header">
                  <span class="code-lang-label lang-py">Python</span>
                </div>
                <div class="guide-code"><pre><code>jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt && pytest</code></pre></div>
              </div>
            </el-tab-pane>
            <el-tab-pane label="Java / Maven">
              <div class="guide-code-wrapper">
                <div class="guide-code-header">
                  <span class="code-lang-label lang-java">Java</span>
                </div>
                <div class="guide-code"><pre><code>jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'
      - run: mvn clean package</code></pre></div>
              </div>
            </el-tab-pane>
            <el-tab-pane label="Go">
              <div class="guide-code-wrapper">
                <div class="guide-code-header">
                  <span class="code-lang-label lang-go">Go</span>
                </div>
                <div class="guide-code"><pre><code>jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with: { go-version: '1.21' }
      - run: go build ./... && go test ./...</code></pre></div>
              </div>
            </el-tab-pane>
            <el-tab-pane label="Docker">
              <div class="guide-code-wrapper">
                <div class="guide-code-header">
                  <span class="code-lang-label lang-docker">Docker</span>
                </div>
                <div class="guide-code"><pre><code>jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t myapp .
      - run: docker push myapp:latest</code></pre></div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </section>

        <!-- 参考链接 -->
        <section class="guide-section">
          <div class="guide-section-header">
            <span class="guide-step-badge guide-step-badge--link"><i class="el-icon-link"></i></span>
            <h3>参考链接</h3>
          </div>
          <div class="guide-links">
            <a href="https://docs.github.com/actions" target="_blank" class="guide-link-card">
              <span class="guide-link-icon" style="background:#e8f4fd;"><i class="el-icon-reading" style="color:#409eff;"></i></span>
              <span class="guide-link-info">
                <strong>GitHub Actions 官方文档</strong>
                <small>docs.github.com/actions</small>
              </span>
              <i class="el-icon-arrow-right guide-link-arrow"></i>
            </a>
            <a href="https://docs.github.com/actions/using-workflows/workflow-syntax-for-github-actions" target="_blank" class="guide-link-card">
              <span class="guide-link-icon" style="background:#f0f5ff;"><i class="el-icon-document-copy" style="color:#6370ff;"></i></span>
              <span class="guide-link-info">
                <strong>Workflow 语法参考</strong>
                <small>docs.github.com/actions</small>
              </span>
              <i class="el-icon-arrow-right guide-link-arrow"></i>
            </a>
            <a href="https://docs.github.com/actions/using-workflows/events-that-trigger-workflows#workflow_dispatch" target="_blank" class="guide-link-card">
              <span class="guide-link-icon" style="background:#fef0e6;"><i class="el-icon-s-operation" style="color:#e6a23c;"></i></span>
              <span class="guide-link-info">
                <strong>workflow_dispatch 事件</strong>
                <small>docs.github.com/actions</small>
              </span>
              <i class="el-icon-arrow-right guide-link-arrow"></i>
            </a>
            <a href="https://github.com/marketplace?type=actions" target="_blank" class="guide-link-card">
              <span class="guide-link-icon" style="background:#f5f0ff;"><i class="el-icon-shopping-bag-1" style="color:#8b5cf6;"></i></span>
              <span class="guide-link-info">
                <strong>Actions Marketplace</strong>
                <small>github.com/marketplace</small>
              </span>
              <i class="el-icon-arrow-right guide-link-arrow"></i>
            </a>
            <a href="https://docs.github.com/actions/using-workflows/reusing-workflows" target="_blank" class="guide-link-card">
              <span class="guide-link-icon" style="background:#e8faf0;"><i class="el-icon-connection" style="color:#67c23a;"></i></span>
              <span class="guide-link-info">
                <strong>复用 Workflow</strong>
                <small>docs.github.com/actions</small>
              </span>
              <i class="el-icon-arrow-right guide-link-arrow"></i>
            </a>
          </div>
        </section>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import AppSidebar from '@/components/Sidebar/index.vue'
import { getProjects, getBuilds, triggerBuild, getBuild, syncBuild, deleteBuild, getReposForBuild, getWorkflows, getArtifactDownloadUrl } from '@/api/rd'

export default {
  name: 'RdBuilds',
  components: { AppSidebar },
  data() {
    return {
      loading: false,
      detailVisible: false,
      selectedBuild: null,
      builds: [],
      projects: [],
      projectId: '',

      // 触发构建对话框
      triggerVisible: false,
      triggering: false,
      guideVisible: false,
      pollTimer: null,
      triggerRepos: [],
      triggerRepoId: '',
      triggerWorkflows: [],
      triggerWorkflowId: '',
      triggerBranch: 'main',
      expandedLogs: {},
    }
  },
  async created() {
    // 支持从其他页面跳转并指定项目和构建
    if (this.$route.query.project_id) {
      this.projectId = this.$route.query.project_id
    }
    await this.loadProjects()
    // 如果有 build_id，自动展开对应构建详情
    if (this.$route.query.build_id) {
      this.$nextTick(() => {
        const b = this.builds.find(x => x.id === this.$route.query.build_id)
        if (b) this.openDetail(b)
      })
    }
  },
  beforeDestroy() {
    this.stopPolling()
  },
  methods: {
    async loadProjects() {
      try {
        const res = await getProjects()
        if (res.code === 200) {
          this.projects = res.data.items || []
          if (this.projects.length > 0 && !this.projectId) {
            this.projectId = this.projects[0].id
          }
          if (this.projectId) {
            await this.loadBuilds()
          }
        }
      } catch (e) {
        console.error('加载项目列表失败', e)
      }
    },
    async onProjectChange(pid) {
      this.projectId = pid
      this.builds = []
      if (pid) await this.loadBuilds()
    },
    async loadBuilds() {
      if (!this.projectId) return
      this.loading = true
      try {
        const res = await getBuilds(this.projectId)
        if (res.code === 200) {
          this.builds = res.data.items || []
          // 如果有运行中的构建，开始轮询
          if (this.builds.some(b => (b.status === 'running' || b.status === 'pending') && b.github_run_id)) {
            this.startPolling()
          }
        }
      } catch (e) {
        console.error('加载构建列表失败', e)
        this.$message.error('加载构建列表失败')
      } finally {
        this.loading = false
      }
    },
    statusLabel(s) {
      return {
        success: '通过', failed: '失败', running: '运行中',
        pending: '等待中', cancelled: '已取消'
      }[s] || s
    },
    stepStatusLabel(s) {
      return {
        success: '成功', failed: '失败', running: '运行中',
        pending: '等待', skipped: '跳过'
      }[s] || s
    },
    buildTypeLabel(t) {
      return { manual: '手动触发', push: '代码推送', schedule: '定时触发', mr: '合并请求' }[t] || t
    },
    formatRelative(iso) {
      if (!iso) return ''
      const diff = Date.now() - new Date(iso).getTime()
      const days = Math.floor(diff / 86400000)
      if (days < 1) return '今天'
      if (days < 2) return '昨天'
      if (days < 30) return days + ' 天前'
      return Math.floor(days / 30) + ' 月前'
    },
    formatTime(iso) {
      if (!iso) return ''
      const d = new Date(iso)
      return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0') + ' ' + String(d.getHours()).padStart(2,'0') + ':' + String(d.getMinutes()).padStart(2,'0')
    },
    formatDuration(sec) {
      if (!sec) return '0s'
      if (sec < 60) return sec + 's'
      return Math.floor(sec / 60) + 'm ' + (sec % 60) + 's'
    },
    openDetail(build) {
      this.selectedBuild = build
      this.detailVisible = true
    },

    // ── 触发构建 ────────────────────────────────────────

    async openTriggerDialog() {
      if (!this.projectId) return this.$message.warning('请先选择项目')
      this.triggerVisible = true
      this.triggerRepoId = ''
      this.triggerWorkflowId = ''
      this.triggerWorkflows = []
      this.triggerBranch = 'main'
      await this.loadTriggerRepos()
    },

    async loadTriggerRepos() {
      try {
        const res = await getReposForBuild(this.projectId)
        if (res.code === 200) {
          this.triggerRepos = res.data.items || []
          if (this.triggerRepos.length === 0) {
            this.$message.warning('该项目暂无关联仓库，请先在仓库管理中关联 GitHub 仓库')
          }
        }
      } catch (e) {
        console.error('加载仓库列表失败', e)
        this.$message.error('加载仓库列表失败')
      }
    },

    async onTriggerRepoChange(repoId) {
      this.triggerWorkflowId = ''
      this.triggerWorkflows = []
      if (!repoId) return
      try {
        const res = await getWorkflows(repoId)
        if (res.code === 200) {
          this.triggerWorkflows = res.data.items || []
          if (this.triggerWorkflows.length === 0) {
            this.$message.warning('该仓库没有可用的 workflow，请确认已配置 workflow_dispatch 触发方式')
          }
        }
      } catch (e) {
        console.error('加载 workflows 失败', e)
        this.$message.error('加载 workflows 失败，请确认已授权 GitHub')
      }
    },

    async submitTriggerBuild() {
      if (!this.triggerWorkflowId) return this.$message.warning('请选择流水线')
      this.triggering = true
      try {
        const res = await triggerBuild(this.projectId, {
          repo_id: this.triggerRepoId,
          workflow_id: this.triggerWorkflowId,
          branch: this.triggerBranch || 'main',
          commit_message: `手动触发: ${this.triggerBranch}`,
        })
        if (res.code === 201) {
          this.builds.unshift(res.data)
          this.$message.success('构建已触发')
          this.triggerVisible = false
          // 开始轮询同步状态
          this.startPolling()
        } else {
          this.$message.error(res.message || '触发失败')
        }
      } catch (e) {
        console.error('触发构建失败', e)
        this.$message.error('触发构建失败，请确认已授权 GitHub 且仓库中有 workflow_dispatch')
      } finally {
        this.triggering = false
      }
    },

    // ── 同步 ────────────────────────────────────────────

    startPolling() {
      this.stopPolling()
      this.pollTimer = setInterval(() => {
        this.pollRunningBuilds()
      }, 8000)
    },

    stopPolling() {
      if (this.pollTimer) {
        clearInterval(this.pollTimer)
        this.pollTimer = null
      }
    },

    async pollRunningBuilds() {
      // 检查是否有需要轮询的构建
      const running = this.builds.filter(
        b => (b.status === 'running' || b.status === 'pending') && b.github_run_id
      )
      if (running.length === 0) {
        this.stopPolling()
        return
      }
      // 逐个同步
      for (const b of running) {
        try {
          await syncBuild(b.id)
        } catch {}
      }
      await this.loadBuilds()
      // 同步详情弹窗
      if (this.detailVisible && this.selectedBuild) {
        const updated = await getBuild(this.selectedBuild.id)
        if (updated.code === 200) this.selectedBuild = updated.data
      }
    },

    async handleSyncBuild(build) {
      if (!build.github_run_id) return
      try {
        const res = await syncBuild(build.id)
        if (res.code === 200) {
          this.$message.success('已同步')
          await this.loadBuilds()
          if (this.detailVisible && this.selectedBuild?.id === build.id) {
            const updated = await getBuild(build.id)
            if (updated.code === 200) this.selectedBuild = updated.data
          }
        }
      } catch (e) {
        console.error('同步失败', e)
        this.$message.error('同步失败')
      }
    },

    // ── 复制指南代码 ────────────────────────────────────

    copyGuideCode() {
      const code = `name: Build and Test

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  workflow_dispatch:
    inputs:
      environment:
        description: '部署环境'
        required: false
        default: 'staging'
        type: choice
        options:
          - staging
          - production

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      - name: Install dependencies
        run: npm ci
      - name: Run tests
        run: npm test
      - name: Build
        run: npm run build
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/`
      navigator.clipboard.writeText(code).then(() => {
        this.$message.success('已复制到剪贴板')
      }).catch(() => {
        this.$message.info('复制失败，请手动复制')
      })
    },

    // ── 日志展开 ────────────────────────────────────────

    toggleLog(stepOrder) {
      this.$set(this.expandedLogs, stepOrder, !this.expandedLogs[stepOrder])
    },

    // ── 产物下载 ────────────────────────────────────────

    downloadArtifact(buildId, art) {
      const artId = typeof art === 'string' ? null : art.id
      if (!artId) {
        this.$message.info('该产物信息不完整，无法下载')
        return
      }
      const url = getArtifactDownloadUrl(buildId, artId)
      window.open(url, '_blank')
    },

    formatFileSize(bytes) {
      if (!bytes) return ''
      if (bytes < 1024) return bytes + ' B'
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
      return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    },

    // ── 删除 ────────────────────────────────────────────

    async handleDeleteBuild(build) {
      try {
        await this.$confirm('确定要删除构建 #' + build.build_number + ' 吗？', '确认删除', {
          type: 'warning',
          confirmButtonText: '删除',
          cancelButtonText: '取消',
        })
        await deleteBuild(build.id)
        this.$message.success('已删除')
        if (this.detailVisible && this.selectedBuild?.id === build.id) {
          this.detailVisible = false
        }
        await this.loadBuilds()
      } catch (e) {
        if (e !== 'cancel') {
          console.error('删除失败', e)
          this.$message.error('删除失败')
        }
      }
    },
  },
}
</script>

<style scoped>
.rd-builds-page {
  display: flex;
  gap: 12px;
  padding: 12px;
  height: 100vh;
  background: linear-gradient(135deg, #e8f0ff 0%, #f0f5ff 50%, #f5f7fa 100%);
  overflow: hidden;
}
.rd-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  overflow: hidden;
}
.rd-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0;
  padding: 18px 22px;
  border-bottom: 1px solid #f0f0f0;
  min-height: 76px;
}
.rd-header h2 { margin: 0 0 4px; font-size: 20px; color: #1e293b; }
.rd-header p { margin: 4px 0 0; font-size: 13px; color: #86909c; }
.header-actions { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }

/* 构建列表 */
.builds-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px 22px 24px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* ── 构建卡片 ── */
.build-card {
  position: relative;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #edf0f4;
  display: flex;
  gap: 0;
  cursor: pointer;
  transition: all 0.2s;
  overflow: hidden;
}
.build-card:hover {
  box-shadow: 0 6px 20px rgba(0,0,0,0.07);
  transform: translateY(-2px);
  border-color: #d8dde5;
}
.build-card-accent {
  width: 4px;
  flex-shrink: 0;
  border-radius: 12px 0 0 12px;
}
.accent-success { background: #67c23a; }
.accent-failed  { background: #f56c6c; }
.accent-running { background: #e6a23c; animation: pulse-accent 1.5s infinite; }
.accent-pending { background: #c0c4cc; }
.accent-cancelled { background: #c0c4cc; }
@keyframes pulse-accent {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.build-card-left {
  display: flex;
  align-items: center;
  padding: 18px 0 18px 16px;
}
.build-icon-circle {
  width: 42px; height: 42px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}
.icon-success { background: #e8f8e8; color: #67c23a; }
.icon-failed  { background: #fef0f0; color: #f56c6c; }
.icon-running { background: #fef6e8; color: #e6a23c; }
.icon-pending, .icon-cancelled { background: #f0f2f5; color: #c0c4cc; }

.build-card-body {
  flex: 1; min-width: 0;
  padding: 16px 18px 14px;
}
.build-card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
  gap: 10px;
}
.build-card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  min-width: 0;
}
.build-num {
  font-size: 15px;
  font-weight: 700;
  color: #1e293b;
  white-space: nowrap;
}
.build-msg {
  font-size: 13.5px;
  color: #475569;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 260px;
}
.build-gh-badge {
  font-size: 10.5px;
  color: #6366f1;
  background: #eef2ff;
  padding: 2px 8px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-weight: 500;
  white-space: nowrap;
}

.build-card-tags { display: flex; gap: 6px; align-items: center; flex-shrink: 0; }
.build-tag {
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}
.tag-success { background: #e8f8e8; color: #529b2e; }
.tag-failed  { background: #fef0f0; color: #d54949; }
.tag-running { background: #fef6e8; color: #b88230; }
.tag-pending { background: #f0f2f5; color: #909399; }
.tag-cancelled { background: #f0f2f5; color: #909399; }
.tag-type { background: #f5f7fa; color: #86909c; }

.build-card-meta {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.meta-item {
  font-size: 12px;
  color: #86909c;
  display: flex;
  align-items: center;
  gap: 4px;
}
.meta-item i { font-size: 13px; }
.meta-date { color: #a0a7b0; }

/* ── 步骤进度条 ── */
.build-card-steps {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.steps-bar {
  display: flex;
  gap: 3px;
  flex: 1;
  max-width: 200px;
}
.steps-bar-seg {
  height: 4px;
  border-radius: 2px;
  flex: 1;
  min-width: 8px;
}
.seg-success { background: #67c23a; }
.seg-failed  { background: #f56c6c; }
.seg-running { background: #e6a23c; animation: pulse-accent 1.5s infinite; }
.seg-pending, .seg-skipped { background: #e4e7ed; }
.steps-count {
  font-size: 11px;
  color: #a0a7b0;
  white-space: nowrap;
}

.build-card-step-names {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}
.step-name-tag {
  font-size: 10.5px;
  padding: 1px 7px;
  border-radius: 4px;
  background: #f5f7fa;
  color: #86909c;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.snt-success { background: #e8f8e8; color: #529b2e; }
.snt-failed  { background: #fef0f0; color: #d54949; }
.snt-running { background: #fef6e8; color: #b88230; }
.step-name-more {
  font-size: 10.5px;
  color: #a0a7b0;
  padding: 1px 4px;
}

.build-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 4px;
}
.card-gh-link {
  font-size: 11.5px;
  color: #6366f1;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 3px;
}
.card-gh-link:hover { text-decoration: underline; }

.build-card-actions {
  display: flex;
  gap: 4px;
  margin-left: auto;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 80px 16px;
}
.empty-icon {
  width: 72px; height: 72px;
  border-radius: 50%;
  background: #f5f7fa;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
}
.empty-icon i { font-size: 32px; color: #c0c4cc; }
.empty-state h3 { margin: 0 0 8px; color: #606266; font-size: 16px; font-weight: 600; }
.empty-state p { margin: 0; color: #a0a7b0; font-size: 13px; }

/* ════════════════════════════════════════════════════════════
   详情侧栏
   ════════════════════════════════════════════════════════════ */
.detail-overlay {
  position: fixed;
  top: 0; right: 0; bottom: 0; left: 0;
  background: rgba(15, 23, 42, 0.35);
  z-index: 2000;
  display: flex;
  justify-content: flex-end;
}
.detail-panel {
  width: 62vw;
  min-width: 560px;
  max-width: 960px;
  height: 100vh;
  background: #fff;
  box-shadow: -8px 0 40px rgba(0,0,0,0.12);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 侧栏滑入动画 */
.panel-slide-enter-active, .panel-slide-leave-active {
  transition: opacity 0.25s;
}
.panel-slide-enter-active .detail-panel, .panel-slide-leave-active .detail-panel {
  transition: transform 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}
.panel-slide-enter { opacity: 0; }
.panel-slide-enter .detail-panel { transform: translateX(100%); }
.panel-slide-leave-to { opacity: 0; }
.panel-slide-leave-to .detail-panel { transform: translateX(100%); }

/* ── 面板头部 ── */
.detail-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid #edf0f4;
  flex-shrink: 0;
}
.detail-panel-title {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.detail-build-num {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
}
.detail-build-msg {
  font-size: 14px;
  color: #64748b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.detail-panel-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.gh-link-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #6366f1;
  text-decoration: none;
  padding: 4px 10px;
  border-radius: 6px;
  background: #eef2ff;
  transition: background 0.2s;
}
.gh-link-btn:hover { background: #e0e7ff; }
.detail-close-btn {
  font-size: 20px;
  color: #94a3b8;
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  transition: all 0.15s;
}
.detail-close-btn:hover { color: #475569; background: #f1f5f9; }

/* ── 面板内容 ── */
.detail-panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px 32px;
}
.detail-panel-body::-webkit-scrollbar { width: 5px; }
.detail-panel-body::-webkit-scrollbar-thumb { background: #d9dde3; border-radius: 10px; }

/* ── 状态横幅 ── */
.detail-status-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
  border-radius: 12px;
  margin-bottom: 16px;
}
.bar-success { background: linear-gradient(135deg, #e8f8e8, #d4f0d4); }
.bar-failed  { background: linear-gradient(135deg, #fef0f0, #fde0e0); }
.bar-running { background: linear-gradient(135deg, #fef6e8, #fef0d0); }
.bar-pending { background: #f5f7fa; }
.bar-cancelled { background: #f5f7fa; }

.detail-status-icon {
  width: 44px; height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
}
.detail-status-icon.icon-success { background: #fff; color: #67c23a; box-shadow: 0 2px 8px rgba(103,194,58,0.2); }
.detail-status-icon.icon-failed  { background: #fff; color: #f56c6c; box-shadow: 0 2px 8px rgba(245,108,108,0.2); }
.detail-status-icon.icon-running { background: #fff; color: #e6a23c; box-shadow: 0 2px 8px rgba(230,162,60,0.2); }
.detail-status-icon.icon-pending, .detail-status-icon.icon-cancelled { background: #fff; color: #c0c4cc; }

.detail-status-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.detail-status-info strong {
  font-size: 16px;
  color: #1e293b;
  font-weight: 700;
}
.detail-status-info span {
  font-size: 12.5px;
  color: #64748b;
}

/* 错误 */
.detail-error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 10px;
  padding: 12px 16px;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  color: #f56c6c;
  margin-bottom: 16px;
}
.detail-error i { margin-top: 2px; flex-shrink: 0; }

/* ── 信息卡片 ── */
.detail-info-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 20px;
}
.info-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid #edf0f4;
}
.info-card-icon {
  width: 34px; height: 34px;
  border-radius: 8px;
  background: #ecf5ff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  color: #409eff;
  flex-shrink: 0;
}
.info-card-body {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}
.info-label {
  font-size: 11px;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.info-value {
  font-size: 13.5px;
  color: #334155;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
}
.mono { font-family: 'Consolas', 'Courier New', monospace; font-size: 12px; }

/* ── 步骤时间线 ── */
.detail-section {
  margin-bottom: 20px;
}
.detail-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.detail-section-header h4 {
  font-size: 15px;
  color: #1e293b;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
}
.detail-section-header h4 i { color: #6366f1; }
.section-badge {
  font-size: 11px;
  color: #6366f1;
  background: #eef2ff;
  padding: 3px 10px;
  border-radius: 10px;
  font-weight: 600;
}

.steps-timeline {
  position: relative;
  padding-left: 24px;
}
.steps-track {
  position: absolute;
  left: 8px; top: 6px; bottom: 6px;
  width: 2px;
  background: #e4e7ed;
  border-radius: 1px;
}
.steps-node {
  position: relative;
  display: flex;
  gap: 14px;
  margin-bottom: 4px;
}
.steps-node:last-child { margin-bottom: 0; }

.node-indicator {
  position: absolute;
  left: -16px; top: 10px;
  width: 20px; height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  z-index: 1;
  border: 2px solid #fff;
}
.node-success .node-indicator { background: #67c23a; color: #fff; }
.node-failed  .node-indicator { background: #f56c6c; color: #fff; }
.node-running .node-indicator { background: #e6a23c; color: #fff; }
.node-skipped .node-indicator { background: #c0c4cc; color: #fff; }
.node-pending .node-indicator { background: #e4e7ed; color: #909399; }

.node-card {
  flex: 1;
  background: #f8fafc;
  border-radius: 10px;
  padding: 12px 16px;
  border: 1px solid #edf0f4;
  margin-bottom: 8px;
  min-width: 0;
  transition: box-shadow 0.2s;
}
.node-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
.node-header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.node-name { font-size: 13.5px; font-weight: 600; color: #334155; flex: 1; }
.node-duration { font-size: 12px; color: #94a3b8; }
.node-tag {
  font-size: 10.5px;
  padding: 2px 8px;
  border-radius: 8px;
  font-weight: 600;
}
.node-tag.tag-success { background: #e8f8e8; color: #529b2e; }
.node-tag.tag-failed  { background: #fef0f0; color: #d54949; }
.node-tag.tag-running { background: #fef6e8; color: #b88230; }
.node-tag.tag-skipped { background: #f0f2f5; color: #909399; }
.node-tag.tag-pending { background: #f0f2f5; color: #909399; }

.node-command { margin-top: 6px; }
.node-command code {
  font-size: 12px;
  color: #475569;
  background: #f1f5f9;
  padding: 4px 8px;
  border-radius: 4px;
  font-family: 'Consolas', monospace;
  word-break: break-all;
  display: inline-block;
}
.node-log { margin-top: 8px; }
.node-log pre {
  margin: 0;
  padding: 12px;
  background: #1e1e1e;
  color: #d4d4d4;
  border-radius: 8px;
  font-size: 11.5px;
  line-height: 1.55;
  font-family: 'Consolas', 'Courier New', monospace;
  overflow-x: auto;
  white-space: pre-wrap;
  max-height: 140px;
  overflow-y: auto;
  transition: max-height 0.3s;
}
.node-log pre.log-expanded {
  max-height: 600px;
}

/* ── 产物 ── */
.artifacts-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.artifact-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: #f8fafc;
  border: 1px solid #edf0f4;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}
.artifact-card:hover {
  background: #eef2ff;
  border-color: #c7d2fe;
  box-shadow: 0 2px 8px rgba(99,102,241,0.08);
}
.artifact-icon {
  width: 38px; height: 38px;
  border-radius: 8px;
  background: #eef2ff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: #6366f1;
  flex-shrink: 0;
}
.artifact-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.artifact-name {
  font-size: 13.5px;
  font-weight: 600;
  color: #334155;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.artifact-size {
  font-size: 11px;
  color: #94a3b8;
}
.artifact-dl-icon {
  width: 32px; height: 32px;
  border-radius: 8px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  color: #6366f1;
  transition: all 0.2s;
  flex-shrink: 0;
}
.artifact-card:hover .artifact-dl-icon {
  background: #6366f1;
  color: #fff;
}

/* 使用指南 — 弹窗标题 */
.guide-dialog-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
}
.guide-title-icon {
  width: 36px; height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #409eff, #337ecc);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: #fff;
}

/* 使用指南 — 内容区 */
.guide-content {
  font-size: 14px;
  color: #303133;
  line-height: 1.7;
  max-height: 62vh;
  overflow-y: auto;
  padding: 4px 2px;
}
.guide-content::-webkit-scrollbar { width: 5px; }
.guide-content::-webkit-scrollbar-thumb { background: #d9dde3; border-radius: 10px; }

.guide-section {
  margin-bottom: 28px;
}
.guide-section p {
  margin: 4px 0 10px;
  color: #606266;
  font-size: 14px;
}
.guide-section code {
  background: #fef5e7;
  padding: 2px 7px;
  border-radius: 4px;
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 12.5px;
  color: #c67711;
  border: 1px solid #fde3b8;
}

/* ── 章节标题 ── */
.guide-section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.guide-section-header h3 {
  font-size: 16px;
  color: #1e293b;
  margin: 0;
  font-weight: 700;
}
.guide-step-badge {
  width: 28px; height: 28px;
  border-radius: 8px;
  background: linear-gradient(135deg, #409eff, #2d7dd2);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  flex-shrink: 0;
}
.guide-step-badge--lang {
  background: linear-gradient(135deg, #8b5cf6, #7c3aed);
  font-size: 13px;
}
.guide-step-badge--link {
  background: linear-gradient(135deg, #67c23a, #529b2e);
  font-size: 13px;
}

/* ── 简介卡片 ── */
.guide-intro-card {
  display: flex;
  gap: 14px;
  padding: 18px 20px;
  background: linear-gradient(135deg, #f0f7ff 0%, #ecf5ff 100%);
  border-radius: 12px;
  border: 1px solid #d9ecff;
}
.guide-intro-icon {
  width: 44px; height: 44px;
  border-radius: 12px;
  background: linear-gradient(135deg, #409eff, #337ecc);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  color: #fff;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
}
.guide-intro-body { flex: 1; }
.guide-intro-body h3 {
  font-size: 16px;
  color: #1e293b;
  margin: 0 0 6px;
  font-weight: 700;
}
.guide-intro-body p {
  margin: 0;
  color: #5a6a7e;
  font-size: 13.5px;
  line-height: 1.7;
}

/* ── 代码块容器 ── */
.guide-code-wrapper {
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid #e2e4e9;
  margin: 10px 0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.guide-code-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  background: #2d2d30;
  font-size: 12px;
}
.code-lang-label {
  padding: 2px 10px;
  border-radius: 4px;
  background: #409eff;
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.5px;
}
.code-lang-label.lang-js { background: #f0db4f; color: #323330; }
.code-lang-label.lang-py { background: #4b8bbe; color: #fff; }
.code-lang-label.lang-java { background: #ed8b00; color: #fff; }
.code-lang-label.lang-go { background: #00add8; color: #fff; }
.code-lang-label.lang-docker { background: #2496ed; color: #fff; }
.code-file-path {
  color: #a0a0a0;
  font-family: 'Consolas', monospace;
  font-size: 11px;
  flex: 1;
}
.code-copy-btn {
  color: #a0a0a0;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 4px;
  transition: all 0.2s;
}
.code-copy-btn:hover { color: #fff; background: rgba(255,255,255,0.1); }

.guide-code {
  background: #1e1e1e;
  padding: 14px 18px;
  overflow-x: auto;
}
.guide-code pre {
  margin: 0;
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.7;
  color: #d4d4d4;
}
.guide-code code { background: none; padding: 0; color: #d4d4d4; border: none; }

/* ── 提示框 ── */
.guide-tip {
  display: flex;
  gap: 12px;
  padding: 14px 16px;
  background: linear-gradient(135deg, #fffdf5 0%, #fef9e7 100%);
  border: 1px solid #fde8a8;
  border-radius: 10px;
  margin: 12px 0;
}
.guide-tip-icon {
  width: 32px; height: 32px;
  border-radius: 8px;
  background: #fde8a8;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  color: #b88230;
  flex-shrink: 0;
}
.guide-tip-body { flex: 1; }
.guide-tip-body strong {
  display: block;
  font-size: 13px;
  color: #8b6914;
  margin-bottom: 2px;
}
.guide-tip-body p {
  margin: 0;
  font-size: 13px;
  color: #b88230;
  line-height: 1.6;
}
.guide-tip-body code { font-size: 12px; }

/* ── 步骤列表 ── */
.guide-steps {
  display: flex;
  flex-direction: column;
  gap: 0;
}
.guide-step {
  display: flex;
  gap: 12px;
}
.guide-step-marker {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 28px;
  flex-shrink: 0;
}
.step-dot-num {
  width: 26px; height: 26px;
  border-radius: 50%;
  background: linear-gradient(135deg, #409eff, #2d7dd2);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(64, 158, 255, 0.3);
}
.step-connector {
  width: 2px;
  flex: 1;
  min-height: 14px;
  background: #e0e4ea;
  margin: 4px 0;
}
.guide-step-card {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  margin-bottom: 10px;
  background: #f8fafc;
  border: 1px solid #edf0f4;
  border-radius: 10px;
  transition: box-shadow 0.2s, border-color 0.2s;
}
.guide-step-card:hover {
  border-color: #d0dae8;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.guide-step-icon {
  width: 34px; height: 34px;
  border-radius: 8px;
  background: #ecf5ff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  color: #409eff;
  flex-shrink: 0;
}
.guide-step-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 13px;
  color: #606266;
}
.guide-step-text strong {
  font-size: 14px;
  color: #303133;
}

/* ── 语言 Tabs ── */
.guide-tabs {
  margin-top: 4px;
}
.guide-tabs ::v-deep .el-tabs__nav {
  border-radius: 8px 8px 0 0;
  border: none;
}
.guide-tabs ::v-deep .el-tabs__item {
  font-size: 13px;
  padding: 0 16px;
  height: 34px;
  line-height: 34px;
  border-radius: 8px 8px 0 0;
}
.guide-tabs ::v-deep .el-tabs__item.is-active {
  background: #1e1e1e;
  color: #fff;
  border: none;
}
.guide-tabs ::v-deep .el-tabs__header {
  margin-bottom: 0;
}
.guide-tabs .guide-code-wrapper {
  border-radius: 0 8px 8px 8px;
  margin-top: 0;
}
.guide-tabs .guide-code pre { max-height: 160px; overflow-y: auto; }

/* ── 参考链接 ── */
.guide-links {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.guide-link-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: #fff;
  border: 1px solid #edf0f4;
  border-radius: 10px;
  text-decoration: none;
  color: #303133;
  transition: all 0.2s;
}
.guide-link-card:hover {
  border-color: #d0dae8;
  box-shadow: 0 4px 12px rgba(0,0,0,0.06);
  transform: translateY(-1px);
  text-decoration: none;
  color: #303133;
}
.guide-link-icon {
  width: 38px; height: 38px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}
.guide-link-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.guide-link-info strong {
  font-size: 14px;
  color: #303133;
}
.guide-link-info small {
  font-size: 11px;
  color: #a0a7b0;
}
.guide-link-arrow {
  font-size: 14px;
  color: #c0c4cc;
  transition: transform 0.2s;
}
.guide-link-card:hover .guide-link-arrow {
  transform: translateX(3px);
  color: #409eff;
}
</style>
