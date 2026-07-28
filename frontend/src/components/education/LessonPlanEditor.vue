<template>
  <div class="lesson-plan-editor" data-testid="lesson-plan-editor">
    <el-form label-position="top">
      <div class="two-column">
        <el-form-item label="课型">
          <el-select
            :value="value.lesson_type_code"
            style="width:100%"
            @input="updateField('lesson_type_code', $event)"
          >
            <el-option
              v-for="option in lessonTypes"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="建议课时（分钟）">
          <el-input-number
            :value="value.duration_minutes"
            :min="10"
            :max="180"
            @input="updateField('duration_minutes', $event)"
          />
        </el-form-item>
      </div>
      <EditableLessonSection
        :value="value.objectives"
        title="教学目标"
        placeholder="每行一个可观察、可评价的学习目标"
        :rows="5"
        @input="updateField('objectives', $event)"
      />
      <EditableLessonSection
        :value="value.activities"
        title="教学活动"
        placeholder="导入、阅读、写作任务、协作活动、评价与总结"
        :rows="10"
        data-testid="expand-teaching-activities"
        @input="updateField('activities', $event)"
      />
      <EditableLessonSection
        :value="value.assessment"
        title="评价与作业"
        placeholder="形成性评价、作业要求和成功标准"
        :rows="5"
        @input="updateField('assessment', $event)"
      />
    </el-form>
  </div>
</template>

<script>
import EditableLessonSection from './EditableLessonSection.vue'

export default {
  name: 'LessonPlanEditor',
  components: { EditableLessonSection },
  props: {
    value: { type: Object, default: () => ({}) },
    subjectCode: { type: String, default: '' },
  },
  computed: {
    lessonTypes() {
      if (this.subjectCode === 'primary_chinese') {
        return [
          { value: 'narrative', label: '叙事类课文' },
          { value: 'scenery', label: '写景类课文' },
          { value: 'expository', label: '说明类课文' },
          { value: 'poetry', label: '诗歌 / 古诗' },
          { value: 'fable', label: '寓言 / 童话' },
          { value: 'writing', label: '习作' },
          { value: 'reading_writing', label: '阅读与习作融合' },
          { value: 'integrated', label: '综合课' },
        ]
      }
      return [
        { value: 'narrative_reading', label: '记叙文阅读' },
        { value: 'expository_reading', label: '说明文阅读' },
        { value: 'argumentative_reading', label: '议论文阅读' },
        { value: 'practical_writing', label: '应用文写作' },
        { value: 'continuation_writing', label: '读后续写' },
        { value: 'reading_writing', label: '阅读与写作融合' },
        { value: 'integrated', label: '综合课' },
      ]
    },
  },
  methods: {
    updateField(key, value) {
      this.$emit('input', { ...this.value, [key]: value })
      this.$emit('change')
    },
  },
}
</script>

<style scoped>
.two-column { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 760px) { .two-column { grid-template-columns: 1fr; } }
</style>
