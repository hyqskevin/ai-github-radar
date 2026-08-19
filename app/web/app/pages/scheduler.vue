<script setup lang="ts">
// pages/scheduler.vue — 定时任务配置 (T128)
// 增删改 cron 表达式,实时算 next_run_at

useHead({ title: '定时任务 · ai-github-radar' })

interface Schedule {
  id: number
  name: string
  cron: string
  enabled: boolean
  last_run_at: string | null
  next_run_at: string | null
  created_at: string
  payload?: unknown
}

const { data, pending, refresh } = await useFetch<{ schedules: Schedule[] }>('/api/schedules', {
  default: () => ({ schedules: [] }),
})

const schedules = computed(() => data.value?.schedules ?? [])

const newSchedule = ref({
  name: '',
  cron: '0 9 * * *',
  enabled: true,
})

const error = ref<string | null>(null)

async function onRefresh() { await refresh() }

async function handleCreate() {
  error.value = null
  if (!newSchedule.value.name.trim() || !newSchedule.value.cron.trim()) {
    error.value = '名称和 cron 必填'
    return
  }
  try {
    await $fetch('/api/schedules', {
      method: 'POST',
      body: {
        name: newSchedule.value.name.trim(),
        cron: newSchedule.value.cron.trim(),
        enabled: newSchedule.value.enabled,
      },
    })
    newSchedule.value.name = ''
    newSchedule.value.cron = '0 9 * * *'
    await refresh()
  } catch (e: any) {
    error.value = e?.data?.detail || e?.message || '创建失败'
  }
}

async function handleToggle(s: Schedule) {
  try {
    await $fetch(`/api/schedules/${s.id}`, {
      method: 'PATCH',
      body: { enabled: !s.enabled },
    })
    await refresh()
  } catch (e: any) {
    error.value = e?.message
  }
}

async function handleDelete(s: Schedule) {
  if (!confirm(`确认删除 "${s.name}"?`)) return
  try {
    await $fetch(`/api/schedules/${s.id}`, { method: 'DELETE' })
    await refresh()
  } catch (e: any) {
    error.value = e?.message
  }
}

// 内置任务模板
const presets = [
  { label: '每天 09:00', cron: '0 9 * * *' },
  { label: '每 6 小时', cron: '0 */6 * * *' },
  { label: '周一至五 09:00', cron: '0 9 * * 1-5' },
  { label: '每周日 20:00', cron: '0 20 * * 0' },
  { label: '每月 1 号 09:00', cron: '0 9 1 * *' },
]
</script>

<template>
  <div class="space-y-6">
    <header class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold tracking-tight">定时任务</h1>
        <p class="text-sm text-muted">用 cron 表达式调度后台任务</p>
      </div>
      <UButton icon="i-lucide-refresh-cw" variant="ghost" :loading="pending" @click="onRefresh">
        刷新
      </UButton>
    </header>

    <UAlert v-if="error" color="error" variant="subtle" :title="error" />

    <!-- Create form -->
    <UCard>
      <template #header>
        <h2 class="text-lg font-semibold">新建任务</h2>
      </template>
      <form class="space-y-4" @submit.prevent="handleCreate">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <UFormField label="名称" required>
            <UInput
              v-model="newSchedule.name"
              placeholder="例:scan_keywords / refresh_stars"
              required
            />
          </UFormField>
          <UFormField label="Cron 表达式" required help="5 段: 分 时 日 月 周">
            <UInput
              v-model="newSchedule.cron"
              placeholder="0 9 * * *"
              required
              font-mono
            />
          </UFormField>
          <UFormField label="启用">
            <UToggle v-model="newSchedule.enabled" />
          </UFormField>
        </div>

        <div class="flex items-center gap-2 flex-wrap">
          <span class="text-xs text-muted">快速模板:</span>
          <UButton
            v-for="p in presets"
            :key="p.cron"
            size="xs"
            variant="soft"
            @click="newSchedule.cron = p.cron"
          >
            {{ p.label }} ({{ p.cron }})
          </UButton>
        </div>

        <UButton type="submit" color="primary" icon="i-lucide-plus">添加</UButton>
      </form>
    </UCard>

    <!-- Table -->
    <UCard>
      <template #header>
        <h2 class="text-lg font-semibold">已配置 ({{ schedules.length }})</h2>
      </template>
      <p v-if="schedules.length === 0" class="text-sm text-muted py-12 text-center">
        还没有定时任务
      </p>
      <UTable
        v-else
        :data="schedules"
        :columns="[
          { id: 'id', header: 'ID' },
          { id: 'name', header: '名称' },
          { id: 'cron', header: 'Cron' },
          { id: 'enabled', header: '启用' },
          { id: 'next_run_at', header: '下次执行' },
          { id: 'last_run_at', header: '上次执行' },
          { id: 'actions', header: '操作' }
        ]"
      >
        <template #id-cell="{ row }">
          <span class="font-mono text-xs">#{{ row.id }}</span>
        </template>
        <template #name-cell="{ row }">
          <UBadge color="primary" variant="subtle">{{ row.name }}</UBadge>
        </template>
        <template #cron-cell="{ row }">
          <span class="font-mono text-xs">{{ row.cron }}</span>
        </template>
        <template #enabled-cell="{ row }">
          <UToggle :model-value="row.enabled" @update:model-value="handleToggle(row)" />
        </template>
        <template #next_run_at-cell="{ row }">
          <span v-if="row.next_run_at" class="font-mono text-xs tabular-nums">
            {{ row.next_run_at }}
          </span>
          <span v-else class="text-xs text-dimmed">—</span>
        </template>
        <template #last_run_at-cell="{ row }">
          <span v-if="row.last_run_at" class="font-mono text-xs">
            {{ row.last_run_at }}
          </span>
          <span v-else class="text-xs text-dimmed">从未</span>
        </template>
        <template #actions-cell="{ row }">
          <UButton
            color="error"
            variant="ghost"
            icon="i-lucide-trash"
            size="sm"
            aria-label="删除"
            @click="handleDelete(row)"
          />
        </template>
      </UTable>
    </UCard>

    <UAlert color="info" variant="subtle">
      <template #title>Cron 语法</template>
      <p class="text-sm">
        5 段从左到右: <code>分(0-59) 时(0-23) 日(1-31) 月(1-12) 周(0-6, 周日=0)</code>
      </p>
      <p class="text-xs text-muted mt-1">
        例: <code>0 9 * * *</code> 每天 9:00 / <code>*/30 * * * *</code> 每 30 分钟
      </p>
    </UAlert>
  </div>
</template>