<script setup lang="ts">
// pages/stars.vue — 我的 Star 总览
// SPEC: docs/superpowers/specs/2026-08-10-page-stars-settings-design.md

useHead({ title: '我的 Star · ai-github-radar' })

interface Star {
  id: number
  repo_id: number
  owner: string
  name: string
  full_name?: string
  description: string | null
  language: string | null
  topics: string[]
  stargazers_count?: number | null
  starred_at?: string | null
}

interface Stats {
  total: number
  by_language: Record<string, number>
  top_topics: Array<{ name: string; count: number }>
}

// 并行拉 stats + stars 列表
const { data: stats, pending: statsPending } = await useFetch<Stats>('/api/stars/stats', {
  default: () => ({ total: 0, by_language: {}, top_topics: [] })
})

const { data: starsData, pending: starsPending2, refresh } = await useFetch<{ stars: Star[]; limit: number }>(
  '/api/stars',
  { default: () => ({ stars: [], limit: 200 }) }
)

const stars = computed(() => starsData.value?.stars ?? [])

const langEntries = computed(() =>
  Object.entries(stats.value?.by_language || {})
    .sort(([, a], [, b]) => (b as number) - (a as number))
    .slice(0, 10)
)

const refreshing = ref(false)
async function onRefresh() {
  refreshing.value = true
  try { await refresh() } finally { refreshing.value = false }
}

// 触发后台 init(拉 GitHub stars + 关键字提取)
const triggering = ref(false)
const lastJobId = ref<number | null>(null)
const triggerError = ref<string | null>(null)
async function triggerInit() {
  triggering.value = true
  triggerError.value = null
  try {
    const r = await $fetch<{ job_id: number }>('/api/stars/refresh', {
      method: 'POST',
      body: { user: '', no_llm: false },
    })
    lastJobId.value = r.job_id
    // 轮询 job 状态
    pollJobUntilDone(r.job_id)
  } catch (e: any) {
    triggerError.value = e?.data?.statusMessage ?? e?.message ?? 'trigger failed'
  } finally {
    triggering.value = false
  }
}

const pollingJobId = ref<number | null>(null)
async function pollJobUntilDone(id: number) {
  pollingJobId.value = id
  for (let i = 0; i < 60; i++) {
    await new Promise(r => setTimeout(r, 2000))
    const j = await $fetch<{ jobs: Array<{ id: number; status: string; result: any; error: string }> }>(
      '/api/jobs'
    )
    const job = j.jobs.find(x => x.id === id)
    if (!job) continue
    if (job.status === 'success') {
      // 拉完刷新 stars 数据
      await refresh()
      lastJobId.value = null
      pollingJobId.value = null
      return
    }
    if (job.status === 'failed') {
      triggerError.value = job.error || 'init failed'
      pollingJobId.value = null
      return
    }
  }
  pollingJobId.value = null
}
</script>

<template>
  <div class="space-y-6">
    <header class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold tracking-tight">我的 Star</h1>
        <p class="text-sm text-muted">从 GitHub API 拉取的真实数据(本地 SQLite 缓存)</p>
      </div>
      <div class="flex items-center gap-2">
        <UButton
          color="primary"
          icon="i-lucide-download"
          :loading="triggering || pollingJobId !== null"
          :disabled="triggering || pollingJobId !== null"
          @click="triggerInit"
        >
          {{ pollingJobId ? `Init #${pollingJobId} 跑中…` : '拉取 Star' }}
        </UButton>
        <UButton icon="i-lucide-refresh-cw" variant="ghost" :loading="refreshing || starsPending2" @click="onRefresh">
          刷新
        </UButton>
      </div>
    </header>

    <UAlert v-if="triggerError" color="error" variant="subtle" :title="triggerError" />
    <UAlert v-if="lastJobId && pollingJobId" color="info" variant="subtle">
      <template #title>后台任务 #{{ lastJobId }} 跑中…</template>
      <p class="text-xs text-muted">最长 2 分钟,完成后自动刷新本页数据</p>
    </UAlert>

    <p v-if="statsPending || starsPending2" class="text-sm text-muted">加载中…</p>

    <template v-else>
      <!-- 统计 -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <UCard>
          <p class="text-xs text-muted uppercase tracking-wider">总 Star 数</p>
          <p class="text-4xl font-bold tabular-nums mt-2 text-tertiary-400">{{ stats.total }}</p>
        </UCard>

        <UCard>
          <p class="text-xs text-muted uppercase tracking-wider mb-3">语言分布 (Top 10)</p>
          <ul class="space-y-1">
            <li v-if="langEntries.length === 0" class="text-sm text-dimmed text-center py-4">
              还没有 star 数据,先去后端跑 init
            </li>
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
          <p class="text-xs text-muted uppercase tracking-wider mb-3">热门 Topic</p>
          <div class="flex flex-wrap gap-2">
            <UBadge
              v-for="t in stats.top_topics"
              :key="t.name"
              color="neutral"
              variant="subtle"
            >
              {{ t.name }} ({{ t.count }})
            </UBadge>
            <p v-if="stats.top_topics.length === 0" class="text-sm text-dimmed">
              还没有 topic 数据
            </p>
          </div>
        </UCard>
      </div>

      <!-- Star 列表 -->
      <UCard>
        <template #header>
          <h2 class="text-lg font-semibold">仓库列表 ({{ stars.length }})</h2>
        </template>
        <p v-if="stars.length === 0" class="text-sm text-muted py-8 text-center">
          还没有 star 数据
          <br />
          <span class="text-xs text-dimmed">在 .env 配 GITHUB_TOKEN + RADAR_USER 后跑 <code>python -m ai_github_radar.cli init</code></span>
        </p>
        <UTable
          v-else
          :data="stars"
          :columns="[
            { id: 'full_name', header: '仓库' },
            { id: 'language', header: '语言' },
            { id: 'topics', header: 'Topics' },
            { id: 'stargazers_count', header: '★ 数' }
          ]"
        >
          <template #full_name-cell="{ row }">
            <a
              :href="`https://github.com/${row.full_name || row.owner + '/' + row.name}`"
              target="_blank"
              rel="noopener noreferrer"
              class="font-mono text-sm text-tertiary-400 hover:underline"
            >
              {{ row.full_name || `${row.owner}/${row.name}` }}
            </a>
          </template>
          <template #language-cell="{ row }">
            <UBadge v-if="row.language" color="neutral" variant="subtle">
              {{ row.language }}
            </UBadge>
            <span v-else class="text-xs text-dimmed">—</span>
          </template>
          <template #topics-cell="{ row }">
            <div class="flex flex-wrap gap-1">
              <span
                v-for="t in (row.topics || []).slice(0, 3)"
                :key="t"
                class="px-1.5 py-0.5 text-xs rounded-sm bg-tertiary-400/15 text-tertiary-400"
              >
                {{ t }}
              </span>
            </div>
          </template>
          <template #stargazers_count-cell="{ row }">
            <span v-if="row.stargazers_count !== null && row.stargazers_count !== undefined" class="tabular-nums">
              {{ row.stargazers_count.toLocaleString() }}
            </span>
            <span v-else class="text-xs text-dimmed">—</span>
          </template>
        </UTable>
      </UCard>
    </template>
  </div>
</template>