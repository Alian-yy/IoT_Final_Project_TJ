/**
 * 舒适度计算工具
 * 综合考虑温度、湿度、压力三个维度
 */

/**
 * 计算舒适度指数（0-100）
 * @param {number} temperature 温度（°C）
 * @param {number} humidity 湿度（%）
 * @param {number} pressure 气压（hPa）
 * @returns {Object} 舒适度信息
 */
export function calculateComfort(temperature, humidity, pressure) {
  if (temperature === null || humidity === null || pressure === null) {
    return {
      score: 0,
      level: 'unknown',
      emoji: '❓',
      message: '数据不完整',
      suggestions: ['等待传感器数据...']
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

  // 综合评分
  const totalScore = tempScore + humidityScore + pressureScore

  // 确定舒适度等级
  let level = 'unknown'
  let emoji = '❓'
  let message = ''
  let suggestions = []

  if (totalScore >= 85) {
    level = 'excellent'
    emoji = '😊'
    message = '环境非常舒适！'
    suggestions = ['当前环境条件理想，适合长时间活动', '保持当前环境状态']
  } else if (totalScore >= 70) {
    level = 'good'
    emoji = '🙂'
    message = '环境较为舒适'
    suggestions = getSuggestions(tempLevel, humidityLevel, pressureLevel)
  } else if (totalScore >= 50) {
    level = 'moderate'
    emoji = '😐'
    message = '环境一般，需要注意'
    suggestions = getSuggestions(tempLevel, humidityLevel, pressureLevel)
  } else if (totalScore >= 30) {
    level = 'poor'
    emoji = '😕'
    message = '环境不太舒适，建议调整'
    suggestions = getSuggestions(tempLevel, humidityLevel, pressureLevel)
  } else {
    level = 'bad'
    emoji = '😰'
    message = '环境不舒适，需要立即改善'
    suggestions = getSuggestions(tempLevel, humidityLevel, pressureLevel)
  }

  return {
    score: totalScore,
    level,
    emoji,
    message,
    suggestions,
    details: {
      temperature: {
        value: temperature,
        score: tempScore,
        level: tempLevel
      },
      humidity: {
        value: humidity,
        score: humidityScore,
        level: humidityLevel
      },
      pressure: {
        value: pressure,
        score: pressureScore,
        level: pressureLevel
      }
    }
  }
}

/**
 * 获取改善建议
 */
function getSuggestions(tempLevel, humidityLevel, pressureLevel) {
  const suggestions = []

  // 温度建议
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

  // 湿度建议
  if (humidityLevel === 'very_dry' || humidityLevel === 'extreme_dry') {
    suggestions.push('湿度过低，建议使用加湿器或放置水盆')
  } else if (humidityLevel === 'dry') {
    suggestions.push('湿度偏低，建议适当增加湿度')
  } else if (humidityLevel === 'very_humid' || humidityLevel === 'extreme_humid') {
    suggestions.push('湿度过高，建议使用除湿器或增加通风')
  } else if (humidityLevel === 'humid') {
    suggestions.push('湿度偏高，建议适当除湿或通风')
  }

  // 气压建议
  if (pressureLevel === 'very_low' || pressureLevel === 'extreme_low') {
    suggestions.push('气压偏低，可能有天气变化，注意关注天气预报')
  } else if (pressureLevel === 'low') {
    suggestions.push('气压稍低，注意天气变化')
  } else if (pressureLevel === 'very_high' || pressureLevel === 'extreme_high') {
    suggestions.push('气压偏高，天气稳定，适合户外活动')
  } else if (pressureLevel === 'high') {
    suggestions.push('气压较高，天气条件良好')
  }

  if (suggestions.length === 0) {
    suggestions.push('环境条件良好，保持当前状态')
  }

  return suggestions
}

/**
 * 计算历史平均舒适度
 */
export function calculateAverageComfort(historyData) {
  if (!historyData || historyData.length === 0) {
    return null
  }

  let totalScore = 0
  let count = 0

  historyData.forEach(item => {
    const comfort = calculateComfort(
      item.temperature,
      item.humidity,
      item.pressure
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
    count
  }
}

