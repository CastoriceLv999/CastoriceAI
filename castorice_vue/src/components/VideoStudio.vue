<template>
  <div class="studio-chat-area">
    <!-- 顶部输入框 -->
    <div class="input-section">
      <ChatInput
        @send="handleGenerate"
        @upload="handleRefUpload"
        :disabled="isGenerating || externalDisabled"
        :is-uploading="isUploading"
        :placeholder="inputPlaceholder"
      />
    </div>

    <!-- 内容区域：倒序 -->
    <div class="content-section messages-reverse">
      <!-- 参考文件展示区 -->
      <div v-if="refItems.length" class="chat-row user">
        <div class="chat-avatar">
          <img src="/avatars/dania.png" class="avatar-img" alt="user" />
        </div>
        <div class="chat-bubble">
          <div class="ref-gallery">
            <div
              v-for="(item, idx) in refItems"
              :key="idx"
              class="ref-item"
              :class="{ 'video-item': item.type === 'video' }"
              @click="openPreview(item.url)"
            >
              <img v-if="item.type === 'image'" :src="item.url" alt="ref" />
              <video v-else :src="item.url" class="ref-video" muted preload="metadata" />
              <div v-if="item.type === 'video'" class="video-badge-overlay">VIDEO</div>
              <button class="ref-del" @click.stop="removeRef(idx)">✕</button>
            </div>
          </div>
          <div class="auto-mode-badge" :class="inferredMode">
            <span class="mode-icon">{{ modeIcon }}</span>
            <span class="mode-text">{{ modeLabel }}</span>
            <span class="mode-desc">{{ modeDesc }}</span>
          </div>
        </div>
      </div>

      <!-- 生成结果 -->
      <div v-if="results.length" class="chat-row assistant">
        <div class="chat-avatar">
          <img src="/avatars/Castorice.gif" class="avatar-img" alt="Castorice" />
        </div>
        <div class="chat-bubble result-bubble">
          <div class="result-grid video-grid">
            <div v-for="(url, idx) in results" :key="idx" class="result-card video-card">
              <video
                :src="url"
                controls
                preload="metadata"
                class="result-video"
                crossorigin="anonymous"
                @error="handleVideoError"
                @loadedmetadata="onVideoLoaded"
              />
              <a :href="url" target="_blank" class="download-btn" download>
                <span>⬇</span> {{ t('download') }}
              </a>
            </div>
          </div>
        </div>
      </div>

      <!-- 生成中状态（进度条版） -->
      <div v-if="isGenerating" class="chat-row assistant">
        <div class="chat-avatar">
          <img src="/avatars/Castorice.gif" class="avatar-img" alt="Castorice" />
        </div>
        <div class="chat-bubble generating-bubble">
          <div class="generating-visual">
            <div class="generating-dots">
              <span></span><span></span><span></span>
            </div>
            <div class="progress-container">
              <div class="progress-bar" :style="{ width: progressPercent + '%' }"></div>
            </div>
          </div>
          <div class="generating-text">
            <span>{{ statusText }}</span>
            <span v-if="progressText" class="progress-detail">{{ progressText }}</span>
            <span v-if="inferredMode" class="mode-hint">({{ modeLabel }})</span>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="!refItems.length && !results.length && !isGenerating" class="empty-hint">
        {{ placeholderText }}
      </div>
    </div>
  </div>
</template>

<script setup>
import ChatInput from './ChatInput.vue'
import { ref, computed, inject, watch, onUnmounted } from 'vue'

const preview = inject('imagePreview')
const openPreview = (url) => preview?.value?.open?.(url)
const emit = defineEmits(['generation-complete', 'busy-change'])
const props = defineProps({
  externalDisabled: Boolean,
  resolution: String,
  ratio: String,
  duration: Number,
  watermark: Boolean,
  promptExtend: { type: Boolean, default: true },
  audio: { type: Boolean, default: true }
})

const currentLang = inject('currentLang', ref('zh-CN'))
const i18n = {
  'zh-CN': {
    t2vEmpty: '输入描述，开始创作你的视频……',
    i2vEmpty: '上传一张首帧图片，我将让它动起来……',
    r2vEmpty: '上传1-9张参考图，保持角色一致性……',
    editEmpty: '上传源视频（和参考图），描述你想要的编辑效果……',
    t2vPlaceholder: '描述你想要的视频画面，例如：夕阳下的海边公路，慢镜头推进……',
    i2vPlaceholder: '描述画面运动方式，例如：镜头缓慢推进，人物转身微笑……',
    r2vPlaceholder: '描述场景和动作，用[Image 1]引用参考图……',
    editPlaceholder: '描述编辑指令，例如：把视频中的角色换成卡通风格……',
    generating: '正在创造你的回忆',
    download: '下载',
    genError: '生成失败，请稍后重试',
    genEmpty: '未获取到视频，请调整提示词',
    uploadError: '上传失败',
    maxFilesReached: '已达到当前模式的最大文件数量',
    videoOnlyOne: '视频编辑模式只能上传1个源视频',
    modeT2V: '文生视频',
    modeI2V: '首帧生视频',
    modeR2V: '参考生视频',
    modeEdit: '视频编辑',
    modeDescT2V: '根据文字描述生成视频',
    modeDescI2V: '让图片动起来',
    modeDescR2V: '多图参考，角色一致',
    modeDescEdit: '编辑已有视频'
  },
  'en-US': {
    t2vEmpty: 'Describe your vision to start creating video...',
    i2vEmpty: 'Upload a first-frame image and I will bring it to life...',
    r2vEmpty: 'Upload 1-9 reference images for character consistency...',
    editEmpty: 'Upload source video (and references), describe the edit...',
    t2vPlaceholder: 'Describe your scene, e.g. sunset highway, slow push-in...',
    i2vPlaceholder: 'Describe motion, e.g. slow push-in, character turns and smiles...',
    r2vPlaceholder: 'Describe scene with [Image 1] refs...',
    editPlaceholder: 'Describe edit instruction, e.g. convert character to cartoon style...',
    generating: 'Creating your memories',
    download: 'Download',
    genError: 'Generation failed, please try again later',
    genEmpty: 'No video returned, please adjust your prompt',
    uploadError: 'Upload failed',
    maxFilesReached: 'Maximum file count reached for current mode',
    videoOnlyOne: 'Video edit mode allows only 1 source video',
    modeT2V: 'Text to Video',
    modeI2V: 'Image to Video',
    modeR2V: 'Reference to Video',
    modeEdit: 'Video Edit',
    modeDescT2V: 'Generate video from text',
    modeDescI2V: 'Animate your image',
    modeDescR2V: 'Multi-image reference',
    modeDescEdit: 'Edit existing video'
  }
}

const t = (key) => i18n[currentLang.value]?.[key] || i18n['zh-CN'][key]

// ==================== 核心状态 ====================
const refItems = ref([])
const isUploading = ref(false)
const isGenerating = ref(false)
watch(isGenerating, value => emit('busy-change', value), { flush: 'sync' })
const results = ref([])
const taskId = ref('')
const progressText = ref('')
const progressPercent = ref(0)
const statusText = ref('')
const pollAbort = ref(null)

// ==================== 自动推断模式 ====================
const inferredMode = computed(() => {
  const images = refItems.value.filter(i => i.type === 'image')
  const videos = refItems.value.filter(i => i.type === 'video')
  if (videos.length > 0) return 'edit'
  if (images.length === 1) return 'i2v'
  if (images.length >= 2) return 'r2v'
  return 't2v'
})

const modeIcon = computed(() => ({
  't2v': '📝',
  'i2v': '🖼️',
  'r2v': '🎨',
  'edit': '✂️'
}[inferredMode.value]))

const modeLabel = computed(() => {
  const labels = {
    't2v': t('modeT2V'),
    'i2v': t('modeI2V'),
    'r2v': t('modeR2V'),
    'edit': t('modeEdit')
  }
  return labels[inferredMode.value]
})

const modeDesc = computed(() => {
  const descs = {
    't2v': t('modeDescT2V'),
    'i2v': t('modeDescI2V'),
    'r2v': t('modeDescR2V'),
    'edit': t('modeDescEdit')
  }
  return descs[inferredMode.value]
})

// ==================== 动态文案 ====================
const placeholderText = computed(() => t(inferredMode.value + 'Empty'))
const inputPlaceholder = computed(() => t(inferredMode.value + 'Placeholder'))

// ==================== 上传限制 ====================
const maxFiles = computed(() => {
    // 关键修复：始终允许最多 9 个文件（r2v 的上限）
    // 模式由后端根据最终文件列表自动推断，前端不要提前锁死
    return 9
})
const canUploadMore = computed(() => {
  return refItems.value.length < maxFiles.value
})

// ==================== 文件上传 ====================
const handleRefUpload = async (files) => {
    // 总文件上限 9（对应 r2v 最大参考图数）
    if (refItems.value.length + files.length > 9) {
        alert(t('maxFilesReached') + ' (9)')
        return
    }

    // 视频编辑模式只能有 1 个源视频
    const hasVideo = refItems.value.some(i => i.type === 'video')
    const newVideos = Array.from(files).filter(f => f.type.startsWith('video/'))
    if (hasVideo && newVideos.length > 0) {
        alert(t('videoOnlyOne'))
        return
    }

    isUploading.value = true
  for (const file of files) {
    const formData = new FormData()
    formData.append('file', file)
    try {
      const res = await fetch('/api/upload', { method: 'POST', body: formData })
      if (!res.ok) throw new Error('Upload failed')
      const data = await res.json()
      refItems.value.push({
        file_id: data.file_id,
        url: data.url,
        type: data.type,
        filename: data.filename
      })
    } catch (e) {
      console.error(e)
      alert(t('uploadError'))
    }
  }
  isUploading.value = false
}

const removeRef = (idx) => { refItems.value.splice(idx, 1) }

// ==================== 视频生成 ====================
const handleGenerate = async (prompt) => {
  if (!prompt.trim() || isGenerating.value || props.externalDisabled) return
  if (pollAbort.value) {
    pollAbort.value.abort()
    pollAbort.value = null
  }
  if (inferredMode.value === 'i2v' && refItems.value.length === 0) {
    alert('请上传首帧图片')
    return
  }
  if (inferredMode.value === 'edit' && !refItems.value.some(i => i.type === 'video')) {
    alert('请上传源视频')
    return
  }
  pollAbort.value = new AbortController()
  const signal = pollAbort.value.signal
  isGenerating.value = true
  results.value = []
  taskId.value = ''
  progressText.value = ''
  progressPercent.value = 0
  statusText.value = t('generating')
  try {
    const res = await fetch('/api/generate/video', {
      method: 'POST',
      signal,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: prompt.trim(),
        files: refItems.value.map(f => f.file_id),
        resolution: props.resolution,
        ratio: props.ratio,
        duration: props.duration,
        watermark: props.watermark,
        prompt_extend: props.promptExtend,
        audio: props.audio
      })
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'Error')
    taskId.value = data.task_id
    await pollTask(data.task_id, prompt.trim(), signal)
  } catch (e) {
    if (e.name === 'AbortError') return
    console.error(e)
    alert(`${t('genError')}: ${e.message}`)
    isGenerating.value = false
  }
}

// ==================== 轮询任务（带进度条）====================
const pollTask = async (tid, prompt, signal) => {
  const maxAttempts = 60
  let interval = 3000
  
  for (let i = 0; i < maxAttempts; i++) {
    await new Promise(r => setTimeout(r, interval))
    if (signal.aborted) return
    
    if (i < 10) interval = 3000
    else if (i < 20) interval = 5000
    else interval = 8000
    
    try {
      const res = await fetch(`/api/tasks/${tid}`, { signal })
      if (!res.ok) {
        console.error(`[Poll] HTTP ${res.status}`)
        continue
      }
      const data = await res.json()

      if (data.status === 'SUCCEEDED') {
        const videos = data.result?.videos || []
        if (videos.length > 0) {
          results.value = videos
          emit('generation-complete', {
            prompt,
            mode: inferredMode.value,
            resolution: props.resolution,
            ratio: props.ratio,
            duration: props.duration,
            refCount: refItems.value.length,
            results: videos,
            timestamp: Date.now()
          })
        } else {
          alert(t('genEmpty'))
        }
        isGenerating.value = false
        return

      } else if (data.status === 'FAILED') {
        alert(t('genError') + (data.error ? `: ${data.error}` : ''))
        isGenerating.value = false
        return
      }

      const progress = data.progress || Math.min(Math.round((i + 1) / maxAttempts * 90), 90)
      progressPercent.value = progress
      progressText.value = `${progress}%`
      statusText.value = getStatusText(data.status, progress)

    } catch (e) {
      if (e.name === 'AbortError') return
      console.error('[Poll] Error:', e)
      if (i >= maxAttempts - 1) {
        alert('轮询异常，请刷新页面')
        isGenerating.value = false
        return
      }
    }
  }
  alert('生成超时，请稍后通过任务ID查询结果')
  isGenerating.value = false
}

// 状态文案映射
const getStatusText = (status, progress) => {
  const statusMap = {
    'PENDING': '任务排队中...',
    'RUNNING': '正在生成视频...',
    'WAIT': '等待资源...',
    'PROCESS': '处理中...',
    'GENERATE': '生成画面中...',
    'RENDER': '渲染中...'
  }
  return statusMap[status] || `生成中... ${progress}%`
}

// ==================== 组件卸载时清理 ====================
onUnmounted(() => {
  if (pollAbort.value) {
    pollAbort.value.abort()
    pollAbort.value = null
  }
})

const onVideoLoaded = (e) => {
  console.log('Video loaded:', e.target.duration)
}

const handleVideoError = (event) => {
  console.error('[VideoStudio] 视频加载失败:', event.target.error, 'URL:', event.target.src)
}
</script>

<style scoped>
/* ==================== 布局 ==================== */
/* 修改后的 VideoStudio.vue 样式 */
.studio-chat-area {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 1rem 0;
    /* 去掉 height: 100% */
}

.input-section {
    flex-shrink: 0;
    position: sticky;
    top: 0;
    z-index: 10;
    background: transparent;
    padding: 0 0.5rem;
}

.content-section {
    /* 去掉 flex: 1 */
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 0 0.5rem;
    min-height: 0;
    overflow-y: visible;  /* 内容少时不滚动，自然撑开 */
}
/* 自定义滚动条 */
.content-section::-webkit-scrollbar {
  width: 6px;
}

.content-section::-webkit-scrollbar-thumb {
  background-color: rgba(255, 255, 255, 0.3);
  border-radius: 3px;
}

.content-section::-webkit-scrollbar-track {
  background: transparent;
}

/* ==================== 参考文件画廊 ==================== */
.ref-gallery {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(90px, 1fr));
  gap: 10px;
}

.ref-item {
  position: relative;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid rgba(140, 220, 255, 0.35);
  aspect-ratio: 1;
  cursor: pointer;
  background: rgba(0, 0, 0, 0.2);
}

.ref-item.video-item {
  aspect-ratio: 16/9;
  border-color: rgba(255, 180, 100, 0.4);
}

.ref-item img,
.ref-item video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.3s;
}

.ref-item:hover img,
.ref-item:hover video {
  transform: scale(1.05);
}

.video-badge-overlay {
  position: absolute;
  bottom: 4px;
  left: 4px;
  padding: 2px 8px;
  background: rgba(255, 140, 60, 0.85);
  border-radius: 4px;
  font-size: 0.7rem;
  color: white;
  font-weight: bold;
  pointer-events: none;
}

.ref-del {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.65);
  border: 1px solid rgba(255, 120, 120, 0.6);
  color: rgba(255, 120, 120, 0.95);
  font-size: 0.8rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  opacity: 0;
  z-index: 2;
}

.ref-item:hover .ref-del {
  opacity: 1;
}

.ref-del:hover {
  background: rgba(255, 60, 60, 0.85);
  color: white;
}

/* ==================== 自动模式徽章 ==================== */
.auto-mode-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 0.85rem;
  margin-top: 10px;
  backdrop-filter: blur(4px);
  border: 1px solid;
  transition: all 0.3s;
}

.auto-mode-badge.t2v {
  background: rgba(100, 200, 255, 0.12);
  border-color: rgba(100, 200, 255, 0.35);
  color: #a0e0ff;
}

.auto-mode-badge.i2v {
  background: rgba(140, 220, 100, 0.12);
  border-color: rgba(140, 220, 100, 0.35);
  color: #b0f0a0;
}

.auto-mode-badge.r2v {
  background: rgba(220, 160, 255, 0.12);
  border-color: rgba(220, 160, 255, 0.35);
  color: #e0c0ff;
}

.auto-mode-badge.edit {
  background: rgba(255, 180, 100, 0.12);
  border-color: rgba(255, 180, 100, 0.35);
  color: #ffd0a0;
}

.mode-icon { font-size: 1rem; }
.mode-text { font-weight: 600; }
.mode-desc {
  font-size: 0.75rem;
  opacity: 0.7;
  margin-left: 4px;
}

/* ==================== 结果区域 ==================== */
.result-bubble {
  max-width: 85% !important;
}

.video-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.result-card.video-card {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(0, 0, 0, 0.3);
  cursor: pointer;
  transition: all 0.3s;
  aspect-ratio: v-bind('props.ratio.replace(":", "/")');
}

.result-card.video-card:hover {
  border-color: rgba(140, 220, 255, 0.5);
  box-shadow: 0 0 20px rgba(140, 220, 255, 0.15);
}

.result-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  border-radius: 8px;
}

.download-btn {
  position: absolute;
  bottom: 12px;
  right: 12px;
  padding: 0.5rem 1rem;
  background: rgba(0, 0, 0, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  border-radius: 8px;
  font-size: 0.85rem;
  text-decoration: none;
  backdrop-filter: blur(8px);
  transition: all 0.3s;
  display: flex;
  align-items: center;
  gap: 6px;
  z-index: 2;
}

.download-btn:hover {
  background: rgba(100, 200, 255, 0.4);
  border-color: rgba(100, 200, 255, 0.6);
}

/* ==================== 生成中动画（进度条版）==================== */
.generating-bubble {
  display: flex;
  align-items: center;
  gap: 12px;
  color: rgba(220, 180, 255, 0.9);
  padding: 14px 18px;
}

.generating-visual {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.generating-dots {
  display: flex;
  gap: 4px;
}

.generating-dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(220, 160, 255, 0.8);
  animation: dotPulse 1.4s ease-in-out infinite;
}

.generating-dots span:nth-child(2) { animation-delay: 0.2s; }
.generating-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes dotPulse {
  0%, 100% { transform: scale(0.6); opacity: 0.4; }
  50% { transform: scale(1); opacity: 1; }
}

/* ==================== 进度条 ==================== */
.progress-container {
  width: 160px;
  height: 6px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 3px;
  overflow: hidden;
  margin-top: 8px;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, rgba(140, 220, 255, 0.8), rgba(220, 160, 255, 0.8));
  border-radius: 3px;
  transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 0 8px rgba(140, 220, 255, 0.4);
  position: relative;
  overflow: hidden;
}

/* 流光效果 */
.progress-bar::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.3),
    transparent
  );
  animation: progressShimmer 1.5s infinite;
}

@keyframes progressShimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.generating-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.progress-detail {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.6);
  font-variant-numeric: tabular-nums;
}

.mode-hint {
  font-size: 0.75rem;
  color: rgba(140, 220, 255, 0.7);
}

/* ==================== 空状态 ==================== */
.empty-hint {
  color: rgba(255, 255, 255, 0.35);
  text-align: center;
  margin: 2rem 0;
  font-size: 0.95rem;
  line-height: 1.6;
}

/* ==================== 响应式 ==================== */
@media (max-width: 768px) {
  .video-grid {
    grid-template-columns: 1fr;
  }
  .ref-gallery {
    grid-template-columns: repeat(auto-fill, minmax(70px, 1fr));
  }
  .auto-mode-badge {
    flex-wrap: wrap;
    padding: 4px 10px;
  }
  .mode-desc {
    width: 100%;
    margin-left: 0;
    margin-top: 2px;
  }
  .progress-container {
    width: 120px;
  }
}
</style>