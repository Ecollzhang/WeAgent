<template>
  <EducationShell
    :title="course ? course.title : '教学空间'"
    :subtitle="courseSubtitle"
    back-to="/education"
  >
    <template #actions>
      <el-tag
        v-if="membershipRole"
        data-testid="course-membership-role"
        :type="isTeacher ? 'success' : 'info'"
      >{{ isTeacher ? '教师空间' : '学生空间' }}</el-tag>
      <el-button icon="el-icon-edit" @click="displayNameDialog = true">修改课程姓名</el-button>
      <el-button
        v-if="isTeacher"
        data-testid="create-invitation-open"
        icon="el-icon-user"
        @click="createInvitation"
      >邀请学生</el-button>
      <el-button
        v-if="isTeacher"
        icon="el-icon-collection"
        @click="$router.push(`/education/courses/${course.id}/knowledge`)"
      >课程知识中心</el-button>
      <el-button
        v-if="isTeacher"
        data-testid="create-assignment-open"
        type="primary"
        icon="el-icon-edit-outline"
        @click="assignmentDialog = true"
      >发布作业</el-button>
    </template>

    <el-skeleton v-if="!course" :rows="8" animated />
    <template v-else>
      <nav class="course-tabs" aria-label="课程模块">
        <button
          v-for="tab in visibleTabs"
          :key="tab.key"
          type="button"
          :class="{ active: activeTab === tab.key }"
          :data-testid="`course-tab-${tab.key}`"
          @click="activeTab = tab.key"
        >
          <i :class="tab.icon"></i>{{ tab.label }}
        </button>
      </nav>

      <section v-if="activeTab === 'lessons'" class="panel">
        <div class="section-heading">
          <div>
            <h2>{{ isTeacher ? '课时与教案' : '本课程学习内容' }}</h2>
            <p>{{ isTeacher ? '按单元组织课时，编辑教案后发布稳定版本。' : '只展示教师已发布的课时和材料。' }}</p>
          </div>
        </div>
        <div v-if="flatLessons.length" class="lesson-list" data-testid="course-lesson-list">
          <button
            v-for="lesson in flatLessons"
            :key="lesson.id"
            type="button"
            class="lesson-row"
            :data-testid="`lesson-${lesson.id}`"
            @click="openLesson(lesson)"
          >
            <span class="lesson-index">{{ lesson.sequence || '•' }}</span>
            <span>
              <b>{{ lesson.title }}</b>
              <small>{{ lesson.lesson_type_code || '阅读与写作' }}</small>
            </span>
            <el-tag size="mini" :type="lesson.status === 'published' ? 'success' : 'info'">
              {{ lesson.status === 'published' ? '已发布' : '草稿' }}
            </el-tag>
            <i class="el-icon-arrow-right"></i>
          </button>
        </div>
        <div v-else class="small-empty">
          <i class="el-icon-notebook-2"></i>
          <p>{{ isTeacher ? '还没有课时。后端内容能力就绪后可在这里新建。' : '教师尚未发布学习内容。' }}</p>
        </div>
      </section>

      <section v-if="activeTab === 'assignments'" class="panel">
        <div class="section-heading">
          <div><h2>阅读与写作作业</h2><p>提交、自动反馈和教师复核都保留版本记录。</p></div>
        </div>
        <div class="assignment-grid" data-testid="course-assignment-list">
          <article
            v-for="assignment in assignments"
            :key="assignment.id"
            class="assignment-card"
            @click="openAssignment(assignment)"
          >
            <div>
              <el-tag size="mini">{{ assignment.kind || assignment.assignment_type || '综合任务' }}</el-tag>
              <span>{{ dueLabel(assignment.due_at) }}</span>
            </div>
            <h3>{{ assignment.title }}</h3>
            <p>{{ instructionText(assignment) }}</p>
            <footer>
              <span>{{ statusLabel(assignment.status) }}</span>
              <b>{{ isTeacher ? '查看提交' : '开始作答' }} <i class="el-icon-right"></i></b>
            </footer>
          </article>
          <div v-if="!assignments.length" class="small-empty">
            <i class="el-icon-edit-outline"></i>
            <p>{{ isTeacher ? '尚未发布作业。' : '暂时没有待完成作业。' }}</p>
          </div>
        </div>
      </section>

      <section v-if="activeTab === 'people' && isTeacher" class="panel">
        <div class="section-heading">
          <div>
            <h2>课程成员</h2>
            <p>显示课程姓名；教师和学生都可用页面顶部“修改课程姓名”单独设置。</p>
          </div>
          <el-button icon="el-icon-edit" @click="displayNameDialog = true">修改我的姓名</el-button>
        </div>
        <el-table :data="members" stripe data-testid="course-member-list">
          <el-table-column prop="display_name" label="姓名" min-width="150" />
          <el-table-column label="身份" width="110">
            <template #default="{ row }">{{ row.role === 'teacher' ? '教师' : '学生' }}</template>
          </el-table-column>
          <el-table-column label="账户标识" min-width="180">
            <template #default="{ row }">
              <span class="account-key">{{ row.user_id }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="joined_at" label="加入时间" min-width="180" />
          <el-table-column prop="status" label="状态" width="100" />
        </el-table>
      </section>

      <section v-if="activeTab === 'analytics' && isTeacher" class="panel">
        <div class="section-heading"><div><h2>学习数据桥</h2><p>学生学习和提交事件回流形成班级学情。</p></div></div>
        <div class="metric-grid" data-testid="course-analytics">
          <div><span>学生</span><b>{{ metric('active_students') }}</b></div>
          <div><span>完成率</span><b>{{ percentMetric('completion_rate') }}</b></div>
          <div><span>已发布作业</span><b>{{ metric('published_assignments') }}</b></div>
          <div><span>平均分</span><b>{{ metric('average_score') }}</b></div>
        </div>
        <div class="analytics-note">
          <i class="el-icon-data-analysis"></i>
          <span>{{ analytics && analytics.summary ? analytics.summary : '完成真实提交与反馈后，这里将显示常见错因和教学建议。' }}</span>
        </div>
      </section>
    </template>

    <el-dialog title="发布作业" :visible.sync="assignmentDialog" width="650px">
      <el-form label-position="top">
        <el-form-item label="作业名称">
          <el-input v-model.trim="assignmentForm.title" data-testid="assignment-title" />
        </el-form-item>
        <el-form-item label="作业要求">
          <el-input v-model="assignmentForm.instructions" type="textarea" :rows="6" />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="所属课时">
            <el-select v-model="assignmentForm.lesson_id" style="width:100%" placeholder="选择课时">
              <el-option
                v-for="lesson in flatLessons"
                :key="lesson.id"
                :label="lesson.title"
                :value="lesson.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="任务侧重">
            <el-select v-model="assignmentForm.kind" style="width:100%">
              <el-option label="阅读练习" value="quiz" />
              <el-option label="写作" value="writing" />
              <el-option label="阅读 + 写作" value="mixed" />
            </el-select>
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="assignmentDialog = false">取消</el-button>
        <el-button
          data-testid="create-assignment-submit"
          type="primary"
          :disabled="!assignmentForm.title || !assignmentForm.lesson_id"
          @click="handleCreateAssignment"
        >保存作业</el-button>
      </template>
    </el-dialog>

    <el-dialog
      title="邀请学生"
      :visible.sync="invitationDialog"
      width="560px"
      @closed="invitationToken = ''"
    >
      <p class="dialog-help">将下面的邀请码发送给学生。学生登录自己的账户后，在“教学空间”中使用邀请码加入。</p>
      <el-input
        v-model="invitationToken"
        data-testid="invitation-token"
        readonly
      >
        <el-button
          slot="append"
          data-testid="copy-invitation-token"
          icon="el-icon-document-copy"
          @click="copyInvitation"
        >一键复制</el-button>
      </el-input>
      <template #footer>
        <el-button type="primary" @click="invitationDialog = false">完成</el-button>
      </template>
    </el-dialog>
    <el-dialog title="修改课程姓名" :visible.sync="displayNameDialog" width="420px">
      <p class="name-help">该姓名只用于本课程成员列表，不会改变登录用户名。</p>
      <el-input
        v-model.trim="displayName"
        maxlength="80"
        show-word-limit
        placeholder="例如：王老师、林同学"
      />
      <template #footer>
        <el-button @click="displayNameDialog = false">取消</el-button>
        <el-button type="primary" :disabled="!displayName" @click="saveDisplayName">
          保存
        </el-button>
      </template>
    </el-dialog>
  </EducationShell>
</template>

<script>
import EducationShell from '../../components/education/EducationShell.vue'

export default {
  name: 'EducationCourseSpace',
  components: { EducationShell },
  data() {
    return {
      activeTab: 'lessons',
      assignmentDialog: false,
      invitationDialog: false,
      displayNameDialog: false,
      displayName: '',
      invitationToken: '',
      assignmentForm: {
        title: '',
        instructions: '',
        kind: 'mixed',
        lesson_id: '',
      },
      tabs: [
        { key: 'lessons', label: '课时', icon: 'el-icon-reading' },
        { key: 'assignments', label: '作业', icon: 'el-icon-edit-outline' },
        { key: 'people', label: '成员', icon: 'el-icon-user', teacherOnly: true },
        { key: 'analytics', label: '学情', icon: 'el-icon-data-analysis', teacherOnly: true },
      ],
    }
  },
  computed: {
    courseId() { return this.$route.params.courseId },
    course() { return this.$store.getters['education/activeCourse'] },
    membershipRole() { return this.$store.getters['education/membershipRole'] },
    isTeacher() { return this.$store.getters['education/isTeacher'] },
    units() { return this.$store.getters['education/units'] || [] },
    assignments() { return this.$store.getters['education/assignments'] || [] },
    members() { return this.$store.getters['education/members'] || [] },
    analytics() { return this.$store.getters['education/analytics'] || {} },
    visibleTabs() { return this.tabs.filter(tab => !tab.teacherOnly || this.isTeacher) },
    flatLessons() {
      return this.units.reduce((all, unit) => {
        const lessons = unit.lessons || []
        return all.concat(lessons.map(lesson => ({ ...lesson, unit_title: unit.title })))
      }, [])
    },
    courseSubtitle() {
      if (!this.course) return '正在核验课程成员身份'
      const subject = this.course.subject_code === 'primary_chinese' ? '小学语文' : '高中英语'
      return `${subject} · 阅读与写作 · ${this.isTeacher ? '教学管理' : '个性化学习'}`
    },
  },
  async created() {
    try {
      await this.$store.dispatch('education/selectCourse', this.courseId)
      await this.$store.dispatch('education/fetchCourseOverview', this.courseId)
    } catch (error) {
      this.$message.error('无法访问该课程，请确认你仍是课程成员')
      this.$router.replace('/education')
    }
  },
  methods: {
    async saveDisplayName() {
      try {
        await this.$store.dispatch('education/updateMyDisplayName', {
          courseId: this.courseId,
          displayName: this.displayName,
        })
        this.displayNameDialog = false
        this.$message.success('课程姓名已更新')
      } catch (error) {
        this.$message.error('课程姓名更新失败')
      }
    },
    openLesson(lesson) {
      this.$router.push(`/education/courses/${this.courseId}/lessons/${lesson.id}`)
    },
    openAssignment(assignment) {
      this.$router.push(`/education/courses/${this.courseId}/assignments/${assignment.id}`)
    },
    async createInvitation() {
      try {
        const invitation = await this.$store.dispatch('education/createInvitation', {
          courseId: this.courseId,
          limits: { max_uses: 30, expires_in_hours: 168 },
        })
        this.invitationToken = invitation.token
        this.invitationDialog = true
      } catch (error) {
        this.$message.error('邀请码创建失败')
      }
    },
    async copyInvitation() {
      if (!this.invitationToken) return
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(this.invitationToken)
        } else {
          const textarea = document.createElement('textarea')
          textarea.value = this.invitationToken
          textarea.setAttribute('readonly', '')
          textarea.style.position = 'fixed'
          textarea.style.opacity = '0'
          document.body.appendChild(textarea)
          textarea.select()
          const copied = document.execCommand('copy')
          document.body.removeChild(textarea)
          if (!copied) throw new Error('copy command was rejected')
        }
        this.$message.success('邀请码已复制')
      } catch (error) {
        this.$message.warning('自动复制失败，请手动选择邀请码复制')
      }
    },
    async handleCreateAssignment() {
      try {
        await this.$store.dispatch('education/createAssignment', {
          courseId: this.courseId,
          lessonId: this.assignmentForm.lesson_id,
          assignment: {
            title: this.assignmentForm.title,
            kind: this.assignmentForm.kind,
            instruction_json: { text: this.assignmentForm.instructions },
            evaluation_json: {},
            max_attempts: 3,
            allow_revision_after_feedback: true,
          },
        })
        this.assignmentDialog = false
        this.assignmentForm = { title: '', instructions: '', kind: 'mixed', lesson_id: '' }
        this.$message.success('作业草稿已保存')
      } catch (error) {
        this.$message.error('作业保存失败')
      }
    },
    dueLabel(value) {
      return value ? `截止 ${new Date(value).toLocaleString()}` : '长期有效'
    },
    statusLabel(value) {
      const labels = { draft: '草稿', published: '进行中', closed: '已截止', archived: '已归档' }
      return labels[value] || value || '待发布'
    },
    instructionText(assignment) {
      const value = assignment.instruction_json
      if (typeof value === 'string') return value
      return (value && (value.text || value.instructions)) || '查看作业要求与评价标准'
    },
    metric(key) {
      const value = this.analytics[key]
      return value === undefined || value === null ? '—' : value
    },
    percentMetric(key) {
      const value = this.analytics[key]
      if (value === undefined || value === null) return '—'
      return `${Math.round(value <= 1 ? value * 100 : value)}%`
    },
  },
}
</script>

<style scoped>
.course-tabs {
  display: flex; gap: 5px; margin-bottom: 18px; padding: 5px;
  border: 1px solid #e5ebf0; border-radius: 11px; background: #f6f9fb;
}
.course-tabs button {
  padding: 10px 18px; border: 0; border-radius: 8px; background: transparent;
  color: #667386; cursor: pointer; font-size: 13px;
}
.course-tabs button i { margin-right: 7px; }
.course-tabs button.active { background: #fff; color: #27887e; font-weight: 700; box-shadow: 0 2px 8px rgba(31,41,55,.07); }
.panel { min-height: 350px; }
.section-heading { display: flex; justify-content: space-between; margin: 4px 0 15px; }
.section-heading h2 { margin: 0; color: #243143; font-size: 18px; }
.section-heading p { margin: 5px 0 0; color: #768396; font-size: 12px; }
.lesson-list { border: 1px solid #e4eaf0; border-radius: 11px; overflow: hidden; }
.lesson-row {
  width: 100%; display: grid; grid-template-columns: 38px 1fr auto 24px; align-items: center;
  gap: 12px; padding: 15px 17px; border: 0; border-bottom: 1px solid #edf1f4;
  background: #fff; text-align: left; cursor: pointer;
}
.lesson-row:hover { background: #f7fbfa; }
.lesson-row:last-child { border-bottom: 0; }
.lesson-index { width: 31px; height: 31px; display: grid; place-items: center; border-radius: 9px; background: #e8f5f3; color: #27887e; }
.lesson-row b, .lesson-row small { display: block; }
.lesson-row b { color: #2a3646; }
.lesson-row small { margin-top: 4px; color: #8994a3; }
.assignment-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }
.assignment-card { padding: 17px; border: 1px solid #e2e8f0; border-radius: 11px; background: #fff; cursor: pointer; }
.assignment-card:hover { border-color: #75b9b2; box-shadow: 0 10px 24px rgba(39,136,126,.09); }
.assignment-card > div, .assignment-card footer { display: flex; align-items: center; justify-content: space-between; color: #8a96a6; font-size: 11px; }
.assignment-card h3 { margin: 14px 0 7px; color: #293647; }
.assignment-card p { min-height: 42px; color: #6c7888; font-size: 12px; line-height: 1.6; }
.assignment-card footer { margin-top: 15px; }
.assignment-card footer b { color: #27887e; }
.small-empty { min-height: 210px; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #8b98a8; border: 1px dashed #d5dfe7; border-radius: 11px; grid-column: 1/-1; }
.small-empty i { font-size: 32px; color: #9bcac5; }
.metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.metric-grid div { padding: 18px; border: 1px solid #e1e8ed; border-radius: 11px; background: #fbfdfd; }
.metric-grid span, .metric-grid b { display: block; }
.metric-grid span { color: #718096; font-size: 12px; }
.metric-grid b { margin-top: 7px; color: #237e74; font-size: 24px; }
.analytics-note { margin-top: 16px; padding: 16px; display: flex; gap: 12px; border-radius: 10px; background: #eef8f6; color: #4d675f; font-size: 13px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
@media (max-width: 900px) { .metric-grid { grid-template-columns: repeat(2, 1fr); } }
</style>
