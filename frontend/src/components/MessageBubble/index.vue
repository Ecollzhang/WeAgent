<template>
  <div class="message-bubble" :class="{ own: isOwn }">
    <div class="bubble-sender" v-if="message.sender_type === 'agent'">
      <span class="agent-tag">{{ getSenderName() }}</span>
      <span v-if="providerLabel" class="provider-tag">{{ providerLabel }}</span>
      <span v-if="message.status" class="status-tag" :class="'status-' + message.status">
        {{ statusLabel(message.status) }}
      </span>
      <el-button
        v-if="canStop"
        type="text"
        size="mini"
        icon="el-icon-close"
        class="stop-btn"
        @click="$emit('stop-agent')"
        title="停止 Agent"
      ></el-button>
    </div>
    <div class="bubble-inner">
      <div v-if="currentProgress" class="current-progress">
        <span class="progress-dot" :class="'progress-' + (currentProgress.status || 'running')"></span>
        <span class="current-progress-label">当前进度</span>
        <span class="current-progress-text">{{ elementContent(currentProgress) }}</span>
      </div>

      <div v-if="visibleRawOutput" class="raw-rendered">
        <div class="raw-rendered-content" v-html="renderMarkdown(visibleRawOutput)"></div>
      </div>

      <div v-if="contentElements.length" class="bubble-elements content-section">
        <template v-for="(el, i) in cardGroupedElements">
          <!-- Card group with collapse (only for requirement/bug cards with > 1 items) -->
          <div v-if="el._group" :key="'g'+i" class="card-group" :class="'cg-' + el.type">
            <div class="card-group-header" @click="$set(collapsedCardGroups, el._groupId, !collapsedCardGroups[el._groupId])">
              <span class="cg-arrow" :class="{ 'cg-collapsed': collapsedCardGroups[el._groupId] }">▾</span>
              <span class="cg-label">{{ cardGroupLabelMap[el.type] }}</span>
              <span class="cg-count">{{ el.count }}</span>
            </div>
            <div v-show="!collapsedCardGroups[el._groupId]" class="card-group-body">
              <div
                v-for="(card, ci) in el.cards"
                :key="ci"
                class="el-block"
                :class="'el-' + card.type"
              >
                <!-- inline requirement card -->
                <div v-if="card.type === 'requirement_card'" class="domain-card requirement-card" @click="navigateToDomain(card)">
                  <div class="dc-row dc-main-row">
                    <span class="dc-domain-tag">研发</span>
                    <span class="dc-type-tag">需求</span>
                    <span class="dc-title">{{ cardTitle(card) }}</span>
                    <span class="dc-priority-tag" :class="'pri-' + cardPriority(card)">{{ cardPriorityLabel(card) }}</span>
                    <span class="dc-status-tag" :class="'req-status-' + cardStatus(card)">{{ cardReqStatusLabel(card) }}</span>
                    <span class="dc-arrow">→</span>
                  </div>
                  <div class="dc-row dc-meta-row" v-if="cardMetaItems(card).length">
                    <span v-for="m in cardMetaItems(card)" :key="m.label" class="dc-meta-item">
                      <i :class="m.icon"></i> {{ m.label }}: {{ m.value }}
                    </span>
                  </div>
                </div>
                <!-- inline bug card -->
                <div v-else-if="card.type === 'bug_card'" class="domain-card bug-card" @click="navigateToDomain(card)">
                  <div class="dc-row dc-main-row">
                    <span class="dc-domain-tag">研发</span>
                    <span class="dc-type-tag bug-type-tag">缺陷</span>
                    <span class="dc-title">{{ cardTitle(card) }}</span>
                    <span class="dc-severity-tag" :class="'sev-' + cardSeverity(card)">{{ cardSeverityLabel(card) }}</span>
                    <span class="dc-status-tag" :class="'bug-status-' + cardStatus(card)">{{ cardBugStatusLabel(card) }}</span>
                    <span class="dc-arrow">→</span>
                  </div>
                  <div class="dc-row dc-meta-row" v-if="cardMetaItems(card).length">
                    <span v-for="m in cardMetaItems(card)" :key="m.label" class="dc-meta-item">
                      <i :class="m.icon"></i> {{ m.label }}: {{ m.value }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Non-group elements (original rendering) -->
          <div
            v-else
            :key="'s'+i"
            class="el-block"
            :class="'el-' + el.type"
          >
            <!-- Text / Output / Result / Summary -->
            <div v-if="el.type === 'text' || el.type === 'output' || el.type === 'result' || el.type === 'summary'" class="el-text" v-html="renderText(elementContent(el))"></div>

            <!-- Progress element -->
            <div v-else-if="el.type === 'progress'" class="el-progress">
              <span class="progress-dot" :class="'progress-' + (el.status || 'running')"></span>
              <span>{{ elementContent(el) }}</span>
            </div>

            <div v-else-if="el.type === 'error'" class="el-error">
              <div class="error-title">
                <i class="el-icon-warning-outline"></i>
                <span>{{ elementData(el).title || '错误' }}</span>
              </div>
              <div class="error-content" v-html="renderText(elementContent(el))"></div>
            </div>

            <!-- Requirement Card -->
            <div v-else-if="el.type === 'requirement_card'" class="domain-card requirement-card" @click="navigateToDomain(el)">
              <div class="dc-row dc-main-row">
                <span class="dc-domain-tag">研发</span>
                <span class="dc-type-tag">需求</span>
                <span class="dc-title">{{ cardTitle(el) }}</span>
                <span class="dc-priority-tag" :class="'pri-' + cardPriority(el)">{{ cardPriorityLabel(el) }}</span>
                <span class="dc-status-tag" :class="'req-status-' + cardStatus(el)">{{ cardReqStatusLabel(el) }}</span>
                <span class="dc-arrow">→</span>
              </div>
              <div class="dc-row dc-meta-row" v-if="cardMetaItems(el).length">
                <span v-for="m in cardMetaItems(el)" :key="m.label" class="dc-meta-item">
                  <i :class="m.icon"></i> {{ m.label }}: {{ m.value }}
                </span>
              </div>
            </div>

            <!-- Bug Card -->
            <div v-else-if="el.type === 'bug_card'" class="domain-card bug-card" @click="navigateToDomain(el)">
              <div class="dc-row dc-main-row">
                <span class="dc-domain-tag">研发</span>
                <span class="dc-type-tag bug-type-tag">缺陷</span>
                <span class="dc-title">{{ cardTitle(el) }}</span>
                <span class="dc-severity-tag" :class="'sev-' + cardSeverity(el)">{{ cardSeverityLabel(el) }}</span>
                <span class="dc-status-tag" :class="'bug-status-' + cardStatus(el)">{{ cardBugStatusLabel(el) }}</span>
                <span class="dc-arrow">→</span>
              </div>
              <div class="dc-row dc-meta-row" v-if="cardMetaItems(el).length">
                <span v-for="m in cardMetaItems(el)" :key="m.label" class="dc-meta-item">
                  <i :class="m.icon"></i> {{ m.label }}: {{ m.value }}
                </span>
              </div>
            </div>

            <!-- Iteration Card -->
            <div v-else-if="el.type === 'iteration_card'" class="domain-card iteration-card" @click="navigateToDomain(el)">
              <div class="dc-header">
                <span class="dc-domain-tag">智能研发</span>
                <span class="dc-type-tag iteration-type-tag">迭代</span>
                <span class="dc-status-tag" :class="'iter-status-' + cardStatus(el)">{{ cardIterStatusLabel(el) }}</span>
              </div>
              <div class="dc-body">
                <div class="dc-title">{{ cardTitle(el) }}</div>
                <div class="dc-summary" v-if="cardSummary(el)">{{ cardSummary(el) }}</div>
                <div class="dc-iter-progress" v-if="cardIterProgress(el) !== null">
                  <div class="dc-progress-bar">
                    <div class="dc-progress-fill" :style="{ width: cardIterProgress(el) + '%' }"></div>
                  </div>
                  <span class="dc-progress-text">{{ cardIterProgress(el) }}%</span>
                </div>
              </div>
              <div class="dc-meta" v-if="cardMetaItems(el).length">
                <span v-for="m in cardMetaItems(el)" :key="m.label" class="dc-meta-item">
                  <i :class="m.icon"></i> {{ m.label }}: {{ m.value }}
                </span>
              </div>
              <div class="dc-actions">
                <el-button size="mini" type="primary" @click.stop="navigateToDomain(el)">查看详情 →</el-button>
              </div>
            </div>

            <!-- Project Card -->
            <div v-else-if="el.type === 'project_card'" class="domain-card project-card" @click="navigateToDomain(el)">
              <div class="dc-header">
                <span class="dc-domain-tag">智能研发</span>
                <span class="dc-type-tag project-type-tag">项目</span>
              </div>
              <div class="dc-body">
                <div class="dc-title">{{ cardTitle(el) }}</div>
                <div class="dc-summary" v-if="cardSummary(el)">{{ cardSummary(el) }}</div>
                <div class="dc-project-stats" v-if="cardProjectStats(el).length">
                  <span v-for="s in cardProjectStats(el)" :key="s.label" class="dc-project-stat">
                    <span class="dc-stat-num">{{ s.value }}</span>
                    <span class="dc-stat-label">{{ s.label }}</span>
                  </span>
                </div>
              </div>
              <div class="dc-actions">
                <el-button size="mini" type="primary" @click.stop="navigateToDomain(el)">查看项目 →</el-button>
              </div>
            </div>

          </div>
        </template>
      </div>

      <!-- Artifact rendering -->
      <div v-if="artifactElements.length" class="bubble-elements artifact-section">
        <div class="artifact-section-header">
          <div class="section-title">产物</div>
          <button class="preview-toggle-chip" @click="togglePreviewVisibility">
            <span>显示所有预览</span>
            <span class="preview-toggle-box" :class="{ checked: showAllPreviews }">
              <i v-if="showAllPreviews" class="el-icon-check"></i>
            </span>
          </button>
        </div>
        <div
          v-for="group in artifactGroups"
          :key="group.key"
          class="artifact-group"
          :data-artifact-group-key="group.key"
        >
          <div v-if="isSummaryTableGroup(group)" class="artifact-summary-wrap">
            <div class="artifact-summary-title">文件清单</div>
            <div>
              <div class="table-meta-row summary-table-meta-row">
                <span class="table-meta-summary">{{ artifactGroupTableRowCount(group) }} rows</span>
                <span class="table-meta-summary">{{ artifactGroupTableHeaders(group).length }} cols</span>
              </div>
              <div class="table-scroll summary-table-scroll summary-table-plain">
                <el-table
                  v-if="artifactGroupTableHeaders(group).length"
                  :data="artifactGroupTableRows(group)"
                  size="small"
                  border
                  stripe
                  style="width: 100%"
                >
                  <el-table-column
                    v-if="shouldShowSummaryIndexColumn(group)"
                    type="index"
                    label="序号"
                    width="72"
                  ></el-table-column>
                  <el-table-column
                    v-for="(h, hi) in artifactGroupTableHeaders(group)"
                    :key="hi"
                    :prop="'col' + hi"
                    :label="h"
                    min-width="140"
                  ></el-table-column>
                </el-table>
                <div v-else class="el-text" v-html="renderText(elementContent(group.tableElement || group.primaryElement))"></div>
              </div>
            </div>
          </div>

          <template v-else>
          <div class="artifact-file-row" :class="{ 'summary-file-row': isSummaryTableGroup(group) }" @click="openArtifactGroup(group)">
            <div class="artifact-file-mainline" @click.stop="toggleArtifactGroup(group.key)">
              <button
                class="artifact-toggle-btn"
              >
                <i :class="isArtifactGroupExpanded(group.key, group) ? 'el-icon-arrow-down' : 'el-icon-arrow-right'"></i>
              </button>
              <div class="file-icon"><i :class="fileIcon(group.fileElement || group.primaryElement)"></i></div>
              <div class="file-main">
                <div class="file-info-row">
                  <div class="file-info-stack">
                    <div class="file-title-line">
                      <button class="file-link-btn">{{ artifactGroupName(group) }}</button>
                    </div>
                    <div class="file-meta-line">
                      <span class="file-path">{{ artifactGroupSubtitle(group) }}</span>
                    </div>
                  </div>
                  <div class="file-attr-group">
                    <span class="artifact-kind-chip">{{ artifactGroupKindLabel(group) }}</span>
                    <span v-if="artifactGroupSizeText(group)" class="file-size-inline-text">{{ artifactGroupSizeText(group) }}</span>
                  </div>
                  <div class="artifact-row-actions" @click.stop>
                    <el-button
                      v-if="canCopyArtifactGroup(group)"
                      size="mini"
                      type="text"
                      class="artifact-action-btn"
                      @click="copyArtifactGroup(group)"
                    >复制</el-button>
                    <el-button
                      v-if="canPreviewArtifactGroup(group)"
                      size="mini"
                      type="text"
                      class="artifact-action-btn"
                      @click="openArtifactGroup(group, group.type === 'workflow' ? 'preview' : 'edit')"
                    >{{ group.type === 'workflow' ? '预览' : '编辑' }}</el-button>
                  </div>
                </div>
                <div v-if="artifactGroupResolvedDiff(group)" class="file-diff-inline-row" :data-diff-row-key="group.key" @click.stop>
                  <div class="file-diff-inline-main">
                    <div class="file-diff-label">变更</div>
                    <div class="file-diff-stats">
                      <span class="diff-stat diff-add">+{{ diffAdditions(artifactGroupResolvedDiff(group)) }}</span>
                      <span class="diff-stat diff-del">-{{ diffDeletions(artifactGroupResolvedDiff(group)) }}</span>
                    </div>
                  </div>
                  <div class="file-diff-actions">
                    <template v-if="supportsInlineArtifactDiff(group)">
                      <el-button
                        size="mini"
                        type="text"
                        class="artifact-action-btn"
                        @click="toggleArtifactDiff(group.key)"
                      >{{ isArtifactDiffVisible(group.key) ? '收起Diff' : '展示Diff' }}</el-button>
                      <el-button
                        size="mini"
                        type="text"
                        :loading="diffBusyKey === group.key"
                        class="artifact-action-btn"
                        :disabled="!canRevertArtifactGroup(group)"
                        @click="revertArtifactDiff(group)"
                      >撤销</el-button>
                    </template>
                    <span v-else class="file-diff-note">详情请在工作台查看</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

            <div v-if="isArtifactGroupExpanded(group.key, group)" class="artifact-detail-pane">
            <div v-if="group.type === 'workflow'" class="artifact-block artifact-detail-card code-card detail-card">
              <pre class="code-body"><code>{{ workflowRawJson(group) }}</code></pre>
            </div>

            <div v-else-if="group.type === 'code' || group.type === 'text'" class="artifact-block artifact-detail-card code-card detail-card">
              <div v-if="isArtifactGroupPreviewLoading(group)" class="artifact-inline-loading"><i class="el-icon-loading"></i> 加载中...</div>
              <template v-else>
                <pre class="code-body"><code>{{ artifactGroupCodeContent(group) }}</code></pre>
              </template>
                <div v-if="supportsInlineArtifactDiff(group) && artifactGroupResolvedDiff(group) && isArtifactDiffVisible(group.key)" class="artifact-attached-diff">
                  <DiffViewCard
                    :element="artifactGroupResolvedDiff(group)"
                    :session-id="sessionId"
                    compact
                    @applied="onWorkbenchDiffApplied"
                  />
              </div>
            </div>

            <div v-else-if="group.type === 'webpage'" class="artifact-block artifact-detail-card webpage-card detail-card">
              <div v-if="artifactGroupPath(group)" class="file-path webpage-path">{{ artifactGroupPath(group) }}</div>
              <div class="webpage-preview">
                <iframe
                  v-if="!isWorkbenchPreviewingPath(artifactGroupPath(group))"
                  class="webpage-frame"
                  :src="webpagePreviewSrc(group)"
                  title="webpage-preview"
                ></iframe>
                <div v-else class="webpage-preview-paused">已在统一编辑平台中打开</div>
              </div>
            </div>

            <div v-else-if="group.type === 'table'" class="artifact-block artifact-detail-card table-block detail-card" :class="{ 'summary-table-card': isSummaryTableGroup(group) }">
              <div class="table-meta-row">
                <span class="table-meta-summary">{{ artifactGroupTableRowCount(group) }} rows</span>
                <span class="table-meta-summary">{{ artifactGroupTableHeaders(group).length }} cols</span>
              </div>
              <div class="table-scroll">
                <div v-if="isArtifactGroupPreviewLoading(group)" class="artifact-inline-loading"><i class="el-icon-loading"></i> 加载中...</div>
                <el-table
                  v-else-if="artifactGroupTableHeaders(group).length"
                  :data="artifactGroupTableRows(group)"
                  size="small"
                  border
                  stripe
                  style="width: 100%"
                >
                  <el-table-column
                    v-for="(h, hi) in artifactGroupTableHeaders(group)"
                    :key="hi"
                    :prop="'col' + hi"
                    :label="h"
                    min-width="120"
                  ></el-table-column>
                </el-table>
                <div v-else class="el-text" v-html="renderText(artifactGroupCodeContent(group))"></div>
              </div>
            </div>

            <div v-else-if="group.type === 'image'" class="artifact-block artifact-detail-card image-block detail-card">
              <div class="image-frame">
                <img
                  class="artifact-image artifact-image-compact"
                  :src="imageSrc(group.imageElement || group.fileElement)"
                  :alt="artifactGroupName(group)"
                  @click="openArtifactGroup(group)"
                />
              </div>
            </div>

            <div v-else-if="group.type === 'diff'" class="artifact-block artifact-detail-card diff-card detail-card">
              <DiffViewCard
                :element="artifactGroupResolvedDiff(group)"
                :session-id="sessionId"
                @applied="onWorkbenchDiffApplied"
              />
            </div>
          </div>
          </template>
        </div>
      </div>

      <el-collapse v-if="historySteps.length" class="steps-collapse">
        <el-collapse-item :title="`进度（${historySteps.length}）`" name="steps">
          <div class="steps-panel">
            <div v-for="(step, index) in historySteps" :key="index" class="step-item">
              <span class="step-dot" :class="'step-' + step.statusClass"></span>
              <div class="step-main">
                <div class="step-title">{{ step.title }}</div>
                <button
                  v-if="step.path"
                  class="step-file"
                  @click="emitOpenFilePath(step.path)"
                >
                  {{ normalizeWorkspacePath(step.path) }}
                </button>
              </div>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>

      <!-- Fallback: render content as HTML (backward compat) -->
      <div v-if="!visibleRawOutput && !contentElements.length && !artifactElements.length" class="bubble-content" v-html="renderedContent"></div>

      <!-- Meta bar -->
      <el-collapse v-if="message.sender_type === 'agent' && message.raw_output && showRawSource" class="raw-collapse">
        <el-collapse-item title="Raw output" name="raw">
          <pre class="raw-output">{{ message.raw_output }}</pre>
        </el-collapse-item>
      </el-collapse>

      <div v-if="message.status === 'streaming'" class="streaming-line">
        <i class="el-icon-loading"></i>
        <span>输出中...</span>
      </div>

      <div class="bubble-meta">
        <span class="bubble-time">{{ formatTime(message.created_at) }}</span>
        <span v-if="selectedWorkflowLabel" class="message-workflow-tag">
          工作流：{{ selectedWorkflowLabel }}
        </span>
        <span v-if="isTempMessage" class="bubble-sending">
          <i class="el-icon-loading"></i> 发送中...
        </span>
        <el-button
          type="text"
          size="mini"
          icon="el-icon-rank"
          @click="$emit('pin')"
          :title="message.is_pinned ? '取消置顶' : '置顶'"
          :class="{ pinned: message.is_pinned }"
        ></el-button>
      </div>
    </div>

    <!-- Artifact link -->
    <div v-if="message.artifact" class="artifact-link">
      <el-tag size="mini" type="success" @click="showArtifact">
        {{ message.artifact.artifact_type }}: {{ message.artifact.title }}
      </el-tag>
    </div>

    <ArtifactWorkbench
      v-if="workbenchVisible && workbenchArtifact"
      :visible.sync="workbenchVisible"
      :artifact="workbenchArtifact"
      :session-id="sessionId"
      @saved="onWorkbenchSaved"
      @diff-applied="onWorkbenchDiffApplied"
    />

    <el-dialog
      title="服务预览"
      :visible.sync="servicePreviewVisible"
      width="86%"
      top="5vh"
      custom-class="service-preview-dialog"
    >
      <div class="service-preview-toolbar">
        <span>{{ servicePreviewUrl }}</span>
        <el-button size="mini" type="text" icon="el-icon-position" @click="openUrl(servicePreviewUrl)">新窗口打开</el-button>
      </div>
      <iframe v-if="servicePreviewUrl" class="service-preview-frame" :src="servicePreviewUrl"></iframe>
    </el-dialog>

    <el-dialog
      title="服务日志"
      :visible.sync="serviceLogsVisible"
      width="760px"
      top="8vh"
      custom-class="service-logs-dialog"
    >
      <div class="service-logs-body" v-loading="serviceLogsLoading">
        <div class="service-logs-meta" v-if="serviceLogsData">
          <el-tag size="mini">{{ serviceLogsData.service_id }}</el-tag>
          <el-tag size="mini" :type="serviceStatusType(serviceLogsData.status)">{{ serviceStatusLabel(serviceLogsData.status) }}</el-tag>
        </div>
        <div class="service-log-section">
          <div class="service-log-title">stdout</div>
          <pre>{{ serviceLogsData?.stdout_tail || '暂无输出' }}</pre>
        </div>
        <div class="service-log-section">
          <div class="service-log-title">stderr</div>
          <pre>{{ serviceLogsData?.stderr_tail || '暂无错误输出' }}</pre>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { formatTime } from '../../utils/format'
import { getFileTree, getSessionRawFileUrl, getWorkspaceFileUrl, getServiceLogs, restartService, stopService, writeFile } from '@/api/sandbox'
import ArtifactWorkbench from '@/components/ArtifactWorkbench/index.vue'
import DiffViewCard from '@/components/DiffViewCard/index.vue'
import { checkVisible } from '../../store/modules/grayscale'

export default {
  name: 'MessageBubble',
  components: { ArtifactWorkbench, DiffViewCard },
  props: {
    message: Object,
    isOwn: Boolean,
    sessionId: { type: String, default: '' },
  },
  data() {
    return {
      workbenchVisible: false,
      workbenchArtifact: null,
      artifactExpanded: {},
      artifactDiffExpanded: {},
      showAllPreviews: true,
      artifactPreviewCache: {},
      artifactPreviewLoading: {},
      artifactMetaLoading: {},
      diffBusyKey: '',

      servicePreviewVisible: false,
      servicePreviewUrl: '',
      serviceLogsVisible: false,
      serviceLogsLoading: false,
      serviceLogsData: null,
      serviceBusyKey: '',

      collapsedCardGroups: {},
    }
  },
  watch: {
    artifactGroups: {
      handler() {
        this.$nextTick(() => {
          this.ensureVisibleArtifactPreviews()
        })
      },
      immediate: true,
      deep: false,
    },
    showAllPreviews() {
      this.$nextTick(() => this.ensureVisibleArtifactPreviews())
    },
  },
  computed: {
    hasElements() {
      return this.message && Array.isArray(this.message.elements) && this.message.elements.length > 0
    },
    activeDomain() {
      return this.$store.getters['workspace/activeDomain']
    },
    visibleDomainCards() {
      const domain = this.activeDomain
      const s = this.$store.state.grayscale
      const visible = new Set()
      if (checkVisible(s, domain, 'ui.chat.card.requirement')) visible.add('requirement_card')
      if (checkVisible(s, domain, 'ui.chat.card.bug')) visible.add('bug_card')
      if (checkVisible(s, domain, 'ui.chat.card.iteration')) visible.add('iteration_card')
      if (checkVisible(s, domain, 'ui.chat.card.project')) visible.add('project_card')
      return visible
    },
    cardGroupedElements() {
      const domainTypes = ['requirement_card', 'bug_card', 'iteration_card', 'project_card']
      const raw = this.contentElements
      const result = []
      let i = 0
      while (i < raw.length) {
        const el = raw[i]
        if (!domainTypes.includes(el?.type)) {
          result.push(el)
          i++
          continue
        }
        // Collect consecutive same-type cards
        const groupType = el.type
        const group = []
        while (i < raw.length && raw[i]?.type === groupType) {
          group.push(raw[i])
          i++
        }
        if (group.length === 1) {
          result.push(group[0])
        } else {
          const groupId = `${groupType}_${i}`
          result.push({ _group: true, _groupId: groupId, type: groupType, cards: group, count: group.length })
        }
      }
      return result
    },
    cardGroupLabelMap() {
      return {
        requirement_card: '需求',
        bug_card: '缺陷',
        iteration_card: '迭代',
        project_card: '项目'
      }
    },
    providerLabel() {
      const provider = this.message?.meta?.provider || this.latestEventProvider()
      if (!provider) return ''
      const key = String(provider).toLowerCase()
      if (key === 'codex') return 'Codex'
      if (key === 'opencode') return 'OpenCode'
      if (key === 'claude' || key === 'claude_code') return 'Claude Code'
      return provider
    },
    renderedElements() {
      const elements = Array.isArray(this.message?.elements) ? this.message.elements : []
      const merged = []
      const seenContent = new Set()
      elements.forEach(el => {
        if (this.shouldHideRawTextElement(el)) return
        // Dedup: skip elements whose content we've already seen
        // (backend may send same content as text + result + output)
        const elNorm = this.normalizeDisplayText(this.elementContent(el))
        if (elNorm && elNorm.length >= 20 && ['text', 'result', 'output', 'summary'].includes(el?.type)) {
          if (seenContent.has(elNorm)) return
          seenContent.add(elNorm)
        }
        const last = merged[merged.length - 1]
        if (el?.type === 'text' && last?.type === 'text') {
          const content = this.elementContent(last) + this.elementContent(el)
          merged[merged.length - 1] = { ...last, content, data: { ...(last.data || {}), content } }
        } else {
          merged.push(el)
        }
      })
      return merged
    },
    contentElements() {
      const domainCardTypes = ['requirement_card', 'bug_card', 'iteration_card', 'project_card']
      const allowedCards = this.visibleDomainCards
      const isDomainCard = type => domainCardTypes.includes(type)

      // When raw_output is the primary display, hide ALL text/result/output/summary
      // elements — they are derived from the same LLM output and would be duplicates.
      // Only errors (genuinely new information) and visible domain cards should still show.
      if (this.visibleRawOutput) {
        return this.renderedElements.filter(el => {
          if (el?.type === 'error') return true
          if (isDomainCard(el?.type)) return allowedCards.has(el?.type)
          return false
        })
      }
      return this.renderedElements.filter(el => {
        const baseTypes = ['text', 'summary', 'result', 'error', 'output']
        if (baseTypes.includes(el?.type)) return true
        if (isDomainCard(el?.type)) return allowedCards.has(el?.type)
        return false
      })
    },
    progressElements() {
      return this.renderedElements.filter(el => el?.type === 'progress')
    },
    currentProgress() {
      const list = this.progressElements
      const latestEventProgress = this.latestEventProgress
      if (!list.length) return latestEventProgress
      const latest = list[list.length - 1]
      if (this.isPlaceholderProgress(latest) && latestEventProgress) {
        return latestEventProgress
      }
      return latest
    },
    latestEventProgress() {
      const events = this.executionEvents
      for (let i = events.length - 1; i >= 0; i--) {
        const event = events[i] || {}
        const title = event.title || event.data?.message || event.data?.content || ''
        if (title && title !== '正在处理...') {
          return {
            type: 'progress',
            content: title,
            status: this.eventProgressStatus(event),
            data: event.data || {},
          }
        }
      }
      return null
    },
    artifactElements() {
      const artifacts = this.renderedElements.filter(el => {
        if (this.isModeratorPlanArtifact(el)) return false
        return ['code', 'webpage', 'table', 'image', 'file', 'service', 'workflow'].includes(el?.type) || this.looksLikeDiffElement(el)
      })
      const seen = new Set()
      return artifacts.filter(el => {
        const key = this.artifactKey(el)
        if (seen.has(key)) return false
        seen.add(key)
        return true
      })
    },
    artifactGroups() {
      const groups = new Map()
      this.artifactElements.forEach((el, index) => {
        const normalizedPath = this.normalizeWorkspacePath(this.elementWorkspacePath(el) || '')
        const fallbackKey = `${el?.type || 'artifact'}:${index}`
        const key = normalizedPath || fallbackKey
        if (!groups.has(key)) {
          groups.set(key, {
            key,
            path: normalizedPath,
            firstIndex: index,
            fileElement: null,
            codeElement: null,
            webpageElement: null,
            tableElement: null,
            imageElement: null,
            diffElement: null,
            workflowElement: null,
            primaryElement: el,
          })
        }
        const group = groups.get(key)
        if (el.type === 'file' && !group.fileElement) group.fileElement = el
        if ((el.type === 'code' || el.type === 'text') && !group.codeElement) group.codeElement = el
        if (el.type === 'webpage' && !group.webpageElement) group.webpageElement = el
        if (el.type === 'table' && !group.tableElement) group.tableElement = el
        if (el.type === 'image' && !group.imageElement) group.imageElement = el
        if (el.type === 'workflow' && !group.workflowElement) group.workflowElement = el
        if (this.looksLikeDiffElement(el) && !group.diffElement) group.diffElement = el
      })
      return Array.from(groups.values())
        .map(group => ({
          ...group,
          type: this.artifactGroupType(group),
          primaryElement: this.artifactGroupPrimaryElement(group),
        }))
        .filter(group => {
          // Hide groups that represent non-existent files.
          // These have no edit button — they are file-type groups with no
          // actual content (agent mentioned a file but didn't create it).
          if (this.isSummaryTableGroup(group)) return true
          if (group.diffElement) return true
          if (['workflow', 'code', 'webpage', 'table', 'image'].includes(group.type)) return true
          return false
        })
        .sort((a, b) => {
          const aSummary = this.isSummaryTableGroup(a)
          const bSummary = this.isSummaryTableGroup(b)
          if (aSummary && !bSummary) return 1
          if (!aSummary && bSummary) return -1
          return (a.firstIndex || 0) - (b.firstIndex || 0)
        })
    },
    isTempMessage() {
      return this.message && typeof this.message.id === 'string' && this.message.id.startsWith('temp_')
    },
    selectedWorkflowLabel() {
      if (!this.message || this.message.sender_type !== 'user') return ''
      const workflow = this.message.meta && this.message.meta.selected_workflow
      if (!workflow || typeof workflow !== 'object') return ''
      const name = workflow.name || '未命名工作流'
      const nodeCount = Array.isArray(workflow.nodes) ? workflow.nodes.length : 0
      const edgeCount = Array.isArray(workflow.edges) ? workflow.edges.length : 0
      return `${name}（${nodeCount} 节点 · ${edgeCount} 连线）`
    },
    canStop() {
      return this.message
        && this.message.sender_type === 'agent'
        && ['pending', 'streaming'].includes(this.message.status)
        && this.message.sender_id !== 'system'
    },
    renderedContent() {
      if (!this.message || !this.message.content) return ''
      return this.renderMarkdown(this.message.content)
    },
    visibleRawOutput() {
      // Raw output is the PRIMARY display for agent messages.
      // When raw_output exists, contentElements hides all text/result/output/summary
      // to prevent duplication (see contentElements computed).
      if (!this.message || this.message.sender_type !== 'agent') return ''
      const raw = String(this.message.raw_output || '').trim()
      if (!raw) return ''
      const output = this.artifactElements.some(el => el?.type === 'table') ? this.stripMarkdownTables(raw) : raw
      return this.formatRawOutputForDisplay(output)
    },
    showRawSource() {
      return false
    },
    executionEvents() {
      return this.message?.meta?.events || []
    },
    completedProgressElements() {
      return this.progressElements.filter(el => (el.status || 'running') !== 'running')
    },
    historySteps() {
      const progressSteps = this.completedProgressElements.map(el => ({
        title: this.elementContent(el) || this.elementData(el).title || '步骤完成',
        statusClass: el.status || 'done',
        path: this.elementData(el).path || this.elementData(el).file || '',
      }))
      const eventSteps = this.executionEvents
        .filter(event => event?.type !== 'agent_progress')
        .map(event => ({
          title: event.title || event.type || '执行步骤',
          statusClass: event.type || 'event',
          path: event.data?.file || event.data?.path || '',
        }))
      return [...progressSteps, ...eventSteps]
    },
  },
  mounted() {
    this.ensureVisibleArtifactPreviews()
  },
  methods: {
    formatTime,
    formatRawOutputForDisplay(raw) {
      const text = String(raw || '').trim()
      if (!text) return ''
      if (!this.isModeratorPlanRaw(text)) return text
      return `主持人任务分派 JSON\n\n\`\`\`json\n${text.replace(/```/g, '`\\`\\`')}\n\`\`\``
    },
    isModeratorPlanRaw(text) {
      const raw = String(text || '').trim()
      const lowered = raw.toLowerCase()
      if (!raw.startsWith('{') && !raw.startsWith('```')) return false
      if (!/["']?tasks["']?\s*:/.test(lowered)) return false
      return /["']?type["']?\s*:\s*["']?plan/.test(lowered) ||
        /["']?parallel_groups["']?\s*:/.test(lowered) ||
        /["']?selected_agents["']?\s*:/.test(lowered)
    },
    isModeratorPlanArtifact(el) {
      if (!el || el.type === 'workflow') return false
      const data = this.elementData(el)
      const values = [
        data.path,
        data.file_path,
        data.filePath,
        data.file,
        data.url,
        data.src,
        data.name,
        data.filename,
        data.title,
        this.elementContent(el),
      ]
      return values.some(value => String(value || '').toLowerCase().includes('moderator-plan.json'))
    },
    isPlaceholderProgress(el) {
      const text = this.normalizeDisplayText(this.elementContent(el))
      return text === '正在处理' || text === '正在处理...'
    },
    eventProgressStatus(event) {
      const type = event?.type || ''
      if (type.includes('completed') || type === 'provider_output' || type === 'claude_output') return 'done'
      if (type.includes('error')) return 'error'
      if (type.includes('stopped')) return 'stopped'
      return 'running'
    },
    escapeHtml(text) {
      const div = document.createElement('div')
      div.textContent = text
      return div.innerHTML
    },
    getSenderName() {
      return this.message.sender_name || this.message.sender?.name || this.message.sender_id || '智能体'
    },
    statusLabel(status) {
      return {
        pending: '等待中',
        streaming: '执行中',
        done: '完成',
        error: '错误',
        stopped: '已停止',
      }[status] || status
    },
    latestEventProvider() {
      const events = Array.isArray(this.message?.meta?.events) ? this.message.meta.events : []
      for (let i = events.length - 1; i >= 0; i--) {
        const event = events[i] || {}
        const provider = event.provider || event.data?.provider
        if (provider) return provider
      }
      return ''
    },
    showArtifact() {
      this.$emit('show-artifact', this.message.artifact)
    },
    artifactKey(el) {
      const data = this.elementData(el)
      return [
        this.looksLikeDiffElement(el) ? 'diff' : (el?.type || ''),
        data.url || '',
        data.proxy_url || '',
        data.service_id || '',
        data.id || '',
        data.path || '',
        data.data?.path || '',
        data.file || '',
        data.data?.file || '',
        data.name || '',
        data.title || '',
        data.diff_text || '',
        this.elementContent(el).slice(0, 160),
      ].join('|')
    },
    artifactGroupType(group) {
      if (group.workflowElement) return 'workflow'
      if (group.webpageElement) return 'webpage'
      if (group.tableElement) return 'table'
      if (group.imageElement || (group.fileElement && this.isImageElement(group.fileElement))) return 'image'
      if (group.codeElement) return 'code'
      const path = this.artifactGroupPath(group)
      if (/\.csv$/i.test(path)) return 'table'
      if (/\.(html?)$/i.test(path)) return 'webpage'
      if (/\.(txt|log)$/i.test(path)) return 'text'
      if (/\.(css|scss|less|js|jsx|ts|tsx|py|md|sql|json|xml|yaml|yml|toml|vue|java|c|h|cpp|cc|cxx|hpp|cs|go|rs|php|rb|sh|bat|ps1|kt|swift|dart)$/i.test(path)) return 'code'
      if (group.diffElement) return 'diff'
      return group.fileElement?.type || group.primaryElement?.type || 'file'
    },
    artifactGroupPrimaryElement(group) {
      return group.workflowElement
        || group.webpageElement
        || group.tableElement
        || group.imageElement
        || group.codeElement
        || group.fileElement
        || group.diffElement
        || group.primaryElement
        || null
    },
    artifactGroupName(group) {
      const source = group.fileElement || group.primaryElement
      const data = source ? this.elementData(source) : {}
      if (group.type === 'workflow') {
        return data.name || data.title || '任务分配工作流'
      }
      if (this.isSummaryTableGroup(group)) {
        return '文件清单'
      }
      const basename = this.pathBasename(this.artifactGroupPath(group))
      if (basename) return basename
      const dataDerivedBasename = this.pathBasename(
        data.path || data.file || this.pathFromUrl(data.url || data.src) || data.name || data.filename || ''
      )
      if (dataDerivedBasename) return dataDerivedBasename
      return data.name || data.filename || data.title || '产物文件'
    },
    artifactGroupSubtitle(group) {
      if (group.type === 'workflow') {
        const data = this.elementData(group.workflowElement || group.primaryElement)
        const nodeCount = Array.isArray(data.nodes) ? data.nodes.length : 0
        const edgeCount = Array.isArray(data.edges) ? data.edges.length : 0
        return `${nodeCount} 节点 · ${edgeCount} 连线`
      }
      return this.artifactGroupPath(group)
    },
    artifactGroupPath(group) {
      return group.path || this.normalizeWorkspacePath(this.elementWorkspacePath(group.primaryElement) || '')
    },
    artifactGroupSize(group) {
      const groupSize = Number(group?.size || group?.file_size || group?.bytes || 0) || 0
      if (groupSize > 0) return groupSize
      const candidates = [
        group.fileElement,
        group.primaryElement,
        group.imageElement,
        group.webpageElement,
        group.codeElement,
        group.tableElement,
      ].filter(Boolean)
      for (const candidate of candidates) {
        const data = this.elementData(candidate)
        const size = Number(
          data.size
          || data.file_size
          || data.bytes
          || data.data?.size
          || data.data?.file_size
          || data.data?.bytes
          || candidate?.size
          || candidate?.file_size
          || candidate?.bytes
          || 0
        ) || 0
        if (size > 0) return size
      }
      return 0
    },
    artifactGroupSizeText(group) {
      const size = this.artifactGroupSize(group)
      if (size > 0) return this.formatFileSize(size)
      this.ensureArtifactGroupMetadata(group)
      return ''
    },
    artifactGroupKindLabel(group) {
      return {
        code: '代码',
        webpage: '网页',
        table: '表格',
        image: '图片',
        workflow: '工作流',
        diff: 'Diff',
        file: '文件',
      }[group.type] || '文件'
    },
    isSummaryTableGroup(group) {
      const data = this.elementData(group.tableElement || group.primaryElement || {})
      const title = String(data.title || data.name || '').trim()
      return group.type === 'table' && (!this.artifactGroupPath(group) || /文件清单|summary|总结/i.test(title))
    },
    isArtifactGroupExpanded(key, group = null) {
      if (group && this.isSummaryTableGroup(group)) return true
      if (Object.prototype.hasOwnProperty.call(this.artifactExpanded, key)) {
        return this.artifactExpanded[key]
      }
      return this.showAllPreviews
    },
    togglePreviewVisibility() {
      this.showAllPreviews = !this.showAllPreviews
      this.artifactExpanded = {}
    },
    toggleArtifactGroup(key) {
      const next = !this.isArtifactGroupExpanded(key)
      this.$set(this.artifactExpanded, key, next)
      if (next) {
        const group = this.artifactGroups.find(item => item.key === key)
        if (group) {
          this.ensureArtifactGroupPreview(group)
        }
      }
    },
    isArtifactDiffVisible(key) {
      return Boolean(this.artifactDiffExpanded[key])
    },
    toggleArtifactDiff(key) {
      this.$set(this.artifactDiffExpanded, key, !this.isArtifactDiffVisible(key))
      if (!this.isArtifactGroupExpanded(key)) {
        this.$set(this.artifactExpanded, key, true)
      }
    },
    artifactGroupResolvedDiff(group) {
      if (!group) return null
      if (group.diffElement) return group.diffElement
      const related = this.findRelatedArtifactElements(
        this.artifactGroupPath(group),
        group.primaryElement || group.fileElement || group.codeElement || null,
      )
      if (related.diffElement) return related.diffElement
      const targetPath = this.normalizeWorkspacePath(this.artifactGroupPath(group))
      return (this.renderedElements || []).find(el => {
        if (!this.looksLikeDiffElement(el)) return false
        const elPath = this.normalizeWorkspacePath(this.elementWorkspacePath(el))
        return !!elPath && elPath === targetPath
      }) || null
    },
    canRevertArtifactGroup(group) {
      const diffData = this.elementData(this.artifactGroupResolvedDiff(group))
      return typeof diffData.before === 'string' && !!this.sessionId && !!this.artifactGroupPath(group)
    },
    supportsInlineArtifactDiff(group) {
      return group?.type === 'code'
    },
    async revertArtifactDiff(group) {
      if (!this.canRevertArtifactGroup(group)) return
      const path = this.artifactGroupPath(group)
      const normalizedPath = this.normalizeWorkspacePath(path)
      const diffElement = this.artifactGroupResolvedDiff(group)
      const diffData = this.elementData(diffElement)
      this.diffBusyKey = group.key
      try {
        await writeFile(this.sessionId, normalizedPath, diffData.before)
        this.$set(diffElement, 'data', {
          ...diffData,
          applied: false,
          after: diffData.after,
          after_preview: diffData.after_preview,
        })
        this.onWorkbenchSaved({ path: normalizedPath, content: diffData.before })
        this.$message.success('已撤销到变更前内容')
      } catch (error) {
        this.$message.error(error?.message || '撤销失败')
      } finally {
        this.diffBusyKey = ''
      }
    },
    openArtifactGroup(group, mode = 'view') {
      if (group?.type === 'workflow') {
        const workflow = this.elementData(group.workflowElement || group.primaryElement)
        this.$emit('preview-workflow', {
          ...workflow,
          name: workflow.name || '任务分配工作流',
        })
        return
      }
      const path = this.artifactGroupPath(group)
      const primary = group.primaryElement
      if (!path || !primary) return
      const data = this.elementData(primary)
      this.workbenchArtifact = {
        ...this.buildWorkbenchPayload(path, primary, data, group),
        openMode: mode,
      }
      this.workbenchVisible = true
    },
    canPreviewArtifactGroup(group) {
      if (this.isSummaryTableGroup(group)) return false
      if (group.type === 'workflow') return true
      return ['code', 'webpage', 'table', 'image'].includes(group.type)
    },
    canCopyArtifactGroup(group) {
      if (this.isSummaryTableGroup(group)) return false
      return Boolean(this.artifactGroupCopyContent(group))
    },
    copyArtifactGroup(group) {
      const content = this.artifactGroupCopyContent(group)
      if (content) this.copyCode(content)
    },
    artifactGroupCodeContent(group) {
      const path = this.artifactGroupPath(group)
      const cached = path ? this.artifactPreviewCache[path]?.text : ''
      return cached || this.elementContent(group.codeElement || group.webpageElement || group.primaryElement)
    },
    isArtifactPlaceholderText(group, text) {
      const trimmed = String(text || '').trim()
      if (!trimmed) return true
      const name = String(this.artifactGroupName(group) || '').trim()
      const subtitle = String(this.artifactGroupSubtitle(group) || '').trim()
      return trimmed === name || trimmed === subtitle
    },
    artifactGroupCopyContent(group) {
      if (group?.type === 'workflow') {
        return this.workflowRawJson(group)
      }
      const diffElement = this.artifactGroupResolvedDiff(group)
      if (diffElement) return this.diffText(diffElement)
      return this.artifactGroupCodeContent(group)
    },
    workflowRawJson(group) {
      const data = this.elementData(group?.workflowElement || group?.primaryElement)
      const raw = data.raw_plan || data.plan || data
      try {
        return JSON.stringify(raw, null, 2)
      } catch (error) {
        return String(raw || '')
      }
    },
    artifactGroupTableHeaders(group) {
      if (group.tableElement) return this.tableHeaders(group.tableElement)
      if (/\.csv$/i.test(this.artifactGroupPath(group))) {
        const text = this.artifactGroupCodeContent(group)
        if (this.isArtifactPlaceholderText(group, text)) return []
        return this.parseCsvContent(text).headers
      }
      return []
    },
    artifactGroupTableRows(group) {
      if (group.tableElement) return this.normalizeTable(group.tableElement)
      if (/\.csv$/i.test(this.artifactGroupPath(group))) {
        const text = this.artifactGroupCodeContent(group)
        if (this.isArtifactPlaceholderText(group, text)) return []
        return this.parseCsvContent(text).rows
      }
      return []
    },
    artifactGroupTableRowCount(group) {
      return this.artifactGroupTableRows(group).length
    },
    hasUsefulArtifactPreview(group) {
      const path = this.artifactGroupPath(group)
      if (!path) return false
      if (group.type === 'table') {
        const text = this.artifactGroupCodeContent(group)
        if (this.isArtifactPlaceholderText(group, text)) return false
        return this.artifactGroupTableHeaders(group).length > 0
      }
      if (group.type === 'webpage') {
        return Boolean(this.webpagePreviewSrc(group))
      }
      if (!['code', 'text'].includes(group.type)) return true
      const text = this.artifactGroupCodeContent(group)
      return !this.isArtifactPlaceholderText(group, text)
    },
    webpagePreviewSrc(group) {
      const path = this.artifactGroupPath(group)
      if (path && this.sessionId) {
        return this.appendVersionQuery(
          getWorkspaceFileUrl(this.sessionId, path),
          this.elementData(group.webpageElement || group.primaryElement)._htmlVersion,
        )
      }
      return this.webpageSrc(group.webpageElement || group.primaryElement)
    },
    isArtifactGroupPreviewLoading(group) {
      const path = this.artifactGroupPath(group)
      return Boolean(path && this.artifactPreviewLoading[path])
    },
    ensureVisibleArtifactPreviews() {
      this.artifactGroups.forEach(group => {
        if (this.isSummaryTableGroup(group)) return
        if (this.isArtifactGroupExpanded(group.key, group)) {
          this.ensureArtifactGroupPreview(group)
        }
      })
    },
    async ensureArtifactGroupPreview(group) {
      const path = this.artifactGroupPath(group)
      if (!path || !this.sessionId) return
      if (!['code', 'text', 'table', 'webpage'].includes(group.type)) return
      if (this.hasUsefulArtifactPreview(group)) return
      if (this.artifactPreviewLoading[path]) return
      this.$set(this.artifactPreviewLoading, path, true)
      try {
        const response = await fetch(getSessionRawFileUrl(this.sessionId, path), { credentials: 'same-origin' })
        if (!response.ok) throw new Error(`Failed to load preview: ${response.status}`)
        const text = await response.text()
        this.$set(this.artifactPreviewCache, path, { text })
      } catch (error) {
        console.warn('[ArtifactPreview] failed to load raw preview', { path, error })
      } finally {
        this.$delete(this.artifactPreviewLoading, path)
      }
    },
    async ensureArtifactGroupMetadata(group) {
      const path = this.normalizeWorkspacePath(this.artifactGroupPath(group))
      if (!path || !this.sessionId || this.artifactMetaLoading[path]) return
      if (this.artifactGroupSize(group) > 0) return
      this.$set(this.artifactMetaLoading, path, true)
      try {
        const res = await getFileTree(this.sessionId, path)
        const tree = res?.data?.tree || null
        const size = Number(tree?.size || 0) || 0
        if (size > 0) this.applyArtifactSize(path, size)
      } catch (error) {
        console.warn('[ArtifactMeta] failed to load file metadata', { path, error })
      } finally {
        this.$delete(this.artifactMetaLoading, path)
      }
    },
    applyArtifactSize(path, size) {
      const normalizedPath = this.normalizeWorkspacePath(path)
      this.artifactElements.forEach(el => {
        const elementPath = this.normalizeWorkspacePath(this.elementWorkspacePath(el))
        if (elementPath !== normalizedPath) return
        const data = this.elementData(el)
        this.$set(el, 'data', {
          ...data,
          size,
          file_size: size,
          bytes: size,
        })
      })
      if (this.workbenchArtifact && this.normalizeWorkspacePath(this.workbenchArtifact.path) === normalizedPath) {
        this.workbenchArtifact = {
          ...this.workbenchArtifact,
          size,
        }
      }
    },
    normalizeDisplayText(text) {
      return String(text || '').replace(/\s+/g, ' ').trim()
    },
    renderText(content) {
      return this.renderMarkdown(content)
    },
    renderMarkdown(content) {
      if (!content) return ''

      const blocks = []
      let html = this.escapeHtml(this.normalizeMarkdown(String(content)))

      html = html.replace(/```([a-zA-Z0-9_+-]*)\n?([\s\S]*?)```/g, (match, lang, code) => {
        const token = `@@CODE_BLOCK_${blocks.length}@@`
        blocks.push(`<pre><code class="language-${lang || 'text'}">${code.trim()}</code></pre>`)
        return token
      })

      const lines = html.split(/\r?\n/)
      const rendered = []
      let listBuffer = []

      const flushList = () => {
        if (listBuffer.length) {
          rendered.push(`<ul>${listBuffer.join('')}</ul>`)
          listBuffer = []
        }
      }

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]
        const nextIndex = this.nextNonEmptyLineIndex(lines, i + 1)
        const nextLine = nextIndex === -1 ? '' : lines[nextIndex]

        if (this.isMarkdownTableRow(line) && this.isMarkdownTableSeparator(nextLine)) {
          flushList()
          const headers = this.parseMarkdownTableRow(line)
          const rows = []
          i = nextIndex + 1

          while (i < lines.length) {
            if (lines[i].trim() === '') {
              i += 1
              continue
            }
            if (!this.isMarkdownTableRow(lines[i])) break
            rows.push(this.parseMarkdownTableRow(lines[i]))
            i += 1
          }
          i -= 1

          rendered.push(this.renderMarkdownTable(headers, rows))
          continue
        }

        if (/^\s*[-*+]\s+/.test(line)) {
          listBuffer.push(`<li>${this.renderInlineMarkdown(line.replace(/^\s*[-*+]\s+/, ''))}</li>`)
          continue
        }
        flushList()
        if (/^###\s+/.test(line)) {
          rendered.push(`<h3>${this.renderInlineMarkdown(line.replace(/^###\s+/, ''))}</h3>`)
        } else if (/^##\s+/.test(line)) {
          rendered.push(`<h2>${this.renderInlineMarkdown(line.replace(/^##\s+/, ''))}</h2>`)
        } else if (/^#\s+/.test(line)) {
          rendered.push(`<h1>${this.renderInlineMarkdown(line.replace(/^#\s+/, ''))}</h1>`)
        } else if (/^>\s?/.test(line)) {
          rendered.push(`<blockquote>${this.renderInlineMarkdown(line.replace(/^>\s?/, ''))}</blockquote>`)
        } else if (line.trim() === '') {
          rendered.push('')
        } else if (this.isWorkspaceImagePathLine(line)) {
          const src = this.resolveFileUrl(line.trim().replace(/^`|`$/g, ''))
          rendered.push(`<p><img class="inline-markdown-image" src="${this.escapeHtml(src)}" alt=""></p>`)
        } else {
          rendered.push(`<p>${this.renderInlineMarkdown(line)}</p>`)
        }
      }
      flushList()

      html = rendered.join('')
      blocks.forEach((block, index) => {
        html = html.replace(`@@CODE_BLOCK_${index}@@`, block)
      })
      return html
    },
    normalizeMarkdown(content) {
      const lines = String(content || '').replace(/\r\n/g, '\n').split('\n')
      const normalized = []
      for (let i = 0; i < lines.length; i++) {
        const current = lines[i]
        const trimmed = current.trim()
        if (/^-{3,}$/.test(trimmed)) {
          const prev = this.lastNonEmptyLine(normalized)
          const nextIndex = this.nextNonEmptyLineIndex(lines, i + 1)
          const next = nextIndex === -1 ? '' : lines[nextIndex]
          if (this.isMarkdownTableRow(prev) || this.isMarkdownTableRow(next)) {
            continue
          }
          normalized.push(current)
          continue
        }
        if (trimmed === '') {
          const prev = this.lastNonEmptyLine(normalized)
          const nextIndex = this.nextNonEmptyLineIndex(lines, i + 1)
          const next = nextIndex === -1 ? '' : lines[nextIndex]
          if (
            this.isMarkdownTableRow(prev) &&
            (this.isMarkdownTableRow(next) || this.isMarkdownTableSeparator(next))
          ) {
            continue
          }
        }
        normalized.push(current)
      }
      return normalized.join('\n')
    },
    lastNonEmptyLine(lines) {
      for (let i = lines.length - 1; i >= 0; i--) {
        if (String(lines[i] || '').trim() !== '') return lines[i]
      }
      return ''
    },
    nextNonEmptyLineIndex(lines, start) {
      for (let i = start; i < lines.length; i++) {
        if (String(lines[i] || '').trim() !== '') return i
      }
      return -1
    },
    stripMarkdownTables(content) {
      const lines = String(content || '').split(/\r?\n/)
      const kept = []
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]
        const nextIndex = this.nextNonEmptyLineIndex(lines, i + 1)
        const nextLine = nextIndex === -1 ? '' : lines[nextIndex]
        if (this.isMarkdownTableRow(line) && this.isMarkdownTableSeparator(nextLine)) {
          i = nextIndex + 1
          while (i < lines.length) {
            if (String(lines[i] || '').trim() === '') {
              i += 1
              continue
            }
            if (!this.isMarkdownTableRow(lines[i])) break
            i += 1
          }
          i -= 1
          continue
        }
        kept.push(line)
      }
      return kept.join('\n').trim()
    },
    renderInlineMarkdown(text) {
      let html = text || ''
      html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
      html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>')
      html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
      return html
    },
    isMarkdownTableRow(line) {
      const text = String(line || '').trim()
      if (!text || !text.includes('|')) return false
      return this.parseMarkdownTableRow(text).length >= 2
    },
    isMarkdownTableSeparator(line) {
      if (!this.isMarkdownTableRow(line)) return false
      const cells = this.parseMarkdownTableRow(line)
      return cells.length >= 2 && cells.every(cell => /^:?-{2,}:?$/.test(cell.replace(/\s+/g, '')))
    },
    parseMarkdownTableRow(line) {
      let text = String(line || '').trim()
      if (text.startsWith('|')) text = text.slice(1)
      if (text.endsWith('|')) text = text.slice(0, -1)
      return text.split('|').map(cell => cell.trim())
    },
    renderMarkdownTable(headers, rows) {
      const thead = headers
        .map(header => `<th>${this.renderInlineMarkdown(header)}</th>`)
        .join('')
      const body = rows
        .map(row => {
          const cells = headers.map((_, index) => `<td>${this.renderInlineMarkdown(row[index] || '')}</td>`).join('')
          return `<tr>${cells}</tr>`
        })
        .join('')
      return `<div class="markdown-table-wrap"><table class="markdown-table"><thead><tr>${thead}</tr></thead><tbody>${body}</tbody></table></div>`
    },
    isWorkspaceImagePathLine(line) {
      const text = String(line || '').trim().replace(/^`|`$/g, '')
      return /^\/?workspace\/.+\.(png|jpe?g|gif|webp|svg|bmp)$/i.test(text)
    },
    tablePayload(el) {
      const data = this.elementData(el)
      if (Array.isArray(data.headers) || Array.isArray(data.rows)) return data
      if (data.data && (Array.isArray(data.data.headers) || Array.isArray(data.data.rows))) return data.data
      const content = this.elementContent(el)
      if (content) {
        try {
          const parsed = JSON.parse(content)
          if (parsed && (Array.isArray(parsed.headers) || Array.isArray(parsed.rows))) return parsed
          if (parsed?.data && (Array.isArray(parsed.data.headers) || Array.isArray(parsed.data.rows))) return parsed.data
        } catch (e) {}
      }
      return {}
    },
    tableHeaders(el) {
      return this.normalizedTablePayload(el).headers
    },
    tableRowCount(el) {
      return this.normalizedTablePayload(el).rows.length
    },
    tablePath(el) {
      const data = this.elementData(el)
      return data.path || data.file || this.workspacePathFromContent(this.elementContent(el)) || ''
    },
    codePath(el) {
      const data = this.elementData(el)
      return data.path || data.file || this.workspacePathFromContent(this.elementContent(el)) || ''
    },
    normalizeTable(el) {
      const { headers, rows } = this.normalizedTablePayload(el)
      if (!headers.length) return []
      return rows.map(row => {
        const cells = Array.isArray(row) ? row : headers.map(h => row?.[h])
        const obj = {}
        headers.forEach((h, i) => {
          obj['col' + i] = cells[i] === undefined || cells[i] === null ? '' : String(cells[i])
        })
        return obj
      })
    },
    normalizedTablePayload(el) {
      const payload = this.tablePayload(el)
      const headers = Array.isArray(payload.headers) ? payload.headers.map(h => String(h || '')) : []
      const rows = Array.isArray(payload.rows) ? payload.rows : []
      return this.removeDuplicateIndexColumn(headers, rows)
    },
    removeDuplicateIndexColumn(headers, rows) {
      if (!Array.isArray(headers) || headers.length < 2) return { headers, rows }
      const normalizedHeaders = headers.map(h => this.normalizeIndexHeaderLabel(h))
      const isIndexLike = label => ['#', '序号', 'index', 'idx', 'no', 'no.', 'number'].includes(label)
      if (!(isIndexLike(normalizedHeaders[0]) && isIndexLike(normalizedHeaders[1]))) {
        return { headers, rows }
      }

      const materializedRows = rows.map(row => (
        Array.isArray(row) ? row.slice() : headers.map(h => row?.[h])
      ))
      if (!materializedRows.length) return { headers, rows }

      const sameSequence = materializedRows.every((cells, index) => {
        const left = String(cells?.[0] ?? '').trim()
        const right = String(cells?.[1] ?? '').trim()
        const expected = String(index + 1)
        return left && right && left === right && left === expected
      })
      if (!sameSequence) return { headers, rows }

      const dropIndex = normalizedHeaders[0] === '序号' ? 1 : 0
      return {
        headers: headers.filter((_, index) => index !== dropIndex),
        rows: materializedRows.map(cells => cells.filter((_, index) => index !== dropIndex)),
      }
    },
    normalizeIndexHeaderLabel(label) {
      const text = String(label || '').trim().toLowerCase()
      if (!text) return ''
      if (text === '#') return '#'
      if (['序号', '序列', '编号'].includes(text)) return '序号'
      if (['index', 'idx'].includes(text)) return 'index'
      if (['no', 'no.', 'number'].includes(text)) return 'no'
      return text
    },
    shouldShowSummaryIndexColumn(group) {
      const firstHeader = this.artifactGroupTableHeaders(group)[0] || ''
      return !['#', '序号', 'index', 'idx', 'no', 'no.', 'number'].includes(
        this.normalizeIndexHeaderLabel(firstHeader)
      )
    },
    elementData(el) {
      return el?.data || {}
    },
    elementContent(el) {
      if (!el) return ''
      if (el.content !== undefined && el.content !== null) return el.content
      return el.data?.content || ''
    },
    shouldHideRawTextElement(el) {
      if (!el || el.type !== 'text') return false
      const content = this.elementContent(el)
      if (!content || content.length < 1200) return false
      const fileDumpCount = (content.match(/##\s+\/workspace\/agents\//g) || []).length
      const fenceCount = (content.match(/```/g) || []).length
      return fileDumpCount >= 1 || fenceCount >= 4
    },
    imageSrc(el) {
      const data = this.elementData(el)
      const candidate = data.url || data.src || data.path || data.file || data.name || this.elementContent(el)
      return this.appendVersionQuery(this.resolveFileUrl(candidate), data._imageVersion)
    },
    appendVersionQuery(url, version) {
      if (!url || !version || /^data:|^blob:/i.test(String(url))) return url
      return `${url}${String(url).includes('?') ? '&' : '?'}v=${encodeURIComponent(version)}`
    },
    pathBasename(path) {
      const normalized = String(path || '').replace(/\\/g, '/')
      if (!normalized) return ''
      return normalized.split('/').filter(Boolean).pop() || ''
    },
    webpagePath(el) {
      const data = this.elementData(el)
      return data.path || data.file || this.workspacePathFromContent(this.elementContent(el)) || ''
    },
    webpageSrc(el) {
      const path = this.webpagePath(el)
      if (path && this.sessionId) {
        return getWorkspaceFileUrl(this.sessionId, this.normalizeWorkspacePath(path))
      }
      return this.resolveFileUrl(path)
    },
    isWorkbenchPreviewingPath(path) {
      if (!this.workbenchVisible || !this.workbenchArtifact?.path) return false
      return this.normalizeWorkspacePath(path) === this.normalizeWorkspacePath(this.workbenchArtifact.path)
    },
    imagePath(el) {
      const data = this.elementData(el)
      return data.path || data.file || this.pathFromUrl(data.url || data.src) || this.workspacePathFromContent(this.elementContent(el)) || ''
    },
    isImageElement(el) {
      const data = this.elementData(el)
      const value = data.path || data.file || data.url || data.src || data.name || this.elementContent(el)
      return /\.(png|jpe?g|gif|webp|svg|bmp)$/i.test(String(value || '').split('?')[0])
    },
    resolveFileUrl(value) {
      if (!value) return ''
      const text = String(value)
      if (/^(data:|blob:|https?:\/\/|\/api\/)/i.test(text)) return text
      if (text.startsWith('/workspace') || text.startsWith('workspace/')) {
        if (!this.sessionId) return text
        const path = this.normalizeWorkspacePath(text)
        return `/api/sandbox/sessions/${encodeURIComponent(this.sessionId)}/files/raw?path=${encodeURIComponent(path)}`
      }
      return text
    },
    async copyCode(content) {
      try {
        await navigator.clipboard.writeText(content)
        this.$message.success('已复制到剪贴板')
      } catch (e) {
        // Fallback
        const textarea = document.createElement('textarea')
        textarea.value = content
        document.body.appendChild(textarea)
        textarea.select()
        document.execCommand('copy')
        document.body.removeChild(textarea)
        this.$message.success('已复制到剪贴板')
      }
    },
    previewCode(data) {
      if (data?.workflow) {
        this.$emit('preview-workflow', data.workflow)
        return
      }
      this.previewData = data
      this.codePreviewVisible = true
    },
    formatFileSize(bytes) {
      if (!bytes) return ''
      const units = ['B', 'KB', 'MB', 'GB']
      let i = 0
      let size = bytes
      while (size >= 1024 && i < units.length - 1) {
        size /= 1024
        i++
      }
      return size.toFixed(1) + ' ' + units[i]
    },
    diffText(el) {
      const data = this.elementData(el)
      return data.diff_text || data.data?.diff_text || this.elementContent(el) || ''
    },
    diffPath(el) {
      const data = this.elementData(el)
      return data.path || data.file || data.data?.path || data.data?.file || this.workspacePathFromContent(this.diffText(el)) || ''
    },
    diffFilename(el) {
      const data = this.elementData(el)
      if (data.filename || data.data?.filename) return data.filename || data.data?.filename
      const path = this.diffPath(el)
      if (!path) return ''
      const normalized = String(path).replace(/\\/g, '/')
      return normalized.split('/').filter(Boolean).pop() || normalized
    },
    diffAdditions(el) {
      const data = this.elementData(el)
      return Number(data?.diff_stat?.additions || data?.data?.diff_stat?.additions || 0)
    },
    diffDeletions(el) {
      const data = this.elementData(el)
      return Number(data?.diff_stat?.deletions || data?.data?.diff_stat?.deletions || 0)
    },
    looksLikeDiffElement(el) {
      if (!el) return false
      if (el.type === 'diff') return true
      const data = this.elementData(el)
      return Boolean(
        data.diff_text
        || data.data?.diff_text
        || data.diff_stat
        || data.data?.diff_stat
        || typeof data.before === 'string'
        || typeof data.data?.before === 'string'
        || typeof data.after === 'string'
        || typeof data.data?.after === 'string'
      )
    },

    serviceInfo(el) {
      const data = this.elementData(el)
      const nested = data.service || data.data || {}
      return {
        ...data,
        ...nested,
        id: data.service_id || data.id || nested.service_id || nested.id || '',
        service_id: data.service_id || data.id || nested.service_id || nested.id || '',
        proxy_url: this.pickServiceUrl(data.proxy_url, nested.proxy_url, data.url, nested.url),
        url: this.pickServiceUrl(data.proxy_url, nested.proxy_url, data.url, nested.url),
      }
    },
    serviceTitle(el) {
      const svc = this.serviceInfo(el)
      return svc.title || svc.name || this.elementData(el).title || this.elementContent(el) || '预览服务'
    },
    pickServiceUrl(...urls) {
      const valid = urls.filter(url => typeof url === 'string' && url.trim())
      return valid.find(url => /[?&]token=/.test(url)) || valid[0] || ''
    },
    serviceUrl(el) {
      const svc = this.serviceInfo(el)
      return this.pickServiceUrl(svc.proxy_url, svc.url)
    },
    serviceStatusLabel(status) {
      const key = String(status || 'unknown').toLowerCase()
      return {
        running: '运行中',
        starting: '启动中',
        stopped: '已停止',
        stopping: '停止中',
        failed: '失败',
        exited: '已退出',
        open: '运行中',
        closed: '已关闭',
        unknown: '未知',
      }[key] || status
    },
    serviceStatusType(status) {
      const key = String(status || '').toLowerCase()
      if (['running', 'open'].includes(key)) return 'success'
      if (['starting', 'stopping'].includes(key)) return 'warning'
      if (['failed', 'exited'].includes(key)) return 'danger'
      return 'info'
    },
    serviceActionKey(el, action) {
      const id = this.serviceInfo(el).service_id || this.serviceInfo(el).id || 'unknown'
      return `${id}:${action}`
    },
    setServiceElement(el, patch) {
      if (!el.data) this.$set(el, 'data', {})
      Object.keys(patch || {}).forEach(key => this.$set(el.data, key, patch[key]))
    },
    openService(el) {
      this.openUrl(this.serviceUrl(el))
    },
    openUrl(url) {
      if (!url) return
      window.open(url, '_blank', 'noopener')
    },
    previewService(el) {
      const url = this.serviceUrl(el)
      if (!url) return
      this.servicePreviewUrl = url
      this.servicePreviewVisible = true
    },
    async copyServiceUrl(url) {
      if (!url) return
      try {
        await navigator.clipboard.writeText(url)
        this.$message.success('已复制服务链接')
      } catch (e) {
        this.$message.info(url)
      }
    },
    async loadServiceLogs(el) {
      const svc = this.serviceInfo(el)
      if (!this.sessionId || !svc.service_id) return
      this.serviceBusyKey = this.serviceActionKey(el, 'logs')
      this.serviceLogsLoading = true
      this.serviceLogsVisible = true
      try {
        const res = await getServiceLogs(this.sessionId, svc.service_id)
        if (res.code === 200) {
          this.serviceLogsData = res.data || {}
        }
      } catch (e) {
        this.$message.error(e?.message || '获取服务日志失败')
      } finally {
        this.serviceLogsLoading = false
        this.serviceBusyKey = ''
      }
    },
    async stopServiceCard(el) {
      const svc = this.serviceInfo(el)
      if (!this.sessionId || !svc.service_id) return
      this.serviceBusyKey = this.serviceActionKey(el, 'stop')
      try {
        const res = await stopService(this.sessionId, svc.service_id)
        if (res.code === 200) {
          const service = res.data?.service || {}
          this.setServiceElement(el, { ...service, status: service.status || 'stopped' })
          this.$message.success('服务已停止')
        }
      } catch (e) {
        this.$message.error(e?.message || '停止服务失败')
      } finally {
        this.serviceBusyKey = ''
      }
    },
    async restartServiceCard(el) {
      const svc = this.serviceInfo(el)
      if (!this.sessionId || !svc.service_id) return
      this.serviceBusyKey = this.serviceActionKey(el, 'restart')
      try {
        const res = await restartService(this.sessionId, svc.service_id)
        if (res.code === 200) {
          const service = res.data?.service || {}
          this.setServiceElement(el, { ...service, status: service.status || 'starting' })
          this.$message.success('服务已重启')
        }
      } catch (e) {
        this.$message.error(e?.message || '重启服务失败')
      } finally {
        this.serviceBusyKey = ''
      }
    },
    fileIcon(el) {
      const value = String(this.elementData(el).path || this.elementData(el).name || this.elementContent(el) || '').toLowerCase()
      if (/\.(html?|vue)$/.test(value)) return 'el-icon-monitor'
      if (/\.(md|txt|pdf|docx?)$/.test(value)) return 'el-icon-document'
      if (/\.(css|js|ts|tsx|jsx|json|py|java|go|rs)$/.test(value)) return 'el-icon-tickets'
      return 'el-icon-folder-opened'
    },
    openFileElement(data, element = null) {
      if (!data) return
      const path = data.path || data.file || this.pathFromUrl(data.url) || this.pathFromUrl(data.src) || this.workspacePathFromContent(data.content) || data.name
      this.openFilePath(path, element || data)
    },
    openArtifactElement(data, element = null) {
      if (!data) return
      const path = data.path || data.file || this.pathFromUrl(data.url) || this.pathFromUrl(data.src) || this.workspacePathFromContent(data.content) || data.name
      this.openArtifactPath(path, element || data)
    },
    openArtifactPath(path, element = null) {
      const normalizedPath = this.normalizeWorkspacePath(path)
      if (!normalizedPath) return
      const related = this.findRelatedArtifactElements(normalizedPath, element)
      const primaryElement = related.codeElement || related.tableElement || related.webpageElement || related.imageElement || related.fileElement || related.diffElement || element
      const data = primaryElement ? this.elementData(primaryElement) : {}
      this.workbenchArtifact = this.buildWorkbenchPayload(normalizedPath, primaryElement, data, related)
      this.workbenchVisible = true
    },
    emitOpenFilePath(path) {
      const normalizedPath = this.normalizeWorkspacePath(path)
      if (!normalizedPath) return
      this.$emit('open-file', { path: normalizedPath })
    },
    openFilePath(path, element = null) {
      const normalizedPath = this.normalizeWorkspacePath(path)
      const related = this.findRelatedArtifactElements(normalizedPath, element)
      const primaryElement = related.codeElement || related.tableElement || related.webpageElement || related.imageElement || related.fileElement || related.diffElement || element
      const data = primaryElement ? this.elementData(primaryElement) : {}
      this.$emit('open-file', this.buildWorkbenchPayload(normalizedPath, primaryElement, data, related))
    },
    buildWorkbenchPayload(normalizedPath, element, data = {}, related = null) {
      const context = related || this.findRelatedArtifactElements(normalizedPath, element)
      const primaryType = element?.type || context.codeElement?.type || context.tableElement?.type || context.webpageElement?.type || context.imageElement?.type || context.fileElement?.type || context.diffElement?.type || ''
      const type = primaryType === 'file' ? this.inferWorkbenchTypeFromContext(context, normalizedPath) : primaryType
      const payload = {
        path: normalizedPath,
        type,
        name: data.name || data.filename || normalizedPath.split('/').pop() || '',
        diffElement: context.diffElement || null,
        diffMap: this.buildWorkbenchDiffMap(),
        fileMap: this.buildWorkbenchFileMap(),
      }
      if ((type === 'code' || type === 'text') && context.codeElement) {
        payload.codeContent = this.elementContent(context.codeElement)
      }
      if (type === 'table' && context.tableElement) {
        payload.tableHeaders = this.tableHeaders(context.tableElement)
        payload.tableRows = this.normalizeTable(context.tableElement)
      }
      if (type === 'image' && context.imageElement) {
        payload.imageUrl = this.imageSrc(context.imageElement)
      }
      if (type === 'webpage') {
        payload.codeContent = this.elementContent(context.webpageElement || element)
        payload.previewUrl = this.webpagePreviewSrc({
          ...context,
          primaryElement: element,
          path: normalizedPath,
        })
      }
      return payload
    },
    buildWorkbenchDiffMap() {
      const map = {}
      ;(this.artifactElements || []).forEach(el => {
        if (!this.looksLikeDiffElement(el)) return
        const path = this.normalizeWorkspacePath(this.elementWorkspacePath(el))
        if (!path || map[path]) return
        map[path] = el
      })
      return map
    },
    buildWorkbenchFileMap() {
      const map = {}
      ;(this.artifactElements || []).forEach(el => {
        if (!['file', 'image', 'code', 'webpage', 'table'].includes(el?.type)) return
        const path = this.normalizeWorkspacePath(this.elementWorkspacePath(el))
        if (!path || map[path]) return
        map[path] = true
      })
      return map
    },
    inferWorkbenchTypeFromContext(context, normalizedPath) {
      if (context.codeElement) return 'code'
      if (context.tableElement) return 'table'
      if (context.webpageElement) return 'webpage'
      if (context.imageElement) return 'image'
      if (/\.csv$/i.test(normalizedPath)) return 'table'
      if (/\.(html?)$/i.test(normalizedPath)) return 'webpage'
      if (/\.(png|jpe?g|gif|webp|svg|bmp)$/i.test(normalizedPath)) return 'image'
      if (/\.(css|scss|less|js|jsx|ts|tsx|py|md|sql|json|xml|yaml|yml|toml|vue|java|c|h|cpp|cc|cxx|hpp|cs|go|rs|php|rb|sh|bat|ps1|kt|swift|dart)$/i.test(normalizedPath)) return 'code'
      if (/\.(txt|log)$/i.test(normalizedPath)) return 'text'
      return 'file'
    },
    findRelatedArtifactElements(normalizedPath, seedElement = null) {
      const result = {
        codeElement: null,
        tableElement: null,
        webpageElement: null,
        imageElement: null,
        fileElement: null,
        diffElement: null,
      }
      const targetPath = this.normalizeWorkspacePath(normalizedPath)
      const elements = this.artifactElements
      if (seedElement) {
        if (this.looksLikeDiffElement(seedElement)) result.diffElement = seedElement
        if (seedElement.type === 'file') result.fileElement = seedElement
        if (seedElement.type === 'image') result.imageElement = seedElement
        if (seedElement.type === 'table') result.tableElement = seedElement
        if (seedElement.type === 'webpage') result.webpageElement = seedElement
        if (seedElement.type === 'code' || seedElement.type === 'text') result.codeElement = seedElement
      }
      elements.forEach(el => {
        const elPath = this.elementWorkspacePath(el)
        if (!elPath || this.normalizeWorkspacePath(elPath) !== targetPath) return
        if (this.looksLikeDiffElement(el) && !result.diffElement) result.diffElement = el
        if (el.type === 'file' && !result.fileElement) result.fileElement = el
        if (el.type === 'image' && !result.imageElement) result.imageElement = el
        if (el.type === 'table' && !result.tableElement) result.tableElement = el
        if (el.type === 'webpage' && !result.webpageElement) result.webpageElement = el
        if ((el.type === 'code' || el.type === 'text') && !result.codeElement) result.codeElement = el
      })
      return result
    },
    elementWorkspacePath(el) {
      if (!el) return ''
      if (el.type === 'table') return this.tablePath(el)
      if (el.type === 'webpage') return this.webpagePath(el)
      if (el.type === 'image') return this.imagePath(el)
      if (this.looksLikeDiffElement(el)) return this.diffPath(el)
      const data = this.elementData(el)
      return data.path || data.file || data.data?.path || data.data?.file || this.pathFromUrl(data.url) || this.pathFromUrl(data.src) || this.workspacePathFromContent(this.elementContent(el)) || ''
    },
    normalizeWorkspacePath(path) {
      if (!path) return ''
      const clean = String(path).replace(/\\/g, '/').replace(/^\/+/, '')
      return clean.startsWith('workspace/') ? `/${clean}` : `/workspace/${clean}`
    },
    estimateContentSize(content) {
      if (typeof content !== 'string' || !content) return 0
      if (content.startsWith('data:image/')) {
        const base64 = content.split(',')[1] || ''
        return Math.max(0, Math.floor((base64.length * 3) / 4))
      }
      if (typeof TextEncoder !== 'undefined') {
        return new TextEncoder().encode(content).length
      }
      return unescape(encodeURIComponent(content)).length
    },
    onWorkbenchSaved({ path, content }) {
      if (!path) return
      const normalizedPath = this.normalizeWorkspacePath(path)
      const isImageContent = typeof content === 'string' && content.startsWith('data:image/')
      const isCsvPath = /\.csv$/i.test(normalizedPath)
      const isHtmlPath = /\.(html?|svg)$/i.test(normalizedPath)
      const estimatedSize = this.estimateContentSize(content)
      if (typeof content === 'string' && !content.startsWith('data:image/')) {
        this.$set(this.artifactPreviewCache, normalizedPath, { text: content })
      }
      if (this.workbenchArtifact && this.workbenchArtifact.path === normalizedPath) {
        const next = { ...this.workbenchArtifact }
        if (isImageContent) {
          next.imageUrl = content
          next._imageVersion = Date.now()
        } else if (isCsvPath) {
          const { headers, rows } = this.parseCsvContent(content)
          next.tableHeaders = headers
          next.tableRows = rows
        } else {
          next.codeContent = content
          if (isHtmlPath) {
            next._htmlVersion = Date.now()
          }
        }
        if (estimatedSize > 0) next.size = estimatedSize
        this.workbenchArtifact = next
      }
      this.artifactElements.forEach(el => {
        const elementPath = this.normalizeWorkspacePath(this.elementWorkspacePath(el))
        if (elementPath !== normalizedPath) return
        const data = this.elementData(el)
        const nextData = { ...data }
        if (estimatedSize > 0) {
          nextData.size = estimatedSize
          nextData.file_size = estimatedSize
          nextData.bytes = estimatedSize
        }
        if (isImageContent && (el.type === 'image' || el.type === 'file' || this.isImageElement(el))) {
          this.$set(el, 'data', { ...nextData, url: content, src: content, _imageVersion: Date.now() })
          return
        }
        if (isCsvPath && (el.type === 'table' || el.type === 'file')) {
          const { headers, rows } = this.parseCsvContent(content)
          this.$set(el, 'content', content)
          this.$set(el, 'data', { ...nextData, headers, rows, content })
          return
        }
        if (el.type === 'code' || el.type === 'text' || el.type === 'webpage' || el.type === 'file') {
          const patch = (el.type === 'webpage' || (el.type === 'file' && isHtmlPath))
            ? { ...nextData, content, _htmlVersion: Date.now() }
            : { ...nextData, content }
          this.$set(el, 'content', content)
          this.$set(el, 'data', patch)
          return
        }
      })
    },
    onWorkbenchDiffApplied({ path, content }) {
      if (!path) return
      const normalizedPath = this.normalizeWorkspacePath(path)
      this.artifactElements.forEach(el => {
        const elementPath = this.normalizeWorkspacePath(this.elementWorkspacePath(el))
        if (elementPath !== normalizedPath || el.type !== 'diff') return
        const data = this.elementData(el)
        this.$set(el, 'data', { ...data, applied: true, after: content, after_preview: content })
      })
      this.onWorkbenchSaved({ path: normalizedPath, content })
    },
    parseCsvContent(text) {
      const source = String(text || '').replace(/^\uFEFF/, '')
      const delimiter = this.detectCsvDelimiter(source)
      const rows = []
      let row = []
      let value = ''
      let inQuotes = false
      for (let i = 0; i < source.length; i += 1) {
        const ch = source[i]
        const next = source[i + 1]
        if (inQuotes) {
          if (ch === '"' && next === '"') {
            value += '"'
            i += 1
          } else if (ch === '"') {
            inQuotes = false
          } else {
            value += ch
          }
          continue
        }
        if (ch === '"') {
          inQuotes = true
        } else if (ch === delimiter) {
          row.push(value)
          value = ''
        } else if (ch === '\n') {
          row.push(value.replace(/\r$/, ''))
          if (row.some(cell => String(cell).length > 0)) {
            rows.push(row)
          }
          row = []
          value = ''
        } else {
          value += ch
        }
      }
      row.push(value.replace(/\r$/, ''))
      if (row.some(cell => String(cell).length > 0)) {
        rows.push(row)
      }
      const normalizedRows = rows
        .map(cells => cells.map(cell => String(cell == null ? '' : cell).trim()))
        .filter(cells => cells.some(cell => cell !== ''))
      const maxCols = normalizedRows.reduce((max, cells) => Math.max(max, cells.length), 0)
      const paddedRows = normalizedRows.map(cells => {
        const next = cells.slice()
        while (next.length < maxCols) next.push('')
        return next
      })
      const headers = (paddedRows[0] || Array.from({ length: maxCols }, (_, index) => `列${index + 1}`))
        .map((header, index) => String(header || '').trim() || `列${index + 1}`)
      const body = paddedRows.slice(1).map(cells => {
        const item = {}
        headers.forEach((header, index) => {
          item[`col${index}`] = cells[index] || ''
        })
        return item
      })
      return { headers, rows: body }
    },
    detectCsvDelimiter(text) {
      const sampleLines = String(text || '')
        .replace(/\r\n/g, '\n')
        .split('\n')
        .map(line => line.trim())
        .filter(Boolean)
        .slice(0, 5)
      const candidates = [',', ';', '\t']
      const score = delimiter => sampleLines.reduce((total, line) => {
        let count = 0
        let inQuotes = false
        for (let i = 0; i < line.length; i += 1) {
          const ch = line[i]
          const next = line[i + 1]
          if (ch === '"') {
            if (inQuotes && next === '"') {
              i += 1
            } else {
              inQuotes = !inQuotes
            }
            continue
          }
          if (!inQuotes && ch === delimiter) count += 1
        }
        return total + count
      }, 0)
      return candidates.reduce((best, delimiter) => {
        const nextScore = score(delimiter)
        if (nextScore > best.score) return { delimiter, score: nextScore }
        return best
      }, { delimiter: ',', score: -1 }).delimiter
    },
    pathFromUrl(url) {
      if (!url) return ''
      const marker = '/workspace/'
      const idx = url.indexOf(marker)
      if (idx === -1) return ''
      return decodeURIComponent(url.slice(idx + marker.length))
    },
    workspacePathFromContent(content) {
      const text = String(content || '').trim()
      if (!text) return ''
      if (text.startsWith('/workspace/') || text.startsWith('workspace/')) return text
      return ''
    },

    // ── Domain Card Helpers ──
    cardData(el) {
      return el?.data || {}
    },
    cardTitle(el) {
      const d = this.cardData(el)
      return d.title || d.name || ''
    },
    cardSummary(el) {
      const d = this.cardData(el)
      return d.summary || d.description || ''
    },
    cardPriority(el) {
      return this.cardData(el).priority || this.cardData(el).meta?.priority || ''
    },
    cardSeverity(el) {
      return this.cardData(el).severity || this.cardData(el).meta?.severity || ''
    },
    cardStatus(el) {
      return this.cardData(el).status || this.cardData(el).meta?.status || ''
    },
    cardMetaItems(el) {
      const d = this.cardData(el)
      const meta = d.meta || {}
      const items = []
      const pushIf = (icon, label, value) => {
        if (value !== undefined && value !== null && value !== '') {
          items.push({ icon, label, value })
        }
      }
      pushIf('el-icon-user', '负责人', meta.assignee || d.assignee)
      pushIf('el-icon-date', '截止', meta.deadline || meta.due_date || d.deadline)
      pushIf('el-icon-date', '日期', meta.start_date || d.start_date || meta.end_date || d.end_date)
      pushIf('el-icon-s-flag', '迭代', meta.iteration_name || d.iteration_name)
      pushIf('el-icon-collection-tag', '标签', meta.labels || d.labels)
      return items
    },
    cardProjectStats(el) {
      const d = this.cardData(el)
      const meta = d.meta || {}
      const stats = []
      const pushIf = (label, value) => {
        if (value !== undefined && value !== null && value !== '') {
          stats.push({ label, value })
        }
      }
      pushIf('需求', meta.requirement_count || d.requirement_count)
      pushIf('缺陷', meta.bug_count || d.bug_count)
      pushIf('迭代', meta.iteration_count || d.iteration_count)
      pushIf('仓库', meta.repo_count || d.repo_count)
      return stats
    },
    cardPriorityLabel(el) {
      const labels = { p0: 'P0 紧急', p1: 'P1 高', p2: 'P2 中', p3: 'P3 低' }
      return labels[this.cardPriority(el)] || this.cardPriority(el)
    },
    cardSeverityLabel(el) {
      const labels = { critical: '致命', major: '严重', minor: '一般', trivial: '轻微' }
      return labels[this.cardSeverity(el)] || this.cardSeverity(el)
    },
    cardReqStatusLabel(el) {
      const labels = { backlog: '待规划', todo: '待办', in_progress: '进行中', in_review: '审查中', done: '已完成', closed: '已关闭' }
      return labels[this.cardStatus(el)] || this.cardStatus(el)
    },
    cardBugStatusLabel(el) {
      const labels = { open: '待处理', in_progress: '处理中', fixed: '已修复', verified: '已验证', closed: '已关闭', reopened: '重开' }
      return labels[this.cardStatus(el)] || this.cardStatus(el)
    },
    cardIterStatusLabel(el) {
      const labels = { planned: '计划中', active: '进行中', completed: '已完成' }
      return labels[this.cardStatus(el)] || this.cardStatus(el)
    },
    cardIterProgress(el) {
      const d = this.cardData(el)
      if (d.progress !== undefined && d.progress !== null) return Number(d.progress) || 0
      if (d.meta?.progress !== undefined && d.meta?.progress !== null) return Number(d.meta.progress) || 0
      return null
    },
    navigateToDomain(el) {
      const d = this.cardData(el)
      const projectId = d.project_id || d.meta?.project_id || ''
      const itemId = d.id || d.meta?.id || ''
      const type = el?.type
      if (!itemId) return

      let route = {}
      if (type === 'requirement_card') {
        route = { name: 'requirementDetail', params: { id: projectId, rid: itemId } }
      } else if (type === 'bug_card') {
        route = { name: 'bugDetail', params: { id: projectId, bid: itemId } }
      } else if (type === 'iteration_card') {
        if (projectId) {
          route = { name: 'projectDetail', params: { id: projectId }, query: { tab: 'iterations' }, hash: '#iter-' + itemId }
        }
      } else if (type === 'project_card') {
        route = { name: 'projectDetail', params: { id: itemId } }
      }
      if (route.name) {
        this.$router.push(route).catch(() => {})
      }
    },
  },
}
</script>

<style scoped>
.message-bubble {
  display: flex;
  flex-direction: column;
  max-width: 78%;
}

.message-bubble.own {
  align-items: flex-end;
  margin-left: auto;
}

.bubble-sender {
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.agent-tag {
  font-size: 12px;
  color: #4080ff;
  font-weight: 500;
}

.provider-tag {
  font-size: 11px;
  line-height: 18px;
  padding: 0 6px;
  border-radius: 4px;
  background: #eef2ff;
  color: #475569;
  border: 1px solid #dbe3ff;
}

.status-tag {
  font-size: 11px;
  line-height: 18px;
  padding: 0 6px;
  border-radius: 4px;
  background: #f1f5f9;
  color: #64748b;
}

.status-streaming,
.status-pending {
  background: #ecf5ff;
  color: #4080ff;
}

.status-done {
  background: #f0f9eb;
  color: #67c23a;
}

.status-error {
  background: #fef0f0;
  color: #f56c6c;
}

.status-stopped {
  background: #f4f4f5;
  color: #909399;
}

.stop-btn {
  padding: 0;
  color: #f56c6c;
}

.bubble-inner {
  background: #ffffff;
  padding: 14px 16px;
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 0 0 1px rgba(15, 23, 42, 0.03);
  border: 1px solid #eef1f6;
  transition: box-shadow 0.2s ease;
}

.bubble-inner:hover {
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06), 0 0 0 1px rgba(15, 23, 42, 0.03);
}

.own .bubble-inner {
  background: linear-gradient(135deg, #f4f8ff 0%, #f0f5ff 100%);
  border-color: #dce8fc;
}

/* ===== Elements ===== */
.bubble-elements {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.artifact-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f3f8;
}

.content-section + .artifact-section,
.raw-rendered + .artifact-section {
  margin-top: 14px;
}

.section-title {
  font-size: 11px;
  line-height: 1;
  color: #8b9ab5;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 2px;
}

.current-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  margin-bottom: 12px;
  border-radius: 10px;
  background: linear-gradient(135deg, #f8fbff 0%, #f0f7ff 100%);
  border: 1px solid #d6e6ff;
  color: #334155;
  font-size: 12px;
  animation: progressPulse 2s ease-in-out infinite;
}

@keyframes progressPulse {
  0%, 100% { border-color: #d6e6ff; }
  50% { border-color: #b0d0ff; }
}

.current-progress-label {
  color: #2563eb;
  font-weight: 600;
  white-space: nowrap;
  font-size: 11px;
}

.current-progress-text {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #475569;
}

.el-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: #fafcff;
  border-radius: 8px;
  font-size: 12px;
  color: #5b6e8c;
  border-left: 3px solid #d0ddf0;
}

.el-error {
  padding: 12px 14px;
  border-radius: 10px;
  background: linear-gradient(135deg, #fff5f5 0%, #fef2f2 100%);
  border: 1px solid #fecaca;
  border-left: 4px solid #ef4444;
}

.error-title {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  color: #dc2626;
  font-size: 12px;
  font-weight: 600;
}

.error-content {
  font-size: 13px;
  line-height: 1.65;
  color: #7f1d1d;
}


.progress-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #4080ff;
  flex-shrink: 0;
  animation: dotPulse 1.6s ease-in-out infinite;
}

@keyframes dotPulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.85); }
}

.progress-done {
  background: #22c55e;
  animation: none;
}

.progress-error {
  background: #ef4444;
  animation: none;
}

.progress-stopped {
  background: #94a3b8;
  animation: none;
}

.el-block {
  width: 100%;
}

/* ── Domain Cards (requirement / bug / iteration) ── */
.domain-card {
  margin: 6px 0;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #fff;
  overflow: hidden;
  cursor: pointer;
  transition: box-shadow 0.2s, border-color 0.2s;
}
.domain-card:hover {
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  border-color: #cbd5e1;
}

/* ---- compact row layout ---- */
.dc-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.dc-main-row {
  padding: 8px 12px;
}
.dc-meta-row {
  padding: 0 12px 7px 12px;
  gap: 14px;
}

.dc-domain-tag {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 3px;
  background: #eef2ff;
  color: #4f6ef7;
  flex-shrink: 0;
}
.dc-type-tag {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 3px;
  flex-shrink: 0;
}
.requirement-card .dc-type-tag {
  background: #e8f4fd;
  color: #409eff;
}
.bug-type-tag {
  background: #fde8e8;
  color: #f56c6c;
}
.iteration-type-tag {
  background: #e8f8e8;
  color: #67c23a;
}
.project-type-tag {
  background: #f0f9ff;
  color: #2563eb;
}

.dc-title {
  flex: 1;
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.dc-priority-tag,
.dc-severity-tag {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 3px;
  flex-shrink: 0;
}
.pri-p0, .sev-critical { background: #fef2f2; color: #dc2626; }
.pri-p1, .sev-major   { background: #fff7ed; color: #ea580c; }
.pri-p2, .sev-minor   { background: #f0f9ff; color: #2563eb; }
.pri-p3, .sev-trivial { background: #f8fafc; color: #64748b; }

.dc-status-tag {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 10px;
  flex-shrink: 0;
}
.req-status-todo, .bug-status-open, .iter-status-planned {
  background: #f1f5f9; color: #64748b;
}
.req-status-in_progress, .bug-status-in_progress, .iter-status-active {
  background: #ecf5ff; color: #409eff;
}
.req-status-in_review, .bug-status-verified {
  background: #fdf6e8; color: #e6a23c;
}
.req-status-done, .req-status-closed, .bug-status-fixed, .bug-status-closed, .iter-status-completed {
  background: #f0f9eb; color: #67c23a;
}
.req-status-backlog {
  background: #f9f0ff; color: #7c3aed;
}

.dc-arrow {
  color: #c0c8d4;
  font-size: 14px;
  flex-shrink: 0;
  transition: color 0.2s;
}
.domain-card:hover .dc-arrow {
  color: #409eff;
}

.dc-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  padding: 0 12px 7px 12px;
}
.dc-meta-item {
  font-size: 11px;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 3px;
  flex-shrink: 0;
}
.dc-meta-item i {
  font-size: 11px;
}

/* ---- collapsible card group ---- */
.card-group {
  margin: 6px 0;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}
.card-group-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #f8fafc;
  cursor: pointer;
  user-select: none;
  font-size: 12px;
  color: #64748b;
  border-bottom: 1px solid #f1f5f9;
}
.card-group-header:hover {
  background: #f1f5f9;
}
.cg-arrow {
  font-size: 10px;
  transition: transform 0.2s;
  display: inline-block;
}
.cg-arrow.cg-collapsed {
  transform: rotate(-90deg);
}
.cg-label {
  font-weight: 600;
  color: #334155;
}
.cg-count {
  background: #e2e8f0;
  padding: 1px 6px;
  border-radius: 10px;
  font-size: 11px;
  color: #64748b;
}
.card-group-body .domain-card {
  margin: 0;
  border-radius: 0;
  border: none;
  border-bottom: 1px solid #f1f5f9;
}
.card-group-body .domain-card:last-child {
  border-bottom: none;
}

/* ---- body / summary (used by iteration/project cards) ---- */
.dc-body {
  padding: 8px 14px 4px 14px;
}
.dc-summary {
  font-size: 12px;
  color: #64748b;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.dc-iter-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}
.dc-progress-bar {
  flex: 1;
  height: 6px;
  border-radius: 3px;
  background: #e2e8f0;
  overflow: hidden;
}
.dc-progress-fill {
  height: 100%;
  border-radius: 3px;
  background: linear-gradient(90deg, #409eff, #67c23a);
  transition: width 0.4s ease;
}
.dc-progress-text {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  min-width: 36px;
  text-align: right;
}

.dc-project-stats {
  display: flex;
  gap: 16px;
  margin-top: 8px;
}
.dc-project-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.dc-stat-num {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
}
.dc-stat-label {
  font-size: 10px;
  color: #94a3b8;
}

/* ---- actions (used by iteration/project cards) ---- */
.dc-actions {
  padding: 6px 14px 10px 14px;
  border-top: 1px solid #f1f5f9;
}

/* Text element — clean inline rendering */
.el-text {
  font-size: 14px;
  line-height: 1.7;
  color: #1e293b;
  word-wrap: break-word;
}

.el-text :deep(p),
.bubble-content :deep(p) {
  margin: 0 0 8px;
}

.el-text :deep(p:last-child),
.bubble-content :deep(p:last-child) {
  margin-bottom: 0;
}

.el-text :deep(h1),
.el-text :deep(h2),
.el-text :deep(h3),
.bubble-content :deep(h1),
.bubble-content :deep(h2),
.bubble-content :deep(h3) {
  margin: 12px 0 6px;
  line-height: 1.35;
  color: #0f172a;
  font-weight: 600;
}

.el-text :deep(h1),
.bubble-content :deep(h1) { font-size: 19px; }
.el-text :deep(h2),
.bubble-content :deep(h2) { font-size: 16px; }
.el-text :deep(h3),
.bubble-content :deep(h3) { font-size: 14px; }

.el-text :deep(ul),
.bubble-content :deep(ul) {
  margin: 4px 0 10px;
  padding-left: 20px;
}

.el-text :deep(li),
.bubble-content :deep(li) {
  margin: 3px 0;
  line-height: 1.6;
}

.el-text :deep(blockquote),
.bubble-content :deep(blockquote) {
  margin: 8px 0;
  padding: 8px 12px;
  border-left: 3px solid #c7d2fe;
  background: #f8fafc;
  border-radius: 0 6px 6px 0;
  color: #475569;
}

.el-text :deep(a),
.bubble-content :deep(a) {
  color: #4080ff;
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: border-color 0.15s;
}

.el-text :deep(a:hover),
.bubble-content :deep(a:hover) {
  border-bottom-color: #4080ff;
}

.el-text :deep(.markdown-table-wrap),
.bubble-content :deep(.markdown-table-wrap) {
  overflow-x: auto;
  margin: 10px 0;
  border-radius: 8px;
  border: 1px solid #e8ecf2;
}

.el-text :deep(.markdown-table),
.bubble-content :deep(.markdown-table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  background: #fff;
}

.el-text :deep(.markdown-table th),
.el-text :deep(.markdown-table td),
.bubble-content :deep(.markdown-table th),
.bubble-content :deep(.markdown-table td) {
  border: 1px solid #eef1f6;
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
}

.el-text :deep(.markdown-table th),
.bubble-content :deep(.markdown-table th) {
  background: #f8fafc;
  font-weight: 600;
  color: #334155;
  font-size: 12px;
}

.el-text :deep(.markdown-table tr:nth-child(even) td),
.bubble-content :deep(.markdown-table tr:nth-child(even) td) {
  background: #fafcff;
}

.el-text :deep(pre) {
  background: #1a1d2e;
  color: #e2e8f0;
  padding: 14px;
  border-radius: 8px;
  overflow: auto;
  max-height: 400px;
  font-size: 12.5px;
  margin: 10px 0;
  line-height: 1.55;
  border: 1px solid #2d3148;
}

.el-text :deep(code) {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12.5px;
  color: #b45309;
}

.el-text :deep(pre code) {
  background: none;
  padding: 0;
  color: inherit;
  font-size: inherit;
}

.code-actions {
  display: flex;
  gap: 4px;
}

.code-actions .el-button--mini {
  font-size: 11px;
  padding: 2px 8px;
  color: #4080ff;
}

.code-body {
  padding: 14px;
  margin: 0;
  background: #1a1d2e;
  color: #e2e8f0;
  font-size: 12.5px;
  line-height: 1.55;
  text-align: left;
  white-space: pre;
  overflow-x: auto;
  max-height: 380px;
  overflow-y: auto;
  border: 1px solid #2d3148;
  border-radius: 8px;
}

.code-body,
.table-scroll,
.raw-output,
.service-log-section pre,
.service-preview-frame,
.webpage-frame {
  scrollbar-width: thin;
  scrollbar-color: #3d4460 transparent;
}

.code-body::-webkit-scrollbar,
.table-scroll::-webkit-scrollbar,
.raw-output::-webkit-scrollbar,
.service-log-section pre::-webkit-scrollbar,
.service-preview-frame::-webkit-scrollbar,
.webpage-frame::-webkit-scrollbar {
  width: 4px;
  height: 4px;
}

.code-body::-webkit-scrollbar-track,
.table-scroll::-webkit-scrollbar-track,
.raw-output::-webkit-scrollbar-track,
.service-log-section pre::-webkit-scrollbar-track,
.service-preview-frame::-webkit-scrollbar-track,
.webpage-frame::-webkit-scrollbar-track {
  background: transparent;
}

.code-body::-webkit-scrollbar-thumb,
.table-scroll::-webkit-scrollbar-thumb,
.raw-output::-webkit-scrollbar-thumb,
.service-log-section pre::-webkit-scrollbar-thumb,
.service-preview-frame::-webkit-scrollbar-thumb,
.webpage-frame::-webkit-scrollbar-thumb {
  background: #3d4460;
  border-radius: 999px;
}


.code-body code {
  font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace;
  text-align: left;
  white-space: pre;
}

/* Artifacts */
.artifact-block {
  border: 1px solid #e8ecf2;
  border-radius: 10px;
  background: #fcfdff;
  overflow: hidden;
  transition: border-color 0.2s;
}

.artifact-group {
  margin-bottom: 12px;
}

.artifact-group:last-child {
  margin-bottom: 0;
}

.artifact-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.preview-toggle-chip {
  border: 1px solid #dde3ef;
  background: #ffffff;
  color: #475569;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 11px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  transition: all 0.15s;
}

.preview-toggle-chip:hover {
  background: #f8fbff;
  border-color: #bcd2f7;
  color: #2563eb;
}

.preview-toggle-box {
  width: 16px;
  height: 16px;
  border: 1px solid #d7dfeb;
  border-radius: 4px;
  background: #ffffff;
  color: #2563eb;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.15s;
}

.preview-toggle-box.checked {
  border-color: #9fc7ff;
  background: #eff6ff;
}

.preview-toggle-box i {
  font-size: 12px;
  font-weight: 700;
}

.artifact-file-row {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 0;
  padding: 12px 14px;
  border: 1px solid #e2e8f2;
  border-radius: 10px;
  background: #ffffff;
  cursor: pointer;
  transition: all 0.2s ease;
}

.artifact-file-mainline {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  width: 100%;
}

.artifact-file-row:hover {
  border-color: #b0cffc;
  background: #fafcff;
  box-shadow: 0 2px 12px rgba(64, 128, 255, 0.07);
  transform: translateY(-1px);
}

.artifact-toggle-btn {
  width: 26px;
  height: 26px;
  border: none;
  border-radius: 7px;
  background: #f1f5f9;
  color: #64748b;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.15s;
}

.artifact-toggle-btn:hover {
  background: #e2eaf5;
  color: #334155;
}

.artifact-toggle-spacer {
  width: 26px;
  height: 26px;
  flex-shrink: 0;
}

.artifact-kind-chip {
  padding: 3px 9px;
  border-radius: 999px;
  background: #eef2ff;
  color: #5b6b8c;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;
}

.file-size-inline-text {
  color: #8b9ab8;
  font-size: 11px;
  font-weight: 400;
  white-space: nowrap;
  flex-shrink: 0;
}

.artifact-row-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  flex-shrink: 0;
}

.artifact-detail-pane {
  margin-top: 10px;
  margin-left: 20px;
  animation: detailSlideDown 0.2s ease-out;
}

@keyframes detailSlideDown {
  from { opacity: 0; transform: translateY(-6px); }
  to { opacity: 1; transform: translateY(0); }
}

.artifact-detail-card {
  border-radius: 9px;
  background: #f9fbff;
}

.artifact-inline-loading {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 14px 16px;
  color: #64748b;
  font-size: 12px;
}

.summary-file-row {
  border-style: dashed;
  background: #fcfdff;
}

.artifact-summary-wrap {
  padding: 4px 0 2px;
  background: #ffffff;
}

.artifact-summary-title {
  padding: 6px 0 8px;
  font-size: 14px;
  font-weight: 700;
  color: #334155;
  text-align: center;
}

.artifact-header {
  min-height: 34px;
  padding: 8px 11px;
  display: flex;
  align-items: center;
  gap: 7px;
  border-bottom: 1px solid #e8edf5;
  color: #334155;
  font-size: 12px;
  font-weight: 600;
  background: #f8fafc;
}

.artifact-header i {
  color: #4080ff;
  font-size: 15px;
}

.artifact-meta {
  padding: 1px 7px;
  border-radius: 999px;
  background: #eef2ff;
  color: #64748b;
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
}

.artifact-title-btn {
  border: none;
  background: transparent;
  padding: 0;
  min-width: 0;
  color: #2563eb;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.artifact-title-btn:hover {
  text-decoration: underline;
}

.table-scroll {
  overflow-x: auto;
  padding: 10px;
}

.table-meta-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px 0;
}

.table-path-btn {
  max-width: calc(100% - 72px);
}

.table-meta-summary {
  color: #94a3b8;
  font-size: 11px;
  white-space: nowrap;
}

.summary-table-meta-row {
  padding: 0 0 8px;
  justify-content: flex-end;
  gap: 10px;
}

.summary-table-scroll {
  padding: 0;
}

.summary-table-plain {
  padding: 0;
}

.summary-table-plain :deep(.el-table th.el-table__cell) {
  background: #eef6ff;
}

.table-block :deep(.el-table) {
  border-radius: 6px;
  overflow: hidden;
}

.table-block :deep(.el-table th.el-table__cell) {
  background: #f1f5f9;
  color: #334155;
  font-weight: 600;
}

.image-frame {
  padding: 10px;
  background: #ffffff;
}

.artifact-image-compact {
  max-height: 280px;
}

.webpage-path {
  padding: 8px 10px 0;
}

.webpage-preview {
  padding: 10px;
  background: #ffffff;
}

.webpage-frame {
  display: block;
  width: 100%;
  min-height: 320px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #ffffff;
}

.webpage-preview-paused {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 320px;
  border: 1px dashed #d0d7e2;
  border-radius: 8px;
  background: #f8fafc;
  color: #6b7280;
  font-size: 13px;
}

.artifact-image {
  display: block;
  max-width: 100%;
  max-height: 420px;
  object-fit: contain;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #f8fafc;
  cursor: zoom-in;
}

.el-text :deep(.inline-markdown-image),
.bubble-content :deep(.inline-markdown-image) {
  display: block;
  max-width: 100%;
  max-height: 400px;
  object-fit: contain;
  border: 1px solid #e8eaed;
  border-radius: 8px;
  background: #f8fafc;
}

.file-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.file-card:hover {
  border-color: #9fc7ff;
  background: #f7fbff;
}

.file-icon {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #eaf3ff;
  color: #2563eb;
  flex-shrink: 0;
}

.file-icon i {
  font-size: 18px;
}

.file-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.file-info-row {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 0;
  min-width: 0;
  width: 100%;
}

.file-info-stack {
  min-width: 0;
  flex: 0 1 auto;
  max-width: 360px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 3px;
}

.file-attr-group {
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  min-width: 130px;
  flex: 0 0 auto;
  margin-left: 30px;
  margin-right: auto;
  flex-shrink: 0;
}

.file-title-line {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.file-link-btn {
  border: none;
  background: transparent;
  padding: 0;
  color: #1e293b;
  font-size: 15px;
  line-height: 1.2;
  font-weight: 700;
  cursor: pointer;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-path {
  color: #8fa0b7;
  font-size: 12px;
  line-height: 1.2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-meta-line {
  display: flex;
  align-items: center;
  min-width: 0;
}

.file-diff-inline-row {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #eef2f7;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
}

.file-diff-inline-main {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.file-diff-label {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
}

.file-diff-stats {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.file-diff-actions {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  margin-left: auto;
}

.artifact-row-actions :deep(.artifact-action-btn.el-button--text),
.file-diff-actions :deep(.artifact-action-btn.el-button--text) {
  color: #2563eb;
  font-size: 12px;
  font-weight: 600;
  padding: 6px 12px;
  min-height: auto;
  line-height: 1.2;
  border: 1px solid #d8e6ff;
  border-radius: 999px;
  background: #f8fbff;
}

.artifact-row-actions :deep(.artifact-action-btn.el-button--text:hover),
.file-diff-actions :deep(.artifact-action-btn.el-button--text:hover) {
  color: #1d4ed8;
  border-color: #bfd5ff;
  background: #eef5ff;
}

.artifact-row-actions :deep(.artifact-action-btn.el-button--text + .artifact-action-btn.el-button--text),
.file-diff-actions :deep(.artifact-action-btn.el-button--text + .artifact-action-btn.el-button--text) {
  margin-left: 0;
}

.file-diff-note {
  color: #7b8aa5;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}

.file-meta-line .file-path {
  min-width: 0;
  flex: 1 1 auto;
}

.file-size {
  font-size: 11px;
  color: #94a3b8;
}

.file-size-inline {
  flex-shrink: 0;
}

.artifact-attached-diff {
  margin-top: 12px;
  padding-top: 4px;
}

.diff-card {
  padding: 10px 12px;
  border: 1px solid #dbe7f3;
  border-radius: 10px;
  background: linear-gradient(180deg, #fbfdff 0%, #f5f9ff 100%);
}

.diff-path {
  margin-top: 6px;
  font-size: 11px;
  color: #94a3b8;
  word-break: break-all;
}

.diff-body {
  margin: 10px 0 0;
  padding: 10px 12px;
  border-radius: 8px;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 12px;
  line-height: 1.55;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.diff-stat {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}

.diff-add {
  background: #e8f8ee;
  color: #1f8f55;
}

.diff-del {
  background: #fff0f0;
  color: #d14343;
}

.service-card {
  padding: 0;
  background: #ffffff;
}

.service-card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-bottom: 1px solid #e8edf5;
  background: #f8fbff;
}

.service-icon {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #eaf3ff;
  color: #2563eb;
  flex-shrink: 0;
}

.service-title-wrap {
  min-width: 0;
  flex: 1;
}

.service-card-title {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.service-subtitle {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 3px;
  color: #64748b;
  font-size: 11px;
}

.service-description {
  padding: 10px 12px 0;
  font-size: 13px;
  line-height: 1.6;
  color: #334155;
}

.service-description :deep(p) {
  margin: 0 0 6px;
}

.service-url-row {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 10px 12px 0;
  padding: 8px 10px;
  border: 1px solid #dbeafe;
  border-radius: 7px;
  background: #f8fbff;
  font-size: 12px;
}

.service-url-row i {
  color: #4080ff;
}

.service-url-row a {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #2563eb;
  text-decoration: none;
}

.service-meta-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 7px;
  margin: 10px 12px 0;
}

.service-meta-item {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  font-size: 12px;
}

.service-meta-item span {
  width: 34px;
  color: #64748b;
  flex-shrink: 0;
}

.service-meta-item code {
  min-width: 0;
  flex: 1;
  padding: 5px 7px;
  border-radius: 6px;
  background: #f1f5f9;
  color: #475569;
  font-size: 11px;
  word-break: break-all;
}

.service-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  padding: 12px;
}

.steps-collapse {
  margin-top: 10px;
  border-top: 1px solid #f0f0f0;
  border-bottom: none;
}

.steps-collapse :deep(.el-collapse-item__header) {
  height: 32px;
  line-height: 32px;
  font-size: 12px;
  color: #64748b;
  border-bottom: none;
}

.steps-collapse :deep(.el-collapse-item__wrap) {
  border-bottom: none;
}

.steps-panel {
  padding: 8px 10px;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  background: #fbfcff;
}

.steps-title {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 6px;
  font-weight: 600;
}

.step-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 5px 0;
}

.step-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 6px;
  background: #94a3b8;
  flex-shrink: 0;
}

.step-agent_task_started {
  background: #4080ff;
}

.step-file_write {
  background: #67c23a;
}

.step-agent_task_completed {
  background: #22c55e;
}

.step-error {
  background: #f56c6c;
}

.step-main {
  min-width: 0;
}

.step-title {
  font-size: 12px;
  color: #334155;
  line-height: 1.5;
}

.step-file {
  display: block;
  border: none;
  background: transparent;
  padding: 1px 0;
  color: #4080ff;
  font-size: 12px;
  cursor: pointer;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Fallback content */
.bubble-content {
  font-size: 14px;
  line-height: 1.7;
  color: #1e293b;
  word-wrap: break-word;
}

.bubble-content :deep(pre) {
  background: #1a1d2e;
  color: #e2e8f0;
  padding: 14px;
  border-radius: 8px;
  overflow: auto;
  max-height: 400px;
  font-size: 12.5px;
  margin: 10px 0;
  line-height: 1.55;
}

.bubble-content :deep(code) {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12.5px;
  color: #b45309;
}

.bubble-content :deep(pre code) {
  background: none;
  padding: 0;
  color: inherit;
}

/* ===== Table styles (shared) ===== */
.table-scroll {
  overflow-x: auto;
  padding: 10px;
}

.table-meta-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px 0;
}

.table-path-btn {
  max-width: calc(100% - 72px);
}

.table-meta-summary {
  color: #94a3b8;
  font-size: 11px;
  white-space: nowrap;
}

.summary-table-meta-row {
  padding: 0 0 8px;
  justify-content: flex-end;
  gap: 10px;
}

.summary-table-scroll {
  padding: 0;
}

.summary-table-plain {
  padding: 0;
}

.summary-table-plain :deep(.el-table th.el-table__cell) {
  background: #eef6ff;
}

.table-block :deep(.el-table) {
  border-radius: 6px;
  overflow: hidden;
}

.table-block :deep(.el-table th.el-table__cell) {
  background: #f1f5f9;
  color: #334155;
  font-weight: 600;
}

/* ===== Image ===== */
.image-frame {
  padding: 10px;
  background: #ffffff;
}

.artifact-image-compact {
  max-height: 280px;
}

.artifact-image {
  display: block;
  max-width: 100%;
  max-height: 420px;
  object-fit: contain;
  border: 1px solid #e8ecf2;
  border-radius: 8px;
  background: #f8fafc;
  cursor: zoom-in;
  transition: transform 0.2s;
}

.artifact-image:hover {
  transform: scale(1.02);
}

.el-text :deep(.inline-markdown-image),
.bubble-content :deep(.inline-markdown-image) {
  display: block;
  max-width: 100%;
  max-height: 400px;
  object-fit: contain;
  border: 1px solid #e8ecf2;
  border-radius: 8px;
  background: #f8fafc;
}

/* ===== Webpage ===== */
.webpage-path {
  padding: 8px 10px 0;
}

.webpage-preview {
  padding: 10px;
  background: #ffffff;
}

.webpage-frame {
  display: block;
  width: 100%;
  min-height: 320px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #ffffff;
}

.webpage-preview-paused {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 320px;
  border: 1px dashed #d0d7e2;
  border-radius: 8px;
  background: #f8fafc;
  color: #6b7280;
  font-size: 13px;
}

/* ===== File Card ===== */
.file-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.file-card:hover {
  border-color: #9fc7ff;
  background: #f7fbff;
}

.file-icon {
  width: 36px;
  height: 36px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #eff6ff 0%, #e8f0fe 100%);
  color: #4080ff;
  flex-shrink: 0;
}

.file-icon i {
  font-size: 18px;
}

.file-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.file-info-row {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 0;
  min-width: 0;
  width: 100%;
}

.file-info-stack {
  min-width: 0;
  flex: 0 1 auto;
  max-width: 360px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 3px;
}

.file-attr-group {
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  min-width: 130px;
  flex: 0 0 auto;
  margin-left: 30px;
  margin-right: auto;
  flex-shrink: 0;
}

.file-title-line {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.file-link-btn {
  border: none;
  background: transparent;
  padding: 0;
  color: #1e293b;
  font-size: 14px;
  line-height: 1.3;
  font-weight: 600;
  cursor: pointer;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color 0.15s;
}

.file-link-btn:hover {
  color: #4080ff;
}

.file-path {
  color: #8fa0b7;
  font-size: 12px;
  line-height: 1.2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-meta-line {
  display: flex;
  align-items: center;
  min-width: 0;
}

.file-diff-inline-row {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #eef2f7;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
}

.file-diff-inline-main {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.file-diff-label {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
}

.file-diff-stats {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.file-diff-actions {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  margin-left: auto;
}

.artifact-row-actions :deep(.artifact-action-btn.el-button--text),
.file-diff-actions :deep(.artifact-action-btn.el-button--text) {
  color: #2563eb;
  font-size: 11px;
  font-weight: 600;
  padding: 5px 12px;
  min-height: auto;
  line-height: 1.2;
  border: 1px solid #d8e6ff;
  border-radius: 999px;
  background: #f8fbff;
  transition: all 0.15s;
}

.artifact-row-actions :deep(.artifact-action-btn.el-button--text:hover),
.file-diff-actions :deep(.artifact-action-btn.el-button--text:hover) {
  color: #1d4ed8;
  border-color: #bfd5ff;
  background: #eef5ff;
}

.artifact-row-actions :deep(.artifact-action-btn.el-button--text + .artifact-action-btn.el-button--text),
.file-diff-actions :deep(.artifact-action-btn.el-button--text + .artifact-action-btn.el-button--text) {
  margin-left: 0;
}

.file-diff-note {
  color: #7b8aa5;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}

.file-meta-line .file-path {
  min-width: 0;
  flex: 1 1 auto;
}

.artifact-attached-diff {
  margin-top: 12px;
  padding-top: 4px;
}

/* ===== Diff Card ===== */
.diff-card {
  padding: 12px 14px;
  border: 1px solid #dce4f2;
  border-radius: 10px;
  background: linear-gradient(180deg, #fbfdff 0%, #f6faff 100%);
}

.diff-path {
  margin-top: 6px;
  font-size: 11px;
  color: #94a3b8;
  word-break: break-all;
}

.diff-body {
  margin: 10px 0 0;
  padding: 12px 14px;
  border-radius: 8px;
  background: #1a1d2e;
  color: #e2e8f0;
  font-size: 12px;
  line-height: 1.55;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.diff-stat {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 40px;
  height: 22px;
  padding: 0 9px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}

.diff-add {
  background: #e6f7ec;
  color: #1f8f55;
}

.diff-del {
  background: #fff0f0;
  color: #d14343;
}

/* ===== Service Card ===== */
.service-card {
  padding: 0;
  background: #ffffff;
}

.service-card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-bottom: 1px solid #e8edf5;
  background: #f8fbff;
}

.service-icon {
  width: 36px;
  height: 36px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #eff6ff 0%, #e8f0fe 100%);
  color: #4080ff;
  flex-shrink: 0;
}

.service-title-wrap {
  min-width: 0;
  flex: 1;
}

.service-card-title {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.service-subtitle {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 3px;
  color: #64748b;
  font-size: 11px;
}

.service-description {
  padding: 10px 12px 0;
  font-size: 13px;
  line-height: 1.6;
  color: #334155;
}

.service-description :deep(p) {
  margin: 0 0 6px;
}

.service-url-row {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 10px 12px 0;
  padding: 8px 10px;
  border: 1px solid #dbeafe;
  border-radius: 7px;
  background: #f8fbff;
  font-size: 12px;
}

.service-url-row i {
  color: #4080ff;
}

.service-url-row a {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #2563eb;
  text-decoration: none;
}

.service-meta-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 7px;
  margin: 10px 12px 0;
}

.service-meta-item {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  font-size: 12px;
}

.service-meta-item span {
  width: 34px;
  color: #64748b;
  flex-shrink: 0;
}

.service-meta-item code {
  min-width: 0;
  flex: 1;
  padding: 5px 7px;
  border-radius: 6px;
  background: #f1f5f9;
  color: #475569;
  font-size: 11px;
  word-break: break-all;
}

.service-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  padding: 12px;
}

/* ===== Steps / History ===== */
.steps-collapse {
  margin-top: 12px;
  border-top: 1px solid #f0f3f8;
  border-bottom: none;
}

.steps-collapse :deep(.el-collapse-item__header) {
  height: 32px;
  line-height: 32px;
  font-size: 12px;
  color: #64748b;
  border-bottom: none;
  font-weight: 500;
}

.steps-collapse :deep(.el-collapse-item__wrap) {
  border-bottom: none;
}

.steps-panel {
  padding: 10px 12px;
  border: 1px solid #eef1f6;
  border-radius: 10px;
  background: #fcfdff;
}

.steps-title {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 8px;
  font-weight: 600;
}

.step-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 5px 0;
}

.step-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 6px;
  background: #94a3b8;
  flex-shrink: 0;
}

.step-agent_task_started { background: #4080ff; }
.step-file_write { background: #22c55e; }
.step-agent_task_completed { background: #22c55e; }
.step-error { background: #ef4444; }

.step-main {
  min-width: 0;
}

.step-title {
  font-size: 12px;
  color: #334155;
  line-height: 1.5;
}

.step-file {
  display: block;
  border: none;
  background: transparent;
  padding: 1px 0;
  color: #4080ff;
  font-size: 12px;
  cursor: pointer;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ===== Raw Output (collapsed) ===== */
.raw-collapse {
  margin-top: 12px;
  border-top: 1px solid #f0f3f8;
  border-bottom: none;
}

.raw-collapse :deep(.el-collapse-item__header) {
  height: 32px;
  line-height: 32px;
  font-size: 12px;
  color: #64748b;
  border-bottom: none;
}

.raw-collapse :deep(.el-collapse-item__wrap) {
  border-bottom: none;
}

.raw-output {
  margin: 0;
  padding: 12px;
  max-height: 280px;
  overflow: auto;
  background: #1a1d2e;
  color: #e2e8f0;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.55;
  text-align: left;
  white-space: pre;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
}

/* ===== Raw rendered output (fallback only — no box, clean text) ===== */
.raw-rendered {
  padding: 0;
  border: none;
  background: transparent;
}

.raw-rendered-content {
  font-size: 14px;
  line-height: 1.7;
  color: #334155;
  word-wrap: break-word;
}

.raw-rendered-content :deep(p) {
  margin: 0 0 8px;
}

.raw-rendered-content :deep(p:last-child) {
  margin-bottom: 0;
}

.raw-rendered-content :deep(pre) {
  background: #1a1d2e;
  color: #e2e8f0;
  padding: 14px;
  border-radius: 8px;
  overflow: auto;
  max-height: 420px;
  font-size: 12.5px;
  margin: 10px 0;
  border: 1px solid #2d3148;
  line-height: 1.55;
}

.raw-rendered-content :deep(code) {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  color: #b45309;
  font-size: 12.5px;
}

.raw-rendered-content :deep(pre code) {
  background: transparent;
  padding: 0;
  color: inherit;
}

.raw-rendered-content :deep(.markdown-table-wrap) {
  overflow-x: auto;
  margin: 8px 0;
  border-radius: 8px;
  border: 1px solid #e8ecf2;
}

.raw-rendered-content :deep(.markdown-table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  background: #fff;
}

.raw-rendered-content :deep(.markdown-table th),
.raw-rendered-content :deep(.markdown-table td) {
  border: 1px solid #eef1f6;
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
}

.raw-rendered-content :deep(.markdown-table th) {
  background: #f8fafc;
  font-weight: 600;
  color: #334155;
}

.raw-rendered-content :deep(h1),
.raw-rendered-content :deep(h2),
.raw-rendered-content :deep(h3) {
  margin: 12px 0 7px;
  line-height: 1.35;
  color: #0f172a;
}

.raw-rendered-content :deep(h1) { font-size: 19px; }
.raw-rendered-content :deep(h2) { font-size: 16px; }
.raw-rendered-content :deep(h3) { font-size: 14px; }

.raw-rendered-content :deep(ul) {
  margin: 4px 0 8px;
  padding-left: 20px;
}

.raw-rendered-content :deep(blockquote) {
  margin: 8px 0;
  padding: 8px 12px;
  border-left: 3px solid #93c5fd;
  background: #f8fafc;
  border-radius: 0 6px 6px 0;
  color: #475569;
}

/* ===== Meta bar ===== */
.bubble-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #f5f6f8;
  font-size: 11px;
  color: #bcc4d2;
}

.bubble-time {
  flex: 1;
}

.bubble-sending {
  color: #4080ff;
  font-size: 11px;
}

.message-workflow-tag {
  max-width: min(360px, 70%);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border: 1px solid #dbeafe;
  border-radius: 999px;
  padding: 2px 9px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 11px;
}

.bubble-meta .el-button {
  padding: 0;
  margin-left: auto;
  color: #c0c4cc;
}

.bubble-meta .pinned {
  color: #e6a23c;
}

/* ===== Streaming indicator ===== */
.streaming-line {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid #f0f3f8;
  font-size: 12px;
  color: #4080ff;
}

.artifact-link {
  margin-top: 4px;
}

/* ===== Service dialogs ===== */
.service-preview-dialog :deep(.el-dialog) {
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.24);
}

.service-preview-dialog :deep(.el-dialog__header) {
  padding: 16px 18px 14px;
  border-bottom: 1px solid #e8edf5;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
}

.service-preview-dialog :deep(.el-dialog__title) {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.service-preview-dialog :deep(.el-dialog__headerbtn) {
  top: 16px;
}

.service-preview-dialog :deep(.el-dialog__body) {
  padding: 0;
  background: #f8fafc;
}

.service-preview-toolbar {
  min-height: 48px;
  padding: 0 16px;
  border-bottom: 1px solid #e8edf5;
  display: flex;
  align-items: center;
  gap: 10px;
  background: #ffffff;
}

.service-preview-toolbar span {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  color: #475569;
}

.service-preview-frame {
  display: block;
  width: 100%;
  height: 74vh;
  border: none;
  background: #ffffff;
}

.service-logs-dialog :deep(.el-dialog__body) {
  padding: 14px 18px 18px;
}

.service-logs-meta {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

.service-log-section + .service-log-section {
  margin-top: 12px;
}

.service-log-title {
  font-size: 12px;
  font-weight: 700;
  color: #475569;
  margin-bottom: 5px;
}

.service-log-section pre {
  margin: 0;
  padding: 10px;
  min-height: 90px;
  max-height: 240px;
  overflow: auto;
  border-radius: 7px;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
}

</style>
