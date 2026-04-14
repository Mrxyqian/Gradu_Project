<template>
  <div>
    <div class="card" style="margin-bottom: 10px">
      <el-input
        v-model="data.id"
        style="width: 220px; margin-right: 10px"
        placeholder="请输入保单编号查询"
        :prefix-icon="Search"
      />
      <el-select v-model="data.typeRisk" style="width: 200px; margin-right: 10px" placeholder="请选择车辆类型" clearable>
        <el-option label="摩托车" :value="1" />
        <el-option label="货车" :value="2" />
        <el-option label="乘用车" :value="3" />
        <el-option label="农用车" :value="4" />
      </el-select>
      <el-select v-model="data.typeFuel" style="width: 200px; margin-right: 10px" placeholder="请选择燃料类型" clearable>
        <el-option label="汽油" value="P" />
        <el-option label="柴油" value="D" />
      </el-select>
      <el-input v-model.number="data.yearMatriculation" style="width: 200px; margin-right: 10px" placeholder="请输入注册年份" />
      <el-button type="primary" style="margin-left: 10px" @click="load">查询</el-button>
      <el-button type="info" @click="reset">重置</el-button>
    </div>

    <div class="card">
      <div style="margin-bottom: 10px">
        <el-button type="primary" @click="handleAdd">新增</el-button>
      </div>
      <div style="overflow-x: auto">
        <el-table :data="data.tableData" style="width: 100%">
          <el-table-column prop="id" label="保单编号" width="110" />
          <el-table-column prop="typeRisk" label="车辆类型" width="100">
            <template #default="scope">
              {{ getTypeRiskText(scope.row.typeRisk) }}
            </template>
          </el-table-column>
          <el-table-column prop="yearMatriculation" label="注册年份" width="100" />
          <el-table-column prop="power" label="车辆功率(HP)" width="120" />
          <el-table-column prop="cylinderCapacity" label="发动机排量(cc)" width="140" />
          <el-table-column prop="valueVehicle" label="车辆市场价值" width="130" />
          <el-table-column prop="nDoors" label="车门数量" width="100" />
          <el-table-column prop="typeFuel" label="燃料类型" width="100">
            <template #default="scope">
              {{ scope.row.typeFuel === 'P' ? '汽油' : '柴油' }}
            </template>
          </el-table-column>
          <el-table-column prop="length" label="车辆长度(米)" width="130" />
          <el-table-column prop="weight" label="车辆重量(千克)" width="140" />
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="scope">
              <el-button class="edit-action-btn" type="primary" plain size="small" @click="handleEdit(scope.row)">编辑</el-button>
              <el-button v-if="canDelete" type="danger" plain size="small" @click="del(scope.row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <div class="card" style="margin-top: 10px">
      <el-pagination
        v-model:current-page="data.pageNum"
        v-model:page-size="data.pageSize"
        background
        layout="prev, pager, next"
        :total="data.total"
        @current-change="handleCurrentChange"
      />
    </div>

    <el-dialog v-model="data.formVisible" width="50%" :title="data.formMode === 'edit' ? '车辆信息' : '新增车辆信息'" destroy-on-close>
      <el-form ref="formRef" :model="data.form" :rules="rules" label-width="140px" label-position="right" style="padding-right: 40px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="保单编号" prop="id">
              <el-input v-model="data.form.id" :disabled="data.formMode === 'edit'" autocomplete="off" placeholder="请输入已存在的保单编号" />
            </el-form-item>
          </el-col>
          <el-col v-if="data.formMode === 'edit'" :span="12">
            <el-form-item label="车辆类型" prop="typeRisk">
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
            <el-form-item label="注册年份" prop="yearMatriculation">
              <el-input-number v-model="data.form.yearMatriculation" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="车辆功率(HP)" prop="power">
              <el-input-number v-model="data.form.power" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="发动机排量(cc)" prop="cylinderCapacity">
              <el-input-number v-model="data.form.cylinderCapacity" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="车辆市场价值" prop="valueVehicle">
              <el-input-number v-model="data.form.valueVehicle" :precision="2" :step="100" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="车门数量" prop="nDoors">
              <el-input-number v-model="data.form.nDoors" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="燃料类型" prop="typeFuel">
              <el-select v-model="data.form.typeFuel" style="width: 100%">
                <el-option label="汽油" value="P" />
                <el-option label="柴油" value="D" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="车辆长度(米)" prop="length">
              <el-input-number v-model="data.form.length" :precision="2" :step="0.1" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="车辆重量(千克)" prop="weight">
              <el-input-number v-model="data.form.weight" :min="0" style="width: 100%" />
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

const baseUrl = '/vehicleInfo'
const canDelete = true

const createEmptyForm = () => ({
  id: null,
  typeRisk: null,
  yearMatriculation: null,
  power: null,
  cylinderCapacity: null,
  valueVehicle: null,
  nDoors: null,
  typeFuel: '',
  length: null,
  weight: null,
})

const data = reactive({
  id: '',
  typeRisk: null,
  typeFuel: '',
  yearMatriculation: null,
  tableData: [],
  total: 0,
  pageNum: 1,
  pageSize: 10,
  formVisible: false,
  formMode: 'add',
  form: createEmptyForm(),
})

const rules = reactive({
  id: [{ required: true, message: '请输入保单编号', trigger: 'blur' }],
  yearMatriculation: [{ required: true, message: '请输入注册年份', trigger: 'blur' }],
  power: [{ required: true, message: '请输入车辆功率', trigger: 'blur' }],
  cylinderCapacity: [{ required: true, message: '请输入发动机排量', trigger: 'blur' }],
  valueVehicle: [{ required: true, message: '请输入车辆市场价值', trigger: 'blur' }],
  nDoors: [{ required: true, message: '请输入车门数量', trigger: 'blur' }],
  typeFuel: [{ required: true, message: '请选择燃料类型', trigger: 'change' }],
})

const formRef = ref()

const getTypeRiskText = (type) => {
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
      typeFuel: data.typeFuel,
      yearMatriculation: data.yearMatriculation,
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
  data.typeFuel = ''
  data.yearMatriculation = null
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