import axios from 'axios'

// 订阅端后端（backenddata）默认端口：8002
// 前端不直接连 MQTT（浏览器若直连需要 broker 开 websockets，例如 9001），本项目按发布端方式走后端 API + WebSocket。
class SubscriberService {
  constructor() {
    this.apiBaseUrl = 'http://localhost:8002'
    this.wsConnection = null
  }

  setApiBaseUrl(url) {
    this.apiBaseUrl = url.replace(/\/+$/, '')
  }

  async health() {
    const response = await axios.get(`${this.apiBaseUrl}/`)
    return response.data
  }

  async connectBroker({ broker, port, username, password }) {
    try {
      const response = await axios.post(`${this.apiBaseUrl}/mqtt/connect`, {
        broker,
        port,
        username: username || null,
        password: password || null
      })
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.detail || '连接MQTT失败')
    }
  }

  async disconnectBroker() {
    try {
      const response = await axios.post(`${this.apiBaseUrl}/mqtt/disconnect`)
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.detail || '断开MQTT失败')
    }
  }

  async updateSubscription(sensorTypes) {
    try {
      const response = await axios.post(`${this.apiBaseUrl}/subscribe/update`, {
        sensor_types: sensorTypes
      })
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.detail || '更新订阅失败')
    }
  }

  async getStatus() {
    try {
      const response = await axios.get(`${this.apiBaseUrl}/subscribe/status`)
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.detail || '获取订阅状态失败')
    }
  }

  async getDataCount(sensorType) {
    try {
      const response = await axios.get(`${this.apiBaseUrl}/data/count`, {
        params: sensorType ? { sensor_type: sensorType } : {}
      })
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.detail || '获取数据统计失败')
    }
  }

  async getLatestData(sensorType, limit = 100) {
    try {
      const response = await axios.get(`${this.apiBaseUrl}/data/latest`, {
        params: { sensor_type: sensorType, limit }
      })
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.detail || '获取最新数据失败')
    }
  }

  async getRangeData(sensorType, startDate, endDate) {
    try {
      const response = await axios.get(`${this.apiBaseUrl}/data/range`, {
        params: { sensor_type: sensorType, start_date: startDate, end_date: endDate }
      })
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.detail || '获取范围数据失败')
    }
  }

  async analyzeLinear(payload) {
    const response = await axios.post(`${this.apiBaseUrl}/analysis/linear`, payload)
    return response.data
  }

  async analyzePolynomial(payload) {
    const response = await axios.post(`${this.apiBaseUrl}/analysis/polynomial`, payload)
    return response.data
  }

  async analyzeMovingAverage(payload) {
    const response = await axios.post(`${this.apiBaseUrl}/analysis/moving_average`, payload)
    return response.data
  }

  async analyzeTrend(payload) {
    const response = await axios.post(`${this.apiBaseUrl}/analysis/trend`, payload)
    return response.data
  }

  async analyzeStatistical(payload) {
    const response = await axios.post(`${this.apiBaseUrl}/analysis/statistical`, payload)
    return response.data
  }

  connectWebSocket(onMessage, onStatus) {
    const wsUrl = this.apiBaseUrl.replace(/^http/, 'ws') + '/ws/data'
    this.wsConnection = new WebSocket(wsUrl)

    this.wsConnection.onopen = () => {
      onStatus?.({ type: 'ws', connected: true })
      try {
        // backenddata 端需要 receive_text 保持连接，这里定期发心跳即可
        this._heartbeatTimer = setInterval(() => {
          if (this.wsConnection && this.wsConnection.readyState === WebSocket.OPEN) {
            this.wsConnection.send('ping')
          }
        }, 15000)
      } catch {
        // ignore
      }
    }

    this.wsConnection.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage?.(data)
      } catch {
        // ignore
      }
    }

    this.wsConnection.onerror = () => {
      onStatus?.({ type: 'ws', connected: false })
    }

    this.wsConnection.onclose = () => {
      onStatus?.({ type: 'ws', connected: false })
      if (this._heartbeatTimer) {
        clearInterval(this._heartbeatTimer)
        this._heartbeatTimer = null
      }
    }
  }

  disconnectWebSocket() {
    if (this._heartbeatTimer) {
      clearInterval(this._heartbeatTimer)
      this._heartbeatTimer = null
    }
    if (this.wsConnection) {
      this.wsConnection.close()
      this.wsConnection = null
    }
  }
}

export const subscriberService = new SubscriberService()

