<template>
  <div class="chat-window">
    <div class="chat-header" v-if="conversation">
      <div class="header-left">
        <h3>{{ conversation.title }}</h3>
        <span class="participant-count">
          {{ participantCount }} 个参与者
        </span>
      </div>
      <div class="header-actions">
        <el-button size="mini" icon="el-icon-search" type="text" @click="$emit('search-messages')" title="搜索"></el-button>
        <el-button size="mini" icon="el-icon-paperclip" type="text" @click="$emit('open-attachment')" title="附件"></el-button>
        <el-button size="mini" icon="el-icon-star-off" type="text" @click="$emit('toggle-star')" title="收藏"></el-button>
        <el-button size="mini" icon="el-icon-time" type="text" @click="$emit('open-history')" title="历史"></el-button>
        <el-dropdown trigger="click" @command="handleMoreCommand">
          <el-button size="mini" icon="el-icon-more" type="text" title="更多"></el-button>
          <el-dropdown-menu slot="dropdown">
            <el-dropdown-item command="delete" v-if="conversation.owner_id === userId">
              <i class="el-icon-delete"></i> 删除会话
            </el-dropdown-item>
          </el-dropdown-menu>
        </el-dropdown>
      </div>
    </div>

    <div class="chat-header" v-else>
      <div class="header-left">
        <h3 class="text-primary">WeAgent</h3>
        <span class="participant-count">请选择或创建一个会话</span>
      </div>
      <div class="header-actions">
        <el-button size="mini" icon="el-icon-search" type="text" title="搜索"></el-button>
        <el-button size="mini" icon="el-icon-paperclip" type="text" title="附件"></el-button>
        <el-button size="mini" icon="el-icon-star-off" type="text" title="收藏"></el-button>
        <el-button size="mini" icon="el-icon-time" type="text" title="历史"></el-button>
        <el-button size="mini" icon="el-icon-more" type="text" title="更多"></el-button>
      </div>
    </div>

    <div class="messages-container" ref="messagesContainer">
      <template v-if="messages && messages.length > 0">
        <div v-for="msg in messages" :key="msg.id" class="message-wrapper">
          <MessageBubble
            :message="msg"
            :isOwn="msg.sender_type === 'user' && msg.sender_id === userId"
            @pin="$emit('pin-message', msg.id)"
          />
        </div>
      </template>

      <div v-else-if="conversation" class="empty-messages">
        <i class="el-icon-chat-dot-round"></i>
        <p>发送一条消息开始对话！</p>
      </div>

      <!-- Agent typing indicator -->
      <div v-if="agentResponding" class="typing-indicator">
        <div class="typing-dots">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </div>
        <span class="typing-text">智能体正在响应...</span>
      </div>

      <div v-else class="empty-messages">
        <i class="el-icon-s-promotion"></i>
        <h2>欢迎使用 WeAgent</h2>
        <p>多智能体协作平台</p>
        <p class="hint">创建或选择会话开始聊天</p>
      </div>
    </div>

    <!-- 底部标签切换栏 -->
    <div class="chat-tabs" v-if="conversation">
      <span
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-item"
        :class="{ active: activeTab === tab.key }"
        @click="handleTabSwitch(tab.key)"
      >{{ tab.label }}</span>
    </div>

    <div class="message-input" v-if="conversation">
      <div class="input-wrapper">
        <el-input
          type="text"
          placeholder="输入消息..."
          v-model="inputText"
          @keydown.enter.native="handleSend"
          class="feishu-input"
        >
        </el-input>
        <el-button type="text" class="send-btn" @click="handleSend" :disabled="!inputText.trim()">
          <i class="el-icon-promotion"></i>
        </el-button>
      </div>
    </div>
  </div>
</template>

<script>
import MessageBubble from '../MessageBubble/index.vue'

export default {
  name: 'ChatWindow',
  components: { MessageBubble },
  props: {
    conversation: Object,
    messages: Array,
    userId: String,
    agentResponding: { type: Boolean, default: false },
  },
  data() {
    return {
      inputText: '',
      activeTab: 'chat',
      tabs: [
        { key: 'chat', label: '对话' },
        { key: 'agent_config', label: '智能体配置' },
        { key: 'tool_calls', label: '工具调用' },
        { key: 'logs', label: '日志' },
      ],
    }
  },
  computed: {
    participantCount() {
      if (!this.conversation || !this.conversation.participants) return 0
      return this.conversation.participants.length
    },
  },
  watch: {
    messages() {
      this.$nextTick(() => this.scrollToBottom())
    },
    conversation() {
      this.$nextTick(() => this.scrollToBottom())
    },
  },
  methods: {
    handleSend() {
      if (!this.inputText.trim()) return
      this.$emit('send-message', this.inputText.trim())
      this.inputText = ''
    },
    scrollToBottom() {
      const container = this.$refs.messagesContainer
      if (container) {
        container.scrollTop = container.scrollHeight
      }
    },
    handleMoreCommand(command) {
      if (command === 'delete') {
        this.$emit('delete-conversation')
      }
    },
    handleTabSwitch(key) {
      this.activeTab = key
      if (key !== 'chat') {
        this.$message.info(key === 'agent_config' ? '智能体配置功能即将上线' :
                          key === 'tool_calls' ? '工具调用记录功能即将上线' :
                          '日志功能即将上线')
      }
    },
  },
}
</script>

<style scoped>
.chat-window {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-header {
  height: 60px;
  padding: 0 20px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
  background: #ffffff;
}

.header-left h3 {
  margin: 0;
  font-size: 16px;
  color: #1e293b;
}

.header-left .text-primary {
  color: #4080ff;
}

.participant-count {
  font-size: 12px;
  color: #94a3b8;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #86909c;
}

.header-actions .el-button--text {
  font-size: 16px;
  color: #86909c;
  padding: 6px;
}

.header-actions .el-button--text:hover {
  color: #4080ff;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  background: #fafafa;
}

.messages-container::-webkit-scrollbar {
  width: 4px;
}

.messages-container::-webkit-scrollbar-thumb {
  background: #dcdde1;
  border-radius: 4px;
}

.message-wrapper {
  margin-bottom: 12px;
}

.empty-messages {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #94a3b8;
}

.empty-messages i {
  font-size: 64px;
  margin-bottom: 16px;
  color: #cbd5e1;
}

.empty-messages h2 {
  font-size: 22px;
  color: #1e293b;
  margin-bottom: 8px;
}

.empty-messages .hint {
  font-size: 13px;
  margin-top: 8px;
}

/* 底部标签栏 */
.chat-tabs {
  height: 42px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 8px;
  background: rgba(250,250,250,0.8);
  flex-shrink: 0;
}

.tab-item {
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 12px;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-item:hover {
  background: #f0f0f0;
}

.tab-item.active {
  background: #4080ff;
  color: #fff;
}

/* 飞书风格输入框 */
.message-input {
  height: 68px;
  padding: 10px 16px;
  border-top: 1px solid #f0f0f0;
  flex-shrink: 0;
  background: #ffffff;
}

.input-wrapper {
  display: flex;
  align-items: center;
  background: #f2f3f5;
  border-radius: 8px;
  padding: 0 12px;
  height: 44px;
}

.input-wrapper .feishu-input :deep(.el-input__inner) {
  border: none;
  background: transparent;
  font-size: 14px;
  height: 44px;
  padding: 0;
}

.input-wrapper .feishu-input :deep(.el-input__inner:focus) {
  box-shadow: none;
}

.input-wrapper .feishu-input {
  flex: 1;
}

.send-btn {
  font-size: 18px;
  color: #4080ff;
  padding: 8px;
}

.send-btn:disabled {
  color: #c0c4cc;
}

/* Typing indicator */
.typing-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
}

.typing-dots {
  display: flex;
  align-items: center;
  gap: 4px;
}

.dot {
  width: 8px;
  height: 8px;
  background: #c0d3f0;
  border-radius: 50%;
  animation: typingBounce 1.4s ease-in-out infinite;
}

.dot:nth-child(1) { animation-delay: 0s; }
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes typingBounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-6px); opacity: 1; }
}

.typing-text {
  font-size: 12px;
  color: #94a3b8;
}
</style>
