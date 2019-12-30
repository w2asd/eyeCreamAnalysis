url = "https://s.taobao.com/search?q=%E7%9C%BC%E9%9C%9C&imgfile=&js=1&stats_click=search_radio_all%3A1&initiative_id=staobaoz_20191229&ie=utf8&filter_tianmao=tmall&s="
f = open('urls.txt', 'w')
for i in range(100+1):
    nurl = url+str(i*44)
    f.write(nurl+'\n')
f.close()