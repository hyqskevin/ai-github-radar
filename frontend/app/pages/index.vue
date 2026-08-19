<script setup lang="ts">
// pages/index.vue — Dashboard
// 显示:今日推荐 + 总 star + 关键字数 + 最近 job

useHead({ title: 'Dashboard · ai-github-radar' })

interface Stats {
  total: number
  by_language: Record<string, number>
  top_topics: Array<{ name: string; count: number }>
}

interface Recommendation {
  id: number
  repo_id: number
  score: number
  matched_keywords: string[]
  channel: string
  pushed_at: string
}

interface Keyword {
  id: number
  term: string
  weight: number
  source: string
  enabled: boolean
}

interface Job {
  id: number
  name: string
  status: string
  started_at: string
  duration_ms: number | null
}

// 并行拉四份数据
const [
  { data: stats },
  { data: recsData },
  { data: kwData },
  { data: jobsData },
] = await Promise.all([
  useFetch<Stats>('/api/stars/stats', {
    default: () => ({ total: 0, by_language: {}, top_topics: [] })
  }),
  useFetch<{ recommendations: Recommendation[] }>('/api/recommendations', {
    default: () => ({ recommendations: [] })
  }),
  useFetch<Keyword[] | { keywords: Keyword[] }>('/api/keywords', {
    default: () => []
  }),
  useFetch<{ jobs: Job[] }>('/api/jobs', {
    default: () => ({ jobs: [] })
  }),
])

const recs = computed(() => (recsData.value?.recommendations ?? []).slice(0, 6))
const keywords = computed(() => {
  const raw = kwData.value
  return Array.isArray(raw) ? raw : (raw?.keywords ?? [])
})
const enabledKeywords = computed(() => keywords.value.filter(k => k.enabled).length)
const totalStars = computed(() => stats.value?.total ?? 0)
const recentJobs = computed(() => (jobsData.value?.jobs ?? []).slice(0, 5))
const loading = computed(() => !stats.value || !recsData.value || !kwData.value || !jobsData.value)
</script>

<template>
  <div class="space-y-8">
    <header class="flex items-start justify-between gap-4">
      <div class="space-y-2">
        <h1 class="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p class="text-sm text-muted">
          AI 驱动的 GitHub 项目发现 — 从你的 star 建模偏好，周期扫描 trending
        </p>
      </div>
    </header>

    <!-- Stats Grid -->
    <section class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <UCard>
        <p class="text-xs text-muted uppercase tracking-wider">总 Star</p>
        <p class="text-3xl font-bold tabular-nums mt-2 text-tertiary-400">
          {{ totalStars }}
        </p>
        <p class="text-xs text-dimmed mt-1">GitHub star 收藏数</p>
      </UCard>

      <UCard>
        <p class="text-xs text-muted uppercase tracking-wider">启用关键字</p>
        <p class="text-3xl font-bold tabular-nums mt-2 text-tertiary-400">
          {{ enabledKeywords }} / {{ keywords.length }}
        </p>
        <p class="text-xs text-dimmed mt-1">auto + manual</p>
      </UCard>

      <UCard>
        <p class="text-xs text-muted uppercase tracking-wider">最近推荐</p>
        <p class="text-3xl font-bold tabular-nums mt-2 text-tertiary-400">
          {{ recs.length }}
        </p>
        <p class="text-xs text-dimmed mt-1">最近一次 scan</p>
      </UCard>
    </section>

    <!-- 推荐 + 最近任务 -->
    <section class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- 推荐 -->
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-semibold">最近推荐</h2>
          <NuxtLink to="/recommendations" class="text-sm text-tertiary-400 hover:underline">
            全部 →
          </NuxtLink>
        </div>
        <p v-if="loading" class="text-sm text-muted">加载中…</p>
        <UCard v-else-if="recs.length === 0">
          <div class="text-center py-8 space-y-2">
            <UIcon name="i-lucide-inbox" class="size-10 mx-auto text-dimmed" />
            <p class="text-sm text-muted">还没有推荐</p>
            <p class="text-xs text-dimmed">配置 <NuxtLink to="/scheduler" class="text-tertiary-400">定时任务</NuxtLink> 跑 scan</p>
          </div>
        </UCard>
        <div v-else class="space-y-2">
          <UCard v-for="r in recs" :key="r.id" class="hover:border-tertiary-400 transition-colors">
            <div class="flex items-center justify-between gap-2">
              <div class="min-w-0 flex-1">
                <p class="font-mono text-sm font-semibold">#{{ r.repo_id }}</p>
                <div class="flex flex-wrap gap-1 mt-1">
                  <span
                    v-for="kw in (r.matched_keywords || []).slice(0, 3)"
                    :key="kw"
                    class="px-1.5 py-0.5 text-xs rounded-sm bg-tertiary-400/15 text-tertiary-400"
                  >
                    {{ kw }}
                  </span>
                </div>
              </div>
              <p class="text-lg font-semibold tabular-nums text-tertiary-400">
                {{ r.score.toFixed(2) }}
              </p>
            </div>
          </UCard>
        </div>
      </div>

      <!-- 最近任务 -->
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-semibold">最近任务</h2>
          <NuxtLink to="/tasks" class="text-sm text-tertiary-400 hover:underline">
            监控 →
          </NuxtLink>
        </div>
        <p v-if="loading" class="text-sm text-muted">加载中…</p>
        <UCard v-else-if="recentJobs.length === 0">
          <div class="text-center py-8 space-y-2">
            <UIcon name="i-lucide-activity" class="size-10 mx-auto text-dimmed" />
            <p class="text-sm text-muted">还没有任务记录</p>
          </div>
        </UCard>
        <div v-else class="space-y-2">
          <UCard v-for="j in recentJobs" :key="j.id" class="hover:border-tertiary-400 transition-colors">
            <div class="flex items-center justify-between gap-2">
              <div class="min-w-0 flex-1">
                <p class="font-mono text-sm">{{ j.name }} <span class="text-xs text-muted">#{{ j.id }}</span></p>
                <p class="text-xs text-dimmed font-mono">{{ j.started_at }}</p>
              </div>
              <UBadge
                :color="j.status === 'success' ? 'success' : j.status === 'failed' ? 'error' : 'warning'"
                variant="subtle"
              >
                {{ j.status }}
              </UBadge>
            </div>
          </UCard>
        </div>
      </div>
    </section>
  </div>
</template>