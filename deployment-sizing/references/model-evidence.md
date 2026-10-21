# 选型佐证：榜单名次 + 社区口碑

**先确认工具可用性。** 这一章要联网：榜单靠 `curl` / `tvly`，社区口碑靠 `agent-reach` skill。
这些在对外 bot 里不一定装了。

- **都不可用** → 跳过本章，在方案第二章末尾写一句「第三方榜单与社区口碑佐证需 供应商
  补充」，并把它列进「需供应商确认的事项」。**不要凭记忆编名次或口碑**——记忆里的
  榜单名次三个月就过期，编出来的推文链接是假的。
- **只有榜单可用** → 做榜单，社区口碑那节写「未采集」。
- **都可用** → 整章照做。

以下内容与内部版共用，改判据时两边要同步。

---

方案里每个**入选模型**（含备选编队里的）都要带两类第三方佐证，这两类都进对客交付件：

1. **权威榜单名次** — 证明「这个模型在同类里排第几」，客户不必信我们的自述
2. **社区口碑（X + Reddit，中英双语）** — 证明「真有人在生产里用它」，以及**别人踩过什么坑**

淘汰的模型不做佐证，只留淘汰依据。

---

## 一、权威榜单名次

### 取哪个榜

按模型模态选榜。**每个模型给两个数：开源榜名次 + 总榜绝对名次**（总榜含闭源）。只给开源名次会让客户误以为它是全球最强；只给总榜名次会埋没「开源里第一」这个真正的卖点。

| 模态 | 榜单 | 入口 | 取值 |
|---|---|---|---|
| 语言 | Artificial Analysis Intelligence Index | `https://artificialanalysis.ai/leaderboards/models` | `intelligenceIndex`（越高越好），过滤 `deprecated:true` |
| 语言（用量维度） | OpenRouter rankings | `https://openrouter.ai/api/frontend/v1/rankings/models?view=month` | 近 30 天调用量 / token，按 `model_permaslug` 聚合 |
| 图像生成 | AA Image Arena | `https://artificialanalysis.ai/image/leaderboard/text-to-image` | `elo` / `rank`（0-based，+1） |
| 视频生成 | AA Video Arena | `https://artificialanalysis.ai/video/leaderboard/text-to-video` | 同上 |
| 语音 TTS | AA Speech Arena | `https://artificialanalysis.ai/text-to-speech/leaderboard` | 同上 |
| ASR | AA Speech-to-Text，AA-WER Index | `https://artificialanalysis.ai/speech-to-text` | `werIndex`（**越低越好**） |
| OCR / 文档解析 | OmniDocBench | `https://raw.githubusercontent.com/opendatalab/OmniDocBench/main/README.md` | `Overall`（越高越好） |
| Embedding | MTEB | `https://mteb-leaderboard-backend.hf.space/v1/benchmarks/{name}/scores` | 后端 API，前端 Space 是 SPA 抓不到 |
| Reranker | 无公认公开榜 | — | 写「无公开榜单」，改用 BEIR / 官方评测 + 参数量，别硬凑名次 |

### 取数踩坑（都实测过，别重新踩）

- **Artificial Analysis 是 Next.js 页面**：`tvly extract` 只拿得到图表说明文字，拿不到榜单数据。用 `curl -sL` 抓 HTML 再解析内嵌 JSON。
  - `/leaderboards/models`：正则抓 `{"id":"<uuid>","name":...,"modelCreatorName":...,"intelligenceIndex":...}`
  - arena 类页面（image / video / text-to-speech）：先把 `\\"` / `\"` 还原成 `"`，再抓 `"values":{...}` 块，字段有 `name` / `rank` / `elo` / `creator.name` / `openWeightsUrl`（**AA 自带开放权重标记，可直接用，仍需 HF 复核**）
  - `/speech-to-text`：数据在 JSON-LD `{"@context":"https://schema.org","@type":"Dataset"...}` 块里，取 name 为 `Artificial Analysis Word Error Rate Index (Non-streaming)` 的那个。该页**不带 openWeightsUrl**，开源与否必须逐个 HF API 验。
  - **路径错了会返回 404 但 body 仍有 17KB**，别看字节数就以为抓到了。`/text-to-image`、`/video` 这类短路径是产品页不是榜单页。
- **LMArena 已不可用**：`lmarena.ai/api/*` 301 到 `arena.ai` 返回 `{"error":"Route not allowed"}`；`tvly extract` 拿得到分数列但模型名整列丢失。不要再用。
- **OmniDocBench 榜在 README 的 HTML `<table>` 里**，不是 markdown 表：按 `<tr>`/`<td>` 解析，且**表格行未按 Overall 排序**，必须自己重排再取名次。
- **开源与否一律 HF API 验真**，不凭印象、不凭模型名猜：`curl "https://huggingface.co/api/models?search=<名>&limit=4"`。API-only 加速端点不算开源。

### 写进方案的口径

- **每条名次都写清楚：榜单名 + 取数日期 + 分数 + 名次**。榜单是滚动的，不写日期的名次三个月后就是错的。
- 榜单页 URL 给**人能打开的页面**，不给 API endpoint（例外：MTEB 只有后端 API）。
- **榜单取不到就明写「该模态当期榜单不可得」**，给官方评测数字兜底，不硬凑一个名次。
- **榜单名次不替代硬件闸门**。榜首模型装不下客户的卡，它就是出局，名次不构成翻案理由。佐证章节和第二步的筛选结论冲突时，以硬件筛选为准，并在方案里写明「榜单第 N 但本次硬件下不可行」——这恰恰是有说服力的一句话。

---

## 二、社区口碑（X + Reddit）

用 `agent-reach` skill。先跑 `agent-reach doctor --json` 确认 Twitter / Reddit 的 `active_backend`（当前 X 走 `twitter search "<query>" -n 10`，Reddit 走 `opencli reddit search "<query>" -f yaml`；以 doctor 实际输出为准）。

### 时间窗

**自模型发布日起至今**，不是最近两周。部署方案关心的是这个模型上线以来累计暴露了什么问题，早期的量化 bug、引擎不支持、长上下文退化，全都算数。

### 三路必搜，缺一不可

1. **X 英文**：`twitter search "<英文模型名>" -n 10`
2. **X 中文**：`twitter search "<模型名> 评价" -n 10` 或 `"<中文模型名> 实测"` —— **不可省略**。候选池里中国厂商（阿里 / 智谱 / 腾讯 / 字节 / MiniMax / Moonshot / 小米 / 阶跃）占大头，这些模型的中文圈讨论量常大于英文圈，只搜英文等于漏掉主要证据。
3. **Reddit 英文**：`opencli reddit search "<英文模型名>" -f yaml`，重点 r/LocalLLaMA（自建部署人群集中地，踩坑贴最密）。

补充查询词（部署方案特有，比通用口碑更有用）：`"<模型名> vLLM"`、`"<模型名> SGLang"`、`"<模型名> quantization"`、`"<模型名> 显存"`、`"<模型名> 部署"`。

### 后端与限流

- 默认顺序 `opencli` → 限流后 TikHub → 兜底 Tavily。
- **Reddit 一旦 429 立即停掉全部 Reddit 重试**，转纯 X 采集。重试只会加重限流并拖死 subagent。
- Tavily 兜底：`tvly search "<模型名> <关键词>" --include-domains reddit.com --max-results 6 --json`。两个坑：日期过滤不可靠，会混入老帖；返回的是正文片段**不含点赞数**，拿不到就不写数字，不估算。
- TikHub（经 mcporter）数据最结构化，直接给 `createdAt` / `score` / `commentCount` / `permalink`：`mcporter call tikhub-reddit.reddit_app_fetch_dynamic_search query="<模型名>" search_type=posts sort=top time_range=month`。三个坑：返回是**双层 JSON**（外层 `{"result":"<JSON 字符串>"}`）要 `json.loads` 两次；单次响应可达 100KB，**用管道捕获会被截断**，必须重定向到临时文件再读；帖子对象深埋 GraphQL 嵌套里，按 `__typename in ("SubredditPost","ProfilePost")` 递归提取。
- **「零口碑」结论要至少两套后端交叉确认**才写进方案，避免把采集失败误判成社区无讨论。
- 模型多时拆 3~5 个并行 subagent 分组搜集。

### 采集侧返回格式（subagent 按此返回）

**URL 跟在每一条要点后面**，不要在末尾统一给代表帖——否则每格 3~6 条论点只配得到 1~2 个链接，最终大半论点没有出处，且只能拿旧数据重排版、补不齐。

```
## <模型名>
- 【X 中文】<要点，标 好评/吐槽/部署坑>｜👍<likes>｜<完整 x.com URL>
- 【X 英文】<要点>｜—｜<榜单页或原文 URL>      ← 无点赞数的事实，点赞栏写 —，URL 仍必填
- 【Reddit】<要点>｜👍<score>｜<完整 reddit URL>
```

X 链接拼法 `https://x.com/<author.screenName>/status/<id>`，两个字段都必须来自工具真实返回。**绝不允许拼凑或估算推文 ID**——拿不到真实 ID 就退回纯文字写「（👍280）」不加链接。宁可少一个链接也不能给一个假链接。

### 只收什么

- 真实用户反馈：实测体验、好评、吐槽、横向对比、**部署踩坑**（引擎版本要求、量化后掉点、长上下文退化、tool call 不稳）。
- 剔除：官方宣传、纯新闻转发、营销号推广。
- **部署坑类口碑要转成方案里的动作项**——「社区反映 vLLM 0.x 以下不支持该架构」要落成部署前置条件或 PoC 实测项，不能只当一句评论摆着。

### 负面口碑分类与闸门判据

采到的负面先分类。**只有第一类进闸门**，第二类照写进佐证表但不影响选型。

| 类 | 判据 | 例 | 闸门 |
|---|---|---|---|
| **可复现工程缺陷**（归模型本身） | 缺陷在我们自己的部署环境里会重现——与厂商定价、服务策略、舆论环境无关 | 量化后掉点、长上下文退化、tool call / JSON mode 不稳、某引擎版本不支持该架构、权重与模型卡不符、发布权重与评测用权重不一致、许可条款争议 | **有** |
| **不可复现 / 与本单无关** | 缺陷依附于厂商的托管服务或舆论场，私有化部署里不存在 | 官方 API 价格、官方限流与稳定性、内容审查与拒答策略、厂商政策与地缘争议、跑分刷榜争议、hype 反弹与「过誉」评论、与闭源对手的口水战 | **无** |

**计入闸门的双重门槛（两条都要满足）**：

1. **≥2 个互相独立的来源**。同一条推文被转发、同一个帖子被多个聚合号搬运，算 **1 个**。判独立看的是「是否各自做了自己的实测」，不是链接数量。
2. **至少一条给出可复现条件**——引擎与版本号（`vLLM 0.x`）、部署参数（TP / 量化格式 / max-model-len）、或数据样例。只有情绪没有条件的（「这模型不行」「拉胯」）不计入，写进佐证表当观察即可。

**分类要写在佐证表里**。「部署注意」列只放第一类；第二类若确实值得客户知道（如厂商政策影响后续权重更新节奏），放「社区口碑要点」列并写明**这条不影响本次私有化部署**。

**绕法要一起采**。判定「有无已知绕法」是闸门阶梯的分水岭，采集时对每条第一类缺陷追问一句：社区有没有给出可用的规避手段（升引擎版本、换量化格式、关某个开关、改采样参数）。有绕法就把绕法和它的出处一起带回来——绕法本身要落成部署前置条件，需要可溯源。

**「缺陷落在主场景还是非主场景」由第一步的场景切分判定**，不由采集侧判。采集侧只负责把缺陷描述准（是什么能力、什么条件下出现），归到哪个场景是写方案时的事。

### 写进方案的口径

- **中英观点冲突必须双向保留并标注差异**。英文社区叫好、中文圈实测唱衰这种反差是最有价值的信号，不许只取一边，也不许折中成「褒贬不一」。
- **每条论点后面紧跟它自己的出处链接**，点赞数本身做成超链接：
  - ✅ `吐槽「长上下文掉点」<a href="https://x.com/xxx/status/123">👍280</a>；Reddit 上有人当唯一主力 <a href="https://www.reddit.com/r/LocalLLaMA/comments/abc/">👍11</a>`
  - ❌ 写完 2~3 条论点最后甩一两个汇总链接——读者无法判断哪个链接对应哪条论点
  - 没有点赞数的条目用 `<a href="URL">帖</a>` 作锚文本
- **正文不写采集口径**：不出现「经 N 套后端交叉验证」「某后端限流改用某后端」「未采集（限流）」这类元叙述，也不加「采集口径：…」脚注。有口碑就写口碑，没有就写「公开讨论量少」。用了几个后端、哪个挂了，是我们的事。
- **负面口碑照写**。这是对客件，藏坑等于把风险留到 PoC 现场爆。写法是「社区反映 X，我方处置：Y」——有处置的坑不是减分项，是专业度。

---

## 三、佐证表（对客交付件里的形态）

放在方案第二章「选模型」末尾，覆盖**所有入选模型**（主推 + 保底 + 能力上限档三套编队里出现过的都算）：

| 模型 | 编队位置 | 模态 | 开源榜名次 | 总榜名次 | 榜单/分数（取数日期） | 社区口碑要点 | 部署注意 |
|---|---|---|---|---|---|---|---|

- 「社区口碑要点」每格 2~3 条，好评与吐槽都要有，各自带内联链接，标来源平台（【X 中文】/【X 英文】/【Reddit】）。
- 「部署注意」= 从口碑里提炼出的、要落进交付计划或 PoC 项的具体条目；没有就写「—」。**只放上表第一类（可复现工程缺陷）**，并写成「缺陷 + 我方处置」。
- **被口碑闸门降级或淘汰的模型也留在这张表里**，「编队位置」写「降备选（原主推）」或「淘汰」，「部署注意」写触发降级的那条缺陷。降级过程本身是客户最想看的部分，删掉等于让客户觉得我们没做过筛。
- 榜单与口碑都缺的模型（新发布、社区尚无讨论）写「发布未满 N 周，公开榜单与讨论均未形成」，**并把这条本身当成一个风险项写进交付计划**——没人趟过的模型，PoC 周期要留长。
