// src/utils/toolRouter.js

const IMAGE_GEN_KEYWORDS = {
  'zh-CN': ['生成', '画', '绘制', '创作', '画一张', '生成一张', '画个', '画一', '生成一', 'create', 'generate', 'draw', 'paint'],
  'en-US': ['generate', 'create', 'draw', 'paint', 'make', 'produce', 'render']
}

const VIDEO_GEN_KEYWORDS = {
  'zh-CN': ['生成视频', '制作视频', '创作视频', '视频生成', '做视频', '生成一段视频', 'create video', 'generate video'],
  'en-US': ['generate video', 'create video', 'make video', 'video generation', 'produce video']
}

const IMAGE_SEARCH_PATTERNS = [
  /找.*?(?:图|图片|照片|壁纸|头像|背景|配图)/i,
  /搜.*?(?:图|图片|照片|壁纸|头像|背景|配图)/i,
  /(?:图|图片|照片|壁纸|头像|背景|配图).*?(?:搜索|查找|推荐)/i,
  /(?:search|find|look for).*?(?:image|photo|picture|wallpaper|avatar)/i,
  /来?张.*?[图照片]/,
  /推荐.*?[图照片]/,
  /有没有.*?[图照片]/,
]

export function isImageGenRequest(text, lang = 'zh-CN') {
  const keywords = IMAGE_GEN_KEYWORDS[lang] || IMAGE_GEN_KEYWORDS['zh-CN']
  return keywords.some(k => text.toLowerCase().includes(k.toLowerCase()))
}

export function isVideoGenRequest(text, lang = 'zh-CN') {
  const keywords = VIDEO_GEN_KEYWORDS[lang] || VIDEO_GEN_KEYWORDS['zh-CN']
  return keywords.some(k => text.toLowerCase().includes(k.toLowerCase()))
}

export function isImageSearchRequest(text) {
  return IMAGE_SEARCH_PATTERNS.some(p => p.test(text))
}

export function determineTool(text, hasImage, agentTool = 'auto', lang = 'zh-CN') {
  if (agentTool !== 'auto') return agentTool
  
  // 1. 有图片且问相似/同款/类似 -> 图搜图
  if (hasImage && /相似|同款|类似|找一样的|like|similar|same style|look like/i.test(text)) {
    return 'image_search'
  }
  
  // 2. 有图片但问分析/描述/这是什么 -> 视觉理解
  if (hasImage && /描述|分析|这是什么|describe|analyze|what is|what's this/i.test(text)) {
    return 'vision'
  }
  
  // 3. 文生图请求 -> 图像生成
  if (isImageGenRequest(text, lang)) {
    return 'image_gen'
  }
  
  // 4. 代码/计算/编程相关
  if (/代码|编程|计算|code|program|calculate|compute|plot|function|算法|写个|写一个|实现|debug|报错/i.test(text)) {
    return 'code'
  }
  
  // 5. 网页抓取：包含URL且要求提取/读取/总结内容
  if (/https?:\/\/\S+/.test(text) && /抓取|提取|内容|总结|extract|content|read|summarize|fetch/i.test(text)) {
    return 'web_extract'
  }
  
  // 6. 文搜图
  if (isImageSearchRequest(text)) {
    return 'search_image'
  }
  
  // 7. 默认联网搜索
  return 'search'
}