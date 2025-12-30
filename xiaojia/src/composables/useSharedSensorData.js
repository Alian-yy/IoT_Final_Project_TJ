/**
 * 共享传感器数据存储服务
 * 用于在 SubscriberPage 和 MonitorPage 之间共享订阅的数据
 */
import { reactive, ref } from 'vue'

// 全局共享状态
const subscribedTypes = ref([]) // 当前订阅的传感器类型
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
const historyData = reactive({
  temperature: [],
  humidity: [],
  pressure: []
})

// 历史数据最大保留数量
const MAX_HISTORY_COUNT = 1000

export function useSharedSensorData() {
  /**
   * 更新订阅的传感器类型
   */
  function updateSubscribedTypes(types) {
    subscribedTypes.value = [...types]
  }

  /**
   * 更新传感器数据
   */
  function updateSensorData(sensorType, value, timestamp) {
    if (!(sensorType in currentValues)) {
      return
    }

    // 更新当前值
    currentValues[sensorType] = value
    lastUpdated[sensorType] = timestamp || new Date().toISOString()

    // 更新历史数据
    const numValue = Number(value)
    if (Number.isFinite(numValue)) {
      historyData[sensorType].push({ t: timestamp || new Date().toISOString(), v: numValue })
      
      // 限制历史数据数量
      if (historyData[sensorType].length > MAX_HISTORY_COUNT) {
        historyData[sensorType].shift()
      }
    }
  }

  /**
   * 批量更新历史数据
   */
  function updateHistoryData(sensorType, dataArray) {
    if (!(sensorType in historyData)) {
      return
    }
    historyData[sensorType] = dataArray.slice(-MAX_HISTORY_COUNT)
  }

  /**
   * 清空所有数据
   */
  function clearAllData() {
    currentValues.temperature = null
    currentValues.humidity = null
    currentValues.pressure = null
    lastUpdated.temperature = null
    lastUpdated.humidity = null
    lastUpdated.pressure = null
    historyData.temperature = []
    historyData.humidity = []
    historyData.pressure = []
  }

  /**
   * 清空特定传感器的数据
   */
  function clearSensorData(sensorType) {
    if (sensorType in currentValues) {
      currentValues[sensorType] = null
      lastUpdated[sensorType] = null
      historyData[sensorType] = []
    }
  }

  /**
   * 获取可用的传感器类型（有数据的）
   */
  function getAvailableTypes() {
    return subscribedTypes.value.filter(type => {
      return currentValues[type] !== null && currentValues[type] !== undefined
    })
  }

  /**
   * 检查是否有数据
   */
  function hasData(sensorType) {
    return currentValues[sensorType] !== null && currentValues[sensorType] !== undefined
  }

  /**
   * 检查是否有任何数据
   */
  function hasAnyData() {
    return subscribedTypes.value.some(type => hasData(type))
  }

  return {
    // 状态
    subscribedTypes,
    currentValues,
    lastUpdated,
    historyData,
    
    // 方法
    updateSubscribedTypes,
    updateSensorData,
    updateHistoryData,
    clearAllData,
    clearSensorData,
    getAvailableTypes,
    hasData,
    hasAnyData
  }
}

