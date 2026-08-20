<script setup lang="ts">
// pages/settings.vue — 设置页(只管 LLM + GitHub 配置;拉 star 在 /stars,提关键字在 /keywords)
// T139: 统一管理 LLM + GitHub 配置(含 token);配置回填 /api/settings/all
// T144: 拆分 init 任务 → /stars 拉取 + /keywords 提取
// SPEC: docs/superpowers/specs/2026-08-19-settings-merge-init-design.md,
// docs/superpowers/specs/2026-08-20-split-init-into-stars-and-keywords-design.md

useHead({ title: '设置 · ai-github-radar' })

const config = ref({
  llmProvider: 'none',
  llmModel: '',
  llmApiKey: '',
  llmBaseUrl: '',
  apiKeySet: false,
  githubUser: '',
  githubToken: '',
  githubTokenSet: false,
})

const saving = ref(false)
const saveOk = ref(false)
const error = ref<string | null>(null)

async function loadConfig() {
  try {
    const r = await $fetch<{
      llm_provider: string
      llm_model: string
      llm_api_key_set: boolean
      llm_base_url?: string
      github_user: string
      github_token_set: boolean
    }>('/api/settings/all')
    config.value.llmProvider = r.llm_provider || 'none'
    config.value.llmModel = r.llm_model || ''
    config.value.llmBaseUrl = r.llm_base_url || ''
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
    if (config.value.llmBaseUrl) llmBody.base_url = config.value.llmBaseUrl
    const llm = await $fetch<{ provider: string; model: string; api_key_set: boolean; base_url: string }>('/api/settings/llm', {
      method: 'POST',
      body: llmBody,
    })
    config.value.llmProvider = llm.provider
    config.value.llmModel = llm.model
    config.value.apiKeySet = llm.api_key_set
    config.value.llmBaseUrl = llm.base_url || ''
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

// ---- T144: 初始化动作已迁出 — 拉 star 入口在 /stars 页;提取关键字入口在 /keywords 页 ----

onMounted(loadConfig)
</script>

<template>
  <div class="space-y-6">
    <header>
      <h1 class="text-2xl font-bold tracking-tight">设置</h1>
      <p class="text-sm text-muted">LLM + GitHub 配置</p>
    </header>

    <UAlert v-if="error" color="error" variant="subtle" :title="error" />
    <UAlert v-if="saveOk" color="success" variant="subtle" title="已保存到本地 SQLite" />

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

        <UFormField v-if="config.llmProvider && config.llmProvider !== 'none'" label="Base URL" help="OpenAI 兼容 API 地址;留空走 provider 默认(MiniMax / Qwen 自建网关 / Azure 等可填自定义)">
          <UInput
            v-model="config.llmBaseUrl"
            placeholder="例:https://api.minimax.chat/v1"
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

        <div class="flex justify-end pt-2">
          <UButton
            color="primary"
            variant="solid"
            icon="i-lucide-save"
            :loading="saving"
            :disabled="saving"
            @click="saveConfig"
          >
            保存 LLM 配置
          </UButton>
        </div>
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

        <div class="flex justify-end pt-2">
          <UButton
            color="primary"
            variant="solid"
            icon="i-lucide-save"
            :loading="saving"
            :disabled="saving"
            @click="saveConfig"
          >
            保存 GitHub 配置
          </UButton>
        </div>
      </div>
    </UCard>

    <!-- T144: 拉取 Star 在 /stars 页;提取关键字在 /keywords 页;本设置页只管配置 -->
  </div>
</template>