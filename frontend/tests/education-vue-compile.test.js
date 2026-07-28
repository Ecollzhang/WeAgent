const assert = require('assert')
const fs = require('fs')
const path = require('path')
const compiler = require('vue-template-compiler')
const parser = require('@babel/parser')

const root = path.resolve(__dirname, '..')
const files = [
  'src/components/education/EducationShell.vue',
  'src/components/education/EducationModuleRail.vue',
  'src/components/education/MindMapTree.vue',
  'src/components/education/CourseCard.vue',
  'src/components/education/SafeHtmlPreview.vue',
  'src/components/education/LessonPlanEditor.vue',
  'src/views/education/EducationHome.vue',
  'src/views/education/CourseSpace.vue',
  'src/views/education/LessonWorkbench.vue',
  'src/views/education/AssignmentWorkspace.vue',
  'src/views/education/CoursewareLibrary.vue',
  'src/views/education/StudentInsights.vue',
  'src/views/education/KnowledgeCenter.vue',
  'src/views/education/MockExamCenter.vue',
  'src/views/education/WeaknessCenter.vue',
  'src/views/education/MindMapCenter.vue',
]

for (const relPath of files) {
  const source = fs.readFileSync(path.join(root, relPath), 'utf8')
  const parsed = compiler.parseComponent(source)
  assert.ok(parsed.template, `${relPath}: missing template`)
  assert.ok(parsed.script, `${relPath}: missing script`)

  const compiled = compiler.compile(parsed.template.content, { outputSourceRange: true })
  assert.deepStrictEqual(
    compiled.errors,
    [],
    `${relPath}: template errors: ${compiled.errors.join('; ')}`
  )
  parser.parse(parsed.script.content, {
    sourceType: 'module',
    plugins: ['objectRestSpread', 'optionalChaining'],
  })
}

console.log('education Vue compile contract ok')
