<template>
  <div class="login-container">
    <div class="login-card">
      <h2>客服系统登录</h2>
      
      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        label-position="top"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名"
            prefix-icon="User"
          />
        </el-form-item>
        
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        
        <el-form-item label="角色" prop="role">
          <el-radio-group v-model="loginForm.role">
            <el-radio value="agent">客服人员</el-radio>
            <el-radio value="admin">管理员</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="isLoading"
            @click="handleLogin"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>
      
      <div style="text-align: center; margin-top: 20px;">
        <el-link type="primary" @click="goBack">返回首页</el-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const loginFormRef = ref(null)
const isLoading = ref(false)

const loginForm = reactive({
  username: '',
  password: '',
  role: 'agent'
})

const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 4, message: '密码长度不能少于4位', trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  if (!loginFormRef.value) return
  
  await loginFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    isLoading.value = true
    
    try {
      const result = await authStore.login(loginForm)
      
      if (result.success) {
        ElMessage.success('登录成功')
        
        const redirect = route.query.redirect || '/admin'
        router.push(redirect)
      } else {
        ElMessage.error('登录失败，请检查用户名和密码')
      }
    } catch (error) {
      console.error('Login error:', error)
      ElMessage.error('登录失败，请稍后重试')
    } finally {
      isLoading.value = false
    }
  })
}

const goBack = () => {
  router.push('/')
}
</script>
