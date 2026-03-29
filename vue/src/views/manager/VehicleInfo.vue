<template>
  <div>
    <div class="card" style="margin-bottom: 10px">
      <el-input style="width: 200px; margin-right: 10px" v-model="data.id" placeholder="请输入ID查询" :prefix-icon="Search"/>
      <el-select style="width: 200px; margin-right: 10px" v-model="data.typeRisk" placeholder="请选择车辆类型" clearable>
        <el-option label="摩托车" :value="1"></el-option>
        <el-option label="货车" :value="2"></el-option>
        <el-option label="乘用车" :value="3"></el-option>
        <el-option label="农用车" :value="4"></el-option>
      </el-select>
      <el-select style="width: 200px; margin-right: 10px" v-model="data.typeFuel" placeholder="请选择能源类型" clearable>
        <el-option label="汽油" value="P"></el-option>
        <el-option label="柴油" value="D"></el-option>
      </el-select>
      <el-input style="width: 200px; margin-right: 10px" v-model.number="data.yearMatriculation" placeholder="请输入注册年份" clearable/>
      <el-button type="primary" style="margin-left: 10px" @click="load">查询</el-button>
      <el-button type="info" @click="reset">重置</el-button>
    </div>

    <div class="card">
      <div style="overflow-x: auto;">
        <el-table :data="data.tableData" style="width: 100%">
          <el-table-column prop="id" label="ID" width="80" />
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
          <el-table-column prop="typeFuel" label="能源类型" width="100">
            <template #default="scope">
              {{ scope.row.typeFuel === 'P' ? '汽油' : '柴油' }}
            </template>
          </el-table-column>
          <el-table-column prop="length" label="车辆长度(米)" width="130" />
          <el-table-column prop="weight" label="车辆重量(千克)" width="140" />
        </el-table>
      </div>
    </div>

    <div class="card" style="margin-top: 10px">
      <el-pagination v-model:current-page="data.pageNum" v-model:page-size="data.pageSize"
                     @current-change="handleCurrentChange"
                     background layout="prev, pager, next" :total="data.total" />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from "vue";
import { Search } from '@element-plus/icons-vue'
import request from "@/utils/request";

const baseUrl = '/vehicleInfo'

const data = reactive({
  id: '',
  typeRisk: null,
  typeFuel: '',
  yearMatriculation: null,
  tableData: [],
  total: 0,
  pageNum: 1,
  pageSize: 10
})

const getTypeRiskText = (type) => {
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
      typeFuel: data.typeFuel,
      yearMatriculation: data.yearMatriculation
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
  data.typeFuel = ''
  data.yearMatriculation = null
  load()
}
</script>
