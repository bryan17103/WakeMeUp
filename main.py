from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from weather_route_modules import (
    get_current_weather,
    add_trip_segment,
    summarize_trip,
    get_bus_estimates,
    get_mrt_info,
    get_filtered_modes
)

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

user_states = {}  # 20250524 update : user state manage

@app.route("/", methods=["GET"])
def home():
    return "WakeMeUp LINE Bot is running!"

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(403)

    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip() #remove 1st blank
    msg_lower = msg.lower()
    user_id = event.source.user_id #one to one 

    global user_states 

    #keyword trigger
    
    if "天氣查詢" in msg_lower:
        user_states[user_id] = {"state": "awaiting_weather_location"}
        reply = "🌤️ 請輸入你想查詢天氣的地點！"

    elif "路線規劃" in msg_lower:
        user_states[user_id] = {"state": "awaiting_route_input"}
        reply = (
            "🗺️ 請按照以下格式查詢：\n\n"
            "出發地\n"
            "目的地\n"
            "日期（YYYY-MM-DD）\n"
            "出發時間（HHMM 或 HH:MM）\n"
            "排除方式（選填）\n\n"
            "目前支援的交通方式為：開車、走路、騎腳踏車、公車、大眾運輸（捷運、火車、高鐵）\n\n" #大眾運輸到底想怎樣
            "若不輸入日期與時間，則預設為當下時間。"
        )

    elif "公車查詢" in msg_lower:
        user_states[user_id] = {"state": "awaiting_bus_input"}
        reply = "🚍 請按照以下格式查詢：\n [城市] [路線]（例如：Taipei 265）"

    elif "簡介" in msg_lower:
        reply = (
            "👥 第十組 WakeMeUp 🛏️\n"
            "個人化智慧通勤規劃 Line Bot\n\n"
            "🔧 開發環境工具與環境\n"
            "語言：Python 3.9.6\n"
            "框架：Flask\n"
            "API 串接：OpenWeatherMap、Google Maps、TDX\n"
            "部署平台：Railway\n"
            "版本控制：GitHub\n"
            "外部整合：LINE Messaging API\n\n"
            "👨 成員\n"
            "藥學二　王瑋仁\n"
            "化工二　呂子毅\n"
            "藥學二　唐翊安\n"
            "工海一　張博彥"
        )

    elif "功能" in msg_lower:
        reply = (
            "目前支援的功能有：\n\n"
            "🌀 天氣查詢 ➤ 輸入：天氣查詢\n"
            "🗺️ 行程規劃 ➤ 輸入：路線規劃\n"
            "🚍 公車查詢 ➤ 輸入：公車查詢\n"
            "📚 功能查詢 ➤ 輸入：功能\n"
            "🧑🏻‍💻 開發者查詢 ➤ 輸入：簡介\n"
            "🪧 WakeMeUp 版本資訊：1.20"
        )

    elif "ib" in msg_lower:
        reply = "我是IB！"
        
    elif msg_lower == "403403403": #內部測試，check all user status
        if user_states:
            state_list = "\n".join([f"{uid} ➤ {info['state']}" for uid, info in user_states.items()])
            reply = f"目前使用者狀態如下：\n{state_list}"
        else:
            reply = "目前沒有任何使用者狀態紀錄。"

    #state check
    elif user_id in user_states:
        state_info = user_states[user_id]
        state = state_info["state"]

        if state == "awaiting_weather_location":
            reply = get_current_weather(msg)
            user_states.pop(user_id)

        elif state == "awaiting_route_input":
            if msg_lower == "結束":
                reply = summarize_trip()
                user_states.pop(user_id, None)
            else:
                try:
                    lines = [line.strip() for line in msg.splitlines() if line.strip() != ""]
                    if len(lines) not in [2, 3, 4, 5]:
                        raise ValueError("請輸入 2~5 行資訊：出發地、目的地、日期、時間與排除方式")

                    origin = lines[0]
                    destination = lines[1]

                    now = datetime.now(ZoneInfo("Asia/Taipei"))
                    time = now.strftime("%Y-%m-%d,%H:%M") #如果沒有輸入日期時間就當作是right now
                    filtered = get_filtered_modes([]) #這個是排除的交通方式

                    if len(lines) == 3:
                        filtered = get_filtered_modes([lines[2]])

                    elif len(lines) == 4:
                        date_str = lines[2]
                        time_str = lines[3]
                        time = f"{date_str},{time_str}"

                    elif len(lines) == 5:
                        date_str = lines[2]
                        time_str = lines[3]
                        time = f"{date_str},{time_str}"
                        filtered = get_filtered_modes([lines[4]])

                    reply = add_trip_segment(origin, destination, time, filtered)

                except Exception as e:
                    reply = f"⚠️ 輸入格式錯誤：請輸入正確的行程資料（每一項一行）\n錯誤詳情：{e}"

        elif state == "awaiting_bus_input":
            try:
                city, route = msg.strip().split()
                reply = get_bus_estimates(city, route)
                user_states.pop(user_id)
            except:
                reply = "⚠️ 請按照以下格式查詢：\n [城市] [路線]（例如：Taipei 265）"

        else:
            reply = "⚠️ 無法辨識的操作狀態，請重新輸入關鍵字"
            user_states.pop(user_id, None)

    else:
        reply = "指令無法辨識，請輸入「功能」查詢支援功能！"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

#dont touch
if __name__ == "__main__":
    user_states.clear()   # reset all user states on server start
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
