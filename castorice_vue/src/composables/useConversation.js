import { ref, watch, onScopeDispose } from 'vue'
import { checkedResponse, readEvents } from '../utils/stream.js'
import { readConversation, writeConversation, replayConversation, requestFiles, validMessages } from '../utils/conversation.js'

export function useConversation({ storageKey, agent = false, settings, storage, fetchImpl = (...args) => fetch(...args) }) {
  let localStore = storage
  try { localStore ??= globalThis.localStorage } catch {}
  const loaded = localStore ? readConversation(localStore, storageKey) : { messages: [], attachments: [], draft: '', backup: null, error: '浏览器不允许保存会话，当前内容只能保留到页面关闭。' }
  const messages = ref(loaded.messages)
  const attachments = ref(loaded.attachments)
  const draft = ref(loaded.draft)
  const backup = ref(loaded.backup)
  const streamingMsg = ref(null)
  const isBusy = ref(false)
  const saveError = ref(loaded.error || '')
  let controller
  let timer
  function persist() {
    clearTimeout(timer)
    timer = null
    try {
      if (!localStore) throw new Error('Storage unavailable')
      writeConversation(localStore, storageKey, { messages: messages.value, attachments: attachments.value, draft: draft.value, backup: backup.value, streaming: streamingMsg.value })
      saveError.value = ''
    } catch { saveError.value = '自动保存失败，请检查浏览器存储空间；当前页面中的对话仍可继续使用。' }
  }
  function scheduleSave() { if (!timer) timer = setTimeout(persist, 250) }
  watch([messages, attachments, draft, streamingMsg, backup], scheduleSave, { deep: true, flush: 'sync' })
  watch(isBusy, busy => { if (!busy) persist() }, { flush: 'sync' })
  if (loaded.recovered) persist()
  const page = typeof window === 'undefined' ? null : window
  page?.addEventListener('pagehide', persist)
  page?.addEventListener('beforeunload', persist)

  async function generate(text, replay) {
    if (isBusy.value || !text.trim()) return
    const options = settings()
    if (replay) {
      backup.value = JSON.parse(JSON.stringify(messages.value))
      messages.value = replay.messages
    } else {
      backup.value = null
      messages.value.push({ id: crypto.randomUUID(), createdAt: Date.now(), role: 'user', content: text.trim(), files: attachments.value.map(file => ({ ...file })), agentTool: agent ? options.tool : undefined })
      draft.value = ''
    }
    const consumed = attachments.value.map(file => file.file_id)
    const user = messages.value.findLast(message => message.role === 'user')
    isBusy.value = true
    controller = new AbortController()
    streamingMsg.value = { id: crypto.randomUUID(), createdAt: Date.now(), role: 'assistant', content: '', reasoning: '', images: [], searchResults: [], toolInfo: '', toolCalls: [] }
    persist()
    try {
      const payload = {
        ...(options.connection ? { connection: options.connection, model: options.model } : {}),
        messages: [{ role: 'system', content: options.language === 'en-US' ? 'Answer in English.' : '请用中文回答。' },
          ...messages.value.filter(message => !message.isError && !message.isAgentError && !(message.isStopped && !message.content)).map(({ role, content }) => ({ role, content }))],
        files: requestFiles(messages.value, agent),
        ...(agent ? { tool: user.agentTool || options.tool, thinking: true } : { thinking: options.thinking, image_mode: options.image_mode, enable_search: options.enable_search }),
      }
      const response = await fetchImpl(agent ? '/api/agent/stream' : options.stream ? '/api/chat/stream' : '/api/chat', {
        method: 'POST', signal: controller.signal, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
      })
      if (agent || options.stream) {
        for await (const event of readEvents(response)) {
          const result = streamingMsg.value
          result.content += event.content || ''
          result.reasoning += event.reasoning || ''
          result.toolInfo += event.tool_info ? event.tool_info + '\n' : ''
          if (event.images) result.images.push(...event.images)
          if (event.search_results) result.searchResults = event.search_results
          if (event.tool_name) result.toolName = event.tool_name
          if (event.tool_calling !== undefined) result.isToolCalling = event.tool_calling
          if (event.tool_name && event.tool_calling === false && !result.toolCalls.some(tool => tool.tool === event.tool_name)) result.toolCalls.push({ tool: event.tool_name, status: 'done' })
        }
      } else {
        await checkedResponse(response)
        Object.assign(streamingMsg.value, await response.json())
      }
      if (!streamingMsg.value.content.trim() && !streamingMsg.value.images.length) throw new Error('模型未返回有效内容，请重试')
      messages.value.push({ ...streamingMsg.value, isToolCalling: false })
      if (!replay) attachments.value = attachments.value.filter(file => !consumed.includes(file.file_id))
    } catch (error) {
      const stopped = error.name === 'AbortError'
      const partial = streamingMsg.value
      messages.value.push({ ...partial, isToolCalling: false, isStopped: stopped, isError: !stopped, isAgentError: agent && !stopped,
        content: stopped ? partial.content || (options.language === 'en-US' ? 'Generation stopped.' : '已停止生成。') : `${partial.content ? partial.content + '\n\n' : ''}请求失败：${error.message}` })
      if (!replay && !stopped && !draft.value) draft.value = text
    } finally {
      streamingMsg.value = null
      controller = null
      isBusy.value = false
    }
  }
  function send(text) { return generate(text) }
  function editMessage({ index, text, files }) { if (!isBusy.value) return generate(text, replayConversation(messages.value, index, text, files)) }
  function regenerate(index) {
    if (isBusy.value) return
    const replay = replayConversation(messages.value, index)
    return generate(replay.messages.at(-1).content, replay)
  }
  function restorePrevious() {
    if (!isBusy.value && backup.value) { messages.value = backup.value; backup.value = null; persist() }
  }
  function loadSession(value) {
    if (isBusy.value || !validMessages(value)) return
    messages.value = JSON.parse(JSON.stringify(value))
    attachments.value = []
    draft.value = ''
    backup.value = null
    persist()
  }
  function clear() { loadSession([]) }
  function stop() { controller?.abort() }
  onScopeDispose(() => { persist(); stop(); clearTimeout(timer); page?.removeEventListener('pagehide', persist); page?.removeEventListener('beforeunload', persist) })
  return { messages, attachments, draft, backup, streamingMsg, isBusy, saveError, send, editMessage, regenerate, restorePrevious, loadSession, clear, stop, persist }
}
