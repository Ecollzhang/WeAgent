<template>
  <el-dialog
    title="创建研发项目"
    :visible.sync="visible"
    width="560px"
    :close-on-click-modal="false"
    @closed="resetForm"
  >
    <el-form
      ref="form"
      :model="form"
      :rules="rules"
      label-width="80px"
      label-position="top"
    >
      <el-form-item label="项目名称" prop="name">
        <el-input
          v-model="form.name"
          placeholder="如：用户反馈系统"
          maxlength="200"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="项目描述">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="2"
          placeholder="简要描述项目做什么（可选）"
          maxlength="500"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="技术栈">
        <TechStackSelector v-model="form.tech_stack" />
      </el-form-item>
    </el-form>

    <span slot="footer">
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">
        创建项目
      </el-button>
    </span>
  </el-dialog>
</template>

<script>
import TechStackSelector from './TechStackSelector.vue'

export default {
  name: 'CreateProjectDialog',
  components: { TechStackSelector },
  props: {
    value: { type: Boolean, default: false },
  },
  data() {
    return {
      submitting: false,
      form: {
        name: '',
        description: '',
        tech_stack: { frontend: '', backend: '', database: '', deployment: '' },
      },
      rules: {
        name: [
          { required: true, message: '请输入项目名称', trigger: 'blur' },
          { max: 200, message: '项目名称不能超过200个字符', trigger: 'blur' },
        ],
      },
    }
  },
  computed: {
    visible: {
      get() { return this.value },
      set(v) { this.$emit('input', v) },
    },
  },
  methods: {
    resetForm() {
      this.form = {
        name: '',
        description: '',
        tech_stack: { frontend: '', backend: '', database: '', deployment: '' },
      }
      this.submitting = false
      if (this.$refs.form) {
        this.$refs.form.resetFields()
      }
    },
    async handleSubmit() {
      try {
        await this.$refs.form.validate()
      } catch {
        return
      }
      this.submitting = true
      try {
        this.$emit('submit', { ...this.form })
      } finally {
        this.submitting = false
      }
    },
  },
}
</script>
