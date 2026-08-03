<template>
  <div class="rd-project-detail-page">
    <AppSidebar />

    <main class="rd-detail-content">
      <!-- 顶部导航 -->
      <header class="detail-header">
        <el-button type="text" icon="el-icon-arrow-left" @click="$router.push('/projects')">
          返回项目列表
        </el-button>
        <div class="header-main" v-if="project">
          <div class="header-info">
            <h2>{{ project.name }}</h2>
            <span class="header-desc" v-if="project.description">{{ project.description }}</span>
          </div>
          <div class="header-actions">
            <el-button size="small" icon="el-icon-edit" @click="openEditProject">编辑</el-button>
            <el-button size="small" icon="el-icon-chat-dot-round" type="primary" @click="startConversation">
              AI 对话
            </el-button>
          </div>
        </div>
        <!-- Tabs -->
        <el-tabs v-model="activeTab" class="detail-tabs">
          <el-tab-pane label="概览" name="overview" />
          <el-tab-pane label="迭代" name="iterations" />
          <el-tab-pane label="需求" name="requirements" />
          <el-tab-pane label="缺陷" name="bugs" />
          <el-tab-pane label="成员" name="members" />
          <el-tab-pane label="甘特图" name="gantt" />
          <el-tab-pane label="代码仓库" name="repos" />
        </el-tabs>
      </header>

      <div class="detail-body" v-loading="loading">
        <!-- ==================== 概览 Tab ==================== -->
        <template v-if="activeTab === 'overview'">
          <!-- 技术栈概览 -->
          <section class="info-cards">
            <div class="info-card">
              <h4><i class="el-icon-monitor"></i> 前端</h4>
              <span>{{ tech.frontend }}</span>
            </div>
            <div class="info-card">
              <h4><i class="el-icon-cpu"></i> 后端</h4>
              <span>{{ tech.backend }}</span>
            </div>
            <div class="info-card">
              <h4><i class="el-icon-coin"></i> 数据库</h4>
              <span>{{ tech.database }}</span>
            </div>
            <div class="info-card">
              <h4><i class="el-icon-upload2"></i> 部署</h4>
              <span>{{ tech.deployment }}</span>
            </div>
          </section>

          <!-- 统计数据 -->
          <section class="stats-row">
            <div class="stat-card">
              <div class="stat-icon" style="background: #e8f4fd;"><i class="el-icon-s-flag" style="color:#409eff" /></div>
              <div class="stat-body">
                <div class="stat-num">{{ iterations.length }}</div>
                <div class="stat-label">迭代</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon" style="background: #e8f8e8;"><i class="el-icon-document" style="color:#67c23a" /></div>
              <div class="stat-body">
                <div class="stat-num">{{ requirements.length }}</div>
                <div class="stat-label">需求</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon" style="background: #fde8e8;"><i class="el-icon-warning" style="color:#f56c6c" /></div>
              <div class="stat-body">
                <div class="stat-num">{{ bugs.length }}</div>
                <div class="stat-label">缺陷</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon" style="background: #fdf6e8;"><i class="el-icon-folder-opened" style="color:#e6a23c" /></div>
              <div class="stat-body">
                <div class="stat-num">{{ repos.length }}</div>
                <div class="stat-label">仓库</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon" style="background: #e8f0fe;"><i class="el-icon-circle-check" style="color:#909399" /></div>
              <div class="stat-body">
                <div class="stat-num">{{ builds.filter(b => b.status === 'success').length }}/{{ builds.length }}</div>
                <div class="stat-label">构建通过</div>
              </div>
            </div>
          </section>

          <!-- 当前迭代 + 最近构建 -->
          <section class="overview-panels">
            <div class="overview-panel">
              <div class="panel-header">
                <h4><i class="el-icon-s-flag"></i> 当前迭代</h4>
                <el-button type="text" size="mini" @click="activeTab = 'iterations'">查看全部</el-button>
              </div>
              <div v-if="activeIteration" class="active-iteration-card">
                <div class="ai-top">
                  <div class="ai-badge">
                    <span class="ai-badge-dot"></span>
                    进行中
                  </div>
                  <span class="ai-name">{{ activeIteration.name }}</span>
                </div>
                <div class="ai-body">
                  <div class="ai-meta-row">
                    <span class="ai-meta"><i class="el-icon-date"></i> {{ activeIteration.start_date || '未定' }} — {{ activeIteration.end_date || '未定' }}</span>
                    <span class="ai-meta"><i class="el-icon-document"></i> {{ iterReqs.length }} 需求</span>
                    <span class="ai-meta"><i class="el-icon-warning"></i> {{ iterBugs.length }} 缺陷</span>
                  </div>
                  <div class="ai-progress">
                    <div class="progress-track">
                      <div class="progress-fill" :style="{ width: iterationProgress + '%' }">
                        <span v-if="iterationProgress >= 15" class="progress-inner-text">{{ iterationProgress }}%</span>
                      </div>
                    </div>
                    <span v-if="iterationProgress < 15" class="progress-text-out">{{ iterationProgress }}%</span>
                  </div>
                  <div class="ai-goal" v-if="activeIteration.goal" v-html="renderMarkdown(activeIteration.goal)"></div>
                </div>
              </div>
              <div v-else class="panel-empty">
                <i class="el-icon-s-flag" style="font-size:40px;color:#dcdfe6;margin-bottom:8px;display:block"></i>
                <p>暂无进行中的迭代</p>
                <el-button size="small" type="primary" plain @click="showCreateIteration = true">+ 新建迭代</el-button>
              </div>
            </div>

            <div class="overview-panel">
              <div class="panel-header">
                <h4><i class="el-icon-s-tools"></i> 最近构建</h4>
                <el-button type="text" size="mini" @click="$router.push({ path: '/builds', query: { project_id: projectId } })">查看全部</el-button>
              </div>
              <div v-if="recentBuilds.length" class="build-mini-list">
                <div v-for="b in recentBuilds" :key="b.id" class="build-mini-item" @click="goToBuild(b.id)">
                  <i :class="b.status === 'success' ? 'el-icon-circle-check text-green' : b.status === 'failed' ? 'el-icon-circle-close text-red' : b.status === 'running' || b.status === 'pending' ? 'el-icon-loading' : 'el-icon-minus'" />
                  <span class="bmi-num">#{{ b.build_number }}</span>
                  <span class="bmi-msg" :title="b.commit_message">{{ b.commit_message }}</span>
                  <span class="bmi-time">{{ formatRelative(b.started_at) }}</span>
                  <el-tag :type="b.status === 'success' ? 'success' : b.status === 'failed' || b.status === 'cancelled' ? 'danger' : 'warning'" size="mini">{{ statusLabel(b.status) }}</el-tag>
                </div>
              </div>
              <div v-else class="panel-empty">暂无构建记录</div>
            </div>
          </section>
        </template>

        <!-- ==================== 迭代 Tab ==================== -->
        <template v-if="activeTab === 'iterations'">
          <div class="tab-toolbar">
            <span class="tab-count">共 {{ iterations.length }} 个迭代</span>
            <el-button type="primary" size="small" icon="el-icon-plus" @click="showCreateIteration = true">新建迭代</el-button>
          </div>

          <div v-if="iterations.length === 0" class="iter-empty-state">
            <i class="el-icon-s-flag"></i>
            <h3>暂无迭代</h3>
            <p>创建第一个迭代来规划工作周期</p>
            <el-button type="primary" @click="showCreateIteration = true">+ 新建迭代</el-button>
          </div>

          <div v-else class="iterations-list">
            <div v-for="iter in iterations" :key="iter.id" class="iteration-card" :class="'iter-' + iter.status">
              <!-- 卡片头部 -->
              <div class="iter-head">
                <div class="iter-head-left">
                  <div class="iter-status-dot" :class="'dot-' + iter.status"></div>
                  <div class="iter-head-info">
                    <h4 class="iter-name">{{ iter.name }}</h4>
                    <div class="iter-subtitle">
                      <span class="iter-status-badge" :class="'badge-' + iter.status">
                        {{ iter.status === 'active' ? '进行中' : iter.status === 'completed' ? '已完成' : '计划中' }}
                      </span>
                      <span class="iter-date-range" v-if="iter.start_date || iter.end_date">
                        <i class="el-icon-date"></i>
                        {{ iter.start_date || '?' }} — {{ iter.end_date || '?' }}
                      </span>
                    </div>
                  </div>
                </div>
                <div class="iter-head-actions">
                  <el-button circle size="mini" icon="el-icon-edit" @click.stop="openIterEdit(iter)" title="编辑" />
                  <el-button circle size="mini" icon="el-icon-delete" style="color:#f56c6c" @click.stop="handleDeleteIter(iter)" title="删除" />
                </div>
              </div>

              <!-- 目标 -->
              <div class="iter-goal-area" v-if="iter.goal">
                <i class="el-icon-aim"></i>
                <span v-html="renderMarkdown(iter.goal)"></span>
              </div>

              <!-- 进度条 -->
              <div class="iter-progress-row">
                <div class="iter-progress-bar">
                  <div class="iter-progress-fill" :class="'fill-' + iter.status" :style="{ width: iterProgressPct(iter.id) + '%' }"></div>
                </div>
                <div class="iter-progress-meta">
                  <span class="iter-progress-num">{{ iterProgressPct(iter.id) }}%</span>
                  <span class="iter-progress-label">完成</span>
                </div>
              </div>

              <!-- 统计 -->
              <div class="iter-stats">
                <div class="iter-stat-card">
                  <span class="iter-stat-num">{{ getIterRequirements(iter.id).length }}</span>
                  <span class="iter-stat-label">需求</span>
                </div>
                <div class="iter-stat-card">
                  <span class="iter-stat-num">{{ getIterBugs(iter.id).length }}</span>
                  <span class="iter-stat-label">缺陷</span>
                </div>
                <div class="iter-stat-card">
                  <span class="iter-stat-num">{{ getIterRequirements(iter.id).filter(r => ['done','closed'].includes(r.status)).length + getIterBugs(iter.id).filter(b => ['fixed','verified','closed'].includes(b.status)).length }}</span>
                  <span class="iter-stat-label">已关闭</span>
                </div>
              </div>

              <!-- 看板 -->
              <div class="iter-kanban">
                <div class="kanban-col">
                  <div class="kanban-col-head">
                    <i class="el-icon-document"></i> 需求
                    <span class="kanban-col-count">{{ getIterRequirements(iter.id).length }}</span>
                  </div>
                  <div v-for="r in getIterRequirements(iter.id).slice(0, 5)" :key="r.id" class="kanban-card req-card" @click="goToRequirementDetail(r)">
                    <span class="kanban-card-tag" :class="'pri-' + r.priority">{{ priorityLabel(r.priority) }}</span>
                    <span class="kanban-card-title">{{ r.title }}</span>
                    <span class="kanban-card-status">{{ statusLabel(r.status) }}</span>
                  </div>
                  <div v-if="getIterRequirements(iter.id).length === 0" class="kanban-empty">—</div>
                  <div v-else-if="getIterRequirements(iter.id).length > 5" class="kanban-more" @click="activeTab = 'requirements'; reqFilter.iteration = iter.id">
                    +{{ getIterRequirements(iter.id).length - 5 }} 更多 →
                  </div>
                </div>
                <div class="kanban-col">
                  <div class="kanban-col-head">
                    <i class="el-icon-warning"></i> 缺陷
                    <span class="kanban-col-count">{{ getIterBugs(iter.id).length }}</span>
                  </div>
                  <div v-for="b in getIterBugs(iter.id).slice(0, 5)" :key="b.id" class="kanban-card bug-card" @click="goToBugDetail(b)">
                    <span class="kanban-card-tag" :class="'sev-' + b.severity">{{ severityLabel(b.severity) }}</span>
                    <span class="kanban-card-title">{{ b.title }}</span>
                    <span class="kanban-card-status">{{ bugStatusLabel(b.status) }}</span>
                  </div>
                  <div v-if="getIterBugs(iter.id).length === 0" class="kanban-empty">—</div>
                  <div v-else-if="getIterBugs(iter.id).length > 5" class="kanban-more" @click="activeTab = 'bugs'; bugFilter.iteration = iter.id">
                    +{{ getIterBugs(iter.id).length - 5 }} 更多 →
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- ==================== 需求 Tab ==================== -->
        <template v-if="activeTab === 'requirements'">
          <div class="tab-toolbar">
            <div class="toolbar-left">
              <span class="tab-count">共 {{ filteredRequirements.length }} 个需求</span>
              <el-select v-model="reqFilter.iteration" placeholder="迭代筛选" size="small" clearable style="width:180px;margin-left:12px">
                <el-option v-for="i in iterations" :key="i.id" :label="i.name" :value="i.id" />
              </el-select>
              <el-select v-model="reqFilter.priority" placeholder="优先级" size="small" clearable style="width:100px;margin-left:8px">
                <el-option label="P0 紧急" value="p0" />
                <el-option label="P1 高" value="p1" />
                <el-option label="P2 中" value="p2" />
                <el-option label="P3 低" value="p3" />
              </el-select>
              <el-select v-model="reqFilter.status" placeholder="状态" size="small" clearable style="width:110px;margin-left:8px">
                <el-option label="待规划" value="backlog" />
                <el-option label="待办" value="todo" />
                <el-option label="进行中" value="in_progress" />
                <el-option label="审查中" value="in_review" />
                <el-option label="已完成" value="done" />
              </el-select>
              <el-select v-model="reqFilter.assignee" placeholder="负责人" size="small" clearable style="width:120px;margin-left:8px">
                <el-option v-for="m in projectMembers" :key="m.user_id" :label="m.user_name" :value="m.user_id" />
              </el-select>
            </div>
            <div class="toolbar-right">
              <el-popover placement="bottom-end" trigger="click" width="200">
                <div class="col-toggle-list">
                  <el-checkbox v-model="reqCols.priority">优先级</el-checkbox>
                  <el-checkbox v-model="reqCols.status">状态</el-checkbox>
                  <el-checkbox v-model="reqCols.iteration">迭代</el-checkbox>
                  <el-checkbox v-model="reqCols.assignee">负责人</el-checkbox>
                  <el-checkbox v-model="reqCols.story_points">规模点</el-checkbox>
                  <el-checkbox v-model="reqCols.type">类型</el-checkbox>
                  <el-checkbox v-model="reqCols.labels">标签</el-checkbox>
                  <el-checkbox v-model="reqCols.dates">日期</el-checkbox>
                </div>
                <el-button size="small" icon="el-icon-s-grid" slot="reference" style="margin-right:8px">列显示</el-button>
              </el-popover>
              <el-button size="small" @click="reqMultiSelect = !reqMultiSelect" :type="reqMultiSelect ? 'warning' : ''" icon="el-icon-s-check">{{ reqMultiSelect ? '取消多选' : '多选' }}</el-button>
              <el-button type="primary" size="small" icon="el-icon-plus" @click="showCreateRequirement = true">新建需求</el-button>
            </div>
          </div>

          <!-- 多选操作栏 -->
          <div v-if="reqMultiSelect && reqSelectedIds.length > 0" class="multi-select-bar">
            <span>已选 {{ reqSelectedIds.length }} 项</span>
            <el-button size="mini" @click="batchMoveIteration">批量移入迭代</el-button>
            <el-button size="mini" @click="batchChangeStatus">批量改状态</el-button>
            <el-button size="mini" type="danger" @click="batchDelete">批量删除</el-button>
          </div>

          <el-table
            :data="hierarchicalRequirements"
            class="req-table-enhanced"
            style="width:100%"
            row-key="id"
            border
            @row-click="goToRequirementDetail"
            @selection-change="val => reqSelectedIds = val.map(r => r.id)"
            ref="reqTable"
          >
            <!-- 多选列 -->
            <el-table-column v-if="reqMultiSelect" type="selection" width="42" />

            <!-- ... 操作菜单 -->
            <el-table-column width="40" class-name="col-menu">
              <template slot-scope="{row}">
                <el-popover placement="right-start" trigger="click" width="180" :ref="'row-menu-' + row.id">
                  <div class="row-menu-list">
                    <div class="row-menu-item" @click="goToRequirementDetail(row)"><i class="el-icon-view"></i> 查看详情</div>
                    <div class="row-menu-item" @click="createSubRequirement(row)"><i class="el-icon-plus"></i> 创建子需求</div>
                    <div class="row-menu-item" @click="duplicateReq(row)"><i class="el-icon-document-copy"></i> 复制需求</div>
                    <div class="row-menu-item danger" @click="deleteReqRow(row)"><i class="el-icon-delete"></i> 删除</div>
                  </div>
                  <el-button slot="reference" type="text" size="mini" icon="el-icon-more" class="row-menu-btn" @click.stop />
                </el-popover>
              </template>
            </el-table-column>

            <!-- 标题 (click to edit) -->
            <el-table-column prop="title" label="标题" min-width="250">
              <template slot-scope="{row}">
                <div class="cell-title-wrap" v-if="inlineEditId !== row.id" @click.stop>
                  <span v-if="row._depth > 0" class="tree-indent" :style="{ marginLeft: (row._depth * 20) + 'px' }">
                    <span class="tree-corner"></span>
                  </span>
                  <span class="req-title-text" @click="startInlineEditReq(row)" title="点击编辑标题" :style="{ marginLeft: row._depth > 0 ? '0' : '0' }">{{ row.title }}</span>
                </div>
                <div v-else class="cell-title-edit" @click.stop>
                  <el-input
                    v-model="inlineTitle"
                    size="small"
                    @blur="saveInlineEditReq(row)"
                    @keyup.enter.native="saveInlineEditReq(row)"
                    @keyup.escape.native="cancelInlineEdit"
                    :ref="'inline-input-' + row.id"
                  />
                </div>
              </template>
            </el-table-column>

            <!-- 优先级 (click to dropdown) -->
            <el-table-column v-if="reqCols.priority" prop="priority" label="优先级" width="85">
              <template slot-scope="{row}">
                <el-select
                  v-if="row._editPriority"
                  v-model="row.priority"
                  size="mini"
                  style="width:62px"
                  @change="val => { row.priority = val; row._editPriority = false; rdApi.updateRequirement(row.id, { priority: val }).catch(() => {}) }"
                  @visible-change="vis => { if (!vis) row._editPriority = false }"
                  @click.stop
                >
                  <el-option v-for="p in ['p0','p1','p2','p3']" :key="p" :label="priorityLabel(p)" :value="p" />
                </el-select>
                <div v-else class="priority-btn" :class="'pbtn-' + row.priority" @click.stop="row._editPriority = true">
                  {{ priorityLabel(row.priority) }}
                </div>
              </template>
            </el-table-column>

            <!-- 状态 (click to show dropdown) -->
            <el-table-column v-if="reqCols.status" prop="status" label="状态" width="100">
              <template slot-scope="{row}">
                <el-select
                  v-if="row._editStatus"
                  v-model="row.status"
                  size="mini"
                  style="width:88px"
                  @change="val => { changeReqStatus(row, val); row._editStatus = false }"
                  @visible-change="vis => { if (!vis) row._editStatus = false }"
                  :ref="'sel-status-' + row.id"
                  @click.stop
                >
                  <el-option v-for="s in ['backlog','todo','in_progress','in_review','done','closed']" :key="s" :label="statusLabel(s)" :value="s" />
                </el-select>
                <span v-else class="status-display" :class="'s-' + row.status" @click.stop="row._editStatus = true; $nextTick(() => autoFocusSelect('sel-status-' + row.id))">{{ statusLabel(row.status) }}</span>
              </template>
            </el-table-column>

            <!-- 迭代 (click to change) -->
            <el-table-column v-if="reqCols.iteration" prop="iteration_name" label="迭代" width="130">
              <template slot-scope="{row}">
                <el-select
                  v-if="row._editIter"
                  v-model="row.iteration_id"
                  size="mini"
                  clearable
                  style="width:110px"
                  @change="val => { moveReqIteration(row, val); row._editIter = false }"
                  @visible-change="vis => { if (!vis) row._editIter = false }"
                  @click.stop
                >
                  <el-option v-for="i in iterations" :key="i.id" :label="i.name" :value="i.id" />
                </el-select>
                <el-tag
                  v-else
                  size="mini"
                  :type="row.iteration_id ? 'success' : 'info'"
                  effect="plain"
                  class="clickable-cell"
                  @click.stop="row._editIter = true"
                >{{ row.iteration_name || '待规划' }}</el-tag>
              </template>
            </el-table-column>

            <!-- 负责人 (multi-select) -->
            <el-table-column v-if="reqCols.assignee" prop="assignee_name" label="负责人" width="140">
              <template slot-scope="{row}">
                <el-select
                  v-if="row._editAssignee"
                  v-model="row._assigneeIds"
                  multiple
                  size="mini"
                  placeholder="选择负责人"
                  style="width:125px"
                  @change="saveAssigneeChange(row)"
                  @visible-change="vis => { if (!vis) row._editAssignee = false }"
                  @click.stop
                >
                  <el-option v-for="m in projectMembers" :key="m.user_id" :label="m.user_name" :value="m.user_id" />
                </el-select>
                <div v-else class="assignee-cell" @click.stop="row._editAssignee = true">
                  <template v-if="row.assignee_name">
                    <span class="assignee-avatar-sm" :style="{ background: avatarColor(row.assignee_name) }">{{ row.assignee_name.charAt(0) }}</span>
                    <span class="assignee-text">{{ row.assignee_name }}</span>
                  </template>
                  <span v-else class="no-assignee">-</span>
                </div>
              </template>
            </el-table-column>

            <!-- 规模点 (plain input, click to edit) -->
            <el-table-column v-if="reqCols.story_points" prop="story_points" label="规模点" width="85">
              <template slot-scope="{row}">
                <div v-if="row._editSP" class="cell-edit-inline" @click.stop>
                  <input
                    v-model="row.story_points"
                    type="number"
                    min="0"
                    max="100"
                    class="plain-number-input"
                    @blur="saveStoryPoints(row)"
                    @keyup.enter="saveStoryPoints(row)"
                    :ref="'sp-input-' + row.id"
                  />
                </div>
                <span v-else class="sp-display" :class="{ 'has-sp': row.story_points > 0 }" @click.stop="row._editSP = true; $nextTick(() => { const el = $refs['sp-input-'+row.id]; const inp = Array.isArray(el) ? el[0] : el; if (inp) inp.focus() })">
                  {{ row.story_points || '-' }}
                </span>
              </template>
            </el-table-column>

            <!-- 类型 -->
            <el-table-column v-if="reqCols.type" prop="type" label="类型" width="80">
              <template slot-scope="{row}">
                <span class="type-tag" :class="'tp-' + row.type">{{ typeLabel(row.type) }}</span>
              </template>
            </el-table-column>

            <!-- 标签 -->
            <el-table-column v-if="reqCols.labels" label="标签" width="170">
              <template slot-scope="{row}">
                <div class="label-inline">
                  <el-tag v-for="lb in (row.labels || []).slice(0, 3)" :key="lb" size="mini" effect="plain" style="margin-right:3px">{{ lb }}</el-tag>
                  <span v-if="(row.labels || []).length > 3" class="more-labels">+{{ row.labels.length - 3 }}</span>
                  <span v-if="!row.labels || row.labels.length === 0" class="no-labels">-</span>
                </div>
              </template>
            </el-table-column>

            <!-- 日期 -->
            <el-table-column v-if="reqCols.dates" label="日期" width="170">
              <template slot-scope="{row}">
                <span class="cell-dates" v-if="row.start_date || row.due_date">
                  {{ row.start_date || '?' }} ~ {{ row.due_date || '?' }}
                </span>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
          </el-table>
        </template>

        <!-- ==================== Bug Tab ==================== -->
        <template v-if="activeTab === 'bugs'">
          <div class="tab-toolbar">
            <div class="toolbar-left">
              <span class="tab-count">共 {{ filteredBugs.length }} 个缺陷</span>
              <el-select v-model="bugFilter.iteration" placeholder="迭代筛选" size="small" clearable style="width:150px;margin-left:12px">
                <el-option v-for="i in iterations" :key="i.id" :label="i.name" :value="i.id" />
              </el-select>
              <el-select v-model="bugFilter.severity" placeholder="严重程度" size="small" clearable style="width:100px;margin-left:8px">
                <el-option label="阻塞" value="blocker" />
                <el-option label="致命" value="critical" />
                <el-option label="严重" value="major" />
                <el-option label="一般" value="minor" />
                <el-option label="轻微" value="trivial" />
              </el-select>
              <el-select v-model="bugFilter.status" placeholder="状态" size="small" clearable style="width:100px;margin-left:8px">
                <el-option label="待处理" value="open" />
                <el-option label="已确认" value="confirmed" />
                <el-option label="修复中" value="in_progress" />
                <el-option label="已修复" value="fixed" />
                <el-option label="已验证" value="verified" />
                <el-option label="已关闭" value="closed" />
              </el-select>
              <el-select v-model="bugFilter.assignee" placeholder="负责人" size="small" clearable style="width:110px;margin-left:8px">
                <el-option v-for="m in projectMembers" :key="m.user_id" :label="m.user_name" :value="m.user_id" />
              </el-select>
            </div>
            <div class="toolbar-right">
              <el-popover placement="bottom-end" trigger="click" width="180">
                <div class="col-toggle-list">
                  <el-checkbox v-for="col in bugColDefs" :key="col.key" v-model="bugCols[col.key]" style="display:block;padding:4px 0">{{ col.label }}</el-checkbox>
                </div>
                <el-button slot="reference" size="small" icon="el-icon-menu" style="margin-right:8px">列显示</el-button>
              </el-popover>
              <el-button size="small" :type="bugMultiSelect ? 'warning' : 'default'" @click="bugMultiSelect = !bugMultiSelect; bugSelectedIds = []" style="margin-right:8px">多选</el-button>
              <el-button type="primary" size="small" icon="el-icon-plus" @click="showCreateBug = true">提交缺陷</el-button>
            </div>
          </div>

          <!-- 批量操作栏 -->
          <div v-if="bugMultiSelect && bugSelectedIds.length > 0" class="batch-bar">
            <span class="batch-info">已选 {{ bugSelectedIds.length }} 项</span>
            <el-select v-model="_moveBugTarget" placeholder="移入迭代" size="small" clearable style="width:160px" @change="batchMoveBugs">
              <el-option v-for="i in iterations" :key="i.id" :label="i.name" :value="i.id" />
            </el-select>
            <el-select v-model="_batchBugStatus" placeholder="更改状态" size="small" clearable style="width:120px;margin-left:8px" @change="batchChangeBugStatus">
              <el-option label="待处理" value="open" />
              <el-option label="已确认" value="confirmed" />
              <el-option label="修复中" value="in_progress" />
              <el-option label="已修复" value="fixed" />
              <el-option label="已验证" value="verified" />
              <el-option label="已关闭" value="closed" />
            </el-select>
            <el-button size="small" type="danger" plain style="margin-left:8px" @click="batchDeleteBugs">批量删除</el-button>
          </div>

          <el-table
            :data="filteredBugs"
            class="req-table-enhanced"
            style="width:100%"
            row-key="id"
            border
            @row-click="goToBugDetail"
            @selection-change="val => bugSelectedIds = val.map(b => b.id)"
            ref="bugTable"
          >
            <!-- 多选列 -->
            <el-table-column v-if="bugMultiSelect" type="selection" width="42" />

            <!-- ... 操作菜单 -->
            <el-table-column width="40" class-name="col-menu">
              <template slot-scope="{row}">
                <el-popover placement="right-start" trigger="click" width="160">
                  <div class="row-menu-list">
                    <div class="row-menu-item" @click="goToBugDetail(row)"><i class="el-icon-view"></i> 查看详情</div>
                    <div class="row-menu-item" @click="duplicateBug(row)"><i class="el-icon-document-copy"></i> 复制缺陷</div>
                    <div class="row-menu-item danger" @click="deleteBugRow(row)"><i class="el-icon-delete"></i> 删除</div>
                  </div>
                  <el-button slot="reference" type="text" size="mini" icon="el-icon-more" class="row-menu-btn" @click.stop />
                </el-popover>
              </template>
            </el-table-column>

            <!-- 标题 (click to edit) -->
            <el-table-column prop="title" label="标题" min-width="250">
              <template slot-scope="{row}">
                <div class="cell-title-wrap" v-if="inlineEditBugId !== row.id" @click.stop>
                  <span class="req-title-text" @click="startInlineEditBug(row)" title="点击编辑标题">{{ row.title }}</span>
                </div>
                <div v-else class="cell-title-edit" @click.stop>
                  <el-input v-model="inlineBugTitle" size="small" @blur="saveInlineEditBug(row)" @keyup.enter.native="saveInlineEditBug(row)" @keyup.escape.native="cancelInlineBugEdit" />
                </div>
              </template>
            </el-table-column>

            <!-- 严重程度 (click to dropdown) -->
            <el-table-column v-if="bugCols.severity" prop="severity" label="严重程度" width="85">
              <template slot-scope="{row}">
                <el-select
                  v-if="row._editSeverity"
                  v-model="row.severity"
                  size="mini"
                  style="width:70px"
                  @change="val => { row.severity = val; row._editSeverity = false; rdApi.updateBug(row.id, { severity: val }).catch(() => {}) }"
                  @visible-change="vis => { if (!vis) row._editSeverity = false }"
                  @click.stop
                >
                  <el-option v-for="s in ['blocker','critical','major','minor','trivial']" :key="s" :label="severityLabel(s)" :value="s" />
                </el-select>
                <div v-else class="priority-btn" :class="'pbtn-sev-' + row.severity" @click.stop="row._editSeverity = true">
                  {{ severityLabel(row.severity) }}
                </div>
              </template>
            </el-table-column>

            <!-- 优先级 (click to dropdown) -->
            <el-table-column v-if="bugCols.priority" prop="priority" label="优先级" width="80">
              <template slot-scope="{row}">
                <el-select
                  v-if="row._editPriority"
                  v-model="row.priority"
                  size="mini"
                  style="width:62px"
                  @change="val => { row.priority = val; row._editPriority = false; rdApi.updateBug(row.id, { priority: val }).catch(() => {}) }"
                  @visible-change="vis => { if (!vis) row._editPriority = false }"
                  @click.stop
                >
                  <el-option v-for="p in ['p0','p1','p2','p3']" :key="p" :label="priorityLabel(p)" :value="p" />
                </el-select>
                <div v-else class="priority-btn" :class="'pbtn-' + row.priority" @click.stop="row._editPriority = true">
                  {{ priorityLabel(row.priority) }}
                </div>
              </template>
            </el-table-column>

            <!-- 状态 (click for dropdown) -->
            <el-table-column v-if="bugCols.status" prop="status" label="状态" width="90">
              <template slot-scope="{row}">
                <el-select
                  v-if="row._editStatus"
                  v-model="row.status"
                  size="mini"
                  style="width:80px"
                  @change="val => { changeBugStatus(row, val); row._editStatus = false }"
                  @visible-change="vis => { if (!vis) row._editStatus = false }"
                  @click.stop
                >
                  <el-option v-for="s in ['open','confirmed','in_progress','fixed','verified','closed']" :key="s" :label="bugStatusLabel(s)" :value="s" />
                </el-select>
                <span v-else class="status-display" :class="'s-bug-' + row.status" @click.stop="row._editStatus = true">{{ bugStatusLabel(row.status) }}</span>
              </template>
            </el-table-column>

            <!-- 迭代 (click to change) -->
            <el-table-column v-if="bugCols.iteration" prop="iteration_name" label="迭代" width="120">
              <template slot-scope="{row}">
                <el-select
                  v-if="row._editIter"
                  v-model="row.iteration_id"
                  size="mini"
                  clearable
                  style="width:105px"
                  @change="val => { moveBugIteration(row, val); row._editIter = false }"
                  @visible-change="vis => { if (!vis) row._editIter = false }"
                  @click.stop
                >
                  <el-option v-for="i in iterations" :key="i.id" :label="i.name" :value="i.id" />
                </el-select>
                <el-tag v-else size="mini" :type="row.iteration_id ? 'success' : 'info'" effect="plain" class="clickable-cell" @click.stop="row._editIter = true">{{ row.iteration_name || '待规划' }}</el-tag>
              </template>
            </el-table-column>

            <!-- 负责人 (click to edit) -->
            <el-table-column v-if="bugCols.assignee" prop="assignee_name" label="负责人" width="140">
              <template slot-scope="{row}">
                <el-select
                  v-if="row._editAssignee"
                  v-model="row._assigneeIds"
                  size="mini"
                  multiple
                  style="width:125px"
                  @change="(val) => { saveBugAssignees(row, val); row._editAssignee = false }"
                  @visible-change="vis => { if (!vis) row._editAssignee = false }"
                  @click.stop
                >
                  <el-option v-for="m in projectMembers" :key="m.user_id" :label="m.user_name" :value="m.user_id" />
                </el-select>
                <div v-else class="assignee-cell" @click.stop="row._editAssignee = true">
                  <template v-if="row.assignee_name">
                    <span class="assignee-avatar-sm" :style="{ background: avatarColor(row.assignee_name) }">{{ row.assignee_name.charAt(0) }}</span>
                    <span class="assignee-text">{{ row.assignee_name }}</span>
                  </template>
                  <span v-else class="no-assignee">-</span>
                </div>
              </template>
            </el-table-column>

            <!-- 环境 -->
            <el-table-column v-if="bugCols.environment" prop="environment" label="环境" width="110">
              <template slot-scope="{row}">{{ row.environment || '-' }}</template>
            </el-table-column>

            <!-- 标签 -->
            <el-table-column v-if="bugCols.labels" prop="labels" label="标签" width="140">
              <template slot-scope="{row}">
                <div class="label-mini-list">
                  <el-tag v-for="(lb, idx) in (row.labels || []).slice(0, 2)" :key="idx" size="mini" effect="plain" style="margin:0 2px 2px 0">{{ lb }}</el-tag>
                  <span v-if="(row.labels || []).length > 2" class="more-label">+{{ row.labels.length - 2 }}</span>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </template>

        <!-- ==================== 成员 Tab ==================== -->
        <template v-if="activeTab === 'members'">
          <div class="tab-toolbar">
            <span class="tab-count">共 {{ projectMembers.length }} 名成员</span>
            <el-button type="primary" size="small" icon="el-icon-plus" @click="showAddMember = true">添加成员</el-button>
          </div>
          <div class="members-grid">
            <div v-for="m in projectMembers" :key="m.user_id" class="member-card">
              <div class="member-avatar" :style="{ background: avatarColor(m.user_name) }">
                {{ m.user_name.charAt(0) }}
              </div>
              <div class="member-info">
                <span class="member-name">{{ m.user_name }}</span>
                <el-tag size="mini" :type="memberRoleType(m.role)">{{ memberRoleLabel(m.role) }}</el-tag>
              </div>
              <div class="member-actions">
                <el-dropdown trigger="click" @command="cmd => changeMemberRole(m.user_id, cmd)">
                  <el-button size="mini" icon="el-icon-setting" circle />
                  <el-dropdown-menu slot="dropdown">
                    <el-dropdown-item command="owner">Owner — 所有者</el-dropdown-item>
                    <el-dropdown-item command="admin">Admin — 管理员</el-dropdown-item>
                    <el-dropdown-item command="developer">Developer — 开发者</el-dropdown-item>
                    <el-dropdown-item command="viewer">Viewer — 观察者</el-dropdown-item>
                  </el-dropdown-menu>
                </el-dropdown>
                <el-button size="mini" type="danger" icon="el-icon-delete" circle @click="removeMember(m)" :disabled="m.role === 'owner'" />
              </div>
            </div>
            <div v-if="projectMembers.length === 0" class="panel-empty" style="grid-column:1/-1;padding:48px">
              <p>暂无成员，点击"添加成员"开始协作</p>
            </div>
          </div>

          <!-- 添加成员弹窗 -->
          <el-dialog title="添加项目成员" :visible.sync="showAddMember" width="450px" :close-on-click-modal="false" custom-class="pretty-dialog">
            <el-form label-width="80px">
              <el-form-item label="选择成员">
                <el-select v-model="newMemberId" placeholder="选择要添加的成员" filterable style="width:100%" size="medium">
                  <el-option v-for="d in availableMembers" :key="d.id" :label="d.name + ' — ' + d.role" :value="d.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="项目角色">
                <el-select v-model="newMemberRole" style="width:100%" size="medium">
                  <el-option label="Developer — 开发者" value="developer" />
                  <el-option label="Admin — 管理员" value="admin" />
                  <el-option label="Viewer — 观察者" value="viewer" />
                </el-select>
              </el-form-item>
            </el-form>
            <span slot="footer">
              <el-button @click="showAddMember = false">取消</el-button>
              <el-button type="primary" @click="handleAddMember" :disabled="!newMemberId">添加</el-button>
            </span>
          </el-dialog>
        </template>

        <!-- ==================== 甘特图 Tab ==================== -->
        <template v-if="activeTab === 'gantt'">
          <div class="tab-toolbar">
            <span class="tab-count">甘特图预览</span>
            <el-button type="text" size="small" icon="el-icon-full-screen" @click="goToGantt">全屏查看</el-button>
          </div>
          <div class="gantt-preview">
            <div v-if="iterationsWithDates.length === 0 && reqsWithDates.length === 0" class="panel-empty" style="padding:48px">
              <i class="el-icon-date" style="font-size:48px;display:block;margin-bottom:12px"></i>
              <p>暂无带日期数据，请先在迭代或需求中设置起止日期</p>
            </div>
            <div v-else class="gantt-mini">
              <div class="gantt-mini-header">
                <div class="gantt-mini-label">任务</div>
                <div class="gantt-mini-timeline">
                  <span v-for="(m, idx) in ganttMonths" :key="idx" class="gantt-month-col">{{ m }}</span>
                </div>
              </div>
              <template v-for="iter in iterationsWithDates">
                <div :key="'gi-'+iter.id" class="gantt-mini-row iter-row">
                  <span class="gantt-row-label">
                    <span class="mini-iter-dot"></span> {{ iter.name }}
                  </span>
                  <div class="gantt-row-bar">
                    <div class="gantt-mini-bar iter-bar" :style="ganttBarStyle(iter.start_date, iter.end_date)"></div>
                  </div>
                </div>
                <div
                  v-for="req in getIterReqsWithDates(iter.id)"
                  :key="'gr-'+req.id"
                  class="gantt-mini-row req-row"
                  @click="goToRequirementDetail(req)"
                >
                  <span class="gantt-row-label req-label">
                    <span class="req-dot" :class="'pri-' + req.priority"></span>
                    {{ req.title }}
                  </span>
                  <div class="gantt-row-bar">
                    <div class="gantt-mini-bar req-bar" :class="'s-' + req.status" :style="ganttBarStyle(req.start_date, req.due_date)"></div>
                  </div>
                </div>
              </template>
              <template v-if="unassignedReqsWithDates.length > 0">
                <div class="gantt-mini-row section-row">
                  <span class="gantt-row-label" style="font-weight:700;color:#409eff;font-size:12px">
                    未分配迭代 ({{ unassignedReqsWithDates.length }})
                  </span>
                  <div class="gantt-row-bar"></div>
                </div>
                <div
                  v-for="req in unassignedReqsWithDates"
                  :key="'gu-'+req.id"
                  class="gantt-mini-row req-row"
                  @click="goToRequirementDetail(req)"
                >
                  <span class="gantt-row-label req-label">
                    <span class="req-dot" :class="'pri-' + req.priority"></span>
                    {{ req.title }}
                  </span>
                  <div class="gantt-row-bar">
                    <div class="gantt-mini-bar req-bar" :class="'s-' + req.status" :style="ganttBarStyle(req.start_date, req.due_date)"></div>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </template>

        <!-- ==================== 代码仓库 Tab ==================== -->
        <template v-if="activeTab === 'repos'">
          <!-- 未配置 GitHub OAuth App -->
          <div v-if="!oauthConfigured" class="oauth-setup-panel">
            <h3><i class="el-icon-setting"></i> 配置 GitHub OAuth App</h3>

            <!-- 教程步骤 -->
            <div class="oauth-tutorial">
              <div class="oauth-step">
                <div class="step-num">1</div>
                <div class="step-content">
                  <strong>打开 GitHub 创建 OAuth App</strong>
                  <p>登录 GitHub → 右上角头像 → <b>Settings</b> → 左侧 <b>Developer settings</b> → <b>OAuth Apps</b> → <b>New OAuth App</b></p>
                  <a class="oauth-link-btn" href="https://github.com/settings/developers" target="_blank">
                    <i class="el-icon-top-right"></i> 直接打开 GitHub Developer Settings
                  </a>
                </div>
              </div>

              <div class="oauth-step">
                <div class="step-num">2</div>
                <div class="step-content">
                  <strong>在 GitHub 上填写以下信息</strong>
                  <table class="oauth-field-table">
                    <tr>
                      <td class="field-label">Application name</td>
                      <td class="field-value"><code>WeAgent</code></td>
                      <td class="field-hint">任意名称即可，如 WeAgent、我的项目</td>
                    </tr>
                    <tr>
                      <td class="field-label">Homepage URL</td>
                      <td class="field-value"><code>{{ oauthForm.homepage_url }}</code></td>
                      <td class="field-hint">
                        <el-button type="text" size="mini" icon="el-icon-document-copy" @click="copyField(oauthForm.homepage_url)">复制</el-button>
                      </td>
                    </tr>
                    <tr>
                      <td class="field-label" style="color:#e6a23c">Authorization callback URL <strong>*</strong></td>
                      <td class="field-value"><code>{{ oauthForm.redirect_uri }}</code></td>
                      <td class="field-hint">
                        <el-button type="text" size="mini" icon="el-icon-document-copy" @click="copyRedirectUri">复制</el-button>
                        <span style="color:#e6a23c;font-size:11px">必须完全一致</span>
                      </td>
                    </tr>
                  </table>
                  <p class="oauth-note">点击 <b>Register application</b> 完成创建。</p>
                </div>
              </div>

              <div class="oauth-step">
                <div class="step-num">3</div>
                <div class="step-content">
                  <strong>复制凭证回到本页</strong>
                  <p>创建成功后，GitHub 会跳转到应用详情页。点击 <b>Generate a new client secret</b> 生成密钥，然后将下方两串字符粘贴过来：</p>
                </div>
              </div>
            </div>

            <!-- 凭证输入 -->
            <el-form class="oauth-cred-form" label-width="110px" size="small" @submit.native.prevent>
              <el-form-item label="Client ID">
                <el-input v-model="oauthForm.client_id" placeholder="从 GitHub 页面复制 Client ID" />
              </el-form-item>
              <el-form-item label="Client Secret">
                <el-input v-model="oauthForm.client_secret" type="password" show-password placeholder="从 GitHub 页面复制 Client Secret" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="saveOauthConfig" :loading="savingOauthConfig" icon="el-icon-check">
                  保存配置
                </el-button>
              </el-form-item>
            </el-form>
          </div>

          <!-- 已配置但未连接 -->
          <div v-else-if="!githubConnected" class="github-connect-panel">
            <div class="github-connect-icon">
              <i class="el-icon-link"></i>
            </div>
            <h3>连接 GitHub</h3>
            <p>授权 WeAgent 访问您的 GitHub 仓库，即可在平台查看提交记录、文件树和分支信息。</p>
            <el-button type="primary" size="medium" icon="el-icon-link" @click="connectGithub" :loading="connectingGithub">
              连接 GitHub
            </el-button>
            <p class="github-note">我们将通过 GitHub OAuth 获取 <code>repo</code> 权限，您的代码始终存储在 GitHub。</p>
          </div>

          <!-- 已连接 -->
          <template v-else>
            <div class="tab-toolbar">
              <span class="tab-count">
                共 {{ repos.length }} 个仓库
                <el-tag size="mini" effect="plain" type="success" style="margin-left:8px">
                  <i class="el-icon-check"></i> {{ githubUser }}
                </el-tag>
              </span>
              <div class="toolbar-actions">
                <el-button type="primary" size="small" icon="el-icon-plus" @click="openAssociateDialog" :loading="loadingGithubRepos">
                  关联仓库
                </el-button>
                <el-button type="text" size="small" @click="disconnectGithub" style="margin-left:8px;color:#f56c6c">
                  断开连接
                </el-button>
              </div>
            </div>

            <div class="repos-grid">
              <div v-for="repo in repos" :key="repo.id" class="repo-card" @click="$router.push('/repos/' + repo.id)">
                <el-button
                  class="repo-card-close"
                  type="text"
                  icon="el-icon-close"
                  size="mini"
                  @click.stop="disassociateRepo(repo)"
                  title="取消关联"
                />
                <div class="repo-card-header">
                  <h4><i class="el-icon-folder-opened"></i> {{ repo.full_name || repo.repo_name || repo.name }}</h4>
                  <el-tag size="mini" effect="plain">{{ repo.language || '—' }}</el-tag>
                </div>
                <p class="repo-desc" v-if="repo.description">{{ repo.description }}</p>
                <div class="repo-meta">
                  <span><i class="el-icon-share"></i> {{ repo.default_branch || 'main' }}</span>
                  <span v-if="repo.html_url">
                    <a :href="repo.html_url" target="_blank" @click.stop><i class="el-icon-link"></i> GitHub</a>
                  </span>
                </div>
              </div>
              <div v-if="repos.length === 0" class="panel-empty" style="grid-column:1/-1;padding:48px">
                <p>暂无关联仓库，请点击"关联仓库"从您的 GitHub 仓库中选择</p>
              </div>
            </div>
          </template>
        </template>
      </div>
    </main>

    <!-- ==================== 弹窗：关联 GitHub 仓库 ==================== -->
    <el-dialog title="关联 GitHub 仓库" :visible.sync="showAssociateDialog" width="600px" :close-on-click-modal="false" custom-class="pretty-dialog">
      <div v-loading="loadingGithubRepos">
        <el-input v-model="githubRepoSearch" placeholder="搜索仓库..." size="small" clearable style="margin-bottom:12px" />
        <div class="github-repo-list">
          <div v-for="repo in filteredGithubRepos" :key="repo.github_id" class="github-repo-item"
               :class="{ 'is-associated': associatedRepoIds.includes(repo.github_id) }">
            <div class="github-repo-info">
              <strong>{{ repo.full_name }}</strong>
              <span v-if="repo.description">{{ repo.description }}</span>
              <div class="github-repo-meta">
                <el-tag size="mini" effect="plain">{{ repo.language || '—' }}</el-tag>
                <span>{{ repo.private ? '私有' : '公开' }}</span>
              </div>
            </div>
            <el-button v-if="associatedRepoIds.includes(repo.github_id)" size="mini" disabled>已关联</el-button>
            <el-button v-else type="primary" size="mini" @click="associateRepo(repo)" :loading="associatingRepo === repo.github_id">关联</el-button>
          </div>
          <div v-if="filteredGithubRepos.length === 0 && !loadingGithubRepos" class="panel-empty" style="padding:24px">
            <p>{{ githubRepoSearch ? '没有匹配的仓库' : 'GitHub 账户暂无仓库' }}</p>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- ==================== 弹窗：需求详情 ==================== -->
    <el-dialog :title="selectedReq ? '需求详情' : ''" :visible.sync="reqDetailVisible" width="700px" :close-on-click-modal="false" custom-class="pretty-dialog">
      <template v-if="selectedReq">
        <div class="detail-dialog">
          <div class="dd-header">
            <h3>{{ selectedReq.title }}</h3>
            <div class="dd-tags">
              <el-tag :type="priorityTagType(selectedReq.priority)">{{ priorityLabel(selectedReq.priority) }}</el-tag>
              <el-tag>{{ statusLabel(selectedReq.status) }}</el-tag>
            </div>
          </div>
          <div class="dd-meta">
            <span>迭代：{{ selectedReq.iteration_name || '待规划' }}</span>
            <span>负责人：{{ selectedReq.assignee_name || '未分配' }}</span>
            <span>规模点：{{ selectedReq.story_points }}</span>
          </div>
          <div class="dd-desc" v-if="selectedReq.description">
            <h4>描述</h4>
            <p>{{ selectedReq.description }}</p>
          </div>
          <div class="dd-labels" v-if="selectedReq.labels && selectedReq.labels.length">
            <h4>标签</h4>
            <el-tag v-for="lb in selectedReq.labels" :key="lb" size="small" effect="plain" style="margin-right:6px">{{ lb }}</el-tag>
          </div>
          <!-- 关联分支和提交 -->
          <div class="dd-branches">
            <h4>关联分支</h4>
            <div v-if="getReqBranches(selectedReq.id).length">
              <div v-for="br in getReqBranches(selectedReq.id)" :key="br.id" class="branch-item">
                <i class="el-icon-share"></i>
                <span class="branch-name">{{ br.branch_name }}</span>
                <el-tag size="mini" :type="br.status === 'merged' ? 'success' : 'info'">{{ br.status === 'merged' ? '已合并' : '活跃' }}</el-tag>
              </div>
            </div>
            <span v-else class="text-muted">暂无关联分支</span>
          </div>
          <div class="dd-commits">
            <h4>最近提交</h4>
            <div v-if="getBranchCommits(selectedReq.id).length">
              <div v-for="cm in getBranchCommits(selectedReq.id)" :key="cm.id" class="commit-item">
                <i class="el-icon-check"></i>
                <span class="commit-hash">{{ cm.commit_hash.substring(0, 7) }}</span>
                <span class="commit-msg">{{ cm.message.split('\n')[0] }}</span>
                <span class="commit-author">{{ cm.author_name }}</span>
                <span class="commit-time">{{ formatRelative(cm.committed_at) }}</span>
              </div>
            </div>
            <span v-else class="text-muted">暂无提交记录</span>
          </div>
        </div>
      </template>
    </el-dialog>

    <!-- ==================== 弹窗：Bug 详情 ==================== -->
    <el-dialog :title="selectedBug ? '缺陷详情' : ''" :visible.sync="bugDetailVisible" width="700px" :close-on-click-modal="false" custom-class="pretty-dialog">
      <template v-if="selectedBug">
        <div class="detail-dialog">
          <div class="dd-header">
            <h3>{{ selectedBug.title }}</h3>
            <div class="dd-tags">
              <el-tag :type="severityTagType(selectedBug.severity)">{{ severityLabel(selectedBug.severity) }}</el-tag>
              <el-tag>{{ bugStatusLabel(selectedBug.status) }}</el-tag>
            </div>
          </div>
          <div class="dd-meta">
            <span>优先级：{{ priorityLabel(selectedBug.priority) }}</span>
            <span>负责人：{{ selectedBug.assignee_name || '未分配' }}</span>
            <span>环境：{{ selectedBug.environment || '-' }}</span>
          </div>
          <div class="dd-desc" v-if="selectedBug.description">
            <h4>复现步骤</h4>
            <p>{{ selectedBug.description }}</p>
          </div>
          <div class="dd-behavior" v-if="selectedBug.expected_behavior">
            <h4>期望行为</h4>
            <p class="text-green">{{ selectedBug.expected_behavior }}</p>
          </div>
          <div class="dd-behavior" v-if="selectedBug.actual_behavior">
            <h4>实际行为</h4>
            <p class="text-red">{{ selectedBug.actual_behavior }}</p>
          </div>
          <div class="dd-branches">
            <h4>关联修复分支</h4>
            <div v-if="getBugBranches(selectedBug.id).length">
              <div v-for="br in getBugBranches(selectedBug.id)" :key="br.id" class="branch-item">
                <i class="el-icon-share"></i>
                <span class="branch-name">{{ br.branch_name }}</span>
                <el-tag size="mini" :type="br.status === 'merged' ? 'success' : 'info'">{{ br.status === 'merged' ? '已合并' : '活跃' }}</el-tag>
              </div>
            </div>
            <span v-else class="text-muted">暂无关联修复分支</span>
          </div>
        </div>
      </template>
    </el-dialog>

    <!-- ==================== 弹窗：创建迭代 ==================== -->
    <el-dialog :visible.sync="showCreateIteration" width="540px" :close-on-click-modal="false" custom-class="iter-dialog">
      <template slot="title">
        <div class="dialog-title-row">
          <i class="el-icon-circle-plus-outline"></i>
          <span>新建迭代</span>
        </div>
      </template>
      <div class="iter-form-body">
        <div class="iter-form-main">
          <div class="form-field-lg">
            <label class="form-label">迭代名称 <span class="required">*</span></label>
            <el-input v-model="iterForm.name" placeholder="如 Sprint 1、v2.0 发布里程碑" maxlength="200" size="medium" />
          </div>
          <div class="form-field-lg">
            <label class="form-label">迭代目标</label>
            <el-input v-model="iterForm.goal" type="textarea" :rows="3" placeholder="描述本次迭代要达成的目标，支持 Markdown（可选）" />
          </div>
          <div class="form-field-lg">
            <label class="form-label">起止日期</label>
            <el-date-picker v-model="iterForm.dates" type="daterange" range-separator="—" start-placeholder="开始日期" end-placeholder="结束日期" value-format="yyyy-MM-dd" style="width:100%" />
          </div>
        </div>
      </div>
      <span slot="footer" class="dialog-footer-row">
        <el-button @click="showCreateIteration = false" size="medium">取消</el-button>
        <el-button type="primary" @click="handleCreateIteration" size="medium">创建迭代</el-button>
      </span>
    </el-dialog>

    <!-- ==================== 弹窗：编辑迭代 ==================== -->
    <el-dialog :visible.sync="showEditIter" width="540px" :close-on-click-modal="false" custom-class="iter-dialog">
      <template slot="title">
        <div class="dialog-title-row">
          <i class="el-icon-edit-outline"></i>
          <span>编辑迭代</span>
        </div>
      </template>
      <div class="iter-form-body">
        <div class="iter-form-main">
          <div class="form-field-lg">
            <label class="form-label">迭代名称 <span class="required">*</span></label>
            <el-input v-model="editIterForm.name" placeholder="迭代名称" maxlength="200" size="medium" />
          </div>
          <div class="form-field-lg">
            <label class="form-label">迭代目标</label>
            <el-input v-model="editIterForm.goal" type="textarea" :rows="3" placeholder="描述本次迭代要达成的目标，支持 Markdown" />
          </div>
          <div class="form-row-2col">
            <div class="form-field">
              <label class="form-label">状态</label>
              <div class="status-radio-group">
                <label class="status-radio" :class="{ active: editIterForm.status === 'planning' }" @click="editIterForm.status = 'planning'">
                  <span class="sr-dot dot-planning"></span> 计划中
                </label>
                <label class="status-radio" :class="{ active: editIterForm.status === 'active' }" @click="editIterForm.status = 'active'">
                  <span class="sr-dot dot-active"></span> 进行中
                </label>
                <label class="status-radio" :class="{ active: editIterForm.status === 'completed' }" @click="editIterForm.status = 'completed'">
                  <span class="sr-dot dot-completed"></span> 已完成
                </label>
              </div>
            </div>
            <div class="form-field">
              <label class="form-label">起止日期</label>
              <el-date-picker v-model="editIterForm.dates" type="daterange" range-separator="—" start-placeholder="开始" end-placeholder="结束" value-format="yyyy-MM-dd" style="width:100%" size="medium" />
            </div>
          </div>
        </div>
      </div>
      <span slot="footer" class="dialog-footer-row">
        <el-button @click="showEditIter = false" size="medium">取消</el-button>
        <el-button type="primary" @click="handleEditIter" size="medium">保存修改</el-button>
      </span>
    </el-dialog>

    <!-- ==================== 弹窗：创建需求 ==================== -->
    <el-dialog :visible.sync="showCreateRequirement" width="620px" :close-on-click-modal="false" class="create-req-dialog">
      <div slot="title" class="cr-dialog-title">
        <i class="el-icon-plus cr-title-icon"></i>
        <span>新建需求</span>
        <span v-if="reqForm.parent_id" class="cr-sub-badge">子需求</span>
      </div>
      <div class="create-req-body">
        <!-- 标题 -->
        <div class="cr-field-group">
          <label class="cr-label">需求标题 <span class="cr-required">*</span></label>
          <el-input v-model="reqForm.title" placeholder="清晰描述要实现的功能" maxlength="300" size="medium" />
        </div>
        <!-- 描述 -->
        <div class="cr-field-group">
          <label class="cr-label">描述</label>
          <el-input v-model="reqForm.description" type="textarea" :rows="3" placeholder="详细描述需求内容，支持 Markdown" size="medium" />
        </div>
        <!-- 行1：类型 / 优先级 -->
        <div class="cr-field-row">
          <div class="cr-field-half">
            <label class="cr-label">类型</label>
            <el-select v-model="reqForm.type" style="width:100%" size="medium">
              <el-option v-for="t in typeOptions" :key="t.value" :label="t.label" :value="t.value" />
            </el-select>
          </div>
          <div class="cr-field-half">
            <label class="cr-label">优先级</label>
            <div class="cr-priority-select">
              <el-radio-group v-model="reqForm.priority" size="small">
                <el-radio-button label="p0"><span class="pri-radio-text pri-radio-p0">P0</span></el-radio-button>
                <el-radio-button label="p1"><span class="pri-radio-text pri-radio-p1">P1</span></el-radio-button>
                <el-radio-button label="p2"><span class="pri-radio-text pri-radio-p2">P2</span></el-radio-button>
                <el-radio-button label="p3"><span class="pri-radio-text pri-radio-p3">P3</span></el-radio-button>
              </el-radio-group>
            </div>
          </div>
        </div>
        <!-- 行2：迭代 / 负责人 / 规模点 -->
        <div class="cr-field-row cr-field-triple">
          <div class="cr-field-third">
            <label class="cr-label">所属迭代</label>
            <el-select v-model="reqForm.iteration_id" placeholder="选择迭代" clearable style="width:100%" size="medium">
              <el-option v-for="i in iterations" :key="i.id" :label="i.name" :value="i.id" />
            </el-select>
          </div>
          <div class="cr-field-third">
            <label class="cr-label">负责人</label>
            <el-select v-model="reqForm.assignee_ids" multiple placeholder="选择负责人" clearable style="width:100%" size="medium">
              <el-option v-for="m in projectMembers" :key="m.user_id" :label="m.user_name" :value="m.user_id" />
            </el-select>
          </div>
          <div class="cr-field-third">
            <label class="cr-label">规模点</label>
            <el-input-number v-model="reqForm.story_points" :min="0" :max="100" size="medium" style="width:100%" />
          </div>
        </div>
        <!-- 父需求 (创建子需求时) -->
        <div class="cr-field-group" v-if="reqForm.parent_id">
          <label class="cr-label"><i class="el-icon-connection"></i> 父需求</label>
          <div class="cr-parent-display">
            <span class="cr-parent-title">{{ getParentReqTitle(reqForm.parent_id) }}</span>
            <el-button type="text" size="mini" icon="el-icon-close" @click="reqForm.parent_id = null" style="color:#f56c6c">移除</el-button>
          </div>
        </div>
        <!-- 行3：开始日期 / 截止日期 -->
        <div class="cr-field-row">
          <div class="cr-field-half">
            <label class="cr-label">开始日期</label>
            <el-date-picker v-model="reqForm.start_date" type="date" placeholder="计划开始" value-format="yyyy-MM-dd" style="width:100%" size="medium" />
          </div>
          <div class="cr-field-half">
            <label class="cr-label">截止日期</label>
            <el-date-picker v-model="reqForm.due_date" type="date" placeholder="计划完成" value-format="yyyy-MM-dd" style="width:100%" size="medium" />
          </div>
        </div>
      </div>
      <span slot="footer" class="dialog-footer">
        <el-button @click="showCreateRequirement = false" size="medium">取消</el-button>
        <el-button type="primary" @click="handleCreateRequirement" size="medium" :disabled="!reqForm.title.trim()">创建需求</el-button>
      </span>
    </el-dialog>

    <!-- ==================== 弹窗：创建 Bug ==================== -->
    <el-dialog title="提交缺陷" :visible.sync="showCreateBug" width="580px" :close-on-click-modal="false" custom-class="pretty-dialog">
      <el-form :model="bugForm" label-width="80px">
        <el-form-item label="缺陷标题" required>
          <el-input v-model="bugForm.title" placeholder="缺陷标题" maxlength="300" />
        </el-form-item>
        <el-form-item label="详细描述">
          <el-input v-model="bugForm.description" type="textarea" :rows="3" placeholder="描述缺陷详情 (支持 Markdown)" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="严重程度">
              <el-select v-model="bugForm.severity" style="width:100%">
                <el-option label="阻塞 (Blocker)" value="blocker" />
                <el-option label="致命 (Critical)" value="critical" />
                <el-option label="严重 (Major)" value="major" />
                <el-option label="一般 (Minor)" value="minor" />
                <el-option label="轻微 (Trivial)" value="trivial" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="优先级">
              <el-select v-model="bugForm.priority" style="width:100%">
                <el-option label="P0 紧急" value="p0" />
                <el-option label="P1 高" value="p1" />
                <el-option label="P2 中" value="p2" />
                <el-option label="P3 低" value="p3" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="所属迭代">
          <el-select v-model="bugForm.iteration_id" placeholder="选择迭代（可选）" clearable style="width:100%">
            <el-option v-for="i in iterations" :key="i.id" :label="i.name" :value="i.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="运行环境">
          <el-input v-model="bugForm.environment" placeholder="如 production / staging / Chrome 120" />
        </el-form-item>
        <el-form-item label="指派给">
          <el-select v-model="bugForm.assignee_id" placeholder="选择修复人（可选）" clearable style="width:100%">
            <el-option v-for="m in projectMembers" :key="m.user_id" :label="m.user_name" :value="m.user_id" />
          </el-select>
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="开发人员">
              <el-select v-model="bugForm.developer_id" placeholder="选择" clearable style="width:100%">
                <el-option v-for="m in projectMembers" :key="m.user_id" :label="m.user_name" :value="m.user_id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="设计人员">
              <el-select v-model="bugForm.designer_id" placeholder="选择" clearable style="width:100%">
                <el-option v-for="m in projectMembers" :key="m.user_id" :label="m.user_name" :value="m.user_id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="测试人员">
              <el-select v-model="bugForm.tester_id" placeholder="选择" clearable style="width:100%">
                <el-option v-for="m in projectMembers" :key="m.user_id" :label="m.user_name" :value="m.user_id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <span slot="footer">
        <el-button @click="showCreateBug = false">取消</el-button>
        <el-button type="primary" @click="handleCreateBug" :loading="creatingBug">提交</el-button>
      </span>
    </el-dialog>

    <!-- 编辑项目弹窗 -->
    <el-dialog title="编辑项目" :visible.sync="showEditDialog" width="560px" :close-on-click-modal="false" custom-class="pretty-dialog">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="项目名称" required>
          <el-input v-model="editForm.name" placeholder="项目名称" maxlength="200" />
        </el-form-item>
        <el-form-item label="项目描述">
          <el-input v-model="editForm.description" type="textarea" :rows="3" placeholder="项目描述" />
        </el-form-item>
        <el-divider content-position="left">技术栈</el-divider>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="前端">
              <el-select v-model="editForm.tech_frontend" filterable allow-create placeholder="选择或输入" style="width:100%">
                <el-option v-for="t in techOptions.frontend" :key="t" :label="t" :value="t" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="后端">
              <el-select v-model="editForm.tech_backend" filterable allow-create placeholder="选择或输入" style="width:100%">
                <el-option v-for="t in techOptions.backend" :key="t" :label="t" :value="t" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="数据库">
              <el-select v-model="editForm.tech_database" filterable allow-create placeholder="选择或输入" style="width:100%">
                <el-option v-for="t in techOptions.database" :key="t" :label="t" :value="t" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="部署">
              <el-select v-model="editForm.tech_deployment" filterable allow-create placeholder="选择或输入" style="width:100%">
                <el-option v-for="t in techOptions.deployment" :key="t" :label="t" :value="t" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <span slot="footer">
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSaveProject" :loading="savingProject">保存</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import { mapState, mapActions } from 'vuex'
import AppSidebar from '@/components/Sidebar/index.vue'
import {
  developers,
  demoProjects, demoIterations, demoRequirements, demoBugs,
  demoBranches, demoCommits, demoRepos, demoBuilds,
} from './demoData'
import * as rdApi from '@/api/rd'
import { getUsers } from '@/api/auth'
import { getConversations } from '@/api/conversation'

export default {
  name: 'RdProjectDetail',
  components: { AppSidebar },
  data() {
    return {
      activeTab: 'overview',
      showEditDialog: false,
      savingProject: false,
      showCreateIteration: false,
      showEditIter: false,
      editingIterId: null,
      editIterForm: { name: '', goal: '', status: 'planning', dates: [] },
      showCreateRequirement: false,
      showCreateBug: false,
      techOptions: {
        frontend: ['Vue 3', 'React 18', 'Angular', 'Svelte', 'Next.js', 'Nuxt 3', 'TypeScript'],
        backend: ['Flask', 'Django', 'FastAPI', 'Spring Boot', 'Express', 'Go Gin', 'NestJS'],
        database: ['MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'SQLite', 'Elasticsearch'],
        deployment: ['Docker', 'Kubernetes', 'Nginx', 'Vercel', 'AWS', '阿里云', 'GitHub Actions'],
      },
      reqDetailVisible: false,
      bugDetailVisible: false,
      selectedReq: null,
      selectedBug: null,
      editForm: { name: '', description: '', tech_stack: {} },

      // 筛选
      reqFilter: { iteration: '', priority: '', status: '', assignee: '' },
      bugFilter: { iteration: '', severity: '', status: '', assignee: '' },

      // 需求表格列显示控制
      reqCols: { priority: true, status: true, iteration: true, assignee: true, story_points: true, type: true, labels: true, dates: true },
      inlineEditId: null,
      inlineTitle: '',

      // 多选
      reqMultiSelect: false,
      reqSelectedIds: [],

      // Bug 表格列显示 + 多选
      bugCols: { severity: true, priority: true, status: true, iteration: true, assignee: true, environment: true, labels: true },
      bugColDefs: [
        { key: 'severity', label: '严重程度' },
        { key: 'priority', label: '优先级' },
        { key: 'status', label: '状态' },
        { key: 'iteration', label: '迭代' },
        { key: 'assignee', label: '负责人' },
        { key: 'environment', label: '环境' },
        { key: 'labels', label: '标签' },
      ],
      bugMultiSelect: false,
      bugSelectedIds: [],
      inlineEditBugId: null,
      inlineBugTitle: '',
      _moveBugTarget: null,
      _batchBugStatus: '',
      creatingBug: false,

      // 成员管理
      projectMembers: [],
      allUsers: [],
      showAddMember: false,
      newMemberId: '',
      newMemberRole: 'developer',
      _moveReqTarget: null,
      _moveIterVisible: false,

      // 表单
      iterForm: { name: '', goal: '', dates: [] },
      typeOptions: [
        { value: 'feature', label: '新功能' },
        { value: 'enhancement', label: '优化增强' },
        { value: 'bugfix', label: '问题修复' },
        { value: 'tech_debt', label: '技术债务' },
        { value: 'research', label: '技术研究' },
      ],
      reqForm: { title: '', description: '', priority: 'p2', type: 'feature', iteration_id: '', assignee_ids: [], story_points: 0, parent_id: null, start_date: null, due_date: null },
      bugForm: { title: '', description: '', severity: 'major', priority: 'p2', assignee_id: '', iteration_id: '', environment: '', developer_id: '', designer_id: '', tester_id: '' },

      // GitHub 授权
      oauthConfigured: false,
      oauthForm: { client_id: '', client_secret: '', redirect_uri: '', homepage_url: window.location.origin },
      savingOauthConfig: false,
      githubConnected: false,
      githubUser: '',
      connectingGithub: false,
      showAssociateDialog: false,
      loadingGithubRepos: false,
      githubRepos: [],
      githubRepoSearch: '',
      associatingRepo: null,

      // 演示数据
      developers,
      iterations: [],
      requirements: [],
      bugs: [],
      branches: [],
      commits: [],
      repos: [],
      builds: [],
    }
  },
  computed: {
    ...mapState('rd', ['currentProject', 'currentFiles', 'loading']),
    project() { return this.currentProject },
    tech() {
      const t = this.project?.tech_stack || {}
      return {
        frontend: t.frontend || '未指定',
        backend: t.backend || '未指定',
        database: t.database || '未指定',
        deployment: t.deployment || '未指定',
      }
    },
    activeIteration() {
      return this.iterations.find(i => i.status === 'active')
    },
    iterReqs() {
      return this.requirements.filter(r => r.iteration_id === this.activeIteration?.id)
    },
    iterBugs() {
      return this.bugs.filter(b => b.iteration_id === this.activeIteration?.id)
    },
    iterationProgress() {
      if (!this.activeIteration) return 0
      const all = [...this.iterReqs, ...this.iterBugs]
      if (all.length === 0) return 0
      const done = all.filter(i => ['done', 'closed', 'fixed', 'verified'].includes(i.status)).length
      return Math.round((done / all.length) * 100)
    },
    recentBuilds() {
      return this.builds.slice(0, 5)
    },
    filteredRequirements() {
      let list = this.requirements
      if (this.reqFilter.iteration) list = list.filter(r => r.iteration_id === this.reqFilter.iteration)
      if (this.reqFilter.priority) list = list.filter(r => r.priority === this.reqFilter.priority)
      if (this.reqFilter.status) list = list.filter(r => r.status === this.reqFilter.status)
      if (this.reqFilter.assignee) list = list.filter(r => (r._assigneeIds || []).includes(this.reqFilter.assignee))
      return list
    },
    filteredBugs() {
      let list = this.bugs
      if (this.bugFilter.iteration) list = list.filter(b => b.iteration_id === this.bugFilter.iteration)
      if (this.bugFilter.severity) list = list.filter(b => b.severity === this.bugFilter.severity)
      if (this.bugFilter.status) list = list.filter(b => b.status === this.bugFilter.status)
      if (this.bugFilter.assignee) list = list.filter(b => (b._assignees || []).some(a => a.user_id === this.bugFilter.assignee))
      return list
    },
    availableMembers() {
      const memberIds = this.projectMembers.map(m => m.user_id)
      const allAvailable = this.allUsers.length > 0
        ? this.allUsers.filter(u => !memberIds.includes(u.id)).map(u => ({ id: u.id, name: u.username, role: u.role || 'user' }))
        : developers.filter(d => !memberIds.includes(d.id))
      return allAvailable
    },
    // 需求层级展示（flat list with indent level）
    hierarchicalRequirements() {
      const list = this.filteredRequirements
      const map = {}
      const roots = []
      // Build lookup
      list.forEach(r => { map[r.id] = { ...r, _depth: 0, _children: [] } })
      // Build tree
      list.forEach(r => {
        if (r.parent_id && map[r.parent_id]) {
          map[r.parent_id]._children.push(map[r.id])
        } else if (!r.parent_id || !map[r.parent_id]) {
          roots.push(map[r.id])
        }
      })
      // Flatten with depth
      const flat = []
      const walk = (items, depth) => {
        items.forEach(item => {
          item._depth = depth
          flat.push(item)
          if (item._children && item._children.length) {
            walk(item._children, depth + 1)
          }
        })
      }
      walk(roots, 0)
      return flat
    },

    // ── 甘特图预览 (使用真实 API 数据) ──
    iterationsWithDates() {
      return (this.iterations || []).filter(i => i.start_date && i.end_date)
    },
    reqsWithDates() {
      return (this.requirements || []).filter(r => r.start_date && r.due_date)
    },
    unassignedReqsWithDates() {
      return (this.requirements || []).filter(r => !r.iteration_id && r.start_date && r.due_date)
    },
    ganttMonths() {
      const all = [
        ...this.iterationsWithDates.map(i => [i.start_date, i.end_date]),
        ...this.reqsWithDates.map(r => [r.start_date, r.due_date]),
      ].flat().filter(Boolean).sort()
      if (all.length === 0) return []
      const months = []
      let cur = new Date(all[0])
      const end = new Date(all[all.length - 1])
      while (cur <= end) {
        months.push((cur.getMonth()+1) + '月')
        cur.setMonth(cur.getMonth() + 1)
      }
      return months
    },
    filteredGithubRepos() {
      if (!this.githubRepoSearch) return this.githubRepos
      const kw = this.githubRepoSearch.toLowerCase()
      return this.githubRepos.filter(r => r.full_name.toLowerCase().includes(kw))
    },
    associatedRepoIds() {
      return this.repos.map(r => r.github_id)
    },
  },
  created() {
    const projectId = this.$route.params.id
    // 恢复上次的Tab
    const savedTab = sessionStorage.getItem('rd_project_tab_' + projectId)
    if (savedTab) this.activeTab = savedTab
    this.loadData(projectId)
  },
  watch: {
    activeTab(val) {
      const projectId = this.$route.params.id
      sessionStorage.setItem('rd_project_tab_' + projectId, val)
    },
  },
  methods: {
    ...mapActions('rd', ['fetchProject']),
    async loadData(projectId) {
      // 尝试从 API 加载项目信息
      try {
        await this.fetchProject(projectId)
      } catch (e) { /* 使用演示数据 */ }

      if (!this.currentProject) {
        const demo = demoProjects.find(p => p.id === projectId)
        if (demo) this.$store.commit('rd/SET_CURRENT_PROJECT', demo)
      }

      // 加载用户列表 (用于添加成员)
      try {
        const usersRes = await getUsers()
        if (usersRes.code === 200) this.allUsers = usersRes.data.items || []
      } catch (e) { /* fallback to developers */ }

      // 尝试从 API 加载关联数据
      const results = await Promise.allSettled([
        rdApi.getIterations(projectId),
        rdApi.getRequirements(projectId),
        rdApi.getBugs(projectId),
        rdApi.getMembers(projectId),
        rdApi.getProjectBranches(projectId),
        rdApi.getRepos(projectId),
        rdApi.getBuilds(projectId),
      ])

      const [iterRes, reqRes, bugRes, memRes, brRes, repoRes, buildRes] = results

      if (iterRes.status === 'fulfilled' && iterRes.value.code === 200) {
        this.iterations = (iterRes.value.data.items || []).sort((a, b) => {
          // active 排最前
          if (a.status === 'active' && b.status !== 'active') return -1
          if (b.status === 'active' && a.status !== 'active') return 1
          // 其次按 sort_order 升序
          return (a.sort_order || 0) - (b.sort_order || 0)
        })
      } else {
        this.iterations = demoIterations.filter(i => i.project_id === projectId).sort((a, b) => {
          if (a.status === 'active' && b.status !== 'active') return -1
          if (b.status === 'active' && a.status !== 'active') return 1
          return (a.sort_order || 0) - (b.sort_order || 0)
        })
      }

      if (reqRes.status === 'fulfilled' && reqRes.value.code === 200) {
        this.requirements = (reqRes.value.data.items || []).map(r => {
          const assigneeList = r.assignees || []
          const assigneeIds = assigneeList.map(a => a.user_id)
          const assigneeNames = assigneeIds.map(id => this.getDevName(id)).join(', ')
          return {
            ...r,
            _editStatus: false, _editIter: false, _editAssignee: false, _editSP: false, _editPriority: false,
            _assignees: assigneeList,
            _assigneeIds: assigneeIds,
            assignee_name: assigneeNames || null,
          }
        })
      } else {
        this.requirements = demoRequirements.filter(r => r.project_id === projectId).map(r => ({
          ...r, _editStatus: false, _editIter: false, _editAssignee: false, _editSP: false, _editPriority: false,
          _assignees: r.assignees || [],
          _assigneeIds: r.assignee_id ? [r.assignee_id] : [],
        }))
      }

      if (bugRes.status === 'fulfilled' && bugRes.value.code === 200) {
        this.bugs = (bugRes.value.data.items || []).map(b => {
          const assigneeList = b.assignees || []
          const assigneeIds = assigneeList.map(a => a.user_id)
          const assigneeNames = assigneeIds.map(id => this.getDevName(id)).join(', ')
          return {
            ...b,
            _editStatus: false, _editIter: false, _editAssignee: false, _editSeverity: false, _editPriority: false,
            _assignees: assigneeList,
            _assigneeIds: assigneeIds,
            assignee_name: assigneeNames || null,
          }
        })
      } else {
        this.bugs = demoBugs.filter(b => b.project_id === projectId).map(b => ({
          ...b, _editStatus: false, _editIter: false, _editAssignee: false, _editSeverity: false, _editPriority: false,
          _assignees: b.assignees || [],
          _assigneeIds: b.assignee_id ? [b.assignee_id] : [],
        }))
      }

      if (memRes.status === 'fulfilled' && memRes.value.code === 200) {
        this.projectMembers = memRes.value.data.items || []
        // 如果 API 没有返回用户, 尝试从 allUsers 中补充
        if (this.projectMembers.length > 0 && !this.projectMembers[0].user_name) {
          this.projectMembers = this.projectMembers.map(m => {
            const u = this.allUsers.find(u => u.id === m.user_id)
            return { ...m, user_name: u ? u.username : m.user_id }
          })
        }
      } else {
        const demoProject = demoProjects.find(p => p.id === projectId)
        if (demoProject && demoProject.members) {
          this.projectMembers = JSON.parse(JSON.stringify(demoProject.members))
        }
      }

      if (brRes.status === 'fulfilled' && brRes.value.code === 200) {
        this.branches = brRes.value.data.items || []
      } else {
        this.branches = demoBranches.filter(b => b.project_id === projectId)
      }

      if (repoRes.status === 'fulfilled' && repoRes.value.code === 200) {
        this.repos = repoRes.value.data.items || []
      } else {
        this.repos = demoRepos.filter(r => r.project_id === projectId)
      }

      if (buildRes.status === 'fulfilled' && buildRes.value.code === 200) {
        this.builds = buildRes.value.data.items || []
      } else {
        this.builds = demoBuilds.filter(b => b.project_id === projectId)
      }

      this.commits = [...demoCommits]

      // 检查 GitHub 授权状态
      this.checkGithubStatus()
    },

    // ── 帮助方法 ──
    getIterRequirements(iterId) { return this.requirements.filter(r => r.iteration_id === iterId) },
    getIterBugs(iterId) { return this.bugs.filter(b => b.iteration_id === iterId) },
    iterProgressPct(iterId) {
      const reqs = this.getIterRequirements(iterId)
      const bugs = this.getIterBugs(iterId)
      const all = [...reqs, ...bugs]
      if (all.length === 0) return 0
      const done = all.filter(i => ['done', 'closed', 'fixed', 'verified'].includes(i.status)).length
      return Math.round((done / all.length) * 100)
    },
    openIterEdit(iter) {
      this.editingIterId = iter.id
      this.editIterForm = {
        name: iter.name,
        goal: iter.goal || '',
        status: iter.status,
        dates: iter.start_date && iter.end_date ? [iter.start_date, iter.end_date] : [],
      }
      this.showEditIter = true
    },
    handleEditIter() {
      if (!this.editIterForm.name) return this.$message.warning('请输入迭代名称')
      const [start, end] = this.editIterForm.dates || []
      const data = {
        name: this.editIterForm.name,
        goal: this.editIterForm.goal,
        status: this.editIterForm.status,
        start_date: start || undefined,
        end_date: end || undefined,
      }
      rdApi.updateIteration(this.editingIterId, data).then(res => {
        if (res.code === 200) {
          const updated = res.data
          const idx = this.iterations.findIndex(i => i.id === updated.id)
          if (idx >= 0) this.$set(this.iterations, idx, { ...this.iterations[idx], ...updated })
          // 更新关联需求的 iteration_name
          this.requirements.forEach(r => {
            if (r.iteration_id === updated.id) r.iteration_name = updated.name
          })
          this.bugs.forEach(b => {
            if (b.iteration_id === updated.id) b.iteration_name = updated.name
          })
          this.$message.success('迭代已更新')
        }
      }).catch(() => {
        // 回退到演示模式
        const idx = this.iterations.findIndex(i => i.id === this.editingIterId)
        if (idx >= 0) {
          const iter = this.iterations[idx]
          this.$set(this.iterations, idx, { ...iter, ...data,
            start_date: start || iter.start_date, end_date: end || iter.end_date })
        }
        this.$message.success('迭代已更新（本地）')
      })
      this.showEditIter = false
    },
    handleDeleteIter(iter) {
      this.$confirm(`确定删除迭代 "${iter.name}"？关联的需求将移出迭代。`, '确认删除', { type: 'warning' }).then(() => {
        rdApi.deleteIteration(iter.id).then(res => {
          if (res.code === 200) {
            this.iterations = this.iterations.filter(i => i.id !== iter.id)
            this.requirements.forEach(r => { if (r.iteration_id === iter.id) { r.iteration_id = null; r.iteration_name = null } })
            this.bugs.forEach(b => { if (b.iteration_id === iter.id) { b.iteration_id = null; b.iteration_name = null } })
            this.$message.success('迭代已删除')
          }
        }).catch(() => {
          this.iterations = this.iterations.filter(i => i.id !== iter.id)
          this.$message.success('迭代已删除（本地）')
        })
      }).catch(() => {})
    },
    getReqBranches(reqId) { return this.branches.filter(b => b.source_type === 'requirement' && b.source_id === reqId) },
    getBugBranches(bugId) { return this.branches.filter(b => b.source_type === 'bug' && b.source_id === bugId) },
    getBranchCommits(sourceId) {
      const brs = this.branches.filter(b => (b.source_type === 'requirement' || b.source_type === 'bug') && b.source_id === sourceId)
      return this.commits.filter(c => brs.some(b => b.id === c.branch_id))
    },

    priorityLabel(p) { return ({ p0: 'P0', p1: 'P1', p2: 'P2', p3: 'P3' })[p] || p },
    priorityTagType(p) { return ({ p0: 'danger', p1: 'warning', p2: 'info', p3: '' })[p] || '' },
    typeLabel(t) { return ({ feature: '新功能', enhancement: '增强', bugfix: '修复', tech_debt: '技术债务', research: '研究' })[t] || t || '-' },
    statusLabel(s) { return ({ backlog: '待规划', todo: '待办', in_progress: '进行中', in_review: '审查中', done: '已完成', closed: '已关闭' })[s] || s },
    severityLabel(s) { return ({ blocker: '致命', critical: '严重', major: '主要', minor: '次要', trivial: '轻微' })[s] || s },
    severityTagType(s) { return ({ blocker: 'danger', critical: 'danger', major: 'warning', minor: 'info', trivial: '' })[s] || '' },
    bugStatusLabel(s) { return ({ open: '未处理', confirmed: '已确认', in_progress: '修复中', fixed: '已修复', verified: '已验证', closed: '已关闭', wont_fix: '不修复' })[s] || s },

    formatRelative(iso) {
      if (!iso) return ''
      const diff = Date.now() - new Date(iso).getTime()
      const mins = Math.floor(diff / 60000)
      if (mins < 60) return mins + ' 分钟前'
      const hours = Math.floor(mins / 60)
      if (hours < 24) return hours + ' 小时前'
      const days = Math.floor(hours / 24)
      if (days < 30) return days + ' 天前'
      return Math.floor(days / 30) + ' 月前'
    },
    statusLabel(s) {
      return { success: '通过', failed: '失败', running: '运行中', pending: '等待中', cancelled: '已取消' }[s] || s
    },
    goToBuild(buildId) {
      this.$router.push({ path: '/builds', query: { project_id: this.projectId, build_id: buildId } })
    },
    renderMarkdown(text) {
      if (!text) return '<span class="text-muted">暂无内容</span>'

      const renderTable = (rows) => {
        if (rows.length === 0) return ''
        const parseRow = (r) => {
          return r.replace(/^\||\|$/g, '').split('|').map(c => c.trim())
        }
        let html = '<table class="md-table"><thead><tr>'
        const headerCells = parseRow(rows[0])
        headerCells.forEach(c => { html += '<th>' + c + '</th>' })
        html += '</tr></thead><tbody>'
        for (let i = 1; i < rows.length; i++) {
          html += '<tr>'
          const cells = parseRow(rows[i])
          cells.forEach(c => { html += '<td>' + c + '</td>' })
          html += '</tr>'
        }
        html += '</tbody></table>'
        return html
      }

      let html = String(text)
        // 先转义 HTML 防止 XSS
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

      // 代码块 (```...```)
      html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="code-block"><code>$2</code></pre>')
      // 行内代码
      html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')

      // 表格 — 逐行处理
      const lines = html.split('\n')
      const result = []
      let inTable = false
      let tableRows = []
      let headerRowIdx = -1

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim()
        // 检测表格行：以 | 开头或结尾，或包含 | 分隔符
        const isTableLine = /^\|.*\|$/.test(line) || /^\|.*\|\s*$/.test(line)
        const isSepLine = /^\|[\s\-:|]+\|$/.test(line)

        if (isTableLine && !isSepLine) {
          if (!inTable) {
            inTable = true
            tableRows = []
            headerRowIdx = 0
          }
          tableRows.push(line)
        } else if (isSepLine && inTable && tableRows.length === 1) {
          // 分隔行，标记表头已确定
          headerRowIdx = 0
        } else {
          // 不在表格中，或表格结束
          if (inTable && tableRows.length > 0) {
            result.push(renderTable(tableRows))
            tableRows = []
            inTable = false
          }
          if (line) {
            result.push(line)
          } else {
            result.push('')
          }
        }
      }
      // 处理末尾表格
      if (inTable && tableRows.length > 0) {
        result.push(renderTable(tableRows))
      }

      html = result.join('\n')

      // 标题 (# ## ### ...)
      html = html.replace(/^### (.+)$/gm, '<h4 class="md-h4">$1</h4>')
      html = html.replace(/^## (.+)$/gm, '<h3 class="md-h3">$1</h3>')
      html = html.replace(/^# (.+)$/gm, '<h2 class="md-h2">$1</h2>')

      // 粗体 / 斜体
      html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>')

      // 无序列表
      html = html.replace(/^- (.+)$/gm, '<li style="margin-left:16px">$1</li>')
      // 有序列表
      html = html.replace(/^\d+\. (.+)$/gm, '<li style="margin-left:16px">$1</li>')

      // 段落
      html = html.replace(/\n\n/g, '</p><p>')
      html = html.replace(/\n/g, '<br>')

      return html
    },

    // ── 需求表格行内编辑 ──
    startInlineEditReq(row) {
      this.inlineEditId = row.id
      this.inlineTitle = row.title
      this.$nextTick(() => {
        const input = this.$refs['inline-input-' + row.id]
        if (input) {
          const el = Array.isArray(input) ? input[0] : input
          if (el && el.focus) el.focus()
        }
      })
    },
    saveInlineEditReq(row) {
      const newTitle = this.inlineTitle ? this.inlineTitle.trim() : ''
      this.inlineEditId = null
      this.inlineTitle = ''
      if (newTitle && newTitle !== row.title) {
        row.title = newTitle
        rdApi.updateRequirement(row.id, { title: newTitle }).then(() => {
          this.$message.success('标题已更新')
        }).catch(() => {})
      }
    },
    cancelInlineEdit() {
      this.inlineEditId = null
      this.inlineTitle = ''
    },
    cyclePriority(row) {
      const order = ['p0', 'p1', 'p2', 'p3']
      const idx = order.indexOf(row.priority)
      const newPri = order[(idx + 1) % order.length]
      row.priority = newPri
      rdApi.updateRequirement(row.id, { priority: newPri }).then(() => {
        this.$message.success('优先级已更新')
      }).catch(() => {})
    },
    changeReqStatus(row, val) {
      row.status = val
      rdApi.updateRequirementStatus(row.id, val).then(() => {
        this.$message.success('状态已更新')
      }).catch(() => {})
    },
    moveReqIteration(row, val) {
      const iter = this.iterations.find(i => i.id === val)
      row.iteration_id = val || null
      row.iteration_name = iter ? iter.name : null
      rdApi.moveRequirementToIteration(row.id, val || null).then(() => {
        this.$message.success('迭代已更新')
      }).catch(() => {})
    },
    updateReqField(row, field, val) {
      row[field] = val
    },
    getDevName(id) {
      const m = this.projectMembers.find(m => m.user_id === id)
      if (m) return m.user_name
      const u = this.allUsers.find(u => u.id === id)
      if (u) return u.username
      const d = developers.find(d => d.id === id)
      return d ? d.name : id
    },
    saveStoryPoints(row) {
      const val = parseInt(row.story_points) || 0
      row.story_points = val
      row._editSP = false
      rdApi.updateRequirement(row.id, { story_points: val }).then(() => {
        this.$message.success('规模点已更新')
      }).catch(() => {})
    },
    saveAssigneeChange(row) {
      const newIds = row._assigneeIds || []
      const oldAssignees = row._assignees || []
      const oldIds = oldAssignees.map(a => a.user_id)
      row._editAssignee = false

      const added = newIds.filter(id => !oldIds.includes(id))
      const removed = oldIds.filter(id => !newIds.includes(id))

      const pid = this.project.id
      const promises = []

      added.forEach(uid => {
        promises.push(rdApi.addRequirementAssignee(pid, row.id, uid, 'primary'))
      })
      removed.forEach(uid => {
        promises.push(rdApi.removeRequirementAssignee(pid, row.id, uid))
      })

      Promise.all(promises).then(() => {
        // Update local cache
        const kept = oldAssignees.filter(a => !removed.includes(a.user_id))
        const addedObjs = added.map(uid => {
          const m = this.projectMembers.find(m2 => m2.user_id === uid)
          return { user_id: uid, user_name: m ? m.user_name : uid, role: 'primary' }
        })
        row._assignees = [...kept, ...addedObjs]
        row.assignee_name = newIds.map(id => this.getDevName(id)).join(', ')
        this.$message.success('负责人已更新')
      }).catch(() => {
        // Rollback local state
        row._assigneeIds = [...oldIds]
        this.$message.error('负责人更新失败')
      })
    },
    avatarColor(name) {
      const colors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#b37feb']
      let hash = 0
      for (let i = 0; i < (name || '').length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
      return colors[Math.abs(hash) % colors.length]
    },

    // ── 行内编辑辅助 ──
    autoFocusSelect(refName) {
      const el = this.$refs[refName]
      if (el) {
        const sel = Array.isArray(el) ? el[0] : el
        if (sel && sel.toggleMenu) sel.toggleMenu()
        if (sel && sel.focus) sel.focus()
      }
    },
    getParentReqTitle(parentId) {
      const parent = this.requirements.find(r => r.id === parentId)
      return parent ? parent.title : '(未知需求)'
    },

    // ── 行菜单操作 ──
    createSubRequirement(row) {
      this.reqForm = {
        title: '',
        description: '',
        priority: 'p2',
        type: 'feature',
        iteration_id: row.iteration_id || '',
        assignee_ids: [],
        story_points: 0,
        parent_id: row.id,
        start_date: null,
        due_date: null,
      }
      this.showCreateRequirement = true
    },
    openMoveIterDialog(row) {
      // Trigger inline iteration editor via the row menu action
      row._editIter = true
    },
    moveReqToIter(row, iterId) {
      this.moveReqIteration(row, iterId)
      row._editIter = false
      this.$message.success('已移动需求到迭代')
    },
    duplicateReq(row) {
      rdApi.createRequirement(this.project.id, {
        title: row.title + ' (副本)',
        description: row.description,
        priority: row.priority,
        type: row.type,
        iteration_id: row.iteration_id,
        story_points: row.story_points,
        parent_id: row.parent_id,
        start_date: row.start_date,
        due_date: row.due_date,
      }).then(res => {
        if (res.code === 201) {
          const newReq = { ...res.data, _editStatus: false, _editIter: false, _editAssignee: false, _editSP: false, _editPriority: false, _assigneeIds: res.data.assignee_id ? [res.data.assignee_id] : [] }
          this.requirements.unshift(newReq)
          this.$message.success('需求已复制')
        }
      }).catch(() => {
        const copy = JSON.parse(JSON.stringify(row))
        copy.id = 'req-dup-' + Date.now()
        copy.title = copy.title + ' (副本)'
        copy.created_at = new Date().toISOString()
        copy._editStatus = false; copy._editIter = false; copy._editAssignee = false; copy._editSP = false
        copy._assigneeIds = copy.assignee_id ? [copy.assignee_id] : []
        this.requirements.unshift(copy)
        this.$message.success('需求已复制（本地）')
      })
    },
    deleteReqRow(row) {
      this.$confirm('确定删除此需求？', '确认', { type: 'warning' }).then(() => {
        rdApi.deleteRequirement(row.id).then(res => {
          if (res.code === 200) {
            this.requirements = this.requirements.filter(r => r.id !== row.id)
            this.$message.success('需求已删除')
          }
        }).catch(() => {
          this.requirements = this.requirements.filter(r => r.id !== row.id)
          this.$message.success('需求已删除（本地）')
        })
      }).catch(() => {})
    },

    // ── 批量操作 ──
    batchMoveIteration() {
      const activeIter = this.iterations.find(i => i.status === 'active')
      if (!activeIter) return this.$message.warning('没有进行中的迭代')
      const ids = [...this.reqSelectedIds]
      ids.forEach(id => {
        const r = this.requirements.find(r => r.id === id)
        if (r) { r.iteration_id = activeIter.id; r.iteration_name = activeIter.name }
        rdApi.moveRequirementToIteration(id, activeIter.id).catch(() => {})
      })
      this.$message.success(`已将 ${ids.length} 个需求移入迭代 "${activeIter.name}"`)
      this.reqSelectedIds = []
    },
    batchChangeStatus() {
      this.$prompt('输入新状态 (backlog/todo/in_progress/in_review/done/closed)', '批量改状态', {
        inputPattern: /^(backlog|todo|in_progress|in_review|done|closed)$/,
        inputErrorMessage: '无效的状态值',
      }).then(({ value }) => {
        const ids = [...this.reqSelectedIds]
        ids.forEach(id => {
          const r = this.requirements.find(r => r.id === id)
          if (r) r.status = value
          rdApi.updateRequirementStatus(id, value).catch(() => {})
        })
        this.$message.success(`已将 ${ids.length} 个需求状态改为 "${this.statusLabel(value)}"`)
        this.reqSelectedIds = []
      }).catch(() => {})
    },
    batchDelete() {
      this.$confirm(`确定删除选中的 ${this.reqSelectedIds.length} 个需求？`, '批量删除', { type: 'warning' }).then(() => {
        const ids = [...this.reqSelectedIds]
        ids.forEach(id => {
          rdApi.deleteRequirement(id).catch(() => {})
        })
        this.requirements = this.requirements.filter(r => !ids.includes(r.id))
        this.$message.success(`已删除 ${ids.length} 个需求`)
        this.reqSelectedIds = []
      }).catch(() => {})
    },

    openRequirementDetail(row) {
      this.selectedReq = row
      this.reqDetailVisible = true
    },
    openBugDetail(row) {
      this.selectedBug = row
      this.bugDetailVisible = true
    },
    goToRequirementDetail(row) {
      this.$router.push(`/projects/${this.project.id}/requirements/${row.id}`)
    },
    goToBugDetail(row) {
      this.$router.push(`/projects/${this.project.id}/bugs/${row.id}`)
    },
    goToGantt() {
      this.$router.push(`/projects/${this.project.id}/gantt`)
    },

    ganttBarStyle(start, end) {
      const all = [
        ...this.iterationsWithDates.map(i => [i.start_date, i.end_date]),
        ...this.reqsWithDates.map(r => [r.start_date, r.due_date]),
      ].flat().filter(Boolean).sort()
      if (all.length === 0) return { left: '0%', width: '0%' }
      const rangeStart = new Date(all[0]).getTime()
      const rangeEnd = new Date(all[all.length - 1]).getTime()
      const total = rangeEnd - rangeStart || 1
      const left = ((new Date(start).getTime() - rangeStart) / total) * 100
      const width = ((new Date(end).getTime() - new Date(start).getTime()) / total) * 100
      return { left: Math.max(0, left) + '%', width: Math.max(2, width) + '%' }
    },

    getIterReqsWithDates(iterId) {
      return (this.requirements || []).filter(r => r.iteration_id === iterId && r.start_date && r.due_date)
    },

    async startConversation() {
      const domain = this.$store.getters['workspace/activeDomain'] || 'rd'
      try {
        const response = await getConversations()
        const linkedConversation = (response?.data || []).find(
          conversation =>
            conversation.project_id === this.project.id &&
            Array.isArray(conversation.services) &&
            conversation.services.includes('rd')
        )
        if (linkedConversation) {
          this.$router.push({
            path: '/dashboard',
            query: { conversation_id: linkedConversation.id, domain },
          })
          return
        }
      } catch (error) {
        // The create-conversation flow below remains available if history fails.
      }
      this.$router.push({ path: '/dashboard', query: { project_id: this.project.id, domain } })
    },

    // ── 项目编辑 ──
    openEditProject() {
      const p = this.project || {}
      this.editForm = {
        name: p.name || '',
        description: p.description || '',
        tech_frontend: (p.tech_stack && p.tech_stack.frontend) || '',
        tech_backend: (p.tech_stack && p.tech_stack.backend) || '',
        tech_database: (p.tech_stack && p.tech_stack.database) || '',
        tech_deployment: (p.tech_stack && p.tech_stack.deployment) || '',
      }
      this.showEditDialog = true
    },
    async handleSaveProject() {
      if (!this.editForm.name.trim()) {
        return this.$message.warning('项目名称不能为空')
      }
      const data = {
        name: this.editForm.name.trim(),
        description: this.editForm.description.trim(),
        tech_stack: {
          frontend: this.editForm.tech_frontend || '',
          backend: this.editForm.tech_backend || '',
          database: this.editForm.tech_database || '',
          deployment: this.editForm.tech_deployment || '',
        },
      }
      this.savingProject = true
      try {
        const res = await rdApi.updateProject(this.project.id, data)
        if (res.code === 200) {
          this.$message.success('项目更新成功')
          this.showEditDialog = false
          // 更新 Vuex store
          this.$store.commit('rd/SET_CURRENT_PROJECT', { ...this.project, ...data })
        } else {
          this.$message.error(res.message || '更新失败')
        }
      } catch (e) {
        this.$message.error('更新失败，请重试')
      } finally {
        this.savingProject = false
      }
    },

    // ── 成员管理 ──
    memberRoleLabel(role) {
      return { owner: 'Owner', admin: 'Admin', developer: 'Developer', viewer: 'Viewer', tester: 'Tester' }[role] || role
    },
    memberRoleType(role) {
      return { owner: '', admin: 'warning', developer: 'success', viewer: 'info', tester: '' }[role] || 'info'
    },
    handleAddMember() {
      if (!this.newMemberId) return
      const pid = this.project.id
      rdApi.addMember(pid, { user_id: this.newMemberId, role: this.newMemberRole }).then(res => {
        if (res.code === 201) {
          const newMember = res.data
          if (!newMember.user_name) {
            const u = this.allUsers.find(u => u.id === this.newMemberId)
            newMember.user_name = u ? u.username : this.newMemberId
          }
          this.projectMembers.push(newMember)
          this.$message.success('成员已添加')
        }
      }).catch(() => {
        const u = this.allUsers.find(u => u.id === this.newMemberId)
        this.projectMembers.push({ user_id: this.newMemberId, user_name: u ? u.username : this.newMemberId, role: this.newMemberRole })
        this.$message.success('成员已添加（本地）')
      })
      this.showAddMember = false
      this.newMemberId = ''
      this.newMemberRole = 'developer'
    },
    changeMemberRole(userId, newRole) {
      const member = this.projectMembers.find(m => m.user_id === userId)
      if (!member) return
      rdApi.updateMemberRole(this.project.id, userId, newRole).then(res => {
        if (res.code === 200) {
          member.role = newRole
          this.$message.success('角色已更新')
        }
      }).catch(() => {
        member.role = newRole
        this.$message.success('角色已更新（本地）')
      })
    },
    removeMember(member) {
      if (member.role === 'owner') {
        return this.$message.warning('不能移除项目所有者')
      }
      this.$confirm(`确定移除成员 "${member.user_name}"？`, '确认', { type: 'warning' }).then(() => {
        rdApi.removeMember(this.project.id, member.user_id).then(res => {
          if (res.code === 200) {
            this.projectMembers = this.projectMembers.filter(m => m.user_id !== member.user_id)
            this.$message.success('成员已移除')
          }
        }).catch(() => {
          this.projectMembers = this.projectMembers.filter(m => m.user_id !== member.user_id)
          this.$message.success('成员已移除（本地）')
        })
      }).catch(() => {})
    },

    // ── GitHub 授权 ──
    async checkGithubStatus() {
      // 先检查 OAuth 配置
      try {
        const cfgRes = await rdApi.getOauthConfig()
        if (cfgRes.code === 200 && cfgRes.data) {
          this.oauthConfigured = cfgRes.data.configured
          if (cfgRes.data.redirect_uri) {
            this.oauthForm.redirect_uri = cfgRes.data.redirect_uri
          }
        }
      } catch (e) { /* 保持默认 false */ }

      if (!this.oauthConfigured) return

      // 再检查授权状态
      try {
        const res = await rdApi.getGithubStatus()
        if (res.code === 200 && res.data) {
          this.githubConnected = res.data.connected
          this.githubUser = res.data.github_user || ''
        }
      } catch (e) { /* 保持默认 false */ }
    },
    async saveOauthConfig() {
      if (!this.oauthForm.client_id || !this.oauthForm.client_secret) {
        return this.$message.warning('请填写 Client ID 和 Client Secret')
      }
      this.savingOauthConfig = true
      try {
        const res = await rdApi.saveOauthConfig(this.oauthForm)
        if (res.code === 200) {
          this.oauthConfigured = true
          this.$message.success('OAuth 配置已保存')
        }
      } catch (e) {
        this.$message.error('保存失败，请重试')
      } finally {
        this.savingOauthConfig = false
      }
    },
    copyRedirectUri() {
      this.copyField(this.oauthForm.redirect_uri)
    },
    copyField(text) {
      navigator.clipboard.writeText(text).then(() => {
        this.$message.success('已复制: ' + text)
      }).catch(() => {
        this.$message.info('请手动复制: ' + text)
      })
    },
    async connectGithub() {
      this.connectingGithub = true
      try {
        const projectId = this.$route.params.id
        const res = await rdApi.getGithubAuthUrl({ state: projectId })
        if (res.code === 200 && res.data.url) {
          // 跳转到 GitHub 授权页面
          window.location.href = res.data.url
        } else {
          this.$message.error('获取授权链接失败')
        }
      } catch (e) {
        this.$message.error('获取授权链接失败，请稍后重试')
      } finally {
        this.connectingGithub = false
      }
    },
    async disconnectGithub() {
      this.$confirm('断开 GitHub 连接后，已关联的仓库将无法同步数据。确定断开？', '确认', { type: 'warning' }).then(async () => {
        try {
          await rdApi.revokeGithub()
          this.githubConnected = false
          this.githubUser = ''
          this.$message.success('已断开 GitHub 连接')
        } catch (e) {
          this.$message.error('操作失败')
        }
      }).catch(() => {})
    },
    async openAssociateDialog() {
      this.showAssociateDialog = true
      this.loadingGithubRepos = true
      this.githubRepoSearch = ''
      try {
        const res = await rdApi.listGithubRepos()
        if (res.code === 200) {
          this.githubRepos = res.data.items || []
        }
      } catch (e) {
        this.$message.error('获取 GitHub 仓库列表失败')
      } finally {
        this.loadingGithubRepos = false
      }
    },
    async associateRepo(repo) {
      this.associatingRepo = repo.github_id
      try {
        const res = await rdApi.createRepo(this.project.id, {
          full_name: repo.full_name,
          github_id: repo.github_id,
          description: repo.description,
          default_branch: repo.default_branch,
          language: repo.language,
          html_url: repo.html_url,
          clone_url: repo.clone_url,
          private: repo.private,
        })
        if (res.code === 201) {
          this.repos.push(res.data)
          this.$message.success(`已关联仓库 ${repo.full_name}`)
        }
      } catch (e) {
        this.$message.error('关联失败，请重试')
      } finally {
        this.associatingRepo = null
      }
    },

    async disassociateRepo(repo) {
      try {
        await this.$confirm('确定要取消关联该仓库吗？取消后可在 GitHub 中重新关联。', '取消关联仓库', {
          confirmButtonText: '确定取消',
          cancelButtonText: '保留',
          type: 'warning',
        })
      } catch {
        return
      }
      try {
        await rdApi.deleteRepo(this.project.id, repo.id)
        this.repos = this.repos.filter(r => r.id !== repo.id)
        this.$message.success('已取消关联')
      } catch (e) {
        this.$message.error('取消关联失败，请重试')
      }
    },

    // ── 创建操作 ──
    handleCreateIteration() {
      if (!this.iterForm.name) return this.$message.warning('请输入迭代名称')
      const pid = this.project.id
      const [start, end] = this.iterForm.dates || []
      const data = { name: this.iterForm.name, goal: this.iterForm.goal, start_date: start || undefined, end_date: end || undefined }
      rdApi.createIteration(pid, data).then(res => {
        if (res.code === 201) this.iterations.unshift(res.data)
        this.$message.success('迭代已创建')
      }).catch(() => {
        this.iterations.unshift({ id: 'iter-new-' + Date.now(), project_id: pid, ...data, status: 'planning', sort_order: this.iterations.length + 1, start_date: start || '', end_date: end || '' })
        this.$message.success('迭代已创建（本地）')
      })
      this.showCreateIteration = false
      this.iterForm = { name: '', goal: '', dates: [] }
    },
    handleCreateRequirement() {
      if (!this.reqForm.title.trim()) return this.$message.warning('请输入需求标题')
      const pid = this.project.id
      const assigneeIds = this.reqForm.assignee_ids || []
      const data = {
        title: this.reqForm.title.trim(),
        description: this.reqForm.description,
        priority: this.reqForm.priority,
        type: this.reqForm.type,
        iteration_id: this.reqForm.iteration_id || undefined,
        story_points: this.reqForm.story_points,
        parent_id: this.reqForm.parent_id || undefined,
        start_date: this.reqForm.start_date || undefined,
        due_date: this.reqForm.due_date || undefined,
      }
      this.showCreateRequirement = false
      this.reqForm = { title: '', description: '', priority: 'p2', type: 'feature', iteration_id: '', assignee_ids: [], story_points: 0, parent_id: null, start_date: null, due_date: null }

      rdApi.createRequirement(pid, data).then(res => {
        if (res.code === 201) {
          const iter = this.iterations.find(i => i.id === data.iteration_id)
          const newReq = {
            ...res.data,
            iteration_name: iter ? iter.name : null,
            _editStatus: false, _editIter: false, _editAssignee: false, _editSP: false, _editPriority: false,
            _assigneeIds: [...assigneeIds],
            _assignees: [],
          }
          this.requirements.unshift(newReq)
          // 添加所有负责人
          if (assigneeIds.length > 0) {
            const addPromises = assigneeIds.map(uid =>
              rdApi.addRequirementAssignee(pid, res.data.id, uid, 'primary').then(() => {
                const m = this.projectMembers.find(m2 => m2.user_id === uid)
                newReq._assignees.push({ user_id: uid, user_name: m ? m.user_name : uid, role: 'primary' })
                newReq.assignee_name = newReq._assignees.map(a => a.user_name).join(', ')
              }).catch(() => {})
            )
            Promise.all(addPromises).then(() => {
              newReq._assigneeIds = [...assigneeIds]
            })
          }
        }
        const suffix = this.reqForm.parent_id ? '（子需求）' : ''
        this.$message.success('需求已创建' + suffix)
      }).catch(err => {
        console.error('创建需求失败:', err)
        const assigneeNames = assigneeIds.map(id => {
          const m = this.projectMembers.find(m2 => m2.user_id === id)
          return m ? m.user_name : id
        }).join(', ')
        const iter = this.iterations.find(i => i.id === data.iteration_id)
        this.requirements.unshift({
          id: 'req-new-' + Date.now(), project_id: pid, ...data,
          iteration_name: iter ? iter.name : null,
          assignee_name: assigneeNames || null,
          status: 'backlog', labels: [], created_at: new Date().toISOString(),
          _editStatus: false, _editIter: false, _editAssignee: false, _editSP: false, _editPriority: false,
          _assigneeIds: [...assigneeIds],
          _assignees: assigneeIds.map(uid => {
            const m = this.projectMembers.find(m2 => m2.user_id === uid)
            return { user_id: uid, user_name: m ? m.user_name : uid, role: 'primary' }
          }),
        })
        this.$message.success('需求已创建（本地）')
      })
    },
    handleCreateBug() {
      if (!this.bugForm.title) return this.$message.warning('请输入缺陷标题')
      const pid = this.project.id
      const assigneeId = this.bugForm.assignee_id || undefined
      const data = {
        title: this.bugForm.title,
        description: this.bugForm.description,
        severity: this.bugForm.severity,
        priority: this.bugForm.priority,
        iteration_id: this.bugForm.iteration_id || undefined,
        environment: this.bugForm.environment || undefined,
        developer_id: this.bugForm.developer_id || undefined,
        designer_id: this.bugForm.designer_id || undefined,
        tester_id: this.bugForm.tester_id || undefined,
      }
      this.creatingBug = true
      rdApi.createBug(pid, data).then(res => {
        if (res.code === 201) {
          const newBug = { ...res.data, _editStatus: false, _editIter: false, _editAssignee: false, _editSeverity: false, _editPriority: false, _assignees: [], _assigneeIds: [] }
          this.bugs.unshift(newBug)
          if (assigneeId) {
            rdApi.addBugAssignee(pid, res.data.id, assigneeId, 'fixer').then(() => {
              const m = this.projectMembers.find(m2 => m2.user_id === assigneeId)
              newBug._assignees = [{ user_id: assigneeId, user_name: m ? m.user_name : assigneeId, role: 'fixer' }]
              newBug._assigneeIds = [assigneeId]
              newBug.assignee_name = m ? m.user_name : assigneeId
            }).catch(() => {})
          }
        }
        this.showCreateBug = false
        this.bugForm = { title: '', description: '', severity: 'major', priority: 'p2', assignee_id: '', iteration_id: '', environment: '', developer_id: '', designer_id: '', tester_id: '' }
        this.creatingBug = false
        this.$message.success('缺陷已提交')
      }).catch(() => {
        const assignee = this.projectMembers.find(m => m.user_id === assigneeId)
        this.bugs.unshift({
          id: 'bug-new-' + Date.now(), project_id: pid, ...data,
          assignee_name: assignee ? assignee.user_name : null,
          iteration_name: (this.iterations.find(i => i.id === data.iteration_id) || {}).name || null,
          status: 'open', labels: [], created_at: new Date().toISOString(),
          _editStatus: false, _editIter: false, _editAssignee: false, _editSeverity: false, _editPriority: false,
          _assignees: assignee ? [{ user_id: assigneeId, user_name: assignee.user_name, role: 'fixer' }] : [],
          _assigneeIds: assignee ? [assigneeId] : [],
        })
        this.showCreateBug = false
        this.bugForm = { title: '', description: '', severity: 'major', priority: 'p2', assignee_id: '', iteration_id: '', environment: '', developer_id: '', designer_id: '', tester_id: '' }
        this.creatingBug = false
        this.$message.success('缺陷已提交（本地）')
      })
    },

    // ── Bug 行内编辑方法 ──
    startInlineEditBug(row) {
      this.inlineEditBugId = row.id
      this.inlineBugTitle = row.title
    },
    saveInlineEditBug(row) {
      const newTitle = (this.inlineBugTitle || '').trim()
      this.inlineEditBugId = null
      this.inlineBugTitle = ''
      if (newTitle && newTitle !== row.title) {
        row.title = newTitle
        rdApi.updateBug(row.id, { title: newTitle }).catch(() => {})
      }
    },
    cancelInlineBugEdit() {
      this.inlineEditBugId = null
      this.inlineBugTitle = ''
    },
    cycleBugSeverity(row) {
      const order = ['blocker', 'critical', 'major', 'minor', 'trivial']
      const idx = order.indexOf(row.severity)
      row.severity = order[(idx + 1) % order.length]
      rdApi.updateBug(row.id, { severity: row.severity }).catch(() => {})
    },
    cycleBugPriority(row) {
      const order = ['p0', 'p1', 'p2', 'p3']
      const idx = order.indexOf(row.priority)
      row.priority = order[(idx + 1) % order.length]
      rdApi.updateBug(row.id, { priority: row.priority }).catch(() => {})
    },
    changeBugStatus(row, newStatus) {
      row.status = newStatus
      rdApi.updateBug(row.id, { status: newStatus }).catch(() => {})
    },
    moveBugIteration(row, iterId) {
      const prevIter = row.iteration_id
      row.iteration_id = iterId || null
      row.iteration_name = iterId ? (this.iterations.find(i => i.id === iterId) || {}).name || null : null
      rdApi.updateBug(row.id, { iteration_id: iterId || null }).catch(() => {
        row.iteration_id = prevIter
      })
    },
    saveBugAssignees(row, userIds) {
      const pid = this.project.id
      row._assigneeIds = userIds || []
      row._assignees = (userIds || []).map(uid => {
        const m = this.projectMembers.find(m2 => m2.user_id === uid)
        return { user_id: uid, user_name: m ? m.user_name : uid, role: 'fixer' }
      })
      row.assignee_name = (userIds || []).map(uid => this.getDevName(uid)).join(', ')
      // 简化：仅保留第一个为API调用
      if (userIds && userIds.length > 0) {
        rdApi.addBugAssignee(pid, row.id, userIds[0], 'fixer').catch(() => {})
      }
    },
    duplicateBug(row) {
      const { id, created_at, updated_at, _editStatus, _editIter, _editAssignee, _assignees, _assigneeIds, assignee_name, ...copy } = { ...row }
      copy.title = (copy.title || '') + ' (副本)'
      copy.status = 'open'
      const pid = this.project.id
      rdApi.createBug(pid, copy).then(res => {
        if (res.code === 201) {
          this.bugs.unshift({ ...res.data, _editStatus: false, _editIter: false, _editAssignee: false, _editSeverity: false, _editPriority: false, _assignees: [], _assigneeIds: [] })
          this.$message.success('缺陷已复制')
        }
      }).catch(() => {
        this.bugs.unshift({
          id: 'bug-dup-' + Date.now(), project_id: pid, ...copy,
          created_at: new Date().toISOString(),
          _editStatus: false, _editIter: false, _editAssignee: false, _editSeverity: false, _editPriority: false,
          _assignees: [], _assigneeIds: [],
        })
        this.$message.success('缺陷已复制（本地）')
      })
    },
    deleteBugRow(row) {
      this.$confirm(`确定删除缺陷 "${row.title}"？`, '确认', { type: 'warning' }).then(() => {
        rdApi.deleteBug(row.id).then(() => {
          this.bugs = this.bugs.filter(b => b.id !== row.id)
          this.$message.success('缺陷已删除')
        }).catch(() => {
          this.bugs = this.bugs.filter(b => b.id !== row.id)
          this.$message.success('缺陷已删除（本地）')
        })
      }).catch(() => {})
    },
    batchMoveBugs(iterId) {
      if (!iterId) return
      const iterName = (this.iterations.find(i => i.id === iterId) || {}).name || null
      this.bugSelectedIds.forEach(id => {
        const b = this.bugs.find(b2 => b2.id === id)
        if (b) {
          b.iteration_id = iterId
          b.iteration_name = iterName
          rdApi.updateBug(id, { iteration_id: iterId }).catch(() => {})
        }
      })
      this._moveBugTarget = null
      this.$message.success('已批量移入迭代')
    },
    batchChangeBugStatus(status) {
      if (!status) return
      this.bugSelectedIds.forEach(id => {
        const b = this.bugs.find(b2 => b2.id === id)
        if (b) { b.status = status; rdApi.updateBug(id, { status }).catch(() => {}) }
      })
      this._batchBugStatus = ''
      this.$message.success('已批量更改状态')
    },
    batchDeleteBugs() {
      this.$confirm(`确定删除选中的 ${this.bugSelectedIds.length} 个缺陷？`, '批量删除', { type: 'warning' }).then(() => {
        Promise.allSettled(this.bugSelectedIds.map(id => rdApi.deleteBug(id))).finally(() => {
          this.bugs = this.bugs.filter(b => !this.bugSelectedIds.includes(b.id))
          this.bugSelectedIds = []
          this.$message.success('已批量删除')
        })
      }).catch(() => {})
    },
  },
}
</script>

<style scoped>
.rd-project-detail-page {
  display: flex;
  gap: 12px;
  padding: 12px;
  height: 100vh;
  background: linear-gradient(135deg, #e8f0ff 0%, #f0f5ff 50%, #f5f7fa 100%);
  overflow: hidden;
}
.rd-detail-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  overflow: hidden;
}

/* 顶部 */
.detail-header { margin-bottom: 0; padding: 18px 22px 0; border-bottom: 1px solid #f0f0f0; }
.header-main {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-top: 8px;
}
.header-info h2 { margin: 0 0 4px; font-size: 22px; color: #303133; }
.header-desc { font-size: 13px; color: #909399; }
.header-actions { display: flex; gap: 8px; flex-shrink: 0; }
.detail-tabs { margin-top: 16px; }
.detail-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 22px 24px;
}

/* 技术栈 */
.info-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}
.info-card {
  background: #fff;
  border-radius: 8px;
  padding: 14px 18px;
  border: 1px solid #ebeef5;
}
.info-card h4 { margin: 0 0 4px; font-size: 12px; color: #909399; display: flex; align-items: center; gap: 4px; }
.info-card span { font-size: 15px; font-weight: 500; color: #303133; }

/* 统计卡片 */
.stats-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}
.stat-card {
  background: #fff;
  border-radius: 10px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  border: 1px solid #ebeef5;
}
.stat-icon {
  width: 44px; height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}
.stat-body { flex: 1; }
.stat-num { font-size: 22px; font-weight: 700; color: #303133; }
.stat-label { font-size: 12px; color: #909399; margin-top: 2px; }

/* 概览面板 */
.overview-panels {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.overview-panel {
  background: #fff;
  border-radius: 10px;
  border: 1px solid #ebeef5;
  padding: 20px;
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.panel-header h4 { margin: 0; font-size: 14px; color: #303133; display: flex; align-items: center; gap: 6px; }
.panel-empty { text-align: center; color: #c0c4cc; padding: 32px; font-size: 13px; }

/* ========================= 当前迭代卡片（Overview） ========================= */
.active-iteration-card {
  background: linear-gradient(135deg, #f8fafc 0%, #f0f9ff 100%);
  border-radius: 12px;
  padding: 20px 22px;
  border: 1px solid #e0edf8;
  transition: box-shadow 0.2s;
}
.active-iteration-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.04); }
.ai-top { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.ai-badge {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 11px; font-weight: 700; color: #67c23a;
  background: #e8f5e9; padding: 3px 10px; border-radius: 20px;
  white-space: nowrap;
}
.ai-badge-dot { width: 6px; height: 6px; border-radius: 50%; background: #67c23a; animation: pulse-dot 2s infinite; }
@keyframes pulse-dot { 0%,100% { opacity:1 } 50% { opacity:0.4 } }
.ai-name { font-size: 16px; font-weight: 700; color: #1e293b; }
.ai-body { display: flex; flex-direction: column; gap: 10px; }
.ai-meta-row { display: flex; gap: 20px; flex-wrap: wrap; }
.ai-meta { font-size: 12px; color: #64748b; display: flex; align-items: center; gap: 4px; }
.ai-meta i { font-size: 13px; color: #94a3b8; }
.ai-progress { display: flex; align-items: center; gap: 10px; }
.progress-track {
  flex: 1; height: 20px; background: #e8ecf1; border-radius: 10px; overflow: hidden;
  position: relative;
}
.progress-fill {
  height: 100%; background: linear-gradient(90deg, #409eff, #67c23a);
  border-radius: 10px; transition: width 0.5s ease;
  display: flex; align-items: center; justify-content: flex-end;
  min-width: 0;
}
.progress-inner-text { font-size: 10px; color: #fff; font-weight: 700; padding-right: 8px; white-space: nowrap; }
.progress-text-out { font-size: 12px; font-weight: 700; color: #409eff; white-space: nowrap; }
.ai-goal {
  font-size: 12px; color: #64748b; background: #fff; padding: 8px 12px;
  border-radius: 8px; border: 1px dashed #d0e0f0; line-height: 1.5;
}
/* Markdown 渲染样式 — ::v-deep 穿透 scoped 以样式化 v-html 注入内容 */
::v-deep .ai-goal .md-h2, ::v-deep .iter-goal-area .md-h2 { font-size: 15px; font-weight: 700; color: #1e293b; margin: 10px 0 6px; }
::v-deep .ai-goal .md-h3, ::v-deep .iter-goal-area .md-h3 { font-size: 14px; font-weight: 700; color: #334155; margin: 8px 0 4px; }
::v-deep .ai-goal .md-h4, ::v-deep .iter-goal-area .md-h4 { font-size: 13px; font-weight: 600; color: #475569; margin: 6px 0 4px; }
::v-deep .ai-goal .md-table, ::v-deep .iter-goal-area .md-table {
  width: 100%; border-collapse: collapse; font-size: 12px; margin: 8px 0;
}
::v-deep .ai-goal .md-table th, ::v-deep .iter-goal-area .md-table th {
  background: #f0f5ff; padding: 6px 10px; border: 1px solid #c0ccda;
  font-weight: 600; color: #1e293b; text-align: left;
}
::v-deep .ai-goal .md-table td, ::v-deep .iter-goal-area .md-table td {
  padding: 5px 10px; border: 1px solid #d0d7e2; color: #475569;
}
::v-deep .ai-goal .md-table tr:nth-child(even) td, ::v-deep .iter-goal-area .md-table tr:nth-child(even) td {
  background: #fafbfc;
}
::v-deep .ai-goal .code-block, ::v-deep .iter-goal-area .code-block {
  display: block; background: #1e293b; color: #e2e8f0; padding: 10px 14px;
  border-radius: 6px; font-size: 12px; margin: 6px 0; overflow-x: auto;
  font-family: 'Consolas', 'Courier New', monospace;
}
::v-deep .ai-goal .inline-code, ::v-deep .iter-goal-area .inline-code {
  background: #f0f2f5; color: #e03e3e; padding: 1px 6px; border-radius: 3px;
  font-size: 11px; font-family: 'Consolas', 'Courier New', monospace;
}
::v-deep .ai-goal li, ::v-deep .iter-goal-area li {
  margin: 0 0 0 16px; padding: 0; line-height: 1.4; font-size: 12px;
}
::v-deep .ai-goal p, ::v-deep .iter-goal-area p {
  margin: 4px 0; line-height: 1.5;
}

/* ========================= 构建迷你列表 ========================= */
.build-mini-list { display: flex; flex-direction: column; gap: 8px; }
.build-mini-item {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 12px; background: #f5f7fa; border-radius: 6px; font-size: 13px;
  cursor: pointer; transition: background 0.2s, box-shadow 0.2s;
}
.build-mini-item:hover { background: #ecf5ff; box-shadow: 0 2px 6px rgba(64,158,255,0.12); }
.bmi-num { font-weight: 600; color: #303133; min-width: 36px; flex-shrink: 0; }
.bmi-msg { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #606266; max-width: 260px; }
.bmi-time { color: #909399; white-space: nowrap; flex-shrink: 0; }

/* ========================= 迭代 Tab ========================= */
.tab-toolbar {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;
}
.toolbar-left { display: flex; align-items: center; flex-wrap: wrap; }
.toolbar-right { display: flex; align-items: center; gap: 8px; }
.tab-count { font-size: 14px; font-weight: 600; color: #303133; }

/* 空状态 */
.iter-empty-state {
  text-align: center; padding: 64px 20px; color: #c0c4cc;
}
.iter-empty-state i { font-size: 56px; display: block; margin-bottom: 12px; }
.iter-empty-state h3 { font-size: 18px; color: #909399; margin: 0 0 8px; }
.iter-empty-state p { font-size: 13px; margin: 0 0 20px; }

/* 迭代卡片列表 */
.iterations-list { display: flex; flex-direction: column; gap: 20px; }

/* 迭代卡片 */
.iteration-card {
  background: #fff;
  border-radius: 14px;
  border: 1px solid #e8ecf1;
  padding: 0;
  overflow: hidden;
  transition: box-shadow 0.2s, transform 0.15s;
  position: relative;
}
.iteration-card::before {
  content: '';
  position: absolute; left: 0; top: 0; bottom: 0;
  width: 4px;
  border-radius: 14px 0 0 14px;
}
.iteration-card.iter-active::before { background: linear-gradient(180deg, #67c23a, #85ce61); }
.iteration-card.iter-completed::before { background: linear-gradient(180deg, #909399, #b0b4bb); }
.iteration-card.iter-planning::before { background: linear-gradient(180deg, #e6a23c, #f0c060); }
.iteration-card:hover { box-shadow: 0 6px 24px rgba(0,0,0,0.06); transform: translateY(-1px); }

/* 卡片头部 */
.iter-head {
  display: flex; justify-content: space-between; align-items: flex-start;
  padding: 20px 22px 14px 22px;
}
.iter-head-left { display: flex; gap: 12px; align-items: flex-start; }
.iter-status-dot {
  width: 10px; height: 10px; border-radius: 50%; margin-top: 6px; flex-shrink: 0;
}
.dot-active { background: #67c23a; box-shadow: 0 0 0 4px rgba(103,194,58,0.15); }
.dot-completed { background: #909399; box-shadow: 0 0 0 4px rgba(144,147,153,0.12); }
.dot-planning { background: #e6a23c; box-shadow: 0 0 0 4px rgba(230,162,60,0.12); }
.iter-head-info { display: flex; flex-direction: column; gap: 4px; }
.iter-name { margin: 0; font-size: 16px; font-weight: 700; color: #1e293b; letter-spacing: -0.2px; }
.iter-subtitle { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.iter-status-badge {
  font-size: 11px; font-weight: 600; padding: 2px 10px; border-radius: 12px;
}
.badge-active { background: #e8f5e9; color: #67c23a; }
.badge-completed { background: #f0f2f5; color: #909399; }
.badge-planning { background: #fef5e7; color: #e6a23c; }
.iter-date-range { font-size: 12px; color: #94a3b8; display: flex; align-items: center; gap: 4px; }
.iter-date-range i { font-size: 12px; }
.iter-head-actions { display: flex; gap: 4px; opacity: 0; transition: opacity 0.15s; }
.iteration-card:hover .iter-head-actions { opacity: 1; }

/* 目标 */
.iter-goal-area {
  margin: 0 22px 14px;
  display: flex; align-items: flex-start; gap: 8px;
  font-size: 13px; color: #475569; background: #f8fafc;
  padding: 10px 14px; border-radius: 8px; border: 1px solid #f0f2f5;
  line-height: 1.5;
}
.iter-goal-area i { color: #409eff; margin-top: 2px; flex-shrink: 0; }

/* 进度条 */
.iter-progress-row {
  display: flex; align-items: center; gap: 12px;
  margin: 0 22px 14px;
}
.iter-progress-bar {
  flex: 1; height: 8px; background: #f0f2f5; border-radius: 4px; overflow: hidden;
}
.iter-progress-fill {
  height: 100%; border-radius: 4px; transition: width 0.6s ease;
}
.fill-active { background: linear-gradient(90deg, #67c23a, #85ce61); }
.fill-completed { background: linear-gradient(90deg, #909399, #b0b4bb); }
.fill-planning { background: linear-gradient(90deg, #e6a23c, #f0c060); }
.iter-progress-meta { display: flex; align-items: baseline; gap: 4px; white-space: nowrap; }
.iter-progress-num { font-size: 15px; font-weight: 700; color: #303133; }
.iter-progress-label { font-size: 11px; color: #94a3b8; }

/* 统计卡片 */
.iter-stats {
  display: flex; gap: 10px; margin: 0 22px 16px;
}
.iter-stat-card {
  flex: 1; text-align: center;
  padding: 10px 8px; background: #f8fafc;
  border-radius: 8px; border: 1px solid #f0f2f5;
}
.iter-stat-num { display: block; font-size: 18px; font-weight: 700; color: #1e293b; }
.iter-stat-label { display: block; font-size: 11px; color: #94a3b8; margin-top: 2px; }

/* 看板 */
.iter-kanban {
  display: grid; grid-template-columns: 1fr 1fr; gap: 1px;
  background: #e8ecf1; border-top: 1px solid #e8ecf1;
}
.kanban-col {
  background: #fafbfc; padding: 14px 16px;
}
.kanban-col:first-child { border-right: 1px solid #e8ecf1; }
.kanban-col-head {
  font-size: 12px; font-weight: 700; color: #64748b; margin-bottom: 10px;
  display: flex; align-items: center; gap: 6px;
  text-transform: uppercase; letter-spacing: 0.4px;
}
.kanban-col-head i { font-size: 13px; }
.kanban-col-count {
  margin-left: auto; font-size: 11px; font-weight: 600;
  background: #e8ecf1; color: #64748b; padding: 1px 8px; border-radius: 10px;
}
.kanban-card {
  background: #fff;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  border: 1px solid #ebeef5;
  transition: all 0.15s;
}
.kanban-card:last-child { margin-bottom: 0; }
.kanban-card:hover { border-color: #c0c8d8; box-shadow: 0 2px 8px rgba(0,0,0,0.05); transform: translateX(2px); }
.kanban-card-tag {
  font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px;
  white-space: nowrap; flex-shrink: 0;
}
.kanban-card-title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #303133; font-weight: 500; }
.kanban-card-status {
  font-size: 10px; color: #94a3b8; padding: 2px 6px; background: #f0f2f5;
  border-radius: 4px; white-space: nowrap; flex-shrink: 0;
}
.pri-p0 { background: #fde8e8; color: #f56c6c; }
.pri-p1 { background: #fdf6e8; color: #e6a23c; }
.pri-p2 { background: #e8f4fd; color: #409eff; }
.pri-p3 { background: #f0f2f5; color: #909399; }
.sev-blocker, .sev-critical { background: #fde8e8; color: #f56c6c; }
.sev-major { background: #fdf6e8; color: #e6a23c; }
.sev-minor { background: #e8f4fd; color: #409eff; }
.sev-trivial { background: #f0f2f5; color: #909399; }
.kanban-empty { text-align: center; font-size: 13px; color: #d0d4d9; padding: 12px; }
.kanban-more {
  text-align: center; font-size: 12px; color: #409eff; padding: 8px;
  cursor: pointer; border-top: 1px dashed #e8ecf1; margin-top: 4px;
  transition: color 0.15s;
}
.kanban-more:hover { color: #1a6dd4; }

/* ========================= 迭代弹窗 ========================= */
.iter-dialog ::v-deep .el-dialog__header {
  padding: 20px 24px 0; border-bottom: none;
}
.iter-dialog ::v-deep .el-dialog__body {
  padding: 16px 24px 8px;
}
.iter-dialog ::v-deep .el-dialog__footer {
  padding: 12px 24px 20px; border-top: none;
}
.dialog-title-row {
  display: flex; align-items: center; gap: 10px;
  font-size: 17px; font-weight: 700; color: #1e293b;
}
.dialog-title-row i { font-size: 20px; color: #409eff; }
.dialog-footer-row { display: flex; justify-content: flex-end; gap: 10px; }
.iter-form-body { }
.iter-form-main { display: flex; flex-direction: column; gap: 18px; }
.form-field-lg { display: flex; flex-direction: column; gap: 6px; }
.form-field { display: flex; flex-direction: column; gap: 6px; }
.form-label { font-size: 13px; font-weight: 600; color: #475569; }
.form-label .required { color: #f56c6c; margin-left: 1px; }
.form-row-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

/* 状态选择自定义 */
.status-radio-group { display: flex; gap: 4px; }
.status-radio {
  flex: 1; display: flex; align-items: center; justify-content: center; gap: 6px;
  padding: 8px 4px; border-radius: 8px; cursor: pointer;
  font-size: 12px; font-weight: 500; color: #64748b;
  border: 2px solid #e8ecf1; background: #fafbfc;
  transition: all 0.2s;
}
.status-radio:hover { border-color: #c0c8d8; }
.status-radio.active { border-color: #409eff; background: #e8f4fd; color: #409eff; }
.sr-dot { width: 8px; height: 8px; border-radius: 50%; }
.sr-dot.dot-planning { background: #e6a23c; }
.sr-dot.dot-active { background: #67c23a; }
.sr-dot.dot-completed { background: #909399; }

/* ========================= 列显示切换 ========================= */
.col-toggle-list { display: flex; flex-direction: column; gap: 6px; }

/* ========================= 需求表格增强 ========================= */
.req-table { font-size: 13px; }
.req-table ::v-deep .el-table__row { cursor: pointer; }
.req-table ::v-deep .el-table__row:hover { background: #f0f5ff !important; }
.cell-title { cursor: pointer; }
.cell-dates { font-size: 12px; color: #909399; white-space: nowrap; }

/* 需求表格增强 */
.req-table-enhanced {
  font-size: 13px;
  border-radius: 8px;
  overflow: hidden;
}
.req-table-enhanced ::v-deep .el-table__header th {
  background: #f8fafc;
  color: #64748b;
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  border-bottom: 2px solid #e2e8f0;
  padding: 10px 8px;
}
.req-table-enhanced ::v-deep .el-table__row {
  cursor: pointer;
  transition: background 0.1s;
}
.req-table-enhanced ::v-deep .el-table__row:hover {
  background: #f0f5ff !important;
}
.req-table-enhanced ::v-deep .el-table__row .cell {
  padding: 0 8px;
}

/* 行菜单按钮 */
.col-menu { text-align: center; }
.row-menu-btn {
  padding: 2px 4px !important;
  font-size: 16px;
  color: #909399;
  opacity: 0;
  transition: opacity 0.15s;
}
.req-table-enhanced ::v-deep .el-table__row:hover .row-menu-btn { opacity: 1; }
.row-menu-list { display: flex; flex-direction: column; gap: 2px; }
.row-menu-item {
  padding: 8px 12px;
  font-size: 13px;
  color: #475569;
  cursor: pointer;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: background 0.1s;
}
.row-menu-item:hover { background: #f0f5ff; }
.row-menu-item.danger { color: #f56c6c; }
.row-menu-item.danger:hover { background: #fef0f0; }
.row-menu-item i { width: 16px; text-align: center; }

/* 优先级按钮样式 */
.priority-btn {
  display: inline-block;
  padding: 3px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  user-select: none;
  transition: transform 0.1s, box-shadow 0.1s;
  border: 1px solid transparent;
}
.priority-btn:hover { transform: scale(1.05); }
.pbtn-p0 { background: #fde8e8; color: #f56c6c; border-color: #fbc4c4; }
.pbtn-p1 { background: #fdf6e8; color: #e6a23c; border-color: #faecd8; }
.pbtn-p2 { background: #e8f4fd; color: #409eff; border-color: #cce5fa; }
.pbtn-p3 { background: #f0f2f5; color: #909399; border-color: #e2e4e7; }

/* 状态显示 */
.status-display {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}
.status-display:hover { filter: brightness(0.95); }
.s-backlog { background: #f0f2f5; color: #909399; }
.s-todo { background: #fdf6e8; color: #e6a23c; }
.s-in_progress { background: #e8f4fd; color: #409eff; }
.s-in_review { background: #f0e6ff; color: #b37feb; }
.s-done, .s-closed { background: #f0fdf4; color: #67c23a; }

/* 类型标签 */
.type-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}
.tp-feature { background: #e8f4fd; color: #409eff; }
.tp-enhancement { background: #f0fdf4; color: #67c23a; }
.tp-bugfix { background: #fef0f0; color: #f56c6c; }
.tp-tech_debt { background: #f0f2f5; color: #909399; }
.tp-research { background: #f0e6ff; color: #b37feb; }

/* 可点击单元格 */
.clickable-cell { cursor: pointer; transition: filter 0.1s; }
.clickable-cell:hover { filter: brightness(1.05); }

/* 内联编辑 */
.cell-edit-inline {
  min-width: 60px;
}
.plain-number-input {
  width: 55px;
  padding: 4px 6px;
  border: 1px solid #409eff;
  border-radius: 6px;
  font-size: 13px;
  text-align: center;
  outline: none;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.15);
}
.plain-number-input::-webkit-inner-spin-button,
.plain-number-input::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

/* 规模点显示 */
.sp-display {
  cursor: pointer;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
  color: #909399;
  transition: background 0.1s;
}
.sp-display:hover { background: #f0f5ff; color: #409eff; }
.sp-display.has-sp { color: #303133; }

/* 负责人 */
.assignee-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 6px;
  transition: background 0.1s;
}
.assignee-cell:hover { background: #f0f5ff; }
.assignee-avatar-sm {
  width: 24px; height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
}
.assignee-text { font-size: 12px; color: #303133; }
.no-assignee { font-size: 12px; color: #c0c4cc; }

/* 标签内联 */
.label-inline { display: flex; flex-wrap: wrap; align-items: center; gap: 2px; }
.more-labels { font-size: 11px; color: #909399; }
.no-labels { font-size: 12px; color: #c0c4cc; }

/* 多选操作栏 */
.multi-select-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  background: #f0f5ff;
  border: 1px solid #d0e0f7;
  border-radius: 8px;
  margin-bottom: 10px;
  font-size: 13px;
  color: #475569;
}
.multi-select-bar span:first-child {
  font-weight: 600;
  color: #409eff;
}

/* GitHub 连接面板 */
.github-connect-panel {
  text-align: center;
  padding: 56px 24px;
  background: #fff;
  border-radius: 12px;
  max-width: 520px;
  margin: 0 auto;
}
.github-connect-panel .github-connect-icon {
  font-size: 48px;
  color: #c0c4cc;
  margin-bottom: 16px;
}
.github-connect-panel h3 {
  font-size: 20px;
  margin: 0 0 8px;
  color: #303133;
}
.github-connect-panel p {
  color: #909399;
  margin: 0 0 20px;
  line-height: 1.6;
  font-size: 14px;
}
.github-note {
  margin-top: 16px !important;
  font-size: 12px !important;
  color: #c0c4cc !important;
}
.github-note code {
  background: #f5f7fa;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 12px;
}
.github-note a {
  color: #409eff;
  text-decoration: none;
}

/* OAuth 配置教程面板 */
.oauth-setup-panel {
  background: #fff;
  border-radius: 12px;
  max-width: 700px;
  margin: 0 auto;
  padding: 32px;
}
.oauth-setup-panel > h3 {
  font-size: 20px;
  margin: 0 0 24px;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
}
.oauth-tutorial {
  margin-bottom: 24px;
}
.oauth-step {
  display: flex;
  gap: 14px;
  margin-bottom: 20px;
}
.step-num {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
}
.step-content {
  flex: 1;
}
.step-content strong {
  display: block;
  font-size: 15px;
  color: #303133;
  margin-bottom: 6px;
}
.step-content p {
  font-size: 13px;
  color: #606266;
  margin: 0 0 6px;
  line-height: 1.6;
}
.oauth-link-btn {
  display: inline-block;
  padding: 6px 14px;
  background: #f0f5ff;
  color: #409eff;
  border-radius: 6px;
  font-size: 13px;
  text-decoration: none;
  margin-top: 4px;
}
.oauth-link-btn:hover {
  background: #e0edff;
}
.oauth-field-table {
  width: 100%;
  border-collapse: collapse;
  margin: 8px 0;
  font-size: 13px;
}
.oauth-field-table td {
  padding: 8px 10px;
  border: 1px solid #ebeef5;
  vertical-align: middle;
}
.oauth-field-table .field-label {
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
  background: #fafbfc;
  width: 200px;
}
.oauth-field-table .field-label strong {
  font-size: 13px;
  display: inline;
}
.oauth-field-table .field-value code {
  background: #f5f7fa;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 13px;
  color: #e6a23c;
  word-break: break-all;
}
.oauth-field-table .field-hint {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
}
.oauth-note {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}
.oauth-cred-form {
  border-top: 1px solid #ebeef5;
  padding-top: 20px;
}

/* GitHub 仓库关联列表 */
.github-repo-list {
  max-height: 400px;
  overflow-y: auto;
}
.github-repo-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid #f2f3f5;
}
.github-repo-item.is-associated {
  opacity: 0.5;
}
.github-repo-info strong {
  display: block;
  font-size: 14px;
  color: #303133;
}
.github-repo-info > span {
  display: block;
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}
.github-repo-meta {
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #c0c4cc;
}

/* 仓库卡片网格 */
.repos-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 14px;
}
.repo-card {
  background: #fff;
  border-radius: 10px;
  border: 1px solid #ebeef5;
  padding: 20px;
  cursor: pointer;
  transition: box-shadow 0.2s, transform 0.15s;
  position: relative;
}
.repo-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.08); transform: translateY(-2px); }
.repo-card-close {
  position: absolute;
  top: 6px;
  right: 6px;
  color: #c0c4cc;
  font-size: 14px;
  padding: 2px;
  opacity: 0;
  transition: opacity 0.15s, color 0.15s;
}
.repo-card:hover .repo-card-close { opacity: 1; }
.repo-card-close:hover { color: #f56c6c; }
.repo-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.repo-card-header h4 { margin: 0; font-size: 15px; color: #303133; display: flex; align-items: center; gap: 8px; }
.repo-desc { font-size: 13px; color: #606266; margin: 0 0 12px; }
.repo-meta { display: flex; gap: 16px; font-size: 12px; color: #909399; margin-bottom: 10px; }
.repo-branches { display: flex; flex-wrap: wrap; gap: 4px; align-items: center; }
.more-branches { font-size: 11px; color: #909399; }

/* 详情弹窗 */
.detail-dialog .dd-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
.detail-dialog .dd-header h3 { margin: 0; font-size: 17px; color: #303133; max-width: 70%; }
.dd-tags { display: flex; gap: 6px; }
.dd-meta { display: flex; gap: 20px; font-size: 13px; color: #909399; margin-bottom: 16px; }
.detail-dialog h4 { font-size: 13px; color: #303133; margin: 12px 0 6px; }
.dd-desc p { font-size: 13px; color: #606266; line-height: 1.6; margin: 0; }
.dd-behavior p { font-size: 13px; margin: 0; }
.branch-item { display: flex; align-items: center; gap: 8px; padding: 8px 10px; background: #f5f7fa; border-radius: 6px; margin-bottom: 4px; font-size: 13px; }
.branch-name { font-family: monospace; flex: 1; color: #303133; }
.commit-item { display: flex; align-items: center; gap: 8px; padding: 6px 10px; font-size: 12px; border-bottom: 1px solid #f0f2f5; }
.commit-hash { font-family: monospace; color: #409eff; }
.commit-msg { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #606266; }
.commit-author { color: #909399; }
.commit-time { color: #c0c4cc; white-space: nowrap; }

.text-green { color: #67c23a; }
.text-red { color: #f56c6c; }
.text-muted { color: #c0c4cc; font-size: 12px; }

/* 甘特图预览 */
.gantt-preview { overflow-x: auto; }
.gantt-mini { min-width: 600px; }
.gantt-mini-header { display: flex; margin-bottom: 8px; }
.gantt-mini-label { width: 220px; flex-shrink: 0; font-size: 12px; font-weight: 600; color: #909399; padding: 6px 12px; }
.gantt-mini-timeline { flex: 1; display: flex; }
.gantt-month-col { flex: 1; text-align: center; font-size: 11px; color: #909399; padding: 6px 0; border-left: 1px solid #ebeef5; }
.gantt-mini-row { display: flex; align-items: center; margin-bottom: 6px; border-radius: 6px; transition: background 0.1s; }
.gantt-mini-row:hover { background: #f8fafc; }
.gantt-mini-row.req-row { cursor: pointer; }
.gantt-row-label { width: 220px; flex-shrink: 0; font-size: 13px; color: #303133; padding: 8px 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: flex; align-items: center; gap: 6px; }
.gantt-row-label.req-label { padding-left: 24px; font-size: 12px; color: #606266; }
.req-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.gantt-row-bar { flex: 1; position: relative; height: 28px; }
.gantt-mini-bar { position: absolute; top: 4px; height: 20px; border-radius: 4px; }
.gantt-mini-bar.iter-bar { background: #409eff; opacity: 0.25; }
.gantt-mini-bar.req-bar { background: #67c23a; opacity: 0.7; }
.gantt-mini-bar.req-bar.s-in_progress { background: #409eff; }
.gantt-mini-bar.req-bar.s-in_review { background: #e6a23c; }
.gantt-mini-bar.req-bar.s-done, .gantt-mini-bar.req-bar.s-closed { background: #909399; }
.gantt-mini-row.section-row { background: #f0f5ff; border-radius: 6px; margin-bottom: 6px; }
.gantt-mini-row.section-row .gantt-row-bar { height: 32px; }
.mini-iter-dot { width: 10px; height: 10px; border-radius: 3px; background: #409eff; flex-shrink: 0; }

/* ── 创建需求弹窗美化 ── */
.create-req-dialog ::v-deep .el-dialog {
  border-radius: 14px;
  overflow: hidden;
}
.create-req-dialog ::v-deep .el-dialog__header {
  padding: 20px 24px 16px;
  border-bottom: 1px solid #f0f0f0;
  background: #fafbfc;
}
.create-req-dialog ::v-deep .el-dialog__body {
  padding: 24px;
}
.create-req-dialog ::v-deep .el-dialog__footer {
  padding: 16px 24px 20px;
  border-top: 1px solid #f0f0f0;
}
.cr-dialog-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 17px;
  font-weight: 700;
  color: #1e293b;
}
.cr-title-icon {
  color: #409eff;
  font-size: 18px;
  font-weight: 700;
}
.cr-sub-badge {
  font-size: 11px;
  font-weight: 600;
  background: #e8f4fd;
  color: #409eff;
  padding: 2px 10px;
  border-radius: 10px;
}
.create-req-body {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.cr-field-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.cr-label {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  display: flex;
  align-items: center;
  gap: 4px;
}
.cr-label i {
  font-size: 14px;
  color: #64748b;
}
.cr-required {
  color: #f56c6c;
  font-weight: 700;
}
.cr-field-row {
  display: flex;
  gap: 16px;
}
.cr-field-half {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.cr-field-triple {
  gap: 12px;
}
.cr-field-third {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.cr-priority-select ::v-deep .el-radio-button__inner {
  padding: 6px 10px;
  font-size: 12px;
  border-radius: 0;
}
.pri-radio-text {
  font-weight: 700;
  font-size: 12px;
}
.pri-radio-p0 { color: #f56c6c; }
.pri-radio-p1 { color: #e6a23c; }
.pri-radio-p2 { color: #409eff; }
.pri-radio-p3 { color: #909399; }
.cr-priority-select ::v-deep .is-active .pri-radio-p0 { color: #fff; }
.cr-priority-select ::v-deep .is-active .pri-radio-p1 { color: #fff; }
.cr-priority-select ::v-deep .is-active .pri-radio-p2 { color: #fff; }
.cr-priority-select ::v-deep .is-active .pri-radio-p3 { color: #fff; }
.cr-parent-display {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f0f5ff;
  border: 1px solid #d0e0f7;
  border-radius: 8px;
  padding: 10px 14px;
}
.cr-parent-title {
  font-size: 13px;
  color: #475569;
  font-weight: 500;
}
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* ── 标题单元格 ── */
.cell-title-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
}
.req-title-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #1e293b;
  font-weight: 500;
  cursor: text;
  transition: color 0.1s;
  padding: 2px 4px;
  border-radius: 4px;
}
.req-title-text:hover {
  color: #409eff;
  background: #f0f5ff;
}
.cell-title-edit {
  width: 100%;
}

/* ── 需求层级缩进 ── */
.tree-indent {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
  position: relative;
}
.tree-corner::before {
  content: '';
  display: inline-block;
  width: 12px;
  height: 12px;
  border-left: 2px solid #d0d5dd;
  border-bottom: 2px solid #d0d5dd;
  border-radius: 0 0 0 4px;
  margin-right: 6px;
  vertical-align: middle;
}

/* ── 项目成员 ── */
.members-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 12px;
}
.member-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
  border-radius: 10px;
  border: 1px solid #ebeef5;
  background: #fff;
  transition: box-shadow 0.15s;
}
.member-card:hover {
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
.member-avatar {
  width: 44px; height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
}
.member-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.member-name {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}
.member-actions {
  display: flex;
  gap: 6px;
  opacity: 0;
  transition: opacity 0.15s;
}
.member-card:hover .member-actions {
  opacity: 1;
}

/* ── Bug 列表增强样式 ── */

/* Bug 严重程度按钮 */
.pbtn-sev-blocker { background: #fef0f0; color: #f56c6c; border-color: #fbc4c4; }
.pbtn-sev-critical { background: #fde8e8; color: #e63946; border-color: #f5b4b8; }
.pbtn-sev-major { background: #fdf6e8; color: #e6a23c; border-color: #faecd8; }
.pbtn-sev-minor { background: #e8f4fd; color: #409eff; border-color: #cce5fa; }
.pbtn-sev-trivial { background: #f0f2f5; color: #909399; border-color: #e2e4e7; }

/* Bug 状态显示 */
.s-bug-open { background: #fef0f0; color: #f56c6c; }
.s-bug-confirmed { background: #fdf6e8; color: #e6a23c; }
.s-bug-in_progress { background: #e8f4fd; color: #409eff; }
.s-bug-fixed { background: #f0fdf4; color: #67c23a; }
.s-bug-verified { background: #f0e6ff; color: #b37feb; }
.s-bug-closed { background: #f0f2f5; color: #909399; }

/* Bug 批量操作栏 */
.batch-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  background: #fef8e8;
  border: 1px solid #fae8b0;
  border-radius: 8px;
  margin-bottom: 10px;
  font-size: 13px;
}
.batch-info {
  font-weight: 600;
  color: #e6a23c;
}

/* Bug 负责人头像堆叠 */
.avatar-stack {
  display: inline-flex;
  gap: -4px;
  cursor: pointer;
}
.mini-avatar {
  width: 22px; height: 22px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  font-size: 10px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #fff;
  margin-left: -4px;
}
.mini-avatar:first-child { margin-left: 0; }

/* Bug 标签迷你列表 */
.label-mini-list {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}
.more-label {
  font-size: 10px;
  color: #909399;
  margin-left: 2px;
}
</style>

<!-- 全局弹窗美化（非 scoped） -->
<style>
.pretty-dialog {
  border-radius: 14px !important;
  overflow: hidden !important;
}
.pretty-dialog .el-dialog__header {
  padding: 20px 24px 16px !important;
  border-bottom: 1px solid #f0f2f5 !important;
  background: #fafbfc !important;
}
.pretty-dialog .el-dialog__title {
  font-size: 16px;
  font-weight: 700;
  color: #1e293b;
}
.pretty-dialog .el-dialog__body {
  padding: 24px !important;
}
.pretty-dialog .el-dialog__footer {
  padding: 16px 24px 20px !important;
  border-top: 1px solid #f0f2f5 !important;
}
.pretty-dialog .el-dialog__headerbtn {
  top: 16px !important;
  right: 20px !important;
}
.pretty-dialog .el-dialog__close {
  font-size: 18px;
  color: #94a3b8;
}
.pretty-dialog .el-dialog__close:hover {
  color: #475569;
}
</style>
