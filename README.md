# AI Infra Product Skills

私有化部署选型与测算的 **Agent Skill**。装进 Claude Code（或任何支持 Agent Skill 的
agent），把「一批 GPU + 一组业务场景」变成一份可读的选型建议与部署形态。

本仓库是一个 Claude Code plugin marketplace，目前发布一个 plugin：`deployment-sizing`。

## 这个技能做什么

输入是实际对话里常见的问法，例如「我有 8 台 H20，想做知识库和客服，怎么部署」或者
「这批卡能跑多大的模型」。输出是四步推导：

1. **筛候选**——按方法论从模型目录里挑符合场景的模型。三维定位：业务类型 × 语言 ×
   合规档。
2. **筛可行**——按权重实测体积、显存、卡间互联判断这批硬件能不能跑。用落盘体积而不是
   参数量，低比特发布下两者可差 1.8 倍。
3. **定编队形态与配比**——确定几个实例、每个实例几张卡、各场景分多少并发。
4. **配第三方佐证**——给选型结论附公开榜单名次与社区口碑，带可点的出处。

## 零外部凭据

方法论、模型目录、硬件规格都以数据文件的形式随包发布，脚本只用 Python 3 标准库。
技能运行不需要任何账号、API key 或内部网络。联网时可以选做公开榜单与口碑佐证，
但不是必需的。

模型目录只收录**开放权重且可自建**的模型——闭源 / API-only 的模型放不到自己的卡上，
给出来就是无法交付的选项。语言类模型再加一层限制，只收近半年发布的，因为迭代太快，
固化全量历史库只会让方案引用两年前的型号。目录之外的，靠公开榜单现搜补充并标注。

## 并发数字怎么读

**输出的所有并发数字都是 roofline 物理包络，不是可承诺并发。** roofline 不建模预填充
与解码互相挤占、请求排队、P95 尾延迟，真实工程可承载约低一个数量级。技能强制每份输出
都写明这一点。要能写进合同的并发与 SLA 数字，只能靠实测或 PoC。

## 不包含什么

这一版只有通用判断框架。按行业 × 业务 × 语言 × 合规档组合的首选/备选模型清单、模型 ×
任务 × 地域的阻断清单、微调的典型数据量与预算、报价与商务条件、可承诺的并发与 SLA
数字——都不在里面，技能会要求把这些标注为「需供应商确认」而不是凭记忆编。

## 安装

在 Claude Code 里跑：

```
/plugin marketplace add DarrickBM/ai-infra-product-skills
```

```
/plugin install deployment-sizing
```

之后用 `/plugin update` 拉最新版。

## 目录结构

```
.claude-plugin/
├── marketplace.json              # marketplace 清单
└── plugin.json                   # plugin 清单
deployment-sizing/
├── SKILL.md                      # 技能主文件：四步推导、输出契约、常见错误
├── data/
│   ├── methodology-public.md     # 三维定位、合规筛查项、失效类型分层、RAG 检索侧判据
│   ├── model-catalog.json        # 模型目录快照：开放权重且可自建，含参数量/KV 估值/模态
│   └── hardware-profiles.md      # 卡的显存/带宽/算力/精度支持/TP 形态
├── references/
│   ├── catalog-query.md          # 字段语义、快照时效、KV 列的已知偏差
│   ├── catalog-refresh.md        # 目录截止日之后怎么现搜补充并标注
│   └── model-evidence.md         # 第三方榜单与社区口碑的取证口径
└── scripts/
    ├── catalog.py                # 按类别/模态/参数量/发布时间查目录
    └── fleet_sizing.py           # 装载、KV 池、并发包络、重排代价
```

数据是**固化快照**，各自带生成日期，`catalog.py` 会打印快照日与语言类截止日。用这个
技能出的方案应写明快照日期，让读的人能判断时效。

## License

[Apache-2.0](LICENSE)
