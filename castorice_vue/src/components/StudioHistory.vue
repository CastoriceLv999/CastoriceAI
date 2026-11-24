<template>
  <div class="timeline-section studio-history">
    <div class="session-header">
      <h3>{{ t('studioHistory') }}</h3>
      <button class="session-btn" @click="clearAll" v-if="records.length">
        {{ t('clearAll') }}
      </button>
    </div>
    <div class="session-list">
      <div v-for="(record, idx) in records" :key="record.id" class="timeline-item session-item">
        <div class="timeline-dot"></div>
        <div class="timeline-card session-card">
          <div class="session-meta">
            <span class="session-time">{{ formatTime(record.timestamp) }}</span>
            <span class="session-badge mode-badge"
                  :class="record.mode === 'video' ? 'video-badge' : 'image-badge'">
                  {{ record.mode === 'video' ? 'VIDEO' : 'IMAGE' }}
            </span>
            <span class="session-badge">{{ record.size }} · {{ record.count }}{{ t('unit') }}</span>
            <span v-if="record.refCount" class="session-badge ref-badge">{{ record.refCount }}{{ t('refUnit') }}</span>
          </div>
          <div class="studio-prompt">{{ record.prompt }}</div>
          <div v-if="record.results.length" class="studio-results">
            <a v-for="(url, uidx) in record.results" :key="uidx" :href="url" target="_blank" class="studio-thumb-link">
              <video v-if="record.mode === 'video'"
                      :src="url" class="studio-thumb"
                      muted preload="metadata" />
              <img v-else :src="url" class="studio-thumb" alt="result" />
            </a>
          </div>
          <div class="session-actions-row">
            <button class="session-btn delete-btn" @click="remove(idx)">{{ t('delete') }}</button>
          </div>
        </div>
      </div>
      <div v-if="!records.length" class="empty-hint">{{ t('noRecords') }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, inject } from 'vue'

const currentLang = inject('currentLang', ref('zh-CN'))
const i18n = {
  'zh-CN': {
    studioHistory: '✦ 创意记录',
    clearAll: '清空记录',
    delete: '删除',
    noRecords: '暂无创意记录，开始生成你的第一幅作品吧......',
    unit: '张',
    refUnit: '张参考图'
  },
  'en-US': {
    studioHistory: '✦ Creation History',
    clearAll: 'Clear All',
    delete: 'Delete',
    noRecords: 'No creation history yet. Start generating your first artwork......',
    unit: ' images',
    refUnit: ' refs'
  }
}
const t = (key) => i18n[currentLang.value]?.[key] || i18n['zh-CN'][key]

const STORAGE_KEY = 'castorice_studio_history'
const records = ref([])

onMounted(() => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) records.value = JSON.parse(raw)
  } catch (e) { records.value = [] }
})

const persist = () => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(records.value))
  } catch (e) {}
}

const addRecord = (record) => {
  records.value.unshift({
    id: `studio_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
    ...record
  })
  if (records.value.length > 20) records.value = records.value.slice(0, 20)
  persist()
}

const remove = (idx) => {
  records.value.splice(idx, 1)
  persist()
}

const clearAll = () => {
  records.value = []
  persist()
}

const formatTime = (ts) => {
  const d = new Date(ts)
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

defineExpose({ addRecord })
</script>

<style scoped>
.studio-history { margin-top: 2rem; }
.session-header { display: flex; justify-content: space-between; align-items: center; margin: 2rem 0 1rem; flex-wrap: wrap; gap: 0.5rem; }
.session-header h3 { margin: 0; color: white; text-shadow: 0 1px 4px rgba(0,0,0,0.9); }
.session-btn { padding: 0.4rem 0.9rem; border-radius: 8px; border: 1px solid rgba(255,255,255,0.3); background: rgba(0,0,0,var(--chat-alpha)); color: white; font-size: 0.85rem; cursor: pointer; transition: all 0.3s; backdrop-filter: blur(4px); font-family: inherit; }
.session-btn:hover { background: rgba(0,0,0,var(--chat-alpha-focus)); border-color: rgba(255,255,255,0.5); transform: translateY(-1px); }
.delete-btn { border-color: rgba(255,120,120,0.4); color: rgba(255,160,160,1); font-size: 0.8rem; padding: 0.3rem 0.7rem; }
.delete-btn:hover { background: rgba(0,0,0,var(--chat-alpha-focus)); border-color: rgba(255,120,120,0.6); }
.session-list { position: relative; margin-left: 20px; border-left: 2px solid rgba(255,255,255,0.3); padding-left: 20px; }
.timeline-item { position: relative; margin-bottom: 20px; }
.timeline-dot { position: absolute; left: -31px; top: 4px; width: 12px; height: 12px; background: rgba(220,160,255,0.8); border-radius: 50%; box-shadow: 0 0 10px rgba(220,160,255,0.5); }
.session-card { background: rgba(0,0,0,var(--chat-alpha)); padding: 14px 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.2); backdrop-filter: blur(4px); }
.session-meta { display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; margin-bottom: 8px; }
.session-time { font-size: 0.8rem; color: rgba(255,255,255,0.6); font-family: 'M PLUS Rounded 1c', monospace; }
.session-badge { padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; background: rgba(0,0,0,var(--chat-alpha-focus)); color: rgba(220,180,255,1); border: 1px solid rgba(220,160,255,0.5); }
.ref-badge { color: rgba(140,220,255,1); border-color: rgba(140,220,255,0.5); }
.studio-prompt { color: white; font-size: 0.9rem; margin-bottom: 10px; line-height: 1.5; word-break: break-all; }
.studio-results { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
.studio-thumb-link { display: block; border-radius: 8px; overflow: hidden; border: 1px solid rgba(255,255,255,0.2); width: 80px; height: 80px; }
.studio-thumb { width: 100%; height: 100%; object-fit: cover; display: block; transition: transform 0.3s; }
.studio-thumb-link:hover .studio-thumb { transform: scale(1.05); }
.empty-hint { color: rgba(255,255,255,0.35); text-align: center; margin: 2rem 0; font-size: 0.9rem; }
.session-actions-row { display: flex; gap: 0.5rem; margin-top: 0.5rem; }
@media (max-width: 768px) {
  .session-header { flex-direction: column; align-items: flex-start; }
  .studio-thumb-link { width: 60px; height: 60px; }
}
.mode-badge {
    background: rgba(100,200,255,0.15) !important;
    border-color: rgba(100,200,255,0.4) !important;
}
.mode-badge.video-badge {
    background: rgba(220,160,255,0.15) !important;
    border-color: rgba(220,160,255,0.4) !important;
    color: rgba(220,180,255,1) !important;
}
</style>