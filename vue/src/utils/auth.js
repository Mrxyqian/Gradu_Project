const USER_KEY = 'vehic-insur-user'

export const getCurrentUser = () => {
  try {
    return JSON.parse(sessionStorage.getItem(USER_KEY) || '{}')
  } catch (e) {
    return {}
  }
}

export const setCurrentUser = (user) => {
  sessionStorage.setItem(USER_KEY, JSON.stringify(user || {}))
}

export const clearCurrentUser = () => {
  sessionStorage.removeItem(USER_KEY)
}
