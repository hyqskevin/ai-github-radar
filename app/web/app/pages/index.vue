<script setup lang="ts">
// pages/index.vue — Dashboard
// SPEC: docs/superpowers/specs/2026-08-10-page-dashboard-design.md
// 阶段一：调 useKeywordsStore + useRecommendationsStore；reco / stars / scan 用 mock fallback

import { useKeywordsStore } from '~/stores/keywords'
import { mockRecommendations, mockStarsStats } from '~/utils/mock-data'

useHead({ title: 'Dashboard · ai-github-radar' })

const keywordsStore = useKeywordsStore()
const recs = ref<Array<{ id: number; owner: string; name: string; score: number; matched_keywords: string[]; created_at: string }>>([])
const starsTotal = ref<number | null>(null)
const lastScanAt = ref<string | null>(null)
const scanning = ref(false)
const loadError = ref<string | null>(null)

const enabledKeywordsCount = computed(() =>
  keywordsStore.items.filter(k => k.enabled).length
)
const topRecs = computed(() =>
  [...recs.value].sort((a, b) => b.score - a.score).slice(0, 6)
)

async function loadAll() {
  loadError.value = null
  scanning.value = true
  try {
    // 阶段一：keywords 走真 store（T104）
    await keywordsStore.fetchAll()
    // reco / stars / scan 走 mock fallback（对应 store 阶段二建）
    recs.value = mockRecommendations
    starsTotal.value = mockStarsStats.total
    lastScanAt.value = new Date().toISOString()
  } catch (e) {
    loadError.value = (e as Error).message ?? 'load failed'
  } finally {
    scanning.value = false
  }
}

async function triggerScan() {
  scanning.value = true
  try {
    lastScanAt.value = new Date().toISOString()
  } finally {
    scanning.value = false
  }
}

onMounted(loadAll)
</script>

<template>
  <div class="space-y-8">
    <!-- Header -->
    <header class="flex items-start justify-between gap-4">
      <div class="space-y-2">
        <h1 class="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p class="text-sm text-muted">
          AI 驱动的 GitHub 项目发现 — 从你的 star 建模偏好，周期扫描 trending
        </p>
      </div>
      <UButton
        color="primary"
        icon="i-lucide-radar"
        :loading="scanning"
        :disabled="scanning"
        @click="triggerScan"
      >
        {{ scanning ? '扫描中…' : '立即扫描' }}
      </UButton>
    </header>

    <!-- Error banner -->
    <UAlert
      v-if="loadError"
      color="error"
      variant="subtle"
      icon="i-lucide-triangle-alert"
      :title="'加载失败：' + loadError"
    >
      <template #actions>
        <UButton color="error" variant="outline" size="sm" @click="loadAll">重试</UButton>
      </template>
    </UAlert>

    <!-- Stats Grid -->
    <section class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <UCard>
        <div class="flex items-start gap-3">
          <UIcon name="i-lucide-sparkles" class="size-5 text-tertiary-400 shrink-0 mt-1" />
          <div class="space-y-1 min-w-0">
            <p class="text-xs text-muted uppercase tracking-wider">今日推荐</p>
            <p class="text-2xl font-semibold tabular-nums">
              {{ scanning ? '—' : topRecs.length }}
            </p>
            <p class="text-xs text-dimmed">命中关键字的 trending</p>
          </div>
        </div>
      </UCard>

      <UCard>
        <div class="flex items-start gap-3">
          <UIcon name="i-lucide-tag" class="size-5 text-tertiary-400 shrink-0 mt-1" />
          <div class="space-y-1 min-w-0">
            <p class="text-xs text-muted uppercase tracking-wider">启用关键字</p>
            <p class="text-2xl font-semibold tabular-nums">
              {{ scanning ? '—' : enabledKeywordsCount }}
            </p>
            <p class="text-xs text-dimmed">auto + manual 启用项</p>
          </div>
        </div>
      </UCard>

      <UCard>
        <div class="flex items-start gap-3">
          <UIcon name="i-lucide-star" class="size-5 text-tertiary-400 shrink-0 mt-1" />
          <div class="space-y-1 min-w-0">
            <p class="text-xs text-muted uppercase tracking-wider">总 Star</p>
            <p class="text-2xl font-semibold tabular-nums">
              {{ scanning ? '—' : (starsTotal ?? '?') }}
            </p>
            <p class="text-xs text-dimmed">你的 GitHub star 收藏</p>
          </div>
        </div>
      </UCard>
    </section>

    <!-- Recommendations Grid -->
    <section class="space-y-4">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold">命中推荐</h2>
        <NuxtLink to="/recommendations" class="text-sm text-tertiary-400 hover:underline">
          查看全部 ({{ recs.length }}) →
        </NuxtLink>
      </div>

      <!-- Empty state -->
      <UCard v-if="!scanning && topRecs.length === 0">
        <div class="text-center py-12 space-y-3">
          <UIcon name="i-lucide-inbox" class="size-12 mx-auto text-dimmed" />
          <p class="text-sm text-muted">还没有推荐</p>
          <p class="text-xs text-dimmed">运行 init + scan 后会出现</p>
        </div>
      </UCard>

      <!-- Cards grid -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <UCard v-for="r in topRecs" :key="r.id" class="hover:border-tertiary-400 transition-colors">
          <div class="space-y-3">
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0">
                <p class="font-mono text-sm font-semibold truncate">
                  {{ r.owner }}/{{ r.name }}
                </p>
                <p class="text-xs text-muted tabular-nums">⭐ {{ r.score.toFixed(1) }}</p>
              </div>
            </div>
            <p class="text-sm text-default line-clamp-2">{{ '仓库描述占位' }}</p>
            <div v-if="r.matched_keywords.length" class="flex flex-wrap gap-1">
              <span
                v-for="kw in r.matched_keywords"
                :key="kw"
                class="px-2 py-1 text-xs rounded-sm bg-tertiary-400/15 text-tertiary-400"
              >
                {{ kw }}
              </span>
            </div>
          </div>
        </UCard>
      </div>
    </section>
  </div>
</template>