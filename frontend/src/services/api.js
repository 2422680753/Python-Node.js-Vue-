import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export const conversationApi = {
  create: (data) => api.post('/conversations', data),
  get: (conversationId) => api.get(`/conversations/${conversationId}`),
  getMessages: (conversationId, params) => 
    api.get(`/conversations/${conversationId}/messages`, { params }),
  sendMessage: (conversationId, data) => 
    api.post(`/conversations/${conversationId}/messages`, data),
  close: (conversationId, data) => 
    api.post(`/conversations/${conversationId}/close`, data),
  getActive: () => api.get('/conversations/status/active'),
  getEscalated: () => api.get('/conversations/status/escalated'),
  assignAgent: (conversationId, agentId) => 
    api.post(`/conversations/${conversationId}/assign-agent`, { agentId })
}

export const searchApi = {
  messages: (query, filters) => 
    api.get('/search/messages', { params: { query, ...filters } })
}

export const languageApi = {
  getSupported: () => api.get('/languages')
}

export const healthApi = {
  check: () => api.get('/health')
}

export default api
