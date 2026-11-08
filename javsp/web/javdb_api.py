"""JavDB App API 客户端（纯标准库实现，可脱离 JavSP 单独测试）。

本模块移植自 SakuraMedia (tinypinglite/sakuramediabe) 的元数据刮削实现：

- ``src/metadata/_providers/javdb.py``  -> JavdbProvider 的 API 路径、签名、
  搜索匹配与详情字段映射
- ``src/metadata/_providers/http_client.py`` -> 重试 / 线性退避 / 请求头
- ``src/metadata/_providers/models.py`` -> 结果字段含义
- ``src/common/movie_numbers.py``       -> normalize_movie_number

与 JavSP 旧版 ``javdb_html.py`` 的区别：不再解析网页 HTML，也不再依赖浏览器
Cookies 与 cloudscraper 过 CloudFlare，而是走 JavDB 官方 App 的 JSON 接口。
因此这里刻意只使用标准库，不引入 httpx / loguru / pydantic 等 SakuraMedia
的依赖，便于在 JavSP 现有的 requests 技术栈中直接使用。

环境变量（全部可选）：
    JAVSP_JAVDB_API_HOST    API 域名，默认 jdforrepam.com
    JAVSP_JAVDB_API_TIMEOUT 单次请求超时秒数，默认 10
    JAVSP_JAVDB_API_RETRIES 网络错误重试次数，默认 3
    JAVSP_JAVDB_WEB_BASE    生成的影片网页 URL 前缀，默认 https://javdb.com
    JAVSP_JAVDB_PROXY       形如 http://127.0.0.1:10808 的代理覆盖值
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

__all__ = [
    'JavdbApiClient', 'JavdbApiError', 'JavdbApiRequestError', 'JavdbMovieNotFound',
    'normalize_movie_number', 'to_javsp_fields',
    'DEFAULT_HOST', 'WEB_BASE', 'APP_CDN_HOST', 'WEB_CDN_HOST',
]

logger = logging.getLogger(__name__)

DEFAULT_HOST = 'jdforrepam.com'
WEB_BASE = 'https://javdb.com'
APP_CDN_HOST = 'tp.spfcas.com'
WEB_CDN_HOST = 'c0.jdbstatic.com'

# jdsignature 的固定盐值，与官方 App 抓包一致，不要改动
_SIGN_SECRET = (
    '71cf27bb3c0bcdf207b64abecddc970098c7421ee7203b9cdae54478478a199e7d5a6e1a'
    '57691123c1a931c057842fb73ba3b3c83bcd69c17ccf174081e3d8aa'
)
_RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


class JavdbApiError(Exception):
    """JavDB App API 相关异常的基类。"""


class JavdbApiRequestError(JavdbApiError):
    """网络请求失败（重试耗尽或非重试型 HTTP 错误）。"""


class JavdbMovieNotFound(JavdbApiError):
    """搜索结果中没有与目标番号精确匹配的影片。"""


def normalize_movie_number(value: str) -> str:
    """番号匹配键（移植自 SakuraMedia 的 common.movie_numbers）。

    只用于比对搜索结果，不用于改写落库番号：纯数字番号保留分隔符，其他番号
    统一大写、去掉空格、把 ``_`` 视作 ``-``，并去掉 FC2-PPV- 中间的 PPV-。
    """
    normalized = (value or '').strip().upper().replace(' ', '')
    if re.fullmatch(r'\d+[-_]\d+', normalized):
        return normalized
    return normalized.replace('_', '-').replace('PPV-', '')


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def to_web_cdn_url(url: str | None) -> str | None:
    """把 app CDN 图片地址改写成网页 CDN 地址（去掉 tenant 路径段）。

    app CDN 的字节经过 XOR 混淆，只能由本地下载层还原；写进 NFO 供
    Emby/Jellyfin 自行拉取的地址必须是明文，因此头像类 URL 统一改写为
    网页 CDN。SakuraMedia 的 GFriends/网页 CDN 链路也是同样的取舍。
    """
    if not url:
        return None
    parts = urllib.parse.urlparse(url)
    if parts.hostname != APP_CDN_HOST:
        return url
    segments = [s for s in parts.path.split('/') if s]
    # 第一段是租户名（如 rhe951l4q），网页 CDN 不带这一段
    if len(segments) < 2:
        return url
    return f'https://{WEB_CDN_HOST}/' + '/'.join(segments[1:])


class JavdbApiClient:
    """JavDB App API 的最小实现，对齐 SakuraMedia 的 JavdbProvider。"""

    API_PATH_SEARCH = '/api/v2/search'
    API_PATH_MOVIE_DETAIL = '/api/v4/movies/{javdb_id}'
    API_PARAMS_MOVIE_SEARCH = {
        'from_recent': 'false',
        'type': 'movie',
        'movie_type': 'all',
        'movie_sort_by': 'relevance',
        'movie_filter_by': 'all',
        'page': 1,
        'limit': 24,
    }
    API_PARAMS_MOVIE_DETAIL = {'from_rankings': 'true'}

    def __init__(
        self,
        host: str | None = None,
        proxies: dict[str, str] | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ) -> None:
        self.host = host or os.environ.get('JAVSP_JAVDB_API_HOST', DEFAULT_HOST)
        self.timeout = _env_float('JAVSP_JAVDB_API_TIMEOUT', 10.0) if timeout is None else timeout
        self.max_retries = _env_int('JAVSP_JAVDB_API_RETRIES', 3) if max_retries is None else max_retries
        self.proxies = proxies or {}
        self._opener = urllib.request.build_opener(
            urllib.request.ProxyHandler(self.proxies) if self.proxies else urllib.request.ProxyHandler({})
        )

    def _get_sign(self) -> str:
        """构造 jdsignature：``timestamp.lpw6vgqzsp.md5(timestamp + salt)``。"""
        ts = int(time.time())
        sign = hashlib.md5(f'{ts}{_SIGN_SECRET}'.encode()).hexdigest()
        return f'{ts}.lpw6vgqzsp.{sign}'

    def build_request_headers(self) -> dict[str, str]:
        """对齐 SakuraMedia ``JavdbProvider.build_request_headers``。"""
        return {
            'connection': 'keep-alive',
            'accept-language': 'zh-TW',
            'host': self.host,
            'jdsignature': self._get_sign(),
            'user-agent': 'Dart/3.5 (dart:io)',
        }

    def _build_api_url(
        self,
        path: str,
        path_params: dict[str, Any] | None = None,
        query_params: dict[str, Any] | None = None,
    ) -> str:
        resolved = path.format(**(path_params or {}))
        url = f'https://{self.host}{resolved}'
        if query_params:
            url = f'{url}?{urllib.parse.urlencode(query_params, quote_via=urllib.parse.quote, safe=":-")}'
        return url

    def request_json(
        self,
        method: str,
        url: str,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """发起请求并解析 JSON；网络类错误按线性退避重试。

        对应 SakuraMedia ``MetadataRequestClient._request`` 的重试策略，
        仅把 httpx 换成标准库 urllib，以免给 JavSP 增加运行时依赖。
        """
        req_headers = self.build_request_headers()
        if headers:
            req_headers.update(headers)
        body = None
        if data is not None:
            body = urllib.parse.urlencode(data).encode('utf-8')
            req_headers.setdefault('Content-Type', 'application/x-www-form-urlencoded')

        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            req = urllib.request.Request(url, data=body, headers=req_headers, method=method.upper())
            try:
                with self._opener.open(req, timeout=self.timeout) as resp:
                    raw = resp.read()
                return json.loads(raw.decode('utf-8'))
            except urllib.error.HTTPError as exc:
                last_exc = exc
                logger.debug('JavDB API HTTP %s: %s (attempt %s)', exc.code, url, attempt + 1)
                if exc.code not in _RETRYABLE_STATUS:
                    raise JavdbApiRequestError(f'{method} {url}: HTTP {exc.code}') from exc
            except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
                last_exc = exc
                logger.debug('JavDB API transient error: %s (attempt %s)', exc, attempt + 1)
            if attempt >= self.max_retries:
                break
            # 与 SakuraMedia 的 backoff_delay(step=0.5, cap=2.0) 一致
            time.sleep(min(0.5 * (attempt + 1), 2.0))
        raise JavdbApiRequestError(f'{method} {url}: {last_exc!r}') from last_exc

    def search_movie(self, movie_number: str) -> dict[str, Any]:
        """按番号搜索，返回精确匹配的那条结果（可能带 ``id``）。

        对齐 SakuraMedia ``JavdbProvider._search_movie``：按发行日期倒序
        遍历候选，只有规范化番号完全相等才采纳，避免同名前缀误匹配。
        """
        normalized = normalize_movie_number(movie_number)
        url = self._build_api_url(
            self.API_PATH_SEARCH,
            query_params={'q': normalized, **self.API_PARAMS_MOVIE_SEARCH},
        )
        payload = self.request_json('GET', url)
        movies = payload.get('data', {}).get('movies', []) or []
        for movie in sorted(movies, key=lambda m: m.get('release_date') or '', reverse=True):
            if normalize_movie_number(movie.get('number', '')) == normalized:
                return movie
        raise JavdbMovieNotFound(f'movie not found: {movie_number}')

    def get_movie_detail(self, javdb_id: str) -> dict[str, Any]:
        """按 App 影片 id 取详情，返回 ``data.movie`` 字典。"""
        url = self._build_api_url(
            self.API_PATH_MOVIE_DETAIL,
            path_params={'javdb_id': javdb_id},
            query_params=self.API_PARAMS_MOVIE_DETAIL,
        )
        payload = self.request_json('GET', url)
        if payload.get('success') != 1:
            raise JavdbApiRequestError(
                f'{url}: unexpected success={payload.get("success")}, {payload.get("message")}'
            )
        movie = payload.get('data', {}).get('movie')
        if not movie:
            raise JavdbMovieNotFound(f'movie detail missing: {javdb_id}')
        return movie

    def get_movie_by_number(self, movie_number: str) -> dict[str, Any]:
        """搜索 + 取详情，一步拿到完整影片数据。"""
        found = self.search_movie(movie_number)
        javdb_id = found.get('id')
        if not javdb_id:
            raise JavdbMovieNotFound(f'movie id missing: {movie_number}')
        return self.get_movie_detail(javdb_id)


def _map_actor_gender(raw: Any) -> int:
    """性别映射（移植自 SakuraMedia）：未知 0、女 1、男 2。"""
    if raw is None:
        return 0
    if isinstance(raw, str):
        value = raw.strip().lower()
        if value in {'female', '女'}:
            return 1
        if value in {'male', '男'}:
            return 2
        if value not in {'0', '1'}:
            return 0
        raw = int(value)
    if raw == 0:
        return 1
    if raw == 1:
        return 2
    return 0


def _score_to_10(raw: Any) -> str | None:
    """App 返回 5 分制，JavSP 的 MovieInfo.score 统一用 10 分制字符串。"""
    try:
        return '{:.2f}'.format(float(raw) * 2)
    except (TypeError, ValueError):
        return None


def to_javsp_fields(movie: dict[str, Any]) -> dict[str, Any]:
    """把 JavDB App 详情映射为 JavSP ``MovieInfo`` 的属性字典（纯函数）。

    字段对齐 ``javsp/datatype.py::MovieInfo``；值为 ``None`` 的项由调用方
    跳过，避免覆盖其它抓取器已经填好的数据。
    """
    javdb_id = str(movie.get('id') or '')
    web_base = os.environ.get('JAVSP_JAVDB_WEB_BASE', WEB_BASE).rstrip('/')
    number = movie.get('number') or ''

    title = (movie.get('title') or '').strip()
    if number and title.startswith(number):
        title = title[len(number):].strip()
    ori_title = (movie.get('origin_title') or '').strip() or None
    if ori_title == title:
        ori_title = None

    tags = movie.get('tags') if isinstance(movie.get('tags'), list) else []
    genre = [str(t.get('name')) for t in tags if isinstance(t, dict) and t.get('name')] or None

    # 只保留女优；SakuraMedia 的 actors 同时含男女优，gender 0 为女
    actors = movie.get('actors') if isinstance(movie.get('actors'), list) else []
    actress = [a.get('name') for a in actors
               if isinstance(a, dict) and a.get('name') and _map_actor_gender(a.get('gender')) == 1] or None
    # 写进 NFO 的头像地址会被媒体服务器直接拉取，必须用未混淆的网页 CDN
    actress_pics = {
        a['name']: to_web_cdn_url(a.get('avatar_url'))
        for a in actors
        if isinstance(a, dict) and a.get('name') and _map_actor_gender(a.get('gender')) == 1
        and to_web_cdn_url(a.get('avatar_url'))
    } or None

    images = movie.get('preview_images') if isinstance(movie.get('preview_images'), list) else []
    preview_pics = [i['large_url'] for i in images
                    if isinstance(i, dict) and i.get('large_url')] or None

    # JavDB App 的 type: 0 有码 / 1 无码 / 3 欧美
    movie_type = movie.get('type')
    uncensored = True if movie_type == 1 else (False if movie_type in (0, 3) else None)

    duration = movie.get('duration')
    fields: dict[str, Any] = {
        'dvdid': number or None,
        'url': f'{web_base}/v/{javdb_id}' if javdb_id else None,
        'title': title or None,
        'ori_title': ori_title,
        'plot': (movie.get('summary') or '').strip() or None,
        'cover': movie.get('cover_url') or None,
        'genre': genre,
        # App 的 tag id 与 JavSP data/genre_javdb.csv 的网页 tag key 不同源，
        # 不做 genre_id -> genre_norm 的误映射，直接保留 API 的中文标签名
        'genre_id': None,
        'score': _score_to_10(movie.get('score')),
        'publish_date': movie.get('release_date') or None,
        'duration': str(duration) if duration else None,
        'director': movie.get('director_name') or None,
        'producer': movie.get('maker_name') or None,
        'publisher': movie.get('publisher_name') or None,
        'serial': movie.get('series_name') or None,
        'actress': actress,
        'actress_pics': actress_pics,
        'uncensored': uncensored,
        'preview_pics': preview_pics,
        # App 只提供 m3u8 预览，JavSP 的 NFO trailer 期望可直接播放的地址，
        # 因此不写 preview_video / magnet，交由其它抓取器补充
        'preview_video': None,
        'magnet': None,
    }
    return fields
