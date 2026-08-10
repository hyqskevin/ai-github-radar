<script setup lang="ts">
// layouts/default.vue — ai-github-radar 全局布局
// AppBar + SideNav + Content
// 见 docs/ui-design.md
//
// 设计参照 Nuxt UI 4 dashboard pattern
// - AppBar: 56px 高, sticky top
// - SideNav: 240px 宽, sticky, 跟内容区同高
// - Content: max-w-7xl 居中

const navItems = [
  { label: '推荐', icon: 'i-lucide-sparkles', to: '/' },
  { label: '推荐列表', icon: 'i-lucide-list', to: '/recommendations' },
  { label: '关键字', icon: 'i-lucide-tag', to: '/keywords' },
  { label: '我的 Star', icon: 'i-lucide-star', to: '/stars' },
  { label: '扫描', icon: 'i-lucide-radar', to: '/scan' },
  { label: '设置', icon: 'i-lucide-settings', to: '/settings' }
]
</script>

<template>
  <div class="h-screen flex flex-col bg-default text-default">
    <!-- AppBar -->
    <header class="h-14 shrink-0 border-b border-default bg-default/95 backdrop-blur flex items-center px-6 gap-6 sticky top-0 z-10">
      <NuxtLink to="/" class="flex items-center gap-2 font-mono font-bold text-base tracking-tight">
        <UIcon name="i-lucide-radar" class="size-5 text-tertiary-400" />
        <span>ai-github-radar</span>
      </NuxtLink>
      <div class="flex-1" />
      <UColorModeButton />
      <UButton
        to="/settings"
        variant="ghost"
        color="neutral"
        icon="i-lucide-settings"
        size="sm"
        aria-label="设置"
      />
    </header>

    <!-- Body: SideNav + Content -->
    <div class="flex flex-1 min-h-0">
      <!-- SideNav -->
      <aside class="w-60 shrink-0 border-r border-default bg-elevated/50 overflow-y-auto">
        <UVerticalNavigation :items="navItems" class="py-4 px-2" />
      </aside>

      <!-- Content -->
      <main class="flex-1 overflow-y-auto">
        <div class="max-w-7xl mx-auto px-8 py-8">
          <slot />
        </div>
      </main>
    </div>
  </div>
</template>