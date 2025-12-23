import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'
import PublisherPage from '@/pages/PublisherPage.vue'

const routes = [
  {
    path: '/',
    component: MainLayout,
    children: [
      {
        path: '',
        name: 'Publisher',
        component: PublisherPage,
        meta: { title: '消息发布' }
      },
      {
        path: '/subscriber',
        name: 'Subscriber',
        component: () => import('@/pages/SubscriberPage.vue'),
        meta: { title: '消息订阅' }
      },
      {
        path: '/monitor',
        name: 'Monitor',
        component: () => import('@/pages/MonitorPage.vue'),
        meta: { title: '实时监控' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
