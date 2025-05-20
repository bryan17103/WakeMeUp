from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os

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
    msg = event.message.text.strip()
    msg_lower = msg.lower()

    if msg_lower.startswith("天氣"):
        city = msg.replace("天氣", "").strip()
        reply = get_current_weather(city)

    elif msg_lower.startswith("路線"):
        inputs = msg[3:].strip().split(",")
        try:
            if len(inputs) == 2:
                origin, destination = inputs
                time = ""  # 空字串表示使用目前時間
                filtered = get_filtered_modes([])
            elif len(inputs) == 4:
                origin, destination, date_str, time_str = inputs
                time = f"{date_str},{time_str}"
                filtered = get_filtered_modes([])
            elif len(inputs) == 5:
                origin, destination, date_str, time_str, blocked = inputs
                time = f"{date_str},{time_str}"
                filtered = get_filtered_modes([blocked])
                else:
                    raise ValueError(f"你輸入了 {len(inputs)} 個欄位，格式應為：出發地,目的地[,日期,時間[,排除方式]]")
            if len(inputs) == 4:
                origin, destination, date_str, time_str = inputs
                time = f"{date_str},{time_str}"
                filtered = get_filtered_modes([])
            elif len(inputs) == 5:
                origin, destination, date_str, time_str, blocked = inputs
                time = f"{date_str},{time_str}"
                filtered = get_filtered_modes([blocked])
            else:
                raise ValueError(f"你輸入了 {len(inputs)} 個欄位，格式應為：出發地,目的地,日期,時間[,排除方式]")
            reply = add_trip_segment(origin.strip(), destination.strip(), time, filtered)
        except Exception as e:
            reply = f"⚠️ 請輸入格式正確的：路線 出發地,目的地,日期,時間（可加排除方式）\n錯誤詳情：{e}"

    elif msg_lower.startswith("班次"):
        try:
            _, city, route = msg.strip().split()
            reply = get_bus_estimates(city, route)
        except:
            reply = "⚠️ 請輸入格式正確的：班次 [城市] [公車路線]（例如：班次 Taipei 265）"

    elif msg_lower == "結束":
        reply = summarize_trip()

    elif "簡介" in msg_lower:
        reply = (
            "👥 第十組 WakeMeUp 🛏️\n"
            "個人化智慧通勤規劃 Line Bot\n\n"
            "💻 開發環境：Python 3.9.6\n\n"
            "📌 成員：\n"
            "藥學二　王瑋仁\n"
            "化工二　呂子毅\n"
            "藥學二　唐翊安\n"
            "工海一　張博彥"
        )

    elif "功能" in msg_lower:
        reply = (
            "目前支援的功能有：\n\n"
            "🌀 天氣查詢 ➤ 請輸入：\n"
            "　　天氣 【地點】\n"
            "　　例如：天氣 國立台灣大學\n\n"
            "🗺️ 行程規劃 ➤ 請輸入：\n"
            "　　路線 【出發地】,【目的地】\n"
            "　　或 路線 【出發地】,【目的地】,【日期】,【時間】\n"
            "　　例如：路線 台北車站,國父紀念館,2025-05-23,0800\n"
            "　　或加入欲排除交通方式：路線 台北車站,國父紀念館,2025-05-23,0800,開車\n\n"
            "🚍 班次查詢 ➤ 請輸入：\n"
            "　　班次 [城市] [公車路線]\n"
            "　　例如：班次 Taipei 265\n\n"
            "📚 功能查詢 ➤ 輸入：功能\n"
            "🧑🏻‍💻 開發者查詢 ➤ 輸入：簡介\n\n"
            "🪧 WakeMeUp 版本資訊：1.0"
        )

    elif "ib" in msg_lower:
        reply = "我是IB！"

    else:
        reply = "指令無法辨識，請輸入「功能」查詢支援功能！"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
