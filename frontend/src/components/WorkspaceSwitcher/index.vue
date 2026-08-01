<template>
  <div class="workspace-switcher">
    <!-- 领域切换 -->
    <div class="domain-selector">
      <el-dropdown trigger="click" @command="handleDomainSwitch">
        <div class="domain-trigger">
          <i :class="domainIcon"></i>
          <span class="domain-name">{{ domainLabel }}</span>
          <i class="el-icon-arrow-down domain-arrow"></i>
        </div>
        <el-dropdown-menu slot="dropdown">
          <el-dropdown-item
            v-for="d in domains"
            :key="d.key"
            :command="d.key"
            :class="{ 'is-active': activeDomain === d.key }"
          >
            <i :class="domainIconFor(d.key)"></i>
            {{ d.name }}
          </el-dropdown-item>
        </el-dropdown-menu>
      </el-dropdown>
    </div>

    <!-- 工作空间选择 -->
    <div class="workspace-list">
      <div
        v-for="ws in currentWorkspaces"
        :key="ws.id"
        class="ws-item"
        :class="{ active: activeWorkspaceId === ws.id }"
        @click="switchWorkspace(ws)"
      >
        <span class="ws-icon" aria-hidden="true">
          <i :class="workspaceIconClass(ws.icon)"></i>
        </span>
        <span class="ws-name">{{ ws.name }}</span>
        <el-tag v-if="ws.sub_role" size="mini" class="ws-sub-tag">
          {{ ws.sub_role === 'teacher' ? '教师' : '学生' }}
        </el-tag>
      </div>
    </div>

    <!-- 新建空间 -->
    <div class="ws-create" @click="showCreate = true">
      <i class="el-icon-plus"></i>
      <span>新建空间</span>
    </div>

    <!-- 新建空间弹窗 -->
    <el-dialog
      title="新建工作空间"
      :visible.sync="showCreate"
      width="420px"
      custom-class="ws-create-dialog"
      top="15vh"
    >
      <el-form label-position="top" size="small" class="ws-create-form">
        <el-form-item label="空间名称">
          <el-input v-model="newWs.name" placeholder="例如：我的课程空间" maxlength="200" />
        </el-form-item>
        <el-form-item label="所属领域">
          <el-select v-model="newWs.domain" style="width: 100%">
            <el-option
              v-for="d in domains"
              :key="d.key"
              :label="d.name"
              :value="d.key"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="newWs.domain === 'edu'" label="角色身份">
          <el-radio-group v-model="newWs.sub_role">
            <el-radio-button value="teacher">教师端</el-radio-button>
            <el-radio-button value="student">学生端</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="描述（可选）">
          <el-input v-model="newWs.description" type="textarea" :rows="3" placeholder="空间用途说明" />
        </el-form-item>
      </el-form>
      <span slot="footer">
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="creating">创建</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
export default {
  name: 'WorkspaceSwitcher',
  data() {
    return {
      showCreate: false,
      creating: false,
      newWs: { name: '', domain: 'rd', sub_role: '', description: '' },
    }
  },
  watch: {
    showCreate(val) {
      if (val) {
        this.newWs = { name: '', domain: 'rd', sub_role: '', description: '' }
      }
    },
    'newWs.domain'(val) {
      if (val === 'edu') {
        this.newWs.sub_role = this.newWs.sub_role || 'teacher'
      } else {
        this.newWs.sub_role = ''
      }
    },
  },
  computed: {
    activeDomain() {
      return this.$store.getters['workspace/activeDomain']
    },
    activeWorkspaceId() {
      return this.$store.getters['workspace/activeWorkspaceId']
    },
    domains() {
      return [
        { key: 'rd', name: '智能研发', icon: 'el-icon-monitor' },
        { key: 'edu', name: '智慧教育', icon: 'el-icon-reading' },
        { key: 'office', name: '智慧办公', icon: 'el-icon-s-home' },
      ]
    },
    currentWorkspaces() {
      return this.$store.getters['workspace/workspacesByDomain'](this.activeDomain)
    },
    domainIcon() {
      return this.domainIconFor(this.activeDomain)
    },
    domainLabel() {
      const d = this.domains.find(d => d.key === this.activeDomain)
      return d ? d.name : this.activeDomain
    },
  },
  methods: {
    domainIconFor(key) {
      const map = { rd: 'el-icon-monitor', edu: 'el-icon-reading', office: 'el-icon-s-home' }
      return map[key] || 'el-icon-menu'
    },

    handleDomainSwitch(domain) {
      this.$store.dispatch('grayscale/loadDomainConfig', domain)
      this.$store.dispatch('workspace/fetchWorkspaces', domain).then(() => {
        const workspaces = this.$store.getters['workspace/workspacesByDomain'](domain)
        if (workspaces.length > 0) {
          this.switchWorkspace(workspaces[0])
        } else {
          this.$store.dispatch('workspace/selectWorkspace', { id: null, domain, name: '' })
          this.$router.push('/dashboard').catch(() => {})
        }
      })
    },

    async switchWorkspace(ws) {
      await this.$store.dispatch('workspace/selectWorkspace', ws)
      this.$store.dispatch('grayscale/loadDomainConfig', ws.domain)
      if (ws.domain === 'edu') {
        await this.syncEducationContext(ws)
      } else {
        this.$store.commit('education/SET_ACTIVE_COURSE', null)
      }
    },

    workspaceIconClass(value) {
      const icons = {
        default: 'el-icon-folder',
        education: 'el-icon-reading',
        edu: 'el-icon-reading',
        research: 'el-icon-monitor',
        office: 'el-icon-s-home',
      }
      return icons[value] || 'el-icon-folder'
    },

    async syncEducationContext(ws) {
      try {
        const courses = await this.$store.dispatch('education/fetchCourses')
        const requestedRole = ws.sub_role || ''
        const candidate = requestedRole
          ? courses.find(course => course.membership_role === requestedRole)
          : courses[0]
        if (candidate) {
          await this.$store.dispatch('education/selectCourse', candidate.id)
        } else {
          this.$store.commit('education/SET_ACTIVE_COURSE', null)
        }
      } catch (error) {
        this.$store.commit('education/SET_ACTIVE_COURSE', null)
      }
    },

    async handleCreate() {
      if (!this.newWs.name.trim()) {
        this.$message.warning('请输入空间名称')
        return
      }
      this.creating = true
      const domain = this.newWs.domain
      try {
        const res = await this.$store.dispatch('workspace/createWorkspace', {
          name: this.newWs.name.trim(),
          domain: domain,
          sub_role: domain === 'edu' ? this.newWs.sub_role : '',
          description: this.newWs.description,
        })
        if (res.code === 201) {
          this.$message.success('工作空间已创建')
          this.showCreate = false
          this.newWs = { name: '', domain: 'rd', sub_role: '', description: '' }
          this.$store.dispatch('grayscale/loadDomainConfig', domain)
        } else {
          this.$message.error(res.message || '创建失败')
        }
      } catch {
        this.$message.error('创建失败')
      } finally {
        this.creating = false
      }
    },
  },
}
</script>

<style scoped>
.workspace-switcher {
  padding: 4px 12px 10px;
  border-bottom: 1px solid rgba(59,130,246,0.12);
}

.domain-selector {
  margin-bottom: 6px;
}

.domain-trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #1e293b;
  background: rgba(64,128,255,0.08);
  transition: background 0.2s;
}

.domain-trigger:hover {
  background: rgba(64,128,255,0.15);
}

.domain-arrow {
  margin-left: auto;
  font-size: 10px;
  color: #94a3b8;
}

.workspace-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
  max-height: 120px;
  overflow-y: auto;
}

.ws-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  color: #64748b;
  transition: all 0.15s;
}

.ws-item:hover {
  background: rgba(255,255,255,0.5);
  color: #1e293b;
}

.ws-item.active {
  background: rgba(64,128,255,0.12);
  color: #4080ff;
  font-weight: 600;
}

.ws-icon {
  font-size: 14px;
  width: 18px;
  text-align: center;
  flex-shrink: 0;
  overflow: hidden;
  line-height: 18px;
}

.ws-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ws-sub-tag {
  flex-shrink: 0;
  font-size: 10px;
  padding: 0 4px;
  height: 18px;
  line-height: 18px;
}

.ws-create {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 8px;
  margin-top: 4px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  color: #94a3b8;
  transition: all 0.15s;
}

.ws-create:hover {
  background: rgba(255,255,255,0.5);
  color: #4080ff;
}

/* 创建弹窗 */
.ws-create-form {
  padding: 0 6px;
}
</style>

<style>
.ws-create-dialog {
  border-radius: 14px;
  overflow: hidden;
}
.ws-create-dialog .el-dialog__header {
  padding: 20px 24px 0;
}
.ws-create-dialog .el-dialog__body {
  padding: 16px 24px 10px;
}
.ws-create-dialog .el-dialog__footer {
  padding: 0 24px 20px;
}
</style>
