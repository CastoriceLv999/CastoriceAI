<template>
  <div class="timeline-section agent-history">
    <div class="session-header">
      <h3>{{ t('agentHistory') }}</h3>
      <div class="session-actions">
        <button 
          class="session-btn new-session-btn" 
          @click="startNewSession"
          :disabled="!currentSession || currentSession.messages.length === 0"
        >
          {{ t('newSession') }}
        </button>
        <button class="session-btn" @click="clearAll" v-if="savedSessions.length">
          {{ t('clearAll') }}
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
            <span class="session-badge tool-badge">{{ toolLabel(currentSession.lastTool) }}</span>
          </div>
          <div class="session-title">
            <span class="session-name">{{ currentSession.name }}</span>
            <span class="session-count">{{ currentSession.messageCount }} {{ t('messages') }}</span>
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
            <span class="session-badge tool-badge">{{ toolLabel(session.lastTool) }}</span>
          </div>
          <div class="session-title">
            <span class="session-name">{{ session.name }}</span>
            <span class="session-count">{{ session.messageCount }} {{ t('messages') }}</span>
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
import { ref, watch, inject } from 'vue'

const emit = defineEmits(['load-session', 'clear-session', 'new-session'])

const props = defineProps({
  // 接收当前会话的实时数据
  sessionData: {
    type: Object,
    default: null
  }
})

const currentLang = inject('currentLang', ref('zh-CN'))

const i18n = {
  'zh-CN': {
    agentHistory: '✦ Agent 会话记录',
    newSession: '✨ 新建会话',
    endSession: '✓ 结束并保存',
    loadSession: '↺ 加载会话',
    deleteSession: '✕ 删除',
    clearAll: '清空记录',
    inProgress: '进行中',
    saved: '已保存',
    noSession: '暂无 Agent 会话记录，开始你的第一次工具调用吧......',
    messages: '轮对话',
    noMessage: '暂无消息',
    you: '你: ',
    bot: '遐蝶: ',
    toolAuto: '智能自动',
    toolSearch: '联网搜索',
    toolWebExtract: '网页抓取',
    toolCode: '代码解释器',
    toolSearchImage: '图片搜索',
    toolImageSearch: '以图搜图',
    toolImageGen: '图像生成'
  },
  'en-US': {
    agentHistory: '✦ Agent Session History',
    newSession: '✨ New Session',
    endSession: '✓ End & Save',
    loadSession: '↺ Load',
    deleteSession: '✕ Delete',
    clearAll: 'Clear All',
    inProgress: 'In Progress',
    saved: 'Saved',
    noSession: 'No agent sessions yet. Start your first tool call......',
    messages: 'turns',
    noMessage: 'No messages',
    you: 'You: ',
    bot: 'Castorice: ',
    toolAuto: 'Auto',
    toolSearch: 'Web Search',
    toolWebExtract: 'Web Extract',
    toolCode: 'Code Interpreter',
    toolSearchImage: 'Image Search',
    toolImageSearch: 'Image Search',
    toolImageGen: 'Image Generation'
  }
}

const t = (key) => i18n[currentLang.value]?.[key] || i18n['zh-CN'][key]

const toolLabel = (tool) => {
  const map = {
    auto: t('toolAuto'),
    search: t('toolSearch'),
    web_extract: t('toolWebExtract'),
    code: t('toolCode'),
    search_image: t('toolSearchImage'),
    image_search: t('toolImageSearch'),
    image_gen: t('toolImageGen'),
    vision: t('toolAuto')
  }
  return map[tool] || tool
}

// ==================== 会话状态管理 ====================
let sessionCounter = parseInt(localStorage.getItem('castorice_agent_counter') || '0')

const currentSession = ref(null)
const savedSessions = ref([])

const STORAGE_KEY = 'castorice_agent_sessions'
const COUNTER_KEY = 'castorice_agent_counter'

const loadSavedSessions = () => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) savedSessions.value = JSON.parse(stored)
  } catch (e) {
    savedSessions.value = []
  }
}

const persistSessions = () => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(savedSessions.value))
    localStorage.setItem(COUNTER_KEY, String(sessionCounter))
  } catch (e) {}
}

loadSavedSessions()

// ==================== 监听实时会话数据 ====================
watch(() => props.sessionData, (newData) => {
  if (!newData?.messages?.length) { currentSession.value = null; return }
  
  if (!currentSession.value) {
    // 创建新会话
    currentSession.value = {
      id: newData.messages[0].id ? `agent_${newData.messages[0].id}` : `agent_${Date.now()}_${sessionCounter++}`,
      name: generateSessionName(newData.messages),
      startTime: newData.messages[0].createdAt || Date.now(),
      endTime: null,
      messages: [...newData.messages],
      lastTool: newData.lastTool,
      lastPrompt: newData.lastPrompt,
      messageCount: Math.ceil(newData.messages.filter(m => m.role !== 'tool').length / 2)
    }
  } else {
    // 更新现有会话
    currentSession.value.messages = [...newData.messages]
    currentSession.value.lastTool = newData.lastTool
    currentSession.value.lastPrompt = newData.lastPrompt
    currentSession.value.name = generateSessionName(newData.messages)
    currentSession.value.messageCount = Math.ceil(newData.messages.filter(m => m.role !== 'tool').length / 2)
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
  // 找到最后一条非 tool 消息
  const lastMsg = [...session.messages].reverse().find(m => m.role !== 'tool')
  if (!lastMsg) return t('noMessage')
  
  const prefix = lastMsg.role === 'user' ? t('you') : t('bot')
  const text = (lastMsg.content || '').trim()
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
  return `${y}-${m}-${d} ${hh}:${mm}`
}

function formatDateShort(timestamp) {
  const date = new Date(timestamp)
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

// ==================== 会话操作 ====================
const startNewSession = () => {
  if (currentSession.value && currentSession.value.messages.length > 0) {
    endCurrentSession()
  }
  emit('new-session')
}

const endCurrentSession = () => {
  if (!currentSession.value || currentSession.value.messages.length === 0) return
  
  currentSession.value.endTime = Date.now()
  savedSessions.value.unshift({ ...currentSession.value })
  
  // 限制保存数量
  if (savedSessions.value.length > 15) {
    savedSessions.value = savedSessions.value.slice(0, 15)
  }
  
  persistSessions()
  currentSession.value = null
  emit('clear-session')
}

const loadSession = (session, index) => {
  savedSessions.value.splice(index, 1)
  // 如果当前有会话，先保存
  if (currentSession.value && currentSession.value.messages.length > 0) {
    currentSession.value.endTime = Date.now()
    savedSessions.value.unshift({ ...currentSession.value })
  }
  
  
  // 恢复为当前会话
  currentSession.value = {
    id: session.id,
    name: session.name,
    startTime: session.startTime,
    endTime: null,
    messages: [...session.messages],
    lastTool: session.lastTool,
    lastPrompt: session.lastPrompt,
    messageCount: session.messageCount
  }
  
  persistSessions()
  emit('load-session', session.messages)
}

const deleteSession = (index) => {
  savedSessions.value.splice(index, 1)
  persistSessions()
}

const clearAll = () => {
  savedSessions.value = []
  persistSessions()
}

defineExpose({
  startNewSession,
  endCurrentSession
})
</script>

<style scoped>
.agent-history { margin-top: 2rem; }

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

.session-btn {
  padding: 0.4rem 0.9rem;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.3);
  background: rgba(0,0,0,var(--chat-alpha));
  color: white;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.3s;
  backdrop-filter: blur(4px);
  font-family: inherit;
}

.session-btn:hover:not(:disabled) {
  background: rgba(0,0,0,var(--chat-alpha-focus));
  border-color: rgba(255,255,255,0.5);
  transform: translateY(-1px);
}

.session-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* 新建会话：青色 */
.new-session-btn {
  border-color: rgba(140, 220, 255, 0.5);
  color: rgba(200, 240, 255, 1);
}

.new-session-btn:hover:not(:disabled) {
  border-color: rgba(140, 220, 255, 0.8);
  box-shadow: 0 0 15px rgba(140, 220, 255, 0.2);
}

/* 结束并保存：绿色 */
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

/* 会话列表 */
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
  background: rgba(140, 220, 255, 0.9);
  box-shadow: 0 0 12px rgba(140, 220, 255, 0.8);
  animation: pulse-dot 2s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.3); opacity: 0.7; }
}

/* 会话卡片 */
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

/* 元信息 */
.session-meta {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
  margin-bottom: 6px;
}

.session-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: bold;
}

.session-badge.current {
  background: rgba(0,0,0, var(--chat-alpha-focus));
  color: rgba(140, 220, 255, 1);
  border: 1px solid rgba(140, 220, 255, 0.5);
}

.session-badge.saved {
  background: rgba(0,0,0, var(--chat-alpha));
  color: rgba(200, 200, 200, 0.9);
  border: 1px solid rgba(255,255,255,0.2);
}

.tool-badge {
  background: rgba(100,200,255,0.15) !important;
  color: rgba(140,220,255,1) !important;
  border: 1px solid rgba(100,200,255,0.4) !important;
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
  background: rgba(0,0,0, var(--chat-alpha-focus));
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
  background: rgba(0,0,0, var(--chat-alpha-focus));
  border-color: rgba(255, 120, 120, 0.6);
}

.timeline-dot {
  position: absolute;
  left: -31px;
  top: 4px;
  width: 12px;
  height: 12px;
  background: rgba(220,160,255,0.8);
  border-radius: 50%;
  box-shadow: 0 0 10px rgba(220,160,255,0.5);
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