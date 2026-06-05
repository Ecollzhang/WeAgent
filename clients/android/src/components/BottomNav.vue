<template>
  <nav class="bottom-nav" aria-label="主导航">
    <router-link to="/conversations" class="bottom-nav-item">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 5.5A3.5 3.5 0 0 1 7.5 2h9A3.5 3.5 0 0 1 20 5.5v7A3.5 3.5 0 0 1 16.5 16H12l-4.4 3.3A1 1 0 0 1 6 18.5V16A3.5 3.5 0 0 1 4 12.5v-7Z" />
      </svg>
      <span>会话</span>
    </router-link>
    <router-link to="/agents" class="bottom-nav-item">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 2a4 4 0 0 1 4 4v1h1.5A2.5 2.5 0 0 1 20 9.5v6A4.5 4.5 0 0 1 15.5 20h-7A4.5 4.5 0 0 1 4 15.5v-6A2.5 2.5 0 0 1 6.5 7H8V6a4 4 0 0 1 4-4Zm-2.5 9.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3Zm5 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3Z" />
      </svg>
      <span>Agent</span>
    </router-link>
    <router-link to="/settings" class="bottom-nav-item">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm0 2c-4.4 0-8 2.4-8 5.4A1.6 1.6 0 0 0 5.6 21h12.8a1.6 1.6 0 0 0 1.6-1.6C20 16.4 16.4 14 12 14Z" />
      </svg>
      <span>我的</span>
    </router-link>
  </nav>
</template>

<script>
export default {
  name: 'BottomNav'
}
</script>
