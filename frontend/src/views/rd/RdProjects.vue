<template>
  <div class="rd-projects-page">
    <AppSidebar />

    <main class="rd-content">
      <header class="rd-header">
        <div>
          <h2>研发项目</h2>
          <p>管理你的研发项目，AI Agent 将自动感知项目上下文进行协作</p>
        </div>
        <el-button type="primary" icon="el-icon-plus" @click="showCreateDialog = true">
          创建项目
        </el-button>
      </header>

      <!-- 项目卡片列表 -->
      <section class="projects-grid" v-loading="loading">
        <template v-if="projects.length > 0">
          <article
            v-for="(project, pidx) in projects"
            :key="project.id"
            class="project-card"
            @click="goToProject(project.id)"
          >
            <!-- 卡片顶部渐变条 -->
            <div class="card-cover" :class="'cover-' + coverColors[pidx % 4]"></div>
            <div class="card-header">
              <h3 class="project-name">{{ project.name }}</h3>
              <el-tag size="mini" :type="project.status === 'active' ? 'success' : 'info'" effect="plain">
                {{ project.status === 'active' ? '进行中' : '已归档' }}
              </el-tag>
            </div>

            <p class="project-desc" v-if="project.description">
              {{ project.description }}
            </p>
            <p class="project-desc placeholder" v-else>暂无描述</p>

            <!-- 进度条 -->
            <div class="card-progress" v-if="(project.requirement_count || 0) > 0">
              <div class="progress-bar-mini">
                <div class="progress-fill-mini" :style="{ width: (project.completion_rate || 0) + '%' }"></div>
              </div>
              <span class="progress-pct">{{ project.completion_rate || 0 }}%</span>
            </div>

            <div class="tech-tags" v-if="hasTechStack(project.tech_stack)">
              <span
                v-for="item in displayTech(project.tech_stack)"
                :key="item.key"
                class="tech-tag-item"
              >
                {{ item.label }}: {{ item.value }}
              </span>
            </div>

            <div class="project-stats">
              <div class="stat-pill iterations">
                <i class="el-icon-s-flag"></i> {{ project.iteration_count || 0 }} 迭代
              </div>
              <div class="stat-pill requirements">
                <i class="el-icon-document"></i> {{ project.requirement_count || 0 }} 需求
              </div>
              <div class="stat-pill bugs">
                <i class="el-icon-warning"></i> {{ project.bug_count || 0 }} Bug
              </div>
            </div>

            <div class="card-footer">
              <span class="footer-time">{{ formatTime(project.updated_at) }}</span>
              <span class="footer-stat">
                <i class="el-icon-document"></i> {{ project.file_count || 0 }} 文件
              </span>
            </div>
          </article>
        </template>

        <div v-else class="empty-state">
          <i class="el-icon-folder-opened"></i>
          <h3>暂无项目</h3>
          <p>创建你的第一个研发项目，开启 AI 全栈协作之旅</p>
          <el-button type="primary" @click="showCreateDialog = true">创建项目</el-button>
        </div>
      </section>
    </main>

    <CreateProjectDialog
      v-model="showCreateDialog"
      @submit="handleCreate"
    />
  </div>
</template>

<script>
import { mapActions } from 'vuex'
import AppSidebar from '@/components/Sidebar/index.vue'
import CreateProjectDialog from '@/components/rd/CreateProjectDialog.vue'
import {
  demoProjects, demoIterations, demoRequirements, demoBugs,
} from './demoData'

export default {
  name: 'RdProjects',
  components: { AppSidebar, CreateProjectDialog },
  data() {
    return {
      showCreateDialog: false,
      projects: [],
      loading: false,
      coverColors: ['blue', 'green', 'purple', 'orange'],
      // 演示数据辅助
      iterationsData: demoIterations,
      requirementsData: demoRequirements,
      bugsData: demoBugs,
    }
  },
  created() {
    this.loadProjects()
  },
  methods: {
    ...mapActions('rd', ['fetchProjects', 'createProject']),

    async loadProjects() {
      // 1. 先加载演示数据，保证页面立即有内容
      this.projects = JSON.parse(JSON.stringify(demoProjects))

      // 2. 尝试从 API 加载真实数据
      this.loading = true
      try {
        await this.fetchProjects()
        const storeProjects = this.$store.state.rd.projects
        if (storeProjects && storeProjects.length > 0) {
          // API 有真实数据就用真实数据
          this.projects = storeProjects
        }
      } catch (e) {
        // API 失败，继续用演示数据
      } finally {
        this.loading = false
      }
    },

    hasTechStack(stack) {
      if (!stack) return false
      return Object.values(stack).some(v => v && v !== '无' && v !== '未定')
    },
    displayTech(stack) {
      if (!stack) return []
      const items = []
      const labelMap = { frontend: '前端', backend: '后端', database: '数据库', deployment: '部署' }
      for (const [k, v] of Object.entries(stack)) {
        if (v && v !== '无' && v !== '未定') {
          items.push({ key: k, label: labelMap[k] || k, value: v })
        }
      }
      return items
    },
    getProjectProgress(projectId) {
      const project = this.projects.find(p => p.id === projectId)
      return project ? (project.completion_rate || 0) : 0
    },
    formatTime(iso) {
      if (!iso) return ''
      const d = new Date(iso)
      const month = String(d.getMonth() + 1).padStart(2, '0')
      const day = String(d.getDate()).padStart(2, '0')
      const hour = String(d.getHours()).padStart(2, '0')
      const min = String(d.getMinutes()).padStart(2, '0')
      return `${month}-${day} ${hour}:${min}`
    },
    goToProject(id) {
      this.$router.push(`/projects/${id}`)
    },
    async handleCreate(formData) {
      try {
        const res = await this.createProject({
          name: formData.name,
          description: formData.description,
          tech_stack: formData.tech_stack,
          workspace_id: this.$store.getters['workspace/activeWorkspaceId'] || '',
        })
        if (res && (res.code === 201 || res.code === 200)) {
          this.showCreateDialog = false
          this.loadProjects()
          return
        }
      } catch (e) { /* API 失败走演示模式 */ }

      // 演示模式：直接加入本地列表
      const newProject = {
        id: 'proj-demo-' + Date.now(),
        name: formData.name,
        description: formData.description || '',
        tech_stack: formData.tech_stack || {},
        status: 'active',
        file_count: 0,
        updated_at: new Date().toISOString(),
      }
      this.projects.unshift(newProject)
      this.showCreateDialog = false
      this.$message.success('项目已创建（演示模式）')
    },
  },
}
</script>

<style scoped>
.rd-projects-page {
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

/* 项目卡片网格 */
.projects-grid {
  flex: 1;
  overflow-y: auto;
  padding: 16px 22px 24px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
  align-content: start;
}

.project-card {
  background: #fff;
  border-radius: 12px;
  cursor: pointer;
  transition: box-shadow 0.25s, transform 0.2s;
  border: 1px solid #ebeef5;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.project-card:hover {
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.1);
  transform: translateY(-4px);
}

/* 卡片顶部渐变条 */
.card-cover {
  height: 5px;
  width: 100%;
}
.card-cover.cover-blue { background: linear-gradient(90deg, #409eff, #66b1ff); }
.card-cover.cover-green { background: linear-gradient(90deg, #67c23a, #85ce61); }
.card-cover.cover-purple { background: linear-gradient(90deg, #b37feb, #d3adf7); }
.card-cover.cover-orange { background: linear-gradient(90deg, #e6a23c, #ebb563); }

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 22px 0;
}
.project-name {
  margin: 0;
  font-size: 16px;
  color: #1e293b;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  margin-right: 10px;
}
.project-desc {
  font-size: 13px;
  color: #64748b;
  margin: 8px 22px 0;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex-shrink: 0;
}
.project-desc.placeholder {
  color: #c0c4cc;
  font-style: italic;
}

/* 进度条 */
.card-progress {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 14px 22px 0;
}
.progress-bar-mini {
  flex: 1;
  height: 5px;
  background: #f0f2f5;
  border-radius: 3px;
  overflow: hidden;
}
.progress-fill-mini {
  height: 100%;
  background: linear-gradient(90deg, #409eff, #66b1ff);
  border-radius: 3px;
  transition: width 0.5s ease;
}
.progress-pct {
  font-size: 12px;
  font-weight: 700;
  color: #409eff;
  min-width: 32px;
  text-align: right;
}

.tech-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 0 22px;
  margin-top: 14px;
}

/* 项目统计 */
.project-stats {
  display: flex;
  gap: 8px;
  padding: 0 22px;
  margin-top: 14px;
}
.stat-pill {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  padding: 5px 12px;
  border-radius: 6px;
  font-weight: 500;
}
.stat-pill.iterations { color: #409eff; background: #e8f4fd; }
.stat-pill.requirements { color: #67c23a; background: #e8f8e8; }
.stat-pill.bugs { color: #f56c6c; background: #fef0f0; }
.stat-pill i { font-size: 12px; }

.tech-tag-item {
  display: inline-block;
  font-size: 11px;
  padding: 2px 10px;
  border-radius: 4px;
  color: #409eff;
  background: #ecf5ff;
  border: 1px solid #d9ecff;
  white-space: nowrap;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #909399;
  padding: 14px 22px 18px;
  margin-top: auto;
}
.footer-stat i { margin-right: 2px; }

/* 空状态 */
.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 64px 16px;
}
.empty-state i { font-size: 56px; color: #dcdfe6; display: block; margin-bottom: 16px; }
.empty-state h3 { margin: 0 0 8px; color: #909399; font-size: 16px; }
.empty-state p { margin: 0 0 20px; color: #c0c4cc; font-size: 13px; }
</style>
