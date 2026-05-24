<template>
  <div class="fullscreen-overlay" v-if="visible" @click.self="close">
    <div class="fs-header">
      <span class="fs-title">{{ data?.title || '全屏预览' }}</span>
      <div class="fs-actions">
        <el-button-group>
          <el-button size="mini" :type="mode === 'visual' ? 'primary' : 'default'" @click="switchMode('visual')">可视化编辑</el-button>
          <el-button size="mini" :type="mode === 'source' ? 'primary' : 'default'" @click="switchMode('source')">源码编辑</el-button>
        </el-button-group>
        <el-button size="mini" @click="close">关闭</el-button>
      </div>
    </div>
    <div class="fs-body">
      <div class="fs-layers" v-if="mode === 'visual' && showLayers" @click.stop :style="{width: layerWidth+'px'}">
        <div class="layers-spacer"></div>
        <div class="layers-scroll">
          <div v-for="node in filteredLayerTree" :key="node.fullPath" class="layer-row" :class="{active: selectedPath === node.fullPath}" :style="{paddingLeft: (node.depth * 16 + 12) + 'px'}">
            <span v-for="d in node.depth" :key="'l'+d" class="layer-line" :style="{left: (d * 16 + 8) + 'px'}" :class="{active: selectedPath && node.fullPath.startsWith(selectedPath.split('>').slice(0,d+1).join('>'))}"></span>
            <span class="layer-toggle" v-if="node.hasChildren" @click.stop="toggleNode(node.fullPath)">
              <i class="el-icon-arrow-right" v-if="!isExpanded(node.fullPath)"></i>
              <i class="el-icon-arrow-down" v-else></i>
            </span>
            <span class="layer-toggle-empty" v-else></span>
            <span class="layer-node" @click="selectByPath(node.fullPath)">
              <span class="layer-text">{{ node.text }}</span>
              <span class="layer-tag">&lt;{{ node.tag }}&gt;</span>
            </span>
          </div>
          <div v-if="layerTree.length === 0" class="layers-empty">无元素</div>
        </div>
        <div class="layers-resize" @pointerdown.prevent="startResize"></div>
      </div>
      <div class="fs-preview" v-show="mode === 'visual'">
        <iframe :srcdoc="visualHtml" ref="previewIframe" class="fs-iframe" sandbox="allow-scripts allow-same-origin"></iframe>
      </div>
      <div class="fs-panel" v-if="mode === 'visual' && selectedEl" @click.stop>
        <div class="layers-spacer"></div>
        <div class="panel-scroll">
          <div class="panel-section"><div class="section-title">元素 <el-tag size="mini" type="info">{{ selectedEl?.tag }}</el-tag> <el-button size="mini" type="text" class="panel-close" @click="selectedEl=null;selectedPath=''">✕</el-button></div>
            <div class="prop-row" v-if="selectedEl?.id"><span class="prop-label">ID</span><span class="prop-val">{{ selectedEl.id }}</span></div>
            <div class="prop-row" v-if="selectedEl?.classes"><span class="prop-label">类</span><span class="prop-val">{{ selectedEl.classes }}</span></div>
            <div class="prop-row prop-text-row" v-if="selectedEl?.hasText && !isImg">
              <span class="prop-label">内容</span>
              <textarea class="prop-textarea" v-model="styleDraft.textContent" @input="applyText" :rows="2"></textarea>
            </div>
          </div>

          <!-- Image-specific controls -->
          <div class="panel-section" v-if="isImg">
            <div class="section-title">图片</div>
            <div class="prop-row"><span class="prop-label">缩放</span><input class="prop-input" v-model.number="imgScale" type="number" min="1" max="200" @input="applyImgScale" /><span class="prop-unit">%</span></div>
            <div class="prop-row"><span class="prop-label">边距</span><input class="prop-input" v-model.number="styleDraft.margin" type="number" @input="applyStyle('margin', styleDraft.margin + 'px')" /><span class="prop-unit">px</span></div>
            <div class="prop-row"><span class="prop-label">浮动</span>
              <select class="prop-select" :value="styleDraft.float" @change="applyFloat($event.target.value)">
                <option value="none">无</option><option value="left">左浮动</option><option value="right">右浮动</option>
                <option value="center">居中</option>
              </select>
            </div>
            <div class="prop-row"><span class="prop-label">替换</span>
              <el-button size="mini" @click="triggerReplaceImg">选择新图片</el-button>
              <input type="file" ref="replaceImgInput" accept="image/*" style="display:none" @change="replaceImage">
            </div>
          </div>

          <div class="panel-section"><div class="section-title">尺寸</div>
            <div class="prop-row"><span class="prop-label">宽</span><input class="prop-input" v-model.number="styleDraft.width" type="number" @input="applyStyle('width', styleDraft.width + 'px')" /><span class="prop-unit">px</span></div>
            <div class="prop-row"><span class="prop-label">高</span><input class="prop-input" v-model.number="styleDraft.height" type="number" @input="applyStyle('height', styleDraft.height + 'px')" /><span class="prop-unit">px</span></div>
          </div>
          <div class="panel-section"><div class="section-title">间距</div>
            <div class="prop-row"><span class="prop-label">上</span><input class="prop-input" v-model.number="styleDraft.paddingTop" type="number" @input="applyStyle('paddingTop', styleDraft.paddingTop + 'px')" /><span class="prop-unit">px</span></div>
            <div class="prop-row"><span class="prop-label">下</span><input class="prop-input" v-model.number="styleDraft.paddingBottom" type="number" @input="applyStyle('paddingBottom', styleDraft.paddingBottom + 'px')" /><span class="prop-unit">px</span></div>
            <div class="prop-row"><span class="prop-label">左</span><input class="prop-input" v-model.number="styleDraft.paddingLeft" type="number" @input="applyStyle('paddingLeft', styleDraft.paddingLeft + 'px')" /><span class="prop-unit">px</span></div>
            <div class="prop-row"><span class="prop-label">右</span><input class="prop-input" v-model.number="styleDraft.paddingRight" type="number" @input="applyStyle('paddingRight', styleDraft.paddingRight + 'px')" /><span class="prop-unit">px</span></div>
          </div>
          <div class="panel-section"><div class="section-title">外观</div>
            <div class="prop-row"><span class="prop-label">背景色</span><input class="prop-color" v-model="styleDraft.backgroundColor" type="color" @input="applyStyle('backgroundColor', styleDraft.backgroundColor)" /></div>
            <div class="prop-row"><span class="prop-label">文字色</span><input class="prop-color" v-model="styleDraft.color" type="color" @input="applyStyle('color', styleDraft.color)" /></div>
            <div class="prop-row"><span class="prop-label">字号</span><select class="prop-select" v-model.number="styleDraft.fontSize" @change="applyStyle('fontSize', styleDraft.fontSize + 'px')"><option v-for="s in [10,12,14,16,18,20,24,28,32,36,48]" :key="s" :value="s">{{ s }}px</option></select></div>
            <div class="prop-row"><span class="prop-label">对齐</span><div class="align-group"><button :class="{on:styleDraft.textAlign==='left'}" @click="setAlign('left')">≡</button><button :class="{on:styleDraft.textAlign==='center'}" @click="setAlign('center')">≡</button><button :class="{on:styleDraft.textAlign==='right'}" @click="setAlign('right')">≡</button></div></div>
            <div class="prop-row"><span class="prop-label">粗细</span><el-switch v-model="isBold" active-text="粗体" inactive-text="" size="mini"></el-switch></div>
          </div>
          <div class="panel-section"><div class="section-title">边框</div>
            <div class="prop-row"><span class="prop-label">宽度</span><input class="prop-input" v-model.number="styleDraft.borderWidth" type="number" @input="applyBorder" /><span class="prop-unit">px</span></div>
            <div class="prop-row"><span class="prop-label">颜色</span><input class="prop-color" v-model="styleDraft.borderColor" type="color" @input="applyBorder" /></div>
            <div class="prop-row"><span class="prop-label">圆角</span><input class="prop-input" v-model.number="styleDraft.borderRadius" type="number" @input="applyStyle('borderRadius', styleDraft.borderRadius + 'px')" /><span class="prop-unit">px</span></div>
          </div>
        </div>
        <div class="panel-footer">
          <el-button size="small" @click="duplicateComponent" icon="el-icon-document-copy">复制此组件</el-button>
          <el-button size="small" @click="deleteComponent" icon="el-icon-delete">删除此组件</el-button>
        </div>
      </div>
      <div class="fs-editor" v-show="mode === 'source'">
        <textarea class="fs-textarea" v-model="sourceDraft" spellcheck="false"></textarea>
        <div class="editor-actions">
          <span class="editor-hint" v-if="sourceDirty">* 源码已修改，尚未应用</span>
          <el-button size="small" type="primary" @click="applySource" :disabled="!sourceDirty">应用修改</el-button>
          <el-button size="small" @click="resetSource">重置</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
const INJECT_SCRIPT = `
(function(){
var s=document.createElement('style');
s.textContent='.we-toolbar{position:fixed;top:0;left:0;right:0;z-index:99999;display:flex;align-items:center;gap:4px;padding:6px 10px;background:#1e293b;border-bottom:1px solid #334155;font-family:-apple-system,sans-serif;flex-wrap:wrap;}'+
'.we-toolbar button,.we-toolbar label.btn-like{background:#334155;border:none;color:#e2e8f0;padding:3px 8px;border-radius:4px;cursor:pointer;font-size:12px;white-space:nowrap;display:inline-flex;align-items:center;gap:3px;}'+
'.we-toolbar button:hover,.we-toolbar button.on,.we-toolbar label.btn-like:hover{background:#475569;}'+
'.we-toolbar input[type=file]{display:none;}.we-toolbar .sep{width:1px;height:18px;background:#475569;margin:0 2px;}'+
'[contenteditable]:focus{outline:2px solid #4080ff;outline-offset:1px;}'+
'[contenteditable]:hover{outline:1px dashed #4080ff;outline-offset:1px;}'+
'.we-selected{outline:2px solid #4080ff!important;outline-offset:2px;}'+
'.we-dragging{opacity:0.4;}'+
'.we-drag-over{outline:2px dashed #4080ff!important;outline-offset:2px;}'+
'.we-drag-handle{cursor:grab;color:#94a3b8;font-size:13px;padding:0 3px;user-select:none;display:none;}'+
'.we-drag-mode .we-drag-handle{display:inline-block;}'+
'.we-drag-mode *{user-select:none!important;cursor:default!important;}';
document.head.appendChild(s);

var tb=document.createElement('div');
tb.className='we-toolbar';
tb.innerHTML='<button data-cmd="layers">📋 层级树</button><span class="sep"></span>'+
'<button data-cmd="undo">↩ 撤销</button><button data-cmd="redo">↪ 重做</button><span class="sep"></span>'+
'<button data-cmd="drag" class="on">⊞ 布局修改</button><span class="sep"></span>'+
'<button data-cmd="image">🖼 插入图片</button>'+
'<input type="file" id="we-img-input" accept="image/*" style="display:none">'+
'<span style="flex:1"></span><span class="label" style="color:#22c55e;">✓ 实时同步</span>';
document.body.appendChild(tb);
document.body.style.paddingTop='40px';

function getPath(el){
  var parts=[];
  while(el&&el!==document.body&&el!==document.documentElement){
    if(el.classList&&el.classList.contains('we-toolbar')){el=el.parentElement;continue;}
    var tag=el.tagName.toLowerCase();
    if(el.id){parts.unshift(tag+'#'+el.id);break;}
    var p=el.parentElement;
    if(p){
      var sib=Array.from(p.children).filter(function(c){return c.tagName===el.tagName;});
      parts.unshift(sib.length>1?tag+':nth-of-type('+(sib.indexOf(el)+1)+')':tag);
    }else{parts.unshift(tag);}
    el=p;
  }
  return parts.join('>');
}

function selectEl(el){
  document.querySelectorAll('.we-selected').forEach(function(e){e.classList.remove('we-selected');});
  el.classList.add('we-selected');
  var cs=getComputedStyle(el);
  var txt=(el.textContent||'').trim();
  parent.postMessage({type:'weagent-select',path:getPath(el),tag:el.tagName.toLowerCase(),id:el.id||'',
    classes:Array.from(el.classList).filter(function(c){return c!=='we-selected';}).join('.')||'',
    hasText:txt.length>0,textContent:txt,
    isImg:el.tagName==='IMG',
    styles:{width:parseInt(cs.width)||0,height:parseInt(cs.height)||0,
      paddingTop:parseInt(cs.paddingTop)||0,paddingRight:parseInt(cs.paddingRight)||0,
      paddingBottom:parseInt(cs.paddingBottom)||0,paddingLeft:parseInt(cs.paddingLeft)||0,
      backgroundColor:cs.backgroundColor,color:cs.color,fontSize:parseInt(cs.fontSize)||14,
      textAlign:cs.textAlign||'left',fontWeight:cs.fontWeight,
      borderWidth:parseInt(cs.borderWidth)||0,borderColor:cs.borderColor||'#000',borderRadius:parseInt(cs.borderRadius)||0,
      margin:parseInt(cs.marginTop)||0,float:cs.cssFloat||'none',
    }
  },'*');
}

document.addEventListener('click',function(e){
  var t=e.target;
  if(t.closest('.we-toolbar')||t.closest('.we-drag-handle'))return;
  if(t.isContentEditable||t.tagName==='BODY'||t.tagName==='HTML')return;
  selectEl(t);
});
document.addEventListener('dblclick',function(e){
  var t=e.target;
  if(t.closest('.we-toolbar')||t.closest('.we-drag-handle'))return;
  if(t.isContentEditable||t.tagName==='BODY'||t.tagName==='HTML')return;
  t.contentEditable=true;t.focus();
});
document.addEventListener('keydown',function(e){
  if(e.key==='Escape'&&document.activeElement&&document.activeElement.isContentEditable)
    document.activeElement.blur();
});

var syncTimer=null;
function autoSync(){
  if(syncTimer)clearTimeout(syncTimer);
  syncTimer=setTimeout(function(){parent.postMessage({type:'weagent-sync',html:document.documentElement.outerHTML},'*');},200);
}

tb.addEventListener('click',function(e){
  var btn=e.target.closest('button');if(!btn)return;
  var cmd=btn.dataset.cmd;
  if(cmd==='layers'){parent.postMessage({type:'weagent-toggle-layers'},'*');}
  else if(cmd==='undo'){parent.postMessage({type:'weagent-undo'},'*');}
  else if(cmd==='redo'){parent.postMessage({type:'weagent-redo'},'*');}
  else if(cmd==='drag'){document.body.classList.toggle('we-drag-mode');btn.classList.toggle('on');
    if(document.body.classList.contains('we-drag-mode')){addDragHandles();}else{removeDragHandles();}}
  else if(cmd==='image'){document.getElementById('we-img-input').click();}
});

document.getElementById('we-img-input').addEventListener('change',function(){
  var file=this.files[0];if(!file)return;
  var r=new FileReader();var that=this;
  r.onload=function(ev){
    var html='<div contenteditable="false" style="margin:8px 0;max-width:100%;overflow:hidden;"><img src="'+ev.target.result+'" style="width:100%;height:auto;border-radius:6px;display:block;object-fit:contain;"/></div>';
    var sel=document.querySelector('.we-selected');
    if(sel&&sel.tagName!=='BODY'){sel.insertAdjacentHTML('afterend',html);}
    else{document.body.insertAdjacentHTML('beforeend',html);}
    parent.postMessage({type:'weagent-push-undo',html:document.documentElement.outerHTML},'*');that.value='';
  };
  r.readAsDataURL(file);
});

window.addEventListener('message',function(e){
  var d=e.data;if(!d)return;
  if(d.type==='weagent-select-path'){
    var tgt=document.querySelector(d.path);
    if(tgt){selectEl(tgt);}return;
  }
  if(d.type==='weagent-duplicate'||d.type==='weagent-delete'){
    var el=document.querySelector('.we-selected');if(!el||el.tagName==='BODY')return;
    if(d.type==='weagent-duplicate'){
      var clone=el.cloneNode(true);
      el.parentNode.insertBefore(clone,el.nextSibling);selectEl(clone);
    }else{
      var next=el.nextElementSibling||el.previousElementSibling;
      el.remove();if(next)selectEl(next);
    }
    autoSync();return;
  }
  if(d.type==='weagent-img-replace'){
    var el=document.querySelector('.we-selected');
    if(el&&el.tagName==='IMG'){el.src=d.src;autoSync();}return;
  }
  var el=document.querySelector('.we-selected');if(!el)return;
  if(d.type==='weagent-style'){
    if(d.prop==='borderWidth'||d.prop==='borderColor'){
      el.style.borderWidth=d.borderWidth+'px';el.style.borderColor=d.borderColor;
      el.style.borderStyle=d.borderWidth>0?'solid':'none';
    }else{el.style[d.prop]=d.value;}
    autoSync();
  }else if(d.type==='weagent-text'){el.textContent=d.value;autoSync();}
});

var dragSrc=null;
function addHandle(el){
  if(el.classList.contains('we-toolbar'))return;
  var h=document.createElement('span');
  h.className='we-drag-handle';h.textContent='⣿';h.draggable=true;
  el.insertBefore(h,el.firstChild);
  h.addEventListener('dragstart',function(e){dragSrc=el;el.classList.add('we-dragging');e.dataTransfer.effectAllowed='move';});
  h.addEventListener('dragend',function(){el.classList.remove('we-dragging');dragSrc=null;document.querySelectorAll('.we-drag-over').forEach(function(o){o.classList.remove('we-drag-over');});});
  el.addEventListener('dragover',function(e){e.preventDefault();el.classList.add('we-drag-over');});
  el.addEventListener('dragleave',function(){el.classList.remove('we-drag-over');});
  el.addEventListener('drop',function(e){
    e.preventDefault();el.classList.remove('we-drag-over');
    if(!dragSrc||dragSrc===el||dragSrc.parentNode!==el.parentNode)return;
    var cur=el.previousSibling;
    while(cur){if(cur===dragSrc){el.parentNode.insertBefore(dragSrc,el.nextSibling);parent.postMessage({type:'weagent-push-undo',html:document.documentElement.outerHTML},'*');return;}cur=cur.previousSibling;}
    el.parentNode.insertBefore(dragSrc,el);parent.postMessage({type:'weagent-push-undo',html:document.documentElement.outerHTML},'*');
  });
}
function addDragHandles(){removeDragHandles();
  document.querySelectorAll('.grid>*,.bar-chart>*,.card,.dashboard>*:not(.we-toolbar)').forEach(function(el){addHandle(el);});}
function removeDragHandles(){document.querySelectorAll('.we-drag-handle').forEach(function(h){h.remove();});}
})();
`;

function parseRgb(rgb) {
  if (!rgb || rgb === 'transparent') return '#ffffff'
  if (rgb.startsWith('#')) return rgb
  const m = rgb.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/)
  if (m) return '#' + [m[1], m[2], m[3]].map(x => parseInt(x).toString(16).padStart(2, '0')).join('')
  return '#ffffff'
}

function stripInjected(html) {
  return html.replace(/<div class="we-toolbar">[\s\S]*?<\/div>/g, '').replace(/<script>[\s\S]*?<\/script>/g, '')
}

function buildLayerTree(html) {
  const skipTags = ['html','head','script','style','meta','link','title','base']
  const items = []
  const parser = new DOMParser()
  const doc = parser.parseFromString(html, 'text/html')
  function walk(el, depth, parentPath) {
    if (!el || el.nodeType !== 1) return
    const tag = el.tagName.toLowerCase()
    if (!tag || skipTags.includes(tag) || tag === 'body') {
      for (let i = 0; i < el.children.length; i++) walk(el.children[i], depth, parentPath)
      return
    }
    if (el.classList && el.classList.contains('we-toolbar')) return
    const p = el.parentElement
    const sib = p ? Array.from(p.children).filter(c => c.tagName === el.tagName) : [el]
    let seg = el.tagName.toLowerCase()
    if (el.id) { seg += '#' + el.id }
    else if (sib.length > 1) { seg += ':nth-of-type(' + (sib.indexOf(el) + 1) + ')' }
    const fullPath = parentPath ? parentPath + '>' + seg : seg
    const text = (el.textContent || '').trim().slice(0, 28)
    const hasChildren = el.children.length > 0 && Array.from(el.children).some(c => c.nodeType === 1 && !skipTags.includes(c.tagName.toLowerCase()))
    items.push({ tag: seg, text, depth, hasChildren, fullPath })
    for (let i = 0; i < el.children.length; i++) walk(el.children[i], depth + 1, fullPath)
  }
  walk(doc.body, 0, '')
  return items
}

export default {
  name: 'ArtifactFullscreenPreview',
  props: {
    data: { type: Object, default: null },
    visible: { type: Boolean, default: false },
  },
  data() {
    return {
      mode: 'visual',
      visualHtml: '',
      savedHtml: '',
      sourceDraft: '',
      sourceDirty: false,
      selectedEl: null,
      selectedPath: '',
      showLayers: false,
      layerWidth: 240,
      expandedNodes: {},
      isImg: false,
      undoStack: [],
      redoStack: [],
      styleDraft: {
        width: 0, height: 0,
        paddingTop: 0, paddingRight: 0, paddingBottom: 0, paddingLeft: 0,
        backgroundColor: '#ffffff', color: '#1e293b',
        fontSize: 14, textAlign: 'left', fontWeight: 'normal',
        borderWidth: 0, borderColor: '#000000', borderRadius: 0,
        textContent: '', margin: 0, float: 'none', scale: 100,
      },
    }
  },
  computed: {
    isBold: {
      get() { return this.styleDraft.fontWeight === 'bold' || this.styleDraft.fontWeight === '700' },
      set(v) { this.styleDraft.fontWeight = v ? 'bold' : 'normal'; this.applyStyle('fontWeight', this.styleDraft.fontWeight) },
    },
    imgScale: {
      get() { return this.styleDraft.scale || 100 },
      set(v) { this.styleDraft.scale = v },
    },
    layerTree() { return buildLayerTree(this.savedHtml) },
    filteredLayerTree() {
      return this.layerTree.filter(n => {
        if (n.depth === 0) return true
        const parts = n.fullPath.split('>')
        parts.pop()
        return this.isExpanded(parts.join('>'))
      })
    },
  },
  watch: {
    data: {
      immediate: true,
      handler(val) {
        const html = val?.content || ''
        const injected = html.replace('</body>', '<script>' + INJECT_SCRIPT + '<\/script>\n</body>')
        this.visualHtml = injected
        this.savedHtml = injected; this.sourceDraft = html
        this.sourceDirty = false; this.mode = 'visual'
        this.selectedEl = null; this.selectedPath = ''; this.showLayers = false; this.isImg = false
      },
    },
    visible(val) {
      if (val) {
        this.$nextTick(() => {
          window.removeEventListener('message', this._msgHandler)
          this._msgHandler = (e) => {
            const d = e.data; if (!d) return
            if (d.type === 'weagent-sync') {
              this.savedHtml = d.html
              this.$emit('save', { ...this.data, content: stripInjected(d.html) })
            } else if (d.type === 'weagent-push-undo') {
              this.pushUndo()
              this.savedHtml = d.html
              this.$emit('save', { ...this.data, content: stripInjected(d.html) })
            } else if (d.type === 'weagent-select') {
              this.selectedEl = { tag: d.tag, id: d.id, classes: d.classes, hasText: d.hasText }
              this.selectedPath = d.path || ''
              this.isImg = !!d.isImg
              const s = d.styles
              const prevScale = this.styleDraft.scale || 100
              this.styleDraft = { ...this.styleDraft,
                width: s.width, height: s.height,
                paddingTop: s.paddingTop, paddingRight: s.paddingRight,
                paddingBottom: s.paddingBottom, paddingLeft: s.paddingLeft,
                backgroundColor: parseRgb(s.backgroundColor), color: parseRgb(s.color),
                fontSize: s.fontSize, textAlign: s.textAlign, fontWeight: s.fontWeight,
                borderWidth: s.borderWidth, borderColor: parseRgb(s.borderColor), borderRadius: s.borderRadius,
                textContent: d.textContent || '', margin: s.margin || 0, float: s.float || 'none',
                scale: d.isImg ? prevScale : 100,
              }
            } else if (d.type === 'weagent-toggle-layers') {
              this.showLayers = !this.showLayers
            } else if (d.type === 'weagent-undo') {
              this.undo()
            } else if (d.type === 'weagent-redo') {
              this.redo()
            }
          }
          window.addEventListener('message', this._msgHandler)
        })
      }
    },
  },
  methods: {
    close() { this.mode = 'visual'; this.selectedEl = null; this.selectedPath = ''; this.$emit('close') },
    switchMode(newMode) {
      if (newMode === this.mode) return
      if (this.mode === 'source' && this.sourceDirty) {
        this.$confirm('源码有未应用的修改，是否放弃？', '提示', { confirmButtonText: '放弃修改', cancelButtonText: '取消', type: 'warning',
        }).then(() => { this.sourceDraft = this.savedHtml; this.sourceDirty = false; this._doSwitch(newMode) }).catch(() => {})
        return
      }
      this._doSwitch(newMode)
    },
    _doSwitch(newMode) {
      if (this.mode === 'visual' && newMode === 'source') { this.sourceDraft = stripInjected(this.savedHtml); this.sourceDirty = false }
      if (this.mode === 'source' && newMode === 'visual') {
        this.visualHtml = this.savedHtml
      }
      this.mode = newMode
      if (newMode !== 'visual') { this.selectedEl = null; this.selectedPath = '' }
    },
    applySource() {
      const withInjection = this.sourceDraft.replace('</body>', '<script>' + INJECT_SCRIPT + '<\/script>\n</body>')
      this.visualHtml = withInjection
      this.savedHtml = withInjection
      this.sourceDirty = false; this.$emit('save', { ...this.data, content: this.sourceDraft })
    },
    resetSource() { this.sourceDraft = this.savedHtml; this.sourceDirty = false },
    selectByPath(path) {
      this.selectedPath = path
      const iframe = this.$refs.previewIframe
      if (iframe && iframe.contentWindow) iframe.contentWindow.postMessage({ type: 'weagent-select-path', path }, '*')
    },
    _postToIframe(msg) {
      if (msg.type === 'weagent-style' || msg.type === 'weagent-text') this.pushUndo()
      const f = this.$refs.previewIframe; if (f && f.contentWindow) f.contentWindow.postMessage(msg, '*')
    },
    duplicateComponent() { this._postToIframe({ type: 'weagent-duplicate' }) },
    deleteComponent() { this.$confirm('确认删除此组件？', '提示', { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning',
      }).then(() => { this._postToIframe({ type: 'weagent-delete' }) }).catch(() => {}) },
    isExpanded(path) { return this.expandedNodes[path] !== false },
    toggleNode(path) { this.$set(this.expandedNodes, path, !this.isExpanded(path)) },
    pushUndo() {
      this.undoStack.push(this.savedHtml)
      if (this.undoStack.length > 50) this.undoStack.shift()
      this.redoStack = []
    },
    undo() {
      if (this.undoStack.length === 0) { this.$message.info('没有可撤销的操作'); return }
      this.redoStack.push(this.savedHtml)
      const prev = this.undoStack.pop()
      this._restoreHtml(prev)
    },
    redo() {
      if (this.redoStack.length === 0) { this.$message.info('没有可重做的操作'); return }
      this.undoStack.push(this.savedHtml)
      const next = this.redoStack.pop()
      this._restoreHtml(next)
    },
    _restoreHtml(html) {
      const withInjection = html.replace('</body>', '<script>' + INJECT_SCRIPT + '<\/script>\n</body>')
      this.visualHtml = withInjection
      this.savedHtml = withInjection
      this.sourceDraft = html
      this.sourceDirty = false
      this.selectedEl = null
      this.selectedPath = ''
      this.$emit('save', { ...this.data, content: html })
    },
    startResize(e) {
      const el = e.target
      el.setPointerCapture(e.pointerId)
      const startX = e.clientX; const startW = this.layerWidth
      const move = (ev) => { this.layerWidth = Math.max(160, Math.min(500, startW + ev.clientX - startX)) }
      const up = () => { el.removeEventListener('pointermove', move); el.removeEventListener('pointerup', up); el.releasePointerCapture(e.pointerId) }
      el.addEventListener('pointermove', move); el.addEventListener('pointerup', up)
      e.preventDefault()
    },
    applyImgScale() {
      const pct = Math.max(10, Math.min(200, this.imgScale || 100))
      this.styleDraft.scale = pct
      this._postToIframe({ type: 'weagent-style', prop: 'width', value: pct + '%' })
      this._postToIframe({ type: 'weagent-style', prop: 'maxWidth', value: '100%' })
      this._postToIframe({ type: 'weagent-style', prop: 'height', value: 'auto' })
    },
    applyFloat(v) {
      this.styleDraft.float = v
      if (v === 'center') {
        this._postToIframe({ type: 'weagent-style', prop: 'display', value: 'block' })
        this._postToIframe({ type: 'weagent-style', prop: 'marginLeft', value: 'auto' })
        this._postToIframe({ type: 'weagent-style', prop: 'marginRight', value: 'auto' })
        this._postToIframe({ type: 'weagent-style', prop: 'float', value: 'none' })
      } else {
        this._postToIframe({ type: 'weagent-style', prop: 'float', value: v })
        this._postToIframe({ type: 'weagent-style', prop: 'marginLeft', value: '' })
        this._postToIframe({ type: 'weagent-style', prop: 'marginRight', value: '' })
      }
    },
    triggerReplaceImg() { this.$refs.replaceImgInput?.click() },
    replaceImage(e) {
      const file = e.target.files[0]; if (!file) return
      const r = new FileReader()
      r.onload = (ev) => { this._postToIframe({ type: 'weagent-img-replace', src: ev.target.result }); e.target.value = '' }
      r.readAsDataURL(file)
    },
    applyStyle(prop, value) {
      if (prop === 'borderWidth' || prop === 'borderColor') { this.applyBorder(); return }
      this._postToIframe({ type: 'weagent-style', prop, value })
    },
    applyBorder() { this._postToIframe({ type: 'weagent-style', prop: 'borderWidth', value: '',
      borderWidth: this.styleDraft.borderWidth, borderColor: this.styleDraft.borderColor }) },
    setAlign(v) { this.styleDraft.textAlign = v; this.applyStyle('textAlign', v) },
    applyText() { this.pushUndo(); this._postToIframe({ type: 'weagent-text', value: this.styleDraft.textContent }) },
  },
  beforeDestroy() { window.removeEventListener('message', this._msgHandler) },
}
</script>

<style scoped>
.fullscreen-overlay { position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);z-index:2000;display:flex;flex-direction:column; }
.fs-header { display:flex;align-items:center;gap:8px;padding:10px 16px;background:#1e293b;color:#fff;flex-shrink:0;position:relative;z-index:20; }
.fs-title { font-size:14px;font-weight:500;flex:1; }
.fs-actions { display:flex;gap:6px;align-items:center; }
.fs-actions .el-button-group .el-button--mini { font-size:11px;padding:4px 8px; }
.fs-body { flex:1;display:flex;overflow:hidden;position:relative; }

/* Layer tree */
.fs-layers { background:#f8f9fa;border-right:1px solid #e8eaed;display:flex;flex-direction:column;position:relative;flex-shrink:0;overflow:hidden; }
.layers-spacer { height:40px;flex-shrink:0;background:#f8f9fa;border-bottom:1px solid #e8eaed; }
.layers-scroll { flex:1;overflow-y:auto;padding:4px 0;min-height:100px; }
.layers-empty { padding:20px;text-align:center;color:#94a3b8;font-size:12px; }
.layers-resize { position:absolute;top:0;right:-3px;bottom:0;width:6px;cursor:col-resize;z-index:3; }
.layers-resize:hover { background:rgba(64,128,255,0.2); }
.layer-row { position:relative;display:flex;align-items:center;min-height:26px;font-size:12px; }
.layer-row.active { background:#e8f0fe; }
.layer-line { position:absolute;top:0;bottom:0;width:1px;border-left:1px dashed #d0d5dd;pointer-events:none; }
.layer-line.active { border-left-color:#4080ff;border-left-style:solid; }
.layer-toggle { width:16px;flex-shrink:0;cursor:pointer;color:#94a3b8;font-size:12px;text-align:center;z-index:1; }
.layer-toggle i { font-size:12px; }
.layer-toggle-empty { width:16px;flex-shrink:0; }
.layer-node { flex:1;padding:3px 6px;border-radius:4px;cursor:pointer;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;display:flex;align-items:center;gap:6px;z-index:1; }
.layer-node:hover { background:#e2e8f0; }
.layer-row.active .layer-node { background:#4080ff;color:#fff; }
.layer-row.active .layer-node .layer-tag { color:#fff; }
.layer-row.active .layer-node .layer-text { color:#fff; }
.layer-tag { color:#4080ff;font-weight:500;flex-shrink:0; }
.layer-text { color:#1e293b;font-size:12px;overflow:hidden;text-overflow:ellipsis; }

/* Preview */
.fs-preview { flex:1;background:#fff;min-width:0; }
.fs-iframe { width:100%;height:100%;display:block;border:none; }

/* Property panel */
.fs-panel { width:280px;min-width:280px;background:#f8f9fa;border-left:1px solid #e8eaed;display:flex;flex-direction:column;overflow:hidden; }
.panel-scroll { flex:1;overflow-y:auto;padding:8px 0; }
.panel-footer { padding:8px 14px;border-top:1px solid #e8eaed;background:#fff;flex-shrink:0; }
.panel-section { padding:8px 14px;border-bottom:1px solid #e8eaed; }
.section-title { font-size:11px;color:#94a3b8;font-weight:600;margin-bottom:6px;text-transform:uppercase;display:flex;align-items:center;gap:6px; }
.panel-close { color:#94a3b8;font-size:13px;padding:0;margin-left:auto; }
.prop-row { display:flex;align-items:center;gap:6px;margin-bottom:4px;font-size:12px; }
.prop-label { width:40px;color:#64748b;flex-shrink:0; }
.prop-val { color:#1e293b;font-weight:500;flex:1;overflow:hidden;text-overflow:ellipsis; }
.prop-input { width:60px;padding:2px 6px;border:1px solid #e2e8f0;border-radius:4px;font-size:12px;text-align:right;outline:none;background:#fff; }
.prop-input:focus { border-color:#4080ff; }
.prop-unit { color:#94a3b8;font-size:11px; }
.prop-color { width:28px;height:24px;border:1px solid #e2e8f0;border-radius:4px;padding:0;cursor:pointer; }
.prop-select { flex:1;padding:2px 4px;border:1px solid #e2e8f0;border-radius:4px;font-size:12px;background:#fff;outline:none; }
.align-group { display:flex;gap:2px; }
.align-group button { width:28px;height:24px;border:1px solid #e2e8f0;background:#fff;border-radius:4px;cursor:pointer;font-size:12px;color:#64748b;padding:0; }
.align-group button.on { background:#4080ff;color:#fff;border-color:#4080ff; }
.prop-text-row { flex-direction:column;align-items:stretch;gap:2px; }
.prop-textarea { width:100%;padding:4px 6px;border:1px solid #e2e8f0;border-radius:4px;font-size:12px;font-family:inherit;resize:vertical;outline:none;background:#fff; }
.prop-textarea:focus { border-color:#4080ff; }

/* Source editor */
.fs-editor { flex:1;display:flex;flex-direction:column;background:#fff; }
.fs-textarea { flex:1;background:#fff;color:#1e293b;border:none;padding:16px;font-family:'SF Mono','Fira Code','Consolas',monospace;font-size:13px;line-height:1.5;resize:none;outline:none;tab-size:2; }
.editor-actions { padding:8px 12px;background:#f8f9fa;display:flex;gap:8px;flex-shrink:0;border-top:1px solid #e8eaed;align-items:center; }
.editor-hint { font-size:12px;color:#f59e0b;flex:1; }
</style>
