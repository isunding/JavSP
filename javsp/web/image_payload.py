"""图片字节形态识别，以及 JavDB app CDN 的单字节 XOR 还原。

移植自 SakuraMedia (tinypinglite/sakuramediabe) 的
``src/common/image_payload.py``，供 JavSP 的下载层使用。

JavDB 有两条图片链路，同一张图的内容并不相同：

- app CDN（``tp.spfcas.com/<tenant>/...``）：干净原图，但字节被单字节 XOR
  混淆——首字节是本次响应随机生成的 key，其余字节逐字节异或它。直接按图片
  解码会失败。
- 网页 CDN（``c0.jdbstatic.com/...``）：普通 JPEG，但 ``covers/`` 带
  ``javdb.com`` 半透明水印。

SakuraMedia 的做法是统一走 app CDN，并在下载层还原；这里保持一致。判定只看
魔数、不解码，避免为"是不是图片"付出解码成本，也不会误伤未混淆的明文。
"""

from __future__ import annotations

from functools import lru_cache

__all__ = ['looks_like_image', 'deobfuscate_image_bytes', 'APP_CDN_HOST', 'WEB_CDN_HOST']

APP_CDN_HOST = 'tp.spfcas.com'
WEB_CDN_HOST = 'c0.jdbstatic.com'

_JPEG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_GIF_MAGICS = (b"GIF87a", b"GIF89a")
_RIFF_MAGIC = b"RIFF"
_WEBP_TAG = b"WEBP"
_ISO_BMFF_TAG = b"ftyp"
_ISO_BMFF_BRANDS = (b"avif", b"avis", b"heic", b"heix", b"heif", b"mif1", b"msf1")

# 短于此长度的载荷无法承载完整魔数，直接按非图片处理
_MIN_IMAGE_BYTES = 12


def looks_like_image(data: bytes) -> bool:
    """按魔数判断字节是否像一张图片；不解析像素、不抛异常。"""
    if len(data) < _MIN_IMAGE_BYTES:
        return False
    if data.startswith((_JPEG_MAGIC, _PNG_MAGIC)):
        return True
    if data.startswith(_GIF_MAGICS):
        return True
    if data.startswith(_RIFF_MAGIC) and data[8:12] == _WEBP_TAG:
        return True
    return data[4:8] == _ISO_BMFF_TAG and data[8:12] in _ISO_BMFF_BRANDS


@lru_cache(maxsize=256)
def _xor_table(key: int) -> bytes:
    """256 字节异或表；bytes.translate 由 C 实现，比逐字节推导快两个量级。"""
    return bytes(byte ^ key for byte in range(256))


def deobfuscate_image_bytes(data: bytes) -> bytes:
    """还原 app CDN 的单字节 XOR 混淆；本来就是明文时原样返回。

    判定顺序保证不会误伤明文：先看原字节是不是图片，不是才尝试
    ``data[1:] ^ data[0]``；还原结果仍不像图片时返回原字节，让下游的
    解码校验报出真实错误，而不是把损坏数据写进图片库。
    """
    if looks_like_image(data):
        return data
    if len(data) < _MIN_IMAGE_BYTES:
        return data
    candidate = data[1:].translate(_xor_table(data[0]))
    if looks_like_image(candidate):
        return candidate
    return data
