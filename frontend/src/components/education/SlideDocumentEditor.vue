<template>
  <div class="slide-editor" data-testid="slide-document-editor">
    <aside class="slide-list">
      <div class="document-title">
        <span>课件标题</span>
        <el-input v-model="draft.title" size="small" @input="markChanged" />
      </div>
      <button
        v-for="(slide, index) in draft.slides"
        :key="slide.id || index"
        type="button"
        :class="{ active: selectedIndex === index }"
        @click="selectedIndex = index"
      >
        <span>{{ String(index + 1).padStart(2, '0') }}</span>
        <b>{{ slide.title || `第 ${index + 1} 页` }}</b>
      </button>
    </aside>
    <section v-if="selectedSlide" class="slide-stage">
      <header>
        <span>SLIDE {{ String(selectedIndex + 1).padStart(2, '0') }}</span>
        <el-input v-model="selectedSlide.title" placeholder="页面标题" @input="markChanged" />
      </header>
      <div class="block-grid">
        <article v-for="(block, index) in selectedSlide.blocks" :key="index">
          <div class="block-heading">
            <el-tag size="mini" effect="plain">{{ block.type || 'text' }}</el-tag>
            <small v-if="!block._editable">复杂组件保留结构，可在导出文件中继续排版</small>
          </div>
          <el-input
            v-if="block._editable"
            v-model="block._editorValue"
            type="textarea"
            :rows="block._arrayContent ? 4 : 3"
            resize="vertical"
            @input="markChanged"
          />
          <div v-else class="structured-preview">{{ block._preview }}</div>
        </article>
      </div>
      <div class="speaker-notes">
        <label>讲者备注</label>
        <el-input
          v-model="selectedSlide.speaker_notes"
          type="textarea"
          :rows="3"
          placeholder="课堂提示、时间分配和讲解要点"
          @input="markChanged"
        />
      </div>
    </section>
  </div>
</template>

<script>
const { objectText } = require('../../utils/slideDocument')

function editorDraft(value) {
  const draft = JSON.parse(JSON.stringify(value || { title: '', theme: {}, slides: [] }))
  draft.slides = Array.isArray(draft.slides) ? draft.slides : []
  draft.slides.forEach((slide) => {
    slide.blocks = Array.isArray(slide.blocks) ? slide.blocks : []
    slide.blocks.forEach((block) => {
      const content = block.content
      const arrayContent = Array.isArray(content) && content.every(item => typeof item === 'string')
      block._editable = typeof content === 'string' || arrayContent
      block._arrayContent = arrayContent
      block._editorValue = arrayContent ? content.join('\n') : (typeof content === 'string' ? content : '')
      block._preview = objectText(content)
    })
  })
  return draft
}

export default {
  name: 'SlideDocumentEditor',
  props: { value: { type: Object, required: true } },
  data() {
    return { draft: editorDraft(this.value), selectedIndex: 0, changed: false }
  },
  computed: {
    selectedSlide() { return this.draft.slides[this.selectedIndex] || null },
  },
  methods: {
    markChanged() { this.changed = true },
    exportDocument() {
      const source = JSON.parse(JSON.stringify(this.draft))
      source.slides.forEach((slide) => {
        slide.blocks.forEach((block) => {
          if (block._editable) {
            block.content = block._arrayContent
              ? block._editorValue.split('\n').map(item => item.trim()).filter(Boolean)
              : block._editorValue
          }
          delete block._editable
          delete block._arrayContent
          delete block._editorValue
          delete block._preview
        })
      })
      return source
    },
  },
}
</script>

<style scoped>
.slide-editor { display: grid; grid-template-columns: 250px minmax(0, 1fr); min-height: 620px; background: #eef4f2; border-radius: 14px; overflow: hidden; }
.slide-list { padding: 18px 14px; border-right: 1px solid #d4e3df; background: #f8fbfa; overflow-y: auto; }
.document-title { margin-bottom: 16px; }
.document-title span { display: block; margin-bottom: 7px; color: #607570; font-size: 12px; font-weight: 700; }
.slide-list button { display: grid; grid-template-columns: 34px 1fr; width: 100%; margin: 7px 0; padding: 12px; border: 1px solid transparent; border-radius: 10px; color: #4b625d; background: transparent; text-align: left; cursor: pointer; transition: .2s ease; }
.slide-list button:hover { transform: translateX(2px); background: #edf5f2; }
.slide-list button.active { border-color: #b9d6cf; color: #176d63; background: #e7f2ef; box-shadow: 0 8px 18px rgba(37, 108, 97, .08); }
.slide-list button span { color: #76a39b; font-size: 11px; font-weight: 800; letter-spacing: .08em; }
.slide-list button b { font-size: 13px; line-height: 1.5; }
.slide-stage { margin: 24px; padding: 30px 34px; border: 1px solid #d8e5e2; border-radius: 16px; background: #fff; box-shadow: 0 18px 45px rgba(40, 82, 75, .08); overflow-y: auto; }
.slide-stage header { display: grid; grid-template-columns: 92px 1fr; align-items: center; gap: 14px; margin-bottom: 22px; }
.slide-stage header span { color: #2c7c72; font-size: 10px; font-weight: 900; letter-spacing: .12em; }
.block-grid { display: grid; gap: 12px; }
.block-grid article { padding: 14px 16px; border: 1px solid #e1eae8; border-radius: 11px; background: #fbfcfc; }
.block-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 9px; }
.block-heading small { color: #8a9996; font-size: 11px; }
.structured-preview { max-height: 110px; overflow: auto; color: #4e625e; font-size: 13px; line-height: 1.65; white-space: pre-wrap; }
.speaker-notes { margin-top: 20px; padding-top: 18px; border-top: 1px dashed #cbdad6; }
.speaker-notes label { display: block; margin-bottom: 8px; color: #56706a; font-size: 12px; font-weight: 700; }
@media (max-width: 900px) { .slide-editor { grid-template-columns: 1fr; } .slide-list { display: flex; gap: 8px; border-right: 0; border-bottom: 1px solid #d4e3df; overflow-x: auto; } .document-title { min-width: 220px; } .slide-list button { min-width: 180px; } .slide-stage { margin: 12px; padding: 22px; } }
@media (prefers-reduced-motion: reduce) { .slide-list button { transition: none; } }
</style>
