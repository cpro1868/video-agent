#!/usr/bin/env python3
"""Video-Agent-Skill Markdown 输出包装脚本

将 CLI 的 JSON 输出转换为 Markdown 文件。

Usage:
    python scripts/to_markdown.py < input.json > output.md
    python scripts/to_markdown.py input.json output.md
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path


def json_to_markdown(data: dict) -> str:
    """Convert JSON response to Markdown document."""
    if data.get("status") != "success":
        error = data.get("error", {})
        return f"""# 处理失败

**错误码**: {error.get('code', 'UNKNOWN')}
**错误信息**: {error.get('message', 'Unknown error')}
"""

    meta = data["meta"]
    content = data["content"]

    md = f"""# {content['title']}

## 视频信息
- **URL**: {meta['url']}
- **处理策略**: {meta['strategy_used']}
- **语言**: {meta['language']}
- **时长**: {meta.get('duration_seconds', '未知')} 秒
- **生成时间**: {datetime.now().isoformat()}

## 摘要

{content['summary']}

## 关键要点

"""

    for i, point in enumerate(content['key_points'], 1):
        md += f"{i}. {point}\n"

    md += "\n## 详细内容\n\n"
    for section in content.get('detailed_content', []):
        md += f"### {section['section_title']}\n\n{section['content']}\n\n"

    md += f"""## 标签

{'、'.join(content['tags'])}

## 转录片段

```
{content.get('transcript_excerpt', '')[:500]}...
```
"""

    # Append markdown field if present (contains danmaku analysis)
    raw_markdown = content.get('markdown', '')
    if raw_markdown and '##' in raw_markdown:
        # Extract danmaku section if present
        danmaku_idx = raw_markdown.find('## 弹幕')
        if danmaku_idx == -1:
            danmaku_idx = raw_markdown.find('## 整体情感')
        if danmaku_idx > 0:
            md += "\n" + raw_markdown[danmaku_idx:]

    return md


def main() -> int:
    if len(sys.argv) >= 3:
        # File mode
        input_path = Path(sys.argv[1])
        output_path = Path(sys.argv[2])
        raw = input_path.read_bytes().decode('utf-8', errors='ignore')
    elif len(sys.argv) == 2:
        input_path = Path(sys.argv[1])
        raw = input_path.read_bytes().decode('utf-8', errors='ignore')
        output_path = None
    else:
        # Stdin mode
        raw = sys.stdin.read()
        output_path = None

    # Find JSON in raw content (skip stderr noise)
    json_start = raw.rfind('{"status":"success"')
    if json_start == -1:
        json_start = raw.rfind('{"status":"error"')
    if json_start == -1:
        print("Error: No JSON found in input", file=sys.stderr)
        return 1

    data = json.loads(raw[json_start:])
    markdown = json_to_markdown(data)

    if output_path:
        output_path.write_text(markdown, encoding='utf-8')
        print(f"Markdown saved to: {output_path}")
    else:
        print(markdown)

    return 0


if __name__ == "__main__":
    sys.exit(main())
