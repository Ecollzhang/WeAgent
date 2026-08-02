<template>
  <div class="rd-repo-detail-page">
    <AppSidebar />

    <main class="rd-detail-content">
      <header class="detail-header">
        <el-button type="text" icon="el-icon-arrow-left" @click="$router.push('/repos')">
          返回仓库列表
        </el-button>
        <div class="header-main" v-if="repo">
          <div class="header-info">
            <h2><i class="el-icon-folder-opened"></i> {{ repo.repo_name || repo.full_name || repo.name }}</h2>
            <span class="header-desc" v-if="repo.description">{{ repo.description }}</span>
          </div>
          <div class="header-actions">
            <el-select v-model="selectedBranch" size="small" style="width:240px" @change="onBranchChange">
              <el-option v-for="br in branches" :key="br.name" :label="br.name" :value="br.name">
                <span>{{ br.name }}</span>
              </el-option>
            </el-select>
          </div>
        </div>
        <el-tabs v-model="activeTab" class="detail-tabs">
          <el-tab-pane label="代码" name="code" />
          <el-tab-pane label="分支" name="branches" />
          <el-tab-pane label="提交历史" name="commits" />
        </el-tabs>
      </header>

      <div class="detail-body">
        <!-- ==================== 代码 Tab ==================== -->
        <template v-if="activeTab === 'code'">
          <div class="code-layout" ref="codeLayout">
            <!-- 文件树 -->
            <div class="file-tree-panel" :style="{ width: treePanelWidth + 'px' }">
              <div class="tree-header">
                <el-input v-model="fileSearch" placeholder="搜索文件..." size="small" clearable />
              </div>
              <div class="tree-body">
                <TreeNode
                  v-for="node in displayTree"
                  :key="node.path || node.name"
                  :node="node"
                  :depth="0"
                  :selected-path="selectedFilePath"
                  @select="handleFileSelect"
                />
              </div>
            </div>

            <!-- 拖拽分隔条 -->
            <div class="tree-resize-handle" @mousedown="startResize"></div>

            <!-- 代码查看器 -->
            <div class="code-viewer-panel">
              <template v-if="selectedFilePath">
                <div class="viewer-toolbar">
                  <span class="viewer-path">{{ selectedFilePath }}</span>
                  <div class="viewer-toolbar-right">
                    <template v-if="fileType === 'code'">
                      <div class="theme-picker">
                        <span
                          v-for="t in codeThemes"
                          :key="t.name"
                          class="theme-dot"
                          :class="{ active: codeTheme === t.name }"
                          :style="{ background: t.dot }"
                          :title="t.label"
                          @click="selectTheme(t.name)"
                        ></span>
                      </div>
                    </template>
                  </div>
                </div>

                <!-- 图片预览 -->
                <div v-if="fileType === 'image'" class="viewer-image-wrap">
                  <img :src="imageUrl" :alt="selectedFilePath" />
                </div>

                <!-- Markdown 预览 -->
                <div v-else-if="fileType === 'markdown'" class="viewer-markdown-wrap">
                  <div class="markdown-body" v-html="renderedMarkdown"></div>
                </div>

                <!-- 代码查看 -->
                <pre v-else class="code-block" :class="'theme-' + codeTheme"><code class="hljs" v-html="highlightedCode"></code></pre>
              </template>
              <div v-else class="viewer-empty">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#c0c4cc" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                <p>选择左侧文件查看代码</p>
              </div>
            </div>
          </div>
        </template>

        <!-- ==================== 分支 Tab ==================== -->
        <div v-if="activeTab === 'branches'" class="tab-scroll-wrap">
          <div class="tab-toolbar">
            <span class="tab-count">共 {{ branches.length }} 个分支</span>
          </div>
          <el-table :data="branches" stripe style="width:100%">
            <el-table-column prop="name" label="分支名" min-width="250">
              <template slot-scope="{row}">
                <i class="el-icon-share"></i>
                <span style="font-family:monospace;margin-left:6px">{{ row.name }}</span>
                <el-tag v-if="repo && row.name === repo.default_branch" size="mini" type="info" style="margin-left:8px">默认</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="sha" label="SHA" min-width="180">
              <template slot-scope="{row}">
                <code>{{ (row.sha || '').substring(0, 7) }}</code>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- ==================== 提交历史 Tab ==================== -->
        <div v-if="activeTab === 'commits'" class="tab-scroll-wrap">
          <div class="tab-toolbar">
            <span class="tab-count">分支：{{ selectedBranch }}</span>
          </div>
          <div class="commit-timeline">
            <div v-for="cm in allCommits" :key="cm.id" class="commit-card">
              <div class="commit-dot"></div>
              <div class="commit-body">
                <div class="commit-header-row">
                  <a class="commit-hash" :href="cm.html_url" target="_blank" :title="cm.commit_hash">{{ cm.commit_hash.substring(0, 7) }}</a>
                  <span class="commit-msg">{{ cm.message.split('\n')[0] }}</span>
                </div>
                <div class="commit-meta">
                  <span><i class="el-icon-user"></i> {{ cm.author_name }}</span>
                  <span><i class="el-icon-time"></i> {{ formatTime(cm.committed_at) }}</span>
                  <span class="commit-stats">
                    <span class="additions">+{{ cm.additions }}</span>
                    <span class="deletions">-{{ cm.deletions }}</span>
                    <span>{{ cm.files_changed }} 个文件</span>
                  </span>
                </div>
                <div class="commit-full-msg" v-if="cm.message.includes('\n')">
                  <pre>{{ cm.message.split('\n').slice(1).join('\n') }}</pre>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script>
import AppSidebar from '@/components/Sidebar/index.vue'
import TreeNode from './TreeNode.vue'
import { demoRepos, demoFileTree, demoFileContent, demoCommits } from './demoData'
import * as rdApi from '@/api/rd'
import hljs from 'highlight.js/lib/core'
import javascript from 'highlight.js/lib/languages/javascript'
import python from 'highlight.js/lib/languages/python'
import xml from 'highlight.js/lib/languages/xml'
import css from 'highlight.js/lib/languages/css'
import json from 'highlight.js/lib/languages/json'
import bash from 'highlight.js/lib/languages/bash'
import typescript from 'highlight.js/lib/languages/typescript'
import java from 'highlight.js/lib/languages/java'
import go from 'highlight.js/lib/languages/go'
import c from 'highlight.js/lib/languages/c'
import cpp from 'highlight.js/lib/languages/cpp'
import sql from 'highlight.js/lib/languages/sql'
import yaml from 'highlight.js/lib/languages/yaml'
import markdown from 'highlight.js/lib/languages/markdown'
import plaintext from 'highlight.js/lib/languages/plaintext'

hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('js', javascript)
hljs.registerLanguage('python', python)
hljs.registerLanguage('py', python)
hljs.registerLanguage('xml', xml)
hljs.registerLanguage('html', xml)
hljs.registerLanguage('vue', xml)
hljs.registerLanguage('css', css)
hljs.registerLanguage('json', json)
hljs.registerLanguage('bash', bash)
hljs.registerLanguage('sh', bash)
hljs.registerLanguage('shell', bash)
hljs.registerLanguage('typescript', typescript)
hljs.registerLanguage('ts', typescript)
hljs.registerLanguage('java', java)
hljs.registerLanguage('go', go)
hljs.registerLanguage('c', c)
hljs.registerLanguage('cpp', cpp)
hljs.registerLanguage('sql', sql)
hljs.registerLanguage('yaml', yaml)
hljs.registerLanguage('yml', yaml)
hljs.registerLanguage('markdown', markdown)
hljs.registerLanguage('md', markdown)
hljs.registerLanguage('plaintext', plaintext)
hljs.registerLanguage('txt', plaintext)

const EXT_LANG_MAP = {
  js: 'javascript', jsx: 'javascript', ts: 'typescript', tsx: 'typescript',
  py: 'python', java: 'java', go: 'go', rs: 'rust',
  c: 'c', cpp: 'cpp', h: 'c', hpp: 'cpp',
  html: 'xml', htm: 'xml', vue: 'xml', jsx: 'javascript',
  css: 'css', scss: 'css', less: 'css',
  json: 'json', xml: 'xml', yaml: 'yaml', yml: 'yaml', toml: 'ini',
  sql: 'sql', sh: 'bash', bash: 'bash', zsh: 'bash',
  md: 'markdown', txt: 'plaintext', env: 'bash',
  dockerfile: 'dockerfile', makefile: 'makefile',
}

// 将 GitHub API 返回的扁平 tree 转为嵌套结构
function buildFileTree(items) {
  const root = { name: '/', type: 'tree', children: [] }
  const map = { '': root }
  // 排序：目录在前，然后按名称
  const sorted = [...items].sort((a, b) => {
    if (a.type !== b.type) return a.type === 'tree' ? -1 : 1
    return (a.path || '').localeCompare(b.path || '')
  })
  for (const item of sorted) {
    const path = item.path || ''
    const parts = path.split('/')
    const name = parts[parts.length - 1]
    const parentPath = parts.slice(0, -1).join('/')

    const node = {
      name,
      path,
      type: item.type,  // 'blob' or 'tree'
      size: item.size,
      sha: item.sha,
      children: item.type === 'tree' ? [] : undefined,
    }

    if (!map[parentPath]) {
      // 确保父目录存在
      map[parentPath] = { name: parentPath.split('/').pop(), path: parentPath, type: 'tree', children: [] }
      root.children.push(map[parentPath])
    }

    const parent = map[parentPath] || root
    if (parent.children) {
      parent.children.push(node)
    }
    if (item.type === 'tree') {
      map[path] = node
    }
  }
  return root.children.length ? root.children : []
}

export default {
  name: 'RdRepoDetail',
  components: { AppSidebar, TreeNode },
  data() {
    return {
      activeTab: 'code',
      selectedBranch: 'main',
      selectedFilePath: '',
      currentFileContent: '',
      currentFileSize: 0,
      fileSearch: '',
      fileTree: [],
      branches: [],
      repo: null,
      allCommits: [],
      loadingTree: false,
      loadingFile: false,
      loadingCommits: false,
      treePanelWidth: 260,
      resizing: false,
      codeTheme: 'dark',
      codeThemes: [
        { name: 'dark', label: 'Dark', dot: '#1e1e1e' },
        { name: 'light', label: 'Light', dot: '#ffffff' },
        { name: 'monokai', label: 'Monokai', dot: '#272822' },
        { name: 'github', label: 'GitHub', dot: '#f6f8fa' },
        { name: 'dracula', label: 'Dracula', dot: '#282a36' },
      ],
    }
  },
  computed: {
    displayTree() {
      if (!this.fileSearch) return this.fileTree
      const filter = (nodes) => {
        return nodes.reduce((acc, n) => {
          const isDir = n.type === 'tree' || n.type === 'dir' || n.file_type === 'directory'
          if (isDir) {
            const filtered = filter(n.children || [])
            if (filtered.length) acc.push({ ...n, children: filtered })
          } else if ((n.name || '').toLowerCase().includes(this.fileSearch.toLowerCase())) {
            acc.push(n)
          }
          return acc
        }, [])
      }
      return filter(this.fileTree)
    },
    fileType() {
      if (!this.selectedFilePath) return 'code'
      const ext = (this.selectedFilePath || '').split('.').pop().toLowerCase()
      if (['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico', 'bmp'].includes(ext)) return 'image'
      if (['md', 'markdown'].includes(ext)) return 'markdown'
      return 'code'
    },
    imageUrl() {
      if (!this.repo || !this.selectedFilePath) return ''
      const owner = this.repo.owner || ''
      const repoName = this.repo.repo_name || ''
      const branch = this.selectedBranch || 'main'
      if (!owner || !repoName) return ''
      return `https://raw.githubusercontent.com/${owner}/${repoName}/${branch}/${this.selectedFilePath}`
    },
    renderedMarkdown() {
      if (this.fileType !== 'markdown' || !this.currentFileContent) return ''
      return this.renderMarkdown(this.currentFileContent)
    },
    codeLanguage() {
      if (!this.selectedFilePath) return 'plaintext'
      const ext = (this.selectedFilePath || '').split('.').pop().toLowerCase()
      return EXT_LANG_MAP[ext] || 'plaintext'
    },
    highlightedCode() {
      if (!this.currentFileContent || this.fileType !== 'code') return ''
      try {
        const lang = hljs.getLanguage(this.codeLanguage) ? this.codeLanguage : 'plaintext'
        return hljs.highlight(this.currentFileContent, { language: lang }).value
      } catch (e) {
        return this.currentFileContent.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      }
    },
  },
  async created() {
    const repoId = this.$route.params.id
    await this.loadRepo(repoId)
  },
  methods: {
    async loadRepo(repoId) {
      // 加载仓库信息
      try {
        const res = await rdApi.getRepo(repoId)
        if (res.code === 200 && res.data) {
          this.repo = res.data
          this.selectedBranch = res.data.default_branch || 'main'
        }
      } catch (e) {
        // 兜底 demoData
        const found = demoRepos.find(r => r.id === repoId)
        if (found) {
          this.repo = found
          this.selectedBranch = found.default_branch || 'main'
        }
      }

      // 如果 repo 仍然为空，无法继续
      if (!this.repo) return

      // 加载分支列表
      try {
        const res = await rdApi.getRepoBranches(repoId)
        if (res.code === 200) {
          this.branches = (res.data.items || []).map(b => ({
            name: b.name,
            sha: b.sha,
            last_commit_msg: '',
            author: '',
            last_commit_time: null,
          }))
        }
      } catch (e) { /* 使用默认分支 */ }
      // 兜底：至少添加默认分支
      if (this.branches.length === 0) {
        this.branches = [{ name: this.selectedBranch, sha: '' }]
      }

      // 加载文件树
      this.loadFileTree()
      // 加载提交记录
      this.loadCommits()
    },

    async loadFileTree() {
      if (!this.repo) return
      this.loadingTree = true
      try {
        const res = await rdApi.getRepoTree(this.repo.id, {
          branch: this.selectedBranch,
        })
        if (res.code === 200 && res.data.items) {
          this.fileTree = buildFileTree(res.data.items)
          this.loadingTree = false
          return
        }
      } catch (e) { /* fallback */ }
      // 兜底 demoData
      this.fileTree = demoFileTree
      this.loadingTree = false
    },

    async loadCommits() {
      if (!this.repo) return
      this.loadingCommits = true
      try {
        const res = await rdApi.getRepoCommits(this.repo.id, {
          branch: this.selectedBranch,
        })
        if (res.code === 200 && res.data.items) {
          this.allCommits = res.data.items.map(c => ({
            id: c.sha,
            commit_hash: c.sha,
            message: c.message || '',
            author_name: (c.author && c.author.name) || '',
            author_email: (c.author && c.author.email) || '',
            committed_at: (c.author && c.author.date) || '',
            html_url: c.html_url || '',
            additions: c.additions || 0,
            deletions: c.deletions || 0,
            files_changed: c.files_changed || 0,
          }))
          this.loadingCommits = false
          return
        }
      } catch (e) { /* fallback */ }
      this.allCommits = [...demoCommits]
      this.loadingCommits = false
    },

    async handleFileSelect(node) {
      const isDir = node.type === 'tree' || node.type === 'dir' || node.file_type === 'directory'
      if (isDir) return
      const filePath = node.path || node.file_path
      if (!filePath) return
      this.selectedFilePath = filePath
      this.currentFileSize = node.size || 0

      // 图片文件直接用 raw URL 预览，无需获取内容
      const ext = (filePath || '').split('.').pop().toLowerCase()
      if (['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico', 'bmp'].includes(ext)) {
        this.currentFileContent = ''
        this.loadingFile = false
        return
      }

      this.loadingFile = true
      // 尝试 API
      if (this.repo && this.repo.id) {
        try {
          const res = await rdApi.getRepoFile(this.repo.id, {
            branch: this.selectedBranch,
            path: filePath,
          })
          if (res.code === 200 && res.data) {
            this.currentFileContent = res.data.content || ''
            this.loadingFile = false
            return
          }
        } catch (e) { /* fallback */ }
      }
      // 兜底 demoData
      this.currentFileContent = demoFileContent[filePath] || '// 文件内容（演示数据）\n// ' + filePath
      this.loadingFile = false
    },

    onBranchChange() {
      this.selectedFilePath = ''
      this.currentFileContent = ''
      this.loadFileTree()
      this.loadCommits()
    },

    formatRelative(iso) {
      if (!iso) return ''
      const diff = Date.now() - new Date(iso).getTime()
      const days = Math.floor(diff / 86400000)
      if (days < 1) return '今天'
      if (days < 2) return '昨天'
      if (days < 30) return days + ' 天前'
      return Math.floor(days / 30) + ' 月前'
    },
    formatTime(iso) {
      if (!iso) return ''
      const d = new Date(iso)
      return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0') + ' ' + String(d.getHours()).padStart(2,'0') + ':' + String(d.getMinutes()).padStart(2,'0')
    },
    formatSize(bytes) {
      if (!bytes) return '0 B'
      if (bytes < 1024) return bytes + ' B'
      if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
      return (bytes / 1048576).toFixed(1) + ' MB'
    },

    selectTheme(name) {
      this.codeTheme = name
    },

    renderMarkdown(text) {
      if (!text) return ''

      // Step 1: 提取代码块
      const codeBlocks = []
      let html = text.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
        codeBlocks.push({ lang, code })
        return `\x00CODEBLOCK_${codeBlocks.length - 1}\x00`
      })

      // Step 2: 提取内联代码
      const inlineCodes = []
      html = html.replace(/`([^`]+)`/g, (_, code) => {
        inlineCodes.push(code)
        return `\x00INLINE_${inlineCodes.length - 1}\x00`
      })

      // Step 3: 转义剩余文本中的 HTML
      html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

      // Step 4: Markdown 转换
      html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>')
      html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>')
      html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>')
      html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>')
      html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
      html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')
      html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" />')
      html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
      html = html.replace(/^---$/gm, '<hr />')
      html = html.replace(/^[\*\-] (.+)$/gm, '<li>$1</li>')
      html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
      html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>')

      // Step 5: 还原内联代码
      html = html.replace(/\x00INLINE_(\d+)\x00/g, (_, i) => {
        const c = inlineCodes[i].replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        return `<code class="md-inline-code">${c}</code>`
      })

      // Step 6: 还原代码块
      html = html.replace(/\x00CODEBLOCK_(\d+)\x00/g, (_, i) => {
        const { lang, code } = codeBlocks[i]
        const escaped = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        return `<pre class="md-code"><code class="${lang || ''}">${escaped}</code></pre>`
      })

      // Step 7: 段落包裹
      const lines = html.split('\n')
      const result = []
      let inP = false
      for (const line of lines) {
        const t = line.trim()
        if (t === '') {
          if (inP) { result.push('</p>'); inP = false }
          continue
        }
        if (/^<(h[1-4]|pre|hr|img|ul|ol|li|blockquote|table)/.test(t)) {
          if (inP) { result.push('</p>'); inP = false }
          result.push(line)
        } else {
          if (!inP) { result.push('<p>'); inP = true }
          result.push(line)
        }
      }
      if (inP) result.push('</p>')
      return result.join('\n')
    },

    startResize(e) {
      this.resizing = true
      this._resizeStartX = e.clientX
      this._resizeStartW = this.treePanelWidth
      document.addEventListener('mousemove', this.onResize)
      document.addEventListener('mouseup', this.stopResize)
      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'
    },
    onResize(e) {
      if (!this.resizing) return
      const dx = e.clientX - this._resizeStartX
      this.treePanelWidth = Math.max(180, Math.min(500, this._resizeStartW + dx))
    },
    stopResize() {
      this.resizing = false
      document.removeEventListener('mousemove', this.onResize)
      document.removeEventListener('mouseup', this.stopResize)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    },
  },
  beforeDestroy() {
    document.removeEventListener('mousemove', this.onResize)
    document.removeEventListener('mouseup', this.stopResize)
  },
}
</script>

<style scoped>
.rd-repo-detail-page {
  display: flex;
  gap: 12px;
  padding: 12px;
  height: 100vh;
  background: linear-gradient(135deg, #e8f0ff 0%, #f0f5ff 50%, #f5f7fa 100%);
  overflow: hidden;
}
.rd-detail-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  overflow: hidden;
}

.detail-header { flex-shrink: 0; margin-bottom: 0; padding: 18px 22px 0; border-bottom: 1px solid #f0f0f0; }
.header-main {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-top: 8px;
}
.header-info h2 { margin: 0 0 4px; font-size: 22px; color: #303133; display: flex; align-items: center; gap: 8px; }
.header-desc { font-size: 13px; color: #909399; }
.header-actions { display: flex; gap: 8px; flex-shrink: 0; }
.detail-tabs { margin-top: 12px; }
.detail-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Tab 滚动包装 */
.tab-scroll-wrap {
  flex: 1;
  overflow-y: auto;
  padding: 16px 22px 24px;
}

/* Tab toolbar */
.tab-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.tab-count { font-size: 14px; font-weight: 600; color: #303133; }

/* 代码布局 */
.code-layout {
  display: flex;
  gap: 0;
  background: #fff;
  border-radius: 10px;
  border: 1px solid #ebeef5;
  overflow: hidden;
  flex: 1;
  min-height: 0;
  margin: 12px 22px 20px;
}
.file-tree-panel {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: #f8f9fb;
}
.tree-header { padding: 10px; border-bottom: 1px solid #e8eaed; }
.tree-body { flex: 1; overflow-y: auto; overflow-x: hidden; padding: 6px 0; }

.tree-resize-handle {
  width: 5px;
  flex-shrink: 0;
  cursor: col-resize;
  background: transparent;
  transition: background 0.15s;
  position: relative;
  z-index: 2;
}
.tree-resize-handle:hover,
.tree-resize-handle:active {
  background: #1967d2;
}

/* 查看器 */
.code-viewer-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.viewer-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: #f5f7fa;
  border-bottom: 1px solid #ebeef5;
  font-size: 13px;
  flex-shrink: 0;
}
.viewer-path { color: #5f6368; display: flex; align-items: center; gap: 6px; font-family: 'Consolas', 'Courier New', monospace; font-size: 12px; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.viewer-toolbar-right { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }

/* 主题选择器 */
.theme-picker { display: flex; gap: 4px; }
.theme-dot {
  width: 16px; height: 16px;
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid transparent;
  transition: border-color 0.15s, transform 0.15s;
  box-shadow: 0 0 0 1px rgba(0,0,0,0.12);
}
.theme-dot:hover { transform: scale(1.15); }
.theme-dot.active { border-color: #1967d2; box-shadow: 0 0 0 2px #1967d2; }

/* 代码块基础 */
.code-block {
  flex: 1;
  margin: 0;
  padding: 20px;
  font-size: 13px;
  line-height: 1.7;
  overflow: auto;
  font-family: 'Consolas', 'Courier New', monospace;
  tab-size: 2;
}
.code-block code { font-family: inherit; }

/* 主题背景色 */
.code-block.theme-dark { background: #1e1e1e; }
.code-block.theme-light { background: #ffffff; border-top: 1px solid #e1e4e8; }
.code-block.theme-monokai { background: #272822; }
.code-block.theme-github { background: #f6f8fa; border-top: 1px solid #e1e4e8; }
.code-block.theme-dracula { background: #282a36; }

/* 图片预览 */
.viewer-image-wrap {
  flex: 1;
  overflow: auto;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 20px;
  background: repeating-conic-gradient(#f0f0f0 0% 25%, #fff 0% 50%) 50% / 20px 20px;
}
.viewer-image-wrap img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border-radius: 4px;
  box-shadow: 0 2px 16px rgba(0,0,0,0.12);
}

/* Markdown 预览 */
.viewer-markdown-wrap {
  flex: 1;
  overflow: auto;
  padding: 24px 32px;
  background: #fff;
}
.markdown-body { max-width: 860px; margin: 0 auto; font-size: 14px; line-height: 1.8; color: #24292e; }
.markdown-body h1 { font-size: 1.8em; border-bottom: 1px solid #e8eaed; padding-bottom: 8px; margin: 20px 0 12px; }
.markdown-body h2 { font-size: 1.4em; border-bottom: 1px solid #e8eaed; padding-bottom: 6px; margin: 18px 0 10px; }
.markdown-body h3 { font-size: 1.15em; margin: 16px 0 8px; }
.markdown-body h4 { font-size: 1em; margin: 12px 0 6px; }
.markdown-body p { margin: 0 0 10px; }
.markdown-body ul, .markdown-body ol { padding-left: 24px; margin: 0 0 10px; }
.markdown-body li { margin-bottom: 2px; }
.markdown-body a { color: #1967d2; text-decoration: none; }
.markdown-body a:hover { text-decoration: underline; }
.markdown-body img { max-width: 100%; border-radius: 4px; }
.markdown-body hr { border: none; border-top: 1px solid #e8eaed; margin: 16px 0; }
.markdown-body .md-code {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 14px 18px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.6;
  overflow: auto;
  margin: 10px 0;
  font-family: 'Consolas', 'Courier New', monospace;
}
.markdown-body .md-inline-code {
  background: #f0f0f0;
  color: #e04040;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
  font-family: 'Consolas', 'Courier New', monospace;
}

.viewer-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #c0c4cc;
  gap: 10px;
}
.viewer-empty p { font-size: 13px; }

/* 提交时间线 */
.commit-timeline { padding-left: 20px; border-left: 2px solid #e4e7ed; margin-left: 10px; }
.commit-card {
  position: relative;
  margin-bottom: 16px;
  padding: 14px 18px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}
.commit-dot {
  position: absolute;
  left: -27px;
  top: 18px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #409eff;
  border: 2px solid #fff;
}
.commit-header-row { display: flex; gap: 10px; align-items: center; margin-bottom: 6px; }
.commit-hash { font-family: monospace; color: #409eff; font-weight: 600; font-size: 13px; text-decoration: none; }
.commit-hash:hover { text-decoration: underline; }
.commit-msg { font-size: 14px; font-weight: 500; color: #303133; flex: 1; }
.commit-meta { display: flex; gap: 16px; font-size: 12px; color: #909399; }
.commit-stats { display: flex; gap: 6px; }
.additions { color: #67c23a; }
.deletions { color: #f56c6c; }
.commit-full-msg { margin-top: 8px; }
.commit-full-msg pre {
  margin: 0;
  font-size: 12px;
  color: #606266;
  background: #f5f7fa;
  padding: 10px;
  border-radius: 6px;
  font-family: 'Consolas', monospace;
  white-space: pre-wrap;
}
</style>

<!-- 非 scoped: highlight.js 主题色 -->
<style>
/* Dark 主题 (默认) */
.code-block.theme-dark .hljs { color: #d4d4d4; }
.code-block.theme-dark .hljs-keyword { color: #569cd6; }
.code-block.theme-dark .hljs-string { color: #ce9178; }
.code-block.theme-dark .hljs-comment { color: #6a9955; font-style: italic; }
.code-block.theme-dark .hljs-number { color: #b5cea8; }
.code-block.theme-dark .hljs-title { color: #dcdcaa; }
.code-block.theme-dark .hljs-type { color: #4ec9b0; }
.code-block.theme-dark .hljs-attr { color: #9cdcfe; }
.code-block.theme-dark .hljs-built_in { color: #dcdcaa; }
.code-block.theme-dark .hljs-literal { color: #569cd6; }
.code-block.theme-dark .hljs-meta { color: #808080; }
.code-block.theme-dark .hljs-regexp { color: #d16969; }
.code-block.theme-dark .hljs-params { color: #d4d4d4; }

/* Light 主题 */
.code-block.theme-light .hljs { color: #24292e; }
.code-block.theme-light .hljs-keyword { color: #d73a49; }
.code-block.theme-light .hljs-string { color: #032f62; }
.code-block.theme-light .hljs-comment { color: #6a737d; font-style: italic; }
.code-block.theme-light .hljs-number { color: #005cc5; }
.code-block.theme-light .hljs-title { color: #6f42c1; }
.code-block.theme-light .hljs-type { color: #005cc5; }
.code-block.theme-light .hljs-attr { color: #005cc5; }
.code-block.theme-light .hljs-built_in { color: #6f42c1; }
.code-block.theme-light .hljs-literal { color: #005cc5; }
.code-block.theme-light .hljs-meta { color: #6a737d; }
.code-block.theme-light .hljs-regexp { color: #032f62; }

/* Monokai 主题 */
.code-block.theme-monokai .hljs { color: #f8f8f2; }
.code-block.theme-monokai .hljs-keyword { color: #f92672; }
.code-block.theme-monokai .hljs-string { color: #e6db74; }
.code-block.theme-monokai .hljs-comment { color: #75715e; font-style: italic; }
.code-block.theme-monokai .hljs-number { color: #ae81ff; }
.code-block.theme-monokai .hljs-title { color: #a6e22e; }
.code-block.theme-monokai .hljs-type { color: #66d9ef; }
.code-block.theme-monokai .hljs-attr { color: #a6e22e; }
.code-block.theme-monokai .hljs-built_in { color: #a6e22e; }
.code-block.theme-monokai .hljs-literal { color: #ae81ff; }
.code-block.theme-monokai .hljs-meta { color: #75715e; }
.code-block.theme-monokai .hljs-regexp { color: #e6db74; }

/* GitHub 主题 */
.code-block.theme-github .hljs { color: #24292e; }
.code-block.theme-github .hljs-keyword { color: #d73a49; }
.code-block.theme-github .hljs-string { color: #032f62; }
.code-block.theme-github .hljs-comment { color: #6a737d; font-style: italic; }
.code-block.theme-github .hljs-number { color: #005cc5; }
.code-block.theme-github .hljs-title { color: #6f42c1; }
.code-block.theme-github .hljs-type { color: #005cc5; }
.code-block.theme-github .hljs-attr { color: #005cc5; }
.code-block.theme-github .hljs-built_in { color: #6f42c1; }
.code-block.theme-github .hljs-literal { color: #005cc5; }

/* Dracula 主题 */
.code-block.theme-dracula .hljs { color: #f8f8f2; }
.code-block.theme-dracula .hljs-keyword { color: #ff79c6; }
.code-block.theme-dracula .hljs-string { color: #f1fa8c; }
.code-block.theme-dracula .hljs-comment { color: #6272a4; font-style: italic; }
.code-block.theme-dracula .hljs-number { color: #bd93f9; }
.code-block.theme-dracula .hljs-title { color: #50fa7b; }
.code-block.theme-dracula .hljs-type { color: #8be9fd; }
.code-block.theme-dracula .hljs-attr { color: #50fa7b; }
.code-block.theme-dracula .hljs-built_in { color: #8be9fd; }
.code-block.theme-dracula .hljs-literal { color: #bd93f9; }
.code-block.theme-dracula .hljs-meta { color: #6272a4; }
.code-block.theme-dracula .hljs-regexp { color: #f1fa8c; }
</style>
