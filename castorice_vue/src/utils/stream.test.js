import test from 'node:test'
import assert from 'node:assert/strict'
import { readEvents } from './stream.js'

function response(text, byteByByte = false) {
  const bytes = new TextEncoder().encode(text)
  return new Response(new ReadableStream({ start(controller) {
    if (byteByByte) for (const byte of bytes) controller.enqueue(new Uint8Array([byte]))
    else controller.enqueue(bytes)
    controller.close()
  } }), { headers: { 'Content-Type': 'text/event-stream' } })
}

test('UTF-8 and CRLF split across chunks, final unterminated event', async () => {
  const events = []
  for await (const event of readEvents(response('data: {"content":"你好"}\r\n\r\ndata: {"content":"末尾"}', true))) events.push(event)
  assert.deepEqual(events, [{ content: '你好' }, { content: '末尾' }])
})

test('upstream errors are not swallowed', async () => {
  await assert.rejects(async () => {
    for await (const event of readEvents(response('data: {"error":"quota exhausted"}\n\n'))) void event
  }, /quota exhausted/)
})

test('HTTP error detail is visible', async () => {
  await assert.rejects(async () => {
    for await (const event of readEvents(new Response('{"detail":"missing file"}', { status: 404 }))) void event
  }, /missing file/)
})

test('empty proxy errors explain how to start the backend', async () => {
  await assert.rejects(async () => {
    for await (const event of readEvents(new Response('', { status: 502 }))) void event
  }, /start-dev\.ps1/)
})
