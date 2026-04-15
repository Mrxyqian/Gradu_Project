import { createRouter, createWebHistory } from 'vue-router'
import { getCurrentUser } from '@/utils/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/login',
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue'),
    },
    {
      path: '/manager',
      name: 'Manager',
      component: () => import('@/views/MainLayout.vue'),
      redirect: '/home',
      children: [
        { path: '/home', name: 'Home', component: () => import('@/views/manager/Home.vue') },
        { path: '/motorInsurance', name: 'MotorInsurance', component: () => import('@/views/manager/MotorInsurance.vue') },
        { path: '/motorInsuranceStatistics', name: 'MotorInsuranceStatistics', component: () => import('@/views/manager/BusinessAnalytics.vue'), meta: { analyticsSubject: 'policy' } },
        { path: '/claimTypes', name: 'ClaimTypes', component: () => import('@/views/manager/ClaimTypes.vue') },
        { path: '/claimStatistics', name: 'ClaimStatistics', component: () => import('@/views/manager/BusinessAnalytics.vue'), meta: { analyticsSubject: 'claim' } },
        { path: '/vehicleInfo', name: 'VehicleInfo', component: () => import('@/views/manager/VehicleInfo.vue') },
        { path: '/predictionManage', name: 'PredictionManage', component: () => import('@/views/manager/PredictionManage.vue') },
        { path: '/predictionStatistics', name: 'PredictionStatistics', component: () => import('@/views/manager/PredictionStatistics.vue') },
        { path: '/modelTraining', name: 'ModelTraining', component: () => import('@/views/manager/ModelTraining.vue'), meta: { adminOnly: true } },
        { path: '/modelTraining/result/:jobId', name: 'ModelTrainingResult', component: () => import('@/views/manager/ModelTrainingResult.vue'), meta: { adminOnly: true } },
        { path: '/userManage', name: 'UserManage', component: () => import('@/views/manager/UserManage.vue'), meta: { adminOnly: true } },
      ]
    },
  ]
})

router.beforeEach((to, from, next) => {
  const user = getCurrentUser()
  const isLoginPage = to.path === '/login'
  const hasLogin = !!user.employeeNo

  if (!hasLogin && !isLoginPage) {
    next('/login')
    return
  }

  if (hasLogin && isLoginPage) {
    next('/home')
    return
  }

  if (to.meta.adminOnly && user.role !== 'ADMIN') {
    next('/home')
    return
  }

  next()
})

export default router
