<template>
  <div class="model-switcher">
    <template v-if="route">
      <span>{{ label }}</span>
      <select v-model="connection" :disabled="disabled || saving" aria-label="当前功能连接" @change="changeConnection">
        <option v-for="item in connections" :key="item.id" :value="item.id">{{ item.name }}</option>
      </select>
      <input v-model="model" :list="listId" :disabled="disabled || saving" aria-label="当前功能模型" @input="application.pendingRoutes[module]=true" @change="commit" placeholder="模型名称" />
      <datalist :id="listId"><option v-for="item in application.models[connection] || []" :key="item.id" :value="item.id" /></datalist>
      <button :disabled="disabled || saving" @click="refresh">刷新模型</button>
      <button v-if="application.pendingRoutes[module]" @click="cancel">取消切换</button>
    </template>
    <button @click="$emit('settings')">{{ route ? '详细设置' : '配置连接与模型' }}</button>
    <span v-if="error" class="error" role="alert">{{ error }}</span>
  </div>
</template>
<script setup>
import { computed, ref, watch } from 'vue'
import { application, routeFor, saveApplicationSettings, refreshModels } from '../composables/useApplicationSettings.js'
const props = defineProps({ module: { type: String, default: 'chat' }, disabled: Boolean })
defineEmits(['settings'])
const route = computed(() => routeFor(props.module))
const labels = { chat: '聊天', vision: '图片理解', document: '文档回答', embedding: '文档检索', agent: 'Agent', image: '生图', video: '视频', search_image: '文字搜图', image_search: '以图搜图' }
const label = computed(() => labels[props.module])
const connections = computed(() => (application.config?.connections || []).filter(c => !['agent','image','video','search_image','image_search'].includes(props.module) || c.provider === 'dashscope'))
const connection = ref(''), model = ref(''), error = ref(''), saving = ref(false)
const listId = computed(() => 'quick-models-' + props.module)
watch(route, value => { if (value) { connection.value = value.connection; model.value = value.model; application.pendingRoutes[props.module] = false } }, { immediate: true, deep: true })
async function commit() {
  if (!route.value || !model.value.trim() || props.disabled) return
  error.value = ''; saving.value = true
  try {
    const target = application.config.connections.find(c => c.id === connection.value)
    const previous = application.config.connections.find(c => c.id === route.value.connection)
    if (previous?.provider === 'ollama' && target?.provider !== 'ollama' && !window.confirm('切换到云端后，后续请求会发送当前对话及相关附件。是否继续？')) { cancel(); return }
    const candidate = JSON.parse(JSON.stringify(application.config))
    candidate.modules[props.module] = { connection: connection.value, model: model.value.trim() }
    await saveApplicationSettings(candidate)
    application.pendingRoutes[props.module] = false
  } catch (e) { error.value = e.message } finally { saving.value = false }
}
function cancel() { connection.value=route.value.connection;model.value=route.value.model;application.pendingRoutes[props.module]=false;error.value='' }
function changeConnection() { model.value = ''; application.pendingRoutes[props.module]=true; error.value = '请选择或输入模型；保存成功前暂不能发送。'; refresh() }
async function refresh() { try { await refreshModels(connection.value); error.value = '' } catch (e) { error.value = e.message } }
</script>
<style scoped>
.model-switcher{display:flex;align-items:center;gap:8px;flex-wrap:wrap;color:#ddcff3;font-size:13px}.model-switcher input,.model-switcher select,.model-switcher button{background:#1b1530;color:inherit;border:1px solid #655080;border-radius:10px;padding:7px;max-width:240px}.error{color:#ffb6bd}.model-switcher button{cursor:pointer}
</style>
