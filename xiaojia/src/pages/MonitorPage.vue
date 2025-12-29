<template>
  <div class="monitor-page">
    <!-- 顶部状态卡片 -->
    <div class="status-cards">
      <StatusCard
        title="实时监控状态"
        :value="connectionStatus"
        :status="isConnected ? 'online' : 'offline'"
        icon="📊"
      />
      <MiniCard title="舒适度指数" :value="currentComfort?.score || '--'" :highlight="true" />
      <MiniCard title="数据更新" :value="lastUpdateTime || '--'" :highlight="true" />
    </div>

    <!-- 舒适度展示区域 -->
    <div class="comfort-section">
      <div class="comfort-card">
        <div class="comfort-emoji">{{ currentComfort?.emoji || '❓' }}</div>
        <div class="comfort-info">
          <div class="comfort-score">
            <span class="score-label">舒适度指数</span>
            <span class="score-value">{{ currentComfort?.score || 0 }}</span>
            <span class="score-unit">/100</span>
          </div>
          <div class="comfort-message">{{ currentComfort?.message || '等待数据...' }}</div>
        </div>
        <div class="comfort-details">
          <div class="detail-item">
            <span class="detail-label">温度</span>
            <span class="detail-value">{{ formatValue(currentValues.temperature, '°C') }}</span>
            <span class="detail-status" :class="getStatusClass(currentComfort?.details?.temperature?.level)">
              {{ getStatusText(currentComfort?.details?.temperature?.level) }}
            </span>
          </div>
          <div class="detail-item">
            <span class="detail-label">湿度</span>
            <span class="detail-value">{{ formatValue(currentValues.humidity, '%') }}</span>
            <span class="detail-status" :class="getStatusClass(currentComfort?.details?.humidity?.level)">
              {{ getStatusText(currentComfort?.details?.humidity?.level) }}
            </span>
          </div>
          <div class="detail-item">
            <span class="detail-label">气压</span>
            <span class="detail-value">{{ formatValue(currentValues.pressure, 'hPa') }}</span>
            <span class="detail-status" :class="getStatusClass(currentComfort?.details?.pressure?.level)">
              {{ getStatusText(currentComfort?.details?.pressure?.level) }}
            </span>
          </div>
        </div>
      </div>

      <!-- 分析建议区域 -->
      <div class="suggestions-card">
        <div class="card-header">
          <span class="card-icon">💡</span>
          <span class="card-title">环境分析与建议</span>
        </div>
        <div class="suggestions-content">
          <div v-if="currentComfort?.suggestions && currentComfort.suggestions.length > 0" class="suggestions-list">
            <div v-for="(suggestion, idx) in currentComfort.suggestions" :key="idx" class="suggestion-item">
              <span class="suggestion-icon">•</span>
              <span class="suggestion-text">{{ suggestion }}</span>
            </div>
          </div>
          <div v-else class="suggestions-empty">等待数据进行分析...</div>
        </div>
      </div>
    </div>

    <!-- 数据预测区域 -->
    <div class="prediction-section">
      <div class="panel">
        <div class="panel-header">
          <span class="panel-icon">📈</span>
          <span class="panel-title">未来数据预测</span>
          <div class="panel-controls">
            <label>预测时长：</label>
            <select v-model="predictHours" class="select-field" @change="updateAllPredictions">
              <option :value="6">6小时</option>
              <option :value="12">12小时</option>
              <option :value="24">24小时</option>
              <option :value="48">48小时</option>
              <option :value="72">72小时</option>
            </select>
            <button class="btn btn-primary" @click="updateAllPredictions" :disabled="loadingPrediction">
              {{ loadingPrediction ? '预测中...' : '刷新预测' }}
            </button>
          </div>
        </div>
        <div class="panel-content">
          <!-- 温度预测 -->
          <div v-if="hasData('temperature')" class="prediction-chart">
            <div class="chart-title">🌡️ 温度预测</div>
            <div class="chart-container">
              <v-chart class="chart" :option="temperatureChartOption" autoresize />
            </div>
          </div>
          
          <!-- 湿度预测 -->
          <div v-if="hasData('humidity')" class="prediction-chart">
            <div class="chart-title">💧 湿度预测</div>
            <div class="chart-container">
              <v-chart class="chart" :option="humidityChartOption" autoresize />
            </div>
          </div>
          
          <!-- 气压预测 -->
          <div v-if="hasData('pressure')" class="prediction-chart">
            <div class="chart-title">📊 气压预测</div>
            <div class="chart-container">
              <v-chart class="chart" :option="pressureChartOption" autoresize />
            </div>
          </div>
          
          <div v-if="!hasAnyData()" class="chart-empty">
            <div class="empty-icon">📊</div>
            <div class="empty-text">等待接收数据后自动生成预测图表</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 历史平均数据 -->
    <div class="history-section">
      <div class="panel">
        <div class="panel-header">
          <span class="panel-icon">📊</span>
          <span class="panel-title">历史平均数据</span>
          <div class="panel-controls">
            <label>选择方式：</label>
            <select v-model="historyMode" class="select-field" @change="onHistoryModeChange">
              <option value="count">按数据条数</option>
              <option value="time">按时间范围</option>
            </select>
            <template v-if="historyMode === 'count'">
              <label style="margin-left: 10px;">数据条数：</label>
              <select v-model="historyCount" class="select-field">
                <option :value="50">最近50条</option>
                <option :value="100">最近100条</option>
                <option :value="200">最近200条</option>
                <option :value="500">最近500条</option>
                <option :value="1000">最近1000条</option>
              </select>
            </template>
            <template v-else>
              <label style="margin-left: 10px;">开始时间：</label>
              <input 
                v-model="historyStartTime" 
                type="datetime-local" 
                class="datetime-input"
              />
              <label style="margin-left: 10px;">结束时间：</label>
              <input 
                v-model="historyEndTime" 
                type="datetime-local" 
                class="datetime-input"
              />
            </template>
            <button class="btn btn-secondary" @click="loadHistoryAverage" :disabled="loadingHistory">
              {{ loadingHistory ? '计算中...' : '计算平均值' }}
            </button>
          </div>
        </div>
        <div class="panel-content">
          <div v-if="historyAverage" class="history-stats">
            <div class="stat-card">
              <div class="stat-icon">😊</div>
              <div class="stat-info">
                <div class="stat-label">平均舒适度</div>
                <div class="stat-value">{{ historyAverage.score }}</div>
                <div class="stat-emoji">{{ historyAverage.emoji }}</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon">🌡️</div>
              <div class="stat-info">
                <div class="stat-label">平均温度</div>
                <div class="stat-value">{{ formatValue(historyAverage.temperature, '°C') }}</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon">💧</div>
              <div class="stat-info">
                <div class="stat-label">平均湿度</div>
                <div class="stat-value">{{ formatValue(historyAverage.humidity, '%') }}</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon">📊</div>
              <div class="stat-info">
                <div class="stat-label">平均气压</div>
                <div class="stat-value">{{ formatValue(historyAverage.pressure, 'hPa') }}</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon">📈</div>
              <div class="stat-info">
                <div class="stat-label">数据点数</div>
                <div class="stat-value">{{ historyAverage.count }}</div>
              </div>
            </div>
            <div v-if="historyAverage.timeRange" class="stat-card full-width">
              <div class="stat-icon">⏰</div>
              <div class="stat-info">
                <div class="stat-label">时间范围</div>
                <div class="stat-value-small">
                  {{ historyAverage.timeRange.start }} 至 {{ historyAverage.timeRange.end }}
                </div>
              </div>
            </div>
          </div>
          <div v-else class="history-empty">
            <div class="empty-icon">📊</div>
            <div class="empty-text">点击"计算平均值"加载历史平均数据</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent
} from 'echarts/components'
import VChart, { THEME_KEY } from 'vue-echarts'
import StatusCard from '@/components/StatusCard.vue'
import MiniCard from '@/components/MiniCard.vue'
import { subscriberService } from '@/services/subscriberService'
import { calculateComfort, calculateAverageComfort } from '@/utils/comfortCalculator'
import mqtt from 'mqtt'

// 注册 ECharts 组件
use([
  CanvasRenderer,
  LineChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent
])

// ========= 连接状态 =========
const isConnected = ref(false)
const connectionStatus = computed(() => (isConnected.value ? '已连接' : '未连接'))
const lastUpdateTime = ref('')

// ========= MQTT WebSocket 连接 =========
const mqttWs = reactive({
  url: 'ws://118.31.63.5:9001/mqtt'
})
const mqttWsClient = ref(null)
const mqttWsConnected = ref(false)

// ========= 当前数据 =========
const currentValues = reactive({
  temperature: null,
  humidity: null,
  pressure: null
})

// ========= 舒适度 =========
const currentComfort = ref(null)

// ========= 预测数据 =========
const predictHours = ref(24)
const loadingPrediction = ref(false)
const predictionData = reactive({
  temperature: null,
  humidity: null,
  pressure: null
})

// ========= 历史数据 =========
const historyMode = ref('count') // 'count' 或 'time'
const historyCount = ref(100)
const historyStartTime = ref('')
const historyEndTime = ref('')
const loadingHistory = ref(false)
const historyAverage = ref(null)

// ========= 历史数据存储 =========
const historyData = reactive({
  temperature: [],
  humidity: [],
  pressure: []
})

// ========= 创建图表配置函数 =========
function createChartOption(sensorType, data) {
  if (!data || !data.historical || data.historical.length === 0) {
    return {
      title: {
        text: '暂无数据',
        left: 'center',
        top: 'middle',
        textStyle: { color: '#8fa8c0' }
      }
    }
  }

  const historical = data.historical || []
  const future = data.future || []

  // 计算历史平均值
  const avgValue = historical.length > 0
    ? historical.reduce((sum, item) => sum + (item.actual || item.value || 0), 0) / historical.length
    : 0

  // 准备历史数据
  const historicalData = historical.map(item => [
    new Date(item.timestamp).getTime(),
    item.actual || item.value
  ])

  // 准备预测数据
  const futureData = future.map(item => [
    new Date(item.timestamp).getTime(),
    item.predicted_value
  ])

  // 准备平均线数据（覆盖所有时间点）
  const allTimes = [
    ...historical.map(item => new Date(item.timestamp).getTime()),
    ...future.map(item => new Date(item.timestamp).getTime())
  ]
  const avgLineData = allTimes.map(time => [time, avgValue])

  const unitMap = {
    temperature: '°C',
    humidity: '%',
    pressure: 'hPa'
  }

  const nameMap = {
    temperature: '温度',
    humidity: '湿度',
    pressure: '气压'
  }

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      formatter: (params) => {
        let result = ''
        params.forEach(param => {
          const date = new Date(param.data[0])
          result += `${date.toLocaleString('zh-CN')}<br/>`
          result += `${param.seriesName}: ${param.data[1].toFixed(2)} ${unitMap[sensorType]}<br/>`
        })
        return result
      }
    },
    legend: {
      data: ['历史数据', '预测数据', '历史平均'],
      textStyle: { color: '#aaddff' },
      top: 10
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '15%',
      containLabel: true
    },
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100
      },
      {
        type: 'slider',
        start: 0,
        end: 100,
        height: 20,
        textStyle: { color: '#aaddff' },
        borderColor: 'rgba(124, 231, 255, 0.2)',
        fillerColor: 'rgba(124, 231, 255, 0.1)',
        handleStyle: {
          color: '#7ce7ff'
        }
      }
    ],
    xAxis: {
      type: 'time',
      boundaryGap: false,
      axisLabel: {
        color: '#aaddff',
        formatter: (value) => {
          const date = new Date(value)
          return date.toLocaleString('zh-CN', { 
            month: 'short', 
            day: 'numeric', 
            hour: '2-digit', 
            minute: '2-digit' 
          })
        }
      },
      axisLine: { lineStyle: { color: '#7ce7ff' } },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'value',
      name: `${nameMap[sensorType]} (${unitMap[sensorType]})`,
      nameTextStyle: { color: '#aaddff' },
      axisLabel: { color: '#aaddff' },
      axisLine: { lineStyle: { color: '#7ce7ff' } },
      splitLine: { lineStyle: { color: 'rgba(124, 231, 255, 0.1)' } }
    },
    series: [
      {
        name: '历史数据',
        type: 'line',
        data: historicalData,
        smooth: true,
        lineStyle: { color: '#7ce7ff', width: 2 },
        itemStyle: { color: '#7ce7ff' },
        symbol: 'circle',
        symbolSize: 4,
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(124, 231, 255, 0.3)' },
              { offset: 1, color: 'rgba(124, 231, 255, 0.05)' }
            ]
          }
        }
      },
      {
        name: '预测数据',
        type: 'line',
        data: futureData,
        smooth: true,
        lineStyle: { color: '#ffaa00', width: 2, type: 'dashed' },
        itemStyle: { color: '#ffaa00' },
        symbol: 'circle',
        symbolSize: 4
      },
      {
        name: '历史平均',
        type: 'line',
        data: avgLineData,
        lineStyle: { color: '#3ddf9e', width: 1, type: 'dotted' },
        itemStyle: { color: '#3ddf9e' },
        symbol: 'none'
      }
    ]
  }
}

// ========= 图表配置 =========
const temperatureChartOption = computed(() => {
  return createChartOption('temperature', predictionData.temperature)
})

const humidityChartOption = computed(() => {
  return createChartOption('humidity', predictionData.humidity)
})

const pressureChartOption = computed(() => {
  return createChartOption('pressure', predictionData.pressure)
})

// ========= 检查数据是否存在 =========
function hasData(sensorType) {
  return predictionData[sensorType] !== null && 
         predictionData[sensorType]?.historical?.length > 0
}

function hasAnyData() {
  return hasData('temperature') || hasData('humidity') || hasData('pressure')
}

// ========= 工具函数 =========
function formatValue(v, unit) {
  if (v === null || v === undefined) return '--'
  const n = Number(v)
  if (Number.isFinite(n)) return `${n.toFixed(1)}${unit}`
  return String(v)
}

function getStatusClass(level) {
  if (!level) return ''
  if (level.includes('perfect') || level === 'normal') return 'status-good'
  if (level.includes('very') || level.includes('extreme')) return 'status-bad'
  return 'status-moderate'
}

function getStatusText(level) {
  if (!level) return '--'
  const map = {
    perfect: '理想',
    normal: '正常',
    cool: '偏凉',
    warm: '偏暖',
    cold: '较冷',
    hot: '较热',
    very_cold: '很冷',
    very_hot: '很热',
    extreme_cold: '极冷',
    extreme_hot: '极热',
    dry: '偏干',
    humid: '偏湿',
    very_dry: '很干',
    very_humid: '很湿',
    extreme_dry: '极干',
    extreme_humid: '极湿',
    low: '偏低',
    high: '偏高',
    very_low: '很低',
    very_high: '很高',
    extreme_low: '极低',
    extreme_high: '极高'
  }
  return map[level] || level
}

// ========= 更新舒适度 =========
function updateComfort() {
  currentComfort.value = calculateComfort(
    currentValues.temperature,
    currentValues.humidity,
    currentValues.pressure
  )
  lastUpdateTime.value = new Date().toLocaleTimeString('zh-CN')
}

// ========= MQTT 消息处理 =========
function handleMqttMessage(topic, payload) {
  try {
    const str = payload.toString()
    const data = JSON.parse(str)
    const sensorType = topic.split('/').pop()
    const v = data.value
    const ts = data.timestamp || new Date().toISOString()

    if (sensorType in currentValues) {
      currentValues[sensorType] = v
      const n = Number(v)
      if (Number.isFinite(n)) {
        historyData[sensorType].push({ t: ts, v: n })
        if (historyData[sensorType].length > 1000) {
          historyData[sensorType].shift()
        }
        
        // 当数据积累到一定数量时，自动生成预测
        if (historyData[sensorType].length >= 10 && historyData[sensorType].length % 10 === 0) {
          generatePrediction(sensorType)
        }
      }
      updateComfort()
    }
  } catch (e) {
    console.error('处理MQTT消息失败:', e)
  }
}

// ========= 连接MQTT =========
function connectMqttWs() {
  if (!mqttWs.url) {
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

  const options = {
    clientId: `monitor_${crypto.randomUUID?.() || Math.random().toString(16).slice(2)}`,
    clean: true,
    reconnectPeriod: 2000,
    connectTimeout: 5000
  }

  const client = mqtt.connect(mqttWs.url, options)
  mqttWsClient.value = client

  client.on('connect', () => {
    mqttWsConnected.value = true
    isConnected.value = true
    // 订阅所有传感器主题
    client.subscribe('sensor/temperature', { qos: 1 })
    client.subscribe('sensor/humidity', { qos: 1 })
    client.subscribe('sensor/pressure', { qos: 1 })
  })

  client.on('reconnect', () => {
    isConnected.value = false
  })

  client.on('close', () => {
    mqttWsConnected.value = false
    isConnected.value = false
  })

  client.on('error', (err) => {
    console.error('MQTT错误:', err)
    mqttWsConnected.value = false
    isConnected.value = false
  })

  client.on('message', handleMqttMessage)
}

// ========= 断开MQTT =========
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
  isConnected.value = false
}

// ========= 为单个传感器类型生成预测 =========
async function generatePrediction(sensorType) {
  // 如果本地数据不足，跳过
  if (!historyData[sensorType] || historyData[sensorType].length < 10) {
    return
  }

  const localData = historyData[sensorType].slice(-200) // 使用最近200个数据点
  
  // 简单的线性回归预测
  const values = localData.map(d => d.v)
  const n = values.length
  
  // 计算时间间隔（秒）
  let interval = 3600 // 默认1小时
  if (localData.length > 1) {
    const timeDiff = new Date(localData[localData.length - 1].t).getTime() - 
                     new Date(localData[0].t).getTime()
    interval = timeDiff / (localData.length - 1)
  }

  // 线性回归计算
  let sumX = 0, sumY = 0, sumXY = 0, sumXX = 0
  values.forEach((val, idx) => {
    const x = idx + 1
    sumX += x
    sumY += val
    sumXY += x * val
    sumXX += x * x
  })

  const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX)
  const intercept = (sumY - slope * sumX) / n

  // 准备历史数据
  const historical = localData.map((item, idx) => ({
    timestamp: item.t,
    actual: item.v,
    predicted: slope * (idx + 1) + intercept
  }))

  // 生成未来预测
  const lastTime = new Date(localData[localData.length - 1].t).getTime()
  const future = []
  for (let i = 1; i <= predictHours.value; i++) {
    const futureTime = lastTime + i * interval
    const futureValue = slope * (n + i) + intercept
    future.push({
      timestamp: new Date(futureTime).toISOString(),
      predicted_value: futureValue
    })
  }

  predictionData[sensorType] = {
    sensor_type: sensorType,
    historical,
    future
  }
}

// ========= 更新所有预测数据 =========
async function updateAllPredictions() {
  loadingPrediction.value = true
  try {
    // 为每个有数据的传感器类型生成预测
    const promises = []
    
    if (historyData.temperature && historyData.temperature.length >= 10) {
      promises.push(generatePrediction('temperature'))
    }
    if (historyData.humidity && historyData.humidity.length >= 10) {
      promises.push(generatePrediction('humidity'))
    }
    if (historyData.pressure && historyData.pressure.length >= 10) {
      promises.push(generatePrediction('pressure'))
    }

    if (promises.length === 0) {
      alert('数据不足，请先等待接收一些数据后再进行预测（至少需要10个数据点）')
      return
    }

    await Promise.all(promises)
  } catch (e) {
    console.error('生成预测数据失败:', e)
    alert('预测失败: ' + (e.message || '未知错误'))
  } finally {
    loadingPrediction.value = false
  }
}

// ========= 历史模式切换 =========
function onHistoryModeChange() {
  if (historyMode.value === 'time') {
    // 切换到时间模式时，设置默认时间范围（最近24小时）
    const endDate = new Date()
    const startDate = new Date(endDate.getTime() - 24 * 60 * 60 * 1000)
    historyEndTime.value = formatDateTimeLocal(endDate)
    historyStartTime.value = formatDateTimeLocal(startDate)
  }
}

// ========= 格式化日期时间为本地datetime-local格式 =========
function formatDateTimeLocal(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day}T${hours}:${minutes}`
}

// ========= 加载历史平均数据 =========
async function loadHistoryAverage() {
  loadingHistory.value = true
  try {
    let tempFiltered = []
    let humidFiltered = []
    let pressFiltered = []
    let timeRange = null

    if (historyMode.value === 'count') {
      // 按数据条数模式：使用本地历史数据
      const count = historyCount.value
      
      tempFiltered = historyData.temperature.slice(-count).map(item => ({
        timestamp: item.t,
        value: item.v
      }))
      humidFiltered = historyData.humidity.slice(-count).map(item => ({
        timestamp: item.t,
        value: item.v
      }))
      pressFiltered = historyData.pressure.slice(-count).map(item => ({
        timestamp: item.t,
        value: item.v
      }))

      if (tempFiltered.length > 0 || humidFiltered.length > 0 || pressFiltered.length > 0) {
        const allTimes = [
          ...tempFiltered.map(d => new Date(d.timestamp).getTime()),
          ...humidFiltered.map(d => new Date(d.timestamp).getTime()),
          ...pressFiltered.map(d => new Date(d.timestamp).getTime())
        ]
        if (allTimes.length > 0) {
          const minTime = new Date(Math.min(...allTimes))
          const maxTime = new Date(Math.max(...allTimes))
          timeRange = {
            start: minTime.toLocaleString('zh-CN'),
            end: maxTime.toLocaleString('zh-CN')
          }
        }
      }
    } else {
      // 按时间范围模式
      if (!historyStartTime.value || !historyEndTime.value) {
        alert('请选择开始时间和结束时间')
        return
      }

      const startDate = new Date(historyStartTime.value)
      const endDate = new Date(historyEndTime.value)

      if (startDate >= endDate) {
        alert('开始时间必须早于结束时间')
        return
      }

      timeRange = {
        start: startDate.toLocaleString('zh-CN'),
        end: endDate.toLocaleString('zh-CN')
      }

      // 从本地历史数据中过滤时间范围
      const filterByTime = (data) => {
        return data.filter(item => {
          const itemTime = new Date(item.t)
          return itemTime >= startDate && itemTime <= endDate
        }).map(item => ({
          timestamp: item.t,
          value: item.v
        }))
      }

      tempFiltered = filterByTime(historyData.temperature)
      humidFiltered = filterByTime(historyData.humidity)
      pressFiltered = filterByTime(historyData.pressure)

      // 如果本地数据不足，尝试从后端获取
      if (tempFiltered.length === 0 && humidFiltered.length === 0 && pressFiltered.length === 0) {
        try {
          const [tempData, humidData, pressData] = await Promise.all([
            subscriberService.getLatestData('temperature', 10000).catch(() => ({ data: [] })),
            subscriberService.getLatestData('humidity', 10000).catch(() => ({ data: [] })),
            subscriberService.getLatestData('pressure', 10000).catch(() => ({ data: [] }))
          ])

          const filterBackendData = (data) => {
            return (data.data || []).filter(item => {
              const itemTime = new Date(item.timestamp)
              return itemTime >= startDate && itemTime <= endDate
            })
          }

          tempFiltered = filterBackendData(tempData)
          humidFiltered = filterBackendData(humidData)
          pressFiltered = filterBackendData(pressData)
        } catch (e) {
          console.warn('从后端获取数据失败:', e)
        }
      }
    }

    if (tempFiltered.length === 0 && humidFiltered.length === 0 && pressFiltered.length === 0) {
      alert('所选范围内没有数据')
      return
    }

    // 计算平均值
    const avgTemp = tempFiltered.length > 0
      ? tempFiltered.reduce((sum, item) => sum + Number(item.value), 0) / tempFiltered.length
      : null
    const avgHumid = humidFiltered.length > 0
      ? humidFiltered.reduce((sum, item) => sum + Number(item.value), 0) / humidFiltered.length
      : null
    const avgPress = pressFiltered.length > 0
      ? pressFiltered.reduce((sum, item) => sum + Number(item.value), 0) / pressFiltered.length
      : null

    // 计算平均舒适度 - 需要同时有温度、湿度、气压的数据
    const comfortData = []
    
    // 按时间戳对齐数据
    const allTimestamps = new Set([
      ...tempFiltered.map(d => d.timestamp),
      ...humidFiltered.map(d => d.timestamp),
      ...pressFiltered.map(d => d.timestamp)
    ])

    allTimestamps.forEach(timestamp => {
      const tempItem = tempFiltered.find(d => d.timestamp === timestamp)
      const humidItem = humidFiltered.find(d => d.timestamp === timestamp)
      const pressItem = pressFiltered.find(d => d.timestamp === timestamp)

      const temp = tempItem ? Number(tempItem.value) : null
      const humid = humidItem ? Number(humidItem.value) : null
      const press = pressItem ? Number(pressItem.value) : null

      // 只有三个值都存在时才计算舒适度
      if (temp !== null && humid !== null && press !== null) {
        comfortData.push({ temperature: temp, humidity: humid, pressure: press })
      }
    })

    const avgComfort = calculateAverageComfort(comfortData)

    historyAverage.value = {
      temperature: avgTemp,
      humidity: avgHumid,
      pressure: avgPress,
      score: avgComfort?.score || 0,
      emoji: avgComfort?.emoji || '❓',
      count: comfortData.length,
      timeRange
    }
  } catch (e) {
    console.error('加载历史平均数据失败:', e)
    alert('计算失败: ' + (e.message || '未知错误'))
  } finally {
    loadingHistory.value = false
  }
}

// ========= 生命周期 =========
onMounted(() => {
  connectMqttWs()
  // 初始化舒适度
  updateComfort()
  // 初始化时间范围（默认最近24小时）
  onHistoryModeChange()
})

onUnmounted(() => {
  disconnectMqttWs()
})

// 监听数据变化，自动更新舒适度
watch(
  () => [currentValues.temperature, currentValues.humidity, currentValues.pressure],
  () => {
    updateComfort()
  }
)
</script>

<style scoped>
.monitor-page {
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

/* 舒适度区域 */
.comfort-section {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
}

.comfort-card {
  background: rgba(10, 30, 60, 0.55);
  border: 2px solid rgba(100, 180, 255, 0.18);
  border-radius: 12px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.comfort-emoji {
  font-size: 80px;
  text-align: center;
  filter: drop-shadow(0 0 20px rgba(124, 231, 255, 0.4));
}

.comfort-info {
  text-align: center;
}

.comfort-score {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 8px;
  margin-bottom: 12px;
}

.score-label {
  color: #aaddff;
  font-size: 16px;
}

.score-value {
  color: #7ce7ff;
  font-size: 48px;
  font-weight: bold;
  text-shadow: 0 0 15px rgba(124, 231, 255, 0.5);
}

.score-unit {
  color: #8fa8c0;
  font-size: 20px;
}

.comfort-message {
  color: #7ce7ff;
  font-size: 18px;
  font-weight: 600;
}

.comfort-details {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  background: rgba(10, 20, 40, 0.35);
  border-radius: 8px;
  border: 1px solid rgba(100, 180, 255, 0.1);
}

.detail-label {
  color: #aaddff;
  font-size: 14px;
  min-width: 60px;
}

.detail-value {
  color: #dfe9f5;
  font-size: 16px;
  font-weight: 600;
  flex: 1;
  text-align: center;
}

.detail-status {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  min-width: 50px;
  text-align: center;
}

.detail-status.status-good {
  background: rgba(61, 223, 158, 0.2);
  color: #3ddf9e;
  border: 1px solid rgba(61, 223, 158, 0.3);
}

.detail-status.status-moderate {
  background: rgba(255, 200, 0, 0.2);
  color: #ffc800;
  border: 1px solid rgba(255, 200, 0, 0.3);
}

.detail-status.status-bad {
  background: rgba(255, 85, 85, 0.2);
  color: #ff5555;
  border: 1px solid rgba(255, 85, 85, 0.3);
}

/* 建议卡片 */
.suggestions-card {
  background: rgba(10, 30, 60, 0.55);
  border: 2px solid rgba(100, 180, 255, 0.18);
  border-radius: 12px;
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(100, 180, 255, 0.18);
  background: linear-gradient(90deg, rgba(20, 60, 100, 0.55), rgba(10, 30, 60, 0));
}

.card-icon {
  font-size: 18px;
  filter: drop-shadow(0 0 8px rgba(124, 231, 255, 0.35));
}

.card-title {
  color: #7ce7ff;
  font-weight: 700;
}

.suggestions-content {
  padding: 16px;
  min-height: 200px;
}

.suggestions-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.suggestion-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  color: #dfe9f5;
  line-height: 1.6;
}

.suggestion-icon {
  color: #7ce7ff;
  font-weight: bold;
}

.suggestion-text {
  flex: 1;
}

.suggestions-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #8fa8c0;
}

/* 预测和历史区域 */
.prediction-section,
.history-section {
  width: 100%;
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
  flex: 1;
}

.panel-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.panel-controls label {
  color: #aaddff;
  font-size: 13px;
}

.panel-content {
  padding: 16px;
}

.prediction-chart {
  margin-bottom: 24px;
}

.prediction-chart:last-child {
  margin-bottom: 0;
}

.chart-title {
  color: #7ce7ff;
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(100, 180, 255, 0.18);
}

.chart-container {
  width: 100%;
  height: 400px;
}

.chart {
  width: 100%;
  height: 100%;
}

.chart-empty,
.history-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 400px;
  color: #8fa8c0;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.5;
}

.empty-text {
  font-size: 14px;
}

/* 历史统计 */
.history-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.stat-card {
  background: rgba(10, 20, 40, 0.35);
  border: 1px solid rgba(100, 180, 255, 0.15);
  border-radius: 10px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.stat-icon {
  font-size: 32px;
  filter: drop-shadow(0 0 8px rgba(124, 231, 255, 0.3));
}

.stat-info {
  flex: 1;
}

.stat-label {
  color: #aaddff;
  font-size: 12px;
  margin-bottom: 4px;
}

.stat-value {
  color: #7ce7ff;
  font-size: 20px;
  font-weight: bold;
}

.stat-emoji {
  font-size: 24px;
  margin-top: 4px;
}

.stat-card.full-width {
  grid-column: 1 / -1;
}

.stat-value-small {
  color: #aaddff;
  font-size: 13px;
  margin-top: 4px;
  line-height: 1.4;
}

.select-field {
  padding: 6px 10px;
  border-radius: 10px;
  border: 1px solid rgba(100, 180, 255, 0.25);
  background: rgba(10, 20, 40, 0.55);
  color: #dfe9f5;
  outline: none;
}

.datetime-input {
  padding: 6px 10px;
  border-radius: 10px;
  border: 1px solid rgba(100, 180, 255, 0.25);
  background: rgba(10, 20, 40, 0.55);
  color: #dfe9f5;
  outline: none;
  font-size: 13px;
}

.datetime-input::-webkit-calendar-picker-indicator {
  filter: invert(1);
  cursor: pointer;
}

.btn {
  padding: 8px 14px;
  border-radius: 10px;
  border: 1px solid rgba(100, 180, 255, 0.25);
  background: rgba(10, 20, 40, 0.55);
  color: #dfe9f5;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 13px;
}

.btn:hover:not(:disabled) {
  border-color: rgba(124, 231, 255, 0.45);
  box-shadow: 0 6px 16px rgba(60, 197, 255, 0.18);
  transform: translateY(-1px);
}

.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.btn-primary {
  background: linear-gradient(180deg, rgba(0, 120, 200, 0.6), rgba(0, 80, 150, 0.6));
}

.btn-secondary {
  background: linear-gradient(180deg, rgba(40, 90, 150, 0.55), rgba(20, 60, 110, 0.55));
}

@media (max-width: 1100px) {
  .status-cards {
    grid-template-columns: 1fr;
  }
  .comfort-section {
    grid-template-columns: 1fr;
  }
  .history-stats {
    grid-template-columns: 1fr;
  }
}
</style>
