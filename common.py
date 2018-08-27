import os
import time
import json
import re
import requests
import urllib3
from logger import logger


basepath = os.path.abspath(os.path.dirname(__file__))  # 当前模块文件的根目录


def get_response(url, info='image url', *args, **kwargs):
    '''捕获request.get()方法的异常，比如连接超时、被拒绝等
    如果请求成功，则返回响应体；如果请求失败，则返回None，所以在调用get_response()函数时需要先判断返回值
    '''
    s = requests.session()
    s.keep_alive = False
    urllib3.disable_warnings()  # 使用requests库请求HTTPS时,因为忽略证书验证,导致每次运行时都会报异常（InsecureRequestWarning），这行代码可禁止显示警告信息

    try:
        resp = requests.get(url, *args, **kwargs)
        resp.raise_for_status()
    except requests.exceptions.HTTPError as errh:
        # In the event of the rare invalid HTTP response, Requests will raise an HTTPError exception (e.g. 401 Unauthorized)
        logger.exception('Unsuccessfully get {} [{}], HTTP Error: {}'.format(info, url, errh))
        pass
    except requests.exceptions.ConnectionError as errc:
        # In the event of a network problem (e.g. DNS failure, refused connection, etc)
        logger.exception('Unsuccessfully get {} [{}], Connecting Error: {}'.format(info, url, errc))
        pass
    except requests.exceptions.Timeout as errt:
        # If a request times out, a Timeout exception is raised. Maybe set up for a retry, or continue in a retry loop
        logger.exception('Unsuccessfully get {} [{}], Timeout Error: {}'.format(info, url, errt))
        pass
    except requests.exceptions.TooManyRedirects as errr:
        # If a request exceeds the configured number of maximum redirections, a TooManyRedirects exception is raised. Tell the user their URL was bad and try a different one
        logger.exception('Unsuccessfully get {} [{}], Redirect Error: {}'.format(info, url, errr))
        pass
    except requests.exceptions.RequestException as err:
        # catastrophic error. bail.
        logger.exception('Unsuccessfully get {} [{}], Else Error: {}'.format(info, url, err))
        pass
    except Exception as err:
        logger.exception('Unsuccessfully get {} [{}], Exception: {}'.format(info, url, err.__class__))
        pass
    else:
        return resp


def setup_down_path():
    '''设置图片下载后的保存位置，所有图片放在同一个目录下'''
    down_path = os.path.join(basepath, 'downloads')
    if not os.path.isdir(down_path):
        os.mkdir(down_path)
        logger.critical('Create download path {}'.format(down_path))
    return down_path


def get_links():
    '''获取所有图片的下载链接'''
    # 捕获request.get方法的异常，比如连接超时、被拒绝等
    resp = get_response('http://gank.io/api/data/%E7%A6%8F%E5%88%A9/1000/1', info='API')
    if not resp:  # 请求失败时，resp为None，不能往下执行
        return
    dict_obj = json.loads(resp.content)
    links = [item['url'] for item in dict_obj['results']]

    return links


def download_one(image):  # 为什么设计成接收一个字典参数，而不是三个位置参数? 方便后续多线程时concurrent.futures.ThreadPoolExecutor.map()
    '''下载一张图片
    :param image: 字典，包括图片的保存目录、图片的序号、图片的URL
    '''
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

    # 部分图片是https，需要将verify设置为False，忽略对 SSL 证书的验证
    resp = get_response(image['link'], info='image url', verify=False)  # 捕获request.get方法的异常，比如连接超时、被拒绝等
    if not resp:  # 请求失败时，resp为None，不能往下执行
        return {
            'failed': True  # 用于告知download_one()的调用方，请求此图片URL时失败了
        }

    with open(os.path.join(image['path'], filename), 'wb') as f:
        f.write(resp.content)  # resp.content是bytes类型，而resp.text是str类型

    t1 = time.time()
    logger.debug('Task No.{} [{}] runs {:.2f} seconds.'.format(image['linkno'], image['link'], t1 - t0))

    return {
        'failed': False  # 用于告知download_one()的调用方，此图片被成功下载
    }
