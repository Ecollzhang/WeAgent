<template>
  <div class="comment-list">
    <!-- Pinned Comments -->
    <div
      v-for="comment in pinnedComments"
      :key="'pinned-' + comment.id"
      class="comment-thread"
    >
      <div class="comment-item pinned" :class="commentClass(comment)">
        <div class="comment-pin-badge">
          <i class="el-icon-top"></i> 已置顶
        </div>
        <div class="comment-body">
          <div class="comment-avatar">
            <el-avatar :size="28" :style="{ backgroundColor: avatarColor(comment.author_name || 'U') }">
              {{ avatarInitials(comment.author_name || 'U') }}
            </el-avatar>
          </div>
          <div class="comment-content-wrapper">
            <div class="comment-header">
              <span class="comment-author">{{ comment.author_name || '未知用户' }}</span>
              <span class="comment-time">{{ timeAgo(comment.created_at) }}</span>
              <i v-if="comment.content_type === 'system'" class="el-icon-info system-icon"></i>
            </div>
            <div v-if="editingCommentId === comment.id" class="inline-edit-area">
              <CommentEditor
                v-model="editingContent"
                :show-cancel="true"
                @submit="confirmEdit"
                @cancel="cancelEdit"
              />
            </div>
            <div class="comment-text" v-else-if="!comment.is_deleted" :class="{ 'system-text': comment.content_type === 'system' }">
              <span v-html="renderContent(comment.content)"></span>
            </div>
            <div class="comment-deleted" v-else>[该评论已删除]</div>
            <div class="comment-actions" v-if="!comment.is_deleted && comment.content_type !== 'system' && currentUserId && editingCommentId !== comment.id">
              <span class="action-btn" @click="toggleReplyInput(comment.id, comment.replies)">
                <i class="el-icon-chat-line-round"></i> 回复
              </span>
              <span v-if="comment.author_id === currentUserId" class="action-btn" @click="handleEdit(comment)">
                <i class="el-icon-edit"></i> 编辑
              </span>
              <span
                v-if="comment.author_id === currentUserId"
                class="action-btn danger"
                @click="$emit('delete', comment.id)"
              >
                <i class="el-icon-delete"></i> 删除
              </span>
            </div>
            <div v-if="showReplyInputFor === comment.id" class="reply-input-area">
              <CommentEditor
                :placeholder="'回复 ' + (comment.author_name || '用户') + '...'"
                :show-cancel="true"
                @submit="(content) => submitReply(comment.id, content)"
                @cancel="showReplyInputFor = null"
              />
            </div>
          </div>
        </div>
      </div>
      <div v-if="comment.replies && comment.replies.length > 0" class="replies-container">
        <div
          v-for="reply in comment.replies"
          :key="'reply-' + reply.id"
          class="comment-item reply"
          :class="commentClass(reply)"
        >
          <div class="comment-body">
            <div class="comment-avatar">
              <el-avatar :size="22" :style="{ backgroundColor: avatarColor(reply.author_name || 'U') }">
                {{ avatarInitials(reply.author_name || 'U') }}
              </el-avatar>
            </div>
            <div class="comment-content-wrapper">
              <div class="comment-header">
                <span class="comment-author">{{ reply.author_name || '未知用户' }}</span>
                <span class="comment-time">{{ timeAgo(reply.created_at) }}</span>
                <span v-if="reply.reply_to_name" class="reply-to">
                  回复 <span class="reply-target">@{{ reply.reply_to_name }}</span>
                </span>
              </div>
              <div v-if="editingCommentId === reply.id" class="inline-edit-area">
                <CommentEditor
                  v-model="editingContent"
                  :show-cancel="true"
                  @submit="confirmEdit"
                  @cancel="cancelEdit"
                />
              </div>
              <div class="comment-text" v-else-if="!reply.is_deleted" :class="{ 'system-text': reply.content_type === 'system' }">
                <span v-html="renderContent(reply.content)"></span>
              </div>
              <div class="comment-deleted" v-else>[该评论已删除]</div>
              <div class="comment-actions" v-if="!reply.is_deleted && reply.content_type !== 'system' && currentUserId && editingCommentId !== reply.id">
                <span class="action-btn" @click="toggleReplyInput(reply.id, comment.replies)">
                  <i class="el-icon-chat-line-round"></i> 回复
                </span>
                <span v-if="reply.author_id === currentUserId" class="action-btn" @click="handleEdit(reply)">
                  <i class="el-icon-edit"></i> 编辑
                </span>
                <span
                  v-if="reply.author_id === currentUserId"
                  class="action-btn danger"
                  @click="$emit('delete', reply.id)"
                >
                  <i class="el-icon-delete"></i> 删除
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div
        v-if="comment.replies && comment.replies.length > 3 && !expandedReplies[comment.id]"
        class="show-more-replies"
        @click="toggleRepliesExpand(comment.id)"
      >
        <span>查看全部 {{ comment.replies.length }} 条回复</span>
        <i class="el-icon-arrow-down"></i>
      </div>
      <div
        v-if="comment.replies && comment.replies.length > 3 && expandedReplies[comment.id]"
        class="show-more-replies"
        @click="toggleRepliesExpand(comment.id)"
      >
        <span>收起回复</span>
        <i class="el-icon-arrow-up"></i>
      </div>
    </div>

    <!-- Regular Comments -->
    <div
      v-for="comment in regularComments"
      :key="'comment-' + comment.id"
      class="comment-thread"
    >
      <div class="comment-item" :class="commentClass(comment)">
        <div class="comment-body">
          <div class="comment-avatar">
            <el-avatar :size="28" :style="{ backgroundColor: avatarColor(comment.author_name || 'U') }">
              {{ avatarInitials(comment.author_name || 'U') }}
            </el-avatar>
          </div>
          <div class="comment-content-wrapper">
            <div class="comment-header">
              <span class="comment-author">{{ comment.author_name || '未知用户' }}</span>
              <span class="comment-time">{{ timeAgo(comment.created_at) }}</span>
              <i v-if="comment.content_type === 'system'" class="el-icon-info system-icon"></i>
            </div>
            <div v-if="editingCommentId === comment.id" class="inline-edit-area">
              <CommentEditor
                v-model="editingContent"
                :show-cancel="true"
                @submit="confirmEdit"
                @cancel="cancelEdit"
              />
            </div>
            <div class="comment-text" v-else-if="!comment.is_deleted" :class="{ 'system-text': comment.content_type === 'system' }">
              <span v-html="renderContent(comment.content)"></span>
            </div>
            <div class="comment-deleted" v-else>[该评论已删除]</div>
            <div class="comment-actions" v-if="!comment.is_deleted && comment.content_type !== 'system' && currentUserId && editingCommentId !== comment.id">
              <span class="action-btn" @click="toggleReplyInput(comment.id, comment.replies)">
                <i class="el-icon-chat-line-round"></i> 回复
              </span>
              <span v-if="comment.author_id === currentUserId" class="action-btn" @click="handleEdit(comment)">
                <i class="el-icon-edit"></i> 编辑
              </span>
              <span
                v-if="comment.author_id === currentUserId"
                class="action-btn danger"
                @click="$emit('delete', comment.id)"
              >
                <i class="el-icon-delete"></i> 删除
              </span>
            </div>
            <div v-if="showReplyInputFor === comment.id" class="reply-input-area">
              <CommentEditor
                :placeholder="'回复 ' + (comment.author_name || '用户') + '...'"
                :show-cancel="true"
                @submit="(content) => submitReply(comment.id, content)"
                @cancel="showReplyInputFor = null"
              />
            </div>
          </div>
        </div>
      </div>
      <div v-if="comment.replies && comment.replies.length > 0" class="replies-container">
        <div
          v-for="reply in displayedReplies(comment)"
          :key="'reply-' + reply.id"
          class="comment-item reply"
          :class="commentClass(reply)"
        >
          <div class="comment-body">
            <div class="comment-avatar">
              <el-avatar :size="22" :style="{ backgroundColor: avatarColor(reply.author_name || 'U') }">
                {{ avatarInitials(reply.author_name || 'U') }}
              </el-avatar>
            </div>
            <div class="comment-content-wrapper">
              <div class="comment-header">
                <span class="comment-author">{{ reply.author_name || '未知用户' }}</span>
                <span class="comment-time">{{ timeAgo(reply.created_at) }}</span>
                <span v-if="reply.reply_to_name" class="reply-to">
                  回复 <span class="reply-target">@{{ reply.reply_to_name }}</span>
                </span>
              </div>
              <div v-if="editingCommentId === reply.id" class="inline-edit-area">
                <CommentEditor
                  v-model="editingContent"
                  :show-cancel="true"
                  @submit="confirmEdit"
                  @cancel="cancelEdit"
                />
              </div>
              <div class="comment-text" v-else-if="!reply.is_deleted" :class="{ 'system-text': reply.content_type === 'system' }">
                <span v-html="renderContent(reply.content)"></span>
              </div>
              <div class="comment-deleted" v-else>[该评论已删除]</div>
              <div class="comment-actions" v-if="!reply.is_deleted && reply.content_type !== 'system' && currentUserId && editingCommentId !== reply.id">
                <span class="action-btn" @click="toggleReplyInput(reply.id, comment.replies)">
                  <i class="el-icon-chat-line-round"></i> 回复
                </span>
                <span v-if="reply.author_id === currentUserId" class="action-btn" @click="handleEdit(reply)">
                  <i class="el-icon-edit"></i> 编辑
                </span>
                <span
                  v-if="reply.author_id === currentUserId"
                  class="action-btn danger"
                  @click="$emit('delete', reply.id)"
                >
                  <i class="el-icon-delete"></i> 删除
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div
        v-if="comment.replies && comment.replies.length > 3 && !expandedReplies[comment.id]"
        class="show-more-replies"
        @click="toggleRepliesExpand(comment.id)"
      >
        <span>查看全部 {{ comment.replies.length }} 条回复</span>
        <i class="el-icon-arrow-down"></i>
      </div>
      <div
        v-if="comment.replies && comment.replies.length > 3 && expandedReplies[comment.id]"
        class="show-more-replies"
        @click="toggleRepliesExpand(comment.id)"
      >
        <span>收起回复</span>
        <i class="el-icon-arrow-up"></i>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="allComments.length === 0" class="empty-state">
      <div class="empty-icon-wrapper">
        <i class="el-icon-chat-line-round"></i>
      </div>
      <p class="empty-title">暂无评论</p>
      <p class="empty-desc">成为第一个参与讨论的人</p>
    </div>
  </div>
</template>

<script>
import CommentEditor from './CommentEditor.vue'

export default {
  name: 'CommentList',
  components: { CommentEditor },
  props: {
    comments: {
      type: Array,
      default: () => [],
    },
    currentUserId: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      showReplyInputFor: null,
      expandedReplies: {},
      editingCommentId: null,
      editingContent: '',
    }
  },
  computed: {
    allComments() {
      return this.comments || []
    },
    pinnedComments() {
      return this.allComments.filter(c => c.is_pinned && !c.parent_id)
    },
    regularComments() {
      return this.allComments.filter(c => !c.is_pinned && !c.parent_id)
    },
  },
  methods: {
    avatarInitials(name) {
      if (!name) return '?'
      const parts = name.trim().split(/\s+/)
      if (parts.length >= 2) {
        return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
      }
      return name.slice(0, 2).toUpperCase()
    },
    avatarColor(name) {
      const colors = [
        '#5b8def', '#52c41a', '#fa9550', '#f55252',
        '#8c8c8c', '#b37feb', '#36cfc9', '#f759ab',
      ]
      if (!name) return colors[0]
      let hash = 0
      for (let i = 0; i < name.length; i++) {
        hash = name.charCodeAt(i) + ((hash << 5) - hash)
      }
      return colors[Math.abs(hash) % colors.length]
    },
    timeAgo(dateStr) {
      if (!dateStr) return ''
      const now = Date.now()
      const date = new Date(dateStr).getTime()
      const diff = Math.floor((now - date) / 1000)
      if (diff < 60) return '刚刚'
      if (diff < 3600) return Math.floor(diff / 60) + ' 分钟前'
      if (diff < 86400) return Math.floor(diff / 3600) + ' 小时前'
      if (diff < 2592000) return Math.floor(diff / 86400) + ' 天前'
      if (diff < 31536000) return Math.floor(diff / 2592000) + ' 个月前'
      return Math.floor(diff / 31536000) + ' 年前'
    },
    renderContent(content) {
      if (!content) return ''
      let html = this.escapeHtml(content)
      html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      html = html.replace(/__(.+?)__/g, '<strong>$1</strong>')
      html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')
      html = html.replace(/_(.+?)_/g, '<em>$1</em>')
      html = html.replace(/`(.+?)`/g, '<code class="inline-code">$1</code>')
      html = html.replace(
        /\[([^\]]+)\]\(([^)]+)\)/g,
        '<a href="$2" target="_blank" rel="noopener">$1</a>'
      )
      html = html.replace(/\n/g, '<br>')
      return html
    },
    escapeHtml(text) {
      const div = document.createElement('div')
      div.textContent = text
      return div.innerHTML
    },
    commentClass(comment) {
      return {
        'is-system': comment.content_type === 'system',
        'is-deleted': comment.is_deleted,
      }
    },
    toggleReplyInput(commentId, replies) {
      if (this.showReplyInputFor === commentId) {
        this.showReplyInputFor = null
      } else {
        this.showReplyInputFor = commentId
        this.ensureExpanded(replies)
      }
    },
    ensureExpanded(replies) {
      if (!replies) return
      const parentComment = this.allComments.find(c => {
        return c.replies && c.replies.some(r => replies.includes(r))
      })
      if (parentComment && parentComment.replies && parentComment.replies.length > 3) {
        this.$set(this.expandedReplies, parentComment.id, true)
      }
    },
    displayedReplies(comment) {
      if (!comment.replies) return []
      if (this.expandedReplies[comment.id]) {
        return comment.replies
      }
      return comment.replies.slice(0, 3)
    },
    toggleRepliesExpand(commentId) {
      this.$set(this.expandedReplies, commentId, !this.expandedReplies[commentId])
    },
    submitReply(commentId, content) {
      this.$emit('reply', commentId, content)
      this.showReplyInputFor = null
    },
    handleEdit(comment) {
      this.editingCommentId = comment.id
      this.editingContent = comment.content || ''
    },
    confirmEdit(content) {
      if (this.editingCommentId) {
        this.$emit('edit', this.editingCommentId, content)
      }
      this.editingCommentId = null
      this.editingContent = ''
    },
    cancelEdit() {
      this.editingCommentId = null
      this.editingContent = ''
    },
  },
}
</script>

<style scoped>
.comment-list {
  width: 100%;
}

/* ── Thread ─────────────────────────────────────────── */
.comment-thread {
  margin-bottom: 6px;
}

/* ── Comment Item ────────────────────────────────────── */
.comment-item {
  padding: 6px 12px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid transparent;
  transition: all 0.2s ease;
}

.comment-item:hover {
  background: #fafbfc;
  border-color: #e8eaed;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.comment-item.is-system {
  background: #f7f8fa;
}

.comment-item.is-deleted {
  opacity: 0.5;
}

/* Pinned */
.comment-item.pinned {
  background: linear-gradient(135deg, #f0f5ff 0%, #f8faff 100%);
  border: 1px solid #d6e4ff;
  border-left: 3px solid #4080ff;
  padding-left: 11px;
}

.comment-pin-badge {
  font-size: 11px;
  color: #4080ff;
  font-weight: 500;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

/* ── Body layout ─────────────────────────────────────── */
.comment-body {
  display: flex;
  gap: 8px;
}

.comment-avatar {
  flex-shrink: 0;
  padding-top: 1px;
}

.comment-avatar >>> .el-avatar {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  font-weight: 600;
  font-size: 12px;
}

.comment-content-wrapper {
  flex: 1;
  min-width: 0;
}

/* ── Header ──────────────────────────────────────────── */
.comment-header {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 2px;
  flex-wrap: wrap;
}

.comment-author {
  font-size: 13px;
  font-weight: 600;
  color: #1d2129;
}

.comment-time {
  font-size: 12px;
  color: #86909c;
}

.system-icon {
  font-size: 13px;
  color: #86909c;
}

.reply-to {
  font-size: 12px;
  color: #86909c;
}

.reply-target {
  color: #4080ff;
  font-weight: 500;
}

/* ── Text ────────────────────────────────────────────── */
.comment-text {
  font-size: 14px;
  color: #1d2129;
  line-height: 1.65;
  word-break: break-word;
}

.comment-text.system-text {
  color: #86909c;
}

.comment-text >>> .inline-code {
  background: #f2f3f5;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Menlo', 'Consolas', 'Monaco', monospace;
  font-size: 12.5px;
  color: #e07c20;
}

.comment-text >>> a {
  color: #4080ff;
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: border-color 0.2s;
}

.comment-text >>> a:hover {
  border-bottom-color: #4080ff;
}

.comment-text >>> strong {
  font-weight: 600;
}

.comment-deleted {
  font-size: 13px;
  color: #c9cdd4;
  font-style: italic;
}

/* ── Actions ─────────────────────────────────────────── */
.comment-actions {
  max-height: 0;
  overflow: hidden;
  display: flex;
  gap: 14px;
  margin-top: 0;
  transition: max-height 0.2s, margin-top 0.2s;
}

.comment-item:hover .comment-actions {
  max-height: 24px;
  margin-top: 4px;
}

.action-btn {
  font-size: 12px;
  color: #86909c;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: color 0.15s;
  user-select: none;
}

.action-btn:hover {
  color: #4080ff;
}

.action-btn.danger:hover {
  color: #f55252;
}

/* ── Inline edit ─────────────────────────────────────── */
.inline-edit-area {
  margin: 2px 0 6px;
}

.reply-input-area {
  margin-top: 8px;
}

/* ── Replies ─────────────────────────────────────────── */
.replies-container {
  margin-left: 36px;
  margin-top: 2px;
}

.comment-item.reply {
  padding: 4px 8px;
  background: transparent;
  border: none;
  border-radius: 6px;
  margin-bottom: 1px;
}

.comment-item.reply:hover {
  background: #f7f8fa;
  box-shadow: none;
  border-color: transparent;
}

/* ── Show more ───────────────────────────────────────── */
.show-more-replies {
  margin-left: 36px;
  font-size: 12px;
  color: #4080ff;
  cursor: pointer;
  padding: 3px 0;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: color 0.2s;
  user-select: none;
}

.show-more-replies:hover {
  color: #6aa1ff;
}

/* ── Empty ───────────────────────────────────────────── */
.empty-state {
  text-align: center;
  padding: 48px 20px 40px;
}

.empty-icon-wrapper {
  width: 56px;
  height: 56px;
  margin: 0 auto 16px;
  border-radius: 50%;
  background: #f2f3f5;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-icon-wrapper i {
  font-size: 24px;
  color: #c9cdd4;
}

.empty-title {
  font-size: 14px;
  color: #86909c;
  margin: 0 0 4px;
  font-weight: 500;
}

.empty-desc {
  font-size: 12px;
  color: #c9cdd4;
  margin: 0;
}
</style>
