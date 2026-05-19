import os
import requests
import time
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from DrissionPage import ChromiumPage, ChromiumOptions

# ==========================================
# 🔐 GitHub Secrets
# ==========================================
GENERAL_WEBHOOK = os.getenv("GENERAL_WEBHOOK")
LOG_WEBHOOK = os.getenv("LOG_WEBHOOK")
MAIN_URL = os.getenv("MAIN_URL")

def send_discord(message, mode="all"):
    now_str = datetime.now(ZoneInfo("Asia/Seoul")).strftime('%H:%M:%S')
    
    if message.startswith("-# "):
        formatted_message = f"-# [{now_str}] {message[3:]}"
    else:
        formatted_message = f"[{now_str}] {message}"
        
    print(formatted_message)
    
    if not GENERAL_WEBHOOK or not LOG_WEBHOOK:
        print(f"[{now_str}] ⚠️ 환경변수(Webhook) 미설정. 콘솔 출력만 진행합니다.")
        return

    targets = []
    if mode == "all":
        targets.extend([GENERAL_WEBHOOK, LOG_WEBHOOK])
    elif mode == "log":
        targets.append(LOG_WEBHOOK)

    for url in targets:
        try:
            requests.post(url, json={'content': formatted_message}, timeout=3)
        except Exception as e:
            print(f"[{now_str}] 웹훅 전송 실패: {e}")

# ==========================================
# 🎯 타겟 설정 및 주입용 JS 스니펫
# ==========================================
TARGET_PERFORMANCES = [
    {'date': '2026년 5월 24일', 'time': '19:00'},
]

REACT_INJECT_JS = """
let keys = Object.keys(this);
let reactKey = keys.find(k => k.startsWith('__reactProps$') || k.startsWith('__reactEventHandlers$'));
if (reactKey && this[reactKey] && typeof this[reactKey].onClick === 'function') {
    this[reactKey].onClick({ preventDefault: () => {}, stopPropagation: () => {}, target: this, currentTarget: this });
    return "React Inject Success";
} else {
    this.click();
    return "Fallback Native Click";
}
"""

# ==========================================
# 🤖 DrissionPage 브라우저 세팅 (Ubuntu Headless 최적화)
# ==========================================
send_discord("프로그램을 시작합니다.", mode="log")
send_discord("⚙️ GitHub Actions DrissionPage 엔진 기동 중...", mode="log")

co = ChromiumOptions()
co.headless(True)  # 백그라운드 실행
co.set_argument('--no-sandbox')
co.set_argument('--disable-dev-shm-usage')
co.set_argument('--disable-gpu')
co.set_argument('--window-size=1920,1080')
co.set_argument('--disable-blink-features=AutomationControlled')
co.set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')

try:
    page = ChromiumPage(co)
except Exception as e:
    send_discord(f"❌ 크롬 기동 실패:\n{e}", mode="all")
    exit(1)

send_discord("DrissionPage 설정 완료!", mode="log")

# ==========================================
# 🚀 React DOM 파싱 루프 (타이머 적용)
# ==========================================
send_discord("🚀 프로그램 감시 시작", mode="log")

loop_count = 0
start_time = datetime.now(ZoneInfo("Asia/Seoul"))
max_duration = timedelta(hours=5, minutes=55)

# 이전 루프의 상태를 기억할 리스트 선언
previous_seats_info = []

while True:
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    loop_count += 1

    if now - start_time > max_duration:
        send_discord("⏱️ GitHub Actions 타임아웃 임박. 릴레이를 위해 스크립트를 안전 종료합니다.", mode="log")
        break

    try:
        page.get(MAIN_URL)
        page.wait(1)

        # 1. 팝업 처리
        popup_btn = page.ele('text:오늘 하루 그만보기', timeout=1)
        if popup_btn:
            popup_btn.run_js(REACT_INJECT_JS)
            page.wait(0.5)

        available_seats_info = []

        # 2. 타겟 스케줄 순회
        for target in TARGET_PERFORMANCES:
            t_date = target['date']
            t_time = target['time']
            
            # 날짜 클릭 (React Inject)
            date_element = page.ele(f'@aria-label:{t_date}', timeout=1)
            if not date_element:
                continue
            date_element.run_js(REACT_INJECT_JS)
            page.wait(0.6)
            
            # 시간 클릭 (React Inject)
            time_list = page.ele('.product_time_list', timeout=1)
            if not time_list:
                continue
            time_element = time_list.ele(f'text:{t_time}', timeout=1)
            if not time_element:
                continue
            time_element.run_js(REACT_INJECT_JS)
            page.wait(0.6)
            
            # 좌석 확인
            seat_items = page.eles('.product_seat_item')
            for item in seat_items:
                seat_title = item.ele('.product_seat_title').text
                seat_num = item.ele('.product_seat_number').text
                
                # 매진이 아니면 배열에 추가
                if "매진" not in seat_num and "0" not in seat_num:
                    available_seats_info.append(f"[{t_date} {t_time}] {seat_title}: {seat_num}석")

        # 3. 결과 판별 및 디스코드 알림 (이전 상태와 비교 로직 적용)
        if available_seats_info:
            # 🔥 현재 발견된 좌석과 이전 루프의 좌석이 다를 때만 알림 전송
            # (set을 사용하여 순서에 상관없이 구성 요소만 정확히 일치하는지 판별)
            if set(available_seats_info) != set(previous_seats_info):
                seat_msg = "\n".join(available_seats_info)
                send_discord(f"🔔 @here 🚨🎉 상태 변동!\n{seat_msg}\n👉 {MAIN_URL}", mode="all")
            else:
                # 표는 있지만 이전과 수량/종류가 똑같다면 알림 스킵 (로그만 가끔 찍음)
                if loop_count % 10 == 0:
                    send_discord(f"-# {loop_count}회차 감시 중... 상태 유지 중", mode="log")
        else:
            # 매진일 때 (알림 X)
            if loop_count % 10 == 0:
                send_discord(f"-# {loop_count}회차 감시 중... 전부 매진", mode="log")

        # 다음 루프에서 비교하기 위해 현재 상태를 이전 상태로 덮어씌움
        previous_seats_info = available_seats_info.copy()

        # 서버 밴 방지를 위한 랜덤 대기 후 다음 루프 (새로고침)
        time.sleep(random.uniform(4.0, 8.0))

    except Exception as e:
        send_discord(f"⚠️ 루프 에러! 다음 루프로 넘어갑니다...\n{str(e)[:500]}", mode="log")
        time.sleep(random.uniform(10.0,30.0))

page.quit()
