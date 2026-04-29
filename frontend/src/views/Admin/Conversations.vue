<template>
  <div class="conversations-page">
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>对话列表</span>
              <el-select
                v-model="statusFilter"
                placeholder="状态筛选"
                size="small"
                clearable
                style="width: 120px;"
                @change="loadConversations"
              >
                <el-option label="全部" value="" />
                <el-option label="进行中" value="active" />
                <el-option label="已转接" value="escalated" />
                <el-option label="已关闭" value="closed" />
              </el-select>
            </div>
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
                  <p class="preview">{{ conv.lastMessagePreview || '暂无消息' }}</p>
                </div>
                <div class="conversation-meta">
                  <el-tag :type="getStatusType(conv.status)" size="small">
                    {{ getStatusText(conv.status) }}
                  </el-tag>
                  <span class="time">{{ formatTime(conv.lastMessageTime || conv.startTime) }}</span>
                </div>
              </div>
            </div>
            
            <el-empty v-if="conversations.length === 0 && !isLoading" description="暂无对话" />
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="16">
        <el-card v-if="selectedConversation">
          <template #header>
            <div class="card-header">
              <div>
                <span>对话详情</span>
                <el-tag
                  v-if="selectedConversation.status === 'escalated'"
                  type="warning"
                  size="small"
                  style="margin-left: 12px;"
                >
                  已转接人工
                </el-tag>
              </div>
              <div>
                <el-button
                  v-if="selectedConversation.status === 'active'"
                  type="warning"
                  size="small"
                  @click="handleEscalate"
                >
                  转接人工
                </el-button>
                <el-button
                  v-if="selectedConversation.status !== 'closed'"
                  type="danger"
                  size="small"
                  @click="handleClose"
                >
                  关闭对话
                </el-button>
              </div>
            </div>
          </template>
          
          <div class="chat-messages" ref="messagesContainer" style="height: 500px; overflow-y: auto;">
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
                </div>
                <div v-if="message.isEscalated" class="message-escalated">
                  <el-icon><Warning /></el-icon>
                  已转接人工
                </div>
              </div>
            </div>
            
            <el-empty v-if="conversationMessages.length === 0" description="暂无消息" />
          </div>
          
          <div v-if="selectedConversation.status !== 'closed'" class="chat-input-area" style="margin-top: 16px;">
            <div class="input-wrapper">
              <el-input
                v-model="replyContent"
                type="textarea"
                :rows="2"
                placeholder="输入回复内容..."
                maxlength="500"
                show-word-limit
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
import { ref, computed, onMounted, nextTick } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useAuthStore } from '@/stores/auth'
import { conversationApi } from '@/services/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'

const chatStore = useChatStore()
const authStore = useAuthStore()

const isLoading = ref(false)
const statusFilter = ref('')
const conversations = ref([])
const selectedConversation = ref(null)
const currentConversationId = ref(null)
const conversationMessages = ref([])
const replyContent = ref('')
const messagesContainer = ref(null)

const loadConversations = async () => {
  isLoading.value = true
  
  try {
    let result
    
    if (statusFilter.value === 'escalated') {
      result = await conversationApi.getEscalated()
    } else {
      result = await conversationApi.getActive()
    }
    
    if (result.success) {
      conversations.value = result.data || []
    }
  } catch (error) {
    console.error('Failed to load conversations:', error)
    ElMessage.error('加载对话列表失败')
  } finally {
    isLoading.value = false
  }
}

const selectConversation = async (conv) => {
  selectedConversation.value = conv
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
  if (!selectedConversation.value) return
  
  try {
    await ElMessageBox.confirm('确定要将此对话转接人工客服吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const result = await conversationApi.assignAgent(
      selectedConversation.value.conversationId,
      authStore.user?.id || 'agent_001'
    )
    
    if (result.success) {
      selectedConversation.value.status = 'escalated'
      chatStore.updateConversationStatus(
        selectedConversation.value.conversationId,
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
  if (!selectedConversation.value) return
  
  try {
    await ElMessageBox.confirm('确定要关闭此对话吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const result = await conversationApi.close(selectedConversation.value.conversationId, {})
    
    if (result.success) {
      selectedConversation.value.status = 'closed'
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
  if (!replyContent.value.trim() || !selectedConversation.value) return
  
  try {
    const result = await conversationApi.sendMessage(
      selectedConversation.value.conversationId,
      {
        content: replyContent.value.trim(),
        language: 'zh'
      }
    )
    
    if (result.success) {
      replyContent.value = ''
      selectConversation(selectedConversation.value)
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

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  return dayjs(timestamp).format('MM-DD HH:mm')
}

onMounted(() => {
  loadConversations()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.conversations-page {
  height: 100%;
}
</style>
