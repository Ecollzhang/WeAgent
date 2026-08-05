const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')
const read = relative => fs.readFileSync(path.join(root, relative), 'utf8')
const assert = (condition, message) => { if (!condition) throw new Error(message) }

const api = read('src/api/education.js')
const store = read('src/store/modules/education.js')
const page = read('src/views/education/KnowledgeCenter.vue')

assert(api.includes('export function adoptWebKnowledgeResource'), 'web resource adoption API required')
assert(api.includes('/knowledge-resources/adopt-url'), 'adoption must use trusted server endpoint')
assert(store.includes('async adoptWebKnowledgeResource'), 'store must refresh after adoption')
assert(store.includes('value.results || []'), 'search response must preserve pipeline results')
assert(page.includes('ProductAgentRunPanel'), 'knowledge center needs visible Agent progress')
assert(page.includes('AI 生成题目'), 'question bank needs Agent product entry')
assert(page.includes('AI 智能组卷'), 'paper bank needs Agent product entry')
assert(page.includes('联网补充资料'), 'knowledge base needs research entry')
assert(page.includes("startKnowledgeProduct('question_generation'"), 'question Agent product code missing')
assert(page.includes("startKnowledgeProduct('paper_generation'"), 'paper Agent product code missing')
assert(page.includes("startKnowledgeProduct('knowledge_research'"), 'research Agent product code missing')
assert(page.includes('teacherConfirmedRights'), 'adoption must require explicit rights confirmation')
assert(page.includes('licenseNote'), 'adoption must retain license note')
assert(page.includes('search_excerpt'), 'search excerpt must stay discovery metadata')
assert(page.includes('return false'), 'a failed Agent launch must keep its dialog recoverable')

console.log('education knowledge agent contract ok')
