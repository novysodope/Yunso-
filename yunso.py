
import requests
from datetime import datetime, timedelta
from wxauto import *
import os
import json
import re
from rich import print
import time
from rich.console import Console
from datetime import datetime
import sys
from rich.progress import Progress
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Side
from bs4 import BeautifulSoup
import configparser
import threading

config_file = 'yunso_config.ini'
config = configparser.ConfigParser()
config.read(config_file, encoding="utf-8")


class Yunso:
    def __init__(self,config):
        global config_file
        self.banner = """
____    ____  __    __  .__   __.      _______.  ______   
\\   \\  /   / |  |  |  | |  \\ |  |     /       | /  __  \\  
 \\   \\/   /  |  |  |  | |   \\|  |    |   (----`|  |  |  | 
  \\_    _/   |  |  |  | |  . `  |     \\   \\    |  |  |  | 
    |  |     |  `--'  | |  |\\   | .----)   |   |  `--'  | 
    |__|      \\______/  |__| \\__| |_______/     \\______/  

https://github.com/novysodope/yunso      云索|Fupo Series

"""
        print(f"[green]{self.banner}[/green]")
        print("————————————————初始化开始————————————————\n")
        print(f"[green][配置文件][/green] {config_file}\n")
#---------------------配置-------------------------------
        self.config = config
        self.listen_list = self.config.get("DEFAULT", "listen_list", fallback="").split(",")
        item = '|'.join(self.listen_list)
        print(f"[green][消息发送对象][/green] {item}\n")
        self.access_token = self.config['DEFAULT']['github_api_key']
        print(f"[green][Github访问令牌][/green] {self.access_token}\n")

        self.SEARCH_TYPES = ['repositories']
        self.GITHUB_API_URL = 'https://api.github.com/search'
        self.VULBOX_API_URL = "https://vip.vulbox.com/api/data/base_vuln_list"

        self.SENT_RECORDS_FILE = "sent_records.json"
        self.LAST_REPORT_FILE = "last_report.json"

        self.now = datetime.now()
        self.formatted_date = self.now.strftime("%Y-%m-%d")
        self.filename = f"推送周报_{self.formatted_date}.xlsx"
        self.SEARCH_KEYWORDS = self.config.get("DEFAULT", "search_keywords", fallback="").split(",")
        itemkey = '|'.join(self.SEARCH_KEYWORDS)
        print(f"[green][监控内容][/green] {itemkey}\n")
        self.weekdays = {
            0: "星期一",
            1: "星期二",
            2: "星期三",
            3: "星期四",
            4: "星期五",
            5: "星期六",
            6: "星期日"
        }
        self.last_printed_date = None

        self.GITHUB_HEADERS = {
            'Authorization': f'token {self.access_token}',
            'Accept': 'application/vnd.github.v3+json',
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        }

        self.VULBOX_HEADERS = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36",
            "Content-Type": "application/json; charset=UTF-8",
            "Origin": "https://vip.vulbox.com",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Referer": "https://vip.vulbox.com/originalList?keyword=",
            "Accept-Language": "zh-CN,zh;q=0.9"
        }
        self.wx = WeChat()
#---------------------配置-------------------------------
     
#----------------------初始化sent_records.json，用来检查是否有重复记录------------------------------
        if os.path.exists(self.SENT_RECORDS_FILE):
            try:
                with open(self.SENT_RECORDS_FILE, "r") as f:
                    content = f.read().strip()
                    self.sent_records = set(json.loads(content)) if content else set()
            except json.JSONDecodeError:
                self.sent_records = set()
        else:
            self.sent_records = set()
#----------------------初始化sent_records.json，用来检查是否有重复记录------------------------------

#----------------------拿到漏洞标题------------------------------
    def query_vulbox(self, cve):
        api_url = self.VULBOX_API_URL
        payload = {
            "keyword": cve,
            "riskLevelSort": "",
            "modifyTimeSort": 0,
            "publishTimeSort": None,
            "page": 1,
            "pageSize": 10
        }
        try:
            response = requests.post(api_url, json=payload, headers=self.VULBOX_HEADERS, timeout=10)
            time.sleep(3)

            if response.status_code == 200:
                data = response.json()
                records = data.get("data", {}).get("records", [])

                for record in records:
                    print(f"input:{cve}")
                    vuln_cve = record.get("vulnCveCode", "")
                    print(f"api:{vuln_cve}")

                    if vuln_cve == cve:
                        vuln_id = records[0].get("id", "")
                        print("|--------Block begin---------|")
                        print(f"input:{cve}")
                        print(f"api:{vuln_cve}")
                        print(f"id:{vuln_id}")

                        if vuln_id:
                            detail_url = f"https://vip.vulbox.com/detail/{vuln_id}"
                            print(f"url:{detail_url}")
                            detail_response = requests.get(detail_url, headers=self.VULBOX_HEADERS)

                            if detail_response.status_code == 200:
                                soup = BeautifulSoup(detail_response.text, 'html.parser')
                                title_tag = soup.find('h3', class_='break-all ui-pr60 header-tit text-overflow-3')

                                if title_tag and title_tag.has_attr('title'):
                                    vuln_name = title_tag['title']
                                    print(f"name:{vuln_name}")
                                    print("|------------End-------------|\n")
                                    return vuln_name
                    else:
                        return cve
        except Exception as e:
            print(f"查询接口出错: {e}")
        return cve
#----------------------拿到漏洞标题------------------------------

#-----------------------Github监听，结果整理-----------------------------
    def search_and_notify(self):
        global sent_records
        new_sent_records = set()
        message_vuln = []
        nows = datetime.utcnow()
        search_time = nows - timedelta(days=2)
        search_time_td = search_time.strftime('%Y-%m-%d')

        with Progress() as progress:
            search_keywords_count = len(self.SEARCH_KEYWORDS)
            task = progress.add_task(f"[cyan]一共[{search_keywords_count}]个关键字，请稍候[/cyan]", total=len(self.SEARCH_KEYWORDS))
            sys.stdout.write("\r")
            sys.stdout.flush()
            for keyword in self.SEARCH_KEYWORDS:
                query = f'{keyword.lower()} created:>{search_time_td}'
                params = {'q': query}

                for search_type in self.SEARCH_TYPES:
                    full_url = f"{self.GITHUB_API_URL}/{search_type}"
                    response = requests.get(full_url, headers=self.GITHUB_HEADERS, params=params, timeout=120)
                    time.sleep(5)

                    if response.status_code == 200:
                        results = response.json()
                        items = results.get('items', [])

                        for item in items:
                            name = item.get('name', '')
                            html_url = item.get('html_url', '')
                            description = item.get('description', '')
                            unique_identifier = f"{name}|{html_url}|{description}"

                            if unique_identifier not in self.sent_records and unique_identifier not in new_sent_records:
                                if 'cve' in name.lower():
                                    match = re.search(r'cve[-_ ]?\d{4}[-_ ]?\d{3,}', name, re.IGNORECASE)
                                    if match:
                                        cve = match.group(0).upper().replace("_", "-").replace(" ", "-")
                                        cve_name = self.query_vulbox(cve)
                                        if cve_name:
                                            name = cve_name
                                            message_vuln.append(
                                                f"- 漏洞信息: {name}\n- 地址: {html_url}\n- 描述: {description}\n")
                                        else:
                                            message_vuln.append(
                                                f"- 名称: {name}\n- 地址: {html_url}\n- 描述: {description}\n")
                                else:
                                    message_vuln.append(f"- 名称: {name}\n- 地址: {html_url}\n- 描述: {description}\n")
                                new_sent_records.add(unique_identifier)

                    else:
                        print(f'请求失败，状态码: {response.status_code}, 响应: {response.text}')

                progress.update(task, advance=1)  # 更新进度条
 #-----------------------Github监听，结果整理-----------------------------

 #-----------------------发送文本-----------------------------
        if message_vuln:
            msg = '#新动态提示\n\n' + '\n'.join(message_vuln)
            msg += '\n* POC及工具等信息均来自Github，请注意辨别。本脚本仅用于监控推送'
            for who in self.listen_list:
                print(f"正在向 {who} 发送消息...")
                self.wx.SendMsg(msg, who)
            self.sent_records.update(new_sent_records)

            with open(self.SENT_RECORDS_FILE, "w", encoding="utf-8") as f:
                json.dump(list(self.sent_records), f)
        else:
            print("没有新内容，开始表明存活状态")
            self.wx.GetSessionList()
            self.wx.SendMsg("online", '文件传输助手')
#-----------------------发送文本-----------------------------

#---------------------生成周报-------------------------------
    def parse_sent_records(self):
        print(self.SENT_RECORDS_FILE)
        if not os.path.exists(self.SENT_RECORDS_FILE):
            return []

        with open(self.SENT_RECORDS_FILE, "r") as f:
            try:
                records = json.load(f)
            except json.JSONDecodeError:
                records = []
        parsed_records = []

        for record in records:
            parts = record.split('|')
            if len(parts) == 3:
                title, address, description = parts
                parsed_records.append({"标题": title, "地址": address, "描述": description})

        return parsed_records

    def get_previous_report(self):
        if os.path.exists(self.LAST_REPORT_FILE):
            try:
                with open(self.LAST_REPORT_FILE, "r", encoding="utf-8") as f:
                    return set(tuple(item.items()) for item in json.load(f))
            except json.JSONDecodeError:
                return set()
        return set()

    def filter_new_records(self, records):
        previous_records = self.get_previous_report()
        new_records = [record for record in records if tuple(record.items()) not in previous_records]
        return new_records

    def generate_weekly_report(self):
        records = self.parse_sent_records()
        if not records:
            print("没有新漏洞记录，无需生成周报。")
            return False

        new_records = self.filter_new_records(records)

        if not new_records:
            print("本周无新增漏洞记录，跳过生成。")
            return False

        df = pd.DataFrame(records)
        df.to_excel(self.filename, index=False)

        wb = load_workbook(self.filename)
        ws = wb.active
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(cell.value)
                except:
                    pass
            adjusted_width = (max_length + 2)
            ws.column_dimensions[column].width = max(adjusted_width, 54)
        for row in ws.iter_rows():
            for cell in row:
                cell.alignment = Alignment(wrap_text=True)
                cell.border = Border(
                    top=Side(border_style="thin", color="000000"),
                    bottom=Side(border_style="thin", color="000000"),
                    left=Side(border_style="thin", color="000000"),
                    right=Side(border_style="thin", color="000000")
                    )

        wb.save(self.filename)

        print(f"周报已生成：{self.filename}")

        with open(self.LAST_REPORT_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=4)

        msg = '开始统计本周周报：'
        for who in self.listen_list:
            print(f"正在向 {who} 发送消息...")
            wxchat.SendMsg(msg, who)
            print("消息发送完成。")
        return True
#---------------------生成周报-------------------------------

#-----------------------每周五发送文件-----------------------------
    def print_weekday(self):
        print("周五开始统计周报")
        if self.generate_weekly_report():
            wxchat.SendFiles(self.filename, self.who)
#-----------------------每周五发送文件-----------------------------

#----------------------脚本循环------------------------------
    def run(self):
        while True:
            self.search_and_notify()
            if self.now.weekday() == 4 and self.last_printed_date != self.now.date():
                self.print_weekday()
                self.last_printed_date = self.now.date()
            print("等待30分钟后继续...")
            time.sleep(1800)
#----------------------脚本循环------------------------------

'''
github的搜索结果太露骨了，我先删掉这个方法了不公开了，避免被有心之人利用
'''


if __name__ == "__main__":
    yunso = Yunso(config)
    # yunsobt = Yunsobt(config)
    # 又学会了一招，设置daemon=True让线程随主线程退出
    yunso_thread = threading.Thread(target=yunso.run,daemon=True)
    # yunsobt_thread = threading.Thread(target=yunsobt.run,daemon=True)
    yunso_thread.start()
    # yunsobt_thread.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        exit = '''
        \n\n
        [red]ヾ(￣▽￣)Bye~Bye~[/red]
        \n\n
    '''
        print(exit)
