import { reactive, ref, watch, onScopeDispose } from 'vue'
import { normalizePreferences, resetParameters } from '../utils/preferences.js'

export function usePreferences(storage) {
  const key = 'castorice_preferences_v1'
  const error = ref('')
  let initial
  try { storage ??= globalThis.localStorage; initial = JSON.parse(storage.getItem(key) || '{}') }
  catch { error.value = '设置无法读取，已使用默认参数。' }
  const values = reactive(normalizePreferences(initial))
  let timer
  function save() {
    clearTimeout(timer)
    timer = null
    try { storage.setItem(key, JSON.stringify(values)); error.value = '' }
    catch { error.value = '设置未能保存，刷新后可能丢失本次修改。' }
  }
  watch(values, () => { if (!timer) timer = setTimeout(save, 150) }, { deep: true })
  const page = typeof window === 'undefined' ? null : window
  page?.addEventListener('pagehide', save)
  onScopeDispose(() => { save(); page?.removeEventListener('pagehide', save) })
  return { values, error, reset: group => resetParameters(values, group) }
}
