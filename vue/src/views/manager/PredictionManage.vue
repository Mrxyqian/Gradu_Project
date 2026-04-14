<template>
  <div>
    <div class="card prediction-banner">
      <div>
        <div class="banner-title">理赔概率预测</div>
      </div>
      <div class="banner-actions">
        <el-button class="policy-predict-button" plain @click="existingPolicyDialogVisible = true">预测已有保单</el-button>
        <div class="version-picker">
          <span class="version-label">预测模型</span>
          <el-select
            v-model="selectedModelVersion"
            placeholder="请选择模型版本"
            filterable
            style="width: 340px"
            :loading="modelVersionLoading"
          >
            <el-option
              v-for="item in modelVersions"
              :key="item.modelVersion"
              :label="buildModelVersionLabel(item)"
              :value="item.modelVersion"
            />
          </el-select>
        </div>
      </div>
    </div>

    <el-row :gutter="18">
      <el-col :xs="24" :xl="15">
        <div class="card section-card">
          <div class="section-title">待预测信息</div>
          <el-form :model="predictForm" label-position="top" class="predict-form">
            <div class="group-title">保单信息</div>
            <el-row :gutter="12">
              <el-col :xs="24" :sm="12">
                <el-form-item label="合同开始日期">
                  <el-date-picker v-model="predictForm.dateStartContract" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :sm="12">
                <el-form-item label="最后续保日期">
                  <el-date-picker v-model="predictForm.dateLastRenewal" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :sm="12">
                <el-form-item label="下次续保日期">
                  <el-date-picker v-model="predictForm.dateNextRenewal" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :sm="12">
                <el-form-item label="出生日期">
                  <el-date-picker v-model="predictForm.dateBirth" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :sm="12">
                <el-form-item label="驾照签发日期">
                  <el-date-picker v-model="predictForm.dateDrivingLicence" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :sm="12">
                <el-form-item label="分销渠道">
                  <el-select v-model="predictForm.distributionChannel">
                    <el-option label="代理人" :value="0" />
                    <el-option label="保险经纪" :value="1" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :xs="24" :sm="12"><el-form-item label="合作年数"><el-input-number v-model="predictForm.seniority" :min="0" controls-position="right" /></el-form-item></el-col>
              <el-col :xs="24" :sm="12"><el-form-item label="当前生效保单数"><el-input-number v-model="predictForm.policiesInForce" :min="0" controls-position="right" /></el-form-item></el-col>
              <el-col :xs="24" :sm="12"><el-form-item label="历史最高保单数"><el-input-number v-model="predictForm.maxPolicies" :min="0" controls-position="right" /></el-form-item></el-col>
              <el-col :xs="24" :sm="12"><el-form-item label="历史最高产品数"><el-input-number v-model="predictForm.maxProducts" :min="0" controls-position="right" /></el-form-item></el-col>
              <el-col :xs="24" :sm="12"><el-form-item label="失效保单数"><el-input-number v-model="predictForm.lapse" :min="0" controls-position="right" /></el-form-item></el-col>
              <el-col :xs="24" :sm="12">
                <el-form-item label="缴费方式">
                  <el-select v-model="predictForm.payment">
                    <el-option label="年缴" :value="0" />
                    <el-option label="半年缴" :value="1" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :xs="24" :sm="12"><el-form-item label="净保费"><el-input-number v-model="predictForm.premium" :min="0" :step="100" :precision="2" controls-position="right" /></el-form-item></el-col>
            </el-row>

            <div class="group-title">理赔历史</div>
            <el-row :gutter="12">
              <el-col :xs="24" :sm="12"><el-form-item label="历史索赔次数"><el-input-number v-model="predictForm.nClaimsHistory" :min="0" controls-position="right" /></el-form-item></el-col>
              <el-col :xs="24" :sm="12"><el-form-item label="历史出险率"><el-input-number v-model="predictForm.rClaimsHistory" :min="0" :step="0.01" :precision="4" controls-position="right" /></el-form-item></el-col>
              <el-col :xs="24" :sm="12">
                <el-form-item label="风险类型">
                  <el-select v-model="predictForm.typeRisk">
                    <el-option label="摩托车" :value="1" />
                    <el-option label="货车" :value="2" />
                    <el-option label="乘用车" :value="3" />
                    <el-option label="农用车" :value="4" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :xs="24" :sm="12">
                <el-form-item label="地区">
                  <el-select v-model="predictForm.area">
                    <el-option label="农村" :value="0" />
                    <el-option label="城市" :value="1" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :xs="24" :sm="12">
                <el-form-item label="第二驾驶员">
                  <el-select v-model="predictForm.secondDriver">
                    <el-option label="否" :value="0" />
                    <el-option label="是" :value="1" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>

            <div class="group-title">车辆信息</div>
            <el-row :gutter="12">
              <el-col :xs="24" :sm="12"><el-form-item label="注册年份"><el-input-number v-model="predictForm.yearMatriculation" :min="1900" :max="2100" controls-position="right" /></el-form-item></el-col>
              <el-col :xs="24" :sm="12"><el-form-item label="马力"><el-input-number v-model="predictForm.power" :min="0" controls-position="right" /></el-form-item></el-col>
              <el-col :xs="24" :sm="12"><el-form-item label="排量"><el-input-number v-model="predictForm.cylinderCapacity" :min="0" controls-position="right" /></el-form-item></el-col>
              <el-col :xs="24" :sm="12"><el-form-item label="车辆价值"><el-input-number v-model="predictForm.valueVehicle" :min="0" :step="1000" :precision="2" controls-position="right" /></el-form-item></el-col>
              <el-col :xs="24" :sm="12"><el-form-item label="车门数"><el-input-number v-model="predictForm.nDoors" :min="0" controls-position="right" /></el-form-item></el-col>
              <el-col :xs="24" :sm="12">
                <el-form-item label="燃料类型">
                  <el-select v-model="predictForm.typeFuel">
                    <el-option label="汽油" value="P" />
                    <el-option label="柴油" value="D" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :xs="24" :sm="12"><el-form-item label="车长"><el-input-number v-model="predictForm.length" :min="0" :step="0.01" :precision="2" controls-position="right" /></el-form-item></el-col>
              <el-col :xs="24" :sm="12"><el-form-item label="车重"><el-input-number v-model="predictForm.weight" :min="0" controls-position="right" /></el-form-item></el-col>
            </el-row>

            <div class="form-actions">
              <el-button type="primary" :loading="predicting" @click="handlePredict">开始预测</el-button>
              <el-button @click="resetPredictForm">重置</el-button>
            </div>
          </el-form>
        </div>
      </el-col>

      <el-col :xs="24" :xl="9">
        <div class="card section-card history-card">
          <div class="section-title">历史预测记录</div>
          <el-table :data="historyTableData" style="width: 100%; margin-top: 12px">
            <el-table-column prop="predId" label="记录ID" width="88" />
            <el-table-column prop="id" label="保单编号" width="100" />
            <el-table-column prop="claimProbability" label="理赔概率" width="110">
              <template #default="scope">{{ formatPercent(scope.row.claimProbability) }}</template>
            </el-table-column>
            <el-table-column prop="claimFlag" label="预测标签" width="90">
              <template #default="scope">{{ Number(scope.row.claimFlag) === 1 ? '理赔' : '不理赔' }}</template>
            </el-table-column>
            <el-table-column prop="riskLevel" label="风险等级" width="100">
              <template #default="scope">
                <el-tag :type="getRiskLevelTag(scope.row.riskLevel)">{{ getRiskLevelText(scope.row.riskLevel) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="predictionTime" label="预测时间" min-width="160" />
            <el-table-column prop="modelVersion" label="模型版本" min-width="180" show-overflow-tooltip />
            <el-table-column prop="thresholdUsed" label="阈值" width="90" />
            <el-table-column label="操作" width="82" fixed="right">
              <template #default="scope">
                <el-button type="danger" plain size="small" @click="deleteHistory(scope.row.predId)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pager-wrap">
            <el-pagination
              v-model:current-page="historyPageNum"
              v-model:page-size="historyPageSize"
              :total="historyTotal"
              background
              layout="prev, pager, next"
              @current-change="loadHistoryPage"
            />
          </div>
        </div>
      </el-col>
    </el-row>

    <el-dialog v-model="resultDialogVisible" title="预测结果" width="520px" destroy-on-close>
      <div v-if="latestResult" class="result-grid">
        <div class="result-card blue-card">
          <div class="result-label">理赔概率</div>
          <div class="result-value">{{ formatPercent(latestResult.claimProbability) }}</div>
        </div>
        <div class="result-card orange-card">
          <div class="result-label">预测标签</div>
          <div class="result-value">{{ Number(latestResult.claimFlag) === 1 ? '理赔' : '不理赔' }}</div>
        </div>
        <div class="result-card green-card">
          <div class="result-label">风险等级</div>
          <div class="result-value">{{ getRiskLevelText(latestResult.riskLevel) }}</div>
        </div>
      </div>
      <el-descriptions v-if="latestResult" :column="1" border style="margin-top: 16px">
        <el-descriptions-item label="记录ID">{{ latestResult.predId }}</el-descriptions-item>
        <el-descriptions-item label="保单编号">{{ latestResult.id ?? 0 }}</el-descriptions-item>
        <el-descriptions-item label="模型版本">{{ latestResult.modelVersion || '-' }}</el-descriptions-item>
        <el-descriptions-item label="分类阈值">{{ latestResult.thresholdUsed ?? '-' }}</el-descriptions-item>
        <el-descriptions-item label="预测时间">{{ latestResult.predictionTime || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <el-dialog v-model="existingPolicyDialogVisible" title="预测已有保单" width="420px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="保单编号">
          <el-input-number v-model="existingPolicyId" :min="1" :step="1" controls-position="right" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="existingPolicyDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="predictingExistingPolicy" @click="handlePredictById">开始预测</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import request from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'

const defaultPredictForm = () => ({
  dateStartContract: '',
  dateLastRenewal: '',
  dateNextRenewal: '',
  distributionChannel: 0,
  dateBirth: '',
  dateDrivingLicence: '',
  seniority: null,
  policiesInForce: null,
  maxPolicies: null,
  maxProducts: null,
  lapse: null,
  payment: 0,
  premium: null,
  nClaimsHistory: null,
  rClaimsHistory: null,
  typeRisk: null,
  area: null,
  secondDriver: 0,
  yearMatriculation: null,
  power: null,
  cylinderCapacity: null,
  valueVehicle: null,
  nDoors: null,
  typeFuel: 'P',
  length: null,
  weight: null,
})

const predictForm = reactive(defaultPredictForm())
const predicting = ref(false)
const predictingExistingPolicy = ref(false)
const resultDialogVisible = ref(false)
const latestResult = ref(null)
const existingPolicyDialogVisible = ref(false)
const existingPolicyId = ref(null)

const historyTableData = ref([])
const historyPageNum = ref(1)
const historyPageSize = ref(10)
const historyTotal = ref(0)

const modelVersions = ref([])
const selectedModelVersion = ref('')
const defaultModelVersion = ref('')
const modelVersionLoading = ref(false)

const buildPayloadRecord = () => {
  const payload = {}
  Object.entries(predictForm).forEach(([key, value]) => {
    if (value !== '' && value !== null && value !== undefined) {
      payload[key] = value
    }
  })
  return payload
}

const resetPredictForm = () => {
  Object.assign(predictForm, defaultPredictForm())
}

const getRiskLevelText = (riskLevel) => {
  const map = { LOW: '低风险', MEDIUM: '中风险', HIGH: '高风险' }
  return map[riskLevel] || riskLevel
}

const getRiskLevelTag = (riskLevel) => {
  const map = { LOW: 'success', MEDIUM: 'warning', HIGH: 'danger' }
  return map[riskLevel] || 'info'
}

const formatPercent = (value) => `${(Number(value || 0) * 100).toFixed(2)}%`

const buildModelVersionLabel = (item) => {
  const tags = []
  if (item.savedAt) tags.push(String(item.savedAt).replace('T', ' '))
  if (item.checkpointType) tags.push(item.checkpointType)
  if (item.auc !== undefined && item.auc !== null) tags.push(`AUC ${Number(item.auc).toFixed(4)}`)
  return `${item.displayName || item.modelVersion}${tags.length ? `（${tags.join(' | ')}）` : ''}`
}

const loadHistoryPage = () => {
  request.get('/insurPred/selectPage', {
    params: {
      pageNum: historyPageNum.value,
      pageSize: historyPageSize.value,
    },
  }).then((res) => {
    historyTableData.value = res.data?.list || []
    historyTotal.value = res.data?.total || 0
  })
}

const loadModelVersions = async () => {
  try {
    modelVersionLoading.value = true
    const res = await request.get('/insurPred/modelVersions')
    const data = res.data || {}
    modelVersions.value = data.versions || []
    defaultModelVersion.value = data.defaultModelVersion || ''
    if (!selectedModelVersion.value || !modelVersions.value.some((item) => item.modelVersion === selectedModelVersion.value)) {
      selectedModelVersion.value = defaultModelVersion.value
    }
  } catch (error) {
    console.error(error)
    ElMessage.error('加载模型版本失败')
  } finally {
    modelVersionLoading.value = false
  }
}

const handlePredict = async () => {
  if (!selectedModelVersion.value) {
    ElMessage.warning('请先选择模型版本')
    return
  }

  try {
    predicting.value = true
    const res = await request.post('/insurPred/predict', {
      modelVersion: selectedModelVersion.value,
      record: buildPayloadRecord(),
    })
    if (res.code === '200') {
      latestResult.value = res.data || null
      resultDialogVisible.value = true
      ElMessage.success('预测完成并已保存历史记录')
      loadHistoryPage()
    } else {
      ElMessage.error(res.msg || '预测失败')
    }
  } catch (error) {
    console.error(error)
    ElMessage.error('预测请求失败，请检查后端服务')
  } finally {
    predicting.value = false
  }
}

const handlePredictById = async () => {
  if (!selectedModelVersion.value) {
    ElMessage.warning('请先选择模型版本')
    return
  }
  if (!existingPolicyId.value || Number(existingPolicyId.value) <= 0) {
    ElMessage.warning('请输入有效的保单编号')
    return
  }

  try {
    predictingExistingPolicy.value = true
    const res = await request.post('/insurPred/predictById', {
      id: Number(existingPolicyId.value),
      modelVersion: selectedModelVersion.value,
    })
    if (res.code === '200') {
      latestResult.value = res.data || null
      existingPolicyDialogVisible.value = false
      existingPolicyId.value = null
      resultDialogVisible.value = true
      ElMessage.success('已有保单预测完成并已保存历史记录')
      loadHistoryPage()
    } else {
      ElMessage.error(res.msg || '预测失败')
    }
  } catch (error) {
    console.error(error)
    ElMessage.error(error?.response?.data?.msg || error?.response?.data?.message || '按保单编号预测失败')
  } finally {
    predictingExistingPolicy.value = false
  }
}

const deleteHistory = async (predId) => {
  try {
    await ElMessageBox.confirm('删除后无法恢复，确认删除该预测记录吗？', '删除确认', { type: 'warning' })
    const res = await request.delete(`/insurPred/delete/${predId}`)
    if (res.code === '200') {
      ElMessage.success('删除成功')
      loadHistoryPage()
    } else {
      ElMessage.error(res.msg || '删除失败')
    }
  } catch (error) {}
}

onMounted(() => {
  loadHistoryPage()
  loadModelVersions()
})
</script>

<style scoped>
.prediction-banner {
  margin-bottom: 16px;
  padding: 18px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.08), rgba(14, 165, 233, 0.16)), #fff;
}

.banner-title {
  font-size: 22px;
  font-weight: 700;
  color: #1d4ed8;
}

.banner-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.policy-predict-button {
  border-radius: 999px;
  padding-inline: 18px;
}

.version-picker {
  display: flex;
  align-items: center;
  gap: 10px;
}

.version-label {
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

.predict-form {
  margin-top: 14px;
}

.predict-form :deep(.el-input-number),
.predict-form :deep(.el-select) {
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

.form-actions {
  margin-top: 8px;
  display: flex;
  gap: 12px;
}

.history-card {
  min-height: 100%;
}

.pager-wrap {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.result-card {
  border-radius: 16px;
  padding: 18px;
  color: #fff;
}

.blue-card {
  background: linear-gradient(135deg, #2563eb, #0ea5e9);
}

.orange-card {
  background: linear-gradient(135deg, #f97316, #fb7185);
}

.green-card {
  background: linear-gradient(135deg, #059669, #22c55e);
}

.result-label {
  font-size: 13px;
  opacity: 0.92;
}

.result-value {
  margin-top: 10px;
  font-size: 26px;
  font-weight: 700;
}

@media (max-width: 1280px) {
  .result-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .prediction-banner {
    flex-direction: column;
    align-items: flex-start;
  }

  .version-picker {
    width: 100%;
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>