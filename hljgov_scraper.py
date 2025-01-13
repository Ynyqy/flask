import re
import pymysql  # 使用 pymysql 替换 mysql.connector
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json


# 从文件读取关键词
def read_keywords():
    with open('keywords.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data.get('keywords', [])


# 将多个页面的 URL 放在一个列表中
URLS = [
    "https://jt.hlj.gov.cn/jt/c105080/list.shtml",
    "https://jt.hlj.gov.cn/jt/c105088/list.shtml",
    "https://jt.hlj.gov.cn/jt/c105090/list.shtml",
    "https://jt.hlj.gov.cn/jt/tzxx/list.shtml",
    "https://jt.hlj.gov.cn/jt/c105081/list.shtml"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}


def clean_title(title):
    """
    清理标题，移除可能包含的日期信息。
    :param title: 原始标题字符串
    :return: 清理后的标题
    """
    # 移除格式类似 "2025-01-07" 的日期
    cleaned_title = re.sub(r'\d{4}-\d{2}-\d{2}', '', title)
    # 移除额外的空格
    return cleaned_title.strip()


# 连接到 MySQL 数据库，使用 pymysql
def connect_to_db():
    try:
        connection = pymysql.connect(
            host="localhost",  # 数据库主机
            user="root",  # 数据库用户名
            password="1234",  # 数据库密码
            database="news",  # 数据库名称
            charset="utf8mb4"  # 支持中文字符集
        )
        return connection
    except pymysql.MySQLError as err:
        print(f"数据库连接错误：{err}")
        return None


# 将数据插入到数据库中
def save_to_db(data):
    connection = connect_to_db()
    if connection is None:
        print("无法连接到数据库")
        return

    cursor = connection.cursor()

    # 插入数据到 news_table 表
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
                item.get('标签', None),
                item.get('正文', None),
                item.get('摘要', None)
            ))
            connection.commit()
        except pymysql.MySQLError as err:
            print(f"插入数据时发生错误: {err}")

    cursor.close()
    connection.close()


def get_news_list(url, keywords):
    """
    抓取新闻列表并根据关键词筛选新闻
    :param url: 目标页面的 URL
    :param keywords: 要筛选的关键词列表
    :return: 筛选后的新闻列表，包含标题、链接和发布日期
    """
    news_list = []

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()  # 检查请求是否成功
        response.encoding = "utf-8"  # 设置编码，确保中文正确显示
    except requests.RequestException as e:
        print(f"请求错误：{e}")
        return news_list

    soup = BeautifulSoup(response.text, "html.parser")

    # 解析新闻条目
    for item in soup.select("ul.listul li"):
        a_tag = item.find("a")
        if a_tag:
            title = a_tag.get_text(strip=True) if a_tag else "无标题"
            title = clean_title(title)  # 调用函数清理标题
            link = a_tag["href"]
            raw_date = item.find("span", class_="date").get_text(strip=True) if item.find("span",
                                                                                          class_="date") else "无日期"

            try:
                # 假设日期格式为：2025-01-07
                date = datetime.strptime(raw_date, "%Y-%m-%d").strftime("%Y-%m-%d")
            except ValueError:
                date = "日期格式错误"

            if not link.startswith("http"):
                link = "https://jt.hlj.gov.cn" + link  # 拼接完整的链接

            # 如果标题中包含任何关键词，则添加到新闻列表
            if any(keyword in title for keyword in keywords):
                news_list.append({"标题": title, "链接": link, "发布日期": date})

    return news_list


def main():
    """主程序"""
    print("正在爬取头条新闻...")

    # 读取关键词列表
    keywords = read_keywords()

    if not keywords:
        print("未找到关键词文件或文件为空，请检查关键词文件。")
        return

    all_news = []  # 用于存储所有页面的新闻数据

    for url in URLS:
        print(f"正在抓取页面: {url}")
        news_list = get_news_list(url, keywords)
        all_news.extend(news_list)
        print(f"已抓取 {len(news_list)} 条新闻。")

    print(f"抓取到 {len(all_news)} 条新闻。")

    if all_news:
        save_to_db(all_news)
        print("数据已保存到数据库")
    else:
        print("未抓取到任何符合条件的新闻数据。")


if __name__ == "__main__":
    main()
