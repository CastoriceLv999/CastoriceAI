import test from 'node:test'
import assert from 'node:assert/strict'
import { effectScope } from 'vue'
import { useConversation } from './useConversation.js'

function setup(options = {}) {
  const scope = effectScope()
  const data = new Map()
  const requests = []
  const storage = { getItem: key => data.get(key), setItem: (key, value) => data.set(key, value) }
  const conversation = scope.run(() => useConversation({ storageKey: 'test', storage, settings: () => ({ stream: false, language: 'zh-CN', tool: 'auto' }),
    fetchImpl: async (url, init) => { requests.push(JSON.parse(init.body)); return new Response('{"content":"test answer"}') }, ...options }))
  return { scope, data, storage, requests, conversation }
}

test('selected connection and model are sent with each chat request', async () => {
  let route = { connection: 'ollama', model: 'qwen3.5:4b' }
  const { scope, requests, conversation: c } = setup({ settings: () => ({ stream: false, language: 'zh-CN', ...route }) })
  try {
    await c.send('local question')
    assert.equal(requests[0].connection, 'ollama')
    assert.equal(requests[0].model, 'qwen3.5:4b')
    route = { connection: 'bailian', model: 'cloud-model' }
    await c.send('cloud question')
    assert.equal(requests[1].connection, 'bailian')
    assert.equal(requests[1].model, 'cloud-model')
  } finally { scope.stop() }
})

test('chat send, editing, regeneration and restore use the correct context and persist', async () => {
  const { scope, conversation: c, data, requests } = setup()
  try {
    c.attachments.value = [{ file_id: 'ref', filename: 'ref.png', type: 'image' }]
    await c.send('first')
    await c.send('second')
    assert.equal(c.messages.value.length, 4)
    await c.editMessage({ index: 0, text: 'edited' })
    assert.equal(c.messages.value.length, 2)
    assert.deepEqual(requests.at(-1).messages.filter(m => m.role !== 'system').map(m => m.content), ['edited'])
    assert.deepEqual(requests.at(-1).files, ['ref'])
    c.restorePrevious()
    assert.equal(c.messages.value.length, 4)
    assert.equal(c.messages.value[0].content, 'first')
    await c.regenerate(1)
    assert.equal(c.messages.value.length, 2)
    assert.equal(c.backup.value.length, 4)
    const saved = JSON.parse(data.get('test'))
    assert.equal(saved.messages.length, 2)
    assert.equal(saved.streaming, null)
    c.clear()
    assert.equal(JSON.parse(data.get('test')).messages.length, 0)
  } finally { scope.stop() }
})

test('failed send retains draft and attachments, retry does not send the failure text', async () => {
  let fail = true
  let request
  const { scope, conversation: c } = setup({ fetchImpl: async (url, init) => {
    request = JSON.parse(init.body)
    return fail ? new Response('{"detail":"quota exhausted"}', { status: 502 }) : new Response('{"content":"recovered"}')
  } })
  try {
    c.attachments.value = [{ file_id: 'doc', filename: 'doc.txt', type: 'text' }]
    await c.send('question')
    assert.equal(c.draft.value, 'question')
    assert.equal(c.attachments.value.length, 1)
    assert.equal(c.messages.value.at(-1).isError, true)
    fail = false
    await c.regenerate(1)
    assert.deepEqual(request.messages.filter(m => m.role !== 'system').map(m => m.content), ['question'])
    assert.equal(c.messages.value.at(-1).content, 'recovered')
  } finally { scope.stop() }
})

test('agent regeneration preserves the original selected tool and image result', async () => {
  let request
  const { scope, conversation: c } = setup({ agent: true, fetchImpl: async (url, init) => {
    request = JSON.parse(init.body)
    return new Response('data: {"images":[{"url":"https://example.com/a.png"}]}\n\ndata: [DONE]\n\n', { headers: { 'Content-Type': 'text/event-stream' } })
  } })
  try {
    c.loadSession([{ role: 'user', content: 'find', agentTool: 'search_image' }, { role: 'assistant', content: 'old' }])
    await c.regenerate(1)
    assert.equal(request.tool, 'search_image')
    assert.equal(c.messages.value.at(-1).images.length, 1)
  } finally { scope.stop() }
})

test('storage failure is visible and does not prevent a successful response', async () => {
  const { scope, conversation: c } = setup({ storage: { getItem: () => null, setItem() { throw Error('quota') } } })
  try {
    await c.send('question')
    assert.ok(c.saveError.value.includes('自动保存失败'))
    assert.equal(c.messages.value.at(-1).content, 'test answer')
  } finally { scope.stop() }
})

test('restoring an interrupted conversation does not send a model request', () => {
  let calls = 0
  const saved = JSON.stringify({ version: 1, messages: [{ role: 'user', content: 'q' }], streaming: { role: 'assistant', content: 'partial' } })
  const { scope, conversation: c } = setup({ storage: { getItem: () => saved, setItem() {} }, fetchImpl: () => { calls++ } })
  try {
    assert.equal(c.messages.value.at(-1).isInterrupted, true)
    assert.equal(c.isBusy.value, false)
    assert.equal(calls, 0)
  } finally { scope.stop() }
})

test('stopping a pending request exits busy state and persists a stopped reply', async () => {
  const { scope, conversation: c, data } = setup({ fetchImpl: (url, init) => new Promise((resolve, reject) => {
    init.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
  }) })
  try {
    const pending = c.send('question')
    assert.equal(c.isBusy.value, true)
    c.stop()
    await pending
    assert.equal(c.isBusy.value, false)
    assert.equal(c.messages.value.at(-1).isStopped, true)
    assert.equal(JSON.parse(data.get('test')).streaming, null)
  } finally { scope.stop() }
})
