<template>
  <div class="custom-background" :style="surfaceStyle">
    <video v-if="videoSource" ref="videoRef" :src="videoSource" muted loop playsinline preload="auto" :style="mediaStyle" @loadeddata="resume();emit('ready',true)" @error="mediaError" />
    <img v-else-if="imageSource" :src="imageSource" alt="" :style="mediaStyle" @load="emit('ready',true)" @error="mediaError" />
    <div class="background-shade" :style="{background:`rgba(0,0,0,${appearance.background_dim})`}" />
    <p v-if="error" class="background-error" role="status">{{error}}</p>
  </div>
</template>
<script setup>
import { computed, inject, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { defaultAppearance } from '../composables/useApplicationSettings.js'
const appearance=inject('appAppearance',ref(defaultAppearance))
const props=defineProps({paused:Boolean})
const emit=defineEmits(['ready'])
const videoRef=ref(null),error=ref('')
const videoSource=computed(()=>appearance.value.background_mode==='default'?'/media/Castorice.mp4':appearance.value.background_mode==='video'?appearance.value.background_asset:'')
const imageSource=computed(()=>appearance.value.background_mode==='image'?appearance.value.background_asset:'')
const surfaceStyle=computed(()=>({background:appearance.value.background_mode==='gradient'?`linear-gradient(135deg,${appearance.value.background_color},#080512)`:appearance.value.background_color}))
const mediaStyle=computed(()=>({objectFit:appearance.value.background_fit,filter:`blur(${appearance.value.background_blur}px)`}))
function resume(){if(!videoRef.value)return;if(props.paused||appearance.value.reduce_motion||(appearance.value.pause_hidden&&document.hidden))videoRef.value.pause();else videoRef.value.play().catch(()=>{})}
function mediaError(){error.value='背景文件无法播放或读取，请在应用设置中更换文件或恢复默认。';emit('ready',true)}
watch(()=>[appearance.value.background_asset,appearance.value.background_mode],async()=>{error.value='';emit('ready',!['default','video','image'].includes(appearance.value.background_mode));await nextTick();resume()})
watch(()=>[appearance.value.pause_hidden,appearance.value.reduce_motion],resume)
watch(()=>props.paused,resume)
onMounted(()=>{document.addEventListener('visibilitychange',resume);resume()})
onBeforeUnmount(()=>document.removeEventListener('visibilitychange',resume))
defineExpose({videoRef})
</script>
<style scoped>
.custom-background{position:fixed;inset:0;z-index:-1;pointer-events:none;overflow:hidden}.custom-background video,.custom-background img,.background-shade{position:absolute;inset:0;width:100%;height:100%}.background-error{position:fixed;bottom:4px;left:12px;color:#ffbdc7;background:#100c1dcc;border-radius:8px;padding:6px;max-width:70vw;font-size:12px}
</style>
