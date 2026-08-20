<script setup lang="ts">
// pages/settings.vue — 设置页(合并原 /init 一次性初始化)
// T139: 统一管理 LLM + GitHub(含 token)+ 拉取初始化动作;配置回填 /api/settings/all
// SPEC: docs/superpowers/specs/2026-08-19-settings-merge-init-design.md

useHead({ title: '设置 · ai-github-radar' })

const config = ref({
  llmProvider: 'none',
  llmModel: '',
  llmApiKey: '',
  apiKeySet: false,
  githubUser: '',
  githubToken: '',
  githubTokenSet: false,
})
const noLlm = ref(false)

const saving = ref(false)
const saveOk = ref(false)
const error = ref<string | null>(null)

async function loadConfig() {
  try {
    const r = await $fetch<{
      llm_provider: string
      llm_model: string
      llm_api_key_set: boolean
      github_user: string
      github_token_set: boolean
    }>('/api/settings/all')
    config.value.llmProvider = r.llm_provider || 'none'
    config.value.llmModel = r.llm_model || ''
    config.value.apiKeySet = !!r.llm_api_key_set
    config.value.githubUser = r.github_user || ''
    config.value.githubTokenSet = !!r.github_token_set
  } catch (e: any) {
    error.value = e?.message ?? 'load failed'
  }
}

async function saveConfig() {
  saving.value = true
  error.value = null
  try {
    // LLM 配置
    const llmBody: any = { provider: config.value.llmProvider, model: config.value.llmModel }
    if (config.value.llmApiKey) llmBody.api_key = config.value.llmApiKey
    const llm = await $fetch<{ provider: string; model: string; api_key_set: boolean }>('/api/settings/llm', {
      method: 'POST',
      body: llmBody,
    })
    config.value.llmProvider = llm.provider
    config.value.llmModel = llm.model
    config.value.apiKeySet = llm.api_key_set
    config.value.llmApiKey = ''

    // GitHub 配置
    const ghBody: any = { github_user: config.value.githubUser }
    if (config.value.githubToken) ghBody.github_token = config.value.githubToken
    const gh = await $fetch<{ github_user: string; github_token_set: boolean }>('/api/settings/all', {
      method: 'POST',
      body: ghBody,
    })
    config.value.githubUser = gh.github_user || ''
    config.value.githubTokenSet = !!gh.github_token_set
    config.value.githubToken = ''

    saveOk.value = true
    setTimeout(() => (saveOk.value = false), 2000)
  } catch (e: any) {
    error.value = e?.data?.statusMessage ?? e?.message ?? '保存失败'
  } finally {
    saving.value = false
  }
}

// ---- 初始化动作(拉取 star + 提取关键字,原 init.vue 迁入) ----
const triggerError = ref<string | null>(null)
const triggerInfo = ref<string | null>(null)
const pollingJobId = ref<number | null>(null)

async function saveAndInit() {
  triggerError.value = null
  triggerInfo.value = null
  try {
    await saveConfig()
    if (error.value) {
      triggerError.value = error.value
      return
    }
    const r = await $fetch<{ job_id: number }>('/api/stars/refresh', {
      method: 'POST',
      body: { user: config.value.githubUser, no_llm: noLlm.value },
    })
    triggerInfo.value = `已提交 init job #${r.job_id},后台跑中`
    pollJob(r.job_id)
  } catch (e: any) {
    triggerError.value = e?.data?.statusMessage ?? e?.message ?? '初始化失败'
  }
}

async function pollJob(id: number) {
  pollingJobId.value = id
  for (let i = 0; i < 90; i++) {  // 3 分钟上限
    await new Promise(r => setTimeout(r, 2000))
    const j = await $fetch<{ jobs: Array<{ id: number; status: string; result: any; error: string }> }>(
      '/api/jobs'
    )
    const job = j.jobs.find(x => x.id === id)
    if (!job) continue
    if (job.status === 'success') {
      const stars = job.result?.stars ?? '?'
      const kws = job.result?.keywords ?? '?'
      const method = job.result?.kw_method ?? '?'
      triggerInfo.value = `✓ 拉了 ${stars} 个 star,提取了 ${kws} 个关键字 (${method})`
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
  triggerError.value = 'job timeout (3 分钟还没跑完)'
}

onMounted(loadConfig)
</script>

<template>
  <div class="space-y-6">
    <header>
      <h1 class="text-2xl font-bold tracking-tight">设置</h1>
      <p class="text-sm text-muted">LLM + GitHub 配置与初始化</p>
    </header>

    <UAlert v-if="error" color="error" variant="subtle" :title="error" />
    <UAlert v-if="saveOk" color="success" variant="subtle" title="已保存到本地 SQLite" />
    <UAlert v-if="triggerError" color="error" variant="subtle" :title="triggerError" />
    <UAlert v-if="triggerInfo" color="info" variant="subtle" :title="triggerInfo" />

    <!-- LLM -->
    <UCard>
      <template #header>
        <h2 class="text-lg font-semibold flex items-center gap-2">
          <UIcon name="i-lucide-sparkles" /> LLM 关键字提取
        </h2>
      </template>
      <div class="space-y-4">
        <UFormField label="Provider" help="关键字提取用的 LLM provider;留 none = TF-IDF 基线。常用:openai / anthropic / deepseek / dashscope / moonshot / zhipuai">
          <UInput
            v-model="config.llmProvider"
            placeholder="例:deepseek"
          />
        </UFormField>

        <UFormField label="Model" help="模型名;留空走 provider 默认。例:deepseek-chat / gpt-4o-mini / qwen-plus / moonshot-v1-8k">
          <UInput v-model="config.llmModel" placeholder="例:deepseek-chat / gpt-4o-mini" />
        </UFormField>

        <UFormField label="API Key" help="选择 provider 后填写;留空保持不变">
          <UInput
            v-model="config.llmApiKey"
            type="password"
            :placeholder="config.apiKeySet ? '•••••••(已设置)' : 'sk-...'"
          />
        </UFormField>

        <p v-if="config.apiKeySet" class="text-xs text-success">
          ✓ API key 已配置
        </p>
      </div>
    </UCard>

    <!-- GitHub -->
    <UCard>
      <template #header>
        <h2 class="text-lg font-semibold flex items-center gap-2">
          <UIcon name="i-lucide-github" /> GitHub
        </h2>
      </template>
      <div class="space-y-4">
        <UFormField label="GitHub username" required help="Star 拉取 + 初始化的目标用户">
          <UInput v-model="config.githubUser" placeholder="例:hyqskevin" required />
        </UFormField>

        <UFormField label="GitHub Personal Access Token" help="需要 repo:read;留空走 .env 的 GITHUB_TOKEN">
          <UInput
            v-model="config.githubToken"
            type="password"
            :placeholder="config.githubTokenSet ? '•••••••(已设置)' : 'ghp_... 或留空走 .env'"
          />
        </UFormField>
        <p v-if="config.githubTokenSet" class="text-xs text-success text-sm">
          ✓ GitHub token 已配置
        </p>
      </div>
    </UCard>

    <!-- 初始化动作 -->
    <UCard>
      <template #header>
        <h2 class="text-lg font-semibold flex items-center gap-2">
          <UIcon name="i-lucide-rocket" /> 初始化(拉取 Star + 提取关键字)
        </h2>
      </template>
      <div class="space-y-4">
        <UFormField label="跳过 LLM 关键字提取">
          <UToggle v-model="noLlm" />
          <p class="text-xs text-muted mt-1">
            默认用 LLM 提取(更准);勾上走 TF-IDF(免 API key)
          </p>
        </UFormField>

        <div class="flex justify-end">
          <UButton
            color="primary"
            icon="i-lucide-play"
            size="lg"
            :loading="saving || pollingJobId !== null"
            :disabled="saving || pollingJobId !== null || !config.githubUser"
            @click="saveAndInit"
          >
            {{ pollingJobId ? `Init #${pollingJobId} 跑中…` : '保存配置 + 立即拉取' }}
          </UButton>
        </div>
      </div>
    </UCard>

    <UAlert color="info" variant="subtle">
      <template #title>初始化流程</template>
      <ol class="text-sm space-y-1 list-decimal pl-4">
        <li>保存 GitHub user + token 到本地 SQLite <code>settings</code> 表</li>
        <li>提交后台 job → 调用 GitHub API 拉所有 star 仓库 → 写入 <code>stars</code> 表</li>
        <li>用 LLM(默认)/TF-IDF 提取关键字 → 写入 <code>keywords</code> 表</li>
      </ol>
    </UAlert>
    <div class="flex justify-end -mt-4">
      <UButton color="neutral" variant="ghost" icon="i-lucide-save" :loading="saving" :disabled="saving" @click="saveConfig">
        仅保存
      </UButton>
    </div>
  </div>
</template>