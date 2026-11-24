<template>
  <div class="timeline-section">
    <h3>与蝶的时光轴</h3>
    <div class="timeline-container">
      <div v-for="(item, idx) in milestones" :key="idx" class="timeline-item">
        <div class="timeline-dot"></div>
        <div class="timeline-card">
          <div class="timeline-date">{{ item.date }} · 已过去 {{ daysPassed(item.date) }} 天</div>
          <div class="timeline-title">{{ item.title }}</div>
          <div class="timeline-desc">{{ item.desc }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const milestones = [
  { date: "2025-04-09", title: "与你的相遇", desc: "那一天，在翁法罗斯的星空下..." },
  { date: "2025-05-20", title: "奇美拉娃娃", desc: "第一次亲手为你编织了娃娃。" },
  { date: "2025-12-25", title: "约定的未来", desc: "下一个目标：一起去斯缇科西亚看花海。" },
]

const daysPassed = (date) => {
  const d = new Date(date + 'T00:00:00')
  const now = new Date()
  return Math.max(0, Math.floor((now - d) / (1000 * 60 * 60 * 24)))
}
</script>