<template>
  <div v-if="active" class="startup-experience" :class="{transitioning:phase==='transition',reduced:appearance.reduce_motion}" :data-progress="frame.progress.toFixed(3)" :style="{'--intro-opacity':frame.introOpacity}" role="region" aria-label="启动画面">
    <video ref="intro" class="intro-video" src="/media/启动动画.mp4" autoplay muted playsinline preload="auto" @loadeddata="introReady=true" @ended="ended=true" @error="videoError=true" />
    <canvas ref="canvas" class="transition-canvas" aria-hidden="true" />
    <div v-if="phase==='waiting'" class="startup-controls">
      <p v-if="videoError" role="status">启动视频无法播放，可以直接进入应用。</p>
      <p v-else-if="application.error" role="status">{{application.error}}</p>
      <button v-if="ready" ref="enterButton" class="enter-button" @click="begin" aria-label="点击进入 Castorice">点击进入 <span>✦</span></button>
      <p v-else class="loading-status" role="status">{{loadingText}}<span class="loading-dots">…</span></p>
      <p class="startup-hint">{{ready?'界面已就绪 · 点击继续，或按 Enter':'正在准备后台配置与背景画面'}}</p>
      <button v-if="application.error" class="retry-button" @click="retry">重新连接</button>
    </div>
    <button v-if="phase==='waiting'" class="skip-button" @click="skip">跳过动画</button>
    <button v-if="phase==='waiting'" class="sound-button" @click="toggleSound" :aria-label="sound?'关闭启动音效':'打开启动音效'">{{sound?'音效 开':'音效 关'}}</button>
    <button v-if="ready && phase==='waiting'" class="enter-hit-area" tabindex="-1" aria-hidden="true" @click="begin" />
  </div>
</template>
<script setup>
import { computed, inject, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { application, defaultAppearance, loadApplicationSettings } from '../composables/useApplicationSettings.js'
import { startupFrame } from '../utils/startupTransition.js'
import { paintFluidTransition } from '../utils/startupFluid.js'
const props=defineProps({backgroundReady:Boolean})
const emit=defineEmits(['reveal','finished','handoff'])
const appearance=inject('appAppearance',ref(defaultAppearance))
const active=ref(true),phase=ref('waiting'),intro=ref(null),canvas=ref(null),enterButton=ref(null),introReady=ref(false),videoError=ref(false),ended=ref(false),sound=ref(false),fontsReady=ref(false)
const frame=ref(startupFrame(0)),elapsedWait=ref(0)
const ready=computed(()=>application.loaded&&props.backgroundReady&&fontsReady.value&&(introReady.value||videoError.value))
const loadingText=computed(()=>!application.loaded?'正在连接本地后台':!props.backgroundReady?'正在准备背景视频':!introReady.value&&!videoError.value?'正在读取启动视频':'正在准备界面')
let requestId=0,startTime=0,context,width=0,height=0,density=1,retryTimer,waitTimer,loading=false,disposed=false,handedOff=false
function resize(){
  width=window.innerWidth;height=window.innerHeight;density=Math.min(window.devicePixelRatio||1,1.5)
  if(canvas.value){canvas.value.width=Math.round(width*density);canvas.value.height=Math.round(height*density);context=canvas.value.getContext('2d');context?.setTransform(density,0,0,density,0,0)}
}
function draw(time){
  const elapsed=time-startTime;frame.value=startupFrame(elapsed,appearance.value.reduce_motion)
  if(intro.value&&sound.value)intro.value.volume=Math.max(0,1-frame.value.progress/.7)
  const {progress,cover,interfaceOpacity}=frame.value
  if(progress>=.43&&!handedOff){handedOff=true;emit('handoff')}
  emit('reveal',interfaceOpacity)
  if(context){
    context.clearRect(0,0,width,height)
    if(appearance.value.reduce_motion){context.globalAlpha=cover;context.fillStyle='#40274f';context.fillRect(0,0,width,height);context.globalAlpha=1}
    else paintFluidTransition(context,progress,width,height,time)
    context.globalAlpha=1
  }
  if(frame.value.done){finish();return}
  requestId=requestAnimationFrame(draw)
}
function begin(){
  if(!ready.value||phase.value!=='waiting')return
  phase.value='transition'
  // Do not seek or restart: the video keeps its exact playback position at click time.
  if(!ended.value)intro.value?.play().catch(()=>{})
  resize();startTime=performance.now();requestId=requestAnimationFrame(draw)
}
function finish(){cancelAnimationFrame(requestId);intro.value?.pause();active.value=false;phase.value='finished';emit('reveal',1);emit('finished')}
function skip(){if(phase.value==='transition')return;finish()}
function toggleSound(){sound.value=!sound.value;if(intro.value){intro.value.muted=!sound.value;intro.value.volume=1;intro.value.play().catch(()=>{})}}
function key(event){if(!active.value)return;if(event.key==='Escape'){event.preventDefault();skip()}else if((event.key==='Enter'||event.key===' ')&&ready.value&&phase.value==='waiting'&&event.target===document.body){event.preventDefault();begin()}}
async function retry(){if(loading||disposed)return;loading=true;try{await loadApplicationSettings()}finally{loading=false}}
watch(ready,async value=>{if(value){await nextTick();if(phase.value==='waiting')enterButton.value?.focus()}})
onMounted(()=>{
  resize();window.addEventListener('resize',resize);window.addEventListener('keydown',key)
  document.fonts.ready.then(()=>{if(!disposed)fontsReady.value=true});setTimeout(()=>{if(!disposed)fontsReady.value=true},8000)
  intro.value?.play().catch(()=>{})
  retryTimer=setInterval(()=>{if(!application.loaded&&elapsedWait.value<60)retry()},1500)
  waitTimer=setInterval(()=>{elapsedWait.value++},1000)
})
onBeforeUnmount(()=>{disposed=true;cancelAnimationFrame(requestId);clearInterval(retryTimer);clearInterval(waitTimer);window.removeEventListener('resize',resize);window.removeEventListener('keydown',key);intro.value?.pause()})
</script>
<style scoped>
.startup-experience{position:fixed;inset:0;z-index:180000;background:#080610;overflow:hidden}.startup-experience.transitioning{background:transparent}.intro-video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:var(--intro-opacity,1)}.transition-canvas{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:2}.startup-controls{position:absolute;bottom:9%;left:5%;right:5%;text-align:center;z-index:5;color:#fff;text-shadow:0 2px 10px #160721}.enter-button{background:transparent;border:0;color:#fff;font:500 clamp(20px,3vw,30px)/1.6 system-ui;letter-spacing:.3em;padding:14px 30px;cursor:pointer;animation:invite 2s ease-in-out infinite;text-shadow:0 0 18px #b67be2}.enter-button span{display:inline-block;color:#e7b6ff;font-size:18px}.startup-hint{font-size:12px;letter-spacing:.12em;color:#e1d4ed;margin-top:4px}.loading-status{font-size:16px;letter-spacing:.15em}.skip-button,.sound-button,.retry-button{position:absolute;z-index:6;color:#f0dfff;background:#170c3099;border:1px solid #d7afff55;border-radius:20px;padding:8px 14px;cursor:pointer;font:12px system-ui}.skip-button{right:24px;top:24px}.sound-button{left:24px;top:24px}.retry-button{position:relative;margin-top:10px}.enter-hit-area{position:absolute;inset:0;background:transparent;border:0;cursor:pointer;z-index:3}.startup-controls{pointer-events:none}.startup-controls button{pointer-events:auto}@keyframes invite{50%{opacity:.55}}@media(prefers-reduced-motion:reduce){.enter-button{animation:none}}.startup-experience.reduced .enter-button{animation:none}.startup-experience :focus-visible{outline:2px solid #e1b7ff;outline-offset:5px}
</style>
