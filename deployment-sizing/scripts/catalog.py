#!/usr/bin/env python3
"""查询打包的模型目录快照。纯标准库，不联网，不读任何凭据。

目录是 data/model-catalog.json，由维护者导出并人工审核后随本 skill 发布。
这个脚本是本 skill 访问模型数据的唯一入口——不要另写代码去连任何在线服务。

用法：
    python3 catalog.py --stats
    python3 catalog.py --category 语言 --open-source
    python3 catalog.py --category 语言 --open-source --modality 图像 --max-params 40
    python3 catalog.py --name Qwen3.6-27B --json
    python3 catalog.py --category Reranker
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

CATALOG = Path(__file__).resolve().parent.parent / "data" / "model-catalog.json"
STALE_DAYS = 45


def load() -> dict:
    if not CATALOG.exists():
        sys.exit(f"找不到目录快照 {CATALOG}——本 skill 没有它就没有候选池，不要改用别的数据源。")
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def age_days(doc: dict) -> int | None:
    ts = doc.get("generated_at")
    if not ts:
        return None
    try:
        gen = datetime.fromisoformat(ts)
    except ValueError:
        return None
    if gen.tzinfo is None:
        gen = gen.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - gen).days


def as_text(value) -> str:
    if isinstance(value, list):
        return " ".join(str(v) for v in value)
    return "" if value is None else str(value)


def match(rec: dict, args) -> bool:
    if args.name and args.name.lower() not in str(rec.get("name", "")).lower():
        return False
    if args.category and args.category not in as_text(rec.get("category")):
        return False
    if args.modality and args.modality not in as_text(rec.get("input_modalities")):
        return False
    if args.developer and args.developer.lower() not in as_text(rec.get("developer")).lower():
        return False
    if args.open_source and not rec.get("open_weights"):
        return False
    if args.self_hostable and not rec.get("self_hostable"):
        return False
    if args.max_params is not None:
        total = rec.get("total_params_b")
        if total is None or total > args.max_params:
            return False
    if args.max_active is not None:
        active = rec.get("active_params_b")
        if active is None or active > args.max_active:
            return False
    if args.since and str(rec.get("released_at") or "") < args.since:
        return False
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description="查询打包的模型目录快照")
    ap.add_argument("--name", help="按模型名子串筛")
    ap.add_argument("--category", help="模型类别：语言 / 视觉理解 / 图像生成 / 视频生成 / 语音 / Embedding / Reranker")
    ap.add_argument("--modality", help="输入模态含某项：文本 / 图像 / 视频 / 音频")
    ap.add_argument("--developer", help="按开发方筛")
    ap.add_argument("--open-source", action="store_true", help="只要开放权重的")
    ap.add_argument("--self-hostable", action="store_true", help="只要可自建的")
    ap.add_argument("--max-params", type=float, help="总参上限 B")
    ap.add_argument("--max-active", type=float, help="激活参数上限 B")
    ap.add_argument("--since", help="发布时间不早于 YYYY-MM-DD")
    ap.add_argument("--stats", action="store_true", help="只打印目录概况")
    ap.add_argument("--json", action="store_true", help="输出 JSON 而非表格")
    ap.add_argument("--limit", type=int, default=60)
    args = ap.parse_args()

    doc = load()
    models = doc.get("models", [])
    days = age_days(doc)

    header = (f"目录快照 {doc.get('generated_at', '?')[:10]}"
              f" · {doc.get('row_count', len(models))} 个模型")
    cutoff = doc.get("language_cutoff")
    if cutoff:
        header += f" · 语言类只含 {cutoff} 及以后发布的"
    if days is not None:
        header += f" · {days} 天前"
        if days > STALE_DAYS:
            header += (f"\n⚠️ 快照已超 {STALE_DAYS} 天。方案里必须注明快照日期；"
                       f"联网可用时按 references/catalog-refresh.md 分模态现搜补最新模型。")

    if args.stats:
        print(header)
        cats: dict[str, int] = {}
        for m in models:
            for c in (m.get("category") if isinstance(m.get("category"), list)
                      else [m.get("category")]):
                if c:
                    cats[str(c)] = cats.get(str(c), 0) + 1
        print("\n按类别：")
        for c, n in sorted(cats.items(), key=lambda x: -x[1]):
            print(f"  {c:<12}{n:>5}")
        oss = [m for m in models if m.get("open_weights") and m.get("self_hostable")]
        print(f"\n开放权重且可自建：{len(oss)}")
        if doc.get("coverage_note"):
            print(f"\n覆盖范围：{doc['coverage_note']}")
        print(f"\n{doc.get('field_note', '')}")
        return

    hits = [m for m in models if match(m, args)]
    hits.sort(key=lambda m: -(m.get("total_params_b") or 0))

    if args.json:
        print(json.dumps({"generated_at": doc.get("generated_at"),
                          "count": len(hits),
                          "models": hits[:args.limit]},
                         ensure_ascii=False, indent=2))
        return

    print(header)
    print(f"命中 {len(hits)} 个" + (f"（显示前 {args.limit}）" if len(hits) > args.limit else ""))
    print(f"\n{'模型':<34}{'开发方':<16}{'类别':<12}{'总参B':>8}{'激活B':>8}"
          f"{'KV KB*':>8}{'开源':>5}{'模态':<18}")
    print("-" * 118)
    for m in hits[:args.limit]:
        kv = m.get("kv_bytes_per_token_base")
        print(f"{str(m.get('name'))[:33]:<34}"
              f"{as_text(m.get('developer'))[:15]:<16}"
              f"{as_text(m.get('category'))[:11]:<12}"
              f"{(m.get('total_params_b') or 0):>8.0f}"
              f"{(m.get('active_params_b') or 0):>8.0f}"
              f"{(kv / 1024 if kv else 0):>8.0f}"
              f"{'是' if m.get('open_weights') else '否':>5} "
              f"{as_text(m.get('input_modalities')):<18}")
    print("\n* KV KB 是目录里的粗估，高估低估都出现过（混合注意力高估至 6.3×，大 head_dim 的 MLA/GQA 低估至 1.8×），只可用于粗筛。")
    print("  入选模型必须按 HuggingFace 上的 config.json 复核——见 references/catalog-query.md。")
    if cutoff and (args.category is None or "语言" in args.category):
        print(f"  语言类只含 {cutoff} 及以后发布的型号。候选不够或要更新的，"
              f"按 references/catalog-refresh.md 现搜补充。")


if __name__ == "__main__":
    main()
