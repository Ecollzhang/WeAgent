const USER_SESSION_KEYS = [
  'access_token',
  'refresh_token',
  'user',
  'active_workspace',
  'user_avatar',
  'agent_meta',
  'model_config',
]

const USER_SESSION_PREFIXES = [
  'weagent.web.workflows.',
  'weagent.web.selectedWorkflow.',
  'weagent.web.deletedWorkflows.',
  'weagent.web.sessionAgentConfigs.',
  'education_submission_draft:',
]

export function clearUserSessionStorage() {
  USER_SESSION_KEYS.forEach(key => localStorage.removeItem(key))
  for (let index = localStorage.length - 1; index >= 0; index -= 1) {
    const key = localStorage.key(index)
    if (key && USER_SESSION_PREFIXES.some(prefix => key.startsWith(prefix))) {
      localStorage.removeItem(key)
    }
  }
}
