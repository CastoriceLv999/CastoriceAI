<template>
  <div class="studio-chat-area">
    <!-- 输入框置顶 -->
    <ChatInput
      @send="handleGenerate"
      @upload="handleRefUpload"
      :disabled="isGenerating || externalDisabled"
      :is-uploading="isUploading"
      :placeholder="t('studioPlaceholder')"
    />
    
    <!-- 内容区域：倒序显示，最新消息在上 -->
    <div class="content-section messages-reverse">
      <!-- 生成结果作为 assistant 消息（最新的在上面） -->
      <div v-if="results.length" class="chat-row assistant">
        <div class="chat-avatar">
          <img src="/avatars/Castorice.gif" class="avatar-img" alt="Castorice" />
        </div>
        <div class="chat-bubble result-bubble">
          <div class="result-grid">
            <div v-for="(url, idx) in results" :key="idx" class="result-card" @click="openPreview(url)">
              <img :src="url" alt="generated" />
              <a :href="url" target="_blank" class="download-btn" download>
                <span>⬇</span> {{ t('download') }}
              </a>
            </div>
          </div>
        </div>
      </div>

      <!-- 生成中状态 -->
      <div v-if="isGenerating" class="chat-row assistant">
        <div class="chat-avatar">
          <img src="/avatars/Castorice.gif" class="avatar-img" alt="Castorice" />
        </div>
        <div class="chat-bubble generating-bubble">
          <div class="generating-dots">
            <span></span><span></span><span></span>
          </div>
          <span>{{ t('generating') }}</span>
        </div>
      </div>

      <!-- 参考图作为 user 消息 -->
      <div v-if="refImages.length" class="chat-row user">
        <div class="chat-avatar">
          <img src="/avatars/dania.png" class="avatar-img" alt="user" />
        </div>
        <div class="chat-bubble">
          <div class="ref-gallery">
            <div v-for="(f, idx) in refImages" :key="f.file_id" class="ref-item" @click="openPreview(f.url)">
              <img :src="f.url" alt="ref" />
              <button class="ref-del" @click.stop="removeRef(idx)">✕</button>
            </div>
          </div>
          <div class="ref-count">{{ refImages.length }}/3 {{ t('refLabel') }}</div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="!refImages.length && !results.length && !isGenerating" class="empty-hint">
        {{ t('studioEmpty') }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, inject, watch } from 'vue'
import ChatInput from './ChatInput.vue'
const preview = inject('imagePreview')
const openPreview = (url) => preview?.value?.open?.(url)

const emit = defineEmits(['generation-complete', 'busy-change'])

const props = defineProps({
  externalDisabled: Boolean,
  alpha: Number,
  size: String,
  count: Number,
  watermark: Boolean,
  promptExtend: { type: Boolean, default: true },
  negativePrompt: { type: String, default: '' }
})

const currentLang = inject('currentLang', ref('zh-CN'))

const i18n = {
  'zh-CN': {
    studioEmpty: '添加参考图或输入描述，开始创作……',
    studioPlaceholder: '描述你想要的画面，例如：赛博朋克风格的城市夜景……',
    generating: '正在创造你的回忆……',
    refLabel: '参考图',
    download: '下载',
    genError: '生成失败，请稍后重试',
    genEmpty: '未获取到图片，请调整提示词',
    uploadError: '上传失败'
  },
  'en-US': {
    studioEmpty: 'Add references or describe your vision to start creating...',
    studioPlaceholder: 'Describe your scene, e.g. cyberpunk city night...',
    generating: 'Creating your memories...',
    refLabel: 'references',
    download: 'Download',
    genError: 'Generation failed, please try again later',
    genEmpty: 'No images returned, please adjust your prompt',
    uploadError: 'Upload failed'
  }
}

const t = (key) => i18n[currentLang.value]?.[key] || i18n['zh-CN'][key]

const refImages = ref([])
const isUploading = ref(false)
const isGenerating = ref(false)
watch(isGenerating, value => emit('busy-change', value), { flush: 'sync' })
const results = ref([])

const handleRefUpload = async (files) => {
  if (refImages.value.length + files.length > 3) {
    alert('最多 3 张参考图')
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
      if (data.type === 'image') refImages.value.push(data)
    } catch (e) {
      console.error(e)
    }
  }
  isUploading.value = false
}

const removeRef = (idx) => { refImages.value.splice(idx, 1) }

const handleGenerate = async (prompt) => {
  if (!prompt.trim() || isGenerating.value || props.externalDisabled) return
  isGenerating.value = true
  results.value = []
  try {
    const res = await fetch('/api/generate/image', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: prompt.trim(),
        files: refImages.value.map(f => f.file_id),
        size: props.size,
        n: props.count,
        watermark: props.watermark,
        prompt_extend: props.promptExtend,
        negative_prompt: props.negativePrompt
      })
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'Error')
    if (data.urls && data.urls.length) {
      results.value = data.urls
      emit('generation-complete', {
        prompt: prompt.trim(),
        size: props.size,
        count: props.count,
        refCount: refImages.value.length,
        results: data.urls,
        timestamp: Date.now()
        })
    } else {
      alert(t('genEmpty'))
    }
  } catch (e) {
    console.error(e)
    alert(`${t('genError')}: ${e.message}`)
  }
  isGenerating.value = false
}
</script>

<style scoped>
.studio-chat-area {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 1rem 0;
}

/* 参考图画廊 */
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
  background: rgba(0,0,0,0.2);
}
.ref-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.3s;
}
.ref-item:hover img {
  transform: scale(1.05);
}
.ref-del {
  position: absolute;
  top: 4px; right: 4px;
  width: 24px; height: 24px;
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

.ref-count {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 6px;
}

/* 结果气泡 */
.result-bubble {
  max-width: 85% !important;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.result-card {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(0, 0, 0, 0.2);
  cursor: pointer;
  transition: all 0.3s;
}
.result-card:hover {
  border-color: rgba(140, 220, 255, 0.5);
  box-shadow: 0 0 20px rgba(140, 220, 255, 0.15);
}
.result-card img {
  width: 100%;
  max-height: 300px;
  object-fit: cover;
  display: block;
  transition: transform 0.3s;
}
.result-card:hover img {
  transform: scale(1.03);
}

.download-btn {
  position: absolute;
  bottom: 8px;
  right: 8px;
  padding: 0.4rem 0.9rem;
  background: rgba(0, 0, 0, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  border-radius: 8px;
  font-size: 0.8rem;
  text-decoration: none;
  backdrop-filter: blur(4px);
  transition: all 0.3s;
  display: flex;
  align-items: center;
  gap: 4px;
}

.download-btn:hover {
  background: rgba(100, 200, 255, 0.3);
  border-color: rgba(100, 200, 255, 0.6);
}

/* 生成中动画 */
.generating-bubble {
  display: flex;
  align-items: center;
  gap: 10px;
  color: rgba(220, 180, 255, 0.9);
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

/* 复用全局样式 */
.empty-hint {
  color: rgba(255, 255, 255, 0.35);
  text-align: center;
  margin: 2rem 0;
}

@media (max-width: 768px) {
  .result-grid {
    grid-template-columns: 1fr;
  }
  .ref-item img {
    max-height: 80px;
    max-width: 120px;
  }
}

.messages-reverse {
  display: flex;
  flex-direction: column-reverse;
  gap: 14px;
  padding: 0 0.5rem;
  overflow-y: auto;
  max-height: 400px;
  min-height: 200px;
  scrollbar-width: thin;
  scrollbar-color: rgba(255,255,255,0.3) transparent;
}

.messages-reverse::-webkit-scrollbar {
  width: 6px;
}

.messages-reverse::-webkit-scrollbar-thumb {
  background-color: rgba(255,255,255,0.3);
  border-radius: 3px;
}

.messages-reverse::-webkit-scrollbar-track {
  background: transparent;
}
</style>