import test from 'node:test'
import assert from 'node:assert/strict'
import { messageParts } from './messageParts.js'

test('separates prose from code without changing copyable source', () => {
  const parts = messageParts('Example\n```javascript\nconst a = [];\nf({});\n```\nDone')
  assert.deepEqual(parts, [
    { type: 'text', language: 'text', content: 'Example' },
    { type: 'code', language: 'javascript', content: 'const a = [];\nf({});' },
    { type: 'text', language: 'text', content: 'Done' },
  ])
})
test('unfinished streamed code remains in its code panel', () => {
  assert.equal(messageParts('```python\nx = [')[0].type, 'code')
  assert.equal(messageParts('```python\nx = [')[0].content, 'x = [')
})
test('long fences can contain shorter fences', () => {
  assert.equal(messageParts('````md\n```js\nx()\n```\n````')[0].content, '```js\nx()\n```')
})
test('inline backticks do not start a code panel', () => {
  assert.equal(messageParts('Use `a()` here.')[0].type, 'text')
})
