<template>
  <div class="main-layout">
    <!-- 顶部导航栏 -->
    <header class="top-navbar">
      <div class="navbar-left">
        <div class="logo">
          <span class="logo-icon">🌡️</span>
          <span class="logo-text">小嘉智能环境监控系统</span>
        </div>
      </div>
      <div class="navbar-center">
        <h2 class="page-title">{{ currentPageTitle }}</h2>
      </div>
      <div class="navbar-right">
        <div class="status-indicator" :class="{ online: isOnline }">
          <span class="status-dot"></span>
          <span>{{ isOnline ? '在线' : '离线' }}</span>
        </div>
        <div class="user-info">
          <span class="user-icon">👤</span>
          <span class="username">管理员</span>
        </div>
      </div>
    </header>

    <!-- 主内容区域 -->
    <div class="main-content">
      <!-- 左侧侧边栏 -->
      <aside class="sidebar">
        <nav class="sidebar-nav">
          <router-link
            v-for="item in menuItems"
            :key="item.path"
            :to="item.path"
            class="nav-item"
            :class="{ active: $route.path === item.path }"
          >
            <span class="nav-icon">{{ item.icon }}</span>
            <span class="nav-text">{{ item.title }}</span>
          </router-link>
        </nav>
        
        <div class="sidebar-footer">
          <div class="version-info">
            <span>版本 1.0.0</span>
          </div>
        </div>
      </aside>

      <!-- 页面内容区域 -->
      <main class="page-content">
        <router-view v-slot="{ Component }">
          <!-- 仅缓存订阅页：避免切换页面时断开订阅端连接 -->
          <keep-alive include="SubscriberPage">
            <component :is="Component" />
          </keep-alive>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const menuItems = ref([
  { path: '/', title: '消息发布', icon: '📤' },
  { path: '/subscriber', title: '消息订阅', icon: '📥' },
  { path: '/monitor', title: '实时监控', icon: '📊' }
])

const isOnline = ref(true)

const currentPageTitle = computed(() => {
  return route.meta.title || '消息发布'
})
</script>

<style scoped>
.main-layout {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 顶部导航栏 */
.top-navbar {
  height: 70px;
  background: linear-gradient(135deg, rgba(10, 30, 60, 0.95) 0%, rgba(20, 50, 80, 0.95) 100%);
  border-bottom: 2px solid rgba(100, 180, 255, 0.3);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 30px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(10px);
}

.navbar-left {
  flex: 1;
  display: flex;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 20px;
  font-weight: bold;
}

.logo-icon {
  font-size: 28px;
  filter: drop-shadow(0 0 8px rgba(124, 231, 255, 0.6));
}

.logo-text {
  color: #7ce7ff;
  text-shadow: 0 0 10px rgba(124, 231, 255, 0.5);
  letter-spacing: 1px;
}

.navbar-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.page-title {
  color: #aaddff;
  font-size: 22px;
  font-weight: 600;
  text-shadow: 0 2px 8px rgba(170, 221, 255, 0.3);
}

.navbar-right {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 20px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(10, 30, 50, 0.6);
  border: 1px solid rgba(255, 100, 100, 0.3);
  border-radius: 20px;
  font-size: 13px;
  color: #ff9999;
  transition: all 0.3s;
}

.status-indicator.online {
  border-color: rgba(100, 255, 150, 0.3);
  color: #8df5c5;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ff5555;
  box-shadow: 0 0 8px rgba(255, 85, 85, 0.6);
  animation: pulse-offline 2s infinite;
}

.status-indicator.online .status-dot {
  background: #3ddf9e;
  box-shadow: 0 0 8px rgba(61, 223, 158, 0.6);
  animation: pulse-online 2s infinite;
}

@keyframes pulse-online {
  0%, 100% {
    box-shadow: 0 0 8px rgba(61, 223, 158, 0.6);
  }
  50% {
    box-shadow: 0 0 15px rgba(61, 223, 158, 0.9);
  }
}

@keyframes pulse-offline {
  0%, 100% {
    box-shadow: 0 0 8px rgba(255, 85, 85, 0.6);
  }
  50% {
    box-shadow: 0 0 15px rgba(255, 85, 85, 0.9);
  }
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(10, 30, 50, 0.6);
  border: 1px solid rgba(100, 180, 255, 0.2);
  border-radius: 20px;
  color: #aaddff;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s;
}

.user-info:hover {
  border-color: rgba(100, 180, 255, 0.4);
  background: rgba(20, 40, 70, 0.8);
  box-shadow: 0 0 10px rgba(100, 180, 255, 0.2);
}

.user-icon {
  font-size: 18px;
}

/* 主内容区域 */
.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* 左侧侧边栏 */
.sidebar {
  width: 220px;
  background: linear-gradient(180deg, rgba(10, 30, 60, 0.8) 0%, rgba(15, 40, 70, 0.8) 100%);
  border-right: 2px solid rgba(100, 180, 255, 0.2);
  display: flex;
  flex-direction: column;
  padding: 20px 0;
  box-shadow: 4px 0 12px rgba(0, 0, 0, 0.2);
}

.sidebar-nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0 15px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  background: rgba(10, 30, 50, 0.4);
  border: 1px solid rgba(100, 180, 255, 0.15);
  border-radius: 10px;
  color: #aaddff;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s;
  cursor: pointer;
}

.nav-item:hover {
  background: rgba(20, 50, 90, 0.6);
  border-color: rgba(100, 180, 255, 0.3);
  transform: translateX(5px);
  box-shadow: 0 4px 12px rgba(60, 197, 255, 0.2);
}

.nav-item.active {
  background: linear-gradient(135deg, rgba(60, 197, 255, 0.25) 0%, rgba(31, 111, 255, 0.25) 100%);
  border-color: rgba(124, 231, 255, 0.5);
  color: #7ce7ff;
  box-shadow: 0 4px 15px rgba(60, 197, 255, 0.3);
}

.nav-icon {
  font-size: 20px;
  filter: drop-shadow(0 0 4px rgba(124, 231, 255, 0.3));
}

.nav-text {
  letter-spacing: 0.5px;
}

.sidebar-footer {
  padding: 15px;
  border-top: 1px solid rgba(100, 180, 255, 0.15);
  margin-top: 20px;
}

.version-info {
  text-align: center;
  color: #6f8fa8;
  font-size: 12px;
}

/* 页面内容区域 */
.page-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: linear-gradient(135deg, rgba(10, 25, 41, 0.5) 0%, rgba(26, 47, 74, 0.5) 100%);
}

/* 滚动条样式 */
.page-content::-webkit-scrollbar {
  width: 8px;
}

.page-content::-webkit-scrollbar-track {
  background: rgba(10, 30, 60, 0.3);
}

.page-content::-webkit-scrollbar-thumb {
  background: rgba(100, 180, 255, 0.3);
  border-radius: 4px;
}

.page-content::-webkit-scrollbar-thumb:hover {
  background: rgba(100, 180, 255, 0.5);
}
</style>
