<template>
  <div class="publisher-page">
    <!-- 顶部状态卡片 -->
    <div class="status-cards">
      <StatusCard
        title="MQTT 状态"
        :value="mqttStatus"
        :status="isConnected ? 'online' : 'offline'"
        icon="🛰️"
      />
      <MiniCard
        title="已发布"
        :value="publishCount.toString()"
        :highlight="true"
      />
      <MiniCard
        title="数据文件"
        :value="`${totalRecords} 条`"
        :highlight="true"
      />
    </div>

    <!-- 连接配置面板 -->
    <div class="panel">
      <div class="panel-header">
        <span class="panel-icon">🔌</span>
        <span class="panel-title">连接配置</span>
      </div>
      <div class="panel-content">
        <div class="form-row">
          <label>Broker:</label>
          <input
            v-model="config.broker"
            type="text"
            placeholder="输入MQTT Broker地址"
            class="input-field"
          />
          <label style="margin-left: 20px;">端口:</label>
          <input
            v-model.number="config.port"
            type="number"
            min="1"
            max="65535"
            class="input-field port-input"
          />
          <button
            @click="connectBroker"
            :disabled="isConnected || isConnecting"
            class="btn btn-primary"
          >
            {{ isConnecting ? '连接中...' : (isConnected ? '🔗 已连接' : '🔗 连接') }}
          </button>
          <button
            @click="disconnectBroker"
            :disabled="!isConnected"
            class="btn btn-danger"
          >
            🔌 断开
          </button>
        </div>
      </div>
    </div>

    <!-- 传感器配置面板 -->
    <div class="panel">
      <div class="panel-header">
        <span class="panel-icon">📍</span>
        <span class="panel-title">传感器配置</span>
      </div>
      <div class="panel-content">
        <div class="form-row">
          <label>传感器ID:</label>
          <input
            v-model="sensorConfig.id"
            type="text"
            placeholder="例如: JX_Teach_01"
            class="input-field"
          />
          <label style="margin-left: 20px;">位置:</label>
          <input
            v-model="sensorConfig.location"
            type="text"
            placeholder="例如: 教学楼A"
            class="input-field"
          />
        </div>
        <div class="form-row" style="margin-top: 12px;">
          <label>备注:</label>
          <input
            v-model="sensorConfig.extra"
            type="text"
            placeholder="例如: 三楼301教室"
            class="input-field"
            style="flex: 1;"
          />
        </div>
      </div>
    </div>

    <!-- 发布控制面板 -->
    <div class="panel">
      <div class="panel-header">
        <span class="panel-icon">📁</span>
        <span class="panel-title">从文件发布数据</span>
      </div>
      <div class="panel-content">
        <div class="form-row">
          <label>发布间隔:</label>
          <input
            v-model.number="publishConfig.interval"
            type="number"
            min="0.01"
            max="10"
            step="0.1"
            class="input-field interval-input"
          />
          <span style="margin-left: 8px; color: #aaddff;">秒</span>
        </div>

        <!-- 发布进度信息 -->
        <div v-if="publishConfig.currentIndex > 0 && !isPublishing" class="info-message">
          📌 上次停止在第 {{ publishConfig.currentIndex }} 条，点击"开始发布"继续，或点击"重置"从头开始
        </div>
        
        <div v-if="isPublishing" class="progress-container">
          <div class="progress-bar">
            <div
              class="progress-fill"
              :style="{ width: publishProgress + '%' }"
            ></div>
          </div>
          <span class="progress-text">{{ publishProgress }}%</span>
        </div>

        <div class="button-row">
          <button
            @click="startPublish"
            :disabled="!isConnected || isPublishing"
            class="btn btn-success btn-large"
          >
            {{ publishConfig.currentIndex > 0 ? '▶️ 继续发布' : '🚀 开始发布' }}
          </button>
          <button
            @click="stopPublish"
            :disabled="!isPublishing"
            class="btn btn-danger btn-large"
          >
            ⏹ 停止发布
          </button>
          <button
            @click="resetPublish"
            :disabled="isPublishing || publishConfig.currentIndex === 0"
            class="btn btn-warning btn-large"
          >
            🔄 重置
          </button>
        </div>
      </div>
    </div>

    <!-- 发布日志 -->
    <div class="panel">
      <div class="panel-header">
        <span class="panel-icon">📝</span>
        <span class="panel-title">发布日志</span>
        <button @click="clearLog" class="btn-clear-log">清空日志</button>
      </div>
      <div class="panel-content">
        <div class="log-container" ref="logContainer">
          <div
            v-for="(log, index) in logs"
            :key="index"
            class="log-entry"
          >
            {{ log }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, nextTick, onMounted, onUnmounted } from 'vue'
import StatusCard from '@/components/StatusCard.vue'
import MiniCard from '@/components/MiniCard.vue'
import { publisherService } from '@/services/publisherService'

// 状态管理
const isConnected = ref(false)
const isConnecting = ref(false)
const isPublishing = ref(false)
const publishCount = ref(0)
const totalRecords = ref(0)
const logs = ref([])
const logContainer = ref(null)

// 配置
const config = reactive({
  broker: '192.168.1.10',
  port: 1883
})

const sensorConfig = reactive({
  id: 'JX_Teach_01',
  location: '教学楼A',
  extra: '三楼301教室'
})

const publishConfig = reactive({
  interval: 0.2,
  currentIndex: 0,
  totalCount: 0
})

// 计算属性
const mqttStatus = computed(() => {
  return isConnected.value ? '已连接' : '未连接'
})

const publishProgress = computed(() => {
  if (publishConfig.totalCount === 0) return 0
  return Math.round((publishConfig.currentIndex / publishConfig.totalCount) * 100)
})

// 方法
const addLog = (message) => {
  logs.value.push(`[${new Date().toLocaleTimeString()}] ${message}`)
  if (logs.value.length > 500) {
    logs.value.shift()
  }
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}

const clearLog = () => {
  logs.value = []
  addLog('日志已清空')
}

const connectBroker = async () => {
  if (!config.broker) {
    addLog('❌ Broker地址不能为空')
    return
  }

  isConnecting.value = true
  addLog(`⏳ 正在连接到 ${config.broker}:${config.port}...`)

  try {
    await publisherService.connect(config.broker, config.port)
    isConnected.value = true
    isConnecting.value = false
    addLog('✅ 连接成功')
    
    // 加载数据文件信息
    const info = await publisherService.getDataInfo()
    totalRecords.value = info.total_records || 0
  } catch (error) {
    isConnecting.value = false
    addLog(`❌ 连接失败: ${error.message}`)
  }
}

const disconnectBroker = () => {
  publisherService.disconnect()
  isConnected.value = false
  if (isPublishing.value) {
    stopPublish()
  }
  addLog('❌ 已断开连接')
}

const startPublish = async () => {
  try {
    const response = await publisherService.startPublish({
      interval: publishConfig.interval,
      sensor_id: sensorConfig.id,
      location: sensorConfig.location,
      extra: sensorConfig.extra
    })
    
    isPublishing.value = true
    publishConfig.totalCount = response.total_records
    
    // 使用后端返回的起始位置
    if (response.start_index > 0) {
      addLog(`▶️ 继续发布数据（从第 ${response.start_index + 1} 条开始，剩余 ${response.remaining} 条）`)
    } else {
      addLog(`🚀 开始从文件发布数据（间隔 ${publishConfig.interval}s，共 ${response.total_records} 条）`)
    }
    
    // 连接WebSocket接收发布进度
    publisherService.connectWebSocket((data) => {
      if (data.type === 'progress') {
        publishConfig.currentIndex = data.published
        publishCount.value = data.published
        
        if (data.current_message) {
          // current_message 现在是一个数组，包含三种类型的消息
          if (Array.isArray(data.current_message)) {
            // 显示所有三条消息
            data.current_message.forEach(msg => {
              addLog(`[${msg.timestamp}] ${msg.topic} → ${msg.type}: ${msg.value}`)
            })
          } else {
            // 兼容单条消息（手动发布的情况）
            const msg = data.current_message
            addLog(`[${msg.timestamp}] ${msg.topic} → ${msg.type}: ${msg.value}`)
          }
        }
      } else if (data.type === 'stopped') {
        // 手动停止（还有未发布的数据）
        isPublishing.value = false
        publishConfig.currentIndex = data.current_index || 0
       
      } else if (data.type === 'complete') {
        // 全部发布完成
        isPublishing.value = false
        publishConfig.currentIndex = 0
        addLog('✅ 所有数据发布完成')
      } else if (data.type === 'error') {
        isPublishing.value = false
        addLog(`❌ 发布错误: ${data.message}`)
      }
    })
  } catch (error) {
    addLog(`❌ 启动发布失败: ${error.message}`)
  }
}

const stopPublish = async () => {
  try {
    const response = await publisherService.stopPublish()
    isPublishing.value = false
    // 保存停止时的位置（从后端获取）
    if (response.current_index !== undefined) {
      publishConfig.currentIndex = response.current_index
      addLog(`⏹ 停止发布（已发布 ${publishCount.value} 条，停止在第 ${response.current_index} 条）`)
    } else {
      addLog('⏹ 停止发布')
    }
  } catch (error) {
    addLog(`❌ 停止发布失败: ${error.message}`)
  }
}

const resetPublish = async () => {
  try {
    await publisherService.resetPublish()
    publishConfig.currentIndex = 0
    publishConfig.totalCount = 0
    publishCount.value = 0
    addLog('🔄 发布进度已重置，下次将从头开始')
  } catch (error) {
    addLog(`❌ 重置失败: ${error.message}`)
  }
}

// 生命周期
onMounted(async () => {
  addLog('发布页面已加载')
  
  // 尝试获取数据文件信息
  try {
    const info = await publisherService.getDataInfo()
    totalRecords.value = info.total_records || 0
  } catch (error) {
    console.error('Failed to load data info:', error)
  }
})

onUnmounted(() => {
  if (isConnected.value) {
    publisherService.disconnect()
  }
})
</script>

<style scoped>
.publisher-page {
  max-width: 1400px;
  margin: 0 auto;
}

/* 状态卡片 */
.status-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

/* 面板样式 */
.panel {
  background: rgba(10, 40, 70, 0.6);
  border: 1px solid rgba(100, 180, 255, 0.2);
  border-radius: 12px;
  margin-bottom: 20px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  transition: all 0.3s;
}

.panel:hover {
  border-color: rgba(100, 180, 255, 0.3);
  box-shadow: 0 6px 16px rgba(60, 197, 255, 0.15);
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 15px 20px;
  background: linear-gradient(135deg, rgba(20, 50, 90, 0.8) 0%, rgba(30, 60, 100, 0.8) 100%);
  border-bottom: 1px solid rgba(100, 180, 255, 0.2);
}

.panel-icon {
  font-size: 20px;
  filter: drop-shadow(0 0 6px rgba(124, 231, 255, 0.4));
}

.panel-title {
  font-size: 16px;
  font-weight: 600;
  color: #7ce7ff;
  text-shadow: 0 0 8px rgba(124, 231, 255, 0.3);
  flex: 1;
}

.btn-clear-log {
  padding: 6px 14px;
  background: rgba(255, 100, 100, 0.2);
  border: 1px solid rgba(255, 100, 100, 0.3);
  border-radius: 6px;
  color: #ff9999;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-clear-log:hover {
  background: rgba(255, 100, 100, 0.3);
  border-color: rgba(255, 100, 100, 0.5);
}

.panel-content {
  padding: 20px;
}

/* 表单行 */
.form-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.form-row label {
  min-width: 80px;
  color: #aaddff;
  font-size: 13px;
  font-weight: 500;
}

.input-field {
  flex: 1;
  padding: 10px 14px;
  background: rgba(10, 30, 60, 0.6);
  border: 1px solid rgba(100, 180, 255, 0.2);
  border-radius: 8px;
  color: #e0e0e0;
  font-size: 13px;
  transition: all 0.3s;
}

.input-field:focus {
  outline: none;
  border-color: rgba(124, 231, 255, 0.5);
  box-shadow: 0 0 12px rgba(124, 231, 255, 0.25);
}

.port-input {
  max-width: 100px;
  flex: none;
}

.interval-input {
  max-width: 120px;
  flex: none;
}

/* 按钮样式 */
.btn {
  padding: 10px 20px;
  border: 2px solid;
  border-radius: 10px;
  font-size: 13px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s;
  white-space: nowrap;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  color: #0c1729;
  background: linear-gradient(135deg, #7ce7ff 0%, #3cc5ff 100%);
  border-color: #4fd4ff;
}

.btn-primary:hover:not(:disabled) {
  background: linear-gradient(135deg, #9bf0ff 0%, #56d6ff 100%);
  border-color: #7ce7ff;
  box-shadow: 0 4px 12px rgba(124, 231, 255, 0.3);
}

.btn-danger {
  color: #ffecec;
  background: linear-gradient(135deg, #ff6b6b 0%, #d83c3c 100%);
  border-color: #ff8a8a;
}

.btn-danger:hover:not(:disabled) {
  background: linear-gradient(135deg, #ff8a8a 0%, #e34f4f 100%);
  border-color: #ffc1c1;
  box-shadow: 0 4px 12px rgba(255, 107, 107, 0.3);
}

.btn-warning {
  color: #fff9ec;
  background: linear-gradient(135deg, #ffa500 0%, #ff8c00 100%);
  border-color: #ffb733;
}

.btn-warning:hover:not(:disabled) {
  background: linear-gradient(135deg, #ffb733 0%, #ffa500 100%);
  border-color: #ffd966;
  box-shadow: 0 4px 12px rgba(255, 165, 0, 0.3);
}

.info-message {
  margin: 15px 0;
  padding: 12px 16px;
  background: rgba(124, 231, 255, 0.1);
  border: 1px solid rgba(124, 231, 255, 0.3);
  border-radius: 8px;
  color: #7ce7ff;
  font-size: 14px;
  line-height: 1.6;
}

.btn-success {
  color: #0b1a2a;
  background: linear-gradient(135deg, #8df5c5 0%, #3ddf9e 100%);
  border-color: #6ce6b4;
}

.btn-success:hover:not(:disabled) {
  background: linear-gradient(135deg, #adf9d6 0%, #5aecb4 100%);
  border-color: #9cf7d0;
  box-shadow: 0 4px 12px rgba(61, 223, 158, 0.3);
}

.btn-info {
  color: #e8f3ff;
  background: linear-gradient(135deg, #3aa0ff 0%, #1f6fff 100%);
  border-color: #5ab3ff;
}

.btn-info:hover:not(:disabled) {
  background: linear-gradient(135deg, #62b6ff 0%, #3685ff 100%);
  border-color: #8dcaff;
  box-shadow: 0 4px 12px rgba(58, 160, 255, 0.3);
}

.btn-large {
  padding: 14px 24px;
  font-size: 14px;
  border-radius: 12px;
}

/* 控制面板行 */
.button-row {
  display: flex;
  gap: 12px;
  margin-top: 15px;
}

.button-row .btn {
  flex: 1;
}

/* 进度条 */
.progress-container {
  margin: 15px 0;
  display: flex;
  align-items: center;
  gap: 12px;
}

.progress-bar {
  flex: 1;
  height: 24px;
  background: rgba(10, 30, 60, 0.8);
  border: 1px solid rgba(100, 180, 255, 0.2);
  border-radius: 12px;
  overflow: hidden;
  position: relative;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #00a0cc 0%, #00d4ff 100%);
  border-radius: 12px;
  transition: width 0.3s;
  box-shadow: 0 0 12px rgba(0, 212, 255, 0.5);
}

.progress-text {
  min-width: 50px;
  color: #7ce7ff;
  font-weight: bold;
  font-size: 14px;
  text-align: right;
}

/* 日志容器 */
.log-container {
  height: 200px;
  overflow-y: auto;
  background: rgba(10, 30, 50, 0.8);
  border: 1px solid rgba(100, 180, 255, 0.2);
  border-radius: 8px;
  padding: 12px;
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.6;
}

.log-entry {
  color: #aaddff;
  margin-bottom: 4px;
  word-break: break-word;
}

.log-container::-webkit-scrollbar {
  width: 8px;
}

.log-container::-webkit-scrollbar-track {
  background: rgba(10, 30, 60, 0.5);
  border-radius: 4px;
}

.log-container::-webkit-scrollbar-thumb {
  background: rgba(100, 180, 255, 0.3);
  border-radius: 4px;
}

.log-container::-webkit-scrollbar-thumb:hover {
  background: rgba(100, 180, 255, 0.5);
}
</style>
