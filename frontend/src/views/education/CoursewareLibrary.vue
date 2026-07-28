<template>
  <EducationShell
    title="PPT 与课件"
    :subtitle="course ? `${course.title} · 从教案与课程资料制作可编辑课件` : '选择一门教师课程开始'"
  >
    <template #actions>
      <input
        ref="coursewareFile"
        data-testid="courseware-upload"
        class="visually-hidden"
        type="file"
        accept=".pdf,.doc,.docx,.ppt,.pptx,.html,.htm"
        @change="uploadSelectedFile"
      >
      <el-button icon="el-icon-upload2" :loading="uploading" @click="$refs.coursewareFile.click()">
        上传课件
      </el-button>
      <el-button
        type="primary"
        icon="el-icon-magic-stick"
        :disabled="!lessons.length"
        :loading="agentRunning"
        @click="openAgentDialog"
      >用 Agent 制作</el-button>
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
      <ProductAgentRunPanel
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
          <div v-if="lessons.length" class="lesson-stack">
            <article v-for="lesson in lessons" :key="lesson.id">
              <div class="lesson-number">{{ lesson.position + 1 || '—' }}</div>
              <div>
                <b>{{ lesson.title }}</b>
                <span>{{ lesson.status === 'published' ? '已发布' : '草稿' }} · {{ lessonType(lesson) }}</span>
              </div>
              <el-button size="mini" @click="openLesson(lesson)">编辑课件</el-button>
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
  </EducationShell>
</template>

<script>
import { downloadCourseAsset } from '../../api/education'
import EducationShell from '../../components/education/EducationShell.vue'
import ProductAgentRunPanel from '../../components/education/ProductAgentRunPanel.vue'

export default {
  name: 'CoursewareLibrary',
  components: { EducationShell, ProductAgentRunPanel },
  data() {
    return {
      roleError: false,
      uploading: false,
      loadingAssets: false,
      agentDialog: false,
      agentForm: {
        lesson_id: '',
        requirements: '',
      },
    }
  },
  computed: {
    course() { return this.$store.getters['education/activeCourse'] },
    assets() {
      return (this.$store.getters['education/assets'] || [])
        .filter(asset => ['courseware', 'lesson_material', 'course_material', 'agent_output'].includes(asset.purpose))
    },
    units() { return this.$store.getters['education/units'] || [] },
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
        if (!this.agentForm.lesson_id && this.lessons[0]) {
          this.agentForm.lesson_id = this.lessons[0].id
        }
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
      if (!this.agentForm.lesson_id && this.lessons[0]) {
        this.agentForm.lesson_id = this.lessons[0].id
      }
      this.agentDialog = true
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
        this.$message.success('Agent 课件草稿已写入课时，可继续编辑后发布')
      }
    },
    closeAgentRun() {
      this.$store.commit('education/SET_PRODUCT_AGENT_RUN', null)
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
      return value ? new Date(value).toLocaleString('zh-CN') : '刚刚'
    },
  },
}
</script>

<style scoped>
.visually-hidden { position: absolute; width: 1px; height: 1px; opacity: 0; pointer-events: none; }
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
.studio-panel > header { margin-bottom: 16px; border-bottom: 1px solid #edf1f0; padding-bottom: 14px; }
.studio-panel > header > div { display: flex; align-items: center; gap: 8px; }
.studio-panel h3 { margin: 0; color: #2c3d3a; font-size: 16px; }
.studio-panel header small { display: block; margin-top: 7px; color: #8a9996; line-height: 1.5; }
.panel-index { color: #36897e; font-family: Georgia, serif; font-size: 11px; }
.lesson-stack, .asset-list { display: flex; flex-direction: column; gap: 9px; }
.lesson-stack article, .asset-list article {
  display: grid; align-items: center; gap: 11px; padding: 12px;
  border: 1px solid #e6edeb; border-radius: 10px; background: #fbfdfc;
}
.lesson-stack article { grid-template-columns: 34px 1fr auto; }
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
}
</style>
