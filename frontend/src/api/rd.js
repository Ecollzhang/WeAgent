import axios from './axios'

const RD_BASE = '/rd'

// ── 项目 CRUD ────────────────────────────────────────────────

export function getProjects(workspaceId = '') {
  return axios.get(`${RD_BASE}/projects`, {
    params: workspaceId ? { workspace_id: workspaceId } : {}
  })
}

export function getProject(id) {
  return axios.get(`${RD_BASE}/projects/${id}`)
}

export function createProject(data) {
  return axios.post(`${RD_BASE}/projects`, data)
}

export function updateProject(id, data) {
  return axios.put(`${RD_BASE}/projects/${id}`, data)
}

export function deleteProject(id) {
  return axios.delete(`${RD_BASE}/projects/${id}`)
}

// ── 项目文件管理 ──────────────────────────────────────────────

export function getProjectFiles(projectId) {
  return axios.get(`${RD_BASE}/projects/${projectId}/files`)
}

export function getProjectFile(projectId, fileId) {
  return axios.get(`${RD_BASE}/projects/${projectId}/files/${fileId}`)
}

export function addProjectFile(projectId, data) {
  return axios.post(`${RD_BASE}/projects/${projectId}/files`, data)
}

export function deleteProjectFile(projectId, fileId) {
  return axios.delete(`${RD_BASE}/projects/${projectId}/files/${fileId}`)
}

// ── 项目上下文 ────────────────────────────────────────────────

export function getProjectContext(projectId) {
  return axios.get(`${RD_BASE}/projects/${projectId}/context`)
}

// ── 迭代管理 ──────────────────────────────────────────────────

export function getIterations(projectId) {
  return axios.get(`${RD_BASE}/projects/${projectId}/iterations`)
}

export function createIteration(projectId, data) {
  return axios.post(`${RD_BASE}/projects/${projectId}/iterations`, data)
}

export function getIteration(id) {
  return axios.get(`${RD_BASE}/iterations/${id}`)
}

export function updateIteration(id, data) {
  return axios.put(`${RD_BASE}/iterations/${id}`, data)
}

export function deleteIteration(id) {
  return axios.delete(`${RD_BASE}/iterations/${id}`)
}

export function updateIterationStatus(id, status) {
  return axios.patch(`${RD_BASE}/iterations/${id}/status`, { status })
}

// ── 需求管理 ──────────────────────────────────────────────────

export function getRequirements(projectId, params = {}) {
  return axios.get(`${RD_BASE}/projects/${projectId}/requirements`, { params })
}

export function createRequirement(projectId, data) {
  return axios.post(`${RD_BASE}/projects/${projectId}/requirements`, data)
}

export function getRequirement(id) {
  return axios.get(`${RD_BASE}/requirements/${id}`)
}

export function updateRequirement(id, data) {
  return axios.put(`${RD_BASE}/requirements/${id}`, data)
}

export function deleteRequirement(id) {
  return axios.delete(`${RD_BASE}/requirements/${id}`)
}

export function updateRequirementStatus(id, status) {
  return axios.patch(`${RD_BASE}/requirements/${id}/status`, { status })
}

export function assignRequirement(id, assigneeId) {
  return axios.patch(`${RD_BASE}/requirements/${id}/assign`, { assignee_id: assigneeId })
}

export function moveRequirementToIteration(id, iterationId) {
  return axios.post(`${RD_BASE}/requirements/${id}/move-iteration`, { iteration_id: iterationId })
}

export function addRequirementAssignee(projectId, requirementId, userId, role = 'primary') {
  return axios.post(`${RD_BASE}/projects/${projectId}/requirements/${requirementId}/assignees`, { user_id: userId, role })
}

export function removeRequirementAssignee(projectId, requirementId, userId) {
  return axios.delete(`${RD_BASE}/projects/${projectId}/requirements/${requirementId}/assignees/${userId}`)
}

// ── Bug 管理 ──────────────────────────────────────────────────

export function getBugs(projectId, params = {}) {
  return axios.get(`${RD_BASE}/projects/${projectId}/bugs`, { params })
}

export function createBug(projectId, data) {
  return axios.post(`${RD_BASE}/projects/${projectId}/bugs`, data)
}

export function getBug(id) {
  return axios.get(`${RD_BASE}/bugs/${id}`)
}

export function updateBug(id, data) {
  return axios.put(`${RD_BASE}/bugs/${id}`, data)
}

export function deleteBug(id) {
  return axios.delete(`${RD_BASE}/bugs/${id}`)
}

export function updateBugStatus(id, status) {
  return axios.patch(`${RD_BASE}/bugs/${id}/status`, { status })
}

export function assignBug(id, assigneeId) {
  return axios.patch(`${RD_BASE}/bugs/${id}/assign`, { assignee_id: assigneeId })
}

export function moveBugToIteration(id, iterationId) {
  return axios.post(`${RD_BASE}/bugs/${id}/move-iteration`, { iteration_id: iterationId })
}

export function addBugAssignee(projectId, bugId, userId, role = 'fixer') {
  return axios.post(`${RD_BASE}/projects/${projectId}/bugs/${bugId}/assignees`, { user_id: userId, role })
}

export function removeBugAssignee(projectId, bugId, userId) {
  return axios.delete(`${RD_BASE}/projects/${projectId}/bugs/${bugId}/assignees/${userId}`)
}

// ── 分支与提交 ────────────────────────────────────────────────

export function getProjectBranches(projectId, params = {}) {
  return axios.get(`${RD_BASE}/projects/${projectId}/branches`, { params })
}

export function createBranch(projectId, data) {
  return axios.post(`${RD_BASE}/projects/${projectId}/branches`, data)
}

export function updateBranch(projectId, branchId, data) {
  return axios.put(`${RD_BASE}/projects/${projectId}/branches/${branchId}`, data)
}

export function deleteBranch(projectId, branchId) {
  return axios.delete(`${RD_BASE}/projects/${projectId}/branches/${branchId}`)
}

// ── 代码仓库 ──────────────────────────────────────────────────

// GitHub OAuth
export function getGithubAuthUrl(params = {}) {
  return axios.get(`${RD_BASE}/github/auth-url`, { params })
}

export function getGithubStatus() {
  return axios.get(`${RD_BASE}/github/status`)
}

export function saveGithubToken(data) {
  return axios.post(`${RD_BASE}/github/save-token`, data)
}

export function revokeGithub() {
  return axios.delete(`${RD_BASE}/github/revoke`)
}

export function listGithubRepos(params = {}) {
  return axios.get(`${RD_BASE}/github/repos`, { params })
}

export function getOauthConfig() {
  return axios.get(`${RD_BASE}/github/oauth-config`)
}

export function saveOauthConfig(data) {
  return axios.put(`${RD_BASE}/github/oauth-config`, data)
}

// 仓库 CRUD
export function getRepos(projectId) {
  return axios.get(`${RD_BASE}/projects/${projectId}/repos`)
}

export function getAllRepos(params = {}) {
  return axios.get(`${RD_BASE}/repos`, { params })
}

export function createRepo(projectId, data) {
  return axios.post(`${RD_BASE}/projects/${projectId}/repos`, data)
}

export function deleteRepo(projectId, repoId) {
  return axios.delete(`${RD_BASE}/projects/${projectId}/repos/${repoId}`)
}

export function getRepo(id) {
  return axios.get(`${RD_BASE}/repos/${id}`)
}

export function getRepoTree(repoId, params = {}) {
  return axios.get(`${RD_BASE}/repos/${repoId}/tree`, { params })
}

export function getRepoFile(repoId, params = {}) {
  return axios.get(`${RD_BASE}/repos/${repoId}/file`, { params })
}

export function getRepoBranches(repoId) {
  return axios.get(`${RD_BASE}/repos/${repoId}/branches`)
}

export function createRepoBranch(repoId, data) {
  return axios.post(`${RD_BASE}/repos/${repoId}/branches`, data)
}

export function getRepoCommits(repoId, params = {}) {
  return axios.get(`${RD_BASE}/repos/${repoId}/commits`, { params })
}

export function getCommitDiff(repoId, sha) {
  return axios.get(`${RD_BASE}/repos/${repoId}/commits/${sha}/diff`)
}

// ── 代码审查 ──────────────────────────────────────────────────

export function getReviews(projectId, params = {}) {
  return axios.get(`${RD_BASE}/projects/${projectId}/reviews`, { params })
}

export function createReview(projectId, data) {
  return axios.post(`${RD_BASE}/projects/${projectId}/reviews`, data)
}

export function getReview(id) {
  return axios.get(`${RD_BASE}/reviews/${id}`)
}

export function deleteReview(id) {
  return axios.delete(`${RD_BASE}/reviews/${id}`)
}

export function retryReview(id) {
  return axios.post(`${RD_BASE}/reviews/${id}/retry`)
}

export function autoFixReview(id) {
  return axios.post(`${RD_BASE}/reviews/${id}/auto-fix`)
}

export function updateReviewIssue(reviewId, issueId, data) {
  return axios.patch(`${RD_BASE}/reviews/${reviewId}/issues/${issueId}`, data)
}

// ── 构建管理 ──────────────────────────────────────────────────

export function getBuilds(projectId, params = {}) {
  return axios.get(`${RD_BASE}/projects/${projectId}/builds`, { params })
}

export function triggerBuild(projectId, data) {
  return axios.post(`${RD_BASE}/projects/${projectId}/builds`, data)
}

export function getBuild(id) {
  return axios.get(`${RD_BASE}/builds/${id}`)
}

export function getBuildLog(id, params = {}) {
  return axios.get(`${RD_BASE}/builds/${id}/log`, { params })
}

export function cancelBuild(id) {
  return axios.post(`${RD_BASE}/builds/${id}/cancel`)
}

export function getBuildArtifacts(id) {
  return axios.get(`${RD_BASE}/builds/${id}/artifacts`)
}

export function getArtifactDownloadUrl(buildId, artifactId) {
  return `${RD_BASE}/builds/${buildId}/artifacts/${artifactId}/download`
}

export function deleteBuild(id) {
  return axios.delete(`${RD_BASE}/builds/${id}`)
}

export function syncBuild(id) {
  return axios.post(`${RD_BASE}/builds/${id}/sync`)
}

export function getReposForBuild(projectId) {
  return axios.get(`${RD_BASE}/projects/${projectId}/repos-for-build`)
}

export function getWorkflows(repoId) {
  return axios.get(`${RD_BASE}/repos/${repoId}/workflows`)
}

// ── 服务自描述 ────────────────────────────────────────────────

export function getServiceSpec() {
  return axios.get(`${RD_BASE}/spec`)
}

// ── 评论 ──────────────────────────────────────────────────────

export function getComments(projectId, params = {}) {
  return axios.get(`${RD_BASE}/projects/${projectId}/comments`, { params })
}

export function createComment(projectId, data) {
  return axios.post(`${RD_BASE}/projects/${projectId}/comments`, data)
}

export function updateComment(projectId, commentId, data) {
  return axios.put(`${RD_BASE}/projects/${projectId}/comments/${commentId}`, data)
}

export function deleteComment(projectId, commentId) {
  return axios.delete(`${RD_BASE}/projects/${projectId}/comments/${commentId}`)
}

// ── 成员 ──────────────────────────────────────────────────────

export function getMembers(projectId) {
  return axios.get(`${RD_BASE}/projects/${projectId}/members`)
}

export function addMember(projectId, data) {
  return axios.post(`${RD_BASE}/projects/${projectId}/members`, data)
}

export function updateMemberRole(projectId, userId, role) {
  return axios.put(`${RD_BASE}/projects/${projectId}/members/${userId}`, { role })
}

export function removeMember(projectId, memberId) {
  return axios.delete(`${RD_BASE}/projects/${projectId}/members/${memberId}`)
}

// ── 活动日志 ──────────────────────────────────────────────────

export function getActivities(projectId, params = {}) {
  return axios.get(`${RD_BASE}/projects/${projectId}/activities`, { params })
}

// ── 甘特图 ────────────────────────────────────────────────────

export function getGanttData(projectId) {
  return axios.get(`${RD_BASE}/projects/${projectId}/gantt`)
}
