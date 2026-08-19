<script setup lang="ts">
// error.vue — 全局错误页（404 / 500）
// 风格保持 dashboard 一致：AppBar + 居中错误提示
import type { NuxtError } from '#app'

defineProps<{
  error: NuxtError
}>()

const handleHome = () => clearError({ redirect: '/' })
</script>

<template>
  <UApp>
    <div class="min-h-screen flex flex-col bg-default text-default">
      <header class="h-14 shrink-0 border-b border-default bg-default/95 backdrop-blur flex items-center px-6 gap-3 sticky top-0 z-10">
        <NuxtLink to="/" class="flex items-center gap-2 font-mono font-bold text-base tracking-tight">
          <UIcon name="i-lucide-radar" class="size-5 text-tertiary-400" />
          <span>ai-github-radar</span>
        </NuxtLink>
      </header>

      <main class="flex-1 flex items-center justify-center p-8">
        <UCard class="max-w-md w-full">
          <div class="text-center space-y-4 py-8">
            <UIcon name="i-lucide-triangle-alert" class="size-12 mx-auto text-warning" />
            <div class="space-y-2">
              <p class="text-3xl font-bold tabular-nums">{{ error.statusCode }}</p>
              <p class="text-sm text-muted">{{ error.statusMessage || '出错了' }}</p>
            </div>
            <UButton color="primary" icon="i-lucide-home" @click="handleHome">
              回到首页
            </UButton>
          </div>
        </UCard>
      </main>
    </div>
  </UApp>
</template>