import React, { useMemo, useState } from "react";
import {
  ArrowLeft,
  Calendar,
  CheckCircle2,
  CheckSquare,
  CircleAlert,
  ClipboardList,
  FileSearch,
  FlaskConical,
  GitBranch,
  LayoutDashboard,
  Lightbulb,
  Radar,
  ShoppingCart,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  Trophy,
  Workflow,
  Zap,
} from "lucide-react";

const topics = [
  {
    id: "agenthub",
    title: "AgentHub",
    subtitle: "多 Agent 协作平台",
    oneLiner: "把不同能力的 Agent 像团队成员一样编排、调度、观测和复用。",
    icon: Workflow,
    color: "blue",
    score: 82,
    tags: ["平台型", "技术深", "通用能力"],
    bestFor: "强调底层架构能力、Agent 编排、任务流可视化。",
    insight:
      "这个方向的优势是技术上限高，适合展示 Supervisor、Worker Agent、工具调用、状态追踪和人类审核节点；风险是容易做成空壳平台，所以 Demo 必须绑定一个具体任务。",
    ideas: [
      "Agent 商店：Research、Coder、Verifier、Reporter 等 Agent 可拖拽组合。",
      "任务流运行态：展示每个 Agent 的输入、输出、状态、耗时和失败重试。",
      "Human-in-the-loop：高风险结论暂停，等待人工确认后继续执行。",
      "Agent 评测面板：比较不同 Agent 在成本、速度、准确率上的表现。",
    ],
    demo: `输入一个任务，例如"分析三个竞品并生成报告"，AgentHub 自动拆成搜索、抽取、验证、报告四个节点并展示执行过程。`,
    mvp: ["Agent 列表", "工作流画布", "运行日志", "任务状态", "结果卡片"],
    risks: ["业务价值不够直观", "3 天内容易只做 UI", "需要一个强场景承载"],
    pros: [
      "技术上限高，可深入展示系统设计能力",
      "架构可复用，一个平台承载多个场景",
      "简历含金量高，体现工程化思维",
      "适合展示 Supervisor、工具调用、状态机等核心概念",
    ],
    cons: [
      "没有具体业务场景容易做成空壳平台",
      "3 天时间难以充实功能，Demo 容易单薄",
      `评委可能觉得"什么都做但什么都没做完"`,
      "需要额外精力设计一个足够具体的任务场景",
    ],
    sop: [
      { step: 1, title: "定义任务类型", desc: "确定 Agent 需要处理的任务范围，如竞品分析、代码审查、文献综述等" },
      { step: 2, title: "构建 Agent 模板", desc: "设计 Research / Coder / Verifier / Reporter 四种 Agent 角色的能力边界和输入输出" },
      { step: 3, title: "实现 Supervisor 路由", desc: "编写调度逻辑，让 Supervisor 根据任务类型自动分配给对应 Worker Agent" },
      { step: 4, title: "接入工具调用", desc: "为每个 Agent 接入搜索、代码执行、文件读写等外部工具" },
      { step: 5, title: "搭建任务流画布 UI", desc: "可视化展示 Agent 之间的数据流转、状态变化和执行进度" },
      { step: 6, title: "端到端 Demo 验证", desc: "输入一个完整任务，展示 Agent 拆解 → 逐步执行 → 汇总输出的全过程" },
    ],
    poc: {
      goal: "证明 Supervisor 能调度 2+ Worker Agent 并汇总结果",
      deliverables: ["3 个 Agent 按顺序执行的任务流 demo", "任务状态实时更新 UI", "最终结果汇总卡片"],
      timeEstimate: "4-6 小时",
      successCriteria: "输入一个任务，3 个 Agent 分别完成搜索、分析、报告，结果可展示",
    },
    schedule: [
      { day: "Day 1", tasks: ["搭建 monorepo 工程骨架", "定义 Agent 接口和数据结构", "实现 Supervisor 调度逻辑"], milestone: "Supervisor 能分配任务给 2+ Worker" },
      { day: "Day 2", tasks: ["实现 3 个 Worker Agent", "接入工具调用", "搭建任务流画布 UI"], milestone: "完整任务流可运行并可视化" },
      { day: "Day 3", tasks: ["Demo 场景打磨", "错误处理和重试", "演示脚本排练"], milestone: "5 分钟 Demo 稳定运行" },
    ],
  },
  {
    id: "compete",
    title: "InsightForge",
    subtitle: "AI 驱动的竞品分析 Agent 协作系统",
    oneLiner: "从公开资料到可验证结论，自动生成竞品矩阵、证据链和机会点。",
    icon: FileSearch,
    color: "purple",
    score: 92,
    tags: ["Agent + RAG", "大屏好看", "简历友好"],
    bestFor: "最适合当前团队目标：技术深度、Demo 完整度、简历表达三者平衡。",
    insight:
      "这个方向天然适合多 Agent：Planner 规划、Research 收集、RAG 检索、Extractor 抽取、Comparator 对比、Verifier 校验、Reporter 输出。它比单纯聊天机器人更像一个完整系统。",
    ideas: [
      "证据优先竞品矩阵：每个结论都能点开来源片段。",
      "AI Coding Agent 赛道分析：对比 Cursor、Copilot、Windsurf、Claude Code 等。",
      "Battlecard 自动生成：为销售/产品团队生成竞品反驳点。",
      "机会点挖掘：根据竞品弱项生成产品切入建议。",
    ],
    demo: "输入赛道和 3 个竞品，系统跑出 Agent 工作流、竞品功能表、价格对比、证据支持率和机会点报告。",
    mvp: ["竞品输入", "RAG 证据库", "结构化抽取", "对比矩阵", "证据侧栏", "报告导出"],
    risks: ["数据源质量影响结果", "不要承诺全自动全网爬取", "需要预置高质量样例数据"],
    pros: [
      "技术深度 + Demo 完整度 + 简历价值三者最佳平衡",
      "天然适合多 Agent 协作，7 个角色职责清晰",
      "证据链机制让结论可信度强，差异化明显",
      "有完整 PDF 规划文档，工程路径明确",
    ],
    cons: [
      "数据源质量直接决定结果好坏",
      "需要预置高质量样例数据，不能依赖实时爬取",
      "范围容易扩大，要严格控制在 3-5 家竞品",
      "RAG 检索精度需要调优，chunk 策略很关键",
    ],
    sop: [
      { step: 1, title: "创建工作区", desc: "输入研究赛道、竞品名称、对比维度和种子 URL" },
      { step: 2, title: "Supervisor 生成研究计划", desc: "拆分出需要采集的来源类型、比较维度和执行顺序" },
      { step: 3, title: "Source/Index 流水线", desc: "抓取公开页面、清洗文本、按规则切块并写入向量库" },
      { step: 4, title: "Extractor + Comparator", desc: "抽取结构化竞品条目，生成横向差异矩阵" },
      { step: 5, title: "Verifier 证据回查", desc: "对每个关键结论回查证据，标注 supported / partial / conflict / weak" },
      { step: 6, title: "Reporter 输出报告", desc: "生成最终报告，大屏同步展示覆盖率、证据密度和可钻取卡片" },
    ],
    poc: {
      goal: "证明 RAG 检索返回有效 chunk + Agent pipeline 生成结构化竞品 JSON",
      deliverables: ["2 家竞品对比结果", "每条结论附带 evidence citation", "差异矩阵可视化"],
      timeEstimate: "6-8 小时",
      successCriteria: "每条结论可追溯到来源片段，差异矩阵可展示，证据状态标注完整",
    },
    schedule: [
      { day: "Day 1", tasks: ["搭工程骨架（monorepo / 前后端 / 基础 DB）", "创建工作区、录入竞品与种子 URL", "抓取、清洗、chunk、embedding、入库"], milestone: "3 个竞品、至少 20 个公开来源、向量检索能跑通" },
      { day: "Day 2", tasks: ["搭 LangGraph supervisor 与 Planner", "Extractor + Comparator 结构化抽取", "Verifier + citation side panel"], milestone: "至少 1 张差异矩阵、每条关键结论有 citation、弱证据可见" },
      { day: "Day 3", tasks: ["Dashboard 聚合接口", "Report export + demo script", "稳定性与兜底（预热数据、回放、录屏）"], milestone: "大屏可展示、报告可导出、演示脚本 rehearse 至少两轮" },
    ],
  },
  {
    id: "shopping",
    title: "ShopLens AI",
    subtitle: "智能识物比价购物 AI APP 助手",
    oneLiner: "拍照识别商品，自动找同款、比价格、看评价、给购买建议。",
    icon: ShoppingCart,
    color: "green",
    score: 86,
    tags: ["消费级", "好理解", "视觉 Demo 强"],
    bestFor: "适合做一个非常直观的产品 Demo，评委不用解释也能理解。",
    insight:
      "这个方向展示效果强，用户路径非常简单：拍照 → 识物 → 找同款 → 比价 → 推荐。但技术深度需要刻意设计，比如加入多模态识别、RAG 评论总结、价格可信度校验和购买决策 Agent。",
    ideas: [
      "拍照识物：识别品牌、型号、类目和相似商品。",
      "全网比价 Agent：聚合不同渠道价格、优惠券和历史低价。",
      "评论 RAG 总结：自动总结好评、差评和购买风险。",
      "替代品推荐：如果预算有限，推荐性价比替代款。",
    ],
    demo: "上传一张耳机/鞋/包图片，系统识别商品并展示多个平台价格、评论摘要、购买建议和风险提醒。",
    mvp: ["图片上传", "商品识别", "候选商品卡片", "价格对比", "评论摘要", "购买建议"],
    risks: ["真实电商数据难拿", "价格实时性难保证", "容易被看成普通导购 App"],
    pros: [
      "Demo 最直观，评委无需解释就能理解",
      "视觉冲击强，拍照识别的交互天然吸引眼球",
      "消费级场景人人有共鸣，落地感最强",
      "用户路径清晰：拍照 → 识物 → 比价 → 推荐",
    ],
    cons: [
      "真实电商数据难获取，需要预置商品库",
      "价格实时性难以保证，容易被质疑数据真实性",
      "容易被看成普通导购 App，技术深度需要刻意设计",
      "视觉识别准确率受限于模型能力和商品库覆盖",
    ],
    sop: [
      { step: 1, title: "搭建图片上传管线", desc: "实现图片上传、预处理和格式标准化" },
      { step: 2, title: "接入视觉识别模型", desc: "使用多模态模型识别品牌、型号、类目和外观特征" },
      { step: 3, title: "匹配候选商品库", desc: "根据识别结果在预置商品库中检索相似商品" },
      { step: 4, title: "聚合多渠道价格", desc: "收集不同平台的价格、优惠券和历史低价信息" },
      { step: 5, title: "RAG 评论总结", desc: "自动总结好评、差评和购买风险点" },
      { step: 6, title: "生成购买建议", desc: "综合价格、评价和用户偏好给出推荐和替代品建议" },
    ],
    poc: {
      goal: "证明视觉识别能返回品类匹配 + 多平台价格对比",
      deliverables: ["上传图片 → 3+ 类似商品卡片", "价格对比表", "评论摘要"],
      timeEstimate: "4-6 小时",
      successCriteria: "识别准确率 > 80%，价格数据可展示，评论摘要有意义",
    },
    schedule: [
      { day: "Day 1", tasks: ["搭建图片上传 + 预处理管线", "接入视觉识别模型", "构建预置商品库"], milestone: "上传图片能识别出商品品类和基本信息" },
      { day: "Day 2", tasks: ["实现多渠道价格聚合", "搭建 RAG 评论总结", "构建候选商品匹配逻辑"], milestone: "能展示 3+ 商品的价格对比和评论摘要" },
      { day: "Day 3", tasks: ["购买建议生成", "UI 打磨和交互优化", "演示脚本排练"], milestone: "完整购物流程可演示，5 分钟 Demo 稳定" },
    ],
  },
];

const colorMap = {
  blue: {
    badge: "bg-blue-500/10 text-blue-300 ring-blue-400/20",
    button: "from-blue-500 to-cyan-400",
    soft: "from-blue-500/20 to-cyan-500/5",
    icon: "text-blue-300 bg-blue-500/10",
  },
  purple: {
    badge: "bg-purple-500/10 text-purple-300 ring-purple-400/20",
    button: "from-purple-500 to-fuchsia-400",
    soft: "from-purple-500/20 to-fuchsia-500/5",
    icon: "text-purple-300 bg-purple-500/10",
  },
  green: {
    badge: "bg-emerald-500/10 text-emerald-300 ring-emerald-400/20",
    button: "from-emerald-500 to-teal-400",
    soft: "from-emerald-500/20 to-teal-500/5",
    icon: "text-emerald-300 bg-emerald-500/10",
  },
};

const comparison = [
  ["技术深度", 92, 94, 82],
  ["3 天可交付", 76, 88, 84],
  ["Demo 直观度", 74, 90, 95],
  ["简历价值", 88, 94, 82],
  ["风险可控", 70, 86, 78],
];

function Badge({ children, color = "blue" }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ring-1 ${colorMap[color].badge}`}>
      {children}
    </span>
  );
}

function ScoreBar({ value, color = "blue" }) {
  return (
    <div className="flex items-center gap-3">
      <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
        <div className={`h-full rounded-full bg-gradient-to-r ${colorMap[color].button}`} style={{ width: `${value}%` }} />
      </div>
      <span className="w-8 text-right text-xs text-slate-300">{value}</span>
    </div>
  );
}

function TopicCard({ topic, onClick }) {
  const Icon = topic.icon;
  return (
    <button
      onClick={onClick}
      className="group text-left rounded-3xl border border-white/10 bg-white/[0.04] p-5 transition hover:bg-white/[0.07] hover:border-white/25 hover:shadow-2xl hover:shadow-black/30"
    >
      <div className="flex items-start justify-between gap-4">
        <div className={`rounded-2xl p-3 ${colorMap[topic.color].icon}`}>
          <Icon className="h-6 w-6" />
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-white">{topic.score}</div>
          <div className="text-xs text-slate-500">推荐分</div>
        </div>
      </div>
      <h3 className="mt-5 text-xl font-bold text-white">{topic.title}</h3>
      <p className="mt-1 text-sm text-slate-400">{topic.subtitle}</p>
      <p className="mt-4 text-sm leading-6 text-slate-300">{topic.oneLiner}</p>
      <div className="mt-5 flex flex-wrap gap-2">
        {topic.tags.map((tag) => (
          <Badge key={tag} color={topic.color}>{tag}</Badge>
        ))}
      </div>
      <div className="mt-4 flex items-center gap-1 text-xs text-slate-500 group-hover:text-slate-300 transition">
        查看详情 <ArrowLeft className="h-3 w-3 rotate-180" />
      </div>
    </button>
  );
}

function Section({ title, icon: Icon, children }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-5 backdrop-blur">
      <div className="mb-4 flex items-center gap-2">
        <div className="rounded-xl bg-white/10 p-2 text-slate-200">
          <Icon className="h-4 w-4" />
        </div>
        <h2 className="text-lg font-semibold text-white">{title}</h2>
      </div>
      {children}
    </div>
  );
}

function TopicDetailPage({ topic, onBack }) {
  const Icon = topic.icon;
  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100">
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute left-20 top-0 h-96 w-96 rounded-full bg-blue-500/10 blur-3xl" />
        <div className="absolute right-20 top-24 h-96 w-96 rounded-full bg-purple-500/10 blur-3xl" />
        <div className="absolute bottom-10 left-1/3 h-96 w-96 rounded-full bg-emerald-500/10 blur-3xl" />
      </div>

      <main className="relative mx-auto max-w-7xl px-6 py-6">
        {/* Back button + Hero */}
        <header className="rounded-3xl border border-white/10 bg-white/[0.05] p-6 shadow-2xl shadow-black/30 backdrop-blur">
          <button
            onClick={onBack}
            className="mb-4 flex items-center gap-2 text-sm text-slate-400 hover:text-white transition"
          >
            <ArrowLeft className="h-4 w-4" /> 返回选题看板
          </button>
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center gap-4">
              <div className={`rounded-2xl p-4 ${colorMap[topic.color].icon}`}>
                <Icon className="h-8 w-8" />
              </div>
              <div>
                <div className="flex flex-wrap gap-2 mb-2">
                  {topic.tags.map((tag) => (
                    <Badge key={tag} color={topic.color}>{tag}</Badge>
                  ))}
                </div>
                <h1 className="text-3xl font-bold tracking-tight text-white md:text-4xl">
                  {topic.title}
                </h1>
                <p className="mt-1 text-sm text-slate-400">{topic.subtitle}</p>
              </div>
            </div>
            <div className="text-center rounded-2xl border border-white/10 bg-slate-950/60 px-8 py-4">
              <div className="text-4xl font-bold text-white">{topic.score}</div>
              <div className="text-xs text-slate-500">推荐分</div>
            </div>
          </div>
          <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-300">{topic.oneLiner}</p>
        </header>

        {/* Core Insight + Pros/Cons */}
        <section className="mt-6 grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-6">
            <Section title="核心见解" icon={Lightbulb}>
              <div className={`rounded-2xl border border-white/10 bg-gradient-to-br ${colorMap[topic.color].soft} p-5`}>
                <p className="text-sm leading-7 text-slate-200">{topic.insight}</p>
              </div>
              <div className="mt-4 rounded-2xl border border-white/10 bg-slate-950/60 p-4">
                <div className="mb-2 text-sm font-semibold text-white">适合强调</div>
                <p className="text-sm leading-6 text-slate-400">{topic.bestFor}</p>
              </div>
            </Section>

            {/* SOP */}
            <Section title="SOP 标准操作流程" icon={ClipboardList}>
              <div className="space-y-3">
                {topic.sop.map((item, idx) => (
                  <div key={item.step} className="flex gap-4 rounded-2xl border border-white/10 bg-slate-950/60 p-4">
                    <div className="flex flex-col items-center">
                      <span className={`flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-r ${colorMap[topic.color].button} text-sm font-bold`}>
                        {item.step}
                      </span>
                      {idx < topic.sop.length - 1 && (
                        <div className="mt-2 h-full w-px bg-white/10" />
                      )}
                    </div>
                    <div className="flex-1">
                      <div className="text-sm font-semibold text-white">{item.title}</div>
                      <p className="mt-1 text-sm leading-6 text-slate-400">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </Section>

            {/* POC */}
            <Section title="POC 概念验证" icon={FlaskConical}>
              <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-5">
                <div className="mb-3 text-sm font-semibold text-white">验证目标</div>
                <p className="text-sm leading-6 text-slate-300">{topic.poc.goal}</p>
              </div>
              <div className="mt-4 rounded-2xl border border-white/10 bg-slate-950/60 p-5">
                <div className="mb-3 text-sm font-semibold text-white">交付物</div>
                <div className="space-y-2">
                  {topic.poc.deliverables.map((d) => (
                    <div key={d} className="flex items-start gap-2 text-sm text-slate-300">
                      <CheckSquare className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                      {d}
                    </div>
                  ))}
                </div>
              </div>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
                  <div className="mb-1 text-xs text-slate-500">预估时间</div>
                  <div className="text-sm font-semibold text-white">{topic.poc.timeEstimate}</div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
                  <div className="mb-1 text-xs text-slate-500">成功标准</div>
                  <div className="text-sm text-slate-300">{topic.poc.successCriteria}</div>
                </div>
              </div>
            </Section>
          </div>

          <div className="space-y-6">
            {/* Pros / Cons */}
            <Section title="优势与劣势" icon={ThumbsUp}>
              <div className="space-y-3">
                {topic.pros.map((p) => (
                  <div key={p} className="flex gap-3 rounded-2xl border border-emerald-400/20 bg-emerald-500/10 p-4">
                    <ThumbsUp className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" />
                    <p className="text-sm leading-6 text-slate-200">{p}</p>
                  </div>
                ))}
                {topic.cons.map((c) => (
                  <div key={c} className="flex gap-3 rounded-2xl border border-red-400/20 bg-red-500/10 p-4">
                    <ThumbsDown className="mt-0.5 h-4 w-4 shrink-0 text-red-300" />
                    <p className="text-sm leading-6 text-slate-200">{c}</p>
                  </div>
                ))}
              </div>
            </Section>

            {/* Ideas */}
            <Section title="可以准备的 Idea" icon={Sparkles}>
              <div className="space-y-3">
                {topic.ideas.map((idea, index) => (
                  <div key={idea} className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
                    <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-white">
                      <span className={`flex h-6 w-6 items-center justify-center rounded-full bg-gradient-to-r ${colorMap[topic.color].button} text-xs`}>
                        {index + 1}
                      </span>
                      Idea {index + 1}
                    </div>
                    <p className="text-sm leading-6 text-slate-400">{idea}</p>
                  </div>
                ))}
              </div>
            </Section>

            {/* Demo */}
            <Section title="最小 Demo 怎么讲" icon={Zap}>
              <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
                <p className="text-sm leading-7 text-slate-200">{topic.demo}</p>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {topic.mvp.map((item) => (
                  <Badge key={item} color={topic.color}>{item}</Badge>
                ))}
              </div>
            </Section>

            {/* Schedule */}
            <Section title="3 天工程计划" icon={Calendar}>
              <div className="space-y-4">
                {topic.schedule.map((day) => (
                  <div key={day.day} className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
                    <div className="mb-2 flex items-center gap-2">
                      <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold bg-gradient-to-r ${colorMap[topic.color].button} text-white`}>
                        {day.day}
                      </span>
                    </div>
                    <div className="space-y-1">
                      {day.tasks.map((task) => (
                        <div key={task} className="flex items-start gap-2 text-sm text-slate-300">
                          <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-500" />
                          {task}
                        </div>
                      ))}
                    </div>
                    <div className="mt-3 rounded-xl bg-white/5 px-3 py-2 text-xs text-slate-400">
                      里程碑：{day.milestone}
                    </div>
                  </div>
                ))}
              </div>
            </Section>

            {/* Risks */}
            <Section title="风险提醒" icon={CircleAlert}>
              <div className="space-y-3">
                {topic.risks.map((risk) => (
                  <div key={risk} className="flex gap-3 rounded-2xl border border-amber-400/20 bg-amber-500/10 p-4">
                    <CircleAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" />
                    <p className="text-sm leading-6 text-slate-200">{risk}</p>
                  </div>
                ))}
              </div>
            </Section>
          </div>
        </section>
      </main>
    </div>
  );
}

export default function HackathonTopicExplorer() {
  const [view, setView] = useState({ page: "overview" });

  const activeTopic = useMemo(
    () => topics.find((t) => t.id === view.topicId),
    [view.topicId]
  );

  if (view.page === "detail" && activeTopic) {
    return (
      <TopicDetailPage
        topic={activeTopic}
        onBack={() => setView({ page: "overview" })}
      />
    );
  }

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100">
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute left-20 top-0 h-96 w-96 rounded-full bg-blue-500/10 blur-3xl" />
        <div className="absolute right-20 top-24 h-96 w-96 rounded-full bg-purple-500/10 blur-3xl" />
        <div className="absolute bottom-10 left-1/3 h-96 w-96 rounded-full bg-emerald-500/10 blur-3xl" />
      </div>

      <main className="relative mx-auto max-w-7xl px-6 py-6">
        <header className="rounded-3xl border border-white/10 bg-white/[0.05] p-6 shadow-2xl shadow-black/30 backdrop-blur">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="mb-3 flex flex-wrap gap-2">
                <Badge color="blue">黑客松选题预研</Badge>
                <Badge color="purple">Agent / RAG 方向</Badge>
                <Badge color="green">前端理解页</Badge>
              </div>
              <h1 className="text-3xl font-bold tracking-tight text-white md:text-4xl">
                三个 AI Agent 选题方向对比看板
              </h1>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-400">
                目标不是现在写完整产品，而是为团队讨论准备：每个方向的核心见解、SOP、POC、优劣势、可做 idea、MVP Demo、风险和 3 天计划。点击卡片查看详情。
              </p>
            </div>
            <div className="grid grid-cols-3 gap-3 rounded-2xl border border-white/10 bg-slate-950/60 p-3 text-center">
              <div className="px-3">
                <div className="text-2xl font-bold text-white">3</div>
                <div className="text-xs text-slate-500">候选方向</div>
              </div>
              <div className="px-3">
                <div className="text-2xl font-bold text-white">3 天</div>
                <div className="text-xs text-slate-500">可交付周期</div>
              </div>
              <div className="px-3">
                <div className="text-2xl font-bold text-white">1 页</div>
                <div className="text-xs text-slate-500">讲清概念</div>
              </div>
            </div>
          </div>
        </header>

        <section className="mt-6 grid gap-5 lg:grid-cols-3">
          {topics.map((topic) => (
            <TopicCard
              key={topic.id}
              topic={topic}
              onClick={() => setView({ page: "detail", topicId: topic.id })}
            />
          ))}
        </section>

        <section className="mt-6 grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-6">
            <Section title="三方向快速对比" icon={Radar}>
              <div className="space-y-4">
                {comparison.map(([label, a, b, c]) => (
                  <div key={label} className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
                    <div className="mb-3 text-sm font-semibold text-white">{label}</div>
                    <div className="space-y-2">
                      <div className="grid grid-cols-[88px_1fr] items-center gap-3 text-xs text-slate-400">
                        <span>AgentHub</span><ScoreBar value={a} color="blue" />
                      </div>
                      <div className="grid grid-cols-[88px_1fr] items-center gap-3 text-xs text-slate-400">
                        <span>竞品分析</span><ScoreBar value={b} color="purple" />
                      </div>
                      <div className="grid grid-cols-[88px_1fr] items-center gap-3 text-xs text-slate-400">
                        <span>识物比价</span><ScoreBar value={c} color="green" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Section>
          </div>

          <div className="space-y-6">
            <Section title="推荐结论" icon={Trophy}>
              <div className="space-y-4">
                <div className="rounded-2xl border border-purple-400/20 bg-purple-500/10 p-4">
                  <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-purple-200">
                    <CheckCircle2 className="h-4 w-4" /> 首推方向
                  </div>
                  <p className="text-sm leading-6 text-slate-200">
                    如果团队目标是技术深度 + 简历作品 + 3 天可交付，优先选「AI 驱动的竞品分析 Agent 协作系统」。
                  </p>
                </div>
                <div className="rounded-2xl border border-blue-400/20 bg-blue-500/10 p-4">
                  <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-blue-200">
                    <GitBranch className="h-4 w-4" /> 组合策略
                  </div>
                  <p className="text-sm leading-6 text-slate-200">
                    可以把 AgentHub 作为底层架构，把竞品分析作为主场景，把识物比价作为可选扩展场景，而不是三个都做成完整项目。
                  </p>
                </div>
              </div>
            </Section>
          </div>
        </section>

        <section className="mt-6 rounded-3xl border border-white/10 bg-white/[0.04] p-5 backdrop-blur">
          <div className="mb-4 flex items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-white">给团队讨论用的一句话版本</h2>
              <p className="text-sm text-slate-400">可以直接复制到选题文档或答辩开场。</p>
            </div>
            <LayoutDashboard className="h-5 w-5 text-slate-300" />
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            {topics.map((topic) => {
              const Icon = topic.icon;
              return (
                <div key={topic.id} className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
                  <div className="mb-3 flex items-center gap-2">
                    <div className={`rounded-xl p-2 ${colorMap[topic.color].icon}`}>
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="font-semibold text-white">{topic.title}</div>
                  </div>
                  <p className="text-sm leading-6 text-slate-300">{topic.oneLiner}</p>
                </div>
              );
            })}
          </div>
        </section>
      </main>
    </div>
  );
}
