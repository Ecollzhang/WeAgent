const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')
const read = relative => fs.readFileSync(path.join(root, relative), 'utf8')
const assert = (condition, message) => { if (!condition) throw new Error(message) }

const api = read('src/api/education.js')
const store = read('src/store/modules/education.js')
const page = read('src/views/education/MindMapCenter.vue')
const graph = read('src/components/education/MindMapGraphEditor.vue')

assert(api.includes('getMindMapVersions'), 'mind map history API missing')
assert(store.includes('fetchMindMapVersions'), 'mind map history store action missing')
assert(page.includes('MindMapGraphEditor'), 'mind map page must use visual graph editor')
assert(!page.includes('json-editor'), 'raw JSON must not be the primary editor')
assert(page.includes('scope_type'), 'create flow must choose course/lesson scope')
assert(page.includes('lesson_ids'), 'lesson map must bind selected lessons')
assert(page.includes('versionHistory'), 'version history must be visible')
assert(graph.includes("from 'echarts/core'"), 'graph editor should borrow existing ECharts')
assert(graph.includes('SVGRenderer'), 'SVG renderer is required for vector export')
assert(graph.includes('draggable: this.editable'), 'nodes must be draggable only in edit mode')
assert(graph.includes('roam: true'), 'canvas must pan and zoom')
assert(graph.includes('addChild'), 'editor needs add node')
assert(graph.includes('renameNode'), 'editor needs rename node')
assert(graph.includes('deleteNode'), 'editor needs delete node')
assert(graph.includes('reparentNode'), 'editor needs visual reparenting')
assert(graph.includes('addRelation'), 'editor needs cross relations')
assert(graph.includes('undo'), 'editor needs undo')
assert(graph.includes('redo'), 'editor needs redo')
assert(graph.includes('command="png"'), 'PNG export missing')
assert(graph.includes('command="svg"'), 'SVG export missing')
assert(graph.includes('command="html"'), 'HTML export missing')
assert(
  graph.includes('params.event && Number.isFinite(params.event.offsetX)'),
  'drag handling must tolerate mouseup events without pixel coordinates'
)
assert(
  /this\.snapshot\(\)[\s\S]{0,240}node\.view_position\s*=/.test(graph),
  'dragging a node must snapshot the document before mutating its position so undo remains available'
)
assert(
  graph.includes(':disabled="!editable || !undoStack.length"') &&
    graph.includes(':disabled="!editable || !redoStack.length"'),
  'undo and redo must be disabled outside edit mode'
)
assert(
  /editable\(\)\s*\{\s*this\.\$nextTick\(this\.renderGraph\)/.test(graph),
  'the chart must re-render when edit mode changes'
)

console.log('education mind map v2 contract ok')
