<template>
  <div class="status-flow-bar">
    <div class="flow-steps">
      <template v-for="(step, index) in statusFlow">
        <!-- Step Circle -->
        <div
          :key="'step-' + index"
          class="flow-step"
          :class="stepClass(step)"
          @click="handleStepClick(step)"
        >
          <div class="step-circle" :class="stepClass(step)">
            <i v-if="isCompleted(step)" class="el-icon-check step-icon"></i>
            <span v-else class="step-index">{{ index + 1 }}</span>
          </div>
          <span class="step-label" :class="stepClass(step)">
            {{ getStatusLabel(step) }}
          </span>
        </div>

        <!-- Arrow Between Steps -->
        <div
          v-if="index < statusFlow.length - 1"
          :key="'arrow-' + index"
          class="flow-arrow"
          :class="{ 'is-completed': isCompleted(statusFlow[index + 1]) || isCurrent(statusFlow[index]) }"
        >
          <i class="el-icon-right"></i>
        </div>
      </template>
    </div>
  </div>
</template>

<script>
export default {
  name: 'StatusFlowBar',
  props: {
    status: {
      type: String,
      default: '',
    },
    statusFlow: {
      type: Array,
      default: () => [],
    },
    statusLabels: {
      type: Object,
      default: () => ({}),
    },
  },
  methods: {
    getStatusLabel(status) {
      return this.statusLabels[status] || status || '未知'
    },
    isCompleted(step) {
      const currentIdx = this.statusFlow.indexOf(this.status)
      const stepIdx = this.statusFlow.indexOf(step)
      if (currentIdx === -1) return false
      return stepIdx < currentIdx
    },
    isCurrent(step) {
      return step === this.status
    },
    isFuture(step) {
      const currentIdx = this.statusFlow.indexOf(this.status)
      const stepIdx = this.statusFlow.indexOf(step)
      if (currentIdx === -1) return false
      return stepIdx > currentIdx
    },
    stepClass(step) {
      return {
        'is-completed': this.isCompleted(step),
        'is-current': this.isCurrent(step),
        'is-future': this.isFuture(step),
        'is-clickable': this.isCurrent(step) || this.isFuture(step),
      }
    },
    handleStepClick(step) {
      if (this.isFuture(step) || this.isCurrent(step)) {
        this.$emit('change', step)
      }
    },
  },
}
</script>

<style scoped>
.status-flow-bar {
  width: 100%;
  padding: 16px 0;
}

.flow-steps {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 0;
}

.flow-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: default;
}

.flow-step.is-clickable {
  cursor: pointer;
}

.step-circle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 2px solid #dcdfe6;
  background: #fff;
  transition: all 0.3s ease;
  font-weight: 600;
  font-size: 14px;
  color: #c0c4cc;
}

.step-circle.is-current {
  border-color: #4080ff;
  background: #4080ff;
  color: #fff;
  box-shadow: 0 2px 8px rgba(64, 128, 255, 0.35);
}

.step-circle.is-completed {
  border-color: #67c23a;
  background: #67c23a;
  color: #fff;
}

.step-circle.is-future {
  border-color: #e4e7ed;
  background: #f5f7fa;
  color: #c0c4cc;
}

.flow-step.is-clickable:hover .step-circle.is-current {
  transform: scale(1.1);
  box-shadow: 0 4px 12px rgba(64, 128, 255, 0.45);
}

.flow-step.is-clickable:hover .step-circle.is-future {
  border-color: #4080ff;
  color: #4080ff;
  background: #f0f5ff;
}

.step-icon {
  font-size: 16px;
  font-weight: bold;
}

.step-index {
  font-size: 13px;
}

.step-label {
  font-size: 12px;
  white-space: nowrap;
  transition: color 0.3s;
}

.step-label.is-current {
  color: #4080ff;
  font-weight: 600;
}

.step-label.is-completed {
  color: #67c23a;
}

.step-label.is-future {
  color: #c0c4cc;
}

.flow-arrow {
  display: flex;
  align-items: center;
  padding: 0 8px;
  padding-bottom: 28px;
  color: #dcdfe6;
  font-size: 14px;
  transition: color 0.3s;
}

.flow-arrow.is-completed {
  color: #67c23a;
}

/* Mobile responsive */
@media (max-width: 768px) {
  .flow-steps {
    justify-content: flex-start;
    flex-wrap: nowrap;
    overflow-x: auto;
    padding: 0 8px;
  }

  .flow-steps::-webkit-scrollbar {
    display: none;
  }

  .step-circle {
    width: 30px;
    height: 30px;
  }

  .step-label {
    font-size: 11px;
  }

  .flow-arrow {
    padding: 0 4px;
    padding-bottom: 24px;
    font-size: 12px;
  }
}
</style>
