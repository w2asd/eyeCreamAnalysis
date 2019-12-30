import requests
from requests.auth import HTTPBasicAuth
import json,pymongo,redis
from tqdm import tqdm
import re

class Spider:

	def __init__(self):
		self.client = pymongo.MongoClient('localhost', 27017)
		self.db = self.client['taobao']
		self.rs = redis.Redis(host='localhost', port=6379, password='root', decode_responses=True)
		self.proxies = []


	def getCookies(self):
		cookies = self.db['cookies'].find().sort("create_time", -1).limit(1)
		cookies = list(cookies)[0]['cookies']
		r = {}
		for cookie in cookies:
			r[cookie['name']] = cookie['value']
		return r

	def getCrawlUrls(self):
		base_url = "https://s.taobao.com/search?q=%E7%9C%BC%E9%9C%9C&imgfile=&js=1&stats_click=search_radio_all%3A1&initiative_id=staobaoz_20191229&ie=utf8&fs=1&filter_tianmao=tmall"
		urls = [base_url + f"&s={44 * i}" for i in range(100 + 1)]
		return urls

	def getProxy(self):
		# proxy = self.rs.get('zdy')
		proxy = self.proxies.pop()
		user = '201912282329478339'
		pwd = 'b6bf5c41da60a922'
		proxies = {"http":f"http://{user}:{pwd}@{proxy}"}
		return proxies

	def _add_proxy(self):
		zdy_api = "http://www.zdopen.com/ShortProxy/GetIP/?api=201912282329478339&akey=b6bf5c41da60a922&order=1&type=3"
		r = requests.get(zdy_api, auth=HTTPBasicAuth('201912282329478339', '29571816'))
		r = json.loads(r.text)
		proxies = [str(x['ip'])+":"+str(x['port']) for x in r['data']['proxy_list']]
		self.proxies = proxies

	def crawl(self):
		headers = {
			'referer': 'https://www.taobao.com',
			'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36'
		}
		for url in tqdm(self.getCrawlUrls()):
			sign = None
			print(url)
			while (sign != 200):
				if not self.proxies:
					self._add_proxy()
				r = requests.get(url, proxies=self.getProxy(), headers=headers, )
				sign = r.status_code
			item = re.search(r'g_page_config = ({.*?});', r.text)	
			print(r.text)
			item = {'item', json.loads(item.group(1))}
			item['url'] = url
			item['crawl_time'] = time.time()
			self.db['item'].insert_one(item)
			print("爬取成功, url:",url)


spider = Spider()
spider.crawl()