![JavSP](./image/JavSP.svg)

# JavSP

**汇总多站点数据的 AV 元数据刮削器**

从文件名中识别番号，多线程并行抓取多个站点的数据并合并，按命名规则整理影片文件，同时生成 Emby / Jellyfin / Kodi 可直接读取的 NFO 与图片资源。

本项目是 [Yuukiy/JavSP](https://github.com/Yuukiy/JavSP) 的分支：上游功能全部保留，另外把 JavDB 抓取器换成官方 App JSON 接口，并新增「单文件 exe + 外置配置」的打包与部署方式。

![License](https://img.shields.io/github/license/isunding/JavSP)
[![LICENSE](https://img.shields.io/badge/license-Anti%20996-blue.svg)](https://github.com/996icu/996.ICU/blob/master/LICENSE)
![Python 3.10 ~ 3.12](https://img.shields.io/badge/python-3.10%20~%203.12-green.svg)
[![Latest release](https://img.shields.io/github/v/release/isunding/JavSP)](https://github.com/isunding/JavSP/releases/latest)
[![Build](https://img.shields.io/github/actions/workflow/status/isunding/JavSP/cx_freeze.yml?label=build)](https://github.com/isunding/JavSP/actions/workflows/cx_freeze.yml)

## 功能特点

- [x] 自动识别影片番号，支持分片文件
- [x] 多站点数据汇总，多线程并行抓取
- [x] 生成 NFO 元数据文件与高清封面、预览图
- [x] 可自定义文件夹与文件命名规则、分类方式
- [x] 基于 AI 人体分析裁剪素人等非常规封面
- [x] 翻译标题与剧情简介（Google / Bing / 百度 / Claude / OpenAI）
- [x] 内置抓取器可用性测试（`unittest` + GitHub Actions 工作流）
- [x] JavDB 通过官方 App JSON 接口抓取，无需浏览器 Cookies、无需绕过 CloudFlare
- [ ] 匹配本地字幕
- [ ] 使用小缩略图创建文件夹封面
- [ ] 保持不同站点间 genre 分类统一
- [ ] 更多运行模式（仅抓取数据、仅整理）

> WebUI 不在本项目的目标范围内（见上游 issue #148），请通过配置文件与命令行使用。

## 快速开始

### 方式一：下载现成的 exe（Windows，推荐）

1. 到 Releases 页面下载 `JavSP.exe`
2. 把 `JavSP.exe` 和 `config.yml` 放在**同一个文件夹**里
3. 双击运行，在弹窗中选择要整理的影片目录

程序的只读资源（`data/`、`image/`）已打进 exe，`config.yml` 是唯一需要放在外部的文件。**配置固定从 exe 所在目录读取**，用快捷方式、计划任务或从其它目录调用都不影响。缺少配置时会直接提示完整路径。

`scanner.input_directory` 保持 `null` 时，每次运行都会弹窗选择目录；填了具体路径则直接使用该目录。

### 方式二：从源码运行

需要 Python 3.10 ~ 3.12（推荐 3.10）。

```bash
git clone https://github.com/isunding/JavSP.git
cd JavSP
poetry install
poetry run javsp
```

也可以 `python -m javsp`，或安装后直接执行 `javsp`。依赖中 `slimeface` 需要预编译轮子，Windows 与 macOS x64 可直接安装；其它平台若安装失败，可关闭封面裁剪功能。

### 方式三：自己打包单文件 exe

```bash
poetry install
poetry run python tools/build_onefile.py   # 产物：dist/onefile/JavSP.exe
```

脚本使用 PyInstaller onefile：`data/`、`image/` 打进 exe，`config.yml` 不打包、留在 exe 同目录。仓库里另有 `setup.py`（cx_Freeze，产物是一个含 exe + 库的目录），按需选择。

## 配置

配置文件为 `config.yml`，默认取程序目录下那份，也可以用 `-c` 指定别的文件：

```bash
JavSP -c D:/configs/javsp.yml
```

临时覆盖个别配置项、又不想改文件时，用 `--o` 前缀加完整配置路径：

```bash
JavSP --oscanner.input_directory "D:/videos"
JavSP --onetwork.proxy_server null --ocrawler.hardworking false
```

命令行参数优先于配置文件。注意参数名虽是 `--o...` 形式，但没有空格，`o` 后面直接跟配置路径。

常用配置项：

| 配置项 | 说明 |
| --- | --- |
| `scanner.input_directory` | 扫描目录；`null` 表示每次运行弹窗选择 |
| `scanner.minimum_size` | 小于该体积的文件不处理，默认 `232MiB` |
| `scanner.skip_nfo_dir` | 已存在 NFO 的目录直接跳过 |
| `scanner.manual` | 扫描后先人工确认/补充识别结果 |
| `network.proxy_server` | 代理地址，如 `http://127.0.0.1:1080`；`null` 为不使用 |
| `network.retry` / `network.timeout` | 网络失败重试次数与单次超时 |
| `crawler.selection` | 各类型影片使用哪些抓取器，按顺序合并数据 |
| `crawler.required_keys` | 至少拿到哪些字段才算抓取成功，默认 `[cover, title]` |
| `crawler.use_javdb_cover` | `fallback` 时优先用其它站点的无水印封面 |
| `crawler.normalize_actress_name` | 统一女优的多个艺名 |
| `summarizer.move_files` | `true` 移动整理，`false` 原地生成同级文件 |
| `summarizer.path` / `name` | 文件夹与文件命名规则，支持变量引用 |
| `translator.engine` | 翻译引擎，`null` 关闭 |
| `other.interactive` | 需要输入时是否交互，无人值守环境设为 `false` |
| `other.check_update` / `auto_update` | 检查/自动更新。自定义构建建议都设为 `false` |

各项含义在 `config.yml` 内都有逐条注释；命名规则支持的变量见上游 Wiki 的 NamingRule 页面。

## 支持的抓取器

| 类型 | 抓取器 | 说明 |
| --- | --- | --- |
| 普通影片 | `airav` `avsox` `javbus` `javdb` `javlib` `jav321` `mgstage` `prestige` | 默认启用，汇总标题、简介、封面、评分、女优等 |
| | `avwiki` | 女优资料与别名，默认未启用 |
| | `arzon` `arzon_iv` | 实体碟与配信商品信息 |
| 数字商品 | `fanza` `dl_getchu` `gyutto` | 数字发行商品 |
| FC2 | `fc2` `fc2ppvdb` `javmenu` | FC2 作品 |
| | `fc2fan` | 已关站，仅支持本地镜像 |

具体启用哪些见 `crawler.selection`。站点本身的反爬策略与 IP 限制会随时变化，单个站点抓取失败不影响整轮整理，会由其它站点补齐。

## JavDB 抓取器（App API 版）

`javsp/web/javdb.py` 已从网页抓取（cloudscraper + xpath + 浏览器 Cookies）改为 JavDB 官方 App 的 JSON 接口，客户端实现在 `javsp/web/javdb_api.py`：

- 搜索接口按规范化番号精确匹配，避免前缀误匹配
- 详情接口一次取回标题、原名、简介、封面、评分、时长、导演、片商、系列、女优（含头像）、标签与预览图
- 鉴权只需请求头里的一个签名（时间戳 + 固定盐的 MD5），不需要账号登录，也不需要浏览器 Cookies
- 内置重试与线性退避，单个站点网络抖动不会中断整轮刮削
- App 侧图片有单字节 XOR 混淆，下载层会自动还原，否则封面与预览图落盘后无法解码；写进 NFO 的女优头像改用未混淆的普通图片地址

接口地址、CDN 等细节不在此列出，需要时见源码顶部的常量与环境变量说明。可选环境变量：

| 变量 | 说明 | 默认 |
| --- | --- | --- |
| `JAVSP_JAVDB_API_HOST` | 接口域名 | 内置默认 |
| `JAVSP_JAVDB_API_TIMEOUT` | 单次请求超时（秒） | `10` |
| `JAVSP_JAVDB_API_RETRIES` | 网络错误重试次数 | `3` |
| `JAVSP_JAVDB_PROXY` | 覆盖 `network.proxy_server` | 空 |
| `JAVSP_JAVDB_WEB_BASE` | 生成影片网页地址的前缀 | 内置默认 |
| `JAVSP_JAVDB_LEGACY_FALLBACK` | 设为 `1` 时接口失败后回退旧网页抓取器 | 空 |

旧网页版抓取器完整保留在 `javsp/web/javdb_html.py`，`collect_actress_alias` 仍走旧实现。

## 多盘部署

把同一个 exe 放到多个磁盘/目录时，每个目录各放一份 `JavSP.exe` 与该目录自己的 `config.yml` 即可，互不影响：

```
D:\影片A\JavSP.exe   D:\影片A\config.yml
E:\影片B\JavSP.exe   E:\影片B\config.yml
```

因为配置固定按 exe 所在目录解析，不需要设置工作目录，也不会读错别处的配置。需要给不同盘设置不同的整理规则或扫描目录时，只改对应那份 `config.yml`。

## 从 config.ini 迁移

v1.8 及更早版本使用 `config.ini`。新版只认 `config.yml`，可参考新版 `config.yml` 的注释手工重配，或用仓库内的迁移脚本：

```bash
python tools/config_migration.py -i config.ini -o config.yml
```

注意：脚本需要 **Python 3.12+**（f-string 表达式内含反斜杠，3.10/3.11 下会报 `SyntaxError`）；生成的配置仍需手工检查——补齐 `scanner.manual`、删掉已不存在的抓取器名、修正 `scrap_interval` 等字段后才能被新版正常加载。

## 常见问题

**启动提示「未找到配置文件」**
把 `config.yml` 放到 `JavSP.exe` 所在目录；提示信息里会给出期望的完整路径。

**封面或预览图打不开**
多半是图片没有经过 XOR 还原。请使用本分支的 exe 或源码，旧版程序无法解码 App 侧的图片。

**抓取全部失败 / 超时**
多数站点需要代理。先设置 `network.proxy_server`，再确认该代理可正常访问外网站点。

**每次运行都要选一次目录**
这是 `scanner.input_directory: null` 的设计行为。想固定目录，把路径填进去即可。

**整理完没移动文件**
确认 `summarizer.move_files` 为 `true`；为 `false` 时只在影片同级生成 NFO 与图片。

## 参与贡献

此项目不需要捐赠。欢迎通过以下方式参与：

- 完善 Wiki 与文档
- 补充单元测试数据（例如发现某系列番号识别不准，整理一下提 Issue 就很有帮助）
- 完善 genre 翻译
- Bugfix / 新功能，欢迎提交 Pull Request
- 顺手点个 Star

## 许可

本项目所有权利与许可受 GPL-3.0 License 与 [Anti 996 License](https://github.com/996icu/996.ICU/blob/master/LICENSE_CN) 共同限制。使用本项目即表示你额外接受以下条款：

- 本软件仅供学习 Python 与技术交流使用
- 请勿在微博、微信等墙内公共社交平台宣传本项目
- 请遵守当地法律法规
- 禁止将本软件用于商业用途
