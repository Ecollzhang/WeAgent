<template>
  <div :class="['mind-node', `depth-${Math.min(depth, 4)}`]">
    <div class="node-card">
      <span class="node-pin"></span>
      <div>
        <b>{{ node.label }}</b>
        <small v-if="node.source_type">{{ sourceLabel(node.source_type) }}</small>
      </div>
      <i v-if="node.source_ref" class="el-icon-link"></i>
    </div>
    <div v-if="node.children && node.children.length" class="node-children">
      <MindMapTree
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :depth="depth + 1"
      />
    </div>
  </div>
</template>

<script>
export default {
  name: 'MindMapTree',
  props: {
    node: { type: Object, required: true },
    depth: { type: Number, default: 0 },
  },
  methods: {
    sourceLabel(type) {
      return ({
        course: '课程',
        lesson: '课时',
        knowledge_resource: '知识资料',
      })[type] || '来源'
    },
  },
}
</script>

<style scoped>
.mind-node { position: relative; }
.node-card {
  min-width: 150px; max-width: 230px; min-height: 48px;
  display: grid; grid-template-columns: 8px 1fr auto; align-items: center; gap: 8px;
  padding: 9px 11px; border: 1px solid #d7e3df; border-radius: 10px;
  background: #fff; box-shadow: 0 6px 18px rgba(41, 76, 69, .05);
}
.node-pin { width: 6px; height: 24px; border-radius: 3px; background: #418b80; }
.node-card b, .node-card small { display: block; }.node-card b { color: #3d504b; font-size: 10px; line-height: 1.4; }.node-card small { margin-top: 3px; color: #98a4a1; font-size: 8px; }.node-card > i { color: #7b9b94; font-size: 10px; }
.depth-0 > .node-card { min-width: 185px; border-color: #6da79d; background: #edf7f4; }.depth-0 > .node-card b { color: #286f66; font-family: 'Noto Serif SC', 'Songti SC', SimSun, serif; font-size: 12px; }.depth-0 > .node-card .node-pin { background: #1f776d; }
.depth-2 > .node-card .node-pin { background: #bf8a58; }.depth-3 > .node-card .node-pin, .depth-4 > .node-card .node-pin { background: #718da8; }
.node-children { display: flex; flex-wrap: wrap; align-items: flex-start; gap: 18px; margin: 20px 0 0 32px; padding-left: 24px; border-left: 1px solid #bdd1cc; position: relative; }
.node-children::before { content: ''; position: absolute; left: -1px; top: -20px; width: 24px; height: 42px; border-bottom: 1px solid #bdd1cc; }
.node-children > .mind-node::before { content: ''; position: absolute; left: -24px; top: 23px; width: 24px; border-top: 1px solid #bdd1cc; }
</style>

