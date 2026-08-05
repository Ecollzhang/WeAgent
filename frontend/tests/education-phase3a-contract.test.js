const assert = require('assert')
const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8')

function contains(relPath, fragment, message) {
  assert.ok(read(relPath).includes(fragment), `${message}: ${relPath}`)
}

function excludes(relPath, fragment, message) {
  assert.ok(!read(relPath).includes(fragment), `${message}: ${relPath}`)
}

contains(
  'src/api/education.js',
  'getCourseAssets(courseId, params = {})',
  'asset reads must support server-side purpose and lesson filters'
)
contains(
  'src/api/education.js',
  'deleteCourseAsset',
  'teachers need the durable asset archive API'
)
contains(
  'src/store/modules/education.js',
  "form.append('lesson_id', lessonId)",
  'courseware uploads must preserve their lesson binding'
)
contains(
  'src/store/modules/education.js',
  'setAssetVisibility',
  'asset visibility must be reversible from both teacher surfaces'
)
contains(
  'src/store/modules/education.js',
  'archiveAsset',
  'asset deletion must refresh the canonical course query'
)

contains(
  'src/views/education/CoursewareLibrary.vue',
  "['courseware', 'lesson_material'].includes(asset.purpose)",
  'the cabinet must not absorb assignment or generic Agent files'
)
excludes(
  'src/views/education/CoursewareLibrary.vue',
  "'course_material', 'agent_output'",
  'broad legacy purposes must not define the courseware cabinet'
)
for (const command of ['teacher', 'student', 'delete']) {
  contains(
    'src/views/education/CoursewareLibrary.vue',
    `command=\"${command}\"`,
    `the teacher cabinet must expose ${command}`
  )
}
for (const page of [
  'src/views/education/CoursewareLibrary.vue',
  'src/views/education/LessonWorkbench.vue',
]) {
  contains(page, 'slot="dropdown"', 'Element UI 2 asset menus need the named dropdown slot')
  excludes(page, '<el-dropdown-menu #dropdown>', 'Vue 3 slot shorthand leaves the asset menu empty')
}
contains(
  'src/views/education/CoursewareLibrary.vue',
  'assetScope',
  'the cabinet must switch between the selected lesson and whole course'
)
contains(
  'src/views/education/CoursewareLibrary.vue',
  'visibleGeneratedContents',
  'structured versions must default to the selected lesson'
)
for (const command of ['teacher', 'student', 'delete']) {
  contains(
    'src/views/education/LessonWorkbench.vue',
    `command="${command}"`,
    `the lesson material surface must expose the same ${command} asset operation`
  )
}
contains(
  'src/views/education/LessonWorkbench.vue',
  "['courseware', 'lesson_material'].includes(asset.purpose)",
  'the lesson surface must read the canonical scoped asset collection'
)
contains(
  'src/store/modules/education.js',
  'courseOverviewSequence',
  'course overview requests must discard stale responses after a course switch'
)
excludes(
  'src/components/education/EducationCourseContext.vue',
  'created() {\n    this.bootstrapCourse()',
  'the header context must not race page-owned course initialization'
)

contains(
  'src/components/WorkspaceSwitcher/index.vue',
  'workspaceIconClass',
  'workspace icons must map controlled keys instead of rendering raw strings'
)
excludes(
  'src/components/WorkspaceSwitcher/index.vue',
  "{{ ws.icon === 'default' ? '📁' : ws.icon }}",
  'raw icon strings cause the Education workspace ghosting defect'
)

contains(
  'src/components/education/EmbeddedAgentRecord.vue',
  'canOpenBusinessPage',
  'business navigation must be hidden when the current page is already the target'
)
contains(
  'src/views/education/CourseSpace.vue',
  'assignment-card-body',
  'long assignment text needs a bounded card body'
)
contains(
  'src/components/education/EducationShell.vue',
  'grid-template-areas',
  'the Education header must use an intentional responsive grid'
)

console.log('education Phase 3A contract ok')
