<template>
  <div class="webpage-preview-card">
    <div class="wp-header">
      <span class="wp-title">
        <i class="el-icon-monitor"></i> {{ data.title || '网页预览' }}
      </span>
      <div class="wp-actions">
        <el-button size="mini" type="text" @click="$emit('expand', data)">展开</el-button>
      </div>
    </div>
    <div class="wp-body">
      <iframe
        v-if="data.content"
        :srcdoc="data.content"
        class="wp-iframe"
        sandbox="allow-scripts allow-same-origin"
        frameborder="0"
      ></iframe>
      <div v-else-if="data.preview_url" class="wp-url-preview">
        <iframe :src="data.preview_url" class="wp-iframe" frameborder="0"></iframe>
      </div>
      <div v-else class="wp-empty">无预览内容</div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'WebPreviewCard',
  props: {
    data: { type: Object, required: true },
  },
}
</script>

<style scoped>
.webpage-preview-card {
  border: 1px solid #e8eaed;
  border-radius: 8px;
  overflow: hidden;
}

.wp-header {
  display: flex;
  align-items: center;
  padding: 6px 12px;
  background: #f8f9fa;
  border-bottom: 1px solid #e8eaed;
}

.wp-title {
  font-size: 12px;
  color: #1e293b;
  font-weight: 500;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wp-title i {
  margin-right: 4px;
  color: #4080ff;
}

.wp-actions {
  flex-shrink: 0;
}

.wp-actions .el-button--mini {
  font-size: 11px;
  padding: 2px 8px;
  color: #4080ff;
}

.wp-body {
  position: relative;
}

.wp-iframe {
  width: 100%;
  height: 320px;
  display: block;
  background: #fff;
}

.wp-url-preview .wp-iframe {
  border: none;
}

.wp-empty {
  padding: 40px;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
}
</style>
