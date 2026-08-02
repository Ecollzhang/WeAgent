import {
  getProjects, getProject, createProject, updateProject, deleteProject,
  getProjectFiles, getProjectFile, addProjectFile, deleteProjectFile,
  getProjectContext,
  getIterations, createIteration, getIteration, updateIteration, deleteIteration, updateIterationStatus,
  getRequirements, createRequirement, getRequirement, updateRequirement, deleteRequirement, updateRequirementStatus,
  getBugs, createBug, getBug, updateBug, deleteBug, updateBugStatus,
  getProjectBranches, createBranch, updateBranch, deleteBranch,
  getRepos, getRepo, getRepoTree, getRepoFile, getRepoBranches, getRepoCommits,
  getReviews, createReview, getReview, deleteReview, retryReview,
  getBuilds, triggerBuild, getBuild,
  getComments, createComment, deleteComment,
  getMembers, addMember, updateMemberRole, removeMember,
  getActivities, getGanttData,
} from '../../api/rd'

export default {
  namespaced: true,

  state: {
    // 项目
    projects: [],
    currentProject: null,
    currentFiles: [],
    currentFile: null,
    projectContext: null,

    // 迭代
    iterations: [],
    currentIteration: null,

    // 需求
    requirements: [],
    currentRequirement: null,

    // Bug
    bugs: [],
    currentBug: null,

    // 分支与提交
    branches: [],
    commits: [],

    // 代码仓库
    repos: [],
    currentRepo: null,
    repoTree: [],
    repoFile: null,
    repoBranches: [],
    repoCommits: [],

    // 代码审查
    reviews: [],
    currentReview: null,

    // 构建
    builds: [],
    currentBuild: null,

    // 评论
    comments: [],

    // 成员
    members: [],

    // 活动日志
    activities: [],
    activityTotal: 0,

    // 甘特图
    ganttData: null,

    loading: false,
  },

  getters: {
    allProjects: state => state.projects,
    currentProject: state => state.currentProject,
    currentFiles: state => state.currentFiles,
    currentFile: state => state.currentFile,
    projectContext: state => state.projectContext,
    isLoading: state => state.loading,
    projectById: state => id => state.projects.find(p => p.id === id),

    // 迭代
    allIterations: state => state.iterations,
    currentIteration: state => state.currentIteration,
    activeIteration: state => state.iterations.find(i => i.status === 'active'),

    // 需求
    allRequirements: state => state.requirements,
    currentRequirement: state => state.currentRequirement,

    // Bug
    allBugs: state => state.bugs,
    currentBug: state => state.currentBug,

    // 仓库
    allRepos: state => state.repos,
    currentRepo: state => state.currentRepo,

    // 审查
    allReviews: state => state.reviews,
    currentReview: state => state.currentReview,

    // 构建
    allBuilds: state => state.builds,
    currentBuild: state => state.currentBuild,

    // 评论
    allComments: state => state.comments,

    // 成员
    allMembers: state => state.members,

    // 活动日志
    allActivities: state => state.activities,
    activityTotal: state => state.activityTotal,

    // 甘特图
    ganttData: state => state.ganttData,
  },

  mutations: {
    SET_PROJECTS(state, projects) { state.projects = projects },
    SET_CURRENT_PROJECT(state, project) { state.currentProject = project },
    ADD_PROJECT(state, project) { state.projects.unshift(project) },
    UPDATE_PROJECT(state, updated) {
      const idx = state.projects.findIndex(p => p.id === updated.id)
      if (idx >= 0) state.projects.splice(idx, 1, updated)
      if (state.currentProject?.id === updated.id) state.currentProject = updated
    },
    REMOVE_PROJECT(state, id) {
      state.projects = state.projects.filter(p => p.id !== id)
      if (state.currentProject?.id === id) state.currentProject = null
    },
    SET_FILES(state, files) { state.currentFiles = files },
    SET_CURRENT_FILE(state, file) { state.currentFile = file },
    ADD_FILE(state, file) { state.currentFiles.push(file) },
    REMOVE_FILE(state, fileId) { state.currentFiles = state.currentFiles.filter(f => f.id !== fileId) },
    SET_PROJECT_CONTEXT(state, context) { state.projectContext = context },

    // 迭代
    SET_ITERATIONS(state, items) { state.iterations = items },
    SET_CURRENT_ITERATION(state, item) { state.currentIteration = item },
    ADD_ITERATION(state, item) { state.iterations.push(item) },
    UPDATE_ITERATION(state, updated) {
      const idx = state.iterations.findIndex(i => i.id === updated.id)
      if (idx >= 0) state.iterations.splice(idx, 1, updated)
    },
    REMOVE_ITERATION(state, id) { state.iterations = state.iterations.filter(i => i.id !== id) },

    // 需求
    SET_REQUIREMENTS(state, items) { state.requirements = items },
    SET_CURRENT_REQUIREMENT(state, item) { state.currentRequirement = item },
    ADD_REQUIREMENT(state, item) { state.requirements.unshift(item) },
    UPDATE_REQUIREMENT(state, updated) {
      const idx = state.requirements.findIndex(r => r.id === updated.id)
      if (idx >= 0) state.requirements.splice(idx, 1, updated)
    },
    REMOVE_REQUIREMENT(state, id) { state.requirements = state.requirements.filter(r => r.id !== id) },

    // Bug
    SET_BUGS(state, items) { state.bugs = items },
    SET_CURRENT_BUG(state, item) { state.currentBug = item },
    ADD_BUG(state, item) { state.bugs.unshift(item) },
    UPDATE_BUG(state, updated) {
      const idx = state.bugs.findIndex(b => b.id === updated.id)
      if (idx >= 0) state.bugs.splice(idx, 1, updated)
    },
    REMOVE_BUG(state, id) { state.bugs = state.bugs.filter(b => b.id !== id) },

    // 分支与提交
    SET_BRANCHES(state, items) { state.branches = items },
    SET_COMMITS(state, items) { state.commits = items },

    // 仓库
    SET_REPOS(state, items) { state.repos = items },
    SET_CURRENT_REPO(state, item) { state.currentRepo = item },
    SET_REPO_TREE(state, tree) { state.repoTree = tree },
    SET_REPO_FILE(state, file) { state.repoFile = file },
    SET_REPO_BRANCHES(state, items) { state.repoBranches = items },
    SET_REPO_COMMITS(state, items) { state.repoCommits = items },

    // 审查
    SET_REVIEWS(state, items) { state.reviews = items },
    SET_CURRENT_REVIEW(state, item) { state.currentReview = item },
    ADD_REVIEW(state, item) { state.reviews.unshift(item) },
    REMOVE_REVIEW(state, id) { state.reviews = state.reviews.filter(r => r.id !== id) },

    // 构建
    SET_BUILDS(state, items) { state.builds = items },
    SET_CURRENT_BUILD(state, item) { state.currentBuild = item },
    ADD_BUILD(state, item) { state.builds.unshift(item) },

    // 评论
    SET_COMMENTS(state, items) { state.comments = items },
    ADD_COMMENT(state, item) { state.comments.unshift(item) },
    UPDATE_COMMENT(state, updated) {
      const idx = state.comments.findIndex(c => c.id === updated.id)
      if (idx >= 0) state.comments.splice(idx, 1, updated)
    },
    REMOVE_COMMENT(state, id) { state.comments = state.comments.filter(c => c.id !== id) },

    // 成员
    SET_MEMBERS(state, items) { state.members = items },
    ADD_MEMBER(state, item) { state.members.push(item) },
    REMOVE_MEMBER(state, id) { state.members = state.members.filter(m => m.id !== id && m.user_id !== id) },

    // 活动日志
    SET_ACTIVITIES(state, { items, total }) {
      state.activities = items
      state.activityTotal = total || items.length
    },

    // 甘特图
    SET_GANTT_DATA(state, data) { state.ganttData = data },

    SET_LOADING(state, loading) { state.loading = loading },
  },

  actions: {
    // ── 项目 ──
    async fetchProjects({ commit }, workspaceId = '') {
      commit('SET_LOADING', true)
      try {
        const res = await getProjects(workspaceId)
        if (res.code === 200) commit('SET_PROJECTS', res.data.items || [])
      } finally { commit('SET_LOADING', false) }
    },
    async fetchProject({ commit }, id) {
      commit('SET_LOADING', true)
      try {
        const res = await getProject(id)
        if (res.code === 200) commit('SET_CURRENT_PROJECT', res.data)
        return res
      } finally { commit('SET_LOADING', false) }
    },
    async createProject({ commit }, data) {
      const res = await createProject(data)
      if (res.code === 201) commit('ADD_PROJECT', res.data)
      return res
    },
    async updateProject({ commit }, { id, data }) {
      const res = await updateProject(id, data)
      if (res.code === 200) commit('UPDATE_PROJECT', res.data)
      return res
    },
    async deleteProject({ commit }, id) {
      const res = await deleteProject(id)
      if (res.code === 200) commit('REMOVE_PROJECT', id)
      return res
    },
    async fetchFiles({ commit }, projectId) {
      const res = await getProjectFiles(projectId)
      if (res.code === 200) commit('SET_FILES', res.data.items || [])
      return res
    },
    async fetchFile({ commit }, { projectId, fileId }) {
      const res = await getProjectFile(projectId, fileId)
      if (res.code === 200) commit('SET_CURRENT_FILE', res.data)
      return res
    },
    async addFile({ commit }, { projectId, data }) {
      const res = await addProjectFile(projectId, data)
      if (res.code === 201) commit('ADD_FILE', res.data)
      return res
    },
    async deleteFile({ commit }, { projectId, fileId }) {
      const res = await deleteProjectFile(projectId, fileId)
      if (res.code === 200) commit('REMOVE_FILE', fileId)
      return res
    },
    async fetchProjectContext({ commit }, projectId) {
      const res = await getProjectContext(projectId)
      if (res.code === 200) commit('SET_PROJECT_CONTEXT', res.data)
      return res
    },

    // ── 迭代 ──
    async fetchIterations({ commit }, projectId) {
      const res = await getIterations(projectId)
      if (res.code === 200) commit('SET_ITERATIONS', res.data.items || [])
      return res
    },
    async fetchIteration({ commit }, id) {
      const res = await getIteration(id)
      if (res.code === 200) commit('SET_CURRENT_ITERATION', res.data)
      return res
    },
    async createIteration({ commit }, { projectId, data }) {
      const res = await createIteration(projectId, data)
      if (res.code === 201) commit('ADD_ITERATION', res.data)
      return res
    },
    async updateIteration({ commit }, { id, data }) {
      const res = await updateIteration(id, data)
      if (res.code === 200) commit('UPDATE_ITERATION', res.data)
      return res
    },
    async deleteIteration({ commit }, id) {
      const res = await deleteIteration(id)
      if (res.code === 200) commit('REMOVE_ITERATION', id)
      return res
    },

    // ── 需求 ──
    async fetchRequirements({ commit }, { projectId, params = {} }) {
      const res = await getRequirements(projectId, params)
      if (res.code === 200) commit('SET_REQUIREMENTS', res.data.items || [])
      return res
    },
    async fetchRequirement({ commit }, id) {
      const res = await getRequirement(id)
      if (res.code === 200) commit('SET_CURRENT_REQUIREMENT', res.data)
      return res
    },
    async createRequirement({ commit }, { projectId, data }) {
      const res = await createRequirement(projectId, data)
      if (res.code === 201) commit('ADD_REQUIREMENT', res.data)
      return res
    },
    async updateRequirement({ commit }, { id, data }) {
      const res = await updateRequirement(id, data)
      if (res.code === 200) commit('UPDATE_REQUIREMENT', res.data)
      return res
    },
    async deleteRequirement({ commit }, id) {
      const res = await deleteRequirement(id)
      if (res.code === 200) commit('REMOVE_REQUIREMENT', id)
      return res
    },
    async updateRequirementStatus({ commit }, { id, status }) {
      const res = await updateRequirementStatus(id, status)
      if (res.code === 200) commit('UPDATE_REQUIREMENT', res.data)
      return res
    },

    // ── Bug ──
    async fetchBugs({ commit }, { projectId, params = {} }) {
      const res = await getBugs(projectId, params)
      if (res.code === 200) commit('SET_BUGS', res.data.items || [])
      return res
    },
    async fetchBug({ commit }, id) {
      const res = await getBug(id)
      if (res.code === 200) commit('SET_CURRENT_BUG', res.data)
      return res
    },
    async createBug({ commit }, { projectId, data }) {
      const res = await createBug(projectId, data)
      if (res.code === 201) commit('ADD_BUG', res.data)
      return res
    },
    async updateBug({ commit }, { id, data }) {
      const res = await updateBug(id, data)
      if (res.code === 200) commit('UPDATE_BUG', res.data)
      return res
    },
    async deleteBug({ commit }, id) {
      const res = await deleteBug(id)
      if (res.code === 200) commit('REMOVE_BUG', id)
      return res
    },

    // ── 仓库 ──
    async fetchRepos({ commit }, projectId) {
      const res = await getRepos(projectId)
      if (res.code === 200) commit('SET_REPOS', res.data.items || [])
      return res
    },
    async fetchRepo({ commit }, id) {
      const res = await getRepo(id)
      if (res.code === 200) commit('SET_CURRENT_REPO', res.data)
      return res
    },

    // ── 审查 ──
    async fetchReviews({ commit }, { projectId, params = {} }) {
      const res = await getReviews(projectId, params)
      if (res.code === 200) commit('SET_REVIEWS', res.data.items || [])
      return res
    },
    async fetchReview({ commit }, id) {
      const res = await getReview(id)
      if (res.code === 200) commit('SET_CURRENT_REVIEW', res.data)
      return res
    },
    async createReview({ commit }, { projectId, data }) {
      const res = await createReview(projectId, data)
      if (res.code === 201) commit('ADD_REVIEW', res.data)
      return res
    },
    async deleteReview({ commit }, id) {
      const res = await deleteReview(id)
      if (res.code === 200) commit('REMOVE_REVIEW', id)
      return res
    },

    // ── 构建 ──
    async fetchBuilds({ commit }, { projectId, params = {} }) {
      const res = await getBuilds(projectId, params)
      if (res.code === 200) commit('SET_BUILDS', res.data.items || [])
      return res
    },
    async fetchBuild({ commit }, id) {
      const res = await getBuild(id)
      if (res.code === 200) commit('SET_CURRENT_BUILD', res.data)
      return res
    },

    // ── 评论 ──
    async fetchComments({ commit }, { projectId, params = {} }) {
      const res = await getComments(projectId, params)
      if (res.code === 200) commit('SET_COMMENTS', res.data.items || [])
      return res
    },
    async addComment({ commit }, { projectId, data }) {
      const res = await createComment(projectId, data)
      if (res.code === 201) commit('ADD_COMMENT', res.data)
      return res
    },
    async removeComment({ commit }, { projectId, commentId }) {
      const res = await deleteComment(projectId, commentId)
      if (res.code === 200) commit('REMOVE_COMMENT', commentId)
      return res
    },

    // ── 成员 ──
    async fetchMembers({ commit }, projectId) {
      const res = await getMembers(projectId)
      if (res.code === 200) commit('SET_MEMBERS', res.data.items || [])
      return res
    },
    async addMember({ commit }, { projectId, data }) {
      const res = await addMember(projectId, data)
      if (res.code === 201) commit('ADD_MEMBER', res.data)
      return res
    },
    async updateMemberRole({ commit }, { projectId, userId, role }) {
      const res = await updateMemberRole(projectId, userId, role)
      if (res.code === 200) {
        // Re-fetch members to get updated data
        const membersRes = await getMembers(projectId)
        if (membersRes.code === 200) commit('SET_MEMBERS', membersRes.data.items || [])
      }
      return res
    },
    async removeMember({ commit }, { projectId, memberId }) {
      const res = await removeMember(projectId, memberId)
      if (res.code === 200) commit('REMOVE_MEMBER', memberId)
      return res
    },

    // ── 活动日志 ──
    async fetchActivities({ commit }, { projectId, params = {} }) {
      const res = await getActivities(projectId, params)
      if (res.code === 200) {
        commit('SET_ACTIVITIES', { items: res.data.items || [], total: res.data.total || 0 })
      }
      return res
    },

    // ── 甘特图 ──
    async fetchGanttData({ commit }, projectId) {
      const res = await getGanttData(projectId)
      if (res.code === 200) commit('SET_GANTT_DATA', res.data)
      return res
    },

    // ── 分支 ──
    async fetchBranches({ commit }, { projectId, params = {} }) {
      const res = await getProjectBranches(projectId, params)
      if (res.code === 200) commit('SET_BRANCHES', res.data.items || [])
      return res
    },
    async createBranch({ commit }, { projectId, data }) {
      const res = await createBranch(projectId, data)
      if (res.code === 201) commit('SET_BRANCHES', [...this.state.rd.branches, res.data])
      return res
    },
  },
}
