import test from 'node:test'
import assert from 'node:assert/strict'
import { replayConversation, requestFiles, readConversation, writeConversation } from './conversation.js'

const turns = [{ role: 'user', content: 'old question', files: [{ file_id: 'image-1', type: 'image' }] }, { role: 'assistant', content: 'old answer' }, { role: 'user', content: 'later question' }, { role: 'assistant', content: 'later answer' }]

test('editing creates a request from the chosen question and retains its attachments', () => {
  const result = replayConversation(turns, 0, 'new question')
  assert.equal(result.messages.length, 1)
  assert.equal(result.messages[0].content, 'new question')
  assert.deepEqual(result.messages[0].files, turns[0].files)
  assert.equal(turns.length, 4)
  assert.equal(turns[0].content, 'old question')
})
test('editing can remove obsolete attachments without mutating the old conversation', () => {
  assert.deepEqual(replayConversation(turns, 0, 'retry without file', []).messages[0].files, [])
  assert.equal(turns[0].files.length, 1)
})
test('regeneration locates the preceding user and excludes later turns', () => {
  assert.deepEqual(replayConversation(turns, 1).messages, [turns[0]])
  assert.throws(() => replayConversation([{ role: 'assistant', content: 'orphan' }], 0), /未找到/)
  assert.throws(() => replayConversation(turns, 0, ' '), /不能为空/)
})
test('document context persists across turns while old images are not resent', () => {
  const messages = [{ role: 'user', content: 'doc', files: [{ file_id: 'doc', type: 'text' }, { file_id: 'old-image', type: 'image' }] }, { role: 'user', content: 'follow-up', files: [{ file_id: 'new-image', type: 'image' }] }]
  assert.deepEqual(requestFiles(messages), ['new-image', 'doc'])
  assert.deepEqual(requestFiles(messages, true), ['new-image'])
})
test('refresh restores draft, attachments, backup and interrupted partial output', () => {
  const data = new Map()
  const storage = { getItem: key => data.get(key), setItem: (key, value) => data.set(key, value) }
  writeConversation(storage, 'chat', { messages: [turns[0]], attachments: [{ file_id: 'doc', filename: 'doc.txt' }], draft: 'unsent', backup: turns, streaming: { role: 'assistant', content: 'partial' } })
  const restored = readConversation(storage, 'chat')
  assert.equal(restored.messages.at(-1).content, 'partial')
  assert.equal(restored.messages.at(-1).isInterrupted, true)
  assert.equal(restored.draft, 'unsent')
  assert.equal(restored.attachments.length, 1)
  assert.deepEqual(restored.backup, turns)
})
test('corrupt or inaccessible storage does not crash or erase the old data', () => {
  assert.ok(readConversation({ getItem: () => '{bad json' }, 'chat').error)
  assert.ok(readConversation({ getItem() { throw Error('denied') } }, 'chat').error)
})
