<template>
  <aside class="education-chat-context" data-testid="education-chat-context">
    <span class="context-mark"><i class="el-icon-reading"></i></span>
    <div class="context-copy">
      <small>Education 业务任务</small>
      <b v-if="loading">正在关联课程与产物…</b>
      <template v-else>
        <b>{{ contextTitle }}</b>
        <span>{{ progressText }}</span>
      </template>
    </div>
    <button
      v-if="!loading && businessRoute"
      type="button"
      @click="$router.push(businessRoute)"
    >
      返回业务页面 <i class="el-icon-right"></i>
    </button>
  </aside>
</template>

<script>
export default {
  name: 'EducationChatContext',
  props: {
    context: { type: Object, default: null },
    loading: { type: Boolean, default: false },
  },
  computed: {
    contextTitle() {
      if (!this.context) return '未关联 Education 任务'
      const course = this.context.course || {}
      const lesson = this.context.lesson || {}
      const run = this.context.run || {}
      if (!course.title && this.context.binding?.binding_mode === 'course_bootstrap') {
        return '创建新课程 · 课程设计 Agent'
      }
      return [course.title, lesson.title, run.workflow_name].filter(Boolean).join(' · ')
    },
    progressText() {
      const progress = (this.context && this.context.progress) || {}
      const run = (this.context && this.context.run) || {}
      const done = progress.completed_count || 0
      const total = progress.agent_count
        || Object.keys((this.context && this.context.agent_service_views) || {}).length
      const labels = {
        pending: '等待开始', running: '协作进行中', completed: '已完成并写入业务产物',
        failed: '执行结束，可复核记录', cancelled: '已取消',
      }
      const role = this.context?.course?.membership_role
        || this.context?.membership_role
        || this.context?.binding?.membership_role_snapshot
      const roleLabel = {
        teacher: '教师',
        student: '学生',
        course_creator: '课程创建',
      }[role] || '课程成员'
      if (!run.status) {
        return `${roleLabel} · ${total || 1} 个受控 Agent · 上下文已持久化`
      }
      return `${roleLabel} · ${labels[run.status] || '已记录'} · ${done}/${total} Agent`
    },
    businessRoute() {
      if (!this.context) return null
      return this.context.run?.business_route || this.context.binding?.source_route || null
    },
  },
}
</script>

<style scoped>
.education-chat-context {
  display: grid; grid-template-columns: 34px minmax(0, 1fr) auto; align-items: center;
  gap: 10px; margin: 10px 12px 0; padding: 9px 11px; border: 1px solid #dbeae7;
  border-radius: 10px; background: linear-gradient(105deg, #f2f8f6 0%, #fbfdfc 100%);
  color: #34514c; flex-shrink: 0;
}
.context-mark {
  width: 32px; height: 32px; display: grid; place-items: center;
  border-radius: 9px; background: #267d71; color: #fff;
}
.context-copy { display: flex; min-width: 0; flex-direction: column; gap: 2px; }
.context-copy small { color: #78918c; font-size: 9px; letter-spacing: .05em; }
.context-copy b { overflow: hidden; color: #27423d; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.context-copy span { color: #78918c; font-size: 10px; }
.education-chat-context button {
  border: 0; border-radius: 8px; padding: 7px 10px; background: #fff;
  color: #267d71; box-shadow: 0 1px 4px rgba(28, 79, 71, .1); cursor: pointer;
}
.education-chat-context button:hover { background: #e4f1ee; }
</style>
