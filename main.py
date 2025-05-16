from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import requests

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
weather_api_key = os.getenv("WEATHER_API_KEY")
maps_api_key = os.getenv("MAPS_API_KEY")

CITY_MAP = {
    "台北": "Taipei", "臺北": "Taipei",
    "台中": "Taichung", "臺中": "Taichung",
    "高雄": "Kaohsiung", "臺南": "Tainan",
    "台南": "Tainan", "台東": "Taitung",
    "臺東": "Taitung", "花蓮": "Hualien",
    "基隆": "Keelung", "新竹": "Hsinchu"
}

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
    msg = event.message.text.strip().lower()

    if msg.startswith("天氣 "):
        city_raw = msg[3:].strip()
        city = CITY_MAP.get(city_raw, city_raw)
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={weather_api_key}&units=metric&lang=zh_tw"
        try:
            response = requests.get(url)
            data = response.json()
            if response.status_code == 200:
                weather = data["weather"][0]["description"]
                temp = data["main"]["temp"]
                reply = f"{city.title()} 的天氣是 {weather}，氣溫約 {temp}°C。"
            else:
                reply = f"查無「{city_raw}」的天氣資料，請確認地名拼寫正確。"
        except Exception as e:
            reply = "發生錯誤，無法取得天氣資訊。"
            print("Weather API Error:", e)

    elif msg.startswith("路線 ") or msg == "路線":
        inputs = msg[3:].strip().split(",")
        if len(inputs) != 3:
            reply = "請輸入格式正確的內容：出發地,目的地,出發時間（例如：台北,高雄,08:00）"
        else:
            origin_raw, destination_raw, departure_time = inputs
            origin = CITY_MAP.get(origin_raw.strip(), origin_raw.strip())
            destination = CITY_MAP.get(destination_raw.strip(), destination_raw.strip())
            url = (
                f"https://maps.googleapis.com/maps/api/directions/json?"
                f"origin={origin}&destination={destination}&departure_time=now&key={maps_api_key}&language=zh-TW"
            )
            try:
                response = requests.get(url)
                data = response.json()
                if response.status_code == 200 and data["status"] == "OK":
                    route = data["routes"][0]["legs"][0]
                    distance = route["distance"]["text"]
                    duration = route["duration"]["text"]
                    reply = f"從 {origin} 到 {destination} 的距離是 {distance}，預計需要 {duration}。"
                else:
                    reply = f"無法取得路線資訊，請確認地點拼寫正確。\nAPI 回應: {data.get('status')}"
                    print("Route API Response:", data)
            except Exception as e:
                reply = "發生錯誤，無法查詢路線資訊。"
                print("Route API Error:", e)

    elif "簡介" in msg:
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

    elif "功能" in msg:
        reply = (
            "目前支援的功能有：\n\n"
            "🌀 天氣查詢 ➤ 請輸入：\n"
            "　　天氣 【地點】\n"
            "　　例如：天氣 台北\n\n"
            "🗺️ 路線查詢 ➤ 請輸入：\n"
            "　　路線 【出發地】,【目的地】,【時間】\n"
            "　　例如：路線 台北,高雄,08:00\n\n"
            "📚 功能查詢 ➤ 輸入：\n"
            "　　功能\n\n"
            "🧑🏻‍💻 開發者查詢 ➤ 輸入：\n"
            "　　簡介\n\n"
            "🔁 其他訊息 ➤ 原樣回覆"
        )

    elif "ib" in msg:
        reply = "我是IB！"

    else:
        reply = event.message.text

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
