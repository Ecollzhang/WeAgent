<template>
  <div class="agent-edit-form">
    <div class="form-header">
      <el-button type="text" icon="el-icon-arrow-left" @click="$emit('back')">
        返回
      </el-button>
      <h2>{{ isNew ? '创建Agent' : '编辑Agent' }}</h2>
      <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
    </div>

    <div class="form-body" v-loading="loading">
      <!-- 头像 + 名称 -->
      <div class="form-section avatar-section">
        <div class="avatar-area">
          <div
            class="agent-avatar"
            :style="{ background: form.color || '#4080ff' }"
            @click="triggerAvatarUpload"
          >
            <img v-if="form.avatar" :src="form.avatar" class="avatar-img" />
            <span v-else class="avatar-letter">{{ form.name?.charAt(0) || '?' }}</span>
            <div class="avatar-overlay">
              <i class="el-icon-camera"></i>
            </div>
          </div>
          <div class="avatar-actions">
            <el-color-picker v-model="form.color" size="mini" title="选择颜色"></el-color-picker>
            <el-button size="mini" type="text" @click="triggerAvatarUpload">上传头像</el-button>
            <el-button size="mini" type="text" v-if="form.avatar" @click="form.avatar = ''">清除</el-button>
          </div>
          <input ref="fileInput" type="file" accept="image/*" style="display:none" @change="handleAvatarFile" />
        </div>
      </div>

      <!-- 基本信息 -->
      <div class="form-section">
        <el-form label-position="top">
          <el-form-item label="Agent 名称">
            <el-input v-model="form.name" placeholder="输入Agent名称"></el-input>
          </el-form-item>

          <el-form-item label="底层模型">
            <el-select v-model="form.adapter_name" style="width:100%">
              <el-option label="Claude Code" value="claude"></el-option>
              <el-option label="Codex" value="codex"></el-option>
              <el-option label="OpenCode" value="opencode"></el-option>
              <el-option label="Mock" value="mock"></el-option>
            </el-select>
          </el-form-item>

          <el-form-item label="系统提示词">
            <el-input type="textarea" :rows="5" v-model="form.system_prompt" placeholder="描述Agent的行为和专业领域..."></el-input>
          </el-form-item>

          <el-form-item label="技能/工作流 (Skill)">
            <el-input type="textarea" :rows="4" v-model="form.skill" placeholder="定义Agent完成角色任务的具体步骤、流程或说明书..."></el-input>
          </el-form-item>

          <el-form-item label="工具集">
            <el-select v-model="form.tool_ids" multiple filterable style="width:100%" placeholder="选择工具">
              <el-option v-for="tool in allTools" :key="tool.id" :label="tool.name" :value="tool.id">
                <span>{{ tool.name }}</span>
                <span style="float:right;color:#86909c;font-size:12px">
                  <i :class="tool.icon || 'el-icon-setting'"></i>
                </span>
              </el-option>
            </el-select>
          </el-form-item>

          <el-form-item label="标签 (点击标签可编辑)">
            <div class="tags-wrapper">
              <el-tag
                v-for="(tag, i) in form.capability_tags"
                :key="i"
                closable
                :disable-transitions="true"
                :color="tagColor(tag)"
                @close="handleDeleteTag(i)"
              >
                <span
                  v-if="editingTagIdx !== i"
                  @click="startEditTag(i)"
                  class="tag-text"
                >{{ tag }}</span>
                <el-input
                  v-else
                  v-model="editTagValue"
                  size="mini"
                  ref="tagInput"
                  @blur="finishEditTag(i)"
                  @keydown.enter.native="finishEditTag(i)"
                  style="width:80px"
                ></el-input>
              </el-tag>
              <el-input
                v-if="showTagInput"
                v-model="newTag"
                size="mini"
                placeholder="新标签"
                ref="newTagInput"
                @blur="confirmAddTag"
                @keydown.enter.native="confirmAddTag"
                style="width:100px"
              ></el-input>
              <el-button v-else size="mini" type="text" icon="el-icon-plus" @click="showTagInput = true">
                添加标签
              </el-button>
            </div>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script>
import { getTools } from '../../api/tools'
import { uploadFile } from '../../api/upload'

export default {
  name: 'AgentEditForm',
  props: {
    agent: Object,
    loading: Boolean,
  },
  data() {
    return {
      saving: false,
      isNew: false,
      showTagInput: false,
      newTag: '',
      editingTagIdx: -1,
      editTagValue: '',
      allTools: [],
      form: {
        name: '',
        adapter_name: 'claude',
        system_prompt: '',
        skill: '',
        capability_tags: [],
        tool_ids: [],
        avatar: '',
        color: '#4080ff',
      },
    }
  },
  created() {
    this.fetchTools()
  },
  watch: {
    agent: {
      immediate: true,
      handler(val) {
        if (val) {
          this.isNew = val.is_new === true
          this.form = {
            name: val.name || '',
            adapter_name: val.adapter_name || 'claude',
            system_prompt: val.system_prompt || '',
            skill: val.skill || '',
            capability_tags: [...(val.capability_tags || [])],
            tool_ids: [...(val.tool_ids || [])],
            avatar: val.avatar || val.avatar_url || '',
            color: val.avatar_color || val.color || '#4080ff',
          }
        } else {
          this.isNew = true
          this.form = {
            name: '',
            adapter_name: 'claude',
            system_prompt: '',
            skill: '',
            capability_tags: [],
            tool_ids: [],
            avatar: '',
            color: '#4080ff',
          }
        }
      },
    },
  },
  methods: {
    async fetchTools() {
      try {
        const res = await getTools()
        if (res.code === 200) {
          this.allTools = res.data
        }
      } catch (e) {
        console.error('Failed to load tools', e)
      }
    },
    triggerAvatarUpload() {
      this.$refs.fileInput.click()
    },
    async handleAvatarFile(e) {
      const file = e.target.files[0]
      if (!file) return
      if (file.size > 2 * 1024 * 1024) {
        this.$message.warning('图片不能超过 2MB')
        return
      }
      try {
        const res = await uploadFile(file)
        if (res.code === 200) {
          this.form.avatar = res.data.url
        } else {
          this.$message.error(res.message || '上传头像失败')
        }
      } catch (err) {
        this.$message.error('上传头像失败，请重试')
      }
      e.target.value = ''
    },
    handleDeleteTag(i) {
      this.form.capability_tags.splice(i, 1)
    },
    tagColor(tag) {
      const palette = [
        '#2d7ce6', '#47b03a', '#cc7d20', '#d9534f',
        '#8e5cd6', '#2baaa0', '#d9538c', '#e68a2e',
      ]
      let h = 0
      for (let i = 0; i < tag.length; i++) {
        h = tag.charCodeAt(i) + ((h << 5) - h)
      }
      return palette[Math.abs(h) % palette.length]
    },
    startEditTag(i) {
      this.editingTagIdx = i
      this.editTagValue = this.form.capability_tags[i]
      this.$nextTick(() => {
        if (this.$refs.tagInput) this.$refs.tagInput[0].focus()
      })
    },
    finishEditTag(i) {
      if (this.editTagValue.trim()) {
        this.form.capability_tags.splice(i, 1, this.editTagValue.trim())
      }
      this.editingTagIdx = -1
      this.editTagValue = ''
    },
    confirmAddTag() {
      if (this.newTag.trim()) {
        this.form.capability_tags.push(this.newTag.trim())
      }
      this.newTag = ''
      this.showTagInput = false
    },
    async handleSave() {
      if (!this.form.name) {
        this.$message.warning('请输入Agent名称')
        return
      }
      this.saving = true
      try {
        this.$emit('save', { ...this.form })
      } finally {
        this.saving = false
      }
    },
  },
}
</script>

<style scoped>
.agent-edit-form {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.form-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.form-header h2 {
  flex: 1;
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
}

.form-header .el-button--primary {
  background: #4080ff;
  border: none;
  border-radius: 8px;
}

.form-body {
  flex: 1;
  padding: 24px 32px;
  overflow-y: auto;
}

.form-body::-webkit-scrollbar { width: 4px; }
.form-body::-webkit-scrollbar-thumb { background: #dcdde1; border-radius: 4px; }

.form-section {
  max-width: 560px;
  margin-bottom: 24px;
}

/* 头像区域 */
.avatar-area {
  display: flex;
  align-items: center;
  gap: 16px;
}

.agent-avatar {
  width: 72px;
  height: 72px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  flex-shrink: 0;
  transition: transform 0.2s;
}

.agent-avatar:hover {
  transform: scale(1.05);
}

.agent-avatar .avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-letter {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
}

.avatar-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
  color: #fff;
  font-size: 24px;
}

.agent-avatar:hover .avatar-overlay {
  opacity: 1;
}

.avatar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.avatar-actions .el-button--text {
  font-size: 13px;
  color: #4080ff;
}

/* 标签 */
.tags-wrapper {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.tag-text {
  cursor: text;
  display: inline-block;
  min-width: 20px;
}

.el-tag {
  cursor: default;
  color: #fff !important;
}

.el-tag .el-input--mini {
  vertical-align: top;
}
</style>
