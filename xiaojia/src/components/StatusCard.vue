<template>
  <div class="status-card" :class="statusClass">
    <div class="card-icon">{{ icon }}</div>
    <div class="card-content">
      <div class="card-title">{{ title }}</div>
      <div class="card-value">{{ value }}</div>
    </div>
    <div class="status-indicator" :class="status"></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: String,
  value: String,
  status: {
    type: String,
    default: 'offline'
  },
  icon: {
    type: String,
    default: '📊'
  }
})

const statusClass = computed(() => {
  return `status-${props.status}`
})
</script>

<style scoped>
.status-card {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 20px;
  background: rgba(10, 40, 70, 0.6);
  border: 2px solid rgba(100, 180, 255, 0.2);
  border-radius: 12px;
  position: relative;
  transition: all 0.3s;
  overflow: hidden;
}

.status-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, transparent, rgba(100, 180, 255, 0.5), transparent);
  opacity: 0;
  transition: opacity 0.3s;
}

.status-card:hover {
  border-color: rgba(100, 180, 255, 0.4);
  box-shadow: 0 6px 16px rgba(60, 197, 255, 0.2);
}

.status-card:hover::before {
  opacity: 1;
}

.card-icon {
  font-size: 36px;
  filter: drop-shadow(0 0 8px rgba(124, 231, 255, 0.4));
}

.card-content {
  flex: 1;
}

.card-title {
  font-size: 13px;
  color: #aaddff;
  margin-bottom: 6px;
  font-weight: 500;
}

.card-value {
  font-size: 20px;
  font-weight: bold;
  color: #7ce7ff;
  text-shadow: 0 0 8px rgba(124, 231, 255, 0.3);
}

.status-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  position: absolute;
  top: 15px;
  right: 15px;
}

.status-indicator.online {
  background: #3ddf9e;
  box-shadow: 0 0 10px rgba(61, 223, 158, 0.6);
  animation: pulse-online 2s infinite;
}

.status-indicator.offline {
  background: #ff5555;
  box-shadow: 0 0 10px rgba(255, 85, 85, 0.6);
  animation: pulse-offline 2s infinite;
}

@keyframes pulse-online {
  0%, 100% {
    box-shadow: 0 0 10px rgba(61, 223, 158, 0.6);
  }
  50% {
    box-shadow: 0 0 20px rgba(61, 223, 158, 0.9);
  }
}

@keyframes pulse-offline {
  0%, 100% {
    box-shadow: 0 0 10px rgba(255, 85, 85, 0.6);
  }
  50% {
    box-shadow: 0 0 20px rgba(255, 85, 85, 0.9);
  }
}
</style>
