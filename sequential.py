import time
import progressbar
from common import setup_down_path, get_links, download_one
from logger import logger


def download_many():
    '''依序下载所有图片，同步阻塞'''
    down_path = setup_down_path()
    links = get_links()

    find_images = len(links)  # 发现的总图片链接数
    ignored_images = 0  # 被忽略的图片数
    visited_images = 0  # 请求成功的图片数
    failed_images = 0  # 请求失败的图片数

    with progressbar.ProgressBar(max_value=len(links)) as bar:
        for linkno, link in enumerate(links, 1):  # 链接带序号
            image = {
                'path': down_path,
                'linkno': linkno,  # 图片序号，方便日志输出时，正在下载哪一张
                'link': link
            }
            result = download_one(image)
            if result.get('ignored'):
                ignored_images += 1
            else:
                if result.get('failed'):
                    failed_images += 1
                else:
                    visited_images += 1
            bar.update(linkno)

    logger.critical('Find [{}] images, ignored [{}] images, visited [{}] images, failed [{}] images'.format(find_images, ignored_images, visited_images, failed_images))


if __name__ == '__main__':
    t0 = time.time()
    download_many()
    logger.critical('Total Cost {:.2f} seconds'.format(time.time() - t0))
