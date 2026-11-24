<template>
  <div class="agent-conversation">
    <ChatInput v-model="draft" @send="!externalDisabled && handleSend($event)" @upload="handleUpload" @stop="stop"
      :disabled="isProcessing || externalDisabled" :can-stop="isProcessing" :is-uploading="isUploading" :placeholder="placeholderText" />
    <div v-if="refItems.length" class="agent-attachments">
      <div v-for="(item, index) in refItems" :key="item.file_id" class="agent-attachment">
        <button @click="openPreview(item.url)" :aria-label="item.filename"><img :src="item.url" :alt="item.filename" /></button>
        <button :disabled="isProcessing" @click="removeRef(index)" aria-label="移除附件">×</button>
      </div>
    </div>
    <p v-if="saveError" class="save-warning" role="alert">{{ saveError }}</p>
    <ChatArea v-model:messages="messages" :streaming-msg="streamingMsg" :busy="isProcessing" :can-restore="!!backup"
      @edit-message="editMessage" @regenerate="regenerate" @restore-previous="restorePrevious" />
  </div>
</template>

<script setup>
import { ref, computed, inject, watch } from 'vue'
import ChatInput from './ChatInput.vue'
import ChatArea from './ChatArea.vue'
import { useConversation } from '../composables/useConversation.js'

const props = defineProps({
  externalDisabled: Boolean,
  agentTool: { type: String, default: 'auto' }
})

const emit = defineEmits(['session-update', 'busy-change'])

const currentLang = inject('currentLang', ref('zh-CN'))
const preview = inject('imagePreview')

const i18n = {
  'zh-CN': {
    agentEmpty: '选择工具并输入指令，遐蝶将为你调用相应的能力……',
    placeholderAuto: '描述你的需求，例如：计算 123 的 21 次方……',
    placeholderSearch: '输入搜索关键词，例如：杭州明天天气……',
    placeholderWeb_extract: '输入需要深度抓取的主题，例如：阿里云百炼代码解释器文档……',
    placeholderCode: '输入编程或计算需求，例如：用 Python 绘制正弦曲线并解释原理……',
    placeholderSearch_image: '描述想找的图片，例如：适合做 PPT 封面的科技感背景图……',
    placeholderImage_search: '上传参考图并描述需求，例如：找与这张图相似风格的风景图……',
    thinkingLabel: '✦ 思考过程',
    thinkingPlaceholder: '思考中……',
    error: '抱歉，工具调用出现了一些问题……'
  },
  'en-US': {
    agentEmpty: 'Select a tool and enter instructions, Castorice will invoke the capability for you……',
    placeholderAuto: 'Describe your needs, e.g. calculate 123^21……',
    placeholderSearch: 'Enter search keywords, e.g. weather in Hangzhou tomorrow……',
    placeholderWeb_extract: 'Enter a topic for deep extraction, e.g. Bailian code interpreter docs……',
    placeholderCode: 'Enter coding or calculation needs, e.g. plot a sine wave in Python……',
    placeholderSearch_image: 'Describe the image you want, e.g. tech background for PPT cover……',
    placeholderImage_search: 'Upload a reference image and describe, e.g. find similar landscape photos……',
    thinkingLabel: '✦ Reasoning',
    thinkingPlaceholder: 'Thinking……',
    error: 'Sorry, something went wrong with the tool call……'
  }
}

const t = (key) => i18n[currentLang.value]?.[key] || i18n['zh-CN'][key]

const placeholderText = computed(() => {
  const key = `placeholder${props.agentTool.charAt(0).toUpperCase() + props.agentTool.slice(1)}`
  return i18n[currentLang.value]?.[key] || i18n['zh-CN'][key] || t('placeholderAuto')
})

// ==================== 核心状态 ====================
const {
  messages, attachments: refItems, draft, backup, streamingMsg, isBusy: isProcessing, saveError,
  send: handleSend, editMessage, regenerate, restorePrevious, loadSession, clear: clearSession, stop
} = useConversation({ storageKey: 'castorice_active_agent_v1', agent: true,
  settings: () => ({ tool: props.agentTool, language: currentLang.value }) })
const isUploading = ref(false)

const openPreview = url => preview?.value?.open?.(url)
watch(messages, value => emit('session-update', { messages: value, lastTool: value.findLast(message => message.role === 'user')?.agentTool || props.agentTool }), { deep: true, immediate: true })
watch(isProcessing, value => emit('busy-change', value))

// ==================== 文件上传 ====================
const handleUpload = async (files) => {
  if (!['image_search', 'auto', 'code'].includes(props.agentTool)) {
    alert('当前工具模式不支持图片上传，请切换到"图搜图"或"智能选择"')
    return
  }
  if (refItems.value.length + files.length > 3) {
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
      if (data.type === 'image') refItems.value.push(data)
    } catch (e) {
      console.error(e)
    }
  }
  isUploading.value = false
}

const removeRef = (idx) => {
  refItems.value.splice(idx, 1)
}

defineExpose({ loadSession, clearSession })
</script>

<style scoped>
.agent-conversation { min-width: 0; }
.agent-attachments { display: flex; gap: 10px; margin-top: 12px; }
.agent-attachment { display: flex; gap: 4px; align-items: center; border-radius: 10px; padding: 5px; background: #1d183bd9; }
.agent-attachment button { border: 0; background: transparent; color: #eee; cursor: pointer; }
.agent-attachment img { width: 60px; height: 50px; object-fit: cover; border-radius: 6px; }
</style>
