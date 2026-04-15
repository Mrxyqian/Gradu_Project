<template>
  <div class="auth-page">
    <div class="auth-panel">
      <div class="auth-cover">
        <div class="cover-orb cover-orb-a"></div>
        <div class="cover-orb cover-orb-b"></div>
        <div class="cover-grid"></div>
        <div class="cover-badge">Vehicle Claim Platform</div>
        <h1>车险理赔预测系统</h1>
        <div class="cover-tags">
          <span>实用</span>
          <span>高效</span>
          <span>稳定</span>
          <span>安全</span>
        </div>
      </div>

      <div class="auth-form-wrap">
        <div class="auth-form-panel">
          <div class="form-header">
            <div class="form-title">欢迎登录</div>
          </div>

          <el-tabs v-model="activeTab" stretch>
            <el-tab-pane label="登录" name="login">
              <el-form ref="loginFormRef" :model="loginForm" :rules="loginRules" label-position="top">
                <el-form-item label="员工工号" prop="employeeNo">
                  <el-input v-model="loginForm.employeeNo" maxlength="6" placeholder="请输入6位工号" />
                </el-form-item>
                <el-form-item label="密码" prop="password">
                  <el-input
                    v-model="loginForm.password"
                    show-password
                    placeholder="请输入密码"
                    @keyup.enter="handleLoginEnter"
                  />
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

const handleLoginEnter = () => {
  if (!loginForm.value.employeeNo?.trim() || !loginForm.value.password?.trim()) return
  handleLogin(loginFormRef.value)
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
  padding: 28px;
  background:
    radial-gradient(circle at top left, rgba(47, 125, 107, 0.22), transparent 28%),
    radial-gradient(circle at bottom right, rgba(91, 143, 203, 0.2), transparent 25%),
    linear-gradient(135deg, #f7faf7, #eef4ef 45%, #edf3f7);
}

.auth-panel {
  width: min(1180px, 100%);
  min-height: 680px;
  display: grid;
  grid-template-columns: 1.08fr 0.92fr;
  border-radius: 34px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(95, 123, 114, 0.14);
  box-shadow: 0 28px 80px rgba(34, 58, 50, 0.12);
  backdrop-filter: blur(18px);
}

.auth-cover {
  position: relative;
  padding: 60px 54px;
  color: #fff;
  background:
    radial-gradient(circle at top right, rgba(255, 255, 255, 0.16), transparent 22%),
    linear-gradient(155deg, rgba(36, 96, 83, 0.94), rgba(47, 125, 107, 0.92) 46%, rgba(91, 143, 203, 0.82));
  display: flex;
  flex-direction: column;
  justify-content: center;
  overflow: hidden;
}

.auth-cover h1 {
  margin: 0 0 18px;
  font-size: 42px;
  line-height: 1.2;
  position: relative;
  z-index: 1;
}

.cover-badge {
  width: fit-content;
  margin-bottom: 18px;
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  position: relative;
  z-index: 1;
}

.cover-orb {
  position: absolute;
  border-radius: 999px;
  filter: blur(6px);
}

.cover-orb-a {
  top: -48px;
  right: 40px;
  width: 220px;
  height: 220px;
  background: rgba(255, 255, 255, 0.1);
}

.cover-orb-b {
  bottom: 56px;
  left: -64px;
  width: 180px;
  height: 180px;
  background: rgba(140, 194, 255, 0.16);
}

.cover-grid {
  position: absolute;
  inset: 28px;
  border-radius: 30px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.06) 1px, transparent 1px);
  background-size: 34px 34px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.7), transparent 92%);
}

.cover-tags {
  position: relative;
  z-index: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.cover-tags span {
  padding: 9px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.14);
  color: rgba(255, 255, 255, 0.94);
  font-size: 13px;
}

.auth-form-wrap {
  padding: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.auth-form-panel {
  width: min(440px, 100%);
  padding: 30px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.76);
  border: 1px solid rgba(95, 123, 114, 0.12);
  box-shadow: 0 16px 38px rgba(48, 77, 67, 0.06);
}

.form-header {
  margin-bottom: 18px;
}

.form-title {
  font-size: 28px;
  font-weight: 700;
  color: #233b33;
}

.auth-form-panel :deep(.el-tabs__header) {
  margin-bottom: 26px;
}

.auth-form-panel :deep(.el-form-item__label) {
  font-weight: 600;
}

.full-btn {
  width: 100%;
  margin-top: 10px;
}

@media (max-width: 960px) {
  .auth-panel {
    grid-template-columns: 1fr;
  }

  .auth-cover {
    padding: 42px 30px;
  }

  .auth-cover h1 {
    font-size: 32px;
  }
}

@media (max-width: 640px) {
  .auth-page {
    padding: 14px;
  }

  .auth-form-wrap {
    padding: 18px;
  }

  .auth-form-panel {
    padding: 22px 18px;
  }
}
</style>
