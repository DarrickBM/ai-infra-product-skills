# 补目录：分模态现搜最新模型

`data/model-catalog.json` 是快照，**语言类只保留窗口内发布的型号**（顶层
`language_cutoff` 写明截止日）。语言模型迭代太快，固化一份全量历史库只会让方案引用
两年前的型号；其余模态迭代慢，不设窗口。

代价是：**截止日之后发布的模型不在目录里。** 这一章讲怎么把它们找回来。

## 什么时候要搜

任一条成立就搜：

- 快照距今超过 30 天（`catalog.py` 会打印天数并标出）
- 主场景是语言类——语言类是被裁剪最狠的那一档
- 客户点名了一个目录里没有的模型
- 候选池筛完只剩两三个，不够组出「主推 + 保底 + 能力上限」三档编队

**工具不可用（无网络、无 `curl` / `tvly`）就跳过**，在方案里写明「目录快照于
YYYY-MM-DD，此后新模型未检索，需供应商补充」。**不要凭记忆列新模型**——记忆里的
版本号、参数量、许可几乎一定是错的。

## 按模态搜

每个模态一个公开榜单源。**语言类必搜质量榜 + 用量榜两个**，其余模态一个榜够用。

| 模态 | 榜单源 | 入口 |
|---|---|---|
| 语言（质量） | Artificial Analysis Intelligence Index | `https://artificialanalysis.ai/leaderboards/models` |
| 语言（用量） | OpenRouter rankings | `https://openrouter.ai/api/frontend/v1/rankings/models?view=month` |
| 图像生成 | AA Image Arena | `https://artificialanalysis.ai/image/leaderboard/text-to-image` |
| 视频生成 | AA Video Arena | `https://artificialanalysis.ai/video/leaderboard/text-to-video` |
| 语音 TTS | AA Speech Arena | `https://artificialanalysis.ai/text-to-speech/leaderboard` |
| ASR | AA Speech-to-Text，取 AA-WER Index（**越低越好**） | `https://artificialanalysis.ai/speech-to-text` |
| OCR / 文档解析 | OmniDocBench | `https://raw.githubusercontent.com/opendatalab/OmniDocBench/main/README.md` |
| Embedding | MTEB（走后端 API，前端是 SPA 抓不到） | `https://mteb-leaderboard-backend.hf.space/v1/benchmarks/{name}/scores` |

榜单页的解析踩坑与 `curl` 用法见 `references/model-evidence.md`——同一批源，同一套坑。

OpenRouter 另有一个免 key 端点给上架时间、定价、上下文长度：

```bash
curl -s "https://openrouter.ai/api/v1/models"
```

### 四个会算错的坑

1. **rankings 必须带 `?view=month`。** 默认视图只回近 6 天，窗口对不上，会漏掉大半新模型。
2. **按 `model_permaslug` 聚合。** 同一模型的 free / standard 变体是独立条目，要求和；
   permaslug 可能带日期后缀，是 `-YYYYMMDD` 八位无连字符，正则写 `-\d{8}$` 做前缀匹配。
3. **匿名 `stealth/*` 条目要并回本尊。** 它们在榜上是独立 permaslug，不会自动合并，
   揭晓后不合并会同时低估两边的排名。判定别名只能靠官方公告或新闻，端点里没有指向
   本尊的字段。**仍未揭晓的，开放权重一律记「否」。**
4. **按模型发布时间筛，不是上架时间。** 上架晚于发布是常态，按上架时间筛会把刚发布的
   模型判成旧的。

### 开源与否必须验，不能凭印象

```bash
curl -s "https://huggingface.co/api/models?search=<模型名>&limit=4"
```

HF 官方 org 下有可下载权重才算开放权重。**API-only 的加速端点不算**，榜单页上的
「open weights」标记也要复核。

**这一条是硬闸门，不只是隐私档的事。** 目录本身只含开放权重且可自建的模型；现搜补充的
同样只收这一类。榜单前几名多半是闭源旗舰，验完直接跳过——它们放不到客户的卡上，
列进方案就是无法交付的选项。

## 搜到之后

新模型要进编队测算，得补齐目录里本来就有的那几个关键字段。都从公开的 HF 仓库取，
不需要任何内部权限：

| 字段 | 怎么取 | 补不齐会怎样 |
|---|---|---|
| 权重实测体积 | `HfApi().model_info(repo, files_metadata=True)`，求和 `.safetensors` **和 `.bin`**（只算前者对老模型会返回 0）。**取目标精度那个仓的体积**，不是主仓——见 SKILL.md 坑一 | 装载算不了，或按主仓 BF16 误判装不下 |
| KV 字节/token | `config.json` 的 `layer_types` / MLA 字段，公式见 `catalog-query.md`。**算出来大于目录值就按算出来的走** | 并发算不了，或算高 |
| 输入模态 | `config.json` 有无 `vision_config` / `video_token_id` | 多模态判断只能靠猜 |
| 许可 | `hf_hub_download(repo, "LICENSE")` **读正文** | 商用与否不能下结论 |

**补齐了** → 进候选池，参与编队与测算。

**补不齐**（拿不到权重、没有 config、读不到 LICENSE）→ 只能写进方案的「值得关注，
待评估」，**不进编队、不进测算数字**。

## 标注规矩（硬性）

现搜补进来的模型，在方案里**每次出现都要带标记**：

> 目录外候选（2026-09-09 检索补充），需供应商确认可供与商务条件

理由：目录里的模型是维护者复核过的；现搜来的只是「公开可查」，**我们并
不知道它能不能供、什么时候能供**。不标注就等于给了客户一个我们没有承诺过的东西。

淘汰它的时候同样要写依据，和目录内的模型一视同仁。

## 不要写回目录文件

**不要修改 `data/model-catalog.json`。** 那份文件是内部导出并逐条人工审核过才随包
发布的，运行时写进去的内容没人复核过，下次发布也会被覆盖。

现搜的结果只在**本次会话**里作为候选池的补充存在。要让某个模型长期进目录，是维护者
把它录进模型库、下次导出时带出来——在方案的「需供应商确认的事项」里提一句即可。
