<template>
  <div class="escalated-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>待处理转接</span>
          <el-button type="primary" size="small" @click="loadEscalated">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>
      
      <el-table
        :data="escalatedConversations"
        v-loading="isLoading"
        style="width: 100%"
        @row-click="handleRowClick"
        row-key="conversationId"
      >
        <el-table-column prop="conversationId" label="对话ID" width="200">
          <template #default="{ row }">
            <span>{{ row.conversationId?.slice(0, 15) }}...</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="userId" label="用户ID" width="150">
          <template #default="{ row }">
            <span>{{ row.userId?.slice(0, 12) }}...</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="userLanguage" label="用户语言" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ getLanguageName(row.userLanguage) }}</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="messageCount" label="消息数" width="80" />
        
        <el-table-column prop="intents" label="涉及意图" min-width="200">
          <template #default="{ row }">
            <div class="intent-tags">
              <el-tag
                v-for="intent in (row.intents || []).slice(0, 3)"
                :key="intent"
                size="small"
                type="warning"
                effect="light"
                style="margin-right: 4px; margin-bottom: 4px;"
              >
                {{ getIntentText(intent) }}
              </el-tag>
              <el-tag
                v-if="(row.intents || []).length > 3"
                size="small"
                effect="plain"
              >
                +{{ (row.intents || []).length - 3 }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="currentAgent" label="当前分配" width="120">
          <template #default="{ row }">
            <span v-if="row.currentAgent" style="color: #67c23a;">
              {{ row.currentAgent?.slice(0, 10) }}
            </span>
            <span v-else style="color: #e6a23c;">待分配</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="lastMessageTime" label="最后消息时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.lastMessageTime) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click.stop="viewDetail(row)">
              查看详情
            </el-button>
            <el-button
              v-if="!row.currentAgent"
              type="success"
              size="small"
              @click.stop="assignSelf(row)"
            >
              接管
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <el-empty
        v-if="!isLoading && escalatedConversations.length === 0"
        description="暂无待处理转接"
      />
    </el-card>
    
    <el-dialog
      v-model="detailVisible"
      title="对话详情"
      width="800px"
      :close-on-click-modal="false"
    >
      <div v-if="selectedConversation" class="conversation-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="对话ID">
            {{ selectedConversation.conversationId }}
          </el-descriptions-item>
          <el-descriptions-item label="用户ID">
            {{ selectedConversation.userId }}
          </el-descriptions-item>
          <el-descriptions-item label="用户语言">
            {{ getLanguageName(selectedConversation.userLanguage) }}
          </el-descriptions-item>
          <el-descriptions-item label="消息数">
            {{ selectedConversation.messageCount }}
          </el-descriptions-item>
          <el-descriptions-item label="涉及意图" :span="2">
            <el-tag
              v-for="intent in selectedConversation.intents || []"
              :key="intent"
              size="small"
              type="warning"
              effect="light"
              style="margin-right: 8px;"
            >
              {{ getIntentText(intent) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="开始时间">
            {{ formatTime(selectedConversation.startTime) }}
          </el-descriptions-item>
          <el-descriptions-item label="最后消息时间">
            {{ formatTime(selectedConversation.lastMessageTime) }}
          </el-descriptions-item>
        </el-descriptions>
        
        <div style="margin-top: 20px;">
          <h4 style="margin-bottom: 12px;">最新消息</h4>
          <div class="chat-messages" style="max-height: 300px; overflow-y: auto;">
            <div
              v-for="(msg, index) in conversationMessages.slice(-5)"
              :key="msg.messageId || index"
              :class="['message-item', msg.sender]"
            >
              <div :class="['message-avatar', msg.sender]">
                <el-icon v-if="msg.sender === 'user'"><User /></el-icon>
                <el-icon v-else-if="msg.sender === 'bot'"><Service /></el-icon>
                <el-icon v-else><Avatar /></el-icon>
              </div>
              <div class="message-content">
                <div class="message-bubble">{{ msg.content }}</div>
                <div class="message-time">{{ formatTime(msg.timestamp) }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <template #footer>
        <el-button @click="detailVisible = false">取消</el-button>
        <el-button
          v-if="!selectedConversation?.currentAgent"
          type="success"
          @click="handleAssign"
        >
          接管并处理
        </el-button>
        <el-button type="primary" @click="goToDetail">
          查看完整对话
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'
import { useAuthStore } from '@/stores/auth'
import { conversationApi } from '@/services/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'

const router = useRouter()
const settingsStore = useSettingsStore()
const authStore = useAuthStore()

const isLoading = ref(false)
const escalatedConversations = ref([])
const detailVisible = ref(false)
const selectedConversation = ref(null)
const conversationMessages = ref([])

const loadEscalated = async () => {
  isLoading.value = true
  
  try {
    const result = await conversationApi.getEscalated()
    
    if (result.success) {
      escalatedConversations.value = result.data || []
    }
  } catch (error) {
    console.error('Failed to load escalated conversations:', error)
    ElMessage.error('加载待处理转接失败')
  } finally {
    isLoading.value = false
  }
}

const handleRowClick = (row) => {
  viewDetail(row)
}

const viewDetail = async (row) => {
  selectedConversation.value = row
  
  try {
    const result = await conversationApi.getMessages(row.conversationId, { limit: 50 })
    if (result.success) {
      conversationMessages.value = result.data || []
    }
  } catch (error) {
    console.error('Failed to load messages:', error)
  }
  
  detailVisible.value = true
}

const assignSelf = async (row) => {
  try {
    await ElMessageBox.confirm('确定要接管此对话吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const result = await conversationApi.assignAgent(
      row.conversationId,
      authStore.user?.id || 'agent_001'
    )
    
    if (result.success) {
      row.currentAgent = authStore.user?.id || 'agent_001'
      ElMessage.success('接管成功')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to assign:', error)
      ElMessage.error('接管失败')
    }
  }
}

const handleAssign = async () => {
  if (!selectedConversation.value) return
  
  try {
    const result = await conversationApi.assignAgent(
      selectedConversation.value.conversationId,
      authStore.user?.id || 'agent_001'
    )
    
    if (result.success) {
      selectedConversation.value.currentAgent = authStore.user?.id || 'agent_001'
      detailVisible.value = false
      ElMessage.success('接管成功')
      goToDetail()
    }
  } catch (error) {
    console.error('Failed to assign:', error)
    ElMessage.error('接管失败')
  }
}

const goToDetail = () => {
  if (selectedConversation.value) {
    detailVisible.value = false
    router.push(`/admin/conversations/${selectedConversation.value.conversationId}`)
  }
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
  if (!timestamp) return '-'
  return dayjs(timestamp).format('YYYY-MM-DD HH:mm:ss')
}

onMounted(() => {
  loadEscalated()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.intent-tags {
  display: flex;
  flex-wrap: wrap;
}

.conversation-detail {
  padding: 10px 0;
}
</style>
