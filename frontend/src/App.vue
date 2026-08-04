<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script>
export default {
  name: 'App',
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "Source Han Sans SC", Arial, sans-serif;
}

/* ── 极细滚动条 (Chrome / Edge) ────────────────────────── */
::-webkit-scrollbar {
  width: 2px !important;
  height: 2px !important;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.10);
  border-radius: 1px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.20);
}

/* Firefox 专用：thin 已经是 Firefox 最细的 */
@-moz-document url-prefix() {
  * {
    scrollbar-width: thin;
    scrollbar-color: rgba(0, 0, 0, 0.10) transparent;
  }
}
</style>
