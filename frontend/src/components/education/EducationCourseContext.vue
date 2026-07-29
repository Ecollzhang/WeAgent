<template>
  <section class="course-context" aria-label="当前课程上下文">
    <button
      type="button"
      class="all-courses"
      title="返回全部课程"
      @click="openAllCourses"
    >
      <i class="el-icon-collection"></i>
      <span>全部课程</span>
    </button>
    <div class="context-divider"></div>
    <label for="education-course-selector">当前课程</label>
    <el-select
      id="education-course-selector"
      v-model="selectedCourseId"
      data-testid="education-course-selector"
      size="small"
      placeholder="选择课程"
      @change="handleCourseChange"
    >
      <el-option
        v-for="course in courses"
        :key="course.id"
        :value="course.id"
        :label="`${course.title} · ${roleLabel(course.membership_role)}`"
      />
    </el-select>
    <div v-if="activeCourse" class="course-meta">
      <span :class="['role-dot', membershipRole]"></span>
      <b>{{ roleLabel(membershipRole) }}</b>
      <span>{{ subjectLabel(activeCourse.subject_code) }}</span>
    </div>
    <span v-else class="empty-copy">创建或加入课程后解锁对应领域</span>
  </section>
</template>

<script>
export default {
  name: 'EducationCourseContext',
  data() {
    return { selectedCourseId: '' }
  },
  computed: {
    courses() {
      return this.$store.getters['education/courses'] || []
    },
    activeCourse() {
      return this.$store.getters['education/activeCourse']
    },
    membershipRole() {
      return this.activeCourse && this.activeCourse.membership_role
        ? this.activeCourse.membership_role
        : ''
    },
    requestedRole() {
      return (this.$route.meta && this.$route.meta.educationRole) || ''
    },
  },
  watch: {
    activeCourse: {
      immediate: true,
      handler(course) {
        this.selectedCourseId = course ? course.id : ''
      },
    },
    '$route.fullPath'() {
      this.bootstrapCourse()
    },
  },
  created() {
    this.bootstrapCourse()
  },
  methods: {
    roleLabel(role) {
      return role === 'student' ? '学生' : '教师'
    },
    subjectLabel(subject) {
      return subject === 'primary_chinese' ? '小学语文' : '高中英语'
    },
    routeCourseId() {
      return this.$route.params.courseId || this.$route.query.courseId || ''
    },
    async bootstrapCourse() {
      try {
        if (!this.courses.length) {
          await this.$store.dispatch('education/fetchCourses')
        }
        const routeCourseId = this.routeCourseId()
        const activeId = this.activeCourse && this.activeCourse.id
        const candidate = this.courses.find(course => course.id === routeCourseId)
          || this.courses.find(course => course.id === activeId)
          || this.courses.find(course => (
            !this.requestedRole || course.membership_role === this.requestedRole
          ))
          || this.courses[0]
        if (candidate && (!this.activeCourse || this.activeCourse.id !== candidate.id)) {
          await this.$store.dispatch('education/selectCourse', candidate.id)
        }
      } catch (error) {
        // Page-level empty and authorization states own user-facing messages.
      }
    },
    openAllCourses() {
      if (this.$route.name !== 'EducationHome') this.$router.push('/education')
    },
    routeFor(course, preserveModule) {
      const module = preserveModule
        ? (this.$route.meta && this.$route.meta.educationModule)
        : 'teaching-space'
      const routes = course.membership_role === 'student'
        ? {
          'mock-exams': '/education/student/mock-exams',
          'mind-maps': '/education/student/mind-maps',
        }
        : {
          courseware: '/education/teacher/courseware',
          insights: '/education/teacher/insights',
        }
      return routes[module] || `/education/courses/${course.id}`
    },
    async handleCourseChange(courseId) {
      const course = this.courses.find(item => item.id === courseId)
      if (!course) return
      const previousRole = this.membershipRole
      await this.$store.dispatch('education/selectCourse', courseId)
      const path = this.routeFor(course, previousRole === course.membership_role)
      const query = { courseId: course.id }
      if (this.$route.path !== path || this.$route.query.courseId !== course.id) {
        this.$router.push({ path, query })
      }
    },
  },
}
</script>

<style scoped>
.course-context {
  min-width: 420px;
  display: grid;
  grid-template-columns: auto 1px auto minmax(190px, 1fr);
  align-items: center;
  gap: 9px;
  padding: 8px 11px;
  border: 1px solid #dce8e5;
  border-radius: 12px;
  background: linear-gradient(120deg, rgba(246, 251, 249, .96), rgba(255, 255, 255, .98));
  box-shadow: 0 6px 20px rgba(34, 83, 76, .06);
}
.all-courses {
  display: flex;
  align-items: center;
  gap: 6px;
  border: 0;
  background: transparent;
  color: #47736d;
  cursor: pointer;
  font-size: 12px;
  white-space: nowrap;
}
.all-courses:hover { color: #1f7d73; }
.context-divider { align-self: stretch; background: #dfe9e6; }
label {
  color: #7d8d8a;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .06em;
  white-space: nowrap;
}
.course-context :deep(.el-select) { width: 100%; }
.course-context :deep(.el-input__inner) {
  border-color: #d8e5e1;
  background: #fff;
  color: #30443f;
}
.course-meta {
  grid-column: 4;
  display: flex;
  align-items: center;
  gap: 6px;
  color: #7c8c89;
  font-size: 10px;
}
.course-meta b { color: #334943; }
.role-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #c99b4c;
}
.role-dot.student { background: #5485c5; }
.empty-copy {
  grid-column: 4;
  color: #95a29f;
  font-size: 10px;
}
@media (max-width: 1120px) {
  .course-context { min-width: 310px; grid-template-columns: auto 1px minmax(160px, 1fr); }
  label, .course-meta, .empty-copy { display: none; }
  .course-context :deep(.el-select) { grid-column: 3; }
}
@media (max-width: 760px) {
  .course-context { min-width: 0; width: 100%; }
  .all-courses span { display: none; }
}
</style>
