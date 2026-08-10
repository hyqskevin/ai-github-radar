// app.config.ts — 把 DESIGN.md 的 token 注入 Nuxt UI
//
// 来源：../DESIGN.md（design.md 规范）
// 通过 `npx -y @google/design.md export --format tailwind` 导出到 app/assets/css/tokens.json
// 这里手动映射给 Nuxt UI 的 ui.colors（v4 之后直接接 CSS 变量）

import type { Direction } from '@nuxt/ui'

export default defineAppConfig({
  dir: 'ltr' as Direction,

  toaster: {
    position: 'bottom-right' as const,
    duration: 4000,
    max: 5,
    expand: true,
    disableSwipe: false
  },

  // 颜色来自 DESIGN.md
  // primary: secondary 色（中性、低饱和、不抢戏）
  // neutral: 主文字色（暗色模式）
  // 注意：tertiary (强调色 #4FD8EB) 通过 CSS 变量 --ui-color-primary 注入，
  //       通过 Tailwind 的 arbitrary value 在组件里使用（如 text-tertiary）
  ui: {
    colors: {
      primary: 'neutral',
      secondary: 'secondary',
      success: 'success',
      warning: 'warning',
      error: 'error',
      info: 'primary'
    },
    button: {
      defaultVariants: {
        color: 'primary',
        size: 'md'
      }
    }
  }
})