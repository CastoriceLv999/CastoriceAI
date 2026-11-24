<template>
  <StartupExperience v-if="startupActive" :background-ready="backgroundReady" @reveal="startupOpacity=$event" @handoff="backgroundActive=true" @finished="startupActive=false;startupOpacity=1" />
  <div class="app-wrapper" :style="cssVars" :class="[bodyClasses, {'startup-pending':startupActive}]" :inert="startupActive">
    <!-- 视频背景层（全局统一） -->
    <div class="media-layer">
      <VideoBackground ref="videoRef" :paused="startupActive && !backgroundActive" @ready="backgroundReady=$event" />
      <FloatingClock />
    </div>

    <!-- 音乐播放器 -->
    <MusicPlayer v-show="currentPage === 'chat'" ref="musicRef" />

    <!-- 顶部导航栏 -->
    <nav class="top-nav">
      <div class="nav-brand-wrapper" @click="navigate('home')">
        <img src="/images/castorice_logo1.png" alt="Logo" class="nav-logo" />
        <div class="nav-brand">Castorice</div>
      </div>
      <div class="nav-links">
        <a v-for="item in navItems" :key="item.id"
          :class="['nav-item', { active: currentPage === item.id }]"
          @click.prevent="navigate(item.id)" href="#">
          {{ item.label }}
        </a>
        <button class="settings-trigger" @click="settingsOpen = true">⚙ 应用设置</button>
      </div>
    </nav>

    <!-- 主页 -->
    <div v-show="currentPage === 'home'" class="page-container">
      <div class="coming-soon">
        <div class="coming-soon-emoji">🏠</div>
        <h1>{{ t('home') }}</h1>
        <p>{{ t('welcome') }}</p>
        <div class="coming-soon-hint">{{ t('comingSoon') }}</div>
      </div>
    </div>

    <!-- Castorice AI 聊天页 -->
    <div v-show="currentPage === 'chat'" class="chat-page">
      <TitleHeader page-type="ai" />
      <div class="main-layout" >
        <main class="content">
          <!-- 保留原布局：输入框 → 附件 → 聊天消息 → 历史记录 -->
          <ChatInput v-model="chatDraft" @send="handleSend" @upload="handleFileUpload" @stop="stopChat"
            :disabled="isLoading || application.pendingRoutes[activeChatModule]" :can-stop="isLoading" :is-uploading="isUploading" />
          <div class="chat-quick-options"><ModelSwitcher :module="activeChatModule" :disabled="isLoading || isUploading" @settings="settingsOpen=true" /><label><input type="checkbox" v-model="enableSearch" :disabled="isLoading || !chatSearchAvailable" />联网</label><label><input type="checkbox" v-model="thinkingMode" :disabled="isLoading" />思考</label></div>
          <p v-if="application.error" class="save-warning" role="alert">{{application.error}} <button @click="settingsOpen=true">打开设置</button></p>
          <!-- 文件区域 -->
          <div v-if="uploadedFiles.length" class="file-area">
            <div class="file-tags">
              <div v-for="(file, idx) in uploadedFiles" :key="file.file_id" class="file-tag"
                :class="{ 'is-image': file.type === 'image' }">
                <img
                  v-if="file.type === 'image'"
                  :src="file.url"
                  class="file-thumb"
                  alt="thumb"
                  @click="handlePreview(file.url)"
                />
                <span v-else class="file-ico">📄</span>
                <span class="file-name">{{ file.filename }}</span>
                <button class="file-del" @click="removeFile(idx)">✕</button>
              </div>
              <button class="file-clear" @click="clearFiles">清空</button>
            </div>
          </div>
          <p v-if="chatSaveError" class="save-warning" role="alert">{{ chatSaveError }}</p>
          <ChatArea v-model:messages="messages" :streamingMsg="streamingMsg" :busy="isLoading" :can-restore="!!chatBackup"
            @edit-message="editChatMessage" @regenerate="regenerateChat" @restore-previous="restoreChat" />
          <!-- 会话记录在最下方 -->
          <SessionHistory :messages="messages" :inert="isLoading"
            @load-session="handleLoadSession"
            @clear-messages="handleClearMessages" />
        </main>
      </div>
    </div>

    <!-- Castorice Studio 图像工坊 -->
    <div v-show="currentPage === 'studio'" class="chat-page">
      <TitleHeader page-type="studio" :subtitle="studioSubtitle" />
      <div class="main-layout" >
        <main class="content">
          <div class="chat-quick-options"><label>创作方式<select v-model="studioMode" :disabled="studioBusy"><option value="image">图片</option><option value="video">视频</option></select></label><ModelSwitcher :module="studioMode" :disabled="studioBusy" @settings="settingsOpen=true" /><button @click="settingsOpen=true">生成参数</button></div>
          <ImageStudio
            :external-disabled="application.pendingRoutes.image"
            v-if="studioMode === 'image'"
            :alpha="alpha"
            :size="studioSize"
            :count="studioCount"
            :watermark="imageWatermark" :prompt-extend="imagePromptExtend" :negative-prompt="imageNegativePrompt"
            @busy-change="studioBusy = $event"
            @generation-complete="onGenerationComplete"
          />
          <VideoStudio
            :external-disabled="application.pendingRoutes.video"
            v-else
            :resolution="videoResolution"
            :ratio="videoRatio"
            :duration="videoDuration"
            :watermark="videoWatermark"
            :promptExtend="videoPromptExtend"
            :audio="videoAudio"
            @busy-change="studioBusy = $event"
            @generation-complete="onVideoGenerationComplete"
          />
          <StudioHistory ref="studioHistoryRef" />
        </main>
      </div>
    </div>

    <!-- Castorice Agent 页面 -->
    <div v-show="currentPage === 'agent'" class="chat-page">
      <TitleHeader page-type="agent" />
      <div class="main-layout" >
        <main class="content">
          <div class="chat-quick-options"><label>工具<select v-model="agentTool" :disabled="agentBusy"><option value="auto">智能选择</option><option value="search">联网搜索</option><option value="web_extract">网页读取</option><option value="code">代码工具</option><option value="search_image">文字搜图</option><option value="image_search">以图搜图</option></select></label><ModelSwitcher :module="['search_image','image_search'].includes(agentTool)?agentTool:'agent'" :disabled="agentBusy" @settings="settingsOpen=true" /></div>
          <AgentStudio
            :external-disabled="application.pendingRoutes[['search_image','image_search'].includes(agentTool)?agentTool:'agent']"
            :agentTool="agentTool"
            ref="agentStudioRef"
            @session-update="onAgentSessionUpdate"
            @busy-change="agentBusy = $event"
            @request-image-gen="onRequestImageGen"
          />
          <AgentHistory :inert="agentBusy"
            ref="agentHistoryRef"
            :sessionData="agentSessionData"
            @load-session="onLoadAgentSession"
            @clear-session="onClearAgentSession"
            @new-session="onNewAgentSession"
          />
        </main>
      </div>
    </div>

    <!-- 关于我 -->
    <div v-show="currentPage === 'about'" class="page-container">
      <div class="coming-soon">
        <div class="coming-soon-emoji">👤</div>
        <h1>{{ t('about') }}</h1>
        <div class="coming-soon-hint">{{ t('comingSoon') }}</div>
      </div>
    </div>

    <ImagePreview ref="previewRef" />
    <ApplicationSettings v-if="settingsOpen" :disabled="isLoading || isUploading || studioBusy || agentBusy" @close="settingsOpen=false">
      <template #general><label>系统字体<select :value="currentFont" @change="setFont($event.target.value)"><option v-for="font in fontOptions" :key="font.value" :value="font.value">{{font.label}}</option></select></label><label>系统语言<select :value="currentLang" @change="setLang($event.target.value)"><option v-for="lang in langOptions" :key="lang.value" :value="lang.value">{{lang.label}}</option></select></label><p>字体与语言修改后自动保存。</p></template>
      <template #parameters><details class="parameter-section"><summary>聊天参数</summary><SettingsPanel :disabled="isLoading || isUploading" :save-error="preferenceError" @reset="preferences.reset('chat')" v-model="alpha" v-model:streamMode="streamMode"
                v-model:thinkingMode="thinkingMode" v-model:imageMode="imageMode"
                v-model:enableSearch="enableSearch"
                :hide-ai-mode="false"
                :hide-search-mode="false"
                :hide-image-mode="false"/></details><details class="parameter-section"><summary>图片与视频参数</summary><SettingsPanel :disabled="studioBusy" :save-error="preferenceError" @reset="preferences.reset(studioMode)"
                v-model="alpha"
                v-model:streamMode="streamMode"
                v-model:thinkingMode="thinkingMode"
                v-model:imageMode="imageMode"
                v-model:studioSize="studioSize"
                v-model:studioCount="studioCount"
                v-model:studioMode="studioMode"
                v-model:videoResolution="videoResolution"
                v-model:videoRatio="videoRatio"
                v-model:videoDuration="videoDuration"
                v-model:videoWatermark="videoWatermark"
                v-model:videoPromptExtend="videoPromptExtend"
                v-model:videoAudio="videoAudio"
                v-model:imageWatermark="imageWatermark"
                v-model:imagePromptExtend="imagePromptExtend"
                v-model:imageNegativePrompt="imageNegativePrompt"
                :show-studio-params="true"
                :hide-ai-mode="true"  
                :hide-search-mode="true"   
                :hide-image-mode="true"   
              /></details><details class="parameter-section"><summary>Agent 工具</summary><SettingsPanel :disabled="agentBusy" :save-error="preferenceError" @reset="preferences.reset('agent')"
                v-model="alpha"
                v-model:streamMode="streamMode"
                v-model:thinkingMode="thinkingMode"
                v-model:imageMode="imageMode"
                v-model:agentTool="agentTool"
                :show-agent-params="true"
                :hide-ai-mode="true"
                :hide-image-mode="true"
                :hide-search-mode="true"
                v-model:enableSearch="enableSearch"
              /></details></template>
    </ApplicationSettings>
  </div>
</template>

<script setup>
import { ref, toRef, computed, onMounted, onBeforeUnmount, provide, nextTick, watch } from 'vue'
import { useConversation } from './composables/useConversation.js'
import { usePreferences } from './composables/usePreferences.js'
import VideoBackground from './components/VideoBackground.vue'
import MusicPlayer from './components/MusicPlayer.vue'
import FloatingClock from './components/FloatingClock.vue'
import TitleHeader from './components/TitleHeader.vue'
import ChatArea from './components/ChatArea.vue'
import ChatInput from './components/ChatInput.vue'
import SettingsPanel from './components/SettingsPanel.vue'
import ApplicationSettings from './components/ApplicationSettings.vue'
import ModelSwitcher from './components/ModelSwitcher.vue'
import StartupExperience from './components/StartupExperience.vue'
import { application, appearance, loadApplicationSettings, routeFor } from './composables/useApplicationSettings.js'
import SessionHistory from './components/SessionHistory.vue'
import ImageStudio from './components/ImageStudio.vue'
import VideoStudio from './components/VideoStudio.vue'
import StudioHistory from './components/StudioHistory.vue'
import ImagePreview from './components/ImagePreview.vue'
import AgentStudio from './components/AgentStudio.vue'
import AgentHistory from './components/AgentHistory.vue'

const preferences = usePreferences()
const startupActive = ref(true)
const startupOpacity = ref(0)
const backgroundReady = ref(false)
const backgroundActive = ref(false)
const appAppearance = computed(appearance)
provide('appAppearance', appAppearance)
let settingsRetryTimer
onMounted(() => {
  loadApplicationSettings()
  let attempts = 0
  settingsRetryTimer = setInterval(() => {
    if (application.loaded || ++attempts > 30) { clearInterval(settingsRetryTimer); return }
    loadApplicationSettings()
  }, 2000)
})
onBeforeUnmount(() => clearInterval(settingsRetryTimer))
const preferenceError = preferences.error
const enableSearch = toRef(preferences.values, 'enableSearch')
const previewRef = ref(null)
provide('imagePreview', previewRef)

const handlePreview = (url) => {
  previewRef.value?.open?.(url)
}

const videoPromptExtend = toRef(preferences.values, 'videoPromptExtend')
const imageWatermark = toRef(preferences.values, 'imageWatermark')
const imagePromptExtend = toRef(preferences.values, 'imagePromptExtend')
const imageNegativePrompt = toRef(preferences.values, 'imageNegativePrompt')
const videoAudio = toRef(preferences.values, 'videoAudio')
const studioBusy = ref(false)
const studioHistoryRef = ref(null)

const onGenerationComplete = (record) => {
  studioHistoryRef.value?.addRecord?.(record)
}

const onVideoGenerationComplete = (record) => {
  studioHistoryRef.value?.addRecord?.({
    ...record,
    mode: 'video'
  })
}

// 定义滚动函数
const scrollToTop = () => {
  nextTick(() => {
    const chatArea = document.querySelector('.chat-scroll-area')
    if (chatArea) {
      chatArea.scrollTop = 0
    }
  })
}

// ===== 多语言文案 =====
const i18n = {
  'zh-CN': {
    home: '主页', chat: 'Castorice AI', studio: 'Castorice Studio', agent: 'Castorice Agent', about: '关于我',
    welcome: '欢迎来到 Castorice 的世界', comingSoon: '敬请期待更多内容......',
    overlayTitle: '点击任意处开启Castorice之旅', overlaySub: '不可思议的相遇，从一段旋律开始......',
    settings: '应用设置', systemFont: '系统字体', systemLanguage: '系统语言',
    expand: '展开', collapse: '收起',
    fontNoto: 'Noto Sans（默认）', fontWenkai: '霞鹜文楷（文艺）',
    fontOutfit: 'Outfit（现代）', fontNunito: 'Nunito（圆润）',
    langZh: '简体中文', langEn: 'English',
    placeholder: '路漫漫其修远兮，吾将上下而求索......', send: '✉ 启航',
    sessionHistory: '✦ 会话记录', newSession: '✨ 新建会话',
    endSession: '✓ 结束并保存', loadSession: '↺ 加载会话', deleteSession: '✕ 删除',
    inProgress: '进行中', saved: '已保存',
    noSession: '暂无会话记录，开始与 Castorice 对话吧......',
    messages: '条消息', noMessage: '暂无消息',
    you: '你: ', bot: 'Castorice: ',
    interfaceSettings: '🛠 界面设置', opacity: '控件透明度',
    aiMode: '🛠 AI 输出模式', stream: '⚡ 流式输出', complete: '⏳ 完整回复',
    thinking: '🧠 深度思考', thinkingOff: '🧠 关闭思考',
    checkin: '今日打卡', optionA: 'A. 哀地里亚', optionB: 'B. 斯缇科西亚', optionC: 'C. 回忆花海',
    timelineTitle: '卓越的时光轴', timelineMeet: '与你的相遇',
    timelineMeetDesc: '那一天，在翁法罗斯的星空下......',
    timelineDoll: '奇美拉娃娃', timelineDollDesc: '第一次亲手为你编织了娃娃。',
    timelineFuture: '约定的未来', timelineFutureDesc: '下一个目标：一起去斯缇科西亚看花海。',
    daysPassed: '已过去', days: '天',
    error: '抱歉，连接出现了一些问题......',
    thinkingLabel: '✦ 思考过程', thinkingPlaceholder: '思考中......',
    emptyChat: '在此输入，与Castorice开始对话......',
    startExperience: '点击任意处开启Castorice之旅', startSub: '不可思议的相遇，从一段旋律开始......'
  },
  'en-US': {
    home: 'Home', chat: 'Castorice AI', studio: 'Castorice Studio', agent: 'Castorice Agent', about: 'About',
    welcome: 'Welcome to the world of Castorice', comingSoon: 'More content coming soon......',
    overlayTitle: 'Click anywhere to start your Castorice journey',
    overlaySub: 'An incredible encounter begins with a melody......',
    settings: 'Settings', systemFont: 'System Font', systemLanguage: 'Language',
    expand: 'Expand', collapse: 'Collapse',
    fontNoto: 'Noto Sans (Default)', fontWenkai: 'LXGW WenKai (Artistic)',
    fontOutfit: 'Outfit (Modern)', fontNunito: 'Nunito (Rounded)',
    langZh: '简体中文', langEn: 'English',
    placeholder: 'The road ahead is long; I will search high and low......', send: '✉ Send',
    sessionHistory: '✦ Session History', newSession: '✨ New Session',
    endSession: '✓ End & Save', loadSession: '↺ Load', deleteSession: '✕ Delete',
    inProgress: 'In Progress', saved: 'Saved',
    noSession: 'No session history yet. Start chatting with Castorice......',
    messages: 'messages', noMessage: 'No messages',
    you: 'You: ', bot: 'Castorice: ',
    interfaceSettings: '🛠 Interface', opacity: 'Opacity',
    aiMode: '🛠 AI Output Mode', stream: '⚡ Streaming', complete: '⏳ Complete',
    thinking: '🧠 Deep Think', thinkingOff: '🧠 Off',
    checkin: 'Daily Check-in', optionA: 'A. Aedirn', optionB: 'B. Styxia', optionC: 'C. Memory Garden',
    timelineTitle: 'Timeline of Memories', timelineMeet: 'Our Encounter',
    timelineMeetDesc: 'That day, under the starlit sky of Amphoreus...',
    timelineDoll: 'Chimera Doll', timelineDollDesc: 'The first time I knitted a doll for you.',
    timelineFuture: 'Promised Future', timelineFutureDesc: 'Next goal: Visit the flower sea in Styxia together.',
    daysPassed: '', days: 'days ago',
    error: 'Sorry, something went wrong......',
    thinkingLabel: '✦ Reasoning', thinkingPlaceholder: 'Thinking...',
    emptyChat: 'Type here to start a conversation with Castorice......',
    startExperience: 'Click anywhere to start your Castorice journey',
    startSub: 'An incredible encounter begins with a melody......'
  }
}

const currentLang = ref('zh-CN')
const t = (key) => i18n[currentLang.value]?.[key] || i18n['zh-CN'][key]
provide('currentLang', currentLang)

// ===== 系统字体配置 =====
const fontOptions = computed(() => [
  { value: 'noto', label: t('fontNoto') },
  { value: 'wenkai', label: t('fontWenkai') },
  { value: 'outfit', label: t('fontOutfit') },
  { value: 'nunito', label: t('fontNunito') }
])

const langOptions = computed(() => [
  { value: 'zh-CN', label: t('langZh') },
  { value: 'en-US', label: t('langEn') }
])

const currentFont = ref('noto')
const settingsOpen = ref(false)

onMounted(() => {
  const savedFont = localStorage.getItem('castorice_font')
  const savedLang = localStorage.getItem('castorice_lang')
  if (savedFont) currentFont.value = savedFont
  if (savedLang) currentLang.value = savedLang
})

const bodyClasses = computed(() => ({
  'reduce-motion': appAppearance.value.reduce_motion,
  [`font-${currentFont.value}`]: true,
  [`lang-${currentLang.value === 'en-US' ? 'en' : 'zh'}`]: true
}))

const setFont = (font) => { currentFont.value = font; localStorage.setItem('castorice_font', font) }
const setLang = (lang) => { currentLang.value = lang; localStorage.setItem('castorice_lang', lang); updateNavItems() }
const toggleSettings = () => { settingsOpen.value = true }
const closeSettings = () => { settingsOpen.value = false }

const vClickOutside = {
  mounted(el, binding) {
    el._clickOutside = (e) => { if (!el.contains(e.target)) binding.value() }
    document.addEventListener('click', el._clickOutside)
  },
  unmounted(el) { document.removeEventListener('click', el._clickOutside) }
}

// ===== 导航项 =====
const navItems = ref([])
const updateNavItems = () => {
  navItems.value = [
    { id: 'home', label: t('home') },
    { id: 'chat', label: t('chat') },
    { id: 'studio', label: t('studio') },
    { id: 'agent', label: t('agent') },
    { id: 'about', label: t('about') },
  ]
}
updateNavItems()

const currentPage = ref('chat')
const navigate = (page) => { currentPage.value = page }

const alpha = toRef(preferences.values, 'alpha')
const cssVars = computed(() => ({
  '--interface-opacity': startupOpacity.value,
  '--message-font-size': appAppearance.value.font_size + 'px',
  '--chat-alpha': alpha.value,
  '--chat-alpha-focus': Math.min(alpha.value + 0.04, 0.55),
  '--nav-alpha': Math.min(alpha.value + 0.1, 0.6)
}))

// Studio 专属副标题
const studioSubtitle = computed(() => {
  return currentLang.value === 'en-US'
    ? 'Create your own memories------2026.06.01 | Where imagination blooms'
    : '创造属于你的回忆------2026.06.01 | 想象绽放之地'
})

const streamMode = toRef(preferences.values, 'streamMode')
const thinkingMode = toRef(preferences.values, 'thinkingMode')
const imageMode = toRef(preferences.values, 'imageMode')

// Studio 参数
const studioSize = toRef(preferences.values, 'studioSize')
const studioCount = toRef(preferences.values, 'studioCount')
const studioMode = toRef(preferences.values, 'studioMode')
const videoResolution = toRef(preferences.values, 'videoResolution')
const videoRatio = toRef(preferences.values, 'videoRatio')
const videoDuration = toRef(preferences.values, 'videoDuration')
const videoWatermark = toRef(preferences.values, 'videoWatermark')

const {
  messages, streamingMsg, isBusy: isLoading, attachments: uploadedFiles, draft: chatDraft,
  backup: chatBackup, saveError: chatSaveError, send: handleSend, editMessage: editChatMessage,
  regenerate: regenerateChat, restorePrevious: restoreChat, loadSession: handleLoadSession,
  clear: handleClearMessages, stop: stopChat
} = useConversation({
  storageKey: 'castorice_active_chat_v1',
  settings: () => ({ stream: streamMode.value, thinking: thinkingMode.value, image_mode: imageMode.value,
    enable_search: enableSearch.value, language: currentLang.value, ...routeFor(activeChatModule.value) })
})
const activeChatModule = computed(() => uploadedFiles.value.some(f => f.type === 'image') && imageMode.value === 'vision' ? 'vision' : uploadedFiles.value.some(f => !['image','video'].includes(f.type)) ? 'document' : 'chat')
const chatSearchAvailable = computed(() => application.config?.connections.find(c=>c.id===routeFor(activeChatModule.value)?.connection)?.provider === 'dashscope')
watch(() => [chatSearchAvailable.value, application.loaded], ([available,loaded]) => { if (!available && loaded) enableSearch.value = false })
const sidebarCollapsed = ref(true)
const videoRef = ref(null)
const musicRef = ref(null)

// ===== 文件上传状态 =====
const isUploading = ref(false)

const handleFileUpload = async (files) => {
  if (!files || !files.length) return
  isUploading.value = true
  for (const file of files) {
    const formData = new FormData()
    formData.append('file', file)
    try {
      const res = await fetch('/api/upload', { method: 'POST', body: formData })
      if (!res.ok) throw new Error('Upload failed')
      const data = await res.json()
      uploadedFiles.value.push(data)
    } catch (err) {
      console.error(err)
      messages.value.push({ role: 'assistant', content: `❌ 文件 ${file.name} 上传失败` })
    }
  }
  isUploading.value = false
}

const removeFile = (idx) => { uploadedFiles.value.splice(idx, 1) }
const clearFiles = () => { uploadedFiles.value = [] }

// ==================== Agent 会话状态 ====================
const agentBusy = ref(false)
const agentTool = toRef(preferences.values, 'agentTool')
const agentSessionData = ref(null)
const agentStudioRef = ref(null)
const agentHistoryRef = ref(null)

const onAgentSessionUpdate = (data) => {
  agentSessionData.value = data
}

const onRequestImageGen = ({ prompt, refFiles }) => {
  currentPage.value = 'studio'
  studioMode.value = 'image'
  nextTick(() => {
    // 如果 ImageStudio 暴露了 setPrompt 方法可以调用
    // studioHistoryRef.value?.setPrompt?.(prompt)
  })
}

const onLoadAgentSession = (messages) => {
  agentStudioRef.value?.loadSession?.(messages)
}

const onClearAgentSession = () => {
  agentStudioRef.value?.clearSession?.()
}

const onNewAgentSession = () => {
  agentStudioRef.value?.clearSession?.()
  agentSessionData.value = null
}
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Dancing+Script:wght@700&family=Ma+Shan+Zheng&family=Pacifico&family=ZCOOL+QingKe+HuangYou&family=M+PLUS+Rounded+1c:wght@400;700&family=Noto+Sans+SC:wght@300;400;500;600;700&family=Noto+Serif+SC:wght@400;600;700&family=LXGW+WenKai:wght@300;400;700&family=Inter:wght@300;400;500;600;700&family=Nunito:wght@400;600;700&family=Outfit:wght@300;400;500;600;700&display=swap');
.save-warning { font-size: 12px; color: #ffd2a6; margin: 0 0 8px; }

:root {
  --chat-alpha: 0.05;
  --chat-alpha-focus: 0.09;
  --sidebar-width: 260px;
  --sidebar-collapsed-width: 36px;
  --font-system-zh: 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  --font-system-en: 'Inter', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
  --font-system-wenkai: 'LXGW WenKai', 'Noto Sans SC', 'PingFang SC', sans-serif;
  --font-system-nunito: 'Nunito', 'Inter', sans-serif;
  --font-system-outfit: 'Outfit', 'Inter', sans-serif;
  --font-body: var(--font-system-zh);
  --font-brand: 'Pacifico', cursive, sans-serif;
  --font-title-display: 'ZCOOL QingKe HuangYou', 'PingFang SC', sans-serif;
  --font-title-art: 'Ma Shan Zheng', cursive, sans-serif;
  --font-clock: 'M PLUS Rounded 1c', 'PingFang SC', sans-serif;
  --font-dancing: 'Dancing Script', cursive;
  --lang: 'zh-CN';
}

.font-noto { --font-body: var(--font-system-zh); }
.font-wenkai { --font-body: var(--font-system-wenkai); }
.font-outfit { --font-body: var(--font-system-outfit); }
.font-nunito { --font-body: var(--font-system-nunito); }

.lang-en {
  --lang: 'en-US';
  --font-body: var(--font-system-en);
}
.lang-en.font-wenkai { --font-body: var(--font-system-nunito); }

* { margin: 0; padding: 0; box-sizing: border-box; }

html, body, #app {
  width: 100%; height: 100%; overflow-x: hidden;
  background: transparent; color: white;
}

body, #app, .app-wrapper, input, button, textarea, select, option, label {
  font-family: var(--font-body);
  transition: font-family 0.4s ease;
}

.nav-brand, .castorice-title, .coming-soon h1 {
  font-family: var(--font-brand) !important;
}

.coming-soon-hint { font-family: var(--font-title-art) !important; }

#floating-clock-card .fclock-time { font-family: var(--font-clock) !important; }
#floating-clock-card .fclock-meta { font-family: var(--font-title-display) !important; }

.castorice-subtitle { font-family: var(--font-title-display) !important; }

.app-wrapper {
  position: relative; width: 100%; min-height: 100vh; background: transparent;
}

/* ========== 启动遮罩 ========== */
.start-overlay {
  position: fixed; inset: 0;
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  z-index: 100000;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  cursor: pointer; transition: opacity 0.6s ease;
}

.overlay-emoji { font-size: 3rem; margin-bottom: 20px; animation: bounce 2s infinite; }
.overlay-title { font-size: 1.6rem; color: white; text-shadow: 0 0 20px rgba(255,255,255,0.5); letter-spacing: 2px; }
.overlay-sub { margin-top: 12px; font-size: 0.9rem; color: rgba(255,255,255,0.6); }

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-12px); }
}

/* ========== 布局 ========== */
.main-layout {
  display: flex; max-width: 1200px; margin: 0 auto;
  padding: 0 2rem 2rem; gap: 2rem;
  position: relative; z-index: 1;
}

.sidebar {
  position: fixed; left: 0; top: 56px; bottom: 0;
  width: var(--sidebar-width); z-index: 100;
  transition: width 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: visible;
}

.sidebar.collapsed { width: var(--sidebar-collapsed-width); }

.sidebar-inner {
  position: relative; width: 100%; height: 100%;
  background: rgba(10, 10, 30, var(--chat-alpha));
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-right: 1px solid rgba(255,255,255,0.1);
  padding: 1.5rem;
  transition: background 0.3s ease, border-radius 0.3s ease;
  overflow: hidden;
}

.sidebar.collapsed .sidebar-inner {
  background: rgba(10, 10, 30, var(--chat-alpha));
  padding: 1rem 0; border-radius: 0 12px 12px 0;
}

.content {
  flex: 1;
  min-width: 0;
  margin-left: var(--sidebar-width);
  transition: margin-left 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.main-layout.sidebar-open .content { margin-left: var(--sidebar-width); }
.main-layout:not(.sidebar-open) .content { margin-left: var(--sidebar-collapsed-width); }

.sidebar-toggle {
  position: absolute; top: 1rem; right: 1rem;
  width: 28px; height: 28px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 6px; color: white;
  font-size: 0.85rem; cursor: pointer; z-index: 10;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.3s;
}

.sidebar-toggle:hover { background: rgba(255, 255, 255, 0.2); }

.sidebar.collapsed .sidebar-toggle {
  right: auto; left: 50%; transform: translateX(-50%); top: 1.2rem;
}

.sidebar-content {
  opacity: 1; transform: translateX(0);
  transition: opacity 0.25s ease 0.1s, transform 0.25s ease 0.1s;
  pointer-events: auto;
  max-height: calc(100% - 32px);
  margin-top: 32px;
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-width: thin;
  padding-right: 6px;
}

.sidebar.collapsed .sidebar-content {
  opacity: 0; pointer-events: none; transform: translateX(-20px);
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.sidebar h4 { margin-bottom: 1rem; font-size: 1rem; color: white; text-shadow: 0 1px 4px rgba(0,0,0,0.9); }
.sidebar label { display: block; margin: 0.8rem 0 0.3rem; font-size: 0.9rem; color: rgba(255,255,255,0.85); }
.sidebar input[type="range"] { width: 100%; margin-bottom: 1rem; accent-color: rgba(140, 220, 255, 0.9); }

.sidebar select {
  width: 100%; margin-bottom: 0.8rem; padding: 0.5rem;
  border-radius: 8px; border: 1px solid rgba(255,255,255,0.3);
  background: rgba(0,0,0,var(--chat-alpha)); color: white;
  backdrop-filter: blur(4px); outline: none; cursor: pointer;
}

.sidebar select option { background: #1a1a2e; color: white; }

/* ========== 文件标签区域 ========== */
.file-area { margin-bottom: 0.8rem; }
.file-tags { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }

.file-tag {
  display: inline-flex; align-items: center; gap: 0.4rem;
  padding: 0.35rem 0.7rem;
  background: rgba(0, 0, 0, var(--chat-alpha, 0.05));
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px; font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(6px);
  transition: all 0.3s;
}

.file-tag.is-image {
  border-color: rgba(140, 220, 255, 0.4);
  background: rgba(10, 20, 40, 0.35);
}

.file-thumb {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  object-fit: cover;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid rgba(255,255,255,0.2);
  flex-shrink: 0;
}

.file-thumb:hover {
  transform: scale(1.08);
  box-shadow: 0 0 12px rgba(140, 220, 255, 0.35);
}

.file-ico { font-size: 0.9rem; }
.file-name { max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.file-del {
  background: none; border: none;
  color: rgba(255, 120, 120, 0.7);
  cursor: pointer; font-size: 0.75rem;
  padding: 0 0.15rem; line-height: 1;
  transition: color 0.2s;
}

.file-del:hover { color: #ff5555; }

.file-clear {
  padding: 0.25rem 0.6rem; font-size: 0.8rem;
  background: rgba(255, 100, 100, 0.12);
  border: 1px solid rgba(255, 100, 100, 0.25);
  color: rgba(255, 150, 150, 0.9);
  border-radius: 6px; cursor: pointer;
  transition: all 0.2s; font-family: inherit;
}

.file-clear:hover {
  background: rgba(255, 100, 100, 0.25);
  border-color: rgba(255, 100, 100, 0.45);
}

/* ========== 聊天区域（全局兜底，供子组件继承） ========== */
.chat-scroll-area {
  max-height: 320px; overflow-y: auto; overflow-x: hidden;
  padding-right: 8px; margin: 1rem 0;
  display: flex; flex-direction: column;
  scrollbar-width: thin;
  scrollbar-color: rgba(255,255,255,0.3) transparent;
}

.chat-scroll-area::-webkit-scrollbar { width: 6px; }
.chat-scroll-area::-webkit-scrollbar-thumb { background-color: rgba(255,255,255,0.3); border-radius: 3px; }
.chat-scroll-area::-webkit-scrollbar-track { background: transparent; }

.chat-row { display: flex; margin-bottom: 14px; align-items: flex-start; }
.chat-row.user { flex-direction: row-reverse; }
.chat-row.assistant { flex-direction: row; }

.chat-avatar {
  width: 58px; height: 58px; border-radius: 50%;
  flex-shrink: 0; margin: 0 10px; position: relative;
}

.chat-avatar::before {
  content: ""; position: absolute; inset: 0; border-radius: 50%;
  background: conic-gradient(
    from 0deg, transparent 0%, rgba(140, 220, 255, 0.9) 25%,
    rgba(255, 255, 255, 0.9) 50%, rgba(140, 220, 255, 0.9) 75%, transparent 100%
  );
  animation: borderFlow 2.5s linear infinite; z-index: 0;
}

.chat-row.assistant .chat-avatar::before {
  background: conic-gradient(
    from 0deg, transparent 0%, rgba(220, 160, 255, 0.9) 25%,
    rgba(255, 200, 255, 0.9) 50%, rgba(220, 160, 255, 0.9) 75%, transparent 100%
  );
}

.chat-avatar .avatar-img {
  position: absolute; inset: 3px;
  width: calc(100% - 6px); height: calc(100% - 6px);
  border-radius: 50%; object-fit: cover;
  border: 1px solid rgba(255, 255, 255, 0.35); z-index: 1;
}

@keyframes borderFlow {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.chat-bubble {
  max-width: 78%; padding: 10px 14px; border-radius: 14px;
  background-color: rgba(0, 0, 0, var(--chat-alpha));
  border: 1px solid rgba(255, 255, 255, 0.35);
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.15);
  color: white; font-size: 0.95rem; line-height: 1.6;
  word-wrap: break-word; text-shadow: 0 1px 4px rgba(0,0,0,0.9);
}

/* ========== 思考气泡 ========== */
.think-bubble {
  max-width: 78%; padding: 10px 14px; border-radius: 14px;
  background-color: rgba(40, 10, 60, var(--chat-alpha-focus));
  border: 1px solid rgba(200, 140, 255, 0.4);
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.15);
  color: #e8d5ff; font-size: 0.9rem; line-height: 1.6;
  word-wrap: break-word; margin-bottom: 8px;
}

/* ========== 输入区域（全局兜底） ========== */
.chat-form {
  position: sticky;
  top: 0;
  z-index: 10;
  margin-bottom: 0.5rem;
}

.chat-form input {
  flex: 1; padding: 0.8rem 1rem; border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.35);
  background: rgba(0,0,0,var(--chat-alpha));
  color: white;
  font-size: 1rem; outline: none; caret-color: white;
  box-shadow: 0 4px 30px rgba(0,0,0,0.15); transition: all 0.3s;
}

.chat-form input::placeholder { color: rgba(255,255,255,0.55); font-family: inherit; }
.chat-form input:focus {
  background: rgba(0,0,0,var(--chat-alpha-focus));
  border-color: rgba(255,255,255,0.6);
  box-shadow: 0 0 20px rgba(255,255,255,0.15);
}

.chat-form button {
  padding: 0 1.2rem; border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.35);
  background: rgba(255,255,255, calc(var(--chat-alpha) + 0.07));
  color: white;
  cursor: pointer; font-size: 1rem; transition: all 0.3s;
  box-shadow: 0 4px 20px rgba(0,0,0,0.2);
}

.chat-form button:hover:not(:disabled) {
  background: rgba(255,255,255, calc(var(--chat-alpha) + 0.2));
  border-color: rgba(255,255,255,0.5);
}

.chat-form button:disabled { opacity: 0.5; cursor: not-allowed; }

/* ========== 时间轴/会话记录 ========== */
.timeline-section h3 { margin: 2rem 0 1rem; color: white; text-shadow: 0 1px 4px rgba(0,0,0,0.9); }

.timeline-container {
  position: relative; margin-left: 20px;
  border-left: 2px solid rgba(255,255,255,0.3); padding-left: 20px;
}

.timeline-item { position: relative; margin-bottom: 25px; }

.timeline-dot {
  position: absolute; left: -31px; top: 4px;
  width: 12px; height: 12px; background: rgba(255,255,255,0.8);
  border-radius: 50%; box-shadow: 0 0 10px rgba(255,255,255,0.5);
}

.timeline-card {
  background: rgba(0,0,0,var(--chat-alpha));
  padding: 12px 16px; border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.2);
  backdrop-filter: blur(4px);
}

.timeline-date { font-size: 0.85em; color: rgba(255,255,255,0.6); }
.timeline-title { font-weight: bold; color: white; margin: 4px 0; }
.timeline-desc { color: rgba(255,255,255,0.8); font-size: 0.9em; }

/* ========== 空状态 ========== */
.empty-hint { color: rgba(255,255,255,0.35); text-align: center; margin: 2rem 0; }

/* ========== 顶部导航栏 ========== */
.top-nav {
  position: fixed; top: 0; left: 0; right: 0; height: 56px;
  background: rgba(10, 10, 30, var(--nav-alpha, 0.35));
  backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 2rem; z-index: 1000; transition: background 0.3s ease;
}

.nav-brand-wrapper { display: flex; align-items: center; gap: 0.6rem; cursor: pointer; transition: all 0.3s; }
.nav-brand-wrapper:hover { transform: scale(1.03); }

.nav-logo {
  width: 36px; height: 36px; border-radius: 50%; object-fit: cover;
  border: 2px solid rgba(140, 220, 255, 0.5);
  box-shadow: 0 0 10px rgba(140, 220, 255, 0.3);
  animation: navLogoPulse 3s ease-in-out infinite; transition: all 0.3s;
}

.nav-brand-wrapper:hover .nav-logo {
  border-color: rgba(140, 220, 255, 0.8);
  box-shadow: 0 0 15px rgba(140, 220, 255, 0.5);
  transform: rotate(10deg) scale(1.1);
}

@keyframes navLogoPulse {
  0%, 100% { box-shadow: 0 0 8px rgba(140, 220, 255, 0.3); }
  50% { box-shadow: 0 0 15px rgba(140, 220, 255, 0.5), 0 0 25px rgba(220, 160, 255, 0.2); }
}

.nav-brand {
  font-family: var(--font-brand) !important; font-size: 1.6rem;
  color: #e0f7ff; text-shadow: 0 0 12px rgba(100, 200, 255, 0.8);
  letter-spacing: 1px; transition: all 0.3s;
}

.nav-brand-wrapper:hover .nav-brand {
  text-shadow: 0 0 20px rgba(100, 200, 255, 1), 0 0 40px rgba(80, 180, 255, 0.5);
}

.nav-links { display: flex; gap: 0.5rem; align-items: center; position: relative; }

.nav-item {
  padding: 0.5rem 1rem; border-radius: 8px;
  color: rgba(255, 255, 255, 0.7); text-decoration: none;
  font-size: 0.95rem; transition: all 0.3s; cursor: pointer;
  border: 1px solid transparent; text-shadow: 0 1px 4px rgba(0,0,0,0.9);
}

.nav-item:hover { color: white; background: rgba(255, 255, 255, 0.08); border-color: rgba(255, 255, 255, 0.15); }

.nav-item.active {
  color: #e0f7ff; background: rgba(100, 200, 255, 0.15);
  border-color: rgba(100, 200, 255, 0.4);
  box-shadow: 0 0 15px rgba(100, 200, 255, 0.2);
}

/* ========== 页面设置下拉框 ========== */
.nav-settings { position: relative; display: inline-block; }

.settings-trigger {
  padding: 0.5rem 1rem; border-radius: 8px;
  color: rgba(255, 255, 255, 0.7); font-size: 0.95rem;
  cursor: pointer; border: 1px solid transparent;
  background: transparent; transition: all 0.3s;
  display: flex; align-items: center; gap: 0.3rem;
  font-family: inherit;
}

.settings-trigger:hover { color: white; background: rgba(255, 255, 255, 0.08); border-color: rgba(255, 255, 255, 0.15); }

.settings-trigger .arrow { transition: transform 0.3s; font-size: 0.7rem; }
.nav-settings.open .settings-trigger .arrow { transform: rotate(180deg); }

.settings-dropdown {
  position: absolute; top: calc(100% + 8px); right: 0;
  min-width: 220px;
  background: rgba(15, 15, 35, 0.95);
  backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 12px; padding: 1rem; z-index: 1001;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  opacity: 0; visibility: hidden;
  transform: translateY(-8px);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  pointer-events: none;
}

.nav-settings.open .settings-dropdown {
  opacity: 1; visibility: visible;
  transform: translateY(0); pointer-events: auto;
}

.settings-group { margin-bottom: 1rem; }
.settings-group:last-child { margin-bottom: 0; }

.settings-label {
  font-size: 0.8rem; color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase; letter-spacing: 1px;
  margin-bottom: 0.6rem; display: block;
}

.settings-options { display: flex; flex-direction: column; gap: 0.3rem; }

.settings-option {
  padding: 0.5rem 0.8rem; border-radius: 8px;
  border: 1px solid transparent; background: transparent;
  color: rgba(255, 255, 255, 0.8); font-size: 0.9rem;
  cursor: pointer; transition: all 0.2s; text-align: left;
  font-family: inherit; display: flex; align-items: center; gap: 0.5rem;
}

.settings-option:hover { background: rgba(255, 255, 255, 0.08); color: white; }

.settings-option.active {
  background: rgba(100, 200, 255, 0.15);
  border-color: rgba(100, 200, 255, 0.35);
  color: #e0f7ff;
}

.settings-option .check { font-size: 0.8rem; opacity: 0; transition: opacity 0.2s; }
.settings-option.active .check { opacity: 1; }

.settings-divider { height: 1px; background: rgba(255, 255, 255, 0.1); margin: 0.8rem 0; }

/* ========== 页面容器 ========== */
.page-container { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding-top: 56px; }

/* ========== 敬请期待 ========== */
.coming-soon { text-align: center; padding: 3rem; }

.coming-soon-emoji { font-size: 5rem; margin-bottom: 1.5rem; animation: bounce 2s infinite; }

.coming-soon h1 {
  font-family: var(--font-title-display) !important; font-size: 3.5rem;
  color: #e0f7ff;
  text-shadow: 0 0 20px rgba(100, 200, 255, 0.8), 0 0 6px rgba(0, 120, 255, 0.9);
  margin-bottom: 1rem; letter-spacing: 4px;
}

.coming-soon p { font-size: 1.2rem; color: rgba(255, 255, 255, 0.7); margin-bottom: 2rem; text-shadow: 0 1px 4px rgba(0,0,0,0.9); }

.coming-soon-hint {
  font-family: var(--font-title-art) !important; font-size: 2rem;
  color: rgba(220, 180, 255, 0.9);
  text-shadow: 0 0 15px rgba(200, 140, 255, 0.6);
  letter-spacing: 8px; animation: pulse 3s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.6; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.05); }
}

/* ========== 聊天页调整 ========== */
.chat-page { padding-top: 56px; position: relative; z-index: 1; }

/* ========== 媒体层 ========== */
.media-layer { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: -1; pointer-events: none; }

/* ========== 响应式 ========== */
@media (max-width: 768px) {
  .main-layout { flex-direction: column; padding: 0 1rem 1rem; }
  .sidebar { position: fixed; left: 0; top: 48px; bottom: auto; height: 70dvh; max-height: 640px; width: var(--sidebar-width); z-index: 100; }
  .sidebar.collapsed { width: var(--sidebar-collapsed-width); height: 64px; }
  .content { margin-left: 0 !important; margin-top: 1rem; }
  .main-layout.sidebar-open .content, .main-layout:not(.sidebar-open) .content { margin-left: 0; }
  .top-nav { padding: 0 1rem; height: 48px; }
  .nav-brand-wrapper { gap: 0.4rem; }
  .nav-logo { width: 28px; height: 28px; }
  .nav-brand { font-size: 1.2rem; }
  .nav-item { padding: 0.4rem 0.6rem; font-size: 0.85rem; }
  .coming-soon h1 { font-size: 2.5rem; }
  .coming-soon-hint { font-size: 1.5rem; }
  .page-container, .chat-page { padding-top: 48px; }
  .settings-dropdown { right: -1rem; min-width: 200px; }
  .file-name { max-width: 80px; }
}
</style>

<style>
.chat-quick-options{display:flex;align-items:center;gap:12px;flex-wrap:wrap;color:#ddcff3;font-size:13px}.chat-quick-options select,.chat-quick-options button{background:#211831;border:1px solid #6d5684;border-radius:9px;color:#eee;padding:6px}.parameter-section{padding:14px 0;border-bottom:1px solid #493752}.parameter-section summary{cursor:pointer;font-weight:600}.reduce-motion *, .reduce-motion *::before, .reduce-motion *::after{animation:none!important;transition:none!important}.message-surface{font-size:var(--message-font-size,16px)}
</style>

<style>
.app-wrapper.startup-pending > .top-nav,.app-wrapper.startup-pending > .chat-page,.app-wrapper.startup-pending > .page-container,.app-wrapper.startup-pending .floating-clock-card,.app-wrapper.startup-pending #st-music-btn{opacity:var(--interface-opacity,0);transform:translateY(calc((1 - var(--interface-opacity,0))*10px));pointer-events:none}
</style>
