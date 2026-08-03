<template>
  <div class="github-callback-loading">
    <i class="el-icon-loading"></i>
    <p>正在完成 GitHub 授权...</p>
  </div>
</template>

<script>
import * as rdApi from '@/api/rd'

export default {
  name: 'GithubCallback',
  async created() {
    const query = this.$route.query
    const accessToken = query.access_token
    const state = query.state || ''
    const githubUser = query.github_user || ''

    if (!accessToken) {
      this.$message.error('授权失败：缺少 token')
      this.goBack(state)
      return
    }

    try {
      await rdApi.saveGithubToken({
        access_token: accessToken,
        token_type: query.token_type || 'bearer',
        scope: query.scope || '',
        github_user: githubUser,
        github_id: query.github_id || '',
      })
      this.$message.success(`GitHub 授权成功，已连接 ${githubUser}`)
    } catch (e) {
      this.$message.error('保存授权信息失败')
    }

    this.goBack(state)
  },
  methods: {
    goBack(state) {
      // state 参数包含项目 ID
      if (state) {
        this.$router.push('/projects/' + state)
      } else {
        this.$router.push('/projects')
      }
    },
  },
}
</script>

<style scoped>
.github-callback-loading {
  text-align: center;
  padding: 80px;
  color: #909399;
}
.github-callback-loading i {
  font-size: 36px;
  display: block;
  margin-bottom: 16px;
}
</style>
