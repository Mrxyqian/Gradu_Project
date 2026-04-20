<template>
  <div>
    <div class="card toolbar-card">
      <div class="toolbar-actions">
        <el-button type="primary" @click="handleAdd">新增</el-button>
        <el-button type="success" plain @click="openQueryDialog">查询</el-button>
        <el-button type="info" plain @click="resetQuery">重置查询</el-button>
      </div>
    </div>

    <div class="card" style="margin-bottom: 10px">
      <div style="overflow-x: auto">
        <el-table :data="data.tableData" style="width: 100%">
          <el-table-column prop="id" label="保单编号" width="110" />
          <el-table-column prop="costClaimsYear" label="索赔成本" width="140" />
          <el-table-column prop="nClaimsYear" label="本年度索赔次数" width="150" />
          <el-table-column prop="nClaimsHistory" width="150">
            <template #header>
              <div class="filterable-header">
                <span>&#x5386;&#x53F2;&#x7D22;&#x8D54;&#x6B21;&#x6570;</span>
                <el-popover v-model:visible="historyClaimFilterVisible" placement="bottom" :width="156" trigger="click">
                  <template #reference>
                    <el-button class="header-filter-button" :class="{ active: isHistoryClaimFilterActive }" link>
                      <el-icon><Filter /></el-icon>
                    </el-button>
                  </template>
                  <div class="header-filter-panel">
                    <el-button text @click="clearHistoryClaimFilter">&#x5168;&#x90E8;</el-button>
                    <el-button text @click="applyHistoryClaimFilter(1)">&#x53D1;&#x751F;&#x7406;&#x8D54;</el-button>
                  </div>
                </el-popover>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="rClaimsHistory" label="历史出险率" width="140" />
          <el-table-column prop="typeRisk" label="风险类型" width="110">
            <template #default="scope">
              {{ getRiskTypeText(scope.row.typeRisk) }}
            </template>
          </el-table-column>
          <el-table-column prop="area" label="地区" width="100">
            <template #default="scope">
              {{ getAreaText(scope.row.area) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="scope">
              <el-button class="edit-action-btn" type="primary" plain size="small" @click="handleEdit(scope.row)">编辑</el-button>
              <el-button v-if="canDelete" type="danger" plain size="small" @click="del(scope.row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <div class="card">
      <el-pagination
        v-model:current-page="data.pageNum"
        v-model:page-size="data.pageSize"
        background
        layout="prev, pager, next"
        :total="data.total"
        @current-change="handleCurrentChange"
      />
    </div>

    <el-dialog v-model="data.queryVisible" title="查询理赔记录" width="72%" destroy-on-close>
      <el-form :model="data.queryForm" label-width="140px" label-position="right" style="padding-right: 30px">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="保单编号">
              <el-input-number v-model="data.queryForm.id" :min="1" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="索赔成本">
              <el-input-number v-model="data.queryForm.costClaimsYear" :precision="2" :step="100" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="本年度索赔次数">
              <el-input-number v-model="data.queryForm.nClaimsYear" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="历史索赔次数">
              <el-input-number v-model="data.queryForm.nClaimsHistory" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="历史出险率">
              <el-input-number v-model="data.queryForm.rClaimsHistory" :precision="2" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="风险类型">
              <el-select v-model="data.queryForm.typeRisk" style="width: 100%" clearable>
                <el-option label="摩托车" :value="1" />
                <el-option label="货车" :value="2" />
                <el-option label="乘用车" :value="3" />
                <el-option label="农用车" :value="4" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="地区">
              <el-select v-model="data.queryForm.area" style="width: 100%" clearable>
                <el-option label="农村" :value="0" />
                <el-option label="城市" :value="1" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="data.queryVisible = false">取消</el-button>
          <el-button type="primary" @click="submitQuery">开始查询</el-button>
        </span>
      </template>
    </el-dialog>

    <el-dialog v-model="data.formVisible" width="46%" :title="data.formMode === 'edit' ? '理赔记录信息' : '新增理赔记录'" destroy-on-close>
      <el-form ref="formRef" :model="data.form" :rules="rules" label-width="140px" label-position="right" style="padding-right: 40px">
        <el-form-item label="保单编号" prop="id">
          <el-input v-model="data.form.id" :disabled="data.formMode === 'edit'" placeholder="请输入已存在的保单编号" />
        </el-form-item>
        <el-form-item label="索赔成本" prop="costClaimsYear">
          <el-input-number v-model="data.form.costClaimsYear" :precision="2" :step="100" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="本年度索赔次数" prop="nClaimsYear">
          <el-input-number v-model="data.form.nClaimsYear" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="历史索赔次数" prop="nClaimsHistory">
          <el-input-number v-model="data.form.nClaimsHistory" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="历史出险率" prop="rClaimsHistory">
          <el-input-number v-model="data.form.rClaimsHistory" :precision="2" :min="0" style="width: 100%" />
        </el-form-item>
        <template v-if="data.formMode === 'edit'">
          <el-form-item label="风险类型" prop="typeRisk">
            <el-select v-model="data.form.typeRisk" style="width: 100%">
              <el-option label="摩托车" :value="1" />
              <el-option label="货车" :value="2" />
              <el-option label="乘用车" :value="3" />
              <el-option label="农用车" :value="4" />
            </el-select>
          </el-form-item>
          <el-form-item label="地区" prop="area">
            <el-select v-model="data.form.area" style="width: 100%">
              <el-option label="农村" :value="0" />
              <el-option label="城市" :value="1" />
            </el-select>
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="data.formVisible = false">取消</el-button>
          <el-button type="primary" @click="save">保存</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Filter } from '@element-plus/icons-vue'
import request from '@/utils/request'

const baseUrl = '/claimTypes'
const canDelete = true

const createEmptyForm = () => ({
  id: null,
  costClaimsYear: 0,
  nClaimsYear: 0,
  nClaimsHistory: 0,
  rClaimsHistory: 0,
  typeRisk: null,
  area: null,
})

const createEmptyQueryForm = () => ({
  id: null,
  costClaimsYear: null,
  nClaimsYear: null,
  nClaimsHistory: null,
  rClaimsHistory: null,
  typeRisk: null,
  area: null,
})

const data = reactive({
  queryVisible: false,
  queryForm: createEmptyQueryForm(),
  tableData: [],
  total: 0,
  pageNum: 1,
  pageSize: 10,
  formVisible: false,
  formMode: 'add',
  form: createEmptyForm(),
})

const historyClaimFilterVisible = ref(false)
const historyClaimStatus = ref(null)

const rules = reactive({
  id: [{ required: true, message: '请输入保单编号', trigger: 'blur' }],
  costClaimsYear: [{ required: true, message: '请输入索赔成本', trigger: 'blur' }],
  nClaimsYear: [{ required: true, message: '请输入本年度索赔次数', trigger: 'blur' }],
  nClaimsHistory: [{ required: true, message: '请输入历史索赔次数', trigger: 'blur' }],
  rClaimsHistory: [{ required: true, message: '请输入历史出险率', trigger: 'blur' }],
})

const formRef = ref()
const isHistoryClaimFilterActive = computed(() => historyClaimStatus.value !== null)

const getRiskTypeText = (type) => {
  const map = { 1: '摩托车', 2: '货车', 3: '乘用车', 4: '农用车' }
  return map[type] || type
}

const getAreaText = (area) => (Number(area) === 0 ? '农村' : '城市')

const buildQueryParams = () => {
  const params = {
    pageNum: data.pageNum,
    pageSize: data.pageSize,
    historyClaimStatus: historyClaimStatus.value,
    ...data.queryForm,
  }

  Object.keys(params).forEach((key) => {
    if (params[key] === '' || params[key] === undefined) {
      params[key] = null
    }
  })

  return params
}

const applyHistoryClaimFilter = (value) => {
  historyClaimStatus.value = value
  historyClaimFilterVisible.value = false
  data.pageNum = 1
  load()
}

const clearHistoryClaimFilter = () => {
  historyClaimStatus.value = null
  historyClaimFilterVisible.value = false
  data.pageNum = 1
  load()
}

const load = () => {
  request.get(baseUrl + '/selectPage', {
    params: buildQueryParams(),
  }).then((res) => {
    data.tableData = res.data?.list || []
    data.total = res.data?.total || 0
  })
}

load()

const handleCurrentChange = (pageNum) => {
  data.pageNum = pageNum
  load()
}

const openQueryDialog = () => {
  data.queryVisible = true
}

const submitQuery = () => {
  data.pageNum = 1
  data.queryVisible = false
  load()
}

const resetQuery = () => {
  data.queryForm = createEmptyQueryForm()
  historyClaimStatus.value = null
  historyClaimFilterVisible.value = false
  data.pageNum = 1
  load()
}

const handleAdd = () => {
  data.form = createEmptyForm()
  data.formMode = 'add'
  data.formVisible = true
}

const handleEdit = (row) => {
  data.form = JSON.parse(JSON.stringify(row))
  data.formMode = 'edit'
  data.formVisible = true
}

const save = () => {
  formRef.value.validate((valid) => {
    if (!valid) return
    request.request({
      url: data.formMode === 'edit' ? baseUrl + '/update' : baseUrl + '/add',
      method: data.formMode === 'edit' ? 'PUT' : 'POST',
      data: data.form,
    }).then((res) => {
      if (res.code === '200') {
        load()
        data.formVisible = false
        ElMessage.success('保存成功')
      } else {
        ElMessage.error(res.msg || '保存失败')
      }
    })
  })
}

const del = (id) => {
  if (!canDelete) {
    ElMessage.error('普通用户不能删除数据')
    return
  }
  ElMessageBox.confirm('删除数据后无法恢复，您确认删除吗？', '删除确认', { type: 'warning' })
    .then(() => {
      request.delete(baseUrl + '/delete/' + id).then((res) => {
        if (res.code === '200') {
          load()
          ElMessage.success('删除成功')
        } else {
          ElMessage.error(res.msg || '删除失败')
        }
      })
    })
    .catch(() => {})
}
</script>

<style scoped>
.toolbar-card {
  margin-bottom: 10px;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.edit-action-btn {
  color: #1f5a4c;
  border-color: rgba(47, 125, 107, 0.28);
  background: rgba(228, 242, 236, 0.95);
}

.edit-action-btn:hover,
.edit-action-btn:focus {
  color: #173f35;
  border-color: rgba(47, 125, 107, 0.42);
  background: rgba(214, 234, 227, 0.98);
}

.filterable-header {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.header-filter-button {
  padding: 0;
  min-height: auto;
  color: #64748b;
}

.header-filter-button.active {
  color: #2563eb;
}

.header-filter-panel {
  display: flex;
  flex-direction: column;
  align-items: stretch;
}

.header-filter-panel :deep(.el-button) {
  justify-content: flex-start;
  margin-left: 0;
}
</style>
