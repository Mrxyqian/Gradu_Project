<template>
  <div>
    <div class="card" style="margin-bottom: 10px">
      <el-input style="width: 200px; margin-right: 10px" v-model="data.id" placeholder="请输入ID查询" :prefix-icon="Search"/>
      <el-select style="width: 200px; margin-right: 10px" v-model="data.typeRisk" placeholder="请选择风险类型" clearable>
        <el-option label="摩托车" :value="1"></el-option>
        <el-option label="货车" :value="2"></el-option>
        <el-option label="乘用车" :value="3"></el-option>
        <el-option label="农用车" :value="4"></el-option>
      </el-select>
      <el-select style="width: 200px; margin-right: 10px" v-model="data.area" placeholder="请选择地区" clearable>
        <el-option label="农村" :value="0"></el-option>
        <el-option label="城市" :value="1"></el-option>
      </el-select>
      <el-button type="primary" style="margin-left: 10px" @click="load">查询</el-button>
      <el-button type="info" @click="reset">重置</el-button>
    </div>

    <div class="card" style="margin-bottom: 10px">
      <div style="margin-bottom: 10px">
          <el-button type="primary" @click="handleAdd">新增</el-button>
      </div>

      <div style="overflow-x: auto;">
        <el-table :data="data.tableData" style="width: 100%">
          <el-table-column prop="id" label="ID" width="80" fixed="left" />
          <el-table-column prop="dateStartContract" label="合同开始日期" width="130" />
          <el-table-column prop="dateLastRenewal" label="最后续保日期" width="130" />
          <el-table-column prop="dateNextRenewal" label="下次续保日期" width="130" />
          <el-table-column prop="distributionChannel" label="分销渠道" width="100">
            <template #default="scope">
              {{ scope.row.distributionChannel === 0 ? '代理人' : '保险经纪' }}
            </template>
          </el-table-column>
          <el-table-column prop="dateBirth" label="被保险人出生日期" width="140" />
          <el-table-column prop="dateDrivingLicence" label="驾照签发日期" width="130" />
          <el-table-column prop="seniority" label="关联总年数" width="100" />
          <el-table-column prop="policiesInForce" label="有效保单数" width="100" />
          <el-table-column prop="maxPolicies" label="历史最高保单数" width="130" />
          <el-table-column prop="maxProducts" label="历史最高产品数" width="140" />
          <el-table-column prop="lapse" label="失效保单数" width="110" />
          <el-table-column prop="dateLapse" label="合同终止日期" width="130" />
          <el-table-column prop="payment" label="缴费方式" width="100">
            <template #default="scope">
              {{ scope.row.payment === 0 ? '年缴' : '半年缴' }}
            </template>
          </el-table-column>
          <el-table-column prop="premium" label="净保费" width="100" />
          <el-table-column prop="costClaimsYear" label="索赔成本" width="100" />
          <el-table-column prop="nClaimsYear" label="本年度索赔次数" width="140" />
          <el-table-column prop="nClaimsHistory" label="历史索赔次数" width="130" />
          <el-table-column prop="rClaimsHistory" label="索赔频率比" width="120" />
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
              <el-button type="primary" plain size="small" @click="handleEdit(scope.row)">编辑</el-button>
              <el-button type="danger" plain size="small" @click="del(scope.row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <div class="card">
      <el-pagination v-model:current-page="data.pageNum" v-model:page-size="data.pageSize"
                     @current-change="handleCurrentChange"
                     background layout="prev, pager, next" :total="data.total" />
    </div>

    <el-dialog width="80%" v-model="data.formVisible" title="保单信息" destroy-on-close>
      <el-form :model="data.form" :rules="rules" ref="formRef" label-width="150px" label-position="right" style="padding-right: 40px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="ID" prop="id">
              <el-input v-model="data.form.id" autocomplete="off" />
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
                <el-option label="代理人" :value="0"></el-option>
                <el-option label="保险经纪" :value="1"></el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="被保险人出生日期" prop="dateBirth">
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
            <el-form-item label="关联总年数" prop="seniority">
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
                <el-option label="年缴" :value="0"></el-option>
                <el-option label="半年缴" :value="1"></el-option>
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
            <el-form-item label="索赔成本" prop="costClaimsYear">
              <el-input-number v-model="data.form.costClaimsYear" :precision="2" :step="100" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="本年度索赔次数" prop="nClaimsYear">
              <el-input-number v-model="data.form.nClaimsYear" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="历史索赔次数" prop="nClaimsHistory">
              <el-input-number v-model="data.form.nClaimsHistory" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="索赔频率比" prop="rClaimsHistory">
              <el-input-number v-model="data.form.rClaimsHistory" :precision="2" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="风险类型" prop="typeRisk">
              <el-select v-model="data.form.typeRisk" style="width: 100%">
                <el-option label="摩托车" :value="1"></el-option>
                <el-option label="货车" :value="2"></el-option>
                <el-option label="乘用车" :value="3"></el-option>
                <el-option label="农用车" :value="4"></el-option>
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="地区" prop="area">
              <el-select v-model="data.form.area" style="width: 100%">
                <el-option label="农村" :value="0"></el-option>
                <el-option label="城市" :value="1"></el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="第二驾驶员" prop="secondDriver">
              <el-select v-model="data.form.secondDriver" style="width: 100%">
                <el-option label="否" :value="0"></el-option>
                <el-option label="是" :value="1"></el-option>
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="data.formVisible = false">取 消</el-button>
          <el-button type="primary" @click="save">保 存</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from "vue";
import { Search } from '@element-plus/icons-vue'
import request from "@/utils/request";
import {ElMessage, ElMessageBox} from "element-plus";

const baseUrl = '/motorInsurance'

const data = reactive({
  id: '',
  typeRisk: null,
  area: null,
  tableData: [],
  total: 0,
  pageNum: 1,
  pageSize: 10,
  formVisible: false,
  form: {}
})

const rules = reactive({
  id: [{ required: true, message: '请输入ID', trigger: 'blur' }],
  dateStartContract: [{ required: true, message: '请输入合同开始日期', trigger: 'blur' }],
  typeRisk: [{ required: true, message: '请选择风险类型', trigger: 'change' }],
  area: [{ required: true, message: '请选择地区', trigger: 'change' }],
  premium: [{ required: true, message: '请输入净保费', trigger: 'blur' }]
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
      id: data.id,
      typeRisk: data.typeRisk,
      area: data.area
    }
  }).then(res => {
    data.tableData = res.data?.list || []
    data.total = res.data.total || 0
  })
}

load()

const handleCurrentChange = (pageNum) => {
  load()
}

const reset = () => {
  data.id = ''
  data.typeRisk = null
  data.area = null
  load()
}

const handleAdd = () => {
  data.form = {}
  data.formVisible = true
}

const save = () => {
  formRef.value.validate((valid) =>{
    if (valid) {
      request.request({
        url: data.form.id ? baseUrl + '/update' : baseUrl + '/add',
        method: data.form.id ? 'PUT' : 'POST',
        data: data.form
      }).then(res => {
        if (res.code === '200') {
          load()
          data.formVisible = false
          ElMessage.success('保存成功')
        } else {
          ElMessage.error(res.msg || '保存失败')
        }
      })
    }
  })
}

const handleEdit = (row) => {
  data.form = JSON.parse(JSON.stringify(row))
  data.formVisible = true
}

const del = (id) => {
  ElMessageBox.confirm('删除数据后无法恢复，您确认删除吗？', '删除确认', { type: 'warning' }).then(res => {
    request.delete(baseUrl + '/delete/' + id).then(res => {
      if (res.code === '200') {
        load()
        ElMessage.success('删除成功')
      } else {
        ElMessage.error(res.msg || '删除失败')
      }
    })
  }).catch(res => {})
}
</script>
