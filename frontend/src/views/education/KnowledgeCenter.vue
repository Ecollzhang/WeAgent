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
        icon="el-icon-cpu"
        @click="questionAgentDialog = true"
      >AI 生成题目</el-button>
      <el-button
        v-if="activeTab === 'questions'"
        icon="el-icon-reading"
        @click="stimulusDialog = true"
      >新建阅读材料</el-button>
      <el-button
        v-if="activeTab === 'questions'"
        type="primary"
        icon="el-icon-plus"
        @click="openQuestionDialog()"
      >新建题目</el-button>
      <el-button
        v-if="activeTab === 'papers'"
        icon="el-icon-cpu"
        @click="paperAgentDialog = true"
      >AI 智能组卷</el-button>
      <el-button
        v-if="activeTab === 'papers'"
        type="primary"
        icon="el-icon-document-add"
        :disabled="!selectedQuestionIds.length"
        @click="paperDialog = true"
      >从所选题目组卷</el-button>
      <el-button
        v-if="activeTab === 'resources'"
        icon="el-icon-search"
        @click="researchDialog = true"
      >联网补充资料</el-button>
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

    <ProductAgentRunPanel
      :run="productAgentRun"
      @terminal="handleAgentTerminal"
      @close="closeAgentRun"
    />

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
      <div v-if="stimulusGroups.length" class="stimulus-groups">
        <article v-for="group in stimulusGroups" :key="group.id" class="stimulus-card">
          <header>
            <div>
              <span>阅读材料 · {{ group.current_version.word_or_character_count }} {{ group.current_version.language === 'en' ? '词' : '字' }}</span>
              <h3>{{ group.title }}</h3>
              <p>{{ sourceLabel(group) }}</p>
            </div>
            <div class="stimulus-actions">
              <el-tag size="mini" :type="group.status === 'published' ? 'success' : 'info'">
                {{ group.status === 'published' ? '材料已发布' : '材料草稿' }}
              </el-tag>
              <el-button v-if="group.status !== 'published'" size="mini" @click="publishStimulus(group)">发布材料</el-button>
              <el-button size="mini" type="primary" plain @click="openQuestionDialog(null, group)">添加子题</el-button>
            </div>
          </header>
          <el-collapse>
            <el-collapse-item title="展开阅读材料全文" :name="group.id">
              <div class="stimulus-text">
                <p v-for="(paragraph, index) in stimulusParagraphs(group)" :key="index">{{ paragraph }}</p>
              </div>
            </el-collapse-item>
          </el-collapse>
          <div class="group-question-list">
            <article v-for="(question, index) in groupedQuestions(group)" :key="question.id">
              <el-checkbox v-model="selectedQuestionIds" :label="question.id" :disabled="question.status !== 'published'"><span></span></el-checkbox>
              <span>{{ index + 1 }}</span>
              <div><b>{{ typeLabel(question.current_version.question_type) }} · {{ question.title }}</b><p>{{ question.current_version.prompt }}</p></div>
              <el-button size="mini" type="text" @click="openQuestionDialog(question, group)">编辑</el-button>
              <el-button v-if="question.status !== 'published' || question.current_version_id !== question.published_version_id" size="mini" type="text" @click="publishQuestion(question)">发布此版本</el-button>
            </article>
            <p v-if="!groupedQuestions(group).length" class="group-empty">材料已保存。点击“添加子题”建立一篇材料对应多道问题的题组。</p>
          </div>
        </article>
      </div>
      <h4 v-if="stimulusGroups.length && standaloneQuestions.length" class="standalone-heading">独立题目</h4>
      <div v-if="standaloneQuestions.length" class="question-list">
        <article v-for="(question, index) in standaloneQuestions" :key="question.id">
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
            <el-button size="mini" @click="openQuestionDialog(question)">编辑</el-button>
            <el-button
              v-if="question.status !== 'published' || question.current_version_id !== question.published_version_id"
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
      <EmptyLibrary v-if="!questions.length && !stimulusGroups.length" icon="el-icon-edit-outline" title="题库还是空的" description="创建阅读材料题组、独立题目，或让习题 Agent 写入可审核草稿。" />
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
            <el-button size="mini" type="text" @click="previewPaper(paper)">预览</el-button>
            <el-button size="mini" type="text" @click="editPaper(paper)">编辑</el-button>
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

    <el-dialog :title="editingQuestion ? '编辑题目并创建新版本' : '新建题目'" :visible.sync="questionDialog" width="760px" custom-class="education-dialog education-dialog--editor">
      <el-form label-position="top">
        <div class="two-columns">
          <el-form-item label="题目名称"><el-input v-model.trim="questionForm.title" /></el-form-item>
          <el-form-item label="知识点"><el-input v-model.trim="questionForm.knowledgePoint" placeholder="例如：情感推断" /></el-form-item>
        </div>
        <div class="two-columns">
          <el-form-item label="题目类型">
            <el-select v-model="questionForm.questionType" style="width:100%" @change="normalizeQuestionAnswer">
              <el-option v-for="option in questionTypeOptions" :key="option.value" :label="option.label" :value="option.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="所属材料">
            <el-select v-model="questionForm.stimulusVersionId" clearable style="width:100%" placeholder="独立题目">
              <el-option v-for="stimulus in stimuli" :key="stimulus.current_version_id" :label="stimulus.title" :value="stimulus.current_version_id" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="题干">
          <el-input v-model="questionForm.prompt" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item v-if="isChoiceQuestion" label="选项（每行一个，不要输入 A/B 标签）">
          <el-input v-model="questionForm.optionsText" type="textarea" :rows="5" placeholder="选项一&#10;选项二&#10;选项三&#10;选项四" />
        </el-form-item>
        <div class="three-columns">
          <el-form-item label="答案">
            <el-select v-if="questionForm.questionType === 'single_choice'" v-model="questionForm.correctAnswer" style="width:100%">
              <el-option v-for="index in 8" :key="index" :label="optionLetter(index - 1)" :value="optionLetter(index - 1)" />
            </el-select>
            <el-select v-else-if="questionForm.questionType === 'multiple_choice'" v-model="questionForm.correctAnswer" multiple style="width:100%">
              <el-option v-for="index in 8" :key="index" :label="optionLetter(index - 1)" :value="optionLetter(index - 1)" />
            </el-select>
            <el-select v-else-if="questionForm.questionType === 'true_false'" v-model="questionForm.correctAnswer" style="width:100%">
              <el-option label="正确" :value="true" /><el-option label="错误" :value="false" />
            </el-select>
            <el-input v-else v-model="questionForm.correctAnswer" placeholder="标准答案或参考作答" />
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
        <el-button type="primary" :loading="saving" @click="createQuestion">{{ editingQuestion ? '保存新版本' : '保存草稿' }}</el-button>
      </template>
    </el-dialog>

    <el-dialog title="新建阅读材料" :visible.sync="stimulusDialog" width="760px" custom-class="education-dialog education-dialog--editor">
      <el-form label-position="top">
        <div class="two-columns">
          <el-form-item label="材料标题"><el-input v-model.trim="stimulusForm.title" /></el-form-item>
          <el-form-item label="语言"><el-select v-model="stimulusForm.language" style="width:100%"><el-option label="英语" value="en" /><el-option label="中文" value="zh" /></el-select></el-form-item>
        </div>
        <el-form-item label="正文（按段落换行）"><el-input v-model="stimulusForm.text" type="textarea" :rows="10" /></el-form-item>
        <div class="two-columns">
          <el-form-item label="来源标题"><el-input v-model.trim="stimulusForm.sourceTitle" /></el-form-item>
          <el-form-item label="作者"><el-input v-model.trim="stimulusForm.author" /></el-form-item>
        </div>
        <el-form-item label="来源链接"><el-input v-model.trim="stimulusForm.sourceUrl" /></el-form-item>
        <el-form-item label="权利说明"><el-input v-model.trim="stimulusForm.rights" placeholder="公共领域、CC 许可或教师提供" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="stimulusDialog = false">取消</el-button><el-button type="primary" :loading="saving" @click="createStimulus">保存材料草稿</el-button></template>
    </el-dialog>

    <el-dialog :title="editingPaper ? '编辑试卷并创建新版本' : '从所选题目组卷'" :visible.sync="paperDialog" width="620px" custom-class="education-dialog">
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
        <el-button type="primary" :loading="saving" @click="composePaper">{{ editingPaper ? '保存试卷新版本' : '生成试卷草稿' }}</el-button>
      </template>
    </el-dialog>

    <el-dialog title="试卷预览" :visible.sync="paperPreviewDialog" width="900px" custom-class="education-dialog education-dialog--preview">
      <div class="preview-toolbar"><el-radio-group v-model="previewMode" size="mini" @change="reloadPaperPreview"><el-radio-button label="student">学生视图</el-radio-button><el-radio-button label="teacher">教师视图（含答案）</el-radio-button></el-radio-group></div>
      <div v-if="paperPreview" class="paper-preview">
        <header><h2>{{ paperPreview.paper.title }}</h2><p>{{ paperPreview.paper.current_version.duration_minutes }} 分钟 · {{ paperPreview.paper.current_version.total_score }} 分 · v{{ paperPreview.paper.current_version.version_number }}</p></header>
        <section v-for="stimulus in paperPreview.stimuli" :key="stimulus.id" class="preview-stimulus"><h3>{{ stimulus.title }}</h3><p v-for="(paragraph, index) in (stimulus.content.paragraphs || [])" :key="index">{{ paragraph }}</p></section>
        <article v-for="(question, index) in paperPreview.questions" :key="question.id" class="preview-question"><h4>{{ index + 1 }}. {{ question.prompt }} <small>{{ question.score }} 分</small></h4><ol v-if="question.options.length"><li v-for="(option, optionIndex) in question.options" :key="optionIndex">{{ optionLetter(optionIndex) }}. {{ option }}</li></ol><div v-if="question.answer" class="preview-answer">答案：{{ question.answer.correct_answer }}<br>{{ question.answer.explanation }}</div></article>
      </div>
      <template #footer><el-button @click="paperPreviewDialog = false">关闭</el-button></template>
    </el-dialog>

    <el-dialog title="AI 生成题目" :visible.sync="questionAgentDialog" width="560px">
      <el-form label-position="top">
        <div class="two-columns">
          <el-form-item label="题目数量"><el-input-number v-model="questionAgentForm.questionCount" :min="1" :max="30" /></el-form-item>
          <el-form-item label="难度">
            <el-select v-model="questionAgentForm.difficulty" style="width:100%">
              <el-option label="简单" value="easy" /><el-option label="中等" value="medium" /><el-option label="困难" value="hard" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="知识点"><el-input v-model.trim="questionAgentForm.knowledgePoint" placeholder="例如：文本证据、人物情感推断" /></el-form-item>
        <el-form-item label="补充要求"><el-input v-model="questionAgentForm.requirements" type="textarea" :rows="3" /></el-form-item>
        <el-alert title="Agent 只写入题库草稿，不会自动发布答案给学生。" type="info" :closable="false" />
      </el-form>
      <template #footer>
        <el-button @click="questionAgentDialog = false">取消</el-button>
        <el-button type="primary" :loading="agentRunning" @click="startQuestionAgent">启动 Agent 团队</el-button>
      </template>
    </el-dialog>

    <el-dialog title="AI 智能组卷" :visible.sync="paperAgentDialog" width="560px">
      <el-form label-position="top">
        <el-form-item label="试卷名称"><el-input v-model.trim="paperAgentForm.title" /></el-form-item>
        <div class="two-columns">
          <el-form-item label="题目数量"><el-input-number v-model="paperAgentForm.questionCount" :min="1" :max="30" /></el-form-item>
          <el-form-item label="建议时长"><el-input-number v-model="paperAgentForm.duration" :min="5" :max="180" /></el-form-item>
        </div>
        <el-alert title="只从已发布题目中冻结版本；题量不足时 Agent 会报告缺口。" type="info" :closable="false" />
      </el-form>
      <template #footer>
        <el-button @click="paperAgentDialog = false">取消</el-button>
        <el-button type="primary" :loading="agentRunning" @click="startPaperAgent">启动 Agent 团队</el-button>
      </template>
    </el-dialog>

    <el-dialog title="联网补充课程资料" :visible.sync="researchDialog" width="760px">
      <el-form label-position="top">
        <el-form-item label="搜索主题"><el-input v-model.trim="researchForm.query" placeholder="输入课程主题、课文或知识点" /></el-form-item>
        <el-form-item label="来源许可说明"><el-input v-model.trim="researchForm.licenseNote" placeholder="例如：CC BY 4.0 / 公共领域 / 已获教学使用许可" /></el-form-item>
        <el-checkbox v-model="researchForm.teacherConfirmedRights" class="rights-check">
          我已核对所选来源的许可与教学使用权；系统将重新抓取正文，不会把搜索摘要当作全文。
        </el-checkbox>
        <div class="research-actions">
          <el-button :loading="researching" icon="el-icon-search" @click="searchWebResources">搜索并读取正文</el-button>
          <el-button type="primary" :loading="agentRunning" icon="el-icon-cpu" @click="startKnowledgeAgent">让 Agent 搜索并采纳</el-button>
        </div>
      </el-form>
      <div v-if="researchDiagnostics.length" class="research-diagnostics">
        搜索链路已记录 {{ researchDiagnostics.length }} 条 fallback / 抓取诊断。
      </div>
      <div class="research-results">
        <article v-for="result in researchResults" :key="result.url">
          <div><b>{{ result.title }}</b><small>{{ result.url }}</small><p>{{ result.search_excerpt || '已读取正文，搜索服务未提供摘要。' }}</p></div>
          <el-button size="mini" type="primary" plain @click="adoptResearchResult(result)">采纳为教师资料</el-button>
        </article>
      </div>
    </el-dialog>
  </EducationShell>
</template>

<script>
import { downloadCourseAsset } from '../../api/education'
import EducationShell from '../../components/education/EducationShell.vue'
import ProductAgentRunPanel from '../../components/education/ProductAgentRunPanel.vue'
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
  components: { EducationShell, EmptyLibrary, ProductAgentRunPanel },
  data() {
    return {
      activeTab: 'questions',
      loading: false,
      uploading: false,
      saving: false,
      questionDialog: false,
      stimulusDialog: false,
      paperDialog: false,
      paperPreviewDialog: false,
      previewMode: 'student',
      paperPreview: null,
      previewingPaper: null,
      editingQuestion: null,
      editingPaper: null,
      questionAgentDialog: false,
      paperAgentDialog: false,
      researchDialog: false,
      researching: false,
      researchResults: [],
      researchDiagnostics: [],
      selectedQuestionIds: [],
      tabs: [
        { key: 'questions', label: '题库', caption: '规范题目与答案版本', icon: 'el-icon-edit-outline' },
        { key: 'papers', label: '试卷库', caption: '冻结题目版本组合', icon: 'el-icon-document' },
        { key: 'resources', label: '知识库', caption: '课程文件与 RAG', icon: 'el-icon-collection' },
      ],
      questionForm: {
        title: '',
        questionType: 'single_choice',
        stimulusVersionId: '',
        stimulusOrder: 1,
        prompt: '',
        optionsText: '',
        correctAnswer: 'A',
        difficulty: 'easy',
        score: 5,
        knowledgePoint: '',
        explanation: '',
      },
      stimulusForm: { title: '', language: 'en', text: '', sourceTitle: '', author: '', sourceUrl: '', rights: '' },
      paperForm: { title: '', purpose: 'mock_exam', duration: 30 },
      questionAgentForm: { questionCount: 5, difficulty: 'medium', knowledgePoint: '', requirements: '' },
      paperAgentForm: { title: '课程诊断试卷', questionCount: 5, duration: 30 },
      researchForm: { query: '', licenseNote: '', teacherConfirmedRights: false },
    }
  },
  computed: {
    course() { return this.$store.getters['education/activeCourse'] },
    summary() { return this.$store.getters['education/knowledgeSummary'] || { counts: {} } },
    questions() { return this.$store.getters['education/questions'] || [] },
    stimuli() { return this.$store.getters['education/stimuli'] || [] },
    stimulusGroups() {
      return this.stimuli
    },
    standaloneQuestions() {
      return this.questions.filter(question => !(question.current_version && question.current_version.stimulus_version_id))
    },
    questionTypeOptions() {
      return [
        { value: 'single_choice', label: '单项选择' },
        { value: 'multiple_choice', label: '多项选择' },
        { value: 'true_false', label: '判断题' },
        { value: 'fill_blank', label: '填空题' },
        { value: 'short_answer', label: '简答题' },
        { value: 'writing', label: '写作任务' },
      ]
    },
    isChoiceQuestion() { return ['single_choice', 'multiple_choice'].includes(this.questionForm.questionType) },
    papers() { return this.$store.getters['education/papers'] || [] },
    resources() { return this.$store.getters['education/knowledgeResources'] || [] },
    productAgentRun() { return this.$store.getters['education/productAgentRun'] },
    agentRunning() { return Boolean(this.productAgentRun && ['pending', 'running'].includes(this.productAgentRun.status)) },
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
        await this.$store.dispatch('education/restoreProductAgentRun', { courseId })
      } catch (error) {
        this.$message.error('知识中心加载失败')
      } finally {
        this.loading = false
      }
    },
    count(key) { return this.summary.counts[key] || 0 },
    async startQuestionAgent() {
      const started = await this.startKnowledgeProduct('question_generation', {
        question_count: this.questionAgentForm.questionCount,
        difficulty: this.questionAgentForm.difficulty,
        knowledge_points: this.questionAgentForm.knowledgePoint ? [this.questionAgentForm.knowledgePoint] : [],
        requirements: this.questionAgentForm.requirements,
      })
      if (started) this.questionAgentDialog = false
    },
    async startPaperAgent() {
      if (!this.paperAgentForm.title) return this.$message.warning('请输入试卷名称')
      const started = await this.startKnowledgeProduct('paper_generation', {
        title: this.paperAgentForm.title,
        question_count: this.paperAgentForm.questionCount,
        duration_minutes: this.paperAgentForm.duration,
      })
      if (started) this.paperAgentDialog = false
    },
    async startKnowledgeAgent() {
      if (!this.validResearchForm()) return
      const started = await this.startKnowledgeProduct('knowledge_research', {
        query: this.researchForm.query,
        license_note: this.researchForm.licenseNote,
        teacher_confirmed_rights: true,
      })
      if (started) this.researchDialog = false
    },
    async startKnowledgeProduct(productCode, options) {
      try {
        await this.$store.dispatch('education/startProductAgentRun', {
          course_id: this.course.id,
          product_code: productCode,
          options,
        })
        this.$message.success('Agent 团队已启动，进度会显示在知识中心')
        return true
      } catch (error) {
        const data = error.response && error.response.data
        this.$message.error((data && data.error) || 'Agent 启动失败')
        return false
      }
    },
    validResearchForm() {
      if (!this.researchForm.query || !this.researchForm.licenseNote || !this.researchForm.teacherConfirmedRights) {
        this.$message.warning('请填写搜索主题、许可说明并确认使用权')
        return false
      }
      return true
    },
    async searchWebResources() {
      if (!this.validResearchForm()) return
      this.researching = true
      try {
        const result = await this.$store.dispatch('education/searchResources', {
          course_id: this.course.id,
          query: this.researchForm.query,
          limit: 6,
        })
        this.researchResults = result.results || []
        this.researchDiagnostics = result.diagnostics || []
        if (!this.researchResults.length) this.$message.warning('搜索 provider 已完成 fallback，但没有可采纳正文')
      } catch (error) {
        this.$message.error('联网搜索失败')
      } finally {
        this.researching = false
      }
    },
    async adoptResearchResult(result) {
      if (!this.validResearchForm()) return
      try {
        await this.$store.dispatch('education/adoptWebKnowledgeResource', {
          courseId: this.course.id,
          resource: {
            url: result.url,
            title: result.title,
            search_excerpt: result.search_excerpt || '',
            license_note: this.researchForm.licenseNote,
            teacher_confirmed_rights: this.researchForm.teacherConfirmedRights,
          },
        })
        this.activeTab = 'resources'
        this.$message.success('网页正文已重新抓取并保存为教师可见知识资料')
      } catch (error) {
        const data = error.response && error.response.data
        this.$message.error((data && (data.error_code || data.error)) || '资料采纳失败')
      }
    },
    async handleAgentTerminal(run) {
      if (run.status === 'completed') await this.load(this.course.id)
    },
    closeAgentRun() {
      this.$store.commit('education/SET_PRODUCT_AGENT_RUN', null)
    },
    optionLetter(index) { return String.fromCharCode(65 + index) },
    typeLabel(value) { return (this.questionTypeOptions.find(row => row.value === value) || {}).label || value },
    difficultyLabel(value) { return ({ easy: '简单', medium: '中等', hard: '困难' })[value] || value },
    purposeLabel(value) { return ({ mock_exam: '模拟', diagnostic: '诊断', assignment: '作业', practice: '练习' })[value] || '试卷' },
    answerLabel(question) {
      const answer = question.current_version.answer
      return answer ? answer.correct_answer : '未提供'
    },
    groupedQuestions(stimulus) {
      const versionId = stimulus && stimulus.current_version_id
      return this.questions
        .filter(question => question.current_version && question.current_version.stimulus_version_id === versionId)
        .sort((left, right) => (left.current_version.stimulus_order || 0) - (right.current_version.stimulus_order || 0))
    },
    stimulusParagraphs(stimulus) {
      const content = stimulus && stimulus.current_version && stimulus.current_version.content
      return (content && content.paragraphs) || []
    },
    sourceLabel(stimulus) {
      const refs = stimulus && stimulus.current_version && stimulus.current_version.source_refs
      if (!refs || !refs.length) return '教师提供材料'
      const source = refs[0]
      return [source.author, source.title, source.rights].filter(Boolean).join(' · ')
    },
    emptyQuestionForm() {
      return {
        title: '', questionType: 'single_choice', stimulusVersionId: '', stimulusOrder: 1,
        prompt: '', optionsText: '', correctAnswer: 'A', difficulty: 'easy', score: 5,
        knowledgePoint: '', explanation: '',
      }
    },
    openQuestionDialog(question = null, stimulus = null) {
      this.editingQuestion = question
      if (!question) {
        this.questionForm = this.emptyQuestionForm()
        if (stimulus) {
          this.questionForm.stimulusVersionId = stimulus.current_version_id
          this.questionForm.stimulusOrder = this.groupedQuestions(stimulus).length + 1
        }
      } else {
        const version = question.current_version || {}
        const answer = version.answer && version.answer.correct_answer
        this.questionForm = {
          title: question.title,
          questionType: version.question_type,
          stimulusVersionId: version.stimulus_version_id || '',
          stimulusOrder: version.stimulus_order || 1,
          prompt: version.prompt || '',
          optionsText: (version.options || []).join('\n'),
          correctAnswer: Array.isArray(answer) ? [...answer] : answer,
          difficulty: version.difficulty || 'easy',
          score: version.score || 5,
          knowledgePoint: (version.knowledge_points || []).join('、'),
          explanation: (version.answer && version.answer.explanation) || '',
        }
      }
      this.normalizeQuestionAnswer()
      this.questionDialog = true
    },
    editQuestion(question) {
      this.openQuestionDialog(question)
    },
    normalizeQuestionAnswer() {
      const type = this.questionForm.questionType
      if (type === 'multiple_choice' && !Array.isArray(this.questionForm.correctAnswer)) this.questionForm.correctAnswer = []
      else if (type === 'true_false' && typeof this.questionForm.correctAnswer !== 'boolean') this.questionForm.correctAnswer = true
      else if (type === 'single_choice' && typeof this.questionForm.correctAnswer !== 'string') this.questionForm.correctAnswer = 'A'
      else if (['fill_blank', 'short_answer', 'writing'].includes(type) && typeof this.questionForm.correctAnswer !== 'string') this.questionForm.correctAnswer = ''
    },
    async createStimulus() {
      const paragraphs = this.stimulusForm.text.split(/\n\s*\n|\n/).map(value => value.trim()).filter(Boolean)
      if (!this.stimulusForm.title || !paragraphs.length) return this.$message.warning('请填写材料标题和正文')
      const sourceRefs = this.stimulusForm.sourceTitle || this.stimulusForm.sourceUrl ? [{
        title: this.stimulusForm.sourceTitle || this.stimulusForm.title,
        author: this.stimulusForm.author,
        url: this.stimulusForm.sourceUrl,
        rights: this.stimulusForm.rights || '教师已核对教学使用权',
      }] : []
      this.saving = true
      try {
        await this.$store.dispatch('education/createStimulus', {
          courseId: this.course.id,
          stimulus: { title: this.stimulusForm.title, stimulus_type: 'reading_passage', language: this.stimulusForm.language, content: { paragraphs }, source_refs: sourceRefs },
        })
        this.stimulusDialog = false
        this.stimulusForm = { title: '', language: 'en', text: '', sourceTitle: '', author: '', sourceUrl: '', rights: '' }
        this.$message.success('阅读材料草稿已保存，可继续添加多道子题')
      } catch (error) {
        this.$message.error('阅读材料未通过校验')
      } finally { this.saving = false }
    },
    async publishStimulus(stimulus) {
      await this.$store.dispatch('education/publishStimulus', { courseId: this.course.id, stimulusId: stimulus.id })
      this.$message.success('阅读材料已发布')
    },
    async createQuestion() {
      const options = this.questionForm.optionsText.split('\n').map(value => value.trim()).filter(Boolean)
      if (!this.questionForm.title || !this.questionForm.prompt || (this.isChoiceQuestion && options.length < 2)) {
        this.$message.warning('请填写题目名称、题干；选择题至少需要两个选项')
        return
      }
      this.saving = true
      try {
        const payload = {
          title: this.questionForm.title,
          question_type: this.questionForm.questionType,
          prompt: this.questionForm.prompt,
          options: this.isChoiceQuestion ? options : [],
          difficulty: this.questionForm.difficulty,
          score: this.questionForm.score,
          knowledge_points: this.questionForm.knowledgePoint ? this.questionForm.knowledgePoint.split(/[、,，]/).map(value => value.trim()).filter(Boolean) : [],
          correct_answer: this.questionForm.correctAnswer,
          explanation: this.questionForm.explanation,
          stimulus_version_id: this.questionForm.stimulusVersionId || null,
          stimulus_order: this.questionForm.stimulusVersionId ? this.questionForm.stimulusOrder : null,
          rubric: ['short_answer', 'writing'].includes(this.questionForm.questionType) ? { evidence: 2, explanation: 2 } : {},
        }
        await this.$store.dispatch(this.editingQuestion ? 'education/saveQuestionVersion' : 'education/createQuestion', {
          courseId: this.course.id,
          ...(this.editingQuestion ? { questionId: this.editingQuestion.id } : {}),
          question: payload,
        })
        this.questionDialog = false
        this.questionForm = this.emptyQuestionForm()
        this.editingQuestion = null
        this.$message.success('题目草稿版本已保存；重新发布前学生仍使用旧版本')
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
        await this.$store.dispatch(this.editingPaper ? 'education/savePaperVersion' : 'education/composePaper', {
          courseId: this.course.id,
          ...(this.editingPaper ? { paperId: this.editingPaper.id } : {}),
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
        this.editingPaper = null
        this.$message.success('试卷草稿已冻结')
      } catch (error) {
        this.$message.error('组卷失败，请确认所选题目均已发布')
      } finally {
        this.saving = false
      }
    },
    editPaper(paper) {
      this.editingPaper = paper
      this.paperForm = { title: paper.title, purpose: paper.purpose, duration: paper.current_version.duration_minutes }
      const frozen = new Set(paper.current_version.item_version_ids || [])
      this.selectedQuestionIds = this.questions.filter(question => frozen.has(question.published_version_id) || frozen.has(question.current_version_id)).map(question => question.id)
      this.paperDialog = true
    },
    async previewPaper(paper) {
      this.previewingPaper = paper
      this.previewMode = 'student'
      this.paperPreviewDialog = true
      await this.reloadPaperPreview()
    },
    async reloadPaperPreview() {
      if (!this.previewingPaper) return
      try {
        this.paperPreview = await this.$store.dispatch('education/fetchPaperPreview', { paperId: this.previewingPaper.id, mode: this.previewMode })
      } catch (error) {
        this.paperPreview = null
        this.$message.error('试卷预览加载失败')
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
.stimulus-groups { display: grid; gap: 14px; margin: 15px 0 20px; }
.stimulus-card { padding: 18px; border: 1px solid #d4e4e0; border-radius: 14px; background: linear-gradient(145deg, #fff, #f7fbfa); }
.stimulus-card > header { display: flex; justify-content: space-between; gap: 18px; }
.stimulus-card > header span { color: #3a8177; font-size: 9px; font-weight: 700; letter-spacing: .08em; }
.stimulus-card h3 { margin: 5px 0; color: #2e4540; font-size: 16px; }.stimulus-card > header p { margin: 0; color: #899692; font-size: 9px; }
.stimulus-actions { display: flex; align-items: flex-start; gap: 7px; }
.stimulus-text { max-height: 330px; overflow-y: auto; padding: 13px 16px; border-radius: 9px; background: #f9faf7; color: #40504c; font-size: 12px; line-height: 1.8; }
.stimulus-text p { margin: 0 0 10px; }.group-question-list { margin-top: 8px; border-top: 1px solid #e5ecea; }
.group-question-list > article { display: grid; grid-template-columns: 24px 26px minmax(0, 1fr) auto auto; gap: 9px; align-items: start; padding: 12px 3px; border-bottom: 1px solid #edf1f0; }
.group-question-list b { color: #344a45; font-size: 11px; }.group-question-list p { margin: 4px 0 0; color: #677974; font-size: 11px; line-height: 1.55; }
.group-empty { margin: 12px 0 0; color: #8b9995; font-size: 10px; }.standalone-heading { margin: 18px 0 4px; color: #4d635e; }
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
.preview-toolbar { display: flex; justify-content: flex-end; margin-bottom: 14px; }.paper-preview { color: #263b37; }
.paper-preview > header { padding: 16px 20px; border-radius: 12px; background: #eef5f3; text-align: center; }.paper-preview > header h2 { margin: 0; }
.preview-stimulus { margin: 16px 0; padding: 18px 22px; border: 1px solid #dfe7e4; border-radius: 10px; background: #fffdf8; line-height: 1.8; }
.preview-stimulus h3 { margin-top: 0; }.preview-question { padding: 14px 8px; border-bottom: 1px solid #e8edeb; }.preview-question h4 { margin: 0 0 9px; line-height: 1.55; }.preview-question h4 small { float: right; color: #71827e; }
.preview-question ol { display: grid; gap: 5px; margin: 0; padding-left: 28px; }.preview-answer { margin-top: 10px; padding: 10px; border-radius: 8px; background: #eef7f3; color: #356a61; font-size: 11px; line-height: 1.6; }
:deep(.education-dialog) { display: flex; flex-direction: column; max-width: calc(100vw - 24px); max-height: calc(100vh - 64px); margin-top: 32px !important; border-radius: 16px; overflow: hidden; }
:deep(.education-dialog .el-dialog__header), :deep(.education-dialog .el-dialog__footer) { flex: 0 0 auto; padding: 20px 24px; }
:deep(.education-dialog .el-dialog__body) { flex: 1 1 auto; min-height: 0; overflow-y: auto; padding: 20px 24px; }
.resource-table { display: flex; flex-direction: column; padding-top: 10px; }
.resource-table article { display: grid; grid-template-columns: 42px 1fr auto 75px auto; align-items: center; gap: 11px; padding: 13px 7px; border-bottom: 1px solid #edf1f0; }
.resource-icon { width: 39px; height: 39px; display: grid; place-items: center; border-radius: 10px; background: #edf4f2; color: #397e74; }
.resource-table b { color: #3b4d49; font-size: 12px; }.resource-table p { margin: 4px 0 0; color: #96a19f; font-size: 9px; }.scope-label { color: #758783; font-size: 9px; }
.empty-library { min-height: 330px; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #8b9a96; text-align: center; }
.empty-library i { font-size: 32px; color: #6f9b93; }.empty-library h3 { margin: 11px 0 5px; color: #526661; }.empty-library p { max-width: 420px; margin: 0; font-size: 10px; line-height: 1.6; }
.two-columns { display: grid; grid-template-columns: 1fr 1fr; gap: 13px; }.three-columns { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 13px; }
.rights-check { display: flex; align-items: flex-start; white-space: normal; line-height: 1.6; }
.research-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 18px; }
.research-diagnostics { margin: 16px 0 8px; padding: 9px 12px; border-radius: 8px; background: #f4f7f8; color: #75848a; font-size: 11px; }
.research-results { display: grid; gap: 9px; max-height: 360px; overflow-y: auto; margin-top: 12px; }
.research-results article { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 16px; padding: 13px; border: 1px solid #dfe8e5; border-radius: 10px; background: #f9fbfa; }
.research-results b, .research-results small { display: block; }
.research-results b { color: #334b46; }
.research-results small { margin-top: 3px; overflow: hidden; color: #85928f; font-size: 9px; text-overflow: ellipsis; white-space: nowrap; }
.research-results p { margin: 7px 0 0; color: #687a76; font-size: 11px; line-height: 1.55; }
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
