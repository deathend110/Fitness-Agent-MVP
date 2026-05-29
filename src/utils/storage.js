/**
 * 统一封装 localStorage 读取，兼容空值、非法 JSON 和非浏览器环境。
 */
export function loadStorage(key, fallback) {
  if (typeof window === 'undefined' || !window.localStorage) {
    return fallback
  }

  const rawValue = window.localStorage.getItem(key)

  if (rawValue === null) {
    return fallback
  }

  try {
    return JSON.parse(rawValue)
  } catch (error) {
    console.warn(`[storage] 读取 ${key} 失败，已回退到默认数据。`, error)
    return fallback
  }
}

/**
 * 统一封装 localStorage 写入，保持所有业务数据都以 JSON 形式保存。
 */
export function saveStorage(key, value) {
  if (typeof window === 'undefined' || !window.localStorage) {
    return
  }

  window.localStorage.setItem(key, JSON.stringify(value))
}
