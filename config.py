# config.py
# VibeCoding SDD Phase 2.5: Add Bingo Bingo Config

class LotteryType:
    SUPER_LOTTO = "super_lotto"
    LOTTO_649 = "lotto_649"
    DAILY_539 = "daily_539"
    BINGO_BINGO = "bingo_bingo" # [New]

LOTTERY_CONFIG = {
    LotteryType.SUPER_LOTTO: {
        "name": "威力彩 (Super Lotto)",
        "api_endpoint": "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/SuperLotto638Result",
        "api_key": "superLotto638Res",
        "start_date": "2008-01",
        "primary_range": (1, 38),
        "special_range": (1, 8),
        "select_count": 6,
        "has_special": True,
        "special_label": "第二區",
        "theme_color": "#FFD700",
        "is_high_frequency": False # 一般彩券
    },
    LotteryType.LOTTO_649: {
        "name": "大樂透 (Lotto 6/49)",
        "api_endpoint": "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/Lotto649Result",
        "api_key": "lotto649Res",
        "start_date": "2004-01",
        "primary_range": (1, 49),
        "special_range": (1, 49),
        "select_count": 6,
        "has_special": True,
        "special_label": "特別號",
        "theme_color": "#FF6347",
        "is_high_frequency": False
    },
    LotteryType.DAILY_539: {
        "name": "今彩539 (Daily 539)",
        "api_endpoint": "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/Daily539Result",
        "api_key": "daily539Res",
        "start_date": "2007-01",
        "primary_range": (1, 39),
        "special_range": None,
        "select_count": 5,
        "has_special": False,
        "special_label": None,
        "theme_color": "#2E8B57",
        "is_high_frequency": False
    },
    # [Fix] 賓果賓果設定 (更新版)
    LotteryType.BINGO_BINGO: {
        "name": "賓果賓果 (Bingo Bingo)",
        "api_endpoint": "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/BingoResult", # 修正路徑
        "api_key": "bingoQueryResult", # 修正 Key
        "start_date": "N/A", 
        "primary_range": (1, 80), 
        "special_range": (1, 80), 
        "select_count": 5, 
        "has_special": True, 
        "special_label": "超級獎號",
        "theme_color": "#9C27B0", 
        "is_high_frequency": True, 
        "keep_days": 5, 
        "play_mode": "star_selection" 
    }
}