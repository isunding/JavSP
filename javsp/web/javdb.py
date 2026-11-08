"""从 JavDB 抓取数据（App API 版）。

这一版用 SakuraMedia (tinypinglite/sakuramediabe) 的 JavDB 刮削实现替换了
JavSP 原来的网页抓取：不再依赖 cloudscraper 过 CloudFlare、不再读取浏览器
Cookies、不再用 xpath 解析随时会变的 HTML，改为调用 JavDB 官方 App 的 JSON
接口（详见 ``javsp.web.javdb_api``）。原有的网页版抓取器完整保留在
``javsp.web.javdb_html``，可通过环境变量 ``JAVSP_JAVDB_LEGACY_FALLBACK=1``
在 API 失败时回退。

对外接口与 JavSP 其它抓取器保持一致：``parse_data`` / ``parse_clean_data`` /
``collect_actress_alias``，因此 ``javsp.__main__.parallel_crawler`` 无需改动。

可用环境变量（均可选，代理默认沿用 config.yml 的 network.proxy_server）：
    JAVSP_JAVDB_PROXY            覆盖代理，例如 http://127.0.0.1:10808
    JAVSP_JAVDB_API_HOST         API 域名，默认 jdforrepam.com
    JAVSP_JAVDB_API_TIMEOUT      超时秒数，默认 10
    JAVSP_JAVDB_API_RETRIES      重试次数，默认 3
    JAVSP_JAVDB_LEGACY_FALLBACK  =1 时 API 失败回退到旧网页抓取器
"""

from __future__ import annotations

import logging
import os

from javsp.web.exceptions import *
from javsp.datatype import MovieInfo, GenreMap
from javsp.web.javdb_api import (
    JavdbApiClient, JavdbApiError, JavdbApiRequestError, JavdbMovieNotFound,
    to_javsp_fields,
)

__all__ = ['parse_data', 'parse_clean_data', 'collect_actress_alias']

logger = logging.getLogger(__name__)

permanent_url = 'https://javdb.com'
genre_map = GenreMap('data/genre_javdb.csv')


def _proxy_dict() -> dict[str, str]:
    """优先使用显式环境变量，否则复用 JavSP 全局配置里的代理。"""
    override = os.environ.get('JAVSP_JAVDB_PROXY')
    if override:
        return {'http': override, 'https': override}
    try:
        from javsp.web.base import read_proxy
        return read_proxy()
    except Exception as exc:      # 配置未加载（例如单独跑本模块）时退化为直连
        logger.debug('JavDB: 无法读取全局代理配置，改为直连: %r', exc)
        return {}


def _client() -> JavdbApiClient:
    return JavdbApiClient(proxies=_proxy_dict())


def _legacy_enabled() -> bool:
    return os.environ.get('JAVSP_JAVDB_LEGACY_FALLBACK', '').strip() in ('1', 'true', 'yes')


def _legacy_parse_data(movie: MovieInfo) -> None:
    """回退到移植前的网页版抓取器（保留原有能力，仅按需加载）。"""
    from javsp.web.javdb_html import parse_data as legacy_parse_data
    logger.warning('JavDB: App API 抓取失败，回退到旧版网页抓取器')
    legacy_parse_data(movie)


def parse_data(movie: MovieInfo):
    """抓取并解析指定番号的数据，结果直接写回 ``movie``。

    Args:
        movie (MovieInfo): 要解析的影片信息
    """
    avid = movie.dvdid or movie.cid
    if not avid:
        raise MovieNotFoundError(__name__, 'empty avid')

    try:
        detail = _client().get_movie_by_number(avid)
    except JavdbMovieNotFound:
        raise MovieNotFoundError(__name__, avid)
    except JavdbApiRequestError as exc:
        if _legacy_enabled():
            _legacy_parse_data(movie)
            return
        raise WebsiteError(f'JavDB App API 请求失败: {exc}') from exc
    except JavdbApiError as exc:
        logger.debug('JavDB App API 返回异常: %r', exc)
        raise OtherError(f'JavDB App API: {exc}') from exc

    fields = to_javsp_fields(detail)
    for key, value in fields.items():
        if value is not None:
            setattr(movie, key, value)
    logger.debug("JavDB App API 抓取完成: '%s' -> '%s'", avid, movie.url)


def parse_clean_data(movie: MovieInfo):
    """解析影片数据并做清洗（供单测/手动调用，主流程直接调用 parse_data）。"""
    parse_data(movie)
    # App 的 tag id 与网页版 CSV 的 key 不同源；仅当确实拿到 genre_id 时才转换
    if movie.genre_id:
        movie.genre_norm = genre_map.map(movie.genre_id)
        movie.genre_id = None


def collect_actress_alias(type=0, use_original=True):
    """收集女优别名（开发用工具函数）。

    该能力依赖网页版按演员列表翻页，App API 没有对应的全量列表接口，
    因此继续委托给保留下来的旧版抓取器。
    """
    from javsp.web.javdb_html import collect_actress_alias as legacy_collect
    return legacy_collect(type=type, use_original=use_original)


if __name__ == '__main__':
    import pretty_errors
    pretty_errors.configure(display_link=True)
    logging.basicConfig(level=logging.DEBUG)

    m = MovieInfo('SSIS-001')
    try:
        parse_clean_data(m)
        print(m)
    except CrawlerError as e:
        print(repr(e))
