const formatNumber = (n) => {
  n = n.toString()
  return n[1] ? n : `0${n}`
}

const formatTime = (date) => {
  const year = date.getFullYear()
  const month = date.getMonth() + 1
  const day = date.getDate()
  const hour = date.getHours()
  const minute = date.getMinutes()
  const second = date.getSeconds()

  return `${[year, month, day].map(formatNumber).join('/')} ${[hour, minute, second].map(formatNumber).join(':')}`
}

const parseApiDateTime = (value) => {
  if (!value || typeof value !== 'string') return null

  const normalized = value.trim().replace(' ', 'T')
  const match = normalized.match(
    /^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2})(?::(\d{2}))?)?$/
  )

  if (match) {
    const [, year, month, day, hour = '00', minute = '00', second = '00'] = match
    return new Date(
      Number(year),
      Number(month) - 1,
      Number(day),
      Number(hour),
      Number(minute),
      Number(second)
    )
  }

  const fallback = new Date(value)
  return Number.isNaN(fallback.getTime()) ? null : fallback
}

const formatApiDateTime = (value) => {
  const date = value instanceof Date ? value : parseApiDateTime(value)
  if (!date || Number.isNaN(date.getTime())) return ''

  return `${date.getFullYear()}-${formatNumber(date.getMonth() + 1)}-${formatNumber(date.getDate())}T${formatNumber(date.getHours())}:${formatNumber(date.getMinutes())}:${formatNumber(date.getSeconds())}`
}

const formatDisplayDateTime = (value) => {
  const date = value instanceof Date ? value : parseApiDateTime(value)
  if (!date || Number.isNaN(date.getTime())) return '未设置'

  return `${date.getMonth() + 1}月${date.getDate()}日 ${formatNumber(date.getHours())}:${formatNumber(date.getMinutes())}`
}

module.exports = {
  formatTime,
  parseApiDateTime,
  formatApiDateTime,
  formatDisplayDateTime,
}
