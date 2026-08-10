<script setup lang="ts">
// pages/index.vue — Dashboard（默认页）
// 见 docs/ui-design.md §Dashboard
//
// 阶段一：占位页（T106 实现）
// 当前显示：项目名 + 欢迎语 + 后续 TODO 链接

useHead({ title: 'Dashboard · ai-github-radar' })
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold">Dashboard</h1>

    <UCard>
      <div class="text-center py-12 space-y-3">
        <UIcon name="i-lucide-sparkles" class="size-12 mx-auto text-tertiary-400" />
        <p class="text-lg text-muted">ai-github-radar 脚手架已就绪</p>
        <p class="text-sm text-dimmed">
          下一条 TODO：<NuxtLink to="/keywords" class="text-tertiary-400 hover:underline">T107 关键字管理</NuxtLink>
        </p>
      </div>
    </UCard>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <UCard>
        <div class="space-y-1">
          <p class="text-sm text-muted">今日推荐</p>
          <p class="text-3xl font-bold">—</p>
        </div>
      </UCard>
      <UCard>
        <div class="space-y-1">
          <p class="text-sm text-muted">已 Star</p>
          <p class="text-3xl font-bold">—</p>
        </div>
      </UCard>
      <UCard>
        <div class="space-y-1">
          <p class="text-sm text-muted">关键字</p>
          <p class="text-3xl font-bold">—</p>
        </div>
      </UCard>
    </div>
  </div>
</template>
