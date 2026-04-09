<template>
  <div class="auth-page">
    <div class="auth-panel">
      <div class="auth-cover">
        <div class="cover-badge">Vehic Insurance</div>
        <h1>车辆保险理赔记录管理系统</h1>
        <p>支持员工使用工号、中文姓名和密码完成注册与登录，登录后会同步展示最近一次访问记录。</p>
      </div>

      <div class="auth-form-wrap">
        <el-tabs v-model="activeTab" stretch>
          <el-tab-pane label="登录" name="login">
            <el-form ref="loginFormRef" :model="loginForm" :rules="loginRules" label-position="top">
              <el-form-item label="员工工号" prop="employeeNo">
                <el-input v-model="loginForm.employeeNo" maxlength="6" placeholder="请输入6位工号" />
              </el-form-item>
              <el-form-item label="密码" prop="password">
                <el-input v-model="loginForm.password" show-password placeholder="请输入密码" />
              </el-form-item>
              <el-button type="primary" class="full-btn" @click="handleLogin(loginFormRef)">登录</el-button>
            </el-form>
          </el-tab-pane>

          <el-tab-pane label="注册" name="register">
            <el-form ref="registerFormRef" :model="registerForm" :rules="registerRules" label-position="top">
              <el-form-item label="员工工号" prop="employeeNo">
                <el-input v-model="registerForm.employeeNo" maxlength="6" placeholder="请输入6位工号" />
              </el-form-item>
              <el-form-item label="中文姓名" prop="name">
                <el-input v-model="registerForm.name" placeholder="请输入中文姓名" />
              </el-form-item>
              <el-form-item label="密码" prop="password">
                <el-input v-model="registerForm.password" show-password placeholder="请设置登录密码" />
              </el-form-item>
              <el-form-item label="角色" prop="role">
                <el-select v-model="registerForm.role" style="width: 100%">
                  <el-option label="普通用户" value="USER" />
                  <el-option label="管理员" value="ADMIN" />
                </el-select>
              </el-form-item>
              <el-form-item label="注册口令" prop="registerCode">
                <el-input v-model="registerForm.registerCode" placeholder="请输入注册口令" />
              </el-form-item>
              <el-button type="primary" class="full-btn" @click="handleRegister(registerFormRef)">注册并进入系统</el-button>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import request from '@/utils/request'
import { setCurrentUser } from '@/utils/auth'

const router = useRouter()
const activeTab = ref('login')
const loginFormRef = ref()
const registerFormRef = ref()

const loginForm = ref({
  employeeNo: '',
  password: '',
})

const registerForm = ref({
  employeeNo: '',
  name: '',
  password: '',
  role: 'USER',
  registerCode: '',
})

const validateEmployeeNo = (rule, value, callback) => {
  if (!/^\d{6}$/.test(value || '')) {
    callback(new Error('请输入6位数字工号'))
    return
  }
  callback()
}

const validateName = (rule, value, callback) => {
  if (!value || !value.trim()) {
    callback(new Error('请输入中文姓名'))
    return
  }
  callback()
}

const loginRules = {
  employeeNo: [{ required: true, validator: validateEmployeeNo, trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const registerRules = {
  employeeNo: [{ required: true, validator: validateEmployeeNo, trigger: 'blur' }],
  name: [{ required: true, validator: validateName, trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  registerCode: [{ required: true, message: '请输入注册口令', trigger: 'blur' }],
}

const handleAuthSuccess = (res) => {
  setCurrentUser(res.data.user)
  ElMessage.success(res.data.loginMessage)
  router.push('/home')
}

const handleLogin = async (formEl) => {
  if (!formEl) return
  await formEl.validate(async (valid) => {
    if (!valid) return
    const res = await request.post('/auth/login', loginForm.value)
    if (res.code === '200') {
      handleAuthSuccess(res)
    } else {
      ElMessage.error(res.msg)
    }
  })
}

const handleRegister = async (formEl) => {
  if (!formEl) return
  await formEl.validate(async (valid) => {
    if (!valid) return
    const res = await request.post('/auth/register', registerForm.value)
    if (res.code === '200') {
      handleAuthSuccess(res)
    } else {
      ElMessage.error(res.msg)
    }
  })
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(17, 169, 131, 0.2), transparent 35%),
    radial-gradient(circle at bottom right, rgba(11, 87, 208, 0.18), transparent 30%),
    linear-gradient(135deg, #f4f9f7, #edf3fb);
}

.auth-panel {
  width: min(1080px, 100%);
  min-height: 620px;
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  background: rgba(255, 255, 255, 0.92);
  border-radius: 28px;
  overflow: hidden;
  box-shadow: 0 24px 80px rgba(25, 53, 89, 0.12);
}

.auth-cover {
  padding: 56px 48px;
  color: #fff;
  background:
    linear-gradient(160deg, rgba(10, 88, 76, 0.9), rgba(17, 169, 131, 0.85)),
    linear-gradient(45deg, #0f766e, #0ea5a5);
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.auth-cover h1 {
  margin: 0 0 18px;
  font-size: 40px;
  line-height: 1.2;
}

.auth-cover p {
  margin: 0;
  max-width: 440px;
  font-size: 15px;
  line-height: 1.8;
  color: rgba(255, 255, 255, 0.88);
}

.cover-badge {
  width: fit-content;
  margin-bottom: 18px;
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
  letter-spacing: 0.08em;
  font-size: 12px;
  text-transform: uppercase;
}

.auth-form-wrap {
  padding: 48px 42px;
  display: flex;
  align-items: center;
}

.auth-form-wrap :deep(.el-tabs) {
  width: 100%;
}

.auth-form-wrap :deep(.el-tabs__header) {
  margin-bottom: 28px;
}

.full-btn {
  width: 100%;
  margin-top: 10px;
  height: 44px;
}

@media (max-width: 900px) {
  .auth-panel {
    grid-template-columns: 1fr;
  }

  .auth-cover {
    padding: 36px 28px;
  }

  .auth-form-wrap {
    padding: 32px 24px 36px;
  }

  .auth-cover h1 {
    font-size: 30px;
  }
}
</style>
