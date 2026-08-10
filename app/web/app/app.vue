<script setup lang="ts">
// app.vue — ai-github-radar 全局入口
// 布局：AppBar + SideNav + Content（见 docs/ui-design.md）

const appConfig = useAppConfig()

useHead({
  title: 'ai-github-radar',
  meta: [
    { name: 'viewport', content: 'width=device-width, initial-scale=1' },
    { name: 'description', content: 'AI-driven GitHub project discovery dashboard' }
  ],
  htmlAttrs: {
    lang: 'zh-CN',
    dir: computed(() => appConfig.dir)
  }
})
</script>

<template>
  <UApp :toaster="appConfig.toaster" :dir="appConfig.dir">
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </UApp>
</template>