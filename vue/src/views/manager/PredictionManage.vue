<template>
  <div>
    <div class="card prediction-banner">
      <div>
        <div class="banner-title">理赔率预测管理</div>
        <div class="banner-desc">从保单库中勾选 1 到 10 条记录执行预测，系统会自动保存预测历史。</div>
      </div>
      <div class="banner-actions">
        <div class="pick-count">已选 {{ selectedIds.length }} / 10 条</div>
        <el-button @click="clearSelection" :disabled="selectedIds.length === 0">清空选择</el-button>
        <el-button type="primary" @click="handlePredict" :disabled="selectedIds.length === 0">开始预测</el-button>
      </div>
    </div>

    <div class="card" style="margin-bottom: 12px;">
      <div class="section-title">可选保单列表</div>
      <div class="section-subtitle">允许跨页勾选，超出 10 条后将禁止继续选择。</div>
      <el-table
          ref="policyTableRef"
          :data="policyTableData"
          row-key="id"
          @selection-change="handleSelectionChange"
          style="width: 100%; margin-top: 12px;"
      >
        <el-table-column type="selection" width="55" :selectable="isSelectable" reserve-selection />
        <el-table-column prop="id" label="保单ID" width="100" />
        <el-table-column prop="typeRisk" label="风险类型" width="110">
          <template #default="scope">
            {{ getRiskTypeText(scope.row.typeRisk) }}
          </template>
        </el-table-column>
        <el-table-column prop="area" label="地区" width="90">
          <template #default="scope">
            {{ scope.row.area === 0 ? '农村' : '城市' }}
          </template>
        </el-table-column>
        <el-table-column prop="premium" label="净保费" width="120" />
        <el-table-column prop="nClaimsHistory" label="历史索赔次数" width="130" />
        <el-table-column prop="rClaimsHistory" label="历史索赔频率比" width="140" />
        <el-table-column prop="yearMatriculation" label="注册年份" width="110" />
        <el-table-column prop="typeFuel" label="燃料类型" width="100">
          <template #default="scope">
            {{ scope.row.typeFuel === 'P' ? '汽油' : '柴油' }}
          </template>
        </el-table-column>
        <el-table-column prop="dateStartContract" label="合同开始日期" min-width="130" />
      </el-table>
      <div style="margin-top: 12px; display: flex; justify-content: flex-end;">
        <el-pagination
            v-model:current-page="policyPageNum"
            v-model:page-size="policyPageSize"
            :total="policyTotal"
            background
            layout="prev, pager, next"
            @current-change="loadPolicyPage"
        />
      </div>
    </div>

    <div class="card" style="margin-bottom: 12px;">
      <div class="section-title">历史预测记录</div>
      <div class="section-subtitle">支持按预测记录主键删除，不能手工新增或修改。</div>
      <el-table :data="historyTableData" style="width: 100%; margin-top: 12px;">
        <el-table-column prop="predId" label="记录ID" width="100" />
        <el-table-column prop="id" label="保单ID" width="100" />
        <el-table-column prop="claimProbability" label="理赔概率" width="140">
          <template #default="scope">
            {{ formatPercent(scope.row.claimProbability) }}
          </template>
        </el-table-column>
        <el-table-column prop="riskLevel" label="风险等级" width="120">
          <template #default="scope">
            <el-tag :type="getRiskLevelTag(scope.row.riskLevel)">{{ getRiskLevelText(scope.row.riskLevel) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="expectedClaimAmount" label="预计理赔金额" width="150">
          <template #default="scope">
            ¥{{ formatMoney(scope.row.expectedClaimAmount) }}
          </template>
        </el-table-column>
        <el-table-column prop="predictionTime" label="预测时间" width="180" />
        <el-table-column prop="modelVersion" label="模型版本" min-width="190" show-overflow-tooltip />
        <el-table-column prop="thresholdUsed" label="阈值" width="110" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="scope">
            <el-button type="danger" plain size="small" @click="deleteHistory(scope.row.predId)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top: 12px; display: flex; justify-content: flex-end;">
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

    <el-dialog v-model="resultDialogVisible" title="本次预测结果" width="72%" destroy-on-close>
      <div class="result-grid">
        <div class="result-card result-blue">
          <div class="result-label">本次预测条数</div>
          <div class="result-value">{{ latestResults.length }}</div>
        </div>
        <div class="result-card result-orange">
          <div class="result-label">平均理赔概率</div>
          <div class="result-value">{{ latestAverageProbability }}</div>
        </div>
        <div class="result-card result-green">
          <div class="result-label">平均预计金额</div>
          <div class="result-value">¥{{ latestAverageAmount }}</div>
        </div>
      </div>

      <el-table :data="latestResults" style="width: 100%; margin-top: 16px;">
        <el-table-column prop="predId" label="记录ID" width="100" />
        <el-table-column prop="id" label="保单ID" width="100" />
        <el-table-column prop="claimProbability" label="理赔概率" width="140">
          <template #default="scope">
            {{ formatPercent(scope.row.claimProbability) }}
          </template>
        </el-table-column>
        <el-table-column prop="riskLevel" label="风险等级" width="120">
          <template #default="scope">
            <el-tag :type="getRiskLevelTag(scope.row.riskLevel)">{{ getRiskLevelText(scope.row.riskLevel) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="expectedClaimAmount" label="预计理赔金额" width="150">
          <template #default="scope">
            ¥{{ formatMoney(scope.row.expectedClaimAmount) }}
          </template>
        </el-table-column>
        <el-table-column prop="predictionTime" label="预测时间" width="180" />
        <el-table-column prop="modelVersion" label="模型版本" min-width="190" show-overflow-tooltip />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, reactive, ref } from "vue";
import request from "@/utils/request";
import { ElMessage, ElMessageBox } from "element-plus";

const policyTableRef = ref()

const policyTableData = ref([])
const policyPageNum = ref(1)
const policyPageSize = ref(10)
const policyTotal = ref(0)

const historyTableData = ref([])
const historyPageNum = ref(1)
const historyPageSize = ref(10)
const historyTotal = ref(0)

const selectedRowMap = reactive({})
const resultDialogVisible = ref(false)
const latestResults = ref([])

const selectedIds = computed(() => Object.keys(selectedRowMap).map(id => Number(id)))

const latestAverageProbability = computed(() => {
  if (!latestResults.value.length) return '0.00%'
  const avg = latestResults.value.reduce((sum, item) => sum + Number(item.claimProbability || 0), 0) / latestResults.value.length
  return formatPercent(avg)
})

const latestAverageAmount = computed(() => {
  if (!latestResults.value.length) return '0.00'
  const avg = latestResults.value.reduce((sum, item) => sum + Number(item.expectedClaimAmount || 0), 0) / latestResults.value.length
  return formatMoney(avg)
})

const getRiskTypeText = (type) => {
  const map = { 1: '摩托车', 2: '货车', 3: '乘用车', 4: '农用车' }
  return map[type] || type
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

const formatMoney = (value) => Number(value || 0).toFixed(2)

const isSelectable = (row) => {
  return selectedRowMap[row.id] || selectedIds.value.length < 10
}

const syncCurrentPageSelection = () => {
  nextTick(() => {
    if (!policyTableRef.value) return
    policyTableData.value.forEach(row => {
      policyTableRef.value.toggleRowSelection(row, !!selectedRowMap[row.id])
    })
    if (selectedIds.value.length >= 10) {
      ElMessage.warning('最多只能选择 10 条保单进行预测')
    }
  })
}

const loadPolicyPage = () => {
  request.get('/motorInsurance/selectPage', {
    params: {
      pageNum: policyPageNum.value,
      pageSize: policyPageSize.value,
    }
  }).then(res => {
    policyTableData.value = res.data?.list || []
    policyTotal.value = res.data?.total || 0
    syncCurrentPageSelection()
  })
}

const loadHistoryPage = () => {
  request.get('/insurPred/selectPage', {
    params: {
      pageNum: historyPageNum.value,
      pageSize: historyPageSize.value,
    }
  }).then(res => {
    historyTableData.value = res.data?.list || []
    historyTotal.value = res.data?.total || 0
  })
}

const handleSelectionChange = (currentSelection) => {
  const currentPageIds = new Set(policyTableData.value.map(item => item.id))
  currentPageIds.forEach(id => {
    delete selectedRowMap[id]
  })
  currentSelection.forEach(row => {
    selectedRowMap[row.id] = row
  })
}

const clearSelection = () => {
  Object.keys(selectedRowMap).forEach(key => delete selectedRowMap[key])
  policyTableRef.value?.clearSelection()
}

const handlePredict = async () => {
  if (!selectedIds.value.length) {
    ElMessage.warning('请先选择要预测的保单')
    return
  }

  try {
    const duplicateRes = await request.post('/insurPred/countByBusinessIds', {
      ids: selectedIds.value
    })
    const duplicateIds = (duplicateRes.data || []).map(item => item.id)
    if (duplicateIds.length) {
      await ElMessageBox.confirm(
          `保单 ${duplicateIds.join('、')} 已存在历史预测记录，是否继续重复预测？`,
          '重复预测提示',
          { type: 'warning' }
      )
    }

    const predictRes = await request.post('/insurPred/predict', {
      ids: selectedIds.value
    })

    if (predictRes.code === '200') {
      latestResults.value = predictRes.data || []
      resultDialogVisible.value = true
      ElMessage.success('预测完成并已保存历史记录')
      clearSelection()
      loadPolicyPage()
      loadHistoryPage()
    } else {
      ElMessage.error(predictRes.msg || '预测失败')
    }
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      console.error(error)
      ElMessage.error('预测请求未完成，请检查 FastAPI 和 Spring Boot 服务是否已启动')
    }
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

loadPolicyPage()
loadHistoryPage()
</script>

<style scoped>
.prediction-banner {
  margin-bottom: 12px;
  padding: 18px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background:
      linear-gradient(135deg, rgba(40, 167, 69, 0.10), rgba(32, 201, 151, 0.16)),
      #fff;
}

.banner-title {
  font-size: 20px;
  font-weight: bold;
  color: #14532d;
}

.banner-desc {
  margin-top: 6px;
  color: #4b5563;
}

.banner-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.pick-count {
  min-width: 115px;
  padding: 10px 14px;
  border-radius: 12px;
  background: #ecfdf3;
  color: #047857;
  font-weight: 600;
  text-align: center;
}

.section-title {
  font-size: 18px;
  font-weight: bold;
  color: #1f2937;
}

.section-subtitle {
  margin-top: 4px;
  color: #6b7280;
  font-size: 13px;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.result-card {
  border-radius: 14px;
  padding: 18px;
  color: #fff;
}

.result-blue {
  background: linear-gradient(135deg, #2563eb, #0ea5e9);
}

.result-orange {
  background: linear-gradient(135deg, #f97316, #fb7185);
}

.result-green {
  background: linear-gradient(135deg, #059669, #22c55e);
}

.result-label {
  opacity: 0.92;
  font-size: 13px;
}

.result-value {
  margin-top: 8px;
  font-size: 28px;
  font-weight: bold;
}

@media (max-width: 900px) {
  .prediction-banner {
    flex-direction: column;
    align-items: stretch;
  }

  .result-grid {
    grid-template-columns: 1fr;
  }
}
</style>
