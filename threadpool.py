from concurrent import futures
import progressbar
import time
from common import setup_down_path, get_links, download_one
from logger import logger


def download_many():
    '''多线程，按线程数 并发（非并行） 下载所有图片'''
    down_path = setup_down_path()
    links = get_links()

    find_images = len(links)  # 发现的总图片链接数
    ignored_images = 0  # 被忽略的图片数
    visited_images = 0  # 请求成功的图片数
    failed_images = 0  # 请求失败的图片数

    images = []
    for linkno, link in enumerate(links, 1):
        image = {
            'path': down_path,
            'linkno': linkno,
            'link': link
        }
        images.append(image)

    workers = min(64, len(links))
    with futures.ThreadPoolExecutor(workers) as executor:
        to_do = [executor.submit(download_one, image) for image in images]
        # 获取Future的结果，futures.as_completed(to_do)的参数是Future列表，返回迭代器。只有当有Future运行结束后，才产出future
        done_iter = futures.as_completed(to_do)
        with progressbar.ProgressBar(max_value=len(to_do)) as bar:
            for i, future in enumerate(done_iter):  # future变量表示已完成的Future对象，所以后续future.result()绝不会阻塞
                result = future.result()
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
    download_many()
    logger.critical('Total Cost {:.2f} seconds'.format(time.time() - t0))
