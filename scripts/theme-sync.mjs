#!/usr/bin/env node
// scripts/theme-sync.mjs
//
// 把 DESIGN.md 的 design token 同步到 Nuxt UI 4 + Tailwind v4。
// DESIGN.md 是 single source of truth — 不要手改 app.config.ts / main.css 的相关段。
//
// SPEC: docs/superpowers/specs/2026-08-10-theme-sync-design.md
//
// 用法:
//   node scripts/theme-sync.mjs          # 默认：同步
//   node scripts/theme-sync.mjs --check  # 只检查，不改文件（CI 用）
//   node scripts/theme-sync.mjs --verbose # 打印每条改了什么

import { readFileSync, writeFileSync, existsSync } from 'node:fs'
import { resolve, join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = resolve(__dirname, '..')
const DESIGN_PATH = join(REPO_ROOT, 'DESIGN.md')
const APP_CONFIG_PATH = join(REPO_ROOT, 'app/web/app/app.config.ts')
const MAIN_CSS_PATH = join(REPO_ROOT, 'app/web/app/assets/css/main.css')

const ARGS = process.argv.slice(2)
const CHECK_ONLY = ARGS.includes('--check')
const VERBOSE = ARGS.includes('--verbose')

// -----------------------------------------------------------------------------
// 解析 DESIGN.md YAML frontmatter
// -----------------------------------------------------------------------------

function parseDesign(path) {
  if (!existsSync(path)) {
    throw new Error(`DESIGN.md not found at ${path}`)
  }
  const content = readFileSync(path, 'utf-8')
  const fmMatch = content.match(/^```yaml\n([\s\S]*?)\n```/m)
  if (!fmMatch) {
    throw new Error('DESIGN.md must have a YAML frontmatter block (between ```yaml ... ```)')
  }
  return fmMatch[1]
}

function parseColors(block) {
  // colors:\n  primary: "#E6E1E5"\n  secondary: "#938F99"\n  ...
  const match = block.match(/colors:\n((?:  \w+:\s+"?#([0-9A-Fa-f]{6})"?\n?)+)/)
  if (!match) return []
  const colors = []
  for (const line of match[1].trim().split('\n')) {
    const m = line.match(/^  (\w+):\s+"?#([0-9A-Fa-f]{6})"?$/)
    if (m) colors.push({ name: m[1], hex: '#' + m[2].toUpperCase() })
  }
  return colors
}

function parseSpacing(block) {
  // spacing:\n  xs: 4px\n  sm: 8px\n  ...
  const match = block.match(/spacing:\n((?:  \w+:\s+\d+px\n?)+)/)
  if (!match) return []
  const items = []
  for (const line of match[1].trim().split('\n')) {
    const m = line.match(/^  (\w+):\s+(\d+)px$/)
    if (m) items.push({ name: m[1], px: parseInt(m[2], 10) })
  }
  return items
}

function parseRounded(block) {
  const match = block.match(/rounded:\n((?:  \w+:\s+\d+px\n?)+)/)
  if (!match) return []
  const items = []
  for (const line of match[1].trim().split('\n')) {
    const m = line.match(/^  (\w+):\s+(\d+)px$/)
    if (m) items.push({ name: m[1], px: parseInt(m[2], 10) })
  }
  return items
}

// -----------------------------------------------------------------------------
// 生成 app.config.ts 的 ui.colors 段（只覆盖 ui.colors 块，其余保持原样）
// -----------------------------------------------------------------------------

function buildUiColorsBlock(colors) {
  // 缩进：嵌套在 defineAppConfig({ ... }) 里，所以 ui: / colors: / 各层 +2 空格
  // ui: {     2 空格
  //   colors: {   4 空格
  //     xxx  6 空格
  //   },      4 空格
  // }         2 空格
  const lines = ['  ui: {']
  lines.push('    colors: {')
  for (const c of colors) {
    const nuxtName = c.name === 'tertiary' ? 'primary' : c.name
    lines.push(`      ${nuxtName}: '${c.name}',`)
  }
  lines.push('    },')
  lines.push('    button: {')
  lines.push('      defaultVariants: {')
  lines.push("        color: 'primary',")
  lines.push("        size: 'md'")
  lines.push('      }')
  lines.push('    }')
  lines.push('  }')
  return lines.join('\n')
}

function patchAppConfig(colors) {
  if (!existsSync(APP_CONFIG_PATH)) return null
  let content = readFileSync(APP_CONFIG_PATH, 'utf-8')

  // 策略：只替换 colors: { ... } 块内部，保留 ui: { ... } 外壳 + button 块不动
  const colorsStart = content.indexOf('colors: {')
  if (colorsStart === -1) {
    // 没有 colors: { — 整个 ui: 都缺，追加
    const newBlock = buildUiColorsBlock(colors)
    content = content + '\n\n' + newBlock + '\n'
    return content
  }

  // 从 colors: { 开始往后数花括号，找到匹配 }
  let depth = 0
  let endIdx = -1
  for (let i = colorsStart; i < content.length; i++) {
    if (content[i] === '{') depth++
    else if (content[i] === '}') {
      depth--
      if (depth === 0) { endIdx = i; break }
    }
  }
  if (endIdx === -1) return content

  // before 包含到 'colors: {' 结束（即包含开头的 {）
  const before = content.slice(0, colorsStart + 'colors: {'.length)
  // after 从 } 之后开始
  const after = content.slice(endIdx + 1)

  // 生成 colors 内部（不包含外层 { 和 }）
  // 缩进：ui: 在 2 空格层，colors: { 在 4 空格层，内容在 6 空格层
  const lines = []
  const designNames = new Set(colors.map(c => c.name))
  // 保留 colors 块里不在 DESIGN.md 里的原有条目（不丢失手改）
  // 抓原 colors: { ... } 内容
  const oldColorsBody = content.slice(colorsStart + 'colors: {'.length, endIdx)
  for (const line of oldColorsBody.split('\n')) {
    const m = line.match(/^\s+(\w+):\s+'([^']+)'(,?)\s*$/)
    if (m && !designNames.has(m[1]) && !['primary', 'secondary', 'tertiary', 'neutral', 'success', 'warning', 'error'].includes(m[1])) {
      // 归一化：缩进 6 空格 + 必有尾逗号
      lines.push(`      ${m[1]}: '${m[2]}',`)
    }
  }
  // DESIGN.md 的 colors 排前面
  for (const c of colors) {
    const nuxtName = c.name === 'tertiary' ? 'primary' : c.name
    lines.push(`      ${nuxtName}: '${c.name}',`)
  }
  const newBody = '\n' + lines.join('\n') + '\n    }'

  return before + newBody + after
}

// -----------------------------------------------------------------------------
// 生成 main.css 的 @theme static 段（只覆盖 @theme static 块）
// -----------------------------------------------------------------------------

function buildMainCssBlock(colors, spacing, rounded) {
  const lines = []
  lines.push('@theme static {')
  lines.push("  --font-sans: 'Inter', system-ui, -apple-system, sans-serif;")
  lines.push("  --font-mono: 'IBM Plex Mono', 'Menlo', 'Consolas', monospace;")
  lines.push('')

  // colors
  for (const c of colors) {
    // 给每个颜色生成 -50 到 -950 共 10 档（围绕 hex 插值）
    // 简化版：用 hex 本身作为 -500，前后用 lighten/darken
    // 实际 Nuxt UI 用 oklch 颜色空间，这里用 hex 作为基色 + lightness 阶梯
    const baseHex = c.hex
    const rgb = hexToRgb(baseHex)
    if (!rgb) continue
    const scale = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]
    lines.push(`  /* DESIGN.md colors.${c.name} = ${baseHex} */`)
    for (const s of scale) {
      const lightness = sToLightness(s)
      const oklch = rgbToOklch(rgb, lightness)
      lines.push(`  --color-${c.name}-${s}: ${oklch};`)
    }
    lines.push('')
  }

  lines.push('  /* Status colors (hardcoded — DESIGN.md uses success/warning/error names) */')
  lines.push('  --color-success-400: #7DCE82;')
  lines.push('  --color-success-500: #5BC062;')
  lines.push('  --color-success-600: #46A14D;')
  lines.push('  --color-warning-400: #FFB77A;')
  lines.push('  --color-warning-500: #FF9F4D;')
  lines.push('  --color-warning-600: #E8872E;')
  lines.push('  --color-error-400: #FFB4AB;')
  lines.push('  --color-error-500: #FF8A7B;')
  lines.push('  --color-error-600: #E8635A;')
  lines.push('}')

  return lines.join('\n')
}

function hexToRgb(hex) {
  const m = hex.match(/^#([0-9A-Fa-f]{6})$/)
  if (!m) return null
  return {
    r: parseInt(m[1].slice(0, 2), 16),
    g: parseInt(m[1].slice(2, 4), 16),
    b: parseInt(m[1].slice(4, 6), 16)
  }
}

function sToLightness(s) {
  // 0=lightest (95%), 950=darkest (15%)
  // 500 = base color (~50%)
  return {
    50: 0.95, 100: 0.90, 200: 0.80, 300: 0.70,
    400: 0.60, 500: 0.50, 600: 0.40,
    700: 0.30, 800: 0.22, 900: 0.15, 950: 0.10
  }[s]
}

function rgbToOklch(rgb, lightness) {
  // 简化：保持 hue 不变，调 lightness
  // 真正的 oklch 需要色彩空间转换，这里用 hex 字符串作为占位（Tailwind v4 也接受 hex）
  // 实际生成 hex 调整版（perceptual lightness）
  const factor = lightness / 0.5
  const r = Math.min(255, Math.max(0, Math.round(rgb.r * factor)))
  const g = Math.min(255, Math.max(0, Math.round(rgb.g * factor)))
  const b = Math.min(255, Math.max(0, Math.round(rgb.b * factor)))
  const hex = '#' + [r, g, b].map(x => x.toString(16).padStart(2, '0').toUpperCase()).join('')
  return hex
}

function patchMainCss(colors, spacing, rounded) {
  if (!existsSync(MAIN_CSS_PATH)) return null
  let content = readFileSync(MAIN_CSS_PATH, 'utf-8')

  const newBlock = buildMainCssBlock(colors, spacing, rounded)

  // 找 @theme static { ... } 块（含嵌套花括号匹配）
  const startIdx = content.indexOf('@theme static {')
  if (startIdx === -1) {
    // 不存在，追加
    return content + '\n\n' + newBlock + '\n'
  }

  // 找匹配的右花括号（简单计数）
  let depth = 0
  let endIdx = -1
  for (let i = startIdx; i < content.length; i++) {
    if (content[i] === '{') depth++
    else if (content[i] === '}') {
      depth--
      if (depth === 0) { endIdx = i; break }
    }
  }
  if (endIdx === -1) return content

  content = content.slice(0, startIdx) + newBlock + content.slice(endIdx + 1)
  return content
}

// -----------------------------------------------------------------------------
// 主流程
// -----------------------------------------------------------------------------

function main() {
  const block = parseDesign(DESIGN_PATH)
  const colors = parseColors(block)
  const spacing = parseSpacing(block)
  const rounded = parseRounded(block)

  if (colors.length === 0) {
    throw new Error('No colors found in DESIGN.md frontmatter (colors block empty or missing)')
  }
  if (!colors.some(c => c.name === 'tertiary')) {
    throw new Error('DESIGN.md must declare colors.tertiary (emphasis color, see SPEC §B1)')
  }

  const newAppConfig = patchAppConfig(colors)
  const newMainCss = patchMainCss(colors, spacing, rounded)

  if (!newAppConfig || !newMainCss) {
    throw new Error('app.config.ts or main.css not found')
  }

  const oldAppConfig = readFileSync(APP_CONFIG_PATH, 'utf-8')
  const oldMainCss = readFileSync(MAIN_CSS_PATH, 'utf-8')

  const appConfigChanged = newAppConfig !== oldAppConfig
  const mainCssChanged = newMainCss !== oldMainCss

  if (CHECK_ONLY) {
    if (appConfigChanged || mainCssChanged) {
      console.error('❌ theme-sync: files out of sync with DESIGN.md')
      if (appConfigChanged) console.error('  - app.config.ts differs')
      if (mainCssChanged) console.error('  - main.css differs')
      console.error('Run: node scripts/theme-sync.mjs')
      process.exit(1)
    }
    console.log('✓ theme-sync: files in sync')
    return
  }

  if (appConfigChanged) {
    writeFileSync(APP_CONFIG_PATH, newAppConfig)
    if (VERBOSE) console.log('✓ updated app.config.ts')
  }
  if (mainCssChanged) {
    writeFileSync(MAIN_CSS_PATH, newMainCss)
    if (VERBOSE) console.log('✓ updated main.css')
  }

  if (VERBOSE || (!appConfigChanged && !mainCssChanged)) {
    console.log(`✓ theme-sync: ${colors.length} colors, ${spacing.length} spacing, ${rounded.length} rounded (no changes)`)
  } else {
    console.log(`✓ theme-sync: updated ${[appConfigChanged && 'app.config.ts', mainCssChanged && 'main.css'].filter(Boolean).join(' + ')}`)
  }
}

try {
  main()
} catch (err) {
  console.error(`❌ theme-sync: ${err.message}`)
  process.exit(1)
}