<template>
  <el-dialog
    title="Artifact 预览"
    :visible.sync="visible"
    width="80%"
    top="5vh"
    :fullscreen="fullscreen"
  >
    <div class="artifact-preview">
      <div class="artifact-toolbar">
        <el-tag size="small">{{ artifact?.artifact_type }}</el-tag>
        <el-tag size="small" type="info" v-if="artifact?.language">{{ artifact.language }}</el-tag>
        <span class="artifact-title">{{ artifact?.title }}</span>
        <span class="artifact-version" v-if="artifact">v{{ artifact.version }}</span>
      </div>
      <div class="artifact-content" v-if="artifact?.artifact_type === 'code'">
        <pre><code>{{ artifact.content }}</code></pre>
      </div>
      <div class="artifact-content" v-else-if="artifact?.artifact_type === 'webpage'">
        <iframe :srcdoc="artifact.content" frameborder="0" class="preview-iframe"></iframe>
      </div>
      <div class="artifact-content" v-else>
        <div class="plain-content">{{ artifact?.content }}</div>
      </div>
      <div class="artifact-links" v-if="artifact?.preview_url || artifact?.deploy_url">
        <el-button
          v-if="artifact.preview_url"
          size="small"
          type="primary"
          @click="openUrl(artifact.preview_url)"
        >
          Preview URL
        </el-button>
        <el-button
          v-if="artifact.deploy_url"
          size="small"
          type="success"
          @click="openUrl(artifact.deploy_url)"
        >
          Deployed URL
        </el-button>
      </div>
    </div>
  </el-dialog>
</template>

<script>
export default {
  name: 'ArtifactPreview',
  props: {
    artifact: Object,
    visible: Boolean,
  },
  data() {
    return {
      fullscreen: false,
    }
  },
  methods: {
    openUrl(url) {
      window.open(url, '_blank')
    },
  },
}
</script>

<style scoped>
.artifact-preview {
  min-height: 300px;
}

.artifact-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e4e7ed;
}

.artifact-title {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
  flex: 1;
}

.artifact-version {
  font-size: 12px;
  color: #909399;
}

.artifact-content {
  max-height: 60vh;
  overflow-y: auto;
}

.artifact-content pre {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.5;
}

.preview-iframe {
  width: 100%;
  height: 500px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
}

.plain-content {
  white-space: pre-wrap;
  line-height: 1.6;
}

.artifact-links {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #e4e7ed;
  display: flex;
  gap: 8px;
}
</style>
