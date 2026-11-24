<template>
  <div class="avatar-picker">
    <img :src="modelValue || fallback" :alt="label" class="avatar-sample" :style="{borderRadius:shape === 'circle' ? '50%' : '14px'}" />
    <label>{{ label }}<input type="file" accept="image/png,image/jpeg,image/webp,image/gif" @change="choose" :disabled="busy" /></label>
    <button type="button" :disabled="busy" @click="$emit('update:modelValue', '')">恢复默认</button>
    <div v-if="source && !animated" class="crop-panel">
      <canvas ref="canvas" width="512" height="512" style="width:180px;height:180px;border:1px solid #806896" />
      <label>缩放<input type="range" min="1" max="3" step=".01" v-model.number="zoom" @input="draw" /></label>
      <label>左右<input type="range" min="-128" max="128" v-model.number="offsetX" @input="draw" /></label>
      <label>上下<input type="range" min="-128" max="128" v-model.number="offsetY" @input="draw" /></label>
      <button type="button" @click="uploadCrop" :disabled="busy">使用裁剪结果</button><button type="button" @click="clear">取消</button>
    </div>
    <p v-if="error" role="alert">{{ error }}</p>
  </div>
</template>
<script setup>
import { nextTick, onBeforeUnmount, ref } from 'vue'
import { settingsRequest } from '../composables/useApplicationSettings.js'
defineProps({ modelValue: String, fallback: String, label: String, shape: String })
const emit = defineEmits(['update:modelValue', 'busy-change'])
const source = ref(''), canvas = ref(null), animated = ref(false), zoom = ref(1), offsetX = ref(0), offsetY = ref(0), busy = ref(false), error = ref('')
let image
function clear() { if (source.value) URL.revokeObjectURL(source.value); source.value = ''; image = null }
onBeforeUnmount(clear)
async function upload(file) {
  busy.value = true
  emit('busy-change', true)
  try { const form = new FormData(); form.append('file', file); const result = await settingsRequest('/asset?kind=avatar', { method: 'POST', body: form }); emit('update:modelValue', result.url); clear() }
  catch (e) { error.value = e.message } finally { busy.value = false; emit('busy-change', false) }
}
async function choose(event) {
  const file = event.target.files?.[0]; event.target.value = ''; if (!file) return
  clear(); error.value = ''
  if (file.size > 10 * 1024 * 1024) { error.value = '头像不能超过 10 MB'; return }
  animated.value = file.type === 'image/gif' || file.type === 'image/webp' && new TextDecoder('latin1').decode(await file.arrayBuffer()).includes('ANIM')
  if (animated.value) { await upload(file); return }
  source.value = URL.createObjectURL(file); zoom.value = 1; offsetX.value = 0; offsetY.value = 0
  image = new Image(); image.onload = async () => { await nextTick(); draw() }; image.onerror = () => { error.value = '无法读取图片'; clear() }; image.src = source.value
}
function draw() { if (!canvas.value || !image) return; const ctx = canvas.value.getContext('2d'); ctx.clearRect(0,0,512,512); const scale = Math.max(512/image.width,512/image.height)*zoom.value; ctx.drawImage(image,(512-image.width*scale)/2+offsetX.value*2,(512-image.height*scale)/2+offsetY.value*2,image.width*scale,image.height*scale) }
function uploadCrop() { canvas.value.toBlob(blob => { if (blob) upload(new File([blob], 'avatar.png', {type:'image/png'})) }, 'image/png') }
</script>
<style scoped>
.avatar-picker{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:14px 0}.avatar-sample{width:64px;height:64px;object-fit:cover}.crop-panel{width:100%;display:grid;gap:8px}.avatar-picker p{color:#ffb6bd}
</style>
