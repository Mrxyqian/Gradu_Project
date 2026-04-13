<template>
  <div>
    <el-row :gutter="20">
      <el-col :span="12">
        <div class="card">
          <div style="font-size: 16px; font-weight: bold; margin-bottom: 15px">按风险类型统计</div>
          <div ref="riskTypeChart" style="height: 380px"></div>
        </div>
      </el-col>
      <el-col :span="12">
        <div class="card">
          <div style="font-size: 16px; font-weight: bold; margin-bottom: 15px">按地区统计</div>
          <div ref="areaChart" style="height: 380px"></div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import * as echarts from 'echarts'
import request from '@/utils/request'

const riskTypeChart = ref(null)
const areaChart = ref(null)

let riskTypeChartInstance = null
let areaChartInstance = null

const getRiskTypeText = (type) => {
  const map = { 1: '摩托车', 2: '货车', 3: '乘用车', 4: '农用车' }
  return map[type] || type
}

const getAreaText = (area) => (Number(area) === 0 ? '农村' : '城市')

const initRiskTypeChart = (data) => {
  if (!riskTypeChart.value) return

  riskTypeChartInstance = echarts.init(riskTypeChart.value)
  const names = data.map(item => getRiskTypeText(item.typeRisk))
  const counts = data.map(item => item.count)
  const claimsCosts = data.map(item => item.totalClaimsCost)

  riskTypeChartInstance.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['理赔记录数量', '总索赔成本'] },
    xAxis: { type: 'category', data: names },
    yAxis: [{ type: 'value', name: '记录数量' }, { type: 'value', name: '总索赔成本' }],
    series: [
      { name: '理赔记录数量', type: 'bar', data: counts, itemStyle: { color: '#5470c6' } },
      { name: '总索赔成本', type: 'bar', yAxisIndex: 1, data: claimsCosts, itemStyle: { color: '#91cc75' } },
    ],
  })
}

const initAreaChart = (data) => {
  if (!areaChart.value) return

  areaChartInstance = echarts.init(areaChart.value)
  const names = data.map(item => getAreaText(item.area))
  const counts = data.map(item => item.count)

  areaChartInstance.setOption({
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
      data: names.map((name, index) => ({ value: counts[index], name })),
    }],
  })
}

const loadStatistics = () => {
  request.get('/claimTypes/statisticsByRiskType').then((res) => {
    if (res.code === '200' && res.data) {
      initRiskTypeChart(res.data)
    }
  })

  request.get('/claimTypes/statisticsByArea').then((res) => {
    if (res.code === '200' && res.data) {
      initAreaChart(res.data)
    }
  })
}

const handleResize = () => {
  riskTypeChartInstance?.resize()
  areaChartInstance?.resize()
}

onMounted(() => {
  loadStatistics()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  riskTypeChartInstance?.dispose()
  areaChartInstance?.dispose()
})
</script>
