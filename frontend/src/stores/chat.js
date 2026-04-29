import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import io from 'socket.io-client'
import { useAuthStore } from './auth'

export const useChatStore = defineStore('chat', () => {
  const authStore = useAuthStore()
  
  const socket = ref(null)
  const connected = ref(false)
  
  const conversations = ref([])
  const currentConversationId = ref(null)
  const messages = ref([])
  
  const isTyping = ref(false)
  const isLoading = ref(false)
  
  const currentConversation = computed(() => {
    return conversations.value.find(c => c.conversationId === currentConversationId.value)
  })
  
  const currentMessages = computed(() => {
    return messages.value
  })
  
  const connect = () => {
    if (socket.value && connected.value) return
    
    socket.value = io({
      query: {
        userId: authStore.userId
      },
      transports: ['websocket', 'polling']
    })
    
    socket.value.on('connect', () => {
      console.log('Socket connected')
      connected.value = true
    })
    
    socket.value.on('disconnect', () => {
      console.log('Socket disconnected')
      connected.value = false
    })
    
    socket.value.on('conversation-history', (data) => {
      messages.value = data.messages || []
    })
    
    socket.value.on('bot-response', (data) => {
      if (data.message) {
        messages.value.push(data.message)
      }
      isTyping.value = false
    })
    
    socket.value.on('message-queued', (data) => {
      isTyping.value = true
    })
    
    socket.value.on('user-typing', (data) => {
      isTyping.value = data.isTyping
    })
    
    socket.value.on('conversations-escalated', (data) => {
      const conv = conversations.value.find(c => c.conversationId === data.conversationId)
      if (conv) {
        conv.status = 'escalated'
      }
    })
    
    socket.value.on('error', (error) => {
      console.error('Socket error:', error)
    })
  }
  
  const disconnect = () => {
    if (socket.value) {
      socket.value.disconnect()
      socket.value = null
      connected.value = false
    }
  }
  
  const joinConversation = (conversationId) => {
    if (!socket.value || !connected.value) {
      connect()
    }
    
    currentConversationId.value = conversationId
    messages.value = []
    
    socket.value.emit('join-conversation', { conversationId })
  }
  
  const leaveConversation = (conversationId) => {
    if (socket.value && conversationId) {
      socket.value.emit('leave-conversation', { conversationId })
    }
    
    if (currentConversationId.value === conversationId) {
      currentConversationId.value = null
      messages.value = []
    }
  }
  
  const sendMessage = (content, language = 'zh') => {
    if (!socket.value || !connected.value || !currentConversationId.value) {
      return false
    }
    
    const userMessage = {
      messageId: `temp_${Date.now()}`,
      conversationId: currentConversationId.value,
      sender: 'user',
      content: content,
      language: language,
      timestamp: new Date()
    }
    
    messages.value.push(userMessage)
    isTyping.value = true
    
    socket.value.emit('send-message', {
      conversationId: currentConversationId.value,
      content: content,
      language: language
    })
    
    return true
  }
  
  const addConversation = (conversation) => {
    const existing = conversations.value.find(c => c.conversationId === conversation.conversationId)
    if (!existing) {
      conversations.value.unshift(conversation)
    } else {
      Object.assign(existing, conversation)
    }
  }
  
  const setConversations = (newConversations) => {
    conversations.value = newConversations
  }
  
  const updateConversationStatus = (conversationId, status) => {
    const conv = conversations.value.find(c => c.conversationId === conversationId)
    if (conv) {
      conv.status = status
    }
  }
  
  return {
    socket,
    connected,
    conversations,
    currentConversationId,
    messages,
    isTyping,
    isLoading,
    currentConversation,
    currentMessages,
    connect,
    disconnect,
    joinConversation,
    leaveConversation,
    sendMessage,
    addConversation,
    setConversations,
    updateConversationStatus
  }
})
