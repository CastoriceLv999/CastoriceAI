import test from 'node:test'
import assert from 'node:assert/strict'
import { renderMarkdown, highlightCode } from './markdown.js'

test('code keeps empty collections, calls and operators', () => {
  const html = renderMarkdown('```python\nx = []\nf()\ny = {}\nz = 2 ** 3\n```')
  assert.ok(html.replace(/<[^>]*>/g, '').includes('x = []\nf()\ny = {}\nz = 2 ** 3'))
  assert.ok(!html.includes('<strong>'))
})

test('headings, tables, lists and blockquotes render as semantic elements', () => {
  const html = renderMarkdown('# Heading\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n- Item\n\n> Quote')
  for (const tag of ['h1', 'table', 'ul', 'blockquote']) assert.ok(html.includes(`<${tag}`))
})

test('unsafe links are inert and external links have safe attributes', () => {
  assert.ok(!renderMarkdown('[run](javascript:alert(1))').includes('href="javascript:'))
  const html = renderMarkdown('[source](https://example.com)')
  assert.ok(html.includes('rel="noopener noreferrer"'))
  assert.ok(html.includes('target="_blank"'))
})

test('highlighting escapes HTML, highlights known languages and handles unknown ones', () => {
  assert.ok(highlightCode('const n = 2;', 'javascript').includes('hljs-keyword'))
  assert.ok(!highlightCode('<script>alert(1)</script>', 'unknown').includes('<script>'))
  assert.equal(highlightCode('x = []', 'unknown'), 'x = []')
})
test('source HTML is escaped', () => {
  assert.ok(!renderMarkdown('<img src=x onerror=alert(1)>').includes('<img'))
})
