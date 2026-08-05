const EDUCATION_ERROR_MESSAGES = {
  asset_storage_capacity_exceeded: '文件超过当前存储容量，请压缩文件后重试或联系管理员。',
  asset_size_invalid: '文件大小不符合要求，单个文件不能超过 25 MB。',
  asset_extension_not_allowed: '不支持该文件类型，请选择页面列出的格式。',
  asset_mime_not_allowed: '文件内容与扩展名不匹配，请确认文件未损坏。',
  file_required: '请选择需要上传的文件。',
}

export function educationErrorMessage(error, fallback = '操作失败，请稍后重试') {
  const payload = (error && error.response && error.response.data) || error || {}
  const code = payload.error_code || payload.code
  if (code && EDUCATION_ERROR_MESSAGES[code]) return EDUCATION_ERROR_MESSAGES[code]
  return payload.error || payload.message || fallback
}

export { EDUCATION_ERROR_MESSAGES }
