<template>
  <section class="structured-editor">
    <header class="editor-caption">
      <div>
        <b>{{ title }}</b>
        <span>结构化文本编辑 · 排版操作会保留为可解析的纯文本</span>
      </div>
      <el-tag size="mini" effect="plain">教案字段</el-tag>
    </header>
    <div class="structured-toolbar" role="toolbar" :aria-label="`${title}编辑工具`">
      <el-button-group>
        <el-button size="mini" icon="el-icon-refresh-left" title="撤销" @click="undo" />
        <el-button size="mini" icon="el-icon-refresh-right" title="重做" @click="redo" />
      </el-button-group>
      <el-button-group>
        <el-button size="mini" icon="el-icon-tickets" @click="prefixLines('ordered')">编号</el-button>
        <el-button size="mini" icon="el-icon-menu" @click="prefixLines('bullet')">项目符号</el-button>
      </el-button-group>
      <el-button-group>
        <el-button size="mini" icon="el-icon-d-arrow-left" @click="indentLines(-1)">减少缩进</el-button>
        <el-button size="mini" icon="el-icon-d-arrow-right" @click="indentLines(1)">增加缩进</el-button>
      </el-button-group>
      <el-button size="mini" icon="el-icon-brush" @click="clearTextFormatting">清除格式</el-button>
      <el-select v-model="readingSize" size="mini" class="reading-size" aria-label="阅读字号">
        <el-option label="小字号" value="14" />
        <el-option label="标准字号" value="16" />
        <el-option label="大字号" value="18" />
        <el-option label="特大字号" value="21" />
      </el-select>
    </div>
    <textarea
      ref="textarea"
      class="editor-surface"
      :style="{ fontSize: `${readingSize}px` }"
      :value="value"
      :placeholder="placeholder"
      @input="handleInput"
    />
    <footer class="editor-footer">
      <span><kbd>Ctrl</kbd>/<kbd>⌘</kbd> + <kbd>S</kbd> 保存课时版本</span>
      <span>{{ value.length }} 字符</span>
    </footer>
  </section>
</template>

<script>
export default {
  name: 'StructuredTextEditor',
  props: {
    value: { type: String, default: '' },
    title: { type: String, required: true },
    placeholder: { type: String, default: '' },
  },
  data() {
    return {
      readingSize: '16',
      history: [this.value],
      historyIndex: 0,
    }
  },
  watch: {
    value(next) {
      if (this.history[this.historyIndex] !== next) this.record(next)
    },
  },
  methods: {
    record(value) {
      this.history = this.history.slice(0, this.historyIndex + 1)
      this.history.push(value)
      this.historyIndex = this.history.length - 1
    },
    emitValue(value) {
      this.$emit('input', value)
      this.$nextTick(() => this.$refs.textarea && this.$refs.textarea.focus())
    },
    handleInput(event) {
      const value = event.target.value
      this.record(value)
      this.$emit('input', value)
    },
    undo() {
      if (this.historyIndex <= 0) return
      this.historyIndex -= 1
      this.emitValue(this.history[this.historyIndex])
    },
    redo() {
      if (this.historyIndex >= this.history.length - 1) return
      this.historyIndex += 1
      this.emitValue(this.history[this.historyIndex])
    },
    transformSelectedLines(transformer) {
      const textarea = this.$refs.textarea
      if (!textarea) return
      const start = textarea.selectionStart
      const end = textarea.selectionEnd
      const lineStart = this.value.lastIndexOf('\n', Math.max(0, start - 1)) + 1
      const nextBreak = this.value.indexOf('\n', end)
      const lineEnd = nextBreak < 0 ? this.value.length : nextBreak
      const selected = this.value.slice(lineStart, lineEnd)
      const transformed = transformer(selected.split('\n')).join('\n')
      const next = this.value.slice(0, lineStart) + transformed + this.value.slice(lineEnd)
      this.record(next)
      this.$emit('input', next)
    },
    prefixLines(kind) {
      this.transformSelectedLines(lines => lines.map((line, index) => {
        const clean = line.replace(/^\s*(?:[-•]\s+|\d+[.、]\s*)/, '')
        return kind === 'ordered' ? `${index + 1}. ${clean}` : `• ${clean}`
      }))
    },
    indentLines(direction) {
      this.transformSelectedLines(lines => lines.map(line => (
        direction > 0 ? `  ${line}` : line.replace(/^ {1,2}/, '')
      )))
    },
    clearTextFormatting() {
      this.transformSelectedLines(lines => lines.map(line => (
        line.replace(/^\s*(?:[-•]\s+|\d+[.、]\s*)/, '')
      )))
    },
  },
}
</script>

<style scoped>
.structured-editor { overflow: hidden; border: 1px solid #d7e1e5; border-radius: 12px; background: #fff; box-shadow: 0 10px 28px rgba(36, 67, 73, .08); }
.editor-caption { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 13px 16px; border-bottom: 1px solid #e5ecef; background: linear-gradient(90deg, #f5faf8, #fbfcfd); }
.editor-caption b, .editor-caption span { display: block; }
.editor-caption b { color: #24434a; font-size: 14px; }
.editor-caption span { margin-top: 3px; color: #73828c; font-size: 11px; }
.structured-toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 8px 12px; border-bottom: 1px solid #dfe7ea; background: #f8fafb; }
.reading-size { width: 112px; margin-left: auto; }
.editor-surface { box-sizing: border-box; width: 100%; min-height: 52vh; padding: 24px 28px; border: 0; outline: none; resize: vertical; background: #fff; color: #334155; font-family: "Microsoft YaHei", "Noto Sans SC", sans-serif; line-height: 1.85; }
.editor-footer { display: flex; justify-content: space-between; padding: 9px 14px; border-top: 1px solid #e8eef0; color: #80909a; font-size: 11px; }
kbd { padding: 1px 4px; border: 1px solid #ccd7dc; border-radius: 3px; background: #f7f9fa; color: #53636d; font-family: inherit; }
</style>
