<template>
  <div class="mini-card" :class="{ highlight }">
    <div class="mini-title">{{ title }}</div>
    <div class="mini-value">{{ value }}</div>
  </div>
</template>

<script setup>
defineProps({
  title: String,
  value: String,
  highlight: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.mini-card {
  padding: 20px;
  background: rgba(10, 40, 70, 0.6);
  border: 2px solid rgba(100, 180, 255, 0.2);
  border-radius: 12px;
  text-align: center;
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
}

.mini-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, transparent, rgba(100, 180, 255, 0.5), transparent);
  opacity: 0;
  transition: opacity 0.3s;
}

.mini-card:hover {
  border-color: rgba(100, 180, 255, 0.4);
  box-shadow: 0 6px 16px rgba(60, 197, 255, 0.2);
  transform: translateY(-3px);
}

.mini-card:hover::before {
  opacity: 1;
}

.mini-card.highlight {
  border-color: rgba(124, 231, 255, 0.3);
}

.mini-title {
  font-size: 13px;
  color: #aaddff;
  margin-bottom: 8px;
  font-weight: 500;
}

.mini-value {
  font-size: 24px;
  font-weight: bold;
  color: #7ce7ff;
  text-shadow: 0 0 10px rgba(124, 231, 255, 0.3);
}
</style>
