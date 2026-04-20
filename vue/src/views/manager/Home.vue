<template>
  <div class="home-shell">
    <section class="card home-hero">
      <div class="hero-main">
        <div class="hero-chip-row">
          <span class="hero-chip">{{ todayLabel }}</span>
        </div>
        <h1 class="hero-title">欢迎回来，{{ currentUser.name || '用户' }}</h1>

        <div
          v-if="showTodoPanel"
          class="todo-panel"
          role="button"
          tabindex="0"
          @click="openTodoDialog"
          @keyup.enter="openTodoDialog"
          @keyup.space.prevent="openTodoDialog"
        >
          <div class="todo-icon-wrap">
            <el-icon><Calendar /></el-icon>
          </div>

          <div class="todo-body">
            <div class="todo-head">
              <div class="todo-title">待办事项清单</div>
            </div>

            <div class="todo-badge-row">
              <span class="todo-badge">缺理赔记录 {{ homeTodo.missingClaimCount || 0 }}</span>
              <span class="todo-badge">缺车辆信息 {{ homeTodo.missingVehicleCount || 0 }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="hero-side">
        <div class="hero-side-panel">
          <div class="hero-side-head">
            <div>
              <div class="hero-side-label">业务概览</div>
              <div class="hero-side-value">核心数据</div>
            </div>
            <div class="hero-side-badge">总览</div>
          </div>

          <div class="hero-side-mosaic">
            <div class="hero-side-item hero-side-item-primary">
              <span>总保费收入</span>
              <strong>{{ formatWanCurrency(statistics.totalPremium) }}</strong>
            </div>
            <div class="hero-side-item hero-side-item-profit">
              <span>赔付率</span>
              <strong>{{ formatPercent(statistics.premiumProfitRate) }}</strong>
            </div>
            <div class="hero-side-item hero-side-item-policy">
              <span>本年度保单数量</span>
              <strong>{{ formatNumber(statistics.policyCount2018) }}</strong>
            </div>
          </div>
        </div>
      </div>
    </section>

    <div class="card feature-card">
      <div class="block-head block-head-row">
        <div class="block-title">快捷入口</div>
        <el-button class="shortcut-manage-btn" type="primary" plain @click="openShortcutDialog">管理快捷入口</el-button>
      </div>

      <div v-if="visibleQuickEntries.length" class="quick-grid">
        <button
          v-for="item in visibleQuickEntries"
          :key="item.title"
          class="quick-entry"
          type="button"
          @click="goTo(item.path)"
        >
          <div class="quick-entry-icon" :style="{ background: item.iconBackground, color: item.iconColor }">
            <component :is="item.icon" />
          </div>
          <div class="quick-entry-body">
            <div class="quick-entry-title">{{ item.title }}</div>
            <div class="quick-entry-path">{{ item.path }}</div>
          </div>
          <div class="quick-entry-arrow">进入</div>
        </button>
      </div>

      <el-empty v-else description="暂无快捷入口">
        <el-button class="shortcut-manage-btn" type="primary" plain @click="openShortcutDialog">添加快捷入口</el-button>
      </el-empty>
    </div>

    <el-dialog v-model="shortcutDialogVisible" title="管理快捷入口" width="680px">
      <div class="shortcut-dialog-tip">最多可添加 4 个快捷入口。</div>

      <div class="shortcut-option-grid">
        <button
          v-for="item in allShortcutOptions"
          :key="item.path"
          type="button"
          class="shortcut-option"
          :class="{ 'shortcut-option-active': shortcutDraft.includes(item.path) }"
          @click="toggleShortcut(item.path)"
        >
          <div class="shortcut-option-icon" :style="{ background: item.iconBackground, color: item.iconColor }">
            <component :is="item.icon" />
          </div>
          <div class="shortcut-option-body">
            <div class="shortcut-option-title">{{ item.title }}</div>
            <div class="shortcut-option-path">{{ item.path }}</div>
          </div>
          <div class="shortcut-option-check">{{ shortcutDraft.includes(item.path) ? '已选' : '选择' }}</div>
        </button>
      </div>

      <template #footer>
        <el-button @click="shortcutDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingShortcuts" @click="saveShortcuts">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="todoDialogVisible" title="待办事项详情" width="560px" destroy-on-close>
      <div class="todo-badge-row todo-badge-row-dialog">
        <span class="todo-badge">缺理赔记录 {{ homeTodo.missingClaimCount || 0 }}</span>
        <span class="todo-badge">缺车辆信息 {{ homeTodo.missingVehicleCount || 0 }}</span>
      </div>

      <div v-if="homeTodo.items?.length" class="todo-list">
        <div v-for="item in homeTodo.items" :key="item.policyId" class="todo-item">
          <span class="todo-policy">保单编号 {{ item.policyId }}</span>
          <span class="todo-missing">{{ item.missingSummary }}</span>
        </div>
      </div>
      <el-empty v-else description="当前暂无待补录事项" />
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Calendar,
  DataAnalysis,
  Document,
  MagicStick,
  Operation,
  PieChart,
  User as UserIcon,
  Van,
} from '@element-plus/icons-vue'
import request from '@/utils/request'
import { getCurrentUser, setCurrentUser } from '@/utils/auth'

const router = useRouter()
const currentUser = ref(getCurrentUser())
const statistics = ref({
  totalPremium: 0,
  premiumProfitRate: 0,
  policyCount2018: 0,
  avgHistoryClaimRate: 0,
})
const homeTodo = ref({
  totalCount: 0,
  missingClaimCount: 0,
  missingVehicleCount: 0,
  items: [],
})
const selectedShortcutPaths = ref([])
const shortcutDraft = ref([])
const shortcutDialogVisible = ref(false)
const todoDialogVisible = ref(false)
const savingShortcuts = ref(false)

const todayLabel = computed(() => {
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  }).format(new Date())
})

const showTodoPanel = computed(() => currentUser.value?.role === 'USER')

const formatNumber = (value) => {
  const number = Number(value || 0)
  return number.toLocaleString('zh-CN')
}

const formatWanCurrency = (value) => `￥${(Number(value || 0) / 10000).toFixed(1)} 万`
const formatPercent = (value) => `${(Number(value || 0) * 100).toFixed(2)}%`
const parseShortcutPaths = (value) => {
  if (!value) return []
  return String(value)
    .split(',')
    .map(item => item.trim())
    .filter(Boolean)
}

const allShortcutOptions = computed(() => {
  const entries = [
    {
      title: '保单信息',
      path: '/motorInsurance',
      icon: Document,
      iconBackground: 'rgba(47, 125, 107, 0.14)',
      iconColor: '#2f7d6b',
    },
    {
      title: '保单分析',
      path: '/motorInsuranceStatistics',
      icon: DataAnalysis,
      iconBackground: 'rgba(91, 143, 203, 0.14)',
      iconColor: '#4b75ab',
    },
    {
      title: '理赔记录',
      path: '/claimTypes',
      icon: DataAnalysis,
      iconBackground: 'rgba(242, 179, 109, 0.18)',
      iconColor: '#b5792d',
    },
    {
      title: '理赔分析',
      path: '/claimStatistics',
      icon: PieChart,
      iconBackground: 'rgba(124, 181, 139, 0.18)',
      iconColor: '#4d835b',
    },
    {
      title: '预测管理',
      path: '/predictionManage',
      icon: MagicStick,
      iconBackground: 'rgba(137, 124, 201, 0.16)',
      iconColor: '#5c4ab3',
    },
    {
      title: '车辆信息',
      path: '/vehicleInfo',
      icon: Van,
      iconBackground: 'rgba(69, 145, 199, 0.16)',
      iconColor: '#3e74a8',
    },
    {
      title: '预测统计',
      path: '/predictionStatistics',
      icon: PieChart,
      iconBackground: 'rgba(111, 164, 118, 0.16)',
      iconColor: '#487852',
    },
  ]

  if (currentUser.value?.role === 'ADMIN') {
    entries.push({
      title: '模型训练',
      path: '/modelTraining',
      icon: Operation,
      iconBackground: 'rgba(137, 124, 201, 0.16)',
      iconColor: '#5c4ab3',
    })
    entries.push({
      title: '用户管理',
      path: '/userManage',
      icon: UserIcon,
      iconBackground: 'rgba(91, 143, 203, 0.14)',
      iconColor: '#4b75ab',
    })
  }

  return entries
})

const visibleQuickEntries = computed(() => {
  const pathIndexMap = new Map(selectedShortcutPaths.value.map((path, index) => [path, index]))
  return allShortcutOptions.value
    .filter(item => pathIndexMap.has(item.path))
    .sort((a, b) => pathIndexMap.get(a.path) - pathIndexMap.get(b.path))
})

const goTo = (path) => {
  router.push(path)
}

const normalizeSelectedPaths = (paths) => {
  const allowedPaths = new Set(allShortcutOptions.value.map(item => item.path))
  const uniquePaths = []
  ;(paths || []).forEach((path) => {
    if (!allowedPaths.has(path) || uniquePaths.includes(path)) return
    if (uniquePaths.length >= 4) return
    uniquePaths.push(path)
  })
  return uniquePaths
}

const openShortcutDialog = () => {
  shortcutDraft.value = [...selectedShortcutPaths.value]
  shortcutDialogVisible.value = true
}

const openTodoDialog = () => {
  todoDialogVisible.value = true
}

const toggleShortcut = (path) => {
  if (shortcutDraft.value.includes(path)) {
    shortcutDraft.value = shortcutDraft.value.filter(item => item !== path)
    return
  }
  if (shortcutDraft.value.length >= 4) {
    ElMessage.warning('快捷入口最多只能添加 4 个')
    return
  }
  shortcutDraft.value = [...shortcutDraft.value, path]
}

const syncCurrentUser = (user) => {
  currentUser.value = user || {}
  setCurrentUser(user || {})
}

const loadShortcutSettings = async () => {
  const initialPaths = normalizeSelectedPaths(parseShortcutPaths(currentUser.value?.homeShortcuts))
  selectedShortcutPaths.value = initialPaths

  try {
    const res = await request.get('/user/homeShortcuts')
    if (res.code === '200' && res.data) {
      selectedShortcutPaths.value = normalizeSelectedPaths(res.data.selectedPaths || [])
      syncCurrentUser(res.data.user || currentUser.value)
      return
    }
  } catch (error) {
    console.error('加载快捷入口失败', error)
  }

  if (!initialPaths.length) {
    selectedShortcutPaths.value = normalizeSelectedPaths(allShortcutOptions.value.slice(0, 4).map(item => item.path))
  }
}

const saveShortcuts = async () => {
  try {
    savingShortcuts.value = true
    const selectedPaths = normalizeSelectedPaths(shortcutDraft.value)
    const res = await request.put('/user/homeShortcuts', { selectedPaths })
    if (res.code === '200' && res.data) {
      selectedShortcutPaths.value = normalizeSelectedPaths(res.data.selectedPaths || [])
      syncCurrentUser(res.data.user || currentUser.value)
      shortcutDialogVisible.value = false
      ElMessage.success('快捷入口已保存')
      return
    }
    ElMessage.error(res.msg || '保存失败')
  } catch (error) {
    console.error(error)
    ElMessage.error('保存快捷入口失败')
  } finally {
    savingShortcuts.value = false
  }
}

const loadHomeTodos = () => {
  if (!showTodoPanel.value) {
    homeTodo.value = {
      totalCount: 0,
      missingClaimCount: 0,
      missingVehicleCount: 0,
      items: [],
    }
    return
  }

  request.get('/user/homeTodos').then((res) => {
    if (res.code === '200' && res.data) {
      homeTodo.value = {
        totalCount: Number(res.data.totalCount || 0),
        missingClaimCount: Number(res.data.missingClaimCount || 0),
        missingVehicleCount: Number(res.data.missingVehicleCount || 0),
        items: Array.isArray(res.data.items) ? res.data.items : [],
      }
    }
  }).catch((error) => {
    console.error('加载首页待办失败', error)
  })
}

const loadStatistics = () => {
  request.get('/motorInsurance/overallStatistics').then((res) => {
    if (res.code === '200' && res.data) {
      statistics.value = res.data
    }
  }).catch((error) => {
    console.error('加载统计数据失败', error)
  })
}

onMounted(() => {
  loadStatistics()
  loadShortcutSettings()
  loadHomeTodos()
})
</script>

<style scoped>
.home-shell {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.home-hero {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 14px;
  padding: 18px 20px;
  background:
    radial-gradient(circle at top right, rgba(91, 143, 203, 0.16), transparent 28%),
    radial-gradient(circle at bottom left, rgba(47, 125, 107, 0.12), transparent 30%),
    linear-gradient(135deg, rgba(47, 125, 107, 0.12), rgba(255, 255, 255, 0.96) 45%);
}

.hero-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  padding-top: 6px;
}

.hero-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}

.hero-chip {
  display: inline-flex;
  align-items: center;
  padding: 7px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(95, 123, 114, 0.14);
  color: #5d736b;
  font-size: 13px;
  font-weight: 600;
}

.hero-title {
  margin: 0;
  font-size: 34px;
  line-height: 1.18;
  color: #20352e;
}

.todo-panel {
  margin-top: 14px;
  max-width: 720px;
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px 18px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(95, 123, 114, 0.14);
  box-shadow: 0 14px 30px rgba(48, 77, 67, 0.06);
  cursor: pointer;
  transition:
    transform 0.2s ease,
    border-color 0.2s ease,
    box-shadow 0.2s ease;
}

.todo-panel:hover,
.todo-panel:focus {
  transform: translateY(-1px);
  border-color: rgba(47, 125, 107, 0.24);
  box-shadow: 0 18px 34px rgba(48, 77, 67, 0.1);
  outline: none;
}

.todo-icon-wrap {
  width: 58px;
  height: 58px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(47, 125, 107, 0.18), rgba(91, 143, 203, 0.18));
  color: #2f7d6b;
  font-size: 28px;
}

.todo-body {
  flex: 1;
  min-width: 0;
}

.todo-head {
  display: flex;
  align-items: flex-start;
  justify-content: flex-start;
}

.todo-title {
  font-size: 18px;
  font-weight: 700;
  color: #24483d;
}

.todo-badge-row {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.todo-badge {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(248, 251, 249, 0.96);
  border: 1px solid rgba(95, 123, 114, 0.12);
  color: #4b625a;
  font-size: 12px;
  font-weight: 600;
}

.todo-badge-row-dialog {
  margin-top: 0;
  margin-bottom: 12px;
}

.todo-list {
  margin-top: 12px;
  max-height: 180px;
  overflow-y: auto;
  padding-right: 6px;
}

.todo-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px dashed rgba(95, 123, 114, 0.16);
}

.todo-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.todo-policy {
  color: #29433a;
  font-weight: 700;
}

.todo-missing {
  color: #8b5a2b;
  font-weight: 600;
  white-space: nowrap;
}

.todo-empty {
  margin-top: 14px;
  color: #6f837c;
  font-size: 13px;
}

.hero-side {
  width: 360px;
  flex-shrink: 0;
}

.hero-side-panel {
  height: 100%;
  padding: 14px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(95, 123, 114, 0.12);
  box-shadow: 0 14px 32px rgba(48, 77, 67, 0.08);
}

.hero-side-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.hero-side-label {
  color: #769088;
  font-size: 13px;
}

.hero-side-value {
  margin: 6px 0 0;
  font-size: 20px;
  font-weight: 700;
  color: #2b5c4f;
}

.hero-side-badge {
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(232, 243, 238, 0.98);
  color: #245548;
  font-size: 12px;
  font-weight: 700;
}

.hero-side-mosaic {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  grid-template-rows: repeat(2, minmax(74px, auto));
  gap: 10px;
}

.hero-side-item {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 6px;
  padding: 12px 14px;
  border-radius: 18px;
  background: rgba(244, 248, 245, 0.92);
  border: 1px solid rgba(95, 123, 114, 0.1);
  color: #61746d;
}

.hero-side-item span {
  font-size: 12px;
}

.hero-side-item strong {
  color: #24483d;
  font-size: 19px;
  line-height: 1.2;
  word-break: break-word;
}

.hero-side-item-primary {
  grid-column: 1 / 2;
  grid-row: 1 / 3;
  background: linear-gradient(135deg, rgba(47, 125, 107, 0.18), rgba(255, 255, 255, 0.94));
}

.hero-side-item-primary strong {
  font-size: 24px;
}

.hero-side-item-profit {
  grid-column: 2 / 3;
  grid-row: 1 / 2;
  background: linear-gradient(135deg, rgba(91, 143, 203, 0.16), rgba(255, 255, 255, 0.94));
}

.hero-side-item-policy {
  grid-column: 2 / 3;
  grid-row: 2 / 3;
  background: linear-gradient(135deg, rgba(124, 181, 139, 0.16), rgba(255, 255, 255, 0.94));
}

.feature-card {
  height: 100%;
}

.block-head {
  margin-bottom: 18px;
}

.block-head-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  flex-wrap: wrap;
}

.block-title {
  font-size: 20px;
  font-weight: 700;
  color: #233a33;
}

.shortcut-manage-btn {
  color: #245548;
  border-color: rgba(47, 125, 107, 0.22);
  background: rgba(232, 243, 238, 0.98);
}

.shortcut-manage-btn:hover,
.shortcut-manage-btn:focus {
  color: #173e34;
  border-color: rgba(47, 125, 107, 0.32);
  background: rgba(220, 237, 230, 1);
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.quick-entry {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  border: 1px solid rgba(95, 123, 114, 0.12);
  border-radius: 20px;
  background: rgba(248, 251, 249, 0.95);
  cursor: pointer;
  transition:
    transform 0.2s ease,
    border-color 0.2s ease,
    box-shadow 0.2s ease;
}

.quick-entry:hover {
  transform: translateY(-2px);
  border-color: rgba(47, 125, 107, 0.24);
  box-shadow: 0 14px 28px rgba(48, 77, 67, 0.08);
}

.quick-entry-icon {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border-radius: 16px;
  font-size: 22px;
  flex-shrink: 0;
}

.quick-entry-body {
  flex: 1;
  min-width: 0;
  text-align: left;
}

.quick-entry-title {
  font-size: 16px;
  font-weight: 700;
  color: #263e36;
}

.quick-entry-path {
  margin-top: 6px;
  color: #80928c;
  font-size: 12px;
}

.quick-entry-arrow {
  color: #2f7d6b;
  font-weight: 700;
  font-size: 13px;
}

.shortcut-dialog-tip {
  margin-bottom: 16px;
  color: #6d8179;
  font-size: 13px;
}

.shortcut-option-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.shortcut-option {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  border-radius: 20px;
  border: 1px solid rgba(95, 123, 114, 0.14);
  background: rgba(248, 251, 249, 0.96);
  cursor: pointer;
  transition:
    transform 0.2s ease,
    border-color 0.2s ease,
    box-shadow 0.2s ease;
}

.shortcut-option:hover {
  transform: translateY(-1px);
  border-color: rgba(47, 125, 107, 0.24);
  box-shadow: 0 12px 24px rgba(48, 77, 67, 0.08);
}

.shortcut-option-active {
  border-color: rgba(47, 125, 107, 0.34);
  background: rgba(234, 244, 239, 0.96);
}

.shortcut-option-icon {
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  border-radius: 16px;
  font-size: 21px;
  flex-shrink: 0;
}

.shortcut-option-body {
  flex: 1;
  min-width: 0;
  text-align: left;
}

.shortcut-option-title {
  font-size: 15px;
  font-weight: 700;
  color: #264037;
}

.shortcut-option-path {
  margin-top: 6px;
  color: #83958e;
  font-size: 12px;
}

.shortcut-option-check {
  color: #2f7d6b;
  font-size: 13px;
  font-weight: 700;
}

@media (max-width: 1180px) {
  .home-hero {
    flex-direction: column;
  }

  .hero-side {
    width: 100%;
  }
}

@media (max-width: 900px) {
  .hero-side-mosaic {
    grid-template-columns: 1fr;
    grid-template-rows: none;
  }

  .hero-side-item-primary,
  .hero-side-item-profit,
  .hero-side-item-policy {
    grid-column: auto;
    grid-row: auto;
  }

  .quick-grid,
  .shortcut-option-grid {
    grid-template-columns: 1fr;
  }

  .todo-panel,
  .todo-head,
  .todo-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .todo-missing {
    white-space: normal;
  }
}
</style>
