<template>
  <section class="settings-panel">
    <h4>{{ t('interfaceSettings') }}</h4>
    <label>{{ t('opacity') }} <output>{{ Math.round(modelValue * 100) }}%</output>
      <input type="range" min="0" max="80" :aria-label="t('opacity')" :value="Math.round(modelValue * 100)" @input="updateAlpha" />
    </label>
    <fieldset :disabled="disabled">
      <div v-if="!hideAiMode" class="settings-group">
        <h4>{{ t('aiMode') }}</h4>
        <label>{{ t('responseMode') }}<select v-model="localStream" :aria-label="t('responseMode')"><option :value="true">{{ t('stream') }}</option><option :value="false">{{ t('complete') }}</option></select></label>
        <label>{{ t('thinkingSetting') }}<select v-model="localThink" :aria-label="t('thinkingSetting')"><option :value="false">{{ t('thinkingOff') }}</option><option :value="true">{{ t('thinking') }}</option></select></label>
      </div>
      <label v-if="!hideSearchMode">{{ t('searchMode') }}<select v-model="localSearch" :aria-label="t('searchMode')"><option :value="false">{{ t('searchOff') }}</option><option :value="true">{{ t('searchOn') }}</option></select></label>
      <p v-if="!hideSearchMode" class="settings-hint">{{ t('searchHint') }}</p>
      <div v-if="!hideImageMode">
        <label>{{ t('imageMode') }}<select v-model="localImageMode" :aria-label="t('imageMode')"><option value="vision">{{ t('modeVision') }}</option><option value="ocr">{{ t('modeOcr') }}</option></select></label>
        <p class="settings-hint">{{ t('imageHint') }}</p>
      </div>
      <div v-if="showStudioParams" class="settings-group">
        <label>{{ t('studioMode') }}<select :value="studioMode" @change="updateStudioMode" :aria-label="t('studioMode')"><option value="image">🖼️ {{ t('modeImage') }}</option><option value="video">🎬 {{ t('modeVideo') }}</option></select></label>
        <template v-if="studioMode === 'image'">
          <label>{{ t('sizeLabel') }}<select :value="studioSize" @change="updateStudioSize" :aria-label="t('sizeLabel')"><option v-for="size in IMAGE_SIZES" :key="size" :value="size">{{ size.replace('*', '×') }}</option></select></label>
          <label>{{ t('countLabel') }}<select :value="studioCount" @change="updateStudioCount" :aria-label="t('countLabel')"><option v-for="count in 6" :key="count" :value="count">{{ count }} {{ t('countUnit') }}</option></select></label>
          <details><summary>{{ t('advanced') }}</summary>
            <label class="check-label"><input type="checkbox" :checked="imagePromptExtend" @change="emit('update:imagePromptExtend', $event.target.checked)" />{{ t('promptExtend') }}</label>
            <label class="check-label"><input type="checkbox" :checked="imageWatermark" @change="emit('update:imageWatermark', $event.target.checked)" />{{ t('watermark') }}</label>
            <label>{{ t('negativePrompt') }}<textarea rows="3" maxlength="500" :value="imageNegativePrompt" @input="emit('update:imageNegativePrompt', $event.target.value)" :aria-label="t('negativePrompt')" :placeholder="t('negativePromptPlaceholder')"></textarea></label>
          </details>
        </template>
        <template v-else>
          <label>{{ t('resolution') }}<select :value="videoResolution" @change="updateVideoResolution" :aria-label="t('resolution')"><option v-for="resolution in ['480P','720P','1080P']" :key="resolution">{{ resolution }}</option></select></label>
          <label>{{ t('ratio') }}<select :value="videoRatio" @change="updateVideoRatio" :aria-label="t('ratio')"><option v-for="ratio in VIDEO_RATIOS" :key="ratio" :value="ratio">{{ ratio === 'adaptive' ? t('adaptive') : ratio }}</option></select></label>
          <label class="check-label"><input type="checkbox" :checked="videoDuration === -1" @change="emit('update:videoDuration', $event.target.checked ? -1 : 5)" />{{ t('autoDuration') }}</label>
          <label>{{ t('duration') }} <output>{{ videoDuration === -1 ? t('autoDuration') : videoDuration + ' ' + t('seconds') }}</output><input type="range" min="2" max="30" :disabled="videoDuration === -1" :value="videoDuration === -1 ? 5 : videoDuration" @input="updateVideoDuration" :aria-label="t('duration')" /></label>
          <details><summary>{{ t('advanced') }}</summary>
            <label class="check-label"><input type="checkbox" :checked="videoPromptExtend" @change="updateVideoPromptExtend" />{{ t('promptExtend') }}</label>
            <label class="check-label"><input type="checkbox" :checked="videoWatermark" @change="updateVideoWatermark" />{{ t('watermark') }}</label>
            <label class="check-label"><input type="checkbox" :checked="videoAudio" @change="emit('update:videoAudio', $event.target.checked)" />{{ t('audio') }}</label>
          </details>
          <p class="settings-hint">{{ t('autoModeDesc') }}</p>
        </template>
      </div>
      <div v-if="showAgentParams" class="settings-group">
        <label>{{ t('agentSettings') }}<select :value="agentTool" @change="updateAgentTool" :aria-label="t('agentSettings')"><option value="auto">🔮 {{ t('toolAuto') }}</option><option value="search">🌐 {{ t('toolSearch') }}</option><option value="web_extract">📄 {{ t('toolWebExtract') }}</option><option value="code">💻 {{ t('toolCode') }}</option><option value="search_image">🖼️ {{ t('toolSearchImage') }}</option><option value="image_search">🔎 {{ t('toolImageSearch') }}</option></select></label>
        <p class="settings-hint">{{ t('descAuto') }}</p><p class="settings-hint">{{ t('agentHint') }}</p>
      </div>
      <p class="settings-hint">{{ t('nextRequest') }}</p>
      <button type="button" class="reset-parameters" @click="emit('reset')">{{ t('reset') }}</button>
    </fieldset>
    <p v-if="saveError" class="settings-error" role="alert">{{ saveError }}</p>
  </section>
</template>

<script setup>
import { computed, inject } from 'vue'
import { IMAGE_SIZES, VIDEO_RATIOS } from '../utils/preferences.js'

const props = defineProps({
  modelValue: Number,
  disabled: Boolean,
  saveError: String,
  imageWatermark: Boolean,
  imagePromptExtend: { type: Boolean, default: true },
  imageNegativePrompt: { type: String, default: '' },
  videoAudio: { type: Boolean, default: true },
  streamMode: Boolean,
  thinkingMode: Boolean,
  imageMode: { type: String, default: 'vision' },
  enableSearch: { type: Boolean, default: false },
  studioSize: { type: String, default: '1024*1024' },
  studioCount: { type: Number, default: 1 },
  studioMode: { type: String, default: 'image' },
  videoResolution: { type: String, default: '1080P' },
  videoRatio: { type: String, default: '16:9' },
  videoDuration: { type: Number, default: 5 },
  videoWatermark: { type: Boolean, default: true },
  videoPromptExtend: { type: Boolean, default: true },
  showStudioParams: { type: Boolean, default: false },
  agentTool: { type: String, default: 'auto' },
  showAgentParams: { type: Boolean, default: false },
  // ========== 新增：控制隐藏各模块 ==========
  hideAiMode: { type: Boolean, default: false },
  hideSearchMode: { type: Boolean, default: false },
  hideImageMode: { type: Boolean, default: false }
  // =========================================
})

const emit = defineEmits([
  'update:modelValue', 'reset', 'update:imageWatermark', 'update:imagePromptExtend', 'update:imageNegativePrompt', 'update:videoAudio',
  'update:streamMode',
  'update:thinkingMode',
  'update:imageMode',
  'update:enableSearch',
  'update:studioSize',
  'update:studioCount',
  'update:studioMode',
  'update:videoResolution',
  'update:videoRatio',
  'update:videoDuration',
  'update:videoWatermark',
  'update:videoPromptExtend',
  'update:agentTool'
])

const currentLang = inject('currentLang', { value: 'zh-CN' })

const i18n = {
  'zh-CN': {
    interfaceSettings: '🛠 界面设置',
    responseMode: '回复方式', thinkingSetting: '思考模式', advanced: '高级参数', adaptive: '自适应',
    autoDuration: '智能时长', audio: '生成音频', reset: '恢复当前参数默认值',
    nextRequest: '参数用于下一次请求，生成中暂不可修改。',
    imageHint: '有图片附件时生效。视觉理解用于看图；OCR 只提取文字。',
    searchHint: '启用后允许模型按需搜索，并非每条消息都会联网。',
    agentHint: 'Agent 使用流式输出和工具思考模式，无需重复设置。',
    opacity: '背景不透明度',
    aiMode: '🛠 AI 输出模式',
    stream: '⚡ 流式输出',
    complete: '⏳ 完整回复',
    thinking: '🧠 深度思考',
    thinkingOff: '🧠 关闭思考',
    imageMode: '🖼️ 图片识别模式',
    modeAuto: '🔍 自动判断',
    modeOcr: '📄 文字提取（OCR）',
    modeVision: '👁️ 视觉理解（默认）',
    searchMode: '🔍 联网搜索',
    searchOff: '❌ 关闭',
    searchOn: '🌐 启用',
    studioMode: '创作模式',
    modeImage: '图像生成',
    modeVideo: '视频生成',
    sizeLabel: '尺寸',
    countLabel: '数量',
    countUnit: '张',
    resolution: '分辨率',
    ratio: '画面比例',
    duration: '时长',
    seconds: '秒',
    watermark: '添加水印',
    promptExtend: '自动扩写提示词',
    negativePrompt: '负向提示词',
    negativePromptPlaceholder: '输入不想出现的元素，如：模糊、低质量...',
    autoModeTip: '智能模式说明',
    autoModeDesc: '上传1张图→首帧视频 / 多张图→参考视频 / 视频→视频编辑 / 无文件→文生视频',
    agentSettings: '✦ 工具选择',
    toolAuto: '智能自动',
    toolSearch: '联网搜索',
    toolWebExtract: '网页抓取',
    toolCode: '代码解释器',
    toolSearchImage: '文搜图',
    toolImageSearch: '图搜图',
    descAuto: '根据你的输入自动选择搜索、网页提取、代码或搜图工具',
    descSearch: '搜索互联网实时信息',
    descWebExtract: '深度抓取网页内容',
    descCode: '执行代码、计算、绘图',
    descSearchImage: '用文字搜索互联网上的图片',
    descImageSearch: '上传图片搜索相似图片'
  },
  'en-US': {
    interfaceSettings: '🛠 Interface',
    responseMode: 'Response format', thinkingSetting: 'Reasoning', advanced: 'Advanced', adaptive: 'Adaptive',
    autoDuration: 'Automatic duration', audio: 'Generate audio', reset: 'Reset current parameters',
    nextRequest: 'Applies to the next request. Locked while generating.',
    imageHint: 'Applies to image attachments. Vision understands images; OCR extracts text.',
    searchHint: 'Allows the model to search when needed, rather than for every message.',
    agentHint: 'Agent uses streaming and tool reasoning; no duplicate controls are needed.',
    opacity: 'Background opacity',
    aiMode: '🛠 AI Output Mode',
    stream: '⚡ Streaming',
    complete: '⏳ Complete',
    thinking: '🧠 Deep Think',
    thinkingOff: '🧠 Off',
    imageMode: '🖼️ Image Mode',
    modeAuto: '🔍 Auto',
    modeOcr: '📄 Text OCR',
    modeVision: '👁️ Vision',
    searchMode: '🔍 Web Search',
    searchOff: '❌ Off',
    searchOn: '🌐 On',
    studioMode: 'Creation Mode',
    modeImage: 'Image Gen',
    modeVideo: 'Video Gen',
    sizeLabel: 'Size',
    countLabel: 'Count',
    countUnit: ' images',
    resolution: 'Resolution',
    ratio: 'Aspect Ratio',
    duration: 'Duration',
    seconds: 'seconds',
    watermark: 'Add Watermark',
    promptExtend: 'Auto-extend prompt',
    negativePrompt: 'Negative prompt',
    negativePromptPlaceholder: 'Elements to avoid, e.g. blurry, low quality...',
    autoModeTip: 'Smart Mode',
    autoModeDesc: '1 image→I2V / multiple→R2V / video→Edit / none→T2V',
    agentSettings: '✦ Tool Selection',
    toolAuto: 'Auto',
    toolSearch: 'Web Search',
    toolWebExtract: 'Web Extract',
    toolCode: 'Code Interpreter',
    toolSearchImage: 'Text-to-Image Search',
    toolImageSearch: 'Image-to-Image Search',
    descAuto: 'Auto-select best tool based on input',
    descSearch: 'Search internet for real-time info',
    descWebExtract: 'Deep extract web page content',
    descCode: 'Execute code, calculations, plotting',
    descSearchImage: 'Search images on the internet by text',
    descImageSearch: 'Search similar images by uploaded image'
  }
}

const t = (key) => i18n[currentLang.value]?.[key] || i18n['zh-CN'][key]

const updateAlpha = (e) => {
  emit('update:modelValue', Number(e.target.value) / 100)
}

const localStream = computed({
  get: () => props.streamMode,
  set: (v) => emit('update:streamMode', v)
})

const localThink = computed({
  get: () => props.thinkingMode,
  set: (v) => emit('update:thinkingMode', v)
})

const localImageMode = computed({
  get: () => props.imageMode,
  set: (v) => emit('update:imageMode', v)
})

const localSearch = computed({
  get: () => props.enableSearch,
  set: (v) => emit('update:enableSearch', v)
})

const updateStudioSize = (e) => { emit('update:studioSize', e.target.value) }
const updateStudioCount = (e) => { emit('update:studioCount', Number(e.target.value)) }
const updateStudioMode = (e) => { emit('update:studioMode', e.target.value) }
const updateVideoResolution = (e) => { emit('update:videoResolution', e.target.value) }
const updateVideoRatio = (e) => { emit('update:videoRatio', e.target.value) }
const updateVideoDuration = (e) => { emit('update:videoDuration', Number(e.target.value)) }
const updateVideoWatermark = (e) => { emit('update:videoWatermark', e.target.checked) }
const updateVideoPromptExtend = (e) => { emit('update:videoPromptExtend', e.target.checked) }
const updateAgentTool = (e) => { emit('update:agentTool', e.target.value) }
</script>
<style scoped>
fieldset { border: 0; padding: 0; margin: 0; min-width: 0; }fieldset:disabled { opacity: .6; }
.settings-group { margin-top: 20px; }.settings-panel output { float: right; font-size: 12px; color: #cbb9e7; }
.settings-hint { color: #b0a8c1; font-size: 11px; line-height: 1.6; margin: 8px 0; }
.settings-panel details { margin-top: 16px; border-top: 1px solid #ffffff18; padding-top: 10px; }
.settings-panel summary { cursor: pointer; font-size: 13px; color: #d0c0eb; }
.settings-panel .check-label { display: flex; align-items: center; gap: 8px; font-size: 12px; }
.settings-panel textarea { width: 100%; resize: vertical; min-height: 64px; border: 1px solid #ffffff30; background: #15112688; color: white; border-radius: 7px; padding: 8px; font: inherit; font-size: 12px; }
.reset-parameters { width: 100%; padding: 8px; border: 1px solid #c3a6ed40; border-radius: 7px; background: #bda2e80b; color: #d5c5eb; cursor: pointer; font-size: 12px; }
.settings-error { font-size: 11px; color: #ffd0b2; line-height: 1.6; }
</style>
