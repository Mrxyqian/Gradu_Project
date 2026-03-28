<template>
  <div>
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="12">
        <div class="card">
          <div style="font-size: 16px; font-weight: bold; margin-bottom: 15px">按风险类型统计</div>
          <div ref="riskTypeChart" style="height: 350px"></div>
        </div>
      </el-col>
      <el-col :span="12">
        <div class="card">
          <div style="font-size: 16px; font-weight: bold; margin-bottom: 15px">按地区统计</div>
          <div ref="areaChart" style="height: 350px"></div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="12">
        <div class="card">
          <div style="font-size: 16px; font-weight: bold; margin-bottom: 15px">按缴费方式统计</div>
          <div ref="paymentChart" style="height: 350px"></div>
        </div>
      </el-col>
      <el-col :span="12">
        <div class="card">
          <div style="font-size: 16px; font-weight: bold; margin-bottom: 15px">按燃料类型统计</div>
          <div ref="fuelTypeChart" style="height: 350px"></div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="12">
        <div class="card">
          <div style="font-size: 16px; font-weight: bold; margin-bottom: 15px">按车辆注册年份统计</div>
          <div ref="matriculationYearChart" style="height: 350px"></div>
        </div>
      </el-col>
      <el-col :span="12">
        <div class="card">
          <div style="font-size: 16px; font-weight: bold; margin-bottom: 15px">按分销渠道统计</div>
          <div ref="distributionChannelChart" style="height: 350px"></div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import * as echarts from "echarts";
import request from "@/utils/request";

const riskTypeChart = ref(null);
const areaChart = ref(null);
const paymentChart = ref(null);
const fuelTypeChart = ref(null);
const matriculationYearChart = ref(null);
const distributionChannelChart = ref(null);

let riskTypeChartInstance = null;
let areaChartInstance = null;
let paymentChartInstance = null;
let fuelTypeChartInstance = null;
let matriculationYearChartInstance = null;
let distributionChannelChartInstance = null;

const getRiskTypeText = (type) => {
  const map = { 1: '摩托车', 2: '货车', 3: '乘用车', 4: '农用车' };
  return map[type] || type;
};

const getAreaText = (area) => {
  return area === 0 ? '农村' : '城市';
};

const getPaymentText = (payment) => {
  return payment === 0 ? '年缴' : '半年缴';
};

const getFuelTypeText = (fuel) => {
  return fuel === 'P' ? '汽油' : '柴油';
};

const getDistributionChannelText = (channel) => {
  return channel === 0 ? '代理人' : '保险经纪';
};

const initRiskTypeChart = (data) => {
  if (!riskTypeChart.value) return;
  
  riskTypeChartInstance = echarts.init(riskTypeChart.value);
  const names = data.map(item => getRiskTypeText(item.typeRisk));
  const counts = data.map(item => item.count);
  const premiums = data.map(item => item.totalPremium);
  
  const option = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['保单数量', '总保费'] },
    xAxis: { type: 'category', data: names },
    yAxis: [{ type: 'value', name: '保单数量' }, { type: 'value', name: '总保费' }],
    series: [
      { name: '保单数量', type: 'bar', data: counts, itemStyle: { color: '#5470c6' } },
      { name: '总保费', type: 'bar', yAxisIndex: 1, data: premiums, itemStyle: { color: '#91cc75' } }
    ]
  };
  riskTypeChartInstance.setOption(option);
};

const initAreaChart = (data) => {
  if (!areaChart.value) return;
  
  areaChartInstance = echarts.init(areaChart.value);
  const names = data.map(item => getAreaText(item.area));
  const counts = data.map(item => item.count);
  
  const option = {
    tooltip: { trigger: 'item' },
    legend: { orient: 'vertical', left: 'left' },
    series: [{
      name: '地区分布',
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: false, position: 'center' },
      emphasis: { label: { show: true, fontSize: 20, fontWeight: 'bold' } },
      labelLine: { show: false },
      data: names.map((name, i) => ({ value: counts[i], name }))
    }]
  };
  areaChartInstance.setOption(option);
};

const initPaymentChart = (data) => {
  if (!paymentChart.value) return;
  
  paymentChartInstance = echarts.init(paymentChart.value);
  const names = data.map(item => getPaymentText(item.payment));
  const premiums = data.map(item => item.totalPremium);
  
  const option = {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: names },
    yAxis: { type: 'value', name: '总保费' },
    series: [{
      data: premiums,
      type: 'line',
      smooth: true,
      areaStyle: { opacity: 0.3 },
      itemStyle: { color: '#ee6666' }
    }]
  };
  paymentChartInstance.setOption(option);
};

const initFuelTypeChart = (data) => {
  if (!fuelTypeChart.value) return;
  
  fuelTypeChartInstance = echarts.init(fuelTypeChart.value);
  const names = data.map(item => getFuelTypeText(item.typeFuel));
  const avgPowers = data.map(item => item.avgPower);
  const avgCylinders = data.map(item => item.avgCylinderCapacity);
  
  const option = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['平均马力', '平均气缸排量'] },
    xAxis: { type: 'category', data: names },
    yAxis: [{ type: 'value', name: '马力' }, { type: 'value', name: '排量(cc)' }],
    series: [
      { name: '平均马力', type: 'bar', data: avgPowers, itemStyle: { color: '#fac858' } },
      { name: '平均气缸排量', type: 'line', yAxisIndex: 1, data: avgCylinders, itemStyle: { color: '#73c0de' } }
    ]
  };
  fuelTypeChartInstance.setOption(option);
};

const initMatriculationYearChart = (data) => {
  if (!matriculationYearChart.value) return;
  
  matriculationYearChartInstance = echarts.init(matriculationYearChart.value);
  const years = data.map(item => item.yearMatriculation);
  const counts = data.map(item => item.count);
  const avgValues = data.map(item => item.avgVehicleValue);
  
  const option = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['车辆数量', '平均车辆价值'] },
    xAxis: { type: 'category', data: years },
    yAxis: [{ type: 'value', name: '车辆数量' }, { type: 'value', name: '平均价值' }],
    series: [
      { name: '车辆数量', type: 'bar', data: counts, itemStyle: { color: '#3ba272' } },
      { name: '平均车辆价值', type: 'line', yAxisIndex: 1, data: avgValues, smooth: true, itemStyle: { color: '#fc8452' } }
    ]
  };
  matriculationYearChartInstance.setOption(option);
};

const initDistributionChannelChart = (data) => {
  if (!distributionChannelChart.value) return;
  
  distributionChannelChartInstance = echarts.init(distributionChannelChart.value);
  const names = data.map(item => getDistributionChannelText(item.distributionChannel));
  const counts = data.map(item => item.count);
  const premiums = data.map(item => item.totalPremium);
  
  const option = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: {},
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: names },
    series: [
      { name: '保单数量', type: 'bar', data: counts, stack: 'total', itemStyle: { color: '#9a60b4' } },
      { name: '总保费', type: 'bar', data: premiums, stack: 'total', itemStyle: { color: '#ea7ccc' } }
    ]
  };
  distributionChannelChartInstance.setOption(option);
};

const loadStatistics = () => {
  request.get('/motorInsurance/statisticsByRiskType').then(res => {
    if (res.code === '200' && res.data) {
      initRiskTypeChart(res.data);
    }
  });

  request.get('/motorInsurance/statisticsByArea').then(res => {
    if (res.code === '200' && res.data) {
      initAreaChart(res.data);
    }
  });

  request.get('/motorInsurance/statisticsByPayment').then(res => {
    if (res.code === '200' && res.data) {
      initPaymentChart(res.data);
    }
  });

  request.get('/motorInsurance/statisticsByFuelType').then(res => {
    if (res.code === '200' && res.data) {
      initFuelTypeChart(res.data);
    }
  });

  request.get('/motorInsurance/statisticsByMatriculationYear').then(res => {
    if (res.code === '200' && res.data) {
      initMatriculationYearChart(res.data);
    }
  });

  request.get('/motorInsurance/statisticsByDistributionChannel').then(res => {
    if (res.code === '200' && res.data) {
      initDistributionChannelChart(res.data);
    }
  });
};

const handleResize = () => {
  riskTypeChartInstance?.resize();
  areaChartInstance?.resize();
  paymentChartInstance?.resize();
  fuelTypeChartInstance?.resize();
  matriculationYearChartInstance?.resize();
  distributionChannelChartInstance?.resize();
};

onMounted(() => {
  loadStatistics();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  riskTypeChartInstance?.dispose();
  areaChartInstance?.dispose();
  paymentChartInstance?.dispose();
  fuelTypeChartInstance?.dispose();
  matriculationYearChartInstance?.dispose();
  distributionChannelChartInstance?.dispose();
});
</script>
