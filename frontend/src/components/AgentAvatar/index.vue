<template>
  <div class="agent-avatar" :style="avatarStyle">
    <i :class="iconClass"></i>
  </div>
</template>

<script>
export default {
  name: 'AgentAvatar',
  props: {
    agent: Object,
    size: {
      type: Number,
      default: 40,
    },
  },
  computed: {
    colorMap() {
      return {
        claude: '#6B4FA0',
        codex: '#00A67E',
        opencode: '#3178C6',
        default: '#409EFF',
      }
    },
    iconMap() {
      return {
        claude: 'el-icon-magic-stick',
        codex: 'el-icon-document-copy',
        opencode: 'el-icon-share',
        default: 'el-icon-user',
      }
    },
    adapterName() {
      return this.agent?.adapter_name || 'default'
    },
    bgColor() {
      return this.colorMap[this.adapterName] || this.colorMap.default
    },
    iconClass() {
      return this.iconMap[this.adapterName] || this.iconMap.default
    },
    avatarStyle() {
      return {
        width: `${this.size}px`,
        height: `${this.size}px`,
        backgroundColor: this.bgColor,
        fontSize: `${Math.floor(this.size * 0.5)}px`,
      }
    },
  },
}
</script>

<style scoped>
.agent-avatar {
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}
</style>
