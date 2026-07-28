<template>
  <el-form-item class="editable-lesson-section">
    <div class="field-heading">
      <span class="field-label">{{ title }}</span>
      <el-button
        class="expand-button"
        type="text"
        icon="el-icon-full-screen"
        @click="expanded = true"
      >
        放大编辑
      </el-button>
    </div>
    <el-input
      :value="value"
      type="textarea"
      :rows="rows"
      resize="vertical"
      :placeholder="placeholder"
      @input="$emit('input', $event)"
    />
    <el-dialog
      :title="`${title} · 放大编辑`"
      :visible.sync="expanded"
      width="88%"
      append-to-body
      custom-class="lesson-expanded-dialog"
    >
      <StructuredTextEditor
        :value="value"
        :title="title"
        :placeholder="placeholder"
        @input="$emit('input', $event)"
      />
      <template #footer>
        <el-button type="primary" @click="expanded = false">完成编辑</el-button>
      </template>
    </el-dialog>
  </el-form-item>
</template>

<script>
import StructuredTextEditor from './StructuredTextEditor.vue'

export default {
  name: 'EditableLessonSection',
  components: { StructuredTextEditor },
  props: {
    value: { type: String, default: '' },
    title: { type: String, required: true },
    placeholder: { type: String, default: '' },
    rows: { type: Number, default: 5 },
  },
  data() {
    return { expanded: false }
  },
}
</script>

<style scoped>
.field-heading {
  display: flex; align-items: center; justify-content: space-between;
  gap: 14px; min-height: 32px; margin-bottom: 8px;
}
.field-label { color: #334155; font-weight: 600; }
.expand-button { flex: 0 0 auto; padding: 0; }
::v-deep .el-form-item__content { line-height: normal; }
</style>
