<template>
  <div class="grayscale-page">
    <div class="grayscale-main">
      <div class="page-header">
        <h2>灰度配置管理</h2>
        <span class="page-subtitle">
          控制各领域的 UI 可见性和功能开关。<strong>公共</strong>配置通过勾选领域来决定对哪些领域生效
        </span>
      </div>

      <el-tabs v-model="activeDomain" @tab-click="onDomainChange">
        <el-tab-pane label="公共" name="common"></el-tab-pane>
        <el-tab-pane label="智能研发" name="rd"></el-tab-pane>
        <el-tab-pane label="智慧教育" name="edu"></el-tab-pane>
        <el-tab-pane label="智慧办公" name="office"></el-tab-pane>
      </el-tabs>

      <div class="toolbar">
        <div class="toolbar-left">
          <el-button size="small" type="primary" @click="openCreateDialog">新建配置</el-button>
          <el-button size="small" type="primary" :loading="saving" @click="handleBatchSave">
            批量保存
          </el-button>
          <el-button size="small" @click="handleRefresh">刷新</el-button>
          <span class="change-hint" v-if="dirtyCount > 0">
            已修改 {{ dirtyCount }} 项
          </span>
        </div>
        <div class="toolbar-right">
          <el-input
            v-model="searchText"
            size="small"
            placeholder="搜索配置键或名称"
            clearable
            prefix-icon="el-icon-search"
            style="width: 260px"
          />
          <el-select
            v-model="filterType"
            size="small"
            placeholder="类型筛选"
            clearable
            style="width: 120px; margin-left: 8px"
          >
            <el-option label="UI" value="ui" />
            <el-option label="功能" value="feature" />
            <el-option label="Agent" value="agent" />
            <el-option label="工具" value="tool" />
          </el-select>
        </div>
      </div>

      <el-table
        :data="filteredData"
        v-loading="loading"
        border
        stripe
        size="small"
        class="config-table"
        row-key="id"
      >
        <el-table-column prop="config_type" label="类型" width="80">
          <template slot-scope="{ row }">
            <el-tag size="mini" :type="typeTag(row.config_type)">
              {{ typeLabel(row.config_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="config_key" label="配置键" min-width="200" show-overflow-tooltip />
        <el-table-column prop="config_name" label="名称" min-width="140" show-overflow-tooltip />
        <el-table-column prop="description" label="描述" min-width="160" show-overflow-tooltip>
          <template slot-scope="{ row }">
            {{ row.description || '-' }}
          </template>
        </el-table-column>

        <!-- 公共 tab：领域多选 -->
        <el-table-column v-if="activeDomain === 'common'" label="适用领域" width="200" align="center">
          <template slot-scope="{ row }">
            <el-checkbox-group
              v-model="row._domains"
              size="mini"
              @change="markDirty(row)"
            >
              <el-checkbox label="rd">研发</el-checkbox>
              <el-checkbox label="edu">教育</el-checkbox>
              <el-checkbox label="office">办公</el-checkbox>
            </el-checkbox-group>
          </template>
        </el-table-column>

        <el-table-column label="启用" width="70" align="center">
          <template slot-scope="{ row }">
            <el-switch v-model="row.enabled" @change="markDirty(row)" />
          </template>
        </el-table-column>
        <el-table-column label="可见" width="70" align="center">
          <template slot-scope="{ row }">
            <el-switch v-model="row.visible" @change="markDirty(row)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center">
          <template slot-scope="{ row }">
            <el-button
              size="mini"
              type="danger"
              plain
              icon="el-icon-delete"
              @click="handleDelete(row)"
            />
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!loading && tableData.length === 0" class="empty-hint">
        该领域暂无灰度配置，点击「新建配置」添加。
      </div>
    </div>

    <!-- 新建配置弹窗 -->
    <el-dialog
      title="新建灰度配置"
      :visible.sync="createVisible"
      width="460px"
      top="12vh"
      :close-on-click-modal="false"
    >
      <el-form label-position="top" size="small">
        <el-form-item label="配置键 (config_key)">
          <el-input v-model="form.config_key" placeholder="例如：ui.sidebar.xxx" maxlength="100" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="form.config_name" placeholder="例如：侧边栏-新功能" maxlength="200" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.config_type" style="width: 100%">
            <el-option label="UI" value="ui" />
            <el-option label="功能" value="feature" />
            <el-option label="Agent" value="agent" />
            <el-option label="工具" value="tool" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属领域">
          <el-select v-model="form.domain" style="width: 100%">
            <el-option label="公共 (common)" value="common" />
            <el-option label="智能研发 (rd)" value="rd" />
            <el-option label="智慧教育 (edu)" value="edu" />
            <el-option label="智慧办公 (office)" value="office" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.domain === 'common'" label="适用领域">
          <el-checkbox-group v-model="form.domains">
            <el-checkbox label="rd">研发</el-checkbox>
            <el-checkbox label="edu">教育</el-checkbox>
            <el-checkbox label="office">办公</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="描述（可选）">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="用途说明" />
        </el-form-item>
      </el-form>
      <span slot="footer">
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="creating">创建</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import {
  batchUpdateGrayscaleConfig,
  createGrayscaleConfig,
  deleteGrayscaleConfig,
} from '../api/grayscale'

export default {
  name: 'GrayscaleConsole',
  data() {
    return {
      activeDomain: 'common',
      loading: false,
      saving: false,
      creating: false,
      dirtyIds: new Set(),
      searchText: '',
      filterType: '',
      createVisible: false,
      form: {
        config_key: '',
        config_name: '',
        config_type: 'ui',
        domain: 'common',
        domains: [],
        description: '',
      },
    }
  },
  computed: {
    tableData() {
      const configs = this.$store.state.grayscale.configsByDomain[this.activeDomain] || []
      return configs.map(c => ({
        ...c,
        _domains: c.domains ? [...c.domains] : [],
      }))
    },
    filteredData() {
      let list = this.tableData
      if (this.searchText) {
        const s = this.searchText.toLowerCase()
        list = list.filter(
          c => c.config_key.toLowerCase().includes(s) || c.config_name.toLowerCase().includes(s)
        )
      }
      if (this.filterType) {
        list = list.filter(c => c.config_type === this.filterType)
      }
      return list
    },
    dirtyCount() {
      return this.dirtyIds.size
    },
  },
  methods: {
    typeLabel(type) {
      return { ui: 'UI', feature: '功能', agent: 'Agent', tool: '工具' }[type] || type
    },
    typeTag(type) {
      return { ui: '', feature: 'success', agent: 'warning', tool: 'info' }[type] || ''
    },

    loadData() {
      this.loading = true
      this.dirtyIds = new Set()
      const promises = [this.$store.dispatch('grayscale/fetchGrayscaleConfig', this.activeDomain)]
      if (this.activeDomain !== 'common') {
        promises.push(this.$store.dispatch('grayscale/fetchGrayscaleConfig', 'common'))
      }
      Promise.all(promises).finally(() => {
        this.loading = false
      })
    },

    markDirty(row) {
      this.dirtyIds.add(row.id)
    },

    onDomainChange() {
      this.searchText = ''
      this.filterType = ''
      this.loadData()
    },

    handleRefresh() {
      this.loadData()
    },

    async handleBatchSave() {
      if (this.dirtyIds.size === 0) {
        this.$message.info('没有需要保存的更改')
        return
      }
      this.saving = true
      try {
        const dirtyRows = this.tableData.filter(c => this.dirtyIds.has(c.id))
        const updates = dirtyRows.map(c => {
          const item = { id: c.id, enabled: !!c.enabled, visible: !!c.visible }
          if (this.activeDomain === 'common') {
            item.domains = c._domains || []
          }
          return item
        })

        const res = await batchUpdateGrayscaleConfig(updates)
        if (res.code === 200) {
          this.$message.success(`已保存 ${res.data.updated} 项配置`)
          this.dirtyIds = new Set()
          this.loadData()
        } else {
          this.$message.error(res.message || '保存失败')
        }
      } catch {
        this.$message.error('保存失败')
      } finally {
        this.saving = false
      }
    },

    // ── 新建 ──
    openCreateDialog() {
      this.form = {
        config_key: '',
        config_name: '',
        config_type: 'ui',
        domain: this.activeDomain,
        domains: this.activeDomain === 'common' ? ['rd', 'edu', 'office'] : [],
        description: '',
      }
      this.createVisible = true
    },

    async handleCreate() {
      if (!this.form.config_key.trim() || !this.form.config_name.trim()) {
        this.$message.warning('配置键和名称不能为空')
        return
      }
      this.creating = true
      try {
        const res = await createGrayscaleConfig({
          config_key: this.form.config_key.trim(),
          config_name: this.form.config_name.trim(),
          config_type: this.form.config_type,
          domain: this.form.domain,
          domains: this.form.domain === 'common' ? this.form.domains : undefined,
          description: this.form.description,
        })
        if (res.code === 201) {
          this.$message.success('配置已创建')
          this.createVisible = false
          // 加载新配置所属领域的列表
          const domainToReload = this.form.domain
          this.$store.dispatch('grayscale/fetchGrayscaleConfig', domainToReload)
          if (this.activeDomain !== domainToReload) {
            this.$store.dispatch('grayscale/fetchGrayscaleConfig', this.activeDomain)
          }
          this.dirtyIds = new Set()
        } else {
          this.$message.error(res.message || '创建失败')
        }
      } catch {
        this.$message.error('创建失败')
      } finally {
        this.creating = false
      }
    },

    // ── 删除 ──
    async handleDelete(row) {
      try {
        await this.$confirm(`确认删除配置「${row.config_key}」？`, '提示', {
          type: 'warning',
        })
        const res = await deleteGrayscaleConfig(row.id)
        if (res.code === 200) {
          this.$message.success('已删除')
          this.dirtyIds.delete(row.id)
          this.loadData()
        } else {
          this.$message.error(res.message || '删除失败')
        }
      } catch {
        // cancelled
      }
    },
  },
  mounted() {
    this.loadData()
  },
}
</script>

<style scoped>
.grayscale-page {
  padding: 24px 32px;
  height: 100vh;
  background: linear-gradient(135deg, #e8f0ff 0%, #f0f5ff 50%, #f5f7fa 100%);
  overflow: hidden;
  display: flex;
}

.grayscale-main {
  flex: 1;
  background: #fff;
  border-radius: 12px;
  padding: 28px 32px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  overflow-y: auto;
}

.page-header {
  margin-bottom: 22px;
}

.page-header h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: #1e293b;
}

.page-subtitle {
  font-size: 13px;
  color: #94a3b8;
  margin-top: 4px;
  display: block;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-right {
  display: flex;
  align-items: center;
}

.change-hint {
  font-size: 12px;
  color: #f0a020;
  margin-left: 4px;
}

.config-table {
  font-size: 13px;
}

.empty-hint {
  text-align: center;
  padding: 40px;
  color: #94a3b8;
  font-size: 14px;
}
</style>
