import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: { title: 'Customer Service' }
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/views/Chat.vue'),
    meta: { title: 'Chat', requiresAuth: true }
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('@/views/Admin/Dashboard.vue'),
    meta: { title: 'Admin Dashboard', requiresAuth: true, requiresAgent: true },
    children: [
      {
        path: '',
        name: 'AdminDashboard',
        component: () => import('@/views/Admin/Conversations.vue'),
        meta: { title: 'Conversations' }
      },
      {
        path: 'conversations',
        name: 'AdminConversations',
        component: () => import('@/views/Admin/Conversations.vue'),
        meta: { title: 'Conversations' }
      },
      {
        path: 'conversations/:id',
        name: 'AdminConversationDetail',
        component: () => import('@/views/Admin/ConversationDetail.vue'),
        meta: { title: 'Conversation Detail' }
      },
      {
        path: 'search',
        name: 'AdminSearch',
        component: () => import('@/views/Admin/Search.vue'),
        meta: { title: 'Search Messages' }
      },
      {
        path: 'escalated',
        name: 'AdminEscalated',
        component: () => import('@/views/Admin/Escalated.vue'),
        meta: { title: 'Escalated Conversations' }
      }
    ]
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: 'Login' }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: { title: 'Page Not Found' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  document.title = `${to.meta.title || 'Customer Service'} | Chatbot`
  
  const authStore = useAuthStore()
  
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }
  
  if (to.meta.requiresAgent && !authStore.isAgent) {
    next({ name: 'Home' })
    return
  }
  
  next()
})

export default router
