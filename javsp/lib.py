"""用来组织不需要依赖任何自定义类型的功能函数"""
import os
import re
import sys
from pathlib import Path


__all__ = ['re_escape', 'resource_path', 'strftime_to_minutes', 'detect_special_attr']


_special_chars_map = {i: '\\' + chr(i) for i in b'()[]{}?*+|^$\\.'}
def re_escape(s: str) -> str:
    """用来对字符串进行转义，以将转义后的字符串用于构造正则表达式"""
    pattern = s.translate(_special_chars_map)
    return pattern


def resource_path(path: str) -> str:
    """获取一个随代码打包的文件在解压后的路径。

    PyInstaller 单文件 exe 会把资源解压到 ``sys._MEIPASS``，而旧逻辑在冻结
    状态下只返回相对路径（即 exe 的工作目录），导致打包时附带的资源找不到。
    这里改为：优先使用 exe 所在工作目录下的同名文件（方便用户按盘覆盖
    config.yml），不存在时回退到打包进 exe 的默认资源；cx_Freeze 的打包方式
    没有 _MEIPASS，行为与原来保持一致。
    """
    if getattr(sys, "frozen", False):
        # 一律以 exe 所在目录为准，而不是启动时的工作目录：双击、快捷方式、
        # 或者从别的目录调用，读到的都是同一份 config.yml
        base_dir = Path(sys.executable).resolve().parent
        candidate = base_dir / path
        if candidate.exists():
            return str(candidate)
        bundle_root = getattr(sys, '_MEIPASS', None)
        if bundle_root:
            bundled = Path(bundle_root) / path
            if bundled.exists():
                return str(bundled)
        # 两边都没有时返回 exe 同目录路径，让报错信息指向用户应当放置文件的位置
        return str(candidate)
    else:
        path_joined = Path(__file__).parent.parent / path
        return str(path_joined)


def strftime_to_minutes(s: str) -> int:
    """将HH:MM:SS或MM:SS的时长转换为分钟数返回

    Args:
        s (str): HH:MM:SS or MM:SS

    Returns:
        [int]: 取整后的分钟数
    """
    items = list(map(int, s.split(':')))
    if len(items) == 2:
        minutes = items[0] + round(items[1]/60)
    elif len(items) == 3:
        minutes = items[0] * 60 + items[1] + round(items[2]/60)
    else:
        raise ValueError(f"无法将字符串'{s}'转换为分钟")
    return minutes


_PATTERN = re.compile(r'(uncen(sor(ed)?)?([- _\s]*leak(ed)?)?|[无無][码碼](流出|破解))', flags=re.I)
def detect_special_attr(filepath: str, avid: str = None) -> str:
    """通过文件名检测影片是否有特殊属性（内嵌字幕、无码流出/破解）

    Returns:
        [str]: '', 'U', 'C', 'UC'
    """
    result = ''
    base = os.path.splitext(os.path.basename(filepath))[0].upper()
    # 尝试使用正则匹配
    match = _PATTERN.search(base)
    if match:
        result += 'U'
    # 尝试匹配-C/-U/-UC后缀的影片
    postfix = base.split('-')[-1]
    if postfix in ('U', 'C', 'UC'):
        result += postfix
    elif avid:
        pattern_str = re.sub(r'[_-]', '[_-]*', avid) + r'(UC|U|C)\b'
        match = re.search(pattern_str, base, flags=re.I)
        if match:
            result += match.group(1)
    # 最终格式化
    result = ''.join(sorted(set(result), reverse=True))
    return result


if __name__ == "__main__":
    print(detect_special_attr('ipx-177cd1.mp4', 'IPX-177'))
