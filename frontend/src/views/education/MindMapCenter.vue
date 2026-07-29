<template>
  <EducationShell
    title="课程思维导图"
    :subtitle="course ? `${course.title} · 从已发布课时与知识资料生成可编辑结构` : '选择一门学生课程'"
  >
    <template #actions>
      <el-button
        icon="el-icon-edit"
        :disabled="!activeMap"
        @click="openEditor"
      >编辑结构</el-button>
      <el-button
        icon="el-icon-magic-stick"
        :loading="generating"
        :disabled="!course"
        @click="generate"
      >规则快速生成</el-button>
      <el-button
        type="primary"
        icon="el-icon-cpu"
        :loading="agentRunning"
        :disabled="!course"
        @click="generateWithAgent"
      >Agent 生成导图</el-button>
    </template>

    <el-alert
      v-if="roleError"
      title="当前没有学生课程"
      type="warning"
      :closable="false"
      show-icon
    />

    <template v-else-if="course">
      <EmbeddedAgentRecord
        :run="productAgentRun"
        @terminal="handleAgentTerminal"
        @poll-error="$message.error('Agent 运行状态暂时无法刷新')"
        @close="closeAgentRun"
      />

      <section class="map-shell">
        <aside class="map-list">
          <header>
            <span>MY COURSE MAPS</span>
            <h2>导图版本</h2>
            <p>每次编辑都会新增不可变版本，原始课程来源保持可追溯。</p>
          </header>
          <button
            v-for="mindMap in mindMaps"
            :key="mindMap.id"
            type="button"
            :class="{ active: activeMap && activeMap.id === mindMap.id }"
            @click="selectMap(mindMap)"
          >
            <span class="map-mini"><i class="el-icon-share"></i></span>
            <span>
              <b>{{ mindMap.title }}</b>
              <small>v{{ mindMap.current_version.version_number }} · {{ sourceCount(mindMap) }} 个来源</small>
            </span>
            <i class="el-icon-arrow-right"></i>
          </button>
          <div v-if="!mindMaps.length" class="no-map">
            <i class="el-icon-share"></i>
            <p>还没有课程导图</p>
          </div>
          <footer>
            <i class="el-icon-link"></i>
            <span>节点来源仅指向你有权访问的课程内容</span>
          </footer>
        </aside>

        <main class="map-canvas" data-testid="course-mind-map">
          <template v-if="activeMap && activeMap.current_version">
            <header class="canvas-header">
              <div>
                <span>VERSION {{ activeMap.current_version.version_number }}</span>
                <h2>{{ activeMap.title }}</h2>
                <p>{{ activeMap.current_version.change_summary || '由课程已发布内容生成' }}</p>
              </div>
              <dl>
                <div><dt>节点</dt><dd>{{ nodeCount(activeMap.current_version.tree) }}</dd></div>
                <div><dt>来源</dt><dd>{{ activeMap.current_version.source_refs.length }}</dd></div>
                <div><dt>更新时间</dt><dd>{{ shortDate(activeMap.current_version.created_at) }}</dd></div>
              </dl>
            </header>
            <div class="tree-viewport">
              <div class="canvas-grid"></div>
              <MindMapTree :node="activeMap.current_version.tree" />
            </div>
          </template>
          <div v-else class="blank-map">
            <div class="map-symbol">
              <span></span><span></span><span></span><i class="el-icon-share"></i>
            </div>
            <h2>从课程来源生成第一张思维导图</h2>
            <p>已发布课时和知识库资料会成为带来源链接的节点，你可以继续编辑结构。</p>
            <el-button type="primary" :loading="generating" @click="generate">生成课程导图</el-button>
          </div>
        </main>
      </section>
    </template>

    <el-dialog title="编辑思维导图结构" :visible.sync="editorVisible" width="780px">
      <el-alert
        title="编辑 JSON 源结构会创建一个新版本；节点需包含唯一 id、label 和 children。"
        type="info"
        :closable="false"
        show-icon
      />
      <el-input
        v-model="editJson"
        class="json-editor"
        type="textarea"
        :rows="18"
        spellcheck="false"
      />
      <el-input
        v-model.trim="changeSummary"
        placeholder="本次修改说明"
        maxlength="200"
      />
      <template #footer>
        <el-button @click="editorVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveMindMapVersion">保存新版本</el-button>
      </template>
    </el-dialog>
  </EducationShell>
</template>

<script>
import EducationShell from '../../components/education/EducationShell.vue'
import MindMapTree from '../../components/education/MindMapTree.vue'
import EmbeddedAgentRecord from '../../components/education/EmbeddedAgentRecord.vue'

export default {
  name: 'MindMapCenter',
  components: { EducationShell, MindMapTree, EmbeddedAgentRecord },
  data() {
    return {
      roleError: false,
      generating: false,
      saving: false,
      editorVisible: false,
      editJson: '',
      changeSummary: '',
    }
  },
  computed: {
    course() { return this.$store.getters['education/activeCourse'] },
    mindMaps() { return this.$store.getters['education/mindMaps'] || [] },
    activeMap() { return this.$store.getters['education/activeMindMap'] },
    productAgentRun() { return this.$store.getters['education/productAgentRun'] },
    agentRunning() {
      return Boolean(this.productAgentRun && ['pending', 'running'].includes(this.productAgentRun.status))
    },
  },
  watch: {
    'course.id'(next, previous) {
      if (next && next !== previous) this.load(next)
    },
  },
  created() {
    this.bootstrap()
  },
  methods: {
    async bootstrap() {
      try {
        const course = await this.$store.dispatch('education/ensureRoleCourse', {
          courseId: this.$route.query.courseId,
          role: 'student',
        })
        await this.load(course.id)
      } catch (error) {
        this.roleError = true
      }
    },
    async load(courseId) {
      try {
        const maps = await this.$store.dispatch('education/fetchMindMaps', courseId)
        this.$store.commit('education/SET_ACTIVE_MIND_MAP', maps[0] || null)
        await this.$store.dispatch('education/restoreProductAgentRun', {
          courseId,
          productCode: 'course_mind_map',
        })
      } catch (error) {
        this.$message.error('课程导图加载失败')
      }
    },
    async generate() {
      this.generating = true
      try {
        await this.$store.dispatch('education/createMindMap', {
          courseId: this.course.id,
          data: { title: `${this.course.title} · 我的导图` },
        })
        this.$message.success('已从课程来源生成导图')
      } catch (error) {
        this.$message.error('导图生成失败')
      } finally {
        this.generating = false
      }
    },
    async generateWithAgent() {
      try {
        await this.$store.dispatch('education/startProductAgentRun', {
          course_id: this.course.id,
          product_code: 'course_mind_map',
          options: { title: `${this.course.title} · 我的导图` },
        })
        this.$message.success('笔记整理与学习规划 Agent 已启动')
      } catch (error) {
        const detail = error.response && error.response.data && error.response.data.error
        this.$message.error(detail || '思维导图 Agent 启动失败')
      }
    },
    async handleAgentTerminal(run) {
      if (run.status !== 'completed') return
      const previousIds = new Set(this.mindMaps.map(item => item.id))
      const maps = await this.$store.dispatch('education/fetchMindMaps', this.course.id)
      const created = maps.find(item => !previousIds.has(item.id)) || maps[0]
      if (created) {
        this.$store.commit('education/SET_ACTIVE_MIND_MAP', created)
        this.$message.success('Agent 已创建可编辑课程导图')
      } else {
        this.$message.warning('Agent 已结束，但未创建导图；可查看协作记录或使用规则生成')
      }
    },
    closeAgentRun() {
      this.$store.commit('education/SET_PRODUCT_AGENT_RUN', null)
    },
    selectMap(mindMap) {
      this.$store.commit('education/SET_ACTIVE_MIND_MAP', mindMap)
    },
    openEditor() {
      if (!this.activeMap) return
      this.editJson = JSON.stringify(this.activeMap.current_version.tree, null, 2)
      this.changeSummary = ''
      this.editorVisible = true
    },
    async saveMindMapVersion() {
      let tree
      try {
        tree = JSON.parse(this.editJson)
      } catch (error) {
        this.$message.error('JSON 格式无效，请检查逗号和引号')
        return
      }
      this.saving = true
      try {
        await this.$store.dispatch('education/saveMindMapVersion', {
          courseId: this.course.id,
          mindMapId: this.activeMap.id,
          data: {
            tree,
            source_refs: this.collectSourceRefs(tree),
            change_summary: this.changeSummary || '学生编辑结构',
          },
        })
        this.editorVisible = false
        this.$message.success('思维导图新版本已保存')
      } catch (error) {
        this.$message.error('导图结构未通过校验')
      } finally {
        this.saving = false
      }
    },
    collectSourceRefs(node) {
      if (!node || typeof node !== 'object') return []
      const own = node.source_ref ? [node.source_ref] : []
      const childRefs = (node.children || []).flatMap(child => this.collectSourceRefs(child))
      return [...new Set([...own, ...childRefs])]
    },
    nodeCount(node) {
      if (!node) return 0
      return 1 + (node.children || []).reduce((total, child) => total + this.nodeCount(child), 0)
    },
    sourceCount(mindMap) {
      return (mindMap.current_version && mindMap.current_version.source_refs || []).length
    },
    shortDate(value) {
      if (!value) return '—'
      return new Date(value).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
    },
  },
}
</script>

<style scoped>
.map-shell { display: grid; grid-template-columns: 245px minmax(0, 1fr); gap: 14px; min-height: 640px; }
.map-list { display: flex; flex-direction: column; padding: 18px 13px; border: 1px solid #dfe8e5; border-radius: 14px; background: linear-gradient(180deg, #fafcfb, #f3f8f6); }
.map-list > header { padding: 2px 5px 15px; border-bottom: 1px solid #dfe8e5; }.map-list header > span { color: #347f74; font-size: 8px; font-weight: 800; letter-spacing: .14em; }.map-list h2 { margin: 6px 0 5px; color: #344944; font-family: 'Noto Serif SC', 'Songti SC', SimSun, serif; font-size: 17px; }.map-list header p { margin: 0; color: #8a9894; font-size: 9px; line-height: 1.55; }
.map-list > button { width: 100%; display: grid; grid-template-columns: 34px 1fr auto; align-items: center; gap: 8px; padding: 11px 7px; border: 0; border-bottom: 1px solid #e5ecea; background: transparent; color: #6e7d79; cursor: pointer; text-align: left; }.map-list > button:hover, .map-list > button.active { border-radius: 9px; background: #fff; box-shadow: 0 5px 16px rgba(44, 80, 72, .06); }
.map-mini { width: 31px; height: 31px; display: grid; place-items: center; border-radius: 9px; background: #e5f1ed; color: #347d73; }.map-list button b, .map-list button small { display: block; }.map-list button b { color: #425651; font-size: 10px; }.map-list button small { margin-top: 4px; color: #97a3a0; font-size: 8px; }.map-list button > i { color: #9ca7a4; font-size: 9px; }
.no-map { flex: 1; display: grid; place-content: center; color: #95a19e; text-align: center; }.no-map i { font-size: 27px; color: #6f9c93; }.no-map p { margin: 8px 0; font-size: 9px; }
.map-list > footer { display: flex; gap: 7px; margin-top: auto; padding: 12px 4px 0; color: #93a09c; font-size: 8px; line-height: 1.45; }
.map-canvas { min-width: 0; overflow: hidden; border: 1px solid #dce6e3; border-radius: 14px; background: #fff; }
.canvas-header { min-height: 94px; display: flex; align-items: center; justify-content: space-between; padding: 18px 24px; border-bottom: 1px solid #e4ebe9; background: #fbfdfc; }.canvas-header > div > span { color: #3c897e; font-size: 8px; font-weight: 800; letter-spacing: .13em; }.canvas-header h2 { margin: 5px 0 3px; color: #334843; font-size: 16px; }.canvas-header p { margin: 0; color: #929e9b; font-size: 9px; }
.canvas-header dl { display: flex; margin: 0; }.canvas-header dl div { min-width: 65px; padding: 0 12px; border-left: 1px solid #dfe7e5; text-align: center; }.canvas-header dt { color: #939f9c; font-size: 8px; }.canvas-header dd { margin: 4px 0 0; color: #397b72; font-family: Georgia, serif; font-size: 15px; }
.tree-viewport { min-height: 544px; padding: 42px; overflow: auto; position: relative; }.tree-viewport > .mind-node { position: relative; z-index: 1; }.canvas-grid { position: absolute; inset: 0; background-image: linear-gradient(rgba(72, 120, 111, .045) 1px, transparent 1px), linear-gradient(90deg, rgba(72, 120, 111, .045) 1px, transparent 1px); background-size: 24px 24px; }
.blank-map { min-height: 640px; display: flex; flex-direction: column; align-items: center; justify-content: center; background: radial-gradient(circle at center, #f3f8f6, #fff 48%); text-align: center; }.map-symbol { width: 110px; height: 90px; position: relative; display: grid; place-items: center; color: #3a857a; font-size: 28px; }.map-symbol span { position: absolute; width: 25px; height: 25px; border: 1px solid #9dbdb6; border-radius: 7px; }.map-symbol span:nth-child(1) { left: 0; top: 5px; }.map-symbol span:nth-child(2) { right: 0; top: 5px; }.map-symbol span:nth-child(3) { left: 42px; bottom: 0; }.blank-map h2 { margin: 17px 0 7px; color: #4a625c; font-family: 'Noto Serif SC', 'Songti SC', SimSun, serif; font-size: 17px; }.blank-map p { max-width: 430px; margin: 0 0 17px; color: #8b9895; font-size: 10px; line-height: 1.6; }
.json-editor { margin: 14px 0 10px; }.json-editor :deep(textarea) { font-family: Consolas, 'Courier New', monospace; font-size: 11px; line-height: 1.55; }
@media (max-width: 900px) { .map-shell { grid-template-columns: 190px 1fr; }.tree-viewport { padding: 28px; } }
@media (max-width: 700px) { .map-shell { grid-template-columns: 1fr; }.map-list { display: none; }.canvas-header dl { display: none; } }
</style>
