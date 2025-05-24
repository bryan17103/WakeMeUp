import requests
from datetime import datetime, timedelta
from dateutil import parser
from zoneinfo import ZoneInfo
import googlemaps
import os

OPENWEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
TDX_CLIENT_ID = os.getenv("TDX_CLIENT_ID")
TDX_CLIENT_SECRET = os.getenv("TDX_CLIENT_SECRET")
GOOGLE_MAPS_API_KEY = os.getenv("MAPS_API_KEY")

gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
travel_plan = []
DEFAULT_RECOMMENDED_MODES = ["開車", "走路", "騎腳踏車", "公車", "大眾運輸（捷運、火車、高鐵）"]

def get_current_weather(city):
    city = city.replace("臺", "台")
    try:
        geocode_result = gmaps.geocode(city)
        if not geocode_result:
            return f"❌ 找不到與「{city}」對應的位置。"
        location = geocode_result[0]["geometry"]["location"]
        lat = location["lat"]
        lon = location["lng"]

        realtime_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&lang=zh_tw"
        forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&lang=zh_tw"

        real_res = requests.get(realtime_url)
        real_data = real_res.json()

        if real_res.status_code == 200:
            desc = real_data["weather"][0]["description"]
            temp = real_data["main"]["temp"]
            now_text = f"目前 {city} 的天氣為 {desc}，氣溫約 {temp}℃"
        else:
            now_text = f"目前天氣資料查詢失敗"

        fore_res = requests.get(forecast_url)
        if fore_res.status_code == 200:
            forecast_data = fore_res.json()
            now = datetime.now(ZoneInfo("Asia/Taipei"))
            near = min(
                forecast_data["list"],
                key=lambda f: abs(
                    datetime.strptime(f["dt_txt"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("Asia/Taipei")) - now
                )
            )
            pop = int(near.get("pop", 0) * 100)
            return f"{now_text}\n🌧️ 降雨機率：{pop}%（未來 3 小時內預測）"
        else:
            return now_text + "\n🌧️ 預報查詢失敗"

    except Exception as e:
        return f"發生錯誤，無法取得天氣資訊。({e})"

def get_weather_forecast(lat, lon, target_time):
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&lang=zh_tw"
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        nearest = min(
            data["list"],
            key=lambda f: abs(
                datetime.strptime(f["dt_txt"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("Asia/Taipei")) - target_time
            )
        )
        desc = nearest["weather"][0]["description"]
        pop = int(nearest.get("pop", 0) * 100)
        return desc, pop
    return "查無預報", 0

def parse_duration_to_minutes(duration_str):
    try:
        minutes = 0
        if "hour" in duration_str:
            parts = duration_str.split("hour")
            hr = int(parts[0].strip())
            minutes += hr * 60
            if "min" in parts[1]:
                min_str = parts[1].split("min")[0]
                minutes += int(min_str.strip())
        elif "min" in duration_str:
            minutes = int(duration_str.split("min")[0].strip())
        return minutes
    except:
        return float('inf')

def get_tdx_access_token():
    url = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": TDX_CLIENT_ID,
        "client_secret": TDX_CLIENT_SECRET
    }
    res = requests.post(url, headers=headers, data=data)
    return res.json()["access_token"] if res.status_code == 200 else ""

def get_bus_estimates(city, route_name):
    token = get_tdx_access_token()
    url = f"https://tdx.transportdata.tw/api/basic/v2/Bus/EstimatedTimeOfArrival/City/{city}/{route_name}?$top=100&$format=JSON"
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        data = res.json()
        output = []
        for stop in data:
            stop_name = stop['StopName']['Zh_tw']
            direction = "順向" if stop['Direction'] == 0 else "逆向"
            est = stop.get("EstimateTime")
            next_time = stop.get("NextBusTime")
            if est:
                mins = int(est / 60)
                output.append(f"🚌 {stop_name}（{direction}）：預估 {mins} 分鐘到站")
            elif next_time:
                dt = datetime.fromisoformat(next_time)
                output.append(f"🚌 {stop_name}（{direction}）：尚未發車，下一班預定 {dt.strftime('%H:%M')}")
            else:
                output.append(f"🚌 {stop_name}（{direction}）：查無即時資料")
        return "\n".join(output)
    else:
        return "⚠️ 查詢公車資料失敗"

def get_mrt_info(): #還沒處理好
    token = get_tdx_access_token()
    url = "https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/EstimatedTimeOfArrival/MetroTaipei?$top=100&$format=JSON"
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        data = res.json()
        output = []
        for item in data:
            station = item["StationName"]["Zh_tw"]
            dest = item["DestinationStationName"]["Zh_tw"]
            est = item.get("EstimateTime")
            direction = "順行" if item.get("Direction", 0) == 0 else "逆行"
            if est:
                mins = int(est / 60)
                output.append(f"🚇 {station} ➜ {dest}（{direction}）：約 {mins} 分鐘抵達")
        return "\n".join(output) if output else "🚇 目前無捷運即時資料"
    else:
        return "⚠️ 查詢捷運資料失敗"

def get_filtered_modes(blocked_modes):
    return [mode for mode in DEFAULT_RECOMMENDED_MODES if mode not in blocked_modes]

def add_trip_segment(start, end, time_str, allowed_modes):
    try:
        if not time_str:
            departure_time = datetime.now(ZoneInfo("Asia/Taipei"))
        elif "," in time_str:
            date_part, time_part = [x.strip() for x in time_str.split(",")]
            departure_time = parser.parse(f"{date_part} {time_part}").replace(tzinfo=ZoneInfo("Asia/Taipei"))
        else:
            departure_time = parser.parse(time_str if ":" in time_str else f"{time_str[:2]}:{time_str[2:]}").replace(tzinfo=ZoneInfo("Asia/Taipei"))
    except Exception as e:
        return f"⚠️ 時間格式錯誤：{e}"

    geo = gmaps.geocode(end)
    lat, lon = geo[0]['geometry']['location'].values() if geo else (25.0478, 121.5319)
    weather, rain_prob = get_weather_forecast(lat, lon, departure_time)

    route_info = {}
    mode_map = {'driving': '開車', 'walking': '走路', 'bicycling': '騎腳踏車', 'transit': '大眾運輸（綜合）', 'bus': '公車', 'subway': '大眾運輸（捷運、火車、高鐵）'}

    for mode in ['driving', 'walking', 'bicycling', 'transit']:
        try:
            result = gmaps.directions(start, end, mode=mode, departure_time=departure_time)
            if result:
                leg = result[0]['legs'][0]
                dur = leg['duration']['text']
                val = leg['duration']['value']
                arr = (departure_time + timedelta(seconds=val)).strftime("%H:%M")
                route_info[mode_map[mode]] = (dur, arr)
        except:
            route_info[mode_map[mode]] = ("查詢失敗", "-")

    for tmode in ['bus', 'subway']:
        try:
            result = gmaps.directions(start, end, mode='transit', transit_mode=tmode, departure_time=departure_time)
            if result:
                leg = result[0]['legs'][0]
                dur = leg['duration']['text']
                val = leg['duration']['value']
                arr = (departure_time + timedelta(seconds=val)).strftime("%H:%M")
                route_info[mode_map[tmode]] = (dur, arr)
        except:
            route_info[mode_map[tmode]] = ("查詢失敗", "-")

    not_recommended = ["騎腳踏車"] if rain_prob >= 30 else []

    best_label = None
    best_time = float('inf')
    for label in route_info:
        if label not in allowed_modes or label in not_recommended:
            continue
        duration_str, arrival = route_info.get(label, (None, "-"))
        if duration_str and duration_str not in ["查無結果", "查詢失敗"]:
            mins = parse_duration_to_minutes(duration_str)
            if mins < best_time:
                best_time = mins
                best_label = label

    actual_arrival = route_info.get(best_label, (None, "-"))[1]

    travel_plan.append({
        "from": start,
        "to": end,
        "depart": departure_time.strftime("%Y-%m-%d %H:%M"),
        "mode": best_label,
        "arrival": actual_arrival,
        "weather": weather,
        "rain": rain_prob
    })

    if not best_label:
        return f"⚠️ 無法找到合適的交通方式從【{start}】到【{end}】，請嘗試更換時間或不要排除太多交通方式。"

    return (
        f"✅ 已新增路線：\n"
        f"📍 出發：{start} ➜ 抵達：{end}\n"
        f"🕒 出發時間：{departure_time.strftime('%Y-%m-%d %H:%M')}\n"
        f"🚗 推薦交通方式：{best_label}\n"
        f"⏱️ 預計抵達時間：{actual_arrival}\n"
        f"☁️ 預報天氣：{weather}，降雨機率：{rain_prob}% \n"
        f"📦 若有接下來的行程規劃，請繼續輸入，否則請輸入「結束」以查看規劃統整。"
    )

def summarize_trip():
    if not travel_plan:
        return "⚠️ 尚未新增任何行程段落。"

    output = ["📋 你的行程規劃如下："]
    for i, seg in enumerate(travel_plan):
        output.append(
            f"\n🚩 第 {i+1} 段：{seg['from']} ➜ {seg['to']}\n"
            f"🕒 出發時間：{seg['depart']}\n"
            f"🚗 交通方式：{seg['mode']}\n"
            f"⏱️ 預計抵達：{seg['arrival']}\n"
            f"☁️ 天氣：{seg['weather']}｜🌧️ 降雨機率：{seg['rain']}%"
        )

    try:
        first_depart_str = travel_plan[0]["depart"] 
        depart_time = datetime.strptime(first_depart_str, "%Y-%m-%d %H:%M")
        wake_time = depart_time - timedelta(hours=1)

        sleep_options = [] 
        for hrs in [9 , 7.5 , 6 , 4.5]: #睡眠週期=3-6個90min；該睡=起床-週期-15min緩衝
            sleep_time = wake_time - timedelta(minutes=int(hrs * 60 + 15))
            sleep_options.append(f"　- {sleep_time.strftime('%H:%M')}（{hrs} 小時）")

        output.append(
            f"\n😴 根據你的第一段出發時間（{depart_time.strftime('%H:%M')}），"
            f"你應於 {wake_time.strftime('%H:%M')} 起床（預留 1 小時準備）。\n"
            "🛏️ 建議你在以下時間入睡（含 15 分鐘入睡緩衝）：\n" + "\n".join(sleep_options)
        )

    except Exception as e:
        output.append(f"\n⚠️ 起床與睡眠推算失敗：{e}")
    result = "\n".join(output)
    travel_plan.clear()  # 清空行程紀錄
    return result
