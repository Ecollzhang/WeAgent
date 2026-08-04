<template>
  <EducationShell
    title="教学空间"
    subtitle="教师备课、发布与学情回流，学生学习、提交与反馈在同一课程内完成"
  >
    <template #actions>
      <el-button
        data-testid="join-course-open"
        icon="el-icon-link"
        @click="joinDialog = true"
      >使用邀请码加入</el-button>
      <el-button
        data-testid="create-course-open"
        type="primary"
        icon="el-icon-plus"
        @click="createDialog = true"
      >创建课程</el-button>
      <el-button
        data-testid="create-course-with-agent"
        icon="el-icon-chat-dot-round"
        :loading="agentCourseLoading"
        @click="createCourseWithAgent"
      >用 Agent 创建课程</el-button>
    </template>

    <div class="course-summary">
      <div>
        <b>{{ courses.length }}</b>
        <span>我的课程</span>
      </div>
      <div>
        <b>{{ teacherCount }}</b>
        <span>负责教学</span>
      </div>
      <div>
        <b>{{ studentCount }}</b>
        <span>正在学习</span>
      </div>
      <p>身份按课程自动确定：创建课程后是教师；通过邀请码加入后是学生，不提供会绕过权限的角色开关。</p>
    </div>

    <section
      v-loading="loading"
      class="course-grid"
      data-testid="education-course-list"
    >
      <CourseCard
        v-for="course in courses"
        :key="course.id"
        :course="course"
        @open="openCourse"
      />
      <div v-if="!loading && courses.length === 0" class="empty-state">
        <div class="empty-icon"><i class="el-icon-reading"></i></div>
        <h2>从一门真实课程开始</h2>
        <p>教师可创建高中英语或小学语文课程；学生可使用教师发出的邀请码加入。</p>
        <el-button type="primary" @click="createDialog = true">创建第一门课程</el-button>
      </div>
    </section>

    <el-dialog title="创建课程" :visible.sync="createDialog" width="560px">
      <el-form ref="courseForm" :model="courseForm" :rules="courseRules" label-position="top">
        <el-form-item label="课程名称" prop="title">
          <el-input
            v-model.trim="courseForm.title"
            data-testid="create-course-title"
            maxlength="100"
            show-word-limit
            placeholder="例如：高一英语阅读与写作"
          />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="学科与学段" prop="subject_code">
            <el-select v-model="courseForm.subject_code" style="width:100%" @change="syncGradeBand">
              <el-option label="高中英语" value="high_school_english" />
              <el-option label="小学语文" value="primary_chinese" />
            </el-select>
          </el-form-item>
          <el-form-item label="教学方向">
            <el-input value="阅读 + 写作" disabled />
          </el-form-item>
        </div>
        <el-form-item label="课程简介">
          <el-input
            v-model="courseForm.description"
            type="textarea"
            :rows="3"
            maxlength="300"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialog = false">取消</el-button>
        <el-button
          data-testid="create-course-submit"
          type="primary"
          :loading="saving"
          @click="handleCreateCourse"
        >创建并进入</el-button>
      </template>
    </el-dialog>

    <el-dialog title="加入课程" :visible.sync="joinDialog" width="500px">
      <p class="dialog-help">粘贴教师发出的完整邀请码。邀请码只用于加入课程，不会改变其他课程的身份。</p>
      <el-input
        v-model.trim="invitationToken"
        data-testid="join-course-token"
        prefix-icon="el-icon-key"
        placeholder="课程邀请码"
        @keyup.enter.native="handleJoinCourse"
      />
      <template #footer>
        <el-button @click="joinDialog = false">取消</el-button>
        <el-button
          data-testid="join-course-submit"
          type="primary"
          :loading="joining"
          :disabled="!invitationToken"
          @click="handleJoinCourse"
        >加入课程</el-button>
      </template>
    </el-dialog>
  </EducationShell>
</template>

<script>
import EducationShell from '../../components/education/EducationShell.vue'
import CourseCard from '../../components/education/CourseCard.vue'
import { bootstrapEducationConversation } from '../../api/education'

export default {
  name: 'EducationHome',
  components: { CourseCard, EducationShell },
  data() {
    return {
      createDialog: false,
      joinDialog: false,
      joining: false,
      agentCourseLoading: false,
      invitationToken: '',
      courseForm: {
        title: '',
        subject_code: 'high_school_english',
        grade_band: 'senior_high',
        description: '',
      },
      courseRules: {
        title: [{ required: true, message: '请输入课程名称', trigger: 'blur' }],
        subject_code: [{ required: true, message: '请选择学科', trigger: 'change' }],
      },
    }
  },
  computed: {
    courses() { return this.$store.getters['education/courses'] || [] },
    loading() { return this.$store.getters['education/loading'] },
    saving() { return this.$store.getters['education/saving'] },
    teacherCount() {
      return this.courses.filter(course => course.membership_role === 'teacher').length
    },
    studentCount() {
      return this.courses.filter(course => course.membership_role === 'student').length
    },
  },
  created() {
    this.loadCourses()
  },
  methods: {
    async loadCourses() {
      try {
        await this.$store.dispatch('education/fetchCourses')
      } catch (error) {
        this.$message.error('课程加载失败，请稍后重试')
      }
    },
    syncGradeBand(subject) {
      this.courseForm.grade_band = subject === 'primary_chinese' ? 'primary' : 'senior_high'
    },
    openCourse(course) {
      this.$router.push(`/education/courses/${course.id}`)
    },
    async createCourseWithAgent() {
      if (this.agentCourseLoading) return
      this.agentCourseLoading = true
      try {
        const response = await bootstrapEducationConversation({
          binding_mode: 'course_bootstrap',
          agent_ids: ['_edu_1'],
          title: '用 Agent 创建新课程',
          source_route: { path: '/education' },
        })
        const conversation = response && (response.conversation || response.data?.conversation)
        if (!conversation || !conversation.id) {
          throw new Error('Education bootstrap did not return a conversation')
        }
        this.$router.push({
          path: '/dashboard',
          query: { conversation_id: conversation.id, domain: 'edu' },
        })
      } catch (error) {
        this.$message.error('课程创建 Agent 暂时无法启动')
      } finally {
        this.agentCourseLoading = false
      }
    },
    handleCreateCourse() {
      this.$refs.courseForm.validate(async valid => {
        if (!valid) return
        try {
          const course = await this.$store.dispatch('education/createCourse', this.courseForm)
          this.createDialog = false
          this.$message.success('课程已创建')
          this.openCourse(course)
        } catch (error) {
          this.$message.error('课程创建失败')
        }
      })
    },
    async handleJoinCourse() {
      if (!this.invitationToken || this.joining) return
      this.joining = true
      try {
        const result = await this.$store.dispatch('education/joinCourse', this.invitationToken)
        this.joinDialog = false
        this.invitationToken = ''
        this.$message.success(result.joined === false ? '你已经在该课程中' : '已加入课程')
      } catch (error) {
        this.$message.error('邀请码无效、已过期或已被撤销')
      } finally {
        this.joining = false
      }
    },
  },
}
</script>

<style scoped>
.course-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(100px, 150px)) 1fr;
  align-items: center;
  gap: 12px;
  margin-bottom: 22px;
  padding: 16px 20px;
  border: 1px solid #dfe8ee;
  border-radius: 12px;
  background: linear-gradient(95deg, #f0faf8, #f8fbfe);
}
.course-summary > div { display: flex; align-items: baseline; gap: 8px; }
.course-summary b { color: #207d74; font-size: 24px; }
.course-summary span,
.course-summary p { color: #657386; font-size: 12px; }
.course-summary p { margin: 0; text-align: right; }
.course-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  min-height: 260px;
}
.empty-state {
  grid-column: 1 / -1;
  min-height: 310px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 1px dashed #ccd9e2;
  border-radius: 14px;
  background: #fbfdfd;
  text-align: center;
}
.empty-icon {
  width: 64px; height: 64px; display: grid; place-items: center;
  border-radius: 18px; background: #e4f5f2; color: #288c81; font-size: 28px;
}
.empty-state h2 { margin: 16px 0 6px; color: #263344; font-size: 19px; }
.empty-state p { max-width: 500px; margin: 0 0 20px; color: #718096; font-size: 13px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.dialog-help { margin: 0 0 16px; color: #64748b; font-size: 13px; line-height: 1.6; }
@media (max-width: 860px) {
  .course-summary { grid-template-columns: repeat(3, 1fr); }
  .course-summary p { display: none; }
}
</style>
