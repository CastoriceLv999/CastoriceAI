import test from 'node:test'
import assert from 'node:assert/strict'
import { normalizePreferences, resetParameters, DEFAULT_PREFERENCES } from './preferences.js'

test('preferences accept actual model parameter ranges and booleans', () => {
  const values = normalizePreferences({ alpha: .7, studioCount: 6, videoDuration: -1, videoResolution: '480P', videoRatio: 'adaptive', videoAudio: false, videoPromptExtend: false, imageWatermark: true, imagePromptExtend: false, imageNegativePrompt: 'blur' })
  assert.equal(values.alpha, .7)
  assert.equal(values.studioCount, 6)
  assert.equal(values.videoDuration, -1)
  assert.equal(values.videoAudio, false)
  assert.equal(values.videoPromptExtend, false)
  assert.equal(values.imageWatermark, true)
  assert.equal(values.imagePromptExtend, false)
  assert.equal(values.imageNegativePrompt, 'blur')
})
test('unsupported, corrupted or legacy duplicate options fall back to safe defaults', () => {
  const values = normalizePreferences({ alpha: 100, videoRatio: '9:21', videoDuration: 1, studioCount: 99, thinkingMode: 'false', imageMode: 'auto' })
  for (const key of ['alpha', 'videoRatio', 'videoDuration', 'studioCount', 'thinkingMode', 'imageMode']) assert.equal(values[key], DEFAULT_PREFERENCES[key])
})
test('resetting a page leaves other modes and shared appearance intact', () => {
  const values = normalizePreferences({ alpha: .5, studioCount: 6, videoDuration: 30, enableSearch: false })
  resetParameters(values, 'image')
  assert.equal(values.studioCount, 1)
  assert.equal(values.videoDuration, 30)
  assert.equal(values.enableSearch, false)
  assert.equal(values.alpha, .5)
})
