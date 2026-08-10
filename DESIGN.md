# DESIGN.md — ai-github-radar 设计系统

> 基于 [google-labs-code/design.md](https://github.com/google-labs-code/design.md) 规范（Apache-2.0）。
> 一份文件 = machine-readable tokens（YAML front matter）+ human-readable rationale（markdown body）。
> 给 Nuxt 4 / Nuxt UI / Vue 组件用，**所有颜色 / 字体 / 间距 / 阴影 / 圆角必须从这里取**。

```yaml
version: alpha
name: ai-github-radar
description: 冷静、克制、工具感的暗色优先 GitHub 项目发现 dashboard。
colors:
  primary: "#E6E1E5"
  secondary: "#938F99"
  tertiary: "#4FD8EB"
  neutral: "#1D1B20"
  success: "#7DCE82"
  warning: "#FFB77A"
  error: "#FFB4AB"
typography:
  h1:
    fontFamily: Inter
    fontSize: 2rem
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  h2:
    fontFamily: Inter
    fontSize: 1.5rem
    fontWeight: 600
    lineHeight: 1.25
  h3:
    fontFamily: Inter
    fontSize: 1.125rem
    fontWeight: 600
    lineHeight: 1.3
  body-md:
    fontFamily: Inter
    fontSize: 0.875rem
    fontWeight: 400
    lineHeight: 1.5
  body-sm:
    fontFamily: Inter
    fontSize: 0.75rem
    fontWeight: 400
    lineHeight: 1.4
  mono:
    fontFamily: "IBM Plex Mono"
    fontSize: 0.875rem
    fontWeight: 400
    lineHeight: 1.5
rounded:
  sm: 4px
  md: 8px
  lg: 16px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  x2l: 48px
elevation:
  "0": "none"
  "1": "0 1px 3px rgba(0,0,0,0.12)"
  "2": "0 4px 12px rgba(0,0,0,0.16)"
  "3": "0 12px 24px rgba(0,0,0,0.20)"
components:
  button-primary:
    backgroundColor: "{colors.tertiary}"
    textColor: "#0F1419"
    rounded: "{rounded.sm}"
    padding: "12px 16px"
    typography: "{typography.body-md}"
  button-primary-hover:
    backgroundColor: "{colors.tertiary}"
    textColor: "#FFFFFF"
    rounded: "{rounded.sm}"
    padding: "12px 16px"
  button-primary-disabled:
    backgroundColor: "{colors.secondary}"
    textColor: "{colors.neutral}"
    rounded: "{rounded.sm}"
    padding: "12px 16px"
  card:
    backgroundColor: "{colors.neutral}"
    rounded: "{rounded.md}"
    padding: "{spacing.md}"
  input-search:
    backgroundColor: "{colors.neutral}"
    textColor: "{colors.primary}"
    rounded: "{rounded.md}"
    padding: "12px 16px"
  chip-keyword:
    backgroundColor: "{colors.tertiary}"
    textColor: "{colors.tertiary}"
    rounded: "{rounded.sm}"
    padding: "2px 8px"
    typography: "{typography.body-sm}"
```

---

## 概述

ai-github-radar 是**单人单机的内部工具**——GitHub 项目发现 CLI 配 Web dashboard。
设计基调：

- **冷静、克制、工具感**——不抢戏，让推荐内容本身说话
- **暗色优先**——开发者工具默认暗色，亮色自动跟随系统
- **WCAG AA 合规**——文本对比度 ≥ 4.5:1
- **一个强调色**——所有"操作"（star / 订阅 / 推送）用同一个 tertiary 颜色，不堆颜色
- **低饱和度**——长期盯着看，不刺眼

---

## 颜色

| Token | 值 | 用途 |
|---|---|---|
| `colors.primary` | `#E6E1E5` | 暗色模式主文字 / 亮色模式主背景 |
| `colors.secondary` | `#938F99` | 次要文字 / 占位符 / icon 静默态 |
| `colors.tertiary` | `#4FD8EB` | **唯一强调色**：CTA、链接、匹配关键字高亮 |
| `colors.neutral` | `#1D1B20` | 暗色模式主背景 / 亮色模式主文字 |
| `colors.success` | `#7DCE82` | 已推送 / 同步成功 |
| `colors.warning` | `#FFB77A` | Token 失效 / GitHub 限流 |
| `colors.error` | `#FFB4AB` | 401 / 网络断开 |

**配色原则**：UI 90% 用 `primary` / `secondary` / `neutral` 三色，`tertiary` 只用在 ≥ 5px 范围内可点元素（按钮 / 链接 / 命中关键字下划线）。

---

## 字体

| Token | 用途 |
|---|---|
| `typography.h1` | 页面标题（32px / 700） |
| `typography.h2` | 章节标题（24px / 600） |
| `typography.h3` | 小节标题（18px / 600） |
| `typography.body-md` | 正文（14px / 400） |
| `typography.body-sm` | 辅助文字 / meta（12px / 400） |
| `typography.mono` | repo 名 / 路径 / hash（IBM Plex Mono） |

字体族：**Inter**（UI）+ **IBM Plex Mono**（代码 / ID）。
等宽字号跟 body-md 保持 14px，GitHub URL、JSON 字段值都用 mono。

---

## 间距

| Token | 值 | 适用 |
|---|---|---|
| `spacing.xs` | 4px | 文字行内 gap |
| `spacing.sm` | 8px | icon + 文字 |
| `spacing.md` | 16px | 卡片内 padding |
| `spacing.lg` | 24px | 卡片间 gap |
| `spacing.xl` | 32px | 页面 section 间距 |
| `spacing.2xl` | 48px | 页面顶部留白 |

**4 的倍数系统**——所有间距 token 都是 4 的倍数（4/8/16/24/32/48）。
不要写 `13px`、`17px` 这种。

---

## 圆角

| Token | 值 | 适用 |
|---|---|---|
| `rounded.sm` | 4px | tag / chip / 小按钮 |
| `rounded.md` | 8px | 卡片 / 输入框 |
| `rounded.lg` | 16px | 模态框 / 大卡片 |

---

## 阴影

| Token | 值 | 适用 |
|---|---|---|
| `elevation.0` | `none` | 默认 |
| `elevation.1` | `0 1px 3px rgba(0,0,0,.12)` | 悬浮卡片 |
| `elevation.2` | `0 4px 12px rgba(0,0,0,.16)` | 模态框 |
| `elevation.3` | `0 12px 24px rgba(0,0,0,.20)` | 推送通知 |

暗色模式下阴影透明度上调到 0.4（不然看不见）。

---

## 组件

### button-primary

- `backgroundColor`: `{colors.tertiary}`
- `textColor`: `#0F1419`（与 tertiary 对比度 7.2:1，AAA 合规）
- `rounded`: `{rounded.sm}`
- `padding`: `12px`
- `typography`: `{typography.body-md}`（fontWeight 500）

**hover/pressed/disabled 都是 sibling key**：

### button-primary-hover

- `backgroundColor`: `{colors.tertiary}`
- `textColor`: `#FFFFFF`
- 加 elevation.1

### button-primary-disabled

- `backgroundColor`: `{colors.secondary}`
- `textColor`: `{colors.neutral}`
- opacity: 0.4

### card

- `backgroundColor`: `{colors.neutral}`
- `rounded`: `{rounded.md}`
- `padding`: `{spacing.md}`
- `elevation`: `{elevation.1}`

### input-search

- `backgroundColor`: `{colors.neutral}`
- `textColor`: `{colors.primary}`
- `placeholderColor`: `{colors.secondary}`
- `rounded`: `{rounded.md}`
- `padding`: `12px 16px`
- `border`: `1px solid {colors.secondary}`（focus 时变 tertiary）

### chip-keyword

- `backgroundColor`: `{colors.tertiary}` + opacity 0.15
- `textColor`: `{colors.tertiary}`
- `rounded`: `{rounded.sm}`
- `padding`: `2px 8px`
- `typography`: `{typography.body-sm}`（fontWeight 500）

命中关键字时用 chip-keyword，未命中用 chip-keyword-muted。

---

## Do's and Don'ts

### ✅ Do

- 间距 token 走 4 的倍数（spacing.xs 到 spacing.2xl）
- 唯一强调色：`tertiary`，不创造额外 accent
- 暗色 / 亮色主题通过 token 自动切换，组件代码里不写死颜色
- 所有交互元素给 hover 状态（`*-hover` sibling）
- WCAG 对比度：正文 4.5:1，大字 3:1

### ❌ Don't

- 不要在组件里写 `#4FD8EB`——必须 `{colors.tertiary}`
- 不要用 `13px` `17px` 这种非 4 倍数间距
- 不要加新的强调色（保留唯一 tertiary）
- 不要给按钮嵌套 hover（`*hover.hover` 是错的）
- 不要在亮色主题用纯白背景（用 `{colors.primary}`）

---

## 导出

```bash
# Tailwind theme（Nuxt UI / Tailwind 用）
npx -y @google/design.md export --format tailwind DESIGN.md > app/web/tailwind.theme.json

# W3C DTCG（任何工具消费）
npx -y @google/design.md export --format dtcg DESIGN.md > tokens.json

# 校验 + WCAG
npx -y @google/design.md lint DESIGN.md
```