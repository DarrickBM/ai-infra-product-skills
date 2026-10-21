# 选型方法论（公开版）

给客户定位、判断该用什么方案、筛合规。

**适用范围：私有化部署，候选全部是开放权重且可自建的模型。** 闭源 / API-only 放不到
客户的卡上，本方法论的每一条判据都在这个前提下写。客户想比较托管调用方案，那是另一套
选型与报价，写进「需供应商确认的事项」。

**这一版只含通用判断框架**——按组合给的首选/备选模型清单、阻断清单、定价与商务口径
不在其中，那些需供应商出具。

所有依据都给了公开可查的出处。写进方案时把出处一起带上，客户不必只信供应商自述。

---

## 一、三维定位

先用这三个维度把客户问清楚。**每个维度都直接收窄候选集**，缺哪个就直接问，不要替客户
假设。

**不用问「数据敏不敏感」**——会做私有化部署的客户都敏感，这个问题收窄不了任何候选。
要问的是**不出域到什么程度**，那决定交付计划，见第二节。

### D1. 行业

通用 / 金融 / 医疗 / 能源 / 农业 等。

通用场景按下面 D2 的业务子类直接选基座，依据公认权威榜单（Artificial Analysis
Intelligence Index、MMMU、AA Video Arena 等，取数方法见 `references/model-evidence.md`）。
垂直行业在通用选型之上叠加行业术语与合规要求，合规那一层见第二节。

### D2. 业务应用

客户决策的第一问是「要做什么」。八个通用子类：

| 子类 | 典型技术栈 |
|---|---|
| 语言（翻译 / 投研 / 资讯） | Reason + 长上下文 |
| 语言（对话 / Copilot / 营销） | Chat + RAG + Agent，员工内部助手 |
| 语言（多语言） | 多语基座 + 分词效率 |
| 视觉（图像 / 视频理解） | VLM + 结构化输出，合同 / 单据 / 审核 |
| 视觉（图像生成） | 扩散 / 自回归图像模型 |
| 视觉（视频生成） | 视频生成模型 |
| 语音（ASR / 语音理解） | 专用 ASR，比让 VLM 兼职更准更省 |
| 边缘云（端侧 / IoT 小模型） | 3–14B 量级，算力与功耗受限 |

常见形态：**Copilot**（Chat+RAG+Agent，内部助手）/ **Chatbot**（Chat+CRM+可选 Voice，
外部客服）/ **投研**（Reason+长上下文）/ **Dev AI**（Code）/ **文档自动化**
（VLM+结构化）/ **RPA**（Agent+工具调用）/ **IoT 边缘**（端侧小模型）。

### D3. 主场景语言

英语 EN / 中文 ZH / 单一 SEA 小语种（TH / MY / ID / VN 等）/ SEA 多语混合。

**自建场景下，小语种特调优于通用开源基座。** 相对 Llama / Qwen / Gemma / Mistral 这类
通用开源模型，特调版有基准优势与分词效率优势：Gemma-SEA-LION-v3-9B 64.13 vs
Llama-3.1-8B 49.94（[SEA-LION, IJCNLP 2025](https://aclanthology.org/2025.ijcnlp-long.30.pdf)；
分词效率见 [SeaLLMs, ACL 2024](https://aclanthology.org/2024.acl-demos.28.pdf)）。

分词效率不只是效果问题——**单个词被切成多 token 会浪费上下文窗口**，直接吃 KV 预算，
在长上下文场景里直接换算成并发。

**要如实告诉客户的一点**：在 SEA 跨语言任务上，闭源旗舰仍然大幅领先开源特调
（[SeaEval, arXiv 2309.04766](https://arxiv.org/abs/2309.04766)）。数据允许出域的场景
里这是个真实的取舍——但那要走托管调用，不在本方案范围内，写进「需供应商确认的
事项」，不要在编队里硬凑。

---

## 二、合规与安全筛查

选型不是只看效果。客户签单前最常被合规官挡下的不是「模型不好」，而是**许可不对 /
数据不能落 / 报告跑不出来**。把这一层前置到选型阶段。

| 检查项 | 内容 | 依据 |
|---|---|---|
| **Model Card** | 每个入选模型一页：许可条款、训练数据声明、已知风险、推荐/不推荐场景、安全过滤默认档位 | 对齐 [Singapore's Approach to AI Governance (PDPC)](https://www.pdpc.gov.sg/organisations/resources/guidance-by-topic/singapores-approach-to-ai-governance) 的 Transparency / Accountability / Reproducibility |
| **许可 × 司法辖区矩阵** | 把每个模型与客户部署国家打成矩阵，标注哪些许可在哪些司法辖区可商用。例：Llama 4 Community License 对月活超 7 亿的企业受限；Apache-2.0 全开放；部分 Community License 需事先书面商用授权 | **读 LICENSE 正文，不看许可名** |
| **AI Verify 预检** | 选型阶段对候选模型跑一次治理指标预检，报告直接作为 PoC 材料 | [AI Verify Foundation](https://aiverifyfoundation.sg/what-is-ai-verify/)（自愿性框架，已是政企 AI 采购的事实信任基线）；金融场景另对齐 [MAS FEAT](https://www.mas.gov.sg/publications/monographs-or-information-paper/2018/FEAT) |
| **风险分档** | 对「模型 × 任务 × 地域」组合分档：**阻断**（不可选）/ **告知**（可选但必须向客户展示已知风险并绑护栏）/ **披露**（仅在 Model Card 列出） | 逐项要有公开可引证据，不凭印象 |

**具体的阻断清单需供应商出具**——本版只给检查项，不给清单。

### 不出域到什么程度

做私有化部署的客户都要求数据不出域，但「不出域」有三档，**决定的是交付计划，不是配置**。
问清楚落在哪一档：

| 档位 | 后果 |
|---|---|
| **业务数据不出域** | 常规部署。遥测、日志、评测样本仍可带出客户环境做调优 |
| **全部数据不出域**（商业机密 / PII） | 日志与评测样本一并留在域内。问题定位只能在客户现场做，PoC 与运维排期要留出人力 |
| **完全离线**（PHI / 主权数据） | 连模型权重更新与遥测都不出域。要按离线运维设计：权重离线导入、无外呼、审计留痕。**这会改交付计划**——升级窗口、故障响应方式、审计材料都跟着变 |

第三档最容易被漏掉，因为它在选型阶段看不出来，到交付才爆。**在方案的交付计划里写明落在
哪一档**，别默认第一档。

---

## 三、失效类型 → 方案层级

**入口是诊断失效类型，不是先挑方案。** 找到失效点，方案自然映到对应层级；数据量与预算
跟着来。搞反了就会出现「上来就说要微调」这种既贵又不解决问题的方案。

| 失效类型 | 症状 / 触发条件 | 首选方案 |
|---|---|---|
| **动态知识缺口** | 行业专有名词幻觉；引用过期条款/案例编号；给出训练截止前的版本号或法规（知识高频更新） | **L1 RAG** |
| **轻量行为缺口** | JSON/模板字段乱序或缺失；企业称谓/语气漂移；多轮对话角色失忆；显式约束（"不超过 200 字"）被违反 | **L2 LoRA / QLoRA** |
| **深度行为缺口** | 专业任务准确率不达标；复杂多步任务执行错误；LoRA 容量不足以覆盖任务分布（编程/数学/行业专业问答） | **L3a 全参 SFT** |
| **对齐缺口** | 领域 SFT 后安全护栏退化（alignment tax）；被 jailbreak 绕过；受监管场景给出违规建议 | **L3b DPO / Safety SFT** |
| **推理缺口** | CoT 中途算术/单位换算错；代码逻辑通过但 edge case 失败；可程序验证的题目反复犯同类错 | **L3c GRPO / RFT** |
| **深度知识缺口** | RAG 无法校正的领域逻辑错误；术语词表外词切分浪费上下文；幻觉抗拒检索纠正（知识稳定且需烧进参数） | **L4a CPT-Knowledge** |
| **语言缺口** | 泰文/缅文词序混乱；马来文夹杂印尼词；单词被切成多 token 浪费上下文 | **L4b CPT-Language** |
| **多重缺口** | 术语幻觉 + 格式不稳 + 护栏不足 + 推理错率高同时出现，任一单点无法覆盖 | **L4\* CPT → SFT → DPO/GRPO 全链路** |

### RAG 还是 CPT

两者解决同类失效（知识缺口），**按更新频率选**：频繁更新选 RAG，深度注入选 CPT。

- [Ovadia et al., EACL 2024 (arXiv 2312.05934)](https://arxiv.org/abs/2312.05934) 直接对比
  unsupervised FT / RAG / RAG+FT：**RAG 一致且显著优于 FT 注入新知识**（当前事件任务
  RAG 0.875 vs FT 0.504），结论 "RAG should be the preferred choice for knowledge injection"
- [RAFT (arXiv 2403.10131)](https://arxiv.org/abs/2403.10131) 证明封闭领域下
  **RAG + 领域 FT 联合 > 单 RAG > 单 FT**（PubMed +6.37 / HotpotQA +30.87 / Gorilla-API +31.41 pp）

其余层级的公开依据：[LoRA](https://arxiv.org/abs/2106.09685) ·
[QLoRA](https://arxiv.org/abs/2305.14314) · [DPO](https://arxiv.org/abs/2305.18290) ·
[DeepSeekMath GRPO](https://arxiv.org/abs/2402.03300)（GSM8K 82.9→88.2、MATH 46.8→51.7）·
[Don't Stop Pretraining, ACL 2020](https://arxiv.org/abs/2004.10964)。

### 微调与基座版本深度绑定

微调层级越深，基座升级后的迁移代价越高。**留在旧基座上，对手用新一代通用模型 + prompt
就可能抹平你的领域优势**：

- 微软 Medprompt 用 GPT-4 + prompting 在 MedQA / USMLE 上反超基于 PaLM-2 深度微调的
  Med-PaLM 2，错误率降低 27%
  （[MSR 2023](https://www.microsoft.com/en-us/research/publication/can-generalist-foundation-models-outcompete-special-purpose-tuning-case-study-in-medicine/)）
- [Nature Communications 2025](https://www.nature.com/articles/s41467-025-56989-2)：GPT-4
  零样本在 MedQA 上 0.72 对 0.42 领先此前的微调 SOTA

**方案里要写明这条**：微调不是一次性投入，基座大版本升级要重做，这是持续成本。

---

## 四、L1 RAG 的检索侧选型

失效类型落到 L1 RAG 之后，真正决定效果的是**检索侧的两个模型**，与主模型无关。四条判据：

1. **托管 embedding API 一律排除**，不分档位。OpenAI text-embedding、Cohere embed、
   Gemini Embedding 这类要把客户文档**全量**发出去，暴露面比 LLM 调用更大；而且本方案
   做的是私有化部署，检索侧挂一个外部 API 会让整条链路的「不出域」承诺失效。
2. **看多语榜，不看英文榜。** SEA 与中文场景用 MTEB / MMTEB 多语榜，英文单语榜的排名
   不迁移。
3. **embedding 与 reranker 取同族。** 同族训练目标与 tokenizer 一致，粗排与精排的判别
   边界不打架。
4. **纯文本场景不要用多模态版本替换文本版本。** 多模态 embedding 在纯文本检索上普遍
   弱于同尺寸文本版；需要图文混检时**并联一路**，不做替换。

**算力代价单独算。** embedding 每块编码一次可缓存，成本可忽略；**reranker 是
cross-encoder，代价随参数量线性变化，换个查询全部重算**。先查候选 reranker 的实际参数量
再决定单级还是两级——详见 SKILL.md「坑三」。

具体推荐型号从 `data/model-catalog.json` 里按上面四条判据选（`category` 为 `Embedding`
/ `Reranker`）。目录里检索侧的行数不多，选不到合适的就在方案里标注为「需供应商补充
候选」，不要拿语言模型硬凑。

---

## 这一版不包含什么

以下需供应商出具，方案里直接写「需供应商确认」，**不要凭记忆补**：

- 按行业 × 业务 × 语言 × 合规档组合的**首选 / 备选模型清单**
- 模型 × 任务 × 地域的**阻断清单**
- 微调各层级的**典型数据量与预算**
- **报价、供货、商务条件**
- 可承诺的**并发与 SLA 数字**
