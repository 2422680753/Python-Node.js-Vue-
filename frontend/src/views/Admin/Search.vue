<template>
  <div class="search-page">
    <el-card>
      <template #header>
        <span>对话搜索</span>
      </template>
      
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="关键词">
          <el-input
            v-model="searchForm.query"
            placeholder="请输入搜索关键词"
            style="width: 300px;"
            clearable
            @keyup.enter="handleSearch"
          >
            <template #append>
              <el-button :icon="Search" @click="handleSearch" />
            </template>
          </el-input>
        </el-form-item>
        
        <el-form-item label="语言">
          <el-select v-model="searchForm.language" placeholder="全部语言" clearable>
            <el-option
              v-for="lang in languages"
              :key="lang.code"
              :label="lang.nativeName"
              :value="lang.code"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="发送者">
          <el-select v-model="searchForm.sender" placeholder="全部" clearable>
            <el-option label="用户" value="user" />
            <el-option label="机器人" value="bot" />
            <el-option label="人工客服" value="agent" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="searchForm.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch" :loading="isSearching">
            搜索
          </el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <el-card style="margin-top: 20px;">
      <template #header>
        <div class="card-header">
          <span>搜索结果</span>
          <span v-if="searchResults.length > 0" style="color: #909399; font-size: 13px;">
            共 {{ searchResults.length }} 条结果
          </span>
        </div>
      </template>
      
      <div class="search-results" v-loading="isSearching">
        <div
          v-for="(result, index) in searchResults"
          :key="result.messageId || index"
          class="search-result-item"
          @click="viewConversation(result.conversationId)"
        >
          <div class="result-header">
            <el-tag :type="getSenderType(result.sender)" size="small">
              {{ getSenderText(result.sender) }}
            </el-tag>
            <span class="message-id" style="color: #909399; font-size: 12px; margin-left: 12px;">
              对话ID: {{ result.conversationId?.slice(0, 15) }}...
            </span>
            <span class="message-time" style="margin-left: auto; color: #c0c4cc; font-size: 12px;">
              {{ formatTime(result.timestamp) }}
            </span>
          </div>
          <div class="result-content" style="margin-top: 8px;">
            <p v-html="highlightText(result.content, searchForm.query)"></p>
          </div>
          <div class="result-meta" style="margin-top: 8px; display: flex; gap: 12px; font-size: 12px; color: #909399;">
            <span v-if="result.language">
              语言: {{ getLanguageName(result.language) }}
            </span>
            <span v-if="result.intent">
              意图: {{ result.intent }}
            </span>
            <span v-if="result.isSensitive">
              <el-tag type="warning" size="small">含敏感信息</el-tag>
            </span>
            <span v-if="result.isEscalated">
              <el-tag type="danger" size="small">已转接人工</el-tag>
            </span>
          </div>
        </div>
        
        <el-empty
          v-if="!isSearching && searchResults.length === 0 && hasSearched"
          description="没有找到匹配的消息"
        />
        
        <el-empty
          v-if="!hasSearched"
          description="请输入关键词开始搜索"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'
import { searchApi } from '@/services/api'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'

const router = useRouter()
const settingsStore = useSettingsStore()

const isSearching = ref(false)
const hasSearched = ref(false)
const searchResults = ref([])

const languages = computed(() => settingsStore.languages)

const searchForm = ref({
  query: '',
  language: '',
  sender: '',
  dateRange: null
})

const handleSearch = async () => {
  if (!searchForm.value.query.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }
  
  isSearching.value = true
  
  try {
    const filters = {}
    
    if (searchForm.value.language) {
      filters.language = searchForm.value.language
    }
    if (searchForm.value.sender) {
      filters.sender = searchForm.value.sender
    }
    if (searchForm.value.dateRange && searchForm.value.dateRange.length === 2) {
      filters.startDate = searchForm.value.dateRange[0]
      filters.endDate = searchForm.value.dateRange[1]
    }
    
    const result = await searchApi.messages(searchForm.value.query, filters)
    
    if (result.success) {
      searchResults.value = result.data || []
      hasSearched.value = true
    }
  } catch (error) {
    console.error('Search failed:', error)
    ElMessage.error('搜索失败，请稍后重试')
  } finally {
    isSearching.value = false
  }
}

const resetSearch = () => {
  searchForm.value = {
    query: '',
    language: '',
    sender: '',
    dateRange: null
  }
  searchResults.value = []
  hasSearched.value = false
}

const highlightText = (text, query) => {
  if (!query || !text) return text
  
  const regex = new RegExp(`(${query})`, 'gi')
  return text.replace(regex, '<span class="highlight">$1</span>')
}

const viewConversation = (conversationId) => {
  if (conversationId) {
    router.push(`/admin/conversations/${conversationId}`)
  }
}

const getSenderType = (sender) => {
  const types = {
    user: 'primary',
    bot: 'success',
    agent: 'warning'
  }
  return types[sender] || 'info'
}

const getSenderText = (sender) => {
  const texts = {
    user: '用户',
    bot: '机器人',
    agent: '人工客服'
  }
  return texts[sender] || sender
}

const getLanguageName = (code) => {
  const lang = languages.value.find(l => l.code === code)
  return lang ? lang.nativeName : code
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  return dayjs(timestamp).format('YYYY-MM-DD HH:mm:ss')
}
</script>

<style scoped>
.search-form {
  margin-bottom: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-result-item {
  cursor: pointer;
  transition: background-color 0.2s;
}

.search-result-item:hover {
  background-color: #f5f7fa;
}

.result-header {
  display: flex;
  align-items: center;
}
</style>
