<template>
  <div>
    <div class="card" style="margin-bottom: 10px">
      <el-input style="width: 260px; margin-right: 10px" v-model="data.claimsType" placeholder="请输入索赔类型查询" :prefix-icon="Search"/>
      <el-button type="primary" style="margin-left: 10px" @click="load">查询</el-button>
      <el-button type="info" @click="reset">重置</el-button>
    </div>

    <div class="card" style="margin-bottom: 10px">
      <div style="margin-bottom: 10px">
          <el-button type="primary" @click="handleAdd">新增</el-button>
      </div>

      <div>
        <el-table :data="data.tableData" style="width: 100%">
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="claimsType" label="索赔类型" />
          <el-table-column prop="costClaimsYear" label="当年总索赔成本" width="150" />
          <el-table-column prop="costClaimsByType" label="按类型索赔成本" width="150" />
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="scope">
              <el-button type="primary" plain size="small" @click="handleEdit(scope.row)">编辑</el-button>
              <el-button v-if="canDelete" type="danger" plain size="small" @click="del(scope.row.id)">删除</el-button>
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

    <el-dialog width="40%" v-model="data.formVisible" title="索赔类型信息" destroy-on-close>
      <el-form :model="data.form" :rules="rules" ref="formRef" label-width="140px" label-position="right" style="padding-right: 40px">
        <el-form-item label="ID" prop="id">
          <el-input v-model="data.form.id" autocomplete="off" />
        </el-form-item>
        <el-form-item label="索赔类型" prop="claimsType">
          <el-input v-model="data.form.claimsType" autocomplete="off" placeholder="请输入索赔类型" />
        </el-form-item>
        <el-form-item label="当年总索赔成本" prop="costClaimsYear">
          <el-input-number v-model="data.form.costClaimsYear" :precision="2" :step="100" style="width: 100%" />
        </el-form-item>
        <el-form-item label="按类型索赔成本" prop="costClaimsByType">
          <el-input-number v-model="data.form.costClaimsByType" :precision="2" :step="100" style="width: 100%" />
        </el-form-item>
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
import { getCurrentUser } from "@/utils/auth";

const baseUrl = '/claimTypes'
const canDelete = getCurrentUser().role === 'ADMIN'

const data = reactive({
  claimsType: '',
  tableData: [],
  total: 0,
  pageNum: 1,
  pageSize: 10,
  formVisible: false,
  form: {}
})

const rules = reactive({
  id: [{ required: true, message: '请输入ID', trigger: 'blur' }],
  claimsType: [{ required: true, message: '请输入索赔类型', trigger: 'blur' }],
  costClaimsYear: [{ required: true, message: '请输入当年总索赔成本', trigger: 'blur' }],
  costClaimsByType: [{ required: true, message: '请输入按类型索赔成本', trigger: 'blur' }]
})

const formRef = ref()

const load = () => {
  request.get(baseUrl + '/selectPage', {
    params: {
      pageNum: data.pageNum,
      pageSize: data.pageSize,
      claimsType: data.claimsType
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
  data.claimsType = ''
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
  if (!canDelete) {
    ElMessage.error('普通用户不能删除索赔类型')
    return
  }
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
