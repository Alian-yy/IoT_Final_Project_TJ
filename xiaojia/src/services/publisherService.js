import axios from 'axios'

const API_BASE_URL = 'http://localhost:8001'

class PublisherService {
  constructor() {
    this.wsConnection = null
    this.isConnected = false
  }

  async connect(broker, port) {
    // 这里实际上是通知后端连接到MQTT broker
    // 前端不直接连接MQTT
    try {
      const response = await axios.post(`${API_BASE_URL}/mqtt/connect`, {
        broker,
        port
      })
      this.isConnected = true
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.detail || '连接失败')
    }
  }

  disconnect() {
    this.isConnected = false
    if (this.wsConnection) {
      this.wsConnection.close()
      this.wsConnection = null
    }
  }

  async getDataInfo() {
    try {
      const response = await axios.get(`${API_BASE_URL}/data/info`)
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.detail || '获取数据信息失败')
    }
  }

  async startPublish(config) {
    try {
      const response = await axios.post(`${API_BASE_URL}/publish/start`, config)
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.detail || '启动发布失败')
    }
  }

  async stopPublish() {
    try {
      const response = await axios.post(`${API_BASE_URL}/publish/stop`)
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.detail || '停止发布失败')
    }
  }

  async resetPublish() {
    try {
      const response = await axios.post(`${API_BASE_URL}/publish/reset`)
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.detail || '重置失败')
    }
  }

  connectWebSocket(onMessage) {
    const wsUrl = `ws://localhost:8001/ws/status`
    this.wsConnection = new WebSocket(wsUrl)

    this.wsConnection.onopen = () => {
      console.log('WebSocket connected')
    }

    this.wsConnection.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage(data)
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }

    this.wsConnection.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    this.wsConnection.onclose = () => {
      console.log('WebSocket disconnected')
    }
  }
}

export const publisherService = new PublisherService()
