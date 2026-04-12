<template>
  <div class="card">
    <div class="toolbar">
      <div class="title">用户管理</div>
      <el-button type="primary" @click="openAdd">新增用户</el-button>
    </div>

    <el-table :data="tableData" stripe style="width: 100%">
      <el-table-column prop="employeeNo" label="工号" width="120" />
      <el-table-column prop="name" label="姓名" width="140" />
      <el-table-column prop="role" label="角色" width="120">
        <template #default="scope">
          <el-tag :type="scope.row.role === 'ADMIN' ? 'danger' : 'success'">
            {{ scope.row.role === 'ADMIN' ? '管理员' : '普通用户' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="lastLoginTime" label="上次登录时间" min-width="180" />
      <el-table-column prop="createTime" label="创建时间" min-width="180" />
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="scope">
          <el-button
            type="primary"
            link
            :disabled="scope.row.role === 'ADMIN'"
            @click="openEdit(scope.row)"
          >
            修改
          </el-button>
          <el-button
            type="danger"
            link
            :disabled="scope.row.role === 'ADMIN' || scope.row.id === currentUser.id"
            @click="handleDelete(scope.row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      v-model="dialogVisible"
      :title="form.id ? '修改用户' : '新增用户'"
      width="460px"
      append-to-body
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="88px">
        <el-form-item label="工号" prop="employeeNo">
          <el-input v-model="form.employeeNo" :disabled="!!form.id" maxlength="6" />
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="密码" :prop="form.id ? '' : 'password'">
          <el-input v-model="form.password" show-password :placeholder="form.id ? '留空则保持原密码' : '请输入密码'" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="form.role" style="width: 100%">
            <el-option label="普通用户" value="USER" />
            <el-option label="管理员" value="ADMIN" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/request'
import { getCurrentUser } from '@/utils/auth'

const formRef = ref()
const dialogVisible = ref(false)
const tableData = ref([])
const currentUser = getCurrentUser()

const emptyForm = () => ({
  id: null,
  employeeNo: '',
  name: '',
  password: '',
  role: 'USER',
})

const form = ref(emptyForm())

const validateEmployeeNo = (rule, value, callback) => {
  if (!/^\d{6}$/.test(value || '')) {
    callback(new Error('请输入6位数字工号'))
    return
  }
  callback()
}

const rules = {
  employeeNo: [{ required: true, validator: validateEmployeeNo, trigger: 'blur' }],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
}

const loadData = async () => {
  const res = await request.get('/user/selectAll')
  if (res.code === '200') {
    tableData.value = res.data || []
  } else {
    ElMessage.error(res.msg)
  }
}

const openAdd = () => {
  form.value = emptyForm()
  dialogVisible.value = true
}

const openEdit = (row) => {
  form.value = {
    id: row.id,
    employeeNo: row.employeeNo,
    name: row.name,
    password: '',
    role: row.role,
  }
  dialogVisible.value = true
}

const submitForm = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    const api = form.value.id ? request.put('/user/update', form.value) : request.post('/user/add', form.value)
    const res = await api
    if (res.code === '200') {
      ElMessage.success(form.value.id ? '修改成功' : '新增成功')
      dialogVisible.value = false
      loadData()
    } else {
      ElMessage.error(res.msg)
    }
  })
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除用户 ${row.name} 吗？`, '删除确认', { type: 'warning' })
    const res = await request.delete(`/user/delete/${row.id}`)
    if (res.code === '200') {
      ElMessage.success('删除成功')
      loadData()
    } else {
      ElMessage.error(res.msg)
    }
  } catch (e) {
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.title {
  font-size: 18px;
  font-weight: bold;
}
</style>
