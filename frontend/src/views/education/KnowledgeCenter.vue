<template>
  <EducationShell
    title="课程知识中心"
    :subtitle="course ? `${course.title} · 题目、试卷与可检索资料共享同一课程边界` : '加载课程知识资产'"
    :back-to="course ? `/education/courses/${course.id}` : '/education'"
  >
    <template #actions>
      <el-button icon="el-icon-refresh" :loading="loading" @click="load">刷新</el-button>
      <el-button
        v-if="activeTab === 'questions'"
        type="primary"
        icon="el-icon-plus"
        @click="questionDialog = true"
      >新建题目</el-button>
      <el-button
        v-if="activeTab === 'papers'"
        type="primary"
        icon="el-icon-document-add"
        :disabled="!selectedQuestionIds.length"
        @click="paperDialog = true"
      >从所选题目组卷</el-button>
      <el-button
        v-if="activeTab === 'resources'"
        type="primary"
        icon="el-icon-upload2"
        @click="$refs.knowledgeFile.click()"
      >上传资料</el-button>
    </template>

    <input
      ref="knowledgeFile"
      class="visually-hidden"
      type="file"
      accept=".pdf,.doc,.docx,.ppt,.pptx,.html,.htm,.txt,.md"
      @change="uploadKnowledgeFile"
    >

    <section class="knowledge-summary">
      <div class="summary-title">
        <span>ONE COURSE · ONE KNOWLEDGE CENTER</span>
        <h2>课程的可复用知识资产</h2>
        <p>Agent、教师页面和学生产品都通过相同 API 使用这些版本化资产；学生只能读取已发布内容。</p>
      </div>
      <div class="summary-metric">
        <b>{{ count('questions') }}</b><span>题库</span>
      </div>
      <div class="summary-metric">
        <b>{{ count('papers') }}</b><span>试卷库</span>
      </div>
      <div class="summary-metric">
        <b>{{ count('knowledge_resources') }}</b><span>知识库</span>
      </div>
    </section>

    <nav class="library-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        <i :class="tab.icon"></i>
        <span><b>{{ tab.label }}</b><small>{{ tab.caption }}</small></span>
      </button>
    </nav>

    <section
      v-if="activeTab === 'questions'"
      v-loading="loading"
      class="library-panel"
      data-testid="question-bank"
    >
      <header class="panel-header">
        <div><h3>题库</h3><p>稳定题目身份 + 不可变版本；答案只对教师可见。</p></div>
        <span>已选择 {{ selectedQuestionIds.length }} 题</span>
      </header>
      <div v-if="questions.length" class="question-list">
        <article v-for="(question, index) in questions" :key="question.id">
          <el-checkbox
            v-model="selectedQuestionIds"
            :label="question.id"
            :disabled="question.status !== 'published'"
          ><span></span></el-checkbox>
          <span class="question-index">{{ index + 1 }}</span>
          <div class="question-body">
            <header>
              <b>{{ question.title }}</b>
              <el-tag size="mini" :type="question.status === 'published' ? 'success' : 'info'">
                {{ question.status === 'published' ? '已发布' : '草稿' }}
              </el-tag>
              <el-tag size="mini" type="info">{{ difficultyLabel(question.current_version.difficulty) }}</el-tag>
              <span>{{ question.current_version.score }} 分</span>
            </header>
            <p>{{ question.current_version.prompt }}</p>
            <ol v-if="question.current_version.options.length" class="option-list">
              <li v-for="(option, optionIndex) in question.current_version.options" :key="optionIndex">
                <b>{{ optionLetter(optionIndex) }}</b><span>{{ option }}</span>
              </li>
            </ol>
            <footer>
              <span
                v-for="point in question.current_version.knowledge_points"
                :key="point"
              >{{ point }}</span>
              <small>v{{ question.current_version.version_number }}</small>
            </footer>
          </div>
          <div class="question-actions">
            <el-button
              v-if="question.status !== 'published'"
              size="mini"
              type="primary"
              @click="publishQuestion(question)"
            >发布</el-button>
            <el-popover placement="left" width="300" trigger="click">
              <p><b>参考答案：</b>{{ answerLabel(question) }}</p>
              <p>{{ question.current_version.answer && question.current_version.answer.explanation }}</p>
              <el-button slot="reference" size="mini">答案</el-button>
            </el-popover>
          </div>
        </article>
      </div>
      <EmptyLibrary v-else icon="el-icon-edit-outline" title="题库还是空的" description="手动创建一道规范题，或让习题 Agent 通过工具写入草稿。" />
    </section>

    <section
      v-if="activeTab === 'papers'"
      v-loading="loading"
      class="library-panel"
      data-testid="paper-bank"
    >
      <header class="panel-header">
        <div><h3>试卷库</h3><p>每个版本冻结题目版本顺序、分值与时长。</p></div>
      </header>
      <div v-if="papers.length" class="paper-grid">
        <article v-for="paper in papers" :key="paper.id">
          <span class="paper-corner">{{ purposeLabel(paper.purpose) }}</span>
          <div class="paper-icon"><i class="el-icon-document"></i></div>
          <h3>{{ paper.title }}</h3>
          <p>
            {{ paper.current_version.item_version_ids.length }} 题 ·
            {{ paper.current_version.total_score }} 分 ·
            {{ paper.current_version.duration_minutes }} 分钟
          </p>
          <footer>
            <el-tag size="mini" :type="paper.status === 'published' ? 'success' : 'info'">
              {{ paper.status === 'published' ? '学生可用' : '草稿' }}
            </el-tag>
            <el-button
              v-if="paper.status !== 'published'"
              size="mini"
              type="text"
              @click="publishPaper(paper)"
            >发布试卷</el-button>
            <small>v{{ paper.current_version.version_number }}</small>
          </footer>
        </article>
      </div>
      <EmptyLibrary v-else icon="el-icon-document" title="还没有试卷" description="先在题库中发布并勾选题目，再冻结成一份试卷。" />
    </section>

    <section
      v-if="activeTab === 'resources'"
      v-loading="loading || uploading"
      class="library-panel"
      data-testid="course-knowledge-base"
    >
      <header class="panel-header">
        <div><h3>知识库</h3><p>文件持久化与 RAG 索引解耦；检索失败不会影响下载和人工使用。</p></div>
      </header>
      <div v-if="resources.length" class="resource-table">
        <article v-for="resource in resources" :key="resource.id">
          <span class="resource-icon"><i class="el-icon-files"></i></span>
          <div>
            <b>{{ resource.title }}</b>
            <p>{{ resource.asset.original_filename }} · {{ sizeLabel(resource.asset.byte_size) }}</p>
          </div>
          <el-tag size="mini" :type="ingestionType(resource.ingestion_status)">
            {{ ingestionLabel(resource.ingestion_status) }}
          </el-tag>
          <span class="scope-label">{{ resource.visibility_scope === 'course_published' ? '学生可见' : '教师可见' }}</span>
          <el-button size="mini" icon="el-icon-download" @click="downloadResource(resource)">下载</el-button>
        </article>
      </div>
      <EmptyLibrary v-else icon="el-icon-folder-opened" title="知识库还没有资料" description="上传 PDF、Word、PPTX、HTML 或文本，文件会先安全保存再进入索引队列。" />
    </section>

    <el-dialog title="新建题目" :visible.sync="questionDialog" width="720px">
      <el-form label-position="top">
        <div class="two-columns">
          <el-form-item label="题目名称"><el-input v-model.trim="questionForm.title" /></el-form-item>
          <el-form-item label="知识点"><el-input v-model.trim="questionForm.knowledgePoint" placeholder="例如：情感推断" /></el-form-item>
        </div>
        <el-form-item label="题干">
          <el-input v-model="questionForm.prompt" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item label="选项（每行一个，不要输入 A/B 标签）">
          <el-input v-model="questionForm.optionsText" type="textarea" :rows="5" placeholder="选项一&#10;选项二&#10;选项三&#10;选项四" />
        </el-form-item>
        <div class="three-columns">
          <el-form-item label="答案">
            <el-select v-model="questionForm.correctAnswer" style="width:100%">
              <el-option v-for="index in 8" :key="index" :label="optionLetter(index - 1)" :value="optionLetter(index - 1)" />
            </el-select>
          </el-form-item>
          <el-form-item label="难度">
            <el-select v-model="questionForm.difficulty" style="width:100%">
              <el-option label="简单" value="easy" /><el-option label="中等" value="medium" /><el-option label="困难" value="hard" />
            </el-select>
          </el-form-item>
          <el-form-item label="分值"><el-input-number v-model="questionForm.score" :min="1" :max="100" /></el-form-item>
        </div>
        <el-form-item label="解析"><el-input v-model="questionForm.explanation" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="questionDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="createQuestion">保存草稿</el-button>
      </template>
    </el-dialog>

    <el-dialog title="从所选题目组卷" :visible.sync="paperDialog" width="560px">
      <el-form label-position="top">
        <el-form-item label="试卷名称"><el-input v-model.trim="paperForm.title" /></el-form-item>
        <div class="two-columns">
          <el-form-item label="用途">
            <el-select v-model="paperForm.purpose" style="width:100%">
              <el-option label="模拟考试" value="mock_exam" />
              <el-option label="诊断练习" value="diagnostic" />
              <el-option label="课程作业" value="assignment" />
            </el-select>
          </el-form-item>
          <el-form-item label="建议时长（分钟）"><el-input-number v-model="paperForm.duration" :min="5" :max="180" /></el-form-item>
        </div>
        <el-alert :title="`将冻结 ${selectedQuestionIds.length} 道已发布题目的当前版本`" type="info" :closable="false" />
      </el-form>
      <template #footer>
        <el-button @click="paperDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="composePaper">生成试卷草稿</el-button>
      </template>
    </el-dialog>
  </EducationShell>
</template>

<script>
import { downloadCourseAsset } from '../../api/education'
import EducationShell from '../../components/education/EducationShell.vue'
import { educationErrorMessage } from '../../utils/educationErrors'

const EmptyLibrary = {
  functional: true,
  props: ['icon', 'title', 'description'],
  render(h, context) {
    return h('div', { class: 'empty-library' }, [
      h('i', { class: context.props.icon }),
      h('h3', context.props.title),
      h('p', context.props.description),
    ])
  },
}

export default {
  name: 'KnowledgeCenter',
  components: { EducationShell, EmptyLibrary },
  data() {
    return {
      activeTab: 'questions',
      loading: false,
      uploading: false,
      saving: false,
      questionDialog: false,
      paperDialog: false,
      selectedQuestionIds: [],
      tabs: [
        { key: 'questions', label: '题库', caption: '规范题目与答案版本', icon: 'el-icon-edit-outline' },
        { key: 'papers', label: '试卷库', caption: '冻结题目版本组合', icon: 'el-icon-document' },
        { key: 'resources', label: '知识库', caption: '课程文件与 RAG', icon: 'el-icon-collection' },
      ],
      questionForm: {
        title: '',
        prompt: '',
        optionsText: '',
        correctAnswer: 'A',
        difficulty: 'easy',
        score: 5,
        knowledgePoint: '',
        explanation: '',
      },
      paperForm: { title: '', purpose: 'mock_exam', duration: 30 },
    }
  },
  computed: {
    course() { return this.$store.getters['education/activeCourse'] },
    summary() { return this.$store.getters['education/knowledgeSummary'] || { counts: {} } },
    questions() { return this.$store.getters['education/questions'] || [] },
    papers() { return this.$store.getters['education/papers'] || [] },
    resources() { return this.$store.getters['education/knowledgeResources'] || [] },
  },
  created() {
    this.bootstrap()
  },
  methods: {
    async bootstrap() {
      try {
        const courseId = this.$route.params.courseId
        const course = await this.$store.dispatch('education/ensureRoleCourse', {
          courseId,
          role: 'teacher',
        })
        await this.load(course.id)
      } catch (error) {
        this.$message.error('课程知识中心不可用')
        this.$router.replace('/education')
      }
    },
    async load(courseId = this.course && this.course.id) {
      if (!courseId) return
      this.loading = true
      try {
        await this.$store.dispatch('education/fetchKnowledgeCenter', courseId)
      } catch (error) {
        this.$message.error('知识中心加载失败')
      } finally {
        this.loading = false
      }
    },
    count(key) { return this.summary.counts[key] || 0 },
    optionLetter(index) { return String.fromCharCode(65 + index) },
    difficultyLabel(value) { return ({ easy: '简单', medium: '中等', hard: '困难' })[value] || value },
    purposeLabel(value) { return ({ mock_exam: '模拟', diagnostic: '诊断', assignment: '作业', practice: '练习' })[value] || '试卷' },
    answerLabel(question) {
      const answer = question.current_version.answer
      return answer ? answer.correct_answer : '未提供'
    },
    async createQuestion() {
      const options = this.questionForm.optionsText.split('\n').map(value => value.trim()).filter(Boolean)
      if (!this.questionForm.title || !this.questionForm.prompt || options.length < 2) {
        this.$message.warning('请填写题目名称、题干和至少两个选项')
        return
      }
      this.saving = true
      try {
        await this.$store.dispatch('education/createQuestion', {
          courseId: this.course.id,
          question: {
            title: this.questionForm.title,
            question_type: 'single_choice',
            prompt: this.questionForm.prompt,
            options,
            difficulty: this.questionForm.difficulty,
            score: this.questionForm.score,
            knowledge_points: this.questionForm.knowledgePoint ? [this.questionForm.knowledgePoint] : [],
            correct_answer: this.questionForm.correctAnswer,
            explanation: this.questionForm.explanation,
          },
        })
        this.questionDialog = false
        this.questionForm = {
          title: '', prompt: '', optionsText: '', correctAnswer: 'A',
          difficulty: 'easy', score: 5, knowledgePoint: '', explanation: '',
        }
        this.$message.success('题目草稿已保存')
      } catch (error) {
        this.$message.error('题目格式未通过校验')
      } finally {
        this.saving = false
      }
    },
    async publishQuestion(question) {
      await this.$store.dispatch('education/publishQuestion', {
        courseId: this.course.id,
        questionId: question.id,
      })
      this.$message.success('题目已发布，可用于组卷')
    },
    async composePaper() {
      if (!this.paperForm.title) {
        this.$message.warning('请输入试卷名称')
        return
      }
      this.saving = true
      try {
        await this.$store.dispatch('education/composePaper', {
          courseId: this.course.id,
          paper: {
            title: this.paperForm.title,
            purpose: this.paperForm.purpose,
            duration_minutes: this.paperForm.duration,
            item_ids: this.selectedQuestionIds,
          },
        })
        this.paperDialog = false
        this.activeTab = 'papers'
        this.selectedQuestionIds = []
        this.paperForm.title = ''
        this.$message.success('试卷草稿已冻结')
      } catch (error) {
        this.$message.error('组卷失败，请确认所选题目均已发布')
      } finally {
        this.saving = false
      }
    },
    async publishPaper(paper) {
      await this.$store.dispatch('education/publishPaper', {
        courseId: this.course.id,
        paperId: paper.id,
      })
      this.$message.success('试卷已发布给学生')
    },
    async uploadKnowledgeFile(event) {
      const file = event.target.files && event.target.files[0]
      event.target.value = ''
      if (!file) return
      this.uploading = true
      try {
        const asset = await this.$store.dispatch('education/uploadAsset', {
          courseId: this.course.id,
          file,
          title: file.name,
          purpose: 'knowledge_resource',
          visibilityScope: 'course_published',
        })
        await this.$store.dispatch('education/addKnowledgeResource', {
          courseId: this.course.id,
          resource: {
            asset_id: asset.id,
            title: file.name,
            resource_type: 'reference',
            visibility_scope: 'course_published',
          },
        })
        this.activeTab = 'resources'
        this.$message.success('资料已持久保存，等待进入检索索引')
      } catch (error) {
        this.$message.error(educationErrorMessage(error, '资料上传失败'))
      } finally {
        this.uploading = false
      }
    },
    async downloadResource(resource) {
      const blob = await downloadCourseAsset(resource.asset.id)
      const objectUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = objectUrl
      link.download = resource.asset.original_filename
      link.click()
      URL.revokeObjectURL(objectUrl)
    },
    sizeLabel(bytes) {
      if (bytes < 1024) return `${bytes} B`
      if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
      return `${(bytes / 1024 / 1024).toFixed(1)} MB`
    },
    ingestionLabel(value) {
      return ({ pending: '等待索引', processing: '索引中', ready: '可检索', failed: '索引失败' })[value] || value
    },
    ingestionType(value) {
      return ({ ready: 'success', failed: 'danger', processing: 'warning' })[value] || 'info'
    },
  },
}
</script>

<style scoped>
.visually-hidden { position: absolute; width: 1px; height: 1px; opacity: 0; pointer-events: none; }
.knowledge-summary {
  display: grid; grid-template-columns: minmax(0, 1fr) repeat(3, 105px); align-items: center;
  gap: 12px; margin-bottom: 15px; padding: 20px 24px; border: 1px solid #dce7e4;
  border-radius: 14px; background: linear-gradient(105deg, #f9fbfa, #edf5f2);
}
.summary-title > span { color: #2d8176; font-size: 9px; font-weight: 800; letter-spacing: .15em; }
.summary-title h2 { margin: 6px 0 5px; color: #293e3a; font-family: 'Noto Serif SC', 'Songti SC', SimSun, serif; font-size: 19px; }
.summary-title p { margin: 0; color: #7c8b88; font-size: 10px; line-height: 1.5; }
.summary-metric { padding: 7px 12px; border-left: 1px solid #d4e1dd; text-align: center; }
.summary-metric b, .summary-metric span { display: block; }
.summary-metric b { color: #286f67; font-family: Georgia, serif; font-size: 25px; }
.summary-metric span { color: #8b9996; font-size: 10px; }
.library-tabs { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 13px; }
.library-tabs button {
  display: grid; grid-template-columns: 35px 1fr; align-items: center; gap: 9px;
  padding: 12px; border: 1px solid #e0e8e6; border-radius: 11px; background: #fff;
  color: #6f7f7b; cursor: pointer; text-align: left;
}
.library-tabs button > i { width: 34px; height: 34px; display: grid; place-items: center; border-radius: 9px; background: #eff4f2; }
.library-tabs b, .library-tabs small { display: block; }.library-tabs b { color: #3e514d; font-size: 12px; }.library-tabs small { margin-top: 3px; color: #98a4a1; font-size: 9px; }
.library-tabs button.active { border-color: #8dbdb4; background: #f4faf8; box-shadow: inset 0 -2px #31877c; }
.library-tabs button.active > i { background: #dff0ec; color: #24796f; }
.library-panel { min-height: 430px; padding: 20px; border: 1px solid #e2e9e7; border-radius: 14px; background: #fff; }
.panel-header { display: flex; align-items: center; justify-content: space-between; padding-bottom: 14px; border-bottom: 1px solid #edf1f0; }
.panel-header h3 { margin: 0; color: #30433f; font-size: 16px; }.panel-header p { margin: 5px 0 0; color: #8d9997; font-size: 10px; }.panel-header > span { color: #43867d; font-size: 10px; }
.question-list { display: flex; flex-direction: column; }
.question-list > article { display: grid; grid-template-columns: 24px 36px 1fr auto; gap: 10px; padding: 17px 4px; border-bottom: 1px solid #edf1f0; }
.question-index { width: 31px; height: 31px; display: grid; place-items: center; border-radius: 50%; background: #edf4f2; color: #3e7f76; font-family: Georgia, serif; }
.question-body > header { display: flex; align-items: center; gap: 7px; }.question-body > header > b { color: #30413e; font-size: 12px; }.question-body > header > span { color: #8d9997; font-size: 9px; }
.question-body > p { margin: 9px 0; color: #3c4a47; font-size: 12px; line-height: 1.65; }
.option-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px 14px; margin: 0; padding: 0; list-style: none; }
.option-list li { display: flex; gap: 7px; color: #667572; font-size: 10px; }.option-list li b { color: #287d72; }
.question-body footer { display: flex; align-items: center; gap: 5px; margin-top: 10px; }
.question-body footer span { padding: 3px 7px; border-radius: 999px; background: #eef5f3; color: #588079; font-size: 8px; }
.question-body footer small { margin-left: auto; color: #9aa5a3; }
.question-actions { display: flex; align-items: flex-start; gap: 5px; }
.paper-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(235px, 1fr)); gap: 12px; padding-top: 16px; }
.paper-grid article { position: relative; min-height: 190px; padding: 20px; overflow: hidden; border: 1px solid #e1e8e6; border-radius: 12px; background: linear-gradient(145deg, #fff, #f7faf9); }
.paper-corner { position: absolute; right: -25px; top: 15px; width: 95px; padding: 4px; transform: rotate(38deg); background: #e3efec; color: #447b73; font-size: 8px; text-align: center; }
.paper-icon { width: 42px; height: 48px; display: grid; place-items: center; border: 1px solid #cfe0dc; border-radius: 6px 12px 6px 6px; background: #f1f7f5; color: #3c8177; font-size: 19px; }
.paper-grid h3 { margin: 14px 0 7px; color: #344742; font-size: 14px; }.paper-grid p { color: #84928f; font-size: 10px; }
.paper-grid footer { display: flex; align-items: center; gap: 8px; margin-top: 17px; }.paper-grid footer small { margin-left: auto; color: #98a4a1; }
.resource-table { display: flex; flex-direction: column; padding-top: 10px; }
.resource-table article { display: grid; grid-template-columns: 42px 1fr auto 75px auto; align-items: center; gap: 11px; padding: 13px 7px; border-bottom: 1px solid #edf1f0; }
.resource-icon { width: 39px; height: 39px; display: grid; place-items: center; border-radius: 10px; background: #edf4f2; color: #397e74; }
.resource-table b { color: #3b4d49; font-size: 12px; }.resource-table p { margin: 4px 0 0; color: #96a19f; font-size: 9px; }.scope-label { color: #758783; font-size: 9px; }
.empty-library { min-height: 330px; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #8b9a96; text-align: center; }
.empty-library i { font-size: 32px; color: #6f9b93; }.empty-library h3 { margin: 11px 0 5px; color: #526661; }.empty-library p { max-width: 420px; margin: 0; font-size: 10px; line-height: 1.6; }
.two-columns { display: grid; grid-template-columns: 1fr 1fr; gap: 13px; }.three-columns { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 13px; }
@media (max-width: 900px) {
  .knowledge-summary { grid-template-columns: 1fr repeat(3, 75px); }
  .summary-title p { display: none; }
}
@media (max-width: 700px) {
  .knowledge-summary { grid-template-columns: 1fr; }.summary-metric { display: none; }
  .library-tabs { grid-template-columns: 1fr; }.library-tabs small { display: none; }
  .question-list > article { grid-template-columns: 32px 1fr; }.question-list .el-checkbox, .question-actions { display: none; }
  .option-list { grid-template-columns: 1fr; }
  .resource-table article { grid-template-columns: 40px 1fr auto; }.scope-label, .resource-table .el-tag { display: none; }
}
</style>
