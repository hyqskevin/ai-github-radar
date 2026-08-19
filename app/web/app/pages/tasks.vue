<script setup lang="ts">
// pages/tasks.vue — 任务执行监控 (T127)
// 显示后端 /api/jobs 列出的最近任务执行记录

useHead({ title: '任务监控 · ai-github-radar' })

interface Job {
  id: number
  name: string
  status: string  // pending / running / success / failed
  started_at: string
  finished_at: string | null
  duration_ms: number | null
  payload?: unknown
  result?: unknown
  error?: string
}

const { data, pending, refresh } = await useFetch<{ jobs: Job[]; limit: number }>('/api/jobs', {
  default: () => ({ jobs: [], limit: 50 }),
})

const jobs = computed(() => data.value?.jobs ?? [])

function statusColor(s: string) {
  switch (s) {
    case 'running': return 'warning'
    case 'success': return 'success'
    case 'failed': return 'error'
    default: return 'neutral'
  }
}

function fmtDuration(ms: number | null) {
  if (ms === null) return '—'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

const refreshing = ref(false)
async function onRefresh() {
  refreshing.value = true
  try { await refresh() } finally { refreshing.value = false }
}

onMounted(() => {
  // auto refresh every 10s (live monitoring)
  const interval = setInterval(() => refresh(), 10_000)
  onUnmounted(() => clearInterval(interval))
})
</script>

<template>
  <div class="space-y-6">
    <header class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold tracking-tight">任务监控</h1>
        <p class="text-sm text-muted">后端 /api/jobs 最近 50 条任务记录(自动 10s 刷新)</p>
      </div>
      <UButton icon="i-lucide-refresh-cw" variant="ghost" :loading="refreshing || pending" @click="onRefresh">
        刷新
      </UButton>
    </header>

    <UCard>
      <p v-if="pending" class="text-sm text-muted py-8 text-center">加载中…</p>
      <p v-else-if="jobs.length === 0" class="text-sm text-muted py-12 text-center">
        还没有任务执行记录
        <br />
        <span class="text-xs text-dimmed">先去 <NuxtLink to="/scan" class="text-tertiary-400">触发 scan</NuxtLink> 或 <NuxtLink to="/scheduler" class="text-tertiary-400">配置定时任务</NuxtLink></span>
      </p>
      <UTable
        v-else
        :data="jobs"
        :columns="[
          { id: 'id', header: 'ID' },
          { id: 'name', header: '任务名' },
          { id: 'status', header: '状态' },
          { id: 'started_at', header: '开始时间' },
          { id: 'duration_ms', header: '耗时' },
          { id: 'error', header: '错误' }
        ]"
      >
        <template #id-cell="{ row }">
          <span class="font-mono text-xs">#{{ row.id }}</span>
        </template>
        <template #name-cell="{ row }">
          <UBadge color="neutral" variant="subtle">{{ row.name }}</UBadge>
        </template>
        <template #status-cell="{ row }">
          <UBadge :color="statusColor(row.status)" variant="subtle">
            {{ row.status }}
          </UBadge>
        </template>
        <template #started_at-cell="{ row }">
          <span class="font-mono text-xs">{{ row.started_at }}</span>
        </template>
        <template #duration_ms-cell="{ row }">
          <span class="tabular-nums">{{ fmtDuration(row.duration_ms) }}</span>
        </template>
        <template #error-cell="{ row }">
          <span v-if="row.error" class="text-xs text-error line-clamp-2 max-w-md">
            {{ row.error }}
          </span>
          <span v-else class="text-xs text-dimmed">—</span>
        </template>
      </UTable>
    </UCard>
  </div>
</template>