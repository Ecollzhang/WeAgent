<template>
  <EducationShell
    title="Education 图文帮助"
    subtitle="用最短路径完成课程、课件、画像与学习任务"
  >
    <section class="help-hero">
      <div>
        <span>QUICK START · VERIFIED FLOWS</span>
        <h2>{{ isStudent ? '学生快速开始' : '教师快速开始' }}</h2>
        <p>每一步都对应当前系统中的真实入口。Agent 是可选加速器，课程数据始终保存在 Education 服务。</p>
      </div>
      <div class="role-switch" role="tablist" aria-label="帮助角色">
        <button :class="{ active: !isStudent }" @click="role = 'teacher'">教师</button>
        <button :class="{ active: isStudent }" @click="role = 'student'">学生</button>
      </div>
    </section>

    <section class="guide-grid">
      <article
        v-for="(step, index) in activeSteps"
        :key="step.key"
        class="guide-card"
        :style="{ '--delay': `${index * 70}ms` }"
      >
        <div :class="['help-visual', `visual-${step.visual}`]" aria-hidden="true">
          <span class="visual-number">0{{ index + 1 }}</span>
          <div v-if="step.visual === 'course'" class="course-sketch">
            <i></i><b></b><b></b><em></em>
          </div>
          <div v-else-if="step.visual === 'slides'" class="slides-sketch">
            <i></i><i></i><i></i><b><span></span><span></span></b>
          </div>
          <div v-else-if="step.visual === 'insight'" class="insight-sketch">
            <i></i><i></i><i></i><b><span></span><span></span><span></span><span></span></b>
          </div>
          <div v-else-if="step.visual === 'join'" class="join-sketch"><i></i><b>••••••</b></div>
          <div v-else-if="step.visual === 'exam'" class="exam-sketch"><i></i><b></b><b></b><b></b></div>
          <div v-else-if="step.visual === 'weakness'" class="weakness-sketch"><i></i><b></b><b></b></div>
          <div v-else class="map-sketch"><i></i><b></b><b></b><b></b></div>
        </div>
        <div class="guide-copy">
          <span>STEP {{ index + 1 }}</span>
          <h3>{{ step.title }}</h3>
          <p>{{ step.description }}</p>
          <ul><li v-for="tip in step.tips" :key="tip">{{ tip }}</li></ul>
          <el-button size="small" type="text" icon="el-icon-right" @click="open(step.route)">
            {{ step.action }}
          </el-button>
        </div>
      </article>
    </section>

    <el-alert
      title="权限提示"
      :description="isStudent ? '学生只能看到已经发布的材料、自己的提交与反馈。' : '教师草稿、答案和待确认评分不会发布给学生。'"
      type="success"
      :closable="false"
      show-icon
    />
  </EducationShell>
</template>

<script>
import EducationShell from '../../components/education/EducationShell.vue'

export default {
  name: 'EducationHelpCenter',
  components: { EducationShell },
  data() {
    return {
      role: this.$route.query.role === 'student' ? 'student' : 'teacher',
      teacherSteps: [
        { key: 'course', visual: 'course', title: '建立课程与课时', description: '在教学空间创建课程、课时并邀请真实学生。', tips: ['课程身份来自成员关系', '课时决定教案和课件上下文'], action: '进入教学空间', route: '/education' },
        { key: 'slides', visual: 'slides', title: '制作可编辑课件', description: '选择课程和课时，从教案、目标与材料生成 SlideDocument。', tips: ['先保存结构化版本', '可导出 PPTX / PDF / HTML'], action: '打开 PPT 与课件', route: '/education/teacher/courseware' },
        { key: 'insight', visual: 'insight', title: '查看班级画像', description: '正式成绩形成最高、最低、平均、中位数、分布和趋势。', tips: ['AI 建议分不进入统计', '结论可下钻到原始证据'], action: '打开学生画像', route: '/education/teacher/insights' },
      ],
      studentSteps: [
        { key: 'join', visual: 'join', title: '加入教师课程', description: '使用教师分享的邀请码进入课程，不需要切换虚拟角色。', tips: ['使用自己的账号加入', '只能看到已发布内容'], action: '查看我的课程', route: '/education' },
        { key: 'exam', visual: 'exam', title: '完成模拟考试', description: '从课程已发布题库生成试卷，作答结果成为真实学习证据。', tips: ['客观题规则判分', '答案与解析按权限显示'], action: '进入模拟考试', route: '/education/student/mock-exams' },
        { key: 'weakness', visual: 'weakness', title: '查看作业弱点', description: '依据自己的作答、错因和教师反馈获得补练建议。', tips: ['不根据聊天猜测弱点', '每条结论都显示证据'], action: '查看弱点', route: '/education/student/weaknesses' },
        { key: 'map', visual: 'map', title: '整理课程思维导图', description: '把已发布课程资料和目标整理为可编辑、有来源的知识树。', tips: ['版本化保存', '节点可以回到课程来源'], action: '打开思维导图', route: '/education/student/mind-maps' },
      ],
    }
  },
  computed: {
    isStudent() { return this.role === 'student' },
    activeSteps() { return this.isStudent ? this.studentSteps : this.teacherSteps },
  },
  methods: {
    open(path) {
      const course = this.$store.getters['education/activeCourse']
      this.$router.push({ path, query: course ? { courseId: course.id } : {} })
    },
  },
}
</script>

<style scoped>
.help-hero { display: flex; align-items: center; justify-content: space-between; gap: 24px; margin-bottom: 18px; padding: 24px 28px; border: 1px solid #dbe7e4; border-radius: 16px; background: radial-gradient(circle at 88% 20%, rgba(193,131,61,.12), transparent 24%), linear-gradient(125deg, #fbfdfc, #eef6f3); }
.help-hero span { color: #2f8277; font-size: 9px; font-weight: 800; letter-spacing: .14em; }.help-hero h2 { margin: 6px 0; color: #273d39; font-family: 'Noto Serif SC', 'Songti SC', SimSun, serif; font-size: 23px; }.help-hero p { margin: 0; color: #748681; font-size: 11px; }
.role-switch { display: flex; padding: 4px; border: 1px solid #d5e3df; border-radius: 11px; background: rgba(255,255,255,.8); }.role-switch button { padding: 8px 17px; border: 0; border-radius: 8px; background: transparent; color: #7d8d89; cursor: pointer; }.role-switch button.active { background: #2f8277; color: #fff; box-shadow: 0 5px 14px rgba(47,130,119,.2); }
.guide-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(290px, 1fr)); gap: 14px; margin-bottom: 18px; }
.guide-card { overflow: hidden; border: 1px solid #e0e8e6; border-radius: 14px; background: #fff; box-shadow: 0 10px 26px rgba(38,74,68,.05); animation: guide-enter 320ms cubic-bezier(.2,.8,.2,1) var(--delay) both; }
.help-visual { height: 145px; position: relative; overflow: hidden; display: grid; place-items: center; background: linear-gradient(145deg, #edf6f3, #f8f4ea); }
.visual-number { position: absolute; left: 15px; top: 12px; color: rgba(47,130,119,.3); font-family: Georgia, serif; font-size: 20px; }
.help-visual > div { width: 76%; height: 88px; position: relative; border: 1px solid rgba(71,113,105,.2); border-radius: 10px; background: rgba(255,255,255,.84); box-shadow: 0 13px 25px rgba(50,85,78,.1); }
.course-sketch i { position: absolute; width: 36px; height: 36px; left: 14px; top: 14px; border-radius: 9px; background: #dceee9; }.course-sketch b { display: block; width: 48%; height: 7px; margin: 16px 0 0 61px; border-radius: 5px; background: #d5e3df; }.course-sketch b + b { width: 35%; margin-top: 8px; }.course-sketch em { position: absolute; left: 14px; right: 14px; bottom: 13px; height: 9px; border-radius: 5px; background: linear-gradient(90deg,#2f8277 64%,#e6ecea 64%); }
.slides-sketch { display: grid; grid-template-columns: 38px 38px 38px 1fr; gap: 6px; padding: 10px; box-sizing: border-box; }.slides-sketch i { height: 28px; border-radius: 4px; background: #d9e9e5; }.slides-sketch b { grid-column: 1 / -1; display: flex; flex-direction: column; justify-content: center; gap: 9px; padding: 10px; border-radius: 7px; background: #f5eee2; }.slides-sketch b span { height: 6px; width: 68%; border-radius: 5px; background: #c9a577; }.slides-sketch b span + span { width: 45%; opacity: .65; }
.insight-sketch i { display: inline-block; width: 25%; height: 24px; margin: 12px 3% 0; border-radius: 6px; background: #dfede9; }.insight-sketch b { position: absolute; left: 12px; right: 12px; bottom: 12px; height: 38px; display: flex; align-items: flex-end; gap: 8px; }.insight-sketch b span { flex: 1; height: 35%; border-radius: 3px 3px 0 0; background: #4f9389; }.insight-sketch b span:nth-child(2) { height: 72%; }.insight-sketch b span:nth-child(3) { height: 52%; }.insight-sketch b span:nth-child(4) { height: 88%; background: #c08b4c; }
.join-sketch { display: grid; place-items: center; }.join-sketch i { width: 35px; height: 35px; border-radius: 50%; background: #dceee9; }.join-sketch b { padding: 7px 13px; border-radius: 7px; background: #f1f5f3; color: #4c786f; letter-spacing: .2em; }
.exam-sketch i, .exam-sketch b { display: block; height: 8px; margin: 13px 15px; border-radius: 5px; background: #dbe9e6; }.exam-sketch i { width: 45%; background: #4d9187; }.exam-sketch b::before { content: ''; display: inline-block; width: 8px; height: 8px; margin-right: 8px; border-radius: 50%; background: #c08b4c; }
.weakness-sketch i { position: absolute; width: 48px; height: 48px; left: 17px; top: 18px; border: 8px solid #d9e9e5; border-right-color: #c08b4c; border-radius: 50%; box-sizing: border-box; }.weakness-sketch b { display: block; height: 8px; margin: 24px 15px 0 82px; border-radius: 5px; background: #d9e6e3; }.weakness-sketch b + b { width: 38%; margin-top: 10px; }
.map-sketch i { position: absolute; width: 46px; height: 18px; left: calc(50% - 23px); top: 14px; border-radius: 6px; background: #4f9187; }.map-sketch b { position: absolute; width: 36px; height: 16px; bottom: 16px; border-radius: 5px; background: #dbeae6; }.map-sketch b:nth-child(2) { left: 13px; }.map-sketch b:nth-child(3) { left: calc(50% - 18px); }.map-sketch b:nth-child(4) { right: 13px; }
.guide-copy { padding: 17px; }.guide-copy > span { color: #37867b; font-size: 8px; font-weight: 800; letter-spacing: .12em; }.guide-copy h3 { margin: 5px 0 7px; color: #304440; font-size: 15px; }.guide-copy p { min-height: 34px; margin: 0; color: #778984; font-size: 10px; line-height: 1.65; }.guide-copy ul { margin: 10px 0 2px; padding-left: 16px; color: #879692; font-size: 9px; line-height: 1.7; }
@keyframes guide-enter { from { opacity: 0; transform: translateY(9px); } to { opacity: 1; transform: translateY(0); } }
@media (max-width: 700px) { .help-hero { align-items: flex-start; flex-direction: column; }.role-switch { width: 100%; }.role-switch button { flex: 1; } }
@media (prefers-reduced-motion: reduce) { .guide-card { animation: none; }.role-switch button { transition: none; } }
</style>
