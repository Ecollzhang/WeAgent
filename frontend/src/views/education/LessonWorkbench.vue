<template>
  <EducationShell
    :title="lesson ? lesson.title : '课时工作台'"
    :subtitle="isTeacher ? '结构化教案、学习材料与发布版本' : '已发布的学习材料与任务'"
    :back-to="`/education/courses/${courseId}`"
  >
    <template #actions>
      <el-tag v-if="lesson" :type="lesson.status === 'published' ? 'success' : 'info'">
        {{ lesson.status === 'published' ? '已发布' : '草稿' }}
      </el-tag>
      <el-button
        v-if="isTeacher"
        data-testid="save-lesson-version"
        :loading="saving"
        @click="saveVersion"
      >保存新版本</el-button>
      <el-button
        v-if="isTeacher"
        data-testid="publish-lesson"
        type="primary"
        :disabled="!savedVersionId"
        @click="publishVersion"
      >发布给学生</el-button>
    </template>

    <el-skeleton v-if="!lesson" :rows="9" animated />
    <div v-else class="workbench">
      <aside class="workbench-nav">
        <button
          v-for="item in sections"
          :key="item.key"
          type="button"
          :class="{ active: section === item.key }"
          @click="section = item.key"
        >
          <i :class="item.icon"></i>
          <span>{{ item.label }}</span>
        </button>
        <div class="version-note">
          <span>当前版本</span>
          <b>{{ currentVersionLabel }}</b>
          <small>发布后学生看到固定快照，后续编辑不会覆盖。</small>
        </div>
      </aside>

      <section class="workbench-content">
        <div v-if="section === 'plan'">
          <div class="content-heading">
            <div><h2>教案</h2><p>根据课型调整教学重点，目标、活动和评价保持一致。</p></div>
          </div>
          <LessonPlanEditor
            v-if="isTeacher"
            v-model="lessonPlan"
            :subject-code="course.subject_code"
            data-testid="lesson-plan-editor"
          />
          <div v-else class="student-plan">
            <h3>本课学习目标</h3>
            <p>{{ lessonPlan.objectives || '教师尚未公开学习目标。' }}</p>
            <h3>学习活动</h3>
            <p>{{ lessonPlan.activities || '请按教师发布的材料完成本课学习。' }}</p>
          </div>
        </div>

        <div v-if="section === 'material'">
          <div class="content-heading">
            <div><h2>可编辑学习材料</h2><p>HTML 是演示产物，结构化内容是后续编辑的真源。</p></div>
            <el-radio-group v-model="materialMode" size="small">
              <el-radio-button label="edit" :disabled="!isTeacher">编辑</el-radio-button>
              <el-radio-button label="preview">安全预览</el-radio-button>
            </el-radio-group>
          </div>
          <el-input
            v-if="materialMode === 'edit' && isTeacher"
            v-model="materialHtml"
            data-testid="lesson-material-editor"
            type="textarea"
            :rows="22"
            placeholder="输入教学材料 HTML"
          />
          <SafeHtmlPreview v-else :html="materialHtml" data-testid="lesson-material-preview" />
        </div>

        <div v-if="section === 'activity'">
          <div class="content-heading">
            <div><h2>课内活动</h2><p>阅读、写作、练习与评价活动按发布顺序展示。</p></div>
          </div>
          <div v-if="activities.length" class="activity-list">
            <article v-for="(activity, index) in activities" :key="activity.id || index">
              <span>{{ index + 1 }}</span>
              <div><b>{{ activity.title || activity.activity_type }}</b><p>{{ activity.instructions || activity.description }}</p></div>
              <el-tag size="mini">{{ activity.activity_type || '学习活动' }}</el-tag>
            </article>
          </div>
          <div v-else class="empty-block">本课暂无独立活动。</div>
        </div>
      </section>
    </div>
  </EducationShell>
</template>

<script>
import EducationShell from '../../components/education/EducationShell.vue'
import LessonPlanEditor from '../../components/education/LessonPlanEditor.vue'
import SafeHtmlPreview from '../../components/education/SafeHtmlPreview.vue'

export default {
  name: 'EducationLessonWorkbench',
  components: { EducationShell, LessonPlanEditor, SafeHtmlPreview },
  data() {
    return {
      section: 'plan',
      materialMode: 'preview',
      lessonPlan: {
        lesson_type_code: '',
        duration_minutes: 45,
        objectives: '',
        activities: '',
        assessment: '',
      },
      materialHtml: '',
      savedVersionId: '',
      sections: [
        { key: 'plan', label: '教案', icon: 'el-icon-document' },
        { key: 'material', label: '课件与材料', icon: 'el-icon-data-board' },
        { key: 'activity', label: '学习活动', icon: 'el-icon-s-operation' },
      ],
    }
  },
  computed: {
    courseId() { return this.$route.params.courseId },
    lessonId() { return this.$route.params.lessonId },
    course() { return this.$store.getters['education/activeCourse'] || {} },
    lesson() { return this.$store.state.education.activeLesson },
    isTeacher() { return this.$store.getters['education/isTeacher'] },
    saving() { return this.$store.getters['education/saving'] },
    activities() { return (this.lesson && this.lesson.activities) || [] },
    currentVersionLabel() {
      const version = this.lesson && (this.lesson.current_version || this.lesson.published_version)
      return version && (version.version_number || version.version) ? `v${version.version_number || version.version}` : '尚未保存'
    },
  },
  async created() {
    try {
      if (!this.course.id) {
        await this.$store.dispatch('education/selectCourse', this.courseId)
      }
      if (!this.$store.getters['education/units'].length) {
        await this.$store.dispatch('education/fetchCourseOverview', this.courseId)
      }
      const lesson = await this.$store.dispatch('education/fetchLesson', this.lessonId)
      const version = lesson.current_version || lesson.published_version || lesson.publication || {}
      const content = version.content || version.content_json || lesson.content || {}
      this.lessonPlan = {
        ...this.lessonPlan,
        ...(content.lesson_plan || lesson.lesson_plan || {}),
        lesson_type_code: lesson.lesson_type_code || (content.lesson_plan || {}).lesson_type_code || '',
      }
      this.materialHtml = content.html || content.material_html || lesson.material_html || ''
      this.savedVersionId = version.id || ''
      this.materialMode = this.isTeacher ? 'edit' : 'preview'
    } catch (error) {
      this.$message.error('课时加载失败或你无权访问')
      this.$router.replace(`/education/courses/${this.courseId}`)
    }
  },
  methods: {
    async saveVersion() {
      try {
        const version = await this.$store.dispatch('education/saveLesson', {
          lessonId: this.lessonId,
          version: {
            lesson_plan_json: this.lessonPlan,
            content: {
              lesson_plan: this.lessonPlan,
              html: this.materialHtml,
            },
          },
        })
        this.savedVersionId = version.version ? version.version.id : version.id
        this.$message.success('新版本已保存')
      } catch (error) {
        this.$message.error('版本保存失败')
      }
    },
    async publishVersion() {
      try {
        await this.$confirm('发布后学生将看到该固定版本，确认发布？', '发布课时')
        await this.$store.dispatch('education/publishLesson', {
          lessonId: this.lessonId,
          versionId: this.savedVersionId,
        })
        this.$message.success('课时已发布')
        await this.$store.dispatch('education/fetchLesson', this.lessonId)
      } catch (error) {
        if (error !== 'cancel') this.$message.error('课时发布失败')
      }
    },
  },
}
</script>

<style scoped>
.workbench { display: grid; grid-template-columns: 210px minmax(0, 1fr); gap: 18px; min-height: 580px; }
.workbench-nav { padding: 8px; border: 1px solid #e3e9ef; border-radius: 11px; background: #f8fafb; }
.workbench-nav button {
  width: 100%; display: flex; align-items: center; gap: 10px; padding: 12px;
  border: 0; border-radius: 8px; background: transparent; color: #657386; cursor: pointer; text-align: left;
}
.workbench-nav button.active { background: #fff; color: #27887e; font-weight: 700; box-shadow: 0 2px 9px rgba(30,41,59,.07); }
.version-note { margin-top: 18px; padding: 13px; border-top: 1px solid #e0e7ed; }
.version-note span, .version-note b, .version-note small { display: block; }
.version-note span { color: #8a96a6; font-size: 11px; }
.version-note b { margin: 5px 0; color: #304052; }
.version-note small { color: #8a96a6; line-height: 1.5; }
.workbench-content { min-width: 0; padding: 19px 21px; border: 1px solid #e3e9ef; border-radius: 11px; background: #fff; }
.content-heading { display: flex; align-items: start; justify-content: space-between; gap: 16px; margin-bottom: 18px; }
.content-heading h2 { margin: 0; color: #253244; font-size: 18px; }
.content-heading p { margin: 5px 0 0; color: #7a8797; font-size: 12px; }
.student-plan h3 { margin: 20px 0 7px; color: #2b394a; font-size: 15px; }
.student-plan p { padding: 14px; border-radius: 9px; background: #f6faf9; color: #586778; white-space: pre-wrap; line-height: 1.8; }
.activity-list article { display: grid; grid-template-columns: 34px 1fr auto; gap: 12px; align-items: start; padding: 14px 0; border-bottom: 1px solid #edf1f4; }
.activity-list article > span { width: 30px; height: 30px; display: grid; place-items: center; border-radius: 8px; background: #e7f5f2; color: #27887e; }
.activity-list b { color: #2f3c4d; }
.activity-list p { margin: 5px 0 0; color: #728092; line-height: 1.6; }
.empty-block { min-height: 240px; display: grid; place-items: center; border: 1px dashed #d6e0e7; border-radius: 10px; color: #8a96a6; }
@media (max-width: 860px) { .workbench { grid-template-columns: 1fr; } .workbench-nav { display: flex; } .version-note { display: none; } }
</style>
