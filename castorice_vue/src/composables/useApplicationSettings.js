import { reactive } from 'vue'

export const application = reactive({ config: null, error: '', models: {}, loaded: false, pendingRoutes: {} })
export const defaultAppearance = { user_name: '你', assistant_name: 'Castorice', user_avatar: '', assistant_avatar: '', avatar_shape: 'circle', background_mode: 'default', background_asset: '', background_color: '#100b25', background_fit: 'cover', background_dim: 0, background_blur: 0, pause_hidden: true, reduce_motion: false, font_size: 16, music_enabled: true, music_volume: .45, send_key: 'enter', system_prompt: '' }
export async function settingsRequest(path = '', options = {}) {
  const response = await fetch('/api/settings' + path, options)
  let result
  try { result = await response.json() } catch { throw new Error('后台设置服务不可用，请检查后台是否已更新并启动') }
  if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : '设置请求失败')
  return result
}
let pendingLoad
export async function loadApplicationSettings() {
  if (pendingLoad) return pendingLoad
  pendingLoad = (async () => {
    try { application.config = await settingsRequest(); application.error = ''; application.loaded = true }
    catch (error) { application.error = error.message }
  })().finally(() => { pendingLoad = null })
  return pendingLoad
}
export async function saveApplicationSettings(config) {
  const result = await settingsRequest('', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(config) })
  application.config = result
  application.error = ''
  return result
}
export async function refreshModels(connection) {
  const result = await settingsRequest('/models', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ connection }) })
  application.models[connection] = result.models
  return result
}
export function routeFor(module) { return application.config?.modules[module] }
export function appearance() { return application.config?.appearance || defaultAppearance }
