<template>
  <div class="tools-page">
    <AppSidebar />

    <!-- 分类侧栏 -->
    <div class="tools-categories">
      <div class="cat-header">
        <h3>工具分类</h3>
        <el-button size="mini" icon="el-icon-plus" circle @click="handleNewTool"></el-button>
      </div>
      <div class="cat-list">
        <div
          v-for="cat in categories"
          :key="cat.id"
          class="cat-item"
          :class="{ active: activeCat === cat.id }"
          @click="activeCat = cat.id"
        >
          <i :class="cat.icon"></i>
          <span class="cat-name">{{ cat.name }}</span>
          <span class="cat-count">{{ filteredTools(cat.id).length }}</span>
        </div>
      </div>
    </div>

    <!-- 内容区 -->
    <div class="tools-content">
      <template v-if="activeCat">
        <div class="content-header">
          <div class="header-left">
            <i :class="activeCatObj?.icon || 'el-icon-folder-opened'"></i>
            <h2>{{ activeCatObj?.name || '工具' }}</h2>
          </div>
          <el-button type="primary" icon="el-icon-plus" @click="handleNewTool">新建工具</el-button>
        </div>

        <div class="tool-grid">
          <div
            v-for="tool in filteredTools(activeCat)"
            :key="tool.value"
            class="tool-card"
            @click="openDetail(tool)"
          >
            <div class="tool-icon" :style="{ background: tool.color || '#4080ff' }">
              <i :class="tool.icon || 'el-icon-setting'"></i>
            </div>
            <div class="tool-body">
              <div class="tool-top">
                <h3>{{ tool.name }}</h3>
                <span class="tool-type-badge" :style="tool.custom ? 'background:#fef3c7;color:#d97706' : 'background:#f0f5ff;color:#4080ff'">
                  {{ tool.custom ? '自定义' : '内置' }}
                </span>
              </div>
              <p class="tool-desc">{{ tool.description || '暂无描述' }}</p>
              <div class="tool-config" v-if="tool.custom && tool.params">
                <code>{{ formatParams(tool.params) }}</code>
              </div>
              <div class="tool-value" v-else-if="!tool.custom">
                <code>{{ tool.value }}</code>
              </div>
            </div>
            <div class="tool-actions" v-if="tool.custom" @click.stop>
              <el-button size="mini" type="text" icon="el-icon-edit" @click="handleEditCustom(tool)"></el-button>
              <el-button size="mini" type="text" icon="el-icon-delete" style="color:#f56c6c" @click="handleDeleteCustom(tool)"></el-button>
            </div>
          </div>

          <div v-if="filteredTools(activeCat).length === 0" class="empty-tools">
            <i class="el-icon-s-tools"></i>
            <p>该分类暂无工具</p>
            <el-button size="small" type="primary" @click="handleNewTool">新建工具</el-button>
          </div>
        </div>
      </template>

      <template v-else>
        <div class="empty-state">
          <i class="el-icon-s-tools"></i>
          <h2>选择分类</h2>
          <p>请从左侧选择一个工具分类</p>
        </div>
      </template>
    </div>

    <!-- 工具详情对话框 -->
    <el-dialog :title="detail?.label || '工具详情'" :visible.sync="showDetail" width="520px">
      <div v-if="detail" class="detail-body">
        <div class="detail-icon" :style="{ background: detail.color || '#4080ff' }">
          <i :class="detail.icon || 'el-icon-setting'"></i>
        </div>
        <h2>{{ detail.label }}</h2>
        <p class="detail-cat">分类: {{ categoryName(detail.category) }}</p>
        <p class="detail-desc">{{ detail.description || '暂无描述' }}</p>
        <div class="detail-meta">
          <h4>{{ detail.custom ? '配置参数' : '工具标识' }}</h4>
          <pre>{{ detail.custom ? formatParams(detail.params) || '无' : detail.value }}</pre>
        </div>
      </div>
    </el-dialog>

    <!-- 新建/编辑工具对话框 -->
    <el-dialog :title="editingTool ? '编辑工具' : '新建工具'" :visible.sync="showForm" width="480px">
      <el-form label-position="top">
        <el-form-item label="工具名称">
          <el-input v-model="form.label" placeholder="输入工具名称"></el-input>
        </el-form-item>
        <el-form-item label="工具标识">
          <el-input v-model="form.value" placeholder="英文标识，如 my_tool"></el-input>
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category" style="width:100%">
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="图标">
          <el-select v-model="form.icon" style="width:100%">
            <el-option label="设置" value="el-icon-setting"></el-option>
            <el-option label="代码" value="el-icon-monitor"></el-option>
            <el-option label="文档" value="el-icon-document"></el-option>
            <el-option label="数据" value="el-icon-data-analysis"></el-option>
            <el-option label="搜索" value="el-icon-search"></el-option>
            <el-option label="链接" value="el-icon-connection"></el-option>
            <el-option label="图片" value="el-icon-picture"></el-option>
            <el-option label="终端" value="el-icon-console"></el-option>
            <el-option label="分享" value="el-icon-share"></el-option>
            <el-option label="工具" value="el-icon-s-tools"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="颜色">
          <el-color-picker v-model="form.color"></el-color-picker>
        </el-form-item>
        <el-form-item label="描述">
          <el-input type="textarea" :rows="3" v-model="form.description" placeholder="描述工具的功能..."></el-input>
        </el-form-item>
        <el-form-item label="参数/配置 (JSON)">
          <el-input type="textarea" :rows="4" v-model="form.params" placeholder='{"url": "", "method": "GET"}'></el-input>
        </el-form-item>
      </el-form>
      <span slot="footer">
        <el-button @click="showForm = false">取消</el-button>
        <el-button type="primary" @click="handleSaveTool">保存</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import AppSidebar from '../components/Sidebar/index.vue'
import { getTools, createTool, updateTool, deleteTool } from '../api/tools'

const TOOL_CATEGORIES = [
  { id: 'tool_code', name: '代码工具', icon: 'el-icon-monitor', color: '#3b82f6' },
  { id: 'tool_file', name: '文件处理', icon: 'el-icon-document', color: '#22c55e' },
  { id: 'tool_web', name: '网络工具', icon: 'el-icon-connection', color: '#8b5cf6' },
  { id: 'tool_data', name: '数据工具', icon: 'el-icon-data-analysis', color: '#14b8a6' },
  { id: 'tool_image', name: '图像工具', icon: 'el-icon-picture', color: '#ec4899' },
  { id: 'tool_sys', name: '系统工具', icon: 'el-icon-setting', color: '#f59e0b' },
  { id: 'tool_custom', name: '自定义工具', icon: 'el-icon-plus', color: '#a0aec0' },
]

export default {
  name: 'Tools',
  components: { AppSidebar },
  data() {
    return {
      activeCat: 'tool_code',
      showDetail: false,
      showForm: false,
      editingTool: null,
      detail: null,
      allTools: [],
      loading: false,
      form: {
        name: '', value: '', category: 'tool_custom', icon: 'el-icon-setting',
        color: '#a0aec0', description: '', params: '',
      },
    }
  },
  computed: {
    categories() { return TOOL_CATEGORIES },
    activeCatObj() {
      return this.categories.find(c => c.id === this.activeCat)
    },
  },
  created() {
    this.fetchTools()
  },
  methods: {
    async fetchTools() {
      this.loading = true
      try {
        const res = await getTools()
        if (res.code === 200) {
          this.allTools = res.data.map(t => ({
            ...t,
            label: t.name,
            custom: !t.is_builtin,
          }))
        }
      } catch (e) {
        this.$message.error('加载工具失败')
        this.allTools = []
      } finally {
        this.loading = false
      }
    },
    filteredTools(catId) {
      return this.allTools.filter(t => t.category === catId)
    },
    categoryName(catId) {
      const c = this.categories.find(c => c.id === catId)
      return c ? c.name : '未分类'
    },
    openDetail(tool) {
      this.detail = tool
      this.showDetail = true
    },
    handleNewTool() {
      this.editingTool = null
      this.form = { name: '', value: '', category: 'tool_custom', icon: 'el-icon-setting', color: '#a0aec0', description: '', params: '' }
      this.showForm = true
    },
    handleEditCustom(tool) {
      this.editingTool = tool
      this.form = {
        name: tool.name, value: tool.value, category: tool.category,
        icon: tool.icon || 'el-icon-setting', color: tool.color || '#a0aec0',
        description: tool.description || '', params: typeof tool.params === 'object' ? JSON.stringify(tool.params, null, 2) : (tool.params || ''),
      }
      this.showForm = true
    },
    async handleSaveTool() {
      if (!this.form.name || !this.form.value) {
        this.$message.warning('请填写工具名称和标识')
        return
      }
      const apiData = {
        name: this.form.name,
        value: this.form.value,
        category: this.form.category,
        icon: this.form.icon,
        color: this.form.color,
        description: this.form.description,
      }
      try {
        let res
        if (this.editingTool) {
          res = await updateTool(this.editingTool.id, apiData)
          if (res.code === 200) {
            this.$message.success('工具已更新')
          }
        } else {
          res = await createTool(apiData)
          if (res.code === 201) {
            this.$message.success('工具已创建')
          }
        }
        this.showForm = false
        this.editingTool = null
        await this.fetchTools()
      } catch (e) {
        this.$message.error(this.editingTool ? '更新失败' : '创建失败')
      }
    },
    async handleDeleteCustom(tool) {
      this.$confirm(`确认删除工具"${tool.name}"？`, '提示', {
        type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消',
      }).then(async () => {
        try {
          await deleteTool(tool.id)
          this.$message.success('工具已删除')
          await this.fetchTools()
        } catch (e) {
          this.$message.error('删除失败')
        }
      }).catch(() => {})
    },
    formatParams(params) {
      if (!params) return ''
      if (typeof params === 'object') return JSON.stringify(params, null, 2)
      return params
    },
  },
}
</script>

<style scoped>
.tools-page {
  display: flex;
  gap: 12px;
  padding: 12px;
  height: 100vh;
  background: linear-gradient(135deg, #e8f0ff 0%, #f0f5ff 50%, #f5f7fa 100%);
  overflow: hidden;
}

/* 分类面板 */
.tools-categories {
  width: 220px;
  flex-shrink: 0;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.cat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 16px 12px;
}
.cat-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}
.cat-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 8px;
}
.cat-list::-webkit-scrollbar { width: 4px; }
.cat-list::-webkit-scrollbar-thumb { background: #dcdde1; border-radius: 4px; }
.cat-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
  margin-bottom: 2px;
}
.cat-item:hover { background: #f5f6f7; }
.cat-item.active { background: #f0f5ff; color: #4080ff; }
.cat-item i { font-size: 16px; color: inherit; }
.cat-name { flex: 1; font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cat-count {
  font-size: 11px; color: #86909c;
  background: #f0f0f0; padding: 0 8px; border-radius: 10px; line-height: 20px;
}
.cat-item.active .cat-count { background: rgba(64,128,255,0.12); color: #4080ff; }

/* 内容区 */
.tools-content {
  flex: 1;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}
.content-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.header-left i { font-size: 22px; color: #4080ff; }
.content-header h2 { margin: 0; font-size: 20px; font-weight: 600; color: #1e293b; }
.content-header .el-button--primary {
  background: #4080ff; border: none; border-radius: 8px;
}

/* 工具网格 */
.tool-grid {
  flex: 1;
  padding: 20px 24px;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 14px;
  align-content: start;
}
.tool-grid::-webkit-scrollbar { width: 4px; }
.tool-grid::-webkit-scrollbar-thumb { background: #dcdde1; border-radius: 4px; }

.tool-card {
  background: #ffffff;
  border: 1px solid #f0f0f0;
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  gap: 14px;
  position: relative;
}
.tool-card:hover {
  border-color: #4080ff;
  box-shadow: 0 4px 20px rgba(64,128,255,0.12);
  transform: translateY(-2px);
}
.tool-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #fff;
  font-size: 20px;
}
.tool-body {
  flex: 1;
  min-width: 0;
}
.tool-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.tool-top h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}
.tool-type-badge {
  font-size: 10px;
  padding: 1px 8px;
  border-radius: 4px;
  line-height: 18px;
  flex-shrink: 0;
}
.tool-desc {
  margin: 0;
  font-size: 12px;
  color: #64748b;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.tool-config, .tool-value {
  margin-top: 6px;
}
.tool-config code, .tool-value code {
  font-size: 11px;
  background: #f0f2f5;
  padding: 2px 8px;
  border-radius: 4px;
  color: #475569;
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tool-actions {
  position: absolute;
  top: 8px;
  right: 8px;
  display: none;
  gap: 2px;
}
.tool-card:hover .tool-actions {
  display: flex;
}

/* 空状态 */
.empty-tools {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #86909c;
}
.empty-tools i { font-size: 48px; color: #dcdde1; margin-bottom: 12px; }
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #86909c;
}
.empty-state i { font-size: 64px; color: #dcdde1; margin-bottom: 16px; }
.empty-state h2 { margin: 0 0 8px; color: #1e293b; }

/* 详情对话框 */
.detail-body { text-align: center; padding: 10px 0; }
.detail-icon {
  width: 56px; height: 56px; border-radius: 14px;
  display: inline-flex; align-items: center; justify-content: center;
  color: #fff; font-size: 26px; margin-bottom: 12px;
}
.detail-body h2 { margin: 0 0 6px; font-size: 20px; color: #1e293b; }
.detail-cat { font-size: 13px; color: #64748b; margin: 0 0 12px; }
.detail-desc {
  font-size: 14px; color: #475569; line-height: 1.6; margin: 0 0 20px;
  text-align: left; background: #f8fafc; padding: 12px 16px; border-radius: 8px;
}
.detail-meta { text-align: left; }
.detail-meta h4 { margin: 0 0 8px; font-size: 13px; color: #1e293b; }
.detail-meta pre {
  font-size: 12px; background: #f0f2f5; padding: 8px 12px;
  border-radius: 6px; color: #475569; margin: 0;
}
</style>
