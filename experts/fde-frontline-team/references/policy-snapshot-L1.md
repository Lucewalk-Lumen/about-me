# L1 政策快照（policy-snapshot-L1）

> 全包唯一政策事实源。只增不改：任何流程（含 L2 / L3）禁止写回本文件。
> 母本：`01-诊断/L1政策快照-工信部414号文-核验记录.md`（官方原文直读核验，快照截至 2026-10-15）。
> 来源 URL 快照时点有效；官方改版可能死链，以快照引文为准。

```yaml
- policy_id: miit-414-2026-001
  title: 工信厅科函〔2026〕414号 · 服务商定义
  source_url: https://www.miit.gov.cn/jgsj/kjs/wjfb/art/2026/art_331b6f1d28ad410aa9df711acf42dbfe.html
  quote: '人工智能应用服务商（以下简称服务商）是指围绕用户单位智能化需求，提供人工智能解决方案咨询规划、交付实施、运营管理、安全治理等服务的企业或机构。'
  snapshot_date: "2026-10-15"
  status: verified
  context_note: "官方原文逐字引文（核验记录第 1 条）"
- policy_id: miit-414-2026-002
  title: 工信厅科函〔2026〕414号 · 服务商资源池目标
  source_url: https://www.miit.gov.cn/jgsj/kjs/wjfb/art/2026/art_331b6f1d28ad410aa9df711acf42dbfe.html
  quote: '到2026年底，全国服务商资源池内服务商数量突破2000家……到2027年底，全国服务商资源池内服务商数量不少于3000家。'
  snapshot_date: "2026-10-15"
  status: verified
  context_note: "官方原文逐字引文（核验记录第 2 条）；另有 2027 年底先导区省份不少于 100 家的补充事实见核验记录"
- policy_id: miit-414-2026-003
  title: 工信厅科函〔2026〕414号 · 任务三 真实场景开放
  source_url: https://www.miit.gov.cn/jgsj/kjs/wjfb/art/2026/art_331b6f1d28ad410aa9df711acf42dbfe.html
  quote: '组织开放一批真实场景，积极引入服务商开展落地实践……探索通过首购首用、风险补偿等模式，加大大模型、智能体、Token等服务采购力度。'
  snapshot_date: "2026-10-15"
  status: verified
  context_note: "官方原文逐字引文（核验记录第 3 条，任务三）"
- policy_id: miit-414-2026-004
  title: 工信厅科函〔2026〕414号 · 任务四 实训基地与人才画像
  source_url: https://www.miit.gov.cn/jgsj/kjs/wjfb/art/2026/art_331b6f1d28ad410aa9df711acf42dbfe.html
  quote: '鼓励高校、职业院校与龙头服务商共建实训基地，批量培养"懂业务、通模型、知安全、能交付"的复合型应用人才。'
  snapshot_date: "2026-10-15"
  status: verified
  context_note: "十二字画像在官方原文中修饰「复合型应用人才」（由高校/院校与服务商共建实训基地培养），非 FDE 岗位本身，引用须保留原语境（核验记录第 4 条）"
- policy_id: miit-414-2026-005
  title: 工信厅科函〔2026〕414号 · 任务四 FDE 团队
  source_url: https://www.miit.gov.cn/jgsj/kjs/wjfb/art/2026/art_331b6f1d28ad410aa9df711acf42dbfe.html
  quote: '鼓励服务商搭建前线部署工程师（FDE）团队，扎根用户现场，保障场景落地。'
  snapshot_date: "2026-10-15"
  status: verified
  context_note: "官方原文逐字引文（核验记录第 5 条，任务四）"
- policy_id: miit-414-2026-006
  title: 工信厅科函〔2026〕414号 · 任务二 安全合规内嵌
  source_url: https://www.miit.gov.cn/jgsj/kjs/wjfb/art/2026/art_331b6f1d28ad410aa9df711acf42dbfe.html
  quote: '引导服务商将网络安全、数据安全、伦理治理、业务合规等管理要求内嵌到研发、部署、应用全流程，变被动应对为主动防控。'
  snapshot_date: "2026-10-15"
  status: verified
  context_note: "官方原文逐字引文（核验记录第 6 条，任务二，合规模块判据）"
```

## 使用纪律

- 每条输出带「快照截至 2026-10-15」与三态标注；本文件全部条目当前 status 均为 verified。
- 十二字引用必须保留「复合型应用人才」原语境（见 miit-414-2026-004 的 context_note）。
- L2 联网核验仅认 gov.cn 系官方 host（白名单见 `skills/policy-radar/references/whitelist.md`）。
- 本文件只增不改；L3 用户沉淀写入用户本地知识库，不写回本文件。
