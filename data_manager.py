# data_manager.py
# VibeCoding SDD Phase 2.5: High Frequency Logic

import requests
import json
import os
import time
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
            except Exception as e:
                print(f"載入失敗: {e}")
                self.data = []

    def save_local_data(self):
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False)
        except Exception as e:
            print(f"存檔失敗: {e}")

    def fetch_all_history(self, progress_callback=None):
        """主入口：區分一般彩券與高頻彩券"""
        if self.config.get('is_high_frequency', False):
            return self._fetch_high_freq_history(progress_callback)
        else:
            return self._fetch_normal_history(progress_callback)

    def _fetch_normal_history(self, progress_callback):
        """原本的按月抓取邏輯 (不變)"""
        today = datetime.now()
        if self.data:
            last_date_str = self.data[0]['lotteryDate']
            last_date = datetime.strptime(last_date_str[:10], "%Y-%m-%d")
            start_date = last_date + timedelta(days=30) 
        else:
            start_date = datetime.strptime(self.config['start_date'], "%Y-%m")

        current_pointer = start_date
        while current_pointer <= today:
            month_str = current_pointer.strftime("%Y-%m")
            if progress_callback: progress_callback(f"正在下載: {month_str} 資料...")
            
            new_items = self._fetch_from_api(month=month_str)
            self._merge_data(new_items)
            
            # 月份 +1
            y, m = current_pointer.year, current_pointer.month
            if m == 12: current_pointer = current_pointer.replace(year=y+1, month=1)
            else: current_pointer = current_pointer.replace(month=m+1)
            time.sleep(0.1)

        self._finalize_data()
        return len(self.data)

    def _fetch_high_freq_history(self, progress_callback):
        """[New] 高頻彩券：只抓最近 N 天"""
        keep_days = self.config.get('keep_days', 5)
        today = datetime.now()
        
        # 抓取最近 N 天 (含今天)
        for i in range(keep_days):
            target_date = today - timedelta(days=i)
            date_str = target_date.strftime("%Y-%m-%d")
            
            if progress_callback: progress_callback(f"下載高頻資料: {date_str}...")
            
            # API 參數改用 date
            new_items = self._fetch_from_api(date=date_str)
            self._merge_data(new_items)
            time.sleep(0.1)
            
        # [滾動清理] 只保留最近 N 天的資料，刪除舊的
        # 簡單做法：只保留最近 1500 期 (5天 * 203期 ≈ 1015，抓寬鬆點)
        limit = keep_days * 210
        self.data.sort(key=lambda x: x['period'], reverse=True)
        if len(self.data) > limit:
            self.data = self.data[:limit]
            
        self._finalize_data()
        return len(self.data)

    def _fetch_from_api(self, month=None, date=None):
        """共用 API 請求函式"""
        url = self.config['api_endpoint']
        params = {}
        if month: params['month'] = month
        if date: params['date'] = date # 支援單日查詢
        
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                content = data.get('content', {})
                return content.get(self.config['api_key'], [])
        except Exception as e:
            print(f"API Error: {e}")
        return []

    def _merge_data(self, new_items):
        if not new_items: return
        existing_periods = {item['period'] for item in self.data}
        for item in new_items:
            if item['period'] not in existing_periods:
                self.data.append(item)

    def _finalize_data(self):
        self.data.sort(key=lambda x: x['period'], reverse=True)
        self.save_local_data()
        self.calculate_statistics()

    def calculate_statistics(self):
        primary_counter = Counter()
        special_counter = Counter()

        for item in self.data:
            raw_nums = item.get('drawNumberSize', [])
            if not raw_nums: continue
            
            # 賓果邏輯：超級獎號是 API 另外給的欄位 superLotto638Res 沒有
            # 但賓果的 JSON 結構通常有 'superPrizeNo' 或是要從 drawNumberSize 判斷?
            # 根據台彩 API，賓果的超級獎號通常在 'superPrizeNo' 欄位，或者特別處理
            # 這裡我們先假設 raw_nums 是 20 個號碼
            
            if self.config['is_high_frequency']:
                 # 賓果：全部 20 個號碼都算入第一區熱度
                 primary_counter.update(raw_nums)
                 
                 # 超級獎號 (Super Prize No)
                 # 檢查 API 回傳是否有 superPrizeNo
                 sp = item.get('superPrizeNo', 0)
                 if sp and sp > 0:
                     special_counter.update([sp])
            
            elif self.config['has_special']:
                # 威力/大樂透
                p_nums = raw_nums[:-1] 
                s_num = raw_nums[-1]
                primary_counter.update(p_nums)
                special_counter.update([s_num])
            else:
                # 539
                primary_counter.update(raw_nums)

        self.stats['primary'] = primary_counter.most_common()
        self.stats['special'] = special_counter.most_common()
    
    def get_sorted_stats(self):
        return self.stats