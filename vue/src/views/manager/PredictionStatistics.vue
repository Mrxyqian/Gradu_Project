<template>
  <div>
    <div class="card stats-header">
      <div>
        <div class="stats-title">预测统计分析</div>
        <div class="stats-desc">基于 insur_pred 历史记录展示风险等级分布与预计理赔金额分布。</div>
      </div>
    </div>

    <el-row :gutter="20" style="margin-bottom: 16px;">
      <el-col :span="8">
        <div class="summary-card summary-blue">
          <div class="summary-label">历史预测总数</div>
          <div class="summary-value">{{ summary.totalCount || 0 }}</div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="summary-card summary-orange">
          <div class="summary-label">平均理赔概率</div>
          <div class="summary-value">{{ averageClaimProbability }}</div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="summary-card summary-green">
          <div class="summary-label">平均预计金额</div>
          <div class="summary-value">¥{{ averageExpectedClaimAmount }}</div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <el-col :span="10">
        <div class="card chart-card">
          <div class="chart-title">风险等级分布</div>
          <div ref="riskPieRef" style="height: 380px;"></div>
        </div>
      </el-col>
      <el-col :span="14">
        <div class="card chart-card">
          <div class="chart-title">预计理赔金额分布（500元步长）</div>
          <div ref="amountBarRef" style="height: 380px;"></div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import * as echarts from "echarts";
import request from "@/utils/request";

const riskPieRef = ref(null)
const amountBarRef = ref(null)

let riskPieChart = null
let amountBarChart = null

const summary = ref({
  totalCount: 0,
  avgClaimProbability: 0,
  avgExpectedClaimAmount: 0
})

const averageClaimProbability = computed(() => `${(Number(summary.value.avgClaimProbability || 0) * 100).toFixed(2)}%`)
const averageExpectedClaimAmount = computed(() => Number(summary.value.avgExpectedClaimAmount || 0).toFixed(2))

const getRiskLevelText = (riskLevel) => {
  const map = { LOW: '低风险', MEDIUM: '中风险', HIGH: '高风险' }
  return map[riskLevel] || riskLevel
}

const initRiskPieChart = (data) => {
  if (!riskPieRef.value) return
  riskPieChart?.dispose()
  riskPieChart = echarts.init(riskPieRef.value)

  const chartData = (data || []).map(item => ({
    value: item.count,
    name: getRiskLevelText(item.riskLevel)
  }))

  riskPieChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} 条 ({d}%)' },
    legend: { bottom: 0 },
    series: [{
      name: '风险等级',
      type: 'pie',
      radius: ['38%', '68%'],
      center: ['50%', '46%'],
      itemStyle: {
        borderRadius: 10,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: { formatter: '{b}\n{c}条' },
      data: chartData
    }]
  })
}

const initAmountBarChart = (data) => {
  if (!amountBarRef.value) return
  amountBarChart?.dispose()
  amountBarChart = echarts.init(amountBarRef.value)

  const xData = (data || []).map(item => `${item.bucketStart}-${item.bucketEnd}`)
  const yData = (data || []).map(item => item.count)

  amountBarChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    xAxis: {
      type: 'category',
      data: xData,
      axisLabel: {
        interval: 0,
        rotate: xData.length > 8 ? 35 : 0
      }
    },
    yAxis: {
      type: 'value',
      name: '记录数'
    },
    series: [{
      name: '记录数',
      type: 'bar',
      barWidth: '55%',
      data: yData,
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#38bdf8' },
          { offset: 1, color: '#2563eb' }
        ]),
        borderRadius: [8, 8, 0, 0]
      }
    }]
  })
}

const loadSummary = () => {
  request.get('/insurPred/overallStatistics').then(res => {
    if (res.code === '200' && res.data) {
      summary.value = res.data
    }
  })
}

const loadCharts = () => {
  request.get('/insurPred/riskLevelDistribution').then(res => {
    if (res.code === '200') {
      initRiskPieChart(res.data || [])
    }
  })

  request.get('/insurPred/claimAmountHistogram').then(res => {
    if (res.code === '200') {
      initAmountBarChart(res.data || [])
    }
  })
}

const handleResize = () => {
  riskPieChart?.resize()
  amountBarChart?.resize()
}

onMounted(() => {
  loadSummary()
  loadCharts()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  riskPieChart?.dispose()
  amountBarChart?.dispose()
})
</script>

<style scoped>
.stats-header {
  margin-bottom: 16px;
  padding: 18px 20px;
  background:
      linear-gradient(135deg, rgba(37, 99, 235, 0.08), rgba(14, 165, 233, 0.16)),
      #fff;
}

.stats-title {
  font-size: 20px;
  font-weight: bold;
  color: #1d4ed8;
}

.stats-desc {
  margin-top: 6px;
  color: #4b5563;
}

.summary-card {
  padding: 20px;
  border-radius: 14px;
  color: #fff;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

.summary-blue {
  background: linear-gradient(135deg, #2563eb, #06b6d4);
}

.summary-orange {
  background: linear-gradient(135deg, #f97316, #fb7185);
}

.summary-green {
  background: linear-gradient(135deg, #059669, #22c55e);
}

.summary-label {
  font-size: 14px;
  opacity: 0.92;
}

.summary-value {
  margin-top: 10px;
  font-size: 30px;
  font-weight: bold;
}

.chart-card {
  min-height: 430px;
}

.chart-title {
  font-size: 17px;
  font-weight: bold;
  color: #1f2937;
  margin-bottom: 10px;
}
</style>
