const assert = require('assert')
const {
  PRESENTATION_THEMES,
  renderSlideDocumentHtml,
} = require('../src/utils/slideDocument')

const html = renderSlideDocumentHtml({
  title: 'Safe <Courseware>',
  slides: [{
    title: 'Evidence & Writing',
    blocks: [
      { type: 'heading', content: '<script>alert(1)</script>' },
      { type: 'list', content: ['Quote evidence', 'Write a continuation'] },
      { type: 'table', content: { headers: ['Item'], rows: [['Turning point']] } },
    ],
    speaker_notes: '45 minutes',
  }],
})

assert.ok(html.startsWith('<!doctype html>'))
assert.ok(html.includes('Evidence &amp; Writing'))
assert.ok(html.includes('&lt;script&gt;alert(1)&lt;/script&gt;'))
assert.ok(!html.includes('<script>alert(1)</script>'))
assert.ok(html.includes('<table>'))
assert.ok(html.includes('45 minutes'))
console.log('slide document rendering ok')

assert.deepStrictEqual(
  Object.values(PRESENTATION_THEMES).map(theme => theme.label),
  ['清朗课堂', '纸张批注', '童趣绘本', '深色聚焦'],
)

for (const style of Object.keys(PRESENTATION_THEMES)) {
  const themed = renderSlideDocumentHtml({
    title: style,
    theme: { style },
    slides: [{
      id: 'theme-check',
      title: 'Theme check',
      layout: 'content',
      blocks: [{ type: 'text', content: 'Readable content' }],
    }],
  })
  assert.ok(themed.includes(`data-theme="${style}"`))
  assert.ok(themed.includes(PRESENTATION_THEMES[style].background))
}
