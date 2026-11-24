// Keep unfinished fences as code while tokens are still arriving.
export function messageParts(text = '') {
  const parts = []
  let buffer = []
  let language = null
  let fence = ''
  const flush = () => {
    if (buffer.length) parts.push({ type: language === null ? 'text' : 'code', language: language || 'text', content: buffer.join('\n') })
    buffer = []
  }
  for (const line of String(text).split('\n')) {
    const opening = line.match(/^\s{0,3}(`{3,}|~{3,})([\w+-]*)[^\n]*$/)
    if (language === null && opening) {
      flush()
      fence = opening[1]
      language = opening[2] || 'text'
    } else if (language !== null && new RegExp(`^\\s{0,3}${fence[0]}{${fence.length},}\\s*$`).test(line)) {
      flush()
      language = null
    } else buffer.push(line)
  }
  flush()
  return parts
}
