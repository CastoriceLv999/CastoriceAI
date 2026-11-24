import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js/lib/common'

const escape = text => String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')

export function highlightCode(code, language = '') {
  if (!language || !hljs.getLanguage(language)) return escape(code)
  try { return hljs.highlight(code, { language, ignoreIllegals: true }).value }
  catch { return escape(code) }
}

const markdown = new MarkdownIt({ html: false, breaks: true, linkify: true, highlight: highlightCode })
const originalLinkOpen = markdown.renderer.rules.link_open || ((tokens, index, options, env, renderer) => renderer.renderToken(tokens, index, options))
markdown.renderer.rules.link_open = (tokens, index, options, env, renderer) => {
  tokens[index].attrSet('target', '_blank')
  tokens[index].attrSet('rel', 'noopener noreferrer')
  return originalLinkOpen(tokens, index, options, env, renderer)
}
// Images use the same URL validation as Markdown links. Keep unsupported protocols inert.
markdown.renderer.rules.image = (tokens, index) => {
  const token = tokens[index]
  const url = token.attrGet('src') || ''
  const alt = token.content || ''
  if (!/^https?:\/\//i.test(url)) return escape(alt)
  return `<a href="${escape(url)}" target="_blank" rel="noopener noreferrer"><img src="${escape(url)}" alt="${escape(alt)}" loading="lazy" referrerpolicy="no-referrer"></a>`
}
export function renderMarkdown(text = '') {
  return markdown.render(String(text))
}
