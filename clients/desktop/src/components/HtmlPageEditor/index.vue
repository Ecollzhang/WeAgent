<template>
  <div v-if="embedded" class="he-embedded">
    <div class="he-layout">
      <div class="he-toolbar">
        <div class="he-toolbar-left">
          <el-tag size="small" type="success">HTML 编辑器</el-tag>
          <span class="he-filename">{{ fileName || 'index.html' }}</span>
          <span class="he-status">{{ mode === 'visual' ? '真实预览模式' : '源码模式' }}</span>
        </div>
        <div class="he-toolbar-right">
          <el-button-group>
            <el-button size="small" :type="mode === 'visual' ? 'primary' : 'default'" @click="switchMode('visual')">可视化</el-button>
            <el-button size="small" :type="mode === 'source' ? 'primary' : 'default'" @click="switchMode('source')">源码</el-button>
          </el-button-group>
          <el-button size="small" icon="el-icon-refresh-left" @click="undo" :disabled="mode !== 'visual' || undoStack.length === 0">撤销</el-button>
          <el-button size="small" icon="el-icon-refresh-right" @click="redo" :disabled="mode !== 'visual' || redoStack.length === 0">重做</el-button>
          <el-button size="small" type="primary" icon="el-icon-check" @click="savePage" :loading="saving">保存</el-button>
          <el-button size="small" icon="el-icon-close" @click="close">关闭</el-button>
        </div>
      </div>

      <div v-show="mode === 'visual'" class="he-body">
        <main class="he-preview">
          <div class="he-preview-bar">
            <span class="preview-hint">点击元素进行编辑，拖住左上角手柄可调整同级顺序</span>
            <span class="preview-meta">{{ selectedSummary }}</span>
          </div>
          <iframe
            ref="previewIframe"
            :srcdoc="visualHtml"
            class="he-iframe"
            sandbox="allow-scripts allow-same-origin"
          ></iframe>
        </main>

        <aside class="he-panel">
          <div class="panel-title">属性</div>
          <div class="panel-body">
            <template v-if="selectedEl">
              <div class="panel-section">
                <div class="section-title">元素信息</div>
                <div class="prop-row"><span class="prop-label">标签</span><span class="prop-value">&lt;{{ selectedEl.tag }}&gt;</span></div>
                <div class="prop-row" v-if="selectedEl.id"><span class="prop-label">ID</span><span class="prop-value">{{ selectedEl.id }}</span></div>
                <div class="prop-row" v-if="selectedEl.classes"><span class="prop-label">类</span><span class="prop-value">{{ selectedEl.classes }}</span></div>
              </div>

              <div class="panel-section" v-if="selectedEl.hasText && !selectedEl.isImg">
                <div class="section-title">文本内容</div>
                <el-input
                  type="textarea"
                  :rows="4"
                  v-model="styleDraft.textContent"
                  placeholder="输入文本内容"
                  @input="applyText"
                />
              </div>

              <div class="panel-section">
                <div class="section-title">尺寸与间距</div>
                <div class="prop-grid">
                  <div class="prop-item">
                    <span class="prop-label">宽度</span>
                    <el-input-number :value="styleDraft.width" :min="0" :step="4" controls-position="right" @change="handleWidthChange" />
                  </div>
                  <div class="prop-item">
                    <span class="prop-label">高度</span>
                    <el-input-number :value="styleDraft.height" :min="0" :step="4" controls-position="right" @change="handleHeightChange" />
                  </div>
                  <div class="prop-item">
                    <span class="prop-label">内边距</span>
                    <el-input-number :value="styleDraft.padding" :min="0" :step="4" controls-position="right" @change="handlePaddingChange" />
                  </div>
                  <div class="prop-item">
                    <span class="prop-label">外边距</span>
                    <el-input-number :value="styleDraft.margin" :min="0" :step="4" controls-position="right" @change="handleMarginChange" />
                  </div>
                </div>
              </div>

              <div class="panel-section" v-if="!selectedEl.isImg">
                <div class="section-title">文字</div>
                <div class="prop-grid">
                  <div class="prop-item">
                    <span class="prop-label">字号</span>
                    <el-input-number :value="styleDraft.fontSize" :min="8" :step="1" controls-position="right" @change="handleFontSizeChange" />
                  </div>
                  <div class="prop-item">
                    <span class="prop-label">对齐</span>
                    <el-select :value="styleDraft.textAlign" @change="handleTextAlignChange">
                      <el-option label="左对齐" value="left" />
                      <el-option label="居中" value="center" />
                      <el-option label="右对齐" value="right" />
                    </el-select>
                  </div>
                </div>
              </div>

              <div class="panel-section">
                <div class="section-title">外观</div>
                <div class="prop-grid">
                  <div class="prop-item">
                    <span class="prop-label">背景色</span>
                    <input class="color-input" type="color" :value="styleDraft.backgroundColor" @input="handleBackgroundColorInput" />
                  </div>
                  <div class="prop-item" v-if="!selectedEl.isImg">
                    <span class="prop-label">文字色</span>
                    <input class="color-input" type="color" :value="styleDraft.color" @input="handleTextColorInput" />
                  </div>
                  <div class="prop-item">
                    <span class="prop-label">圆角</span>
                    <el-input-number :value="styleDraft.borderRadius" :min="0" :step="2" controls-position="right" @change="handleBorderRadiusChange" />
                  </div>
                  <div class="prop-item">
                    <span class="prop-label">边框宽</span>
                    <el-input-number :value="styleDraft.borderWidth" :min="0" :step="1" controls-position="right" @change="handleBorderWidthChange" />
                  </div>
                  <div class="prop-item">
                    <span class="prop-label">边框色</span>
                    <input class="color-input" type="color" :value="styleDraft.borderColor" @input="handleBorderColorInput" />
                  </div>
                </div>
              </div>

              <div class="panel-section">
                <div class="section-title">组件操作</div>
                <div class="component-actions">
                  <el-button class="component-action-btn" @click="duplicateSelected">复制组件</el-button>
                  <el-button class="component-action-btn" type="danger" plain @click="removeSelected">删除组件</el-button>
                </div>
              </div>
            </template>

            <div v-else class="panel-empty">
              <i class="el-icon-crop" />
              <span>点击页面中的元素后，这里会显示它的属性。</span>
            </div>
          </div>
        </aside>
      </div>

      <div v-show="mode === 'source'" class="source-layout">
        <textarea
          v-model="sourceDraft"
          class="source-textarea"
          spellcheck="false"
          @input="sourceDirty = true"
        ></textarea>
        <div class="source-actions">
          <span class="source-hint" v-if="sourceDirty">源码已修改，返回可视化模式时会重新加载预览</span>
          <el-button size="small" type="primary" @click="applySource" :disabled="!sourceDirty">应用到预览</el-button>
          <el-button size="small" @click="resetSource">重置</el-button>
        </div>
      </div>
    </div>
  </div>
  <el-dialog
    v-else
    :visible.sync="dialogVisible"
    fullscreen
    :show-close="false"
    custom-class="html-editor-dialog"
    @closed="onDialogClosed"
  >
    <div class="he-layout">
      <div class="he-toolbar">
        <div class="he-toolbar-left">
          <el-tag size="small" type="success">HTML 编辑器</el-tag>
          <span class="he-filename">{{ fileName || 'index.html' }}</span>
          <span class="he-status">{{ mode === 'visual' ? '真实预览模式' : '源码模式' }}</span>
        </div>
        <div class="he-toolbar-right">
          <el-button-group>
            <el-button size="small" :type="mode === 'visual' ? 'primary' : 'default'" @click="switchMode('visual')">可视化</el-button>
            <el-button size="small" :type="mode === 'source' ? 'primary' : 'default'" @click="switchMode('source')">源码</el-button>
          </el-button-group>
          <el-button size="small" icon="el-icon-refresh-left" @click="undo" :disabled="mode !== 'visual' || undoStack.length === 0">撤销</el-button>
          <el-button size="small" icon="el-icon-refresh-right" @click="redo" :disabled="mode !== 'visual' || redoStack.length === 0">重做</el-button>
          <el-button size="small" type="primary" icon="el-icon-check" @click="savePage" :loading="saving">保存</el-button>
          <el-button size="small" icon="el-icon-close" @click="close">关闭</el-button>
        </div>
      </div>

      <div v-show="mode === 'visual'" class="he-body">
        <main class="he-preview">
          <div class="he-preview-bar">
            <span class="preview-hint">点击元素进行编辑，拖住左上角手柄可调整同级顺序</span>
            <span class="preview-meta">{{ selectedSummary }}</span>
          </div>
          <iframe
            ref="previewIframe"
            :srcdoc="visualHtml"
            class="he-iframe"
            sandbox="allow-scripts allow-same-origin"
          ></iframe>
        </main>

        <aside class="he-panel">
          <div class="panel-title">属性</div>
          <div class="panel-body">
            <template v-if="selectedEl">
              <div class="panel-section">
                <div class="section-title">元素信息</div>
                <div class="prop-row"><span class="prop-label">标签</span><span class="prop-value">&lt;{{ selectedEl.tag }}&gt;</span></div>
                <div class="prop-row" v-if="selectedEl.id"><span class="prop-label">ID</span><span class="prop-value">{{ selectedEl.id }}</span></div>
                <div class="prop-row" v-if="selectedEl.classes"><span class="prop-label">类</span><span class="prop-value">{{ selectedEl.classes }}</span></div>
              </div>

              <div class="panel-section" v-if="selectedEl.hasText && !selectedEl.isImg">
                <div class="section-title">文本内容</div>
                <el-input
                  type="textarea"
                  :rows="4"
                  v-model="styleDraft.textContent"
                  placeholder="输入文本内容"
                  @input="applyText"
                />
              </div>

              <div class="panel-section">
                <div class="section-title">尺寸与间距</div>
                <div class="prop-grid">
                  <div class="prop-item">
                    <span class="prop-label">宽度</span>
                    <el-input-number :value="styleDraft.width" :min="0" :step="4" controls-position="right" @change="handleWidthChange" />
                  </div>
                  <div class="prop-item">
                    <span class="prop-label">高度</span>
                    <el-input-number :value="styleDraft.height" :min="0" :step="4" controls-position="right" @change="handleHeightChange" />
                  </div>
                  <div class="prop-item">
                    <span class="prop-label">内边距</span>
                    <el-input-number :value="styleDraft.padding" :min="0" :step="4" controls-position="right" @change="handlePaddingChange" />
                  </div>
                  <div class="prop-item">
                    <span class="prop-label">外边距</span>
                    <el-input-number :value="styleDraft.margin" :min="0" :step="4" controls-position="right" @change="handleMarginChange" />
                  </div>
                </div>
              </div>

              <div class="panel-section" v-if="!selectedEl.isImg">
                <div class="section-title">文字</div>
                <div class="prop-grid">
                  <div class="prop-item">
                    <span class="prop-label">字号</span>
                    <el-input-number :value="styleDraft.fontSize" :min="8" :step="1" controls-position="right" @change="handleFontSizeChange" />
                  </div>
                  <div class="prop-item">
                    <span class="prop-label">对齐</span>
                    <el-select :value="styleDraft.textAlign" @change="handleTextAlignChange">
                      <el-option label="左对齐" value="left" />
                      <el-option label="居中" value="center" />
                      <el-option label="右对齐" value="right" />
                    </el-select>
                  </div>
                </div>
              </div>

              <div class="panel-section">
                <div class="section-title">外观</div>
                <div class="prop-grid">
                  <div class="prop-item">
                    <span class="prop-label">背景色</span>
                    <input class="color-input" type="color" :value="styleDraft.backgroundColor" @input="handleBackgroundColorInput" />
                  </div>
                  <div class="prop-item" v-if="!selectedEl.isImg">
                    <span class="prop-label">文字色</span>
                    <input class="color-input" type="color" :value="styleDraft.color" @input="handleTextColorInput" />
                  </div>
                  <div class="prop-item">
                    <span class="prop-label">圆角</span>
                    <el-input-number :value="styleDraft.borderRadius" :min="0" :step="2" controls-position="right" @change="handleBorderRadiusChange" />
                  </div>
                  <div class="prop-item">
                    <span class="prop-label">边框宽</span>
                    <el-input-number :value="styleDraft.borderWidth" :min="0" :step="1" controls-position="right" @change="handleBorderWidthChange" />
                  </div>
                  <div class="prop-item">
                    <span class="prop-label">边框色</span>
                    <input class="color-input" type="color" :value="styleDraft.borderColor" @input="handleBorderColorInput" />
                  </div>
                </div>
              </div>

              <div class="panel-section">
                <div class="section-title">组件操作</div>
                <div class="component-actions">
                  <el-button class="component-action-btn" @click="duplicateSelected">复制组件</el-button>
                  <el-button class="component-action-btn" type="danger" plain @click="removeSelected">删除组件</el-button>
                </div>
              </div>
            </template>

            <div v-else class="panel-empty">
              <i class="el-icon-crop" />
              <span>点击页面中的元素后，这里会显示它的属性。</span>
            </div>
          </div>
        </aside>
      </div>

      <div v-show="mode === 'source'" class="source-layout">
        <textarea
          v-model="sourceDraft"
          class="source-textarea"
          spellcheck="false"
          @input="sourceDirty = true"
        ></textarea>
        <div class="source-actions">
          <span class="source-hint" v-if="sourceDirty">源码已修改，返回可视化模式时会重新加载预览</span>
          <el-button size="small" type="primary" @click="applySource" :disabled="!sourceDirty">应用到预览</el-button>
          <el-button size="small" @click="resetSource">重置</el-button>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script>
import { writeFile } from '@/services/sandbox'

const INJECT_SCRIPT = `
(function(){
  var TOOLBAR_ID = 'weagent-light-toolbar';
  var STYLE_ID = 'weagent-light-style';
  var selected = null;
  var dragSource = null;
  var parentHighlight = null;

  function ensureStyle() {
    if (document.getElementById(STYLE_ID)) return;
    var style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent =
      '.weagent-selected{outline:2px solid #3b82f6 !important;outline-offset:2px !important;box-shadow:0 0 0 9999px rgba(59,130,246,0.08) inset !important;}' +
      '.weagent-selected::before{content:attr(data-weagent-label);position:absolute;top:-26px;left:0;z-index:2147483645;padding:3px 8px;border-radius:999px;background:#2563eb;color:#fff;font-size:11px;line-height:1.2;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;white-space:nowrap;box-shadow:0 4px 12px rgba(37,99,235,0.28);}' +
      '.weagent-parent-highlight{box-shadow:0 0 0 9999px rgba(59,130,246,0.04) inset !important;border-radius:10px;transition:box-shadow 0.15s ease;}' +
      '.weagent-drag-handle{position:absolute;top:6px;left:6px;z-index:2147483646;width:18px;height:18px;border-radius:6px;background:#0f172a;color:#fff;font-size:12px;display:flex;align-items:center;justify-content:center;cursor:grab;box-shadow:0 2px 8px rgba(15,23,42,0.35);}' +
      '.weagent-drag-target{outline:2px dashed #38bdf8 !important;outline-offset:3px !important;background-image:linear-gradient(180deg, rgba(56,189,248,0.14), rgba(56,189,248,0.06));}' +
      '.weagent-drag-target::after{content:attr(data-weagent-drop);position:absolute;right:10px;top:10px;z-index:2147483645;padding:4px 8px;border-radius:999px;background:#0f172a;color:#fff;font-size:11px;line-height:1.2;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;white-space:nowrap;box-shadow:0 4px 12px rgba(15,23,42,0.28);}' +
      '.weagent-toolbar{position:fixed;right:16px;bottom:16px;z-index:2147483647;display:flex;gap:8px;padding:10px 12px;background:rgba(15,23,42,0.94);color:#fff;border-radius:12px;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;box-shadow:0 12px 28px rgba(15,23,42,0.32);}' +
      '.weagent-toolbar button{border:none;border-radius:8px;padding:6px 10px;background:#1e293b;color:#fff;cursor:pointer;font-size:12px;}' +
      '.weagent-toolbar button:hover{background:#334155;}' +
      '.weagent-body-pad{padding-bottom:64px !important;}';
    document.head.appendChild(style);
  }

  function ensureToolbar() {
    if (document.getElementById(TOOLBAR_ID)) return;
    var toolbar = document.createElement('div');
    toolbar.id = TOOLBAR_ID;
    toolbar.className = 'weagent-toolbar';
    toolbar.innerHTML =
      '<button data-cmd="undo">撤销</button>' +
      '<button data-cmd="redo">重做</button>' +
      '<button data-cmd="sync">同步</button>';
    toolbar.addEventListener('click', function(e){
      var btn = e.target.closest('button');
      if (!btn) return;
      parent.postMessage({ type: 'weagent-' + btn.getAttribute('data-cmd') }, '*');
    });
    document.body.appendChild(toolbar);
    document.body.classList.add('weagent-body-pad');
  }

  function isIgnored(el) {
    return !el || el === document.body || el === document.documentElement || el.id === TOOLBAR_ID || (el.closest && el.closest('#' + TOOLBAR_ID));
  }

  function getPath(el) {
    var parts = [];
    while (el && el !== document.body && el !== document.documentElement) {
      if (isIgnored(el)) { el = el.parentElement; continue; }
      var tag = el.tagName.toLowerCase();
      if (el.id) { parts.unshift(tag + '#' + el.id); break; }
      var p = el.parentElement;
      if (p) {
        var sib = Array.prototype.filter.call(p.children, function(c){ return c.tagName === el.tagName; });
        parts.unshift(sib.length > 1 ? tag + ':nth-of-type(' + (sib.indexOf(el) + 1) + ')' : tag);
      } else {
        parts.unshift(tag);
      }
      el = p;
    }
    return parts.join('>');
  }

  function cleanSelection() {
    document.querySelectorAll('.weagent-selected').forEach(function(node){ node.classList.remove('weagent-selected'); });
    document.querySelectorAll('.weagent-drag-handle').forEach(function(node){ node.remove(); });
    document.querySelectorAll('[data-weagent-label]').forEach(function(node){ node.removeAttribute('data-weagent-label'); });
    if (parentHighlight) {
      parentHighlight.classList.remove('weagent-parent-highlight');
      parentHighlight = null;
    }
  }

  function findParentContainer(el) {
    var current = el ? el.parentElement : null;
    var blockTags = ['DIV', 'SECTION', 'ARTICLE', 'LI', 'UL', 'OL', 'HEADER', 'FOOTER', 'NAV', 'MAIN', 'ASIDE', 'FORM'];
    while (current && current !== document.body && current !== document.documentElement) {
      if (!isIgnored(current) && blockTags.indexOf(current.tagName) >= 0) return current;
      current = current.parentElement;
    }
    return null;
  }

  function readNumber(value) {
    var num = parseInt(value || '0', 10);
    return isNaN(num) ? 0 : num;
  }

  function toHex(color) {
    if (!color) return '#ffffff';
    if (String(color).indexOf('#') === 0) return color;
    var match = String(color).match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/i);
    if (!match) return '#ffffff';
    return '#' + [match[1], match[2], match[3]].map(function(part){
      return Number(part).toString(16).padStart(2, '0');
    }).join('');
  }

  function getEditableText(el) {
    if (!el) return '';
    var clone = el.cloneNode(true);
    clone.querySelectorAll('.weagent-drag-handle').forEach(function(node){ node.remove(); });
    return clone.textContent || '';
  }

  function canEditText(el) {
    if (!el || el.tagName === 'IMG') return false;
    return true;
  }

  function emitSelection(el) {
    var textValue = getEditableText(el);
    var cs = getComputedStyle(el);
      parent.postMessage({
        type: 'weagent-select',
        path: getPath(el),
        tag: el.tagName.toLowerCase(),
        id: el.id || '',
        classes: Array.from(el.classList || []).filter(function(name){ return name !== 'weagent-selected' && name !== 'weagent-drag-target'; }).join(' '),
        hasText: canEditText(el),
        isImg: el.tagName === 'IMG',
        textContent: textValue,
        styles: {
        width: readNumber(cs.width),
        height: readNumber(cs.height),
        padding: readNumber(cs.paddingTop),
        margin: readNumber(cs.marginTop),
        fontSize: readNumber(cs.fontSize),
        textAlign: cs.textAlign || 'left',
        backgroundColor: toHex(cs.backgroundColor),
        color: toHex(cs.color),
        borderRadius: readNumber(cs.borderRadius),
        borderWidth: readNumber(cs.borderWidth),
        borderColor: toHex(cs.borderColor)
      }
    }, '*');
  }

  function syncHtml() {
    parent.postMessage({ type: 'weagent-sync', html: document.documentElement.outerHTML }, '*');
  }

  function addHandle(el) {
    if (!el || !el.parentElement || isIgnored(el) || el.querySelector('.weagent-drag-handle')) return;
    var position = getComputedStyle(el).position;
    if (!position || position === 'static') el.style.position = 'relative';
    var handle = document.createElement('span');
    handle.className = 'weagent-drag-handle';
    handle.textContent = '⋮⋮';
    handle.draggable = true;
    handle.addEventListener('dragstart', function(e){
      dragSource = el;
      e.dataTransfer.effectAllowed = 'move';
      parent.postMessage({ type: 'weagent-push-undo', html: document.documentElement.outerHTML }, '*');
    });
    handle.addEventListener('dragend', function(){
      dragSource = null;
      document.querySelectorAll('.weagent-drag-target').forEach(function(node){ node.classList.remove('weagent-drag-target'); });
    });
    el.insertBefore(handle, el.firstChild);
    el.addEventListener('dragover', function(e){
      if (!dragSource || dragSource === el || dragSource.parentElement !== el.parentElement) return;
      e.preventDefault();
      el.classList.add('weagent-drag-target');
      var rect = el.getBoundingClientRect();
      var before = e.clientY < rect.top + rect.height / 2;
      el.setAttribute('data-weagent-drop', before ? '插入到前面' : '插入到后面');
    });
    el.addEventListener('dragleave', function(){
      el.classList.remove('weagent-drag-target');
      el.removeAttribute('data-weagent-drop');
    });
    el.addEventListener('drop', function(e){
      if (!dragSource || dragSource === el || dragSource.parentElement !== el.parentElement) return;
      e.preventDefault();
      el.classList.remove('weagent-drag-target');
      el.removeAttribute('data-weagent-drop');
      var rect = el.getBoundingClientRect();
      var before = e.clientY < rect.top + rect.height / 2;
      if (before) el.parentElement.insertBefore(dragSource, el);
      else el.parentElement.insertBefore(dragSource, el.nextSibling);
      selectElement(dragSource);
      syncHtml();
    });
  }

  function selectElement(el) {
    if (!el || isIgnored(el)) return;
    cleanSelection();
    selected = el;
    el.classList.add('weagent-selected');
    var label = el.tagName.toLowerCase();
    if (el.id) label += '#' + el.id;
    else if (el.classList && el.classList.length) label += '.' + Array.from(el.classList).slice(0, 2).join('.');
    el.setAttribute('data-weagent-label', label);
    parentHighlight = findParentContainer(el);
    if (parentHighlight) parentHighlight.classList.add('weagent-parent-highlight');
    addHandle(el);
    emitSelection(el);
  }

  document.addEventListener('click', function(e){
    var target = e.target;
    if (target.closest && target.closest('#' + TOOLBAR_ID)) return;
    if (target.classList && target.classList.contains('weagent-drag-handle')) return;
    if (isIgnored(target)) return;
    e.preventDefault();
    e.stopPropagation();
    selectElement(target);
  }, true);

  window.addEventListener('message', function(e){
    var d = e.data || {};
    if (d.type === 'weagent-apply-style' && selected) {
      selected.style[d.prop] = d.value;
      emitSelection(selected);
      syncHtml();
    } else if (d.type === 'weagent-apply-text' && selected && selected.tagName !== 'IMG') {
      selected.textContent = d.value || '';
      emitSelection(selected);
      syncHtml();
    } else if (d.type === 'weagent-duplicate-selected' && selected && selected.parentElement) {
      parent.postMessage({ type: 'weagent-push-undo', html: document.documentElement.outerHTML }, '*');
      var clone = selected.cloneNode(true);
      clone.querySelectorAll('.weagent-drag-handle').forEach(function(node){ node.remove(); });
      clone.classList.remove('weagent-selected');
      clone.classList.remove('weagent-drag-target');
      clone.removeAttribute('data-weagent-label');
      clone.removeAttribute('data-weagent-drop');
      selected.parentElement.insertBefore(clone, selected.nextSibling);
      selectElement(clone);
      syncHtml();
    } else if (d.type === 'weagent-remove-selected' && selected && selected.parentElement) {
      parent.postMessage({ type: 'weagent-push-undo', html: document.documentElement.outerHTML }, '*');
      var next = selected.nextElementSibling || selected.previousElementSibling || selected.parentElement;
      selected.remove();
      selected = null;
      cleanSelection();
      if (next && !isIgnored(next) && next !== document.body && next !== document.documentElement) {
        selectElement(next);
      } else {
        parent.postMessage({ type: 'weagent-select', path: '', tag: '', id: '', classes: '', hasText: false, isImg: false, textContent: '', styles: {} }, '*');
      }
      syncHtml();
    } else if (d.type === 'weagent-select-path' && d.path) {
      var target = document.querySelector(d.path);
      if (target) selectElement(target);
    }
  });

  ensureStyle();
  ensureToolbar();
})();
`;

function parsePx(value, fallback = 0) {
  const num = parseInt(String(value || ''), 10)
  return Number.isFinite(num) ? num : fallback
}

function buildVisualHtml(source, baseHref) {
  const html = String(source || '')
  const scriptTag = `<script>${INJECT_SCRIPT}<\/script>`
  const baseTag = baseHref ? `<base href="${baseHref}">` : ''
  let output = html

  if (/<head[^>]*>/i.test(output)) {
    output = output.replace(/<head([^>]*)>/i, `<head$1>${baseTag}`)
  } else if (/<html[^>]*>/i.test(output)) {
    output = output.replace(/<html([^>]*)>/i, `<html$1><head>${baseTag}</head>`)
  } else {
    output = `<!DOCTYPE html><html><head>${baseTag}</head><body>${output}</body></html>`
  }

  if (/<\/body>/i.test(output)) {
    output = output.replace(/<\/body>/i, `${scriptTag}</body>`)
  } else {
    output += scriptTag
  }

  return output
}

function stripEditorArtifacts(html) {
  let output = String(html || '')
  output = output.replace(/<script>\s*\(function\(\)\{[\s\S]*?ensureToolbar\(\);\s*\}\)\(\);\s*<\/script>/i, '')
  output = output.replace(/<base href="[^"]*">/i, '')
  output = output.replace(/\sweagent-selected/g, '')
  output = output.replace(/\sweagent-drag-target/g, '')
  output = output.replace(/<span class="weagent-drag-handle"[\s\S]*?<\/span>/gi, '')
  output = output.replace(/<div id="weagent-light-toolbar"[\s\S]*?<\/div>/gi, '')
  output = output.replace(/\sclass="([^"]*?)\sweagent-body-pad([^"]*?)"/gi, ' class="$1$2"')
  output = output.replace(/\sclass="weagent-body-pad"/gi, '')
  output = output.replace(/\sstyle="([^"]*?)position:\s*relative;?([^"]*?)"/gi, (match, before, after) => {
    const merged = `${before || ''}${after || ''}`.trim()
    return merged ? ` style="${merged}"` : ''
  })
  output = output.replace(/\sdata-weagent-[^=]+="[^"]*"/gi, '')
  return output
}

export default {
  name: 'DesktopHtmlPageEditor',
  props: {
    visible: { type: Boolean, default: false },
    content: { type: String, default: '' },
    fileName: { type: String, default: 'index.html' },
    filePath: { type: String, default: '' },
    sessionId: { type: String, default: '' },
    embedded: { type: Boolean, default: false },
    baseHref: { type: String, default: '' },
  },
  data() {
    return {
      dialogVisible: this.visible,
      mode: 'visual',
      saving: false,
      original: '',
      sourceDraft: '',
      sourceDirty: false,
      visualHtml: '',
      selectedEl: null,
      selectedPath: '',
      styleDraft: {
        textContent: '',
        width: 0,
        height: 0,
        padding: 0,
        margin: 0,
        fontSize: 16,
        textAlign: 'left',
        backgroundColor: '#ffffff',
        color: '#111827',
        borderRadius: 0,
        borderWidth: 0,
        borderColor: '#d1d5db',
      },
      undoStack: [],
      redoStack: [],
      messageHandler: null,
    }
  },
  computed: {
    selectedSummary() {
      if (!this.selectedEl) return '未选中元素'
      return `<${this.selectedEl.tag}> ${this.selectedEl.id ? '#' + this.selectedEl.id : ''}`.trim()
    },
  },
  watch: {
    visible(v) {
      this.dialogVisible = v
      if ((v || this.embedded) && (v || this.dialogVisible || this.embedded)) this.resetEditor()
    },
    dialogVisible(v) {
      if (!v && !this.embedded) this.$emit('update:visible', false)
    },
    content() {
      if (this.embedded || this.dialogVisible) this.resetEditor()
    },
  },
  mounted() {
    if (this.visible || this.embedded) this.resetEditor()
  },
  methods: {
    workspaceBaseHref() {
      if (this.baseHref) return this.baseHref
      if (!this.sessionId || !this.filePath) return ''
      const normalized = String(this.filePath).replace(/\\/g, '/').replace(/^\/?workspace\//, '')
      const parts = normalized.split('/')
      parts.pop()
      const encodedDir = parts.map(part => encodeURIComponent(part)).join('/')
      return encodedDir
        ? `/api/sandbox/sessions/${encodeURIComponent(this.sessionId)}/workspace/${encodedDir}/`
        : `/api/sandbox/sessions/${encodeURIComponent(this.sessionId)}/workspace/`
    },
    resetEditor() {
      this.original = this.content || ''
      this.sourceDraft = this.content || ''
      this.sourceDirty = false
      this.mode = 'visual'
      this.selectedEl = null
      this.selectedPath = ''
      this.undoStack = []
      this.redoStack = []
      this.visualHtml = buildVisualHtml(this.sourceDraft, this.workspaceBaseHref())
      this.bindMessageHandler()
    },
    bindMessageHandler() {
      if (this.messageHandler) {
        window.removeEventListener('message', this.messageHandler)
      }
      this.messageHandler = event => {
        const data = event.data || {}
        if (data.type === 'weagent-select') {
          if (!data.tag) {
            this.selectedEl = null
            this.selectedPath = ''
            return
          }
          this.selectedEl = {
            tag: data.tag,
            id: data.id,
            classes: data.classes,
            hasText: data.hasText,
            isImg: data.isImg,
          }
          this.selectedPath = data.path || ''
          const styles = data.styles || {}
          this.styleDraft = {
            ...this.styleDraft,
            textContent: data.textContent || '',
            width: parsePx(styles.width),
            height: parsePx(styles.height),
            padding: parsePx(styles.padding),
            margin: parsePx(styles.margin),
            fontSize: parsePx(styles.fontSize, 16),
            textAlign: styles.textAlign || 'left',
            backgroundColor: styles.backgroundColor || '#ffffff',
            color: styles.color || '#111827',
            borderRadius: parsePx(styles.borderRadius),
            borderWidth: parsePx(styles.borderWidth),
            borderColor: styles.borderColor || '#d1d5db',
          }
        } else if (data.type === 'weagent-sync') {
          const cleaned = stripEditorArtifacts(data.html || '')
          this.sourceDraft = cleaned
          this.sourceDirty = false
        } else if (data.type === 'weagent-push-undo') {
          this.pushUndo(data.html || this.sourceDraft)
        } else if (data.type === 'weagent-undo') {
          this.undo()
        } else if (data.type === 'weagent-redo') {
          this.redo()
        }
      }
      window.addEventListener('message', this.messageHandler)
    },
    pushUndo(html) {
      this.undoStack.push(stripEditorArtifacts(html))
      if (this.undoStack.length > 50) this.undoStack.shift()
      this.redoStack = []
    },
    postToIframe(payload) {
      const iframe = this.$refs.previewIframe
      if (iframe && iframe.contentWindow) {
        iframe.contentWindow.postMessage(payload, '*')
      }
    },
    applyStyle(prop, value) {
      if (!this.selectedEl) return
      this.postToIframe({ type: 'weagent-apply-style', prop, value })
    },
    applyText() {
      if (!this.selectedEl || this.selectedEl.isImg) return
      this.postToIframe({ type: 'weagent-apply-text', value: this.styleDraft.textContent })
    },
    duplicateSelected() {
      if (!this.selectedEl) return
      this.postToIframe({ type: 'weagent-duplicate-selected' })
    },
    removeSelected() {
      if (!this.selectedEl) return
      this.postToIframe({ type: 'weagent-remove-selected' })
    },
    handleWidthChange(value) {
      this.styleDraft.width = Number(value) || 0
      this.applyStyle('width', `${this.styleDraft.width}px`)
    },
    handleHeightChange(value) {
      this.styleDraft.height = Number(value) || 0
      this.applyStyle('height', `${this.styleDraft.height}px`)
    },
    handlePaddingChange(value) {
      this.styleDraft.padding = Number(value) || 0
      this.applyStyle('padding', `${this.styleDraft.padding}px`)
    },
    handleMarginChange(value) {
      this.styleDraft.margin = Number(value) || 0
      this.applyStyle('margin', `${this.styleDraft.margin}px`)
    },
    handleFontSizeChange(value) {
      this.styleDraft.fontSize = Number(value) || 16
      this.applyStyle('fontSize', `${this.styleDraft.fontSize}px`)
    },
    handleTextAlignChange(value) {
      this.styleDraft.textAlign = value
      this.applyStyle('textAlign', value)
    },
    handleBackgroundColorInput(event) {
      this.styleDraft.backgroundColor = event.target.value
      this.applyStyle('backgroundColor', event.target.value)
    },
    handleTextColorInput(event) {
      this.styleDraft.color = event.target.value
      this.applyStyle('color', event.target.value)
    },
    handleBorderRadiusChange(value) {
      this.styleDraft.borderRadius = Number(value) || 0
      this.applyStyle('borderRadius', `${this.styleDraft.borderRadius}px`)
    },
    handleBorderWidthChange(value) {
      this.styleDraft.borderWidth = Number(value) || 0
      this.applyStyle('borderWidth', `${this.styleDraft.borderWidth}px`)
      this.applyStyle('borderStyle', this.styleDraft.borderWidth > 0 ? 'solid' : 'none')
    },
    handleBorderColorInput(event) {
      this.styleDraft.borderColor = event.target.value
      this.applyStyle('borderColor', event.target.value)
    },
    switchMode(nextMode) {
      if (nextMode === this.mode) return
      if (nextMode === 'source') {
        this.sourceDirty = false
      } else if (this.sourceDirty) {
        this.applySource()
        return
      } else {
        this.visualHtml = buildVisualHtml(this.sourceDraft, this.workspaceBaseHref())
      }
      this.mode = nextMode
    },
    applySource() {
      this.visualHtml = buildVisualHtml(this.sourceDraft, this.workspaceBaseHref())
      this.sourceDirty = false
      this.mode = 'visual'
    },
    resetSource() {
      this.sourceDraft = this.original
      this.sourceDirty = false
    },
    undo() {
      if (this.undoStack.length === 0) return
      const current = this.sourceDraft
      const prev = this.undoStack.pop()
      this.redoStack.push(current)
      this.sourceDraft = prev
      this.visualHtml = buildVisualHtml(prev, this.workspaceBaseHref())
    },
    redo() {
      if (this.redoStack.length === 0) return
      const current = this.sourceDraft
      const next = this.redoStack.pop()
      this.undoStack.push(current)
      this.sourceDraft = next
      this.visualHtml = buildVisualHtml(next, this.workspaceBaseHref())
    },
    async savePage() {
      if (!this.filePath || !this.sessionId) {
        this.$message.warning('缺少文件路径或会话 ID')
        return
      }
      this.saving = true
      try {
        const html = this.sourceDraft
        await writeFile(this.sessionId, this.filePath, html)
        this.original = html
        this.sourceDirty = false
        this.$message.success('页面已保存')
        this.$emit('saved', { path: this.filePath, content: html })
        if (this.embedded) this.$emit('close-request')
        else this.dialogVisible = false
      } catch (e) {
        this.$message.error('保存失败: ' + (e.message || ''))
      } finally {
        this.saving = false
      }
    },
    close() {
      const closeEditor = () => {
        if (this.embedded) this.$emit('close-request')
        else this.dialogVisible = false
      }
      if (this.sourceDraft !== this.original) {
        this.$confirm('内容已修改，是否放弃更改？', '提示', {
          confirmButtonText: '放弃',
          cancelButtonText: '继续编辑',
          type: 'warning',
        }).then(() => {
          closeEditor()
        }).catch(() => {})
        return
      }
      closeEditor()
    },
    onDialogClosed() {
      if (this.messageHandler) {
        window.removeEventListener('message', this.messageHandler)
        this.messageHandler = null
      }
      this.selectedEl = null
      this.selectedPath = ''
    },
  },
}
</script>

<style scoped>
.he-embedded {
  height: 100%;
}

:deep(.html-editor-dialog .el-dialog) {
  margin-top: 0 !important;
}

:deep(.html-editor-dialog .el-dialog__header) {
  display: none;
}

:deep(.html-editor-dialog .el-dialog__body) {
  padding: 0;
}

.he-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f6f8fc;
}

.he-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 16px;
  background: rgba(255, 255, 255, 0.96);
  border-bottom: 1px solid #dbe3f0;
  flex-shrink: 0;
}

.he-toolbar-left,
.he-toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.he-filename {
  color: #0f172a;
  font-size: 14px;
  font-weight: 600;
}

.he-status {
  font-size: 12px;
  color: #64748b;
}

.he-body {
  flex: 1;
  min-height: 0;
  display: flex;
  overflow: hidden;
}

.he-preview {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(circle at top, rgba(59, 130, 246, 0.12), transparent 28%),
    linear-gradient(180deg, #f8fbff 0%, #edf3fb 100%);
}

.he-preview-bar {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border-bottom: 1px solid #dbe3f0;
  color: #334155;
  font-size: 12px;
  background: rgba(255, 255, 255, 0.72);
}

.preview-hint {
  color: #2563eb;
}

.preview-meta {
  color: #64748b;
}

.he-iframe {
  flex: 1;
  width: 100%;
  border: none;
  background: #fff;
}

.he-panel {
  width: 320px;
  background: #ffffff;
  border-left: 1px solid #dbe3f0;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.panel-title {
  padding: 12px 14px;
  font-size: 12px;
  font-weight: 700;
  color: #334155;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  border-bottom: 1px solid #e5edf7;
  background: #f8fbff;
}

.panel-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.panel-section {
  padding: 12px;
  border: 1px solid #dbe6f3;
  border-radius: 14px;
  background: linear-gradient(180deg, #ffffff, #f8fbff);
  box-shadow: 0 8px 24px rgba(148, 163, 184, 0.08);
}

.section-title {
  margin-bottom: 10px;
  font-size: 12px;
  font-weight: 700;
  color: #0f172a;
}

.prop-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 6px;
}

.prop-label {
  width: 52px;
  flex-shrink: 0;
  font-size: 12px;
  color: #64748b;
}

.prop-value {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  color: #0f172a;
  word-break: break-all;
}

.prop-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.prop-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.color-input {
  width: 100%;
  height: 36px;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  background: #fff;
  padding: 4px;
  cursor: pointer;
}

.component-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.component-action-btn {
  width: 100%;
}

.panel-empty {
  height: 100%;
  min-height: 220px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #64748b;
  text-align: center;
  line-height: 1.7;
}

.panel-empty i {
  font-size: 30px;
  color: #3b82f6;
}

.source-layout {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #f6f8fc;
}

.source-textarea {
  flex: 1;
  min-height: 0;
  border: none;
  outline: none;
  resize: none;
  padding: 18px 20px;
  background: #ffffff;
  color: #0f172a;
  font-size: 13px;
  line-height: 1.6;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
}

.source-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-top: 1px solid #dbe3f0;
  background: rgba(255, 255, 255, 0.96);
}

.source-hint {
  flex: 1;
  color: #b45309;
  font-size: 12px;
}

.panel-body :deep(.el-input__inner),
.panel-body :deep(.el-input-number__decrease),
.panel-body :deep(.el-input-number__increase),
.panel-body :deep(.el-textarea__inner),
.panel-body :deep(.el-select .el-input__inner) {
  background: #ffffff;
  border-color: #cbd5e1;
  color: #0f172a;
  border-radius: 10px;
}

.panel-body :deep(.el-input-number),
.panel-body :deep(.el-select) {
  width: 100%;
}

.panel-body :deep(.el-input-number__decrease),
.panel-body :deep(.el-input-number__increase) {
  background: #f8fbff;
  color: #64748b;
}
</style>
