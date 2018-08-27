import os
import re
import sys
import time
import asyncio
import aiohttp
import aiofiles
import progressbar
from logger import logger


# 当前模块文件的根目录
basepath = os.path.abspath(os.path.dirname(__file__))


def setup_down_path():
    '''设置图片下载后的保存位置，所有图片放在同一个目录下'''
    down_path = os.path.join(basepath, 'downloads')
    if not os.path.isdir(down_path):
        os.mkdir(down_path)
        logger.critical('Create download path {}'.format(down_path))
    return down_path


async def get_links(session, url):
    '''获取所有图片的下载链接'''
    async with session.get(url) as response:
        dict_obj = await response.json()
        links = [item['url'] for item in dict_obj['results']]
        return links


async def download_one(semaphore, session, image):
    logger.debug('Downloading No.{} [{}]'.format(image['linkno'], image['link']))
    t0 = time.time()

    filename = os.path.split(image['link'])[1]
    # 有些图片链接中最后一部分名称中有 ? 问号，以这个作为文件名，本地创建文件时会报错
    # 比如http://7xi8d6.com1.z0.glb.clouddn.com/2017-04-27-17934080_117414798808566_8957027985114791936_n.jpg?imageslim
    filename = re.sub(r'\?.*', '', filename)  # 删除 ? 问号及它之后的所有字符
    # 如果链接对应的图片已存在，则忽略下载
    if os.path.exists(os.path.join(image['path'], filename)):  # 图片已存在
        logger.debug('The file of link No.{} [{}] exist, ignore this'.format(image['linkno'], image['link']))
        return {
            'ignored': True  # 用于告知download_one()的调用方，此图片被忽略下载
        }

    # 部分图片是https，需要忽略对 SSL 证书的验证
    try:
        async with semaphore:
            async with session.get(image['link'], ssl=False) as response:
                if response.status == 200:
                    image_content = await response.read()  # Binary Response Content: access the response body as bytes, for non-text requests
                else:
                    logger.error('received invalid response code: {}, message: {}'.format(response.status, response.reason))
                    raise aiohttp.ClientError()
    except Exception as e:
        logger.exception('Exception {} raised on No.{} [{}]'.format(e.__class__, image['linkno'], image['link']))
        return {
            'failed': True  # 用于告知download_one()的调用方，请求此图片URL时失败了
        }

    async with aiofiles.open(os.path.join(image['path'], filename), 'wb') as f:
        await f.write(image_content)

    t1 = time.time()
    logger.debug('Task No.{} [{}] runs {:.2f} seconds.'.format(image['linkno'], image['link'], t1 - t0))

    return {
        'failed': False  # 用于告知download_one()的调用方，此图片被成功下载
    }


async def download_many():
    down_path = setup_down_path()

    async with aiohttp.ClientSession() as session:  # aiohttp建议整个应用只创建一个session，不能为每个请求创建一个seesion
        links = await get_links(session, 'http://gank.io/api/data/%E7%A6%8F%E5%88%A9/1000/1')  # 获取所有图片的下载链接
        # 用于限制并发请求数量
        sem = asyncio.Semaphore(min(64, len(links)))
        find_images = len(links)  # 发现的总图片链接数
        ignored_images = 0  # 被忽略的图片数
        visited_images = 0  # 请求成功的图片数
        failed_images = 0  # 请求失败的图片数

        to_do = []
        for linkno, link in enumerate(links, 1):
            image = {
                'path': down_path,
                'linkno': linkno,  # 图片序号，方便日志输出时，正在下载哪一张
                'link': link
            }
            to_do.append(download_one(sem, session, image))

        to_do_iter = asyncio.as_completed(to_do)
        with progressbar.ProgressBar(max_value=len(to_do)) as bar:
            for i, future in enumerate(to_do_iter):
                result = await future
                if result.get('ignored'):
                    ignored_images += 1
                else:
                    if result.get('failed'):
                        failed_images += 1
                    else:
                        visited_images += 1
                bar.update(i)

    logger.critical('Find [{}] images, ignored [{}] images, visited [{}] images, failed [{}] images'.format(find_images, ignored_images, visited_images, failed_images))


if __name__ == '__main__':
    t0 = time.time()
    if sys.platform != 'win32':
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(download_many())
    loop.close()
    logger.critical('Total Cost {:.2f} seconds'.format(time.time() - t0))