export async function checkedResponse(response) {
  if (!response.ok) {
    const body = await response.text()
    let message = body
    try { message = JSON.parse(body).detail || body } catch {}
    if (typeof message === 'string' && !message.trim()) {
      message = [502, 503, 504].includes(response.status)
        ? '无法连接 AI 后端服务，请先运行项目根目录的 start-dev.ps1，同时启动前后端。'
        : `请求失败（HTTP ${response.status}）`
    }
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message))
  }
  return response
}

// Handles UTF-8/chunk boundaries, CRLF, multiline events, and a final unterminated event.
export async function* readEvents(response) {
  await checkedResponse(response)
  if (!response.headers.get('content-type')?.includes('text/event-stream')) {
    throw new Error('服务器未返回事件流，请检查后端错误')
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let lines = []
  const parse = () => {
    const data = lines.filter(x => x.startsWith('data:')).map(x => x.slice(5).trimStart()).join('\n')
    lines = []
    if (!data) return null
    if (data === '[DONE]') return { done: true }
    const event = JSON.parse(data)
    if (event.error) throw new Error(event.error)
    return { event }
  }
  try {
    while (true) {
      const { value, done } = await reader.read()
      buffer += decoder.decode(value, { stream: !done })
      if (done && buffer && !buffer.endsWith('\n')) buffer += '\n'
      let index
      while ((index = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0, index).replace(/\r$/, '')
        buffer = buffer.slice(index + 1)
        if (line) lines.push(line)
        else {
          const result = parse()
          if (result?.done) return
          if (result) yield result.event
        }
      }
      if (done) {
        const result = parse()
        if (result && !result.done) yield result.event
        return
      }
    }
  } finally {
    await reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}
