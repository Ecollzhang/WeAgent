<template>
  <div class="courseware-editor" data-testid="lesson-material-editor">
    <div class="editor-caption">
      <div>
        <b>可视化课件</b>
        <span>像编辑邮件正文一样排版，保存后生成学生可见的 HTML 快照。</span>
      </div>
      <el-tag size="mini" effect="plain">所见即所得</el-tag>
    </div>
    <Toolbar
      class="courseware-toolbar"
      :editor="editor"
      :default-config="toolbarConfig"
      mode="default"
    />
    <Editor
      class="courseware-surface"
      v-model="html"
      :default-config="editorConfig"
      mode="default"
      @onCreated="handleCreated"
    />
    <footer class="editor-footer">
      <span><kbd>Ctrl</kbd>/<kbd>⌘</kbd> + <kbd>S</kbd> 保存</span>
      <span>课件内容由教师审核后才会发布给学生</span>
    </footer>
  </div>
</template>

<script>
import '@wangeditor/editor/dist/css/style.css'
import { Editor, Toolbar } from '@wangeditor/editor-for-vue'

const toolbarKeys = [
  'undo', 'redo', '|',
  'headerSelect', 'fontFamily', 'fontSize', '|',
  'bold', 'italic', 'underline', 'through', 'sub', 'sup', '|',
  'color', 'bgColor', 'clearStyle', '|',
  'justifyLeft', 'justifyCenter', 'justifyRight', '|',
  'bulletedList', 'numberedList', 'indent', 'delIndent', 'lineHeight', '|',
  'blockquote', 'insertLink', 'divider', 'insertTable',
]

export default {
  name: 'RichMaterialEditor',
  components: { Editor, Toolbar },
  props: {
    value: { type: String, default: '' },
  },
  data() {
    return {
      editor: null,
      toolbarConfig: { toolbarKeys },
      editorConfig: {
        placeholder: '输入课件正文，或先运行课件制作 Agent 生成草稿……',
        autoFocus: false,
        scroll: true,
        MENU_CONF: {
          fontFamily: {
            fontFamilyList: [
              { name: '默认字体', value: 'sans-serif' },
              '微软雅黑',
              '宋体',
              '黑体',
              '楷体',
              'Arial',
              'Times New Roman',
            ],
          },
          fontSize: {
            fontSizeList: [
              { name: '小五', value: '12px' },
              { name: '小四', value: '14px' },
              { name: '正文', value: '16px' },
              { name: '小三', value: '18px' },
              { name: '标题', value: '24px' },
              { name: '大标题', value: '32px' },
            ],
          },
          lineHeight: {
            lineHeightList: ['1', '1.25', '1.5', '1.75', '2', '2.5'],
          },
        },
      },
    }
  },
  computed: {
    html: {
      get() { return this.value },
      set(value) {
        if (value !== this.value) {
          this.$emit('input', value)
          this.$emit('change')
        }
      },
    },
  },
  beforeDestroy() {
    if (this.editor) this.editor.destroy()
    this.editor = null
  },
  methods: {
    handleCreated(editor) {
      this.editor = Object.seal(editor)
    },
  },
}
</script>

<style scoped>
.courseware-editor {
  position: relative;
  overflow: hidden;
  border: 1px solid #d7e1e5;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(36, 67, 73, .08);
}
.editor-caption {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 13px 16px;
  border-bottom: 1px solid #e5ecef;
  background: linear-gradient(90deg, #f5faf8, #fbfcfd);
}
.editor-caption b, .editor-caption span { display: block; }
.editor-caption b { color: #24434a; font-size: 14px; }
.editor-caption span { margin-top: 3px; color: #73828c; font-size: 11px; }
.courseware-toolbar {
  border-bottom: 1px solid #dfe7ea;
  background: #f8fafb;
}
.courseware-surface { min-height: 440px; overflow-y: auto; }
.editor-footer {
  display: flex;
  justify-content: space-between;
  padding: 9px 14px;
  border-top: 1px solid #e8eef0;
  color: #80909a;
  font-size: 11px;
}
kbd {
  padding: 1px 4px;
  border: 1px solid #ccd7dc;
  border-radius: 3px;
  background: #f7f9fa;
  color: #53636d;
  font-family: inherit;
}
::v-deep .w-e-text-container { min-height: 440px; }
::v-deep .w-e-text-placeholder { color: #9aa8b1; font-style: normal; }
::v-deep .w-e-bar-item button { border-radius: 5px; }
::v-deep .w-e-bar-item button:hover { background: #eaf4f1; color: #277c72; }
</style>
