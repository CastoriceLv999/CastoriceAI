<template>
  <div class="file-uploader">
    <div
      class="upload-dropzone"
      :class="{ dragging: isDragging }"
      @click="triggerFileInput"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="handleDrop"
    >
      <span class="upload-icon">📎</span>
      <span class="upload-text">{{ t('uploadHint') }}</span>
      <input
        ref="fileInput"
        type="file"
        multiple
        style="display: none"
        @change="handleFileSelect"
        accept="*/*"
      />
    </div>

    <div v-if="attachedFiles.length > 0" class="file-tags">
      <div
        v-for="(file, idx) in attachedFiles"
        :key="file.id || idx"
        class="file-tag"
        :class="{ image: file.is_image, uploading: file.uploading, error: file.error }"
      >
        <img v-if="file.is_image && file.preview" :src="file.preview" class="file-thumb" />
        <span v-else class="file-icon">{{ file.is_image ? '🖼️' : '📄' }}</span>

        <span class="file-name" :title="file.name">{{ file.name }}</span>

        <span v-if="file.uploading" class="status-spin">⏳</span>
        <span v-else-if="file.error" class="status-error">⚠️</span>
        <span v-else class="status-ok">✓</span>

        <button class="file-remove" @click.stop="removeFile(idx)" title="移除">✕</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, inject } from 'vue'

const emit = defineEmits(['update:files'])
const currentLang = inject('currentLang', ref('zh-CN'))

const i18n = {
  'zh-CN': { uploadHint: '点击或拖拽上传文件（支持多选、图片识别、文档RAG）' },
  'en-US': { uploadHint: 'Click or drag to upload files (multi-select, image recognition, document RAG)' }
}
const t = (key) => i18n[currentLang.value]?.[key] || i18n['zh-CN'][key]

const fileInput = ref(null)
const isDragging = ref(false)
const attachedFiles = ref([])

const triggerFileInput = () => fileInput.value?.click()

const handleFileSelect = (e) => {
  const files = Array.from(e.target.files || [])
  if (files.length) processFiles(files)
  e.target.value = ''
}

const handleDrop = (e) => {
  isDragging.value = false
  const files = Array.from(e.dataTransfer.files || [])
  if (files.length) processFiles(files)
}

const processFiles = async (files) => {
  for (const rawFile of files) {
    const exists = attachedFiles.value.some(f => f.name === rawFile.name && f.size === rawFile.size)
    if (exists) continue

    const isImage = rawFile.type.startsWith('image/')
    const fileObj = {
      raw: rawFile,
      name: rawFile.name,
      size: rawFile.size,
      is_image: isImage,
      uploading: true,
      error: false,
      id: null,
      preview: null
    }

    if (isImage) {
      fileObj.preview = await readAsDataURL(rawFile)
    }

    attachedFiles.value.push(fileObj)
    emitUpdate()

    try {
      const formData = new FormData()
      formData.append('files', rawFile)
      const res = await fetch('/api/upload', { method: 'POST', body: formData })
      if (!res.ok) throw new Error('Upload failed')
      const data = await res.json()
      const info = data.files?.[0]
      if (info) {
        fileObj.id = info.id
        fileObj.is_image = info.is_image
      }
      fileObj.uploading = false
    } catch (err) {
      console.error('[Upload]', err)
      fileObj.error = true
      fileObj.uploading = false
    }
    emitUpdate()
  }
}

const removeFile = (idx) => {
  attachedFiles.value.splice(idx, 1)
  emitUpdate()
}

const emitUpdate = () => {
  emit('update:files', attachedFiles.value.map(f => ({
    id: f.id,
    name: f.name,
    is_image: f.is_image,
    preview: f.preview,
    raw: f.raw
  })))
}

const readAsDataURL = (file) => new Promise((resolve) => {
  const reader = new FileReader()
  reader.onload = (e) => resolve(e.target.result)
  reader.readAsDataURL(file)
})

const clearFiles = () => {
  attachedFiles.value = []
  emitUpdate()
}

const getImageBase64List = () => {
  return attachedFiles.value
    .filter(f => f.is_image && f.preview)
    .map(f => f.preview.split(',')[1])
}

const getDocumentFileIds = () => {
  return attachedFiles.value
    .filter(f => !f.is_image && f.id)
    .map(f => f.id)
}

defineExpose({ clearFiles, getImageBase64List, getDocumentFileIds })
</script>

<style scoped>
.file-uploader { margin-bottom: 0.6rem; }
.upload-dropzone {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.8rem;
  border-radius: 10px;
  border: 1px dashed rgba(255, 255, 255, 0.3);
  background: rgba(0, 0, 0, var(--chat-alpha, 0.05));
  backdrop-filter: blur(4px);
  cursor: pointer;
  transition: all 0.3s;
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.9rem;
}
.upload-dropzone:hover, .upload-dropzone.dragging {
  border-color: rgba(140, 220, 255, 0.6);
  background: rgba(140, 220, 255, 0.08);
  color: white;
}
.upload-icon { font-size: 1.1rem; }
.file-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.5rem;
}
.file-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.3rem 0.6rem;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.25);
  background: rgba(0, 0, 0, var(--chat-alpha-focus, 0.09));
  color: white;
  font-size: 0.85rem;
  backdrop-filter: blur(4px);
  transition: all 0.3s;
}
.file-tag.image {
  border-color: rgba(220, 160, 255, 0.4);
  background: rgba(40, 10, 60, var(--chat-alpha-focus, 0.09));
}
.file-tag.uploading { opacity: 0.7; }
.file-tag.error { border-color: rgba(255, 120, 120, 0.6); }
.file-thumb {
  width: 24px;
  height: 24px;
  object-fit: cover;
  border-radius: 4px;
  border: 1px solid rgba(255, 255, 255, 0.2);
}
.file-name {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.file-remove {
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  padding: 0;
  font-size: 0.8rem;
  line-height: 1;
}
.file-remove:hover { color: #ff7878; }
.status-spin { font-size: 0.8rem; animation: spin 1s linear infinite; }
.status-ok { color: rgba(100, 255, 180, 0.9); font-size: 0.8rem; }
.status-error { color: #ff7878; font-size: 0.8rem; }
@keyframes spin { 100% { transform: rotate(360deg); } }
</style>