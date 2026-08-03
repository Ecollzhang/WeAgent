<template>
  <div>
    <div
      class="tree-row"
      :class="{ selected: isSelected, 'is-dir': isDirectory }"
      :style="{ paddingLeft: (depth * 14 + 8) + 'px' }"
      @click="isDirectory ? toggle() : select()"
    >
      <span class="tree-arrow" v-if="isDirectory">
        <svg :class="{ expanded }" width="8" height="8" viewBox="0 0 8 8"><path d="M2 1l4 3-4 3" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </span>
      <span v-else class="tree-dot"> </span>
      <span class="tree-name" :title="node.name">{{ node.name }}</span>
    </div>
    <div v-if="isDirectory && expanded">
      <TreeNode
        v-for="child in (node.children || [])"
        :key="child.path || child.file_path || child.name"
        :node="child"
        :depth="depth + 1"
        :selected-path="selectedPath"
        @select="$emit('select', $event)"
      />
    </div>
  </div>
</template>

<script>
export default {
  name: 'TreeNode',
  props: { node: Object, depth: Number, selectedPath: String },
  data() {
    return { expanded: false }
  },
  computed: {
    isDirectory() { return this.node.type === 'tree' || this.node.type === 'dir' || this.node.file_type === 'directory' },
    isSelected() { return this.selectedPath === (this.node.path || this.node.file_path) },
  },
  methods: {
    toggle() { this.expanded = !this.expanded },
    select() { this.$emit('select', this.node) },
  },
}
</script>

<style scoped>
.tree-row {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 12px;
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
  transition: background 0.1s;
  color: #5f6368;
  border-radius: 0;
  user-select: none;
  line-height: 1.7;
}
.tree-row:hover { background: #e8f0fe; color: #303133; }
.tree-row.selected { background: #d4e4fc; color: #1967d2; font-weight: 500; }
.tree-row.is-dir { color: #303133; }
.tree-row.is-dir:hover { color: #111; }

.tree-arrow {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  color: #909399;
  transition: color 0.1s;
}
.tree-row:hover .tree-arrow { color: #555; }
.tree-arrow svg {
  transition: transform 0.15s ease;
}
.tree-arrow svg.expanded { transform: rotate(90deg); }

.tree-dot {
  width: 14px;
  flex-shrink: 0;
}

.tree-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
