"""构建可单独放到各磁盘根目录的 JavSP.exe（PyInstaller onefile）。

仓库自带的 ``setup.py`` 使用 cx_Freeze，产物是一个包含 exe + lib 的目录，
不适合"把一个 exe 丢进盘根目录"的部署方式。本脚本按磁盘上原有的单文件
形态打包：只把只读资源（data / image）打进 exe，**config.yml 不打进去**，
而是作为独立文件放在 exe 同目录，方便每个盘单独维护自己的配置。
``javsp.lib.resource_path`` 会优先使用工作目录下的文件，找不到才回退到
exe 内的默认资源。

用法（在仓库根目录，需已安装 pyinstaller 及项目依赖）::

    python tools/build_onefile.py

产物：``dist/onefile/JavSP.exe``
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    # import_crawlers() 通过 __import__('javsp.web.<name>') 动态加载抓取器，
    # PyInstaller 的静态分析看不到，必须显式声明，否则打包后所有站点都跳过。
    web_dir = ROOT / 'javsp' / 'web'
    hidden = [p.stem for p in sorted(web_dir.glob('*.py')) if p.stem != '__init__']

    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--noconfirm', '--clean', '--onefile',
        '--name', 'JavSP',
        '--distpath', str(ROOT / 'dist' / 'onefile'),
        '--workpath', str(ROOT / 'build' / 'onefile'),
        '--specpath', str(ROOT / 'build' / 'onefile'),
        '--icon', str(ROOT / 'image' / 'JavSP.ico'),
        # config.yml 刻意不打包：作为 exe 同目录的外部配置文件，按盘独立维护
        '--add-data', f'{ROOT / "data"};data',
        '--add-data', f'{ROOT / "image"};image',
        '--exclude-module', 'unittest',
    ]
    for name in hidden:
        cmd += ['--hidden-import', f'javsp.web.{name}']
    cmd.append(str(ROOT / 'javsp' / '__main__.py'))

    print('hidden web modules:', ', '.join(hidden))
    print('running:', ' '.join(cmd[:8]), '...')
    return subprocess.run(cmd, cwd=str(ROOT), check=False).returncode


if __name__ == '__main__':
    raise SystemExit(main())
