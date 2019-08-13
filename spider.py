from hashlib import md5
import pymongo
import requests, urllib, json,bs4,re,time,string,os
from urllib.parse import urlencode
from requests import codes
from config import *
from multiprocessing import Pool

client = pymongo.MongoClient(MONGO_URL)
db = client[MONGO_DB]


def get_page_index(offset, keyword):
    param = {
        'aid': 24,
        'app_name': 'web_search',
        'offset': offset,
        'format': 'json',
        'keyword': keyword,
        'autoload': True,
        'count': 20,
        'en_qc': 1,
        'cur_tab': 1,
        'from': 'search_tab',
        'pd': 'synthesis'
    }
    url = "https://www.toutiao.com/api/search/content/?" + urlencode(param)
    headers = {
        'cookie': '__guid=32687416.828459707378266200.1564625080901.2488; csrftoken=edf5730c815a95b294e9868378c72961; tt_webid=6720013649635706372; UM_distinctid=16c4aec138d1f9-0fec7bd45fdbaa-454c092b-1fa400-16c4aec138e63d; tt_webid=6720013649635706372; WEATHER_CITY=%E5%8C%97%E4%BA%AC; s_v_web_id=0b961c8fa0fab99a48f1b9bb31471568; CNZZDATA1259612802=800585623-1564622770-https%253A%252F%252Fwww.toutiao.com%252F%7C1564994427; __tasessionId=3scx3t58k1564998330217; monitor_count=19',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36',
        'referer': 'https://www.toutiao.com/search/?keyword=%E8%A1%97%E6%8B%8D',
        'x-requested-with': 'XMLHttpRequest'
    }
    try:
        resp = requests.get(url,headers = headers)
        if 200 == resp.status_code:
            return resp.json()
    except requests.ConnectionError:
            return None


def parse_page_index(json):
    if json.get('data'):
        data = json.get('data')
        try:
            for item in data:
                if item.get('title') is None or item.get('image_list') is None:
                    continue
                title = re.sub('|','',item['title'])
                image_list = item.get('image_list')
                for image in image_list:
                    url_patten = re.compile('.*?list/190x124.*?')
                    if re.search(url_patten,image.get('url')):
                        image['url'] = re.sub('list/190x124','large',image.get('url'))
                    else:
                        image['url'] = re.sub('list','large',image.get('url'))
                images = [image.get('url') for image in image_list]
                yield {
                    'title': title,
                    'images': images
                }
        except Exception:
            print(title + '有问题')
            print(item)
            print('**************分隔符*************')



def save_to_mongo(result):
    if db[MONGO_TABLE].insert(result):
        print('存储到MongoDB成功',result)
        return True
    return False


def save_image(result):
    img_path = 'Jie_Pai' + os.path.sep + result.get('title').replace('|','')
    if not os.path.exists(img_path):
        os.makedirs(img_path)
    try:
        for image in result.get('images'):
            resp = requests.get(image)
            if codes.ok == resp.status_code:
                file_path = img_path + os.path.sep + '{file_name}.{file_suffix}'.format(
                    # 图片内容的md5值，避免重复
                    file_name = md5(resp.content).hexdigest(),
                    file_suffix = 'jpg'
                    )
                if not os.path.exists(file_path):
                    with open(file_path,'wb') as f:
                        f.write(resp.content)
                        f.close()
                    print('下载图片路径 %s' % file_path)
                else:
                    print('已经下载过该图',file_path)
    except Exception as e:
        print(e)


def main(offset):
    index_json = get_page_index(offset, KEYWORD)
    results = parse_page_index(index_json)
    for result in results:
        if result:
            save_image(result)
            save_to_mongo(result)

if __name__ == '__main__':
    groups = [x*20 for x in range(GROUP_START,GROUP_END + 1)]
    pool = Pool()
    pool.map(main,groups)
