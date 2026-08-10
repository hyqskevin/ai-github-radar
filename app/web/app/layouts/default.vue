<script setup lang="ts">
// layouts/default.vue — 全局布局
// AppBar + SideNav + Content
// 见 docs/ui-design.md
const route = useRoute()

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
  <div class="min-h-screen flex flex-col">
    <!-- AppBar -->
    <header class="h-14 border-b border-default bg-neutral-900 flex items-center px-4 gap-4">
      <NuxtLink to="/" class="font-mono font-bold tracking-tight">
        ai-github-radar
      </NuxtLink>
      <div class="flex-1" />
      <UColorModeButton />
      <UButton to="/settings" variant="ghost" icon="i-lucide-settings" size="sm" />
    </header>

    <div class="flex flex-1">
      <!-- SideNav -->
      <nav class="w-60 border-r border-default bg-neutral-900/50 p-4">
        <UNavigationMenu :items="navItems" orientation="vertical" />
      </nav>

      <!-- Content -->
      <main class="flex-1 overflow-auto">
        <div class="max-w-7xl mx-auto p-6">
          <slot />
        </div>
      </main>
    </div>
  </div>
</template>
