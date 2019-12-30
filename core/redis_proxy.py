from requests.auth import HTTPBasicAuth
import requests
import redis
import time
import json



class ProxyPool:

	def __init__(self):
		self.rs = redis.Redis(host='localhost', port=6379, password='root', decode_responses=True)


	def _add_proxy(self, delay=10):
		zdy_api = "http://www.zdopen.com/ShortProxy/GetIP/?api=201912282329478339&akey=b6bf5c41da60a922&order=1&type=3"
		r = requests.get(zdy_api, auth=HTTPBasicAuth('201912282329478339', '29571816'))
		r = json.loads(r.text)
		proxies = [str(x['ip'])+":"+str(x['port']) for x in r['data']['proxy_list']]
		for p in proxies:
			self.rs.set('zdy', p)
			print("add proxy: ",p)
		time.sleep(delay)

	def get_proxy(self):
		p = self.rs.get('zdy')
		return p

	def delete_proxy(self, p):
		self.rs.delete(p)

if __name__ == '__main__':
	pp = ProxyPool()
	pp._add_proxy()