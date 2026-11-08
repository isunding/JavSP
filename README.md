![JavSP](./image/JavSP.svg)

# Jav Scraper Package

**汇总多站点数据的AV元数据刮削器**

提取影片文件名中的番号信息，自动抓取并汇总多个站点数据的 AV 元数据，按照指定的规则分类整理影片文件，并创建供 Emby、Jellyfin、Kodi 等软件使用的元数据文件

**WebUI**: UI界面不是[此项目的目标](https://github.com/Yuukiy/JavSP/issues/148)。

**i18n**: This project currently supports only Chinese. However, if you're willing, you can [vote here](https://github.com/Yuukiy/JavSP/discussions/157) for the language you'd like to see added

![License](https://img.shields.io/github/license/Yuukiy/JavSP)
[![LICENSE](https://img.shields.io/badge/license-Anti%20996-blue.svg)](https://github.com/996icu/996.ICU/blob/master/LICENSE)
![Python 3.10](https://img.shields.io/badge/python-3.10-green.svg)
[![Crawlers test](https://img.shields.io/github/actions/workflow/status/Yuukiy/JavSP/test-web-funcs.yml?label=crawlers%20test)](https://github.com/Yuukiy/JavSP/actions/workflows/test-web-funcs.yml)
[![Latest release](https://img.shields.io/github/v/release/Yuukiy/JavSP)](https://github.com/Yuukiy/JavSP/releases/latest)
[![996.icu](https://img.shields.io/badge/link-996.icu-red.svg)](https://996.icu)
## 功能特点

下面这些是一些已实现或待实现的功能，在逐渐实现和完善，如果想到新的功能点也会加进来。

- [x] 自动识别影片番号
- [x] 支持处理影片分片
- [x] 汇总多个站点的数据生成NFO数据文件
- [x] 每天自动对站点抓取器进行测试
- [x] 多线程并行抓取
- [x] 下载高清封面
- [x] 基于AI人体分析裁剪素人等非常规封面的海报
- [x] 自动检查和更新新版本
- [x] 翻译标题和剧情简介
- [x] JavDB 通过官方 App JSON 接口抓取（无需浏览器 Cookies、无需绕过 CloudFlare）
- [ ] 匹配本地字幕
- [ ] 使用小缩略图创建文件夹封面
- [ ] 保持不同站点间 genre 分类的统一
- [ ] 不同的运行模式（抓取数据+整理，仅抓取数据）
- [ ] 可选：所有站点均抓取失败时由人工介入

## 本分支的改动

### JavDB 抓取器改用官方 App 接口

`javsp/web/javdb.py` 已从网页抓取（cloudscraper + xpath + 浏览器 Cookies）改为 JavDB 官方 App 的 JSON 接口，实现在 `javsp/web/javdb_api.py`，移植自 [SakuraMedia](https://github.com/tinypinglite/sakuramediabe) 的 `src/metadata/_providers/javdb.py`：

- 搜索 `/api/v2/search`：按规范化番号精确匹配，按发行日期倒序取最新一条，避免前缀误匹配
- 详情 `/api/v4/movies/{id}`：一次拿到标题、原名、简介、封面、评分、时长、导演、片商、系列、女优（含性别与头像）、标签、预览图
- 鉴权用请求头 `jdsignature`（`时间戳.lpw6vgqzsp.md5(时间戳 + 盐)`），不需要登录，也不需要浏览器 Cookies
- 内置重试与线性退避，单个站点网络抖动不会中断整轮刮削

原网页版抓取器完整保留在 `javsp/web/javdb_html.py`，设置 `JAVSP_JAVDB_LEGACY_FALLBACK=1` 时在 API 失败后回退；`collect_actress_alias` 仍走旧实现。

`javsp/web/base.py` 的下载层会自动还原 JavDB app CDN（`tp.spfcas.com`）图片的单字节 XOR 混淆，否则封面和预览图落盘后无法解码；写进 NFO 的女优头像则改写为未混淆的网页 CDN 地址。

可选环境变量：

| 变量 | 说明 | 默认 |
| --- | --- | --- |
| `JAVSP_JAVDB_API_HOST` | API 域名 | `jdforrepam.com` |
| `JAVSP_JAVDB_API_TIMEOUT` | 单次请求超时（秒） | `10` |
| `JAVSP_JAVDB_API_RETRIES` | 网络错误重试次数 | `3` |
| `JAVSP_JAVDB_PROXY` | 覆盖 `network.proxy_server` 的代理 | 空 |
| `JAVSP_JAVDB_WEB_BASE` | 生成影片网页 URL 的前缀 | `https://javdb.com` |
| `JAVSP_JAVDB_LEGACY_FALLBACK` | 设为 `1` 时回退旧网页抓取器 | 空 |

### 打包为单文件 exe（配置文件外置）

```bash
python tools/build_onefile.py    # 产物：dist/onefile/JavSP.exe
```

- 使用 PyInstaller onefile，只把只读资源（`data/`、`image/`）打进 exe
- **`config.yml` 不打包**，与 exe 放在同一目录；运行时优先读取 exe 同目录的配置，不受启动时工作目录影响
- 与 `setup.py`（cx_Freeze，产物是一个目录）并存，按需选择
- 部署到多个磁盘根目录时，每个根目录放一份 `JavSP.exe` + 自己的 `config.yml` 即可；`scanner.input_directory` 留空（`null`）则每次运行都会弹窗选择要整理的文件夹

## 迁移

功能修改日志：[ChangeLog](./CHANGELOG.md)

如果你之前使用的是config.ini，请重新配置JavSP，或者通过[这个脚本](./tools/config_migration.py)来将其迁移到最新的config.yml。

注意：`config_migration.py` 需要 Python 3.12+（f-string 表达式内含反斜杠，在 3.10 下会报 `SyntaxError`）；迁移结果中的无效抓取器名、`scrap_interval` 等字段可能仍需手工清理后再使用。

## [安装并运行JavSP](https://github.com/Yuukiy/JavSP/wiki/%E5%AE%89%E8%A3%85%E5%B9%B6%E8%BF%90%E8%A1%8CJavSP)

## 使用

软件开箱即用。如果想让软件更符合你的使用需求，也许你需要更改配置文件:

> 以任意文本编辑器打开 ```config.yml```，根据各个配置项的说明选择你需要的配置即可。

此外软件也支持从命令行指定运行参数（命令行参数的优先级高于配置文件）。运行 ```JavSP -h``` 查看支持的参数列表

更详细的使用说明请前往 [JavSP Wiki](https://github.com/Yuukiy/JavSP/wiki) 查看

如果使用的时候遇到问题也欢迎给我反馈😊

## 问题反馈

如果使用中遇到了 Bug，请[前往 Issue 区反馈](https://github.com/Yuukiy/JavSP/issues)（提问前请先搜索是否已有类似问题）


## 参与贡献

此项目不需要捐赠。如果你想要帮助改进这个项目，欢迎通过以下方式参与进来（并不仅局限于代码）：

- 帮助撰写和改进Wiki

- 帮助完善单元测试数据（不必非要写代码，例如如果你发现有某系列的番号识别不准确，总结一下提issue也是很好的）

- 帮助翻译 genre

- Bugfix / 新功能？欢迎发 Pull Request

- 要不考虑点个 Star ?（我会很开心的）


## 许可

此项目的所有权利与许可受 GPL-3.0 License 与 [Anti 996 License](https://github.com/996icu/996.ICU/blob/master/LICENSE_CN) 共同限制。此外，如果你使用此项目，表明你还额外接受以下条款：

- 本软件仅供学习 Python 和技术交流使用

- 请勿在微博、微信等墙内的公共社交平台上宣传此项目

- 用户在使用本软件时，请遵守当地法律法规

- 禁止将本软件用于商业用途


---

![Star History Chart](https://api.star-history.com/svg?repos=Yuukiy/JavSP&type=Date)
