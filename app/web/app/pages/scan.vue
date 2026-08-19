<script setup lang="ts">
// pages/scan.vue — 手动触发 scan + 历史
// SPEC: docs/superpowers/specs/2026-08-10-page-scan-design.md

useHead({ title: '扫描 · ai-github-radar' })

const triggering = ref(false)
const lastResult = ref<{ count: number; channel: string } | null>(null)
const error = ref<string | null>(null)
const pushTarget = ref<'stdout' | 'local'>('stdout')

const { data: recs, pending, refresh: refreshRecs } = await useFetch('/api/recommendations', {
  default: () => ({ recommendations: [] })
})

const scanHistory = computed(() => (recs.value?.recommendations ?? []).slice(0, 20))

async function triggerScan() {
  triggering.value = true
  error.value = null
  try {
    const result = await $fetch<{ recommendations: any[] }>('/api/scan', {
      method: 'POST',
      body: { top: 10, push: pushTarget.value }
    })
    lastResult.value = {
      count: result.recommendations.length,
      channel: pushTarget.value,
    }
    await refreshRecs()
  } catch (e: any) {
    error.value = e?.message ?? 'scan failed'
  } finally {
    triggering.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <header>
      <h1 class="text-2xl font-bold tracking-tight">手动扫描</h1>
      <p class="text-sm text-muted">立刻拉一次 trending,匹配关键字后推送</p>
    </header>

    <UAlert v-if="error" color="error" variant="subtle" :title="error" />

    <!-- Trigger form -->
    <UCard>
      <div class="flex items-end gap-3">
        <UFormField label="推送目标" class="flex-1">
          <USelectMenu
            v-model="pushTarget"
            :options="[
              { label: 'stdout (打印 JSON)', value: 'stdout' },
              { label: 'local (写 ./data/recommendations)', value: 'local' }
            ]"
            value-key="value"
          />
        </UFormField>
        <UButton
          color="primary"
          icon="i-lucide-play"
          :loading="triggering"
          :disabled="triggering"
          @click="triggerScan"
        >
          {{ triggering ? '扫描中…' : '开始扫描' }}
        </UButton>
      </div>
    </UCard>

    <!-- Last result -->
    <UAlert v-if="lastResult" color="success" variant="subtle">
      <template #title>扫描完成</template>
      找到 <b>{{ lastResult.count }}</b> 条推荐,已推到 <b>{{ lastResult.channel }}</b>
    </UAlert>

    <!-- History -->
    <UCard>
      <template #header>
        <h2 class="text-lg font-semibold">最近推送历史</h2>
      </template>
      <p v-if="pending" class="text-sm text-muted py-4">加载中…</p>
      <p v-else-if="scanHistory.length === 0" class="text-sm text-muted py-8 text-center">
        还没有推送过
      </p>
      <UTable
        v-else
        :data="scanHistory"
        :columns="[
          { key: 'pushed_at', label: '时间' },
          { key: 'repo_id', label: 'Repo ID' },
          { key: 'channel', label: '渠道' },
          { key: 'score', label: 'Score' }
        ]"
      >
        <template #pushed_at-cell="{ row }">
          <span class="font-mono text-xs">{{ row.pushed_at }}</span>
        </template>
        <template #repo_id-cell="{ row }">
          <span class="font-mono">#{{ row.repo_id }}</span>
        </template>
        <template #score-cell="{ row }">
          <span class="tabular-nums text-tertiary-400">{{ row.score.toFixed(3) }}</span>
        </template>
      </UTable>
    </UCard>
  </div>
</template>