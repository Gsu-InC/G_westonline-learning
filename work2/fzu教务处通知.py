import requests
import re
from lxml import etree
import csv
import os
def strip3(a):
    a = a.strip('[')
    a = a.strip(']')
    a = a.strip("'")
    return a
    #一个去href头尾多余字符的函数
def strip2(a):
    # obj = re.compile(r'''.*?\r\n(?P<date>.*?)\r\n.*?''',re.S)
    # res = obj.finditer(a)
    # date = res.__next__().group(date)
    # date = date.strip("', '")
    # return date
    a = a.replace('\r','')
    a = a.replace('\n','')
    a = strip3(a)
    a = a.strip()
    a = a.replace("', '",'')
    pattern = r'\d{4}-\d{2}-\d{2}'
    date = re.findall(pattern, a)
    date = date[0]
    return date
    # 一个去除日期多余字符的函数
def strip_title(a):
    pattern = r'【(?P<the_title>.*?)】'
    a = strip3(a)
    title = re.search(pattern,a)
    title = title.group('the_title')
    return title
    # 一个去除标题多余字符的函数

def safe_file_name(title):
    illegal_chars = r'[<>:"/\\|?*]'
    safe_title = re.sub(illegal_chars, '_', title)
    return safe_title
def main(your_url,page): 
    myheaders = {
        "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0"
    } # 我的请求头
    url = your_url
    resp = requests.get(url,headers=myheaders,timeout=10) # 请求到网站
    resp.encoding = 'utf-8' # windows端改变编码方式为utf-8

    tree = etree.HTML(resp.text)
    child_hrefs = [] # 用于储存子网页的超链接
    names = [] # 用于储存通知人的名字
    titles = [] # 用于储存标题
    date = [] # 用于储存日期
    lis = tree.xpath('/html/body/div[1]/div[2]/div[2]/div/div/div[3]/div[1]/ul/li')
    
    # 获取到所有包含子链接的标签的迭代器

    for li in lis:
        href = li.xpath('./a/@href')
        href = str(href)
        href = strip3(href)
        href = 'https://jwch.fzu.edu.cn/' + href
        child_hrefs.append(href)
    for i in range(1,len(child_hrefs)+1):
        # 处理日期
        span_date = tree.xpath(f'/html/body/div[1]/div[2]/div[2]/div/div/div[3]/div[1]/ul/li[{i}]/span//text()')
        span_date = str(span_date)
        span_date = strip2(span_date)    
        date.append(span_date)
        # 处理通知人(这里变量写错名字懒得改了)
        title = tree.xpath(f'/html/body/div[1]/div[2]/div[2]/div/div/div[3]/div[1]/ul/li[{i}]/text()')
        title = str(title)
        title = strip_title(title)
        names.append(title)
        # 处理标题
        title = tree.xpath(f'/html/body/div[1]/div[2]/div[2]/div/div/div[3]/div[1]/ul/li[{i}]/a/text()')
        titles.append(title[0])

    resp.close() # 关闭请求
    # 开始访问并爬取子页面源代码
    child_html = [] # 用于储存子页面的html源代码
    file_data = {}

    for i in range(0,len(child_hrefs)): # 这个是访问每个通知子页面的循环
        url = child_hrefs[i] # 更新访问链接为子页面链接
        resp = requests.get(url,headers=myheaders,timeout=10) # 请求访问子页面
        resp.encoding = 'utf-8' # windows gbk转utf-8编码
        child_html.append(resp.text) # 子页面html源文件存入列表
        obj = re.compile(r'''.*?<li>附件【<a href="(?P<k_href>.*?)" target="_blank">(?P<file_name>.*?)'''
                        r'''</a>】已下载.*?getClickTimes(?P<params_package>.*?)</script>''')
        matchs = obj.finditer(resp.text) # 找到相关文字的迭代器
        # 接下来处理被动态渲染的点击次数和载入附件信息到附件列表中
        fujian = [] # 用于暂时缓存每一个网页的附件，每次访问到新的子页面时重置为空列表
        for match in matchs: # 这个是查找当前子页面中附件的循环
            k_href = match.group('k_href')
            file_name = match.group('file_name')
            params_package = match.group('params_package')
            params_l = params_package.split(',')
            params = {
                'wbnewsid' : params_l[0].strip('('),
                'owner' : params_l[1].strip('"'),
                'type' : params_l[2].strip('"'),
                'randomid' : params_l[3].strip(')')
            } # 找到点击的params
            url = 'https://jwch.fzu.edu.cn/system/resource/code/news/click/clicktimes.jsp' 
            # 这是用于请求下载次数的链接
            k_resp = requests.get(url,headers=myheaders,params=params,timeout=10)
            obj_click = re.compile(r'''{"wbshowtimes":(?P<click_times>.*?),"''')
            click_match = obj_click.finditer(k_resp.text)# 找到此附件的下载次数的迭代器
            for j in click_match: # 注意这里不能用i
                # 这个可以不看作循环因为如果匹配的话迭代器只迭代一次
                # 因为__next__()出问题StopItteration了所以试试for
                click_times = j.group('click_times')
            k_href = 'https://jwch.fzu.edu.cn'+k_href
            fujian_new = [file_name,f'下载次数为{click_times}次',k_href] # 简单的把这个附件的信息存成列表
            fujian.append(fujian_new) # 存入此附件中
            k_resp.close() # 关闭访问获取click次数页面的请求
        resp.close() # 关闭此次循环的请求
        file_data[titles[i]] = {'日期':date[i],'通知人':names[i],'附件':fujian,'源文件':child_html[i]}

        # 接下来尝试将爬取到的数据存入csv文件
    
    base_path = r"E:\Gsu\python_code\fzu_jwchs" # 绝对路径的文件夹路径    
    for element in file_data:
        title = safe_file_name(element)
        file_name = f"fzu_jwch_page{page}{title}.csv" # 文件名
        file_path = os.path.join(base_path, file_name)
        f = open(file_path,mode='w',encoding='utf-8',newline='')
        csvwriter = csv.writer(f)
        csvwriter.writerow([element," ",file_data[element]['日期']," ",file_data[element]['通知人']," ",file_data[element]['附件']," ",file_data[element]['源文件']])
        f.close()

    

first_url = 'https://jwch.fzu.edu.cn/jxtz.htm' # 这是基础的链接，也是第一页的链接
# 因为fzu网站除第一页之后的链接会是基础链接+倒数的页数，这里直接使用数学方法暴力解决
# ！！！ 如果页面总页数有变要更改总页数！！！

pages_n = 209 # 此时教务处总页数为209

# 接下来开始提取页面信息
main(first_url,1)
for i in range(2,pages_n+1):
    real_page_number = pages_n-i+1
    real_url = f'https://jwch.fzu.edu.cn/jxtz/{real_page_number}.htm'
    main(real_url,i)