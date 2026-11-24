<template>
<div id="castorice-title-container">
  <div class="logo-wrapper">
    <div class="orbit-layer layer-1">
      <div v-for="n in 4" :key="n" class="orbit-particle" :style="orbitStyle(n, 1)"></div>
    </div>
    <div class="orbit-layer layer-2">
      <div v-for="n in 5" :key="n" class="orbit-particle" :style="orbitStyle(n, 2)"></div>
    </div>
    <div class="orbit-layer layer-3">
      <div v-for="n in 3" :key="n" class="orbit-particle" :style="orbitStyle(n, 3)"></div>
    </div>
    <div class="stardust">
      <span v-for="n in 12" :key="n" class="dust" :style="dustStyle(n)"></span>
    </div>
    <div class="ring ring-outer"></div>
    <div class="ring ring-inner"></div>
    <img src="/images/castorice_logo1.png" alt="Castorice Logo" class="castorice-logo" @load="onLogoLoad" />
    <div class="center-glow"></div>
  </div>
  <div class="castorice-title">{{ displayTitle }}</div>
  <div class="castorice-subtitle">{{ displaySubtitle }}</div>
</div>
</template>

<script setup>
import { inject, computed, ref } from 'vue'

const props = defineProps({
  subtitle: { type: String, default: '' },
  pageType: { type: String, default: 'ai' }
})

const currentLang = inject('currentLang')
const logoLoaded = ref(false)

const displayTitle = computed(() => {
  const base = 'Castorice'
  const suffixMap = { studio: 'Studio', agent: 'Agent' }
  return `${base} ${suffixMap[props.pageType] || 'AI'}`
})


const displaySubtitle = computed(() => {
  if (props.subtitle) return props.subtitle
  const lang = currentLang?.value || 'zh-CN'

  if (props.pageType === 'studio') {
    return lang === 'en-US'
      ? 'Create your own memories------2026.06.01 | Where imagination blooms'
      : '创造属于你的回忆------2026.06.01 | 想象绽放之地'
  }

  if (props.pageType === 'agent') {
    return lang === 'en-US'
      ? 'Tools & Reasoning------2026.06.01 | Where capabilities converge'
      : '工具与推理------2026.06.01 | 能力汇聚之地'
  }

  return lang === 'en-US'
    ? 'Our Encounter------2025.4.9 | Embark on a journey with you------2026.05.26'
    : '与你的相遇------2025.4.9 | 与你启航------2026.05.26'
})


const onLogoLoad = () => { logoLoaded.value = true }

const orbitStyle = (n, layer) => {
  const configs = {
    1: { count: 4, radius: 55, duration: 4, size: 5, color: '140, 220, 255' },
    2: { count: 5, radius: 70, duration: 6, size: 4, color: '220, 160, 255' },
    3: { count: 3, radius: 45, duration: 5, size: 6, color: '100, 200, 255' }
  }
  const config = configs[layer]
  const angle = ((n - 1) / config.count) * 360
  const delay = (n - 1) * (config.duration / config.count)
  return {
    width: `${config.size}px`,
    height: `${config.size}px`,
    animationDuration: `${config.duration}s`,
    animationDelay: `${delay}s`,
    '--orbit-radius': `${config.radius * 0.8}px`,
    '--orbit-angle': `${angle}deg`,
    '--particle-color': config.color
  }
}

const dustStyle = (n) => {
  const angle = Math.random() * 360
  const distance = 40 + Math.random() * 50
  const delay = Math.random() * 4
  const duration = 2 + Math.random() * 3
  const size = 2 + Math.random() * 3
  return {
    width: `${size}px`,
    height: `${size}px`,
    top: '50%',
    left: '50%',
    transform: `rotate(${angle}deg) translateX(${distance}px)`,
    animationDuration: `${duration}s`,
    animationDelay: `${delay}s`
  }
}
</script>

<style scoped>
#castorice-title-container {
  width: 100%;
  text-align: center;
  margin-top: 60px;
  margin-bottom: 10px;
  position: relative;
  z-index: 1;
}

/* ===== 星空 Logo 区域 ===== */
.logo-wrapper {
  position: relative;
  display: inline-block;
  margin-bottom: 0px;
  width: 160px;
  height: 160px;
}

/* 轨道层 */
.orbit-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

/* 轨道粒子 */
.orbit-particle {
  position: absolute;
  top: 50%;
  left: 50%;
  border-radius: 50%;
  margin-top: calc(var(--size, 6px) / -2);
  margin-left: calc(var(--size, 6px) / -2);
  background: radial-gradient(
    circle at 30% 30%,
    rgba(255, 255, 255, 1) 0%,
    rgba(var(--particle-color, 140, 220, 255), 0.9) 30%,
    rgba(var(--particle-color, 140, 220, 255), 0.4) 60%,
    transparent 100%
  );
  box-shadow:
    0 0 10px rgba(var(--particle-color, 140, 220, 255), 0.8),
    0 0 20px rgba(var(--particle-color, 140, 220, 255), 0.4),
    0 0 40px rgba(var(--particle-color, 140, 220, 255), 0.2);
  animation: orbit var(--orbit-duration, 4s) linear infinite;
  animation-delay: var(--orbit-delay, 0s);
}

/* 粒子轨道动画 */
@keyframes orbit {
  0% {
    transform: rotate(var(--orbit-angle, 0deg)) translateX(var(--orbit-radius, 55px)) rotate(calc(-1 * var(--orbit-angle, 0deg)));
    opacity: 0.8;
    scale: 1;
  }
  25% {
    opacity: 1;
    scale: 1.3;
  }
  50% {
    opacity: 0.6;
    scale: 0.8;
  }
  75% {
    opacity: 1;
    scale: 1.2;
  }
  100% {
    transform: rotate(calc(var(--orbit-angle, 0deg) + 360deg)) translateX(var(--orbit-radius, 55px)) rotate(calc(-1 * var(--orbit-angle, 0deg) - 360deg));
    opacity: 0.8;
    scale: 1;
  }
}

/* 星尘效果 */
.stardust {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.dust {
  position: absolute;
  border-radius: 50%;
  background: radial-gradient(
    circle,
    rgba(255, 255, 255, 0.9) 0%,
    rgba(140, 220, 255, 0.6) 40%,
    transparent 70%
  );
  box-shadow: 0 0 6px rgba(140, 220, 255, 0.6);
  animation: stardustFloat linear infinite;
  margin-top: -1.5px;
  margin-left: -1.5px;
}

@keyframes stardustFloat {
  0% {
    opacity: 0;
    transform: rotate(var(--dust-angle, 0deg)) translateX(var(--dust-radius, 60px)) scale(0.5);
  }
  20% {
    opacity: 1;
    transform: rotate(var(--dust-angle, 0deg)) translateX(var(--dust-radius, 60px)) scale(1);
  }
  80% {
    opacity: 1;
    transform: rotate(var(--dust-angle, 0deg)) translateX(var(--dust-radius, 60px)) scale(0.8);
  }
  100% {
    opacity: 0;
    transform: rotate(var(--dust-angle, 0deg)) translateX(var(--dust-radius, 60px)) scale(0.3);
  }
}

/* 光环 */
.ring {
  position: absolute;
  top: 50%;
  left: 50%;
  border-radius: 50%;
  border: 1px solid transparent;
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.ring-outer {
  width: 140px;
  height: 140px;
  border-color: rgba(140, 220, 255, 0.15);
  animation: ringPulse 4s ease-in-out infinite;
}

.ring-inner {
  width: 140px;
  height: 140px;
  border-color: rgba(220, 160, 255, 0.2);
  animation: ringPulse 3s ease-in-out infinite reverse;
}

@keyframes ringPulse {
  0%, 100% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 0.5;
    border-width: 1px;
  }
  50% {
    transform: translate(-50%, -50%) scale(1.1);
    opacity: 0.8;
    border-width: 2px;
  }
}

/* Logo 主体 */
.castorice-logo {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  object-fit: cover;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 2;
  border: 2px solid rgba(140, 220, 255, 0.4);
  box-shadow:
    0 0 20px rgba(140, 220, 255, 0.3),
    0 0 40px rgba(220, 160, 255, 0.2),
    inset 0 0 20px rgba(140, 220, 255, 0.1);
  animation: logoBreath 3s ease-in-out infinite;
  transition: all 0.5s ease;
}

.castorice-logo:hover {
  transform: translate(-50%, -50%) scale(1.15);
  box-shadow:
    0 0 30px rgba(140, 220, 255, 0.5),
    0 0 60px rgba(220, 160, 255, 0.3),
    inset 0 0 30px rgba(140, 220, 255, 0.2);
}

/* 中心光晕 */
.center-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  background: radial-gradient(
    circle,
    rgba(140, 220, 255, 0.3) 0%,
    rgba(220, 160, 255, 0.15) 40%,
    transparent 70%
  );
  animation: centerGlow 4s ease-in-out infinite;
  pointer-events: none;
  z-index: 1;
}

@keyframes logoBreath {
  0%, 100% {
    transform: translate(-50%, -50%) scale(1);
    box-shadow:
      0 0 20px rgba(140, 220, 255, 0.3),
      0 0 40px rgba(220, 160, 255, 0.2);
  }
  50% {
    transform: translate(-50%, -50%) scale(1.03);
    box-shadow:
      0 0 30px rgba(140, 220, 255, 0.4),
      0 0 50px rgba(220, 160, 255, 0.3);
  }
}

@keyframes centerGlow {
  0%, 100% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 0.6;
  }
  50% {
    transform: translate(-50%, -50%) scale(1.3);
    opacity: 0.3;
  }
}

/* ===== 标题 ===== */
.castorice-title {
  font-family: 'Pacifico', cursive, sans-serif;
  font-size: 80px;
  font-weight: 400;
  color: #e0f7ff;
  text-align: center;
  text-shadow:
    0 0 18px rgba(100, 200, 255, 1),
    0 0 6px rgba(0, 120, 255, 0.9);
  letter-spacing: 2px;
  margin: 0;
  line-height: 1.2;
  animation: titleShimmer 4s ease-in-out infinite;
}

@keyframes titleShimmer {
  0%, 100% {
    text-shadow: 0 0 18px rgba(100, 200, 255, 1), 0 0 6px rgba(0, 120, 255, 0.9);
  }
  50% {
    text-shadow: 0 0 30px rgba(100, 200, 255, 1), 0 0 10px rgba(0, 120, 255, 1), 0 0 60px rgba(140, 220, 255, 0.5);
  }
}

.castorice-subtitle {
  font-family: 'ZCOOL QingKe HuangYou', "PingFang SC", "Microsoft YaHei", sans-serif;
  font-size: 22px;
  color: #e0f7ff;
  text-align: center;
  text-shadow: 0 0 8px rgba(80, 180, 255, 0.7);
  letter-spacing: 3px;
  margin-top: 10px;
  animation: subtitleFade 3s ease-in-out infinite alternate;
}

@keyframes subtitleFade {
  0% { opacity: 0.8; }
  100% { opacity: 1; }
}

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  #castorice-title-container {
    margin-top: 40px;
  }
  .logo-wrapper {
    width: 160px;
    height: 160px;
  }
  .castorice-logo {
    width: 75px;
    height: 75px;
  }
  .ring-outer {
    width: 130px;
    height: 130px;
  }
  .ring-inner {
    width: 100px;
    height: 100px;
  }
  .center-glow {
    width: 70px;
    height: 70px;
  }
  .castorice-title { font-size: 48px; }
  .castorice-subtitle { font-size: 18px; }
}
</style>