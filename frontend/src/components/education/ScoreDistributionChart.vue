<template>
  <div class="score-chart" :aria-label="ariaLabel">
    <div v-if="!hasData" class="chart-empty">积累正式成绩后显示{{ mode === 'trend' ? '趋势' : '分布' }}</div>
    <div v-else ref="chart" class="chart-canvas"></div>
  </div>
</template>

<script>
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { init, use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'

use([BarChart, LineChart, GridComponent, TooltipComponent, CanvasRenderer])

export default {
  name: 'ScoreDistributionChart',
  props: {
    distribution: { type: Array, default: () => [] },
    trend: { type: Array, default: () => [] },
    mode: { type: String, default: 'distribution' },
  },
  data() {
    return { chart: null, resizeObserver: null }
  },
  computed: {
    rows() { return this.mode === 'trend' ? this.trend : this.distribution },
    hasData() { return this.rows.some(row => this.mode === 'trend' || Number(row.count) > 0) },
    ariaLabel() { return this.mode === 'trend' ? '班级成绩趋势图' : '班级成绩分布图' },
  },
  watch: {
    rows: {
      deep: true,
      handler() { this.$nextTick(this.renderChart) },
    },
    mode() { this.$nextTick(this.renderChart) },
  },
  mounted() {
    this.renderChart()
    if (window.ResizeObserver) {
      this.resizeObserver = new ResizeObserver(() => {
        if (this.chart) this.chart.resize()
      })
      this.resizeObserver.observe(this.$el)
    } else {
      window.addEventListener('resize', this.resize)
    }
  },
  beforeDestroy() {
    if (this.resizeObserver) this.resizeObserver.disconnect()
    window.removeEventListener('resize', this.resize)
    if (this.chart) this.chart.dispose()
  },
  methods: {
    resize() { if (this.chart) this.chart.resize() },
    renderChart() {
      if (!this.hasData || !this.$refs.chart) {
        if (this.chart) {
          this.chart.dispose()
          this.chart = null
        }
        return
      }
      if (!this.chart) this.chart = init(this.$refs.chart)
      const reducedMotion = window.matchMedia
        && window.matchMedia('(prefers-reduced-motion: reduce)').matches
      const isTrend = this.mode === 'trend'
      this.chart.setOption({
        animation: !reducedMotion,
        animationDuration: 420,
        color: isTrend ? ['#c1833d'] : ['#2f8277'],
        tooltip: {
          trigger: 'axis',
          backgroundColor: 'rgba(36, 54, 51, .94)',
          borderWidth: 0,
          textStyle: { color: '#fff', fontSize: 11 },
        },
        grid: { left: 34, right: 12, top: 18, bottom: 30 },
        xAxis: {
          type: 'category',
          data: this.rows.map(row => isTrend ? row.assessment_title : row.label),
          axisLine: { lineStyle: { color: '#dce6e3' } },
          axisTick: { show: false },
          axisLabel: { color: '#788985', fontSize: 9, interval: 0 },
        },
        yAxis: {
          type: 'value',
          min: 0,
          max: isTrend ? 100 : undefined,
          splitLine: { lineStyle: { color: '#edf2f0' } },
          axisLabel: { color: '#9aa6a3', fontSize: 9 },
        },
        series: [{
          type: isTrend ? 'line' : 'bar',
          data: this.rows.map(row => isTrend ? row.average_score : row.count),
          smooth: isTrend,
          symbolSize: 7,
          barMaxWidth: 28,
          lineStyle: { width: 2 },
          areaStyle: isTrend ? { color: 'rgba(193, 131, 61, .08)' } : undefined,
          itemStyle: { borderRadius: isTrend ? 0 : [5, 5, 1, 1] },
        }],
      }, true)
    },
  },
}
</script>

<style scoped>
.score-chart { min-height: 190px; }
.chart-canvas { width: 100%; height: 190px; }
.chart-empty { min-height: 190px; display: grid; place-items: center; color: #98a5a2; font-size: 10px; }
</style>
