#!/usr/bin/env python3
"""编队测算：给定硬件与一组模型，算 KV 池 / 并发包络 / 场景配比 / 重排代价。

编队形态不写死。一个编队 = 任意数量的模型 × 各自的副本数：
  - 单机塞大模型   → 1 个大模型 + 几个小模型，各 1 副本
  - 显存宽裕       → 每场景一个专用模型
  - 多机 / 大显存   → 同一模型开多副本做负载均衡与实例级冗余
形态怎么选见 SKILL.md「编队形态怎么定」。

⚠️ __main__ 里的模型只是**格式示例**，不是候选池。候选池查 data/model-catalog.json
   （用 scripts/catalog.py），且每个入选模型的 kv_kb 要按 HF 上 config.json 的
   layer_types 复核（那列高估低估都出现过，最多高估 6.3×、低估 1.8×）。

口径：roofline 系数 C_dec 11.4 / MFU 0.4 / SLA 降额 0.6 / 单用户 20 tok/s。
输出是**物理包络**，不是可承诺并发——真实工程可承载约低一个数量级。
对外承诺的并发与 SLA 数字需由供应商按实测工程数据出具或做 PoC 实测。
"""

from __future__ import annotations
import argparse
from dataclasses import dataclass

HARDWARE = {
    "h20-141": dict(cards=8, hbm_per_card=141e9, bw_per_card=4.8e12,
                    fp8_tflops=296e12, bf16_tflops=148e12, fp4_tflops=0,
                    note="Hopper，无原生 FP4"),
    "h20-96":  dict(cards=8, hbm_per_card=96e9, bw_per_card=4.8e12,
                    fp8_tflops=296e12, bf16_tflops=148e12, fp4_tflops=0,
                    note="同带宽同算力，仅容量减少"),
    # B300 取 NVIDIA 公开 datasheet 的**密集**口径；
    # 容量按 270GB 保守取（部分 SKU 标 288GB，以实测 nvidia-smi 为准，用 --hbm 覆盖）。
    "b300-270": dict(cards=8, hbm_per_card=270e9, bw_per_card=8.0e12,
                     fp8_tflops=9.0e15, bf16_tflops=4.5e15, fp4_tflops=13.5e15,
                     note="Blackwell Ultra，原生 NVFP4；公开规格口径"),
    # 加新硬件：单卡显存 / 单卡带宽 / FP8 与 BF16 与 FP4 算力 / 卡数（无原生 FP4 填 fp4_tflops=0）
}

RUNTIME_RESERVE = 0.08
C_DEC, MFU, SLA_DERATE, TOK_S_USER = 11.4, 0.4, 0.6, 20


@dataclass
class M:
    """weight_gb 用 HF safetensors 实测；kv_kb 按 config.json 的 layer_types 复核。"""
    name: str
    weight_gb: float
    active_b: float
    kv_kb: float
    ctx: int
    lic: str = ""
    role: str = ""
    bytes_per_param: float = 1.0   # FP8=1 / INT4 weight-only=0.5 / BF16=2 / NVFP4=0.5
    modality: str = "文本"
    # True = 权重与激活都是 FP4（如 MoE 专家 NVFP4 发布），预填充走 FP4 张量核，
    # 且只能落在有原生 FP4 的卡上。INT4 weight-only 保持 False：激活仍是 FP8/BF16。
    native_fp4: bool = False


@dataclass
class HW:
    cards: int; hbm_per_card: float; bw_per_card: float
    fp8_tflops: float; bf16_tflops: float; fp4_tflops: float = 0.0; note: str = ""

    @property
    def total(self): return self.cards * self.hbm_per_card
    @property
    def usable(self): return self.total * (1 - RUNTIME_RESERVE)
    @property
    def bw_total(self): return self.cards * self.bw_per_card

    def tp_cap(self, tp: int): return tp * self.hbm_per_card * (1 - RUNTIME_RESERVE)
    def decode_tok_s(self, m): return C_DEC * self.bw_total / (m.active_b * 1e9 * m.bytes_per_param)
    def compute_tflops(self, m):
        """预填充按激活精度取算力：原生 FP4 模型走 FP4 张量核，其余走 FP8。"""
        return self.fp4_tflops if (m.native_fp4 and self.fp4_tflops) else self.fp8_tflops
    def prefill_tok_s(self, m): return MFU * self.cards * self.compute_tflops(m) / (2 * m.active_b * 1e9)
    def fp4_blocked(self, m): return m.native_fp4 and not self.fp4_tflops
    def conc_cap(self, m):
        hi = self.decode_tok_s(m) / TOK_S_USER
        return hi * SLA_DERATE, hi
    def dense_card_s(self, params_b, tokens):
        return 2 * params_b * 1e9 * tokens / (self.bf16_tflops * MFU)


def kv_gb(m: M, ctx: int, conc: int): return ctx * m.kv_kb * 1024 * conc / 1e9


def placement(hw: HW, m: M) -> str:
    """这个模型能落到什么 TP 形态、有没有实例级冗余。"""
    for tp in (1, 2, 4, 8):
        if m.weight_gb * 1e9 <= hw.tp_cap(tp):
            reps = hw.cards // tp
            return (f"TP{tp} × 最多 {reps} 副本"
                    + ("，有实例级冗余" if reps >= 2 else "，单实例无冗余"))
    return "单机装不下"


def report(hw: HW, fleets: dict, retrieval: dict | None = None, elim=()):
    retrieval = retrieval or {}
    ret_gb = sum(retrieval.values())
    print("=" * 92)
    print(f"{hw.cards}×{hw.hbm_per_card/1e9:.0f}GB · 整机 {hw.total/1e9:,.0f} GB / "
          f"可用 {hw.usable/1e9:,.0f} GB · 带宽 {hw.bw_per_card/1e12:.1f} TB/s·卡"
          + (f" · {hw.note}" if hw.note else ""))
    print("=" * 92)

    for title, f in fleets.items():
        entries = f["models"]                      # [(M, replicas), ...]
        alloc = f["alloc"]                         # [(model_name, scene, ctx, conc), ...]
        w = sum(m.weight_gb * n for m, n in entries) + ret_gb
        pool = hw.usable / 1e9 - w
        print(f"\n### {title}\n")
        print(f"{'模型':<20}{'角色':<20}{'副本':>5}{'权重':>9}{'精度':>6}{'模态':>14}"
              f"{'激活':>7}{'KV/tok':>9}{'解码 tok/s':>12}{'并发封顶':>15}")
        for m, n in entries:
            lo, hi = hw.conc_cap(m)
            prec = ("FP4" if m.native_fp4 else
                    {1.0: "FP8", 0.5: "INT4", 2.0: "BF16"}.get(m.bytes_per_param, "?"))
            print(f"{m.name:<20}{m.role:<20}{n:>5}{m.weight_gb*n:>7.0f}GB{prec:>6}{m.modality:>14}"
                  f"{m.active_b:>6.0f}B{m.kv_kb:>8.0f}KB{hw.decode_tok_s(m):>12,.0f}"
                  f"{lo:>7,.0f}–{hi:<7,.0f}")
        for m, _ in entries:
            if hw.fp4_blocked(m):
                print(f"  ⚠ {m.name} 是原生 FP4 权重，本卡无原生 FP4："
                      f"要么上转 FP8（体积约 ×2，此处 {m.weight_gb:.0f}GB 已失效，需重算），"
                      f"要么靠引擎反量化 kernel，列为 PoC 实测项")
        if retrieval:
            print(f"{'检索侧':<20}{'知识库':<20}{'':>5}{ret_gb:>7.1f}GB{'BF16':>6}"
                  f"   （{' + '.join(retrieval)}）")
        print(f"\n  权重合计 {w:,.1f} GB / 可用 {hw.usable/1e9:,.0f} GB → KV 池 {pool:,.0f} GB"
              + ("" if pool > 0 else "  ✗ 装不下"))
        if pool <= 0:
            continue
        for m, n in entries:
            if m.weight_gb / hw.hbm_per_card * 1e9 > 0.15:     # 只对吃显存的模型提示形态
                print(f"  {m.name} 部署形态：{placement(hw, m)}")

        used = 0.0
        print(f"\n  {'承载模型':<20}{'场景':<26}{'档位':>7}{'并发':>8}{'KV':>10}")
        by = {m.name: m for m, _ in entries}
        lanes: dict[str, int] = {}
        for name, scene, ctx, conc in alloc:
            g = kv_gb(by[name], ctx, conc); used += g
            lanes[name] = lanes.get(name, 0) + conc
            print(f"  {name:<20}{scene:<26}{ctx//1024:>5}K{conc:>8,}{g:>8.0f}GB")
        total_lanes = sum(lanes.values())
        print(f"  {'合计':<46}{used:>16.0f}GB / {pool:.0f}GB "
              f"（{'✓ 装得下' if used <= pool else '✗ 超了'}）")
        print("  路数分布：" + "、".join(
            f"{k} {v:,} 路（{v/total_lanes:.0%}）" for k, v in
            sorted(lanes.items(), key=lambda x: -x[1])))
        wshare = {m.name: m.weight_gb * n / w for m, n in entries}
        print("  权重占比：" + "、".join(
            f"{k} {v:.0%}" for k, v in sorted(wshare.items(), key=lambda x: -x[1])))

        for name in lanes:
            m = by[name]
            lo, hi = hw.conc_cap(m)
            print(f"\n  {name} 包络（KV 池 {pool:.0f} GB 全给它时）：")
            print(f"    {'上下文':>8}{'KV 约束':>10}{'实际可达':>18}{'单请求预填充':>14}")
            for ctx in (8192, 32768, 65536, 131072, 262144, 1048576):
                if ctx > m.ctx: continue
                kvc = pool * 1e9 / (ctx * m.kv_kb * 1024)
                print(f"    {str(ctx//1024)+'K':>8}{kvc:>10,.0f}"
                      f"{min(kvc,lo):>9,.0f}–{min(kvc,hi):<8,.0f}"
                      f"{ctx/hw.prefill_tok_s(m):>12.1f}s")

    if elim:
        print("\n" + "=" * 92); print("装载筛查：装不下 / 这张卡跑不了其原生精度"); print("=" * 92)
        for n, why in elim: print(f"  ✗ {n:<26}{why}")

    print("\n" + "=" * 92); print("知识库重排代价（BF16，每对约 550 token）"); print("=" * 92)
    print(f"{'重排方案':<42}{'卡·秒/查询':>12}{'0.5 QPS':>12}{'1 QPS':>10}{'2 QPS':>10}")
    P = 550
    # 按候选池里实际有的 reranker 尺寸改这里——代价随参数量线性变化
    for label, cs in [
        ("8B Top-50", hw.dense_card_s(8, 50*P)), ("8B Top-20", hw.dense_card_s(8, 20*P)),
        ("0.568B Top-50", hw.dense_card_s(0.568, 50*P)), ("0.568B Top-20", hw.dense_card_s(0.568, 20*P)),
        ("两级 0.6B Top-50 → 8B Top-8", hw.dense_card_s(0.6, 50*P)+hw.dense_card_s(8, 8*P)),
    ]:
        print(f"{label:<42}{cs:>12.2f}" + "".join(f"{cs*q/hw.cards:>11.0%}" for q in (0.5, 1.0, 2.0)))
    print("\n百分比 = 该 QPS 下重排占整机算力比例。折算到人：办公占空比约 8.3%，1 路 ≈ 10–15 坐席。")


# ============ 以下为格式示例，按实际场景改 ============
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--hardware", default="h20-141", choices=list(HARDWARE))
    ap.add_argument("--bandwidth", type=float, help="覆盖单卡带宽 B/s")
    ap.add_argument("--hbm", type=float, help="覆盖单卡显存 B（按实测 nvidia-smi 取）")
    a = ap.parse_args()
    cfg = dict(HARDWARE[a.hardware])
    if a.bandwidth: cfg["bw_per_card"] = a.bandwidth
    if a.hbm: cfg["hbm_per_card"] = a.hbm
    hw = HW(**cfg)

    BIG = M("MiniMax M3", 443.7, 23, 60.0, 1_048_576, "MiniMax Community", "大模型",
            modality="文本+图像+视频")
    MOE = M("Qwen3.6-35B-A3B", 36, 3, 10.0, 262_144, "Apache-2.0", "吞吐主力", modality="文本+图像+视频")
    DENSE = M("Qwen3.6-27B", 27.8, 27, 32.0, 262_144, "Apache-2.0", "质量档", modality="文本+图像+视频")

    report(hw, fleets={
        # 形态一：单机紧约束 → 1 大 + N 小，各 1 副本
        "编队 A：大模型位 + 小模型（单机紧约束）": {
            "models": [(BIG, 1), (MOE, 1), (DENSE, 1)],
            "alloc": [("MiniMax M3", "复杂办公 / 图文混合", 8192, 300),
                      ("MiniMax M3", "跨文档 / 长材料", 32768, 60),
                      ("Qwen3.6-35B-A3B", "通用办公问答", 8192, 500),
                      ("Qwen3.6-27B", "质量档办公", 8192, 80)]},
        # 形态二：显存宽裕 → 不设大模型位，主力模型开多副本
        "编队 B：无大模型位，主力多副本": {
            "models": [(MOE, 3), (DENSE, 2)],
            "alloc": [("Qwen3.6-35B-A3B", "通用办公问答", 8192, 2000),
                      ("Qwen3.6-35B-A3B", "知识库问答", 32768, 400),
                      ("Qwen3.6-27B", "质量档办公 / 图文", 8192, 400)]},
    },
    retrieval={"bge-m3": 1.2, "bge-reranker-v2-m3": 1.2},
    elim=[("某 FP4 专家模型", "Hopper 无原生 FP4；上转 FP8 后体积翻倍")])
