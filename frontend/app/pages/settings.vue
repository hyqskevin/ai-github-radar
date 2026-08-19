<script setup lang="ts">
// pages/settings.vue — 设置页面(简化:无推送,只 LLM + GitHub user + 定时任务)
// SPEC: docs/superpowers/specs/2026-08-10-page-stars-settings-design.md

useHead({ title: '设置 · ai-github-radar' })

const config = ref({
  llmProvider: 'none',
  llmModel: '',
  llmApiKey: '',
  apiKeySet: false,
  githubUser: '',
})

const saving = ref(false)
const saveOk = ref(false)
const error = ref<string | null>(null)

const llmProviders = [
  { label: 'none (TF-IDF 关键字提取)', value: 'none' },
  { label: 'OpenAI', value: 'openai' },
  { label: 'Anthropic', value: 'anthropic' },
  { label: 'DeepSeek', value: 'deepseek' },
  { label: 'Qwen (DashScope)', value: 'dashscope' },
  { label: 'Moonshot (Kimi)', value: 'moonshot' },
  { label: 'Zhipu (智谱 GLM)', value: 'zhipuai' },
]

async function loadConfig() {
  try {
    const r = await $fetch<{ provider: string; model: string; api_key_set: boolean }>('/api/settings/llm')
    config.value.llmProvider = r.provider
    config.value.llmModel = r.model
    config.value.apiKeySet = r.api_key_set
  } catch (e: any) {
    error.value = e?.message
  }
}

async function save() {
  saving.value = true
  error.value = null
  saveOk.value = false
  try {
    const body: any = { provider: config.value.llmProvider, model: config.value.llmModel }
    if (config.value.llmApiKey) body.api_key = config.value.llmApiKey
    const r = await $fetch<{ provider: string; model: string; api_key_set: boolean }>('/api/settings/llm', {
      method: 'POST',
      body,
    })
    config.value.llmProvider = r.provider
    config.value.llmModel = r.model
    config.value.apiKeySet = r.api_key_set
    config.value.llmApiKey = ''  // 清空输入框(不重复显示)
    saveOk.value = true
    setTimeout(() => (saveOk.value = false), 2000)
  } catch (e: any) {
    error.value = e?.message ?? 'save failed'
  } finally {
    saving.value = false
  }
}

onMounted(loadConfig)
</script>

<template>
  <div class="space-y-6">
    <header>
      <h1 class="text-2xl font-bold tracking-tight">设置</h1>
      <p class="text-sm text-muted">LLM 配置 + GitHub user</p>
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
        <UFormField label="Provider" help="关键字提取用的 LLM provider;none = TF-IDF 基线">
          <USelectMenu
            v-model="config.llmProvider"
            :options="llmProviders"
            value-key="value"
          />
        </UFormField>

        <UFormField v-if="config.llmProvider !== 'none'" label="Model" help="留空走 provider 默认">
          <UInput v-model="config.llmModel" placeholder="例:deepseek-chat / gpt-4o-mini" />
        </UFormField>

        <UFormField v-if="config.llmProvider !== 'none'" label="API Key" :help="config.apiKeySet ? '已设置(留空保持不变)' : '在 .env 配也可'">
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
      <UFormField label="GitHub username" help="Star 拉取 + trending 扫描范围">
        <UInput v-model="config.githubUser" placeholder="例:hyqskevin" />
      </UFormField>
      <p class="text-xs text-muted mt-2">
        GITHUB_TOKEN 来自 .env,不在此暴露
      </p>
    </UCard>

    <div class="flex justify-end">
      <UButton color="primary" icon="i-lucide-save" :loading="saving" :disabled="saving" @click="save">
        保存
      </UButton>
    </div>
  </div>
</template>