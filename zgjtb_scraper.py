import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import pymysql  # 使用pymysql替换mysql.connector

# 从文件读取关键词
def read_keywords():
    with open('keywords.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data.get('keywords', [])

# 将多个页面链接加入列表
BASE_URLS = [
    "https://www.zgjtb.com/node_141.html",
    "https://www.zgjtb.com/node_15619.html",
    "https://www.zgjtb.com/node_15620.html",
    "https://www.zgjtb.com/node_15621.html",
    "https://www.zgjtb.com/node_15622.html",
    "https://www.zgjtb.com/node_15623.html",
    "https://www.zgjtb.com/node_15624.html"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def get_news_list(url, max_pages=5):
    """
    抓取头条新闻列表，处理分页，并限制抓取的最大页数
    :param url: 目标页面的 URL
    :param max_pages: 最大抓取的页数
    :return: 新闻列表，包含标题、链接和发布日期
    """
    keywords = read_keywords()  # 获取当前的关键词列表
    news_list = []
    current_page = 1  # 当前页数

    while url and current_page <= max_pages:
        print(f"正在抓取 {url} 第 {current_page} 页...")

        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()  # 检查请求是否成功
            response.encoding = "utf-8"  # 设置编码，确保中文正确显示
        except requests.RequestException as e:
            print(f"请求错误：{e}")
            break

        soup = BeautifulSoup(response.text, "html.parser")

        # 解析新闻条目
        for item in soup.select("div.content-one ul li"):
            a_tag = item.find("a")
            if a_tag:
                title = a_tag.find("span").get_text(strip=True) if a_tag.find("span") else "无标题"
                link = a_tag["href"]
                raw_date = item.find_all("span")[-1].get_text(strip=True) if len(item.find_all("span")) > 1 else "无日期"

                try:
                    current_year = datetime.now().year
                    formatted_date = f"{current_year}-{raw_date[:5]}"  # 补全年份，忽略时间部分
                    date = datetime.strptime(formatted_date, "%Y-%m-%d").strftime("%Y-%m-%d")
                except ValueError:
                    date = "日期格式错误"

                if not link.startswith("http"):
                    link = "https://www.zgjtb.com" + link

                # 只添加标题非“无标题”的新闻，并且标题包含关键词
                if title != "无标题" and any(keyword in title for keyword in keywords):
                    news_list.append({"标题": title, "链接": link, "发布日期": date})

        # 获取下一页的链接
        next_page = soup.select_one("ul.pages li.page-next a")
        if next_page:
            url = next_page["href"]
        else:
            url = None  # 如果没有下一页，结束循环

        current_page += 1  # 增加页数

    return news_list

def save_to_mysql(data):
    """
    将新闻数据保存到 MySQL 数据库
    :param data: 要保存的新闻数据列表
    """
    # MySQL 连接配置
    db_config = {
        "host": "localhost",  # 数据库主机
        "user": "root",  # 数据库用户名
        "password": "1234",  # 数据库密码
        "database": "news"  # 数据库名称
    }

    try:
        # 创建连接
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()

        # 插入新闻数据
        for item in data:
            try:
                cursor.execute("""
                    INSERT INTO news (title, link, publish_date, crawl_time, label, content, summary)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    item['标题'],
                    item['链接'],
                    item['发布日期'],
                    datetime.now(),  # 当前时间作为爬取时间
                    item.get('标签', None),  # 假设没有标签时为 None
                    item.get('正文', None),  # 假设没有正文时为 None
                    item.get('摘要', None)   # 假设没有摘要时为 None
                ))
                conn.commit()
            except pymysql.MySQLError as err:
                print(f"插入数据时发生错误: {err}")

        print(f"成功保存 {len(data)} 条新闻到数据库。")

    except pymysql.MySQLError as err:
        print(f"数据库错误: {err}")
    finally:
        if conn.open:
            cursor.close()
            conn.close()

def main():
    """主程序"""
    print("正在爬取头条新闻...")

    news_list = []

    # 遍历每个BASE_URL
    for base_url in BASE_URLS:
        news_list += get_news_list(base_url, max_pages=3)

    print(f"抓取到 {len(news_list)} 条新闻。")

    if news_list:
        save_to_mysql(news_list)
    else:
        print("未抓取到任何新闻数据。")

if __name__ == "__main__":
    main()
