import test from 'node:test'
import assert from 'node:assert/strict'
import { effectScope } from 'vue'
import { usePreferences } from './usePreferences.js'

test('preferences are restored and saved without persisting sidebar open state', () => {
  let saved
  const scope = effectScope()
  const prefs = scope.run(() => usePreferences({ getItem: () => '{"thinkingMode":true,"videoAudio":false,"sidebarCollapsed":false}', setItem: (key, value) => { saved = JSON.parse(value) } }))
  assert.equal(prefs.values.thinkingMode, true)
  assert.equal(prefs.values.videoAudio, false)
  prefs.values.videoDuration = 30
  scope.stop()
  assert.equal(saved.videoDuration, 30)
  assert.equal('sidebarCollapsed' in saved, false)
})
test('preferences storage failures are reported without blocking controls', () => {
  const scope = effectScope()
  const prefs = scope.run(() => usePreferences({ getItem() { throw Error('denied') }, setItem() { throw Error('denied') } }))
  assert.ok(prefs.error.value)
  prefs.values.videoAudio = false
  scope.stop()
  assert.ok(prefs.error.value.includes('设置未能保存'))
})
