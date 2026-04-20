<template>
  <div>
    <div class="card hero-card">
      <div>
        <div class="hero-title">模型训练中心</div>
      </div>
      <div class="hero-meta hero-status-row">
        <div v-if="currentJob" class="hero-job-id">任务 ID：{{ currentJob.jobId }}</div>
        <el-tag size="large" :type="statusTagType">{{ statusText }}</el-tag>
      </div>
    </div>

    <el-row :gutter="18">
      <el-col :xs="24" :lg="11">
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
                  <el-input-number
                    v-model="trainForm.batchSize"
                    :min="8"
                    :max="4096"
                    controls-position="right"
                    @change="handleBatchSizeChange"
                  />
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
                  <div class="hidden-dims-box">
                    <div
                      v-for="(_, index) in trainForm.hiddenDims"
                      :key="index"
                      class="hidden-dim-cell"
                    >
                      <el-input
                        v-model="trainForm.hiddenDims[index]"
                        :placeholder="`第${index + 1}层`"
                        inputmode="numeric"
                        maxlength="4"
                      />
                    </div>
                  </div>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="分类头隐藏层">
                  <el-input-number
                    v-model="trainForm.headHiddenDim"
                    :min="1"
                    :max="2048"
                    controls-position="right"
                    @change="handleHeadHiddenDimChange"
                  />
                </el-form-item>
              </el-col>
            </el-row>

            <div class="train-actions">
              <el-button type="primary" :loading="starting" :disabled="isRunning" @click="handleStartTraining">
                {{ isRunning ? '训练进行中' : '开始训练' }}
              </el-button>
              <el-button :disabled="isRunning" @click="resetTrainForm">恢复默认配置</el-button>
              <el-button plain @click="openSampleLibrary">训练样本库</el-button>
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

    <el-dialog
      v-model="sampleLibraryVisible"
      title="训练样本库"
      width="580px"
      destroy-on-close
    >
      <div class="dataset-summary dataset-summary--single">
        <div class="summary-item">
          <div class="summary-label">样本总数</div>
          <div class="summary-value">{{ trainDataOverview.totalCount || 0 }}</div>
        </div>
      </div>

      <el-form label-position="top" class="train-form compact-form">
        <el-form-item label="合同开始年份">
          <el-select v-model="selectedImportYear" clearable placeholder="全部年份" :loading="overviewLoading">
            <el-option v-for="year in availableYears" :key="year" :label="`${year}年`" :value="Number(year)" />
          </el-select>
        </el-form-item>
        <div class="train-actions">
          <el-button type="primary" :loading="importingTrainData" @click="handleImportTrainData()">导入到 train_data</el-button>
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
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/request'

const router = useRouter()
const PENDING_TRAINING_JOB_KEY = 'modelTrainingPendingJobId'

const defaultTrainForm = () => ({
  numEpochs: 80,
  batchSize: 256,
  optimizer: 'adamw',
  learningRate: 0.0002,
  earlyStopMetric: 'auc',
  thresholdMetric: 'precision',
  hiddenDims: [128, 256, 256, 128, 128],
  headHiddenDim: 32,
})

const trainForm = reactive(defaultTrainForm())
const currentJob = ref(null)
const starting = ref(false)
const trackedJobId = ref('')
const sampleLibraryVisible = ref(false)
let pollTimer = null

const getPendingTrainingJobId = () => {
  if (typeof window === 'undefined') return ''
  return window.sessionStorage.getItem(PENDING_TRAINING_JOB_KEY) || ''
}

const setPendingTrainingJobId = (jobId) => {
  if (typeof window === 'undefined' || !jobId) return
  window.sessionStorage.setItem(PENDING_TRAINING_JOB_KEY, jobId)
}

const clearPendingTrainingJobId = (jobId = '') => {
  if (typeof window === 'undefined') return
  const currentPendingJobId = getPendingTrainingJobId()
  if (!jobId || !currentPendingJobId || currentPendingJobId === jobId) {
    window.sessionStorage.removeItem(PENDING_TRAINING_JOB_KEY)
  }
}

const trainDataOverview = ref({
  totalCount: 0,
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

const applyExponentialInputStep = (field, value, oldValue, min, max) => {
  const currentValue = Number(value)
  const previousValue = Number(oldValue)
  if (!Number.isFinite(currentValue) || !Number.isFinite(previousValue)) return

  if (currentValue === previousValue + 1) {
    trainForm[field] = Math.min(max, previousValue * 2)
    return
  }

  if (currentValue === previousValue - 1) {
    trainForm[field] = Math.max(min, Math.floor(previousValue / 2))
  }
}

const handleBatchSizeChange = (value, oldValue) => {
  applyExponentialInputStep('batchSize', value, oldValue, 8, 4096)
}

const handleHeadHiddenDimChange = (value, oldValue) => {
  applyExponentialInputStep('headHiddenDim', value, oldValue, 1, 2048)
}

const collectHiddenDims = (values) => {
  if (!Array.isArray(values)) {
    return {
      valid: false,
      message: '请至少填写 1 层主干隐藏层',
      dims: [],
    }
  }

  const dims = []
  let encounteredEmpty = false

  for (const value of values) {
    if (value === undefined || value === null || value === '') {
      encounteredEmpty = true
      continue
    }

    const numericValue = Number(value)
    if (!Number.isInteger(numericValue) || numericValue <= 0) {
      return {
        valid: false,
        message: '主干隐藏层的每一层维数都必须是正整数',
        dims: [],
      }
    }

    if (encounteredEmpty) {
      return {
        valid: false,
        message: '主干隐藏层请按从左到右连续填写，中间不要留空',
        dims: [],
      }
    }

    dims.push(numericValue)
  }

  if (!dims.length) {
    return {
      valid: false,
      message: '请至少填写 1 层主干隐藏层',
      dims: [],
    }
  }

  return {
    valid: true,
    message: '',
    dims,
  }
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
  clearPendingTrainingJobId(jobId)
  await router.push({
    name: 'ModelTrainingResult',
    params: { jobId },
  })
}

const tryOpenCompletedPendingJob = async (job, { showMessage = false } = {}) => {
  if (!job?.jobId) return false
  const pendingJobId = getPendingTrainingJobId()
  if (!pendingJobId || job.jobId !== pendingJobId) return false

  if (job.status === 'completed') {
    if (showMessage) {
      ElMessage.success('训练完成，正在打开结果页面')
    }
    await openResultPage(job.jobId)
    return true
  }

  if (job.status === 'failed') {
    clearPendingTrainingJobId(job.jobId)
  }

  return false
}

const loadLatestJob = async ({ allowCompletedRedirect = false } = {}) => {
  const res = await request.get('/modelTraining/jobs/latest')
  if (res.code === '200' && res.data) {
    currentJob.value = res.data
    if (await tryOpenCompletedPendingJob(res.data, { showMessage: allowCompletedRedirect })) {
      return true
    }
    if (res.data.status === 'running') {
      trackedJobId.value = res.data.jobId
      setPendingTrainingJobId(res.data.jobId)
      startPolling()
    }
    return true
  }
  return false
}

const loadJob = async (jobId, { allowCompletedRedirect = false } = {}) => {
  if (!jobId) return false
  const res = await request.get(`/modelTraining/jobs/${jobId}`)
  if (res.code === '200') {
    currentJob.value = res.data
    if (await tryOpenCompletedPendingJob(res.data, { showMessage: allowCompletedRedirect })) {
      return true
    }
    if (res.data.status === 'running') {
      trackedJobId.value = res.data.jobId
      setPendingTrainingJobId(res.data.jobId)
    }
    return true
  }
  return false
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

const initializeTrainingPage = async () => {
  const pendingJobId = getPendingTrainingJobId()
  if (pendingJobId) {
    const restored = await loadJob(pendingJobId, { allowCompletedRedirect: true })
    if (restored) {
      return
    }
    clearPendingTrainingJobId(pendingJobId)
  }
  await loadLatestJob()
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

const openSampleLibrary = async () => {
  sampleLibraryVisible.value = true
  await loadTrainDataOverview()
}

const buildOverwriteMessage = (payload) => {
  const conflictCount = Number(payload?.conflictCount || 0)
  const sampleIds = Array.isArray(payload?.conflictIds) ? payload.conflictIds : []
  const sampleText = sampleIds.length ? `\n冲突ID示例：${sampleIds.join('、')}` : ''
  return `检测到 ${conflictCount} 个已存在的保单编号。继续后将覆盖 train_data 中这些保单编号对应的原有保单信息。是否继续？${sampleText}`
}

const handleImportTrainData = async (overwriteExisting = false) => {
  const resolvedOverwriteExisting = overwriteExisting === true

  try {
    importingTrainData.value = true
    const res = await request.post('/modelTraining/trainData/import', {
      contractYear: selectedImportYear.value,
      overwriteExisting: resolvedOverwriteExisting,
    })
    if (res.code === '200') {
      if (res.data?.requiresOverwriteConfirm) {
        try {
          await ElMessageBox.confirm(
            buildOverwriteMessage(res.data),
            '保单已存在',
            {
              confirmButtonText: '覆盖原有保单',
              cancelButtonText: '取消',
              type: 'warning',
            }
          )
        } catch (action) {
          if (action === 'cancel' || action === 'close') {
            ElMessage.info('已取消覆盖导入')
            return
          }
          throw action
        }

        await handleImportTrainData(true)
        return
      }

      lastImportResult.value = res.data
      await loadTrainDataOverview()
      ElMessage.success(resolvedOverwriteExisting ? 'train_data 覆盖更新完成' : 'train_data 导入完成')
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
  const hiddenDimsResult = collectHiddenDims(trainForm.hiddenDims)
  if (!hiddenDimsResult.valid) {
    ElMessage.warning(hiddenDimsResult.message)
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
    hiddenDims: hiddenDimsResult.dims,
    headHiddenDim: Number(trainForm.headHiddenDim),
  }

  try {
    starting.value = true
    const res = await request.post('/modelTraining/start', payload)
    if (res.code === '200') {
      trackedJobId.value = res.data.jobId
      setPendingTrainingJobId(res.data.jobId)
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
      clearPendingTrainingJobId(currentJob.value?.jobId)
      ElMessage.error('训练任务失败，请在当前页面查看报错信息')
    }
  }
)

onMounted(async () => {
  await initializeTrainingPage()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.hero-card {
  margin-bottom: 18px;
  padding: 16px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.08), rgba(14, 165, 233, 0.18)), #fff;
}

.hero-title {
  font-size: 20px;
  font-weight: 700;
  color: #1d4ed8;
}

.hero-meta {
  min-width: 260px;
}

.hero-status-row {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

.hero-job-id {
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

.hidden-dims-box {
  display: flex;
  width: fit-content;
  max-width: 100%;
  min-height: 42px;
  overflow: hidden;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: #fff;
}

.hidden-dim-cell {
  flex: 0 0 46px;
  min-width: 46px;
  border-right: 1px solid var(--el-border-color-light);
}

.hidden-dim-cell:last-child {
  border-right: none;
}

.hidden-dim-cell :deep(.el-input) {
  height: 100%;
}

.hidden-dim-cell :deep(.el-input__wrapper) {
  min-height: 42px;
  padding: 0 4px;
  border-radius: 0;
  box-shadow: none;
  background: transparent;
}

.hidden-dim-cell :deep(.el-input__inner) {
  font-size: 13px;
  text-align: center;
}

.hidden-dim-cell :deep(.el-input__wrapper.is-focus) {
  box-shadow: inset 0 0 0 1px #2563eb;
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
  margin-top: 2px;
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

.dataset-summary--single {
  grid-template-columns: 1fr;
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
    min-width: 0;
    width: 100%;
  }

  .hero-status-row {
    justify-content: flex-start;
  }

  .dataset-summary {
    grid-template-columns: 1fr;
  }

  .hidden-dims-box {
    width: 100%;
    flex-wrap: wrap;
  }

  .hidden-dim-cell {
    flex: 0 0 50%;
  }

  .hidden-dim-cell:nth-child(2n) {
    border-right: none;
  }

  .hidden-dim-cell:nth-child(-n + 3) {
    border-bottom: 1px solid var(--el-border-color-light);
  }

  .hidden-dim-cell:last-child {
    border-right: none;
  }
}
</style>
