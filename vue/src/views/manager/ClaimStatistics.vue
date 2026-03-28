<template>
  <div>
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="8">
        <div class="card">
          <div style="font-size: 16px; font-weight: bold; margin-bottom: 15px; text-align: center;">
            当年总索赔成本
          </div>
          <div style="font-size: 36px; font-weight: bold; color: #f56c6c; text-align: center;">
            ¥{{ overallStatistics.totalCostClaimsYear || 0 }}
          </div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="card">
          <div style="font-size: 16px; font-weight: bold; margin-bottom: 15px; text-align: center;">
            按类型总索赔成本
          </div>
          <div style="font-size: 36px; font-weight: bold; color: #409eff; text-align: center;">
            ¥{{ overallStatistics.totalCostClaimsByType || 0 }}
          </div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="card">
          <div style="font-size: 16px; font-weight: bold; margin-bottom: 15px; text-align: center;">
            索赔类型数量
          </div>
          <div style="font-size: 36px; font-weight: bold; color: #67c23a; text-align: center;">
            {{ claimTypeList.length }}
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <el-col :span="12">
        <div class="card">
          <div style="font-size: 16px; font-weight: bold; margin-bottom: 15px">按索赔类型统计（柱状图）</div>
          <div ref="claimTypeBarChart" style="height: 400px"></div>
        </div>
      </el-col>
      <el-col :span="12">
        <div class="card">
          <div style="font-size: 16px; font-weight: bold; margin-bottom: 15px">索赔成本占比（饼图）</div>
          <div ref="claimTypePieChart" style="height: 400px"></div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, reactive } from "vue";
import * as echarts from "echarts";
import request from "@/utils/request";

const claimTypeBarChart = ref(null);
const claimTypePieChart = ref(null);

let claimTypeBarChartInstance = null;
let claimTypePieChartInstance = null;

const overallStatistics = reactive({
  totalCostClaimsYear: 0,
  totalCostClaimsByType: 0
});

const claimTypeList = ref([]);

const initClaimTypeBarChart = (data) => {
  if (!claimTypeBarChart.value) return;
  
  claimTypeBarChartInstance = echarts.init(claimTypeBarChart.value);
  const names = data.map(item => item.claimsType);
  const costsByType = data.map(item => item.costClaimsByType);
  const costsYear = data.map(item => item.costClaimsYear);
  
  const option = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['按类型索赔成本', '当年总索赔成本'] },
    xAxis: { 
      type: 'category', 
      data: names,
      axisLabel: { interval: 0, rotate: 30 }
    },
    yAxis: { type: 'value', name: '索赔成本' },
    series: [
      { 
        name: '按类型索赔成本', 
        type: 'bar', 
        data: costsByType, 
        itemStyle: { color: '#5470c6' },
        barWidth: '30%'
      },
      { 
        name: '当年总索赔成本', 
        type: 'bar', 
        data: costsYear, 
        itemStyle: { color: '#91cc75' },
        barWidth: '30%'
      }
    ]
  };
  claimTypeBarChartInstance.setOption(option);
};

const initClaimTypePieChart = (data) => {
  if (!claimTypePieChart.value) return;
  
  claimTypePieChartInstance = echarts.init(claimTypePieChart.value);
  
  const option = {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'center' },
    series: [{
      name: '索赔成本',
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['60%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, formatter: '{b}: {d}%' },
      emphasis: { 
        label: { show: true, fontSize: 16, fontWeight: 'bold' },
        itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' }
      },
      labelLine: { show: true, smooth: true },
      data: data.map(item => ({ 
        value: item.costClaimsByType, 
        name: item.claimsType 
      }))
    }]
  };
  claimTypePieChartInstance.setOption(option);
};

const loadStatistics = () => {
  request.get('/claimTypes/overallClaimsStatistics').then(res => {
    if (res.code === '200' && res.data) {
      overallStatistics.totalCostClaimsYear = res.data.totalCostClaimsYear;
      overallStatistics.totalCostClaimsByType = res.data.totalCostClaimsByType;
    }
  });

  request.get('/claimTypes/statisticsByClaimType').then(res => {
    if (res.code === '200' && res.data) {
      claimTypeList.value = res.data;
      initClaimTypeBarChart(res.data);
    }
  });

  request.get('/claimTypes/claimsCostPercentage').then(res => {
    if (res.code === '200' && res.data) {
      initClaimTypePieChart(res.data);
    }
  });
};

const handleResize = () => {
  claimTypeBarChartInstance?.resize();
  claimTypePieChartInstance?.resize();
};

onMounted(() => {
  loadStatistics();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  claimTypeBarChartInstance?.dispose();
  claimTypePieChartInstance?.dispose();
});
</script>
