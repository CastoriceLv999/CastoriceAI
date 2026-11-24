<template>
  <form class="composer" @submit.prevent="handleSubmit">
    <div class="composer-body">
      <button type="button" class="attach-button" @click="fileInput?.click()" :disabled="disabled || isUploading" :aria-label="label('上传文件', 'Upload files')" :title="label('上传文件', 'Upload files')">{{ isUploading ? '⏳' : '📎' }}</button>
      <textarea ref="textarea" v-model="input" class="composer-text" rows="1" :placeholder="placeholder || label('路漫漫其修远兮，吾将上下而求索……', 'The road ahead is long; I will search high and low…')"
        :title="label('Enter 发送 · Shift + Enter 换行', 'Enter to send · Shift + Enter for a new line')"
        :aria-label="label('消息输入框', 'Message input')" :disabled="disabled" @keydown="handleKeydown" @input="resize" />
      <button v-if="canStop" type="button" class="submit-button stop-button" @click="emit('stop')" :aria-label="label('停止生成', 'Stop generating')" :title="label('停止生成', 'Stop generating')">■</button>
      <button v-else type="submit" class="submit-button" :disabled="disabled || isUploading || !input.trim()" :aria-label="label('发送消息', 'Send message')">➤</button>
    </div>
    <input ref="fileInput" type="file" multiple hidden accept=".pdf,.docx,.xlsx,.xls,.mp4,.webm,.txt,.md,.json,.csv,.py,.js,.ts,.vue,.html,.css,.java,.cpp,.c,.go,.rs,.png,.jpg,.jpeg,.gif,.webp,.bmp" @change="handleFiles" />
  </form>
</template>

<script setup>
import { ref, computed, inject, nextTick, watch, onMounted } from 'vue'
const props = defineProps({ modelValue: { type: String, default: undefined }, disabled: Boolean, isUploading: Boolean, canStop: Boolean, placeholder: { type: String, default: '' } })
const emit = defineEmits(['send', 'upload', 'stop', 'update:modelValue'])
const lang = inject('currentLang', ref('zh-CN'))
const appearance = inject('appAppearance', ref({send_key:'enter'}))
const label = (zh, en) => lang.value === 'en-US' ? en : zh
const localInput = ref('')
const input = computed({ get: () => props.modelValue ?? localInput.value, set: value => { localInput.value = value; emit('update:modelValue', value) } })
const textarea = ref(null)
const fileInput = ref(null)
function resize() {
  if (!textarea.value) return
  textarea.value.style.height = 'auto'
  textarea.value.style.height = Math.min(textarea.value.scrollHeight, 160) + 'px'
}
watch(() => props.modelValue, () => nextTick(resize))
onMounted(resize)
function handleKeydown(event) {
  const send = appearance.value.send_key === 'ctrl-enter' ? event.ctrlKey || event.metaKey : !event.shiftKey
  if (event.key === 'Enter' && send && !event.isComposing && event.keyCode !== 229) {
    event.preventDefault()
    handleSubmit()
  }
}
function handleSubmit() {
  const text = input.value.trim()
  if (!text || props.disabled || props.isUploading) return
  emit('send', text)
  input.value = ''
  nextTick(resize)
}
function handleFiles(event) {
  if (event.target.files?.length) emit('upload', event.target.files)
  event.target.value = ''
}
</script>

<style scoped>
.composer { margin: 0 0 1.5rem; min-width: 0; }
.composer-body { display: flex; align-items: center; min-height: 48px; overflow: hidden; border: 1px solid rgba(255,255,255,.35); background: rgba(0,0,0,var(--chat-alpha,.1)); border-radius: 24px; box-shadow: 0 4px 30px rgba(0,0,0,.15); transition: border-color .2s, background .2s, box-shadow .2s; }
.composer-body:focus-within { background: rgba(0,0,0,var(--chat-alpha-focus,.15)); border-color: rgba(255,255,255,.6); box-shadow: 0 0 20px rgba(255,255,255,.15); }
.composer-text { display: block; flex: 1; width: 0; min-width: 0; height: 26px; min-height: 26px; max-height: 160px; padding: 0 1rem; margin: 10px 0; resize: none; background: none; color: white; font-family: inherit; font-size: 16px; line-height: 26px; border: 0; outline: none; scrollbar-width: thin; }
.composer-text::placeholder { color: rgba(255,255,255,.55); }.composer-text:disabled { opacity: .6; }
.composer-body button { align-self: stretch; width: 48px; display: grid; place-items: center; flex-shrink: 0; border: 0; background: transparent; color: rgba(255,255,255,.6); cursor: pointer; }
.attach-button { font-size: 18px; }
.composer-body .submit-button { border-left: 1px solid rgba(255,255,255,.15); font-size: 20px; }
.composer-body .stop-button { font-size: 13px; }
.composer-body button:hover:not(:disabled) { color: white; background: rgba(255,255,255,.08); }
.composer-body button:disabled { opacity: .4; cursor: not-allowed; }
.composer-body button:focus-visible { outline: 2px solid #e9d9ff; outline-offset: -4px; }
</style>
