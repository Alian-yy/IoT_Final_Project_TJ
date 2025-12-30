/**
 * 舒适度计算工具
 * 综合考虑温度、湿度、压力三个维度
 * 支持部分数据（根据订阅的传感器类型动态调整）
 */

/**
 * 计算舒适度指数（0-100）
 * @param {number} temperature 温度（°C），可为 null
 * @param {number} humidity 湿度（%），可为 null
 * @param {number} pressure 气压（hPa），可为 null
 * @param {Array<string>} availableTypes 可用的传感器类型数组，如 ['temperature', 'humidity']
 * @returns {Object} 舒适度信息
 */
export function calculateComfort(temperature, humidity, pressure, availableTypes = null) {
  // 如果没有指定可用类型，则根据实际数据判断
  if (!availableTypes) {
    availableTypes = []
    if (temperature !== null && temperature !== undefined) availableTypes.push('temperature')
    if (humidity !== null && humidity !== undefined) availableTypes.push('humidity')
    if (pressure !== null && pressure !== undefined) availableTypes.push('pressure')
  }

  // 如果没有可用数据，返回未知状态
  if (availableTypes.length === 0) {
    return {
      score: 0,
      level: 'unknown',
      emoji: '❓',
      message: '数据不完整',
      suggestions: ['等待传感器数据...'],
      availableTypes: []
    }
  }

  // 温度舒适度评分（0-40分）
  let tempScore = 0
  let tempLevel = 'normal'
  if (temperature >= 20 && temperature <= 26) {
    // 最舒适温度范围
    tempScore = 40
    tempLevel = 'perfect'
  } else if (temperature >= 18 && temperature < 20) {
    tempScore = 35
    tempLevel = 'cool'
  } else if (temperature > 26 && temperature <= 28) {
    tempScore = 35
    tempLevel = 'warm'
  } else if (temperature >= 16 && temperature < 18) {
    tempScore = 25
    tempLevel = 'cold'
  } else if (temperature > 28 && temperature <= 30) {
    tempScore = 25
    tempLevel = 'hot'
  } else if (temperature >= 10 && temperature < 16) {
    tempScore = 15
    tempLevel = 'very_cold'
  } else if (temperature > 30 && temperature <= 35) {
    tempScore = 15
    tempLevel = 'very_hot'
  } else {
    tempScore = 5
    tempLevel = temperature < 10 ? 'extreme_cold' : 'extreme_hot'
  }

  // 湿度舒适度评分（0-30分）
  let humidityScore = 0
  let humidityLevel = 'normal'
  if (humidity >= 40 && humidity <= 60) {
    // 最舒适湿度范围
    humidityScore = 30
    humidityLevel = 'perfect'
  } else if (humidity >= 30 && humidity < 40) {
    humidityScore = 25
    humidityLevel = 'dry'
  } else if (humidity > 60 && humidity <= 70) {
    humidityScore = 25
    humidityLevel = 'humid'
  } else if (humidity >= 20 && humidity < 30) {
    humidityScore = 15
    humidityLevel = 'very_dry'
  } else if (humidity > 70 && humidity <= 80) {
    humidityScore = 15
    humidityLevel = 'very_humid'
  } else {
    humidityScore = 5
    humidityLevel = humidity < 20 ? 'extreme_dry' : 'extreme_humid'
  }

  // 气压舒适度评分（0-30分）
  let pressureScore = 0
  let pressureLevel = 'normal'
  // 标准大气压约1013.25 hPa，正常范围 980-1030
  if (pressure >= 1000 && pressure <= 1020) {
    pressureScore = 30
    pressureLevel = 'perfect'
  } else if (pressure >= 990 && pressure < 1000) {
    pressureScore = 25
    pressureLevel = 'low'
  } else if (pressure > 1020 && pressure <= 1030) {
    pressureScore = 25
    pressureLevel = 'high'
  } else if (pressure >= 980 && pressure < 990) {
    pressureScore = 15
    pressureLevel = 'very_low'
  } else if (pressure > 1030 && pressure <= 1040) {
    pressureScore = 15
    pressureLevel = 'very_high'
  } else {
    pressureScore = 5
    pressureLevel = pressure < 980 ? 'extreme_low' : 'extreme_high'
  }

  // 根据可用数据类型动态调整评分权重
  // 计算总分和满分
  let totalScore = 0
  let maxScore = 0

  if (availableTypes.includes('temperature')) {
    totalScore += tempScore
    maxScore += 40
  }
  if (availableTypes.includes('humidity')) {
    totalScore += humidityScore
    maxScore += 30
  }
  if (availableTypes.includes('pressure')) {
    totalScore += pressureScore
    maxScore += 30
  }

  // 如果没有数据，返回未知状态
  if (maxScore === 0) {
    return {
      score: 0,
      level: 'unknown',
      emoji: '❓',
      message: '数据不完整',
      suggestions: ['等待传感器数据...'],
      availableTypes: []
    }
  }

  // 将分数归一化到0-100分（基于实际满分）
  // 例如：如果只有温度，满分是40，需要归一化到100
  const normalizedScore = Math.round((totalScore / maxScore) * 100)

  // 确定舒适度等级（基于归一化后的分数）
  let level = 'unknown'
  let emoji = '❓'
  let message = ''
  let suggestions = []

  if (normalizedScore >= 85) {
    level = 'excellent'
    emoji = '😊'
    message = '环境非常舒适！'
    suggestions = ['当前环境条件理想，适合长时间活动', '保持当前环境状态']
  } else if (normalizedScore >= 70) {
    level = 'good'
    emoji = '🙂'
    message = '环境较为舒适'
    suggestions = getSuggestions(tempLevel, humidityLevel, pressureLevel, availableTypes)
  } else if (normalizedScore >= 50) {
    level = 'moderate'
    emoji = '😐'
    message = '环境一般，需要注意'
    suggestions = getSuggestions(tempLevel, humidityLevel, pressureLevel, availableTypes)
  } else if (normalizedScore >= 30) {
    level = 'poor'
    emoji = '😕'
    message = '环境不太舒适，建议调整'
    suggestions = getSuggestions(tempLevel, humidityLevel, pressureLevel, availableTypes)
  } else {
    level = 'bad'
    emoji = '😰'
    message = '环境不舒适，需要立即改善'
    suggestions = getSuggestions(tempLevel, humidityLevel, pressureLevel, availableTypes)
  }

  // 构建详情对象（只包含有数据的维度）
  const details = {}
  if (availableTypes.includes('temperature')) {
    details.temperature = {
      value: temperature,
      score: tempScore,
      level: tempLevel
    }
  }
  if (availableTypes.includes('humidity')) {
    details.humidity = {
      value: humidity,
      score: humidityScore,
      level: humidityLevel
    }
  }
  if (availableTypes.includes('pressure')) {
    details.pressure = {
      value: pressure,
      score: pressureScore,
      level: pressureLevel
    }
  }

  return {
    score: normalizedScore,
    rawScore: totalScore,
    maxScore: maxScore,
    level,
    emoji,
    message,
    suggestions,
    availableTypes: [...availableTypes],
    details
  }
}

/**
 * 获取改善建议
 * @param {string} tempLevel 温度等级
 * @param {string} humidityLevel 湿度等级
 * @param {string} pressureLevel 气压等级
 * @param {Array<string>} availableTypes 可用的传感器类型
 */
function getSuggestions(tempLevel, humidityLevel, pressureLevel, availableTypes = ['temperature', 'humidity', 'pressure']) {
  const suggestions = []

  // 温度建议（仅在订阅了温度时显示）
  if (availableTypes.includes('temperature')) {
    if (tempLevel === 'very_cold' || tempLevel === 'extreme_cold') {
      suggestions.push('温度过低，建议开启暖气或增加衣物')
    } else if (tempLevel === 'cold') {
      suggestions.push('温度偏低，建议适当保暖')
    } else if (tempLevel === 'very_hot' || tempLevel === 'extreme_hot') {
      suggestions.push('温度过高，建议开启空调或增加通风')
    } else if (tempLevel === 'hot') {
      suggestions.push('温度偏高，建议开启风扇或增加通风')
    } else if (tempLevel === 'warm') {
      suggestions.push('温度稍高，建议适当通风')
    }
  }

  // 湿度建议（仅在订阅了湿度时显示）
  if (availableTypes.includes('humidity')) {
    if (humidityLevel === 'very_dry' || humidityLevel === 'extreme_dry') {
      suggestions.push('湿度过低，建议使用加湿器或放置水盆')
    } else if (humidityLevel === 'dry') {
      suggestions.push('湿度偏低，建议适当增加湿度')
    } else if (humidityLevel === 'very_humid' || humidityLevel === 'extreme_humid') {
      suggestions.push('湿度过高，建议使用除湿器或增加通风')
    } else if (humidityLevel === 'humid') {
      suggestions.push('湿度偏高，建议适当除湿或通风')
    }
  }

  // 气压建议（仅在订阅了气压时显示）
  if (availableTypes.includes('pressure')) {
    if (pressureLevel === 'very_low' || pressureLevel === 'extreme_low') {
      suggestions.push('气压偏低，可能有天气变化，注意关注天气预报')
    } else if (pressureLevel === 'low') {
      suggestions.push('气压稍低，注意天气变化')
    } else if (pressureLevel === 'very_high' || pressureLevel === 'extreme_high') {
      suggestions.push('气压偏高，天气稳定，适合户外活动')
    } else if (pressureLevel === 'high') {
      suggestions.push('气压较高，天气条件良好')
    }
  }

  if (suggestions.length === 0) {
    suggestions.push('环境条件良好，保持当前状态')
  }

  return suggestions
}

/**
 * 计算历史平均舒适度
 * @param {Array} historyData 历史数据数组，每个元素包含 temperature, humidity, pressure
 * @param {Array<string>} availableTypes 可用的传感器类型
 */
export function calculateAverageComfort(historyData, availableTypes = null) {
  if (!historyData || historyData.length === 0) {
    return null
  }

  // 如果没有指定可用类型，从数据中推断
  if (!availableTypes || availableTypes.length === 0) {
    availableTypes = []
    const firstItem = historyData[0]
    if (firstItem.temperature !== null && firstItem.temperature !== undefined) {
      availableTypes.push('temperature')
    }
    if (firstItem.humidity !== null && firstItem.humidity !== undefined) {
      availableTypes.push('humidity')
    }
    if (firstItem.pressure !== null && firstItem.pressure !== undefined) {
      availableTypes.push('pressure')
    }
  }

  if (availableTypes.length === 0) {
    return null
  }

  let totalScore = 0
  let count = 0

  historyData.forEach(item => {
    const comfort = calculateComfort(
      item.temperature,
      item.humidity,
      item.pressure,
      availableTypes
    )
    if (comfort.score > 0) {
      totalScore += comfort.score
      count++
    }
  })

  if (count === 0) {
    return null
  }

  const avgScore = totalScore / count
  let level = 'unknown'
  let emoji = '❓'

  if (avgScore >= 85) {
    level = 'excellent'
    emoji = '😊'
  } else if (avgScore >= 70) {
    level = 'good'
    emoji = '🙂'
  } else if (avgScore >= 50) {
    level = 'moderate'
    emoji = '😐'
  } else if (avgScore >= 30) {
    level = 'poor'
    emoji = '😕'
  } else {
    level = 'bad'
    emoji = '😰'
  }

  return {
    score: Math.round(avgScore),
    level,
    emoji,
    count,
    availableTypes: [...availableTypes]
  }
}

