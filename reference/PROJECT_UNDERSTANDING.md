# 葡萄通项目初步理解

## 项目概览

“葡萄通”是一套面向葡萄种植管理的完整软件系统，当前仓库由三个主要目录组成：

- `grape_frontend`：Flutter 移动端应用。
- `grape_backend`：Django + DRF 后端服务，并集成多类模型调用。
- `diseasemodel`：独立 FastAPI 病害风险模型服务。

根目录当前不是 Git 仓库。

## 前端：`grape_frontend`

前端是 Flutter 项目，入口文件为：

- `grape_frontend/lib/main.dart`

主页面为 `HomeView`，底部 Tab 包含四个主要入口：

- 地块
- 任务
- 识别
- 论坛

Tab 页面定义在：

- `grape_frontend/lib/constants/ui_constants.dart`

主要功能目录包括：

- `features/auth`：登录、用户资料、版权/说明、意见反馈等。
- `features/field`：地块、作物、品种、生育期、天气、通知、共享、回收站等。
- `features/task`：植保、灌溉、任务列表和任务详情。
- `features/communition`：病害识别、上报、历史消息、智能问答相关页面。
- `features/forum`：论坛、帖子、评论、回复通知等。
- `features/map`：地图和地块绘制/展示相关逻辑。
- `features/note`：农事记录、生育期记录、病害记录等。

前端接口地址大量硬编码为：

```text
http://118.89.50.72/
```

集中配置之一是：

- `grape_frontend/lib/net_config.dart`

但很多页面和控制器也直接写了完整 URL，例如地块、天气、论坛、任务、通知等模块。

前端依赖主要包括：

- `dio` / `http`：网络请求。
- `shared_preferences`：本地存储。
- `amap_flutter_map` / `amap_flutter_location`：高德地图和定位。
- `image_picker`、`flutter_image_compress`：图片选择与压缩。
- `web_socket_channel`：WebSocket 通信。
- `fl_chart`：图表。
- `flutter_pdfview`、`video_player`：PDF 和视频展示。

## 后端：`grape_backend`

后端是 Django 4.2 + Django REST Framework 项目，主项目目录为：

- `grape_backend/grape/grape`

关键入口：

- `grape_backend/grape/manage.py`
- `grape_backend/grape/grape/settings.py`
- `grape_backend/grape/grape/urls.py`
- `grape_backend/grape/grape/asgi.py`
- `grape_backend/grape/grape/routing.py`

后端使用 PostgreSQL，数据库连接通过环境变量配置：

- `GXG_DB_NAME`
- `GXG_DB_USER`
- `GXG_DB_PASSWORD`
- `GXG_DB_HOST`
- `GXG_DB_PORT`

主要依赖包括：

- Django 4.2.1
- djangorestframework
- djangorestframework-simplejwt
- django-filter
- django-cors-headers
- channels
- django-apscheduler
- psycopg2
- geopandas / shapely / fiona
- requests / httpx
- drf-yasg
- openmeteo_requests

### 后端业务模块

主路由中挂载了较多业务模块：

- `user`：用户与手机号验证码登录。
- `field`：地块、地块边界、地块共享、回收站。
- `crop`：作季/葡萄种植季。
- `master_data`：葡萄品种、杀菌剂、杀虫剂、生育期、栽培方式、病害类型等基础数据。
- `weather` / `weatherdata`：天气数据、天气更新、喷药适宜性、病害数据更新调度。
- `phenmodel` / `phendata`：物候模型和物候结果数据。
- `disease` / `diseasedata`：病害模拟请求体和病害结果数据。
- `task`：植保任务、灌溉任务。
- `notice`：通知和 WebSocket 推送。
- `forum`：论坛和评论。
- `message`：历史消息。
- `yolo`：YOLO 识别。
- `seg` / `unet`：病害图像分割和严重度识别。
- `vitgpt`：图像问答或智能识别相关 WebSocket/API。
- `warn`：病害发现/预警上报。
- `grapepdf`：PDF 文件相关功能。
- `updataapk`：APK 更新。
- `suggestions`：意见反馈。

### 核心数据模型

地块模型：

- `grape_backend/grape/field/models.py`

`Field` 保存用户、地块名称、面积、GeoJSON 边界、质心经纬度、共享用户、删除状态、行政区域等。保存时会根据 GeoJSON 生成 SVG 边界图，并调用外部地理编码接口获取区域。

作季模型：

- `grape_backend/grape/crop/models.py`

`CropSeason` 关联葡萄品种、栽培方式、地块、树龄、地块经纬度、地块面积等，是天气、物候、病害、任务等数据的核心关联对象。

基础数据模型：

- `grape_backend/grape/master_data/models.py`

包括葡萄品种、杀菌剂、杀虫剂、生育期、栽培方式、提醒规则、病害类型等。

### WebSocket

ASGI 配置使用 Channels：

- `ws/notice/<group_name>/`：通知推送。
- `ws/vitgpt/<group_name>/`：智能问答或图像识别会话。

当前 Channels layer 使用内存层：

```python
channels.layers.InMemoryChannelLayer
```

## 病害模型服务：`diseasemodel`

`diseasemodel` 是独立的 FastAPI 服务，入口为：

- `diseasemodel/main.py`

启动后默认监听：

```text
0.0.0.0:5002
```

核心接口：

```text
POST /simulate
```

接口接收一个作季级请求体，内部构建 `CropSeason`，再根据请求的 feature 调用作物和病害模型，返回对应结果。

核心调度文件：

- `diseasemodel/crop_season/crop_season.py`

主要模块：

- `crop_season`：请求体解析和作季编排。
- `crops`：作物及作物病害模型。
- `models`：底层病害、物候算法。
- `management`：施药保护期、推荐处理窗口等管理建议。
- `weather`：天气数据对象封装。
- `utilities`：区域、国家编码、生育期处理、地图等工具。

当前 README 中说明支持：

- 葡萄 `VITVI`
- 苹果 `MABSD`

葡萄病害包括：

- `PLASVI`：葡萄霜霉病。
- `UNCINE`：葡萄白粉病。
- `BOTRCI`：灰霉病。
- `ELSIAM`：葡萄炭疽/黑痘相关病害。
- `GUIGBI`：葡萄黑腐病。

常用返回 feature：

- `dailyInfectionRisks`：逐日感染风险。
- `shortTimeAggregatedRisks`：短周期聚合风险。
- `stressRisks`：病害风险。
- `fieldRisks`：田块综合风险。
- `stressProtectionTimes`：药剂保护期。
- `actionRecommendations`：处理建议。
- `treatmentWindows`：处理窗口。

## 后端与病害模型的关系

Django 后端会在天气更新和任务变更时组装病害模型请求体，然后请求病害模拟接口。

主要逻辑集中在：

- `grape_backend/grape/weather/views.py`
- `grape_backend/grape/task/views.py`
- `grape_backend/grape/task/serializers.py`
- `grape_backend/grape/weather/serializers.py`
- `grape_backend/grape/weatherdata/serializers.py`

典型流程：

1. 后端定时任务获取所有未删除地块下的作季。
2. 调用外部天气服务获取历史天气和未来天气。
3. 调用后端内置物候模型生成生育期数据。
4. 查询已完成植保任务，整理历史施药记录。
5. 组装 `rb_disease` 请求体。
6. 请求病害模拟接口。
7. 解析 `dailyInfectionRisks`、`stressRisks`、`fieldRisks`、`stressProtectionTimes`、`actionRecommendations`、`treatmentWindows`。
8. 写入 `DiseaseData` 和 `RB`。
9. 根据风险和生育期生成通知。

当前后端调用病害模型的 URL 多处硬编码为：

```text
http://118.89.50.72/disease/simulate
```

这看起来是线上反向代理后的病害服务地址，而不是本地 `diseasemodel` 的 `:5002/simulate`。

## 图像识别和模型

后端模型目录：

- `grape_backend/model`

其中包含：

- `phen`：葡萄物候模型。
- `qingkephen`：青稞物候模型或相关实验模型。
- `spray`：喷药适宜性模型。
- `seg`：图像分割模型。
- `vit`：ViT/EfficientViT 相关模型。
- `yolov8-main`：YOLOv8 相关代码。

YOLO 接口位于：

- `grape_backend/grape/yolo/views.py`

其逻辑大致是接收图片，保存到指定目录，调用命令行 `yolo predict model=ACF-YOLO.onnx ...`，再解析输出并返回识别结果和处理后的图片。

分割接口位于：

- `grape_backend/grape/seg/views.py`

其逻辑是接收图片，调用：

```python
model.seg.LDSP.Segmentation
```

返回处理后的图片和严重度文本。

## 外部服务依赖

项目当前依赖多个外部服务或公网地址：

- `http://118.89.50.72/`：主要后端 API 地址。
- `http://118.89.50.72/disease/simulate`：病害模拟接口。
- `https://weather.agromodel.cn/api/v1/weather_history/`：历史天气。
- `https://weather.agromodel.cn/api/v1/weather/`：未来天气。
- `https://weather.agromodel.cn/api/v1/geodecoder/`：地理编码。
- `https://cotton.agrodigits.cn/api/v1/stt_gxg/`：短信验证码相关接口。
- `ws://118.89.50.72/ws/notice/...`：通知 WebSocket。
- `ws://106.75.19.191:3389/ws/vitgpt/...`：智能问答 WebSocket。
- `http://106.75.19.191:3389/vit/vit/`：图像问答或 VIT 识别接口。

## 初步风险和后续关注点

- 前端 API 地址分散硬编码，不利于环境切换和部署维护。
- 后端 `SECRET_KEY` 明文写在 `settings.py`，生产环境存在安全风险。
- 后端和前端都有硬编码公网 IP、第三方服务地址和 WebSocket 地址。
- 后端定时任务、天气拉取、物候模拟、病害模拟、通知生成耦合在较长的函数中，后续维护成本较高。
- `grape_backend/model` 下包含完整第三方模型代码、权重和示例数据，体量大，边界需要进一步梳理。
- Django Channels 当前配置为内存层，不适合多进程或分布式部署。
- 一些模型路径和运行路径在代码中写死，例如 YOLO 中的 Linux 服务器目录。
- 病害模型服务独立运行，但 Django 当前调用的是公网代理地址，后续需要明确本地开发、测试、生产三套调用方式。
- 根目录不是 Git 仓库，无法直接查看提交历史或变更状态。

## 后续建议

后续如果要继续接手，建议优先做以下梳理：

1. 画出前端页面到后端 API 的调用矩阵。
2. 梳理后端各 app 的模型关系和核心表结构。
3. 把硬编码地址抽成环境配置。
4. 明确 `diseasemodel` 与 Django 后端的部署关系。
5. 单独整理天气更新、物候模拟、病害模拟、通知生成这条主链路。
6. 梳理视觉模型接口，包括输入、输出、权重路径和运行环境。
