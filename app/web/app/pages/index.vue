<script setup lang="ts">
// pages/index.vue — Dashboard（默认页）
// 见 docs/ui-design.md §Dashboard
//
// 阶段一：占位页（T106 实现）
// 当前显示：项目名 + 欢迎语 + stat 占位

useHead({ title: 'Dashboard · ai-github-radar' })

const stats = [
  { label: '今日推荐', value: '—', hint: '等待首次扫描', icon: 'i-lucide-sparkles' },
  { label: '已 Star', value: '—', hint: '运行 init 后统计', icon: 'i-lucide-star' },
  { label: '关键字', value: '—', hint: 'auto + manual 合计', icon: 'i-lucide-tag' }
]
</script>

<template>
  <div class="space-y-8">
    <!-- Header -->
    <header class="space-y-2">
      <h1 class="text-2xl font-bold tracking-tight">Dashboard</h1>
      <p class="text-sm text-muted">
        AI 驱动的 GitHub 项目发现 — 从你的 star 建模偏好, 周期扫描 trending.
      </p>
    </header>

    <!-- Stats -->
    <section class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <UCard v-for="s in stats" :key="s.label">
        <div class="flex items-start gap-3">
          <UIcon :name="s.icon" class="size-5 text-tertiary-400 shrink-0 mt-0.5" />
          <div class="space-y-1 min-w-0">
            <p class="text-xs text-muted uppercase tracking-wider">{{ s.label }}</p>
            <p class="text-2xl font-semibold tabular-nums">{{ s.value }}</p>
            <p class="text-xs text-dimmed">{{ s.hint }}</p>
          </div>
        </div>
      </UCard>
    </section>

    <!-- Empty state -->
    <UCard>
      <div class="text-center py-16 space-y-4">
        <UIcon name="i-lucide-radar" class="size-12 mx-auto text-tertiary-400" />
        <div class="space-y-2">
          <p class="text-base font-medium">脚手架已就绪</p>
          <p class="text-sm text-muted max-w-md mx-auto">
            下一条 TODO:
            <NuxtLink to="/keywords" class="text-tertiary-400 hover:underline font-medium">T107 关键字管理</NuxtLink>
            或
            <NuxtLink to="/recommendations" class="text-tertiary-400 hover:underline font-medium">T108 推荐列表</NuxtLink>
          </p>
        </div>
      </div>
    </UCard>
  </div>
</template>