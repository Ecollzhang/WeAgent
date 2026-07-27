<template>
  <div class="lesson-plan-editor" data-testid="lesson-plan-editor">
    <el-form label-position="top">
      <div class="two-column">
        <el-form-item label="课型">
          <el-select v-model="draft.lesson_type_code" style="width:100%">
            <el-option
              v-for="option in lessonTypes"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="建议课时（分钟）">
          <el-input-number v-model="draft.duration_minutes" :min="10" :max="180" />
        </el-form-item>
      </div>
      <el-form-item label="教学目标">
        <el-input
          v-model="draft.objectives"
          type="textarea"
          :rows="4"
          placeholder="每行一个可观察、可评价的学习目标"
        />
      </el-form-item>
      <el-form-item label="教学活动">
        <el-input
          v-model="draft.activities"
          type="textarea"
          :rows="7"
          placeholder="导入、阅读/写作任务、协作活动、评价与总结"
        />
      </el-form-item>
      <el-form-item label="评价与作业">
        <el-input
          v-model="draft.assessment"
          type="textarea"
          :rows="4"
          placeholder="形成性评价、作业要求和成功标准"
        />
      </el-form-item>
    </el-form>
  </div>
</template>

<script>
export default {
  name: 'LessonPlanEditor',
  props: {
    value: { type: Object, default: () => ({}) },
    subjectCode: { type: String, default: '' },
  },
  computed: {
    draft: {
      get() {
        return this.value
      },
      set(value) {
        this.$emit('input', value)
      },
    },
    lessonTypes() {
      if (this.subjectCode === 'primary_chinese') {
        return [
          { value: 'narrative', label: '叙事类课文' },
          { value: 'scenery', label: '写景类课文' },
          { value: 'expository', label: '说明类课文' },
          { value: 'poetry', label: '诗歌 / 古诗' },
          { value: 'fable', label: '寓言 / 童话' },
          { value: 'writing', label: '习作' },
        ]
      }
      return [
        { value: 'narrative_reading', label: '记叙文阅读' },
        { value: 'expository_reading', label: '说明文阅读' },
        { value: 'argumentative_reading', label: '议论文阅读' },
        { value: 'practical_writing', label: '应用文写作' },
        { value: 'continuation_writing', label: '读后续写' },
      ]
    },
  },
}
</script>

<style scoped>
.two-column {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
@media (max-width: 760px) {
  .two-column { grid-template-columns: 1fr; }
}
</style>
