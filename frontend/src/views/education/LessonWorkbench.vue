<template>
  <EducationShell
    :title="lesson ? lesson.title : '课时工作台'"
    :subtitle="isTeacher ? '结构化教案、学习材料与发布版本' : '已发布的学习材料与任务'"
    :back-to="`/education/courses/${courseId}`"
  >
    <template #actions>
      <el-tag v-if="lesson" :type="lesson.status === 'published' ? 'success' : 'info'">
        {{ lesson.status === 'published' ? '已发布' : '草稿' }}
      </el-tag>
      <el-tag v-if="isTeacher && hasUnsavedChanges" type="warning" effect="plain">
        有未保存更改
      </el-tag>
      <el-button
        v-if="isTeacher"
        data-testid="start-agent-workflow"
        icon="el-icon-cpu"
        :loading="isAgentRunning"
        @click="agentDialog = true"
      >Agent 协作生成</el-button>
      <el-button
        v-if="isTeacher"
        data-testid="save-lesson-version"
        :loading="saving"
        @click="saveVersion"
      >保存新版本</el-button>
      <el-button
        v-if="isTeacher"
        data-testid="publish-lesson"
        type="primary"
        :loading="publishing"
        @click="publishVersion"
      >发布给学生</el-button>
    </template>

    <el-skeleton v-if="!lesson" :rows="9" animated />
    <div v-else class="workbench">
      <aside class="workbench-nav">
        <button
          v-for="item in visibleSections"
          :key="item.key"
          type="button"
          :class="{ active: section === item.key }"
          @click="section = item.key"
        >
          <i :class="item.icon"></i>
          <span>{{ item.label }}</span>
        </button>
        <div class="version-note">
          <span>当前版本</span>
          <b>{{ currentVersionLabel }}</b>
          <time v-if="currentVersionTimeLabel">{{ currentVersionTimeLabel }}</time>
          <small>发布后学生看到固定快照，后续编辑不会覆盖。</small>
        </div>
      </aside>

      <section class="workbench-content">
        <div v-if="section === 'plan'">
          <div class="content-heading">
            <div><h2>教案</h2><p>根据课型调整教学重点，目标、活动和评价保持一致。</p></div>
          </div>
          <LessonPlanEditor
            v-if="isTeacher"
            v-model="lessonPlan"
            :subject-code="course.subject_code"
            data-testid="lesson-plan-editor"
            @change="markDirty"
          />
          <div v-else class="student-plan">
            <h3>本课学习目标</h3>
            <p>{{ lessonPlan.objectives || '教师尚未公开学习目标。' }}</p>
            <h3>学习活动</h3>
            <p>{{ lessonPlan.activities || '请按教师发布的材料完成本课学习。' }}</p>
          </div>
        </div>

        <div v-if="section === 'material'">
          <div class="content-heading">
            <div><h2>可编辑学习材料</h2><p>HTML 是演示产物，结构化内容是后续编辑的真源。</p></div>
            <el-radio-group v-model="materialMode" size="small">
              <el-radio-button label="edit" :disabled="!isTeacher">编辑</el-radio-button>
              <el-radio-button label="preview">安全预览</el-radio-button>
            </el-radio-group>
          </div>
          <RichMaterialEditor
            v-if="materialMode === 'edit' && isTeacher"
            v-model="materialHtml"
            @change="markDirty"
          />
          <SafeHtmlPreview v-else :html="materialHtml" data-testid="lesson-material-preview" />
          <div v-if="isTeacher" class="material-upload">
            <input
              ref="materialFile"
              class="visually-hidden"
              type="file"
              accept=".pdf,.doc,.docx,.ppt,.pptx,.html,.htm"
              @change="uploadMaterial"
            >
            <el-button icon="el-icon-upload2" @click="$refs.materialFile.click()">
              上传 PDF / Word / PPTX / HTML
            </el-button>
            <small>上传后先作为教师草稿，随课时发布后学生才可下载。</small>
          </div>
          <div v-if="lessonAssets.length" class="material-files">
            <article v-for="asset in lessonAssets" :key="asset.id">
              <div>
                <b>{{ asset.title }}</b>
                <small>{{ asset.original_filename }} · {{ fileSizeLabel(asset.byte_size) }}</small>
              </div>
              <el-tag size="mini" :type="asset.visibility_scope === 'course_published' ? 'success' : 'info'">
                {{ asset.visibility_scope === 'course_published' ? '学生可见' : '教师可见' }}
              </el-tag>
              <el-button size="mini" @click="downloadAsset(asset)">下载</el-button>
              <el-dropdown v-if="isTeacher" trigger="click" @command="handleAssetCommand($event, asset)">
                <el-button size="mini" icon="el-icon-more"></el-button>
                <el-dropdown-menu slot="dropdown">
                  <el-dropdown-item command="teacher" :disabled="asset.visibility_scope === 'course_teacher'">教师可见</el-dropdown-item>
                  <el-dropdown-item command="student" :disabled="asset.visibility_scope === 'course_published'">学生可见</el-dropdown-item>
                  <el-dropdown-item command="delete" icon="el-icon-delete" divided>删除</el-dropdown-item>
                </el-dropdown-menu>
              </el-dropdown>
            </article>
          </div>
        </div>

        <div v-if="section === 'activity'">
          <div class="content-heading">
            <div>
              <h2>学习活动</h2>
              <p>活动卡片和附件随课时版本一起发布；需要学生提交的内容请使用作业。</p>
            </div>
            <el-button
              v-if="isTeacher"
              type="primary"
              plain
              icon="el-icon-plus"
              data-testid="create-learning-activity"
              @click="openActivityDialog"
            >新建活动</el-button>
          </div>
          <div v-if="activities.length" class="activity-list">
            <article v-for="(activity, index) in activities" :key="activity.id || index">
              <span>{{ index + 1 }}</span>
              <div class="activity-body">
                <div class="activity-title-line">
                  <b>{{ activity.title || activity.activity_type }}</b>
                  <small v-if="activity.estimated_minutes">约 {{ activity.estimated_minutes }} 分钟</small>
                </div>
                <p>{{ activity.instructions || activity.prompt || activity.description }}</p>
                <div v-if="activity.questions && activity.questions.length" class="activity-questions">
                  <b>练习题目</b>
                  <p v-for="(question, qIndex) in activity.questions" :key="question.id || qIndex">
                    {{ qIndex + 1 }}. {{ question.prompt || question.question }}
                  </p>
                </div>
                <div v-if="activityAttachments(activity).length" class="activity-attachments">
                  <el-button
                    v-for="material in activityAttachments(activity)"
                    :key="material.id"
                    size="mini"
                    icon="el-icon-paperclip"
                    @click="downloadMaterial(material)"
                  >{{ material.title }}</el-button>
                </div>
              </div>
              <div class="activity-state">
                <el-tag size="mini">{{ activityTypeLabel(activity.activity_type) }}</el-tag>
                <el-tag
                  v-if="isTeacher"
                  size="mini"
                  :type="activity.status === 'published' ? 'success' : 'info'"
                >{{ activity.status === 'published' ? '已发布' : '草稿' }}</el-tag>
              </div>
            </article>
          </div>
          <div v-else class="empty-block">本课暂无学习活动。教师可以新建活动或从 Agent 习题产物添加。</div>
        </div>

        <div v-if="section === 'agents'" class="agent-team-panel">
          <div class="content-heading">
            <div>
              <h2>Agent 协作记录</h2>
              <p>每个 Agent 在独立空间中工作；这里集中展示过程状态、校验结果和可采用产物。</p>
            </div>
            <el-tag v-if="agentRun" :type="runTagType">{{ runStatusLabel }}</el-tag>
          </div>
          <div class="workflow-future-note">
            <div>
              <b>当前团队：阅读课协作模板</b>
              <small>课程设计 → 习题生成 → 教学审校；后续可选择 Agent、调整顺序并保存为自定义模板。</small>
            </div>
            <el-tag size="mini" effect="plain">自定义组合 · 下一阶段</el-tag>
          </div>
          <div
            v-if="agentRun && agentRun.nodes"
            class="agent-node-list"
            data-testid="agent-run-node-list"
          >
            <article v-for="node in agentRun.nodes" :key="node.id" class="agent-node">
              <span class="agent-state" :class="node.status"></span>
              <div>
                <b>{{ node.agent_name || (node.type === 'approval' ? '教师发布审核' : node.id) }}</b>
                <small>{{ nodeStatusLabel(node.status) }}</small>
                <small v-if="node.validation_status" class="validation-state">
                  {{ validationStatusLabel(node.validation_status) }}
                </small>
                <p v-if="node.error">{{ node.error }}</p>
                <p v-if="node.validation_status === 'failed'">{{ node.validation_error }}</p>
                <small v-if="hasArtifact(node)" class="artifact-summary">
                  {{ artifactSummary(node) }}
                </small>
                <div
                  v-if="node.tool_calls && node.tool_calls.length"
                  class="agent-tool-calls"
                  data-testid="agent-business-tool-calls"
                >
                  <div
                    v-for="call in node.tool_calls"
                    :key="call.id"
                    class="agent-tool-call"
                  >
                    <i class="el-icon-connection"></i>
                    <span>
                      <b>{{ toolActionLabel(call.tool_name) }}</b>
                      <small>{{ toolCallSummary(call) }}</small>
                    </span>
                    <el-tag
                      size="mini"
                      :type="call.status === 'completed' ? 'success' : 'danger'"
                    >
                      {{ call.status === 'completed' ? '已写入业务系统' : '调用失败' }}
                    </el-tag>
                  </div>
                </div>
                <el-button
                  v-if="hasArtifact(node)"
                  class="artifact-toggle"
                  type="text"
                  icon="el-icon-view"
                  @click="toggleArtifact(node)"
                >
                  {{ artifactOpen[node.id] ? '收起产物' : '预览产物' }}
                </el-button>
              </div>
              <AgentArtifactPreview
                v-if="hasArtifact(node) && artifactOpen[node.id]"
                :role="node.agent_role"
                :output="artifactFor(node)"
                @add-activity="openExerciseActivity"
              />
            </article>
          </div>
          <div v-else class="empty-block">
            尚未运行 Agent 团队。点击右上角“Agent 协作生成”启动真实工作流。
          </div>
          <div v-if="agentDraft" class="agent-draft">
            <div>
              <b>课程设计师草稿已就绪</b>
              <p>采用后只会填入当前编辑器，不会自动保存或发布。</p>
            </div>
            <el-button type="primary" plain @click="applyAgentDraft">采用到教案</el-button>
          </div>
          <el-alert
            v-if="agentRun && agentRun.error_summary"
            type="error"
            :title="agentRun.error_summary"
            :closable="false"
            show-icon
          />
        </div>
      </section>
    </div>

    <el-dialog
      title="新建学习活动"
      :visible.sync="activityDialog"
      width="620px"
      data-testid="learning-activity-dialog"
    >
      <el-form label-position="top">
        <div class="activity-form-grid">
          <el-form-item label="活动类型">
            <el-select v-model="activityForm.activity_type" style="width:100%">
              <el-option label="资源查看" value="resource" />
              <el-option label="阅读" value="reading" />
              <el-option label="展示" value="presentation" />
              <el-option label="练习" value="practice" />
              <el-option label="写作" value="writing" />
            </el-select>
          </el-form-item>
          <el-form-item label="预计用时（分钟）">
            <el-input-number v-model="activityForm.estimated_minutes" :min="1" :max="180" />
          </el-form-item>
        </div>
        <el-form-item label="活动标题">
          <el-input v-model="activityForm.title" placeholder="例如：阅读证据提取练习" />
        </el-form-item>
        <el-form-item label="给学生的说明">
          <el-input
            v-model="activityForm.instructions"
            type="textarea"
            :rows="5"
            placeholder="说明活动步骤、完成要求和使用材料"
          />
        </el-form-item>
        <el-form-item label="可选附件">
          <input
            ref="activityFile"
            type="file"
            accept=".pdf,.doc,.docx,.ppt,.pptx,.html,.htm"
            @change="selectActivityAttachment"
          >
          <small class="form-help">支持 PDF、Word、PPTX 和 HTML；保存活动时一并上传。</small>
        </el-form-item>
        <el-alert
          v-if="activityForm.questions.length"
          :title="`将添加 ${activityForm.questions.length} 道 Agent 习题；答案仅教师可见`"
          type="success"
          :closable="false"
          show-icon
        />
      </el-form>
      <template #footer>
        <el-button @click="activityDialog = false">取消</el-button>
        <el-button
          type="primary"
          :loading="activitySaving"
          data-testid="save-learning-activity"
          @click="createLearningActivity"
        >保存活动草稿</el-button>
      </template>
    </el-dialog>

    <el-dialog title="启动 Agent 教案协作" :visible.sync="agentDialog" width="620px">
      <p class="dialog-help">
        课程设计师、习题生成器和教学审校员将在各自 workspace 中协作。中间步骤自动推进，
        最终仍由你决定是否采用和发布。
      </p>
      <el-input
        v-model="agentRequirements"
        data-testid="agent-workflow-requirements"
        type="textarea"
        :rows="6"
        placeholder="补充班级情况、教学重点、材料范围或希望避免的内容"
      />
      <template #footer>
        <el-button @click="agentDialog = false">取消</el-button>
        <el-button type="primary" :loading="isAgentRunning" @click="startAgentWorkflow">
          启动真实 Agent 团队
        </el-button>
      </template>
    </el-dialog>
  </EducationShell>
</template>

<script>
import EducationShell from '../../components/education/EducationShell.vue'
import AgentArtifactPreview from '../../components/education/AgentArtifactPreview.vue'
import LessonPlanEditor from '../../components/education/LessonPlanEditor.vue'
import RichMaterialEditor from '../../components/education/RichMaterialEditor.vue'
import SafeHtmlPreview from '../../components/education/SafeHtmlPreview.vue'
import { downloadLessonMaterial } from '../../api/education'
import { educationErrorMessage } from '../../utils/educationErrors'
const {
  formatVersionTime,
  normalizeActivities,
  normalizeObjectives,
} = require('../../utils/educationContent')

export default {
  name: 'EducationLessonWorkbench',
  components: {
    AgentArtifactPreview,
    EducationShell,
    LessonPlanEditor,
    RichMaterialEditor,
    SafeHtmlPreview,
  },
  data() {
    return {
      section: 'plan',
      materialMode: 'preview',
      lessonPlan: {
        lesson_type_code: '',
        duration_minutes: 45,
        objectives: '',
        activities: '',
        assessment: '',
      },
      materialHtml: '',
      savedVersionId: '',
      savedSnapshot: '',
      savedPlanSnapshot: '',
      savedMaterialHtml: '',
      dirty: false,
      suppressDirty: true,
      publishing: false,
      artifactOpen: {},
      agentDialog: false,
      agentRequirements: '',
      activityDialog: false,
      activitySaving: false,
      activityAttachment: null,
      activitySourceArtifact: null,
      activityForm: {
        activity_type: 'reading',
        title: '',
        instructions: '',
        estimated_minutes: 15,
        questions: [],
      },
      pollTimer: null,
      sections: [
        { key: 'plan', label: '教案', icon: 'el-icon-document' },
        { key: 'material', label: '课件与材料', icon: 'el-icon-data-board' },
        { key: 'activity', label: '学习活动', icon: 'el-icon-s-operation' },
        { key: 'agents', label: 'Agent 团队', icon: 'el-icon-cpu', teacherOnly: true },
      ],
    }
  },
  computed: {
    courseId() { return this.$route.params.courseId },
    lessonId() { return this.$route.params.lessonId },
    course() { return this.$store.getters['education/activeCourse'] || {} },
    lesson() { return this.$store.state.education.activeLesson },
    isTeacher() { return this.$store.getters['education/isTeacher'] },
    saving() { return this.$store.getters['education/saving'] },
    activities() { return (this.lesson && this.lesson.activities) || [] },
    materials() { return (this.lesson && this.lesson.materials) || [] },
    lessonAssets() {
      return (this.$store.getters['education/assets'] || []).filter(asset => (
        asset.lesson_id === this.lessonId
        && ['courseware', 'lesson_material'].includes(asset.purpose)
      ))
    },
    visibleSections() {
      return this.sections.filter(item => !item.teacherOnly || this.isTeacher)
    },
    agentRun() { return this.$store.getters['education/agentRun'] },
    isAgentRunning() {
      return Boolean(this.agentRun && ['pending', 'running'].includes(this.agentRun.status))
    },
    agentDraft() {
      return this.agentRun
        && this.agentRun.output
        && this.agentRun.output.course_designer
    },
    runStatusLabel() {
      const labels = {
        pending: '准备中',
        running: '协作中',
        partial: '部分完成',
        awaiting_approval: '等待教师确认',
        failed: '运行失败',
      }
      return labels[this.agentRun && this.agentRun.status] || '未启动'
    },
    runTagType() {
      if (!this.agentRun) return 'info'
      if (this.agentRun.status === 'awaiting_approval') return 'success'
      if (['failed', 'partial'].includes(this.agentRun.status)) return 'danger'
      return 'warning'
    },
    currentVersionLabel() {
      const version = this.lesson && (this.lesson.current_version || this.lesson.published_version)
      return version && (version.version_number || version.version) ? `v${version.version_number || version.version}` : '尚未保存'
    },
    currentVersionTimeLabel() {
      const version = this.lesson && (this.lesson.current_version || this.lesson.published_version)
      return formatVersionTime(version && (version.created_at || version.published_at))
    },
    currentSnapshot() {
      return JSON.stringify({
        lessonPlan: this.lessonPlan,
        materialHtml: this.materialHtml,
      })
    },
    planChanged() {
      return Boolean(this.savedPlanSnapshot && JSON.stringify(this.lessonPlan) !== this.savedPlanSnapshot)
    },
    materialChanged() {
      return Boolean(this.savedSnapshot && this.materialHtml !== this.savedMaterialHtml)
    },
    hasUnsavedChanges() {
      return this.dirty || this.planChanged || this.materialChanged
    },
  },
  async created() {
    try {
      if (!this.course.id) {
        await this.$store.dispatch('education/selectCourse', this.courseId)
      }
      if (!this.$store.getters['education/units'].length) {
        await this.$store.dispatch('education/fetchCourseOverview', this.courseId)
      }
      const lesson = await this.$store.dispatch('education/fetchLesson', this.lessonId)
      await this.$store.dispatch('education/fetchAssets', {
        courseId: this.courseId,
        params: { lesson_id: this.lessonId, purpose: 'courseware,lesson_material' },
      })
      const version = lesson.current_version || lesson.published_version || lesson.publication || {}
      const content = version.source_json || version.content || version.content_json || lesson.content || {}
      const stages = Array.isArray(content.stages) ? content.stages : []
      const objectives = normalizeObjectives(content.objectives)
      this.lessonPlan = {
        ...this.lessonPlan,
        ...(content.lesson_plan || lesson.lesson_plan || {}),
        lesson_type_code: lesson.lesson_type_code || (content.lesson_plan || {}).lesson_type_code || '',
        duration_minutes: content.duration_minutes || lesson.duration_minutes || 45,
        objectives: objectives || (content.lesson_plan || {}).objectives || '',
        activities: normalizeActivities(stages)
          || (content.lesson_plan || {}).activities
          || '',
        assessment: stages.map(stage => stage.assessment).filter(Boolean).join('\n')
          || (content.lesson_plan || {}).assessment
          || '',
      }
      this.materialHtml = (lesson.material_version && lesson.material_version.rendered_html)
        || version.rendered_html
        || content.html
        || content.material_html
        || lesson.material_html
        || ''
      this.savedVersionId = version.id || ''
      this.materialMode = this.isTeacher ? 'edit' : 'preview'
      await this.$nextTick()
      await new Promise(resolve => window.setTimeout(resolve, 500))
      this.markSavedState()
      this.suppressDirty = false
      if (this.isTeacher) {
        try {
          await this.$store.dispatch('education/restoreLessonAgentRun', {
            courseId: this.courseId,
            lessonId: this.lessonId,
          })
        } catch (error) {
          // Lesson editing remains available when run history cannot be restored.
        }
      }
    } catch (error) {
      this.$message.error('课时加载失败或你无权访问')
      this.$router.replace(`/education/courses/${this.courseId}`)
    }
  },
  beforeDestroy() {
    this.stopAgentPolling()
    window.removeEventListener('keydown', this.handleShortcut)
    window.removeEventListener('beforeunload', this.handleBeforeUnload)
  },
  mounted() {
    window.addEventListener('keydown', this.handleShortcut)
    window.addEventListener('beforeunload', this.handleBeforeUnload)
  },
  beforeRouteLeave(to, from, next) {
    if (!this.hasUnsavedChanges) {
      next()
      return
    }
    this.$confirm(
      '当前教案或课件还有未保存更改，离开后这些修改会丢失。',
      '离开课时工作台？',
      {
        confirmButtonText: '仍然离开',
        cancelButtonText: '继续编辑',
        type: 'warning',
      }
    ).then(() => next()).catch(() => next(false))
  },
  methods: {
    toolActionLabel(toolName) {
      const labels = {
        'edu.course.list': '读取课程列表',
        'edu.course.members.list': '读取课程成员',
        'edu.course.context.get': '读取课程上下文',
        'edu.question_bank.search': '检索课程题库',
        'edu.knowledge.search': '检索课程知识库',
        'edu.course.create': '创建课程',
        'edu.course.members.import': '导入学生名单',
        'edu.lesson.create': '创建课时',
        'edu.courseware.create': '采纳教案或课件草稿',
        'edu.asset.attach': '保存持久化文件',
        'edu.question_bank.upsert': '采纳习题到题库',
        'edu.paper.compose': '组建试卷',
        'edu.student_insight.refresh': '刷新学生画像',
        'edu.mock_exam.create': '生成模拟考试',
        'edu.weakness.analyze': '分析作业弱点',
        'edu.mind_map.create': '生成课程思维导图',
      }
      return labels[toolName] || toolName
    },
    toolCallSummary(call) {
      if (call.status !== 'completed') {
        return call.error_message || call.error_code || '业务工具调用失败'
      }
      const summary = call.result_summary || {}
      if (Number.isFinite(summary.item_count)) {
        return `${summary.item_count} 项 · ${call.idempotency_key ? '幂等写入' : '只读查询'}`
      }
      if (summary.data_state === 'insufficient') return '数据不足，未生成推测性结论'
      return call.idempotency_key ? '已校验并持久化，可追踪重放' : '已按课程权限返回'
    },
    artifactFor(node) {
      const outputs = (this.agentRun && this.agentRun.output) || {}
      return outputs[node.agent_role] || node.output || {}
    },
    hasArtifact(node) {
      if (!node || node.type !== 'agent_task') return false
      return Object.keys(this.artifactFor(node)).length > 0
    },
    toggleArtifact(node) {
      this.$set(this.artifactOpen, node.id, !this.artifactOpen[node.id])
    },
    artifactSummary(node) {
      const artifact = this.artifactFor(node)
      if (node.agent_role === 'course_designer') {
        const count = Array.isArray(artifact.objectives) ? artifact.objectives.length : 0
        return `${count || '—'} 个教学目标 · 结构化教案草稿`
      }
      if (node.agent_role === 'exercise_generator') {
        const exercises = artifact.questions || artifact.exercises || artifact.items
        return Array.isArray(exercises)
          ? `${exercises.length} 道练习 · ${artifact.meta && artifact.meta.total_score ? `${artifact.meta.total_score} 分` : '结构化产物'}`
          : '习题结构化失败 · 请重新运行'
      }
      if (node.agent_role === 'teaching_reviewer') {
        const review = artifact.overall_evaluation || {}
        return `${review.grade || review.verdict || '已完成'} · 教学审校结论`
      }
      return 'Agent 产物 · 可展开查看'
    },
    markSavedState() {
      this.savedSnapshot = this.currentSnapshot
      this.savedPlanSnapshot = JSON.stringify(this.lessonPlan)
      this.savedMaterialHtml = this.materialHtml
      this.dirty = false
    },
    markDirty() {
      if (!this.suppressDirty) this.dirty = true
    },
    handleShortcut(event) {
      if (!this.isTeacher || !(event.ctrlKey || event.metaKey)) return
      if (event.key.toLowerCase() === 's') {
        event.preventDefault()
        if (!this.saving) this.saveVersion()
      } else if (event.key === 'Enter') {
        event.preventDefault()
        if (!this.publishing) this.publishVersion()
      }
    },
    handleBeforeUnload(event) {
      if (!this.hasUnsavedChanges) return
      event.preventDefault()
      event.returnValue = ''
    },
    nodeStatusLabel(status) {
      const labels = {
        pending: '等待前序任务',
        running: '正在执行',
        done: '已完成',
        failed: '失败',
        skipped: '已跳过',
        awaiting_approval: '等待教师确认',
      }
      return labels[status] || status
    },
    validationStatusLabel(status) {
      const labels = {
        repairing: '结构化校验失败，已退回该 Agent 自动修复',
        repaired: '结构化输出已校验并自动修复',
        failed: '自动修复失败，已保留可见文本',
      }
      return labels[status] || status
    },
    async startAgentWorkflow() {
      try {
        const run = await this.$store.dispatch('education/startLessonAgentRun', {
          course_id: this.courseId,
          lesson_id: this.lessonId,
          workflow_code: 'reading_lesson',
          teacher_requirements: this.agentRequirements,
        })
        this.agentDialog = false
        this.section = 'agents'
        this.$message.success('Agent 团队已在独立 sandbox 中启动')
        this.startAgentPolling(run.id)
      } catch (error) {
        const detail = error.response
          && error.response.data
          && (error.response.data.error_summary || error.response.data.error)
        this.$message.error(detail || 'Agent 工作流启动失败，请先检查模型配置和 Docker')
      }
    },
    startAgentPolling(runId) {
      this.stopAgentPolling()
      const refresh = async () => {
        try {
          const run = await this.$store.dispatch('education/refreshAgentRun', runId)
          if (!['pending', 'running'].includes(run.status)) {
            this.stopAgentPolling()
          }
        } catch (error) {
          this.stopAgentPolling()
        }
      }
      refresh()
      this.pollTimer = window.setInterval(refresh, 3000)
    },
    stopAgentPolling() {
      if (this.pollTimer) {
        window.clearInterval(this.pollTimer)
        this.pollTimer = null
      }
    },
    applyAgentDraft() {
      const draft = this.agentDraft || {}
      this.lessonPlan = {
        ...this.lessonPlan,
        objectives: normalizeObjectives(draft.objectives) || this.lessonPlan.objectives,
        activities: normalizeActivities(draft.activities || draft.stages)
          || this.lessonPlan.activities,
        assessment: normalizeActivities(draft.assessment) || this.lessonPlan.assessment,
      }
      this.markDirty()
      this.section = 'plan'
      this.$message.success('Agent 草稿已填入教案，请审核后保存新版本')
    },
    resetActivityForm() {
      this.activityForm = {
        activity_type: 'reading',
        title: '',
        instructions: '',
        estimated_minutes: 15,
        questions: [],
      }
      this.activityAttachment = null
      this.activitySourceArtifact = null
      if (this.$refs.activityFile) this.$refs.activityFile.value = ''
    },
    openActivityDialog() {
      this.resetActivityForm()
      this.activityDialog = true
    },
    openExerciseActivity(artifact) {
      const questions = artifact.questions || artifact.exercises || artifact.items || []
      this.resetActivityForm()
      this.activitySourceArtifact = artifact
      this.activityForm = {
        activity_type: 'practice',
        title: (artifact.meta && artifact.meta.title) || 'Agent 生成练习',
        instructions: '请完成以下练习，结合课文或学习材料写出依据。',
        estimated_minutes: Number(artifact.meta && artifact.meta.estimated_minutes) || 15,
        questions: questions.map(question => ({
          id: question.id,
          type: question.type,
          prompt: question.prompt || question.question || question.title,
          options: question.options || [],
          difficulty: question.difficulty,
          knowledge_points: question.knowledge_points || [],
          score: question.score,
        })),
      }
      this.activityDialog = true
    },
    selectActivityAttachment(event) {
      this.activityAttachment = event.target.files && event.target.files[0]
    },
    async createLearningActivity() {
      if (!this.activityForm.title.trim()) {
        this.$message.warning('请填写活动标题')
        return
      }
      this.activitySaving = true
      try {
        const attachmentIds = []
        if (this.activityAttachment) {
          const material = await this.$store.dispatch('education/uploadMaterial', {
            lessonId: this.lessonId,
            file: this.activityAttachment,
            title: this.activityAttachment.name.replace(/\.[^.]+$/, ''),
          })
          attachmentIds.push(material.id)
        }
        const sourceQuestions = (
          this.activitySourceArtifact
          && (this.activitySourceArtifact.questions
            || this.activitySourceArtifact.exercises
            || this.activitySourceArtifact.items)
        ) || []
        await this.$store.dispatch('education/createLearningActivity', {
          lessonId: this.lessonId,
          activity: {
            activity_type: this.activityForm.activity_type,
            title: this.activityForm.title.trim(),
            position: this.activities.length + 1,
            student_payload: {
              instructions: this.activityForm.instructions,
              estimated_minutes: this.activityForm.estimated_minutes,
              attachment_ids: attachmentIds,
              questions: this.activityForm.questions,
            },
            teacher_payload: {
              questions: sourceQuestions.map(question => ({
                id: question.id,
                answer: question.answer,
                explanation: question.explanation,
                common_mistakes: question.common_mistakes,
              })),
            },
          },
        })
        this.activityDialog = false
        this.section = 'activity'
        this.$message.success('学习活动草稿已保存，发布课时后学生可见')
        this.resetActivityForm()
      } catch (error) {
        const detail = error.response && error.response.data && error.response.data.error
        this.$message.error(detail || '学习活动保存失败')
      } finally {
        this.activitySaving = false
      }
    },
    activityTypeLabel(value) {
      const labels = {
        resource: '资源',
        reading: '阅读',
        presentation: '展示',
        practice: '练习',
        writing: '写作',
        assignment: '作业',
      }
      return labels[value] || value || '学习活动'
    },
    activityAttachments(activity) {
      const ids = activity.attachment_ids || []
      return this.materials.filter(material => ids.includes(material.id))
    },
    async saveVersion(options = {}) {
      this.suppressDirty = true
      try {
        const version = await this.$store.dispatch('education/saveLesson', {
          lessonId: this.lessonId,
          version: {
            lesson_plan_json: this.lessonPlan,
            content: {
              lesson_plan: this.lessonPlan,
              html: this.materialHtml,
            },
          },
        })
        this.savedVersionId = version.version ? version.version.id : version.id
        await this.$nextTick()
        // Element inputs may flush their final model update after the keyboard event.
        // Capture the saved baseline once that update queue is settled.
        await new Promise(resolve => window.setTimeout(resolve, 500))
        this.markSavedState()
        if (!options.silent) this.$message.success('新版本已保存')
        return version
      } catch (error) {
        this.$message.error(error.message || '版本保存失败')
        if (options.silent) throw error
        return null
      } finally {
        this.suppressDirty = false
      }
    },
    async publishVersion() {
      if (this.publishing) return
      try {
        const message = this.hasUnsavedChanges
          ? '检测到教案或课件有未保存更改。继续后将先保存新版本，再发布给学生。'
          : '发布后学生将看到当前已保存的固定版本，确认发布？'
        await this.$confirm(message, '发布课时', {
          confirmButtonText: this.hasUnsavedChanges ? '保存并发布' : '确认发布',
          cancelButtonText: '取消',
          type: 'warning',
        })
        this.publishing = true
        if (this.hasUnsavedChanges || !this.savedVersionId) {
          await this.saveVersion({ silent: true })
        }
        await this.$store.dispatch('education/publishLesson', {
          lessonId: this.lessonId,
          versionId: this.savedVersionId,
        })
        this.$message.success('课时已发布')
        await this.$store.dispatch('education/fetchLesson', this.lessonId)
        await this.$nextTick()
        this.markSavedState()
      } catch (error) {
        if (error !== 'cancel') {
          const detail = error.response && error.response.data && error.response.data.error
          this.$message.error(detail || '课时发布失败')
        }
      } finally {
        this.publishing = false
      }
    },
    async uploadMaterial(event) {
      const file = event.target.files && event.target.files[0]
      if (!file) return
      try {
        await this.$store.dispatch('education/uploadMaterial', {
          lessonId: this.lessonId,
          file,
          title: file.name.replace(/\.[^.]+$/, ''),
        })
        await this.$store.dispatch('education/fetchAssets', {
          courseId: this.courseId,
          params: { lesson_id: this.lessonId, purpose: 'courseware,lesson_material' },
        })
        this.$message.success('材料已上传，将在发布课时后对学生可见')
      } catch (error) {
        this.$message.error(educationErrorMessage(error, '材料上传失败'))
      } finally {
        event.target.value = ''
      }
    },
    async downloadMaterial(material) {
      try {
        const response = await downloadLessonMaterial(material.id)
        const blob = response instanceof Blob ? response : response.data
        const href = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = href
        link.download = material.original_filename || material.title
        link.click()
        URL.revokeObjectURL(href)
      } catch (error) {
        this.$message.error('材料下载失败或尚未发布')
      }
    },
    async downloadAsset(asset) {
      try {
        const response = await this.$store.dispatch('education/downloadAsset', asset)
        const blob = response instanceof Blob ? response : response.data
        const href = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = href
        link.download = asset.original_filename || asset.title
        link.click()
        URL.revokeObjectURL(href)
      } catch (error) {
        this.$message.error('文件下载失败或尚未发布')
      }
    },
    async handleAssetCommand(command, asset) {
      try {
        if (command === 'delete') {
          await this.$confirm(
            `删除“${asset.title}”后将从该课时和课件文件柜同时隐藏。`,
            '删除课件或材料',
            { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
          )
          await this.$store.dispatch('education/archiveAsset', {
            courseId: this.courseId,
            assetId: asset.id,
          })
          this.$message.success('文件已删除')
          return
        }
        await this.$store.dispatch('education/setAssetVisibility', {
          courseId: this.courseId,
          assetId: asset.id,
          visibilityScope: command === 'student' ? 'course_published' : 'course_teacher',
        })
        this.$message.success(command === 'student' ? '学生现在可以查看该文件' : '文件已改为仅教师可见')
      } catch (error) {
        if (error === 'cancel' || error === 'close') return
        this.$message.error(educationErrorMessage(error, '文件权限修改失败'))
      }
    },
    fileSizeLabel(bytes) {
      if (!bytes) return '0 KB'
      if (bytes < 1024 * 1024) return `${Math.ceil(bytes / 1024)} KB`
      return `${(bytes / 1024 / 1024).toFixed(1)} MB`
    },
  },
}
</script>

<style scoped>
.workbench { display: grid; grid-template-columns: 210px minmax(0, 1fr); gap: 18px; min-height: 580px; }
.workbench-nav { padding: 8px; border: 1px solid #e3e9ef; border-radius: 11px; background: #f8fafb; }
.workbench-nav button {
  width: 100%; display: flex; align-items: center; gap: 10px; padding: 12px;
  border: 0; border-radius: 8px; background: transparent; color: #657386; cursor: pointer; text-align: left;
}
.workbench-nav button.active { background: #fff; color: #27887e; font-weight: 700; box-shadow: 0 2px 9px rgba(30,41,59,.07); }
.version-note { margin-top: 18px; padding: 13px; border-top: 1px solid #e0e7ed; }
.version-note span, .version-note b, .version-note time, .version-note small { display: block; }
.version-note span { color: #8a96a6; font-size: 11px; }
.version-note b { margin: 5px 0; color: #304052; }
.version-note time { margin: -2px 0 8px; color: #6f7d8d; font-size: 10px; }
.version-note small { color: #8a96a6; line-height: 1.5; }
.workbench-content { min-width: 0; padding: 19px 21px; border: 1px solid #e3e9ef; border-radius: 11px; background: #fff; }
.content-heading { display: flex; align-items: start; justify-content: space-between; gap: 16px; margin-bottom: 18px; }
.content-heading h2 { margin: 0; color: #253244; font-size: 18px; }
.content-heading p { margin: 5px 0 0; color: #7a8797; font-size: 12px; }
.student-plan h3 { margin: 20px 0 7px; color: #2b394a; font-size: 15px; }
.student-plan p { padding: 14px; border-radius: 9px; background: #f6faf9; color: #586778; white-space: pre-wrap; line-height: 1.8; }
.activity-list article { display: grid; grid-template-columns: 34px minmax(0, 1fr) auto; gap: 12px; align-items: start; padding: 16px 0; border-bottom: 1px solid #edf1f4; }
.activity-list article > span { width: 30px; height: 30px; display: grid; place-items: center; border-radius: 8px; background: #e7f5f2; color: #27887e; }
.activity-list b { color: #2f3c4d; }
.activity-list p { margin: 5px 0 0; color: #728092; line-height: 1.6; }
.activity-title-line { display: flex; align-items: center; gap: 10px; }
.activity-title-line small { color: #8a96a6; }
.activity-state { display: flex; align-items: flex-end; gap: 6px; flex-direction: column; }
.activity-questions { margin-top: 12px; padding: 12px 14px; border-radius: 8px; background: #f7faf9; }
.activity-questions > b { font-size: 12px; }
.activity-questions p { font-size: 12px; }
.activity-attachments { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 11px; }
.activity-form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.form-help { display: block; margin-top: 6px; color: #83909e; }
.empty-block { min-height: 240px; display: grid; place-items: center; border: 1px dashed #d6e0e7; border-radius: 10px; color: #8a96a6; }
.material-upload { display: flex; align-items: center; gap: 12px; margin-top: 14px; }
.material-upload small { color: #8190a2; }
.visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0, 0, 0, 0); }
.material-files { margin-top: 14px; border-top: 1px solid #edf1f4; }
.material-files article { display: grid; grid-template-columns: minmax(0, 1fr) auto auto; gap: 12px; align-items: center; padding: 12px 0; border-bottom: 1px solid #edf1f4; }
.material-files b, .material-files small { display: block; }
.material-files small { margin-top: 3px; color: #8190a2; }
.workflow-future-note {
  display: flex; align-items: center; justify-content: space-between; gap: 14px;
  margin-bottom: 14px; padding: 12px 14px; border: 1px solid #e1e9ee; border-radius: 9px; background: #f8fafb;
}
.workflow-future-note b, .workflow-future-note small { display: block; }
.workflow-future-note b { color: #455767; font-size: 12px; }
.workflow-future-note small { margin-top: 4px; color: #82909e; line-height: 1.5; }
.agent-node-list { display: grid; gap: 10px; }
.agent-node { display: grid; grid-template-columns: 14px 1fr; gap: 10px; padding: 13px 14px; border: 1px solid #e4eaf0; border-radius: 9px; }
.agent-node b, .agent-node small { display: block; }
.agent-node small { margin-top: 4px; color: #8190a2; }
.agent-node p { margin: 7px 0 0; color: #c45656; font-size: 12px; }
.agent-node .artifact-summary { margin-top: 8px; color: #3d8279; }
.agent-tool-calls { display: grid; gap: 7px; margin-top: 10px; }
.agent-tool-call { display: grid; grid-template-columns: 18px minmax(0, 1fr) auto; align-items: center; gap: 8px; padding: 9px 10px; border: 1px solid #d9e9e6; border-radius: 8px; background: #f7fbfa; }
.agent-tool-call > i { color: #3d8279; }
.agent-tool-call b { color: #244740; font-size: 12px; }
.agent-tool-call small { margin-top: 2px; color: #758981; }
.agent-state { width: 10px; height: 10px; margin-top: 5px; border-radius: 50%; background: #cbd5df; }
.agent-state.running { background: #e6a23c; box-shadow: 0 0 0 4px #fdf3df; }
.agent-state.done { background: #36a77b; }
.agent-state.failed { background: #d75b5b; }
.agent-state.awaiting_approval { background: #409eff; }
.agent-draft { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-top: 16px; padding: 14px; border: 1px solid #b9ded8; border-radius: 9px; background: #f1faf8; }
.agent-draft p { margin: 4px 0 0; color: #6f7d8d; font-size: 12px; }
.dialog-help { color: #68778a; line-height: 1.7; }
@media (max-width: 860px) { .workbench { grid-template-columns: 1fr; } .workbench-nav { display: flex; } .version-note { display: none; } }
</style>
