<template>
  <div>
    <div class="card train-hero">
      <div>
        <div class="hero-title">模型训练中心</div>
        <div class="hero-desc">
          管理员可直接配置训练超参数、实时查看按 epoch 刷新的训练进度，并在训练完成后查看结果概览与保存权重文件。
        </div>
      </div>
      <div class="hero-status">
        <el-tag size="large" :type="statusTagType">{{ statusText }}</el-tag>
        <div class="hero-job-id" v-if="currentJob">任务ID：{{ currentJob.jobId }}</div>
      </div>
    </div>

    <el-row :gutter="20">
      <el-col :xs="24" :lg="11">
        <div class="card section-card">
          <div class="section-title">训练超参数</div>
          <div class="section-subtitle">当前表单会映射到你现有的 MLP 训练方式，并复用现有数据集与训练逻辑。</div>

          <el-form :model="trainForm" label-position="top" class="train-form">
            <div class="group-title">数据与训练</div>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="训练轮数">
                  <el-input-number v-model="trainForm.numEpochs" :min="1" :max="500" controls-position="right" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="批大小">
                  <el-input-number v-model="trainForm.batchSize" :min="8" :max="4096" controls-position="right" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="验证集比例">
                  <el-input-number v-model="trainForm.valRatio" :min="0.05" :max="0.45" :step="0.01" controls-position="right" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="测试集比例">
                  <el-input-number v-model="trainForm.testRatio" :min="0.05" :max="0.45" :step="0.01" controls-position="right" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="随机种子">
                  <el-input-number v-model="trainForm.randomSeed" :min="0" :max="999999" controls-position="right" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="并行线程数">
                  <el-input-number v-model="trainForm.numWorkers" :min="0" :max="8" controls-position="right" />
                </el-form-item>
              </el-col>
            </el-row>

            <div class="group-title">优化器与调度</div>
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
                <el-form-item label="权重衰减">
                  <el-input-number v-model="trainForm.weightDecay" :min="0" :max="1" :step="0.00001" :precision="6" controls-position="right" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="调度器">
                  <el-select v-model="trainForm.scheduler">
                    <el-option label="Cosine Warmup" value="cosine_warmup" />
                    <el-option label="Reduce On Plateau" value="reduce_on_plateau" />
                    <el-option label="StepLR" value="step" />
                    <el-option label="不使用调度器" value="none" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="Warmup Epochs">
                  <el-input-number v-model="trainForm.warmupEpochs" :min="0" :max="100" controls-position="right" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="最小学习率">
                  <el-input-number v-model="trainForm.minLr" :min="0" :max="1" :step="0.000001" :precision="6" controls-position="right" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="Step Size">
                  <el-input-number v-model="trainForm.stepSize" :min="1" :max="200" controls-position="right" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="Gamma">
                  <el-input-number v-model="trainForm.gamma" :min="0.01" :max="1" :step="0.05" :precision="2" controls-position="right" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="Plateau Factor">
                  <el-input-number v-model="trainForm.plateauFactor" :min="0.1" :max="0.95" :step="0.05" :precision="2" controls-position="right" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="Plateau Patience">
                  <el-input-number v-model="trainForm.plateauPatience" :min="1" :max="100" controls-position="right" />
                </el-form-item>
              </el-col>
            </el-row>

            <div class="group-title">模型与损失</div>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="主干 Dropout">
                  <el-input-number v-model="trainForm.backboneDropout" :min="0" :max="0.9" :step="0.05" :precision="2" controls-position="right" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="任务头 Dropout">
                  <el-input-number v-model="trainForm.headDropout" :min="0" :max="0.9" :step="0.05" :precision="2" controls-position="right" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="正样本权重">
                  <el-input-number v-model="trainForm.posWeight" :min="0.1" :max="100" :step="0.1" :precision="2" controls-position="right" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="梯度裁剪">
                  <el-input-number v-model="trainForm.gradClip" :min="0" :max="100" :step="0.1" :precision="2" controls-position="right" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="分类 log_var 初值">
                  <el-input-number v-model="trainForm.initLogVarClf" :min="-10" :max="10" :step="0.1" :precision="1" controls-position="right" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="回归 log_var 初值">
                  <el-input-number v-model="trainForm.initLogVarReg" :min="-10" :max="10" :step="0.1" :precision="1" controls-position="right" />
                </el-form-item>
              </el-col>
            </el-row>

            <div class="group-title">训练策略</div>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="启用 Early Stopping">
                  <el-switch v-model="trainForm.earlyStop" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="启用 AMP">
                  <el-switch v-model="trainForm.useAmp" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="保存每个 Epoch">
                  <el-switch v-model="trainForm.saveEveryEpoch" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="自动搜索阈值">
                  <el-switch v-model="trainForm.autoThreshold" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="Early Stop Patience">
                  <el-input-number v-model="trainForm.patience" :min="1" :max="200" controls-position="right" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="最小改善阈值">
                  <el-input-number v-model="trainForm.minDelta" :min="0" :max="1" :step="0.0001" :precision="4" controls-position="right" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="监控指标">
                  <el-select v-model="trainForm.earlyStopMetric">
                    <el-option label="AUC" value="auc" />
                    <el-option label="Loss" value="loss" />
                    <el-option label="分类 Loss" value="clf_loss" />
                    <el-option label="Accuracy" value="accuracy" />
                    <el-option label="F1" value="f1" />
                    <el-option label="Precision" value="precision" />
                    <el-option label="Recall" value="recall" />
                    <el-option label="RMSE" value="rmse" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="固定分类阈值">
                  <el-input-number v-model="trainForm.clfThreshold" :min="0.05" :max="0.95" :step="0.01" :precision="2" controls-position="right" />
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
              <el-col :span="12">
                <el-form-item label="Threshold Beta">
                  <el-input-number v-model="trainForm.thresholdBeta" :min="0.1" :max="5" :step="0.1" :precision="1" controls-position="right" />
                </el-form-item>
              </el-col>
            </el-row>

            <div class="train-actions">
              <el-button type="primary" :loading="starting" :disabled="isRunning" @click="handleStartTraining">
                {{ isRunning ? '训练进行中' : '开始训练' }}
              </el-button>
              <el-button @click="resetTrainForm" :disabled="isRunning">恢复默认配置</el-button>
              <span class="form-tip">训练过程会按 epoch 轮询刷新，且仅管理员可操作。</span>
            </div>
          </el-form>
        </div>

        <div class="card section-card">
          <div class="section-title">权重保存</div>
          <div class="section-subtitle">训练完成后可选择保存本次训练的 `best` 或 `last` 权重文件，并写入本地输出目录。</div>

          <el-form :model="saveForm" label-position="top">
            <el-row :gutter="12">
              <el-col :span="10">
                <el-form-item label="权重类型">
                  <el-select v-model="saveForm.checkpointType" :disabled="!isCompleted">
                    <el-option label="best" value="best" />
                    <el-option label="last" value="last" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="14">
                <el-form-item label="目标文件名">
                  <el-input v-model="saveForm.fileName" :disabled="!isCompleted" placeholder="例如 claim-training-best.pth" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-button type="success" :loading="savingWeights" :disabled="!isCompleted" @click="handleSaveWeights">
              保存权重文件
            </el-button>
          </el-form>

          <div v-if="savedWeights.length" class="saved-list">
            <div class="saved-title">已保存的权重文件</div>
            <div v-for="item in savedWeights" :key="`${item.filePath}-${item.savedAt}`" class="saved-item">
              <div>{{ item.fileName }}（{{ item.checkpointType }}）</div>
              <div class="saved-path">{{ item.filePath }}</div>
              <div class="saved-time">{{ item.savedAt }}</div>
            </div>
          </div>
        </div>
      </el-col>

      <el-col :xs="24" :lg="13">
        <div class="card section-card">
          <div class="section-title">训练进度</div>
          <div class="status-row">
            <div class="status-inline">
              <el-tag :type="statusTagType">{{ statusText }}</el-tag>
              <span v-if="currentJob" class="status-hint">任务已完成 {{ currentEpoch }} / {{ totalEpochs }} 个 epoch</span>
            </div>
            <div v-if="currentJob?.createdAt" class="status-time">创建时间：{{ currentJob.createdAt }}</div>
          </div>

          <el-progress :percentage="progressPercent" :status="progressBarStatus" :stroke-width="16" />

          <el-alert
            v-if="currentJob?.error"
            :title="currentJob.error"
            type="error"
            show-icon
            :closable="false"
            style="margin-top: 16px"
          />

          <el-descriptions v-if="currentJob" :column="2" border style="margin-top: 16px">
            <el-descriptions-item label="当前任务">{{ currentJob.jobId }}</el-descriptions-item>
            <el-descriptions-item label="当前阶段">{{ currentJob.message || '-' }}</el-descriptions-item>
            <el-descriptions-item label="开始时间">{{ currentJob.startedAt || '-' }}</el-descriptions-item>
            <el-descriptions-item label="结束时间">{{ currentJob.finishedAt || '-' }}</el-descriptions-item>
            <el-descriptions-item label="当前 Epoch">{{ latestEpoch?.epoch || currentEpoch || 0 }}</el-descriptions-item>
            <el-descriptions-item label="最新学习率">{{ formatScientific(latestEpoch?.learningRate) }}</el-descriptions-item>
            <el-descriptions-item label="最新训练损失">{{ formatMetric(latestEpoch?.trainLoss) }}</el-descriptions-item>
            <el-descriptions-item label="最新验证损失">{{ formatMetric(latestEpoch?.valLoss) }}</el-descriptions-item>
            <el-descriptions-item label="最新验证 AUC">{{ formatMetric(latestEpoch?.valAuc) }}</el-descriptions-item>
            <el-descriptions-item label="最新验证 Accuracy">{{ formatPercent(latestEpoch?.valAccuracy) }}</el-descriptions-item>
            <el-descriptions-item label="最新验证 F1">{{ formatMetric(latestEpoch?.valF1) }}</el-descriptions-item>
            <el-descriptions-item label="最新验证 RMSE">{{ formatMetric(latestEpoch?.valRmse, 4) }}</el-descriptions-item>
          </el-descriptions>

          <el-empty v-else description="暂无训练任务，管理员可在左侧直接发起训练。" />
        </div>

        <div v-if="summary" class="card section-card">
          <div class="section-title">结果概览</div>

          <div class="summary-grid">
            <div class="summary-card blue-card">
              <div class="summary-label">测试 AUC</div>
              <div class="summary-value">{{ formatMetric(summary.finalMetrics?.auc) }}</div>
            </div>
            <div class="summary-card green-card">
              <div class="summary-label">测试 Accuracy</div>
              <div class="summary-value">{{ formatPercent(summary.finalMetrics?.accuracy) }}</div>
            </div>
            <div class="summary-card orange-card">
              <div class="summary-label">测试 F1</div>
              <div class="summary-value">{{ formatMetric(summary.finalMetrics?.f1) }}</div>
            </div>
            <div class="summary-card rose-card">
              <div class="summary-label">测试 RMSE</div>
              <div class="summary-value">{{ formatMetric(summary.finalMetrics?.rmse, 4) }}</div>
            </div>
          </div>

          <el-descriptions :column="2" border style="margin-top: 16px">
            <el-descriptions-item label="完成 Epoch">{{ summary.epochsCompleted }} / {{ summary.configuredEpochs }}</el-descriptions-item>
            <el-descriptions-item label="是否提前停止">{{ summary.stoppedEarly ? '是' : '否' }}</el-descriptions-item>
            <el-descriptions-item label="最佳监控指标">{{ summary.monitorMetric }}</el-descriptions-item>
            <el-descriptions-item label="最佳监控值">{{ formatMetric(summary.bestMonitorValue) }}</el-descriptions-item>
            <el-descriptions-item label="最终分类阈值">{{ formatMetric(summary.finalThreshold) }}</el-descriptions-item>
            <el-descriptions-item label="Precision / Recall">
              {{ formatMetric(summary.finalMetrics?.precision) }} / {{ formatMetric(summary.finalMetrics?.recall) }}
            </el-descriptions-item>
            <el-descriptions-item label="输出目录" :span="2">{{ artifacts?.outputDir || '-' }}</el-descriptions-item>
            <el-descriptions-item label="最佳权重路径" :span="2">{{ artifacts?.bestModelPath || '-' }}</el-descriptions-item>
            <el-descriptions-item label="最新权重路径" :span="2">{{ artifacts?.lastModelPath || '-' }}</el-descriptions-item>
          </el-descriptions>

          <el-collapse style="margin-top: 16px">
            <el-collapse-item title="查看详细分类报告" name="report">
              <pre class="report-box">{{ summary.classificationReport }}</pre>
            </el-collapse-item>
          </el-collapse>
        </div>
      </el-col>
    </el-row>

    <div v-if="hasHistory" class="chart-grid">
      <div class="card chart-card">
        <div class="chart-title">训练损失曲线</div>
        <div ref="trainLossRef" class="chart-body"></div>
      </div>
      <div class="card chart-card">
        <div class="chart-title">验证损失曲线</div>
        <div ref="valLossRef" class="chart-body"></div>
      </div>
      <div class="card chart-card">
        <div class="chart-title">验证 AUC 曲线</div>
        <div ref="valAucRef" class="chart-body"></div>
      </div>
      <div class="card chart-card">
        <div class="chart-title">验证 Accuracy 曲线</div>
        <div ref="valAccuracyRef" class="chart-body"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const defaultTrainForm = () => ({
  numEpochs: 40,
  batchSize: 128,
  randomSeed: 42,
  valRatio: 0.15,
  testRatio: 0.10,
  numWorkers: 0,
  optimizer: 'adamw',
  learningRate: 0.0002,
  weightDecay: 0.00007,
  scheduler: 'cosine_warmup',
  warmupEpochs: 5,
  minLr: 0.000001,
  stepSize: 10,
  gamma: 0.5,
  plateauFactor: 0.5,
  plateauPatience: 5,
  plateauMinLr: 0.000001,
  backboneDropout: 0.25,
  headDropout: 0.10,
  posWeight: 4.15,
  initLogVarClf: -0.5,
  initLogVarReg: 0.5,
  earlyStop: true,
  patience: 20,
  minDelta: 0.0001,
  earlyStopMetric: 'auc',
  useAmp: true,
  gradClip: 1.0,
  saveEveryEpoch: false,
  autoThreshold: true,
  clfThreshold: 0.5,
  thresholdMetric: 'f1',
  thresholdBeta: 1.3,
})

const trainForm = reactive(defaultTrainForm())
const saveForm = reactive({
  checkpointType: 'best',
  fileName: '',
})

const currentJob = ref(null)
const starting = ref(false)
const savingWeights = ref(false)

const trainLossRef = ref(null)
const valLossRef = ref(null)
const valAucRef = ref(null)
const valAccuracyRef = ref(null)

let trainLossChart = null
let valLossChart = null
let valAucChart = null
let valAccuracyChart = null
let pollTimer = null

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
const isCompleted = computed(() => currentJob.value?.status === 'completed')
const currentEpoch = computed(() => Number(currentJob.value?.currentEpoch || 0))
const totalEpochs = computed(() => Number(currentJob.value?.totalEpochs || 0))
const latestEpoch = computed(() => currentJob.value?.latestEpoch || null)
const summary = computed(() => currentJob.value?.summary || null)
const artifacts = computed(() => currentJob.value?.artifacts || null)
const savedWeights = computed(() => currentJob.value?.savedWeights || [])
const history = computed(() => currentJob.value?.history || {})
const hasHistory = computed(() => (history.value?.epochs || []).length > 0)
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

const loadLatestJob = async () => {
  const res = await request.get('/modelTraining/jobs/latest')
  if (res.code === '200' && res.data) {
    currentJob.value = res.data
    if (!saveForm.fileName) {
      saveForm.fileName = `claim-training-${res.data.jobId}.pth`
    }
    if (res.data.status === 'running') {
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

const handleStartTraining = async () => {
  if (Number(trainForm.valRatio) + Number(trainForm.testRatio) >= 0.8) {
    ElMessage.warning('验证集与测试集比例之和必须小于 0.8')
    return
  }

  try {
    starting.value = true
    const res = await request.post('/modelTraining/start', trainForm)
    if (res.code === '200') {
      currentJob.value = res.data
      saveForm.fileName = `claim-training-${res.data.jobId}.pth`
      ElMessage.success('训练任务已启动')
      startPolling()
    } else {
      ElMessage.error(res.msg || '训练任务启动失败')
    }
  } catch (error) {
    console.error(error)
    ElMessage.error('训练任务启动失败，请检查后端训练服务是否正常')
  } finally {
    starting.value = false
  }
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
    if (res.code === '200') {
      ElMessage.success('权重文件保存成功')
      await loadJob(currentJob.value.jobId)
    } else {
      ElMessage.error(res.msg || '保存权重失败')
    }
  } catch (error) {
    console.error(error)
    ElMessage.error('保存权重失败，请稍后重试')
  } finally {
    savingWeights.value = false
  }
}

const buildLineOption = (title, xData, yData, color, formatter) => ({
  tooltip: {
    trigger: 'axis',
    valueFormatter: formatter,
  },
  xAxis: {
    type: 'category',
    data: xData,
    boundaryGap: false,
    axisLabel: {
      color: '#4b5563',
    },
  },
  yAxis: {
    type: 'value',
    axisLabel: {
      color: '#4b5563',
    },
    splitLine: {
      lineStyle: {
        color: '#eef2f7',
      },
    },
  },
  grid: {
    left: 48,
    right: 18,
    top: 20,
    bottom: 36,
  },
  series: [{
    name: title,
    type: 'line',
    smooth: true,
    symbol: 'circle',
    symbolSize: 8,
    data: yData,
    lineStyle: {
      width: 3,
      color,
    },
    itemStyle: {
      color,
    },
    areaStyle: {
      color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: `${color}55` },
        { offset: 1, color: `${color}08` },
      ]),
    },
  }],
})

const renderCharts = () => {
  const epochs = history.value?.epochs || []
  if (!epochs.length) return

  trainLossChart?.dispose()
  valLossChart?.dispose()
  valAucChart?.dispose()
  valAccuracyChart?.dispose()

  if (trainLossRef.value) {
    trainLossChart = echarts.init(trainLossRef.value)
    trainLossChart.setOption(buildLineOption('训练损失', epochs, history.value.trainLoss || [], '#2563eb'))
  }
  if (valLossRef.value) {
    valLossChart = echarts.init(valLossRef.value)
    valLossChart.setOption(buildLineOption('验证损失', epochs, history.value.valLoss || [], '#0f766e'))
  }
  if (valAucRef.value) {
    valAucChart = echarts.init(valAucRef.value)
    valAucChart.setOption(buildLineOption('验证AUC', epochs, history.value.valAuc || [], '#f97316'))
  }
  if (valAccuracyRef.value) {
    valAccuracyChart = echarts.init(valAccuracyRef.value)
    valAccuracyChart.setOption(buildLineOption(
      '验证Accuracy',
      epochs,
      (history.value.valAccuracy || []).map(item => Number((Number(item) * 100).toFixed(2))),
      '#db2777',
      value => `${Number(value || 0).toFixed(2)}%`
    ))
  }
}

const handleResize = () => {
  trainLossChart?.resize()
  valLossChart?.resize()
  valAucChart?.resize()
  valAccuracyChart?.resize()
}

watch(
  () => currentJob.value?.history,
  () => {
    nextTick(() => {
      renderCharts()
    })
  },
  { deep: true }
)

onMounted(async () => {
  await loadLatestJob()
  nextTick(() => {
    renderCharts()
  })
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  stopPolling()
  window.removeEventListener('resize', handleResize)
  trainLossChart?.dispose()
  valLossChart?.dispose()
  valAucChart?.dispose()
  valAccuracyChart?.dispose()
})
</script>

<style scoped>
.train-hero {
  margin-bottom: 18px;
  padding: 22px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background:
    linear-gradient(135deg, rgba(37, 99, 235, 0.08), rgba(14, 165, 233, 0.18)),
    #fff;
}

.hero-title {
  font-size: 22px;
  font-weight: bold;
  color: #1d4ed8;
}

.hero-desc {
  margin-top: 8px;
  color: #475569;
  line-height: 1.8;
}

.hero-status {
  min-width: 200px;
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
  font-weight: bold;
  color: #1f2937;
}

.section-subtitle {
  margin-top: 6px;
  color: #6b7280;
  font-size: 13px;
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

.form-tip {
  color: #64748b;
  font-size: 13px;
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

.summary-grid {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.summary-card {
  border-radius: 16px;
  padding: 18px;
  color: #fff;
}

.blue-card {
  background: linear-gradient(135deg, #2563eb, #0ea5e9);
}

.green-card {
  background: linear-gradient(135deg, #059669, #22c55e);
}

.orange-card {
  background: linear-gradient(135deg, #f97316, #fb7185);
}

.rose-card {
  background: linear-gradient(135deg, #db2777, #f43f5e);
}

.summary-label {
  font-size: 13px;
  opacity: 0.9;
}

.summary-value {
  margin-top: 10px;
  font-size: 28px;
  font-weight: bold;
}

.report-box {
  margin: 0;
  padding: 12px;
  border-radius: 12px;
  background: #0f172a;
  color: #e2e8f0;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.7;
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

.chart-grid {
  margin-top: 2px;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 18px;
}

.chart-card {
  min-height: 350px;
}

.chart-title {
  font-size: 17px;
  font-weight: bold;
  color: #1f2937;
  margin-bottom: 10px;
}

.chart-body {
  height: 280px;
}

@media (max-width: 1200px) {
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 900px) {
  .train-hero {
    flex-direction: column;
    align-items: flex-start;
  }

  .hero-status {
    text-align: left;
    min-width: 0;
  }

  .chart-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
