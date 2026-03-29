import {createRouter, createWebHistory} from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'Manager',
      component: () => import('@/views/Manager.vue'),
      redirect: '/home',
      children: [
        { path: 'home', name: 'Home', component: () => import('@/views/manager/Home.vue')},
        { path: 'motorInsurance', name: 'MotorInsurance', component: () => import('@/views/manager/MotorInsurance.vue')},
        { path: 'motorInsuranceStatistics', name: 'MotorInsuranceStatistics', component: () => import('@/views/manager/MotorInsuranceStatistics.vue')},
        { path: 'claimTypes', name: 'ClaimTypes', component: () => import('@/views/manager/ClaimTypes.vue')},
        { path: 'claimStatistics', name: 'ClaimStatistics', component: () => import('@/views/manager/ClaimStatistics.vue')},
        { path: 'vehicleInfo', name: 'VehicleInfo', component: () => import('@/views/manager/VehicleInfo.vue')},
      ]
    },
  ]
})

export default router
