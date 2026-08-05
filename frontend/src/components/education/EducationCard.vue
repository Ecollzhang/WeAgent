<template>
  <article class="education-card" data-testid="education-card">
    <header>
      <span class="type-mark"><i :class="typeInfo.icon"></i></span>
      <div class="title-copy">
        <small>{{ typeInfo.label }} · {{ sourceLabel }}</small>
        <strong>{{ card.title || typeInfo.label }}</strong>
      </div>
      <span class="status-pill">{{ statusLabel }}</span>
    </header>

    <p v-if="card.summary" class="summary">{{ card.summary }}</p>
    <div class="meta-row">
      <span v-for="item in metaItems" :key="item.label">
        <b>{{ item.label }}</b>{{ item.value }}
      </span>
    </div>
    <p v-if="formatLabel" class="format-row">
      <i class="el-icon-files"></i> 可导出 {{ formatLabel }}
    </p>

    <footer v-if="!accessRevoked">
      <el-button size="mini" plain :loading="previewLoading" @click="preview">
        <i class="el-icon-view"></i> 预览
      </el-button>
      <el-button size="mini" plain @click="openBusiness">
        打开业务页面
      </el-button>
      <el-button
        v-if="card.object_type === 'courseware'"
        size="mini"
        plain
        :loading="exporting"
        @click="downloadPptx"
      >
        下载 PPTX
      </el-button>
      <el-button size="mini" type="primary" @click="continueCollaboration">
        继续协作
      </el-button>
    </footer>
    <footer v-else class="revoked-note">
      <i class="el-icon-lock"></i> {{ card.summary }}
    </footer>

    <el-dialog
      :title="`${card.title || typeInfo.label} · 预览`"
      :visible.sync="previewVisible"
      width="88%"
      top="5vh"
      append-to-body
      custom-class="education-card-preview-dialog"
    >
      <SafeHtmlPreview v-if="previewHtml" :html="previewHtml" />
      <div v-else class="preview-summary">
        <span class="preview-icon"><i :class="typeInfo.icon"></i></span>
        <h3>{{ card.title || typeInfo.label }}</h3>
        <p>{{ card.summary || '该业务对象已保存，可前往对应页面查看和编辑。' }}</p>
        <el-button type="primary" @click="openBusiness">打开业务页面</el-button>
      </div>
    </el-dialog>
  </article>
</template>

<script>
import {
  exportEducationContent,
  getContentVersions,
} from '../../api/education'
import SafeHtmlPreview from './SafeHtmlPreview.vue'
import downloadBlob from '../../utils/downloadBlob'

const TYPES = {
  course: { label: '课程', icon: 'el-icon-school' },
  lesson: { label: '课时', icon: 'el-icon-reading' },
  lesson_plan: { label: '教案', icon: 'el-icon-notebook-2' },
  courseware: { label: '课件', icon: 'el-icon-data-board' },
  assignment: { label: '作业', icon: 'el-icon-edit-outline' },
  question_bank: { label: '题库', icon: 'el-icon-collection-tag' },
  assessment_paper: { label: '试卷', icon: 'el-icon-document-checked' },
  knowledge_resource: { label: '知识资料', icon: 'el-icon-folder-opened' },
  student_insight: { label: '学情报告', icon: 'el-icon-pie-chart' },
  mind_map: { label: '思维导图', icon: 'el-icon-share' },
}

export default {
  name: 'EducationCard',
  components: { SafeHtmlPreview },
  props: {
    element: { type: Object, required: true },
  },
  data() {
    return {
      previewVisible: false,
      previewLoading: false,
      previewHtml: '',
      exporting: false,
    }
  },
  computed: {
    card() {
      return this.element?.data || {}
    },
    canonicalRef() {
      return this.card.canonical_ref || {}
    },
    accessRevoked() {
      return this.card.access_revoked === true
    },
    typeInfo() {
      return TYPES[this.card.object_type] || {
        label: '教学产物',
        icon: 'el-icon-document',
      }
    },
    statusLabel() {
      const labels = {
        draft: '草稿',
        active: '进行中',
        ready: '已生成',
        published: '已发布',
        completed: '已完成',
      }
      return labels[this.card.status] || this.card.status || '已保存'
    },
    sourceLabel() {
      const action = this.card.source_action || ''
      const labels = {
        'edu.courseware.create': '课件制作 Agent',
        'edu.courseware.version.create': '课件版本 Agent',
        'edu.lesson.update': '课程设计 Agent',
        'edu.question_bank.upsert': '习题生成 Agent',
        'edu.paper.compose': '组卷 Agent',
        'edu.student_insight.refresh': '学情分析 Agent',
        'edu.weakness.analyze': '练习教练 Agent',
        'edu.mind_map.create': '学习规划 Agent',
      }
      return labels[action] || 'Education Agent'
    },
    formatLabel() {
      const formats = this.card.meta?.generated_formats
      return Array.isArray(formats)
        ? formats.map(item => String(item).toUpperCase()).join(' · ')
        : ''
    },
    metaItems() {
      const meta = this.card.meta || {}
      const fields = [
        ['version_number', '版本', value => `v${value}`],
        ['version_created_at', '生成', value => new Date(value).toLocaleString()],
        ['slide_count', '页数', value => `${value} 页`],
        ['question_count', '题目', value => `${value} 题`],
        ['student_count', '学生', value => `${value} 人`],
        ['duration_minutes', '时长', value => `${value} 分钟`],
        ['theme', '风格', value => value],
      ]
      return fields
        .filter(([key]) => meta[key] !== undefined && meta[key] !== null)
        .slice(0, 4)
        .map(([key, label, format]) => ({
          label,
          value: format(meta[key]),
        }))
    },
    businessLocation() {
      const meta = this.card.meta || {}
      const courseId = meta.course_id
      const lessonId = meta.lesson_id
      const objectId = this.canonicalRef.object_id
      const type = this.card.object_type
      if (type === 'course') return `/education/courses/${objectId}`
      if (type === 'lesson') {
        return courseId
          ? `/education/courses/${courseId}/lessons/${objectId}`
          : '/education'
      }
      if (type === 'lesson_plan') {
        return courseId && lessonId
          ? `/education/courses/${courseId}/lessons/${lessonId}`
          : '/education'
      }
      if (type === 'courseware') {
        return {
          path: '/education/teacher/courseware',
          query: { courseId, lessonId },
        }
      }
      if (type === 'assignment') {
        return courseId
          ? `/education/courses/${courseId}/assignments/${objectId}`
          : '/education'
      }
      if (['question_bank', 'assessment_paper', 'knowledge_resource'].includes(type)) {
        return courseId
          ? `/education/courses/${courseId}/knowledge`
          : '/education'
      }
      if (type === 'student_insight') {
        return { path: '/education/teacher/insights', query: { courseId } }
      }
      if (type === 'mind_map') {
        return { path: '/education/student/mind-maps', query: { courseId, lessonId } }
      }
      return '/education'
    },
  },
  methods: {
    async preview() {
      if (this.accessRevoked) return
      this.previewHtml = ''
      const type = this.card.object_type
      const contentId = this.canonicalRef.object_id
      if (['courseware', 'lesson_plan'].includes(type) && contentId) {
        this.previewLoading = true
        try {
          const response = await getContentVersions(contentId)
          const versions = response?.items || []
          const versionId = this.canonicalRef.version_id
          const selected = versions.find(item => item.id === versionId) ||
            versions[versions.length - 1]
          this.previewHtml = selected?.rendered_html || ''
        } catch (error) {
          this.$message.error('暂时无法读取该产物预览')
          return
        } finally {
          this.previewLoading = false
        }
      }
      this.previewVisible = true
    },
    async downloadPptx() {
      const contentId = this.canonicalRef.object_id
      if (!contentId || this.accessRevoked) return
      this.exporting = true
      try {
        const blob = await exportEducationContent(contentId, 'pptx')
        downloadBlob(blob, `${this.card.title || '课件'}.pptx`)
      } catch (_error) {
        this.$message.error('PPTX 导出失败，请稍后重试')
      } finally {
        this.exporting = false
      }
    },
    openBusiness() {
      this.previewVisible = false
      this.$router.push(this.businessLocation).catch(() => {})
    },
    continueCollaboration() {
      const input = document.querySelector(
        '.chat-input textarea, .message-input textarea, textarea[placeholder]'
      )
      if (input) {
        input.focus()
        input.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
    },
  },
}
</script>

<style scoped>
.education-card {
  overflow: hidden;
  border: 1px solid #cee3de;
  border-radius: 14px;
  background:
    linear-gradient(110deg, rgba(226, 243, 238, .72), transparent 42%),
    #fff;
  box-shadow: 0 8px 24px rgba(37, 88, 78, .08);
}
.education-card header {
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr) auto;
  align-items: center;
  gap: 11px;
  padding: 15px 16px 10px;
}
.type-mark, .preview-icon {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border-radius: 11px;
  background: #267d71;
  color: #fff;
}
.title-copy { display: flex; min-width: 0; flex-direction: column; gap: 2px; }
.title-copy small { color: #72918a; font-size: 10px; letter-spacing: .04em; }
.title-copy strong {
  overflow: hidden;
  color: #193f38;
  font-size: 15px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.status-pill {
  border-radius: 999px;
  padding: 4px 8px;
  background: #e9f4f0;
  color: #267d71;
  font-size: 10px;
}
.summary { margin: 0; padding: 0 16px 10px; color: #58716c; font-size: 12px; }
.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  padding: 0 16px 13px;
  color: #68817b;
  font-size: 11px;
}
.meta-row b { margin-right: 5px; color: #335a52; }
.format-row {
  margin: -5px 16px 12px;
  color: #67857e;
  font-size: 11px;
}
.education-card footer {
  display: flex;
  justify-content: flex-end;
  gap: 7px;
  padding: 10px 13px;
  border-top: 1px solid #e3efec;
  background: rgba(248, 252, 251, .86);
}
.education-card footer.revoked-note {
  justify-content: flex-start;
  color: #8a9895;
  font-size: 11px;
}
.preview-summary {
  display: flex;
  min-height: 320px;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  color: #5f7872;
  text-align: center;
}
.preview-summary h3 { margin: 18px 0 8px; color: #244a42; }
.preview-summary p { max-width: 520px; margin: 0 0 22px; line-height: 1.7; }
</style>
