<template>
  <div class="tech-stack-selector">
    <div class="stack-section" v-for="section in sections" :key="section.key">
      <label class="stack-label">{{ section.label }}</label>
      <el-select
        v-model="selected[section.key]"
        size="small"
        :placeholder="section.placeholder"
        clearable
        @change="$emit('change', { ...selected })"
      >
        <el-option
          v-for="opt in section.options"
          :key="opt.value"
          :label="opt.label"
          :value="opt.value"
        />
      </el-select>
    </div>
  </div>
</template>

<script>
const DEFAULT_SECTIONS = [
  {
    key: 'frontend',
    label: '前端框架',
    placeholder: '选择前端框架',
    options: [
      { label: 'Vue 3', value: 'Vue 3' },
      { label: 'Vue 2', value: 'Vue 2' },
      { label: 'React', value: 'React' },
      { label: 'Angular', value: 'Angular' },
      { label: 'Svelte', value: 'Svelte' },
      { label: '小程序', value: '小程序' },
      { label: '无前端', value: '无' },
    ],
  },
  {
    key: 'backend',
    label: '后端框架',
    placeholder: '选择后端框架',
    options: [
      { label: 'Flask', value: 'Flask' },
      { label: 'Django', value: 'Django' },
      { label: 'FastAPI', value: 'FastAPI' },
      { label: 'Spring Boot', value: 'Spring Boot' },
      { label: 'Express', value: 'Express' },
      { label: 'Go Gin', value: 'Go Gin' },
      { label: '无后端', value: '无' },
    ],
  },
  {
    key: 'database',
    label: '数据库',
    placeholder: '选择数据库',
    options: [
      { label: 'MySQL', value: 'MySQL' },
      { label: 'PostgreSQL', value: 'PostgreSQL' },
      { label: 'MongoDB', value: 'MongoDB' },
      { label: 'Redis', value: 'Redis' },
      { label: 'SQLite', value: 'SQLite' },
      { label: '无数据库', value: '无' },
    ],
  },
  {
    key: 'deployment',
    label: '部署方式',
    placeholder: '选择部署方式',
    options: [
      { label: 'Docker', value: 'Docker' },
      { label: 'Kubernetes', value: 'Kubernetes' },
      { label: '云服务器', value: '云服务器' },
      { label: 'Serverless', value: 'Serverless' },
      { label: '未定', value: '未定' },
    ],
  },
]

export default {
  name: 'TechStackSelector',
  props: {
    value: { type: Object, default: () => ({}) },
    sections: { type: Array, default: () => DEFAULT_SECTIONS },
  },
  data() {
    return {
      selected: {
        frontend: '',
        backend: '',
        database: '',
        deployment: '',
        ...this.value,
      },
    }
  },
  watch: {
    value(val) {
      this.selected = {
        frontend: '',
        backend: '',
        database: '',
        deployment: '',
        ...val,
      }
    },
  },
}
</script>

<style scoped>
.tech-stack-selector {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 16px;
}
.stack-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.stack-label {
  font-size: 13px;
  color: #606266;
  font-weight: 500;
}
</style>
