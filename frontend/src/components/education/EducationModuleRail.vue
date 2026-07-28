<template>
  <aside class="education-rail" aria-label="Education 产品模块">
    <div class="rail-brand">
      <span class="brand-mark">EDU</span>
      <div>
        <b>教学协作台</b>
        <small>Teach · Learn · Evidence</small>
      </div>
    </div>

    <button
      type="button"
      class="all-courses"
      :class="{ active: $route.name === 'EducationHome' }"
      @click="$router.push('/education')"
    >
      <i class="el-icon-collection"></i>
      <span>全部课程</span>
    </button>

    <section class="course-context">
      <label for="education-course-selector">当前课程</label>
      <el-select
        id="education-course-selector"
        v-model="selectedCourseId"
        data-testid="education-course-selector"
        size="small"
        popper-class="education-course-options"
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
      <p v-else>创建课程成为教师，或使用邀请码以学生身份加入。</p>
    </section>

    <div class="rail-divider"></div>
    <p class="section-label">{{ membershipRole === 'student' ? '学习工具' : '教师工作台' }}</p>

    <nav class="module-list">
      <button
        v-for="module in modules"
        :key="module.key"
        type="button"
        :class="{ active: isModuleActive(module) }"
        :data-testid="`education-module-${module.key}`"
        @click="openModule(module)"
      >
        <span class="module-icon"><i :class="module.icon"></i></span>
        <span>
          <b>{{ module.label }}</b>
          <small>{{ module.caption }}</small>
        </span>
        <i class="el-icon-arrow-right module-arrow"></i>
      </button>
    </nav>

    <footer class="durability-note">
      <i class="el-icon-coin"></i>
      <span><b>课程数据已持久化</b><small>不依赖聊天或临时沙箱</small></span>
    </footer>
  </aside>
</template>

<script>
export default {
  name: 'EducationModuleRail',
  data() {
    return {
      selectedCourseId: '',
    }
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
        : this.preferredRole
    },
    preferredRole() {
      return this.$route.path.includes('/student/') ? 'student' : 'teacher'
    },
    modules() {
      if (this.membershipRole === 'student') {
        return [
          {
            key: 'mock-exams',
            label: '模拟考试',
            caption: '按课程生成与作答',
            icon: 'el-icon-document-checked',
            route: '/education/student/mock-exams',
          },
          {
            key: 'weaknesses',
            label: '作业弱点',
            caption: '证据、错因与补练',
            icon: 'el-icon-data-analysis',
            route: '/education/student/weaknesses',
          },
          {
            key: 'mind-maps',
            label: '课程思维导图',
            caption: '整理知识与来源',
            icon: 'el-icon-share',
            route: '/education/student/mind-maps',
          },
        ]
      }
      return [
        {
          key: 'teaching-space',
          label: '教学空间',
          caption: '课程、教案与作业',
          icon: 'el-icon-school',
          route: this.activeCourse
            ? `/education/courses/${this.activeCourse.id}`
            : '/education',
        },
        {
          key: 'courseware',
          label: 'PPT 与课件',
          caption: '制作、上传与发布',
          icon: 'el-icon-picture-outline',
          route: '/education/teacher/courseware',
        },
        {
          key: 'insights',
          label: '学生画像与评估',
          caption: '从学习证据出发',
          icon: 'el-icon-pie-chart',
          route: '/education/teacher/insights',
        },
      ]
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
        const candidate = this.courses.find(course => course.id === routeCourseId)
          || this.courses.find(course => course.membership_role === this.preferredRole)
          || this.courses[0]
        if (
          candidate
          && (!this.activeCourse || this.activeCourse.id !== candidate.id)
        ) {
          await this.$store.dispatch('education/selectCourse', candidate.id)
        }
      } catch (error) {
        // Page-level empty and error states remain responsible for messaging.
      }
    },
    async handleCourseChange(courseId) {
      const course = this.courses.find(item => item.id === courseId)
      if (!course) return
      await this.$store.dispatch('education/selectCourse', courseId)
      const route = course.membership_role === 'student'
        ? '/education/student/mock-exams'
        : `/education/courses/${course.id}`
      if (this.$route.path !== route || this.$route.query.courseId !== course.id) {
        this.$router.push({ path: route, query: { courseId: course.id } })
      }
    },
    isModuleActive(module) {
      const key = this.$route.meta && this.$route.meta.educationModule
      if (key) return key === module.key
      if (module.key === 'teaching-space') {
        return /^\/education\/courses\/[^/]+(?:\/lessons|\/assignments)?/.test(
          this.$route.path
        )
      }
      return this.$route.path === module.route
    },
    openModule(module) {
      if (!this.activeCourse && module.key !== 'teaching-space') {
        this.$message.info('请先创建或加入一门对应身份的课程')
        return
      }
      this.$router.push({
        path: module.route,
        query: this.activeCourse ? { courseId: this.activeCourse.id } : {},
      })
    },
  },
}
</script>

<style scoped>
.education-rail {
  width: 218px;
  flex: 0 0 218px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 17px 13px 14px;
  overflow: hidden;
  border: 1px solid rgba(122, 151, 163, 0.2);
  border-radius: 14px;
  background:
    linear-gradient(180deg, rgba(250, 253, 252, 0.98), rgba(242, 248, 246, 0.98)),
    repeating-linear-gradient(0deg, transparent 0 23px, rgba(40, 136, 126, 0.025) 24px);
  box-shadow: 0 14px 38px rgba(33, 78, 72, 0.07);
  color: #25333f;
}

.rail-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 2px 4px 15px;
}

.brand-mark {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: 12px 12px 12px 4px;
  background: #1e766e;
  box-shadow: 0 7px 18px rgba(30, 118, 110, 0.2);
  color: #fff;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.rail-brand b,
.rail-brand small {
  display: block;
}

.rail-brand b {
  font-family: 'Noto Serif SC', 'Songti SC', SimSun, serif;
  font-size: 15px;
}

.rail-brand small {
  margin-top: 3px;
  color: #84938f;
  font-size: 9px;
  letter-spacing: 0.035em;
}

.all-courses,
.module-list button {
  width: 100%;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
}

.all-courses {
  height: 38px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 11px;
  border-radius: 9px;
  color: #61716f;
  text-align: left;
}

.all-courses:hover,
.all-courses.active {
  background: #e8f3f0;
  color: #1e766e;
}

.course-context {
  margin-top: 11px;
  padding: 13px 10px 11px;
  border: 1px solid #dce9e5;
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.75);
}

.course-context label,
.section-label {
  display: block;
  margin: 0 0 7px;
  color: #82908e;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.course-context :deep(.el-select) {
  width: 100%;
}

.course-context :deep(.el-input__inner) {
  border-color: #dbe7e4;
  background: #fbfdfc;
  font-size: 12px;
}

.course-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 9px;
  color: #7b8987;
  font-size: 10px;
}

.course-meta b {
  color: #344643;
}

.role-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #cc9f50;
}

.role-dot.student {
  background: #5888c8;
}

.course-context p {
  margin: 8px 0 0;
  color: #8a9996;
  font-size: 10px;
  line-height: 1.5;
}

.rail-divider {
  height: 1px;
  margin: 15px 4px 13px;
  background: linear-gradient(90deg, transparent, #d5e3df 12%, #d5e3df 88%, transparent);
}

.section-label {
  padding: 0 8px;
}

.module-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
  overflow-y: auto;
}

.module-list button {
  min-height: 60px;
  display: grid;
  grid-template-columns: 35px 1fr 14px;
  align-items: center;
  gap: 8px;
  padding: 7px 8px;
  border-radius: 11px;
  text-align: left;
  transition: transform 150ms ease, background 150ms ease, box-shadow 150ms ease;
}

.module-list button:hover {
  transform: translateX(2px);
  background: rgba(232, 243, 240, 0.72);
}

.module-list button.active {
  background: #fff;
  box-shadow: inset 3px 0 #23867b, 0 6px 18px rgba(46, 92, 86, 0.08);
}

.module-icon {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 9px;
  background: #edf4f2;
  color: #437970;
}

.module-list button.active .module-icon {
  background: #dff0ec;
  color: #1f7d73;
}

.module-list b,
.module-list small {
  display: block;
}

.module-list b {
  color: #31423f;
  font-size: 12px;
  font-weight: 650;
}

.module-list small {
  margin-top: 3px;
  color: #91a09d;
  font-size: 9px;
}

.module-arrow {
  color: #a5b1af;
  font-size: 10px;
}

.durability-note {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-top: auto;
  padding: 12px 9px 2px;
  color: #70817e;
}

.durability-note > i {
  color: #3e8f84;
}

.durability-note b,
.durability-note small {
  display: block;
}

.durability-note b {
  font-size: 10px;
}

.durability-note small {
  margin-top: 2px;
  color: #9aa6a4;
  font-size: 8px;
}

@media (max-width: 1160px) {
  .education-rail {
    width: 184px;
    flex-basis: 184px;
  }
  .module-list button {
    grid-template-columns: 31px 1fr;
  }
  .module-arrow { display: none; }
  .module-icon { width: 30px; height: 30px; }
}

@media (max-width: 760px) {
  .education-rail {
    width: 66px;
    flex-basis: 66px;
    padding: 12px 8px;
  }
  .rail-brand { justify-content: center; padding-bottom: 12px; }
  .rail-brand > div,
  .course-context,
  .section-label,
  .module-list button > span:nth-child(2),
  .durability-note span {
    display: none;
  }
  .all-courses { justify-content: center; padding: 0; }
  .all-courses span { display: none; }
  .rail-divider { margin-top: 11px; }
  .module-list button {
    min-height: 44px;
    display: flex;
    justify-content: center;
    padding: 5px;
  }
  .durability-note { justify-content: center; padding: 10px 0 0; }
}
</style>
