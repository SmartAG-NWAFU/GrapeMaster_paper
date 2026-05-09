# 葡萄通项目论文技术参考

本文档基于当前仓库代码阅读整理，目的是为后续撰写论文的技术方法、系统架构、模型集成和实现细节提供参考。仓库由移动端应用、云端业务后端、独立病害风险模型服务和若干视觉智能模型组成，整体可概括为面向葡萄生产管理的端到端智能决策平台。

## 1. 项目定位

“葡萄通”是一套面向葡萄园精细化管理的移动端智能服务系统。系统以地块和作季为核心对象，融合地理边界、天气数据、葡萄物候模型、病害风险模型、农事任务、通知提醒、图像识别和用户社区等功能，为葡萄种植者提供从数据采集、风险预测到管理建议执行的闭环支持。

从论文视角看，该系统不是单一模型或单一应用，而是一个“移动端-后端-模型服务”协同的数字农业平台。其关键技术主线包括：

- 基于移动端的葡萄园地块管理、任务管理、图像采集和结果展示。
- 基于 Django 后端的地块、作季、天气、物候、病害、任务和通知数据管理。
- 基于 FastAPI 的作季级病害风险模拟服务。
- 基于 GDD/BBCH 的葡萄物候预测。
- 基于气象、生育期、品种感病性和施药历史的病害风险动态评估。
- 基于 YOLO、MobileSAM、UNet 和 EfficientViT 的图像识别与病害严重度估计。
- 基于 WebSocket 和任务系统的风险结果推送与农事决策转化。

## 2. 总体架构

当前仓库主要包含三个工程目录：

- `grape_frontend`：Flutter 移动端应用。
- `grape_backend`：Django + Django REST Framework 后端服务。
- `diseasemodel`：FastAPI 病害风险模型服务。

系统整体可抽象为四层：

1. 用户交互层：移动端 App，负责地块绘制、作季创建、天气和风险查看、任务创建、图片上传、通知处理和论坛交互。
2. 业务服务层：Django 后端，负责用户、地块、作季、天气、物候、病害、任务、通知、论坛、记录和模型接口管理。
3. 模型计算层：独立病害模型服务和后端内嵌的物候、喷药适宜性、图像识别、图像分割模型。
4. 外部数据层：天气服务、地理编码服务、短信验证码服务、文件静态服务和 WebSocket 服务。

典型业务链路为：

1. 用户在 App 中创建或选择地块。
2. 后端根据地块边界计算面积和质心坐标。
3. 用户为地块创建葡萄作季，选择品种、栽培方式和树龄。
4. 后端调用天气服务获取历史天气和未来天气。
5. 后端调用物候模型，根据平均温度累计热量并预测 BBCH 生育期。
6. 后端整理小时天气、生育期、品种感病性和历史施药记录，构造病害模型请求体。
7. 后端调用 `diseasemodel` 病害模拟接口，获得感染风险、病害风险、田块风险、药剂保护期和处理建议。
8. 后端将风险结果写入数据库，并生成通知或推荐任务。
9. App 展示天气、物候、病害风险、任务、通知和诊断结果。
10. 用户执行植保或灌溉任务后，任务状态更新会反向影响病害模型的施药历史和后续风险计算。

## 3. 前端技术细节

### 3.1 技术栈

前端是 Flutter 移动端项目，入口文件为 `grape_frontend/lib/main.dart`，主界面为 `grape_frontend/lib/features/home/view/home_view.dart`。底部四个 Tab 在 `grape_frontend/lib/constants/ui_constants.dart` 中定义。

主要依赖包括：

- `dio`、`http`：REST API 请求。
- `shared_preferences`：用户、地块、作季和局部状态缓存。
- `amap_flutter_map`、`amap_flutter_location`：高德地图和定位。
- `geolocator`：位置获取。
- `image_picker`、`flutter_image_compress`、`image`：图像选择、压缩和预处理。
- `web_socket_channel`：实时通知和图像问答会话。
- `fl_chart`：图表展示。
- `flutter_pdfview`、`video_player`：技术资料和介绍视频展示。
- `flutter_localizations`、`intl`：中英文国际化。

### 3.2 功能模块

前端主要功能目录为：

- `features/auth`：登录、用户资料、版权说明、反馈建议。
- `features/field`：地块列表、地块详情、作季、品种、栽培方式、生育期、天气、病害数据和通知。
- `features/map`：地块边界绘制、地图展示和地块提交。
- `features/task`：植保任务、灌溉任务、任务列表、任务详情和状态更新。
- `features/communition`：在线专家、图像识别、病害上报、历史消息和严重度识别。
- `features/forum`：论坛帖子、评论、回复和用户互动。
- `features/note`：普通农事记录、生育期记录、病害记录和图片记录。

### 3.3 页面组织

App 启动后进入 `HomeView`，采用 `IndexedStack` 保持四个 Tab 页面的状态。底部导航包括：

- 地块：进入系统核心数据对象，承载地块、作季、天气、风险、通知和资料入口。
- 任务：查看、创建、删除和完成植保或灌溉任务。
- 识别：拍照或选择图片后上传识别，进入诊断问答或严重度检测。
- 论坛：提供种植者之间的问题交流和互动。

这种组织方式使 App 从用户视角形成“我的地块-我要做的任务-我看到的问题-我和别人交流”的工作流。

### 3.4 地块与地图功能

前端支持基于地图的地块创建和地块查看。地块数据通过 GeoJSON 形式提交到后端，后端负责解析边界、计算面积和质心。前端则展示由后端生成的地块 SVG 图标，并把地块作为后续作季、天气、病害和任务的上层对象。

相关前端控制器和视图包括：

- `features/map/controller/map_controller.dart`
- `features/map/view/map_view.dart`
- `features/field/controller/field_controller.dart`
- `features/field/view/field_view.dart`
- `features/field/view/crop_view.dart`

### 3.5 任务功能

任务模块包括植保和灌溉两类任务。任务列表页面从后端按用户查询任务，并按执行时间和任务状态排序。用户可通过滑动操作删除任务或将任务标记为“已完成”。对于植保任务，药剂列表、用水量、喷雾器容量、混药器容量和执行日期会被提交到后端，并进一步影响病害模型的施药保护期和风险状态。

任务相关文件包括：

- `features/task/view/tasklist_view.dart`
- `features/task/view/weather_view.dart`
- `features/task/view/sterillweather.dart`
- `features/task/controller/irrigation_controller.dart`
- `features/field/controller/sterill_controller.dart`

### 3.6 图像识别与诊断

识别入口位于 `features/communition/communition.dart`。用户可从相册或相机选择图片，前端会将图片裁剪为 256 x 256，并压缩到约 1 MB 以下，再通过 multipart 请求上传到识别服务。

识别相关功能包括：

- 图像病害分类和防治建议。
- 历史诊断消息。
- WebSocket 智能问答。
- 病害上报。
- 病斑严重度识别。

该功能使系统不仅依赖模型预测的气象风险，也能利用用户现场图像形成实际病害诊断和反馈。

### 3.7 通知和实时交互

前端通过 HTTP 和 WebSocket 两种方式获取通知。WebSocket 地址模式为：

```text
ws://118.89.50.72/ws/notice/<username>/
```

通知用于提示风险、任务、地块共享和管理建议。前端在地块页和通知组件中维护未读通知列表，可进行单条已读、全部已读、接受共享、创建任务等操作。

### 3.8 前端工程特点

前端实现的特点是功能覆盖完整、面向实际生产操作，但也存在工程化改进空间：

- API 地址大量硬编码，环境切换困难。
- 网络请求分散在页面、控制器和组件中，缺少统一 API 层。
- 部分页面代码较长，视图、业务逻辑和数据解析耦合较强。
- 登录、通知和任务刷新逻辑在多个页面重复出现。

这些问题不影响论文中对系统功能和技术路线的描述，但可在“系统实现限制与未来优化”中说明。

## 4. 后端技术细节

### 4.1 技术栈

后端是 Django 4.2 + Django REST Framework 项目，入口为：

- `grape_backend/grape/manage.py`
- `grape_backend/grape/grape/settings.py`
- `grape_backend/grape/grape/urls.py`
- `grape_backend/grape/grape/asgi.py`
- `grape_backend/grape/grape/routing.py`

主要技术包括：

- Django ORM：业务数据建模。
- Django REST Framework：REST API。
- SimpleJWT：移动端 Token 认证。
- PostgreSQL：业务数据库。
- Django Channels：WebSocket 通知和 VIT 会话。
- django-apscheduler：定时更新天气、物候和病害数据。
- geopandas、matplotlib、shapely 相关生态：地块 GeoJSON 解析和图标生成。
- httpx、requests：调用天气、地理编码和模型服务。
- drf-yasg：API 文档。

### 4.2 后端模块

后端挂载了较多 Django app，主要包括：

- `user`：用户、手机号登录和 JWT 认证。
- `field`：地块、边界、共享、回收站。
- `crop`：作季。
- `master_data`：品种、药剂、生育期、栽培方式、提醒规则和病害类型。
- `weather`、`weatherdata`：天气数据获取、存储和喷药适宜性。
- `phenmodel`、`phendata`：物候模型数据。
- `disease`、`diseasedata`：病害模型请求和输出数据。
- `task`：植保任务和灌溉任务。
- `notice`：通知和 WebSocket 推送。
- `forum`：论坛、评论和回复。
- `message`：诊断历史消息。
- `warn`：病害发现上报。
- `yolo`：YOLO 图像识别。
- `seg`、`unet`：病害图像分割和严重度识别。
- `vitgpt`：图像识别、诊断问答和 WebSocket 会话。
- `grapepdf`、`suggestions`、`updataapk`：资料、反馈和 App 更新。

### 4.3 核心数据模型

#### 4.3.1 地块模型

`field/models.py` 中的 `Field` 是平台基础对象。主要字段包括：

- 用户 ID。
- 地块 UUID。
- 地块名称。
- 地块面积。
- GeoJSON 边界。
- 地块 SVG 图标。
- 质心经纬度。
- 删除状态。
- 共享用户。
- 行政区域。

`Field.save()` 中会调用 `make_icon()`，通过 GeoJSON 解析地块边界，计算面积和质心，并生成 SVG 边界图。同时调用外部地理编码接口，根据经纬度获取区域信息。

#### 4.3.2 作季模型

`crop/models.py` 中的 `CropSeason` 关联地块、葡萄品种、栽培方式、树龄、地块面积和坐标。它是天气、物候、病害和任务数据的核心关联对象。

#### 4.3.3 主数据模型

`master_data/models.py` 包括：

- `GrapeVariety`：葡萄品种、用途、熟期、抗性描述、霜霉病和白粉病感病性。
- `Fungicide`：杀菌剂名称、目标病害、剂型、有效成分、剂量、适用生育期、保护天数、治疗天数和防效。
- `Pesticide`：杀虫剂基础数据。
- `GrowthStage`：BBCH 生育期及中英文描述。
- `CultivationMethod`：栽培方式。
- `Reminder`：生育期对应农艺操作提醒。
- `DiseaseType`：病害类型。

这些数据为模型参数、任务创建和用户展示提供结构化基础。

#### 4.3.4 任务模型

`task/models.py` 包括：

- `CropProtection`：植保任务。
- `Fungicides`：植保任务关联杀菌剂。
- `Pesticides`：植保任务关联杀虫剂。
- `Irrigation`：灌溉任务。

任务具有执行日期和状态。若执行日期早于当前日期且任务仍为“未执行”，后端保存时会自动标记为“已过期”。植保任务完成后，其药剂信息会被转化为病害模型的 `applied_fungicides` 输入，从而影响后续风险。

#### 4.3.5 天气、物候和病害结果

天气模型包括作季小时天气和日天气。物候结果保存于 `PhenData`，病害结果保存于 `DiseaseData`，病害模型原始请求体或中间请求体保存在 `RB` 中。

`DiseaseData.diseasedata` 中保存的主要序列包括：

- 日期。
- 霜霉病感染风险代码。
- 白粉病感染风险代码。
- 霜霉病风险代码。
- 白粉病风险代码。
- 田块综合风险代码。
- 药剂保护期。
- 推荐代码。
- 操作类型代码。
- 处理窗口代码。
- 处理窗口开始和结束日期。

### 4.4 天气-物候-病害主链路

主链路集中在 `weather/views.py` 和 `weatherdata/serializers.py`。其核心流程如下：

1. 查询所有有效作季。
2. 根据作季地块质心坐标调用天气服务。
3. 获取从当年 1 月 1 日到昨天的历史天气，以及未来 16 天预报。
4. 合并历史和预报的小时、日尺度天气。
5. 对缺测值进行简单前向填补。
6. 计算未来 16 天逐小时喷药适宜性。
7. 构造物候模型输入 `rb`，包含省份、经纬度、年份、品种、树龄、熟期和日平均温度。
8. 调用物候模型 `simulate()` 生成每日 GDD、GDDCUSUM 和 BBCH。
9. 查询历史已完成植保任务，将药剂转成病害模型的施药记录。
10. 构造病害模型请求体 `rb_disease`。
11. 调用病害模型接口。
12. 解析并压缩病害模型返回结果。
13. 写入 `PhenData`、`DiseaseData` 和 `RB`。
14. 根据风险、生育期变化和处理窗口生成通知。

这条链路是论文中系统方法部分最重要的技术流程。

### 4.5 通知和 WebSocket

ASGI 配置中挂载两个 WebSocket 路由：

```text
ws/notice/<group_name>/
ws/vitgpt/<group_name>/
```

`notice` 用于实时通知推送，`vitgpt` 用于图像问答或诊断会话。当前 Channels layer 使用内存层：

```python
channels.layers.InMemoryChannelLayer
```

这适合单进程或开发部署，不适合多进程和分布式部署。论文中如果强调生产部署，应把 Redis Channel Layer 作为建议配置。

## 5. 物候模型

物候模型位于 `grape_backend/model/phen`，核心文件为：

- `phenm.py`
- `GDD.py`
- `BBCHGDD.json`

模型输入为每日平均温度，以及品种、熟期、年份、区域和作季信息。模型首先使用 Wang-Engel 温度响应函数计算每日有效积温 GDD：

```text
T <= Tbase 或 T >= Tcei 时，热效应为 0；
Tbase < T < Tcei 时，根据 Wang-Engel 非线性温度响应函数计算热效应。
```

当前默认参数包括：

- `Tbase = 10`
- `Topt = 30`
- `Tcei = 42`

每日 GDD 累加得到 `GDDCUSUM`，再通过 `BBCHGDD.json` 中不同区域、品种或熟期的阈值，将累积热量映射到 BBCH 主生育期和一位 BBCH 阶段。

模型输出包括：

- `Date`
- `GDD`
- `GDDCUSUM`
- `BBCH_Principal`
- `BBCH_One_digit`

后端进一步根据 `GrowthStage` 表补充主阶段编码、中英文描述，用于 App 展示和农艺提醒。

## 6. 病害风险模型服务

### 6.1 服务架构

`diseasemodel` 是独立 FastAPI 服务，入口为 `diseasemodel/main.py`。服务暴露：

```text
POST /simulate
```

请求体由 `crop_season/crop_season_input.py` 定义，服务接收一个作季级请求体后，构造 `CropSeason` 对象，并根据 `requested_features` 返回对应结果。

### 6.2 输入数据

主要输入字段包括：

- `crop_season_uuid`：作季标识。
- `province`：区域，示例为 Guang Xi。
- `crop_eppo_code`：作物 EPPO 编码，葡萄为 `VITVI`。
- `time_zone`：时区。
- `latitude`、`longitude`：经纬度。
- `request_datetime`：请求时间。
- `growth_stage`：每日生育期、GDD 和 BBCH。
- `weather_hourly`：小时天气。
- `weather_daily`：日天气，可为空。
- `applied_fungicides`：历史施药记录。
- `stress_eppo_codes`：目标病害 EPPO 编码。
- `variety_susceptibility`：品种感病性。
- `requested_features`：请求返回的模型结果。

当前葡萄场景主要使用的目标病害为：

- `PLASVI`：葡萄霜霉病。
- `UNCINE`：葡萄白粉病。

代码中也包含其他葡萄病害：

- `BOTRCI`：灰霉病。
- `ELSIAM`：葡萄炭疽或黑痘相关病害。
- `GUIGBI`：葡萄黑腐病。

### 6.3 输出特征

系统主要使用以下模型输出：

- `dailyInfectionRisks`：逐日感染适宜性。
- `shortTimeAggregatedRisks`：短期聚合风险。
- `stressRisks`：病害风险。
- `fieldRisks`：田块综合风险。
- `stressProtectionTimes`：药剂保护期。
- `actionRecommendations`：处理建议。
- `treatmentWindows`：处理窗口。

风险代码主要包括：

- `NOT_SEASONAL`：不在病害发生季节。
- `UNFAVORABLE`：不适宜。
- `FAVORABLE`：适宜。
- `OPTIMAL`：高风险或最适宜。
- `PROTECTED`：受药剂保护。

处理窗口包括：

- `FUTURE`：未来建议窗口。
- `CURRENT`：当前处理窗口。
- `MISSED`：已错过窗口。
- `NOT_PRESENT`：无处理窗口。

### 6.4 作季级调度

`CropSeason` 对象负责：

- 解析请求体。
- 初始化天气对象。
- 动态加载作物类。
- 动态加载病害类。
- 推导模拟季节起止日期。
- 按 `requested_features` 调用作物模型方法。
- 将内部 DataFrame 结果转换为接口 JSON。

该设计使模型服务可以按作物和病害扩展。当前葡萄类为 `VITVI`，其病害类从 `crops/VITVI/diseases` 动态加载。

### 6.5 天气感染适宜性

葡萄病害通用类为 `VITVIDisease`。其逐日感染适宜性计算主要包括：

1. 从小时天气中提取每日温度、相对湿度和降水等变量。
2. 使用 Magarey 方法计算日尺度天气适宜性。
3. 根据 BBCH 生育期计算生育期修正。
4. 根据品种感病性计算品种修正。
5. 根据施药记录计算药剂效应。
6. 将天气、生育期、品种和药剂效应相乘，得到综合适宜性。
7. 根据配置阈值将连续值分类为风险等级。
8. 对逐日适宜性进行滚动平均，得到短期聚合风险。

Magarey 方法位于 `models/disease/magarey.py`。其核心思想是：

- 以相对湿度超过阈值的小时数作为叶面湿润时长代理。
- 根据日平均温度计算温度适宜性。
- 由温度适宜性调整感染所需湿润时长。
- 若湿润时长满足要求且温度适宜性大于 0，则输出 0 到 1 的感染适宜度。

### 6.6 病害初侵染和发生期

`VITVIDisease` 还包含初侵染过程模拟。模型基于以下过程推断病害 onset：

- 越冬或间作期低温天数对初始菌源的影响。
- 湿润小时和热量累积驱动菌源成熟。
- 降雨事件驱动孢子释放。
- 天气适宜性、菌源释放、生育期和品种感病性共同决定感染事件。

在 onset 之前，病害风险被修正为 `UNFAVORABLE`；在病害发生 BBCH 范围之外，风险被修正为 `NOT_SEASONAL`。

### 6.7 药剂保护和风险修正

施药记录输入格式包括：

- `applied_date`
- `curative_efficacy`
- `curative_protection_days`
- `preventive_efficacy`
- `preventive_protection_days`
- `stress`

后端会根据用户完成的植保任务，从杀菌剂主数据表读取目标病害、防效、保护天数和治疗天数，并转换为病害模型输入。

`FungicideEffects.effect_from_applied_fungicide()` 计算药剂效应。若某病害在参考日期处于药剂预防或治疗保护期内，则药剂效应小于 1，并降低感染风险。若病害风险在非季节外且药剂总体效应小于 1，风险会被标记为 `PROTECTED`。

`stressProtectionTimes` 用于返回每个病害当前可推导的保护结束日期。

### 6.8 田块综合风险

田块风险由多个病害的风险合成。合成逻辑位于 `Crop.get_field_risk_for_a_day()`。基本规则是：

- 若所有目标病害均为 `PROTECTED`，田块风险为 `PROTECTED`。
- 若部分病害受保护、部分病害未保护，则取未保护病害中的最高风险。
- 其他情况下取所有目标病害中的最高风险。

该规则使综合风险既能反映多病害叠加，也能避免药剂保护状态掩盖未保护病害。

### 6.9 处理建议和施药窗口

`management/fungicide.py` 中的 `fungicide_spray_recommendation()` 根据田块风险生成管理建议。规则可概括为：

- `NOT_SEASONAL`、`UNFAVORABLE`、`PROTECTED`、`FAVORABLE` 通常为 `NOT_NEEDED`。
- `OPTIMAL` 对应 `RECOMMENDED` 和 `TREAT`。
- 在首次推荐处理日前若干天生成 `FUTURE` 预警窗口。
- 从推荐处理日开始到治疗窗口结束为 `CURRENT`。
- 超过处理窗口但风险仍存在时标记为 `MISSED`，并可能变为 `NECESSARY`。

该逻辑把风险预测转化为用户可理解、可执行的植保管理建议。

## 7. 视觉识别模型

### 7.1 YOLO 识别

YOLO 接口位于 `grape_backend/grape/yolo/views.py`。后端接收图片后保存到静态目录，调用命令行：

```text
yolo predict model=ACF-YOLO.onnx source=<image_dir> task=detect project=<save_dir>
```

模型输出被解析为图片级和总体统计结果，例如正常、畸形、空粒、畸形率和萌发率等。当前代码包含 `ACF-YOLO.onnx` 和 `ACF-YOLO.pt`。

### 7.2 病斑严重度分割

严重度识别接口位于 `grape_backend/grape/seg/views.py`，核心模型管线在 `grape_backend/model/seg/LDSP.py`。

LDSP 管线包括三个阶段：

1. YOLO 检测叶片或叶盘区域。
2. MobileSAM 根据检测框分割叶片区域。
3. UNet 对裁剪叶片进行叶片和病斑像素分割。

严重度计算方式为：

```text
Severity = 病斑像素数 / (病斑像素数 + 叶片像素数) * 100
```

系统返回带框和严重度标注的结果图，以及每个检测区域的严重度数值。

### 7.3 EfficientViT 分类和诊断建议

EfficientViT 相关代码位于 `grape_backend/model/vit`。`vitgpt.py` 中加载 `efficientvit` 分类模型，输入图像经 Resize、Tensor 转换和 ImageNet 标准化后进行分类。

当前映射类别包括：

- 葡萄斑枯病。
- 葡萄黑腐病。
- 埃斯卡真菌感染，即葡萄黑麻疹。
- 葡萄健康。
- 葡萄黄化病。

代码中还内置了针对不同病害类别的防治建议文本。结合 `vitgpt` WebSocket，可形成“图像识别 + 防治建议 + 问答”的交互式诊断流程。

## 8. 数据闭环

系统形成了较完整的数据闭环：

1. 用户创建地块，系统获得地理边界和坐标。
2. 作季建立后，系统获得品种、熟期、树龄和栽培方式。
3. 后端按地块坐标拉取天气数据。
4. 物候模型将温度序列转换为 BBCH 生育期。
5. 病害模型将天气、生育期、品种感病性和施药历史转换为风险和建议。
6. 任务系统把模型建议转化为植保或灌溉任务。
7. 用户完成任务后，施药信息重新进入病害模型输入。
8. 图像识别和病害上报补充现场观测。
9. 通知系统把模型结果及时推送给用户。

从论文角度，这一闭环是系统区别于单纯预测模型或单纯管理 App 的关键。

## 9. 可提炼的论文技术贡献

### 9.1 端到端葡萄园智能管理架构

系统实现了从移动端数据采集、云端数据管理、模型服务计算到用户决策反馈的端到端架构。该架构可以支撑葡萄园尺度的地块管理、作季监测、病害预警和农事任务推荐。

### 9.2 地块-作季驱动的数据组织

系统以地块作为空间单元，以作季作为时间管理单元，将天气、物候、病害、任务和记录全部绑定到作季上。这种组织方式符合多年生果树生产管理的实际需求。

### 9.3 物候和病害模型融合

系统不是单独使用天气阈值判断病害，而是先用温度驱动 BBCH 生育期预测，再将生育期作为病害发生期限制和风险修正因素。该设计使病害风险计算更贴近作物生长过程。

### 9.4 多因子病害风险评估

病害模型综合考虑：

- 小时天气。
- 生育期。
- 品种感病性。
- 病害初侵染过程。
- 施药保护效应。
- 多病害田块综合风险。

这比单一气象指标阈值更适合实际生产场景。

### 9.5 风险到任务的决策转化

系统将模型输出转换为推荐代码、操作类型和施药窗口，并通过通知和任务系统送达用户。该设计体现了从预测模型到农业管理决策的落地路径。

### 9.6 图像模型与风险模型互补

气象和物候模型提供前瞻性风险预警，图像识别提供现场病害诊断和严重度评估。两类模型分别覆盖“预测”和“观测”，共同增强系统对病害管理的支持能力。

## 10. 论文方法部分建议结构

论文技术方法可按以下结构展开：

1. 系统总体架构：移动端、后端、模型服务和外部数据源。
2. 数据模型设计：用户、地块、作季、天气、物候、病害、任务和通知。
3. 天气数据处理：历史天气、未来预报、小时和日尺度数据融合。
4. 葡萄物候模型：Wang-Engel GDD 和 BBCH 映射。
5. 病害风险模型：输入、感染适宜性、初侵染、生育期修正、品种修正、施药修正和风险分类。
6. 管理建议生成：田块综合风险、药剂保护期、处理窗口和任务推荐。
7. 视觉识别模型：YOLO、MobileSAM、UNet、EfficientViT 和严重度计算。
8. 系统实现：Flutter App、Django REST API、FastAPI 模型服务、WebSocket 通知。
9. 应用流程或案例：某地块从创建作季到病害预警和任务生成的完整流程。
10. 系统局限和未来优化。

## 11. 可写入论文的技术流程图建议

建议后续绘制以下图：

1. 系统总体架构图：App、Django 后端、PostgreSQL、FastAPI 病害模型、视觉模型、外部天气服务。
2. 数据流图：地块和作季输入到天气、物候、病害、任务和通知。
3. 病害风险模型流程图：小时天气、生育期、品种感病性、施药历史到风险和建议。
4. 视觉识别流程图：图片上传、检测、分割、分类、严重度和建议。
5. 数据库核心实体关系图：User、Field、CropSeason、Weather、PhenData、DiseaseData、Task、Notification。
6. 用户工作流图：建地块、建作季、看风险、收通知、建任务、完成任务、更新风险。

## 12. 当前工程限制

论文中如果需要讨论系统部署或未来优化，可提以下限制：

- 前端和后端均存在大量硬编码公网 IP 和服务地址，不利于多环境部署。
- Django Channels 当前使用内存层，不适合多进程或分布式部署。
- YOLO 和部分模型路径存在服务器绝对路径或相对路径假设。
- 天气更新、物候模拟、病害模拟和通知生成在后端部分函数中耦合较强。
- 前端网络请求分散，缺少统一 API 客户端和环境配置。
- 病害模型中不同病害的实现成熟度不完全一致，当前主链路主要稳定接入霜霉病和白粉病。
- 当前论文若描述图像模型性能，需要补充独立测试集、评价指标和实验结果。
- 当前论文若描述病害风险模型效果，需要补充田间观测数据、风险预测对比和验证指标。

## 13. 论文表述建议

建议将系统命名为“面向葡萄园病害预警与农事决策的移动智能平台”或“基于物候-病害模型融合的葡萄园智能管理系统”。技术表述中应突出“系统集成”和“决策闭环”，避免只写成普通 App 或单一模型。

可以使用如下概括性表述：

> 本研究构建了一套面向葡萄生产管理的移动端智能决策平台。系统以地块和作季为基本管理单元，集成天气数据服务、葡萄物候模型、病害风险模型、植保任务管理和图像智能诊断模块，实现了从地块数据采集、作物生长阶段预测、病害风险评估到农事操作建议推送的闭环管理。

也可使用如下技术方法表述：

> 在模型层面，系统首先基于日平均温度和 Wang-Engel 温度响应函数计算有效积温，并结合品种或熟期参数映射至 BBCH 生育期；随后将小时气象数据、BBCH 生育期、品种感病性和历史施药记录输入病害风险模型，计算逐日感染适宜性、短期聚合风险、病害风险和田块综合风险；最后基于田块风险和药剂保护状态生成处理建议和施药窗口。

## 14. 后续写论文仍需补充的数据

为了形成完整论文，当前代码理解之外还需要补充以下材料：

- 系统实际部署架构和服务器配置。
- 目标用户、应用场景和使用地点。
- 葡萄品种、地块数量、气象数据时间范围。
- 病害模型验证数据和评价指标。
- 物候模型验证数据和 BBCH 观测对比。
- 图像识别模型训练集、测试集、类别数、样本量和精度指标。
- 严重度分割模型的标注方法、IoU、Dice 或像素精度。
- 用户使用案例或系统运行截图。
- 与已有葡萄病害预警系统或农业管理平台的对比。

这些内容是论文从“系统介绍”走向“研究论文”的关键支撑。

