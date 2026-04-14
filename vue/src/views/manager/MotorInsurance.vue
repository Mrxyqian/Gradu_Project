<template>
  <div>
    <div class="card" style="margin-bottom: 10px">
      <el-input
        v-model="data.id"
        style="width: 220px; margin-right: 10px"
        placeholder="请输入保单编号查询"
        :prefix-icon="Search"
      />
      <el-select v-model="data.typeRisk" style="width: 200px; margin-right: 10px" placeholder="请选择风险类型" clearable>
        <el-option label="摩托车" :value="1" />
        <el-option label="货车" :value="2" />
        <el-option label="乘用车" :value="3" />
        <el-option label="农用车" :value="4" />
      </el-select>
      <el-select v-model="data.area" style="width: 200px; margin-right: 10px" placeholder="请选择地区" clearable>
        <el-option label="农村" :value="0" />
        <el-option label="城市" :value="1" />
      </el-select>
      <el-button type="primary" style="margin-left: 10px" @click="load">查询</el-button>
      <el-button type="info" @click="reset">重置</el-button>
    </div>

    <div class="card" style="margin-bottom: 10px">
      <div style="margin-bottom: 10px">
        <el-button type="primary" @click="handleAdd">新增</el-button>
      </div>

      <div style="overflow-x: auto">
        <el-table :data="data.tableData" style="width: 100%">
          <el-table-column prop="id" label="保单编号" width="110" fixed="left" />
          <el-table-column prop="dateStartContract" label="合同开始日期" width="130" />
          <el-table-column prop="dateLastRenewal" label="最后续保日期" width="130" />
          <el-table-column prop="dateNextRenewal" label="下次续保日期" width="130" />
          <el-table-column prop="distributionChannel" label="分销渠道" width="100">
            <template #default="scope">
              {{ scope.row.distributionChannel === 0 ? '代理人' : '保险经纪' }}
            </template>
          </el-table-column>
          <el-table-column prop="dateBirth" label="被保人出生日期" width="140" />
          <el-table-column prop="dateDrivingLicence" label="驾照签发日期" width="130" />
          <el-table-column prop="seniority" label="合作年数" width="100" />
          <el-table-column prop="policiesInForce" label="有效保单数" width="100" />
          <el-table-column prop="maxPolicies" label="历史最高保单数" width="130" />
          <el-table-column prop="maxProducts" label="历史最高产品数" width="130" />
          <el-table-column prop="lapse" label="失效保单数" width="100" />
          <el-table-column prop="dateLapse" label="合同终止日期" width="130" />
          <el-table-column prop="payment" label="缴费方式" width="100">
            <template #default="scope">
              {{ scope.row.payment === 0 ? '年缴' : '半年缴' }}
            </template>
          </el-table-column>
          <el-table-column prop="premium" label="净保费" width="100" />
          <el-table-column prop="typeRisk" label="风险类型" width="100">
            <template #default="scope">
              {{ getRiskTypeText(scope.row.typeRisk) }}
            </template>
          </el-table-column>
          <el-table-column prop="area" label="地区" width="80">
            <template #default="scope">
              {{ scope.row.area === 0 ? '农村' : '城市' }}
            </template>
          </el-table-column>
          <el-table-column prop="secondDriver" label="第二驾驶员" width="110">
            <template #default="scope">
              {{ scope.row.secondDriver === 0 ? '否' : '是' }}
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

    <el-dialog
      v-model="data.formVisible"
      width="80%"
      :title="data.formMode === 'edit' ? '保单信息' : '新增保单'"
      destroy-on-close
    >
      <el-form ref="formRef" :model="data.form" :rules="rules" label-width="150px" label-position="right" style="padding-right: 40px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item v-if="data.formMode === 'edit'" label="保单编号" prop="id">
              <el-input v-model="data.form.id" disabled autocomplete="off" />
            </el-form-item>
            <el-form-item v-else label="保单编号">
              <el-input model-value="新增后由系统自动生成" disabled />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="合同开始日期" prop="dateStartContract">
              <el-input v-model="data.form.dateStartContract" autocomplete="off" placeholder="YYYY/MM/DD" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="最后续保日期" prop="dateLastRenewal">
              <el-input v-model="data.form.dateLastRenewal" autocomplete="off" placeholder="YYYY/MM/DD" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="下次续保日期" prop="dateNextRenewal">
              <el-input v-model="data.form.dateNextRenewal" autocomplete="off" placeholder="YYYY/MM/DD" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="分销渠道" prop="distributionChannel">
              <el-select v-model="data.form.distributionChannel" style="width: 100%">
                <el-option label="代理人" :value="0" />
                <el-option label="保险经纪" :value="1" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="被保人出生日期" prop="dateBirth">
              <el-input v-model="data.form.dateBirth" autocomplete="off" placeholder="YYYY/MM/DD" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="驾照签发日期" prop="dateDrivingLicence">
              <el-input v-model="data.form.dateDrivingLicence" autocomplete="off" placeholder="YYYY/MM/DD" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="合作年数" prop="seniority">
              <el-input-number v-model="data.form.seniority" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="有效保单数" prop="policiesInForce">
              <el-input-number v-model="data.form.policiesInForce" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="历史最高保单数" prop="maxPolicies">
              <el-input-number v-model="data.form.maxPolicies" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="历史最高产品数" prop="maxProducts">
              <el-input-number v-model="data.form.maxProducts" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="失效保单数" prop="lapse">
              <el-input-number v-model="data.form.lapse" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="合同终止日期" prop="dateLapse">
              <el-input v-model="data.form.dateLapse" autocomplete="off" placeholder="YYYY/MM/DD" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="缴费方式" prop="payment">
              <el-select v-model="data.form.payment" style="width: 100%">
                <el-option label="年缴" :value="0" />
                <el-option label="半年缴" :value="1" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="净保费" prop="premium">
              <el-input-number v-model="data.form.premium" :precision="2" :step="100" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="风险类型" prop="typeRisk">
              <el-select v-model="data.form.typeRisk" style="width: 100%">
                <el-option label="摩托车" :value="1" />
                <el-option label="货车" :value="2" />
                <el-option label="乘用车" :value="3" />
                <el-option label="农用车" :value="4" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="地区" prop="area">
              <el-select v-model="data.form.area" style="width: 100%">
                <el-option label="农村" :value="0" />
                <el-option label="城市" :value="1" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="第二驾驶员" prop="secondDriver">
              <el-select v-model="data.form.secondDriver" style="width: 100%">
                <el-option label="否" :value="0" />
                <el-option label="是" :value="1" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
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
import { reactive, ref } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/request'

const baseUrl = '/motorInsurance'
const canDelete = true

const createEmptyForm = () => ({
  id: null,
  dateStartContract: '',
  dateLastRenewal: '',
  dateNextRenewal: '',
  distributionChannel: null,
  dateBirth: '',
  dateDrivingLicence: '',
  seniority: null,
  policiesInForce: null,
  maxPolicies: null,
  maxProducts: null,
  lapse: null,
  dateLapse: '',
  payment: null,
  premium: null,
  typeRisk: null,
  area: null,
  secondDriver: null,
})

const data = reactive({
  id: '',
  typeRisk: null,
  area: null,
  tableData: [],
  total: 0,
  pageNum: 1,
  pageSize: 10,
  formVisible: false,
  formMode: 'add',
  form: createEmptyForm(),
})

const rules = reactive({
  id: [{ required: true, message: '保单编号不能为空', trigger: 'blur' }],
  dateStartContract: [{ required: true, message: '请输入合同开始日期', trigger: 'blur' }],
  dateLastRenewal: [{ required: true, message: '请输入最后续保日期', trigger: 'blur' }],
  dateNextRenewal: [{ required: true, message: '请输入下次续保日期', trigger: 'blur' }],
  distributionChannel: [{ required: true, message: '请选择分销渠道', trigger: 'change' }],
  dateBirth: [{ required: true, message: '请输入被保人出生日期', trigger: 'blur' }],
  dateDrivingLicence: [{ required: true, message: '请输入驾照签发日期', trigger: 'blur' }],
  seniority: [{ required: true, message: '请输入合作年数', trigger: 'blur' }],
  policiesInForce: [{ required: true, message: '请输入有效保单数', trigger: 'blur' }],
  maxPolicies: [{ required: true, message: '请输入历史最高保单数', trigger: 'blur' }],
  maxProducts: [{ required: true, message: '请输入历史最高产品数', trigger: 'blur' }],
  lapse: [{ required: true, message: '请输入失效保单数', trigger: 'blur' }],
  payment: [{ required: true, message: '请选择缴费方式', trigger: 'change' }],
  premium: [{ required: true, message: '请输入净保费', trigger: 'blur' }],
  typeRisk: [{ required: true, message: '请选择风险类型', trigger: 'change' }],
  area: [{ required: true, message: '请选择地区', trigger: 'change' }],
  secondDriver: [{ required: true, message: '请选择第二驾驶员', trigger: 'change' }],
})

const formRef = ref()

const getRiskTypeText = (type) => {
  const map = { 1: '摩托车', 2: '货车', 3: '乘用车', 4: '农用车' }
  return map[type] || type
}

const load = () => {
  request.get(baseUrl + '/selectPage', {
    params: {
      pageNum: data.pageNum,
      pageSize: data.pageSize,
      id: data.id || null,
      typeRisk: data.typeRisk,
      area: data.area,
    },
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

const reset = () => {
  data.id = ''
  data.typeRisk = null
  data.area = null
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
        if (data.formMode === 'add') {
          ElMessage.success(`新增成功，保单编号：${res.data?.id ?? '-'}`)
        } else {
          ElMessage.success('保存成功')
        }
      } else {
        ElMessage.error(res.msg || '保存失败')
      }
    })
  })
}

const del = (id) => {
  if (!canDelete) {
    ElMessage.error('普通用户不能删除保单信息')
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
</style>