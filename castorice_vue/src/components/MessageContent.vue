<template>
  <div class="message-content">
    <template v-for="(part, index) in parts" :key="index">
      <section v-if="part.type === 'code'" class="code-panel" :aria-label="`${part.language} code`">
        <header class="code-toolbar">
          <span>{{ part.language }}</span>
          <button type="button" @click="copyCode(part.content, index)">{{ copied === index ? label('已复制', 'Copied') : label('复制代码', 'Copy code') }}</button>
        </header>
        <pre tabindex="0"><code v-html="highlightCode(part.content, part.language)"></code></pre>
      </section>
      <div v-else class="prose" v-html="renderMarkdown(part.content)"></div>
    </template>
    <span v-if="error" class="copy-error" role="status">{{ label('复制失败，请选中文字手动复制', 'Copy failed. Select the text to copy manually.') }}</span>
  </div>
</template>

<script setup>
import { computed, inject, ref, onBeforeUnmount } from 'vue'
import { messageParts } from '../utils/messageParts.js'
import { renderMarkdown, highlightCode } from '../utils/markdown.js'
import 'highlight.js/styles/github-dark.css'
import { copyText } from '../utils/clipboard.js'
const props = defineProps({ text: { type: String, default: '' } })
const parts = computed(() => messageParts(props.text))
const lang = inject('currentLang', ref('zh-CN'))
const label = (zh, en) => lang.value === 'en-US' ? en : zh
const copied = ref(null)
const error = ref(false)
let timer
async function copyCode(text, index) {
  try {
    await copyText(text)
    error.value = false
    copied.value = index
    clearTimeout(timer)
    timer = setTimeout(() => { copied.value = null }, 2000)
  } catch { error.value = true }
}
onBeforeUnmount(() => clearTimeout(timer))
</script>

<style scoped>
.message-content { min-width: 0; overflow-wrap: anywhere; line-height: 1.75; }
.prose { white-space: normal; overflow-x: auto; }
.prose :deep(> :first-child) { margin-top: 0; }.prose :deep(> :last-child) { margin-bottom: 0; }
.prose :deep(p) { margin: .7em 0; }
.prose :deep(h1), .prose :deep(h2), .prose :deep(h3), .prose :deep(h4) { color: inherit; line-height: 1.4; margin: 1em 0 .5em; }
.prose :deep(h1) { font-size: 1.5em; }.prose :deep(h2) { font-size: 1.3em; }.prose :deep(h3) { font-size: 1.15em; }
.prose :deep(ul), .prose :deep(ol) { padding-left: 1.5em; }.prose :deep(li) { margin: .25em 0; }
.prose :deep(blockquote) { margin: .8em 0; padding: 2px 14px; border-left: 3px solid #bba2e7; color: #c8bfd8; background: #bba2e709; }
.prose :deep(table) { border-collapse: collapse; min-width: 50%; margin: 1em 0; font-size: .9em; }
.prose :deep(th), .prose :deep(td) { border: 1px solid #ffffff28; padding: 8px 12px; }
.prose :deep(th) { background: #bba2e714; }.prose :deep(tr:nth-child(even)) { background: #ffffff04; }
.prose :deep(a) { color: #d8c4ff; text-decoration: underline; text-underline-offset: 3px; }
.prose :deep(img) { max-width: 100%; max-height: 320px; border-radius: 10px; }
.prose :deep(hr) { border: 0; border-top: 1px solid #ffffff25; margin: 1.2em 0; }
.prose :deep(pre) { overflow: auto; background: #111322; padding: 14px; border-radius: 10px; }
.prose :deep(code) { background: #ffffff16; padding: 2px 5px; border-radius: 4px; font-family: Consolas, monospace; }
.code-panel { margin: 12px 0; border: 1px solid #ffffff20; border-radius: 12px; overflow: hidden; background: #111322; }
.code-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 8px 14px; background: #ffffff08; color: #bfc3dd; font: 12px system-ui, sans-serif; }
.code-toolbar button { border: 0; background: transparent; color: #d9d1ff; cursor: pointer; padding: 6px 8px; border-radius: 6px; }
.code-toolbar button:hover, .code-toolbar button:focus-visible { background: #ffffff15; outline: 2px solid #b7a0f7; }
pre { margin: 0; padding: 16px; overflow-x: auto; white-space: pre; max-height: 520px; tab-size: 2; scrollbar-width: thin; }
pre code { font: 13px/1.7 Consolas, 'Cascadia Code', monospace; color: #e2e5f4; }
.copy-error { font-size: 12px; color: #ffbfba; }
</style>
