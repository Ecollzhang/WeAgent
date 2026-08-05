<template>
  <div class="mind-graph-editor" data-testid="mind-map-graph-editor">
    <div class="graph-toolbar">
      <el-button-group>
        <el-button size="mini" icon="el-icon-refresh-left" :disabled="!editable || !undoStack.length" @click="undo">撤销</el-button>
        <el-button size="mini" icon="el-icon-refresh-right" :disabled="!editable || !redoStack.length" @click="redo">重做</el-button>
      </el-button-group>
      <el-button size="mini" icon="el-icon-aim" @click="centerGraph">居中</el-button>
      <span class="toolbar-hint">拖动节点 · 滚轮缩放 · 拖动画布平移</span>
      <el-dropdown trigger="click" @command="exportGraph">
        <el-button size="mini" icon="el-icon-download">导出<i class="el-icon-arrow-down el-icon--right"></i></el-button>
        <el-dropdown-menu slot="dropdown">
          <el-dropdown-item command="png">PNG 图片</el-dropdown-item>
          <el-dropdown-item command="svg">SVG 矢量图</el-dropdown-item>
          <el-dropdown-item command="html">HTML 网页</el-dropdown-item>
        </el-dropdown-menu>
      </el-dropdown>
    </div>

    <div class="graph-body" :class="{ editable }">
      <div ref="canvas" class="graph-canvas" aria-label="可拖拽课程思维导图"></div>
      <div v-if="inlineEditingId" class="inline-node-editor">
        <el-input ref="inlineInput" v-model.trim="inlineLabel" size="small" maxlength="120" @keyup.enter.native="commitInlineEdit" @keyup.esc.native="cancelInlineEdit" @blur="commitInlineEdit" />
        <small>Enter 保存 · Esc 取消</small>
      </div>
      <aside v-if="editable" class="node-inspector">
        <template v-if="selectedNode">
          <span class="inspector-kicker">SELECTED NODE</span>
          <el-input v-model.trim="nodeLabel" size="small" maxlength="120" @keyup.enter.native="renameNode" />
          <div class="color-palette" aria-label="节点颜色">
            <button v-for="token in COLOR_TOKENS" :key="token" type="button" :class="['color-dot', `color-${token}`, { active: (selectedNode.color_token || 'auto') === token }]" :title="colorName(token)" @click="setNodeColor(token)"></button>
          </div>
          <div class="inspector-actions">
            <el-button size="mini" type="primary" plain @click="renameNode">重命名</el-button>
            <el-button size="mini" @click="addChild">新增子节点</el-button>
          </div>
          <el-select
            v-if="selectedNode.id !== rootId"
            v-model="parentTargetId"
            size="small"
            placeholder="移动到新父节点"
            @change="reparentNode"
          >
            <el-option v-for="node in validParentNodes" :key="node.id" :label="node.label" :value="node.id" />
          </el-select>
          <div v-if="selectedNode.id !== rootId" class="inspector-actions">
            <el-button size="mini" icon="el-icon-top" @click="moveSibling(-1)">上移</el-button>
            <el-button size="mini" icon="el-icon-bottom" @click="moveSibling(1)">下移</el-button>
            <el-button size="mini" type="danger" plain @click="deleteNode">删除</el-button>
          </div>

          <div class="relation-editor">
            <h4>知识关系线</h4>
            <el-select v-model="relationTarget" size="small" placeholder="连接到节点">
              <el-option v-for="node in relationTargets" :key="node.id" :label="node.label" :value="node.id" />
            </el-select>
            <el-input v-model.trim="relationLabel" size="small" maxlength="100" placeholder="关系：因果 / 支持 / 对比" />
            <el-button size="mini" :disabled="!relationTarget" @click="addRelation">增加关系</el-button>
            <div v-for="relation in selectedRelations" :key="relation.id" class="relation-row">
              <span>{{ nodeName(relation.from) }} → {{ nodeName(relation.to) }} · {{ relation.label || '关联' }}</span>
              <button type="button" @click="deleteRelation(relation.id)"><i class="el-icon-close"></i></button>
            </div>
          </div>
        </template>
        <div v-else class="inspector-empty">点击一个节点开始编辑</div>
      </aside>
    </div>
  </div>
</template>

<script>
import { GraphChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'
import { init, use } from 'echarts/core'
import { SVGRenderer } from 'echarts/renderers'

use([GraphChart, TooltipComponent, SVGRenderer])

const clone = value => JSON.parse(JSON.stringify(value || {}))
const COLOR_TOKENS = ['auto', 'teal', 'blue', 'indigo', 'violet', 'amber', 'orange', 'rose', 'slate']
const COLOR_MAP = {
  auto: ['#f7fbfa', '#9fc3bb', '#36544e'], teal: ['#dff3ef', '#2f897d', '#245f57'],
  blue: ['#e5f0fb', '#4d82b8', '#315f8c'], indigo: ['#e9eafa', '#6167b5', '#454b8f'],
  violet: ['#f0e8fa', '#8a61b2', '#694489'], amber: ['#fff2d7', '#c68a2d', '#8a5c19'],
  orange: ['#fce9dc', '#c46e37', '#8a4825'], rose: ['#f8e5ea', '#b85e76', '#813d50'],
  slate: ['#e9eef0', '#647981', '#40545b'],
}

export default {
  name: 'MindMapGraphEditor',
  props: {
    value: { type: Object, required: true },
    editable: { type: Boolean, default: true },
  },
  data() {
    return {
      localDocument: clone(this.value),
      chart: null,
      selectedId: '',
      nodeLabel: '',
      parentTargetId: '',
      relationTarget: '',
      relationLabel: '',
      undoStack: [],
      redoStack: [],
      inlineEditingId: '',
      inlineLabel: '',
      COLOR_TOKENS,
    }
  },
  computed: {
    rootId() { return this.localDocument.root && this.localDocument.root.id },
    allNodes() {
      const rows = []
      const visit = (node, parentId = '') => {
        if (!node) return
        rows.push({ ...node, parentId })
        for (const child of node.children || []) visit(child, node.id)
      }
      visit(this.localDocument.root)
      return rows
    },
    selectedNode() { return this.findNode(this.selectedId) },
    selectedRelations() {
      return (this.localDocument.relations || []).filter(row => row.from === this.selectedId || row.to === this.selectedId)
    },
    relationTargets() { return this.allNodes.filter(node => node.id !== this.selectedId) },
    validParentNodes() {
      const blocked = new Set(this.descendantIds(this.selectedNode))
      blocked.add(this.selectedId)
      return this.allNodes.filter(node => !blocked.has(node.id))
    },
  },
  watch: {
    editable() {
      this.$nextTick(this.renderGraph)
    },
    value: {
      deep: true,
      handler(value) {
        if (JSON.stringify(value) === JSON.stringify(this.localDocument)) return
        this.localDocument = clone(value)
        this.undoStack = []
        this.redoStack = []
        this.$nextTick(this.renderGraph)
      },
    },
    selectedNode(node) {
      this.nodeLabel = node ? node.label : ''
      this.parentTargetId = node ? this.parentIdOf(node.id) : ''
      this.relationTarget = ''
      this.relationLabel = ''
    },
  },
  mounted() {
    this.chart = init(this.$refs.canvas, null, { renderer: 'svg' })
    this.chart.on('click', params => {
      if (params.dataType === 'node') this.selectedId = params.data.id
    })
    this.chart.on('dblclick', params => {
      if (params.dataType === 'node') this.startInlineEdit(params.data.id)
    })
    this.chart.on('mouseup', params => {
      if (!this.editable || params.dataType !== 'node') return
      if (!(params.event && Number.isFinite(params.event.offsetX) && Number.isFinite(params.event.offsetY))) return
      const point = this.chart.convertFromPixel({ seriesIndex: 0 }, [params.event.offsetX, params.event.offsetY])
      const node = this.findNode(params.data.id)
      if (node && Array.isArray(point)) {
        const nextPosition = { x: Math.round(point[0]), y: Math.round(point[1]) }
        const previousPosition = node.view_position || {}
        if (previousPosition.x === nextPosition.x && previousPosition.y === nextPosition.y) return
        this.snapshot()
        node.view_position = nextPosition
        this.emitChange()
      }
    })
    window.addEventListener('resize', this.resize)
    this.renderGraph()
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.resize)
    if (this.chart) this.chart.dispose()
    this.chart = null
  },
  methods: {
    resize() { if (this.chart) this.chart.resize() },
    findNode(id, node = this.localDocument.root) {
      if (!node || !id) return null
      if (node.id === id) return node
      for (const child of node.children || []) {
        const found = this.findNode(id, child)
        if (found) return found
      }
      return null
    },
    findParent(id, node = this.localDocument.root) {
      if (!node) return null
      if ((node.children || []).some(child => child.id === id)) return node
      for (const child of node.children || []) {
        const found = this.findParent(id, child)
        if (found) return found
      }
      return null
    },
    parentIdOf(id) {
      const parent = this.findParent(id)
      return parent ? parent.id : ''
    },
    descendantIds(node) {
      const ids = []
      for (const child of (node && node.children) || []) {
        ids.push(child.id, ...this.descendantIds(child))
      }
      return ids
    },
    graphData() {
      const data = []
      const edges = []
      let row = 0
      const walk = (node, depth = 0, parent = null) => {
        const position = node.view_position || { x: 80 + depth * 210, y: 70 + row * 76 }
        row += 1
        const token = node.color_token || 'auto'
        const colors = COLOR_MAP[token] || COLOR_MAP.auto
        data.push({
          id: node.id,
          name: node.label,
          x: position.x,
          y: position.y,
          symbolSize: node.id === this.rootId ? [150, 48] : [130, 40],
          itemStyle: {
            color: node.id === this.selectedId ? '#237b70' : node.id === this.rootId && token === 'auto' ? '#2f897d' : colors[0],
            borderColor: node.id === this.selectedId || (node.id === this.rootId && token === 'auto') ? '#237b70' : colors[1],
            borderWidth: 1.4,
          },
          label: { color: node.id === this.selectedId || (node.id === this.rootId && token === 'auto') ? '#fff' : colors[2] },
        })
        if (parent) edges.push({ source: parent.id, target: node.id, lineStyle: { color: '#9cbdb6', width: 1.5 } })
        if (!node.collapsed) for (const child of node.children || []) walk(child, depth + 1, node)
      }
      walk(this.localDocument.root)
      for (const relation of this.localDocument.relations || []) {
        edges.push({
          id: relation.id,
          source: relation.from,
          target: relation.to,
          value: relation.label,
          lineStyle: { color: '#d09545', type: 'dashed', width: 1.5, curveness: 0.2 },
          label: { show: Boolean(relation.label), formatter: relation.label, color: '#9a6c2e', fontSize: 10 },
        })
      }
      return { data, edges }
    },
    renderGraph() {
      if (!this.chart || !this.localDocument.root) return
      const graph = this.graphData()
      this.chart.setOption({
        tooltip: { show: true, formatter: params => params.dataType === 'node' ? params.data.name : params.data.value || '关系' },
        animationDurationUpdate: 280,
        series: [{
          type: 'graph', layout: 'none', roam: true, draggable: this.editable,
          data: graph.data, edges: graph.edges,
          edgeSymbol: ['none', 'arrow'], edgeSymbolSize: 7,
          label: { show: true, fontSize: 12, overflow: 'truncate', width: 112 },
          emphasis: { focus: 'adjacency' },
        }],
      }, true)
    },
    snapshot() {
      this.undoStack.push(clone(this.localDocument))
      if (this.undoStack.length > 50) this.undoStack.shift()
      this.redoStack = []
    },
    mutate(callback) {
      this.snapshot()
      callback()
      this.emitChange()
    },
    emitChange() {
      this.localDocument = clone(this.localDocument)
      this.$emit('input', clone(this.localDocument))
      this.$emit('change', clone(this.localDocument))
      this.$nextTick(this.renderGraph)
    },
    addChild() {
      if (!this.selectedNode) return
      const id = `node-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`
      this.mutate(() => this.selectedNode.children.push({ id, label: '新知识点', children: [] }))
      this.selectedId = id
    },
    renameNode() {
      if (!this.selectedNode || !this.nodeLabel) return
      this.mutate(() => { this.selectedNode.label = this.nodeLabel.slice(0, 120) })
    },
    startInlineEdit(id) {
      const node = this.findNode(id)
      if (!node) return
      this.selectedId = id
      if (!this.editable) this.$emit('request-edit')
      this.inlineEditingId = id
      this.inlineLabel = node.label
      this.$nextTick(() => { if (this.$refs.inlineInput) this.$refs.inlineInput.focus() })
    },
    commitInlineEdit() {
      const node = this.findNode(this.inlineEditingId)
      const next = this.inlineLabel.trim()
      if (node && next && next !== node.label) this.mutate(() => { node.label = next.slice(0, 120) })
      this.inlineEditingId = ''
      this.inlineLabel = ''
    },
    cancelInlineEdit() {
      this.inlineEditingId = ''
      this.inlineLabel = ''
    },
    colorName(token) {
      return ({ auto: '按层级自动配色', teal: '青绿', blue: '蓝色', indigo: '靛蓝', violet: '紫色', amber: '琥珀', orange: '橙色', rose: '玫红', slate: '灰蓝' })[token]
    },
    setNodeColor(color_token) {
      if (!this.selectedNode || !COLOR_TOKENS.includes(color_token)) return
      this.mutate(() => { this.selectedNode.color_token = color_token })
    },
    deleteNode() {
      if (!this.selectedNode || this.selectedId === this.rootId) return
      const removed = new Set([this.selectedId, ...this.descendantIds(this.selectedNode)])
      const parent = this.findParent(this.selectedId)
      this.mutate(() => {
        parent.children = parent.children.filter(child => child.id !== this.selectedId)
        this.localDocument.relations = (this.localDocument.relations || []).filter(row => !removed.has(row.from) && !removed.has(row.to))
      })
      this.selectedId = parent.id
    },
    reparentNode(parentId = this.parentTargetId) {
      const node = this.selectedNode
      const oldParent = this.findParent(this.selectedId)
      const newParent = this.findNode(parentId)
      if (!node || !oldParent || !newParent || oldParent.id === newParent.id) return
      this.mutate(() => {
        oldParent.children = oldParent.children.filter(child => child.id !== node.id)
        newParent.children.push(node)
      })
    },
    moveSibling(direction) {
      const parent = this.findParent(this.selectedId)
      if (!parent) return
      const index = parent.children.findIndex(child => child.id === this.selectedId)
      const target = index + direction
      if (target < 0 || target >= parent.children.length) return
      this.mutate(() => {
        const [node] = parent.children.splice(index, 1)
        parent.children.splice(target, 0, node)
        this.clearSiblingPositions(parent)
      })
    },
    clearSiblingPositions(parent) {
      const clear = node => {
        delete node.view_position
        for (const child of node.children || []) clear(child)
      }
      for (const child of (parent && parent.children) || []) clear(child)
    },
    addRelation() {
      if (!this.selectedNode || !this.relationTarget) return
      const id = `relation-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`
      this.mutate(() => {
        if (!Array.isArray(this.localDocument.relations)) this.localDocument.relations = []
        this.localDocument.relations.push({ id, from: this.selectedId, to: this.relationTarget, label: this.relationLabel, type: 'cross_link' })
      })
      this.relationTarget = ''
      this.relationLabel = ''
    },
    deleteRelation(id) {
      this.mutate(() => { this.localDocument.relations = this.localDocument.relations.filter(row => row.id !== id) })
    },
    nodeName(id) {
      const node = this.findNode(id)
      return node ? node.label : id
    },
    undo() {
      if (!this.undoStack.length) return
      this.redoStack.push(clone(this.localDocument))
      this.localDocument = this.undoStack.pop()
      this.emitChange()
    },
    redo() {
      if (!this.redoStack.length) return
      this.undoStack.push(clone(this.localDocument))
      this.localDocument = this.redoStack.pop()
      this.emitChange()
    },
    centerGraph() {
      if (!this.localDocument.root) return
      const canvasHeight = (this.$refs.canvas && this.$refs.canvas.clientHeight) || 520
      let row = 0
      const visible = this.allNodes.length
      const startY = Math.max(55, Math.round((canvasHeight - Math.max(1, visible) * 68) / 2))
      this.mutate(() => {
        const place = (node, depth = 0) => {
          node.view_position = { x: 110 + depth * 215, y: startY + row * 68 }
          row += 1
          if (!node.collapsed) for (const child of node.children || []) place(child, depth + 1)
        }
        place(this.localDocument.root)
      })
      this.$nextTick(() => { if (this.chart) this.chart.resize() })
    },
    downloadBlob(blob, filename) {
      const href = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = href
      link.download = filename
      link.click()
      URL.revokeObjectURL(href)
    },
    exportGraph(format) {
      const svgNode = this.$refs.canvas && this.$refs.canvas.querySelector('svg')
      if (!svgNode) return
      const svg = svgNode.outerHTML
      const base = (this.localDocument.root.label || 'mind-map').replace(/[\\/:*?"<>|]/g, '-').slice(0, 80)
      if (format === 'svg') {
        this.downloadBlob(new Blob([svg], { type: 'image/svg+xml;charset=utf-8' }), `${base}.svg`)
      } else if (format === 'html') {
        this.downloadBlob(new Blob([`<!doctype html><meta charset="utf-8"><title>${base}</title><style>body{margin:0;background:#f7faf9}svg{width:100%;height:auto}</style>${svg}`], { type: 'text/html;charset=utf-8' }), `${base}.html`)
      } else if (format === 'png') {
        const dataUrl = this.chart && this.chart.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#ffffff' })
        if (dataUrl && dataUrl.startsWith('data:image/png')) {
          const link = document.createElement('a')
          link.href = dataUrl
          link.download = `${base}.png`
          link.click()
          return
        }
        const image = new Image()
        const source = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml;charset=utf-8' }))
        image.onload = () => {
          const canvas = document.createElement('canvas')
          canvas.width = Math.max(1200, image.width)
          canvas.height = Math.max(700, image.height)
          const context = canvas.getContext('2d')
          context.fillStyle = '#ffffff'
          context.fillRect(0, 0, canvas.width, canvas.height)
          context.drawImage(image, 0, 0)
          canvas.toBlob(blob => { if (blob) this.downloadBlob(blob, `${base}.png`) }, 'image/png')
          URL.revokeObjectURL(source)
        }
        image.src = source
      }
    },
  },
}
</script>

<style scoped>
.mind-graph-editor { overflow: hidden; border: 1px solid #dce7e4; border-radius: 12px; background: #fff; }
.graph-toolbar { min-height: 46px; display: flex; align-items: center; gap: 9px; padding: 7px 10px; border-bottom: 1px solid #e4ecea; background: #f8fbfa; }
.toolbar-hint { margin-left: auto; color: #84928e; font-size: 10px; }
.graph-body { position: relative; display: grid; grid-template-columns: minmax(0, 1fr); min-height: 520px; }
.graph-body.editable { grid-template-columns: minmax(0, 1fr) 250px; }
.graph-canvas { min-width: 0; min-height: 520px; background-image: linear-gradient(rgba(57, 113, 103, .05) 1px, transparent 1px), linear-gradient(90deg, rgba(57, 113, 103, .05) 1px, transparent 1px); background-size: 24px 24px; }
.node-inspector { padding: 16px; overflow-y: auto; border-left: 1px solid #e3ebe9; background: #fbfdfc; }
.inline-node-editor { position: absolute; z-index: 4; top: 64px; left: 50%; width: min(320px, 70%); transform: translateX(-50%); padding: 9px; border: 1px solid #b9d5cf; border-radius: 9px; background: #fff; box-shadow: 0 12px 30px rgba(30, 73, 66, .15); }
.inline-node-editor small { display: block; margin-top: 5px; color: #879590; font-size: 9px; text-align: right; }
.color-palette { display: flex; flex-wrap: wrap; gap: 7px; margin: 11px 0; }.color-dot { width: 22px; height: 22px; border: 2px solid #fff; border-radius: 50%; box-shadow: 0 0 0 1px #cad8d4; cursor: pointer; }.color-dot.active { box-shadow: 0 0 0 2px #24796e; }
.color-auto { background: linear-gradient(135deg, #2f897d 0 50%, #dce9f6 50%); }.color-teal { background: #55a99d; }.color-blue { background: #5d91c5; }.color-indigo { background: #6f74c3; }.color-violet { background: #9970c2; }.color-amber { background: #d49b43; }.color-orange { background: #ce7a45; }.color-rose { background: #c46b82; }.color-slate { background: #71878f; }
.inspector-kicker { display: block; margin-bottom: 10px; color: #338176; font-size: 8px; font-weight: 800; letter-spacing: .13em; }
.inspector-actions { display: flex; gap: 6px; margin: 9px 0; }
.node-inspector > .el-select { width: 100%; margin-top: 5px; }
.relation-editor { margin-top: 20px; padding-top: 15px; border-top: 1px solid #e1e9e7; }
.relation-editor h4 { margin: 0 0 9px; color: #445a55; }
.relation-editor .el-select, .relation-editor .el-input { width: 100%; margin-bottom: 7px; }
.relation-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 7px; margin-top: 8px; padding: 7px; border-radius: 7px; background: #f1f6f4; color: #61736e; font-size: 9px; }
.relation-row button { border: 0; background: transparent; color: #a46d5e; cursor: pointer; }
.inspector-empty { min-height: 300px; display: grid; place-items: center; color: #96a29f; font-size: 11px; text-align: center; }
@media (max-width: 900px) { .graph-body { grid-template-columns: 1fr; }.node-inspector { border-left: 0; border-top: 1px solid #e3ebe9; }.toolbar-hint { display: none; } }
</style>
