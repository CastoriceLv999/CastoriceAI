<template>
  <div class="music-player-wrapper">
    <audio
      ref="audioRef"
      preload="auto"
      loop
      src="/media/Castorice.mp3"
      @play="isPlaying = true"
      @pause="isPlaying = false"
      @ended="isPlaying = false"
    ></audio>
    <button
      id="st-music-btn"
      :class="{ playing: isPlaying }"
      @click.stop="toggle"
      :title="isPlaying ? '点击暂停' : '点击播放'"
    >
      {{ isPlaying ? '♪' : '♫' }}
    </button>
  </div>
</template>

<script setup>
import { ref, inject, watch } from 'vue'

const audioRef = ref(null)
const isPlaying = ref(false)
const appearance = inject('appAppearance', ref({music_enabled:true,music_volume:.45}))
watch(() => appearance.value.music_volume, value => {if(audioRef.value)audioRef.value.volume=value})
watch(() => appearance.value.music_enabled, value => {if(!value)audioRef.value?.pause()})

const toggle = () => {
  const audio = audioRef.value
  if (!audio) return
  if (!appearance.value.music_enabled) return
  // 以 audio.paused 作为最终权威判断，彻底杜绝状态失步
  if (!audio.paused) {
    audio.pause()
  } else {
    tryPlay()
  }
}

const tryPlay = () => {
  const audio = audioRef.value
  if (!audio) return
  if (!appearance.value.music_enabled) return
  audio.volume = appearance.value.music_volume
  audio.play()
    .catch(err => {
      console.log('[Audio] 播放失败:', err.name)
      isPlaying.value = false
    })
}

defineExpose({ tryPlay, audioRef })
</script>

<style scoped>
.music-player-wrapper {
  /* 不干扰布局，保持原有定位效果 */
  display: contents;
}

#st-music-btn {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.35);
  color: white;
  font-size: 22px;
  cursor: pointer;
  z-index: 99999;
  pointer-events: auto;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  text-shadow: 0 1px 4px rgba(0,0,0,0.9);
}

#st-music-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: scale(1.12);
  border-color: rgba(255, 255, 255, 0.5);
}

#st-music-btn.playing {
  animation: stMusicPulse 2.4s ease-in-out infinite;
  background: rgba(40, 180, 120, 0.35);
  border-color: rgba(100, 255, 180, 0.6);
}

@keyframes stMusicPulse {
  0%, 100% { box-shadow: 0 0 8px rgba(255,255,255,0.2); }
  50% { box-shadow: 0 0 24px rgba(255,255,255,0.5), 0 0 10px rgba(140,220,255,0.4); }
}
</style>
