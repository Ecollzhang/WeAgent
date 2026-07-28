<template>
  <section class="artifact-preview" :data-role="role" data-testid="agent-artifact-preview">
    <template v-if="role === 'course_designer'">
      <header class="artifact-title">
        <div>
          <span>课程设计产物</span>
          <h3>{{ meta.title || '结构化教案草稿' }}</h3>
        </div>
        <el-tag size="mini">{{ meta.duration_minutes || '—' }} 分钟</el-tag>
      </header>
      <div class="artifact-block">
        <h4>教学目标</h4>
        <ol class="objective-list">
          <li v-for="(objective, index) in objectives" :key="objective.id || index">
            <span>{{ objective.id || index + 1 }}</span>
            <p>{{ objective.description || objective.objective || objective.text || objective }}</p>
          </li>
        </ol>
      </div>
      <ArtifactText title="教学活动" :value="output.activities" />
      <ArtifactText title="评价设计" :value="output.assessment" />
    </template>

    <template v-else-if="role === 'exercise_generator'">
      <header class="artifact-title">
        <div>
          <span>习题生成产物</span>
          <h3>{{ meta.title || '练习与评价任务' }}</h3>
          <small v-if="exercises.length">
            {{ exercises.length }} 题 · {{ meta.total_score || totalScore }} 分
            <template v-if="meta.estimated_minutes"> · 约 {{ meta.estimated_minutes }} 分钟</template>
          </small>
        </div>
        <el-tag size="mini" :type="exercises.length ? 'success' : 'danger'">
          {{ exercises.length ? '结构化题集' : '结构化失败' }}
        </el-tag>
      </header>
      <div v-if="exercises.length" class="exercise-list">
        <article v-for="(exercise, index) in exercises" :key="exercise.id || index">
          <span class="exercise-index">{{ index + 1 }}</span>
          <div class="exercise-body">
            <div class="exercise-meta">
              <el-tag size="mini" effect="plain">{{ typeLabel(exercise.type) }}</el-tag>
              <el-tag size="mini" type="info">{{ exercise.difficulty || '未标注难度' }}</el-tag>
              <span>{{ exercise.score || 0 }} 分</span>
            </div>
            <b>{{ exercise.prompt || exercise.question || exercise.title }}</b>
            <ul v-if="exercise.options && exercise.options.length" class="exercise-options">
              <li v-for="(option, optionIndex) in exercise.options" :key="optionIndex">
                {{ optionLabel(option, optionIndex) }}
              </li>
            </ul>
            <div v-if="exercise.knowledge_points && exercise.knowledge_points.length" class="knowledge-points">
              <span v-for="point in exercise.knowledge_points" :key="point">{{ point }}</span>
            </div>
            <el-collapse class="answer-panel">
              <el-collapse-item title="查看参考答案与解析" :name="exercise.id || index">
                <p v-if="exercise.answer"><b>参考答案：</b>{{ readable(exercise.answer) }}</p>
                <p v-if="exercise.explanation"><b>解析：</b>{{ readable(exercise.explanation) }}</p>
                <p v-if="exercise.common_mistakes"><b>易错提示：</b>{{ readable(exercise.common_mistakes) }}</p>
              </el-collapse-item>
            </el-collapse>
          </div>
        </article>
        <div class="exercise-actions">
          <span>转换后先保存为学习活动草稿，不会自动发布。</span>
          <el-button type="primary" plain icon="el-icon-plus" @click="$emit('add-activity', output)">
            添加到学习活动
          </el-button>
        </div>
      </div>
      <el-alert
        v-else
        title="本次运行没有生成可预览的结构化习题"
        description="旧运行中的文件路径只是沙箱回执，不是正式习题。请重新运行 Agent；新运行会强制生成并校验 exercises_draft.json。"
        type="error"
        :closable="false"
        show-icon
      />
    </template>

    <template v-else-if="role === 'teaching_reviewer'">
      <header class="artifact-title review-title">
        <div>
          <span>教学审校产物</span>
          <h3>{{ review.summary || meta.title || '审校结论' }}</h3>
        </div>
        <el-tag :type="review.verdict === '通过' ? 'success' : 'warning'" size="mini">
          {{ review.grade || review.verdict || '已审校' }}
        </el-tag>
      </header>
      <p v-if="review.recommendation" class="recommendation">{{ review.recommendation }}</p>
      <div v-if="reviewIssues.length" class="review-issues">
        <h4>修改建议</h4>
        <article v-for="(issue, index) in reviewIssues" :key="issue.id || index">
          <el-tag size="mini" :type="issue.severity === '高' ? 'danger' : 'info'">
            {{ issue.severity || '建议' }}
          </el-tag>
          <div>
            <b>{{ issue.description }}</b>
            <p>{{ issue.suggestion }}</p>
          </div>
        </article>
      </div>
    </template>

    <template v-else>
      <ArtifactText title="Agent 产物" :value="output.text || readable(output)" />
    </template>

    <el-collapse v-if="role !== 'exercise_generator' || exercises.length" class="raw-data">
      <el-collapse-item title="查看原始数据" name="raw">
        <pre>{{ formattedJson }}</pre>
      </el-collapse-item>
    </el-collapse>
  </section>
</template>

<script>
const { normalizeChoiceOption } = require('../../utils/educationContent')

const ArtifactText = {
  name: 'ArtifactText',
  functional: true,
  props: {
    title: { type: String, default: '' },
    value: { type: [String, Number, Object, Array], default: '' },
  },
  render(h, context) {
    const value = context.props.value
    const text = typeof value === 'string'
      ? value
      : JSON.stringify(value || '', null, 2)
    return h('div', { class: 'artifact-block' }, [
      h('h4', context.props.title),
      h('div', { class: 'artifact-rich-text' }, text),
    ])
  },
}

export default {
  name: 'AgentArtifactPreview',
  components: { ArtifactText },
  props: {
    role: { type: String, required: true },
    output: { type: Object, default: () => ({}) },
  },
  computed: {
    meta() { return this.output.meta || {} },
    objectives() {
      return Array.isArray(this.output.objectives) ? this.output.objectives : []
    },
    exercises() {
      const candidates = [
        this.output.questions,
        this.output.exercises,
        this.output.items,
      ]
      return candidates.find(Array.isArray) || []
    },
    totalScore() {
      return this.exercises.reduce((total, item) => total + Number(item.score || 0), 0)
    },
    review() { return this.output.overall_evaluation || {} },
    reviewIssues() {
      const value = this.output.issues_and_suggestions
      return value && Array.isArray(value.items) ? value.items : []
    },
    formattedJson() {
      return JSON.stringify(this.output || {}, null, 2)
    },
  },
  methods: {
    readable(value) {
      return typeof value === 'string' ? value : JSON.stringify(value)
    },
    typeLabel(value) {
      const labels = {
        choice: '选择题',
        single_choice: '单选题',
        multiple_choice: '多选题',
        fill_blank: '填空题',
        short_answer: '简答题',
        writing: '写作题',
      }
      return labels[value] || value || '练习题'
    },
    optionLabel(option, index) {
      return normalizeChoiceOption(option, index)
    },
  },
}
</script>

<style scoped>
.artifact-preview {
  grid-column: 2 / -1;
  margin-top: 12px;
  padding: 18px;
  border: 1px solid #dbe7e5;
  border-radius: 12px;
  background: linear-gradient(145deg, #fff, #f7fbfa);
}
.artifact-title { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; }
.artifact-title span { color: #71838a; font-size: 11px; letter-spacing: .08em; text-transform: uppercase; }
.artifact-title h3 { margin: 4px 0 0; color: #24434a; font-family: Georgia, 'Noto Serif SC', serif; font-size: 17px; }
.artifact-title small { display: block; margin-top: 6px; color: #71838a; }
.artifact-block { margin-top: 17px; }
.artifact-block h4, .review-issues h4 { margin: 0 0 9px; color: #3d5b61; font-size: 12px; }
.artifact-rich-text { color: #53666d; white-space: pre-wrap; line-height: 1.75; }
.objective-list { display: grid; gap: 8px; margin: 0; padding: 0; list-style: none; }
.objective-list li { display: grid; grid-template-columns: 42px 1fr; gap: 9px; align-items: start; }
.objective-list li > span { padding: 3px 6px; border-radius: 5px; background: #e7f3f0; color: #277c72; font-size: 10px; text-align: center; }
.objective-list p { margin: 0; color: #455961; line-height: 1.65; }
.exercise-list { display: grid; gap: 10px; margin-top: 16px; }
.exercise-list article { display: grid; grid-template-columns: 30px 1fr; gap: 12px; padding: 15px; border: 1px solid #e2e9eb; border-radius: 10px; background: #fff; }
.exercise-index { display: grid; width: 27px; height: 27px; place-items: center; border-radius: 50%; background: #edf5f3; color: #277c72; font-weight: 700; }
.exercise-list b { color: #344b52; }
.exercise-list p, .exercise-list small { display: block; margin: 6px 0 0; color: #687a81; line-height: 1.6; }
.exercise-meta { display: flex; align-items: center; gap: 7px; margin-bottom: 9px; }
.exercise-meta > span { color: #7b8a93; font-size: 11px; }
.exercise-options { display: grid; gap: 6px; margin: 12px 0; padding: 0; color: #53666d; line-height: 1.6; list-style: none; }
.knowledge-points { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.knowledge-points span { padding: 3px 7px; border-radius: 12px; background: #eef5f4; color: #4b746f; font-size: 10px; }
.answer-panel { margin-top: 12px; }
.exercise-actions { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 13px 15px; border: 1px dashed #b9d8d3; border-radius: 9px; background: #f3faf8; }
.exercise-actions span { color: #71838a; font-size: 11px; }
.recommendation { margin: 14px 0 0; padding: 12px; border-left: 3px solid #3f9c8e; background: #edf7f4; color: #45615f; line-height: 1.7; }
.review-issues { margin-top: 17px; }
.review-issues article { display: grid; grid-template-columns: auto 1fr; gap: 10px; margin-top: 9px; padding: 11px 0; border-top: 1px solid #e5ecee; }
.review-issues b { color: #455961; font-size: 12px; }
.review-issues p { margin: 5px 0 0; color: #73838a; line-height: 1.65; }
.raw-data { margin-top: 16px; }
.raw-data pre { max-height: 320px; overflow: auto; padding: 13px; border-radius: 8px; background: #1f2933; color: #d8e5e2; font-size: 11px; white-space: pre-wrap; }
</style>
