<template>
  <div v-if="embedded" class="cropper-embedded">
    <div class="cropper-shell">
      <div class="cropper-toolbar">
        <el-button-group>
          <el-button size="small" :type="isFreeRatio ? 'primary' : ''" @click="setAspectRatio(null)">自由</el-button>
          <el-button size="small" :type="aspectRatio === 1 ? 'primary' : ''" @click="setAspectRatio(1)">1:1</el-button>
          <el-button size="small" :type="aspectRatio === 4 / 3 ? 'primary' : ''" @click="setAspectRatio(4 / 3)">4:3</el-button>
          <el-button size="small" :type="aspectRatio === 16 / 9 ? 'primary' : ''" @click="setAspectRatio(16 / 9)">16:9</el-button>
        </el-button-group>
        <el-button size="small" @click="rotate(-90)">左旋</el-button>
        <el-button size="small" @click="rotate(90)">右旋</el-button>
        <el-button size="small" @click="resetCrop">重置</el-button>
      </div>

      <div class="cropper-main">
        <div class="cropper-stage">
          <div ref="stage" class="cropper-stage-inner" @mousedown="onStageMouseDown">
            <img
              ref="image"
              :src="imageUrl"
              :style="imageStyle"
              class="cropper-image"
              @load="onImageLoaded"
              draggable="false"
            />
            <div v-if="cropBoxReady" class="crop-box">
              <div class="crop-mask" :style="cropMaskStyles.top"></div>
              <div class="crop-mask" :style="cropMaskStyles.left"></div>
              <div class="crop-mask" :style="cropMaskStyles.right"></div>
              <div class="crop-mask" :style="cropMaskStyles.bottom"></div>
              <div
                class="crop-box-inner"
                :style="cropBoxRectStyle"
                @mousedown.stop="onCropBoxMouseDown('move', $event)"
              >
                <div
                  v-for="handle in handles"
                  :key="handle"
                  class="crop-handle"
                  :class="'handle-' + handle"
                  @mousedown.stop="onCropBoxMouseDown(handle, $event)"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="cropBoxReady" class="cropper-meta">
        <span>裁剪尺寸：{{ Math.round(exportSize.width) }} × {{ Math.round(exportSize.height) }}</span>
        <span>旋转：{{ rotation }}°</span>
      </div>
    </div>
    <div class="cropper-footer">
      <el-button @click="cancel">取消</el-button>
      <el-button type="primary" :loading="saving" @click="saveCrop">保存</el-button>
    </div>
  </div>
  <el-dialog
    v-else
    :visible.sync="dialogVisible"
    title="裁剪图片"
    width="960px"
    top="5vh"
    :close-on-click-modal="false"
    @closed="onDialogClosed"
  >
    <div v-if="dialogVisible" class="cropper-shell">
      <div class="cropper-toolbar">
        <el-button-group>
          <el-button size="small" :type="isFreeRatio ? 'primary' : ''" @click="setAspectRatio(null)">自由</el-button>
          <el-button size="small" :type="aspectRatio === 1 ? 'primary' : ''" @click="setAspectRatio(1)">1:1</el-button>
          <el-button size="small" :type="aspectRatio === 4 / 3 ? 'primary' : ''" @click="setAspectRatio(4 / 3)">4:3</el-button>
          <el-button size="small" :type="aspectRatio === 16 / 9 ? 'primary' : ''" @click="setAspectRatio(16 / 9)">16:9</el-button>
        </el-button-group>
        <el-button size="small" @click="rotate(-90)">左旋</el-button>
        <el-button size="small" @click="rotate(90)">右旋</el-button>
        <el-button size="small" @click="resetCrop">重置</el-button>
      </div>

      <div class="cropper-main">
        <div class="cropper-stage">
          <div ref="stage" class="cropper-stage-inner" @mousedown="onStageMouseDown">
            <img
              ref="image"
              :src="imageUrl"
              :style="imageStyle"
              class="cropper-image"
              @load="onImageLoaded"
              draggable="false"
            />
            <div v-if="cropBoxReady" class="crop-box">
              <div class="crop-mask" :style="cropMaskStyles.top"></div>
              <div class="crop-mask" :style="cropMaskStyles.left"></div>
              <div class="crop-mask" :style="cropMaskStyles.right"></div>
              <div class="crop-mask" :style="cropMaskStyles.bottom"></div>
              <div
                class="crop-box-inner"
                :style="cropBoxRectStyle"
                @mousedown.stop="onCropBoxMouseDown('move', $event)"
              >
                <div
                  v-for="handle in handles"
                  :key="handle"
                  class="crop-handle"
                  :class="'handle-' + handle"
                  @mousedown.stop="onCropBoxMouseDown(handle, $event)"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="cropBoxReady" class="cropper-meta">
        <span>裁剪尺寸：{{ Math.round(exportSize.width) }} × {{ Math.round(exportSize.height) }}</span>
        <span>旋转：{{ rotation }}°</span>
      </div>
    </div>

    <span slot="footer">
      <el-button @click="cancel">取消</el-button>
      <el-button type="primary" :loading="saving" @click="saveCrop">保存</el-button>
    </span>
  </el-dialog>
</template>

<script>
export default {
  name: 'ImageCropper',
  props: {
    visible: { type: Boolean, default: false },
    imageUrl: { type: String, default: '' },
    embedded: { type: Boolean, default: false },
  },
  data() {
    return {
      dialogVisible: false,
      aspectRatio: null,
      saving: false,
      rotation: 0,
      imageMetrics: {
        width: 0,
        height: 0,
        naturalWidth: 0,
        naturalHeight: 0,
        offsetX: 0,
        offsetY: 0,
      },
      cropBox: {
        x: 0,
        y: 0,
        width: 0,
        height: 0,
      },
      activeAction: null,
      dragState: null,
      handles: ['nw', 'ne', 'sw', 'se'],
      boundMouseMove: null,
      boundMouseUp: null,
    }
  },
  computed: {
    isFreeRatio() {
      return this.aspectRatio === null
    },
    cropBoxReady() {
      return this.cropBox.width > 0 && this.cropBox.height > 0
    },
    imageStyle() {
      return {
        transform: `rotate(${this.rotation}deg)`,
      }
    },
    cropBoxRectStyle() {
      return {
        left: `${this.imageMetrics.offsetX + this.cropBox.x}px`,
        top: `${this.imageMetrics.offsetY + this.cropBox.y}px`,
        width: `${this.cropBox.width}px`,
        height: `${this.cropBox.height}px`,
      }
    },
    cropMaskStyles() {
      const offsetX = this.imageMetrics.offsetX || 0
      const offsetY = this.imageMetrics.offsetY || 0
      const imageWidth = this.imageMetrics.width || 0
      const imageHeight = this.imageMetrics.height || 0
      const imageRight = offsetX + imageWidth
      const imageBottom = offsetY + imageHeight
      const cropLeft = offsetX + this.cropBox.x
      const cropTop = offsetY + this.cropBox.y
      const cropRight = cropLeft + this.cropBox.width
      const cropBottom = cropTop + this.cropBox.height
      return {
        top: {
          left: `${offsetX}px`,
          top: `${offsetY}px`,
          width: `${imageWidth}px`,
          height: `${this.cropBox.y}px`,
        },
        left: {
          left: `${offsetX}px`,
          top: `${cropTop}px`,
          width: `${this.cropBox.x}px`,
          height: `${this.cropBox.height}px`,
        },
        right: {
          left: `${cropRight}px`,
          top: `${cropTop}px`,
          width: `${Math.max(0, imageRight - cropRight)}px`,
          height: `${this.cropBox.height}px`,
        },
        bottom: {
          left: `${offsetX}px`,
          top: `${cropBottom}px`,
          width: `${imageWidth}px`,
          height: `${Math.max(0, imageBottom - cropBottom)}px`,
        },
      }
    },
    exportSize() {
      if (!this.imageMetrics.width || !this.cropBoxReady) {
        return { width: 0, height: 0 }
      }
      const scaleX = this.imageMetrics.naturalWidth / this.imageMetrics.width
      const scaleY = this.imageMetrics.naturalHeight / this.imageMetrics.height
      return {
        width: this.cropBox.width * scaleX,
        height: this.cropBox.height * scaleY,
      }
    },
  },
  watch: {
    visible: {
      immediate: true,
      handler(value) {
        this.dialogVisible = value
      },
    },
    dialogVisible(value) {
      if (!value) this.$emit('update:visible', false)
    },
    imageUrl() {
      this.$nextTick(() => {
        const image = this.$refs.image
        if (image && image.complete) this.onImageLoaded()
      })
    },
  },
  mounted() {
    if (this.embedded && this.imageUrl) {
      this.$nextTick(() => {
        const image = this.$refs.image
        if (image && image.complete) this.onImageLoaded()
      })
    }
  },
  methods: {
    onDialogClosed() {
      this.detachDragListeners()
      this.activeAction = null
      this.dragState = null
    },
    onImageLoaded() {
      this.syncImageMetrics()
      this.resetCrop()
    },
    syncImageMetrics() {
      const image = this.$refs.image
      const stage = this.$refs.stage
      if (!image || !stage) return
      const imageRect = image.getBoundingClientRect()
      const stageRect = stage.getBoundingClientRect()
      this.imageMetrics = {
        width: imageRect.width,
        height: imageRect.height,
        naturalWidth: image.naturalWidth,
        naturalHeight: image.naturalHeight,
        offsetX: imageRect.left - stageRect.left,
        offsetY: imageRect.top - stageRect.top,
      }
    },
    resetCrop() {
      const { width, height } = this.imageMetrics
      if (!width || !height) return
      this.cropBox = { x: 0, y: 0, width, height }
    },
    setAspectRatio(value) {
      this.aspectRatio = value
      if (!this.cropBoxReady) return
      if (!value) {
        this.resetCrop()
        return
      }
      const imageWidth = this.imageMetrics.width
      const imageHeight = this.imageMetrics.height
      let nextWidth = imageWidth
      let nextHeight = nextWidth / value
      if (nextHeight > imageHeight) {
        nextHeight = imageHeight
        nextWidth = nextHeight * value
      }
      this.cropBox = {
        x: (imageWidth - nextWidth) / 2,
        y: (imageHeight - nextHeight) / 2,
        width: nextWidth,
        height: nextHeight,
      }
    },
    rotate(delta) {
      this.rotation = (this.rotation + delta + 360) % 360
      this.$nextTick(() => {
        requestAnimationFrame(() => {
          this.syncImageMetrics()
          this.resetCrop()
        })
      })
    },
    onStageMouseDown(event) {
      if (!this.cropBoxReady) return
      const point = this.getPoint(event)
      if (!this.isPointInsideCrop(point.x, point.y)) {
        const width = this.cropBox.width
        const height = this.aspectRatio ? width / this.aspectRatio : this.cropBox.height
        this.cropBox = {
          x: point.x - width / 2,
          y: point.y - height / 2,
          width,
          height,
        }
        this.clampCropBox()
      }
    },
    onCropBoxMouseDown(action, event) {
      if (!this.cropBoxReady) return
      event.preventDefault()
      this.activeAction = action
      this.dragState = {
        startX: event.clientX,
        startY: event.clientY,
        startBox: { ...this.cropBox },
      }
      this.attachDragListeners()
    },
    onGlobalMouseMove(event) {
      if (!this.activeAction || !this.dragState) return
      event.preventDefault()
      const dx = event.clientX - this.dragState.startX
      const dy = event.clientY - this.dragState.startY
      const start = this.dragState.startBox
      const next = { ...start }
      if (this.activeAction === 'move') {
        next.x = start.x + dx
        next.y = start.y + dy
      } else {
        if (this.activeAction.includes('n')) {
          next.y = start.y + dy
          next.height = start.height - dy
        }
        if (this.activeAction.includes('s')) {
          next.height = start.height + dy
        }
        if (this.activeAction.includes('w')) {
          next.x = start.x + dx
          next.width = start.width - dx
        }
        if (this.activeAction.includes('e')) {
          next.width = start.width + dx
        }
        if (this.aspectRatio) {
          if (this.activeAction === 'nw' || this.activeAction === 'se') {
            next.height = next.width / this.aspectRatio
            if (this.activeAction === 'nw') next.y = start.y + (start.height - next.height)
          } else if (this.activeAction === 'ne' || this.activeAction === 'sw') {
            next.height = next.width / this.aspectRatio
            if (this.activeAction === 'ne') next.y = start.y + (start.height - next.height)
            else next.x = start.x + (start.width - next.width)
          }
        }
      }
      this.cropBox = this.normalizedCropBox(next)
    },
    onGlobalMouseUp() {
      this.detachDragListeners()
      this.activeAction = null
      this.dragState = null
    },
    attachDragListeners() {
      this.detachDragListeners()
      if (!this.boundMouseMove) this.boundMouseMove = event => this.onGlobalMouseMove(event)
      if (!this.boundMouseUp) this.boundMouseUp = () => this.onGlobalMouseUp()
      document.addEventListener('mousemove', this.boundMouseMove, true)
      document.addEventListener('mouseup', this.boundMouseUp, true)
    },
    detachDragListeners() {
      if (this.boundMouseMove) document.removeEventListener('mousemove', this.boundMouseMove, true)
      if (this.boundMouseUp) document.removeEventListener('mouseup', this.boundMouseUp, true)
    },
    normalizedCropBox(box) {
      const minSize = 24
      const next = { ...box }
      next.width = Math.max(minSize, next.width)
      next.height = Math.max(minSize, next.height)
      this.cropBox = next
      this.clampCropBox()
      return { ...this.cropBox }
    },
    clampCropBox() {
      const maxWidth = this.imageMetrics.width
      const maxHeight = this.imageMetrics.height
      const next = { ...this.cropBox }
      next.width = Math.min(next.width, maxWidth)
      next.height = Math.min(next.height, maxHeight)
      next.x = Math.max(0, Math.min(next.x, maxWidth - next.width))
      next.y = Math.max(0, Math.min(next.y, maxHeight - next.height))
      this.cropBox = next
    },
    isPointInsideCrop(x, y) {
      return x >= this.cropBox.x && x <= this.cropBox.x + this.cropBox.width
        && y >= this.cropBox.y && y <= this.cropBox.y + this.cropBox.height
    },
    getPoint(event) {
      const image = this.$refs.image
      const rect = image.getBoundingClientRect()
      return {
        x: event.clientX - rect.left,
        y: event.clientY - rect.top,
      }
    },
    getCropSourceRect() {
      const scaleX = this.imageMetrics.naturalWidth / this.imageMetrics.width
      const scaleY = this.imageMetrics.naturalHeight / this.imageMetrics.height
      return {
        sx: this.cropBox.x * scaleX,
        sy: this.cropBox.y * scaleY,
        width: this.cropBox.width * scaleX,
        height: this.cropBox.height * scaleY,
      }
    },
    saveCrop() {
      const image = this.$refs.image
      if (!image || !this.cropBoxReady) return
      this.saving = true
      try {
        const crop = this.getCropSourceRect()
        const canvas = document.createElement('canvas')
        const rotation = ((this.rotation % 360) + 360) % 360
        const swap = rotation === 90 || rotation === 270
        canvas.width = Math.round(swap ? crop.height : crop.width)
        canvas.height = Math.round(swap ? crop.width : crop.height)
        const ctx = canvas.getContext('2d')
        ctx.save()
        ctx.translate(canvas.width / 2, canvas.height / 2)
        ctx.rotate((rotation * Math.PI) / 180)
        ctx.drawImage(
          image,
          crop.sx,
          crop.sy,
          crop.width,
          crop.height,
          -crop.width / 2,
          -crop.height / 2,
          crop.width,
          crop.height
        )
        ctx.restore()
        canvas.toBlob(blob => {
          if (!blob) {
            this.$message.error('裁剪失败')
            this.saving = false
            return
          }
          const reader = new FileReader()
          reader.onload = () => {
            this.$emit('save', {
              blob,
              base64: reader.result,
              width: canvas.width,
              height: canvas.height,
              type: blob.type,
            })
            this.saving = false
            if (!this.embedded) this.dialogVisible = false
          }
          reader.onerror = () => {
            this.$message.error('裁剪失败')
            this.saving = false
          }
          reader.readAsDataURL(blob)
        }, 'image/png')
      } catch (error) {
        this.$message.error(`裁剪失败: ${error.message}`)
        this.saving = false
      }
    },
    cancel() {
      if (!this.embedded) this.dialogVisible = false
      this.$emit('cancel')
    },
  },
}
</script>

<style scoped>
.cropper-embedded {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: #f6f8fc;
}

.cropper-shell {
  display: flex;
  flex-direction: column;
  gap: 14px;
  flex: 1;
  min-height: 0;
}

.cropper-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.cropper-main {
  display: flex;
  flex: 1;
  min-height: 0;
}

.cropper-stage {
  flex: 1;
  min-width: 0;
}

.cropper-stage-inner {
  position: relative;
  width: 100%;
  min-height: 420px;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(255,255,255,.78), rgba(243,247,252,.95)),
    repeating-conic-gradient(#eff4fb 0% 25%, #ffffff 0% 50%) 50%/18px 18px;
  border: 1px solid #dbe6f2;
  border-radius: 14px;
  user-select: none;
}

.cropper-image {
  display: block;
  max-width: 100%;
  max-height: 70vh;
  transform-origin: center center;
}

.crop-box {
  position: absolute;
  inset: 0;
}

.crop-mask {
  position: absolute;
  background: rgba(28, 47, 77, 0.28);
  pointer-events: none;
}

.crop-box-inner {
  position: absolute;
  border: 2px solid #3b82f6;
  box-shadow: 0 0 0 9999px rgba(14, 26, 47, 0.25);
  cursor: move;
}

.crop-box-inner::after {
  content: '';
  position: absolute;
  inset: 0;
  border: 1px dashed rgba(255, 255, 255, 0.82);
}

.crop-handle {
  position: absolute;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid #2563eb;
}

.handle-nw { left: -7px; top: -7px; cursor: nwse-resize; }
.handle-ne { right: -7px; top: -7px; cursor: nesw-resize; }
.handle-sw { left: -7px; bottom: -7px; cursor: nesw-resize; }
.handle-se { right: -7px; bottom: -7px; cursor: nwse-resize; }

.cropper-meta {
  display: flex;
  gap: 18px;
  font-size: 12px;
  color: #61748d;
}

.cropper-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 10px;
}
</style>
