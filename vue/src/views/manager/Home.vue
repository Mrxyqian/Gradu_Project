<template>
  <div class="home-shell">
    <section class="card home-hero">
      <div class="hero-main">
        <div class="hero-chip-row">
          <span class="hero-chip">{{ todayLabel }}</span>
          <span class="hero-chip">{{ roleLabel }}</span>
        </div>
        <h1 class="hero-title">欢迎回来，{{ currentUser.name || '用户' }}</h1>
        <div class="hero-module-row">
          <span>保单管理</span>
          <span>理赔管理</span>
          <span>理赔率预测</span>
          <span v-if="currentUser.role === 'ADMIN'">模型训练</span>
        </div>
      </div>
      <div class="hero-side">
        <div class="hero-side-panel">
          <div class="hero-side-label">业务概览</div>
          <div class="hero-side-value">核心数据</div>
          <div class="hero-side-grid">
            <div class="hero-side-item">
              <span>总保费收入</span>
              <strong>{{ formatWanCurrency(statistics.totalPremium) }}</strong>
            </div>
            <div class="hero-side-item">
              <span>保费利润率</span>
              <strong>{{ formatPercent(statistics.premiumProfitRate) }}</strong>
            </div>
            <div class="hero-side-item">
              <span>本年度保单数量</span>
              <strong>{{ formatNumber(statistics.policyCount2018) }}</strong>
            </div>
            <div class="hero-side-item">
              <span>历史出险率</span>
              <strong>{{ formatHistoryRate(statistics.avgHistoryClaimRate) }}</strong>
            </div>
          </div>
        </div>
      </div>
    </section>

    <el-row :gutter="18">
      <el-col :xs="24" :xl="24">
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
      </el-col>
    </el-row>

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
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
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
const selectedShortcutPaths = ref([])
const shortcutDraft = ref([])
const shortcutDialogVisible = ref(false)
const savingShortcuts = ref(false)

const todayLabel = computed(() => {
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  }).format(new Date())
})

const roleLabel = computed(() => currentUser.value?.role === 'ADMIN' ? '管理员' : '普通用户')

const formatNumber = (value) => {
  const number = Number(value || 0)
  return number.toLocaleString('zh-CN')
}

const formatCurrency = (value) => `￥${formatNumber(value)}`
const formatWanCurrency = (value) => `￥${(Number(value || 0) / 10000).toFixed(1)} 万`
const formatPercent = (value) => `${(Number(value || 0) * 100).toFixed(2)}%`
const formatHistoryRate = (value) => `${Number(value || 0).toFixed(2)}`
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
      title: '保单统计',
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
      title: '理赔统计',
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
  gap: 24px;
  gap: 18px;
  padding: 22px 24px;
  background:
    radial-gradient(circle at top right, rgba(91, 143, 203, 0.16), transparent 28%),
    radial-gradient(circle at bottom left, rgba(47, 125, 107, 0.12), transparent 30%),
    linear-gradient(135deg, rgba(47, 125, 107, 0.12), rgba(255, 255, 255, 0.96) 45%);
}

.hero-main {
  flex: 1;
  min-width: 0;
}

.hero-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.hero-chip {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(95, 123, 114, 0.14);
  color: #5d736b;
  font-size: 12px;
  font-weight: 600;
}

.hero-title {
  margin: 0;
  font-size: 32px;
  line-height: 1.2;
  color: #20352e;
}

.hero-module-row {
  margin-top: 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.hero-module-row span {
  padding: 8px 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(95, 123, 114, 0.12);
  color: #3e544d;
  font-weight: 600;
  font-size: 13px;
}

.hero-side {
  width: 400px;
  flex-shrink: 0;
}

.hero-side-panel {
  height: 100%;
  padding: 16px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(95, 123, 114, 0.12);
  box-shadow: 0 14px 32px rgba(48, 77, 67, 0.08);
}

.hero-side-label {
  color: #769088;
  font-size: 12px;
}

.hero-side-value {
  margin: 6px 0 10px;
  font-size: 20px;
  font-weight: 700;
  color: #2b5c4f;
}

.hero-side-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.hero-side-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: space-between;
  gap: 5px;
  padding: 10px 12px;
  border-radius: 16px;
  background: rgba(244, 248, 245, 0.92);
  border: 1px solid rgba(95, 123, 114, 0.1);
  color: #61746d;
  min-height: 74px;
  line-height: 1.3;
}

.hero-side-item span {
  font-size: 12px;
}

.hero-side-item strong {
  color: #24483d;
  font-size: 17px;
  line-height: 1.2;
  word-break: break-word;
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

@media (max-width: 900px) {
  .home-hero {
    flex-direction: column;
  }

  .hero-side {
    width: 100%;
  }

  .hero-side-grid {
    grid-template-columns: 1fr;
  }

  .quick-grid {
    grid-template-columns: 1fr;
  }

  .shortcut-option-grid {
    grid-template-columns: 1fr;
  }
}
</style>
