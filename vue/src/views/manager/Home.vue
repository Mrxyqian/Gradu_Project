<template>
  <div>
    <div class="card" style="line-height: 30px; margin-bottom: 20px">
      <div>欢迎您，<span style="color: dodgerblue;">管理员</span> 祝您今天过得开心！</div>
    </div>

    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="6">
        <div class="stat-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
          <div class="stat-title">总保费收入</div>
          <div class="stat-value">¥{{ statistics.totalPremium || 0 }}</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
          <div class="stat-title">总索赔成本</div>
          <div class="stat-value">¥{{ statistics.totalClaimsCost || 0 }}</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
          <div class="stat-title">本年度索赔次数</div>
          <div class="stat-value">{{ statistics.totalClaimsCount || 0 }}</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
          <div class="stat-title">平均索赔频率比</div>
          <div class="stat-value">{{ statistics.avgClaimsRatio || 0 }}%</div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <el-col :span="24">
        <div class="card">
          <div style="font-size: 18px; font-weight: bold; margin-bottom: 15px">系统使用说明</div>
          <el-divider></el-divider>
          <ul style="line-height: 2">
            <li><strong>保单管理</strong>：管理车险保单数据，支持增删改查、条件筛选和分页浏览</li>
            <li><strong>保单统计</strong>：按风险类型、地区、缴费方式等维度统计保单数据</li>
            <li><strong>索赔类型</strong>：管理索赔类型信息，支持增删改查操作</li>
            <li><strong>理赔统计</strong>：按索赔类型统计理赔成本，展示成本占比分析</li>
          </ul>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import request from "@/utils/request";

const statistics = ref({
  totalPremium: 0,
  totalClaimsCost: 0,
  totalClaimsCount: 0,
  avgClaimsRatio: 0
});

const loadStatistics = () => {
  request.get('/motorInsurance/overallStatistics').then(res => {
    if (res.code === '200' && res.data) {
      statistics.value = res.data;
    }
  }).catch(err => {
    console.error('加载统计数据失败', err);
  });
};

onMounted(() => {
  loadStatistics();
});
</script>

<style scoped>
.stat-card {
  padding: 20px;
  border-radius: 10px;
  color: white;
  text-align: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
.stat-title {
  font-size: 14px;
  opacity: 0.9;
  margin-bottom: 10px;
}
.stat-value {
  font-size: 28px;
  font-weight: bold;
}
</style>
