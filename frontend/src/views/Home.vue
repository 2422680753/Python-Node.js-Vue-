<template>
  <div class="home-container">
    <div class="home-content">
      <h1>跨境电商智能客服</h1>
      <p>支持10种语言的智能客服机器人，快速响应您的需求，复杂问题自动转接人工客服</p>
      
      <div class="action-buttons" style="display: flex; gap: 16px; margin-bottom: 40px;">
        <el-button type="primary" size="large" @click="startChat">
          <el-icon><ChatDotRound /></el-icon>
          开始咨询
        </el-button>
        <el-button size="large" @click="goToLogin">
          <el-icon><User /></el-icon>
          客服登录
        </el-button>
      </div>
      
      <div class="language-selector" style="margin-bottom: 40px;">
        <span style="color: white; margin-right: 12px;">选择语言 / Select Language:</span>
        <el-select v-model="selectedLanguage" placeholder="选择语言" style="width: 200px;" @change="changeLanguage">
          <el-option
            v-for="lang in languages"
            :key="lang.code"
            :label="lang.nativeName"
            :value="lang.code"
          />
        </el-select>
      </div>
      
      <div class="features">
        <div class="feature-card">
          <div class="icon">🌍</div>
          <h3>10种语言支持</h3>
          <p>支持中文、英文、日文、韩文、法文、德文、西班牙文、葡萄牙文、阿拉伯文、俄文</p>
        </div>
        <div class="feature-card">
          <div class="icon">⚡</div>
          <h3>秒级响应</h3>
          <p>智能机器人快速理解您的问题，即时提供专业解答</p>
        </div>
        <div class="feature-card">
          <div class="icon">👥</div>
          <h3>人工转接</h3>
          <p>复杂问题自动识别，无缝转接专业客服人员</p>
        </div>
        <div class="feature-card">
          <div class="icon">🔒</div>
          <h3>隐私保护</h3>
          <p>信用卡号、电话等敏感信息自动打码，保护您的隐私安全</p>
        </div>
        <div class="feature-card">
          <div class="icon">📝</div>
          <h3>对话记录</h3>
          <p>所有对话自动保存，支持关键词搜索，方便追溯</p>
        </div>
        <div class="feature-card">
          <div class="icon">🚀</div>
          <h3>高并发支持</h3>
          <p>每秒处理1000条消息，高峰期稳定运行不崩溃</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'
import { useChatStore } from '@/stores/chat'
import { conversationApi } from '@/services/api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const settingsStore = useSettingsStore()
const chatStore = useChatStore()

const selectedLanguage = ref(settingsStore.language)
const languages = ref(settingsStore.languages)

onMounted(() => {
  chatStore.connect()
})

const changeLanguage = (lang) => {
  settingsStore.setLanguage(lang)
  ElMessage.success(`已切换到 ${languages.value.find(l => l.code === lang)?.nativeName}`)
}

const startChat = async () => {
  try {
    const result = await conversationApi.create({
      language: selectedLanguage.value
    })
    
    if (result.success) {
      chatStore.addConversation(result.data)
      chatStore.joinConversation(result.data.conversationId)
      router.push('/chat')
    }
  } catch (error) {
    console.error('Failed to create conversation:', error)
    ElMessage.error('创建对话失败，请稍后重试')
  }
}

const goToLogin = () => {
  router.push('/login')
}
</script>
