export const DEFAULT_PREFERENCES = Object.freeze({
  alpha: 0.05, streamMode: true, thinkingMode: false, imageMode: 'vision', enableSearch: true,
  studioMode: 'image', studioSize: '1024*1024', studioCount: 1,
  imageWatermark: false, imagePromptExtend: true, imageNegativePrompt: '',
  videoResolution: '1080P', videoRatio: '16:9', videoDuration: 5,
  videoWatermark: true, videoPromptExtend: true, videoAudio: true, agentTool: 'auto',
})
export const IMAGE_SIZES = ['1024*1024', '768*1152', '1152*768', '960*1280', '1280*960', '720*1280', '1280*720', '1344*576']
export const VIDEO_RATIOS = ['adaptive', '16:9', '9:16', '1:1', '4:3', '3:4', '21:9']
const enums = {
  imageMode: ['vision', 'ocr'], studioMode: ['image', 'video'], studioSize: IMAGE_SIZES,
  videoResolution: ['480P', '720P', '1080P'], videoRatio: VIDEO_RATIOS,
  agentTool: ['auto', 'search', 'web_extract', 'code', 'search_image', 'image_search'],
}
export function normalizePreferences(value = {}) {
  const result = { ...DEFAULT_PREFERENCES }
  if (!value || typeof value !== 'object') return result
  for (const key of Object.keys(result)) {
    const input = value[key]
    if (typeof result[key] === 'boolean') { if (typeof input === 'boolean') result[key] = input }
    else if (enums[key]) { if (enums[key].includes(input)) result[key] = input }
    else if (key === 'alpha' && Number.isFinite(input) && input >= 0 && input <= .8) result[key] = input
    else if (key === 'studioCount' && Number.isInteger(input) && input >= 1 && input <= 6) result[key] = input
    else if (key === 'videoDuration' && (input === -1 || Number.isInteger(input) && input >= 2 && input <= 30)) result[key] = input
    else if (key === 'imageNegativePrompt' && typeof input === 'string') result[key] = input.slice(0, 500)
  }
  return result
}
export function resetParameters(values, page) {
  const groups = {
    chat: ['streamMode', 'thinkingMode', 'imageMode', 'enableSearch'],
    image: ['studioSize', 'studioCount', 'imageWatermark', 'imagePromptExtend', 'imageNegativePrompt'],
    video: ['videoResolution', 'videoRatio', 'videoDuration', 'videoWatermark', 'videoPromptExtend', 'videoAudio'],
    agent: ['agentTool'],
  }
  for (const key of groups[page] || []) values[key] = DEFAULT_PREFERENCES[key]
}
