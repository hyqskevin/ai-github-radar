<script setup lang="ts">
// pages/stars.vue — 我的 Star 总览
// SPEC: docs/superpowers/specs/2026-08-10-page-stars-settings-design.md

useHead({ title: '我的 Star · ai-github-radar' })

const { data, pending } = await useFetch('/api/stars/stats', {
  default: () => ({ total: 0, by_language: {}, top_topics: [] })
})

const langEntries = computed(() =>
  Object.entries(data.value?.by_language || {})
    .sort(([, a], [, b]) => (b as number) - (a as number))
    .slice(0, 10)
)
</script>

<template>
  <div class="space-y-6">
    <header>
      <h1 class="text-2xl font-bold tracking-tight">我的 Star</h1>
      <p class="text-sm text-muted">从 GitHub API 拉取的个人 star 总览</p>
    </header>

    <p v-if="pending" class="text-sm text-muted">加载中…</p>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <UCard>
        <div class="space-y-2">
          <p class="text-xs text-muted uppercase tracking-wider">总 Star 数</p>
          <p class="text-3xl font-bold tabular-nums">{{ data.total }}</p>
        </div>
      </UCard>

      <UCard>
        <p class="text-xs text-muted uppercase tracking-wider mb-3">语言分布 (Top 10)</p>
        <ul class="space-y-1">
            <li
              v-for="[lang, count] in langEntries"
              :key="lang"
              class="flex items-center justify-between text-sm"
            >
              <span class="font-mono">{{ lang }}</span>
              <span class="tabular-nums text-tertiary-400">{{ count }}</span>
            </li>
          </ul>
      </UCard>

      <UCard class="md:col-span-2">
        <p class="text-xs text-muted uppercase tracking-wider mb-3">热门 Topic (Top 10)</p>
        <div class="flex flex-wrap gap-2">
          <UBadge
            v-for="t in data.top_topics"
            :key="t.name"
            color="neutral"
            variant="subtle"
          >
            {{ t.name }} ({{ t.count }})
          </UBadge>
        </div>
      </UCard>
    </div>
  </div>
</template>