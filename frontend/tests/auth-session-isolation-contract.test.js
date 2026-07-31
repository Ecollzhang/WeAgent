const assert = require('assert')
const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8')

const userStore = read('src/store/modules/user.js')
for (const moduleName of [
  'workspace',
  'conversation',
  'message',
  'agent',
  'settings',
  'education',
]) {
  assert.ok(
    userStore.includes(`commit('${moduleName}/RESET_STATE', null, { root: true })`),
    `logout must reset ${moduleName} user-scoped state`
  )
}

for (const modulePath of [
  'src/store/modules/workspace.js',
  'src/store/modules/conversation.js',
  'src/store/modules/message.js',
  'src/store/modules/agent.js',
  'src/store/modules/settings.js',
  'src/store/modules/education.js',
]) {
  assert.ok(
    read(modulePath).includes('RESET_STATE(state)'),
    `${modulePath} must expose an explicit session reset mutation`
  )
}

const sessionStorage = read('src/utils/session-storage.js')
for (const key of [
  "'access_token'",
  "'refresh_token'",
  "'user'",
  "'active_workspace'",
  "'user_avatar'",
  "'agent_meta'",
  "'model_config'",
]) {
  assert.ok(sessionStorage.includes(key), `session cleanup must remove ${key}`)
}
for (const prefix of [
  "'weagent.web.workflows.'",
  "'weagent.web.selectedWorkflow.'",
  "'weagent.web.deletedWorkflows.'",
  "'weagent.web.sessionAgentConfigs.'",
  "'education_submission_draft:'",
]) {
  assert.ok(sessionStorage.includes(prefix), `session cleanup must remove ${prefix} data`)
}
assert.ok(
  read('src/api/axios.js').includes('clearUserSessionStorage()'),
  'expired authentication must clear persistent user scope before reloading'
)

const assignmentWorkspace = read('src/views/education/AssignmentWorkspace.vue')
assert.ok(
  assignmentWorkspace.includes('education_submission_draft:${this.currentUserId}:${this.assignmentId}'),
  'offline assignment drafts must be scoped by user and assignment'
)

console.log('auth session isolation contract passed')
