<template>
  <div id="floating-clock-card">
    <div class="fclock-time">
      {{ h }}<span class="fclock-colon">:</span>{{ m }}<span class="fclock-colon">:</span>{{ s }}
    </div>
    <div class="fclock-meta">
      <span>{{ dateStr }}</span>
      <span class="fclock-divider">|</span>
      <span>{{ weekStr }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, inject, computed, watch } from 'vue'

const currentLang = inject('currentLang', { value: 'zh-CN' })

const h = ref('--'), m = ref('--'), s = ref('--')
const dateStr = ref('---年--月--日'), weekStr = ref('--')

let timer = null

const locale = computed(() => currentLang.value === 'en-US' ? 'en-US' : 'zh-CN')

const update = () => {
  const now = new Date()
  dateStr.value = now.toLocaleDateString(locale.value, {
    year: 'numeric', month: 'long', day: 'numeric',
    timeZone: 'Asia/Shanghai'
  })
  weekStr.value = now.toLocaleDateString(locale.value, {
    weekday: 'short',
    timeZone: 'Asia/Shanghai'
  })
  h.value = String(now.getHours()).padStart(2, '0')
  m.value = String(now.getMinutes()).padStart(2, '0')
  s.value = String(now.getSeconds()).padStart(2, '0')
}

onMounted(() => { update(); timer = setInterval(update, 1000) })
onUnmounted(() => clearInterval(timer))

// 监听语言变化，立即更新日期格式
watch(locale, update)
</script>

<style scoped>
#floating-clock-card {
  position: fixed;
  top: 50px;
  right: 70px;
  z-index: 99998;
  background: transparent;
  border: none;
  box-shadow: none;
  padding: 0;
  text-align: right;
  pointer-events: none;
  user-select: none;
  line-height: 1.2;
}

.fclock-time {
  font-family: 'M PLUS Rounded 1c', 'PingFang SC', sans-serif;
  font-weight: 700;
  font-size: 3.0em;
  color: #ffffff;
  letter-spacing: 4px;
  font-variant-numeric: tabular-nums;
  text-shadow:
    0 0 8px rgba(100, 200, 255, 0.9),
    0 0 20px rgba(80, 180, 255, 0.7),
    0 0 40px rgba(60, 160, 255, 0.4),
    0 2px 4px rgba(0, 0, 0, 0.5);
}

.fclock-colon {
  animation: fclockBlink 1s step-end infinite;
}

@keyframes fclockBlink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.2; }
}

.fclock-meta {
  font-family: 'ZCOOL QingKe HuangYou', "PingFang SC", "Microsoft YaHei", sans-serif;
  font-size: 1.9em;
  color: rgba(220, 245, 255, 0.95);
  margin-top: 6px;
  letter-spacing: 2px;
  text-shadow:
    0 0 6px rgba(100, 200, 255, 0.8),
    0 0 14px rgba(80, 180, 255, 0.5),
    0 1px 2px rgba(0, 0, 0, 0.4);
}

.fclock-divider {
  margin: 0 8px;
  opacity: 0.5;
}

@media (max-width: 768px) {
  #floating-clock-card {
    top: 60px;
    right: 30px;
  }
  .fclock-time { font-size: 2em; letter-spacing: 2px; }
  .fclock-meta { font-size: 0.85em; }
}
</style>