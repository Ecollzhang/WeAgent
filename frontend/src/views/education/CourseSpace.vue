<template>
  <EducationShell
    :title="course ? course.title : '教学空间'"
    :subtitle="courseSubtitle"
    back-to="/education"
  >
    <template #actions>
      <div v-if="isTeacher" class="teacher-actions-grid">
        <el-button icon="el-icon-edit" @click="displayNameDialog = true">修改课程姓名</el-button>
        <el-button
        data-testid="create-invitation-open"
        icon="el-icon-user"
        @click="createInvitation"
      >邀请学生</el-button>
        <el-button
        data-testid="create-lesson-open"
        icon="el-icon-circle-plus-outline"
        @click="openLessonDialog"
      >新建课时</el-button>
        <el-button
        data-testid="create-assignment-open"
        type="primary"
        icon="el-icon-edit-outline"
        @click="assignmentDialog = true"
      >发布作业</el-button>
      </div>
    </template>

    <el-skeleton v-if="!course" :rows="8" animated />
    <template v-else>
      <EmbeddedAgentRecord
        title="AI 生成记录"
        v-if="isTeacher"
        :run="productAgentRun"
        @terminal="handleRosterAgentTerminal"
        @poll-error="$message.error('Agent 运行状态暂时无法刷新')"
        @close="closeAgentRun"
      />

      <nav class="course-tabs" aria-label="课程模块">
        <button
          v-for="tab in visibleTabs"
          :key="tab.key"
          type="button"
          :class="{ active: activeTab === tab.key }"
          :data-testid="`course-tab-${tab.key}`"
          @click="selectCourseTab(tab)"
        >
          <i :class="tab.icon"></i>{{ tab.label }}
        </button>
      </nav>

      <section v-if="activeTab === 'lessons' || activeTab === 'materials'" class="panel">
        <div class="section-heading">
          <div>
            <h2>{{ isTeacher ? '课时与教案' : '课件与学习材料' }}</h2>
            <p>{{ isTeacher ? '按单元组织课时，编辑教案后发布稳定版本。' : '下载教师发布的课件与材料，按课时进入学习。' }}</p>
          </div>
        </div>
        <div
          v-if="!isTeacher && assets.length"
          class="published-assets"
          data-testid="student-published-assets"
        >
          <article v-for="asset in assets" :key="asset.id">
            <span class="asset-icon"><i class="el-icon-document"></i></span>
            <div>
              <b>{{ asset.title }}</b>
              <small>{{ asset.original_filename }} · {{ sizeLabel(asset.byte_size) }}</small>
            </div>
            <el-button
              size="mini"
              icon="el-icon-download"
              @click="downloadPublishedAsset(asset)"
            >下载</el-button>
          </article>
        </div>
        <div v-if="flatLessons.length" class="lesson-list" data-testid="course-lesson-list">
          <button
            v-for="lesson in flatLessons"
            :key="lesson.id"
            type="button"
            class="lesson-row"
            :data-testid="`lesson-${lesson.id}`"
            @click="openLesson(lesson)"
          >
            <span class="lesson-index">{{ lesson.sequence || '•' }}</span>
            <span>
              <b>{{ lesson.title }}</b>
              <small>{{ lesson.lesson_type_code || '阅读与写作' }}</small>
            </span>
            <el-tag size="mini" :type="lesson.status === 'published' ? 'success' : 'info'">
              {{ lesson.status === 'published' ? '已发布' : '草稿' }}
            </el-tag>
            <i class="el-icon-arrow-right"></i>
          </button>
        </div>
        <div v-else class="small-empty">
          <i class="el-icon-notebook-2"></i>
          <p>{{ isTeacher ? '还没有课时。创建第一个课时后即可编写教案、制作课件和发布作业。' : '教师尚未发布学习内容。' }}</p>
          <el-button
            v-if="isTeacher"
            data-testid="create-first-lesson"
            type="primary"
            plain
            @click="openLessonDialog"
          >创建第一个课时</el-button>
        </div>
      </section>

      <section v-if="activeTab === 'weaknesses' && !isTeacher" class="panel">
        <div class="section-heading">
          <div>
            <h2>作业弱点</h2>
            <p>只根据已提交作业和考试证据定位错因，不根据聊天内容猜测能力。</p>
          </div>
          <el-button
            icon="el-icon-refresh"
            :loading="weaknessLoading"
            @click="refreshStudentWeakness"
          >刷新证据</el-button>
        </div>
        <div v-if="weaknessReady" class="weakness-summary" data-testid="student-weakness-summary">
          <article
            v-for="(item, index) in weaknessItems"
            :key="item.knowledge_point"
          >
            <span>{{ String(index + 1).padStart(2, '0') }}</span>
            <div>
              <b>{{ item.knowledge_point }}</b>
              <small>尝试 {{ item.attempted_count }} 次 · 错误 {{ item.wrong_count }} 次</small>
            </div>
            <strong>{{ Math.round(item.error_rate * 100) }}%</strong>
          </article>
          <div v-if="!weaknessItems.length" class="all-clear">
            <i class="el-icon-circle-check"></i>
            <span><b>当前没有错误聚集</b><small>继续完成作业，证据会自动更新。</small></span>
          </div>
        </div>
        <div v-else class="small-empty">
          <i class="el-icon-data-analysis"></i>
          <p>完成至少一份作业或模拟考试后，这里会形成带证据的弱点分析。</p>
          <el-button
            type="primary"
            plain
            @click="$router.push({ path: '/education/student/mock-exams', query: { courseId } })"
          >去完成模拟考试</el-button>
        </div>
      </section>

      <section v-if="activeTab === 'assignments'" class="panel">
        <div class="section-heading">
          <div><h2>阅读与写作作业</h2><p>提交、自动反馈和教师复核都保留版本记录。</p></div>
        </div>
        <div class="assignment-grid" data-testid="course-assignment-list">
          <article
            v-for="assignment in assignments"
            :key="assignment.id"
            class="assignment-card"
            @click="openAssignment(assignment)"
          >
            <div>
              <el-tag size="mini">{{ assignment.kind || assignment.assignment_type || '综合任务' }}</el-tag>
              <span>{{ dueLabel(assignment.due_at) }}</span>
            </div>
            <h3>{{ assignment.title }}</h3>
            <p class="assignment-card-body">{{ instructionText(assignment) }}</p>
            <footer>
              <span>{{ statusLabel(assignment.status) }}</span>
              <b>{{ isTeacher ? '查看提交' : '开始作答' }} <i class="el-icon-right"></i></b>
            </footer>
          </article>
          <div v-if="!assignments.length" class="small-empty">
            <i class="el-icon-edit-outline"></i>
            <p>{{ isTeacher ? '尚未发布作业。' : '暂时没有待完成作业。' }}</p>
          </div>
        </div>
      </section>

      <section v-if="activeTab === 'people' && isTeacher" class="panel">
        <div class="section-heading">
          <div>
            <h2>课程成员</h2>
            <p>显示课程姓名；教师和学生都可用页面顶部“修改课程姓名”单独设置。</p>
          </div>
          <div class="member-actions">
            <el-button
              data-testid="agent-roster-import"
              icon="el-icon-cpu"
              :loading="rosterAgentRunning"
              @click="rosterDialog = true"
            >Agent 导入名单</el-button>
            <el-button icon="el-icon-edit" @click="displayNameDialog = true">修改我的姓名</el-button>
          </div>
        </div>
        <el-table :data="members" stripe data-testid="course-member-list">
          <el-table-column prop="display_name" label="姓名" min-width="150" />
          <el-table-column label="身份" width="110">
            <template #default="{ row }">{{ row.role === 'teacher' ? '教师' : '学生' }}</template>
          </el-table-column>
          <el-table-column label="账户标识" min-width="180">
            <template #default="{ row }">
              <span class="account-key">{{ row.user_id }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="joined_at" label="加入时间" min-width="180" />
          <el-table-column prop="status" label="状态" width="100" />
        </el-table>
      </section>

      <section v-if="activeTab === 'analytics' && isTeacher" class="panel">
        <div class="section-heading"><div><h2>学习数据桥</h2><p>学生学习和提交事件回流形成班级学情。</p></div></div>
        <div class="metric-grid" data-testid="course-analytics">
          <div><span>学生</span><b>{{ metric('active_students') }}</b></div>
          <div><span>完成率</span><b>{{ percentMetric('completion_rate') }}</b></div>
          <div><span>已发布作业</span><b>{{ metric('published_assignments') }}</b></div>
          <div><span>平均分</span><b>{{ metric('average_score') }}</b></div>
        </div>
        <div class="analytics-note">
          <i class="el-icon-data-analysis"></i>
          <span>{{ analytics && analytics.summary ? analytics.summary : '完成真实提交与反馈后，这里将显示常见错因和教学建议。' }}</span>
        </div>
      </section>
    </template>

    <el-dialog title="新建课时" :visible.sync="lessonDialog" width="680px">
      <el-form label-position="top">
        <div class="form-grid">
          <el-form-item label="所属单元">
            <el-select v-model="lessonForm.unit_id" style="width:100%">
              <el-option label="新建单元" value="__new__" />
              <el-option
                v-for="unit in units"
                :key="unit.id"
                :label="unit.title"
                :value="unit.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item v-if="lessonForm.unit_id === '__new__'" label="新单元名称">
            <el-input
              v-model.trim="lessonForm.unit_title"
              maxlength="100"
              placeholder="例如：第一单元 · 成长与选择"
            />
          </el-form-item>
          <el-form-item v-else label="课时顺序">
            <el-input-number
              v-model="lessonForm.position"
              :min="1"
              :max="200"
              style="width:100%"
            />
          </el-form-item>
        </div>
        <el-form-item label="课时名称">
          <el-input
            v-model.trim="lessonForm.title"
            data-testid="lesson-title"
            maxlength="120"
            placeholder="例如：A Turning Point · 叙事阅读与续写"
          />
        </el-form-item>
        <div class="form-grid form-grid-three">
          <el-form-item label="学习领域">
            <el-select v-model="lessonForm.learning_domain" style="width:100%">
              <el-option label="阅读与写作整合" value="integrated" />
              <el-option label="阅读" value="reading" />
              <el-option label="写作" value="writing" />
            </el-select>
          </el-form-item>
          <el-form-item label="课文类型">
            <el-select v-model="lessonForm.text_genre_code" style="width:100%">
              <el-option
                v-for="genre in genreOptions"
                :key="genre.value"
                :label="genre.label"
                :value="genre.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="课时分钟">
            <el-input-number
              v-model="lessonForm.duration_minutes"
              :min="5"
              :max="180"
              :step="5"
              style="width:100%"
            />
          </el-form-item>
        </div>
        <el-form-item label="主题标签（可选）">
          <el-input
            v-model.trim="lessonForm.theme_code"
            maxlength="80"
            placeholder="例如：growth_and_choices"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="lessonDialog = false">取消</el-button>
        <el-button
          data-testid="create-lesson-submit"
          type="primary"
          :loading="$store.getters['education/saving']"
          :disabled="!canCreateLesson"
          @click="handleCreateLesson"
        >创建并编写教案</el-button>
      </template>
    </el-dialog>

    <el-dialog title="发布作业" :visible.sync="assignmentDialog" width="720px" custom-class="education-dialog education-dialog--editor">
      <el-form label-position="top">
        <el-form-item label="从文件开始（可选）">
          <div class="assignment-import-row">
            <el-radio-group v-model="assignmentImportMode" size="small">
              <el-radio-button label="attachment">附件发布</el-radio-button>
              <el-radio-button label="editable">识别为可编辑作业</el-radio-button>
            </el-radio-group>
            <el-upload
              data-testid="assignment-import-upload"
              action=""
              accept=".pdf,.png,.jpg,.jpeg"
              :auto-upload="false"
              :show-file-list="false"
              :disabled="assignmentImportLoading"
              :on-change="handleAssignmentSource"
            >
              <el-button
                size="small"
                icon="el-icon-upload2"
                :loading="assignmentImportLoading"
              >选择 PDF 或照片</el-button>
            </el-upload>
          </div>
          <el-alert
            v-if="assignmentImportStatus"
            class="assignment-import-status"
            :title="assignmentImportStatus"
            :type="assignmentImportError ? 'error' : 'success'"
            :closable="false"
            show-icon
          />
          <p class="dialog-help">
            “附件发布”保留原文件；“识别为可编辑作业”会先提取 PDF 正文或调用开源 OCR，结果仍需教师确认。
          </p>
        </el-form-item>
        <el-form-item label="作业名称">
          <el-input v-model.trim="assignmentForm.title" data-testid="assignment-title" />
        </el-form-item>
        <el-form-item label="作业要求">
          <el-input v-model="assignmentForm.instructions" type="textarea" :rows="6" />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="所属课时">
            <el-select v-model="assignmentForm.lesson_id" style="width:100%" placeholder="选择课时">
              <el-option
                v-for="lesson in flatLessons"
                :key="lesson.id"
                :label="lesson.title"
                :value="lesson.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="任务侧重">
            <el-select v-model="assignmentForm.kind" style="width:100%">
              <el-option label="阅读练习" value="quiz" />
              <el-option label="写作" value="writing" />
              <el-option label="阅读 + 写作" value="mixed" />
            </el-select>
          </el-form-item>
          <el-form-item label="评分方式">
            <div class="fixed-score-card">
              <b>百分制总分 100</b>
              <span>不拆分评分子项；AI 只提供建议，最终分数由教师确认。</span>
            </div>
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="assignmentDialog = false">取消</el-button>
        <el-button
          data-testid="create-assignment-submit"
          type="primary"
          :disabled="!assignmentForm.title || !assignmentForm.lesson_id"
          @click="handleCreateAssignment"
        >保存作业</el-button>
      </template>
    </el-dialog>

    <el-dialog
      title="邀请学生"
      :visible.sync="invitationDialog"
      width="560px"
      @closed="invitationToken = ''"
    >
      <p class="dialog-help">将下面的邀请码发送给学生。学生登录自己的账户后，在“教学空间”中使用邀请码加入。</p>
      <el-input
        v-model="invitationToken"
        data-testid="invitation-token"
        readonly
      >
        <el-button
          slot="append"
          data-testid="copy-invitation-token"
          icon="el-icon-document-copy"
          @click="copyInvitation"
        >一键复制</el-button>
      </el-input>
      <template #footer>
        <el-button type="primary" @click="invitationDialog = false">完成</el-button>
      </template>
    </el-dialog>
    <el-dialog title="修改课程姓名" :visible.sync="displayNameDialog" width="420px">
      <p class="name-help">该姓名只用于本课程成员列表，不会改变登录用户名。</p>
      <el-input
        v-model.trim="displayName"
        maxlength="80"
        show-word-limit
        placeholder="例如：王老师、林同学"
      />
      <template #footer>
        <el-button @click="displayNameDialog = false">取消</el-button>
        <el-button type="primary" :disabled="!displayName" @click="saveDisplayName">
          保存
        </el-button>
      </template>
    </el-dialog>
    <el-dialog title="Agent 导入学生名单" :visible.sync="rosterDialog" width="620px">
      <el-alert
        title="每行填写一个现有 WeAgent 账号，可在逗号后附课程姓名。Agent 会核对现有成员后调用受控导入工具，不会创建登录账号。"
        type="info"
        :closable="false"
        show-icon
      />
      <el-input
        v-model="rosterText"
        class="roster-editor"
        type="textarea"
        :rows="12"
        maxlength="12000"
        show-word-limit
        placeholder="student_001,林同学&#10;student_002,周同学"
      />
      <template #footer>
        <el-button @click="rosterDialog = false">取消</el-button>
        <el-button
          type="primary"
          :loading="rosterAgentRunning"
          :disabled="!rosterText.trim()"
          @click="startRosterAgent"
        >启动名单 Agent</el-button>
      </template>
    </el-dialog>
  </EducationShell>
</template>

<script>
import EducationShell from '../../components/education/EducationShell.vue'
import EmbeddedAgentRecord from '../../components/education/EmbeddedAgentRecord.vue'

export default {
  name: 'EducationCourseSpace',
  components: { EducationShell, EmbeddedAgentRecord },
  data() {
    return {
      activeTab: 'lessons',
      weaknessLoading: false,
      lessonDialog: false,
      assignmentDialog: false,
      invitationDialog: false,
      displayNameDialog: false,
      rosterDialog: false,
      rosterText: '',
      displayName: '',
      invitationToken: '',
      assignmentImportMode: 'attachment',
      assignmentImportLoading: false,
      assignmentImportStatus: '',
      assignmentImportError: false,
      lessonForm: {
        unit_id: '__new__',
        unit_title: '第一单元',
        title: '',
        learning_domain: 'integrated',
        text_genre_code: 'narrative',
        theme_code: '',
        duration_minutes: 45,
        position: 1,
      },
      assignmentForm: {
        title: '',
        instructions: '',
        kind: 'mixed',
        lesson_id: '',
        max_score: 100,
        source_asset_ids: [],
      },
    }
  },
  computed: {
    courseId() { return this.$route.params.courseId },
    course() { return this.$store.getters['education/activeCourse'] },
    membershipRole() { return this.$store.getters['education/membershipRole'] },
    isTeacher() { return this.$store.getters['education/isTeacher'] },
    units() { return this.$store.getters['education/units'] || [] },
    assignments() { return this.$store.getters['education/assignments'] || [] },
    members() { return this.$store.getters['education/members'] || [] },
    analytics() { return this.$store.getters['education/analytics'] || {} },
    productAgentRun() { return this.$store.getters['education/productAgentRun'] },
    assets() {
      return (this.$store.getters['education/assets'] || [])
        .filter(asset => ['courseware', 'lesson_material'].includes(asset.purpose))
    },
    weakness() { return this.$store.getters['education/weakness'] || {} },
    weaknessReady() { return this.weakness.data_state === 'ready' },
    weaknessItems() { return this.weakness.weaknesses || [] },
    rosterAgentRunning() {
      return Boolean(
        this.productAgentRun
        && this.productAgentRun.product_code === 'roster_import'
        && ['pending', 'running'].includes(this.productAgentRun.status)
      )
    },
    tabs() {
      if (!this.isTeacher) {
        return [
          { key: 'materials', label: '课件与材料', icon: 'el-icon-reading' },
          { key: 'assignments', label: '完成作业', icon: 'el-icon-edit-outline' },
          { key: 'weaknesses', label: '作业弱点', icon: 'el-icon-data-analysis' },
        ]
      }
      return [
        { key: 'lessons', label: '课时', icon: 'el-icon-reading' },
        { key: 'assignments', label: '作业', icon: 'el-icon-edit-outline' },
        { key: 'people', label: '成员', icon: 'el-icon-user' },
        { key: 'analytics', label: '学情', icon: 'el-icon-data-analysis' },
        { key: 'knowledge', label: '知识中心', icon: 'el-icon-collection' },
      ]
    },
    visibleTabs() { return this.tabs },
    genreOptions() {
      if (this.course && this.course.subject_code === 'primary_chinese') {
        return [
          { value: 'narrative', label: '记叙文' },
          { value: 'scenery', label: '写景文' },
          { value: 'expository', label: '说明文' },
          { value: 'fairy_tale', label: '童话' },
          { value: 'fable', label: '寓言' },
          { value: 'poetry', label: '现代诗' },
          { value: 'ancient_poetry', label: '古诗文' },
          { value: 'practical', label: '实用类文本' },
          { value: 'composition', label: '习作' },
        ]
      }
      return [
        { value: 'narrative', label: 'Narrative · 叙事' },
        { value: 'expository', label: 'Expository · 说明' },
        { value: 'argumentative', label: 'Argumentative · 议论' },
        { value: 'practical', label: 'Practical · 应用' },
        { value: 'news', label: 'News · 新闻' },
        { value: 'biography', label: 'Biography · 传记' },
        { value: 'literary', label: 'Literary · 文学' },
      ]
    },
    canCreateLesson() {
      return Boolean(
        this.lessonForm.title
        && this.lessonForm.text_genre_code
        && this.lessonForm.duration_minutes
        && (
          this.lessonForm.unit_id !== '__new__'
          || this.lessonForm.unit_title
        )
      )
    },
    flatLessons() {
      return this.units.reduce((all, unit) => {
        const lessons = unit.lessons || []
        return all.concat(lessons.map(lesson => ({ ...lesson, unit_title: unit.title })))
      }, [])
    },
    courseSubtitle() {
      if (!this.course) return '正在核验课程成员身份'
      const subject = this.course.subject_code === 'primary_chinese' ? '小学语文' : '高中英语'
      return `${subject} · 阅读与写作 · ${this.isTeacher ? '教学管理' : '个性化学习'}`
    },
  },
  async created() {
    try {
      await this.$store.dispatch('education/selectCourse', this.courseId)
      await this.$store.dispatch('education/fetchCourseOverview', this.courseId)
      if (this.isTeacher) {
        await this.$store.dispatch('education/restoreProductAgentRun', {
          courseId: this.courseId,
        })
      } else {
        this.activeTab = ['materials', 'assignments', 'weaknesses'].includes(this.$route.query.tab)
          ? this.$route.query.tab
          : 'materials'
        await Promise.all([
          this.$store.dispatch('education/fetchAssets', this.courseId),
          this.$store.dispatch('education/fetchWeakness', this.courseId),
        ])
      }
    } catch (error) {
      this.$message.error('无法访问该课程，请确认你仍是课程成员')
      this.$router.replace('/education')
    }
  },
  methods: {
    selectCourseTab(tab) {
      if (tab.key === 'knowledge') {
        this.$router.push(`/education/courses/${this.course.id}/knowledge`)
        return
      }
      this.activeTab = tab.key
    },
    openLessonDialog() {
      const firstUnit = this.units[0]
      this.lessonForm = {
        unit_id: firstUnit ? firstUnit.id : '__new__',
        unit_title: '第一单元',
        title: '',
        learning_domain: 'integrated',
        text_genre_code: this.course && this.course.subject_code === 'primary_chinese'
          ? 'fable'
          : 'narrative',
        theme_code: '',
        duration_minutes: 45,
        position: this.flatLessons.length + 1,
      }
      this.lessonDialog = true
    },
    async handleCreateLesson() {
      const domain = this.lessonForm.learning_domain
      try {
        const lesson = await this.$store.dispatch('education/createLesson', {
          courseId: this.courseId,
          unitId: this.lessonForm.unit_id === '__new__' ? '' : this.lessonForm.unit_id,
          unitTitle: this.lessonForm.unit_title,
          lesson: {
            title: this.lessonForm.title,
            learning_domain: domain,
            theme_code: this.lessonForm.theme_code,
            text_genre_code: this.lessonForm.text_genre_code,
            lesson_type_code: domain === 'integrated' ? 'reading_writing' : domain,
            duration_minutes: this.lessonForm.duration_minutes,
            position: this.lessonForm.position,
          },
        })
        this.lessonDialog = false
        this.$message.success('课时已创建，可以开始编写教案')
        this.openLesson(lesson)
      } catch (error) {
        const detail = error.response && error.response.data && error.response.data.error
        this.$message.error(detail || '课时创建失败')
      }
    },
    async saveDisplayName() {
      try {
        await this.$store.dispatch('education/updateMyDisplayName', {
          courseId: this.courseId,
          displayName: this.displayName,
        })
        this.displayNameDialog = false
        this.$message.success('课程姓名已更新')
      } catch (error) {
        this.$message.error('课程姓名更新失败')
      }
    },
    openLesson(lesson) {
      this.$router.push(`/education/courses/${this.courseId}/lessons/${lesson.id}`)
    },
    openAssignment(assignment) {
      this.$router.push(`/education/courses/${this.courseId}/assignments/${assignment.id}`)
    },
    async createInvitation() {
      try {
        const invitation = await this.$store.dispatch('education/createInvitation', {
          courseId: this.courseId,
          limits: { max_uses: 30, expires_in_hours: 168 },
        })
        this.invitationToken = invitation.token
        this.invitationDialog = true
      } catch (error) {
        this.$message.error('邀请码创建失败')
      }
    },
    async copyInvitation() {
      if (!this.invitationToken) return
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(this.invitationToken)
        } else {
          const textarea = document.createElement('textarea')
          textarea.value = this.invitationToken
          textarea.setAttribute('readonly', '')
          textarea.style.position = 'fixed'
          textarea.style.opacity = '0'
          document.body.appendChild(textarea)
          textarea.select()
          const copied = document.execCommand('copy')
          document.body.removeChild(textarea)
          if (!copied) throw new Error('copy command was rejected')
        }
        this.$message.success('邀请码已复制')
      } catch (error) {
        this.$message.warning('自动复制失败，请手动选择邀请码复制')
      }
    },
    async downloadPublishedAsset(asset) {
      try {
        const blob = await this.$store.dispatch('education/downloadAsset', asset)
        const objectUrl = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = objectUrl
        link.download = asset.original_filename || asset.title
        link.click()
        URL.revokeObjectURL(objectUrl)
      } catch (error) {
        this.$message.error('文件下载失败')
      }
    },
    async refreshStudentWeakness() {
      if (this.weaknessLoading) return
      this.weaknessLoading = true
      try {
        await this.$store.dispatch('education/refreshWeakness', this.courseId)
        this.$message.success('弱点证据已更新')
      } catch (error) {
        this.$message.error('弱点证据刷新失败')
      } finally {
        this.weaknessLoading = false
      }
    },
    async handleCreateAssignment() {
      try {
        await this.$store.dispatch('education/createAssignment', {
          courseId: this.courseId,
          lessonId: this.assignmentForm.lesson_id,
          assignment: {
            title: this.assignmentForm.title,
            kind: this.assignmentForm.kind,
            max_score: 100,
            instruction_json: { text: this.assignmentForm.instructions },
            evaluation_json: {},
            source_asset_ids: this.assignmentForm.source_asset_ids,
            max_attempts: 3,
            allow_revision_after_feedback: true,
          },
        })
        this.assignmentDialog = false
        this.assignmentForm = {
          title: '',
          instructions: '',
          kind: 'mixed',
          lesson_id: '',
          max_score: 100,
          source_asset_ids: [],
        }
        this.assignmentImportMode = 'attachment'
        this.assignmentImportStatus = ''
        this.assignmentImportError = false
        this.$message.success('作业草稿已保存')
      } catch (error) {
        this.$message.error('作业保存失败')
      }
    },
    async handleAssignmentSource(file) {
      if (!file || !file.raw) return
      if (!this.assignmentForm.lesson_id) {
        this.$message.warning('请先选择所属课时，再上传作业文件')
        return
      }
      this.assignmentImportLoading = true
      this.assignmentImportError = false
      this.assignmentImportStatus = '正在上传文件…'
      const formData = new FormData()
      formData.append('file', file.raw)
      formData.append('lesson_id', this.assignmentForm.lesson_id)
      formData.append('mode', this.assignmentImportMode)
      try {
        let job = await this.$store.dispatch('education/uploadAssignmentSource', {
          courseId: this.courseId,
          formData,
        })
        if (this.assignmentImportMode === 'editable') {
          this.assignmentImportStatus = '上传成功，正在提取文字…'
          job = await this.$store.dispatch('education/processAssignmentImport', job.id)
        }
        const draft = job.draft_json || {}
        this.assignmentForm.title = this.assignmentForm.title || draft.title || ''
        this.assignmentForm.instructions = (
          draft.instruction_json && draft.instruction_json.text
        ) || this.assignmentForm.instructions
        this.assignmentForm.source_asset_ids = draft.source_asset_ids
          || (job.source_asset ? [job.source_asset.id] : [])
        this.assignmentImportStatus = this.assignmentImportMode === 'editable'
          ? '文字已提取，请检查并编辑作业要求'
          : '附件已上传，将随作业发布给学生'
      } catch (error) {
        const data = error.response && error.response.data
        this.assignmentImportError = true
        this.assignmentImportStatus = (data && (data.error_summary || data.error))
          || '文件导入失败，请检查格式后重试'
      } finally {
        this.assignmentImportLoading = false
      }
    },
    parseRoster() {
      const rows = this.rosterText
        .split(/\r?\n/)
        .map(line => line.trim())
        .filter(Boolean)
      if (!rows.length || rows.length > 100) {
        throw new Error('名单需包含 1 到 100 行')
      }
      const seen = new Set()
      return rows.map((line, index) => {
        const parts = line.split(/[\t,，]/)
        const userId = String(parts.shift() || '').trim()
        const displayName = parts.join(' ').trim()
        if (!userId || userId.length > 100 || seen.has(userId)) {
          throw new Error(`第 ${index + 1} 行账号为空、过长或重复`)
        }
        if (displayName.length > 80) {
          throw new Error(`第 ${index + 1} 行课程姓名超过 80 个字符`)
        }
        seen.add(userId)
        return { user_id: userId, display_name: displayName }
      })
    },
    async startRosterAgent() {
      let members
      try {
        members = this.parseRoster()
      } catch (error) {
        this.$message.error(error.message)
        return
      }
      try {
        await this.$store.dispatch('education/startProductAgentRun', {
          course_id: this.courseId,
          product_code: 'roster_import',
          options: { members },
        })
        this.rosterDialog = false
        this.$message.success('名单导入 Agent 已启动')
      } catch (error) {
        const detail = error.response && error.response.data && error.response.data.error
        this.$message.error(detail || '名单 Agent 启动失败')
      }
    },
    async handleRosterAgentTerminal(run) {
      if (run.status === 'completed') {
        await this.$store.dispatch('education/fetchCourseOverview', this.courseId)
        this.$message.success('Agent 名单导入已完成，成员列表已刷新')
      }
    },
    closeAgentRun() {
      this.$store.commit('education/SET_PRODUCT_AGENT_RUN', null)
    },
    dueLabel(value) {
      return value ? `截止 ${new Date(value).toLocaleString()}` : '长期有效'
    },
    statusLabel(value) {
      const labels = { draft: '草稿', published: '进行中', closed: '已截止', archived: '已归档' }
      return labels[value] || value || '待发布'
    },
    instructionText(assignment) {
      const value = assignment.instruction_json
      if (typeof value === 'string') return value
      return (value && (value.text || value.instructions)) || '查看作业要求与评价标准'
    },
    metric(key) {
      const value = this.analytics[key]
      return value === undefined || value === null ? '—' : value
    },
    percentMetric(key) {
      const value = this.analytics[key]
      if (value === undefined || value === null) return '—'
      return `${Math.round(value <= 1 ? value * 100 : value)}%`
    },
    sizeLabel(value) {
      const size = Number(value || 0)
      if (size < 1024) return `${size} B`
      if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
      return `${(size / 1024 / 1024).toFixed(1)} MB`
    },
  },
}
</script>

<style scoped>
.teacher-actions-grid { display: grid; grid-template-columns: repeat(2, minmax(132px, 1fr)); gap: 8px; }
.teacher-actions-grid :deep(.el-button) { width: 100%; margin: 0; justify-content: center; }
.course-tabs {
  display: flex; gap: 5px; margin-bottom: 18px; padding: 5px;
  border: 1px solid #e5ebf0; border-radius: 11px; background: #f6f9fb;
}
.course-tabs button {
  padding: 10px 18px; border: 0; border-radius: 8px; background: transparent;
  color: #667386; cursor: pointer; font-size: 13px;
}
.course-tabs button i { margin-right: 7px; }
.course-tabs button.active { background: #fff; color: #27887e; font-weight: 700; box-shadow: 0 2px 8px rgba(31,41,55,.07); }
.panel { min-height: 350px; }
.section-heading { display: flex; justify-content: space-between; margin: 4px 0 15px; }
.member-actions { display: flex; gap: 8px; }
.roster-editor { margin-top: 14px; }
.section-heading h2 { margin: 0; color: #243143; font-size: 18px; }
.section-heading p { margin: 5px 0 0; color: #768396; font-size: 12px; }
.lesson-list { border: 1px solid #e4eaf0; border-radius: 11px; overflow: hidden; }
.lesson-row {
  width: 100%; display: grid; grid-template-columns: 38px 1fr auto 24px; align-items: center;
  gap: 12px; padding: 15px 17px; border: 0; border-bottom: 1px solid #edf1f4;
  background: #fff; text-align: left; cursor: pointer;
}
.lesson-row:hover { background: #f7fbfa; }
.lesson-row:last-child { border-bottom: 0; }
.lesson-index { width: 31px; height: 31px; display: grid; place-items: center; border-radius: 9px; background: #e8f5f3; color: #27887e; }
.lesson-row b, .lesson-row small { display: block; }
.lesson-row b { color: #2a3646; }
.lesson-row small { margin-top: 4px; color: #8994a3; }
.assignment-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }
.assignment-card { padding: 17px; border: 1px solid #e2e8f0; border-radius: 11px; background: #fff; cursor: pointer; }
.assignment-card:hover { border-color: #75b9b2; box-shadow: 0 10px 24px rgba(39,136,126,.09); }
.assignment-card > div, .assignment-card footer { display: flex; align-items: center; justify-content: space-between; color: #8a96a6; font-size: 11px; }
.assignment-card h3 { margin: 14px 0 7px; color: #293647; }
.assignment-card-body {
  min-height: 76px;
  max-height: 76px;
  margin: 0;
  overflow-y: auto;
  padding-right: 5px;
  color: #6c7888;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  scrollbar-width: thin;
  scrollbar-color: #c7d7d3 transparent;
}
.assignment-card footer { margin-top: 15px; }
.assignment-card footer b { color: #27887e; }
.small-empty { min-height: 210px; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #8b98a8; border: 1px dashed #d5dfe7; border-radius: 11px; grid-column: 1/-1; }
.small-empty i { font-size: 32px; color: #9bcac5; }
.metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.metric-grid div { padding: 18px; border: 1px solid #e1e8ed; border-radius: 11px; background: #fbfdfd; }
.metric-grid span, .metric-grid b { display: block; }
.metric-grid span { color: #718096; font-size: 12px; }
.metric-grid b { margin-top: 7px; color: #237e74; font-size: 24px; }
.analytics-note { margin-top: 16px; padding: 16px; display: flex; gap: 12px; border-radius: 10px; background: #eef8f6; color: #4d675f; font-size: 13px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.form-grid-three { grid-template-columns: 1.2fr 1.2fr .8fr; }
.assignment-import-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.assignment-import-status { margin-top: 10px; }
.fixed-score-card { min-height: 38px; display: flex; flex-direction: column; justify-content: center; padding: 8px 12px; border: 1px solid #d9e8e4; border-radius: 8px; background: #f4faf8; }
.fixed-score-card b { color: #287f75; font-size: 13px; }
.fixed-score-card span { margin-top: 3px; color: #7a8985; font-size: 10px; line-height: 1.45; }
.dialog-help { margin: 8px 0 0; color: #7b8795; font-size: 12px; line-height: 1.6; }
.small-empty .el-button { margin-top: 12px; }
.published-assets { display: grid; gap: 9px; margin-bottom: 16px; }
.published-assets article {
  display: grid; grid-template-columns: 38px 1fr auto; align-items: center; gap: 11px;
  padding: 12px 14px; border: 1px solid #dfe9e6; border-radius: 10px;
  background: linear-gradient(100deg, #f7fbfa, #fff);
}
.asset-icon {
  width: 36px; height: 36px; display: grid; place-items: center;
  border-radius: 9px; background: #e4f3ef; color: #27887e;
}
.published-assets b, .published-assets small { display: block; }
.published-assets small { margin-top: 4px; color: #83908f; font-size: 11px; }
.weakness-summary { display: grid; gap: 10px; }
.weakness-summary article {
  display: grid; grid-template-columns: 38px 1fr auto; align-items: center; gap: 12px;
  padding: 15px 17px; border: 1px solid #e4e8e6; border-radius: 11px; background: #fff;
}
.weakness-summary article > span {
  width: 34px; height: 34px; display: grid; place-items: center;
  border-radius: 50%; background: #f7e9e2; color: #a76149; font-weight: 700;
}
.weakness-summary b, .weakness-summary small { display: block; }
.weakness-summary small { margin-top: 4px; color: #84918f; font-size: 11px; }
.weakness-summary strong { color: #b4654d; font-size: 20px; }
.all-clear { display: flex; align-items: center; gap: 12px; padding: 18px; color: #3d7f72; }
.all-clear i { font-size: 26px; }
.all-clear b, .all-clear small { display: block; }
@media (max-width: 900px) {
  .metric-grid { grid-template-columns: repeat(2, 1fr); }
  .form-grid-three { grid-template-columns: 1fr; }
}
</style>
