<template>
  <div class="analytics-shell">
    <section class="card analytics-hero">
      <div>
        <div class="analytics-eyebrow">动态分析工作台</div>
        <h1 class="analytics-title">{{ subjectTitle }}</h1>
        <p class="analytics-subtitle">
          按分析目标分组、按统计指标聚合、按业务条件筛选，动态查看当前业务表现。
        </p>
      </div>
      <div class="analytics-hero-note">
        <div>当前分析目标：{{ currentGroupLabel }}</div>
        <div>当前指标：{{ selectedMetricLabels.join(' / ') }}</div>
      </div>
    </section>

    <section class="card config-card">
      <div class="section-head">
        <div class="section-title">分析配置</div>
        <div class="section-tip">先确定分析目标和指标，再选择展示方式</div>
      </div>

      <div class="config-panel">
        <div class="config-group emphasis-group">
          <div class="config-group-title">核心配置</div>
          <el-row :gutter="16">
            <el-col :xs="24" :md="10" :xl="6">
              <div class="field-label">分析目标</div>
              <el-select v-model="form.groupBy" style="width: 100%">
                <el-option
                  v-for="item in dimensionOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-col>
            <el-col :xs="24" :md="14" :xl="10">
              <div class="field-label">统计指标</div>
              <el-select v-model="form.metrics" style="width: 100%" multiple collapse-tags collapse-tags-tooltip>
                <el-option
                  v-for="item in availableMetrics"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-col>
            <el-col :xs="24" :md="12" :xl="4">
              <div class="field-label">排序指标</div>
              <el-select v-model="form.sortBy" style="width: 100%">
                <el-option
                  v-for="item in availableMetrics"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-col>
            <el-col :xs="24" :md="12" :xl="4">
              <div class="field-label">排序方向</div>
              <el-select v-model="form.sortOrder" style="width: 100%">
                <el-option label="降序" value="desc" />
                <el-option label="升序" value="asc" />
              </el-select>
            </el-col>
          </el-row>
        </div>

        <div class="config-group compact-group">
          <div class="config-group-title">展示配置</div>
          <el-row :gutter="16">
            <el-col :xs="24" :md="12" :xl="12">
              <div class="field-label">图表类型</div>
              <el-select v-model="form.chartType" style="width: 100%">
                <el-option label="柱状图" value="bar" />
                <el-option label="折线图" value="line" />
                <el-option label="饼图" value="pie" />
              </el-select>
            </el-col>
            <el-col :xs="24" :md="12" :xl="12">
              <div class="field-label">Top N</div>
              <el-input-number v-model="form.topN" :min="1" :max="50" style="width: 100%" />
            </el-col>
          </el-row>
        </div>
      </div>
    </section>

    <section class="card filter-card">
      <div class="section-head">
        <div class="section-title">业务筛选</div>
        <div class="section-tip">按需要筛选数据范围，统计结果会同步刷新</div>
      </div>

      <el-row :gutter="16">
        <el-col :xs="24" :md="8" :xl="4">
          <div class="field-label">合同年份</div>
          <el-input-number v-model="form.filters.contractYear" :min="2000" :max="2100" style="width: 100%" />
        </el-col>
        <el-col :xs="24" :md="8" :xl="4">
          <div class="field-label">风险类型</div>
          <el-select v-model="form.filters.typeRisk" style="width: 100%" clearable>
            <el-option label="摩托车" :value="1" />
            <el-option label="货车" :value="2" />
            <el-option label="乘用车" :value="3" />
            <el-option label="农用车" :value="4" />
          </el-select>
        </el-col>
        <el-col :xs="24" :md="8" :xl="4">
          <div class="field-label">地区</div>
          <el-select v-model="form.filters.area" style="width: 100%" clearable>
            <el-option label="农村" :value="0" />
            <el-option label="城市" :value="1" />
          </el-select>
        </el-col>
        <el-col :xs="24" :md="8" :xl="4">
          <div class="field-label">分销渠道</div>
          <el-select v-model="form.filters.distributionChannel" style="width: 100%" clearable>
            <el-option label="代理人" :value="0" />
            <el-option label="保险经纪" :value="1" />
          </el-select>
        </el-col>
        <el-col :xs="24" :md="8" :xl="4">
          <div class="field-label">缴费方式</div>
          <el-select v-model="form.filters.payment" style="width: 100%" clearable>
            <el-option label="年缴" :value="0" />
            <el-option label="半年缴" :value="1" />
          </el-select>
        </el-col>
        <el-col :xs="24" :md="8" :xl="4">
          <div class="field-label">车辆注册年份起</div>
          <el-input-number
            v-model="form.filters.yearMatriculationStart"
            :min="1900"
            :max="2100"
            style="width: 100%"
          />
        </el-col>
      </el-row>

      <el-row :gutter="16" class="config-row">
        <el-col :xs="24" :md="8" :xl="4">
          <div class="field-label">车辆注册年份止</div>
          <el-input-number
            v-model="form.filters.yearMatriculationEnd"
            :min="1900"
            :max="2100"
            style="width: 100%"
          />
        </el-col>
        <el-col :xs="24" :md="16" :xl="20">
          <div class="filter-actions">
            <div class="filter-actions-tip">调整筛选条件后重新生成当前统计结果</div>
            <div class="filter-actions-buttons">
              <el-button type="primary" :loading="loading" @click="loadAnalytics">开始分析</el-button>
              <el-button @click="resetForm">重置条件</el-button>
            </div>
          </div>
        </el-col>
      </el-row>
    </section>

    <section class="summary-grid">
      <div v-for="item in summaryCards" :key="item.key" class="card summary-card">
        <div class="summary-label">{{ item.label }}</div>
        <div class="summary-value">{{ item.displayValue }}</div>
      </div>
    </section>

    <el-row :gutter="18">
      <el-col :xs="24" :xl="14">
        <section class="card chart-card">
          <div class="section-head">
            <div class="section-title">图表视图</div>
            <div class="section-tip">按 {{ currentGroupLabel }} 展示</div>
          </div>
          <div v-loading="loading" ref="chartRef" class="analytics-chart"></div>
        </section>
      </el-col>

      <el-col :xs="24" :xl="10">
        <section class="card table-card">
          <div class="section-head">
            <div class="section-title">明细结果</div>
            <div class="section-tip">共 {{ rows.length }} 组</div>
          </div>
          <el-table :data="rows" style="width: 100%" height="460">
            <el-table-column prop="groupName" :label="currentGroupLabel" min-width="120" />
            <el-table-column
              v-for="metric in form.metrics"
              :key="metric"
              :prop="metric"
              :label="metricLabelMap[metric]"
              min-width="120"
            >
              <template #default="scope">
                {{ formatMetricValue(metric, scope.row[metric]) }}
              </template>
            </el-table-column>
          </el-table>
        </section>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const route = useRoute()
const chartRef = ref(null)
const legendSelection = ref({})
let chartInstance = null

const dimensionOptions = [
  { label: '风险类型', value: 'typeRisk' },
  { label: '地区', value: 'area' },
  { label: '分销渠道', value: 'distributionChannel' },
  { label: '缴费方式', value: 'payment' },
  { label: '合同开始日期', value: 'contractStartDate' },
  { label: '燃料类型', value: 'typeFuel' },
  { label: '车辆注册年份', value: 'yearMatriculation' },
  { label: '第二驾驶员', value: 'secondDriver' },
]

const metricOptions = [
  { label: '保单数', value: 'policyCount' },
  { label: '总保费', value: 'totalPremium' },
  { label: '平均保费', value: 'avgPremium' },
  { label: '理赔记录数', value: 'claimRecordCount' },
  { label: '总赔付金额', value: 'totalClaimsCost' },
  { label: '平均赔付金额', value: 'avgClaimsCost' },
  { label: '出险频率', value: 'claimFrequency' },
  { label: '赔付率', value: 'lossRatio' },
]

const subjectMetricMap = {
  policy: ['policyCount', 'totalPremium', 'avgPremium'],
  claim: ['claimRecordCount', 'totalClaimsCost', 'avgClaimsCost', 'claimFrequency', 'lossRatio'],
}

const subjectDefaultConfig = {
  policy: {
    groupBy: 'distributionChannel',
    metrics: ['policyCount', 'totalPremium', 'avgPremium'],
    sortBy: 'totalPremium',
  },
  claim: {
    groupBy: 'typeRisk',
    metrics: ['claimRecordCount', 'totalClaimsCost', 'lossRatio'],
    sortBy: 'totalClaimsCost',
  },
}

const metricLabelMap = metricOptions.reduce((acc, item) => {
  acc[item.value] = item.label
  return acc
}, {})

const metricKeyByLabel = metricOptions.reduce((acc, item) => {
  acc[item.label] = item.value
  return acc
}, {})

const dimensionLabelMap = dimensionOptions.reduce((acc, item) => {
  acc[item.value] = item.label
  return acc
}, {})

const ratioMetrics = ['claimFrequency', 'lossRatio']
const currencyMetrics = ['totalPremium', 'avgPremium', 'totalClaimsCost', 'avgClaimsCost']
const chartColors = ['#2f7d6b', '#c96c45', '#4d7db8', '#9a6fd1', '#d1a43f', '#4f9b8f']

const buildEmptyFilters = () => ({
  contractYear: null,
  typeRisk: null,
  area: null,
  distributionChannel: null,
  payment: null,
  yearMatriculationStart: null,
  yearMatriculationEnd: null,
})

const form = reactive({
  subject: 'policy',
  groupBy: 'distributionChannel',
  metrics: ['policyCount', 'totalPremium', 'avgPremium'],
  chartType: 'bar',
  sortBy: 'totalPremium',
  sortOrder: 'desc',
  topN: 10,
  filters: buildEmptyFilters(),
})

const loading = ref(false)
const summary = ref({})
const rows = ref([])

const getSubjectFromRoute = () => (route.meta?.analyticsSubject === 'claim' ? 'claim' : 'policy')

const availableMetrics = computed(() => {
  const allowed = new Set(subjectMetricMap[form.subject] || subjectMetricMap.policy)
  return metricOptions.filter((item) => allowed.has(item.value))
})

const subjectTitle = computed(() => (form.subject === 'claim' ? '理赔分析' : '保单经营分析'))
const currentGroupLabel = computed(() => dimensionLabelMap[form.groupBy] || '分析目标')
const selectedMetricLabels = computed(() => form.metrics.map((metric) => metricLabelMap[metric]).filter(Boolean))

const summaryCards = computed(() => {
  return form.metrics.map((metric) => ({
    key: metric,
    label: metricLabelMap[metric],
    displayValue: formatMetricValue(metric, summary.value?.[metric]),
  }))
})

const syncLegendSelection = (resetAll = false) => {
  const next = {}
  form.metrics.forEach((metric) => {
    next[metric] = resetAll ? true : legendSelection.value[metric] !== false
  })
  legendSelection.value = next
}

const applySubjectDefaults = (subject, preserveFilters = true) => {
  const config = subjectDefaultConfig[subject] || subjectDefaultConfig.policy
  form.subject = subject
  form.groupBy = config.groupBy
  form.metrics = [...config.metrics]
  form.sortBy = config.sortBy
  form.sortOrder = 'desc'
  form.chartType = 'bar'
  form.topN = 10
  if (!preserveFilters) {
    form.filters = buildEmptyFilters()
  }
  syncLegendSelection(true)
}

const resetForm = () => {
  applySubjectDefaults(getSubjectFromRoute(), false)
  loadAnalytics()
}

const formatMetricValue = (metric, value) => {
  const number = Number(value || 0)
  if (ratioMetrics.includes(metric)) {
    return `${(number * 100).toFixed(2)}%`
  }
  if (currencyMetrics.includes(metric)) {
    return `￥${number.toFixed(2)}`
  }
  return number.toLocaleString('zh-CN')
}

const formatCompactNumber = (value) => {
  const number = Number(value || 0)
  const abs = Math.abs(number)
  if (abs >= 100000000) {
    return `${(number / 100000000).toFixed(1)}亿`
  }
  if (abs >= 10000) {
    return `${(number / 10000).toFixed(1)}万`
  }
  return number.toLocaleString('zh-CN')
}

const getAxisName = (metric) => {
  if (ratioMetrics.includes(metric)) {
    return `${metricLabelMap[metric]} (%)`
  }
  if (currencyMetrics.includes(metric)) {
    return `${metricLabelMap[metric]} (元)`
  }
  return metricLabelMap[metric]
}

const formatAxisTick = (metric, value) => {
  const number = Number(value || 0)
  if (ratioMetrics.includes(metric)) {
    return `${(number * 100).toFixed(0)}%`
  }
  return formatCompactNumber(number)
}

const buildLegendSelectedMap = (metrics) => {
  return metrics.reduce((acc, metric) => {
    acc[metricLabelMap[metric]] = legendSelection.value[metric] !== false
    return acc
  }, {})
}

const buildRequestPayload = () => ({
  subject: form.subject,
  groupBy: form.groupBy,
  metrics: form.metrics,
  sortBy: form.sortBy,
  sortOrder: form.sortOrder,
  topN: form.topN,
  filters: {
    ...form.filters,
  },
})

const buildChartOption = () => {
  const sourceRows = rows.value || []
  const names = sourceRows.map((item) => item.groupName)
  const selected = form.metrics.filter((metric) => metricLabelMap[metric])
  const visibleMetrics = selected.filter((metric) => legendSelection.value[metric] !== false)
  const firstMetric = visibleMetrics[0] || selected[0]
  const legendData = selected.map((metric) => metricLabelMap[metric])
  const legendSelected = buildLegendSelectedMap(selected)

  if (!selected.length) {
    return {
      title: {
        text: '请至少选择一个统计指标',
        left: 'center',
        top: 'middle',
        textStyle: { color: '#7b8d86', fontSize: 16, fontWeight: 500 },
      },
    }
  }

  if (!sourceRows.length) {
    return {
      title: {
        text: '当前条件下暂无数据',
        left: 'center',
        top: 'middle',
        textStyle: { color: '#7b8d86', fontSize: 16, fontWeight: 500 },
      },
    }
  }

  if (form.chartType === 'pie') {
    return {
      color: chartColors,
      tooltip: { trigger: 'item' },
      legend: {
        bottom: 0,
        data: legendData,
        selected: legendSelected,
      },
      series: [{
        name: metricLabelMap[firstMetric],
        type: 'pie',
        radius: ['38%', '68%'],
        itemStyle: { borderRadius: 12, borderColor: '#fff', borderWidth: 2 },
        data: sourceRows.map((item) => ({
          name: item.groupName,
          value: Number(item[firstMetric] || 0),
        })),
      }],
    }
  }

  if (!visibleMetrics.length) {
    return {
      color: chartColors,
      legend: {
        top: 0,
        data: legendData,
        selected: legendSelected,
      },
      grid: {
        left: 48,
        right: 48,
        top: 60,
        bottom: 50,
      },
      xAxis: {
        type: 'category',
        data: names,
        show: false,
      },
      yAxis: [
        {
          type: 'value',
          show: false,
        },
      ],
      series: selected.map((metric) => ({
        id: metric,
        name: metricLabelMap[metric],
        type: form.chartType,
        smooth: form.chartType === 'line',
        yAxisIndex: 0,
        data: [],
      })),
      graphic: [{
        type: 'text',
        left: 'center',
        top: 'middle',
        style: {
          text: '已隐藏全部指标，请点击上方图例重新显示',
          fill: '#7b8d86',
          fontSize: 16,
          fontWeight: 500,
        },
      }],
    }
  }

  const yAxis = visibleMetrics.map((metric, index) => {
    const position = index % 2 === 0 ? 'left' : 'right'
    const offset = Math.floor(index / 2) * 56
    return {
      type: 'value',
      name: getAxisName(metric),
      position,
      offset,
      alignTicks: true,
      axisLine: {
        show: true,
        lineStyle: {
          color: chartColors[index % chartColors.length],
        },
      },
      axisLabel: {
        formatter: (value) => formatAxisTick(metric, value),
      },
      splitLine: {
        show: index === 0,
      },
    }
  })

  const leftAxisCount = yAxis.filter((item) => item.position === 'left').length
  const rightAxisCount = yAxis.filter((item) => item.position === 'right').length
  const axisIndexMap = visibleMetrics.reduce((acc, metric, index) => {
    acc[metric] = index
    return acc
  }, {})

  return {
    color: chartColors,
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const source = Array.isArray(params) ? params : [params]
        const title = source[0]?.axisValueLabel || ''
        const lines = source.map((item) => `${item.marker}${item.seriesName}：${formatMetricValue(item.seriesId, item.value)}`)
        return [title, ...lines].join('<br/>')
      },
    },
    legend: {
      top: 0,
      data: legendData,
      selected: legendSelected,
    },
    grid: {
      left: 56 + Math.max(0, leftAxisCount - 1) * 56,
      right: 64 + Math.max(0, rightAxisCount - 1) * 56,
      top: 60,
      bottom: 50,
    },
    xAxis: {
      type: 'category',
      data: names,
      axisLabel: { interval: 0, rotate: names.length > 6 ? 25 : 0 },
    },
    yAxis,
    series: selected.map((metric) => ({
      id: metric,
      name: metricLabelMap[metric],
      type: form.chartType,
      smooth: form.chartType === 'line',
      yAxisIndex: axisIndexMap[metric] ?? 0,
      emphasis: { focus: 'series' },
      data: axisIndexMap[metric] === undefined
        ? []
        : sourceRows.map((item) => Number(item[metric] || 0)),
    })),
  }
}

const handleLegendSelectionChanged = (event) => {
  if (form.chartType === 'pie') {
    return
  }
  const metric = metricKeyByLabel[event.name]
  if (!metric) {
    return
  }
  const next = {}
  form.metrics.forEach((metricKey) => {
    const label = metricLabelMap[metricKey]
    next[metricKey] = event.selected[label] !== false
  })
  legendSelection.value = next
  renderChart()
}

const renderChart = async () => {
  await nextTick()
  if (!chartRef.value) return
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }
  chartInstance.off('legendselectchanged')
  chartInstance.on('legendselectchanged', handleLegendSelectionChanged)
  chartInstance.setOption(buildChartOption(), true)
  chartInstance.resize()
}

const loadAnalytics = async () => {
  if (!form.metrics.length) {
    ElMessage.warning('请至少选择一个统计指标')
    return
  }

  try {
    loading.value = true
    const res = await request.post('/analytics/query', buildRequestPayload())
    if (res.code === '200' && res.data) {
      summary.value = res.data.summary || {}
      rows.value = res.data.rows || []
      syncLegendSelection(false)
      await renderChart()
      return
    }
    ElMessage.error(res.msg || '加载分析数据失败')
  } catch (error) {
    console.error(error)
    ElMessage.error('加载分析数据失败')
  } finally {
    loading.value = false
  }
}

const handleResize = () => {
  chartInstance?.resize()
}

watch(
  () => route.fullPath,
  () => {
    applySubjectDefaults(getSubjectFromRoute(), true)
    loadAnalytics()
  },
  { immediate: true }
)

watch(
  () => form.subject,
  () => {
    const allowedMetrics = new Set(subjectMetricMap[form.subject] || [])
    form.metrics = form.metrics.filter((metric) => allowedMetrics.has(metric))
    if (!form.metrics.length) {
      form.metrics = [...subjectDefaultConfig[form.subject].metrics]
    }
    if (!allowedMetrics.has(form.sortBy)) {
      form.sortBy = form.metrics[0]
    }
    syncLegendSelection(true)
  }
)

watch(
  () => form.metrics,
  () => {
    syncLegendSelection(false)
  },
  { deep: true }
)

watch(
  () => [form.chartType, rows.value, form.metrics],
  () => {
    renderChart()
  },
  { deep: true }
)

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.off('legendselectchanged', handleLegendSelectionChanged)
  chartInstance?.dispose()
  chartInstance = null
})
</script>

<style scoped>
.analytics-shell {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.analytics-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 22px 24px;
  background:
    radial-gradient(circle at top right, rgba(91, 143, 203, 0.16), transparent 28%),
    radial-gradient(circle at bottom left, rgba(47, 125, 107, 0.12), transparent 30%),
    linear-gradient(135deg, rgba(47, 125, 107, 0.12), rgba(255, 255, 255, 0.96) 45%);
}

.analytics-eyebrow {
  color: #6f8b82;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.analytics-title {
  margin: 8px 0 0;
  color: #223932;
  font-size: 30px;
}

.analytics-subtitle {
  margin: 10px 0 0;
  color: #6f847d;
  font-size: 14px;
  line-height: 1.7;
}

.analytics-hero-note {
  min-width: 260px;
  padding: 16px 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(95, 123, 114, 0.12);
  color: #335349;
  line-height: 1.8;
}

.config-card,
.filter-card,
.chart-card,
.table-card {
  padding: 20px 22px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.section-title {
  color: #233a33;
  font-size: 18px;
  font-weight: 700;
}

.section-tip {
  color: #7c9189;
  font-size: 13px;
}

.config-panel {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr);
  gap: 16px;
}

.config-group {
  padding: 18px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(248, 251, 249, 0.95), rgba(243, 248, 245, 0.9));
  border: 1px solid rgba(103, 133, 122, 0.14);
}

.emphasis-group {
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
}

.compact-group {
  align-self: stretch;
}

.config-group-title {
  margin-bottom: 14px;
  color: #29473f;
  font-size: 15px;
  font-weight: 700;
}

.field-label {
  margin-bottom: 8px;
  color: #5f756d;
  font-size: 13px;
  font-weight: 600;
}

.config-row {
  margin-top: 12px;
}

.filter-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 100%;
  padding: 14px 16px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(244, 249, 246, 0.96), rgba(236, 244, 240, 0.88));
  border: 1px dashed rgba(97, 130, 119, 0.28);
}

.filter-actions-tip {
  color: #637b72;
  font-size: 13px;
  line-height: 1.7;
}

.filter-actions-buttons {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.summary-card {
  padding: 18px;
  background: linear-gradient(135deg, rgba(248, 251, 249, 0.98), rgba(234, 244, 239, 0.9));
}

.summary-label {
  color: #738981;
  font-size: 13px;
}

.summary-value {
  margin-top: 12px;
  color: #214137;
  font-size: 28px;
  font-weight: 700;
  word-break: break-word;
}

.analytics-chart {
  height: 460px;
}

@media (max-width: 1280px) {
  .config-panel {
    grid-template-columns: 1fr;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .analytics-hero {
    flex-direction: column;
    align-items: flex-start;
  }

  .analytics-hero-note {
    width: 100%;
    min-width: 0;
  }

  .section-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .filter-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-actions-buttons {
    width: 100%;
  }

  .filter-actions-buttons :deep(.el-button) {
    flex: 1;
  }
}
</style>
