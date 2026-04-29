<template>
  <div class="chat-container">
    <div class="chat-header">
      <div class="header-left">
        <el-button text type="primary" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <h3>智能客服</h3>
        <el-tag v-if="isEscalated" type="warning" effect="light" style="margin-left: 12px;">
          已转接人工
        </el-tag>
      </div>
      <div class="header-right">
        <el-select v-model="currentLanguage" placeholder="语言" size="small" style="width: 120px;" @change="changeLanguage">
          <el-option
            v-for="lang in languages"
            :key="lang.code"
            :label="lang.nativeName"
            :value="lang.code"
          />
        </el-select>
      </div>
    </div>
    
    <div class="chat-messages" ref="messagesContainer">
      <div
        v-for="(message, index) in messages"
        :key="message.messageId || index"
        :class="['message-item', message.sender]"
      >
        <div :class="['message-avatar', message.sender]">
          <el-icon v-if="message.sender === 'user'"><User /></el-icon>
          <el-icon v-else-if="message.sender === 'bot'"><Service /></el-icon>
          <el-icon v-else><Avatar /></el-icon>
        </div>
        <div class="message-content">
          <div class="message-bubble">{{ message.content }}</div>
          <div class="message-time">
            {{ formatTime(message.timestamp) }}
          </div>
          <div v-if="message.isEscalated" class="message-escalated">
            <el-icon><Warning /></el-icon>
            已转接人工客服
          </div>
        </div>
      </div>
      
      <div v-if="isTyping" class="message-item bot">
        <div class="message-avatar bot">
          <el-icon><Service /></el-icon>
        </div>
        <div class="typing-indicator">
          <div class="dot"></div>
          <div class="dot"></div>
          <div class="dot"></div>
        </div>
      </div>
    </div>
    
    <div class="chat-input-area">
      <div class="input-wrapper">
        <el-input
          v-model="inputValue"
          type="textarea"
          :rows="2"
          placeholder="请输入您的问题..."
          maxlength="500"
          show-word-limit
          @keydown.enter.exact="handleSend"
        />
        <el-button
          type="primary"
          size="large"
          :disabled="!inputValue.trim() || isSending"
          @click="handleSend"
          :loading="isSending"
        >
          <el-icon><Promotion /></el-icon>
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import { useSettingsStore } from '@/stores/settings'
import { useAuthStore } from '@/stores/auth'
import { conversationApi } from '@/services/api'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'

const router = useRouter()
const chatStore = useChatStore()
const settingsStore = useSettingsStore()
const authStore = useAuthStore()

const messagesContainer = ref(null)
const inputValue = ref('')
const isSending = ref(false)
const currentLanguage = ref(settingsStore.language)

const messages = computed(() => chatStore.currentMessages)
const isTyping = computed(() => chatStore.isTyping)
const currentConversation = computed(() => chatStore.currentConversation)

const isEscalated = computed(() => {
  return currentConversation.value?.status === 'escalated' ||
    messages.value.some(m => m.isEscalated)
})

const languages = computed(() => settingsStore.languages)

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

watch(messages, () => {
  scrollToBottom()
}, { deep: true })

onMounted(() => {
  chatStore.connect()
  scrollToBottom()
})

onUnmounted(() => {
  if (chatStore.currentConversationId) {
    chatStore.leaveConversation(chatStore.currentConversationId)
  }
})

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  return dayjs(timestamp).format('HH:mm')
}

const changeLanguage = (lang) => {
  currentLanguage.value = lang
  settingsStore.setLanguage(lang)
  ElMessage.success(`已切换到 ${languages.value.find(l => l.code === lang)?.nativeName}`)
}

const handleSend = async () => {
  if (!inputValue.value.trim() || isSending.value) return
  
  const content = inputValue.value.trim()
  inputValue.value = ''
  isSending.value = true
  
  try {
    const sent = chatStore.sendMessage(content, currentLanguage.value)
    if (!sent) {
      ElMessage.error('发送失败，请检查网络连接')
    }
  } catch (error) {
    console.error('Send message error:', error)
    ElMessage.error('发送失败，请稍后重试')
  } finally {
    isSending.value = false
  }
}

const goBack = () => {
  router.push('/')
}
</script>
