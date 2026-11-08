# Changelog

## v1.9.0 - 2026-11-08

### Added
- JavDB 抓取器改用官方 App JSON 接口（`/api/v2/search` + `/api/v4/movies/{id}`），移植自 [SakuraMedia](https://github.com/tinypinglite/sakuramediabe)，不再依赖浏览器 Cookies 与 CloudFlare 绕过 [9eb2d59](https://github.com/isunding/JavSP/commit/9eb2d59)
- 新增 `JAVSP_JAVDB_*` 环境变量，可覆盖 API 域名、超时、重试次数与代理；`JAVSP_JAVDB_LEGACY_FALLBACK=1` 可回退旧网页抓取器
- 新增 `tools/build_onefile.py`：用 PyInstaller 打包单文件 exe，只读资源内置、`config.yml` 外置 [c9eb311](https://github.com/isunding/JavSP/commit/c9eb311)
- 添加无码和字幕的水印 [#73](https://github.com/Yuukiy/JavSP/commit/eaedc84049597eaab1ba064229f9b5bcf38aa504)
- 支持刮削剧照 [#176](https://github.com/Yuukiy/JavSP/issues/176)
- direnv 适配 [134b279](https://github.com/Yuukiy/JavSP/commit/134b279151aead587db0b12d1a30781f2e1be5b1)
- 添加硬链接支持 [#374](https://github.com/Yuukiy/JavSP/pull/374)
- 添加Docker镜像，每次tag发布将会同步更新一个Docker镜像到ghcr.io上。[#322](https://github.com/Yuukiy/JavSP/pull/322)

  参见[Package javsp](https://github.com/Yuukiy/JavSP/pkgs/container/javsp)。
- 添加新的爬虫`arzon`, `arzon_iv` [#377](https://github.com/Yuukiy/JavSP/pull/377)
- Slimeface人脸识别 [#380](https://github.com/Yuukiy/JavSP/pull/380)
- 支持Linux和MacOS(x64)二进制 [a754e1c](https://github.com/Yuukiy/JavSP/commit/a754e1ce0f14b0ca9dcc6d43d8e7d322a3da1c43)
- 添加选项`other.interactive`来表示程序是否应该在interactive模式下运行

### Changed
- JavDB 详情字段改由 App 接口直接映射（标题/原名/简介/评分/时长/导演/片商/系列/女优/标签/预览图），旧网页抓取器完整保留在 `javsp/web/javdb_html.py`
- 下载层自动还原 JavDB app CDN（`tp.spfcas.com`）图片的单字节 XOR 混淆；NFO 中的女优头像改写为未混淆的网页 CDN 地址 [9eb2d59](https://github.com/isunding/JavSP/commit/9eb2d59)
- `resource_path` 在打包后以 exe 所在目录为基准读取配置与资源，不再受启动时工作目录影响 [c6a21c5](https://github.com/isunding/JavSP/commit/c6a21c5)
- 更新检查在缺少包元数据时跳过，版本号改为构建时注入 [9045f01](https://github.com/isunding/JavSP/commit/9045f01)
- 使用 Poetry 作为构建系统 [134b279](https://github.com/Yuukiy/JavSP/commit/134b279151aead587db0b12d1a30781f2e1be5b1)
- 使用 Cx_Freeze 作为打包工具 [134b279](https://github.com/Yuukiy/JavSP/commit/134b279151aead587db0b12d1a30781f2e1be5b1)
- 将 Groq 翻译接口重构为 OpenAI 通用翻译接口 [#371](https://github.com/Yuukiy/JavSP/pull/371)
- FIX: 修复图标没有添加到封面上的 bug [#262](https://github.com/Yuukiy/JavSP/issues/176)
- 用更高清的Logo替换旧的Logo [7b8690f](https://github.com/Yuukiy/JavSP/commit/7b8690fb4af831c0e5ad5ed97cac61d51117c7eb)
- 重构配置文件，现在使用YAML保存配置文件 [e096d83](https://github.com/Yuukiy/JavSP/commit/e096d8394a4db29bb4a1123b3d05021de201207d)

  旧用户迁移可以使用[这个脚本](./tools/config_migration.py)
- 除了`-c,--config`以外的其他命令行参数，都被改为与配置文件的命名一致的传入方法。 [e096d83](https://github.com/Yuukiy/JavSP/commit/e096d8394a4db29bb4a1123b3d05021de201207d)

  比如需要重写扫描的目录可以这样传入参数：
  ```
  poetry run javsp -- --oscanner.input_directory '/some/directory'
  ```
- 删除了所有环境变量，现在环境变量的传入方法如下。 [e096d83](https://github.com/Yuukiy/JavSP/commit/e096d8394a4db29bb4a1123b3d05021de201207d)
  ```
  env JAVSP_SCANNER.INPUT_DIRECTORY='/some/directory' poetry run javsp
  ```
- 为了引入对类型注释的支持，最低Python版本现在为3.10

- 重构封面剪裁逻辑 [#380](https://github.com/Yuukiy/JavSP/pull/380)

### Fixed
- 修复打包为 exe 后裸 `exit()` 触发 `NameError` 的问题（改用 `sys.exit()`）[c6a21c5](https://github.com/isunding/JavSP/commit/c6a21c5)
- 缺少 `config.yml` 时给出明确提示，而不是抛出异常堆栈
- 修复未安装为发行包时 `importlib.metadata.version('javsp')` 抛 `PackageNotFoundError` 导致启动失败的问题 [9045f01](https://github.com/isunding/JavSP/commit/9045f01)

### Removed
- Pyinstaller 打包描述文件 [134b279](https://github.com/Yuukiy/JavSP/commit/134b279151aead587db0b12d1a30781f2e1be5b1)
- requirements.txt [134b279](https://github.com/Yuukiy/JavSP/commit/134b279151aead587db0b12d1a30781f2e1be5b1)
- MovieID.ignore_whole_word 功能和ignore_regex重复 [e096d83](https://github.com/Yuukiy/JavSP/commit/e096d8394a4db29bb4a1123b3d05021de201207d)
- NamingRule.media_servers：由于不常用删除，之后会出更general的解决方案 [#353](https://github.com/Yuukiy/JavSP/issues/353)
- Baidu AIP人脸识别，请使用Slimeface替代。

## v1.8 - 2024-09-28

### Added
- 新增站点njav, fc2ppvdb
- 添加选项控制封面选择逻辑，优先使用非javdb的封面以避免水印
- 支持自定义要写入到nfo的genre和tag中的字段
- 支持添加uncensored标签到poster图片
- 支持调用Claude(haiku)和Groq(llama3.1-70b)翻译接口

### Changed
- 适配网页和接口的变化: avsox, fc2, fanza, mgstage, prestige, javmenu
- 修复写入nfo时的拼写问题
- 修复Windows下无法读取Cookies的问题
- 修复封面图片url存在?参数时下载图片失败的问题
- 解决图片下载请求被javbus拦截的问题
- 优化google翻译参数和速率，减少被QoS
- 为Cloudflare拦截导致的失败请求给出提示
- 改进T38-000系列影片的番号识别
- msin: 站点关闭，移除相应代码及测试用例
