from pyppeteer import launcher

# hook  禁用 防止监测webdriver
from pyppeteer.network_manager import Request

launcher.AUTOMATION_ARGS.remove("--enable-automation")
from pyppeteer import launch
from pymongo import MongoClient
import pymongo
import random
import asyncio
from bs4 import BeautifulSoup as bs
import re, time
from tqdm import tqdm
from retrying import retry
import requests, json
import aiohttp
from requests.auth import HTTPBasicAuth
import requests
from motor.motor_asyncio import AsyncIOMotorClient


import tkinter


def screen_size():
    tk = tkinter.Tk()
    width = tk.winfo_screenwidth()
    height = tk.winfo_screenheight()
    tk.quit()
    return {"width": width, "height": height}


OPTIONS = {
    'browser_options': {
        'headless': False,
        "executablePath": 'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
        # 'userDataDir':'./user_data',
        'args': [
            # '--proxy-server=http://127.0.0.1:8080',
            # '--no-sandbox',
            # '–-disable-infobars'
        ]
    },
    'page_options': {
        'defaultViewport': screen_size(),
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36',
        'jss': [
            '''() =>{ Object.defineProperties(navigator,{ webdriver:{ get: () => false } }) }''',
            '''() =>{ window.navigator.chrome = { runtime: {},  }; }''',
            '''() =>{ Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] }); }''',
            '''() =>{ Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5,6], }); }'''
        ]
    },
    'db_options': {
        'host': '127.0.0.1',
        'port': 27017,
        'db': 'taobao',
        'collection': 'item'
    },
    'comment_options': {
        'login_url': 'https://login.taobao.com/member/login.jhtml?redirectURL=https%3A%2F%2Fwww.taobao.com%2F',
        'search_url': 'https://s.taobao.com/search?q=',
        'cookies': None,
        'base_crawl_url': 'https://s.taobao.com/search?initiative_id=tbindexz_20170306&ie=utf8&spm=a21bo.2017.201856-taobao-item.2&sourceId=tb.index&search_type=item&ssid=s5-e&commend=all&imgfile=&q=%E7%9C%BC%E9%9C%9C&suggest=history_1&_input_charset=utf-8&wq=&suggest_query=&source=suggest&fs=1&filter_tianmao=tmall&s='
    }
}

class Browser:

    def __init__(self, options):
        self.sem = asyncio.Semaphore(2)
        self.crawlUrls = []
        self.cookies = None
        self.proxies = []

    @classmethod
    async def create(cls, options):
        cls = Browser(options)
        for arg_k, arg_v in options.get('comment_options').items():
            cls.__setattr__(arg_k, arg_v)
        cls.__setattr__('page_options', options.get('page_options'))
        cls.browser = await launch(options.get('browser_options'))
        cls.client = AsyncIOMotorClient(options.get('db_options').get('ip'), options.get('db_options').get('port'))
        cls.db = cls.client[options.get('db_options').get('db')]

        return cls

    async def newPage(self):
        page = await self.browser.newPage()
        await page.setViewport(self.page_options.get('defaultViewport'))
        for js in self.page_options.get('jss'):
            await page.evaluateOnNewDocument(js)
        await page.setUserAgent(self.page_options.get('user_agent'))
        if self.cookies:
            for cookie in self.cookies:
                await page.setCookie(cookie)
        return page

    async def login(self, page, username, password):
        # page = await self.newPage()
        await page.goto(self.login_url)
        await page.waitForSelector("#J_QRCodeLogin > div.login-links > a.forget-pwd.J_Quick2Static")
        await page.click("#J_QRCodeLogin > div.login-links > a.forget-pwd.J_Quick2Static")
        await page.waitForSelector("#TPL_username_1")
        await page.type("#TPL_username_1", username, {'delay': random.randint(100, 115) * 0.5})
        await page.type("#TPL_password_1", password, {'delay': random.randint(100, 115) * 0.7})
        await page.waitFor(5)
        await page.click("#J_SubmitStatic")
        await page.waitForNavigation()
        cookies = await page.cookies()
        self.cookies = cookies
        # self.save_cookies(username, cookies)
        # await page.close()
        print("登录成功")
        self.aiohttp_cookies = {
            c['name']: c['value'] for c in cookies
        }
        # self.aiohttp_session = aiohttp.ClientSession(loop=asyncio.get_event_loop(),cookies=self.aiohttp_cookies)
        return page

    def save_cookies(self, username, cookies):
        d = {'useranme': username}
        __time = int(time.time())
        self.create_time = __time
        d.setdefault('ceate_time', __time)
        d.setdefault('cookies', cookies)
        self.db['cookies'].insert_one(d)
        print("cookies保存成功")

    async def search_and_getCrawlUrls(self, page, keyword, filter):
        # page = await self.newPage()
        print(f"search {keyword}....")
        await page.goto(self.search_url)
        # await page.waitFor(3)
        await page.type("#q", keyword)
        await page.click("#J_SearchForm > button")
        await page.waitFor(5)
        print("筛选天猫产品....")
        if filter == 'tmall':
            await page.goto(page.url + "&filter_tianmao=tmall")
            await page.waitFor(3)
        base_url = page.url
        total_pages = self._total_pages(await page.content())
        # await page.close()
        self.crawlUrls = [base_url + f"&s={44 * i}" for i in range(total_pages + 1)]
        return page

    def _total_pages(self, html):
        soup = bs(html, 'lxml')
        total_pages = soup.find("div", attrs={'class': 'total'}).text
        total_pages = re.findall(r"\d+\.?\d*", total_pages)[0]
        return int(total_pages)

    async def nextPage(self, page):
        await page.waitFor(5)
        await page.click("#mainsrp-pager > div > div > div > div.form > span.btn.J_Submit")
        await page.waitFor(5)
        return page

    async def parser(self, page):
        url = page.url
        print("parsing page....\nurl:", url)
        html = await page.content()
        try:
            data = {}
            if html.startwidth('{"totalResults'):
                item = json.loads(html)
                data['url'] = url
                data.setdefault('content', json.loads(item))
            else:
                item = re.search(r"g_page_config = ({.*?});", html).group(1)
                data = {'url': url}
                data.setdefault('content', json.loads(item))
            print(data)
            return data
        except:
            return dict(url=url, content="")

    async def saveHtml(self,url, html):
        data = dict(url=url,html=html)
        await self.db['yanshuang'].insert_one(data)

    async def close(self):
        await self.browser.close()
        self.client.close()


    async def safe_request(self, url, delay):
        async with self.sem:
            await asyncio.sleep(delay)
            return await self.__request(url)

    async def __request(self, url):
        page = await self.newPage()
        await page.goto(url)
        await page.waitFor(10)
        await self.saveHtml(page.url, await page.content())

    def get_proxy(self):
        if not self.proxies:
            self.getProxies()
        return self.proxies.pop()

    async def crawler(self, keyword, filter, username, password):
        page = await self.newPage()
        # await page.setRequestInterception(True)
        page = await self.login(page, username, password)
        page = await self.search_and_getCrawlUrls(page, keyword, filter)
        task = [self.safe_request(url, 10) for url in self.crawlUrls]
        await asyncio.gather(*task)




async def main():
    tbbrowser = await Browser.create(OPTIONS)
    await tbbrowser.crawler("眼霜", 'tmall','黄黄黄祥熙', 'future11')
    tbbrowser.close()




asyncio.run(main())