<template>
  <div>
    <div class="card hero-card">
      <div>
        <div class="hero-title">训练结果总览</div>
      </div>
      <div class="hero-meta">
        <el-tag size="large" :type="statusTagType">{{ statusText }}</el-tag>
        <div class="hero-job-id">任务 ID：{{ route.params.jobId }}</div>
      </div>
    </div>

    <div class="card section-card action-card">
      <div class="section-head">
        <div>
          <div class="section-title">结果操作</div>
        </div>
      </div>

      <el-row :gutter="12" class="save-row">
        <el-col :xs="24" :sm="8" :lg="6">
          <el-select v-model="saveForm.checkpointType" :disabled="!isCompleted">
            <el-option label="Best 权重" value="best" />
            <el-option label="Last 权重" value="last" />
          </el-select>
        </el-col>
        <el-col :xs="24" :sm="16" :lg="10">
          <el-input
            v-model="saveForm.fileName"
            :disabled="!isCompleted"
            placeholder="请输入保存的权重文件名"
          />
        </el-col>
        <el-col :xs="24" :sm="24" :lg="8" class="action-buttons">
          <el-button
            type="primary"
            :loading="savingWeights"
            :disabled="!isCompleted"
            @click="handleSaveWeights"
          >
            保存当前权重
          </el-button>
          <el-button @click="goBack">返回训练页面</el-button>
        </el-col>
      </el-row>

      <div v-if="savedWeights.length" class="saved-list">
        <div class="saved-title">已保存权重</div>
        <div
          v-for="item in savedWeights"
          :key="`${item.fileName}-${item.savedAt}`"
          class="saved-item"
        >
          <div>文件名：{{ item.fileName }}</div>
          <div>类型：{{ item.checkpointType }}</div>
          <div class="saved-path">路径：{{ item.filePath }}</div>
          <div class="saved-time">保存时间：{{ item.savedAt }}</div>
        </div>
      </div>
    </div>

    <div v-if="currentJob" class="card section-card">
      <div class="section-title">训练状态</div>
      <div class="status-row">
        <div class="status-inline">
          <el-tag :type="statusTagType">{{ statusText }}</el-tag>
          <span class="status-hint">已完成 {{ currentEpoch }} / {{ totalEpochs }} 个 epoch</span>
        </div>
        <div class="status-time">开始时间：{{ currentJob.startedAt || '-' }}</div>
      </div>

      <el-progress :percentage="progressPercent" :status="progressBarStatus" :stroke-width="16" />

      <el-alert
        v-if="isRunning"
        title="任务仍在执行中，页面会自动刷新状态，训练完成后指标和图像会完整展示。"
        type="info"
        show-icon
        :closable="false"
        style="margin-top: 16px"
      />

      <el-alert
        v-if="currentJob.error"
        :title="currentJob.error"
        type="error"
        show-icon
        :closable="false"
        style="margin-top: 16px"
      />
    </div>

    <template v-if="summary">
      <div class="metric-grid">
        <div
          v-for="card in metricCards"
          :key="card.label"
          class="metric-card"
          :style="{ background: card.background }"
        >
          <div class="metric-label">{{ card.label }}</div>
          <div class="metric-value">{{ card.value }}</div>
        </div>
      </div>

      <el-row :gutter="18">
        <el-col :xs="24" :lg="12">
          <div class="card section-card">
            <div class="section-title">分类别评估报告</div>
            <pre class="report-box">{{ summary.classificationReport || '暂无分类报告' }}</pre>
          </div>
        </el-col>

        <el-col :xs="24" :lg="12">
          <div class="card section-card">
            <div class="section-title">测试集摘要</div>
            <el-descriptions :column="1" border>
              <el-descriptions-item label="最终阈值">{{ formatMetric(summary.finalThreshold) }}</el-descriptions-item>
              <el-descriptions-item label="监控指标">{{ summary.monitorMetric || '-' }}</el-descriptions-item>
              <el-descriptions-item label="最佳监控值">{{ formatMetric(summary.bestMonitorValue) }}</el-descriptions-item>
              <el-descriptions-item label="正样本权重">{{ formatMetric(summary.resolvedPosWeight) }}</el-descriptions-item>
              <el-descriptions-item label="训练集正样本占比">{{ formatPercent(summary.trainPositiveRate) }}</el-descriptions-item>
              <el-descriptions-item label="完成轮数">
                {{ summary.epochsCompleted || 0 }} / {{ summary.configuredEpochs || 0 }}
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </el-col>
      </el-row>

      <div class="card section-card">
        <div class="section-title">本次训练使用的超参数</div>

        <div class="parameter-grid">
          <div v-for="group in hyperParameterGroups" :key="group.title" class="parameter-card">
            <div class="parameter-title">{{ group.title }}</div>
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item
                v-for="item in group.items"
                :key="item.label"
                :label="item.label"
              >
                {{ item.value }}
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </div>
      </div>

      <div class="card section-card">
        <div class="section-title">训练评估图像</div>

        <div class="chart-grid">
          <div v-for="figure in figureCards" :key="figure.key" class="chart-card image-card">
            <div class="chart-title">{{ figure.title }}</div>
            <div class="image-meta">{{ figure.fileName || '图像文件待生成' }}</div>
            <img v-if="figure.url" :src="figure.url" :alt="figure.title" class="chart-image" />
            <el-empty v-else :description="`${figure.title} 暂无图像`" />
          </div>
        </div>
      </div>
    </template>

    <el-empty
      v-else-if="!loading"
      description="未查询到训练结果，请返回训练页面重新发起任务。"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/request'

const route = useRoute()
const router = useRouter()

const currentJob = ref(null)
const loading = ref(false)
const savingWeights = ref(false)
const saveForm = reactive({
  checkpointType: 'best',
  fileName: '',
})

let pollTimer = null

const isCompleted = computed(() => currentJob.value?.status === 'completed')
const isRunning = computed(() => currentJob.value?.status === 'running')
const currentEpoch = computed(() => Number(currentJob.value?.currentEpoch || 0))
const totalEpochs = computed(() => Number(currentJob.value?.totalEpochs || 0))
const progressPercent = computed(() => {
  const progress = Number(currentJob.value?.progress || 0)
  return Math.min(100, Math.max(0, Number((progress * 100).toFixed(1))))
})
const progressBarStatus = computed(() => {
  if (currentJob.value?.status === 'failed') return 'exception'
  if (currentJob.value?.status === 'completed') return 'success'
  return ''
})
const statusText = computed(() => {
  const map = {
    running: '训练中',
    completed: '已完成',
    failed: '训练失败',
  }
  return map[currentJob.value?.status] || '加载中'
})
const statusTagType = computed(() => {
  const map = {
    running: 'warning',
    completed: 'success',
    failed: 'danger',
  }
  return map[currentJob.value?.status] || 'info'
})
const summary = computed(() => currentJob.value?.summary || null)
const savedWeights = computed(() => currentJob.value?.savedWeights || [])
const hasSavedWeights = computed(() => savedWeights.value.length > 0)
const resolvedConfig = computed(() => currentJob.value?.resolvedConfig || {})
const figureFiles = computed(() => currentJob.value?.artifacts?.figureFiles || {})
const assetVersion = computed(() => currentJob.value?.finishedAt || currentJob.value?.currentEpoch || 'latest')

const formatMetric = (value, digits = 4) => {
  if (value === undefined || value === null || value === '') return '-'
  return Number(value).toFixed(digits)
}

const formatPercent = (value) => {
  if (value === undefined || value === null || value === '') return '-'
  return `${(Number(value) * 100).toFixed(2)}%`
}

const formatDisplayValue = (value) => {
  if (Array.isArray(value)) return value.length ? value.join(' -> ') : '-'
  if (typeof value === 'boolean') return value ? '是' : '否'
  if (value === undefined || value === null || value === '') return '-'
  if (typeof value === 'number' && (Math.abs(value) >= 1000 || (Math.abs(value) > 0 && Math.abs(value) < 0.001))) {
    return Number(value).toExponential(2)
  }
  return String(value)
}

const getBackendBaseUrl = () => {
  const configuredBaseUrl = request.defaults.baseURL
  if (!configuredBaseUrl) return window.location.origin
  try {
    return new URL(configuredBaseUrl, window.location.origin).toString()
  } catch (error) {
    return window.location.origin
  }
}

const buildFigureUrl = (figureKey) => {
  const jobId = currentJob.value?.jobId || route.params.jobId
  if (!jobId || !figureKey) return ''
  const relativePath = `/modelTraining/jobs/${encodeURIComponent(jobId)}/figures/${encodeURIComponent(figureKey)}`
  const url = new URL(relativePath, getBackendBaseUrl())
  url.searchParams.set('v', String(assetVersion.value))
  return url.toString()
}

const metricCards = computed(() => {
  const metrics = summary.value?.finalMetrics || {}
  return [
    { label: 'Accuracy', value: formatPercent(metrics.accuracy), background: 'linear-gradient(135deg, #2563eb, #38bdf8)' },
    { label: 'Precision', value: formatPercent(metrics.precision), background: 'linear-gradient(135deg, #0f766e, #34d399)' },
    { label: 'Recall', value: formatPercent(metrics.recall), background: 'linear-gradient(135deg, #d97706, #f59e0b)' },
    { label: 'F1 Score', value: formatPercent(metrics.f1), background: 'linear-gradient(135deg, #c026d3, #ec4899)' },
    { label: 'TestLoss', value: formatMetric(metrics.loss), background: 'linear-gradient(135deg, #475569, #0f172a)' },
  ]
})

const hyperParameterGroups = computed(() => {
  const cfg = resolvedConfig.value
  const scheduler = cfg.scheduler || {}
  const train = cfg.train || {}
  const data = cfg.data || {}
  const model = cfg.model || {}
  const loss = cfg.loss || {}
  const optimizer = cfg.optimizer || {}

  return [
    {
      title: '核心训练参数',
      items: [
        { label: '训练轮数', value: formatDisplayValue(train.num_epochs) },
        { label: 'Batch Size', value: formatDisplayValue(data.batch_size) },
        { label: '学习率', value: formatDisplayValue(optimizer.lr) },
        { label: '优化器', value: formatDisplayValue(optimizer.optimizer) },
        { label: '监控指标', value: formatDisplayValue(train.early_stop_metric) },
        { label: '阈值搜索目标', value: formatDisplayValue(train.threshold_metric) },
        { label: '调度器', value: formatDisplayValue(scheduler.scheduler) },
      ],
    },
    {
      title: '网络结构参数',
      items: [
        { label: '主干隐藏层', value: formatDisplayValue(model.hidden_dims) },
        { label: '分类头隐藏层', value: formatDisplayValue(model.head_hidden_dim) },
        { label: '输入 Dropout', value: formatDisplayValue(model.input_dropout) },
        { label: '主干 Dropout', value: formatDisplayValue(model.backbone_dropout) },
        { label: '分类头 Dropout', value: formatDisplayValue(model.head_dropout) },
      ],
    },
    {
      title: '损失与训练控制',
      items: [
        { label: 'Pos Weight', value: formatDisplayValue(loss.pos_weight) },
        { label: 'Label Smoothing', value: formatDisplayValue(loss.label_smoothing) },
        { label: 'Early Stop', value: formatDisplayValue(train.early_stop) },
        { label: 'Patience', value: formatDisplayValue(train.patience) },
        { label: 'Min Delta', value: formatDisplayValue(train.min_delta) },
        { label: 'Grad Clip', value: formatDisplayValue(train.grad_clip) },
      ],
    },
    {
      title: '默认辅助参数',
      items: [
        { label: 'Validation Ratio', value: formatDisplayValue(data.val_ratio) },
        { label: 'Test Ratio', value: formatDisplayValue(data.test_ratio) },
        { label: 'Random Seed', value: formatDisplayValue(data.random_seed) },
        { label: 'Warmup Epochs', value: formatDisplayValue(scheduler.warmup_epochs) },
        { label: 'Min LR', value: formatDisplayValue(scheduler.min_lr) },
        { label: 'Threshold Auto Search', value: formatDisplayValue(train.auto_threshold) },
      ],
    },
  ]
})

const figureCards = computed(() => ([
  { key: 'lossCurve', title: '训练损失 / 验证损失' },
  { key: 'accuracyCurve', title: '训练准确率 / 验证准确率' },
  { key: 'valPrAucCurve', title: '验证 PR-AUC' },
  { key: 'confusionMatrix', title: '混淆矩阵' },
]).map((item) => ({
  ...item,
  fileName: figureFiles.value?.[item.key] || '',
  url: figureFiles.value?.[item.key] ? buildFigureUrl(item.key) : '',
})))

const stopPolling = () => {
  if (!pollTimer) return
  clearInterval(pollTimer)
  pollTimer = null
}

const loadJob = async () => {
  if (!route.params.jobId) return
  try {
    loading.value = true
    const res = await request.get(`/modelTraining/jobs/${route.params.jobId}`)
    if (String(res.code) !== '200') {
      ElMessage.error(res.msg || '训练结果加载失败')
      return
    }
    currentJob.value = res.data
    if (!saveForm.fileName && res.data?.jobId) {
      saveForm.fileName = `claim-training-${res.data.jobId}.pth`
    }
    if (res.data?.status === 'running' && !pollTimer) {
      startPolling()
    }
  } catch (error) {
    console.error(error)
    ElMessage.error('训练结果加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

const startPolling = () => {
  stopPolling()
  pollTimer = setInterval(async () => {
    await loadJob()
    if (currentJob.value?.status !== 'running') {
      stopPolling()
    }
  }, 2500)
}

const handleSaveWeights = async () => {
  if (!currentJob.value?.jobId) {
    ElMessage.warning('当前没有可保存的训练任务')
    return
  }
  if (!saveForm.fileName.trim()) {
    ElMessage.warning('请输入目标权重文件名')
    return
  }

  try {
    savingWeights.value = true
    const res = await request.post(`/modelTraining/jobs/${currentJob.value.jobId}/save-weights`, saveForm)
    if (String(res.code) !== '200') {
      ElMessage.error(res.msg || '保存权重失败')
      return
    }
    ElMessage.success('权重文件保存成功')
    await loadJob()
  } catch (error) {
    console.error(error)
    ElMessage.error('保存权重失败，请稍后重试')
  } finally {
    savingWeights.value = false
  }
}

const discardCurrentJob = async () => {
  if (!currentJob.value?.jobId) return
  await request.post(`/modelTraining/jobs/${currentJob.value.jobId}/discard`)
}

const goBack = async () => {
  if (!isCompleted.value || hasSavedWeights.value) {
    router.push({ name: 'ModelTraining' })
    return
  }

  try {
    await ElMessageBox.confirm('是否丢弃本次训练权重？', '返回训练页面', {
      confirmButtonText: '丢弃并返回',
      cancelButtonText: '继续查看',
      type: 'warning',
      closeOnClickModal: false,
    })
    await discardCurrentJob()
    ElMessage.success('本次训练成果已丢弃')
    router.push({ name: 'ModelTraining' })
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    console.error(error)
    ElMessage.error('丢弃训练成果失败，请稍后重试')
  }
}

watch(
  () => route.params.jobId,
  async () => {
    stopPolling()
    currentJob.value = null
    saveForm.fileName = ''
    await loadJob()
  }
)

onMounted(async () => {
  await loadJob()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.hero-card {
  margin-bottom: 18px;
  padding: 22px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: linear-gradient(135deg, rgba(15, 118, 110, 0.08), rgba(59, 130, 246, 0.16)), #fff;
}

.hero-title {
  font-size: 22px;
  font-weight: 700;
  color: #0f766e;
}

.hero-meta {
  min-width: 220px;
  text-align: right;
}

.hero-job-id {
  margin-top: 8px;
  color: #475569;
  font-size: 13px;
}

.section-card {
  margin-bottom: 18px;
}

.action-card :deep(.el-select),
.action-card :deep(.el-input) {
  width: 100%;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.section-title {
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
}

.save-row {
  margin-top: 16px;
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.saved-list {
  margin-top: 16px;
  border-top: 1px dashed #dbe2ea;
  padding-top: 14px;
}

.saved-title {
  margin-bottom: 10px;
  font-weight: 600;
  color: #0f172a;
}

.saved-item {
  padding: 12px 14px;
  border-radius: 12px;
  background: #f8fafc;
  margin-bottom: 10px;
}

.saved-path,
.saved-time {
  margin-top: 4px;
  color: #64748b;
  font-size: 12px;
  word-break: break-all;
}

.status-row {
  margin: 14px 0 10px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.status-inline {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.status-hint,
.status-time {
  color: #475569;
  font-size: 13px;
}

.metric-grid {
  margin: 0 0 18px;
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 14px;
}

.metric-card {
  border-radius: 18px;
  padding: 18px;
  color: #fff;
  min-height: 118px;
}

.metric-label {
  font-size: 13px;
  opacity: 0.92;
}

.metric-value {
  margin-top: 14px;
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
}

.report-box {
  margin: 16px 0 0;
  padding: 14px;
  border-radius: 14px;
  background: #0f172a;
  color: #e2e8f0;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.7;
  min-height: 360px;
}

.parameter-grid {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.parameter-card {
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 14px;
  background: linear-gradient(180deg, #ffffff, #f8fafc);
}

.parameter-title {
  margin-bottom: 12px;
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.chart-grid {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 18px;
}

.chart-card {
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 16px;
  min-height: 350px;
  background: #fff;
}

.image-card {
  display: flex;
  flex-direction: column;
}

.chart-title {
  font-size: 17px;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 10px;
}

.image-meta {
  margin-bottom: 12px;
  color: #64748b;
  font-size: 12px;
  word-break: break-all;
}

.chart-image {
  width: 100%;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: #fff;
  object-fit: contain;
}

@media (max-width: 1400px) {
  .metric-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 1000px) {
  .hero-card {
    flex-direction: column;
    align-items: flex-start;
  }

  .hero-meta {
    text-align: left;
    min-width: 0;
  }

  .parameter-grid,
  .chart-grid,
  .metric-grid {
    grid-template-columns: 1fr;
  }
}
</style>
