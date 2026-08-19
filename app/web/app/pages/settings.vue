<script setup lang="ts">
// pages/settings.vue — 设置页面
// SPEC: docs/superpowers/specs/2026-08-10-page-stars-settings-design.md

useHead({ title: '设置 · ai-github-radar' })

const config = ref({
  radarUser: '',
  pushTarget: 'local',
  feishuWebhook: '',
  smtpHost: '',
  smtpTo: '',
  llmProvider: 'none',
})

const saved = ref(false)

function save() {
  // 阶段二:写 .env / config 文件
  // 阶段一:只展示配置项
  saved.value = true
  setTimeout(() => (saved.value = false), 2000)
}
</script>

<template>
  <div class="space-y-6">
    <header>
      <h1 class="text-2xl font-bold tracking-tight">设置</h1>
      <p class="text-sm text-muted">阶段一:展示配置;阶段二:实际写 .env</p>
    </header>

    <UAlert v-if="saved" color="success" variant="subtle" title="已保存(暂存)" />

    <!-- GitHub -->
    <UCard>
      <template #header>
        <h2 class="text-lg font-semibold flex items-center gap-2">
          <UIcon name="i-lucide-github" /> GitHub
        </h2>
      </template>
      <div class="space-y-3">
        <UFormField label="GitHub username">
          <UInput v-model="config.radarUser" placeholder="例:hyqskevin" />
        </UFormField>
        <p class="text-xs text-muted">
          GITHUB_TOKEN 来自 .env,不在此暴露
        </p>
      </div>
    </UCard>

    <!-- Push -->
    <UCard>
      <template #header>
        <h2 class="text-lg font-semibold flex items-center gap-2">
          <UIcon name="i-lucide-send" /> 推送
        </h2>
      </template>
      <div class="space-y-3">
        <UFormField label="默认推送目标">
          <USelectMenu
            v-model="config.pushTarget"
            :options="[
              { label: 'local', value: 'local' },
              { label: 'feishu', value: 'feishu' },
              { label: 'email', value: 'email' },
              { label: 'stdout', value: 'stdout' }
            ]"
            value-key="value"
          />
        </UFormField>
        <UFormField label="飞书 Webhook URL" help="仅 push_target=feishu 时使用">
          <UInput v-model="config.feishuWebhook" placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..." />
        </UFormField>
        <UFormField label="SMTP 收件人" help="逗号分隔多个收件人">
          <UInput v-model="config.smtpTo" placeholder="alice@example.com,bob@example.com" />
        </UFormField>
        <UFormField label="SMTP 服务器">
          <UInput v-model="config.smtpHost" placeholder="smtp.gmail.com" />
        </UFormField>
      </div>
    </UCard>

    <!-- LLM -->
    <UCard>
      <template #header>
        <h2 class="text-lg font-semibold flex items-center gap-2">
          <UIcon name="i-lucide-sparkles" /> LLM
        </h2>
      </template>
      <UFormField label="关键字提取 provider">
        <USelectMenu
          v-model="config.llmProvider"
          :options="[
            { label: 'none (TF-IDF)', value: 'none' },
            { label: 'OpenAI', value: 'openai' },
            { label: 'Anthropic', value: 'anthropic' },
            { label: 'DeepSeek', value: 'deepseek' },
            { label: 'Qwen (DashScope)', value: 'dashscope' },
            { label: 'Moonshot', value: 'moonshot' },
            { label: 'Zhipu', value: 'zhipuai' }
          ]"
          value-key="value"
        />
      </UFormField>
    </UCard>

    <div class="flex justify-end">
      <UButton color="primary" icon="i-lucide-save" @click="save">保存</UButton>
    </div>
  </div>
</template>