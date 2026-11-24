<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="visible" class="img-preview-overlay" @click="close">
        <div class="img-preview-box" @click.stop>
          <img :src="currentSrc" alt="preview" />
          <button class="img-preview-close" @click="close">✕</button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'
const visible = ref(false)
const currentSrc = ref('')

const open = (src) => {
  currentSrc.value = src
  visible.value = true
  document.body.style.overflow = 'hidden'
}
const close = () => {
  visible.value = false
  document.body.style.overflow = ''
}
defineExpose({ open })
</script>

<style scoped>
.img-preview-overlay {
  position: fixed; inset: 0;
  background: rgba(0, 0, 0, 0.88);
  backdrop-filter: blur(10px);
  z-index: 100000;
  display: flex; align-items: center; justify-content: center;
  cursor: zoom-out;
}
.img-preview-box {
  position: relative;
  max-width: 92vw; max-height: 92vh;
  border-radius: 12px; overflow: hidden;
  box-shadow: 0 0 50px rgba(0,0,0,0.6);
  border: 1px solid rgba(255,255,255,0.15);
}
.img-preview-box img {
  max-width: 92vw; max-height: 92vh;
  object-fit: contain; display: block;
}
.img-preview-close {
  position: absolute; top: 10px; right: 10px;
  width: 34px; height: 34px; border-radius: 50%;
  background: rgba(0,0,0,0.55);
  border: 1px solid rgba(255,255,255,0.3);
  color: white; font-size: 1.1rem; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.2s;
}
.img-preview-close:hover {
  background: rgba(255,80,80,0.8);
  border-color: rgba(255,120,120,0.6);
}
.fade-enter-active, .fade-leave-active { transition: opacity 0.25s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>