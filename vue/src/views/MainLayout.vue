<template>
  <div>
    <div class="header">
      <div style="flex: 1">
        <div class="brand">
          <img src="@/assets/imgs/logo.png" alt="" style="width: 40px">
          <div class="title">车辆保险理赔记录管理系统</div>
        </div>
      </div>
      <el-dropdown trigger="click">
        <div class="user-box">
          <img
            src="https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png"
            alt=""
            class="avatar"
          >
          <span style="margin-left: 8px">{{ user.name || '未登录' }}</span>
          <el-icon style="margin-left: 4px"><ArrowDown /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <div style="display: flex">
      <div style="width: 200px; border-right: 1px solid #ddd; min-height: calc(100vh - 60px)">
        <el-menu
          router
          style="border: none"
          :default-active="$route.path"
          :default-openeds="['/home', '2', '3', '4']"
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
              <span>保单统计</span>
            </el-menu-item>
          </el-sub-menu>
          <el-sub-menu index="3">
            <template #title>
              <el-icon><Memo /></el-icon>
              <span>理赔管理</span>
            </template>
            <el-menu-item index="/claimTypes">
              <el-icon><Document /></el-icon>
              <span>索赔类型</span>
            </el-menu-item>
            <el-menu-item index="/claimStatistics">
              <el-icon><DataAnalysis /></el-icon>
              <span>理赔统计</span>
            </el-menu-item>
          </el-sub-menu>
          <el-menu-item index="/vehicleInfo">
            <el-icon><Van /></el-icon>
            <span>车辆信息管理</span>
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
          </el-sub-menu>
        </el-menu>
      </div>

      <div style="flex: 1; width: 0; background-color: #f8f8ff; padding: 10px">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { clearCurrentUser, getCurrentUser } from '@/utils/auth'

const $route = useRoute()
const router = useRouter()
const user = ref(getCurrentUser())

const logout = () => {
  clearCurrentUser()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<style scoped>
.header {
  height: 60px;
  background-color: #fff;
  display: flex;
  align-items: center;
  border-bottom: 1px solid #ddd;
}

.brand {
  padding-left: 20px;
  display: flex;
  align-items: center;
}

.title {
  font-weight: bold;
  font-size: 24px;
  margin-left: 5px;
}

.user-box {
  width: fit-content;
  padding-right: 10px;
  display: flex;
  align-items: center;
  cursor: pointer;
  color: #333;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
}

.el-menu-item.is-active {
  background-color: #dcede9 !important;
}

.el-menu-item:hover {
  color: #11A983;
}

:deep(th) {
  color: #333;
}
</style>
