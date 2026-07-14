"""提取 markdown 中所有 mermaid 代码块，并调用 beautiful-mermaid-renderer 渲染为 PNG。"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"D:\Projects\Python\visual-novel-translator")
MD_FILE = ROOT / "docs" / "讲稿_润色版.md"
OUT_DIR = ROOT / "docs" / "images" / "mermaid"
RENDER_SCRIPT = (
    ROOT
    / ".claude"
    / "skills"
    / "beautiful-mermaid-renderer"
    / "scripts"
    / "render.mjs"
)
SKILL_DIR = ROOT / ".claude" / "skills" / "beautiful-mermaid-renderer"

OUT_DIR.mkdir(parents=True, exist_ok=True)

text = MD_FILE.read_text(encoding="utf-8")
# 匹配 ```mermaid ... ```
pattern = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)
blocks = pattern.findall(text)
print(f"共找到 {len(blocks)} 个 mermaid 代码块")

results = []
for i, code in enumerate(blocks, 1):
    mmd_path = OUT_DIR / f"diagram_{i:02d}.mmd"
    png_path = OUT_DIR / f"diagram_{i:02d}.png"
    mmd_path.write_text(code.strip() + "\n", encoding="utf-8")
    print(f"\n[{i}/{len(blocks)}] 渲染 {mmd_path.name} -> {png_path.name}")
    try:
        proc = subprocess.run(
            [
                "node",
                str(RENDER_SCRIPT),
                str(mmd_path),
                "-o",
                str(png_path),
                "-t",
                "tokyo-night",
            ],
            cwd=str(SKILL_DIR),
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
            errors="replace",
        )
        ok = proc.returncode == 0 and png_path.exists()
        results.append((i, ok, proc.stderr[-500:] if not ok else ""))
        print("  状态:", "成功" if ok else "失败")
        if not ok:
            print("  stdout:", proc.stdout[-500:])
            print("  stderr:", proc.stderr[-500:])
    except Exception as e:
        results.append((i, False, str(e)))
        print(f"  异常: {e}")

print("\n=== 汇总 ===")
for i, ok, err in results:
    print(f"  diagram_{i:02d}: {'OK' if ok else 'FAIL ' + err[:200]}")
