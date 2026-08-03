<template>
  <div class="comment-editor">
    <!-- Toolbar -->
    <div class="editor-toolbar">
      <el-tooltip content="加粗" placement="top">
        <button
          type="button"
          class="toolbar-btn"
          @click="insertMarkdown('bold')"
        >
          <strong>B</strong>
        </button>
      </el-tooltip>
      <el-tooltip content="行内代码" placement="top">
        <button
          type="button"
          class="toolbar-btn"
          @click="insertMarkdown('code')"
        >
          <i class="el-icon-document-copy"></i>
        </button>
      </el-tooltip>
      <el-tooltip content="无序列表" placement="top">
        <button
          type="button"
          class="toolbar-btn"
          @click="insertMarkdown('list')"
        >
          <i class="el-icon-tickets"></i>
        </button>
      </el-tooltip>
      <el-tooltip content="有序列表" placement="top">
        <button
          type="button"
          class="toolbar-btn"
          @click="insertMarkdown('ordered-list')"
        >
          <i class="el-icon-s-operation"></i>
        </button>
      </el-tooltip>
      <el-tooltip content="链接" placement="top">
        <button
          type="button"
          class="toolbar-btn"
          @click="insertMarkdown('link')"
        >
          <i class="el-icon-link"></i>
        </button>
      </el-tooltip>
    </div>

    <!-- Textarea -->
    <textarea
      ref="textarea"
      v-model="localValue"
      :placeholder="placeholder"
      class="editor-textarea"
      @input="handleInput"
      @keydown.ctrl.enter="handleSubmit"
    ></textarea>

    <!-- Footer -->
    <div class="editor-footer">
      <span class="char-count">{{ localValue.length }} 字符</span>
      <div class="editor-actions">
        <el-button
          v-if="showCancel"
          size="small"
          plain
          @click="handleCancel"
        >取消</el-button>
        <el-button
          type="primary"
          size="small"
          :disabled="!localValue.trim()"
          @click="handleSubmit"
        >提交</el-button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CommentEditor',
  props: {
    value: {
      type: String,
      default: '',
    },
    placeholder: {
      type: String,
      default: '输入评论内容...',
    },
    showCancel: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      localValue: this.value || '',
    }
  },
  watch: {
    value(val) {
      if (val !== this.localValue) {
        this.localValue = val || ''
      }
    },
  },
  methods: {
    handleInput() {
      this.$emit('input', this.localValue)
      this.autoResize()
    },
    autoResize() {
      this.$nextTick(() => {
        const textarea = this.$refs.textarea
        if (textarea) {
          textarea.style.height = 'auto'
          textarea.style.height = textarea.scrollHeight + 'px'
        }
      })
    },
    insertMarkdown(type) {
      const textarea = this.$refs.textarea
      if (!textarea) return

      const start = textarea.selectionStart
      const end = textarea.selectionEnd
      const selectedText = this.localValue.substring(start, end)
      let insertion = ''
      let cursorOffset = 0

      switch (type) {
        case 'bold':
          if (selectedText) {
            insertion = `**${selectedText}**`
          } else {
            insertion = '**加粗文本**'
            cursorOffset = -2
          }
          break
        case 'code':
          if (selectedText) {
            insertion = `\`${selectedText}\``
          } else {
            insertion = '`代码`'
            cursorOffset = -1
          }
          break
        case 'list':
          insertion = selectedText
            ? selectedText.split('\n').map(line => `- ${line}`).join('\n')
            : `- 列表项\n- 列表项`
          break
        case 'ordered-list':
          insertion = selectedText
            ? selectedText.split('\n').map((line, i) => `${i + 1}. ${line}`).join('\n')
            : `1. 列表项\n2. 列表项`
          break
        case 'link':
          if (selectedText) {
            insertion = `[${selectedText}](url)`
            cursorOffset = -4
          } else {
            insertion = '[链接文本](url)'
            cursorOffset = -4
          }
          break
        default:
          break
      }

      this.localValue =
        this.localValue.substring(0, start) +
        insertion +
        this.localValue.substring(end)
      this.$emit('input', this.localValue)

      this.$nextTick(() => {
        const pos = start + insertion.length + cursorOffset
        textarea.selectionStart = pos
        textarea.selectionEnd = pos
        textarea.focus()
        this.autoResize()
      })
    },
    handleSubmit() {
      const content = this.localValue.trim()
      if (!content) return
      this.$emit('submit', content)
      this.localValue = ''
      this.$emit('input', '')
    },
    handleCancel() {
      this.$emit('cancel')
    },
  },
  mounted() {
    this.autoResize()
  },
}
</script>

<style scoped>
.comment-editor {
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
  transition: border-color 0.2s;
}

.comment-editor:focus-within {
  border-color: #4080ff;
}

.editor-toolbar {
  display: flex;
  gap: 2px;
  padding: 6px 8px;
  background: #f5f7fa;
  border-bottom: 1px solid #ebeef5;
}

.toolbar-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 4px;
  background: transparent;
  cursor: pointer;
  color: #606266;
  font-size: 13px;
  transition: all 0.2s;
}

.toolbar-btn:hover {
  background: #e8eaef;
  color: #4080ff;
}

.toolbar-btn i {
  font-size: 14px;
}

.editor-textarea {
  display: block;
  width: 100%;
  min-height: 80px;
  padding: 10px 12px;
  border: none;
  outline: none;
  resize: none;
  font-size: 14px;
  color: #303133;
  line-height: 1.6;
  font-family: inherit;
  box-sizing: border-box;
  overflow: hidden;
}

.editor-textarea::placeholder {
  color: #c0c4cc;
}

.editor-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background: #fafafa;
  border-top: 1px solid #ebeef5;
}

.char-count {
  font-size: 12px;
  color: #909399;
}

.editor-actions {
  display: flex;
  gap: 8px;
}
</style>
