import subprocess
import os
import json
import traceback

from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import threading
import requests
import sys

app = Flask(__name__)

# 定义爬虫脚本的绝对路径
SCRAPER_SCRIPTS = {
    "hljgov": r"D:\Programmings\pythonProject6\app\hljgov_scraper.py",  # 黑龙江省交通运输厅爬虫
    "zgjtb": r"D:\Programmings\pythonProject6\app\zgjtb_scraper.py"     # 中国交通新闻网爬虫
}

# 获取百度API的access_token
API_KEY = '9T3yL2wSarv4ZWySyA2u3cvj'
SECRET_KEY = 'mHBcxbVrY01URBx6Dmm2GQqnbmHYAOVH'

def get_access_token():
    url = f'https://aip.baidubce.com/oauth/2.0/token'
    params = {
        'grant_type': 'client_credentials',
        'client_id': API_KEY,
        'client_secret': SECRET_KEY
    }
    response = requests.post(url, data=params)
    result = response.json()
    return result.get('access_token')

# 调用百度API进行关键词提取
def extract_keywords(text):
    access_token = get_access_token()
    url = f'https://aip.baidubce.com/rpc/2.0/nlp/v1/txt_keywords_extraction?access_token={access_token}'

    headers = {
        'Content-Type': 'application/json',
    }

    data = {
        'text': [text],  # 输入的文本
        'num': 5  # 提取前5个关键词。。。
    }

    response = requests.post(url, json=data, headers=headers)
    return response.json()

# 执行爬虫脚本
def execute_scraper(scraper_name, keywords):
    script = SCRAPER_SCRIPTS.get(scraper_name)
    if script and os.path.exists(script):
        command = [sys.executable, script] + keywords  # 使用当前 Python 环境执行脚本
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')  # 指定编码为utf-8
            print(f"爬取 {scraper_name} 成功，关键词：{keywords}")
            print("标准输出:", result.stdout)
            print("标准错误:", result.stderr)
        except subprocess.CalledProcessError as e:
            print(f"执行爬虫脚本失败: {e}")
            print("标准输出:", e.stdout)
            print("标准错误:", e.stderr)
            print("错误追踪信息:")
            traceback.print_exc()  # 打印详细的错误信息
    else:
        print(f"爬虫脚本 {scraper_name} 不存在！")

# 设置定时任务
def setup_scheduled_task(scraper_names, keywords, interval_minutes):
    scheduler = BackgroundScheduler()

    for scraper_name in scraper_names:
        if scraper_name in SCRAPER_SCRIPTS:
            # 为每个爬虫设置定时任务
            scheduler.add_job(
                execute_scraper,
                trigger=IntervalTrigger(minutes=int(interval_minutes)),
                id=scraper_name,
                name=f"爬取任务：{scraper_name}",
                replace_existing=True,
                args=[scraper_name, keywords]  # 传递关键词和爬虫名称
            )
        else:
            print(f"未知的爬虫名称：{scraper_name}")

    scheduler.start()
    print(f"定时任务设置成功，每 {interval_minutes} 分钟执行一次.")

# 保存关键词到json文件
def save_keywords_to_json(keywords):
    try:
        with open('keywords.json', 'w', encoding='utf-8') as f:
            json.dump({'keywords': keywords}, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"保存关键词失败: {e}")

# 提取并保存关键词的路由
@app.route('/extract-keywords', methods=['POST'])
def extract_keywords_route():
    data = request.get_json()
    text = data.get('text', '')

    if not text:
        return jsonify({'success': False, 'message': '输入文本不能为空'}), 400

    # 提取关键词
    response = extract_keywords(text)
    if 'results' in response:
        keywords = [result['word'] for result in response['results']]
        save_keywords_to_json(keywords)  # 保存关键词到keywords.json文件
        return jsonify({'success': True, 'keywords': keywords}), 200
    else:
        return jsonify({'success': False, 'message': '关键词提取失败'}), 400

# 处理前端请求的路由
@app.route('/schedule-task', methods=['POST'])
def schedule_task():
    data = request.get_json()

    keywords = data.get('keywords', [])
    scraper_names = data.get('scraper_names', [])
    interval_minutes = data.get('interval_minutes', 60)

    if not keywords:
        return jsonify({'success': False, 'message': '关键词不能为空'}), 400

    if not scraper_names:
        return jsonify({'success': False, 'message': '至少选择一个网站'}), 400

    # 使用单独的线程来避免阻塞主线程
    threading.Thread(target=setup_scheduled_task, args=(scraper_names, keywords, interval_minutes)).start()

    return jsonify({'success': True, 'message': '定时任务已设置'}), 200

# 根路由，返回index.html
@app.route('/')
def index():
    return app.send_static_file('index.html')

if __name__ == '__main__':
    app.run(debug=True)
