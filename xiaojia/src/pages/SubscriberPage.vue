<template>
  <div class="subscriber-page">
    <!-- 顶部状态卡 -->
    <div class="status-cards">
      <StatusCard
        title="实时订阅（Broker WS）"
        :value="mqttWsStatusText"
        :status="mqttWsConnected ? 'online' : 'offline'"
        icon="📡"
      />
      <MiniCard title="已处理" :value="processedCount.toString()" :highlight="true" />
      <MiniCard title="订阅主题数" :value="selectedTypes.length.toString()" :highlight="true" />
    </div>

    <!-- 实时订阅（参照 modify.md：前端 mqtt.js 通过 9001 直连 Broker） -->
    <div class="panel">
      <div class="panel-header">
        <span class="panel-icon">🔌</span>
        <span class="panel-title">实时连接（前端 → Broker:9001 WebSocket）</span>
      </div>
      <div class="panel-content">
        <div class="form-row">
          <label>Broker WS:</label>
          <input v-model="mqttWs.url" type="text" class="input-field" placeholder="ws://118.31.63.5:9001/mqtt" />
          <button class="btn btn-primary" @click="connectMqttWs" :disabled="mqttWsConnected || mqttWsConnecting">
            {{ mqttWsConnecting ? '连接中...' : (mqttWsConnected ? '🔒 已连接' : '🔗 连接') }}
          </button>
          <button class="btn btn-danger" @click="disconnectMqttWs" :disabled="!mqttWsConnected">🔌 断开</button>
        </div>
        <div class="hint" style="margin-top: 10px;">
          说明：此处走 MQTT over WebSocket（9001）。发布端/后端处理仍走 TCP 1883。
        </div>
      </div>
    </div>

    <!-- 订阅控制（参照 finalproject：温/湿/压复选） -->
    <div class="panel">
      <div class="panel-header">
        <span class="panel-icon">🧩</span>
        <span class="panel-title">订阅控制</span>
      </div>
      <div class="panel-content">
        <div class="chip-row">
          <label class="chip">
            <input type="checkbox" value="temperature" v-model="selectedTypes" />
            <span>🌡️ 温度</span>
          </label>
          <label class="chip">
            <input type="checkbox" value="humidity" v-model="selectedTypes" />
            <span>💧 湿度</span>
          </label>
          <label class="chip">
            <input type="checkbox" value="pressure" v-model="selectedTypes" />
            <span>📊 气压</span>
          </label>

          <button class="btn btn-success" @click="applyMqttSubscriptions" :disabled="!mqttWsConnected">
            ✅ 应用订阅（实时）
          </button>
          <button class="btn btn-secondary" @click="updateSubscription" :disabled="!backendConnected">
            📥 同步给后端（存储/分析）
          </button>
          <button class="btn btn-warning" @click="clearData">
            🧹 清空数据
          </button>
        </div>

        <div class="sub-list">
          <div class="sub-title">当前订阅：</div>
          <div class="sub-items">
            <span v-if="subscribedTypes.length === 0" class="sub-empty">（无）</span>
            <span v-for="t in subscribedTypes" :key="t" class="sub-item">{{ t }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 地图 + 小嘉 + 位置（参照 finalproject 布局） -->
    <div class="panel">
      <div class="panel-header">
        <span class="panel-icon">🗺️</span>
        <span class="panel-title">位置服务与播报</span>
      </div>
      <div class="panel-content">
        <div class="map-row">
          <div class="map-panel">
            <div class="map-header">
              <span>传感器地图</span>
              <div class="map-controls">
                <label>位置：</label>
                <select v-model="selectedBuilding" class="select-field">
                  <option v-for="b in buildings" :key="b" :value="b">{{ b }}</option>
                </select>
              </div>
            </div>

            <div class="map-container">
              <img class="map-image" :src="mapUrl" alt="map" @error="mapMissing = true" v-if="!mapMissing" />
              <div v-else class="map-missing">
                <div>未找到地图文件</div>
                <div class="small">请将地图放到：<code>xiaojia/public/map.png</code></div>
              </div>
              <div v-if="!mapMissing" class="marker" :class="markerStatus" :style="markerStyle">
                <div class="marker-dot"></div>
                <div class="marker-label">{{ selectedBuilding }}</div>
              </div>
            </div>
          </div>

          <div class="right-panel">
            <div class="card-box">
              <div class="box-title">📍 传感器位置</div>
              <div class="box-body">
                <div>Sensor: <b>{{ sensorId }}</b></div>
                <div>位置: <b>{{ selectedBuilding }}</b></div>
                <div>备注: <b>{{ locationExtra }}</b></div>
              </div>
            </div>

            <div class="card-box" style="margin-top: 12px;">
              <div class="box-title">🤖 小嘉播报</div>
              <div class="box-body">
                <div class="xiaojia-mood">{{ xiaojiaMoodText }}</div>
                <div class="xiaojia-tip">{{ xiaojiaTip }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 三类数据面板 -->
    <div class="sensor-panels">
      <div class="sensor-panel" v-for="t in sensorTypes" :key="t.key">
        <div class="sensor-header">
          <div class="sensor-title">{{ t.icon }} {{ t.title }}</div>
        <div class="sensor-meta">
          <span class="meta-item">最新值：<b>{{ formatValue(currentValues[t.key], t.unit) }}</b></span>
          <span class="meta-item">更新时间：<b>{{ lastUpdated[t.key] || '--' }}</b></span>
          <button class="btn btn-secondary btn-small" @click="loadLatest(t.key)" :disabled="loadingLatest[t.key]">
            {{ loadingLatest[t.key] ? '加载中...' : '拉取历史(最新100)' }}
          </button>
        </div>
        </div>

        <div class="sparkline">
          <svg :viewBox="`0 0 ${sparkW} ${sparkH}`" preserveAspectRatio="none">
            <polyline
              :points="sparkPoints(history[t.key])"
              fill="none"
              stroke="rgba(124,231,255,0.9)"
              stroke-width="2"
            />
          </svg>
        </div>
      </div>
    </div>

    <!-- 日志 -->
    <div class="panel">
      <div class="panel-header">
        <span class="panel-icon">📝</span>
        <span class="panel-title">接收日志（最近 {{ logs.length }} 条）</span>
        <button class="btn-clear-log" @click="logs = []">清空日志</button>
      </div>
      <div class="panel-content">
        <div class="log-container">
          <div v-for="(l, idx) in logs" :key="idx" class="log-entry">{{ l }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import MiniCard from '@/components/MiniCard.vue'
import StatusCard from '@/components/StatusCard.vue'
import { subscriberService } from '@/services/subscriberService'
import { useSharedSensorData } from '@/composables/useSharedSensorData'
import mqtt from 'mqtt'

defineOptions({ name: 'SubscriberPage' })

// ========= 共享数据服务 =========
const sharedData = useSharedSensorData()

// ========= 基础配置 =========
const backendApiBase = ref('http://localhost:8002')
const connecting = ref(false)
const backendConnected = ref(false)
const wsConnected = ref(false)

const mqttConfig = reactive({
  broker: '118.31.63.5',
  port: 1883
})

const subscribedTypes = ref([])
const selectedTypes = ref(['temperature', 'humidity', 'pressure'])

// ========= 前端直连 Broker WebSocket（9001）=========
const mqttWs = reactive({
  url: 'ws://118.31.63.5:9001/mqtt',
})
const mqttWsClient = ref(null)
const mqttWsConnected = ref(false)
const mqttWsConnecting = ref(false)
const mqttWsStatusText = computed(() => (mqttWsConnected.value ? '已连接' : '未连接'))

// ========= 地图（参照 finalproject 的教学楼 A-H 坐标；后端数据不带 location 时，允许手动切换）=========
const mapUrl = '/map.png'
const mapMissing = ref(false)
const buildings = ['教学楼A', '教学楼B', '教学楼C', '教学楼D', '教学楼E', '教学楼F', '教学楼G', '教学楼H']
const selectedBuilding = ref('教学楼A')

const buildingPoints = {
  教学楼A: { x: 0.495, y: 0.481 },
  教学楼B: { x: 0.516, y: 0.432 },
  教学楼C: { x: 0.534, y: 0.391 },
  教学楼D: { x: 0.584, y: 0.558 },
  教学楼E: { x: 0.633, y: 0.598 },
  教学楼F: { x: 0.609, y: 0.509 },
  教学楼G: { x: 0.665, y: 0.55 },
  教学楼H: { x: 0.679, y: 0.516 }
}

const markerStatus = ref('normal')
const markerStyle = computed(() => {
  const p = buildingPoints[selectedBuilding.value] || { x: 0.5, y: 0.5 }
  return {
    left: `${p.x * 100}%`,
    top: `${p.y * 100}%`
  }
})

// ========= 小嘉播报 =========
const sensorId = ref('JX_Teach_01')
const locationExtra = ref('实时：Broker 9001（mqtt.js）；历史：后端API（可选）')
const xiaojiaMood = ref('normal')
const xiaojiaTip = ref('等待订阅数据...')

const xiaojiaMoodText = computed(() => {
  const map = {
    normal: '🙂 状态正常',
    hot: '🥵 温度偏高',
    cold: '🥶 温度偏低',
    humid: '🌧️ 湿度偏高',
    lowp: '⚠️ 气压偏低',
    highp: '⚠️ 气压偏高'
  }
  return map[xiaojiaMood.value] || '🙂 状态正常'
})

// ========= 数据 =========
const sensorTypes = [
  { key: 'temperature', title: '温度', icon: '🌡️', unit: '°C' },
  { key: 'humidity', title: '湿度', icon: '💧', unit: '%' },
  { key: 'pressure', title: '气压', icon: '📊', unit: 'hPa' }
]

const currentValues = reactive({
  temperature: null,
  humidity: null,
  pressure: null
})

const lastUpdated = reactive({
  temperature: null,
  humidity: null,
  pressure: null
})

const history = reactive({
  temperature: [],
  humidity: [],
  pressure: []
})

const loadingLatest = reactive({
  temperature: false,
  humidity: false,
  pressure: false
})

const logs = ref([])
const sparkW = 300
const sparkH = 80

// 仅统计“前端已处理”的条数（节流后每 0.2s 最多处理 1 条）
const processedCount = ref(0)

const statistics = ref({ temperature: 0, humidity: 0, pressure: 0 })

const backendWsUrl = computed(() => backendApiBase.value.replace(/^http/, 'ws') + '/ws/data')

function addLog(msg) {
  const line = `[${new Date().toLocaleTimeString()}] ${msg}`
  logs.value.push(line)
  if (logs.value.length > 200) logs.value.shift()
}

// ========= 前端处理节流（每 0.2 秒处理 1 条）=========
const THROTTLE_MS = 200
const incomingQueue = ref([])
let throttleTimer = null

function enqueueIncoming(item) {
  incomingQueue.value.push(item)
  // 防止队列无限增长：超过阈值丢弃较旧的数据
  if (incomingQueue.value.length > 2000) {
    incomingQueue.value.splice(0, incomingQueue.value.length - 500)
  }
}

function processOne(item) {
  const { topic, sensorType, value, timestamp } = item

  if (sensorType in currentValues) {
    currentValues[sensorType] = value
    lastUpdated[sensorType] = (timestamp || '').replace('T', ' ').slice(0, 19)

    const n = Number(value)
    if (Number.isFinite(n)) {
      history[sensorType].push({ t: timestamp, v: n })
      if (history[sensorType].length > 60) history[sensorType].shift()
    }

    // 同步到共享数据服务
    sharedData.updateSensorData(sensorType, value, timestamp)

    // 本地统计（按前端处理条数统计）
    statistics.value = {
      ...statistics.value,
      [sensorType]: (statistics.value[sensorType] || 0) + 1
    }
    processedCount.value += 1

    updateXiaojia(sensorType, value)
    addLog(`📥 ${topic} = ${value}`)
  }
}

function startThrottle() {
  if (throttleTimer) return
  throttleTimer = setInterval(() => {
    if (incomingQueue.value.length === 0) return
    const item = incomingQueue.value.shift()
    if (item) processOne(item)
  }, THROTTLE_MS)
}

function stopThrottle() {
  if (throttleTimer) {
    clearInterval(throttleTimer)
    throttleTimer = null
  }
}

function applyBackendApi() {
  subscriberService.setApiBaseUrl(backendApiBase.value)
  addLog(`✅ 已设置订阅后端：${backendApiBase.value}`)
}

async function connectBroker() {
  connecting.value = true
  try {
    subscriberService.setApiBaseUrl(backendApiBase.value)
    const r = await subscriberService.connectBroker(mqttConfig)
    backendConnected.value = true
    addLog(`✅ ${r.message || '已连接MQTT'}`)
    await refreshStatus()
  } catch (e) {
    addLog(`❌ ${e.message || '连接失败'}`)
  } finally {
    connecting.value = false
  }
}

async function disconnectBroker() {
  try {
    const r = await subscriberService.disconnectBroker()
    backendConnected.value = false
    subscribedTypes.value = []
    addLog(`ℹ️ ${r.message || '已断开'}`)
  } catch (e) {
    addLog(`❌ ${e.message || '断开失败'}`)
  }
}

async function refreshStatus() {
  try {
    const s = await subscriberService.getStatus()
    backendConnected.value = !!s.is_connected
    subscribedTypes.value = s.subscribed_types || []
    // 同步订阅类型到共享服务
    sharedData.updateSubscribedTypes(subscribedTypes.value)
  } catch {
    // ignore
  }
}

async function updateSubscription() {
  try {
    const r = await subscriberService.updateSubscription(selectedTypes.value)
    addLog(`✅ ${r.message || '订阅已更新'}`)
    await refreshStatus()
  } catch (e) {
    addLog(`❌ ${e.message || '订阅失败'}`)
  }
}

function clearData() {
  history.temperature = []
  history.humidity = []
  history.pressure = []
  currentValues.temperature = null
  currentValues.humidity = null
  currentValues.pressure = null
  lastUpdated.temperature = null
  lastUpdated.humidity = null
  lastUpdated.pressure = null
  statistics.value = { temperature: 0, humidity: 0, pressure: 0 }
  processedCount.value = 0
  incomingQueue.value = []
  xiaojiaMood.value = 'normal'
  xiaojiaTip.value = '已清空数据，等待新消息...'
  markerStatus.value = 'normal'
  // 清空共享数据
  sharedData.clearAllData()
  addLog('🧹 已清空数据')
}

function formatValue(v, unit) {
  if (v === null || v === undefined) return '--'
  const n = Number(v)
  if (Number.isFinite(n)) return `${n.toFixed(1)} ${unit}`
  return String(v)
}

function sparkPoints(arr) {
  if (!arr || arr.length < 2) return ''
  const vals = arr.map((p) => p.v)
  const min = Math.min(...vals)
  const max = Math.max(...vals)
  const range = max - min || 1
  return arr
    .map((p, i) => {
      const x = (i / (arr.length - 1)) * sparkW
      const y = sparkH - ((p.v - min) / range) * sparkH
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
}

function updateXiaojia(type, value) {
  const v = Number(value)
  xiaojiaMood.value = 'normal'
  markerStatus.value = 'normal'
  if (!Number.isFinite(v)) {
    xiaojiaTip.value = `收到 ${type}: ${value}`
    return
  }

  if (type === 'temperature') {
    if (v >= 30) {
      xiaojiaMood.value = 'hot'
      markerStatus.value = 'warning'
      xiaojiaTip.value = `${selectedBuilding.value} 有点热（${v.toFixed(1)}°C），注意通风降温。`
      return
    }
    if (v <= 5) {
      xiaojiaMood.value = 'cold'
      markerStatus.value = 'warning'
      xiaojiaTip.value = `${selectedBuilding.value} 偏冷（${v.toFixed(1)}°C），注意保暖。`
      return
    }
  }

  if (type === 'humidity') {
    if (v >= 80) {
      xiaojiaMood.value = 'humid'
      markerStatus.value = 'warning'
      xiaojiaTip.value = `${selectedBuilding.value} 偏湿（${v.toFixed(1)}%），注意防潮。`
      return
    }
  }

  if (type === 'pressure') {
    if (v < 990) {
      xiaojiaMood.value = 'lowp'
      markerStatus.value = 'error'
      xiaojiaTip.value = `${selectedBuilding.value} 气压偏低（${v.toFixed(1)} hPa），注意天气变化。`
      return
    }
    if (v > 1030) {
      xiaojiaMood.value = 'highp'
      markerStatus.value = 'warning'
      xiaojiaTip.value = `${selectedBuilding.value} 气压偏高（${v.toFixed(1)} hPa）。`
      return
    }
  }

  xiaojiaTip.value = `来自 ${selectedBuilding.value} 的 ${type}: ${v.toFixed(1)}`
}

function handleWsMessage(msg) {
  if (msg.type === 'status' && msg.status) {
    backendConnected.value = !!msg.status.is_connected
    subscribedTypes.value = msg.status.subscribed_types || []
    // 同步订阅类型到共享服务
    sharedData.updateSubscribedTypes(subscribedTypes.value)
    // 后端统计可用于对比，但前端"已处理"计数以本地 processedCount 为准
    return
  }
  if (msg.type === 'data' && msg.data) {
    const d = msg.data
    const topic = d.topic || ''
    const sensorType = d.sensor_type || (topic.split('/').pop() || '')
    const v = d.value
    const ts = d.timestamp || d.received_at || new Date().toISOString()

    enqueueIncoming({ source: 'backend', topic, sensorType, value: v, timestamp: ts })
  }
}

async function loadLatest(type) {
  loadingLatest[type] = true
  try {
    const r = await subscriberService.getLatestData(type, 100)
    const arr = (r.data || []).map((x) => ({ t: x.timestamp, v: Number(x.value) })).filter((x) => Number.isFinite(x.v))
    history[type] = arr.slice(-60)
    // 同步历史数据到共享服务
    sharedData.updateHistoryData(type, arr)
    addLog(`📦 已拉取 ${type} 最新 ${r.count || arr.length} 条`)
  } catch (e) {
    addLog(`❌ 拉取历史失败：${e.message || ''}`)
  } finally {
    loadingLatest[type] = false
  }
}

function toMqttTopics(types) {
  const map = {
    temperature: 'sensor/temperature',
    humidity: 'sensor/humidity',
    pressure: 'sensor/pressure'
  }
  return types.map((t) => map[t]).filter(Boolean)
}

function applyMqttSubscriptions() {
  if (!mqttWsClient.value || !mqttWsConnected.value) return
  const topics = toMqttTopics(selectedTypes.value)
  try {
    mqttWsClient.value.unsubscribe('sensor/temperature')
    mqttWsClient.value.unsubscribe('sensor/humidity')
    mqttWsClient.value.unsubscribe('sensor/pressure')
  } catch {
    // ignore
  }
  topics.forEach((t) => {
    mqttWsClient.value.subscribe(t, { qos: 1 }, (err) => {
      if (err) addLog(`❌ 订阅失败：${t}`)
    })
  })
  subscribedTypes.value = [...selectedTypes.value]
  // 同步订阅类型到共享服务
  sharedData.updateSubscribedTypes(selectedTypes.value)
  addLog(`📡 已订阅（前端直连）：${topics.join(', ')}`)
}

function connectMqttWs() {
  if (!mqttWs.url) {
    addLog('❌ Broker WS 地址不能为空')
    return
  }
  if (mqttWsClient.value) {
    try {
      mqttWsClient.value.end(true)
    } catch {
      // ignore
    }
    mqttWsClient.value = null
  }

  mqttWsConnecting.value = true
  addLog(`🔌 正在连接 Broker WS：${mqttWs.url}`)
  const options = {
    clientId: `sub_${crypto.randomUUID?.() || Math.random().toString(16).slice(2)}`,
    clean: true,
    reconnectPeriod: 2000,
    connectTimeout: 5000
  }

  const client = mqtt.connect(mqttWs.url, options)
  mqttWsClient.value = client

  client.on('connect', () => {
    mqttWsConnecting.value = false
    mqttWsConnected.value = true
    addLog('✅ Broker WS 已连接')
    applyMqttSubscriptions()
  })

  client.on('reconnect', () => {
    mqttWsConnecting.value = true
    addLog('🔄 Broker WS 重连中...')
  })

  client.on('close', () => {
    mqttWsConnecting.value = false
    mqttWsConnected.value = false
    addLog('⚠️ Broker WS 连接已关闭')
  })

  client.on('error', (err) => {
    mqttWsConnecting.value = false
    mqttWsConnected.value = false
    addLog(`❌ Broker WS 错误：${err?.message || err}`)
  })

  client.on('message', (topic, payload) => {
    try {
      const str = payload.toString()
      const data = JSON.parse(str)
      const sensorType = topic.split('/').pop()
      const v = data.value
      const ts = data.timestamp || new Date().toISOString()

      enqueueIncoming({ source: 'mqtt', topic, sensorType, value: v, timestamp: ts })
    } catch {
      // ignore
    }
  })
}

function disconnectMqttWs() {
  if (mqttWsClient.value) {
    try {
      mqttWsClient.value.end(true)
    } catch {
      // ignore
    }
    mqttWsClient.value = null
  }
  mqttWsConnected.value = false
  mqttWsConnecting.value = false
  // 清空待处理队列
  incomingQueue.value = []
  addLog('ℹ️ 已断开 Broker WS')
}

onMounted(async () => {
  applyBackendApi()
  await refreshStatus()
  startThrottle()
  subscriberService.connectWebSocket(handleWsMessage, (s) => {
    wsConnected.value = !!s.connected
  })
  // 初始化时同步订阅类型到共享服务
  sharedData.updateSubscribedTypes(subscribedTypes.value)
})

onUnmounted(() => {
  subscriberService.disconnectWebSocket()
  disconnectMqttWs()
  stopThrottle()
})

watch(
  () => selectedTypes.value.slice().sort().join(','),
  () => {
    if (mqttWsConnected.value) applyMqttSubscriptions()
  }
)
</script>

<style scoped>
.subscriber-page {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.status-cards {
  display: grid;
  grid-template-columns: 1.2fr 1fr 1fr;
  gap: 16px;
}

.panel {
  background: rgba(10, 30, 60, 0.55);
  border: 2px solid rgba(100, 180, 255, 0.18);
  border-radius: 12px;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(100, 180, 255, 0.18);
  background: linear-gradient(90deg, rgba(20, 60, 100, 0.55), rgba(10, 30, 60, 0));
}

.panel-icon {
  font-size: 18px;
  filter: drop-shadow(0 0 8px rgba(124, 231, 255, 0.35));
}

.panel-title {
  color: #7ce7ff;
  font-weight: 700;
}

.panel-content {
  padding: 16px;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

label {
  color: #aaddff;
  font-size: 13px;
}

.hint {
  color: #8fa8c0;
  font-size: 12px;
  margin-left: 8px;
}

.input-field {
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid rgba(100, 180, 255, 0.25);
  background: rgba(10, 20, 40, 0.55);
  color: #dfe9f5;
  outline: none;
  min-width: 240px;
}

.port-input {
  min-width: 120px;
}

.btn {
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid rgba(100, 180, 255, 0.25);
  background: rgba(10, 20, 40, 0.55);
  color: #dfe9f5;
  cursor: pointer;
  transition: all 0.2s;
}

.btn:hover {
  border-color: rgba(124, 231, 255, 0.45);
  box-shadow: 0 6px 16px rgba(60, 197, 255, 0.18);
  transform: translateY(-1px);
}

.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.btn-primary {
  background: linear-gradient(180deg, rgba(0, 120, 200, 0.6), rgba(0, 80, 150, 0.6));
}

.btn-danger {
  background: linear-gradient(180deg, rgba(200, 60, 60, 0.6), rgba(150, 40, 40, 0.6));
}

.btn-success {
  background: linear-gradient(180deg, rgba(0, 160, 120, 0.6), rgba(0, 120, 90, 0.6));
}

.btn-warning {
  background: linear-gradient(180deg, rgba(200, 160, 0, 0.6), rgba(150, 120, 0, 0.6));
}

.btn-secondary {
  background: linear-gradient(180deg, rgba(40, 90, 150, 0.55), rgba(20, 60, 110, 0.55));
}

.btn-small {
  padding: 6px 10px;
  border-radius: 8px;
  font-size: 12px;
}

.chip-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: 1px solid rgba(100, 180, 255, 0.2);
  border-radius: 999px;
  background: rgba(10, 20, 40, 0.45);
  color: #dfe9f5;
  cursor: pointer;
}

.chip input {
  accent-color: #7ce7ff;
}

.sub-list {
  margin-top: 12px;
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.sub-title {
  color: #aaddff;
  font-size: 13px;
}

.sub-items {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.sub-item {
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(124, 231, 255, 0.25);
  color: #7ce7ff;
  background: rgba(10, 20, 40, 0.35);
  font-size: 12px;
}

.sub-empty {
  color: #8fa8c0;
  font-size: 12px;
}

.map-row {
  display: grid;
  grid-template-columns: 3fr 1.4fr;
  gap: 14px;
}

.map-panel {
  border: 1px solid rgba(100, 180, 255, 0.18);
  border-radius: 12px;
  overflow: hidden;
  background: rgba(10, 20, 40, 0.35);
}

.map-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  color: #aaddff;
  border-bottom: 1px solid rgba(100, 180, 255, 0.15);
}

.map-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.select-field {
  padding: 6px 10px;
  border-radius: 10px;
  border: 1px solid rgba(100, 180, 255, 0.25);
  background: rgba(10, 20, 40, 0.55);
  color: #dfe9f5;
}

.map-container {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 10;
  background: rgba(0, 0, 0, 0.25);
}

.map-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.map-missing {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #aaddff;
  gap: 8px;
}

.map-missing .small {
  color: #8fa8c0;
  font-size: 12px;
}

.marker {
  position: absolute;
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.marker-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: rgba(61, 223, 158, 0.95);
  box-shadow: 0 0 14px rgba(61, 223, 158, 0.8);
}

.marker.normal .marker-dot {
  background: rgba(61, 223, 158, 0.95);
  box-shadow: 0 0 14px rgba(61, 223, 158, 0.8);
}

.marker.warning .marker-dot {
  background: rgba(255, 200, 0, 0.95);
  box-shadow: 0 0 14px rgba(255, 200, 0, 0.8);
}

.marker.error .marker-dot {
  background: rgba(255, 85, 85, 0.95);
  box-shadow: 0 0 14px rgba(255, 85, 85, 0.8);
}

.marker-label {
  margin-top: 6px;
  font-size: 12px;
  color: #dfe9f5;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.45);
}

.right-panel {
  display: flex;
  flex-direction: column;
}

.card-box {
  border: 1px solid rgba(100, 180, 255, 0.18);
  border-radius: 12px;
  overflow: hidden;
  background: rgba(10, 20, 40, 0.35);
}

.box-title {
  padding: 10px 12px;
  border-bottom: 1px solid rgba(100, 180, 255, 0.15);
  color: #7ce7ff;
  font-weight: 700;
}

.box-body {
  padding: 12px;
  color: #dfe9f5;
  font-size: 13px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.xiaojia-mood {
  font-size: 16px;
  font-weight: 800;
  color: #7ce7ff;
}

.xiaojia-tip {
  color: #aaddff;
  line-height: 1.6;
}

.sensor-panels {
  display: grid;
  grid-template-columns: 1fr;
  gap: 14px;
}

.sensor-panel {
  border: 2px solid rgba(100, 180, 255, 0.15);
  border-radius: 12px;
  background: rgba(10, 30, 60, 0.45);
  padding: 14px;
}

.sensor-header {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sensor-title {
  color: #7ce7ff;
  font-weight: 800;
  font-size: 16px;
}

.sensor-meta {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  color: #aaddff;
  font-size: 13px;
}

.meta-item b {
  color: #dfe9f5;
}

.sparkline {
  margin-top: 10px;
  width: 100%;
  height: 90px;
  border: 1px solid rgba(100, 180, 255, 0.12);
  border-radius: 10px;
  background: rgba(10, 20, 40, 0.35);
  overflow: hidden;
}

.sparkline svg {
  width: 100%;
  height: 100%;
}

.log-container {
  max-height: 220px;
  overflow: auto;
  border: 1px solid rgba(100, 180, 255, 0.12);
  border-radius: 10px;
  padding: 10px;
  background: rgba(10, 20, 40, 0.35);
}

.log-entry {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
  font-size: 12px;
  color: #dfe9f5;
  padding: 6px 0;
  border-bottom: 1px dashed rgba(100, 180, 255, 0.12);
}

.btn-clear-log {
  margin-left: auto;
  padding: 6px 10px;
  border-radius: 10px;
  border: 1px solid rgba(100, 180, 255, 0.18);
  background: rgba(10, 20, 40, 0.35);
  color: #aaddff;
  cursor: pointer;
}

.btn-clear-log:hover {
  border-color: rgba(124, 231, 255, 0.35);
  box-shadow: 0 6px 16px rgba(60, 197, 255, 0.12);
}

@media (max-width: 1100px) {
  .status-cards {
    grid-template-columns: 1fr;
  }
  .map-row {
    grid-template-columns: 1fr;
  }
}
</style>
