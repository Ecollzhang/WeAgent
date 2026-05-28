<template>
  <div class="capability-page">
    <AppSidebar />

    <div class="capability-rail">
      <div class="rail-header">
        <h3>能力库</h3>
        <el-button size="mini" icon="el-icon-refresh" circle @click="fetchCapabilities"></el-button>
      </div>

      <div class="type-list">
        <div
          v-for="item in capabilityTypes"
          :key="item.type"
          class="type-item"
          :class="{ active: activeType === item.type }"
          @click="selectType(item.type)"
        >
          <i :class="item.icon" :style="{ color: item.color }"></i>
          <span>{{ item.label }}</span>
          <b>{{ typeCounts[item.type] || 0 }}</b>
        </div>
      </div>

      <div class="rail-actions">
        <el-button size="small" type="primary" icon="el-icon-edit-outline" @click="openCreateSkill">
          新建 Skill
        </el-button>
        <el-button size="small" icon="el-icon-upload2" @click="openMarkdownImport">
          Markdown
        </el-button>
        <el-button size="small" icon="el-icon-box" @click="openManifestImport">
          npx manifest
        </el-button>
      </div>
    </div>

    <div class="capability-content">
      <div class="content-header">
        <div class="header-title">
          <i :class="activeTypeMeta.icon" :style="{ color: activeTypeMeta.color }"></i>
          <div>
            <h2>{{ activeTypeMeta.label }}</h2>
            <span>{{ filteredCapabilities.length }} items</span>
          </div>
        </div>
        <el-input
          v-model="keyword"
          size="small"
          prefix-icon="el-icon-search"
          placeholder="Search"
          clearable
          class="search-input"
        ></el-input>
      </div>

      <div class="capability-list" v-loading="loading">
        <div
          v-for="capability in filteredCapabilities"
          :key="capability.id"
          class="capability-card"
          :class="{ selected: selected && selected.id === capability.id }"
          @click="selectCapability(capability)"
        >
          <div class="capability-icon" :style="{ background: typeMeta(capability.type).color }">
            <i :class="typeMeta(capability.type).icon"></i>
          </div>
          <div class="capability-main">
            <div class="capability-title">
              <h3>{{ capability.name }}</h3>
              <el-tag size="mini" :type="capability.is_builtin ? 'info' : 'success'">
                {{ capability.is_builtin ? 'Builtin' : 'Library' }}
              </el-tag>
            </div>
            <p>{{ capability.description || capability.source_ref || 'No description' }}</p>
            <div class="capability-meta">
              <span>v{{ latestVersion(capability).version || '1.0.0' }}</span>
              <span>{{ capability.source || 'user' }}</span>
              <span v-if="capability.type === 'plugin'">manifest only</span>
            </div>
          </div>
          <el-button
            v-if="capability.type === 'skill' && !capability.is_builtin"
            size="mini"
            type="text"
            icon="el-icon-document-add"
            @click.stop="openVersionDialog(capability)"
          ></el-button>
        </div>

        <div v-if="filteredCapabilities.length === 0 && !loading" class="empty-state">
          <i :class="activeTypeMeta.icon"></i>
          <h2>No capabilities</h2>
          <p>{{ activeTypeMeta.label }}</p>
        </div>
      </div>
    </div>

    <div class="capability-detail" v-if="selected">
      <div class="detail-header">
        <div class="detail-icon" :style="{ background: typeMeta(selected.type).color }">
          <i :class="typeMeta(selected.type).icon"></i>
        </div>
        <div>
          <h3>{{ selected.name }}</h3>
          <span>{{ selected.type }} · v{{ latestVersion(selected).version || '1.0.0' }}</span>
        </div>
      </div>

      <div class="detail-section">
        <h4>Permissions</h4>
        <div class="permission-row">
          <span>Required</span>
          <div>
            <el-tag
              v-for="permission in latestPermissions(selected).required"
              :key="permission"
              size="mini"
              type="danger"
            >{{ permission }}</el-tag>
            <em v-if="latestPermissions(selected).required.length === 0">none</em>
          </div>
        </div>
        <div class="permission-row">
          <span>Optional</span>
          <div>
            <el-tag
              v-for="permission in latestPermissions(selected).optional"
              :key="permission"
              size="mini"
            >{{ permission }}</el-tag>
            <em v-if="latestPermissions(selected).optional.length === 0">none</em>
          </div>
        </div>
      </div>

      <div class="detail-section">
        <h4>Source</h4>
        <p>{{ selected.source || 'user' }}</p>
        <code>{{ selected.source_ref || 'manual' }}</code>
      </div>

      <div class="detail-section" v-if="selected.type === 'skill'">
        <h4>Markdown</h4>
        <pre>{{ latestVersion(selected).content || '' }}</pre>
      </div>

      <div class="detail-section" v-else>
        <h4>Manifest</h4>
        <pre>{{ formatJson(latestVersion(selected).manifest) }}</pre>
      </div>
    </div>

    <el-dialog title="New Skill" :visible.sync="skillDialog.visible" width="680px">
      <el-form label-position="top">
        <el-form-item label="Name">
          <el-input v-model="skillDialog.name"></el-input>
        </el-form-item>
        <el-form-item label="Description">
          <el-input v-model="skillDialog.description"></el-input>
        </el-form-item>
        <el-form-item label="Permissions">
          <el-checkbox-group v-model="skillDialog.permissions.required">
            <el-checkbox v-for="item in permissionOptions" :key="item" :label="item">{{ item }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="Markdown">
          <el-input type="textarea" :rows="12" v-model="skillDialog.markdown"></el-input>
        </el-form-item>
      </el-form>
      <span slot="footer">
        <el-button @click="skillDialog.visible = false">Cancel</el-button>
        <el-button type="primary" @click="handleCreateSkill">Save</el-button>
      </span>
    </el-dialog>

    <el-dialog title="Import Markdown" :visible.sync="markdownDialog.visible" width="680px">
      <el-form label-position="top">
        <el-form-item label="Source">
          <el-input v-model="markdownDialog.source_ref"></el-input>
        </el-form-item>
        <el-form-item label="Markdown">
          <el-input type="textarea" :rows="14" v-model="markdownDialog.markdown"></el-input>
        </el-form-item>
        <el-button size="small" icon="el-icon-folder-opened" @click="$refs.markdownFile.click()">
          Load file
        </el-button>
        <input ref="markdownFile" type="file" accept=".md,text/markdown,text/plain" style="display:none" @change="handleMarkdownFile" />
      </el-form>
      <span slot="footer">
        <el-button @click="markdownDialog.visible = false">Cancel</el-button>
        <el-button type="primary" @click="handleImportMarkdown">Import</el-button>
      </span>
    </el-dialog>

    <el-dialog title="Import npx Manifest" :visible.sync="manifestDialog.visible" width="760px">
      <el-form label-position="top">
        <el-form-item label="Source">
          <el-input v-model="manifestDialog.source_ref" placeholder="npx:@scope/package@version"></el-input>
        </el-form-item>
        <el-form-item label="Manifest JSON">
          <el-input type="textarea" :rows="12" v-model="manifestDialog.text"></el-input>
        </el-form-item>
      </el-form>
      <div v-if="manifestPreview.length" class="manifest-preview">
        <h4>Preview</h4>
        <div v-for="item in manifestPreview" :key="item.name + item.type" class="preview-row">
          <el-tag size="mini">{{ item.type }}</el-tag>
          <span>{{ item.name }}</span>
          <code>{{ permissionSummary(item.permissions) }}</code>
        </div>
      </div>
      <span slot="footer">
        <el-button @click="manifestDialog.visible = false">Cancel</el-button>
        <el-button type="primary" @click="handleImportManifest">Import</el-button>
      </span>
    </el-dialog>

    <el-dialog title="New Skill Version" :visible.sync="versionDialog.visible" width="680px">
      <el-form label-position="top">
        <el-form-item label="Version">
          <el-input v-model="versionDialog.version" placeholder="auto"></el-input>
        </el-form-item>
        <el-form-item label="Markdown">
          <el-input type="textarea" :rows="14" v-model="versionDialog.content"></el-input>
        </el-form-item>
      </el-form>
      <span slot="footer">
        <el-button @click="versionDialog.visible = false">Cancel</el-button>
        <el-button type="primary" @click="handleCreateVersion">Save version</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import AppSidebar from '../components/Sidebar/index.vue'
import {
  createCapabilityVersion,
  createSkill,
  getCapabilities,
  importNpxManifest,
  importSkillMarkdown,
} from '../api/capabilities'

const PERMISSIONS = [
  'read_workspace',
  'write_workspace',
  'run_command',
  'network',
  'use_secret',
  'modify_skill',
  'start_service',
]

export default {
  name: 'CapabilityLibrary',
  components: { AppSidebar },
  data() {
    return {
      loading: false,
      activeType: 'skill',
      keyword: '',
      capabilities: [],
      selected: null,
      permissionOptions: PERMISSIONS,
      capabilityTypes: [
        { type: 'skill', label: 'Skill', icon: 'el-icon-document-checked', color: '#2f80ed' },
        { type: 'tool', label: 'Tool', icon: 'el-icon-s-tools', color: '#1f9d55' },
        { type: 'mcp', label: 'MCP', icon: 'el-icon-connection', color: '#b7791f' },
        { type: 'plugin', label: 'Plugin', icon: 'el-icon-box', color: '#c05621' },
      ],
      skillDialog: {
        visible: false,
        name: '',
        description: '',
        markdown: '# New Skill\n',
        permissions: { required: [], optional: [] },
      },
      markdownDialog: {
        visible: false,
        source_ref: 'markdown',
        markdown: '',
      },
      manifestDialog: {
        visible: false,
        source_ref: '',
        text: '{\n  "schema_version": "weagent.capability/v1",\n  "source": {"type": "npx", "package": "", "version": "1.0.0"},\n  "capabilities": []\n}',
      },
      versionDialog: {
        visible: false,
        capability: null,
        version: '',
        content: '',
      },
    }
  },
  computed: {
    activeTypeMeta() {
      return this.typeMeta(this.activeType)
    },
    typeCounts() {
      return this.capabilities.reduce((acc, item) => {
        acc[item.type] = (acc[item.type] || 0) + 1
        return acc
      }, {})
    },
    filteredCapabilities() {
      const text = this.keyword.trim().toLowerCase()
      return this.capabilities.filter(item => {
        const sameType = item.type === this.activeType
        if (!text) return sameType
        const haystack = `${item.name} ${item.description || ''} ${item.source_ref || ''}`.toLowerCase()
        return sameType && haystack.includes(text)
      })
    },
    manifestPreview() {
      try {
        const parsed = JSON.parse(this.manifestDialog.text || '{}')
        return Array.isArray(parsed.capabilities) ? parsed.capabilities : []
      } catch (e) {
        return []
      }
    },
  },
  created() {
    this.fetchCapabilities()
  },
  methods: {
    async fetchCapabilities() {
      this.loading = true
      try {
        const res = await getCapabilities()
        if (res.code === 200) {
          this.capabilities = res.data || []
          if (!this.selected && this.filteredCapabilities.length) {
            this.selected = this.filteredCapabilities[0]
          }
        }
      } catch (e) {
        this.$message.error('Failed to load capabilities')
      } finally {
        this.loading = false
      }
    },
    selectType(type) {
      this.activeType = type
      this.selected = this.filteredCapabilities[0] || null
    },
    selectCapability(capability) {
      this.selected = capability
    },
    typeMeta(type) {
      return this.capabilityTypes.find(item => item.type === type) || this.capabilityTypes[0]
    },
    latestVersion(capability) {
      return capability && capability.latest_version ? capability.latest_version : {}
    },
    latestPermissions(capability) {
      const permissions = this.latestVersion(capability).permissions || {}
      return {
        required: permissions.required || [],
        optional: permissions.optional || [],
      }
    },
    formatJson(value) {
      return JSON.stringify(value || {}, null, 2)
    },
    permissionSummary(permissions) {
      const required = permissions && permissions.required ? permissions.required : []
      const optional = permissions && permissions.optional ? permissions.optional : []
      return `required: ${required.length}, optional: ${optional.length}`
    },
    openCreateSkill() {
      this.skillDialog = {
        visible: true,
        name: '',
        description: '',
        markdown: '# New Skill\n',
        permissions: { required: [], optional: [] },
      }
    },
    async handleCreateSkill() {
      if (!this.skillDialog.name.trim() || !this.skillDialog.markdown.trim()) {
        this.$message.warning('Name and Markdown are required')
        return
      }
      const res = await createSkill({
        name: this.skillDialog.name.trim(),
        description: this.skillDialog.description,
        markdown: this.skillDialog.markdown,
        permissions: this.skillDialog.permissions,
      })
      if (res.code === 201) {
        this.skillDialog.visible = false
        this.activeType = 'skill'
        await this.fetchCapabilities()
        this.selected = res.data
        this.$message.success('Skill saved')
      }
    },
    openMarkdownImport() {
      this.markdownDialog.visible = true
    },
    handleMarkdownFile(event) {
      const file = event.target.files[0]
      if (!file) return
      const reader = new FileReader()
      reader.onload = e => {
        this.markdownDialog.markdown = e.target.result
        this.markdownDialog.source_ref = file.name
      }
      reader.readAsText(file)
      event.target.value = ''
    },
    async handleImportMarkdown() {
      if (!this.markdownDialog.markdown.trim()) {
        this.$message.warning('Markdown is required')
        return
      }
      const res = await importSkillMarkdown({
        markdown: this.markdownDialog.markdown,
        source_ref: this.markdownDialog.source_ref || 'markdown',
      })
      if (res.code === 201) {
        this.markdownDialog.visible = false
        this.activeType = 'skill'
        await this.fetchCapabilities()
        this.selected = res.data
        this.$message.success('Markdown imported')
      }
    },
    openManifestImport() {
      this.manifestDialog.visible = true
    },
    async handleImportManifest() {
      let manifest
      try {
        manifest = JSON.parse(this.manifestDialog.text)
      } catch (e) {
        this.$message.error('Invalid manifest JSON')
        return
      }
      const res = await importNpxManifest({
        source_ref: this.manifestDialog.source_ref,
        manifest,
      })
      if (res.code === 201) {
        this.manifestDialog.visible = false
        await this.fetchCapabilities()
        if (res.data && res.data[0]) {
          this.activeType = res.data[0].type
          this.selected = res.data[0]
        }
        this.$message.success('Manifest imported')
      }
    },
    openVersionDialog(capability) {
      this.versionDialog = {
        visible: true,
        capability,
        version: '',
        content: this.latestVersion(capability).content || '',
      }
    },
    async handleCreateVersion() {
      if (!this.versionDialog.capability || !this.versionDialog.content.trim()) {
        this.$message.warning('Markdown is required')
        return
      }
      const latest = this.latestVersion(this.versionDialog.capability)
      const res = await createCapabilityVersion(this.versionDialog.capability.id, {
        content: this.versionDialog.content,
        manifest: latest.manifest || { entry: 'SKILL.md', format: 'markdown' },
        permissions: latest.permissions || { required: [], optional: [] },
        meta: { edited_from: 'capability-library' },
        version: this.versionDialog.version || null,
      })
      if (res.code === 201) {
        this.versionDialog.visible = false
        await this.fetchCapabilities()
        this.selected = this.capabilities.find(item => item.id === this.versionDialog.capability.id) || this.selected
        this.$message.success('Version saved')
      }
    },
  },
}
</script>

<style scoped>
.capability-page {
  display: flex;
  gap: 12px;
  padding: 12px;
  height: 100vh;
  overflow: hidden;
  background: linear-gradient(135deg, #eef4ff 0%, #f7fafc 45%, #eef8f1 100%);
}

.capability-rail,
.capability-content,
.capability-detail {
  background: #ffffff;
  border: 1px solid #e6eaf0;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.06);
}

.capability-rail {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.rail-header,
.content-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid #edf0f5;
}

.rail-header h3,
.content-header h2,
.detail-header h3 {
  margin: 0;
  color: #1f2937;
}

.type-list {
  padding: 8px;
  flex: 1;
}

.type-item {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 40px;
  padding: 0 10px;
  border-radius: 8px;
  cursor: pointer;
  color: #526070;
  transition: background 0.15s, color 0.15s;
}

.type-item:hover,
.type-item.active {
  background: #f3f7fb;
  color: #111827;
}

.type-item span {
  flex: 1;
}

.type-item b {
  min-width: 24px;
  text-align: center;
  font-size: 12px;
  color: #64748b;
  background: #eef2f7;
  border-radius: 999px;
}

.rail-actions {
  padding: 12px;
  border-top: 1px solid #edf0f5;
  display: grid;
  gap: 8px;
}

.capability-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-title i {
  font-size: 24px;
}

.header-title span {
  color: #6b7280;
  font-size: 12px;
}

.search-input {
  width: 260px;
}

.capability-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(310px, 1fr));
  align-content: start;
  gap: 12px;
}

.capability-card {
  display: flex;
  gap: 12px;
  padding: 14px;
  min-height: 104px;
  border: 1px solid #e8edf3;
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s, transform 0.15s;
}

.capability-card:hover,
.capability-card.selected {
  border-color: #2f80ed;
  box-shadow: 0 8px 22px rgba(47, 128, 237, 0.12);
  transform: translateY(-1px);
}

.capability-icon,
.detail-icon {
  width: 42px;
  height: 42px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.capability-main {
  min-width: 0;
  flex: 1;
}

.capability-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.capability-title h3 {
  margin: 0;
  font-size: 15px;
  color: #1f2937;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.capability-main p {
  margin: 0 0 8px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.capability-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  color: #64748b;
  font-size: 11px;
}

.capability-meta span {
  background: #f4f7fb;
  border-radius: 6px;
  padding: 2px 7px;
}

.capability-detail {
  width: 360px;
  flex-shrink: 0;
  padding: 16px;
  overflow-y: auto;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 16px;
  border-bottom: 1px solid #edf0f5;
}

.detail-header span {
  color: #64748b;
  font-size: 12px;
}

.detail-section {
  padding: 16px 0;
  border-bottom: 1px solid #edf0f5;
}

.detail-section h4 {
  margin: 0 0 10px;
  color: #374151;
}

.detail-section p {
  margin: 0 0 6px;
  color: #526070;
}

.detail-section code,
.detail-section pre {
  display: block;
  background: #f5f7fa;
  border-radius: 6px;
  padding: 8px;
  color: #334155;
  font-size: 12px;
  overflow-x: auto;
}

.permission-row {
  display: grid;
  grid-template-columns: 76px 1fr;
  gap: 8px;
  align-items: start;
  margin-bottom: 8px;
  color: #64748b;
  font-size: 12px;
}

.permission-row .el-tag {
  margin: 0 4px 4px 0;
}

.permission-row em {
  color: #9aa4b2;
  font-style: normal;
}

.empty-state {
  grid-column: 1 / -1;
  min-height: 300px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #8a94a3;
}

.empty-state i {
  font-size: 48px;
  margin-bottom: 12px;
}

.empty-state h2 {
  margin: 0 0 6px;
  color: #374151;
}

.manifest-preview {
  border: 1px solid #edf0f5;
  border-radius: 8px;
  padding: 12px;
  background: #fafcff;
}

.manifest-preview h4 {
  margin: 0 0 8px;
}

.preview-row {
  display: grid;
  grid-template-columns: 76px 1fr 180px;
  gap: 8px;
  align-items: center;
  padding: 6px 0;
  border-top: 1px solid #edf0f5;
}
</style>
