<template>
  <div class="toolset-page">
    <AppSidebar />

    <aside class="category-rail">
      <div class="rail-header">
        <div>
          <h3>工具集</h3>
          <span>{{ categories.length }} 个分类</span>
        </div>
        <el-tooltip content="新建分类" placement="right">
          <el-button size="mini" icon="el-icon-plus" circle @click="openCategoryDialog()"></el-button>
        </el-tooltip>
      </div>

      <div class="category-list" v-loading="categoryLoading">
        <button
          v-for="category in categories"
          :key="category.id"
          class="category-item"
          :class="{ active: activeCategoryId === category.id }"
          type="button"
          @click="selectCategory(category.id)"
        >
          <i :class="category.icon || 'el-icon-folder'" :style="{ color: category.color || '#4080ff' }"></i>
          <span>{{ category.name }}</span>
          <b>{{ categoryTotal(category) }}</b>
        </button>
      </div>

      <div class="rail-footer" v-if="activeCategory && !activeCategory.is_builtin">
        <el-button size="mini" icon="el-icon-edit" @click="openCategoryDialog(activeCategory)">编辑分类</el-button>
        <el-button size="mini" type="danger" plain icon="el-icon-delete" @click="handleDeleteCategory(activeCategory)">
          删除
        </el-button>
      </div>
    </aside>

    <main class="toolset-content">
      <div class="content-header">
        <div class="category-title">
          <i :class="activeCategoryIcon" :style="{ color: activeCategoryColor }"></i>
          <div>
            <h2>{{ activeCategoryName }}</h2>
            <span>先按分类管理，再展开 Skill / MCP / Plugin / Tool</span>
          </div>
        </div>
        <div class="header-actions">
          <el-input
            v-model="keyword"
            size="small"
            prefix-icon="el-icon-search"
            placeholder="搜索工具集内容"
            clearable
          ></el-input>
          <el-button size="small" icon="el-icon-edit-outline" @click="openCreateSkill">新建 Skill</el-button>
          <el-button size="small" type="primary" icon="el-icon-upload2" @click="openImportWizard">
            导入
          </el-button>
        </div>
      </div>

      <el-tabs v-model="activeType" class="type-tabs" @tab-click="selectFirstCapability">
        <el-tab-pane
          v-for="item in capabilityTypes"
          :key="item.type"
          :name="item.type"
        >
          <span slot="label">
            <i :class="item.icon"></i>
            {{ item.label }}
            <b>{{ typeCount(item.type) }}</b>
          </span>
        </el-tab-pane>
      </el-tabs>

      <div class="capability-list" v-loading="loading">
        <div
          v-for="capability in filteredCapabilities"
          :key="capability.id"
          class="capability-card"
          :class="{ selected: selected && selected.id === capability.id }"
          role="button"
          tabindex="0"
          @click="selectCapability(capability)"
          @keyup.enter="selectCapability(capability)"
        >
          <span class="capability-icon" :style="{ background: capabilityIconColor(capability) }">
            <i :class="capabilityIconClass(capability)"></i>
          </span>
          <span class="capability-main">
            <span class="capability-title">
              <strong>{{ capability.name }}</strong>
              <el-tag size="mini" :type="capability.is_builtin ? 'info' : 'success'">
                {{ capability.is_builtin ? '内置' : '用户' }}
              </el-tag>
              <el-tag
                v-if="capability.type === 'tool'"
                size="mini"
                :type="toolStatusTagType(capability)"
              >
                {{ toolStatusLabel(capability) }}
              </el-tag>
            </span>
            <span class="capability-desc">{{ capability.description || capability.source_ref || '暂无描述' }}</span>
            <span class="capability-meta">
              <code>{{ sourceLabel(capability) }}</code>
              <code>v{{ latestVersion(capability).version || '1.0.0' }}</code>
              <code>{{ permissionSummary(latestPermissions(capability)) }}</code>
            </span>
          </span>
          <el-button
            v-if="capability.type === 'skill' && !capability.is_builtin"
            size="mini"
            type="text"
            icon="el-icon-edit-outline"
            @click.stop="openVersionDialog(capability)"
          ></el-button>
        </div>

        <div v-if="filteredCapabilities.length === 0 && !loading" class="empty-state">
          <i :class="activeTypeMeta.icon"></i>
          <h3>当前分类暂无 {{ activeTypeMeta.label }}</h3>
          <p>可以新建 Skill，或从 Markdown、zip bundle、npx、MCP manifest 导入。</p>
        </div>
      </div>
    </main>

    <aside class="detail-panel" v-if="selected">
      <div class="detail-header">
        <div class="detail-heading">
          <span class="detail-icon" :style="{ background: capabilityIconColor(selected) }">
            <i :class="capabilityIconClass(selected)"></i>
          </span>
          <div>
            <h3>{{ selected.name }}</h3>
            <span>{{ typeMeta(selected.type).label }} · {{ selected.category ? selected.category.name : activeCategoryName }}</span>
          </div>
        </div>
        <div class="detail-actions">
          <el-tooltip v-if="selected && !selected.is_builtin" content="删除能力" placement="left">
            <el-button
              size="mini"
              type="danger"
              plain
              icon="el-icon-delete"
              circle
              @click="handleDeleteCapability"
            ></el-button>
          </el-tooltip>
          <el-tooltip content="收起详情" placement="left">
            <el-button size="mini" icon="el-icon-close" circle @click="clearSelection"></el-button>
          </el-tooltip>
        </div>
      </div>

      <el-tabs v-model="detailTab" class="detail-tabs">
        <el-tab-pane label="概览" name="overview">
          <section class="detail-section">
            <h4>权限</h4>
            <div class="permission-row">
              <span>必需</span>
              <div>
                <el-tag
                  v-for="permission in latestPermissions(selected).required"
                  :key="permission"
                  size="mini"
                  type="danger"
                >{{ permission }}</el-tag>
                <em v-if="latestPermissions(selected).required.length === 0">无</em>
              </div>
            </div>
            <div class="permission-row">
              <span>可选</span>
              <div>
                <el-tag
                  v-for="permission in latestPermissions(selected).optional"
                  :key="permission"
                  size="mini"
                >{{ permission }}</el-tag>
                <em v-if="latestPermissions(selected).optional.length === 0">无</em>
              </div>
            </div>
          </section>

          <section class="detail-section">
            <h4>来源</h4>
            <p>{{ sourceLabel(selected) }}</p>
            <code v-if="selected.source_ref">{{ selected.source_ref }}</code>
          </section>

          <section class="detail-section">
            <h4>{{ selected.type === 'tool' ? '工具定义' : '运行摘要' }}</h4>
            <div class="definition-grid">
              <span v-if="selected.type === 'tool'">内部标识</span>
              <span v-else>运行时</span>
              <code>{{ selected.type === 'tool' ? toolIdentifier(selected) : runtimeLabel(selected) }}</code>
              <span v-if="selected.type === 'tool'">状态</span>
              <code v-if="selected.type === 'tool'">{{ toolStatusLabel(selected) }}</code>
              <span v-if="selected.type === 'tool'">运行处理器</span>
              <code v-if="selected.type === 'tool'">{{ toolHandler(selected) || '未声明' }}</code>
              <span>分类</span>
              <code>{{ selected.category ? selected.category.name : activeCategoryName }}</code>
              <span v-if="selected.type === 'mcp'">工具数量</span>
              <code v-if="selected.type === 'mcp'">{{ manifestTools(selected).length }}</code>
            </div>
            <div v-if="manifestTools(selected).length" class="tool-list">
              <el-tag
                v-for="tool in manifestTools(selected)"
                :key="tool.name || tool"
                size="mini"
              >{{ tool.name || tool }}</el-tag>
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="文件" name="files">
          <section class="detail-section" v-loading="detailLoading">
            <div class="file-browser">
              <div class="file-list">
                <button
                  v-for="file in detailFiles"
                  :key="file.path"
                  type="button"
                  class="file-row"
                  :class="{ active: activeFilePath === file.path }"
                  @click="activeFilePath = file.path"
                >
                  <i :class="fileIcon(file)"></i>
                  <span>{{ file.path }}</span>
                  <small>{{ file.kind }}</small>
                </button>
              </div>
              <pre class="file-content">{{ activeFileContent }}</pre>
            </div>
            <div v-if="detailFiles.length === 0 && !detailLoading" class="inline-empty">
              暂无可展示文件
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="安全审计" name="audit">
          <section class="detail-section" v-loading="detailLoading">
            <div v-if="latestAudit" class="audit-card">
              <div class="audit-heading">
                <span>风险等级</span>
                <el-tag size="mini" :type="riskTagType(latestAudit.risk_level)">
                  {{ latestAudit.risk_level || 'low' }}
                </el-tag>
              </div>
              <div class="permission-row">
                <span>权限</span>
                <div>
                  <el-tag
                    v-for="permission in latestAudit.inferred_permissions || []"
                    :key="permission"
                    size="mini"
                  >{{ permission }}</el-tag>
                  <em v-if="!(latestAudit.inferred_permissions || []).length">无推断权限</em>
                </div>
              </div>
              <div class="risk-list">
                <div
                  v-for="item in latestAudit.risk_items || []"
                  :key="item.category + item.path + item.message"
                  class="risk-row"
                >
                  <el-tag size="mini" :type="riskTagType(item.severity)">{{ item.severity }}</el-tag>
                  <span>{{ item.path || 'bundle' }}</span>
                  <p>{{ item.message }}</p>
                </div>
              </div>
              <p v-if="latestAudit.overridden" class="override-note">
                已专家确认：{{ latestAudit.override_reason }}
              </p>
            </div>
            <div v-else class="inline-empty">暂无审计记录</div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="版本" name="versions">
          <section class="detail-section">
            <div class="definition-grid">
              <span>当前版本</span>
              <code>{{ latestVersion(selected).version || '1.0.0' }}</code>
              <span>Checksum</span>
              <code>{{ latestVersion(selected).checksum || '未生成' }}</code>
            </div>
            <el-button
              v-if="selected.type === 'skill' && !selected.is_builtin"
              size="small"
              type="primary"
              icon="el-icon-edit"
              @click="openVersionDialog(selected)"
            >
              编辑 Markdown
            </el-button>
          </section>
        </el-tab-pane>
      </el-tabs>
    </aside>

    <el-dialog :title="categoryDialog.id ? '编辑分类' : '新建分类'" :visible.sync="categoryDialog.visible" width="420px">
      <el-form label-position="top">
        <el-form-item label="分类名称">
          <el-input v-model="categoryDialog.name" placeholder="例如：代码工具"></el-input>
        </el-form-item>
        <el-form-item label="图标">
          <el-select v-model="categoryDialog.icon" style="width: 100%">
            <el-option label="工具" value="el-icon-s-tools"></el-option>
            <el-option label="代码" value="el-icon-monitor"></el-option>
            <el-option label="文档" value="el-icon-document"></el-option>
            <el-option label="网络" value="el-icon-connection"></el-option>
            <el-option label="数据" value="el-icon-data-analysis"></el-option>
            <el-option label="图片" value="el-icon-picture"></el-option>
            <el-option label="终端" value="el-icon-setting"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="颜色">
          <el-color-picker v-model="categoryDialog.color"></el-color-picker>
        </el-form-item>
      </el-form>
      <span slot="footer">
        <el-button @click="categoryDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveCategory">保存</el-button>
      </span>
    </el-dialog>

    <el-dialog title="新建 Skill" :visible.sync="skillDialog.visible" width="720px">
      <el-form label-position="top">
        <el-form-item label="名称">
          <el-input v-model="skillDialog.name"></el-input>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="skillDialog.description"></el-input>
        </el-form-item>
        <el-form-item label="必需权限">
          <el-checkbox-group v-model="skillDialog.permissions.required">
            <el-checkbox v-for="item in permissionOptions" :key="item" :label="item">{{ item }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="Markdown">
          <el-input type="textarea" :rows="12" v-model="skillDialog.markdown"></el-input>
        </el-form-item>
      </el-form>
      <span slot="footer">
        <el-button @click="skillDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleCreateSkill">保存</el-button>
      </span>
    </el-dialog>

    <el-dialog title="导入工具能力" :visible.sync="importDialog.visible" width="880px" class="import-dialog">
      <el-steps :active="importDialog.step" finish-status="success" simple>
        <el-step title="选择来源"></el-step>
        <el-step title="预览审计"></el-step>
        <el-step title="确认入库"></el-step>
      </el-steps>

      <div v-if="importDialog.step === 0" class="wizard-body">
        <el-radio-group v-model="importDialog.source_type" size="small" @change="handleImportSourceChange">
          <el-radio-button label="markdown">Markdown</el-radio-button>
          <el-radio-button label="upload">zip bundle</el-radio-button>
          <el-radio-button label="npx">npx</el-radio-button>
          <el-radio-button label="mcp">MCP manifest</el-radio-button>
        </el-radio-group>

        <el-form label-position="top" class="wizard-form">
          <template v-if="importDialog.source_type === 'markdown'">
            <el-form-item label="来源">
              <el-input v-model="importDialog.source_ref" placeholder="manual.md"></el-input>
            </el-form-item>
            <el-form-item label="Markdown">
              <el-input type="textarea" :rows="12" v-model="importDialog.markdown"></el-input>
            </el-form-item>
            <el-button size="small" icon="el-icon-folder-opened" @click="$refs.importMarkdownFile.click()">
              读取 .md 文件
            </el-button>
            <input ref="importMarkdownFile" type="file" accept=".md,text/markdown,text/plain" style="display:none" @change="handleImportFile" />
          </template>

          <template v-else-if="importDialog.source_type === 'upload'">
            <el-form-item label="上传 zip">
              <div class="upload-row">
                <el-button size="small" icon="el-icon-folder-opened" @click="$refs.importBundleFile.click()">
                  选择 zip bundle
                </el-button>
                <span>{{ importDialog.upload_name || '未选择文件' }}</span>
              </div>
              <input ref="importBundleFile" type="file" accept=".zip" style="display:none" @change="handleImportFile" />
            </el-form-item>
          </template>

          <template v-else-if="importDialog.source_type === 'npx'">
            <el-form-item label="npx 命令">
              <el-input v-model="importDialog.source_ref" placeholder="npx skills add eze-is/web-access"></el-input>
            </el-form-item>
            <el-alert
              title="npx 导入会在 Docker import sandbox 中执行。预览前会进行命令白名单解析和产物审计。"
              type="warning"
              show-icon
              :closable="false"
            ></el-alert>
          </template>

          <template v-else-if="importDialog.source_type === 'mcp'">
            <el-form-item label="来源">
              <el-input v-model="importDialog.source_ref" placeholder="mcp-manifest.json 或 npx:@scope/server"></el-input>
            </el-form-item>
            <el-form-item label="MCP manifest JSON">
              <el-input
                type="textarea"
                :rows="14"
                v-model="importDialog.mcp_manifest_text"
                spellcheck="false"
              ></el-input>
            </el-form-item>
            <el-alert
              title="该入口只导入 MCP 能力定义；如需执行 npm 包安装，请使用 npx 入口生成预览。"
              type="info"
              show-icon
              :closable="false"
            ></el-alert>
          </template>
        </el-form>
      </div>

      <div v-else-if="importDialog.step === 1" class="wizard-body" v-loading="importDialog.loading">
        <div class="preview-layout">
          <section>
            <h4>发现的能力</h4>
            <el-checkbox-group v-model="importDialog.selected_entries">
              <label
                v-for="item in previewCapabilities"
                :key="item.entry"
                class="candidate-row"
              >
                <el-checkbox :label="item.entry">
                  <strong>{{ item.name }}</strong>
                  <span>{{ previewCandidateMeta(item) }}</span>
                </el-checkbox>
              </label>
            </el-checkbox-group>
          </section>

          <section>
            <h4>安全审计</h4>
            <div class="audit-card">
              <div class="audit-heading">
                <span>风险等级</span>
                <el-tag size="mini" :type="riskTagType(previewAudit.risk_level)">
                  {{ previewAudit.risk_level || 'low' }}
                </el-tag>
              </div>
              <div class="permission-row">
                <span>权限</span>
                <div>
                  <el-tag
                    v-for="permission in previewAudit.inferred_permissions || []"
                    :key="permission"
                    size="mini"
                  >{{ permission }}</el-tag>
                  <em v-if="!(previewAudit.inferred_permissions || []).length">无推断权限</em>
                </div>
              </div>
              <div class="risk-list">
                <div
                  v-for="item in previewAudit.risk_items || []"
                  :key="item.category + item.path + item.message"
                  class="risk-row"
                >
                  <el-tag size="mini" :type="riskTagType(item.severity)">{{ item.severity }}</el-tag>
                  <span>{{ item.path || 'bundle' }}</span>
                  <p>{{ item.message }}</p>
                </div>
              </div>
            </div>
          </section>
        </div>

        <section>
          <h4>文件</h4>
          <div class="file-table">
            <div v-for="file in previewFiles" :key="file.path" class="file-table-row">
              <span>{{ file.path }}</span>
              <code>{{ file.kind }}</code>
              <small>{{ file.size || 0 }} bytes</small>
            </div>
          </div>
        </section>
      </div>

      <div v-else class="wizard-body">
        <el-alert
          v-if="isPreviewHighRisk"
          title="当前预览包含高风险项，需要专家模式二次确认并填写原因。"
          type="error"
          show-icon
          :closable="false"
        ></el-alert>
        <div class="confirm-summary">
          <span>将导入</span>
          <strong>{{ importDialog.selected_entries.length }}</strong>
          <span>个能力到</span>
          <strong>{{ activeCategoryName }}</strong>
        </div>
        <el-checkbox v-if="isPreviewHighRisk" v-model="importDialog.override_confirmed">
          我确认已审查风险并继续导入
        </el-checkbox>
        <el-input
          v-if="isPreviewHighRisk"
          v-model="importDialog.override_reason"
          type="textarea"
          :rows="3"
          placeholder="填写专家确认原因"
        ></el-input>
      </div>

      <span slot="footer">
        <el-button v-if="importDialog.step > 0" @click="importDialog.step -= 1">上一步</el-button>
        <el-button @click="importDialog.visible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="importDialog.loading"
          @click="handleImportPrimary"
        >
          {{ importPrimaryLabel }}
        </el-button>
      </span>
    </el-dialog>

    <el-dialog title="编辑 Skill Markdown" :visible.sync="versionDialog.visible" width="720px">
      <el-form label-position="top">
        <el-form-item label="版本号">
          <el-input v-model="versionDialog.version" placeholder="留空自动生成"></el-input>
        </el-form-item>
        <el-form-item label="Markdown">
          <el-input type="textarea" :rows="14" v-model="versionDialog.content"></el-input>
        </el-form-item>
      </el-form>
      <span slot="footer">
        <el-button @click="versionDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleCreateVersion">保存版本</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import AppSidebar from '../components/Sidebar/index.vue'
import {
  confirmCapabilityImport,
  createCapabilityVersion,
  createSkill,
  deleteCapability,
  getCapabilities,
  getCapabilityAssets,
  getCapabilityAudits,
  getCapabilityDeleteImpact,
  importMcpManifest,
  previewCapabilityImport,
} from '../api/capabilities'
import {
  createToolsetCategory,
  deleteToolsetCategory,
  getToolsetCategories,
  updateToolsetCategory,
} from '../api/toolsets'

const PERMISSIONS = [
  'read_workspace',
  'write_workspace',
  'run_command',
  'network',
  'use_secret',
  'modify_skill',
  'start_service',
]

const CAPABILITY_TYPES = [
  { type: 'skill', label: 'Skill', icon: 'el-icon-document-checked', color: '#2f80ed' },
  { type: 'mcp', label: 'MCP', icon: 'el-icon-connection', color: '#b7791f' },
  { type: 'plugin', label: 'Plugin', icon: 'el-icon-box', color: '#c05621' },
  { type: 'tool', label: 'Tool', icon: 'el-icon-s-tools', color: '#1f9d55' },
]

const VALID_ELEMENT_ICONS = new Set([
  'el-icon-box',
  'el-icon-coin',
  'el-icon-connection',
  'el-icon-cpu',
  'el-icon-data-analysis',
  'el-icon-document',
  'el-icon-document-checked',
  'el-icon-download',
  'el-icon-folder',
  'el-icon-folder-opened',
  'el-icon-magic-stick',
  'el-icon-monitor',
  'el-icon-picture',
  'el-icon-reading',
  'el-icon-search',
  'el-icon-s-check',
  'el-icon-s-tools',
  'el-icon-setting',
  'el-icon-share',
])

const ICON_ALIASES = {
  'el-icon-console': 'el-icon-monitor',
}

export default {
  name: 'Tools',
  components: { AppSidebar },
  data() {
    return {
      activeCategoryId: 'tool_code',
      activeType: 'skill',
      keyword: '',
      categories: [],
      capabilities: [],
      selected: null,
      detailTab: 'overview',
      detailFiles: [],
      detailAudits: [],
      activeFilePath: '',
      loading: false,
      detailLoading: false,
      categoryLoading: false,
      permissionOptions: PERMISSIONS,
      capabilityTypes: CAPABILITY_TYPES,
      categoryDialog: {
        visible: false,
        id: '',
        name: '',
        icon: 'el-icon-s-tools',
        color: '#4080ff',
      },
      skillDialog: {
        visible: false,
        name: '',
        description: '',
        markdown: '# New Skill\n',
        permissions: { required: [], optional: [] },
      },
      importDialog: this.emptyImportDialog(),
      versionDialog: {
        visible: false,
        capability: null,
        version: '',
        content: '',
        assets: [],
      },
    }
  },
  computed: {
    activeCategory() {
      return this.categories.find(item => item.id === this.activeCategoryId) || null
    },
    activeCategoryName() {
      return this.activeCategory ? this.activeCategory.name : '工具集'
    },
    activeCategoryIcon() {
      return this.activeCategory ? this.activeCategory.icon : 'el-icon-folder'
    },
    activeCategoryColor() {
      return this.activeCategory ? this.activeCategory.color : '#4080ff'
    },
    activeTypeMeta() {
      return this.typeMeta(this.activeType)
    },
    filteredCapabilities() {
      const text = this.keyword.trim().toLowerCase()
      return this.capabilities.filter(item => {
        const sameType = item.type === this.activeType
        if (!sameType) return false
        if (!text) return true
        const haystack = `${item.name} ${item.description || ''} ${item.source_ref || ''}`.toLowerCase()
        return haystack.includes(text)
      })
    },
    activeFileContent() {
      const file = this.detailFiles.find(item => item.path === this.activeFilePath)
      return file ? file.content || '' : ''
    },
    latestAudit() {
      return this.detailAudits[0] || null
    },
    previewCapabilities() {
      return (this.importDialog.preview && this.importDialog.preview.capabilities) || []
    },
    previewFiles() {
      return (this.importDialog.preview && this.importDialog.preview.files) || []
    },
    previewAudit() {
      return (this.importDialog.preview && this.importDialog.preview.audit) || {}
    },
    isPreviewHighRisk() {
      return this.previewAudit.risk_level === 'high'
    },
    importPrimaryLabel() {
      if (this.importDialog.step === 0) return '生成预览'
      if (this.importDialog.step === 1) return '继续确认'
      return '确认导入'
    },
  },
  created() {
    this.fetchCategories()
  },
  methods: {
    emptyImportDialog() {
      return {
        visible: false,
        step: 0,
        loading: false,
        source_type: 'markdown',
        source_ref: 'manual.md',
        markdown: '',
        upload_name: '',
        upload_base64: '',
        mcp_manifest_text: this.defaultMcpManifestText(),
        preview: null,
        selected_entries: [],
        override_confirmed: false,
        override_reason: '',
      }
    },
    defaultMcpManifestText() {
      return JSON.stringify({
        schema_version: 'weagent.capability/v1',
        source: {
          type: 'npx',
          package: '@modelcontextprotocol/server-memory',
          version: 'latest',
        },
        capabilities: [
          {
            type: 'mcp',
            name: 'Memory MCP',
            description: 'Official MCP memory server.',
            permissions: { required: ['run_command'], optional: [] },
            entry: {
              command: 'npx',
              args: ['--yes', '@modelcontextprotocol/server-memory'],
            },
            tools: [
              { name: 'read_graph' },
              { name: 'search_nodes' },
              { name: 'open_nodes' },
            ],
          },
        ],
      }, null, 2)
    },
    async fetchCategories() {
      this.categoryLoading = true
      try {
        const res = await getToolsetCategories()
        if (res.code === 200) {
          this.categories = res.data || []
          if (!this.categories.find(item => item.id === this.activeCategoryId) && this.categories[0]) {
            this.activeCategoryId = this.categories[0].id
          }
          await this.fetchCapabilities()
        }
      } catch (e) {
        this.$message.error('加载工具集分类失败')
      } finally {
        this.categoryLoading = false
      }
    },
    async fetchCapabilities() {
      if (!this.activeCategoryId) return
      this.loading = true
      try {
        const res = await getCapabilities({ category_id: this.activeCategoryId })
        if (res.code === 200) {
          this.capabilities = res.data || []
          this.ensureActiveTypeHasContent()
          this.selectFirstCapability()
        }
      } catch (e) {
        this.$message.error('加载工具集内容失败')
      } finally {
        this.loading = false
      }
    },
    async refreshAll() {
      await this.fetchCategories()
    },
    async selectCategory(categoryId) {
      this.activeCategoryId = categoryId
      this.selected = null
      await this.fetchCapabilities()
    },
    selectFirstCapability() {
      const next = this.filteredCapabilities[0] || null
      if (next) {
        this.selectCapability(next)
      } else {
        this.selected = null
        this.detailFiles = []
        this.detailAudits = []
      }
    },
    async selectCapability(capability) {
      this.selected = capability
      this.detailTab = 'overview'
      await this.loadCapabilityDetail(capability)
    },
    clearSelection() {
      this.selected = null
    },
    ensureActiveTypeHasContent() {
      if (this.capabilities.length === 0) return
      const currentTypeHasContent = this.capabilities.some(item => item.type === this.activeType)
      if (currentTypeHasContent) return
      const nextType = this.capabilityTypes.find(type => (
        this.capabilities.some(item => item.type === type.type)
      ))
      if (nextType) {
        this.activeType = nextType.type
      }
    },
    async loadCapabilityDetail(capability) {
      if (!capability) return
      this.detailLoading = true
      this.detailFiles = this.virtualFiles(capability)
      this.activeFilePath = this.detailFiles[0] ? this.detailFiles[0].path : ''
      this.detailAudits = []
      try {
        if (capability.type === 'skill') {
          const assetsRes = await getCapabilityAssets(capability.id)
          if (assetsRes.code === 200) {
            this.detailFiles = this.skillFiles(capability, assetsRes.data || [])
            this.activeFilePath = this.detailFiles[0] ? this.detailFiles[0].path : ''
          }
        }
        const auditsRes = await getCapabilityAudits(capability.id)
        if (auditsRes.code === 200) {
          this.detailAudits = auditsRes.data || []
        }
      } catch (e) {
        this.$message.warning('加载详情失败，已显示本地摘要')
      } finally {
        this.detailLoading = false
      }
    },
    categoryTotal(category) {
      const counts = category.counts || {}
      return Object.keys(counts).reduce((sum, key) => sum + Number(counts[key] || 0), 0)
    },
    typeCount(type) {
      if (this.activeCategory && this.activeCategory.counts) {
        return this.activeCategory.counts[type] || 0
      }
      return this.capabilities.filter(item => item.type === type).length
    },
    typeMeta(type) {
      return this.capabilityTypes.find(item => item.type === type) || this.capabilityTypes[0]
    },
    capabilityIconClass(capability) {
      const typeMeta = this.typeMeta(capability.type)
      const categoryIcon = capability.category ? capability.category.icon : ''
      const manifestIcon = this.toolDefinition(capability).icon
      return this.normalizeIconClass(manifestIcon || categoryIcon || typeMeta.icon, typeMeta.icon)
    },
    capabilityIconColor(capability) {
      const typeMeta = this.typeMeta(capability.type)
      const definition = this.toolDefinition(capability)
      const category = capability.category || {}
      return definition.color || category.color || typeMeta.color
    },
    normalizeIconClass(icon, fallback) {
      const normalized = ICON_ALIASES[icon] || icon
      const fallbackIcon = ICON_ALIASES[fallback] || fallback || 'el-icon-s-tools'
      if (VALID_ELEMENT_ICONS.has(normalized)) return normalized
      if (VALID_ELEMENT_ICONS.has(fallbackIcon)) return fallbackIcon
      return 'el-icon-s-tools'
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
    permissionSummary(permissions) {
      const required = permissions && permissions.required ? permissions.required : []
      const optional = permissions && permissions.optional ? permissions.optional : []
      return `必需 ${required.length} / 可选 ${optional.length}`
    },
    latestManifest(capability) {
      return this.latestVersion(capability).manifest || {}
    },
    toolDefinition(capability) {
      return this.latestManifest(capability).tool || {}
    },
    toolIdentifier(capability) {
      const definition = this.toolDefinition(capability)
      return definition.value || capability.source_ref || capability.slug || capability.id
    },
    toolHandler(capability) {
      return this.latestManifest(capability).handler || ''
    },
    toolRuntimeNames(capability) {
      const manifest = this.latestManifest(capability)
      if (Array.isArray(manifest.tool_names)) return manifest.tool_names
      return [this.toolIdentifier(capability)]
    },
    toolStatus(capability) {
      const ui = this.latestManifest(capability).ui || {}
      return ui.status || (capability.type === 'tool' ? 'deferred' : '')
    },
    toolStatusLabel(capability) {
      const labels = {
        implemented: '已实现',
        partial: '部分实现',
        requires_config: '需要配置',
        deferred: '未实现',
      }
      return labels[this.toolStatus(capability)] || '未声明'
    },
    toolStatusTagType(capability) {
      const status = this.toolStatus(capability)
      if (status === 'implemented') return 'success'
      if (status === 'partial') return 'warning'
      if (status === 'requires_config') return 'warning'
      return 'info'
    },
    sourceLabel(capability) {
      if (capability.is_builtin || capability.source === 'builtin') return '平台内置'
      if (capability.source === 'npx') return 'npx 导入'
      if (capability.source === 'repo') return 'repo 导入'
      if (capability.source === 'upload') return 'bundle 上传'
      if (capability.source === 'markdown') return 'Markdown 导入'
      return '用户创建'
    },
    runtimeLabel(capability) {
      const manifest = this.latestManifest(capability)
      const source = manifest.source || {}
      return manifest.runtime || source.type || capability.source || 'user'
    },
    manifestTools(capability) {
      const manifest = this.latestManifest(capability)
      const raw = manifest.raw || {}
      return manifest.tools || raw.tools || []
    },
    entrySummary(capability) {
      const manifest = this.latestManifest(capability)
      const raw = manifest.raw || {}
      const entry = manifest.entry || raw.entry || {}
      if (entry.command) {
        const args = Array.isArray(entry.args) ? entry.args.join(' ') : ''
        return `${entry.command} ${args}`.trim()
      }
      if (entry.module) return entry.module
      return capability.source_ref || '未声明'
    },
    pluginPackageName(capability) {
      const manifest = this.latestManifest(capability)
      const source = manifest.source || {}
      return (capability.install_record && capability.install_record.package_name) ||
        source.package ||
        capability.source_ref ||
        '未声明'
    },
    skillFiles(capability, assets) {
      const latest = this.latestVersion(capability)
      const files = [{
        path: 'SKILL.md',
        kind: 'skill_md',
        content: latest.content || '',
        size: (latest.content || '').length,
      }]
      ;(assets || []).forEach(asset => {
        if (asset.path === 'SKILL.md') return
        files.push({
          path: asset.path,
          kind: asset.kind || 'reference',
          content: asset.content || '',
          size: asset.size || (asset.content || '').length,
        })
      })
      return files.sort((a, b) => {
        if (a.path === 'SKILL.md') return -1
        if (b.path === 'SKILL.md') return 1
        return a.path.localeCompare(b.path)
      })
    },
    virtualFiles(capability) {
      if (!capability) return []
      if (capability.type === 'tool') {
        const definition = this.toolDefinition(capability)
        const manifest = this.latestManifest(capability)
        const summary = {
          runtime: 'builtin',
          name: capability.name,
          identifier: this.toolIdentifier(capability),
          handler: this.toolHandler(capability),
          tool_names: this.toolRuntimeNames(capability),
          status: this.toolStatus(capability),
          category: capability.category ? capability.category.name : this.activeCategoryName,
          description: capability.description || definition.description || '',
        }
        return [
          {
            path: 'TOOL.md',
            kind: 'virtual',
            content: this.latestVersion(capability).content || '',
            size: (this.latestVersion(capability).content || '').length,
          },
          {
            path: 'tool-definition.json',
            kind: 'virtual',
            content: JSON.stringify(summary, null, 2),
            size: JSON.stringify(summary).length,
          },
          {
            path: 'manifest.json',
            kind: 'virtual',
            content: JSON.stringify(manifest, null, 2),
            size: JSON.stringify(manifest).length,
          },
        ]
      }
      return [{
        path: 'manifest.json',
        kind: 'manifest',
        content: JSON.stringify(this.latestManifest(capability), null, 2),
        size: 0,
      }]
    },
    fileIcon(file) {
      if (file.kind === 'script') return 'el-icon-cpu'
      if (file.kind === 'manifest') return 'el-icon-document'
      if (file.kind === 'template') return 'el-icon-files'
      if (file.kind === 'virtual') return 'el-icon-view'
      return 'el-icon-document'
    },
    riskTagType(level) {
      if (level === 'high') return 'danger'
      if (level === 'medium') return 'warning'
      return 'success'
    },
    openCategoryDialog(category = null) {
      this.categoryDialog = {
        visible: true,
        id: category ? category.id : '',
        name: category ? category.name : '',
        icon: category ? category.icon : 'el-icon-s-tools',
        color: category ? category.color : '#4080ff',
      }
    },
    async handleSaveCategory() {
      if (!this.categoryDialog.name.trim()) {
        this.$message.warning('请填写分类名称')
        return
      }
      const payload = {
        name: this.categoryDialog.name.trim(),
        icon: this.categoryDialog.icon,
        color: this.categoryDialog.color,
      }
      const res = this.categoryDialog.id
        ? await updateToolsetCategory(this.categoryDialog.id, payload)
        : await createToolsetCategory(payload)
      if (res.code === 200 || res.code === 201) {
        this.categoryDialog.visible = false
        this.activeCategoryId = res.data.id
        await this.refreshAll()
        this.$message.success('分类已保存')
      }
    },
    async handleDeleteCategory(category) {
      this.$confirm(`删除分类“${category.name}”？其中的工具集内容会移动到“自定义”。`, '提示', {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
      }).then(async () => {
        const res = await deleteToolsetCategory(category.id)
        if (res.code === 200) {
          this.activeCategoryId = res.data.reassigned_to || 'tool_custom'
          await this.refreshAll()
          this.$message.success('分类已删除')
        }
      }).catch(() => {})
    },
    async handleDeleteCapability() {
      const capability = this.selected
      if (!capability) return
      if (capability.is_builtin) {
        this.$message.warning('内置能力不能删除，只能从 Agent 中解绑')
        return
      }

      let impact = {
        binding_count: 0,
        call_record_count: 0,
        affected_agents: [],
      }
      try {
        const impactRes = await getCapabilityDeleteImpact(capability.id)
        if (impactRes.code === 200) {
          impact = impactRes.data || impact
        }
      } catch (e) {
        this.$message.error('加载删除影响失败')
        return
      }

      const message = this.deleteImpactMessage(capability, impact)
      try {
        await this.$confirm(message, '删除能力', {
          type: 'warning',
          confirmButtonText: '删除',
          cancelButtonText: '取消',
        })
      } catch (e) {
        return
      }

      try {
        const res = await deleteCapability(capability.id)
        if (res.code === 200) {
          this.selected = null
          await this.refreshAll()
          this.$message.success('能力已删除，历史记录已保留')
        }
      } catch (e) {
        this.$message.error('删除能力失败')
      }
    },
    deleteImpactMessage(capability, impact) {
      const bindingCount = Number(impact.binding_count || 0)
      const callCount = Number(impact.call_record_count || 0)
      const affected = (impact.affected_agents || []).map(item => item.name).join('、')
      const agentPart = bindingCount
        ? `并解除 ${bindingCount} 个 Agent 绑定${affected ? `（${affected}）` : ''}`
        : '没有 Agent 绑定需要解除'
      return `确认删除“${capability.name}”？删除后会从工具集隐藏该能力，${agentPart}。版本、安全审计和 ${callCount} 条调用记录会继续保留。`
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
        this.$message.warning('请填写名称和 Markdown')
        return
      }
      const res = await createSkill({
        name: this.skillDialog.name.trim(),
        description: this.skillDialog.description,
        markdown: this.skillDialog.markdown,
        permissions: this.skillDialog.permissions,
        category_id: this.activeCategoryId,
      })
      if (res.code === 201) {
        this.skillDialog.visible = false
        this.activeType = 'skill'
        await this.refreshAll()
        this.selected = res.data
        await this.loadCapabilityDetail(res.data)
        this.$message.success('Skill 已保存')
      }
    },
    openImportWizard() {
      this.importDialog = this.emptyImportDialog()
      this.importDialog.visible = true
    },
    handleImportSourceChange(sourceType) {
      this.importDialog.preview = null
      this.importDialog.selected_entries = []
      if (sourceType === 'markdown') {
        this.importDialog.source_ref = 'manual.md'
      } else if (sourceType === 'upload') {
        this.importDialog.source_ref = this.importDialog.upload_name || 'bundle.zip'
      } else if (sourceType === 'npx') {
        this.importDialog.source_ref = 'npx skills add eze-is/web-access'
      } else if (sourceType === 'mcp') {
        this.importDialog.source_ref = 'mcp-manifest.json'
      }
    },
    async handleImportFile(event) {
      const file = event.target.files[0]
      if (!file) return
      if (this.importDialog.source_type === 'markdown') {
        this.importDialog.markdown = await this.readFileAsText(file)
        this.importDialog.source_ref = file.name
      } else if (this.importDialog.source_type === 'upload') {
        this.importDialog.upload_name = file.name
        this.importDialog.source_ref = file.name
        this.importDialog.upload_base64 = await this.readFileAsBase64(file)
      }
      event.target.value = ''
    },
    readFileAsText(file) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = e => resolve(e.target.result)
        reader.onerror = reject
        reader.readAsText(file)
      })
    },
    readFileAsBase64(file) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = e => {
          const value = e.target.result || ''
          resolve(String(value).split(',')[1] || '')
        }
        reader.onerror = reject
        reader.readAsDataURL(file)
      })
    },
    async handleImportPrimary() {
      if (this.importDialog.step === 0) {
        await this.handlePreviewImport()
      } else if (this.importDialog.step === 1) {
        if (!this.importDialog.selected_entries.length) {
          this.$message.warning('请至少选择一个能力')
          return
        }
        this.importDialog.step = 2
      } else {
        await this.handleConfirmImport()
      }
    },
    async handlePreviewImport() {
      if (this.importDialog.source_type === 'mcp') {
        this.handleMcpManifestPreview()
        return
      }
      const payload = this.importPreviewPayload()
      if (!payload) return
      this.importDialog.loading = true
      try {
        const res = await previewCapabilityImport(payload)
        if (res.code === 201 || res.code === 200) {
          this.importDialog.preview = res.data
          this.importDialog.selected_entries = (res.data.capabilities || []).map(item => item.entry)
          this.importDialog.step = 1
          this.$message.success('预览已生成')
        }
      } finally {
        this.importDialog.loading = false
      }
    },
    handleMcpManifestPreview() {
      const manifest = this.parseMcpManifestText()
      if (!manifest) return
      this.importDialog.loading = true
      try {
        const manifestText = this.importDialog.mcp_manifest_text || ''
        const preview = this.mcpPreviewFromManifest(manifest, manifestText)
        this.importDialog.preview = preview
        this.importDialog.selected_entries = preview.capabilities.map(item => item.entry)
        this.importDialog.step = 1
        this.$message.success('预览已生成')
      } finally {
        this.importDialog.loading = false
      }
    },
    parseMcpManifestText() {
      let manifest
      try {
        manifest = JSON.parse(this.importDialog.mcp_manifest_text || '')
      } catch (e) {
        this.$message.warning('MCP manifest 必须是合法 JSON')
        return null
      }
      if (!manifest || typeof manifest !== 'object' || Array.isArray(manifest)) {
        this.$message.warning('MCP manifest 必须是 JSON 对象')
        return null
      }
      if (manifest.schema_version !== 'weagent.capability/v1') {
        this.$message.warning('MCP manifest 需要使用 weagent.capability/v1')
        return null
      }
      const capabilities = Array.isArray(manifest.capabilities) ? manifest.capabilities : []
      if (!capabilities.some(item => item && item.type === 'mcp')) {
        this.$message.warning('MCP manifest 至少需要包含一个 MCP 能力')
        return null
      }
      if (capabilities.some(item => !item || item.type !== 'mcp')) {
        this.$message.warning('MCP 入口只导入 MCP 能力；Skill/Plugin 请使用 npx manifest 或其他入口')
        return null
      }
      return manifest
    },
    mcpPreviewFromManifest(manifest, manifestText) {
      const capabilities = (manifest.capabilities || []).map((item, index) => ({
        type: 'mcp',
        name: item.name || 'Imported MCP',
        description: item.description || '',
        entry: `manifest.json#${index}`,
        manifest_index: index,
        file_count: 1,
        tools: item.tools || [],
        permissions: item.permissions || {},
      }))
      return {
        source_type: 'mcp',
        source_ref: this.importDialog.source_ref || 'mcp-manifest.json',
        manifest,
        capabilities,
        files: [{
          path: this.importDialog.source_ref || 'mcp-manifest.json',
          kind: 'manifest',
          size: manifestText.length,
        }],
        audit: this.mcpPreviewAudit(capabilities, manifest),
      }
    },
    mcpPreviewAudit(capabilities, manifest) {
      const permissions = new Set()
      capabilities.forEach(candidate => {
        const declared = candidate.permissions || {}
        const required = declared.required || []
        const optional = declared.optional || []
        required.forEach(item => permissions.add(item))
        optional.forEach(item => permissions.add(item))
      })
      const manifestCapabilities = manifest.capabilities || []
      manifestCapabilities.forEach(item => {
        if (item.entry && item.entry.command) {
          permissions.add('run_command')
        }
      })
      return {
        risk_level: permissions.has('run_command') ? 'medium' : 'low',
        risk_items: [],
        blocking_items: [],
        inferred_permissions: Array.from(permissions).sort(),
        scanned_files: [this.importDialog.source_ref || 'mcp-manifest.json'],
      }
    },
    previewCandidateMeta(item) {
      if (item.type && item.type !== 'skill') {
        const type = this.typeMeta(item.type).label
        const toolCount = (item.tools || []).length
        return toolCount ? `${type} · ${toolCount} 个工具` : type
      }
      return `${item.file_count || 0} 个文件`
    },
    importPreviewPayload() {
      const sourceType = this.importDialog.source_type
      if (sourceType === 'markdown') {
        if (!this.importDialog.markdown.trim()) {
          this.$message.warning('Markdown 不能为空')
          return null
        }
        return {
          source_type: 'markdown',
          source_ref: this.importDialog.source_ref || 'manual.md',
          markdown: this.importDialog.markdown,
        }
      }
      if (sourceType === 'upload') {
        if (!this.importDialog.upload_base64) {
          this.$message.warning('请先选择 zip bundle')
          return null
        }
        return {
          source_type: 'upload',
          source_ref: this.importDialog.source_ref || this.importDialog.upload_name || 'bundle.zip',
          upload_name: this.importDialog.upload_name,
          upload_base64: this.importDialog.upload_base64,
        }
      }
      if (!this.importDialog.source_ref.trim()) {
        this.$message.warning('请填写 npx 命令')
        return null
      }
      return {
        source_type: 'npx',
        source_ref: this.importDialog.source_ref,
      }
    },
    async handleConfirmImport() {
      if (this.importDialog.source_type === 'mcp') {
        await this.handleConfirmMcpManifest()
        return
      }
      if (this.isPreviewHighRisk) {
        if (!this.importDialog.override_confirmed || !this.importDialog.override_reason.trim()) {
          this.$message.warning('高风险导入需要二次确认和原因')
          return
        }
      }
      this.importDialog.loading = true
      try {
        const res = await confirmCapabilityImport({
          import_job_id: this.importDialog.preview.import_job_id,
          selected_entries: this.importDialog.selected_entries,
          category_id: this.activeCategoryId,
          override_confirmed: this.importDialog.override_confirmed,
          override_reason: this.importDialog.override_reason,
        })
        if (res.code === 201 || res.code === 200) {
          this.importDialog.visible = false
          const created = res.data || []
          if (created[0]) {
            this.activeType = created[0].type
          }
          await this.refreshAll()
          if (created[0]) {
            this.selected = this.capabilities.find(item => item.id === created[0].id) || created[0]
            await this.loadCapabilityDetail(this.selected)
          }
          this.$message.success('导入已完成')
        }
      } finally {
        this.importDialog.loading = false
      }
    },
    selectedMcpManifest() {
      const preview = this.importDialog.preview || {}
      const manifest = preview.manifest || null
      if (!manifest) return null
      const selectedEntries = new Set(this.importDialog.selected_entries || [])
      const selectedIndexes = (preview.capabilities || [])
        .filter(item => selectedEntries.has(item.entry))
        .map(item => item.manifest_index)
      return {
        ...manifest,
        capabilities: (manifest.capabilities || []).filter((_item, index) => selectedIndexes.includes(index)),
      }
    },
    async handleConfirmMcpManifest() {
      const manifest = this.selectedMcpManifest()
      if (!manifest || !(manifest.capabilities || []).length) {
        this.$message.warning('请至少选择一个 MCP 能力')
        return
      }
      this.importDialog.loading = true
      try {
        const res = await importMcpManifest({
          source_ref: this.importDialog.source_ref || 'mcp-manifest.json',
          manifest,
          category_id: this.activeCategoryId,
        })
        if (res.code === 201 || res.code === 200) {
          this.importDialog.visible = false
          const created = res.data || []
          if (created[0]) {
            this.activeType = created[0].type
          }
          await this.refreshAll()
          if (created[0]) {
            this.selected = this.capabilities.find(item => item.id === created[0].id) || created[0]
            await this.loadCapabilityDetail(this.selected)
          }
          this.$message.success('导入已完成')
        }
      } finally {
        this.importDialog.loading = false
      }
    },
    async openVersionDialog(capability) {
      let assets = []
      try {
        const res = await getCapabilityAssets(capability.id)
        if (res.code === 200) {
          assets = (res.data || []).filter(item => item.path !== 'SKILL.md')
        }
      } catch (e) {
        assets = []
      }
      this.versionDialog = {
        visible: true,
        capability,
        version: '',
        content: this.latestVersion(capability).content || '',
        assets,
      }
    },
    async handleCreateVersion() {
      if (!this.versionDialog.capability || !this.versionDialog.content.trim()) {
        this.$message.warning('Markdown 不能为空')
        return
      }
      const latest = this.latestVersion(this.versionDialog.capability)
      const res = await createCapabilityVersion(this.versionDialog.capability.id, {
        content: this.versionDialog.content,
        manifest: latest.manifest || { entry: 'SKILL.md', format: 'markdown' },
        permissions: latest.permissions || { required: [], optional: [] },
        meta: { edited_from: 'toolset-page' },
        version: this.versionDialog.version || null,
        assets: this.versionDialog.assets,
      })
      if (res.code === 201) {
        this.versionDialog.visible = false
        await this.fetchCapabilities()
        this.selected = this.capabilities.find(item => item.id === this.versionDialog.capability.id) || this.selected
        if (this.selected) {
          await this.loadCapabilityDetail(this.selected)
        }
        this.$message.success('Skill 版本已保存')
      }
    },
  },
}
</script>

<style scoped>
.toolset-page {
  display: flex;
  gap: 12px;
  padding: 12px;
  height: 100vh;
  overflow: hidden;
  background: #f4f7fb;
}

.category-rail,
.toolset-content,
.detail-panel {
  background: #ffffff;
  border: 1px solid #e6eaf0;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.06);
}

.category-rail {
  width: 240px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  flex-shrink: 0;
}

.rail-header,
.content-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px;
  border-bottom: 1px solid #edf0f5;
}

.rail-header h3,
.content-header h2,
.detail-header h3 {
  margin: 0;
  color: #1f2937;
}

.rail-header span,
.category-title span,
.detail-heading > div > span {
  display: block;
  margin-top: 4px;
  color: #6b7280;
  font-size: 12px;
}

.category-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.category-item {
  width: 100%;
  height: 42px;
  border: 0;
  background: transparent;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 10px;
  border-radius: 8px;
  cursor: pointer;
  color: #526070;
  text-align: left;
}

.category-item:hover,
.category-item.active {
  background: #f3f7fb;
  color: #111827;
}

.category-item span {
  flex: 1;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.category-item b,
.type-tabs b {
  min-width: 24px;
  display: inline-block;
  text-align: center;
  font-size: 12px;
  color: #64748b;
  background: #eef2f7;
  border-radius: 999px;
  margin-left: 6px;
}

.rail-footer {
  border-top: 1px solid #edf0f5;
  padding: 12px;
  display: grid;
  gap: 8px;
}

.toolset-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.category-title,
.detail-heading {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.category-title i {
  font-size: 26px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-actions .el-input {
  width: 240px;
}

.type-tabs {
  padding: 0 16px;
  flex-shrink: 0;
}

.type-tabs i {
  margin-right: 4px;
}

.capability-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  align-content: start;
  gap: 12px;
}

.capability-card {
  min-height: 112px;
  border: 1px solid #e8edf3;
  border-radius: 8px;
  background: #ffffff;
  padding: 14px;
  display: flex;
  gap: 12px;
  text-align: left;
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

.capability-icon i,
.detail-icon i {
  font-size: 20px;
  line-height: 1;
}

.capability-main,
.detail-heading > div {
  flex: 1;
  min-width: 0;
}

.capability-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.capability-title strong,
.detail-heading h3 {
  color: #1f2937;
  font-size: 15px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.capability-desc {
  display: -webkit-box;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
  overflow: hidden;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.capability-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.capability-meta code,
.detail-section code {
  background: #f4f7fb;
  color: #526070;
  border-radius: 6px;
  padding: 2px 7px;
  font-size: 11px;
}

.detail-panel {
  width: 400px;
  flex-shrink: 0;
  padding: 16px;
  overflow-y: auto;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 16px;
  border-bottom: 1px solid #edf0f5;
}

.detail-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.detail-tabs {
  margin-top: 8px;
}

.detail-section {
  padding: 14px 0;
  border-bottom: 1px solid #edf0f5;
}

.detail-section h4,
.wizard-body h4 {
  margin: 0 0 10px;
  color: #374151;
}

.detail-section p {
  margin: 0 0 6px;
  color: #526070;
}

.permission-row {
  display: grid;
  grid-template-columns: 56px 1fr;
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

.definition-grid {
  display: grid;
  grid-template-columns: 72px 1fr;
  gap: 8px;
  align-items: center;
  color: #64748b;
  font-size: 12px;
}

.definition-grid code {
  display: block;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.tool-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}

.file-browser {
  display: grid;
  grid-template-rows: auto 1fr;
  gap: 10px;
}

.file-list {
  display: grid;
  gap: 6px;
}

.file-row {
  min-height: 34px;
  border: 1px solid #edf0f5;
  background: #fff;
  border-radius: 6px;
  display: grid;
  grid-template-columns: 18px 1fr auto;
  align-items: center;
  gap: 8px;
  padding: 0 8px;
  text-align: left;
  cursor: pointer;
}

.file-row.active,
.file-row:hover {
  border-color: #2f80ed;
  background: #f5f9ff;
}

.file-row span {
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.file-row small,
.file-table-row small {
  color: #94a3b8;
}

.file-content {
  min-height: 220px;
  max-height: 420px;
  overflow: auto;
  margin: 0;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 6px;
  color: #334155;
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
}

.audit-card {
  border: 1px solid #edf0f5;
  border-radius: 8px;
  background: #fafcff;
  padding: 12px;
}

.audit-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.risk-list {
  display: grid;
  gap: 8px;
}

.risk-row {
  display: grid;
  grid-template-columns: 58px 1fr;
  gap: 6px;
  align-items: start;
}

.risk-row p {
  grid-column: 1 / -1;
  margin: 0;
  color: #526070;
}

.override-note {
  margin-top: 10px;
  color: #b45309;
}

.inline-empty {
  color: #8a94a3;
  text-align: center;
  padding: 28px 0;
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
  font-size: 46px;
  margin-bottom: 12px;
}

.empty-state h3 {
  margin: 0 0 6px;
  color: #374151;
}

.wizard-body {
  margin-top: 18px;
}

.wizard-form {
  margin-top: 16px;
}

.upload-row {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #64748b;
}

.preview-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.candidate-row {
  display: block;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  padding: 10px;
  margin-bottom: 8px;
}

.candidate-row strong {
  margin-right: 8px;
}

.candidate-row span {
  color: #64748b;
  font-size: 12px;
}

.file-table {
  max-height: 220px;
  overflow: auto;
  border: 1px solid #edf0f5;
  border-radius: 8px;
}

.file-table-row {
  display: grid;
  grid-template-columns: 1fr 120px 88px;
  gap: 8px;
  align-items: center;
  min-height: 36px;
  padding: 0 10px;
  border-bottom: 1px solid #edf0f5;
}

.file-table-row:last-child {
  border-bottom: 0;
}

.file-table-row span {
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.confirm-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 16px 0;
  color: #526070;
}

.confirm-summary strong {
  color: #111827;
}

@media (max-width: 1180px) {
  .detail-panel {
    display: none;
  }
}
</style>
