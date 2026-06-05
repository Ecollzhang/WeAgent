<template>
  <div v-if="embedded" class="ce-layout ce-layout-embedded">
    <div class="ce-toolbar">
      <div class="ce-toolbar-left">
        <el-tag size="small" type="info">{{ fileLanguage }}</el-tag>
        <span class="ce-filename">{{ fileName || '未命名' }}</span>
      </div>
      <div class="ce-toolbar-right">
        <el-button size="small" icon="el-icon-document-copy" @click="copy">复制</el-button>
        <el-button size="small" type="primary" icon="el-icon-check" @click="save" :loading="saving">保存</el-button>
        <el-button size="small" icon="el-icon-close" @click="close">关闭</el-button>
      </div>
    </div>
    <div class="ce-body">
      <codemirror v-if="ready" ref="cm" v-model="code" :options="cmOptions" />
      <div v-else class="ce-loading"><i class="el-icon-loading" /> 加载中...</div>
    </div>
  </div>
  <el-dialog
    v-else
    :visible.sync="dialogVisible"
    fullscreen
    :show-close="false"
    custom-class="code-editor-dialog"
    @opened="onDialogOpened"
  >
    <div class="ce-layout">
      <div class="ce-toolbar">
        <div class="ce-toolbar-left">
          <el-tag size="small" type="info">{{ fileLanguage }}</el-tag>
          <span class="ce-filename">{{ fileName || '未命名' }}</span>
        </div>
        <div class="ce-toolbar-right">
          <el-button size="small" icon="el-icon-document-copy" @click="copy">复制</el-button>
          <el-button size="small" type="primary" icon="el-icon-check" @click="save" :loading="saving">保存</el-button>
          <el-button size="small" icon="el-icon-close" @click="close">关闭</el-button>
        </div>
      </div>
      <div class="ce-body">
        <codemirror v-if="ready" ref="cm" v-model="code" :options="cmOptions" />
        <div v-else class="ce-loading"><i class="el-icon-loading" /> 加载中...</div>
      </div>
    </div>
  </el-dialog>
</template>

<script>
import { codemirror } from 'vue-codemirror'
import 'codemirror/lib/codemirror.css'
import 'codemirror/mode/javascript/javascript'
import 'codemirror/mode/css/css'
import 'codemirror/mode/python/python'
import 'codemirror/mode/markdown/markdown'
import 'codemirror/mode/sql/sql'
import 'codemirror/mode/xml/xml'
import 'codemirror/mode/clike/clike'
import 'codemirror/mode/shell/shell'
import 'codemirror/mode/ruby/ruby'
import 'codemirror/mode/php/php'
import 'codemirror/mode/go/go'
import 'codemirror/mode/rust/rust'
import 'codemirror/addon/edit/closebrackets'
import 'codemirror/addon/edit/matchbrackets'
import 'codemirror/addon/fold/foldcode'
import 'codemirror/addon/fold/foldgutter'
import 'codemirror/addon/fold/foldgutter.css'
import 'codemirror/addon/fold/brace-fold'
import { writeFile } from '@/api/sandbox'

export default {
  name: 'CodeEditor',
  components: { codemirror },
  props: {
    visible: { type: Boolean, default: false },
    content: { type: String, default: '' },
    language: { type: String, default: 'text' },
    fileName: { type: String, default: '' },
    filePath: { type: String, default: '' },
    sessionId: { type: String, default: '' },
    embedded: { type: Boolean, default: false },
  },
  data() {
    return {
      dialogVisible: this.visible,
      code: '',
      ready: false,
      saving: false,
      original: '',
    }
  },
  computed: {
    cmOptions() {
      return {
        mode: this.fileLanguage,
        theme: 'default',
        lineNumbers: true,
        lineWrapping: true,
        tabSize: 2,
        indentWithTabs: false,
        autoCloseBrackets: true,
        matchBrackets: true,
        foldGutter: true,
        gutters: ['CodeMirror-linenumbers', 'CodeMirror-foldgutter'],
        extraKeys: {
          'Ctrl-S': () => this.save(),
          'Cmd-S': () => this.save(),
        },
      }
    },
    fileLanguage() {
      const map = {
        js: 'javascript',
        jsx: 'javascript',
        ts: 'javascript',
        tsx: 'javascript',
        css: 'css',
        scss: 'css',
        less: 'css',
        py: 'python',
        md: 'markdown',
        sql: 'sql',
        json: 'javascript',
        xml: 'xml',
        svg: 'xml',
        java: 'text/x-java',
        c: 'text/x-csrc',
        h: 'text/x-csrc',
        cpp: 'text/x-c++src',
        cc: 'text/x-c++src',
        cxx: 'text/x-c++src',
        hpp: 'text/x-c++src',
        cs: 'text/x-csharp',
        go: 'go',
        rs: 'rust',
        php: 'php',
        rb: 'ruby',
        sh: 'shell',
        bat: 'shell',
        ps1: 'shell',
        kt: 'text/x-kotlin',
        swift: 'text/x-swift',
        dart: 'javascript',
      }
      return map[(this.language || '').toLowerCase()] || this.language || 'text'
    },
  },
  watch: {
    visible(v) {
      this.dialogVisible = v
      if (v) this.resetEditor()
    },
    content() {
      if (this.embedded) this.resetEditor()
    },
    filePath() {
      if (this.embedded) this.resetEditor()
    },
    dialogVisible(v) {
      if (!v) {
        this.ready = false
        this.$emit('update:visible', false)
      }
    },
  },
  mounted() {
    if (this.visible || this.embedded) this.resetEditor()
  },
  methods: {
    resetEditor() {
      this.original = this.content || ''
      this.code = this.content || ''
      this.$nextTick(() => setTimeout(() => {
        this.ready = true
        this.refreshEditor()
      }, 80))
    },
    refreshEditor() {
      if (this.ready && this.$refs.cm && this.$refs.cm.codemirror) {
        this.$refs.cm.codemirror.refresh()
      }
    },
    onDialogOpened() {
      this.refreshEditor()
    },
    copy() {
      navigator.clipboard.writeText(this.code).then(
        () => this.$message.success('已复制'),
        () => this.$message.error('复制失败')
      )
    },
    async save() {
      if (!this.filePath || !this.sessionId) {
        this.$message.warning('缺少路径或会话 ID')
        return
      }
      this.saving = true
      try {
        await writeFile(this.sessionId, this.filePath, this.code)
        this.original = this.code
        this.$message.success('已保存')
        this.$emit('saved', { path: this.filePath, content: this.code })
        if (!this.embedded) this.dialogVisible = false
      } catch (error) {
        this.$message.error(`保存失败: ${error.message || ''}`)
      } finally {
        this.saving = false
      }
    },
    close() {
      if (this.code !== this.original) {
        this.$confirm('放弃修改？', '提示', {
          confirmButtonText: '放弃',
          cancelButtonText: '继续编辑',
          type: 'warning',
        }).then(() => {
          if (this.embedded) this.$emit('close-request')
          else this.dialogVisible = false
        }).catch(() => {})
        return
      }
      if (this.embedded) this.$emit('close-request')
      else this.dialogVisible = false
    },
  },
}
</script>

<style scoped>
:deep(.code-editor-dialog .el-dialog) { margin-top: 0 !important; }
:deep(.code-editor-dialog .el-dialog__header) { display: none; }
:deep(.code-editor-dialog .el-dialog__body) { padding: 0; }

.ce-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f6f8fc;
  color: #0f172a;
}

.ce-layout-embedded {
  height: 100%;
  min-height: 0;
}

.ce-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: rgba(255, 255, 255, 0.96);
  border-bottom: 1px solid #dbe3f0;
  flex-shrink: 0;
}

.ce-toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ce-filename {
  color: #0f172a;
  font-size: 14px;
  font-weight: 600;
}

.ce-toolbar-right {
  display: flex;
  gap: 8px;
}

.ce-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  background: #eef3fb;
}

.ce-body .CodeMirror,
.ce-body .vue-codemirror {
  height: 100% !important;
}

.ce-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #64748b;
}

.ce-loading i {
  margin-right: 8px;
}

:deep(.CodeMirror) {
  height: 100% !important;
  background: #f8fbff;
  color: #0f172a;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
}

:deep(.CodeMirror-gutters) {
  background: #eef4fb;
  border-right: 1px solid #dbe3f0;
}

:deep(.CodeMirror-linenumber),
:deep(.CodeMirror-foldgutter-open),
:deep(.CodeMirror-foldgutter-folded) {
  color: #94a3b8;
}

:deep(.CodeMirror-cursor) {
  border-left: 1px solid #2563eb;
}

:deep(.CodeMirror-selected) {
  background: rgba(59, 130, 246, 0.16) !important;
}
</style>
