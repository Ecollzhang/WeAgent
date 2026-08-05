<template>
  <article
    class="course-card"
    :data-testid="`course-card-${course.id}`"
    tabindex="0"
    @click="$emit('open', course)"
    @keyup.enter="$emit('open', course)"
  >
    <div class="course-accent" :class="course.subject_code"></div>
    <div class="course-head">
      <span class="subject">{{ subjectLabel }}</span>
      <el-tag size="mini" :type="isTeacher ? 'success' : 'info'">
        {{ isTeacher ? '教师' : '学生' }}
      </el-tag>
    </div>
    <h2>{{ course.title }}</h2>
    <p>{{ course.description || '尚未添加课程简介' }}</p>
    <footer>
      <span>{{ gradeLabel }}</span>
      <span>进入课程 <i class="el-icon-right"></i></span>
    </footer>
  </article>
</template>

<script>
export default {
  name: 'EducationCourseCard',
  props: {
    course: { type: Object, required: true },
  },
  computed: {
    isTeacher() {
      return this.course.membership_role === 'teacher'
    },
    subjectLabel() {
      return this.course.subject_code === 'primary_chinese' ? '小学语文' : '高中英语'
    },
    gradeLabel() {
      return this.course.grade_band === 'primary' ? '小学' : '高中'
    },
  },
}
</script>

<style scoped>
.course-card {
  position: relative;
  min-height: 196px;
  padding: 20px;
  overflow: hidden;
  border: 1px solid #e2e8f0;
  border-radius: 13px;
  background: #fff;
  cursor: pointer;
  transition: transform 0.18s, box-shadow 0.18s, border-color 0.18s;
}
.course-card:hover,
.course-card:focus {
  outline: none;
  transform: translateY(-3px);
  border-color: #70b9b0;
  box-shadow: 0 16px 34px rgba(31, 94, 88, 0.12);
}
.course-accent {
  position: absolute;
  inset: 0 0 auto 0;
  height: 4px;
  background: linear-gradient(90deg, #2d9b8f, #65c2b7);
}
.course-accent.high_school_english {
  background: linear-gradient(90deg, #3f73d8, #7ca7ef);
}
.course-head,
footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.subject {
  color: #27887e;
  font-size: 12px;
  font-weight: 700;
}
h2 { margin: 18px 0 8px; color: #1f2937; font-size: 18px; }
p { min-height: 42px; margin: 0; color: #6b7280; font-size: 13px; line-height: 1.6; }
footer { margin-top: 18px; color: #8491a3; font-size: 12px; }
footer span:last-child { color: #328d83; font-weight: 600; }
</style>
