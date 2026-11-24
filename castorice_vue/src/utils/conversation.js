export function replayConversation(messages, index, editedText, editedFiles) {
  if (!Number.isInteger(index) || index < 0 || index >= messages.length) throw new Error('消息不存在')
  let userIndex = index
  while (userIndex >= 0 && messages[userIndex].role !== 'user') userIndex--
  if (userIndex < 0) throw new Error('未找到需要重新回答的问题')
  const user = messages[userIndex]
  const content = editedText === undefined ? user.content : editedText.trim()
  if (!content) throw new Error('问题不能为空')
  return { messages: [...messages.slice(0, userIndex), { ...user, content, ...(editedFiles ? { files: editedFiles } : {}) }], userIndex }
}

export function requestFiles(messages, agent = false) {
  const lastUser = messages.findLast(message => message.role === 'user')
  const files = [...(lastUser?.files || [])]
  if (!agent) {
    for (const message of messages) {
      if (message.role === 'user') files.push(...(message.files || []).filter(file => file.type === 'text'))
    }
  }
  return [...new Set(files.map(file => file.file_id).filter(Boolean))]
}

export function validMessages(messages) {
  return Array.isArray(messages) && messages.every(message => message && ['user', 'assistant'].includes(message.role) && typeof message.content === 'string')
}

export function readConversation(storage, key) {
  try {
    const raw = storage.getItem(key)
    if (!raw) return { messages: [], attachments: [], draft: '', backup: null }
    const state = JSON.parse(raw)
    if (state.version !== 1 || !validMessages(state.messages)) throw new Error('保存的会话格式不正确')
    if (state.streaming && (state.streaming.role !== 'assistant' || typeof state.streaming.content !== 'string')) throw new Error('保存的生成内容格式不正确')
    const messages = [...state.messages]
    if (state.streaming) messages.push({ ...state.streaming, isToolCalling: false, isStopped: true, isInterrupted: true, content: state.streaming.content || '上次生成已中断，请点击重新生成。' })
    return {
      messages,
      attachments: Array.isArray(state.attachments) ? state.attachments.filter(file => file && typeof file.file_id === 'string' && typeof file.filename === 'string') : [],
      draft: typeof state.draft === 'string' ? state.draft : '',
      backup: validMessages(state.backup) ? state.backup : null,
      recovered: !!state.streaming,
    }
  } catch {
    return { messages: [], attachments: [], draft: '', backup: null, error: '无法读取本地会话；原保存数据未被删除。' }
  }
}

export function writeConversation(storage, key, state) {
  storage.setItem(key, JSON.stringify({ version: 1, savedAt: Date.now(), ...state }))
}
