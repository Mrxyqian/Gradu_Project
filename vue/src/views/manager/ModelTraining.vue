<template>
  <div>
    <div class="card hero-card">
      <div>
        <div class="hero-title">模型训练中心</div>
      </div>
      <div class="hero-meta">
        <el-tag size="large" :type="statusTagType">{{ statusText }}</el-tag>
        <div v-if="currentJob" class="hero-job-id">任务 ID：{{ currentJob.jobId }}</div>
      </div>
    </div>

    <el-row :gutter="18">
      <el-col :xs="24" :lg="11">
        <div class="card section-card">
          <div class="section-title">训练样本库</div>
          <div class="dataset-summary">
            <div class="summary-item">
              <div class="summary-label">样本总数</div>
              <div class="summary-value">{{ trainDataOverview.totalCount || 0 }}</div>
            </div>
            <div class="summary-item">
              <div class="summary-label">不同ID数</div>
              <div class="summary-value">{{ trainDataOverview.distinctIdCount || 0 }}</div>
            </div>
          </div>

          <el-form label-position="top" class="train-form compact-form">
            <el-form-item label="合同开始年份">
              <el-select v-model="selectedImportYear" clearable placeholder="全部年份" :loading="overviewLoading">
                <el-option v-for="year in availableYears" :key="year" :label="`${year}年`" :value="Number(year)" />
              </el-select>
            </el-form-item>
            <div class="train-actions">
              <el-button type="primary" :loading="importingTrainData" @click="handleImportTrainData">导入到 train_data</el-button>
              <el-button @click="loadTrainDataOverview" :disabled="importingTrainData">刷新</el-button>
            </div>
          </el-form>

          <el-descriptions v-if="lastImportResult" :column="1" border style="margin-top: 16px">
            <el-descriptions-item label="筛选年份">{{ lastImportResult.contractYear || '全部年份' }}</el-descriptions-item>
            <el-descriptions-item label="候选记录数">{{ lastImportResult.candidateCount }}</el-descriptions-item>
            <el-descriptions-item label="处理记录数">{{ lastImportResult.processedCount }}</el-descriptions-item>
            <el-descriptions-item label="新增 / 覆盖">{{ lastImportResult.insertedCount }} / {{ lastImportResult.updatedCount }}</el-descriptions-item>
            <el-descriptions-item label="跳过记录数">{{ lastImportResult.skippedCount }}</el-descriptions-item>
          </el-descriptions>
          <div v-if="lastImportResult?.skippedIds?.length" class="skip-box">
            {{ lastImportResult.skippedIds.join('、') }}
          </div>
        </div>

        <div class="card section-card">
          <div class="section-title">训练参数</div>

          <el-form :model="trainForm" label-position="top" class="train-form">
            <div class="group-title">核心超参数</div>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="优化器">
                  <el-select v-model="trainForm.optimizer">
                    <el-option label="AdamW" value="adamw" />
                    <el-option label="Adam" value="adam" />
                    <el-option label="SGD" value="sgd" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="学习率">
                  <el-input-number v-model="trainForm.learningRate" :min="0.000001" :max="1" :step="0.0001" :precision="6" controls-position="right" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="训练轮数">
                  <el-input-number v-model="trainForm.numEpochs" :min="1" :max="500" controls-position="right" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="Batch Size">
                  <el-input-number v-model="trainForm.batchSize" :min="8" :max="4096" controls-position="right" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="监控指标">
                  <el-select v-model="trainForm.earlyStopMetric">
                    <el-option label="AUC" value="auc" />
                    <el-option label="PR-AUC" value="pr_auc" />
                    <el-option label="Loss" value="loss" />
                    <el-option label="分类 Loss" value="clf_loss" />
                    <el-option label="Accuracy" value="accuracy" />
                    <el-option label="Balanced Accuracy" value="balanced_accuracy" />
                    <el-option label="F1" value="f1" />
                    <el-option label="Precision" value="precision" />
                    <el-option label="Recall" value="recall" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="阈值搜索目标">
                  <el-select v-model="trainForm.thresholdMetric">
                    <el-option label="F1" value="f1" />
                    <el-option label="Precision" value="precision" />
                    <el-option label="Recall" value="recall" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>

            <div class="group-title">隐藏层配置</div>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="主干隐藏层">
                  <el-input v-model="trainForm.hiddenDimsText" placeholder="例如 256,512,512,256,256" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="分类头隐藏层">
                  <el-input-number v-model="trainForm.headHiddenDim" :min="1" :max="2048" controls-position="right" />
                </el-form-item>
              </el-col>
            </el-row>

            <div class="train-actions">
              <el-button type="primary" :loading="starting" :disabled="isRunning" @click="handleStartTraining">
                {{ isRunning ? '训练进行中' : '开始训练' }}
              </el-button>
              <el-button :disabled="isRunning" @click="resetTrainForm">恢复默认配置</el-button>
            </div>
          </el-form>
        </div>
      </el-col>

      <el-col :xs="24" :lg="13">
        <div class="card section-card">
          <div class="section-title">训练进度</div>
          <div class="status-row">
            <div class="status-inline">
              <el-tag :type="statusTagType">{{ statusText }}</el-tag>
              <span v-if="currentJob" class="status-hint">当前已完成 {{ currentEpoch }} / {{ totalEpochs }} 个 epoch</span>
            </div>
            <div v-if="currentJob?.createdAt" class="status-time">创建时间：{{ currentJob.createdAt }}</div>
          </div>

          <el-progress :percentage="progressPercent" :status="progressBarStatus" :stroke-width="16" />

          <el-alert
            v-if="currentJob?.status === 'completed'"
            title="训练已经完成，结果页将自动展示完整指标。"
            type="success"
            show-icon
            :closable="false"
            style="margin-top: 16px"
          />

          <el-alert
            v-if="currentJob?.error"
            :title="currentJob.error"
            type="error"
            show-icon
            :closable="false"
            style="margin-top: 16px"
          />

          <el-descriptions v-if="currentJob" :column="2" border style="margin-top: 16px">
            <el-descriptions-item label="任务 ID">{{ currentJob.jobId }}</el-descriptions-item>
            <el-descriptions-item label="当前阶段">{{ currentJob.message || '-' }}</el-descriptions-item>
            <el-descriptions-item label="开始时间">{{ currentJob.startedAt || '-' }}</el-descriptions-item>
            <el-descriptions-item label="结束时间">{{ currentJob.finishedAt || '-' }}</el-descriptions-item>
            <el-descriptions-item label="当前 Epoch">{{ latestEpoch?.epoch || currentEpoch || 0 }}</el-descriptions-item>
            <el-descriptions-item label="当前学习率">{{ formatScientific(latestEpoch?.learningRate) }}</el-descriptions-item>
            <el-descriptions-item label="训练损失">{{ formatMetric(latestEpoch?.trainLoss) }}</el-descriptions-item>
            <el-descriptions-item label="验证损失">{{ formatMetric(latestEpoch?.valLoss) }}</el-descriptions-item>
            <el-descriptions-item label="训练准确率 / 验证准确率">
              {{ formatPercent(latestEpoch?.trainAccuracy) }} / {{ formatPercent(latestEpoch?.valAccuracy) }}
            </el-descriptions-item>
            <el-descriptions-item label="验证 PR-AUC / F1">
              {{ formatMetric(latestEpoch?.valPrAuc) }} / {{ formatMetric(latestEpoch?.valF1) }}
            </el-descriptions-item>
            <el-descriptions-item label="验证 Precision / Recall">
              {{ formatMetric(latestEpoch?.valPrecision) }} / {{ formatMetric(latestEpoch?.valRecall) }}
            </el-descriptions-item>
            <el-descriptions-item label="当前阈值">{{ formatMetric(latestEpoch?.bestThreshold) }}</el-descriptions-item>
          </el-descriptions>

          <el-empty v-else description="暂无训练任务" />
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const router = useRouter()

const defaultTrainForm = () => ({
  numEpochs: 100,
  batchSize: 128,
  optimizer: 'adamw',
  learningRate: 0.0002,
  earlyStopMetric: 'auc',
  thresholdMetric: 'f1',
  hiddenDimsText: '256,512,512,256,256',
  headHiddenDim: 64,
})

const trainForm = reactive(defaultTrainForm())
const currentJob = ref(null)
const starting = ref(false)
const trackedJobId = ref('')
let pollTimer = null

const trainDataOverview = ref({
  totalCount: 0,
  distinctIdCount: 0,
  availableYears: [],
})
const selectedImportYear = ref(null)
const importingTrainData = ref(false)
const overviewLoading = ref(false)
const lastImportResult = ref(null)

const availableYears = computed(() => trainDataOverview.value.availableYears || [])

const statusText = computed(() => {
  const map = {
    running: '训练中',
    completed: '已完成',
    failed: '训练失败',
  }
  return map[currentJob.value?.status] || '未开始'
})

const statusTagType = computed(() => {
  const map = {
    running: 'warning',
    completed: 'success',
    failed: 'danger',
  }
  return map[currentJob.value?.status] || 'info'
})

const isRunning = computed(() => currentJob.value?.status === 'running')
const currentEpoch = computed(() => Number(currentJob.value?.currentEpoch || 0))
const totalEpochs = computed(() => Number(currentJob.value?.totalEpochs || 0))
const latestEpoch = computed(() => currentJob.value?.latestEpoch || null)
const progressPercent = computed(() => {
  const progress = Number(currentJob.value?.progress || 0)
  return Math.min(100, Math.max(0, Number((progress * 100).toFixed(1))))
})
const progressBarStatus = computed(() => {
  if (currentJob.value?.status === 'failed') return 'exception'
  if (currentJob.value?.status === 'completed') return 'success'
  return ''
})

const resetTrainForm = () => {
  Object.assign(trainForm, defaultTrainForm())
}

const parseHiddenDims = (value) => {
  const tokens = String(value || '')
    .split(',')
    .map(item => item.trim())
    .filter(Boolean)

  if (!tokens.length) return null

  const dims = tokens.map((item) => Number(item))
  if (dims.some(item => !Number.isInteger(item) || item <= 0)) {
    return null
  }
  return dims
}

const formatMetric = (value, digits = 4) => {
  if (value === undefined || value === null || value === '') return '-'
  return Number(value).toFixed(digits)
}

const formatPercent = (value) => {
  if (value === undefined || value === null || value === '') return '-'
  return `${(Number(value) * 100).toFixed(2)}%`
}

const formatScientific = (value) => {
  if (value === undefined || value === null || value === '') return '-'
  return Number(value).toExponential(2)
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const openResultPage = async (jobId) => {
  if (!jobId) return
  await router.push({
    name: 'ModelTrainingResult',
    params: { jobId },
  })
}

const loadLatestJob = async () => {
  const res = await request.get('/modelTraining/jobs/latest')
  if (res.code === '200' && res.data) {
    currentJob.value = res.data
    if (res.data.status === 'running') {
      trackedJobId.value = res.data.jobId
      startPolling()
    }
  }
}

const loadJob = async (jobId) => {
  if (!jobId) return
  const res = await request.get(`/modelTraining/jobs/${jobId}`)
  if (res.code === '200') {
    currentJob.value = res.data
  }
}

const startPolling = () => {
  stopPolling()
  pollTimer = setInterval(async () => {
    if (!currentJob.value?.jobId) return
    await loadJob(currentJob.value.jobId)
    if (currentJob.value?.status !== 'running') {
      stopPolling()
    }
  }, 2500)
}

const loadTrainDataOverview = async () => {
  try {
    overviewLoading.value = true
    const res = await request.get('/modelTraining/trainData/overview')
    if (res.code === '200' && res.data) {
      trainDataOverview.value = res.data
    }
  } catch (error) {
    console.error(error)
    ElMessage.error('加载 train_data 概览失败')
  } finally {
    overviewLoading.value = false
  }
}

const handleImportTrainData = async () => {
  try {
    importingTrainData.value = true
    const res = await request.post('/modelTraining/trainData/import', {
      contractYear: selectedImportYear.value,
    })
    if (res.code === '200') {
      lastImportResult.value = res.data
      await loadTrainDataOverview()
      ElMessage.success('train_data 导入完成')
    } else {
      ElMessage.error(res.msg || '导入失败')
    }
  } catch (error) {
    console.error(error)
    ElMessage.error('train_data 导入失败')
  } finally {
    importingTrainData.value = false
  }
}

const handleStartTraining = async () => {
  const hiddenDims = parseHiddenDims(trainForm.hiddenDimsText)
  if (!hiddenDims) {
    ElMessage.warning('请输入合法的主干隐藏层配置，例如 256,512,512,256,256')
    return
  }
  if (!Number.isInteger(Number(trainForm.headHiddenDim)) || Number(trainForm.headHiddenDim) <= 0) {
    ElMessage.warning('分类头隐藏层必须是正整数')
    return
  }

  const payload = {
    numEpochs: Number(trainForm.numEpochs),
    batchSize: Number(trainForm.batchSize),
    optimizer: trainForm.optimizer,
    learningRate: Number(trainForm.learningRate),
    earlyStopMetric: trainForm.earlyStopMetric,
    thresholdMetric: trainForm.thresholdMetric,
    hiddenDims,
    headHiddenDim: Number(trainForm.headHiddenDim),
  }

  try {
    starting.value = true
    const res = await request.post('/modelTraining/start', payload)
    if (res.code === '200') {
      trackedJobId.value = res.data.jobId
      currentJob.value = res.data
      ElMessage.success('训练任务已启动')
      startPolling()
    } else {
      ElMessage.error(res.msg || '训练任务启动失败')
    }
  } catch (error) {
    console.error(error)
    ElMessage.error('训练任务启动失败，请检查后端训练服务')
  } finally {
    starting.value = false
  }
}

watch(
  () => currentJob.value?.status,
  async (status, previousStatus) => {
    if (
      previousStatus === 'running'
      && status === 'completed'
      && currentJob.value?.jobId
      && currentJob.value.jobId === trackedJobId.value
    ) {
      ElMessage.success('训练完成，正在打开结果页面')
      await openResultPage(currentJob.value.jobId)
      return
    }

    if (
      previousStatus === 'running'
      && status === 'failed'
      && currentJob.value?.jobId === trackedJobId.value
    ) {
      ElMessage.error('训练任务失败，请在当前页面查看报错信息')
    }
  }
)

onMounted(async () => {
  await loadLatestJob()
  await loadTrainDataOverview()
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
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.08), rgba(14, 165, 233, 0.18)), #fff;
}

.hero-title {
  font-size: 22px;
  font-weight: 700;
  color: #1d4ed8;
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

.section-title {
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
}

.train-form {
  margin-top: 14px;
}

.train-form :deep(.el-input-number),
.train-form :deep(.el-select) {
  width: 100%;
}

.group-title {
  margin: 8px 0 12px;
  padding-left: 10px;
  border-left: 4px solid #2563eb;
  font-size: 15px;
  font-weight: 600;
  color: #1e3a8a;
}

.train-actions {
  margin-top: 8px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
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

.dataset-summary {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.summary-item {
  padding: 16px 18px;
  border-radius: 16px;
  background: #f8fbff;
  border: 1px solid #dbeafe;
}

.summary-label {
  font-size: 13px;
  color: #64748b;
}

.summary-value {
  margin-top: 10px;
  font-size: 28px;
  font-weight: 700;
  color: #0f172a;
}

.skip-box {
  margin-top: 14px;
  padding: 12px 14px;
  border-radius: 12px;
  background: #f8fafc;
  color: #475569;
  line-height: 1.7;
  word-break: break-word;
}

@media (max-width: 900px) {
  .hero-card {
    flex-direction: column;
    align-items: flex-start;
  }

  .hero-meta {
    text-align: left;
    min-width: 0;
  }

  .dataset-summary {
    grid-template-columns: 1fr;
  }
}
</style>