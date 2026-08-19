<script setup lang="ts">
// pages/recommendations.vue — 推荐列表(真后端 /api/recommendations)

useHead({ title: '推荐列表 · ai-github-radar' })

interface Recommendation {
  id: number
  repo_id: number
  score: number
  matched_keywords: string[]
  channel: string
  pushed_at: string
}

const { data, pending, error, refresh } = await useFetch<{ recommendations: Recommendation[] }>(
  '/api/recommendations',
  { default: () => ({ recommendations: [] }) }
)

const recs = computed(() => data.value?.recommendations ?? [])

function fmtTime(s: string) {
  return s.replace('T', ' ').slice(0, 19)
}
</script>

<template>
  <div class="space-y-6">
    <header class="flex items-center justify-between">
      <h1 class="text-2xl font-bold tracking-tight">推荐列表</h1>
      <UButton icon="i-lucide-refresh-cw" variant="ghost" :loading="pending" @click="refresh()">
        刷新
      </UButton>
    </header>

    <UAlert v-if="error" color="error" variant="subtle" :title="error.message" />

    <p v-if="pending" class="text-sm text-muted">加载中…</p>
    <UCard v-else-if="recs.length === 0">
      <div class="text-center py-12 space-y-3">
        <UIcon name="i-lucide-inbox" class="size-12 mx-auto text-dimmed" />
        <p class="text-sm text-muted">还没有推荐记录</p>
        <p class="text-xs text-dimmed">
          配置 <NuxtLink to="/scheduler" class="text-tertiary-400">定时任务</NuxtLink> 跑 scan 后会出现
        </p>
      </div>
    </UCard>
    <div v-else class="space-y-3">
      <UCard v-for="r in recs" :key="r.id">
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0 flex-1 space-y-2">
            <div class="flex items-center gap-2">
              <span class="font-mono text-sm font-semibold">#{{ r.repo_id }}</span>
              <UBadge color="neutral" variant="subtle" size="xs">{{ r.channel }}</UBadge>
            </div>
            <div class="flex flex-wrap gap-1">
              <span
                v-for="kw in (r.matched_keywords || [])"
                :key="kw"
                class="px-2 py-0.5 text-xs rounded-sm bg-tertiary-400/15 text-tertiary-400"
              >
                {{ kw }}
              </span>
            </div>
            <p class="text-xs text-dimmed font-mono">{{ fmtTime(r.pushed_at) }}</p>
          </div>
          <div class="text-right shrink-0">
            <p class="text-2xl font-semibold tabular-nums text-tertiary-400">
              {{ r.score.toFixed(3) }}
            </p>
            <p class="text-xs text-muted">score</p>
          </div>
        </div>
      </UCard>
    </div>
  </div>
</template>