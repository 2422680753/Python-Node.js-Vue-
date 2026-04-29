<template>
  <div class="admin-layout">
    <div class="admin-sidebar">
      <div class="admin-sidebar-header">
        <h2>客服管理系统</h2>
      </div>
      
      <div class="admin-sidebar-menu">
        <el-menu
          :default-active="activeMenu"
          background-color="#304156"
          text-color="#bfcbd9"
          active-text-color="#409eff"
          router
        >
          <el-menu-item index="/admin/conversations">
            <el-icon><ChatDotRound /></el-icon>
            <span>对话列表</span>
          </el-menu-item>
          
          <el-menu-item index="/admin/escalated">
            <el-icon><Warning /></el-icon>
            <span>待处理转接</span>
            <el-badge
              v-if="escalatedCount > 0"
              :value="escalatedCount"
              :max="99"
              class="menu-badge"
            />
          </el-menu-item>
          
          <el-menu-item index="/admin/search">
            <el-icon><Search /></el-icon>
            <span>对话搜索</span>
          </el-menu-item>
          
          <el-sub-menu index="system">
            <template #title>
              <el-icon><Setting /></el-icon>
              <span>系统设置</span>
            </template>
            <el-menu-item index="/admin/languages">
              <el-icon><Tickets /></el-icon>
              <span>语言设置</span>
            </el-menu-item>
          </el-sub-menu>
        </el-menu>
      </div>
    </div>
    
    <div class="admin-main">
      <div class="admin-header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/admin' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentPageTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        
        <div class="header-right">
          <el-select
            v-model="currentLanguage"
            placeholder="语言"
            size="small"
            style="width: 120px; margin-right: 16px;"
            @change="changeLanguage"
          >
            <el-option
              v-for="lang in languages"
              :key="lang.code"
              :label="lang.nativeName"
              :value="lang.code"
            />
          </el-select>
          
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32" icon="User" />
              <span style="margin-left: 8px;">{{ user?.name || '客服' }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人信息</el-dropdown-item>
                <el-dropdown-item command="settings">设置</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
      
      <div class="admin-content">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSettingsStore } from '@/stores/settings'
import { useChatStore } from '@/stores/chat'
import { conversationApi } from '@/services/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const settingsStore = useSettingsStore()
const chatStore = useChatStore()

const currentLanguage = ref(settingsStore.language)
const escalatedCount = ref(0)

const user = computed(() => authStore.user)
const languages = computed(() => settingsStore.languages)

const activeMenu = computed(() => {
  return route.path
})

const currentPageTitle = computed(() => {
  const titles = {
    '/admin': '对话列表',
    '/admin/conversations': '对话列表',
    '/admin/escalated': '待处理转接',
    '/admin/search': '对话搜索',
    '/admin/languages': '语言设置'
  }
  return titles[route.path] || '系统管理'
})

const loadEscalatedConversations = async () => {
  try {
    const result = await conversationApi.getEscalated()
    if (result.success) {
      escalatedCount.value = result.data.length
    }
  } catch (error) {
    console.error('Failed to load escalated conversations:', error)
  }
}

onMounted(() => {
  chatStore.connect()
  loadEscalatedConversations()
  
  const interval = setInterval(loadEscalatedConversations, 30000)
  window.escalationInterval = interval
})

onUnmounted(() => {
  if (window.escalationInterval) {
    clearInterval(window.escalationInterval)
  }
})

const changeLanguage = (lang) => {
  currentLanguage.value = lang
  settingsStore.setLanguage(lang)
  ElMessage.success(`已切换到 ${languages.value.find(l => l.code === lang)?.nativeName}`)
}

const handleCommand = (command) => {
  switch (command) {
    case 'profile':
      ElMessage.info('个人信息功能开发中')
      break
    case 'settings':
      ElMessage.info('设置功能开发中')
      break
    case 'logout':
      ElMessageBox.confirm('确定要退出登录吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        authStore.logout()
        chatStore.disconnect()
        router.push('/login')
        ElMessage.success('已退出登录')
      }).catch(() => {})
      break
  }
}
</script>

<style scoped>
.menu-badge {
  margin-left: 8px;
}

.user-info {
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.user-info:hover {
  background-color: #f5f7fa;
}
</style>
