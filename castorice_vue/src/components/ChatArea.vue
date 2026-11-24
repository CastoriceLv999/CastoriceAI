<template>
  <section class="conversation-shell" :aria-label="label('对话', 'Conversation')">
    <div v-if="canRestore" class="rewrite-notice" role="status">
      <span>{{ label('已从选定问题重新回答，原对话仍可恢复。', 'Conversation rewritten from the selected question. The previous version can be restored.') }}</span>
      <button :disabled="busy" @click="emit('restore-previous')">{{ label('恢复改写前对话', 'Restore previous conversation') }}</button>
    </div>
    <div ref="scrollRef" class="conversation-scroll" tabindex="0" @scroll="onScroll" @wheel.passive="onWheel" @touchstart.passive="followLatest = false" @keydown="onKeyScroll">
      <div ref="contentRef" class="conversation-messages" :class="{ 'is-empty': !messages.length && !streamingMsg }">
        <div v-if="!messages.length && !streamingMsg" class="conversation-empty">
          <span class="empty-star">✦</span>
          <h2>{{ label('从一个想法开始', 'Start with an idea') }}</h2>
          <p>{{ label('提个问题，分享文件，或者一起写一段代码。', 'Ask a question, share a file, or write some code together.') }}</p>
        </div>
        <article v-for="(msg, index) in visibleMessages" :key="messageKey(msg)" class="message-row" :class="{ 'from-user': msg.role === 'user', 'is-error': msg.isError || msg.isAgentError }">
          <img class="message-avatar" :src="msg.role === 'user' ? appearance.user_avatar || '/avatars/dania.png' : appearance.assistant_avatar || '/avatars/Castorice.gif'" :style="{borderRadius:appearance.avatar_shape==='rounded'?'12px':'50%'}" :alt="msg.role === 'user' ? appearance.user_name : appearance.assistant_name" />
          <div class="message-main">
            <div class="message-author">{{ msg.role === 'user' ? appearance.user_name : appearance.assistant_name }}<span v-if="msg === streamingMsg" class="live-label">{{ label('正在生成', 'Generating') }}</span></div>
            <details v-if="msg.reasoning" class="reasoning-panel">
              <summary>{{ label('思考过程', 'Reasoning') }}</summary>
              <MessageContent :text="msg.reasoning" />
            </details>
            <div v-if="msg.isToolCalling" class="tool-label" role="status">{{ label('正在调用', 'Using') }} {{ toolName(msg.toolName) }}…</div>
            <div v-if="msg.toolCalls?.length || msg.tool_calls?.length" class="tool-label">
              <span v-for="(tool, i) in (msg.toolCalls || msg.tool_calls)" :key="i">✓ {{ toolName(tool.tool) }}</span>
            </div>
            <details v-if="msg.toolInfo" class="reasoning-panel"><summary>{{ label('工具执行', 'Tool execution') }}</summary><MessageContent :text="'```python\n' + msg.toolInfo + '\n```'" /></details>
            <div class="message-surface">
              <form v-if="editingMessage === msg" class="message-editor" @submit.prevent="saveEdit(index)">
                <textarea v-model="editText" :aria-label="label('编辑问题', 'Edit question')" rows="4" @keydown.esc.prevent="editingMessage = null"></textarea>
                <div v-if="editFiles.length" class="edit-files"><span v-for="(file, fileIndex) in editFiles" :key="file.file_id">{{ file.filename }} <button type="button" @click="editFiles.splice(fileIndex, 1)" :aria-label="label('移除附件', 'Remove attachment')">×</button></span></div>
                <p>{{ label('保存后将从这个问题重新回答，后续对话会被替换；可以恢复改写前的对话。', 'Saving regenerates from this question and replaces later turns. You can restore the previous conversation.') }}</p>
                <div><button type="button" @click="editingMessage = null">{{ label('取消', 'Cancel') }}</button><button type="submit" :disabled="busy || !editText.trim()">{{ label('保存并重新生成', 'Save and regenerate') }}</button></div>
              </form>
              <MessageContent v-else-if="msg.content" :text="msg.content" />
              <div v-else-if="msg === streamingMsg" class="typing-indicator" role="status" :aria-label="label('正在等待回复', 'Waiting for a reply')"><i></i><i></i><i></i></div>
              <div v-if="msg.images?.length" class="message-images">
                <button v-for="(image, i) in msg.images" :key="i" @click="openPreview(image.url)" :aria-label="image.title || label('预览图片', 'Preview image')"><img :src="image.url" :alt="image.title || ''" loading="lazy" /><span>{{ image.title }}</span></button>
              </div>
              <div v-if="msg.files?.length" class="message-files">
                <template v-for="file in msg.files" :key="file.file_id">
                  <button v-if="file.type === 'image'" @click="openPreview(file.url)" :aria-label="file.filename"><img :src="file.url" :alt="file.filename" /></button>
                  <span v-else>▧ {{ file.filename }}</span>
                </template>
              </div>
              <div v-if="msg.searchResults?.length" class="message-sources">
                <template v-for="(source, i) in msg.searchResults" :key="i"><a v-if="safeLink(source.url)" :href="source.url" target="_blank" rel="noopener noreferrer">{{ source.title || source.url }}</a></template>
              </div>
            </div>
            <span v-if="msg.isInterrupted" class="message-state" role="status">{{ label('生成因刷新或关闭页面而中断，可重新生成。', 'Generation was interrupted by a reload or closing the page. You can regenerate.') }}</span>
            <span v-else-if="msg.isStopped" class="message-state">{{ label('已停止生成', 'Generation stopped') }}</span>
            <div v-if="msg !== streamingMsg" class="message-actions">
              <button type="button" @click="copyMessage(msg)" :aria-label="label('复制消息', 'Copy message')">{{ copied === msg ? label('✓ 已复制', '✓ Copied') : label('复制', 'Copy') }}</button>
              <button type="button" :disabled="busy" @click="deleteMessage(index)" :aria-label="label('删除消息', 'Delete message')">{{ label('删除', 'Delete') }}</button>
              <button v-if="msg.role === 'user'" type="button" :disabled="busy" @click="startEdit(msg)">{{ label('编辑', 'Edit') }}</button>
              <button v-else-if="hasQuestion(index)" type="button" :disabled="busy" @click="emit('regenerate', index)">{{ label(msg.isError || msg.isAgentError ? '重试' : '重新生成', msg.isError || msg.isAgentError ? 'Retry' : 'Regenerate') }}</button>
            </div>
          </div>
        </article>
      </div>
    </div>
    <button v-if="!followLatest && messages.length" class="jump-latest" @click="jumpToLatest">↓ {{ label('回到最新', 'Jump to latest') }}</button>
    <div v-if="undoState || copyError" class="conversation-notice" role="status">
      <template v-if="undoState">{{ label('消息已删除', 'Message deleted') }} <button :disabled="busy" @click="undoDelete">{{ label('撤销', 'Undo') }}</button></template>
      <template v-else>{{ label('复制失败，请选中文字手动复制', 'Copy failed. Select the text to copy manually.') }}</template>
    </div>
  </section>
</template>

<script setup>
import { computed, inject, ref, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import MessageContent from './MessageContent.vue'
import { copyText } from '../utils/clipboard.js'
import { defaultAppearance } from '../composables/useApplicationSettings.js'
const appearance = inject('appAppearance', ref(defaultAppearance))
const props = defineProps({ messages: { type: Array, default: () => [] }, streamingMsg: Object, busy: Boolean, canRestore: Boolean })
const emit = defineEmits(['update:messages', 'edit-message', 'regenerate', 'restore-previous'])
const lang = inject('currentLang', ref('zh-CN'))
const label = (zh, en) => lang.value === 'en-US' ? en : zh
const preview = inject('imagePreview')
const openPreview = url => preview?.value?.open?.(url)
const safeLink = url => /^https?:\/\//i.test(url || '')
const visibleMessages = computed(() => props.streamingMsg ? [...props.messages, props.streamingMsg] : props.messages)
const editingMessage = ref(null)
const editText = ref('')
const editFiles = ref([])
const hasQuestion = index => props.messages.slice(0, index).some(message => message.role === 'user')
function startEdit(message) { editingMessage.value = message; editText.value = message.content; editFiles.value = [...(message.files || [])] }
function saveEdit(index) {
  if (props.busy || !editText.value.trim()) return
  emit('edit-message', { index, text: editText.value.trim(), files: editFiles.value })
  editingMessage.value = null
}
watch(() => props.busy, busy => { if (busy) editingMessage.value = null })
watch(() => props.messages, messages => { if (editingMessage.value && !messages.includes(editingMessage.value)) editingMessage.value = null })
const ids = new WeakMap()
let sequence = 0
function messageKey(msg) { if (!ids.has(msg)) ids.set(msg, ++sequence); return ids.get(msg) }
const toolName = name => ({ web_search: '联网搜索', web_extractor: '网页提取', code_interpreter: '代码执行', web_search_image: '文字搜图', image_search: '以图搜图' }[name] || name || label('工具', 'Tool'))
const scrollRef = ref(null)
const contentRef = ref(null)
const followLatest = ref(true)
let previousTop = 0
let frame
let resizeObserver
function onScroll() {
  const element = scrollRef.value
  if (!element) return
  const nearBottom = element.scrollHeight - element.clientHeight - element.scrollTop < 48
  if (element.scrollTop < previousTop - 2) followLatest.value = false
  if (nearBottom) followLatest.value = true
  previousTop = element.scrollTop
}
function onWheel(event) { if (event.deltaY < 0) followLatest.value = false }
function onKeyScroll(event) { if (['ArrowUp', 'PageUp', 'Home'].includes(event.key)) followLatest.value = false }
function scheduleScroll() {
  cancelAnimationFrame(frame)
  if (!followLatest.value) return
  frame = requestAnimationFrame(() => {
    if (!followLatest.value || !scrollRef.value) return
    scrollRef.value.scrollTop = scrollRef.value.scrollHeight
    previousTop = scrollRef.value.scrollTop
  })
}
function jumpToLatest() { followLatest.value = true; nextTick(scheduleScroll) }
watch(() => [props.messages.length, props.streamingMsg?.content, props.streamingMsg?.reasoning, props.streamingMsg?.images?.length, props.streamingMsg?.toolInfo], scheduleScroll, { flush: 'post' })
watch(() => props.messages.at(-1), (last, previous) => { if (last !== previous && last?.role === 'user') jumpToLatest() })
watch(() => props.messages, (messages) => {
  if (undoState.value && !sameMessages(messages, undoState.value.after)) undoState.value = null
  if (!messages.length || messages.length > 0 && messages[0] !== firstMessage) jumpToLatest()
  firstMessage = messages[0]
}, { flush: 'post' })
let firstMessage = props.messages[0]
const copied = ref(null)
const copyError = ref(false)
const undoState = ref(null)
let copyTimer
let undoTimer
const sameMessages = (left, right) => left.length === right.length && left.every((msg, i) => msg === right[i])
async function copyMessage(msg) {
  try {
    await copyText(msg.content || (msg.images || []).map(image => image.url).join('\n'))
    copied.value = msg
    copyError.value = false
    clearTimeout(copyTimer)
    copyTimer = setTimeout(() => { copied.value = null }, 2000)
  } catch { copyError.value = true }
}
function deleteMessage(index) {
  if (props.busy) return
  const before = [...props.messages]
  const after = before.filter((_, i) => i !== index)
  undoState.value = { before, after }
  emit('update:messages', after)
  clearTimeout(undoTimer)
  undoTimer = setTimeout(() => { undoState.value = null }, 8000)
}
function undoDelete() {
  if (props.busy || !undoState.value || !sameMessages(props.messages, undoState.value.after)) return
  emit('update:messages', undoState.value.before)
  undoState.value = null
  clearTimeout(undoTimer)
}
onMounted(() => {
  resizeObserver = new ResizeObserver(scheduleScroll)
  resizeObserver.observe(contentRef.value)
  scheduleScroll()
})
onBeforeUnmount(() => { resizeObserver?.disconnect(); cancelAnimationFrame(frame); clearTimeout(copyTimer); clearTimeout(undoTimer) })
defineExpose({ jumpToLatest })
</script>

<style scoped>
.conversation-shell { position: relative; min-width: 0; border: 1px solid #ffffff16; border-radius: 20px; background: rgba(10, 10, 30, var(--chat-alpha, .1)); backdrop-filter: blur(12px); overflow: hidden; }
.rewrite-notice { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; padding: 10px 16px; border-bottom: 1px solid #ffffff16; color: #d2c3e8; font-size: 12px; }
.rewrite-notice button, .message-editor button { color: #e2d1ff; background: #b79ae71a; border: 1px solid #b79ae740; border-radius: 7px; padding: 6px 10px; cursor: pointer; }
.message-editor textarea { width: 100%; resize: vertical; min-height: 80px; background: #121026ba; border: 1px solid #b79ae766; border-radius: 8px; color: white; font: inherit; padding: 10px; }
.message-editor p, .message-state { color: #bfb1d1; font-size: 12px; line-height: 1.6; }
.message-editor > div { display: flex; justify-content: flex-end; gap: 8px; }
.message-editor .edit-files { flex-wrap: wrap; justify-content: flex-start; margin-top: 8px; font-size: 12px; }
.conversation-scroll { max-height: 400px; overflow-y: auto; overflow-x: hidden; overscroll-behavior: contain; scrollbar-width: thin; scrollbar-color: #b6a2dc66 transparent; }
.conversation-scroll:focus-visible { outline: 2px solid #c7b0ff; outline-offset: -3px; }
.conversation-messages { padding: 28px clamp(14px, 3vw, 36px) 40px; display: flex; flex-direction: column; gap: 28px; }
.conversation-messages.is-empty { padding: 16px; }
.conversation-empty { text-align: center; margin: auto; padding: 12px 10px; color: #c0bbd4; }
.empty-star { color: #c7b0ff; font-size: 24px; }
.conversation-empty h2 { font-size: 16px; font-weight: 500; margin: 8px 0; color: #f1eafd; }
.conversation-empty p { font-size: 14px; line-height: 1.7; }
.message-row { display: flex; align-items: flex-start; gap: 12px; min-width: 0; }
.message-avatar { width: 34px; height: 34px; border-radius: 50%; object-fit: cover; border: 1px solid #ffffff30; flex-shrink: 0; }
.message-main { min-width: 0; max-width: min(92%, 880px); flex: 1; }
.message-author { color: #ccc5de; font-size: 12px; margin: 0 0 8px; display: flex; gap: 12px; align-items: center; }
.live-label { color: #c7b0ff; font-size: 11px; }
.message-surface { color: #f2f0f9; font-size: 15px; padding: 6px 0; min-width: 0; }
.from-user { flex-direction: row-reverse; }
.from-user .message-main { flex: 0 1 auto; max-width: 80%; }
.from-user .message-author, .from-user .message-actions { justify-content: flex-end; }
.from-user .message-surface { border: 1px solid #b6a0e138; background: #a78bda1f; border-radius: 16px 4px 16px 16px; padding: 12px 16px; }
.message-actions { display: flex; gap: 6px; padding-top: 8px; }
.message-actions button, .conversation-notice button { background: transparent; border: 0; color: #aaa3bd; font: inherit; font-size: 12px; border-radius: 6px; padding: 5px 8px; cursor: pointer; }
.message-actions button:hover, .message-actions button:focus-visible { color: #f2e9ff; background: #ffffff12; }
button:focus-visible, summary:focus-visible { outline: 2px solid #c7b0ff; outline-offset: 2px; }
button:disabled { opacity: .35; cursor: not-allowed; }
.reasoning-panel { border-left: 2px solid #b6a0e144; padding: 6px 12px; margin: 6px 0 12px; color: #b9b1cb; font-size: 13px; }
.reasoning-panel summary { cursor: pointer; padding: 5px 0; }
.tool-label { display: flex; flex-wrap: wrap; gap: 8px; color: #c2b3e0; font-size: 12px; margin-bottom: 6px; }
.is-error .message-surface { color: #ffd0cc; border-left: 2px solid #d98d88; padding-left: 12px; }
.message-images { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin-top: 12px; }
.message-images button { background: #ffffff08; border: 1px solid #ffffff18; border-radius: 10px; overflow: hidden; color: #d4ccdf; cursor: pointer; text-align: left; }
.message-images img { display: block; width: 100%; height: 150px; object-fit: cover; }
.message-images span { display: block; padding: 8px; font-size: 12px; }
.message-files { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.message-files button { background: none; border: 0; cursor: pointer; }
.message-files img { width: 80px; height: 70px; object-fit: cover; border-radius: 8px; }
.message-files span { font-size: 12px; color: #c9c3d6; }
.message-sources { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.message-sources a { font-size: 12px; color: #d4c1ff; }
.jump-latest { position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%); border: 1px solid #cfbaff55; background: #29223e; color: #f2eaff; border-radius: 30px; padding: 10px 18px; box-shadow: 0 6px 24px #0006; cursor: pointer; font-size: 12px; }
.conversation-notice { position: absolute; top: 12px; left: 50%; transform: translateX(-50%); background: #30283f; border: 1px solid #ffffff25; border-radius: 10px; padding: 8px 14px; color: #e7dff1; font-size: 12px; box-shadow: 0 4px 24px #0004; }
.conversation-notice button { color: #d6bdff; }
.typing-indicator { display: flex; gap: 5px; padding: 10px 0; }
.typing-indicator i { width: 5px; height: 5px; background: #c9b5ed; border-radius: 50%; animation: breathe 1.2s infinite; }
.typing-indicator i:nth-child(2) { animation-delay: .15s; }.typing-indicator i:nth-child(3) { animation-delay: .3s; }
@keyframes breathe { 50% { opacity: .25; transform: translateY(-2px); } }
@media (prefers-reduced-motion: reduce) { .typing-indicator i { animation: none; } }
@media (max-width: 600px) { .message-avatar { width: 26px; height: 26px; }.message-row { gap: 8px; }.message-main { max-width: calc(100% - 34px); }.from-user .message-main { max-width: 85%; }.message-surface { font-size: 14px; } }
</style>
