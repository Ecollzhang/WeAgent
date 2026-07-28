const assert = require('assert')
const {
  normalizeActivities,
  normalizeChoiceOption,
  normalizeObjectives,
  formatVersionTime,
} = require('../src/utils/educationContent')

assert.strictEqual(
  normalizeObjectives([
    { id: 'o1', description: '定位关键信息' },
    { objective: '使用证据完成写作' },
  ]),
  '定位关键信息\n使用证据完成写作'
)
assert.ok(!normalizeObjectives([{ description: '可观察目标' }]).includes('[object Object]'))
assert.ok(normalizeActivities([
  { name: '导入', teacher_activity: '展示图片', student_activity: '预测主题' },
]).includes('展示图片'))
assert.ok(!normalizeActivities([
  { name: '阅读', description: '精读课文', assessment: '完成退出卡' },
]).includes('完成退出卡'))
assert.ok(formatVersionTime('2026-07-28T08:30:00Z'))
assert.strictEqual(normalizeChoiceOption('A. Excitement only', 0), 'A. Excitement only')
assert.strictEqual(normalizeChoiceOption('A Excitement only', 0), 'A. Excitement only')
assert.strictEqual(normalizeChoiceOption('Excitement only', 0), 'A. Excitement only')
assert.strictEqual(
  normalizeChoiceOption({ label: 'B', text: 'B. Nervousness only' }, 1),
  'B. Nervousness only'
)

console.log('education content normalization ok')
