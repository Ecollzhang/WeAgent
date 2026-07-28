<template>
  <div class="education-page">
    <AppSidebar />
    <EducationModuleRail />
    <main class="education-main">
      <header class="education-header">
        <div>
          <button
            v-if="backTo"
            type="button"
            class="back-button"
            aria-label="返回"
            @click="$router.push(backTo)"
          >
            <i class="el-icon-arrow-left"></i>
          </button>
          <span class="eyebrow">WeAgent Education</span>
          <h1>{{ title }}</h1>
          <p v-if="subtitle">{{ subtitle }}</p>
        </div>
        <div class="header-actions">
          <slot name="actions"></slot>
        </div>
      </header>
      <section class="education-content">
        <slot></slot>
      </section>
    </main>
  </div>
</template>

<script>
import AppSidebar from '../Sidebar/index.vue'
import EducationModuleRail from './EducationModuleRail.vue'

export default {
  name: 'EducationShell',
  components: { AppSidebar, EducationModuleRail },
  props: {
    title: { type: String, required: true },
    subtitle: { type: String, default: '' },
    backTo: { type: [String, Object], default: '' },
  },
}
</script>

<style scoped>
.education-page {
  display: flex;
  gap: 12px;
  height: 100vh;
  padding: 12px;
  overflow: hidden;
  background:
    radial-gradient(circle at 78% 5%, rgba(45, 166, 153, 0.13), transparent 31%),
    linear-gradient(135deg, #edf5ff 0%, #f8fafc 44%, #eef8f4 100%);
}

.education-main {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 18px 45px rgba(31, 41, 55, 0.08);
}

.education-header {
  min-height: 92px;
  padding: 18px 26px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  border-bottom: 1px solid #e8edf3;
}

.education-header > div:first-child {
  min-width: 0;
}

.eyebrow {
  color: #27887e;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.13em;
  text-transform: uppercase;
}

h1 {
  display: inline;
  margin: 0 0 0 8px;
  color: #18212f;
  font-size: 23px;
}

p {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 13px;
}

.education-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 22px 26px 30px;
}

.header-actions {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.back-button {
  width: 31px;
  height: 31px;
  margin-right: 10px;
  border: 1px solid #dce4ec;
  border-radius: 9px;
  background: #fff;
  color: #526070;
  cursor: pointer;
}

@media (max-width: 900px) {
  .education-page { padding: 0; gap: 0; }
  .education-main { border-radius: 0; }
  .education-header { padding: 15px 18px; }
  .education-content { padding: 18px; }
}
</style>
