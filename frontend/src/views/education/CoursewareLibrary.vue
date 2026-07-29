<template>
  <EducationShell
    title="PPT 与课件"
    :subtitle="course ? `${course.title} · 从教案与课程资料制作可编辑课件` : '选择一门教师课程开始'"
  >
    <template #actions>
      <input
        v-if="canManageCourseware"
        ref="coursewareFile"
        data-testid="courseware-upload"
        class="visually-hidden"
        type="file"
        accept=".pdf,.doc,.docx,.ppt,.pptx,.html,.htm"
        @change="uploadSelectedFile"
      >
      <el-button v-if="canManageCourseware" icon="el-icon-upload2" :loading="uploading" @click="$refs.coursewareFile.click()">
        上传课件
      </el-button>
      <el-button
        v-if="canManageCourseware"
        type="primary"
        icon="el-icon-magic-stick"
        :disabled="!lessons.length"
        :loading="agentRunning"
        @click="openAgentDialog"
      >AI 生成课件</el-button>
    </template>

    <el-alert
      v-if="roleError"
      title="当前没有可用的教师课程"
      description="课程身份来自服务端成员关系。请先创建一门课程，或在左侧选择教师身份的课程。"
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

      <section class="courseware-hero">
        <div>
          <span class="hero-kicker">COURSEWARE STUDIO</span>
          <h2>教案是蓝图，课件是学生真正看到的表达</h2>
          <p>HTML 可由 Agent 生成并继续编辑；PPTX、PDF、Word 作为持久课程资产上传、下载与发布。文件保存在 Education 数据库中，不依赖临时沙箱。</p>
        </div>
        <div class="hero-stats">
          <div><b>{{ lessons.length }}</b><span>课时</span></div>
          <div><b>{{ assets.length }}</b><span>文件</span></div>
          <div><b>{{ publishedAssets }}</b><span>已分享</span></div>
        </div>
      </section>

      <section class="studio-grid">
        <div class="studio-panel">
          <header>
            <div>
              <span class="panel-index">01</span>
              <h3>从课时继续制作</h3>
            </div>
            <small>教案、可视化 HTML、学习活动和 Agent 产物在同一课时版本中协作。</small>
          </header>
          <div class="lesson-context-picker">
            <label for="courseware-lesson-selector">当前课时</label>
            <el-select
              id="courseware-lesson-selector"
              v-model="selectedLessonId"
              data-testid="courseware-lesson-selector"
              placeholder="选择课时以读取上下文"
              @change="loadSelectedContext"
            >
              <el-option
                v-for="lesson in lessons"
                :key="lesson.id"
                :label="lesson.title"
                :value="lesson.id"
              />
            </el-select>
          </div>
          <div
            v-if="coursewareContext"
            v-loading="contextLoading"
            class="context-sheet"
            data-testid="courseware-context"
          >
            <div class="context-heading">
              <span>课时上下文</span>
              <small>校验码 {{ shortChecksum(coursewareContext.context_checksum) }}</small>
            </div>
            <h4>{{ coursewareContext.lesson.title }}</h4>
            <div class="context-metrics">
              <div><b>{{ contextObjectives.length }}</b><span>教学目标</span></div>
              <div><b>{{ coursewareContext.activities.length }}</b><span>学习活动</span></div>
              <div><b>{{ coursewareContext.materials.length }}</b><span>课时材料</span></div>
              <div><b>{{ coursewareContext.knowledge_resources.length }}</b><span>知识来源</span></div>
            </div>
            <ul v-if="contextObjectives.length">
              <li
                v-for="objective in contextObjectives.slice(0, 3)"
                :key="objective.id || objective.description || objective"
              >{{ objective.description || objective.text || objective }}</li>
            </ul>
          </div>
          <div v-if="lessons.length" class="lesson-stack">
            <article
              v-for="lesson in lessons"
              :key="lesson.id"
              :class="{ active: lesson.id === selectedLessonId }"
            >
              <div class="lesson-number">{{ lesson.position + 1 || '—' }}</div>
              <div>
                <b>{{ lesson.title }}</b>
                <span>{{ lesson.status === 'published' ? '已发布' : '草稿' }} · {{ lessonType(lesson) }}</span>
              </div>
              <div class="lesson-actions">
                <el-button size="mini" type="text" @click="selectLesson(lesson)">读取</el-button>
                <el-button size="mini" @click="openLesson(lesson)">编辑</el-button>
              </div>
            </article>
          </div>
          <div v-else class="empty-paper">
            <i class="el-icon-notebook-2"></i>
            <p>这门课程还没有课时。先回到教学空间建立课时与教案。</p>
            <el-button size="small" @click="openTeachingSpace">进入教学空间</el-button>
          </div>
        </div>

        <div class="studio-panel asset-panel">
          <header>
            <div>
              <span class="panel-index">02</span>
              <h3>课件文件柜</h3>
            </div>
            <small>教师私有文件可在确认后发布给课程学生。</small>
          </header>
          <div v-loading="loadingAssets" class="asset-list">
            <article v-for="asset in assets" :key="asset.id">
              <span class="file-icon">{{ extension(asset.original_filename) }}</span>
              <div class="file-main">
                <b>{{ asset.title }}</b>
                <span>{{ sizeLabel(asset.byte_size) }} · {{ dateLabel(asset.updated_at || asset.created_at) }}</span>
              </div>
              <el-tag
                size="mini"
                :type="asset.visibility_scope === 'course_published' ? 'success' : 'info'"
              >
                {{ asset.visibility_scope === 'course_published' ? '学生可见' : '教师可见' }}
              </el-tag>
              <el-dropdown trigger="click" @command="handleAssetCommand($event, asset)">
                <el-button size="mini" icon="el-icon-more"></el-button>
                <el-dropdown-menu #dropdown>
                  <el-dropdown-item command="download" icon="el-icon-download">下载</el-dropdown-item>
                  <el-dropdown-item
                    v-if="asset.visibility_scope !== 'course_published'"
                    command="publish"
                    icon="el-icon-position"
                  >发布给学生</el-dropdown-item>
                </el-dropdown-menu>
              </el-dropdown>
            </article>
            <div v-if="!loadingAssets && !assets.length" class="empty-paper compact">
              <i class="el-icon-folder-opened"></i>
              <p>还没有课件文件。上传 PPTX、PDF、Word 或 HTML。</p>
            </div>
          </div>
        </div>

        <div class="studio-panel generated-panel">
          <header>
            <div>
              <span class="panel-index">03</span>
              <h3>结构化课件版本</h3>
            </div>
            <small>结构化源是可编辑主版本；PPTX、DOCX、PDF、HTML 与 JSON 均从当前版本即时导出。</small>
          </header>
          <div v-loading="loadingGenerated" class="generated-list">
            <article v-for="entry in generatedContents" :key="entry.content.id">
              <div class="generated-symbol">
                <i :class="entry.content.kind === 'slide_document' ? 'el-icon-data-board' : 'el-icon-document'"></i>
              </div>
              <div class="generated-main">
                <b>{{ entry.lesson.title }}</b>
                <span>
                  {{ contentKindLabel(entry.content.kind) }} ·
                  v{{ entry.version.version_number }} ·
                  {{ dateLabel(entry.version.created_at) }}
                </span>
                <small>{{ entry.version.change_summary || 'Agent 生成的可编辑草稿' }}</small>
              </div>
              <div class="format-actions">
                <el-button
                  v-for="format in exportFormats"
                  :key="format"
                  size="mini"
                  :loading="exportingKey === `${entry.content.id}:${format}`"
                  @click="downloadGenerated(entry, format)"
                >{{ format.toUpperCase() }}</el-button>
              </div>
              <el-button size="mini" type="text" @click="openGeneratedEditor(entry)">打开编辑</el-button>
            </article>
            <div v-if="!loadingGenerated && !generatedContents.length" class="empty-paper compact">
              <i class="el-icon-cpu"></i>
              <p>还没有结构化课件版本。选择课时后可手动编写，或使用 AI 生成可编辑草稿。</p>
            </div>
          </div>
        </div>
      </section>
    </template>

    <el-dialog title="用 Agent 制作课件" :visible.sync="agentDialog" width="620px">
      <el-alert
        title="课程设计、课件制作和教学审校 Agent 会协作生成可编辑课件草稿；不会自动发布给学生。"
        type="info"
        :closable="false"
        show-icon
      />
      <el-form label-position="top" class="agent-form">
        <el-form-item label="基于课时">
          <el-select v-model="agentForm.lesson_id" style="width:100%" placeholder="选择课时">
            <el-option
              v-for="lesson in lessons"
              :key="lesson.id"
              :label="lesson.title"
              :value="lesson.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="课件侧重点">
          <el-input
            v-model.trim="agentForm.requirements"
            type="textarea"
            :rows="5"
            maxlength="2000"
            show-word-limit
            placeholder="例如：突出故事弧、证据提取和读后续写，控制在 12 页以内"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="agentDialog = false">取消</el-button>
        <el-button
          type="primary"
          :loading="agentRunning"
          :disabled="!agentForm.lesson_id"
          @click="startCoursewareAgent"
        >启动 Agent 团队</el-button>
      </template>
    </el-dialog>

    <el-dialog
      title="结构化幻灯片编辑器"
      :visible.sync="editorDialog"
      width="94%"
      top="3vh"
      custom-class="slide-editor-dialog"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <SlideDocumentEditor
        v-if="editingEntry"
        ref="slideEditor"
        :value="editingEntry.version.source_json"
      />
      <template #footer>
        <span class="editor-footnote">保存后生成同一课件的新版本；PPTX、PDF、HTML 会从最新结构重新导出。</span>
        <el-button @click="editorDialog = false">取消</el-button>
        <el-button type="primary" :loading="editorSaving" @click="saveGeneratedEditor">
          保存为新版本
        </el-button>
      </template>
    </el-dialog>
  </EducationShell>
</template>

<script>
import {
  downloadCourseAsset,
  exportEducationContent,
  getContentVersions,
  getLessonContents,
  saveContentVersion,
} from '../../api/education'
import EducationShell from '../../components/education/EducationShell.vue'
import EmbeddedAgentRecord from '../../components/education/EmbeddedAgentRecord.vue'
import SlideDocumentEditor from '../../components/education/SlideDocumentEditor.vue'
const { formatVersionTime } = require('../../utils/educationContent')
const { renderSlideDocumentHtml } = require('../../utils/slideDocument')

export default {
  name: 'CoursewareLibrary',
  components: { EducationShell, EmbeddedAgentRecord, SlideDocumentEditor },
  data() {
    return {
      roleError: false,
      uploading: false,
      loadingAssets: false,
      agentDialog: false,
      editorDialog: false,
      editorSaving: false,
      editingEntry: null,
      loadingGenerated: false,
      contextLoading: false,
      selectedLessonId: '',
      exportingKey: '',
      generatedContents: [],
      exportFormats: ['pptx', 'docx', 'pdf', 'html', 'json'],
      agentForm: {
        lesson_id: '',
        requirements: '',
      },
    }
  },
  computed: {
    course() { return this.$store.getters['education/activeCourse'] },
    canManageCourseware() {
      return Boolean(this.course && this.course.membership_role === 'teacher' && !this.roleError)
    },
    assets() {
      return (this.$store.getters['education/assets'] || [])
        .filter(asset => ['courseware', 'lesson_material', 'course_material', 'agent_output'].includes(asset.purpose))
    },
    units() { return this.$store.getters['education/units'] || [] },
    coursewareContext() { return this.$store.getters['education/coursewareContext'] },
    contextObjectives() {
      const plan = this.coursewareContext && this.coursewareContext.lesson_plan
      return (plan && plan.source_json && plan.source_json.objectives) || []
    },
    lessons() {
      return this.units.flatMap(unit => unit.lessons || [])
    },
    publishedAssets() {
      return this.assets.filter(asset => asset.visibility_scope === 'course_published').length
    },
    productAgentRun() { return this.$store.getters['education/productAgentRun'] },
    agentRunning() {
      return Boolean(this.productAgentRun && ['pending', 'running'].includes(this.productAgentRun.status))
    },
  },
  watch: {
    'course.id'(next, previous) {
      if (next && next !== previous) this.loadCourse(next)
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
          role: 'teacher',
        })
        await this.loadCourse(course.id)
      } catch (error) {
        this.roleError = true
      }
    },
    async loadCourse(courseId) {
      if (!courseId || this.course.membership_role !== 'teacher') {
        this.roleError = true
        return
      }
      this.roleError = false
      this.loadingAssets = true
      try {
        await Promise.all([
          this.$store.dispatch('education/fetchCourseOverview', courseId),
          this.$store.dispatch('education/fetchAssets', courseId),
        ])
        await this.$store.dispatch('education/restoreProductAgentRun', {
          courseId,
          productCode: 'courseware',
        })
        await this.loadGeneratedContents()
        if (!this.agentForm.lesson_id && this.lessons[0]) {
          this.agentForm.lesson_id = this.lessons[0].id
        }
        if (!this.selectedLessonId && this.lessons[0]) {
          this.selectedLessonId = this.lessons[0].id
        }
        if (this.selectedLessonId) await this.loadSelectedContext(this.selectedLessonId)
      } catch (error) {
        this.$message.error('课件资料加载失败')
      } finally {
        this.loadingAssets = false
      }
    },
    async uploadSelectedFile(event) {
      const file = event.target.files && event.target.files[0]
      event.target.value = ''
      if (!file || !this.course) return
      this.uploading = true
      try {
        await this.$store.dispatch('education/uploadAsset', {
          courseId: this.course.id,
          file,
          title: file.name,
          purpose: 'courseware',
          visibilityScope: 'course_teacher',
        })
        this.$message.success('课件已保存到课程文件柜')
      } catch (error) {
        this.$message.error('上传失败，请检查文件类型和大小')
      } finally {
        this.uploading = false
      }
    },
    async downloadAsset(asset) {
      const blob = await downloadCourseAsset(asset.id)
      const objectUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = objectUrl
      link.download = asset.original_filename
      link.click()
      URL.revokeObjectURL(objectUrl)
    },
    async handleAssetCommand(command, asset) {
      if (command === 'download') {
        try {
          await this.downloadAsset(asset)
        } catch (error) {
          this.$message.error('文件下载失败')
        }
      }
      if (command === 'publish') {
        try {
          await this.$store.dispatch('education/publishAsset', {
            courseId: this.course.id,
            assetId: asset.id,
          })
          this.$message.success('该课件已对课程学生可见')
        } catch (error) {
          this.$message.error('发布失败')
        }
      }
    },
    openAgentDialog() {
      this.agentForm.lesson_id = this.selectedLessonId
        || (this.lessons[0] && this.lessons[0].id)
      this.agentDialog = true
    },
    async loadSelectedContext(lessonId) {
      if (!lessonId) return
      this.selectedLessonId = lessonId
      this.agentForm.lesson_id = lessonId
      this.contextLoading = true
      try {
        await this.$store.dispatch('education/fetchCoursewareContext', lessonId)
      } catch (error) {
        this.$message.error('课时上下文加载失败')
      } finally {
        this.contextLoading = false
      }
    },
    selectLesson(lesson) {
      this.loadSelectedContext(lesson.id)
    },
    async startCoursewareAgent() {
      try {
        await this.$store.dispatch('education/startProductAgentRun', {
          course_id: this.course.id,
          lesson_id: this.agentForm.lesson_id,
          product_code: 'courseware',
          options: {
            requirements: this.agentForm.requirements,
          },
        })
        this.agentDialog = false
        this.$message.success('课件 Agent 团队已启动')
      } catch (error) {
        const detail = error.response && error.response.data && error.response.data.error
        this.$message.error(detail || '课件 Agent 启动失败')
      }
    },
    async handleAgentTerminal(run) {
      if (run.status === 'completed') {
        await Promise.all([
          this.$store.dispatch('education/fetchAssets', this.course.id),
          this.$store.dispatch('education/fetchCourseOverview', this.course.id),
        ])
        await this.loadGeneratedContents()
        await this.loadSelectedContext(this.selectedLessonId)
        this.$message.success('Agent 课件草稿已写入课时，可继续编辑后发布')
      }
    },
    closeAgentRun() {
      this.$store.commit('education/SET_PRODUCT_AGENT_RUN', null)
    },
    async loadGeneratedContents() {
      this.loadingGenerated = true
      try {
        const rows = []
        await Promise.all(this.lessons.map(async lesson => {
          const response = await getLessonContents(lesson.id)
          const payload = response && response.data !== undefined && response.code !== undefined
            ? response.data
            : response
          const contents = Array.isArray(payload) ? payload : (payload && payload.items) || []
          await Promise.all(contents
            .filter(content => ['slide_document', 'rich_document'].includes(content.kind))
            .map(async content => {
              const versionResponse = await getContentVersions(content.id)
              const versionPayload = versionResponse
                && versionResponse.data !== undefined
                && versionResponse.code !== undefined
                ? versionResponse.data
                : versionResponse
              const versions = Array.isArray(versionPayload)
                ? versionPayload
                : (versionPayload && versionPayload.items) || []
              const version = versions[versions.length - 1]
              if (version) rows.push({ lesson, content, version })
            }))
        }))
        this.generatedContents = rows.sort((left, right) => {
          return new Date(right.version.created_at || 0) - new Date(left.version.created_at || 0)
        })
      } catch (error) {
        this.generatedContents = []
        this.$message.warning('Agent 课件版本暂时无法加载')
      } finally {
        this.loadingGenerated = false
      }
    },
    async downloadGenerated(entry, format) {
      this.exportingKey = `${entry.content.id}:${format}`
      try {
        const blob = await exportEducationContent(entry.content.id, format)
        const objectUrl = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = objectUrl
        link.download = `${entry.lesson.title}-v${entry.version.version_number}.${format}`
        link.click()
        URL.revokeObjectURL(objectUrl)
      } catch (error) {
        this.$message.error(`${format.toUpperCase()} 导出失败，请尝试 JSON 或 HTML`)
      } finally {
        this.exportingKey = ''
      }
    },
    openGeneratedEditor(entry) {
      if (!entry || entry.content.kind !== 'slide_document') {
        this.openLesson(entry.lesson)
        return
      }
      this.editingEntry = entry
      this.editorDialog = true
    },
    async saveGeneratedEditor() {
      const editor = this.$refs.slideEditor
      if (!editor || !this.editingEntry) return
      const source = editor.exportDocument()
      if (!source.title || !Array.isArray(source.slides) || !source.slides.length) {
        this.$message.warning('课件至少需要一个标题和一页幻灯片')
        return
      }
      this.editorSaving = true
      try {
        await saveContentVersion(this.editingEntry.content.id, {
          schema_name: 'weagent.education.slide-document',
          schema_version: '1.0',
          source_json: source,
          rendered_html: renderSlideDocumentHtml(source),
          change_summary: '教师在结构化幻灯片编辑器中修改',
        })
        this.editorDialog = false
        this.editingEntry = null
        await this.loadGeneratedContents()
        await this.loadSelectedContext(this.selectedLessonId)
        this.$message.success('课件新版本已保存，可按需导出或发布')
      } catch (error) {
        const detail = error.response && error.response.data && error.response.data.error
        this.$message.error(detail || '课件版本保存失败')
      } finally {
        this.editorSaving = false
      }
    },
    openLesson(lesson) {
      this.$router.push(`/education/courses/${this.course.id}/lessons/${lesson.id}`)
    },
    openTeachingSpace() {
      this.$router.push(`/education/courses/${this.course.id}`)
    },
    lessonType(lesson) {
      const labels = {
        reading: '阅读',
        writing: '写作',
        reading_writing: '阅读与写作',
        integrated: '综合',
      }
      return labels[lesson.lesson_type_code] || '阅读与写作'
    },
    contentKindLabel(kind) {
      return kind === 'slide_document' ? '可编辑幻灯片' : '可视化学习材料'
    },
    extension(name) {
      const value = String(name || '').split('.').pop()
      return value ? value.slice(0, 5).toUpperCase() : 'FILE'
    },
    sizeLabel(bytes) {
      if (bytes < 1024) return `${bytes} B`
      if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
      return `${(bytes / 1024 / 1024).toFixed(1)} MB`
    },
    dateLabel(value) {
      return formatVersionTime(value) || '刚刚'
    },
    shortChecksum(value) {
      return value ? value.slice(0, 8) : '—'
    },
  },
}
</script>

<style scoped>
.visually-hidden { position: absolute; width: 1px; height: 1px; opacity: 0; pointer-events: none; }
.editor-footnote { float: left; max-width: 62%; color: #738682; font-size: 12px; line-height: 32px; text-align: left; }
.slide-editor-dialog ::v-deep .el-dialog__body { padding: 12px 20px 4px; }
.agent-form { margin-top: 16px; }
.courseware-hero {
  min-height: 160px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 36px;
  margin-bottom: 18px;
  padding: 26px 30px;
  overflow: hidden;
  border: 1px solid #d5e6e1;
  border-radius: 16px;
  background:
    linear-gradient(105deg, rgba(246, 251, 249, 0.96), rgba(231, 244, 239, 0.9)),
    repeating-linear-gradient(90deg, transparent 0 34px, rgba(42, 117, 105, 0.04) 35px);
  position: relative;
}
.courseware-hero::after {
  content: '';
  position: absolute;
  width: 180px; height: 180px; right: -35px; top: -75px;
  border: 30px solid rgba(43, 132, 119, 0.08);
  border-radius: 50%;
}
.hero-kicker { color: #287f75; font-size: 10px; font-weight: 800; letter-spacing: .16em; }
.courseware-hero h2 {
  margin: 8px 0 8px;
  color: #233735;
  font-family: 'Noto Serif SC', 'Songti SC', SimSun, serif;
  font-size: 22px;
}
.courseware-hero p { max-width: 720px; margin: 0; color: #687b78; font-size: 12px; line-height: 1.75; }
.hero-stats { display: flex; gap: 11px; position: relative; z-index: 1; }
.hero-stats div {
  width: 74px; height: 76px; display: grid; place-content: center;
  border: 1px solid rgba(66, 130, 119, .14); border-radius: 13px;
  background: rgba(255,255,255,.78); text-align: center;
}
.hero-stats b { color: #236f67; font-family: Georgia, serif; font-size: 24px; }
.hero-stats span { color: #83928f; font-size: 10px; }
.studio-grid { display: grid; grid-template-columns: minmax(360px, .9fr) minmax(430px, 1.1fr); gap: 16px; }
.studio-panel {
  min-height: 360px; padding: 20px; border: 1px solid #e1e9e7;
  border-radius: 14px; background: #fff;
}
.generated-panel { grid-column: 1 / -1; min-height: 280px; }
.generated-list { display: grid; gap: 9px; }
.generated-list article {
  display: grid; grid-template-columns: 42px minmax(180px, 1fr) auto auto;
  align-items: center; gap: 11px; padding: 12px;
  border: 1px solid #e2ebe8; border-radius: 10px; background: #fbfdfc;
}
.generated-symbol {
  width: 40px; height: 40px; display: grid; place-items: center;
  border-radius: 10px; background: #e5f2ee; color: #2f7e73; font-size: 17px;
}
.generated-main b, .generated-main span, .generated-main small { display: block; }
.generated-main b { color: #304540; font-size: 12px; }
.generated-main span { margin-top: 3px; color: #7e8e89; font-size: 9px; }
.generated-main small { margin-top: 4px; color: #9aa5a2; font-size: 8px; }
.format-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 4px; }
.format-actions .el-button { margin: 0; min-width: 48px; }
.studio-panel > header { margin-bottom: 16px; border-bottom: 1px solid #edf1f0; padding-bottom: 14px; }
.studio-panel > header > div { display: flex; align-items: center; gap: 8px; }
.studio-panel h3 { margin: 0; color: #2c3d3a; font-size: 16px; }
.studio-panel header small { display: block; margin-top: 7px; color: #8a9996; line-height: 1.5; }
.panel-index { color: #36897e; font-family: Georgia, serif; font-size: 11px; }
.lesson-context-picker { display: grid; gap: 6px; margin-bottom: 11px; }
.lesson-context-picker label { color: #788985; font-size: 9px; font-weight: 700; }
.context-sheet {
  margin-bottom: 13px; padding: 14px; border: 1px solid #d9e8e4;
  border-radius: 11px; background: linear-gradient(140deg, #fbfdfc, #f0f7f5);
  animation: context-enter 260ms cubic-bezier(.2,.8,.2,1) both;
}
.context-heading { display: flex; justify-content: space-between; color: #3a8076; font-size: 9px; font-weight: 750; letter-spacing: .08em; }
.context-heading small { color: #96a5a1; font-family: Consolas, monospace; font-weight: 400; letter-spacing: 0; }
.context-sheet h4 { margin: 8px 0 10px; color: #30433f; font-family: 'Noto Serif SC', 'Songti SC', SimSun, serif; font-size: 15px; }
.context-metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
.context-metrics div { padding: 7px; border-radius: 8px; background: rgba(255,255,255,.78); text-align: center; }
.context-metrics b, .context-metrics span { display: block; }
.context-metrics b { color: #2e7168; font-family: Georgia, serif; font-size: 16px; }.context-metrics span { margin-top: 2px; color: #8a9996; font-size: 8px; }
.context-sheet ul { margin: 10px 0 0; padding-left: 18px; color: #657a75; font-size: 9px; line-height: 1.7; }
@keyframes context-enter { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
.lesson-stack, .asset-list { display: flex; flex-direction: column; gap: 9px; }
.lesson-stack article, .asset-list article {
  display: grid; align-items: center; gap: 11px; padding: 12px;
  border: 1px solid #e6edeb; border-radius: 10px; background: #fbfdfc;
}
.lesson-stack article { grid-template-columns: 34px 1fr auto; }
.lesson-stack article.active { border-color: #9cc9c0; background: #f4faf8; box-shadow: inset 3px 0 #2e887c; }
.lesson-actions { display: flex; align-items: center; }
.lesson-number {
  width: 32px; height: 32px; display: grid; place-items: center; border-radius: 8px;
  background: #e8f2ef; color: #357d73; font-family: Georgia, serif;
}
.lesson-stack b, .lesson-stack span, .file-main b, .file-main span { display: block; }
.lesson-stack b, .file-main b { color: #344541; font-size: 12px; }
.lesson-stack span, .file-main span { margin-top: 4px; color: #92a09d; font-size: 10px; }
.asset-list article { grid-template-columns: 43px 1fr auto auto; }
.file-icon {
  width: 41px; height: 41px; display: grid; place-items: center; border-radius: 10px;
  background: #eff4f1; color: #547770; font-family: Georgia, serif; font-size: 9px; font-weight: 700;
}
.empty-paper {
  min-height: 220px; display: flex; flex-direction: column; align-items: center;
  justify-content: center; border: 1px dashed #d4dfdc; border-radius: 12px;
  background: #fafcfb; color: #91a09c; text-align: center;
}
.empty-paper i { font-size: 28px; color: #7ca097; }
.empty-paper p { max-width: 330px; margin: 10px 0 14px; font-size: 12px; line-height: 1.6; }
.empty-paper.compact { min-height: 210px; }
@media (max-width: 1100px) {
  .studio-grid { grid-template-columns: 1fr; }
}
@media (max-width: 760px) {
  .courseware-hero { grid-template-columns: 1fr; padding: 20px; }
  .hero-stats { display: none; }
  .asset-list article { grid-template-columns: 40px 1fr auto; }
  .asset-list article .el-tag { display: none; }
  .generated-list article { grid-template-columns: 38px 1fr auto; }
  .format-actions { grid-column: 2 / -1; justify-content: flex-start; }
}
@media (prefers-reduced-motion: reduce) {
  .context-sheet { animation: none; }
  .lesson-stack article { transition: none; }
}
</style>
