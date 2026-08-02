<template>
  <div class="rd-repos-page">
    <AppSidebar />

    <main class="rd-content">
      <header class="rd-header">
        <div class="header-left">
          <h2>代码仓库</h2>
          <p>查看和管理所有项目关联的 GitHub 仓库</p>
        </div>
        <div class="header-right">
          <el-select
            v-model="filterProjectId"
            placeholder="全部项目"
            clearable
            size="small"
            style="width: 200px"
            @change="onFilterChange"
          >
            <el-option
              v-for="p in projects"
              :key="p.id"
              :label="p.name"
              :value="p.id"
            />
          </el-select>
          <el-button
            v-if="filterProjectId"
            type="primary"
            size="small"
            icon="el-icon-plus"
            @click="$router.push('/projects/' + filterProjectId)"
          >
            去项目关联仓库
          </el-button>
        </div>
      </header>

      <!-- 仓库列表 -->
      <section class="repos-grid" v-loading="loading">
        <article
          v-for="repo in displayRepos"
          :key="repo.id"
          class="repo-card"
          @click="$router.push('/repos/' + repo.id)"
        >
          <div class="repo-card-top">
            <div class="repo-icon">
              <i class="el-icon-folder-opened"></i>
            </div>
            <div class="repo-body">
              <div class="repo-header">
                <h3>{{ repo.full_name || repo.repo_name || repo.name }}</h3>
                <el-tag size="mini" effect="plain">{{ repo.language || '—' }}</el-tag>
              </div>
              <p class="repo-desc" v-if="repo.description">{{ repo.description }}</p>
              <div class="repo-meta">
                <span class="repo-project-tag" v-if="repo.project_name">
                  <i class="el-icon-s-grid"></i> {{ repo.project_name }}
                </span>
                <span><i class="el-icon-share"></i> {{ repo.default_branch || 'main' }}</span>
                <span v-if="repo.html_url">
                  <a :href="repo.html_url" target="_blank" @click.stop><i class="el-icon-link"></i> GitHub</a>
                </span>
                <span v-if="repo.private" class="repo-visibility">
                  <i class="el-icon-lock"></i> 私有
                </span>
              </div>
            </div>
          </div>
        </article>

        <div v-if="displayRepos.length === 0 && !loading" class="empty-state">
          <i class="el-icon-folder-opened"></i>
          <h3>{{ filterProjectId ? '该项目暂无关联仓库' : '暂无代码仓库' }}</h3>
          <p v-if="filterProjectId">
            前往项目详情页的"代码仓库"Tab 关联 GitHub 仓库
            <el-button type="text" @click="$router.push('/projects/' + filterProjectId)">前往项目</el-button>
          </p>
          <p v-else>
            请先从项目详情页的"代码仓库"Tab 关联 GitHub 仓库。所有已关联的仓库将在此处展示。
          </p>
        </div>
      </section>
    </main>
  </div>
</template>

<script>
import AppSidebar from '@/components/Sidebar/index.vue'
import * as rdApi from '@/api/rd'

export default {
  name: 'RdRepos',
  components: { AppSidebar },
  data() {
    return {
      loading: false,
      filterProjectId: '',
      projects: [],
      allRepos: [],
    }
  },
  computed: {
    displayRepos() {
      return this.allRepos
    },
  },
  created() {
    this.filterProjectId = this.$route.query.projectId || ''
    this.loadProjects()
    this.loadRepos()
  },
  methods: {
    async loadProjects() {
      try {
        const res = await rdApi.getProjects()
        if (res.code === 200) {
          this.projects = res.data.items || []
        }
      } catch (e) { /* ignore */ }
    },
    async loadRepos() {
      this.loading = true
      try {
        const params = {}
        if (this.filterProjectId) {
          params.project_id = this.filterProjectId
        }
        const res = await rdApi.getAllRepos(params)
        if (res.code === 200 && res.data.items) {
          // 附加项目名称
          const projectMap = {}
          this.projects.forEach(p => { projectMap[p.id] = p.name })
          this.allRepos = res.data.items.map(r => ({
            ...r,
            project_name: projectMap[r.project_id] || '',
          }))
          this.loading = false
          return
        }
      } catch (e) { /* fallback */ }
      this.allRepos = []
      this.loading = false
    },
    onFilterChange() {
      this.loadRepos()
    },
  },
}
</script>

<style scoped>
.rd-repos-page {
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
  padding: 18px 22px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}
.header-left h2 { margin: 0 0 4px; font-size: 20px; color: #1e293b; }
.header-left p { margin: 0; font-size: 13px; color: #86909c; }
.header-right { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }

/* 仓库列表 */
.repos-grid {
  flex: 1;
  overflow-y: auto;
  padding: 16px 22px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.repo-card {
  background: #fff;
  border-radius: 10px;
  border: 1px solid #ebeef5;
  padding: 20px 24px;
  cursor: pointer;
  transition: box-shadow 0.2s, transform 0.15s;
}
.repo-card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.08);
  transform: translateY(-1px);
}
.repo-card-top { display: flex; gap: 16px; }
.repo-icon {
  width: 48px; height: 48px;
  background: #e8f4fd;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  color: #409eff;
  flex-shrink: 0;
}
.repo-body { flex: 1; min-width: 0; }
.repo-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.repo-header h3 { margin: 0; font-size: 16px; color: #303133; }
.repo-desc { font-size: 13px; color: #606266; margin: 0 0 10px; }
.repo-meta { display: flex; gap: 16px; font-size: 12px; color: #909399; flex-wrap: wrap; align-items: center; }
.repo-meta span { display: inline-flex; align-items: center; gap: 3px; }
.repo-meta a { color: #409eff; text-decoration: none; }
.repo-meta a:hover { text-decoration: underline; }
.repo-project-tag {
  color: #1967d2;
  background: #e8f0fe;
  padding: 1px 8px;
  border-radius: 10px;
  font-weight: 500;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 64px 16px;
}
.empty-state i { font-size: 56px; color: #dcdfe6; display: block; margin-bottom: 16px; }
.empty-state h3 { margin: 0 0 8px; color: #909399; font-size: 16px; }
.empty-state p { margin: 0; color: #c0c4cc; font-size: 13px; }
</style>
