<template>
  <div class="safe-preview">
    <div class="safe-label">
      <i class="el-icon-lock"></i>
      隔离预览
    </div>
    <iframe
      title="教学内容安全预览"
      :srcdoc="html || emptyDocument"
      sandbox=""
      referrerpolicy="no-referrer"
      class="preview-frame"
    ></iframe>
  </div>
</template>

<script>
export default {
  name: 'SafeHtmlPreview',
  props: {
    html: { type: String, default: '' },
  },
  data() {
    return {
      emptyDocument: '<!doctype html><html><body style="font-family:sans-serif;color:#64748b;padding:24px">暂无预览内容</body></html>',
    }
  },
}
</script>

<style scoped>
.safe-preview {
  position: relative;
  overflow: hidden;
  border: 1px solid #dfe7ee;
  border-radius: 10px;
  background: #fff;
}
.safe-label {
  padding: 8px 12px;
  border-bottom: 1px solid #e9eef3;
  background: #f7fafc;
  color: #64748b;
  font-size: 11px;
}
.preview-frame {
  display: block;
  width: 100%;
  height: 460px;
  border: 0;
  background: #fff;
}
</style>
