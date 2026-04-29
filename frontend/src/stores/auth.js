import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { v4 as uuidv4 } from 'uuid'

const generateUserId = () => `user_${uuidv4().replace(/-/g, '')}`

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  const userId = ref(localStorage.getItem('userId') || generateUserId())
  
  const isAuthenticated = computed(() => !!token.value)
  const isAgent = computed(() => user.value?.role === 'agent' || user.value?.role === 'admin')
  
  if (!localStorage.getItem('userId')) {
    localStorage.setItem('userId', userId.value)
  }
  
  const setToken = (newToken) => {
    token.value = newToken
    localStorage.setItem('token', newToken)
  }
  
  const setUser = (newUser) => {
    user.value = newUser
    localStorage.setItem('user', JSON.stringify(newUser))
  }
  
  const login = async (credentials) => {
    if (credentials.role === 'agent') {
      const mockUser = {
        id: 'agent_001',
        name: credentials.username || 'Agent',
        email: `${credentials.username}@company.com`,
        role: 'agent',
        languages: ['zh', 'en']
      }
      setUser(mockUser)
      setToken('mock_token_' + Date.now())
      return { success: true, user: mockUser }
    }
    return { success: true }
  }
  
  const logout = () => {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }
  
  return {
    token,
    user,
    userId,
    isAuthenticated,
    isAgent,
    setToken,
    setUser,
    login,
    logout
  }
})
