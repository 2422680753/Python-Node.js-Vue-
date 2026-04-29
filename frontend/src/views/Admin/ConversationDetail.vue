<template>
  <div class="conversation-detail-page">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card>
          <template #header>
            <span>对话列表</span>
          </template>
          
          <div class="conversation-list" v-loading="isLoading">
            <div
              v-for="conv in conversations"
              :key="conv.conversationId"
              :class="['conversation-item', { active: currentConversationId === conv.conversationId }]"
              @click="selectConversation(conv)"
            >
              <div class="conversation-info">
                <div>
                  <h4>{{ conv.conversationId.slice(0, 12) }}...</h4>
                  <el-tag :type="getStatusType(conv.status)" size="small" style="margin-top: 4px;">
                    {{ getStatusText(conv.status) }}
                  </el-tag>
                </div>
                <span class="time">{{ formatTime(conv.lastMessageTime || conv.startTime) }}</span>
              </div>
            </div>
            
            <el-empty v-if="conversations.length === 0 && !isLoading" description="暂无对话" />
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="18">
        <el-card v-if="currentConversation">
          <template #header>
            <div class="card-header">
              <div>
                <span>对话详情</span>
                <el-tag
                  v-if="currentConversation.status === 'escalated'"
                  type="warning"
                  size="small"
                  style="margin-left: 12px;"
                >
                  已转接人工
                </el-tag>
              </div>
              <div>
                <el-button
                  v-if="currentConversation.status === 'active'"
                  type="warning"
                  size="small"
                  @click="handleEscalate"
                >
                  转接人工
                </el-button>
                <el-button
                  v-if="currentConversation.status !== 'closed'"
                  type="danger"
                  size="small"
                  @click="handleClose"
                >
                  关闭对话
                </el-button>
              </div>
            </div>
          </template>
          
          <el-descriptions :column="4" border style="margin-bottom: 20px;">
            <el-descriptions-item label="对话ID">
              {{ currentConversation.conversationId }}
            </el-descriptions-item>
            <el-descriptions-item label="用户ID">
              {{ currentConversation.userId }}
            </el-descriptions-item>
            <el-descriptions-item label="用户语言">
              {{ getLanguageName(currentConversation.userLanguage) }}
            </el-descriptions-item>
            <el-descriptions-item label="消息数">
              {{ currentConversation.messageCount }}
            </el-descriptions-item>
            <el-descriptions-item label="开始时间" :span="2">
              {{ formatTime(currentConversation.startTime) }}
            </el-descriptions-item>
            <el-descriptions-item label="最后消息时间" :span="2">
              {{ formatTime(currentConversation.lastMessageTime) }}
            </el-descriptions-item>
            <el-descriptions-item label="涉及意图" :span="4">
              <el-tag
                v-for="intent in currentConversation.intents || []"
                :key="intent"
                size="small"
                type="warning"
                effect="light"
                style="margin-right: 8px;"
              >
                {{ getIntentText(intent) }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
          
          <div class="chat-messages" ref="messagesContainer" style="height: 400px; overflow-y: auto; border: 1px solid #e4e7ed; border-radius: 8px; padding: 16px;">
            <div
              v-for="(message, index) in conversationMessages"
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
                  <span v-if="message.isSensitive" style="margin-left: 8px; color: #e6a23c;">
                    [含敏感信息]
                  </span>
                  <span v-if="message.intent" style="margin-left: 8px; color: #909399; font-size: 11px;">
                    意图: {{ getIntentText(message.intent) }}
                    <span v-if="message.confidence" style="margin-left: 4px;">
                      ({{ (message.confidence * 100).toFixed(0) }}%)
                    </span>
                  </span>
                </div>
                <div v-if="message.isEscalated" class="message-escalated">
                  <el-icon><Warning /></el-icon>
                  已转接人工
                </div>
              </div>
            </div>
            
            <el-empty v-if="conversationMessages.length === 0" description="暂无消息" />
          </div>
          
          <div v-if="currentConversation.status !== 'closed'" class="chat-input-area" style="margin-top: 16px;">
            <div class="input-wrapper">
              <el-input
                v-model="replyContent"
                type="textarea"
                :rows="2"
                placeholder="输入回复内容..."
                maxlength="500"
                show-word-limit
                @keyup.enter.exact="sendReply"
              />
              <el-button
                type="primary"
                size="large"
                :disabled="!replyContent.trim()"
                @click="sendReply"
              >
                发送
              </el-button>
            </div>
          </div>
        </el-card>
        
        <el-card v-else>
          <el-empty description="请选择一个对话查看详情" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import { conversationApi } from '@/services/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()
const settingsStore = useSettingsStore()
const authStore = useAuthStore()
const chatStore = useChatStore()

const isLoading = ref(false)
const conversations = ref([])
const currentConversation = ref(null)
const currentConversationId = ref(null)
const conversationMessages = ref([])
const replyContent = ref('')
const messagesContainer = ref(null)

const loadConversations = async () => {
  isLoading.value = true
  
  try {
    const activeResult = await conversationApi.getActive()
    const escalatedResult = await conversationApi.getEscalated()
    
    const active = activeResult.success ? activeResult.data || [] : []
    const escalated = escalatedResult.success ? escalatedResult.data || [] : []
    
    conversations.value = [...escalated, ...active]
  } catch (error) {
    console.error('Failed to load conversations:', error)
  } finally {
    isLoading.value = false
  }
}

const selectConversation = async (conv) => {
  currentConversation.value = conv
  currentConversationId.value = conv.conversationId
  
  try {
    const result = await conversationApi.getMessages(conv.conversationId, { limit: 100 })
    if (result.success) {
      conversationMessages.value = result.data || []
      nextTick(() => {
        if (messagesContainer.value) {
          messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
        }
      })
    }
  } catch (error) {
    console.error('Failed to load messages:', error)
    ElMessage.error('加载消息失败')
  }
}

const handleEscalate = async () => {
  if (!currentConversation.value) return
  
  try {
    await ElMessageBox.confirm('确定要将此对话转接人工客服吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const result = await conversationApi.assignAgent(
      currentConversation.value.conversationId,
      authStore.user?.id || 'agent_001'
    )
    
    if (result.success) {
      currentConversation.value.status = 'escalated'
      chatStore.updateConversationStatus(
        currentConversation.value.conversationId,
        'escalated'
      )
      ElMessage.success('已转接人工客服')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to escalate:', error)
      ElMessage.error('转接失败')
    }
  }
}

const handleClose = async () => {
  if (!currentConversation.value) return
  
  try {
    await ElMessageBox.confirm('确定要关闭此对话吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const result = await conversationApi.close(currentConversation.value.conversationId, {})
    
    if (result.success) {
      currentConversation.value.status = 'closed'
      ElMessage.success('对话已关闭')
      loadConversations()
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to close:', error)
      ElMessage.error('关闭失败')
    }
  }
}

const sendReply = async () => {
  if (!replyContent.value.trim() || !currentConversation.value) return
  
  try {
    const result = await conversationApi.sendMessage(
      currentConversation.value.conversationId,
      {
        content: replyContent.value.trim(),
        language: 'zh'
      }
    )
    
    if (result.success) {
      replyContent.value = ''
      selectConversation(currentConversation.value)
      ElMessage.success('发送成功')
    }
  } catch (error) {
    console.error('Failed to send reply:', error)
    ElMessage.error('发送失败')
  }
}

const getStatusType = (status) => {
  const types = {
    active: 'success',
    escalated: 'warning',
    closed: 'info'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    active: '进行中',
    escalated: '已转接',
    closed: '已关闭'
  }
  return texts[status] || status
}

const getLanguageName = (code) => {
  const lang = settingsStore.languages.find(l => l.code === code)
  return lang ? lang.nativeName : code
}

const getIntentText = (intent) => {
  const intentTexts = {
    greeting: '问候',
    order_status: '订单状态',
    refund: '退款退货',
    complaint: '投诉',
    payment: '支付问题',
    technical_support: '技术支持',
    product_info: '产品信息',
    shipping_info: '配送信息',
    unknown: '未知'
  }
  return intentTexts[intent] || intent
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  return dayjs(timestamp).format('YYYY-MM-DD HH:mm:ss')
}

onMounted(() => {
  loadConversations()
  
  if (route.params.id) {
    currentConversationId.value = route.params.id
  }
})

watch(conversations, (newConversations) => {
  if (currentConversationId.value && newConversations.length > 0) {
    const conv = newConversations.find(c => c.conversationId === currentConversationId.value)
    if (conv) {
      selectConversation(conv)
    }
  }
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.conversation-detail-page {
  height: 100%;
}
</style>
