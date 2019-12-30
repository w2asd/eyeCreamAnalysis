import aiohttp
import asyncio
from pyppeteer.network_manager import Request
from pyppeteer import launch
import requests, json
from requests.auth import HTTPBasicAuth

aiohttp_session = aiohttp.ClientSession()


def getProxies():
    zdy_api = "http://www.zdopen.com/ShortProxy/GetIP/?api=201912282329478339&akey=b6bf5c41da60a922&order=1&type=3"
    r = requests.get(zdy_api, auth=HTTPBasicAuth('201912282329478339', '29571816'))
    r = json.loads(r.text)

    proxies = ["http://201912282329478339:29571816@" + str(x['ip']) + ":" + str(x['port']) for x in
               r['data']['proxy_list']]
    return proxies[0]


proxy = "http://127.0.0.1:8080"
async def use_proxy_base(request:Request):
    req = {
        "headers": request.headers,
        "data": request.postData,
        "proxy": getProxies(),  # 使用全局变量 则可随意切换
        "timeout": 5,
        "ssl": False,
    }
    try:
        # 使用第三方库获取响应
        async with aiohttp_session.request(
                method=request.method, url=request.url, **req
        ) as response:
            body = await response.read()
    except Exception as e:
        await request.abort()
        return

    # 数据返回给浏览器
    resp = {"body": body, "headers": response.headers, "status": response.status}
    await request.respond(resp)
    return



launch_args = {
    "headless": False,
    "args": [
        "--start-maximized",
        "--no-sandbox",
        "--disable-infobars",
        "--ignore-certificate-errors",
        "--log-level=3",
        "--enable-extensions",
        "--window-size=1920,1080",
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36",
    ],
}

async def interception_test():
    # 启动浏览器
    async def use_proxy_base(request: Request):
        req = {
            "headers": request.headers,
            "data": request.postData,
            "proxy": getProxies(),  # 使用全局变量 则可随意切换
            "timeout": 5,
            "ssl": False,
        }
        print(req['proxy'])
        try:
            # 使用第三方库获取响应
            async with aiohttp_session.request(
                    method=request.method, url=request.url, **req
            ) as response:
                body = await response.read()
        except Exception as e:
            await request.abort()
            return

        # 数据返回给浏览器
        resp = {"body": body, "headers": response.headers, "status": response.status}
        await request.respond(resp)
        return

    browser = await launch(**launch_args)
    aiohttp_session = aiohttp.ClientSession()
    # 新建标签页
    page = await browser.newPage()
    # 设置页面打开超时时间
    page.setDefaultNavigationTimeout(10 * 1000)
    # 设置窗口大小
    await page.setViewport({"width": 1920, "height": 1040})

    # 启用拦截器
    await page.setRequestInterception(True)

    # 设置拦截器
    # 1. 修改请求的url
    if 1:
        page.on("request", use_proxy_base)
        await page.goto("https://www.baidu.com")
        print(await page.content())

    await asyncio.sleep(1)

    # 关闭浏览器
    await page.close()
    await browser.close()
    return


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(interception_test())