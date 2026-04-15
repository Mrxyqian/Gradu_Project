<template>
  <div class="layout-shell">
    <aside class="sidebar-panel">
      <div class="brand-block">
        <div class="brand-mark">
          <img src="@/assets/imgs/insurance-brand.svg" alt="车险理赔预测系统图标" class="brand-logo">
        </div>
        <div class="brand-copy">
          <div class="brand-title">车险理赔预测系统</div>
          <div class="brand-subtitle">业务导航与运营总览</div>
        </div>
      </div>

      <div class="sidebar-caption">业务导航</div>

      <div class="sidebar-scroll">
        <el-menu
          router
          class="sidebar-menu"
          :default-active="$route.path"
          :default-openeds="['2', '3', '4']"
        >
          <el-menu-item index="/home">
            <el-icon><HomeFilled /></el-icon>
            <span>系统首页</span>
          </el-menu-item>

          <el-sub-menu index="2">
            <template #title>
              <el-icon><Memo /></el-icon>
              <span>保单管理</span>
            </template>
            <el-menu-item index="/motorInsurance">
              <el-icon><Document /></el-icon>
              <span>保单信息</span>
            </el-menu-item>
            <el-menu-item index="/motorInsuranceStatistics">
              <el-icon><DataAnalysis /></el-icon>
              <span>保单分析</span>
            </el-menu-item>
          </el-sub-menu>

          <el-sub-menu index="3">
            <template #title>
              <el-icon><Memo /></el-icon>
              <span>理赔管理</span>
            </template>
            <el-menu-item index="/claimTypes">
              <el-icon><Document /></el-icon>
              <span>理赔记录</span>
            </el-menu-item>
            <el-menu-item index="/claimStatistics">
              <el-icon><DataAnalysis /></el-icon>
              <span>理赔分析</span>
            </el-menu-item>
          </el-sub-menu>

          <el-menu-item index="/vehicleInfo">
            <el-icon><Van /></el-icon>
            <span>车辆信息管理</span>
          </el-menu-item>

          <el-menu-item v-if="user.role === 'ADMIN'" index="/userManage">
            <el-icon><User /></el-icon>
            <span>用户管理</span>
          </el-menu-item>

          <el-sub-menu index="4">
            <template #title>
              <el-icon><TrendCharts /></el-icon>
              <span>理赔率预测</span>
            </template>
            <el-menu-item index="/predictionManage">
              <el-icon><MagicStick /></el-icon>
              <span>预测管理</span>
            </el-menu-item>
            <el-menu-item index="/predictionStatistics">
              <el-icon><PieChart /></el-icon>
              <span>预测统计</span>
            </el-menu-item>
            <el-menu-item v-if="user.role === 'ADMIN'" index="/modelTraining">
              <el-icon><Operation /></el-icon>
              <span>模型训练</span>
            </el-menu-item>
          </el-sub-menu>
        </el-menu>
      </div>
    </aside>

    <main class="content-panel">
      <header class="topbar">
        <div class="topbar-copy">
          <div class="topbar-eyebrow">业务控制台</div>
          <div class="topbar-title">车险理赔预测系统</div>
        </div>

        <div class="topbar-actions">
          <div class="session-chip">
            <span class="session-chip-label">当前角色</span>
            <span class="session-chip-value">{{ user.role === 'ADMIN' ? '管理员' : '普通用户' }}</span>
          </div>

          <el-dropdown trigger="click">
            <div class="profile-button">
              <div class="profile-avatar">{{ userInitial }}</div>
              <div class="profile-meta">
                <span class="profile-name">{{ user.name || '未登录用户' }}</span>
                <span class="profile-role">{{ user.role === 'ADMIN' ? 'Administrator' : 'Operator' }}</span>
              </div>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <section class="page-stage">
        <router-view />
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { clearCurrentUser, getCurrentUser } from '@/utils/auth'
import request from '@/utils/request'

const $route = useRoute()
const router = useRouter()
const user = ref(getCurrentUser())

const userInitial = computed(() => {
  const name = String(user.value.name || '').trim()
  return name ? name.slice(0, 1) : 'U'
})

const logout = async () => {
  await request.post('/auth/logout')
  clearCurrentUser()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<style scoped>
.layout-shell {
  height: 100vh;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 18px;
  padding: 18px;
  overflow: hidden;
}

.sidebar-panel {
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 20px 14px 16px;
  border-radius: 30px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(248, 252, 249, 0.9)),
    rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(95, 123, 114, 0.14);
  box-shadow: 0 18px 46px rgba(48, 77, 67, 0.08);
  backdrop-filter: blur(14px);
  overflow: hidden;
}

.brand-block {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 6px 8px 18px;
}

.brand-mark {
  width: 56px;
  height: 56px;
  display: grid;
  place-items: center;
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(47, 125, 107, 0.14), rgba(91, 143, 203, 0.14));
}

.brand-logo {
  width: 34px;
  height: 34px;
  object-fit: contain;
}

.brand-copy {
  min-width: 0;
}

.brand-title {
  font-size: 19px;
  font-weight: 700;
  color: #274139;
}

.brand-subtitle {
  margin-top: 4px;
  color: #88a097;
  font-size: 12px;
}

.sidebar-caption {
  padding: 0 18px 10px;
  color: #89a098;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.sidebar-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding-bottom: 6px;
}

.sidebar-scroll::-webkit-scrollbar,
.page-stage::-webkit-scrollbar {
  width: 8px;
}

.sidebar-scroll::-webkit-scrollbar-thumb,
.page-stage::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(95, 123, 114, 0.28);
}

.sidebar-menu {
  margin-top: 4px;
}

.content-panel {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 18px;
  overflow: hidden;
}

.topbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 20px 24px;
  border-radius: 28px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(248, 252, 249, 0.92)),
    rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(95, 123, 114, 0.14);
  box-shadow: 0 14px 36px rgba(48, 77, 67, 0.06);
  backdrop-filter: blur(14px);
}

.topbar-copy {
  min-width: 0;
}

.topbar-eyebrow {
  margin-bottom: 6px;
  color: #7a9189;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.topbar-title {
  font-size: 26px;
  font-weight: 700;
  color: #233a33;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 14px;
}

.session-chip {
  padding: 12px 16px;
  border-radius: 18px;
  background: rgba(245, 249, 246, 0.92);
  border: 1px solid rgba(95, 123, 114, 0.12);
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.session-chip-label {
  color: #7d918a;
  font-size: 12px;
}

.session-chip-value {
  color: #2d5a4d;
  font-weight: 700;
}

.profile-button {
  min-width: 220px;
  padding: 10px 14px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(95, 123, 114, 0.12);
  cursor: pointer;
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    border-color 0.2s ease;
}

.profile-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 26px rgba(48, 77, 67, 0.08);
  border-color: rgba(47, 125, 107, 0.22);
}

.profile-avatar {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 14px;
  background: linear-gradient(135deg, #2f7d6b, #5b8fcb);
  color: #fff;
  font-weight: 700;
}

.profile-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.profile-name {
  color: #284139;
  font-weight: 700;
}

.profile-role {
  margin-top: 2px;
  color: #82958e;
  font-size: 12px;
}

.page-stage {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding-right: 4px;
}

@media (max-width: 1180px) {
  .layout-shell {
    height: auto;
    min-height: 100vh;
    grid-template-columns: 1fr;
    overflow: visible;
  }

  .sidebar-panel,
  .content-panel {
    min-height: auto;
  }

  .sidebar-scroll,
  .page-stage {
    overflow: visible;
  }
}

@media (max-width: 900px) {
  .topbar {
    flex-direction: column;
    align-items: stretch;
  }

  .topbar-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .profile-button {
    min-width: 0;
  }
}

@media (max-width: 640px) {
  .layout-shell {
    padding: 12px;
    gap: 12px;
  }

  .topbar {
    padding: 18px;
    border-radius: 22px;
  }

  .topbar-title {
    font-size: 22px;
  }
}
</style>
