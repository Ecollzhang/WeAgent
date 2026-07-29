const assert = require('assert')
const { renderSlideDocumentHtml } = require('../src/utils/slideDocument')

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
