# data_manager.py
# VibeCoding SDD Phase 3: Logging Integration

import requests
import json
import os
import time
import csv
import logging  # <--- [新增] 匯入 logging 模組
from datetime import datetime, timedelta
from collections import Counter
from config import LOTTERY_CONFIG

class DataManager:
    def __init__(self, lottery_key):
        self.lottery_key = lottery_key
        self.config = LOTTERY_CONFIG[lottery_key]
        self.filename = f"history_{self.lottery_key}.json"
        self.data = [] 
        self.stats = {} 
        self.load_local_data()

    def load_local_data(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                self.calculate_statistics()
                logging.info(f"[{self.config['name']}] 本地資料載入成功，共 {len(self.data)} 筆") # <--- 改用 logging
            except Exception as e:
                logging.error(f"[{self.config['name']}] 資料載入失敗: {e}") # <--- 改用 logging
                self.data = []
        else:
            logging.info(f"[{self.config['name']}] 無本地資料，初始化為空")

    def save_local_data(self):
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False)
            logging.debug(f"[{self.config['name']}] 資料已存檔")
        except Exception as e:
            logging.error(f"存檔失敗: {e}")

    def fetch_all_history(self, progress_callback=None):
        logging.info(f"開始更新: {self.config['name']}")
        if self.config.get('is_high_frequency', False):
            return self._fetch_high_freq_history(progress_callback)
        else:
            return self._fetch_normal_history(progress_callback)

    def _fetch_normal_history(self, progress_callback):
        today = datetime.now()
        if self.data:
            last_date_str = self.data[0]['lotteryDate']
            try:
                last_date = datetime.strptime(last_date_str[:10], "%Y-%m-%d")
            except:
                last_date = datetime.strptime(self.config['start_date'], "%Y-%m")
            start_date = last_date + timedelta(days=1) 
        else:
            start_date = datetime.strptime(self.config['start_date'], "%Y-%m")

        current_pointer = start_date
        
        if current_pointer > today:
            logging.info("資料已是最新，無需更新")
            return 0

        while current_pointer <= today:
            month_str = current_pointer.strftime("%Y-%m")
            msg = f"正在下載: {month_str} 資料..."
            if progress_callback: progress_callback(msg)
            logging.debug(msg) # 紀錄下載過程
            
            new_items = self._fetch_from_api(month=month_str)
            self._merge_data(new_items)
            
            y, m = current_pointer.year, current_pointer.month
            if m == 12: current_pointer = current_pointer.replace(year=y+1, month=1)
            else: current_pointer = current_pointer.replace(month=m+1)
            time.sleep(0.1)

        self._finalize_data()
        return len(self.data)

    def _fetch_high_freq_history(self, progress_callback):
        keep_days = self.config.get('keep_days', 5)
        today = datetime.now()
        
        for i in range(keep_days):
            target_date = today - timedelta(days=i)
            date_str = target_date.strftime("%Y-%m-%d")
            
            msg = f"下載高頻資料: {date_str}..."
            if progress_callback: progress_callback(msg)
            logging.debug(msg)
            
            new_items = self._fetch_from_api(date=date_str)
            self._merge_data(new_items)
            time.sleep(0.1)
            
        limit = keep_days * 210
        self.data.sort(key=lambda x: str(x['period']), reverse=True)
        if len(self.data) > limit:
            logging.info(f"清理舊資料，保留最近 {limit} 筆")
            self.data = self.data[:limit]
            
        self._finalize_data()
        return len(self.data)

    def _fetch_from_api(self, month=None, date=None):
        url = self.config['api_endpoint']
        params = {}
        if month: params['month'] = month
        if date: params['date'] = date
        
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                content = data.get('content', {})
                if isinstance(content, dict):
                    return content.get(self.config['api_key'], [])
                elif isinstance(content, list):
                    return content
            else:
                logging.warning(f"API 回傳狀態碼非 200: {resp.status_code}")
        except Exception as e:
            logging.error(f"API 連線錯誤: {e}")
        return []

    def _merge_data(self, new_items):
        if not new_items: return 0
        existing_periods = {str(item['period']) for item in self.data}
        count = 0
        for item in new_items:
            if str(item['period']) not in existing_periods:
                self.data.append(item)
                count += 1
        if count > 0:
            logging.debug(f"新增 {count} 筆資料")
        return count

    def _finalize_data(self):
        self.data.sort(key=lambda x: str(x['period']), reverse=True)
        self.save_local_data()
        self.calculate_statistics()

    def calculate_statistics(self):
        primary_counter = Counter()
        special_counter = Counter()

        for item in self.data:
            raw_nums = item.get('drawNumberSize', [])
            if not raw_nums: continue
            
            if self.config['is_high_frequency']:
                 primary_counter.update(raw_nums)
                 sp = item.get('superPrizeNo', 0)
                 if sp and int(sp) > 0:
                     special_counter.update([int(sp)])
            elif self.config['has_special']:
                p_nums = raw_nums[:-1] 
                s_num = raw_nums[-1]
                primary_counter.update(p_nums)
                special_counter.update([s_num])
            else:
                primary_counter.update(raw_nums)

        self.stats['primary'] = primary_counter.most_common()
        self.stats['special'] = special_counter.most_common()
    
    def get_sorted_stats(self):
        return self.stats

    def import_from_csv(self, file_path):
        """讀取 CSV 並轉換為系統格式"""
        logging.info(f"開始匯入 CSV: {file_path}")
        parsed_items = []
        
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                
                for row in reader:
                    if not row or len(row) < 20: continue 
                    
                    try:
                        period = str(row[1]).strip()
                        date_str = row[2].strip()
                        date_fmt = date_str.replace('/', '-')
                        
                        draw_numbers = []
                        for i in range(6, 26):
                            val = row[i].strip()
                            if val.isdigit():
                                draw_numbers.append(int(val))
                        
                        super_prize = 0
                        if len(row) > 26:
                            sp_val = row[26].strip()
                            if sp_val.isdigit():
                                super_prize = int(sp_val)

                        if not draw_numbers: continue

                        item = {
                            "period": period,
                            "lotteryDate": date_fmt,
                            "drawNumberSize": sorted(draw_numbers),
                            "superPrizeNo": super_prize
                        }
                        
                        parsed_items.append(item)
                        
                    except Exception as e:
                        logging.warning(f"CSV 解析警告 (Row 跳過): {row} -> {e}")
                        continue

            if parsed_items:
                added = self._merge_data(parsed_items)
                self._finalize_data()
                logging.info(f"匯入完成: 新增 {added} 筆，重複/略過 {len(parsed_items) - added} 筆")
                return added, len(parsed_items) - added
            else:
                logging.warning("CSV 檔案中未發現有效資料")
                return 0, 0

        except Exception as e:
            logging.error(f"開啟 CSV 檔案失敗: {e}")
            return 0, 0