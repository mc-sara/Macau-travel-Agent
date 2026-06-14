# 澳门适老化景点数据更新说明

## 目录用途

本目录保存澳门景点适老化数据的阶段性更新结果，包括核心景点清单、门票修订、适老化设施信息、交通指引，以及供 Agent 做长者画像匹配的推荐理由表。

当前 `outputs/update/python/` 下的脚本主要是对已采集表格做清洗、字段补全和人工映射修订；原始爬取与主数据流水线位于 `D:\personal\比赛\old people UM\feet`。表格中的开放时间、门票、客流、无障碍说明等内容来自 `feet` 项目抓取官方/准官方页面后的清洗结果，并在 `outputs/update` 阶段继续做人工映射、门票、交通和适老化说明修订。

## feet 数据爬取与处理流水线

`D:\personal\比赛\old people UM\feet` 是原始数据爬取、清洗、建表、导出和校验项目。它是一个 Node.js 项目，主要依赖 `crawlee`、`playwright`、`cheerio` 和 `exceljs`。

项目默认目录关系如下：

```text
D:\personal\比赛\old people UM
├─ feet          # 爬虫、清洗、导出脚本
├─ data_raw      # 原始 HTML / 页面抓取文件
├─ data_clean    # 规范化 JSON、中间表、校验 JSON
└─ outputs       # 原始导出的 Excel
```

完整执行入口是 `feet/run_all.ps1`，实际调用 `npm run all`：

```text
check
  -> discover
  -> crawl:attractions / crawl:events / crawl:accessibility / crawl:heritage
  -> build:id
  -> build:attractions / build:accessibility / build:transport
  -> export
  -> validate
```

也可以用 `run_all.ps1 -Sample` 或脚本参数 `--sample` 做小样本运行；部分爬取脚本还支持 `--limit=<数量>` 限制抓取详情页数量。

### 数据来源发现

`01_discover_sources.mjs` 读取 `scripts/lib/sources.mjs` 中定义的来源地址，包括：

| 来源键 | 地址 | 用途 |
|---|---|---|
| `mgtoAttractionsZh` | 澳门旅游局中文观光页 | 景点列表、景点详情、开放时间、门票、地址、客流文本 |
| `mgtoEventsZh` / `mgtoEventsEn` | 澳门旅游局活动页 | 活动类候选景点或节庆活动 |
| `mgtoAccessibilityZh` / `mgtoAccessibilityEn` | 澳门旅游局无障碍旅游指南 | 无障碍详情、信息页、公交/巴士页、地图链接 |
| `heritageCn` | 澳门世界遗产网站 | 世界遗产相关补充来源 |
| `dsat` | 交通事务局 | 公共交通补充文本 |
| `mlm` | 澳门轻轨 | 轻轨补充文本 |

发现步骤会用 Playwright 打开页面，保存渲染后的 HTML 到 `data_raw/source_discovery/`，同时抽取页面链接、标题、最终 URL、可能出现的 JSON/XHR 响应，并输出 `data_clean/source_discovery.json`。

### 景点爬取逻辑

`02_crawl_mgto_attractions.mjs` 是核心景点爬虫。它使用 Crawlee 的 `PlaywrightCrawler`，从澳门旅游局中文观光首页开始，按固定分类进入列表页：

- 澳门世界遗产
- 博物馆及展览厅
- 教堂
- 庙宇
- 花园
- 炮台
- 其他景点

处理流程：

1. 先访问观光首页，再将各分类页加入队列。
2. 在分类页中抽取景点详情链接，并按 `--sample` 或 `--limit` 分配抓取配额。
3. 在详情页中读取标题、H1、meta 描述、页面正文、JSON-LD。
4. 从表格行或页面文本中抽取 `address`、`opening_hours`、`ticket_info`。
5. 用文本规则初步判断 `region` 和 `category`。
6. 检查详情页是否存在无障碍指南入口；如果存在，会尝试打开对应无障碍指南并同步抽取 `信息`、`无障碍层`、`公共汽车/巴士` 等 tab 内容。
7. 保存景点记录到 `data_clean/mgto_attractions.json`，并将随景点页抓到的无障碍详情合并到 `data_clean/accessibility_raw.json`。

景点爬取会保存每个页面的原始 HTML 到 `data_raw/mgto_attractions/`，无障碍详情 HTML 保存到 `data_raw/accessibility/`。

### 活动爬取逻辑

`03_crawl_mgto_events.mjs` 从澳门旅游局中英文 `whatson` 页面开始抓取活动相关页面。

处理逻辑：

1. 跟随同域内 `whatson` 链接。
2. 保存页面 HTML 到 `data_raw/mgto_events/`。
3. 从 H1、meta、title 中确定名称。
4. 从正文中用日期正则抽取 `event_date_text`。
5. 根据正文判断区域、类别、坐标、开放时间和门票。
6. 输出 `data_clean/mgto_events.json`。

后续 `06_normalize_id_map.mjs` 会过滤英文活动页、下载页、索引页等导航类页面，只保留可作为候选点位的活动记录。

### 无障碍指南爬取逻辑

`04_crawl_accessibility.mjs` 专门抓澳门旅游局无障碍旅游指南。

处理逻辑：

1. 打开无障碍指南索引页。
2. 用 `collectGuideItemsAcrossPages()` 遍历分页，收集可见指南条目。
3. 为每个条目构造内部详情请求参数，如 `__codex_kind=accessibility-detail`、`__codex_item_name`、`__codex_item_id`。
4. 重新打开指南页并定位对应条目，点击进入详情。
5. 依次点击并抽取 `信息`、`无障碍层`、`公共汽车/巴士` 等 tab。
6. 如果 `信息` tab 有 Google Maps 链接，会尝试打开并提取经纬度。
7. 输出 detail/index 记录到 `data_clean/accessibility_raw.json`。

默认模式会读取已有 `accessibility_raw.json` 并按 `name_zh + source_name + page_kind` 去重合并；加 `--overwrite` 时只保留本次新抓取记录。

### 世界遗产与交通补充爬取

`05_crawl_heritage_and_transport.mjs` 从世界遗产、交通事务局和轻轨网站开始抓取补充资料。

处理逻辑：

1. 只跟随 `wh.mo/cn`、`dsat.gov.mo`、`mlm.com.mo` 域名内链接。
2. 保存原始 HTML 到 `data_raw/heritage_transport/`。
3. 以 URL 判断来源名称：`Macao World Heritage`、`DSAT` 或 `Macau LRT`。
4. 抽取标题、正文、meta、坐标、区域、类别。
5. 输出 `data_clean/heritage_transport.json`。

后续建表时，世界遗产记录用于补充景点候选；DSAT 和轻轨记录用于交通文本匹配。

## 清洗、标准化与后续数据处理逻辑

### 文本清洗与基础识别

公共工具在 `scripts/lib/text.mjs` 中：

- `cleanText()`：压缩空白、去掉不可见空格、统一 trim。
- `firstNonEmpty()`：从多个候选值中取第一个非空值。
- `detectRegion()`：用关键词判断 `澳门半岛`、`氹仔`、`路环`，未命中则为 `其他`。
- `detectCategory()`：用关键词判断展览、演出、节庆、博物馆、酒店综合体、公园、海滨、历史景点等。
- `seniorReason()`：按类别和正文生成适老化推荐理由初稿。

这些规则是启发式，不等同于权威分类；因此 `outputs/update/python/update_region.py` 后续又用人工 `id -> region` 映射修正区域。

### ID 归一化与候选合并

`06_normalize_id_map.mjs` 是中间数据汇总脚本，读取：

- `mgto_attractions.json`
- `mgto_events.json`
- `heritage_transport.json`

核心逻辑：

1. 过滤导航页、下载页、搜索页、索引页、英文活动页等非业务记录。
2. 对观光分类列表页做文本拆分，必要时从列表页正文中扩展出景点候选。
3. 规范名称，去掉澳门旅游局站点后缀。
4. 用名称去括号、去空格、小写后的 key 做去重。
5. 如果同一名称有多来源，优先保留详情页质量更高的来源；同时合并别名、来源说明、正文、地址、开放时间、门票、坐标等字段。
6. 按区域分配 id：澳门半岛从 101 起，氹仔从 201 起，路环从 301 起，活动从 401 起，其它从 501 起。
7. 输出 `data_clean/id_map.json` 和 `data_clean/normalized_candidates.json`。

`id_map.json` 是后续所有表的基础主键来源。

### 主景点表构建

`07_build_attractions_table.mjs` 读取 `id_map.json`、`normalized_candidates.json`、`accessibility_raw.json`，输出 `data_clean/macau_attractions.json`。

处理逻辑：

1. 用候选记录中的 `id` 对应原始规范化记录。
2. 对每个景点用名称、别名、URL slug 在无障碍记录中找最佳匹配。
3. 地址优先来自景点详情页，其次从无障碍指南 `信息` tab 文本抽取。
4. 开放时间优先来自景点详情页；如果详情页只有 `以官方公布为准`，则尝试从无障碍指南 `信息` tab 抽取。
5. 经纬度优先使用无障碍指南 Google Maps 链接解析结果，其次使用原始来源坐标。
6. `official_url` 优先从无障碍指南信息文本中的网址抽取，否则使用景点来源 URL。
7. 输出景点主表 JSON，之后由 Excel 导出脚本生成 `macau_attractions.xlsx`。

### 适老化/无障碍表构建

`08_build_accessibility_table.mjs` 读取 `id_map.json`、`normalized_candidates.json`、`accessibility_raw.json`，输出 `data_clean/attraction_accessibility.json`。

处理逻辑：

1. 对每个景点在无障碍 raw 记录中找最佳匹配，优先 detail 页，其次 index 页。
2. 将无障碍详情文本、索引文本和景点详情正文合并为证据文本。
3. 用关键词规则识别布尔或等级字段，例如轮椅、无障碍入口、电梯、坡道、扶手、无障碍厕所、工作人员协助、轮椅租借、急救等。
4. 用正则抽取台阶数、步行距离、建议停留时间等数值；无法抽取时用 `-1`。
5. 根据客流词、室内/冷气、暴晒/淋雨、安静/嘈杂等关键词推导人流压力、暴晒风险、噪音、室内休息点等等级。
6. 根据可用证据生成 `senior_tips_zh`、推荐入口路线和应避开路线。
7. 将未能明确归类但与长者服务相关的文本放入 `other_senior_facilities_uncertain`。

该脚本遵循保守原则：未抓到明确证据时使用 `unknown`、`不明`、`待核实` 或 `-1`，不把资料缺失直接解释为设施不存在。

### 交通表构建

`09_build_transport_table.mjs` 读取 `macau_attractions.json`、`heritage_transport.json` 和 `accessibility_raw.json`，输出 `data_clean/attraction_transport.json`。

处理逻辑：

1. 先从无障碍指南匹配记录中取 `bus_text`。
2. 再从 DSAT、澳门轻轨来源记录中，按景点名称、别名、URL slug 与正文做匹配。
3. 合并公交/轻轨证据文本。
4. 从文本中抽取路线、低地板和轮椅座椅状态、下车/投放站、距离。
5. 如果无法抽取结构化路线，则生成 `待核实` 的 fallback 交通记录。
6. 交通记录 id 从 2001 开始自增，`attraction_id` 才是景点外键。
7. 下车后步行指引使用统一保守模板，提醒先核实官方交通页面，并优先选择电梯、扶手电梯或平缓路面。

### Excel 导出逻辑

`10_export_excels.mjs` 使用 `exceljs` 将 JSON 导出为独立 Excel：

| JSON | 导出 Excel |
|---|---|
| `id_map.json` | `澳门经典ID对应表格.xlsx` |
| `macau_attractions.json` | `macau_attractions.xlsx` |
| `attraction_accessibility.json` | `attraction_accessibility.xlsx` |
| `attraction_transport.json` | `attraction_transport.xlsx` |

导出时会：

1. 使用 `scripts/lib/schema.mjs` 中定义的列顺序和中文表头。
2. 创建 `Sheet1`。
3. 冻结首行。
4. 给首行加深蓝底白字粗体。
5. 启用首行筛选。
6. 根据内容自动调整列宽，并开启自动换行。

### 校验逻辑

`11_validate_outputs.mjs` 读取清洗后的 JSON 表，输出 `data_clean/validation_report.json` 和 `outputs/validation_report.xlsx`。

主要校验项：

1. `id_map` 中 `id` 是否唯一。
2. 同一 id 是否映射多个名称。
3. 景点表 id 是否存在于 id map。
4. 景点是否缺经纬度、official_url。
5. 活动类记录是否可能已过期。
6. 无障碍表 `attraction_id` 是否能连到景点主表。
7. 无障碍记录是否缺 `source_url` 或 `senior_tips_zh` 过短。
8. 交通表 `attraction_id` 是否能连到景点主表。
9. 交通表是否缺 `source_url`、`walking_route`，以及低地板状态是否属于 `true`、`false`、`unknown`。

如果存在 error，脚本会设置非 0 退出码；warning 会进入报告但不阻断导出。

## outputs/update 后续修订逻辑

`feet` 项目生成的是基础版 Excel；`outputs/update` 目录保存的是在基础版之上的后续修订结果。当前能从脚本和表格关系确认的后处理包括：

1. `update_region.py`：在基础 `macau_attractions.xlsx` 上按人工 `id -> region` 映射修正区域，输出 `macau_attractions_corrected.xlsx`。
2. `update_name_en_inplace.py`：按中文名到英文名的人工映射，覆盖修正 `name_en (葡/英文名)`。
3. `update_english_names.py`：按 11 个指定 `id` 追加英文名补丁，处理中文名映射未覆盖或需要更精确名称的景点。
4. `macau_attractions_corrected_ticket_updated.xlsx`：在 corrected 基础上进一步修订门票字段；相对 `macau_attractions_corrected.xlsx` 有 86 条 `ticket_info (门票)` 变更，建议作为当前景点主表。
5. `attraction_accessibility_filled.xlsx`：在无障碍基础表上补齐并改写适老化描述，当前保留 107 个景点的 30 个适老化字段。
6. `attraction_transport_updated.xlsx`：在交通基础表上补充或人工改写路线、上下车点和步行指引；当前每个景点一条交通记录，共 107 条。
7. `澳门经典ID对应表格_适老化理由修订.xlsx`：在 ID 对应表上修订适老化推荐理由，用于 Agent 画像匹配。

因此当前推荐的数据链路是：

```text
feet 爬取官方/准官方页面
  -> data_raw/*.html
  -> data_clean/*.json
  -> outputs/*.xlsx 基础表
  -> outputs/update/python/*.py 与人工表格修订
  -> outputs/update/*.xlsx 当前可用表
```

## 文件清单

| 文件 | 行数 | 主要用途 | 关键字段 |
|---|---:|---|---|
| `macau_attractions_corrected.xlsx` | 107 | 核心景点表的区域、英文名修订版 | `id (主键)`、`name_zh (中文名)`、`name_en (葡/英文名)`、`region (区域)` |
| `macau_attractions_corrected_ticket_updated.xlsx` | 107 | 在核心景点表基础上进一步修订门票信息，建议作为当前核心景点主表 | 同上，重点更新 `ticket_info (门票)` |
| `attraction_accessibility_filled.xlsx` | 107 | 每个景点的适老化/无障碍设施与风险描述 | `attraction_id (外键)` |
| `attraction_transport_updated.xlsx` | 107 | 每个景点的长者友好交通方案 | `id (主键)`、`attraction_id (对应景点)` |
| `澳门经典ID对应表格_适老化理由修订.xlsx` | 107 | 景点类别与适老化推荐理由，用于 Agent 画像匹配 | `id (主键)`、`scenic_category_zh (景点类别)`、`适老化推荐理由（供 Agent 画像匹配）` |

## Python 更新逻辑

### `update_region.py`

该脚本读取 `macau_attractions.xlsx`，按照内置的 `id -> region` 映射修正 `region (区域)`，输出 `macau_attractions_corrected.xlsx`。

处理逻辑：

1. 用 `pandas.read_excel(..., engine="openpyxl")` 读取源表。
2. 检查必须存在 `id (主键)` 和 `region (区域)` 两列。
3. 遍历每行，根据 `region_mapping` 用 `id` 写回区域。
4. 统计被修改的记录数和未命中的 id。
5. 保存为 `macau_attractions_corrected.xlsx`。

### `update_name_en_inplace.py`

该脚本直接修改 `macau_attractions_corrected.xlsx`，根据 `name_zh (中文名)` 到英文名的映射补全或覆盖 `name_en (葡/英文名)`。

处理逻辑：

1. 读取 `macau_attractions_corrected.xlsx`。
2. 检查 `name_zh (中文名)` 与 `name_en (葡/英文名)` 两列。
3. 如果中文名在映射表中，则将英文名更新为官方或整理后的英文名称。
4. 当前英文名为空、为 `待核实` 或与映射值不同都会被覆盖。
5. 覆盖保存原文件。

### `update_english_names.py`

该脚本也是直接修改 `macau_attractions_corrected.xlsx`，但使用的是按 `id` 指定的 11 条英文名补丁。

处理逻辑：

1. 读取 `macau_attractions_corrected.xlsx`。
2. 按 `id (主键)` 匹配指定景点。
3. 将 `name_en (葡/英文名)` 更新为 `updates` 字典中的英文名。
4. 覆盖保存原文件。

这三个脚本构成的顺序关系可以理解为：

```text
macau_attractions.xlsx
  -> update_region.py
  -> macau_attractions_corrected.xlsx
  -> update_name_en_inplace.py / update_english_names.py
  -> macau_attractions_corrected.xlsx
  -> 后续门票修订
  -> macau_attractions_corrected_ticket_updated.xlsx
```

## 表格之间的关系

推荐以 `macau_attractions_corrected_ticket_updated.xlsx` 作为主表，因为它保留核心景点字段，并在 `macau_attractions_corrected.xlsx` 基础上修订了门票信息。

核心关系如下：

```text
macau_attractions_corrected_ticket_updated.xlsx
  id (主键)
    1 : 1 -> attraction_accessibility_filled.xlsx.attraction_id (外键)
    1 : 1 -> attraction_transport_updated.xlsx.attraction_id (对应景点)
    1 : 1 -> 澳门经典ID对应表格_适老化理由修订.xlsx.id (主键)
```

注意：`attraction_transport_updated.xlsx` 中的 `id (主键)` 是交通记录编号，范围为 `2001` 至 `2107`，不是景点 id。关联景点时应使用 `attraction_id (对应景点)`。

## 字段说明

### 核心景点主表

`macau_attractions_corrected_ticket_updated.xlsx` 包含 107 个景点，每个 `id (主键)` 唯一。主要字段：

| 字段 | 说明 |
|---|---|
| `id (主键)` | 景点唯一编号，也是其它表的关联键 |
| `name_zh (中文名)` | 景点中文名称 |
| `name_en (葡/英文名)` | 景点葡文/英文名称，已由脚本映射修订 |
| `region (区域)` | 地理区域，当前统计为澳门半岛 83、路环 13、氹仔 9、路氹 1、其他 1 |
| `latitude (纬度)` / `longitude (经度)` | 当前为空，后续可补地理坐标 |
| `address (地址)` | 景点地址，当前 83 条非空 |
| `opening_hours (开放时间)` | 开放时间说明 |
| `ticket_info (门票)` | 门票说明，较上一版有 86 条变更 |

### 适老化/无障碍表

`attraction_accessibility_filled.xlsx` 通过 `attraction_id (外键)` 关联核心景点表。当前 107 条外键全部能在核心景点表中找到。

主要字段覆盖：

| 字段组 | 代表字段 |
|---|---|
| 通行能力 | `wheelchair_friendly (轮椅友善)`、`accessible_entrance (无障碍入口)`、`ramp_available (是否有坡道)`、`handrails_available (是否有扶手)` |
| 垂直交通 | `has_elevator (有无电梯/升降机/扶梯)`、`steep_slopes (有无陡坡)`、`stairs_count (台阶级数)` |
| 休息与卫生间 | `rest_areas (长椅密集度)`、`accessible_toilet (无障碍厕所)`、`toilet_distance_level (厕所便利度)` |
| 地面和环境风险 | `ground_surface (路面状况)`、`non_slip_surface (防滑性)`、`trip_hazards (绊倒风险)`、`sun_or_rain_exposure (暴晒或淋雨风险)` |
| 长者提示 | `senior_tips_zh (长者专属提示语)`、`best_access_route_zh (推荐长者入口/路线)`、`avoid_route_zh (建议避开的路线)` |

当前轮椅友善统计为 31 条 `true`、76 条 `false`。部分字段使用 `官方未说明`、`待核实`、`-1` 表示未能从资料中确认，不应当作真实的否定值。

### 交通表

`attraction_transport_updated.xlsx` 通过 `attraction_id (对应景点)` 关联核心景点表。当前 107 条外键全部能在核心景点表中找到。

字段说明：

| 字段 | 说明 |
|---|---|
| `id (主键)` | 交通记录编号，不是景点编号 |
| `attraction_id (对应景点)` | 对应核心景点表的 `id (主键)` |
| `transport_type (交通类型)` | 交通方式，如巴士、轻轨 |
| `line_name (路线)` | 推荐路线或线路集合 |
| `low_floor_wheelchair_seat_available (低地板和轮椅座椅可用)` | 对低地板巴士、轮椅位、轻轨无障碍设施的说明 |
| `boarding_point (长辈上车点)` | 建议长者上车点 |
| `dropoff_point (下车站点)` | 建议下车点 |
| `walking_route (下车后步行指引)` | 下车后的步行路径和避险提示 |

交通类型统计：巴士 78 条，巴士加轻轨 28 条，无 1 条。

### 景点类别与推荐理由表

`澳门经典ID对应表格_适老化理由修订.xlsx` 通过 `id (主键)` 关联核心景点表。名称与核心表完全对齐，类别和推荐理由可用于 Agent 画像匹配、路线推荐、长者偏好解释。

主要字段：

| 字段 | 说明 |
|---|---|
| `id (主键)` | 与核心景点表一致 |
| `name_zh (中文名称)` | 景点中文名 |
| `scenic_category_zh (景点类别)` | 景点类别，如博物馆及展览厅、澳门世界遗产、花园、庙宇、教堂等 |
| `region (所属区域)` | 表内区域字段 |
| `适老化推荐理由（供 Agent 画像匹配）` | 面向长者画像和推荐解释的文本理由 |

注意：该表的 `region (所属区域)` 与核心景点主表的 `region (区域)` 有 61 条不一致。若做地理位置筛选、分区统计或地图展示，建议以核心景点主表为准；若只做推荐理由或类别匹配，则可直接使用该表的类别和推荐理由字段。

## 推荐使用方式

### 数据库建表建议

建议拆成 4 类表：

| 逻辑表 | 来源文件 | 主键 | 外键 |
|---|---|---|---|
| `attractions` | `macau_attractions_corrected_ticket_updated.xlsx` | `id` | 无 |
| `attraction_accessibility` | `attraction_accessibility_filled.xlsx` | 可用 `attraction_id` | `attraction_id -> attractions.id` |
| `attraction_transport` | `attraction_transport_updated.xlsx` | `id` | `attraction_id -> attractions.id` |
| `attraction_recommendation_profile` | `澳门经典ID对应表格_适老化理由修订.xlsx` | `id` | `id -> attractions.id` |

### Agent 推荐逻辑建议

可以按以下顺序组合数据：

1. 从核心景点主表读取名称、区域、开放时间、门票。
2. 用适老化表补充轮椅、坡道、台阶、休息点、卫生间、暴晒、人流和长者提示。
3. 用交通表补充从主要站点到景点的低负担到达方式。
4. 用推荐理由表补充景点类别和面向长者画像的推荐解释。
5. 对 `官方未说明`、`待核实`、`-1` 等值保持不确定状态，不要直接推断为不存在或不可用。

## 数据质量备注

1. 所有 5 个表均为 107 条记录，核心关联键完整，没有发现外键缺失。
2. `latitude (纬度)`、`longitude (经度)` 在核心表中当前全部为空，如需要地图或距离计算，需要后续补充坐标。
3. `ticket_info (门票)` 在 `macau_attractions_corrected_ticket_updated.xlsx` 中相对 `macau_attractions_corrected.xlsx` 有 86 条更新，建议使用更新后的文件。
4. 无障碍表中多个字段包含 `官方未说明`，说明资料来源没有明确披露，不等同于设施不存在。
5. 适老化推荐理由表的区域字段与核心表不完全一致，地理区域请以核心表为准。
