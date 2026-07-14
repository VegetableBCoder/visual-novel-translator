#!/usr/bin/env node
/**
 * render.mjs - Mermaid 代码 -> PNG 图片渲染器
 *
 * 技术栈: beautiful-mermaid (SVG 渲染) + agent-browser (截图)
 *
 * 用法:
 *   node scripts/render.mjs <input.mmd> [options]
 *   echo "graph TD; A-->B" | node scripts/render.mjs [options]
 *
 * 选项:
 *   -o, --output <path>      输出 PNG 路径 (默认: 与输入同名 .png)
 *   -t, --theme <name>       主题名 (默认: tokyo-night)
 *   -w, --width <px>         视口宽度 (默认: 1200)
 *   -s, --scale <n>          设备像素比 (默认: 2, 高清)
 *   --bg <color>             背景色 (覆盖主题, 如 #ffffff)
 *   --fg <color>             前景色 (覆盖主题)
 *   --transparent            透明背景
 *   --keep-html              保留中间 HTML 文件
 *   --help                   显示帮助
 */

import { renderMermaidSVG, THEMES, DEFAULTS } from 'beautiful-mermaid'
import { readFileSync, writeFileSync, existsSync, unlinkSync, mkdirSync } from 'fs'
import { resolve, dirname, basename, extname, join } from 'path'
import { execFileSync, spawnSync } from 'child_process'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const SKILL_DIR = resolve(__dirname, '..')

// ============================================================
// 参数解析
// ============================================================

function parseArgs(argv) {
  const args = {
    input: null,
    output: null,
    theme: 'tokyo-night',
    width: 1200,
    scale: 2,
    bg: null,
    fg: null,
    transparent: false,
    keepHtml: false,
  }

  const positional = []
  let i = 0
  while (i < argv.length) {
    const arg = argv[i]
    switch (arg) {
      case '-o':
      case '--output':
        args.output = argv[++i]
        break
      case '-t':
      case '--theme':
        args.theme = argv[++i]
        break
      case '-w':
      case '--width':
        args.width = parseInt(argv[++i], 10)
        break
      case '-s':
      case '--scale':
        args.scale = parseFloat(argv[++i])
        break
      case '--bg':
        args.bg = argv[++i]
        break
      case '--fg':
        args.fg = argv[++i]
        break
      case '--transparent':
        args.transparent = true
        break
      case '--keep-html':
        args.keepHtml = true
        break
      case '--help':
      case '-h':
        console.log(USAGE_TEXT)
        process.exit(0)
        break
      default:
        if (arg.startsWith('-')) {
          console.error(`未知选项: ${arg}`)
          console.error('使用 --help 查看帮助')
          process.exit(1)
        }
        positional.push(arg)
        break
    }
    i++
  }

  args.input = positional[0] || null
  return args
}

const USAGE_TEXT = `
Mermaid -> PNG 渲染器 (beautiful-mermaid + agent-browser)

用法:
  node scripts/render.mjs <input.mmd> [options]
  echo "graph TD; A-->B" | node scripts/render.mjs [options]

选项:
  -o, --output <path>      输出 PNG 路径 (默认: 与输入同名 .png)
  -t, --theme <name>       主题 (默认: tokyo-night)
  -w, --width <px>         视口宽度 (默认: 1200)
  -s, --scale <n>          像素比 (默认: 2, 高清)
  --bg <color>             背景色 (覆盖主题)
  --fg <color>             前景色 (覆盖主题)
  --transparent            透明背景
  --keep-html              保留中间 HTML
  --help                   显示此帮助

可用主题:
  ${Object.keys(THEMES).join(', ')}

支持的图表类型:
  flowchart (graph TD/LR), sequenceDiagram, stateDiagram-v2,
  classDiagram, erDiagram, xychart-beta
`.trim()

// ============================================================
// 核心函数
// ============================================================

/**
 * 读取 Mermaid 代码 - 从文件或 stdin
 */
function readMermaidCode(inputPath) {
  if (inputPath && inputPath !== '-' && existsSync(inputPath)) {
    return readFileSync(inputPath, 'utf-8').trim()
  }
  // 从 stdin 读取
  return readFileSync(0, 'utf-8').trim()
}

/**
 * 从 mermaid 代码中提取 markdown 代码块内容
 * 支持 ```mermaid ... ``` 和 ```mmd ... ``` 格式
 */
function extractMermaidFromMarkdown(text) {
  // 匹配 ```mermaid 或 ```mmd 代码块
  const match = text.match(/```(?:mermaid|mmd)\s*\n([\s\S]*?)```/)
  if (match) {
    return match[1].trim()
  }
  // 如果整个文本就是纯 mermaid 代码（没有代码块包裹），直接返回
  return text
}

/**
 * 构建渲染选项
 */
function buildRenderOptions(args) {
  const opts = { ...THEMES[args.theme] }

  // 覆盖颜色
  if (args.bg) opts.bg = args.bg
  if (args.fg) opts.fg = args.fg
  if (args.transparent) opts.transparent = true

  return opts
}

/**
 * 将 SVG 包装成完整 HTML 页面
 */
function wrapSvgInHtml(svg, theme, transparent, width) {
  const themeColors = THEMES[theme] || THEMES['tokyo-night']
  const bgColor = transparent ? 'transparent' : (themeColors.bg || '#1a1b26')

  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body {
    width: ${width}px;
    background: ${bgColor};
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding: 40px;
    overflow: visible;
  }
  svg {
    max-width: 100%;
    height: auto;
    display: block;
  }
</style>
</head>
<body>
${svg}
</body>
</html>`
}

/**
 * 获取 agent-browser 可执行文件路径
 */
function getAgentBrowserBin() {
  // 优先使用本地安装的 agent-browser
  const localBin = join(SKILL_DIR, 'node_modules', 'agent-browser', 'bin', 'agent-browser.js')
  if (existsSync(localBin)) {
    return { cmd: 'node', args: [localBin] }
  }

  // 尝试全局安装的 agent-browser
  try {
    const result = spawnSync('agent-browser', ['--version'], { stdio: 'pipe', timeout: 5000 })
    if (result.status === 0) {
      return { cmd: 'agent-browser', args: [] }
    }
  } catch {
    // 全局未安装，继续尝试 npx
  }

  // 最后尝试 npx
  return { cmd: 'npx', args: ['agent-browser'] }
}

/**
 * 执行 agent-browser 命令
 */
function runAgentBrowser(bin, subArgs, timeoutMs = 30000) {
  const fullArgs = [...bin.args, ...subArgs]
  try {
    const result = execFileSync(bin.cmd, fullArgs, {
      stdio: 'pipe',
      timeout: timeoutMs,
      cwd: SKILL_DIR,
      encoding: 'utf-8',
    })
    return { success: true, output: result }
  } catch (err) {
    return { success: false, output: err.stderr || err.message }
  }
}

/**
 * 使用 agent-browser 将 HTML 截图为 PNG
 */
async function screenshotHtmlToPng(htmlPath, pngPath, width, scale) {
  const bin = getAgentBrowserBin()
  const fileUrl = `file:///${htmlPath.replace(/\\/g, '/')}`
  const height = Math.round(width * 0.75) // 4:3 默认比例

  // Step 1: 设置视口大小
  runAgentBrowser(bin, ['set', 'viewport', String(width), String(height), String(scale)], 10000)

  // Step 2: 打开 HTML 文件
  const openResult = runAgentBrowser(bin, ['open', fileUrl], 30000)
  if (!openResult.success) {
    throw new Error(`agent-browser 打开失败: ${openResult.output}`)
  }

  // Step 3: 等待页面加载
  runAgentBrowser(bin, ['wait', '500'], 10000) // 等待字体和渲染

  // Step 4: 截图 (使用 --full 获取完整页面)
  const shotResult = runAgentBrowser(bin, ['screenshot', pngPath, '--full'], 30000)
  if (!shotResult.success) {
    throw new Error(`agent-browser 截图失败: ${shotResult.output}`)
  }

  // Step 5: 关闭浏览器
  runAgentBrowser(bin, ['close'], 10000)

  return pngPath
}

// ============================================================
// 主流程
// ============================================================

async function main() {
  const args = parseArgs(process.argv.slice(2))

  // 读取输入
  let mermaidCode
  try {
    const rawInput = readMermaidCode(args.input)
    mermaidCode = extractMermaidFromMarkdown(rawInput)
  } catch (err) {
    console.error(`错误: 无法读取输入 - ${err.message}`)
    process.exit(1)
  }

  if (!mermaidCode) {
    console.error('错误: 输入为空')
    process.exit(1)
  }

  // 确定输出路径
  let outputPath = args.output
  if (!outputPath) {
    if (args.input && args.input !== '-') {
      const base = basename(args.input, extname(args.input))
      outputPath = resolve(dirname(resolve(args.input)), `${base}.png`)
    } else {
      outputPath = resolve(process.cwd(), 'diagram.png')
    }
  }
  outputPath = resolve(outputPath)

  // 确保输出目录存在
  const outputDir = dirname(outputPath)
  if (!existsSync(outputDir)) {
    mkdirSync(outputDir, { recursive: true })
  }

  // Step 1: 渲染 Mermaid -> SVG
  console.log(`[1/3] 渲染 Mermaid -> SVG (主题: ${args.theme})`)
  const renderOpts = buildRenderOptions(args)
  let svg
  try {
    svg = renderMermaidSVG(mermaidCode, renderOpts)
  } catch (err) {
    console.error(`错误: Mermaid 渲染失败 - ${err.message}`)
    console.error('\n请检查 Mermaid 语法是否正确。')
    console.error('支持的类型: flowchart, sequenceDiagram, stateDiagram-v2, classDiagram, erDiagram, xychart-beta')
    process.exit(2)
  }

  // Step 2: 包装 SVG -> HTML
  console.log(`[2/3] 生成 HTML 包装器`)
  const html = wrapSvgInHtml(svg, args.theme, args.transparent, args.width)
  const htmlPath = outputPath.replace(/\.png$/, '.html')
  writeFileSync(htmlPath, html)

  // Step 3: 截图 HTML -> PNG
  console.log(`[3/3] agent-browser 截图 -> PNG (${args.width}px @ ${args.scale}x)`)
  try {
    await screenshotHtmlToPng(htmlPath, outputPath, args.width, args.scale)
  } catch (err) {
    console.error(`错误: 截图失败 - ${err.message}`)
    process.exit(3)
  }

  // 清理临时 HTML
  if (!args.keepHtml && existsSync(htmlPath)) {
    unlinkSync(htmlPath)
  }

  console.log(`\n✓ 完成! PNG 已保存到: ${outputPath}`)
  if (args.keepHtml) {
    console.log(`  HTML 保留在: ${htmlPath}`)
  }
}

// 运行
main().catch((err) => {
  console.error('未捕获的错误:', err)
  process.exit(99)
})


