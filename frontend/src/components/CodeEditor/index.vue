<template>
  <el-dialog :visible.sync="dialogVisible" fullscreen :show-close="false"
    custom-class="code-editor-dialog" @opened="onDialogOpened">
    <div class="ce-layout">
      <div class="ce-toolbar">
        <div class="ce-toolbar-left">
          <el-tag size="small" type="info">{{ fileLanguage }}</el-tag>
          <span class="ce-filename">{{ fileName || '未命名' }}</span>
        </div>
        <div class="ce-toolbar-right">
          <el-button size="small" icon="el-icon-document-copy" @click="copy">复制</el-button>
          <el-button size="small" type="primary" icon="el-icon-check"
            @click="save" :loading="saving">保存</el-button>
          <el-button size="small" icon="el-icon-close" @click="close">关闭</el-button>
        </div>
      </div>
      <div class="ce-body">
        <codemirror v-if="ready" ref="cm" v-model="code"
          :options="cmOptions"/>
        <div v-else class="ce-loading"><i class="el-icon-loading"/> 加载中...</div>
      </div>
    </div>
  </el-dialog>
</template>

<script>
import { codemirror } from 'vue-codemirror'
import 'codemirror/lib/codemirror.css'
import 'codemirror/theme/material-darker.css'
import 'codemirror/mode/javascript/javascript'
import 'codemirror/mode/css/css'
import 'codemirror/mode/python/python'
import 'codemirror/mode/markdown/markdown'
import 'codemirror/mode/sql/sql'
import 'codemirror/mode/xml/xml'
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
  },
  data() { return { dialogVisible: this.visible, code: '', ready: false,
    saving: false, original: '' } },
  mounted() { if (this.visible) { this.original = this.content || '';
    this.code = this.content || ''; this.$nextTick(()=>setTimeout(()=>{ this.ready = true },100)) } },
  computed: {
    cmOptions() { return { mode: this.fileLanguage, theme: 'material-darker',
      lineNumbers: true, lineWrapping: true, tabSize: 2, indentWithTabs: false,
      autoCloseBrackets: true, matchBrackets: true, foldGutter: true,
      gutters: ['CodeMirror-linenumbers','CodeMirror-foldgutter'],
      extraKeys: { 'Ctrl-S': ()=>this.save(), 'Cmd-S': ()=>this.save() } } },
    fileLanguage() {
      const m = { js:'javascript', jsx:'javascript', ts:'javascript', tsx:'javascript',
        css:'css', scss:'css', less:'css', py:'python', md:'markdown', sql:'sql',
        json:'javascript', xml:'xml', svg:'xml' }
      return m[(this.language||'').toLowerCase()] || this.language || 'text'
    },
  },
  watch: {
    visible(v) { this.dialogVisible = v; if(v){ this.original = this.content || '';
      this.code = this.content || ''; this.$nextTick(()=>setTimeout(()=>{ this.ready = true },100)) } },
    dialogVisible(v) { if(!v){ this.ready = false; this.$emit('update:visible',false) } },
  },
  methods: {
    onDialogOpened() { if(this.ready && this.$refs.cm) this.$refs.cm.codemirror.refresh() },
    copy() { navigator.clipboard.writeText(this.code).then(
      ()=>this.$message.success('已复制'), ()=>this.$message.error('复制失败')) },
    async save() {
      console.log('[DEBUG P3A] save 触发, filePath:', this.filePath || '(空!)', 'sessionId:', this.sessionId || '(空!)')
      if(!this.filePath||!this.sessionId){ console.log('[DEBUG P3A] 缺少路径或会话ID, 终止保存'); this.$message.warning('缺少路径或会话ID'); return }
      this.saving = true
      try { await writeFile(this.sessionId, this.filePath, this.code)
        this.original = this.code; console.log('[DEBUG P3A] writeFile 成功'); this.$message.success('已保存')
        this.$emit('saved', { path: this.filePath, content: this.code }); this.dialogVisible = false }
      catch(e){ console.error('[DEBUG P3A] writeFile 失败:', e.message || e); this.$message.error('保存失败: '+(e.message||'')) }
      finally{ this.saving = false }
    },
    close() { if(this.code !== this.original)
      this.$confirm('放弃更改？','提示',{ confirmButtonText:'放弃', cancelButtonText:'继续编辑', type:'warning' })
        .then(()=>this.dialogVisible=false).catch(()=>{})
      else this.dialogVisible = false },
  },
}
</script>

<style scoped>
.ce-layout { display:flex; flex-direction:column; height:100vh; background:#1a1a2e; color:#e0e0e0 }
.ce-toolbar { display:flex; align-items:center; justify-content:space-between;
  padding:8px 16px; background:#16213e; border-bottom:1px solid #0f3460; flex-shrink:0 }
.ce-toolbar-left { display:flex; align-items:center; gap:8px }
.ce-filename { color:#a0aec0; font-size:14px }
.ce-toolbar-right { display:flex; gap:8px }
.ce-body { flex:1; overflow:auto }
.ce-body .CodeMirror { height:100%!important }
.ce-body .vue-codemirror { height:100% }
.ce-loading { display:flex; align-items:center; justify-content:center; height:200px; color:#a0aec0 }
.ce-loading i { margin-right:8px }
</style>
