<script setup lang="ts">
// pages/keywords.vue — 关键字管理表格
// SPEC: docs/superpowers/specs/2026-08-10-page-keywords-design.md

import { useKeywordsStore } from '~/stores/keywords'

useHead({ title: '关键字 · ai-github-radar' })

const store = useKeywordsStore()
const newTerm = ref('')
const newWeight = ref(5.0)
const error = ref<string | null>(null)

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
</script>

<template>
  <div class="space-y-6">
    <header class="flex items-center justify-between">
      <h1 class="text-2xl font-bold tracking-tight">关键字管理</h1>
    </header>

    <UAlert v-if="error" color="error" variant="subtle" :title="error" />

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
          { key: 'term', label: '关键字' },
          { key: 'weight', label: '权重' },
          { key: 'source', label: '来源' },
          { key: 'enabled', label: '状态' },
          { key: 'actions', label: '操作' }
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