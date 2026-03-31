<template>
  <div>
    <div style="height: 60px; background-color: #fff; display: flex; align-items: center; border-bottom: 1px solid #ddd">
      <div style="flex: 1">
        <div style="padding-left: 20px; display: flex; align-items: center">
          <img src="@/assets/imgs/logo.png" alt="" style="width: 40px">
          <div style="font-weight: bold; font-size: 24px; margin-left: 5px">车险理赔记录管理系统</div>
        </div>
      </div>
      <div style="width: fit-content; padding-right: 10px; display: flex; align-items: center;">
        <img src="https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png" alt="" style="width: 40px; height: 40px; border-radius: 50%">
        <span style="margin-left: 5px">管理员</span>
      </div>
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
import { useRoute } from 'vue-router'
const $route = useRoute()
</script>

<style scoped>
.el-menu-item.is-active {
  background-color: #dcede9 !important;
}
.el-menu-item:hover {
  color: #11A983;
}
:deep(th)  {
  color: #333;
}
</style>
