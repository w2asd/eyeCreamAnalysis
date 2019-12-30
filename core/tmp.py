import asyncio
import json
import pickle
import random
import re
import time

import aiohttp
from bs4 import BeautifulSoup as bs
from pyppeteer import launch
from retrying import retry
from setting import *
from motor.motor_asyncio import AsyncIOMotorClient
import pymongo





class TBBrowser:

    def __init__(self, kwargs):
        for k, v in kwargs.items():
            self.__setattr__(k, v)
        self.browser = None
        self.spider_urls = []
        self.tmp_url = None
        self.password = None
        self.username = None
        self.login_url = None
        self.tmp_count = 0

    async def __create_browser(self, kwargs):
        self.browser = await launch(kwargs)

    @classmethod
    async def create_render(cls, kwargs):
        cls = cls(kwargs)
        browser_args = kwargs.get('browser_args', None)
        await cls.__create_browser(browser_args)
        return cls

    async def __base_page(self, url, timeout=15, delay=0):
        page = await self.browser.newPage()
        if self.page_jss:
            for js in self.page_jss:
                await page.evaluateOnNewDocument(js)
        if delay>0:
            await page.waitFor(delay)
        defaultViewport = self.defaultViewport or None
        await page.setViewport(defaultViewport)

        user_agent = self.user_agent or None
        await page.setUserAgent(user_agent)
        if self.cookies:
            for cookie in self.cookies:
                await page.setCookie(cookie)
        await page.goto(url)

        return page

    async def page(self, url, timeout=15, delay=0):
        return await self.__base_page(url, timeout, delay)

    async def close(self):
        try:
            await self.browser.close()
        except:
            pass

    async def spider(self, db_ip, db_port, db_name, db_collection, tiemout=15, delay=10):
        mongo = pymongo.MongoClient(db_ip, db_port)
        collection = mongo[db_name][db_collection]
        page = await self.page('https://www.taobao.com/', tiemout, delay)
        for url in self.spider_urls:
            item = None
            while not item:
                await page.goto(url)
                await page.waitFor(delay)
                html = await page.content()
                item = self.parse(html)
            print(item)
            collection.insert_one(item)
        await page.close()


    async def set_cookies(self, login_url, username, password):
        self.login_url = login_url
        self.username = username
        self.password = password
        if login_url == None and self.login_url:
            login_url = self.login_url
            username = self.username
            password = self.password
        page = await self.page(login_url)
        await page.waitForSelector("#J_QRCodeLogin > div.login-links > a.forget-pwd.J_Quick2Static")
        await page.click("#J_QRCodeLogin > div.login-links > a.forget-pwd.J_Quick2Static")
        await page.waitForSelector("#TPL_username_1")
        await page.type("#TPL_username_1", username, {'delay': random.randint(100,115)*0.5})
        await page.type("#TPL_password_1", password, {'delay': random.randint(100,115)*0.7})

        await page.waitFor(5)
        try:
            slider = await page.Jeval('#nocaptcha', 'node => node.style')
        except:
            slider = None

        if slider:
            flag, page = await self.mouse_slide(page)
            if flag:
                await page.click("#J_SubmitStatic")
                time.sleep(2)
                cookies = await page.cookies()
                self.cookies = cookies
        else:
            await page.click("#J_SubmitStatic")
            await page.waitFor(20)
            await page.waitForNavigation()
            try:
                global error  # 检测是否是账号密码错误
                print("error_1:", error)
                error = await page.Jeval('.error', 'node => node.textContent')
                print("error_2:", error)
            except Exception as e:
                error = None
            finally:
                await page.waitFor(10)
                self.tmp_url = page.url

                if error:
                    print('确保账户安全重新入输入')
                    # 程序退出。

                else:
                    print(page.url)
                    cookies =  await page.cookies()
                    self.cookies = cookies


        q = await page.waitForSelector("#q")
        if q:
            print('登录成功')
            cookies = await page.cookies()
            self.cookies = cookies
        await page.close()

    @staticmethod
    def retry_if_result_none(result):
        return result is None

    @retry(retry_on_result=retry_if_result_none)
    async def mouse_slide(self, page=None):
        await asyncio.sleep(2)
        try:
            await page.hover("#nc_1_n1z")
            await page.mouse.down()
            await page.mouse.move(2000,0,{'delay': random.randin(1000,2000)})
            await page.mouse.up()
        except Exception as e:
            return None, page
        else:
            await asyncio.sleep(2)
            slide_again = await page.Jeval('.nc-lang-cnt', 'node => node.textContent')
            if slide_again != '验证通过':
                return None, page
            else:
                return 1, page

    async def clear_webdriver(self, page):
        if self.page_jss:
            for js in self.page_jss:
                await page.evaluate(js)
        return page

    async def find_pages(self, search_url, keyword, sign='tmall'):
        try:
            page = await self.page(search_url)
            await page.waitFor(5)
            # await page.waitForNavigation()
            await page.type("#q", keyword)
            await page.click("#J_SearchForm > button")
            await page.waitForNavigation()
            await page.querySelector("#mainsrp-pager > div > div > div > div.total")
            html = await page.content()
            total_pages = self.__total_pages(html)
            base_url = page.url
            await page.close()
            # return base_url, total_pages
            if sign == 'tmall':
                sign = "&filter_tianmao=tmall"
            else:
                sign = ""
            self.spider_urls  = [base_url + f"&s={44 * (i - 1)}" + sign for i in range(1, total_pages + 1)]
        except Exception as e:
            print(e)
            time.sleep(1e4)

    def __total_pages(self, html):
        soup = bs(html, 'lxml')
        total_pages = soup.find("div", attrs={'class':'total'}).text
        total_pages = re.findall(r"\d+\.?\d*", total_pages)[0]
        return int(total_pages)

    def save_cookies(self):
        if self.cookies:
            cookies = {}
            for cookie in self.cookies:
                cookies.setdefault(cookie.get('name'), cookie.get('value'))
        with open('cookies.pk', 'wb') as f:
            pickle.dump(cookies, f)
            print('保持cookies成功!')

    def save_spider_urls(self):
        if self.spider_urls:
            with open("spider_urls.csv", 'w') as f:
                for url in self.spider_urls:
                    f.write(url+'\n')
                print('更新urls')

    def parse(self, html):
        try:
            item = re.search(r'g_page_config = ({.*?});', html).group(1)
            item = json.loads(item)
            return item
        except:
            return None




async def main():
    browser = await Browser.create_render(browser_args)
    await browser.set_cookies(**spider_args.get('login_info'))
    await browser.find_pages(**spider_args.get('search_info'))
    browser.save_cookies()
    browser.save_spider_urls()
    await browser.spider('localhost', 27017, 'taobao', 'yanshuang')
    await browser.close()





if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    spider_urls = loop.run_until_complete(main())

