"""从JavBus抓取数据"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import get_html
from core.func import *
from core.config import cfg
from core.datatype import MovieInfo, GenreMap


genre_map = GenreMap('data/genre_javbus.csv')
permanent_url = 'https://www.javbus.com'
if cfg.Network.proxy:
    base_url = permanent_url
else:
    base_url = cfg.ProxyFree.javbus


def parse_data(movie: MovieInfo):
    """解析指定番号的影片数据"""
    html = get_html(f'{base_url}/{movie.dvdid}')
    container = html.xpath("/html/body/div[@class='container']")[0]
    title = container.xpath("h3/text()")[0]
    cover = container.xpath("//a[@class='bigImage']/img/@src")[0]
    preview_pics = container.xpath("//div[@id='sample-waterfall']/a/@href")
    info = container.xpath("//div[@class='col-md-3 info']")[0]
    dvdid = info.xpath("p/span[text()='識別碼:']")[0].getnext().text
    publish_date = info.xpath("p/span[text()='發行日期:']")[0].tail.strip()
    duration = info.xpath("p/span[text()='長度:']")[0].tail.replace('分鐘', '').strip()
    director_tag = info.xpath("p/span[text()='導演:']")
    if director_tag:    # xpath没有匹配时将得到空列表
        movie.director = director_tag[0].getnext().text.strip()
    producer = info.xpath("p/span[text()='製作商:']")[0].getnext().text.strip()
    publisher = info.xpath("p/span[text()='發行商:']")[0].getnext().text.strip()
    serial_tag = info.xpath("p/span[text()='系列:']")
    if serial_tag:
        movie.serial = serial_tag[0].getnext().text
    # genre, genre_id
    genre_tags = info.xpath("//span[@class='genre']/label/a")
    genre, genre_id = [], []
    for tag in genre_tags:
        tag_url = tag.get('href')
        pre_id = tag_url.split('/')[-1]
        genre.append(tag.text)
        if 'uncensored' in tag_url:
            movie.uncensored = True
            genre_id.append('uncensored-' + pre_id)
        else:
            movie.uncensored = False
            genre_id.append(pre_id)
    # JavBus的磁力链接是依赖js脚本加载的，无法通过静态网页来解析
    # actress, actress_pics
    actress, actress_pics = [], {}
    actress_tags = html.xpath("//a[@class='avatar-box']/div/img")
    for tag in actress_tags:
        name = tag.get('title')
        pic_url = tag.get('src')
        actress.append(name)
        if not pic_url.endswith('nowprinting.gif'):     # 略过默认的头像
            actress_pics[name] = pic_url
    # 整理数据并更新movie的相应属性
    movie.title = title.replace(dvdid, '').strip()
    movie.cover = cover
    movie.preview_pics = preview_pics
    movie.publish_date = publish_date
    movie.duration = duration
    movie.producer = producer
    movie.publisher = publisher
    movie.genre = genre
    movie.genre_id = genre_id
    movie.actress = actress
    movie.actress_pics = actress_pics


def parse_clean_data(movie: MovieInfo):
    """解析指定番号的影片数据并进行清洗"""
    parse_data(movie)
    movie.genre_norm = genre_map.map(movie.genre_id)
    movie.genre_id = None   # 没有别的地方需要再用到，清空genre id（暗示已经完成转换）
    # 将此功能放在各个抓取器以保持数据的一致，避免影响转换（写入nfo时的信息来自多个抓取器的汇总，数据来源一致性不好）
    if cfg.Crawler.title__remove_actor:
        new_title = remove_trail_actor_in_title(movie.title, movie.actress)
        if new_title != movie.title:
            movie.ori_title = movie.title
            movie.title = new_title


if __name__ == "__main__":
    movie = MovieInfo('IPX-177')
    parse_clean_data(movie)
    print(movie)
