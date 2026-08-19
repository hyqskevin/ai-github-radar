<script setup lang="ts">
// pages/init.vue — 一次性初始化(配 GitHub user + token + 拉 stars + 提取关键字)

useHead({ title: '初始化 · ai-github-radar' })

// 拉 GitHub user 配置
const config = ref({
  githubUser: '',
  githubToken: '',
  noLlm: false,
})

const saving = ref(false)
const triggerError = ref<string | null>(null)
const triggerInfo = ref<string | null>(null)
const lastJobId = ref<number | null>(null)
const jobStatus = ref<'pending' | 'running' | 'success' | 'failed' | null>(null)

const pollingJobId = ref<number | null>(null)

async function loadConfig() {
  try {
    const r = await $fetch<{ github_user: string }>('/api/settings/all')
    config.value.githubUser = r.github_user || ''
  } catch (e) {
    // ignore
  }
}

async function saveAndTrigger() {
  saving.value = true
  triggerError.value = null
  triggerInfo.value = null
  try {
    // 1. 先保存 GitHub user/token 到 settings(持久化到 SQLite)
    await $fetch('/api/settings/all', {
      method: 'POST',
      body: {
        github_user: config.value.githubUser,
        github_token: config.value.githubToken,
      },
    })
    triggerInfo.value = '配置已保存'

    // 2. 触发 init job(后台跑)
    const r = await $fetch<{ job_id: number }>('/api/stars/refresh', {
      method: 'POST',
      body: {
        user: config.value.githubUser,
        no_llm: config.value.noLlm,
      },
    })
    lastJobId.value = r.job_id
    triggerInfo.value = `已提交 init job #${r.job_id},后台跑中`
    pollJob(r.job_id)
  } catch (e: any) {
    triggerError.value = e?.data?.statusMessage ?? e?.message ?? '保存失败'
  } finally {
    saving.value = false
  }
}

async function pollJob(id: number) {
  pollingJobId.value = id
  jobStatus.value = 'running'
  for (let i = 0; i < 90; i++) {  // 3 分钟上限
    await new Promise(r => setTimeout(r, 2000))
    const j = await $fetch<{ jobs: Array<{ id: number; status: string; result: any; error: string }> }>(
      '/api/jobs'
    )
    const job = j.jobs.find(x => x.id === id)
    if (!job) continue
    if (job.status === 'success') {
      jobStatus.value = 'success'
      const stars = job.result?.stars ?? '?'
      const kws = job.result?.keywords ?? '?'
      const method = job.result?.kw_method ?? '?'
      triggerInfo.value = `✓ 拉了 ${stars} 个 star,提取了 ${kws} 个关键字 (${method})`
      pollingJobId.value = null
      return
    }
    if (job.status === 'failed') {
      jobStatus.value = 'failed'
      triggerError.value = job.error || 'init failed'
      pollingJobId.value = null
      return
    }
  }
  pollingJobId.value = null
  triggerError.value = 'job timeout (3 分钟还没跑完)'
}

onMounted(loadConfig)
</script>

<template>
  <div class="space-y-6">
    <header>
      <h1 class="text-2xl font-bold tracking-tight">初始化</h1>
      <p class="text-sm text-muted">一次性配置 GitHub + 拉 Star 列表 + 提取关键字</p>
    </header>

    <UAlert v-if="triggerError" color="error" variant="subtle" :title="triggerError" />
    <UAlert v-if="triggerInfo" :color="jobStatus === 'failed' ? 'error' : jobStatus === 'success' ? 'success' : 'info'" variant="subtle" :title="triggerInfo" />

    <UCard>
      <template #header>
        <h2 class="text-lg font-semibold flex items-center gap-2">
          <UIcon name="i-lucide-github" /> GitHub 配置
        </h2>
      </template>
      <div class="space-y-4">
        <UFormField label="GitHub username" required help="例如:hyqskevin">
          <UInput v-model="config.githubUser" placeholder="hyqskevin" required />
        </UFormField>

        <UFormField label="GitHub Personal Access Token" help="需要 repo:read + public access">
          <UInput
            v-model="config.githubToken"
            type="password"
            placeholder="ghp_... 或留空走 .env"
          />
        </UFormField>

        <UFormField label="跳过 LLM 关键字提取">
          <UToggle v-model="config.noLlm" />
          <p class="text-xs text-muted mt-1">
            默认会用 LLM 提取(更准);勾上就走 TF-IDF(免 API key)
          </p>
        </UFormField>
      </div>
    </UCard>

    <div class="flex justify-end">
      <UButton
        color="primary"
        icon="i-lucide-play"
        size="lg"
        :loading="saving || pollingJobId !== null"
        :disabled="saving || pollingJobId !== null || !config.githubUser"
        @click="saveAndTrigger"
      >
        {{ pollingJobId ? `Init #${pollingJobId} 跑中…` : '保存配置 + 立即拉取' }}
      </UButton>
    </div>

    <UAlert color="info" variant="subtle">
      <template #title>初始化流程</template>
      <ol class="text-sm space-y-1 list-decimal pl-4">
        <li>保存 GitHub user + token 到本地 SQLite <code>settings</code> 表</li>
        <li>提交后台 job → 调用 GitHub API 拉所有 star 仓库 → 写入 <code>stars</code> 表</li>
        <li>用 LLM(默认)/TF-IDF 提取关键字 → 写入 <code>keywords</code> 表</li>
        <li>完成后跳转 <NuxtLink to="/keywords" class="text-tertiary-400">关键字页</NuxtLink> 查看</li>
      </ol>
    </UAlert>
  </div>
</template>