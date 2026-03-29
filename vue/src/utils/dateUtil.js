export function convertDDMMYYYYToYYYYMMDD(date) {
  if (!date) return date
  const parts = date.split('/')
  if (parts.length === 3) {
    return `${parts[2]}/${parts[1]}/${parts[0]}`
  }
  return date
}

export function convertYYYYMMDDToDDMMYYYY(date) {
  if (!date) return date
  const parts = date.split('/')
  if (parts.length === 3) {
    return `${parts[2]}/${parts[1]}/${parts[0]}`
  }
  return date
}
