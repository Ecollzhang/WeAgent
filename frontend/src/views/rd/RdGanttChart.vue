<template>
  <div class="gantt-page">
    <AppSidebar />
    <main class="gantt-content">
      <header class="gantt-topbar">
        <div class="topbar-left">
          <el-button type="text" icon="el-icon-arrow-left" @click="goBack">返回项目</el-button>
          <h2 class="page-title">甘特图</h2>
        </div>
        <div class="topbar-right">
          <div class="legend-inline">
            <span class="legend-dot iter"></span> 迭代
            <span class="legend-dot req"></span> 需求
            <span class="legend-dot today-dot"></span> 今天
          </div>
          <el-radio-group v-model="viewMode" size="small">
            <el-radio-button label="month">月</el-radio-button>
            <el-radio-button label="week">周</el-radio-button>
            <el-radio-button label="day">日</el-radio-button>
          </el-radio-group>
          <el-button size="small" icon="el-icon-refresh" @click="scrollToToday">今天</el-button>
        </div>
      </header>

      <div class="gantt-chart">
        <!-- 表头 -->
        <div class="gantt-header">
          <div class="gantt-label-col">任务</div>
          <div class="gantt-timeline-col" ref="timelineHeader">
            <div class="timeline-scroll-inner" :style="{ width: totalWidth + 'px' }">
              <div
                v-for="(col, idx) in timelineCols"
                :key="'h-' + idx"
                class="timeline-header-cell"
                :class="{ 'is-today': col.isToday, 'is-weekend': col.isWeekend }"
                :style="col.style"
              >
                {{ col.label }}
              </div>
            </div>
          </div>
        </div>

        <!-- 主体 -->
        <div class="gantt-body" ref="ganttBody" @scroll="syncScroll">
          <div class="gantt-body-inner" :style="{ width: (280 + totalWidth) + 'px' }">
            <!-- 迭代行 -->
            <template v-for="iter in iterations">
              <div :key="'i-' + iter.id" class="gantt-row iteration-row">
                <div class="gantt-label-col">
                  <div class="row-label">
                    <span class="iter-dot"></span>
                    <span class="iter-name">{{ iter.name }}</span>
                    <el-tag size="mini" effect="plain" :type="iterStatusType(iter.status)">{{ iterStatusLabel(iter.status) }}</el-tag>
                  </div>
                </div>
                <div class="gantt-timeline-col">
                  <div class="timeline-bar-area" :style="{ width: totalWidth + 'px' }">
                    <div
                      v-if="iter.start_date && iter.end_date"
                      class="gantt-bar iteration-bar"
                      :style="getBarStyle(iter.start_date, iter.end_date)"
                    >
                      <span class="bar-label">{{ iter.name.substring(0, 16) }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 该迭代下的需求 -->
              <div
                v-for="req in getIterationReqs(iter.id)"
                :key="'r-' + req.id"
                class="gantt-row requirement-row"
                @click="goToRequirement(req.id)"
              >
                <div class="gantt-label-col">
                  <div class="row-label req-label">
                    <span class="req-dot" :class="'pri-' + req.priority"></span>
                    <span class="req-title">{{ req.title }}</span>
                    <span class="req-sp">{{ req.story_points }} pts</span>
                  </div>
                </div>
                <div class="gantt-timeline-col">
                  <div class="timeline-bar-area" :style="{ width: totalWidth + 'px' }">
                    <div
                      v-if="req.start_date && req.due_date"
                      class="gantt-bar requirement-bar"
                      :class="'status-' + req.status"
                      :style="getBarStyle(req.start_date, req.due_date)"
                    >
                      <span class="bar-label">{{ req.title.substring(0, 14) }}</span>
                    </div>
                    <span v-else class="no-bar-hint">未设置日期</span>
                  </div>
                </div>
              </div>
            </template>

            <!-- 未分配迭代的需求 -->
            <template v-if="unassignedReqs.length > 0">
              <div class="gantt-row section-row">
                <div class="gantt-label-col">
                  <span class="section-label">未分配迭代（{{ unassignedReqs.length }}）</span>
                </div>
                <div class="gantt-timeline-col">
                  <div class="timeline-bar-area" :style="{ width: totalWidth + 'px' }"></div>
                </div>
              </div>
              <div
                v-for="req in unassignedReqs"
                :key="'u-' + req.id"
                class="gantt-row requirement-row"
                @click="goToRequirement(req.id)"
              >
                <div class="gantt-label-col">
                  <div class="row-label req-label">
                    <span class="req-dot" :class="'pri-' + req.priority"></span>
                    <span class="req-title">{{ req.title }}</span>
                    <span class="req-sp">{{ req.story_points }} pts</span>
                  </div>
                </div>
                <div class="gantt-timeline-col">
                  <div class="timeline-bar-area" :style="{ width: totalWidth + 'px' }">
                    <div
                      v-if="req.start_date && req.due_date"
                      class="gantt-bar requirement-bar"
                      :class="'status-' + req.status"
                      :style="getBarStyle(req.start_date, req.due_date)"
                    >
                      <span class="bar-label">{{ req.title.substring(0, 14) }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </template>

            <!-- 未分配日期的需求 -->
            <template v-if="noDateReqs.length > 0">
              <div class="gantt-row section-row">
                <div class="gantt-label-col">
                  <span class="section-label">未设置日期（{{ noDateReqs.length }}）</span>
                </div>
                <div class="gantt-timeline-col">
                  <div class="timeline-bar-area" :style="{ width: totalWidth + 'px' }"></div>
                </div>
              </div>
              <div
                v-for="req in noDateReqs"
                :key="'n-' + req.id"
                class="gantt-row requirement-row no-date"
                @click="goToRequirement(req.id)"
              >
                <div class="gantt-label-col">
                  <div class="row-label req-label">
                    <span class="req-dot" :class="'pri-' + req.priority"></span>
                    <span class="req-title">{{ req.title }}</span>
                    <el-tag size="mini" type="info" effect="plain">未设日期</el-tag>
                  </div>
                </div>
                <div class="gantt-timeline-col">
                  <div class="timeline-bar-area" :style="{ width: totalWidth + 'px' }"></div>
                </div>
              </div>
            </template>

            <!-- 空状态 -->
            <div v-if="iterations.length === 0 && allReqs.length === 0" class="gantt-empty">
              <i class="el-icon-date"></i>
              <p>暂无数据，请先创建迭代和需求并设置日期</p>
            </div>

            <!-- 今日竖线 -->
            <div class="today-line" v-if="totalDays > 0" :style="{ left: (280 + todayOffset) + 'px' }"></div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script>
import AppSidebar from '@/components/Sidebar/index.vue'
import { getGanttData } from '@/api/rd'

export default {
  name: 'RdGanttChart',
  components: { AppSidebar },
  data() {
    return {
      viewMode: 'month',
      iterations: [],
      allReqs: [],
      loading: false,
    }
  },
  computed: {
    projectId() { return this.$route.params.id },
    iterationReqsMap() {
      const map = {}
      this.allReqs.forEach(r => {
        if (r.iteration_id) {
          if (!map[r.iteration_id]) map[r.iteration_id] = []
          map[r.iteration_id].push(r)
        }
      })
      return map
    },
    unassignedReqs() {
      return this.allReqs.filter(r => !r.iteration_id && r.start_date && r.due_date)
    },
    noDateReqs() {
      return this.allReqs.filter(r => !r.start_date || !r.due_date)
    },
    allDates() {
      const dates = []
      this.iterations.forEach(i => {
        if (i.start_date) dates.push(i.start_date)
        if (i.end_date) dates.push(i.end_date)
      })
      this.allReqs.forEach(r => {
        if (r.start_date) dates.push(r.start_date)
        if (r.due_date) dates.push(r.due_date)
      })
      if (dates.length === 0) {
        const now = new Date()
        dates.push(now.toISOString().substring(0, 10))
        dates.push(new Date(now.getTime() + 30 * 86400000).toISOString().substring(0, 10))
      }
      return [...new Set(dates)].sort()
    },
    dateRangeStart() { return this.allDates[0] },
    dateRangeEnd() { return this.allDates[this.allDates.length - 1] },
    totalDays() {
      const s = new Date(this.dateRangeStart)
      const e = new Date(this.dateRangeEnd)
      return Math.max(Math.ceil((e - s) / 86400000) + 1, 1)
    },
    dayWidth() {
      if (this.viewMode === 'day') return 36
      if (this.viewMode === 'week') return 24
      return 20
    },
    totalWidth() {
      return this.totalDays * this.dayWidth
    },
    todayOffset() {
      const today = new Date()
      today.setHours(0, 0, 0, 0)
      const start = new Date(this.dateRangeStart)
      const days = Math.floor((today - start) / 86400000)
      if (days < 0 || days >= this.totalDays) return -999
      return days * this.dayWidth + this.dayWidth / 2
    },
    timelineCols() {
      const cols = []
      const start = new Date(this.dateRangeStart)
      const today = new Date()
      today.setHours(0, 0, 0, 0)

      if (this.viewMode === 'day') {
        for (let i = 0; i < this.totalDays; i++) {
          const d = new Date(start.getTime() + i * 86400000)
          const dateStr = d.toISOString().substring(0, 10)
          const isToday = dateStr === today.toISOString().substring(0, 10)
          cols.push({
            label: d.getMonth() + 1 + '/' + d.getDate(),
            isToday,
            isWeekend: d.getDay() === 0 || d.getDay() === 6,
            style: { width: this.dayWidth + 'px' },
          })
        }
      } else if (this.viewMode === 'week') {
        // Group by week
        let weekStart = null
        let weekDays = 0
        for (let i = 0; i < this.totalDays; i++) {
          const d = new Date(start.getTime() + i * 86400000)
          if (d.getDay() === 1 || weekStart === null) {
            if (weekStart !== null && weekDays > 0) {
              cols[cols.length - 1].style = { width: (weekDays * this.dayWidth) + 'px' }
            }
            weekStart = d
            weekDays = 0
            cols.push({
              label: weekStart.getMonth() + 1 + '/' + weekStart.getDate(),
              isToday: false,
              isWeekend: false,
              style: {},
            })
          }
          weekDays++
          const dateStr = d.toISOString().substring(0, 10)
          if (dateStr === today.toISOString().substring(0, 10)) cols[cols.length - 1].isToday = true
        }
        if (cols.length > 0 && weekDays > 0) {
          cols[cols.length - 1].style = { width: (weekDays * this.dayWidth) + 'px' }
        }
      } else {
        // Month view - group by month
        const months = []
        for (let i = 0; i < this.totalDays; i++) {
          const d = new Date(start.getTime() + i * 86400000)
          const mk = d.getFullYear() + '-' + (d.getMonth() + 1)
          if (!months.find(m => m.key === mk)) {
            months.push({ key: mk, days: 0 })
          }
          months.find(m => m.key === mk).days++
        }
        months.forEach(m => {
          const [y, mo] = m.key.split('-')
          cols.push({
            label: y + '年' + mo + '月',
            isToday: false,
            isWeekend: false,
            style: { width: (m.days * this.dayWidth) + 'px' },
          })
        })
      }
      return cols
    },
  },
  created() {
    this.loadData()
  },
  watch: {
    '$route.params.id'() {
      this.loadData()
    },
  },
  methods: {
    async loadData() {
      if (!this.projectId) return
      this.loading = true
      try {
        const res = await getGanttData(this.projectId)
        if (res.code === 200) {
          this.iterations = (res.data.iterations || [])
            .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
          this.allReqs = res.data.requirements || []
        }
      } catch (e) {
        console.error('加载甘特图数据失败', e)
      } finally {
        this.loading = false
      }
    },
    goBack() {
      this.$router.push(`/projects/${this.projectId}`).catch(() => {})
    },
    goToRequirement(reqId) {
      this.$router.push(`/projects/${this.projectId}/requirements/${reqId}`).catch(() => {})
    },
    getIterationReqs(iterId) {
      return this.iterationReqsMap[iterId] || []
    },
    iterStatusType(s) {
      return ({ planning: 'info', active: '', completed: 'success', cancelled: 'danger' })[s] || 'info'
    },
    iterStatusLabel(s) {
      return ({ planning: '规划中', active: '进行中', completed: '已完成', cancelled: '已取消' })[s] || s
    },
    getBarStyle(startDate, endDate) {
      const rangeStart = new Date(this.dateRangeStart)
      const s = new Date(startDate)
      const e = new Date(endDate)
      const left = Math.floor((s - rangeStart) / 86400000) * this.dayWidth
      const width = (Math.floor((e - s) / 86400000) + 1) * this.dayWidth
      return {
        left: left + 'px',
        width: Math.max(width, 3) + 'px',
      }
    },
    scrollToToday() {
      const container = this.$refs.ganttBody
      if (container && this.todayOffset > 0) {
        container.scrollLeft = Math.max(0, this.todayOffset - 300)
      }
    },
    syncScroll(e) {
      const body = this.$refs.ganttBody
      const header = this.$refs.timelineHeader
      if (!body || !header) return
      header.scrollLeft = body.scrollLeft
    },
  },
}
</script>

<style scoped>
.gantt-page {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  gap: 12px;
  padding: 12px;
  background: linear-gradient(135deg, #e8f0ff 0%, #f0f5ff 50%, #f5f7fa 100%);
  overflow: hidden;
}
.gantt-content {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  overflow: hidden;
}

/* topbar */
.gantt-topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 22px;
  border-bottom: 1px solid #f0f0f0;
  background: #fafbfc;
  flex-shrink: 0;
  gap: 16px;
}
.topbar-left { display: flex; align-items: center; gap: 12px; }
.page-title { margin: 0; font-size: 18px; font-weight: 700; color: #1e293b; }
.topbar-right { display: flex; align-items: center; gap: 12px; }

.legend-inline { display: flex; align-items: center; gap: 4px; font-size: 12px; color: #64748b; }
.legend-dot {
  display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin: 0 2px 0 8px;
}
.legend-dot.iter { background: #409eff; }
.legend-dot.req { background: #67c23a; }
.legend-dot.today-dot { background: #f56c6c; border-radius: 50%; width: 8px; height: 8px; }

/* chart */
.gantt-chart {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
  min-height: 0;
}

/* header */
.gantt-header {
  display: flex;
  flex-shrink: 0;
  border-bottom: 2px solid #e2e8f0;
  background: #f8fafc;
  z-index: 3;
}
.gantt-label-col {
  width: 280px;
  flex-shrink: 0;
  padding: 10px 16px;
  border-right: 1px solid #e2e8f0;
  font-size: 13px;
  font-weight: 700;
  color: #475569;
  display: flex;
  align-items: center;
}
.gantt-timeline-col {
  flex: 1;
  overflow-x: hidden;
}
.timeline-scroll-inner { display: flex; }
.timeline-header-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #64748b;
  font-weight: 600;
  border-right: 1px solid #ebeef5;
  padding: 10px 4px;
  flex-shrink: 0;
  text-align: center;
}
.timeline-header-cell.is-today {
  background: #fef0f0;
  color: #f56c6c;
  font-weight: 700;
}
.timeline-header-cell.is-weekend {
  background: #fafafa;
  color: #c0c4cc;
}

/* body */
.gantt-body {
  flex: 1;
  overflow: auto;
  position: relative;
}
.gantt-body-inner { position: relative; min-height: 100%; }

.gantt-row {
  display: flex;
  border-bottom: 1px solid #f0f2f5;
  transition: background 0.1s;
}
.gantt-row:hover { background: #f8fafc; }

.iteration-row {
  background: #fafbfc;
}
.section-row {
  background: #f0f5ff;
  position: sticky;
  top: 0;
  z-index: 2;
}
.section-row .section-label {
  font-size: 13px; font-weight: 700; color: #409eff;
  text-transform: uppercase; letter-spacing: 0.5px;
}
.requirement-row { cursor: pointer; }
.requirement-row.no-date { opacity: 0.45; }

.row-label {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  overflow: hidden;
  padding: 8px 16px;
  min-height: 40px;
}
.iter-dot {
  width: 10px; height: 10px; border-radius: 3px;
  background: #409eff; flex-shrink: 0;
}
.iter-name { font-size: 13px; font-weight: 600; color: #1e293b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.req-label { padding-left: 20px; }
.req-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
}
.req-dot.pri-p0 { background: #f56c6c; }
.req-dot.pri-p1 { background: #e6a23c; }
.req-dot.pri-p2 { background: #409eff; }
.req-dot.pri-p3 { background: #909399; }
.req-title { font-size: 13px; color: #475569; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.req-sp { font-size: 11px; color: #94a3b8; margin-left: auto; flex-shrink: 0; }

.timeline-bar-area {
  position: relative;
  min-height: 40px;
  display: flex;
  align-items: center;
}

/* bars */
.gantt-bar {
  position: absolute;
  top: 7px;
  bottom: 7px;
  border-radius: 5px;
  display: flex;
  align-items: center;
  padding: 0 10px;
  cursor: pointer;
  transition: filter 0.15s, box-shadow 0.15s;
  overflow: hidden;
  min-width: 4px;
  z-index: 1;
}
.gantt-bar:hover {
  filter: brightness(0.9);
  box-shadow: 0 2px 10px rgba(0,0,0,0.18);
  z-index: 3;
}
.bar-label {
  font-size: 11px; font-weight: 600; color: #fff;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.iteration-bar {
  background: linear-gradient(135deg, #409eff, #66b1ff);
  opacity: 0.2;
  border: 1px solid rgba(64, 158, 255, 0.4);
}
.iteration-bar .bar-label { color: #1e293b; font-weight: 500; }

.requirement-bar {
  background: linear-gradient(135deg, #67c23a, #85ce61);
  top: 9px;
  bottom: 9px;
}
.requirement-bar.status-in_progress { background: linear-gradient(135deg, #409eff, #66b1ff); }
.requirement-bar.status-in_review { background: linear-gradient(135deg, #e6a23c, #ebb563); }
.requirement-bar.status-done, .requirement-bar.status-closed { background: linear-gradient(135deg, #909399, #b4b8bf); }
.requirement-bar.status-todo { background: linear-gradient(135deg, #22c55e, #4ade80); }
.requirement-bar.status-backlog { background: linear-gradient(135deg, #c0c4cc, #dcdfe6); }

.no-bar-hint {
  font-size: 11px;
  color: #c0c4cc;
  padding-left: 8px;
}

/* today line */
.today-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #f56c6c;
  z-index: 4;
  opacity: 0.6;
  pointer-events: none;
}

/* empty */
.gantt-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 16px;
  color: #c0c4cc;
}
.gantt-empty i { font-size: 48px; margin-bottom: 16px; }
.gantt-empty p { font-size: 14px; margin: 0; }
</style>
