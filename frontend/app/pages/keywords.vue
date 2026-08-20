<script setup lang="ts">
// pages/keywords.vue — 关键字管理表格
// T144: 顶部新增「提取关键字」按钮触发后台从 stars 提关键字
// SPEC: docs/superpowers/specs/2026-08-10-page-keywords-design.md,
// docs/superpowers/specs/2026-08-20-split-init-into-stars-and-keywords-design.md

import { useKeywordsStore } from '~/stores/keywords'

useHead({ title: '关键字 · ai-github-radar' })

const store = useKeywordsStore()
const newTerm = ref('')
const newWeight = ref(5.0)
const error = ref<string | null>(null)

// T144: 后台提取关键字状态
const noLlm = ref(false)
const triggering = ref(false)
const extractJobId = ref<number | null>(null)
const extractInfo = ref<string | null>(null)
const extractError = ref<string | null>(null)

onMounted(() => store.fetchAll())

async function handleAdd() {
  if (!newTerm.value.trim()) return
  error.value = null
  try {
    await store.create({ term: newTerm.value.trim(), weight: newWeight.value })
    newTerm.value = ''
  } catch (e) {
    error.value = (e as Error).message
  }
}

async function handleToggle(id: number) {
  await store.toggle(id)
}

async function handleDelete(id: number) {
  if (!confirm('确认删除该关键字？')) return
  await store.delete(id)
}

async function handleExtract() {
  extractError.value = null
  extractInfo.value = null
  triggering.value = true
  try {
    const r = await $fetch<{ job_id: number }>('/api/keywords/extract', {
      method: 'POST',
      body: { no_llm: noLlm.value },
    })
    extractJobId.value = r.job_id
    extractInfo.value = `已提交 extract_keywords job #${r.job_id},后台跑中`
    pollExtractJob(r.job_id)
  } catch (e: any) {
    extractError.value = e?.data?.statusMessage ?? e?.message ?? '提取失败'
  } finally {
    triggering.value = false
  }
}

async function pollExtractJob(id: number) {
  for (let i = 0; i < 60; i++) {
    await new Promise(r => setTimeout(r, 2000))
    const j = await $fetch<{ jobs: Array<{ id: number; status: string; result: any; error: string }> }>('/api/jobs')
    const job = j.jobs.find(x => x.id === id)
    if (!job) continue
    if (job.status === 'success') {
      const n = job.result?.keywords ?? '?'
      const m = job.result?.kw_method ?? '?'
      extractInfo.value = `✓ 提取了 ${n} 个关键字 (${m})`
      extractJobId.value = null
      await store.fetchAll()
      return
    }
    if (job.status === 'failed') {
      extractError.value = job.error || 'extract failed'
      extractJobId.value = null
      return
    }
  }
  extractJobId.value = null
  extractError.value = 'job timeout (2 分钟还没跑完)'
}
</script>

<template>
  <div class="space-y-6">
    <header class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold tracking-tight">关键字管理</h1>
        <p class="text-sm text-muted">手动添加 + 后台从 stars 提关键字</p>
      </div>
      <div class="flex items-center gap-3">
        <UToggle v-model="noLlm" />
        <span class="text-xs text-muted">勾上跳过 LLM 走 TF-IDF</span>
        <UButton
          color="primary"
          icon="i-lucide-sparkles"
          :loading="triggering || extractJobId !== null"
          :disabled="triggering || extractJobId !== null"
          @click="handleExtract"
        >
          {{ extractJobId ? `Extract #${extractJobId} 跑中…` : '提取关键字' }}
        </UButton>
      </div>
    </header>

    <UAlert v-if="error" color="error" variant="subtle" :title="error" />
    <UAlert v-if="extractError" color="error" variant="subtle" :title="extractError" />
    <UAlert v-if="extractInfo" color="info" variant="subtle" :title="extractInfo" />

    <!-- Add form -->
    <UCard>
      <form class="flex items-end gap-3" @submit.prevent="handleAdd">
        <UFormField label="关键字" class="flex-1">
          <UInput v-model="newTerm" placeholder="例:fastapi / rust / llm" required />
        </UFormField>
        <UFormField label="权重" class="w-32">
          <UInput v-model.number="newWeight" type="number" min="0" step="0.5" />
        </UFormField>
        <UButton type="submit" color="primary" icon="i-lucide-plus">添加</UButton>
      </form>
    </UCard>

    <!-- Table -->
    <UCard>
      <p v-if="store.loading" class="text-sm text-muted py-4">加载中…</p>
      <p v-else-if="store.items.length === 0" class="text-sm text-muted py-8 text-center">
        还没有关键字,先添加几个
      </p>
      <UTable
        v-else
        :data="store.items"
        :columns="[
          { id: 'term', header: '关键字' },
          { id: 'weight', header: '权重' },
          { id: 'source', header: '来源' },
          { id: 'enabled', header: '状态' },
          { id: 'actions', header: '操作' }
        ]"
      >
        <template #term-cell="{ row }">
          <span class="font-mono text-sm">{{ row.term }}</span>
        </template>
        <template #weight-cell="{ row }">
          <span class="tabular-nums">{{ row.weight.toFixed(2) }}</span>
        </template>
        <template #source-cell="{ row }">
          <UBadge :color="row.source === 'manual' ? 'primary' : 'neutral'" variant="subtle">
            {{ row.source }}
          </UBadge>
        </template>
        <template #enabled-cell="{ row }">
          <UToggle :model-value="row.enabled" @update:model-value="handleToggle(row.id)" />
        </template>
        <template #actions-cell="{ row }">
          <UButton
            color="error"
            variant="ghost"
            icon="i-lucide-trash"
            size="sm"
            aria-label="删除"
            @click="handleDelete(row.id)"
          />
        </template>
      </UTable>
    </UCard>
  </div>
</template>