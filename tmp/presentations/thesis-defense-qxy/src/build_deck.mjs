import fs from "node:fs/promises";
import path from "node:path";
import {
  Presentation,
  PresentationFile,
  column,
  row,
  grid,
  panel,
  text,
  image,
  shape,
  chart,
  rule,
  fill,
  hug,
  fixed,
  wrap,
  fr,
  auto,
} from "@oai/artifact-tool";

const workspace = path.resolve("..");
const scratchDir = path.join(workspace, "scratch");
const outputDir = path.join(workspace, "output");
const assetDir = path.join(scratchDir, "assets");
const previewDir = path.join(scratchDir, "previews");

await fs.mkdir(previewDir, { recursive: true });
await fs.mkdir(outputDir, { recursive: true });

const W = 1920;
const H = 1080;
const font = "Microsoft YaHei";

const C = {
  bg: "#F6F8FA",
  paper: "#FFFFFF",
  ink: "#111827",
  softInk: "#263246",
  muted: "#596A80",
  line: "#D8E1EA",
  teal: "#20796E",
  teal2: "#2F9486",
  blue: "#2765E8",
  coral: "#E15A4F",
  amber: "#D88312",
  green: "#24A064",
  navy: "#0D172A",
  tealSoft: "#E7F4F1",
  blueSoft: "#EAF1FF",
  coralSoft: "#FDEDEA",
  amberSoft: "#FFF3DD",
  greenSoft: "#E9F7EF",
};

const pres = Presentation.create({ slideSize: { width: W, height: H } });

function addSlide(notes) {
  const slide = pres.slides.add();
  slide.background.fill = C.bg;
  if (notes) slide.speakerNotes.setText(notes);
  return slide;
}

function txt(value, opts = {}) {
  return text(value, {
    name: opts.name,
    width: opts.width ?? fill,
    height: opts.height ?? hug,
    columnSpan: opts.columnSpan,
    rowSpan: opts.rowSpan,
    style: {
      fontFace: font,
      color: C.ink,
      fontSize: 30,
      ...(opts.style ?? {}),
    },
  });
}

function compose(slide, children, padding = { x: 86, y: 64 }, gap = 34) {
  slide.compose(
    column({ name: "slide-root", width: fill, height: fill, padding, gap }, children),
    { frame: { left: 0, top: 0, width: W, height: H }, baseUnit: 8 },
  );
}

function header(title, eyebrow, page) {
  return row(
    { width: fill, height: hug, align: "center", gap: 24 },
    [
      column(
        { width: fill, height: hug, gap: 8 },
        [
          txt(eyebrow, { style: { fontSize: 22, bold: true, color: C.teal } }),
          txt(title, {
            width: wrap(1500),
            style: { fontSize: 58, bold: true, color: C.navy, lineSpacingMultiple: 0.98 },
          }),
        ],
      ),
      txt(String(page).padStart(2, "0"), {
        width: fixed(58),
        style: { fontSize: 24, bold: true, color: C.teal, align: "right" },
      }),
    ],
  );
}

function divider(color = C.teal, width = 160) {
  return shape({ width: fixed(width), height: fixed(8), fill: color, line: { fill: color, width: 0 } });
}

function bullet(items, color = C.teal, fontSize = 30, gap = 18) {
  return column(
    { width: fill, height: hug, gap },
    items.map((item, i) =>
      row(
        { width: fill, height: hug, gap: 14, align: "start" },
        [
          shape({
            geometry: "ellipse",
            width: fixed(12),
            height: fixed(12),
            fill: i === 0 ? color : "#C8D3DE",
            line: { fill: i === 0 ? color : "#C8D3DE", width: 0 },
          }),
          txt(item, { width: fill, style: { fontSize, color: C.softInk, lineSpacingMultiple: 1.08 } }),
        ],
      ),
    ),
  );
}

function chip(label, color = C.teal, soft = C.tealSoft) {
  return panel(
    {
      width: hug,
      height: hug,
      padding: { x: 20, y: 10 },
      borderRadius: "rounded-full",
      fill: soft,
      line: { fill: color, width: 1 },
    },
    txt(label, { width: hug, style: { fontSize: 20, bold: true, color } }),
  );
}

function metric(value, label, color = C.teal, note = "") {
  return column(
    { width: fill, height: hug, gap: 8 },
    [
      txt(value, { style: { fontSize: 66, bold: true, color } }),
      txt(label, { style: { fontSize: 25, bold: true, color: C.ink } }),
      note ? txt(note, { style: { fontSize: 20, color: C.muted } }) : txt(" ", { style: { fontSize: 1, color: C.bg } }),
    ],
  );
}

function block(title, body, color = C.teal) {
  return column(
    { width: fill, height: hug, gap: 12 },
    [
      divider(color, 64),
      txt(title, { style: { fontSize: 33, bold: true, color: C.ink } }),
      txt(body, { style: { fontSize: 25, color: C.muted, lineSpacingMultiple: 1.12 } }),
    ],
  );
}

function tableRow(cells, widths, head = false) {
  return row(
    { width: fill, height: hug, gap: 0 },
    cells.map((cell, i) =>
      panel(
        {
          width: widths[i],
          height: fixed(head ? 54 : 50),
          padding: { x: 14, y: 12 },
          fill: head ? C.navy : C.paper,
          line: { fill: C.line, width: 1 },
          borderRadius: "rounded-sm",
        },
        txt(cell, {
          width: fill,
          style: { fontSize: head ? 20 : 19, bold: head, color: head ? "#FFFFFF" : C.ink },
        }),
      ),
    ),
  );
}

function simpleTable(rows, widths) {
  return column({ width: fill, height: hug, gap: 0 }, rows.map((rowData, i) => tableRow(rowData, widths, i === 0)));
}

function card(fillColor, lineColor, child) {
  return panel(
    { width: fill, height: fill, padding: 28, fill: fillColor, line: { fill: lineColor, width: 1 }, borderRadius: "rounded-md" },
    child,
  );
}

function imgPath(name) {
  return path.join(assetDir, name);
}

async function dataUrl(name) {
  const bytes = await fs.readFile(imgPath(name));
  return `data:image/png;base64,${bytes.toString("base64")}`;
}

const raster = {
  architecture: await dataUrl("image14.png"),
  structure: await dataUrl("image15.png"),
  model: await dataUrl("image22.png"),
  training: await dataUrl("image74.png"),
  prediction: await dataUrl("image79.png"),
  stats: await dataUrl("image83.png"),
};

// 1. Cover
{
  const slide = addSlide("0:00-0:35 开场。只交代题目、身份和答辩主题，不提前讲实验指标。");
  slide.background.fill = "#F7F9FB";
  slide.compose(
    grid(
      {
        width: fill,
        height: fill,
        columns: [fr(1), fr(0.42)],
        rows: [fr(1), auto],
        columnGap: 44,
        padding: { x: 96, y: 76 },
      },
      [
        column(
          { width: fill, height: fill, justify: "center", gap: 34 },
          [
            divider(C.teal, 230),
            txt("基于深度学习的车险理赔预测系统设计与实现", {
              width: wrap(1120),
              style: { fontSize: 74, bold: true, color: C.navy, lineSpacingMultiple: 0.94 },
            }),
            txt("本科毕业论文答辩", { style: { fontSize: 36, color: C.teal, bold: true } }),
          ],
        ),
        column(
          { width: fill, height: fill, justify: "center", gap: 24 },
          [
            txt("重庆邮电大学", { style: { fontSize: 36, bold: true, color: C.navy } }),
            rule({ width: fixed(360), stroke: C.line, weight: 1 }),
            txt("人工智能学院", { style: { fontSize: 28, color: C.softInk } }),
            txt("学生：钱信宇", { style: { fontSize: 28, color: C.softInk } }),
            txt("专业：数据科学与大数据技术", { style: { fontSize: 28, color: C.softInk } }),
            txt("指导教师：丁晓宇 讲师", { style: { fontSize: 28, color: C.softInk } }),
            txt("2026年5月", { style: { fontSize: 26, color: C.muted } }),
          ],
        ),
        txt("Design and Implementation of Auto Insurance Claim Prediction System Based on Deep Learning", {
          columnSpan: 2,
          style: { fontSize: 22, color: C.muted },
        }),
      ],
    ),
    { frame: { left: 0, top: 0, width: W, height: H }, baseUnit: 8 },
  );
}

// 2. Agenda
{
  const slide = addSlide("0:35-1:10 介绍目录和时间分配。新版目录用六个部分展开，比上一版更像答辩路线。");
  const agenda = [
    {
      no: "01",
      title: "研究背景与目标",
      desc: "业务痛点、研究意义、论文主要工作",
      time: "约2min",
      pages: "03-04",
      color: C.teal,
      soft: C.tealSoft,
    },
    {
      no: "02",
      title: "技术栈与系统设计",
      desc: "前后端分离、模型服务解耦、功能模块划分",
      time: "约3min",
      pages: "05-07",
      color: C.blue,
      soft: C.blueSoft,
    },
    {
      no: "03",
      title: "数据处理与特征工程",
      desc: "数据集、缺失值、类别不均衡、日期语义特征",
      time: "约2min",
      pages: "08-09",
      color: C.coral,
      soft: C.coralSoft,
    },
    {
      no: "04",
      title: "模型构建与训练策略",
      desc: "残差式 MLP、损失重加权、自动阈值搜索",
      time: "约3min",
      pages: "10-11",
      color: C.amber,
      soft: C.amberSoft,
    },
    {
      no: "05",
      title: "实验结果与系统实现",
      desc: "分类报告、消融实验、训练与预测页面展示",
      time: "约3min",
      pages: "12-14",
      color: C.green,
      soft: C.greenSoft,
    },
    {
      no: "06",
      title: "总结与展望",
      desc: "主要成果、现有不足、后续优化方向",
      time: "约2min",
      pages: "15",
      color: C.teal2,
      soft: C.tealSoft,
    },
  ];
  function agendaRow(item) {
    const timeBadge = panel(
      {
        width: fixed(112),
        height: fixed(54),
        padding: { x: 10, y: 10 },
        borderRadius: "rounded-full",
        fill: item.soft,
        line: { fill: item.color, width: 1 },
      },
      txt(item.time, { width: fill, style: { fontSize: 20, bold: true, color: item.color, align: "center" } }),
    );
    return panel(
      {
        width: fill,
        height: fixed(94),
        padding: { x: 22, y: 14 },
        fill: C.paper,
        line: { fill: C.line, width: 1 },
        borderRadius: "rounded-sm",
      },
      row(
        { width: fill, height: fill, gap: 18, align: "center" },
        [
          txt(item.no, {
            width: fixed(70),
            style: { fontSize: 39, bold: true, color: item.color, align: "center" },
          }),
          shape({ width: fixed(7), height: fixed(58), fill: item.color, line: { fill: item.color, width: 0 } }),
          column(
            { width: fill, height: hug, gap: 7 },
            [
              row(
                { width: fill, height: hug, gap: 14, align: "center" },
                [
                  txt(item.title, {
                    width: fill,
                    style: { fontSize: 29, bold: true, color: C.navy },
                  }),
                  timeBadge,
                ],
              ),
              txt(item.desc, { style: { fontSize: 22, color: C.muted } }),
            ],
          ),
          txt(item.pages, {
            width: fixed(88),
            style: { fontSize: 21, bold: true, color: C.muted, align: "right" },
          }),
        ],
      ),
    );
  }
  compose(slide, [
    header("答辩目录", "围绕“模型研究 + 系统落地”展开", 2),
    grid(
      { width: fill, height: fill, columns: [fr(0.58), fr(1.42)], columnGap: 54 },
      [
        column(
          { width: fill, height: fill, justify: "center", gap: 24 },
          [
            txt("15分钟", { style: { fontSize: 88, bold: true, color: C.teal, lineSpacingMultiple: 0.9 } }),
            txt("答辩节奏", { style: { fontSize: 43, bold: true, color: C.navy } }),
            divider(C.teal, 150),
            txt("主线：背景与目标、关键设计、实验结果和系统展示。", {
              width: fill,
              style: { fontSize: 28, color: C.softInk, lineSpacingMultiple: 1.12 },
            }),
            bullet(["背景和目标不铺开过多", "方法页聚焦关键设计", "结果页服务结论表达"], C.teal, 25, 13),
          ],
        ),
        column({ width: fill, height: fill, justify: "center", gap: 13 }, agenda.map((item) => agendaRow(item))),
      ],
    ),
  ]);
}

// 3. Background
{
  const slide = addSlide("1:10-2:20 讲研究背景：理赔连接成本、服务与风险控制；数据积累使预测建模成为可落地问题。");
  compose(slide, [
    header("研究背景：车险理赔正在从经验处理转向数据驱动风控", "研究背景与意义", 3),
    grid(
      { width: fill, height: fill, columns: [fr(0.92), fr(1.08)], columnGap: 54 },
      [
        column(
          { width: fill, height: fill, justify: "center", gap: 28 },
          [
            txt("理赔环节同时影响赔付支出控制、客户满意度和保险企业运营效率。", {
              width: wrap(780),
              style: { fontSize: 46, bold: true, color: C.navy, lineSpacingMultiple: 1.02 },
            }),
            txt("线上报案、历史保单、车辆属性和理赔记录持续积累，使系统从业务数据中抽取风险信号成为可能。", {
              width: wrap(760),
              style: { fontSize: 30, color: C.muted, lineSpacingMultiple: 1.14 },
            }),
          ],
        ),
        column(
          { width: fill, height: fill, justify: "center", gap: 26 },
          [
            block("传统方式的不足", "人工经验与规则匹配在大规模、高维度、复杂关联数据下效率不足，规则维护成本较高。", C.coral),
            block("机器学习的机会", "神经网络能够从多维结构化字段中学习非线性风险表征，用于辅助识别潜在理赔风险。", C.blue),
            block("系统化落地价值", "将样本管理、模型训练、在线预测、结果查询与统计分析纳入统一平台，降低算法应用门槛。", C.teal),
          ],
        ),
      ],
    ),
  ]);
}

// 4. Goals and contribution
{
  const slide = addSlide("2:20-3:25 说明研究目标和主要工作。强调论文不是只比较模型，而是完成从数据到系统的闭环。");
  compose(slide, [
    header("研究目标：完成车险理赔预测模型与业务系统的结合", "研究目标与主要工作", 4),
    grid(
      { width: fill, height: fill, columns: [fr(1), fr(1)], columnGap: 48 },
      [
        column(
          { width: fill, height: fill, gap: 26, justify: "center" },
          [
            txt("模型部分", { style: { fontSize: 42, bold: true, color: C.teal } }),
            bullet(
              [
                "围绕“保单在当前年度是否发生理赔”构建二分类预测任务",
                "完成数据清洗、特征工程、标准化预处理和类别不均衡处理",
                "设计残差式 MLP 主干网络，并引入 LayerNorm、GELU、Dropout 等优化",
                "使用 AUC、Precision、Recall、F1 和消融实验验证模型效果",
              ],
              C.teal,
              29,
            ),
          ],
        ),
        column(
          { width: fill, height: fill, gap: 26, justify: "center" },
          [
            txt("系统部分", { style: { fontSize: 42, bold: true, color: C.blue } }),
            bullet(
              [
                "构建基于 Spring Boot、Vue3、MySQL、FastAPI 的前后端分离平台",
                "实现用户、保单、理赔记录、车辆信息等业务数据管理",
                "支持管理员进行模型训练、用户发起理赔概率预测",
                "将预测结果、风险等级、记录统计和局部解释展示给业务用户",
              ],
              C.blue,
              29,
            ),
          ],
        ),
      ],
    ),
  ]);
}

// 5. Tech stack
{
  const slide = addSlide("3:25-4:15 单独讲技术栈。说明每个技术服务于哪个层次，不再塞在封面里。");
  function techBlock(title, items, color) {
    return column(
      { width: fill, height: fill, justify: "center", gap: 16 },
      [
        divider(color, 70),
        txt(title, { style: { fontSize: 36, bold: true, color: C.ink } }),
        bullet(items, color, 24, 12),
      ],
    );
  }
  compose(slide, [
    header("系统技术栈：前后端分离 + 独立模型服务", "主要开发技术", 5),
    grid(
      { width: fill, height: fill, columns: [fr(1), fr(1)], rows: [fr(1), fr(1)], gap: 24 },
      [
        card(
          C.tealSoft,
          "#C8E3DC",
          techBlock("前端表现层", ["Vue3 构建单页应用与路由视图", "Element Plus 支撑表格、表单和弹窗交互", "ECharts 展示保单、理赔和预测统计图表", "Axios 统一封装 HTTP 请求"], C.teal),
        ),
        card(
          C.blueSoft,
          "#C9D8FF",
          techBlock("后端业务层", ["Spring Boot 实现认证、CRUD、分页和统计接口", "MyBatis 完成数据库访问与对象映射", "REST API 连接前端页面和模型服务", "统一响应结构与异常处理降低前端适配成本"], C.blue),
        ),
        card(
          C.greenSoft,
          "#CDECD8",
          techBlock("数据持久层", ["MySQL 保存用户、保单、理赔、车辆等业务表", "预测记录表追踪概率、标签和风险等级", "业务查询、统计分析与历史结果复盘共享同一数据源"], C.green),
        ),
        card(
          C.coralSoft,
          "#F5CBC5",
          techBlock("智能预测层", ["PyTorch 构建残差式 MLP 二分类模型", "scikit-learn 完成标准化、数据划分和指标评估", "FastAPI 对外提供模型加载和在线预测接口", "模型产物与业务系统通过 JSON 解耦"], C.coral),
        ),
      ],
    ),
    txt("设计思路：业务系统负责数据管理与流程控制，模型服务负责训练产物加载和在线推理，两者通过 JSON 接口解耦。", {
      style: { fontSize: 30, bold: true, color: C.teal },
    }),
  ]);
}

// 6. System design
{
  const slide = addSlide("4:15-5:10 讲系统架构：表现层、接口层、业务层、智能预测层、数据持久层、基础框架层。");
  compose(slide, [
    header("系统架构：业务系统与智能预测服务解耦", "系统分析与设计", 6),
    grid(
      { width: fill, height: fill, columns: [fr(1.15), fr(0.85)], columnGap: 42 },
      [
        panel(
          { width: fill, height: fill, padding: 16, fill: C.paper, line: { fill: C.line, width: 1 }, borderRadius: "rounded-md" },
          image({ dataUrl: raster.architecture, contentType: "image/png", width: fill, height: fill, fit: "contain", alt: "系统框架图" }),
        ),
        column(
          { width: fill, height: fill, justify: "center", gap: 26 },
          [
            block("表现层", "浏览器端完成业务操作、数据展示和统计图表交互。", C.teal),
            block("业务层", "Spring Boot 处理认证、CRUD、分页查询、统计分析和文件管理。", C.blue),
            block("预测层", "FastAPI 封装训练好的 PyTorch 模型，提供理赔概率、风险等级与解释结果。", C.coral),
            block("数据层", "MySQL 统一保存用户、保单、理赔、车辆、预测记录等核心表。", C.amber),
          ],
        ),
      ],
    ),
  ]);
}

// 7. Requirements and modules
{
  const slide = addSlide("5:10-6:00 讲功能需求。突出十个模块归为业务管理、可视化分析、理赔预测三类。");
  compose(slide, [
    header("功能设计：围绕业务管理、可视化分析与理赔预测展开", "需求分析", 7),
    grid(
      { width: fill, height: fill, columns: [fr(0.88), fr(1.12)], columnGap: 42 },
      [
        panel(
          { width: fill, height: fill, padding: 18, fill: C.paper, line: { fill: C.line, width: 1 }, borderRadius: "rounded-md" },
          image({ dataUrl: raster.structure, contentType: "image/png", width: fill, height: fill, fit: "contain", alt: "系统结构图" }),
        ),
        grid(
          { width: fill, height: fill, rows: [fr(1), fr(1), fr(1)], columns: [fr(1)], gap: 18 },
          [
            card(C.tealSoft, "#C8E3DC", block("业务管理", "用户认证、用户管理、保单信息、理赔记录、车辆信息等基础数据维护。", C.teal)),
            card(C.blueSoft, "#C9D8FF", block("可视化分析", "系统首页、保单统计、理赔统计、预测记录统计，帮助用户快速理解业务状态。", C.blue)),
            card(C.coralSoft, "#F5CBC5", block("理赔预测", "模型训练、批量/单条预测、预测记录管理、风险等级展示和局部消融解释。", C.coral)),
          ],
        ),
      ],
    ),
  ]);
}

// 8. Data preprocessing
{
  const slide = addSlide("6:00-7:05 讲数据集、样本不均衡和数据处理策略。");
  compose(slide, [
    header("数据处理：从公开车险数据集中构建训练样本", "数据集与预处理", 8),
    grid(
      { width: fill, height: fill, columns: [fr(0.72), fr(1.28)], columnGap: 46 },
      [
        column(
          { width: fill, height: fill, justify: "center", gap: 30 },
          [
            metric("105,555", "保单记录", C.teal, "每行代表一笔保单交易"),
            metric("30", "原始变量", C.blue, "涵盖投保人、车辆、保单和理赔历史"),
            metric("18.6%", "理赔样本占比", C.coral, "正负样本约 1 : 4.37"),
          ],
        ),
        column(
          { width: fill, height: fill, justify: "center", gap: 24 },
          [
            chart({
              name: "class-imbalance-chart",
              chartType: "bar",
              width: fill,
              height: fixed(360),
              config: {
                title: "理赔样本与非理赔样本分布",
                categories: ["非理赔样本", "理赔样本"],
                series: [{ name: "样本数", values: [85909, 19646] }],
              },
            }),
            simpleTable(
              [
                ["问题", "处理策略", "目的"],
                ["缺失值", "字段缺失检测、业务语义填充或剔除", "保证模型输入完整"],
                ["极端值", "对保费、车价、功率等字段截断", "降低长尾异常影响"],
                ["样本不均衡", "分层抽样 + 正类权重", "减少模型偏向非理赔类"],
                ["字符串字段", "日期解析与类别编码", "转换为可训练数值特征"],
              ],
              [fixed(170), fixed(430), fill],
            ),
          ],
        ),
      ],
    ),
  ]);
}

// 9. Feature engineering
{
  const slide = addSlide("7:05-8:00 讲特征工程。重点是日期参考点、车辆属性、保单合同特征和类别编码。");
  compose(slide, [
    header("特征工程：将业务字段转化为有语义的模型输入", "特征矩阵构建", 9),
    grid(
      { width: fill, height: fill, columns: [fr(1), fr(1)], columnGap: 44 },
      [
        column(
          { width: fill, height: fill, justify: "center", gap: 26 },
          [
            block("日期锚点特征", "以合同开始日期作为统一参考点，计算驾龄、被保人年龄、合同期限、车龄等语义特征。", C.teal),
            block("车辆属性特征", "保留发动机功率、排量、重量、车辆价值、注册年份等字段，并进行异常值截断。", C.blue),
            block("保单与历史理赔特征", "使用年度保费、历史理赔次数、风险类型、缴费方式等字段表达保单风险状态。", C.coral),
          ],
        ),
        column(
          { width: fill, height: fill, justify: "center", gap: 24 },
          [
            simpleTable(
              [
                ["特征类别", "代表字段", "来源"],
                ["日期原始天数", "Date_start_contract_days 等", "日期解析"],
                ["日期语义衍生", "insured_age_years、vehicle_age_years", "业务计算"],
                ["车辆属性", "Power、Weight、Value_vehicle", "原始字段"],
                ["保单合同", "Premium、Type_risk、Payment", "原始字段"],
                ["类别编码", "Type_fuel", "类别数值化"],
              ],
              [fixed(190), fixed(400), fill],
            ),
            txt("最终输入不是简单堆字段，而是将业务时间、车辆属性和历史理赔信息统一为可复现的结构化特征矩阵。", {
              style: { fontSize: 30, bold: true, color: C.teal },
            }),
          ],
        ),
      ],
    ),
  ]);
}

// 10. Model
{
  const slide = addSlide("8:00-9:05 讲模型结构。基础是 MLP，重点是残差块和分类头。");
  compose(slide, [
    header("模型结构：残差式 MLP 面向表格数据二分类", "模型构建与优化", 10),
    grid(
      { width: fill, height: fill, columns: [fr(1.08), fr(0.92)], columnGap: 42 },
      [
        panel(
          { width: fill, height: fill, padding: 14, fill: C.paper, line: { fill: C.line, width: 1 }, borderRadius: "rounded-md" },
          image({ dataUrl: raster.model, contentType: "image/png", width: fill, height: fill, fit: "contain", alt: "InsuranceMLP 网络结构图" }),
        ),
        column(
          { width: fill, height: fill, justify: "center", gap: 24 },
          [
            txt("输入为标准化后的保单特征向量，输出为“是否发生理赔”的概率 logit。", {
              style: { fontSize: 36, bold: true, color: C.navy, lineSpacingMultiple: 1.08 },
            }),
            bullet(
              [
                "残差块缓解网络加深后特征表达退化问题",
                "LayerNorm 与 GELU 提升训练稳定性和非线性表达",
                "Dropout 与 AdamW 配合控制过拟合",
                "Sigmoid 概率结合最优阈值输出离散预测标签",
              ],
              C.blue,
              29,
            ),
          ],
        ),
      ],
    ),
  ]);
}

// 11. Training
{
  const slide = addSlide("9:05-10:05 讲训练策略。强调阈值搜索服务于车险风控的召回目标。");
  compose(slide, [
    header("训练策略：在类别不均衡场景下兼顾召回与稳定性", "训练流程设计", 11),
    grid(
      { width: fill, height: fill, columns: [fr(1), fr(1), fr(1), fr(1)], gap: 22 },
      [
        card(C.coralSoft, "#F5CBC5", block("正类权重", "使用带正类权重的 BCEWithLogitsLoss，提升模型对理赔样本的关注。", C.coral)),
        card(C.blueSoft, "#C9D8FF", block("自动阈值搜索", "在 0.05-0.95 区间搜索候选阈值，优先满足召回率约束。", C.blue)),
        card(C.tealSoft, "#C8E3DC", block("优化与调度", "AdamW 结合 Cosine Warmup 学习率调度，提高收敛稳定性。", C.teal)),
        card(C.amberSoft, "#F1D8A7", block("训练保护", "Early Stopping、AMP 混合精度和梯度裁剪减少过拟合与数值波动。", C.amber)),
      ],
    ),
    panel(
      { width: fill, height: hug, padding: { x: 28, y: 20 }, fill: C.paper, line: { fill: C.line, width: 1 }, borderRadius: "rounded-md" },
      txt("业务含义：模型先输出理赔概率，阈值搜索再决定分类边界。这样可以在风控场景中适度接受误报，尽量减少高风险保单漏判。", {
        style: { fontSize: 31, bold: true, color: C.teal },
      }),
    ),
  ]);
}

// 12. Evaluation
{
  const slide = addSlide("10:05-11:10 展示核心指标。AUC 说明排序能力，Claim Recall 说明对理赔样本的识别。");
  compose(slide, [
    header("模型评估：整体排序能力与理赔样本召回表现良好", "性能评估", 12),
    grid(
      { width: fill, height: fill, columns: [fr(0.75), fr(1.25)], columnGap: 42 },
      [
        column(
          { width: fill, height: fill, justify: "center", gap: 28 },
          [
            metric("0.9604", "AUC", C.teal, "测试集 10,557 条"),
            metric("0.8305", "Claim Recall", C.coral, "理赔样本召回率"),
            metric("0.9121", "Weighted F1", C.blue, "加权平均 F1-score"),
          ],
        ),
        column(
          { width: fill, height: fill, justify: "center", gap: 22 },
          [
            simpleTable(
              [
                ["类别", "Precision", "Recall", "F1-score", "样本数"],
                ["No Claim", "0.9599", "0.9280", "0.9437", "8592"],
                ["Claim", "0.7250", "0.8305", "0.7742", "1965"],
                ["加权平均", "0.9162", "0.9098", "0.9121", "-"],
              ],
              [fixed(160), fixed(150), fixed(150), fixed(160), fixed(130)],
            ),
            grid(
              { width: fill, height: fixed(360), columns: [fr(1), fr(1), fr(1), fr(1)], gap: 14 },
              [
                card("#124D77", "#124D77", column({ width: fill, height: fill, justify: "center", gap: 8 }, [txt("7973", { style: { fontSize: 46, bold: true, color: "#FFFFFF" } }), txt("TN", { style: { fontSize: 22, color: "#D5EAF2" } })])),
                card("#D7EAF2", "#D7EAF2", column({ width: fill, height: fill, justify: "center", gap: 8 }, [txt("619", { style: { fontSize: 46, bold: true, color: C.ink } }), txt("FP", { style: { fontSize: 22, color: C.muted } })])),
                card("#E9F2F7", "#E9F2F7", column({ width: fill, height: fill, justify: "center", gap: 8 }, [txt("333", { style: { fontSize: 46, bold: true, color: C.ink } }), txt("FN", { style: { fontSize: 22, color: C.muted } })])),
                card("#73A9C7", "#73A9C7", column({ width: fill, height: fill, justify: "center", gap: 8 }, [txt("1632", { style: { fontSize: 46, bold: true, color: "#FFFFFF" } }), txt("TP", { style: { fontSize: 22, color: "#EDF7FB" } })])),
              ],
            ),
          ],
        ),
      ],
    ),
  ]);
}

// 13. Ablation
{
  const slide = addSlide("11:10-12:15 讲消融实验。说明优化策略的取舍和最佳网络结构。");
  compose(slide, [
    header("消融实验：优化策略让模型更贴近风控目标", "对照实验", 13),
    grid(
      { width: fill, height: fill, columns: [fr(1.05), fr(0.95)], columnGap: 40 },
      [
        chart({
          name: "ablation-chart",
          chartType: "bar",
          width: fill,
          height: fill,
          config: {
            title: "损失权重与阈值策略对比",
            categories: ["加权+自动", "加权+固定", "非加权+自动", "非加权+固定"],
            series: [
              { name: "F1", values: [0.755, 0.7046, 0.7477, 0.7628] },
              { name: "Recall", values: [0.8198, 0.9216, 0.8518, 0.751] },
            ],
          },
        }),
        column(
          { width: fill, height: fill, justify: "center", gap: 22 },
          [
            txt("实验结论", { style: { fontSize: 38, bold: true, color: C.navy } }),
            bullet(
              [
                "AUC 基本稳定在 0.957 左右，说明模型排序能力较稳定",
                "固定阈值可提升召回，但会明显牺牲准确率或 F1",
                "加权损失与自动阈值能在 F1、Accuracy、Recall 间取得更平衡表现",
              ],
              C.coral,
              28,
            ),
            panel(
              { width: fill, height: hug, padding: 26, fill: C.tealSoft, line: { fill: "#C8E3DC", width: 1 }, borderRadius: "rounded-md" },
              column(
                { width: fill, height: hug, gap: 12 },
                [
                  txt("最佳网络结构", { style: { fontSize: 26, bold: true, color: C.teal } }),
                  txt("256, 512, 512, 256, 128", { style: { fontSize: 38, bold: true, color: C.navy } }),
                  txt("AUC 0.9588 | F1 0.7583 | Accuracy 0.9018 | Recall 0.8282", {
                    style: { fontSize: 23, color: C.muted },
                  }),
                ],
              ),
            ),
          ],
        ),
      ],
    ),
  ]);
}

// 14. Implementation
{
  const slide = addSlide("12:15-13:20 讲系统实现。用截图证明模型训练和预测展示已经落地。");
  compose(slide, [
    header("系统实现：数据管理、模型训练、在线预测形成闭环", "系统实现与测试", 14),
    grid(
      { width: fill, height: fill, columns: [fr(0.88), fr(1.12)], columnGap: 40 },
      [
        column(
          { width: fill, height: fill, justify: "center", gap: 24 },
          [
            block("业务数据管理", "用户、保单、理赔记录、车辆信息的增删改查与权限控制。", C.teal),
            block("模型训练管理", "管理员配置优化器、学习率、隐藏层结构和阈值策略，生成模型文件。", C.blue),
            block("在线理赔预测", "用户选择已有保单或手动填写特征，系统返回概率、标签、风险等级与解释。", C.coral),
            block("结果统计分析", "预测记录持久化，展示风险等级分布、理赔概率分布和历史预测概览。", C.amber),
          ],
        ),
        grid(
          { width: fill, height: fill, rows: [fr(1), fr(1)], columns: [fr(1)], gap: 18 },
          [
            panel(
              { width: fill, height: fill, padding: 12, fill: C.paper, line: { fill: C.line, width: 1 }, borderRadius: "rounded-md" },
              image({ dataUrl: raster.training, contentType: "image/png", width: fill, height: fill, fit: "cover", alt: "模型训练结果界面" }),
            ),
            panel(
              { width: fill, height: fill, padding: 12, fill: C.paper, line: { fill: C.line, width: 1 }, borderRadius: "rounded-md" },
              image({ dataUrl: raster.prediction, contentType: "image/png", width: fill, height: fill, fit: "cover", alt: "预测结果界面" }),
            ),
          ],
        ),
      ],
    ),
  ]);
}

// 15. Testing and summary
{
  const slide = addSlide("13:20-14:50 总结测试、主要工作、不足和未来方向。");
  compose(slide, [
    header("总结与展望：完成从模型研究到系统落地的基本闭环", "结论", 15),
    grid(
      { width: fill, height: fill, columns: [fr(1), fr(1), fr(1)], gap: 26 },
      [
        card(
          C.paper,
          C.line,
          column(
            { width: fill, height: fill, gap: 22 },
            [
              txt("测试验证", { style: { fontSize: 36, bold: true, color: C.teal } }),
              bullet(["登录注册、用户管理、保单管理通过测试", "理赔记录、车辆信息、统计分析通过测试", "模型训练、预测管理、记录统计通过测试"], C.teal, 26),
            ],
          ),
        ),
        card(
          C.paper,
          C.line,
          column(
            { width: fill, height: fill, gap: 22 },
            [
              txt("主要成果", { style: { fontSize: 36, bold: true, color: C.blue } }),
              bullet(["完成残差式 MLP 理赔预测模型", "完成数据处理、特征工程、训练与评估流程", "完成 Spring Boot + Vue3 + FastAPI 平台集成"], C.blue, 26),
            ],
          ),
        ),
        card(
          C.paper,
          C.line,
          column(
            { width: fill, height: fill, gap: 22 },
            [
              txt("未来优化", { style: { fontSize: 36, bold: true, color: C.coral } }),
              bullet(["引入驾驶行为、天气、道路环境等外部数据", "拓展理赔金额估计和多任务联合建模", "增强模型版本管理、预警推送和业务联动"], C.coral, 26),
            ],
          ),
        ),
      ],
    ),
    txt("最终结论：本文实现了车险理赔预测模型与业务系统的结合，为车险风险识别和辅助决策提供了可运行的原型方案。", {
      style: { fontSize: 31, bold: true, color: C.teal },
    }),
  ]);
}

const pptxBlob = await PresentationFile.exportPptx(pres);
await pptxBlob.save(path.join(outputDir, "output.pptx"));

const previews = [];
for (const [i, slide] of pres.slides.items.entries()) {
  const blob = await slide.export({ format: "png" });
  const out = path.join(previewDir, `slide_${String(i + 1).padStart(2, "0")}.png`);
  await fs.writeFile(out, Buffer.from(await blob.arrayBuffer()));
  previews.push(out);
}

await fs.writeFile(
  path.join(scratchDir, "build-summary.json"),
  JSON.stringify({ slide_count: pres.slides.items.length, output: path.join(outputDir, "output.pptx"), previews }, null, 2),
  "utf8",
);

console.log(JSON.stringify({ output: path.join(outputDir, "output.pptx"), previews }, null, 2));
process.exit(0);
