<template>
  <div class="timeline-section session-history">
    <div class="session-header">
      <h3>{{ t('sessionHistory') }}</h3>
      <div class="session-actions">
        <button 
          class="session-btn new-session-btn" 
          @click="startNewSession"
          :disabled="!currentSession || currentSession.messages.length === 0"
          :title="t('newSession')"
        >
          {{ t('newSession') }}
        </button>
      </div>
    </div>

    <div class="session-list">
      <!-- 当前进行中的会话 -->
      <div v-if="currentSession" class="timeline-item session-item active">
        <div class="timeline-dot active-dot"></div>
        <div class="timeline-card session-card">
          <div class="session-meta">
            <span class="session-badge current">{{ t('inProgress') }}</span>
            <span class="session-time">{{ formatDateTime(currentSession.startTime) }}</span>
          </div>
          <div class="session-title">
            <span class="session-name">{{ currentSession.name }}</span>
            <span class="session-count">{{ currentSession.messages.length }} {{ t('messages') }}</span>
          </div>
          <div class="session-desc">
            {{ getSessionPreview(currentSession) }}
          </div>
          <button 
            class="session-btn end-session-btn" 
            @click="endCurrentSession"
            :disabled="currentSession.messages.length === 0"
          >
            {{ t('endSession') }}
          </button>
        </div>
      </div>

      <!-- 已保存的会话列表 -->
      <div 
        v-for="(session, idx) in savedSessions" 
        :key="session.id" 
        class="timeline-item session-item"
      >
        <div class="timeline-dot"></div>
        <div class="timeline-card session-card">
          <div class="session-meta">
            <span class="session-badge saved">{{ t('saved') }}</span>
            <span class="session-time">{{ formatDateTime(session.startTime) }}</span>
            <span v-if="session.endTime" class="session-end-time">
              → {{ formatDateTime(session.endTime) }}
            </span>
          </div>
          <div class="session-title">
            <span class="session-name">{{ session.name }}</span>
            <span class="session-count">{{ session.messages.length }} {{ t('messages') }}</span>
          </div>
          <div class="session-desc">
            {{ getSessionPreview(session) }}
          </div>
          <div class="session-actions-row">
            <button class="session-btn load-btn" @click="loadSession(session, idx)">
              {{ t('loadSession') }}
            </button>
            <button class="session-btn delete-btn" @click="deleteSession(idx)">
              {{ t('deleteSession') }}
            </button>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="!currentSession && savedSessions.length === 0" class="empty-hint">
        {{ t('noSession') }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, inject } from 'vue'

const props = defineProps({
  messages: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['load-session', 'clear-messages'])

const currentLang = inject('currentLang', ref('zh-CN'))

const i18n = {
  'zh-CN': {
    sessionHistory: '✦ 会话记录',
    newSession: '✨ 新建会话',
    endSession: '✓ 结束并保存',
    loadSession: '↺ 加载会话',
    deleteSession: '✕ 删除',
    inProgress: '进行中',
    saved: '已保存',
    noSession: '暂无会话记录，开始与 Castorice 对话吧......',
    messages: '条消息',
    noMessage: '暂无消息',
    you: '你: ',
    bot: 'Castorice: '
  },
  'en-US': {
    sessionHistory: '✦ Session History',
    newSession: '✨ New Session',
    endSession: '✓ End & Save',
    loadSession: '↺ Load',
    deleteSession: '✕ Delete',
    inProgress: 'In Progress',
    saved: 'Saved',
    noSession: 'No session history yet. Start chatting with Castorice......',
    messages: 'messages',
    noMessage: 'No messages',
    you: 'You: ',
    bot: 'Castorice: '
  }
}

const t = (key) => i18n[currentLang.value]?.[key] || i18n['zh-CN'][key]

// 会话计数器
let sessionCounter = parseInt(localStorage.getItem('castorice_session_counter') || '0')

const currentSession = ref(null)
const savedSessions = ref([])

const loadSavedSessions = () => {
  try {
    const stored = localStorage.getItem('castorice_sessions')
    if (stored) savedSessions.value = JSON.parse(stored)
  } catch (e) {
    savedSessions.value = []
  }
}

const persistSessions = () => {
  try {
    localStorage.setItem('castorice_sessions', JSON.stringify(savedSessions.value))
    localStorage.setItem('castorice_session_counter', String(sessionCounter))
  } catch (e) {}
}

loadSavedSessions()

watch(() => props.messages, (newMessages) => {
  if (newMessages.length > 0) {
    if (!currentSession.value) {
      currentSession.value = {
        id: newMessages[0].id ? `session_${newMessages[0].id}` : `session_${Date.now()}_${sessionCounter++}`,
        name: generateSessionName(newMessages),
        startTime: newMessages[0].createdAt || Date.now(),
        endTime: null,
        messages: [...newMessages]
      }
    } else {
      currentSession.value.messages = [...newMessages]
      currentSession.value.name = generateSessionName(newMessages)
    }
  } else if (currentSession.value && !currentSession.value.endTime) {
    currentSession.value = null
  }
}, { deep: true, immediate: true })

function generateSessionName(messages) {
  const firstUserMsg = messages.find(m => m.role === 'user')
  if (firstUserMsg) {
    const text = firstUserMsg.content.trim()
    return text.length > 20 ? text.slice(0, 20) + '...' : text
  }
  return `${t('session')} ${formatDateShort(Date.now())}`
}

const getSessionPreview = (session) => {
    if (!session.messages || session.messages.length === 0) {
        return t('noMessage')
    }
    const lastMsg = session.messages[session.messages.length - 1]
    const prefix = lastMsg.role === 'user' ? t('you') : t('bot')
    let text = (lastMsg.content || '').trim()
    
    // 过滤零宽字符和控制字符
    text = text
        .replace(/[\u200B-\u200F\uFEFF\uFFFC\u0000-\u001F\u007F-\u009F]/g, '')
        .trim()
    
    if (!text) return prefix + '...'
    return prefix + (text.length > 40 ? text.slice(0, 40) + '...' : text)
}

const formatDateTime = (timestamp) => {
  if (!timestamp) return '--'
  const date = new Date(timestamp)
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  const ss = String(date.getSeconds()).padStart(2, '0')
  return `${y}-${m}-${d} ${hh}:${mm}:${ss}`
}

function formatDateShort(timestamp) {
  const date = new Date(timestamp)
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

const startNewSession = () => {
  if (currentSession.value && currentSession.value.messages.length > 0) {
    endCurrentSession()
  }
  emit('clear-messages')
}

const endCurrentSession = () => {
  if (!currentSession.value || currentSession.value.messages.length === 0) return
  currentSession.value.endTime = Date.now()
  savedSessions.value.unshift({ ...currentSession.value })
  persistSessions()
  currentSession.value = null
  emit('clear-messages')
}

const loadSession = (session, index) => {
  savedSessions.value.splice(index, 1)
  if (currentSession.value && currentSession.value.messages.length > 0) {
    currentSession.value.endTime = Date.now()
    savedSessions.value.unshift({ ...currentSession.value })
  }
  currentSession.value = {
    id: session.id,
    name: session.name,
    startTime: session.startTime,
    endTime: null,
    messages: [...session.messages]
  }
  persistSessions()
  emit('load-session', session.messages)
}

const deleteSession = (index) => {
  savedSessions.value.splice(index, 1)
  persistSessions()
}
</script>

<style scoped>
.session-history {
  --session-primary: rgba(140, 220, 255, 0.9);
  --session-success: rgba(100, 255, 180, 0.9);
  --session-danger: rgba(255, 120, 120, 0.9);
}

.session-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 2rem 0 1rem;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.session-header h3 {
  margin: 0;
  color: white;
  text-shadow: 0 1px 4px rgba(0,0,0,0.9);
}

.session-actions {
  display: flex;
  gap: 0.5rem;
}

/* ========== 基础按钮：统一黑底 ========== */
.session-btn {
  padding: 0.4rem 0.9rem;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.3);
  background: rgba(0, 0, 0, var(--chat-alpha));
  color: white;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.3s;
  backdrop-filter: blur(4px);
  font-family: inherit;
}

.session-btn:hover:not(:disabled) {
  background: rgba(0, 0, 0, var(--chat-alpha-focus));
  border-color: rgba(255,255,255,0.5);
  transform: translateY(-1px);
}

.session-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* 新建会话：黑底+青色边框/文字 */
.new-session-btn {
  border-color: rgba(140, 220, 255, 0.5);
  color: rgba(200, 240, 255, 1);
}

.new-session-btn:hover:not(:disabled) {
  border-color: rgba(140, 220, 255, 0.8);
  box-shadow: 0 0 15px rgba(140, 220, 255, 0.2);
}

/* 结束并保存：黑底+绿色边框/文字 */
.end-session-btn {
  margin-top: 0.6rem;
  border-color: rgba(100, 255, 180, 0.5);
  color: rgba(160, 255, 210, 1);
  font-size: 0.8rem;
}

.end-session-btn:hover:not(:disabled) {
  border-color: rgba(100, 255, 180, 0.8);
  box-shadow: 0 0 12px rgba(100, 255, 180, 0.2);
}

/* ========== 会话列表 ========== */
.session-list {
  position: relative;
  margin-left: 20px;
  border-left: 2px solid rgba(255,255,255,0.3);
  padding-left: 20px;
}

.session-item {
  position: relative;
  margin-bottom: 20px;
}

.session-item.active .timeline-dot {
  background: var(--session-primary);
  box-shadow: 0 0 12px rgba(140, 220, 255, 0.8);
  animation: pulse-dot 2s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.3); opacity: 0.7; }
}

/* ========== 会话卡片 ========== */
.session-card {
  background: rgba(0,0,0, var(--chat-alpha));
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.2);
  backdrop-filter: blur(4px);
  transition: all 0.3s;
}

.session-item.active .session-card {
  border-color: rgba(140, 220, 255, 0.4);
  background: rgba(10, 20, 40, var(--chat-alpha-focus));
  box-shadow: 0 4px 20px rgba(140, 220, 255, 0.1);
}

/* ========== 元信息 ========== */
.session-meta {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
  margin-bottom: 6px;
}

/* 修复：标签统一黑底，用边框/文字色区分状态 */
.session-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: bold;
}

/* 进行中：黑底+青色边框/文字 */
.session-badge.current {
  background: rgba(0, 0, 0, var(--chat-alpha-focus));
  color: rgba(140, 220, 255, 1);
  border: 1px solid rgba(140, 220, 255, 0.5);
}

/* 已保存：黑底+灰色边框/文字 */
.session-badge.saved {
  background: rgba(0, 0, 0, var(--chat-alpha));
  color: rgba(200, 200, 200, 0.9);
  border: 1px solid rgba(255,255,255,0.2);
}

.session-time {
  font-size: 0.8rem;
  color: rgba(255,255,255,0.6);
  font-family: 'M PLUS Rounded 1c', monospace;
}

.session-end-time {
  font-size: 0.8rem;
  color: rgba(255,255,255,0.45);
  font-family: 'M PLUS Rounded 1c', monospace;
}

.session-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin: 6px 0;
}

.session-name {
  font-weight: bold;
  color: white;
  font-size: 0.95rem;
}

.session-count {
  font-size: 0.8rem;
  color: rgba(255,255,255,0.5);
}

.session-desc {
  color: rgba(255,255,255,0.7);
  font-size: 0.85rem;
  line-height: 1.5;
  margin-bottom: 4px;
}

.session-actions-row {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

/* 加载按钮 */
.load-btn {
  font-size: 0.8rem;
  padding: 0.3rem 0.7rem;
}

.load-btn:hover {
  background: rgba(0, 0, 0, var(--chat-alpha-focus));
  border-color: rgba(140, 220, 255, 0.5);
}

/* 删除按钮 */
.delete-btn {
  font-size: 0.8rem;
  padding: 0.3rem 0.7rem;
  border-color: rgba(255, 120, 120, 0.4);
  color: rgba(255, 160, 160, 1);
}

.delete-btn:hover {
  background: rgba(0, 0, 0, var(--chat-alpha-focus));
  border-color: rgba(255, 120, 120, 0.6);
}

.empty-hint {
  color: rgba(255,255,255,0.35);
  text-align: center;
  margin: 2rem 0;
  font-size: 0.9rem;
}

@media (max-width: 768px) {
  .session-header {
    flex-direction: column;
    align-items: flex-start;
  }
  .session-title {
    flex-direction: column;
    align-items: flex-start;
  }
  .session-meta {
    gap: 0.3rem;
  }
}
</style>
