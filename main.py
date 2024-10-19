import sys

import requests
import re
import json
import time
import os
import random
import subprocess
from urllib.parse import urlparse, urlunparse
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

from CookieUtil import CookieUtil


def get_file_content(file_path):
    file_content = ''
    with open(file_path, 'r') as file:
        file_content = file.read()
    return file_content.strip()


def get_douyin_live_data_from_pc(user_agent, pc_live_url, cookie_content):
    headers = {
        'referer': "https://live.douyin.com/",
        'User-Agent': user_agent,
        'Cookie': cookie_content,
    }

    response = requests.get(pc_live_url, headers=headers)
    html_str = response.text

    soup = BeautifulSoup(html_str, 'html.parser')
    scripts = soup.find_all('script')

    json_data = {}
    for script in scripts:
        target_str = script.string
        if target_str is not None and "roomStore" in target_str:
            new_string = target_str.replace('\\"', '"').replace('\\"', '"')
            new_string = re.sub(r'self\.__pace_f\.push\(\[.*?null,', '', new_string)
            new_string = new_string.replace(']\\n"])', "").strip()
            jsonObj = json.loads(new_string)

            if (('state' not in jsonObj) or
                    ('roomStore' not in jsonObj['state']) or
                    ('roomInfo' not in jsonObj['state']['roomStore']) or
                    'room' not in jsonObj['state']['roomStore']['roomInfo'] or
                    'status' not in jsonObj['state']['roomStore']['roomInfo']['room']):
                continue

            live_status = jsonObj['state']['roomStore']['roomInfo']['room']['status']
            if live_status == 4:
                json_data['status'] = live_status
                print("直播已结束")
                break

            origin_url_list = jsonObj['state']['streamStore']['streamData']['H264_streamData']['stream']['origin']['main']

            origin_m3u8 = {'ORIGIN': origin_url_list["hls"]}
            origin_flv = {'ORIGIN': origin_url_list["flv"]}

            hls_pull_url_map = jsonObj['state']['roomStore']['roomInfo']['room']['stream_url']['hls_pull_url_map']
            flv_pull_url_map = jsonObj['state']['roomStore']['roomInfo']['room']['stream_url']['flv_pull_url']

            json_data['hls_pull_url_map'] = {**origin_m3u8, **hls_pull_url_map}
            json_data['flv_pull_url_map'] = {**origin_flv, **flv_pull_url_map}

            json_data['status'] = live_status
            json_data['user_count'] = jsonObj['state']['roomStore']['roomInfo']['room']['user_count_str']
            json_data['nick_name'] = jsonObj['state']['roomStore']['roomInfo']['room']['owner']['nickname']
            json_data['room_title'] = jsonObj['state']['roomStore']['roomInfo']['room']['title']

            json_data['nick_avatar'] = jsonObj['state']['roomStore']['roomInfo']['room']['cover']['url_list'][0]

            break

    return json_data


def get_sec_user_id(url):
    response = requests.get(url, allow_redirects=False, timeout=15)
    response_content = response.text.strip()
    if response_content.endswith('.'):
        response_content = response_content.rstrip('.')

    soup = BeautifulSoup(response_content, 'html.parser')
    a_tags = soup.find_all('a', href=True)
    href = a_tags[0]['href']
    parsed_url = urlparse(href)
    uri = parsed_url.path
    query_params = parse_qs(parsed_url.query)
    reflow_id = os.path.basename(uri)
    sec_user_id = query_params['iid'][0]
    return reflow_id, sec_user_id


def get_ttwid(user_agent):
    headers = {
        "User-Agent": user_agent,
        "Content-Type": "application/json"
    }
    request_url = "https://ttwid.bytedance.com/ttwid/union/register/"

    data = {
        "aid": 2906,
        "service": "douyin.com",
        "unionHost": "https://ttwid.bytedance.com",
        "needFid": "false",
        "union": "true",
        "fid": ""
    }

    data_str = json.dumps(data)
    response = requests.post(request_url, data=data_str, headers=headers)

    jsonObj = json.loads(response.text)
    callback_url = jsonObj['redirect_url']
    response = requests.get(callback_url, headers=headers)
    status_code = response.status_code
    if status_code == 200 and 'Set-Cookie' in response.headers:
        cookie_dict = CookieUtil.cookies_from_headers(response.cookies)
        if "ttwid" in cookie_dict:
            return cookie_dict['ttwid']
    return None


def get_web_id(user_agent):
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Referer': 'https://www.douyin.com/',
        'User-Agent': user_agent
    }

    app_id = 6383
    body = {
        "app_id": app_id,
        "referer": 'https://www.douyin.com/',
        "url": 'https://www.douyin.com/',
        "user_agent": user_agent,
        "user_unique_id": ''
    }

    request_url = f"https://mcs.zijieapi.com/webid?aid={app_id}&sdk_version=5.1.18_zip&device_platform=web"
    response = requests.post(request_url, headers=headers, data=json.dumps(body))
    jsonObj = json.loads(response.text)
    return jsonObj['web_id']


def get_ms_token(randomlength=107):
    random_str = ''
    base_str = 'ABCDEFGHIGKLMNOPQRSTUVWXYZabcdefghigklmnopqrstuvwxyz0123456789='
    length = len(base_str) - 1
    for _ in range(randomlength):
        random_str += base_str[random.randint(0, length)]
    return random_str


def get_ac_nonce(user_agent, url):
    headers = {
        'user-agent': user_agent
    }
    __ac_nonce = requests.get(url, headers=headers).cookies.get('__ac_nonce')
    print(__ac_nonce)
    return __ac_nonce

def big_count_operation(string, final_num):
    for char in string:
        char_code_count = ord(char)
        final_num = ((final_num ^ char_code_count) * 65599) & 0xFFFFFFFF  # Use & to simulate the behavior of >>> 0
    return final_num

def count_to_text(deci_num, ac_signature):
    off_list = [24, 18, 12, 6, 0]
    for value in off_list:
        key_num = (deci_num >> value) & 63
        if key_num < 26:
            val_num = 65
        elif key_num < 52:
            val_num = 71
        elif key_num < 62:
            val_num = -4
        else:
            val_num = -17
        ascii_code = key_num + val_num
        ac_signature += chr(ascii_code)
    return ac_signature

def load_ac_signature(url, ac_nonce, ua):
    final_num = 0
    temp = 0
    ac_signature = "_02B4Z6wo00f01"
    # Get the current timestamp
    time_stamp = str(int(time.time() * 1000))

    # Perform big count operation on timestamp
    final_num = big_count_operation(time_stamp, final_num)

    # Perform big count operation on the URL
    url_num = big_count_operation(url, final_num)
    final_num = url_num

    # Create a 32-bit binary string from a combination of operations
    long_str = bin(((65521 * (final_num % 65521) ^ int(time_stamp)) & 0xFFFFFFFF))[2:]
    while len(long_str) != 32:
        long_str = "0" + long_str

    # Create a binary number and parse it into decimal
    binary_num = "10000000110000" + long_str
    deci_num = int(binary_num, 2)

    # Perform countToText operations
    ac_signature = count_to_text(deci_num >> 2, ac_signature)
    ac_signature = count_to_text((deci_num << 28) | 515, ac_signature)
    ac_signature = count_to_text((deci_num ^ 1489154074) >> 6, ac_signature)

    # Perform operation for the 'aloneNum'
    alone_num = (deci_num ^ 1489154074) & 63
    alone_val = 65 if alone_num < 26 else 71 if alone_num < 52 else -4 if alone_num < 62 else -17
    ac_signature += chr(alone_num + alone_val)

    # Reset final_num and perform additional operations
    final_num = 0
    deci_opera_num = big_count_operation(str(deci_num), final_num)
    final_num = deci_opera_num
    nonce_num = big_count_operation(ac_nonce, final_num)
    final_num = deci_opera_num
    big_count_operation(ua, final_num)

    # More countToText operations
    ac_signature = count_to_text((nonce_num % 65521 | ((final_num % 65521) << 16)) >> 2, ac_signature)
    ac_signature = count_to_text((((final_num % 65521 << 16) ^ (nonce_num % 65521)) << 28) | (((deci_num << 524576) ^ 524576) >> 4), ac_signature)
    ac_signature = count_to_text(url_num % 65521, ac_signature)

    # Final temp operations and appending to ac_signature
    for i in ac_signature:
        temp = ((temp * 65599) + ord(i)) & 0xFFFFFFFF

    last_str = hex(temp)[2:]
    ac_signature += last_str[-2:]

    return ac_signature

def get_douyin_live_room_id(user_agent, mobile_live_url):
    reflow_id, sec_user_id = get_sec_user_id(mobile_live_url)

    ttwid = get_ttwid(user_agent)
    web_id = get_web_id(user_agent)

    cookie_content = f"ttwid={ttwid};webid={web_id}"
    headers = {
        'User-Agent': user_agent,
        'Host': "webcast.amemv.com",
        'Cookie': cookie_content
    }
    request_url = f"https://webcast.amemv.com/douyin/webcast/reflow/{reflow_id}"
    response = requests.get(request_url, headers=headers, allow_redirects=True, timeout=15)
    html_str = response.text
    soup = BeautifulSoup(html_str, 'html.parser')
    scripts = soup.find_all('script')

    for script in scripts:
        target_str = script.string
        if target_str is not None and "webRid" in target_str:
            new_string = target_str.replace('\\"', '"').replace('\\"', '"')
            new_string = re.sub(r'self\.__rsc_f\.push\(\[.*?null,', '', new_string)
            new_string = new_string.replace(']\\n"])', "").strip()
            jsonObj = json.loads(new_string)
            return jsonObj['data']['room']['owner']['webRid']
    return None


def get_douyin_live_stream_url(json_data, video_quality):
    anchor_name = json_data.get('anchor_name', None)

    result = {
        "anchor_name": anchor_name,
        "is_live": False,
    }

    status = json_data.get("status", 4)  # 直播状态 2 是正在直播、4 是未开播

    if status == 2:
        flv_url_dict = json_data['flv_pull_url_map']
        flv_url_list = list(flv_url_dict.values())
        m3u8_url_dict = json_data['hls_pull_url_map']
        m3u8_url_list = list(m3u8_url_dict.values())

        while len(flv_url_list) < 5:
            flv_url_list.append(flv_url_list[-1])
            m3u8_url_list.append(m3u8_url_list[-1])

        video_qualities = {"原画": 0, "蓝光": 0, "超清": 1, "高清": 2, "标清": 3, "流畅": 4}
        quality_index = video_qualities.get(video_quality)
        m3u8_url = m3u8_url_list[quality_index]
        flv_url = flv_url_list[quality_index]
        result['m3u8_url'] = m3u8_url
        result['flv_url'] = flv_url
        result['is_live'] = True
        result['record_url'] = m3u8_url
    return result


def save_video_slice(user_agent, stream_data):
    if 'record_url' not in stream_data:
        print("直播已结束")
        return
    real_url = stream_data['record_url']
    anchor_name = stream_data['anchor_name']

    analyzeduration = "20000000"
    probesize = "10000000"
    bufsize = "8000k"
    max_muxing_queue_size = "1024"

    ffmpeg_command = [
        'ffmpeg', "-y",
        "-v", "verbose",
        "-rw_timeout", "30000000",
        "-loglevel", "error",
        "-hide_banner",
        "-user_agent", user_agent,
        "-protocol_whitelist", "rtmp,crypto,file,http,https,tcp,tls,udp,rtp",
        "-thread_queue_size", "1024",
        "-analyzeduration", analyzeduration,
        "-probesize", probesize,
        "-fflags", "+discardcorrupt",
        "-i", real_url,
        "-bufsize", bufsize,
        "-sn", "-dn",
        "-reconnect_delay_max", "60",
        "-reconnect_streamed", "-reconnect_at_eof",
        "-max_muxing_queue_size", max_muxing_queue_size,
        "-correct_ts_overflow", "1",
    ]

    now = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
    save_file_path = f"{now}_%03d.mp4"
    command = [
        "-c:v", "copy",
        "-c:a", "aac",
        "-map", "0",
        "-f", "segment",
        "-segment_time", "20",
        "-segment_time_delta", "0.01",
        "-segment_format", "mp4",
        "-reset_timestamps", "1",
        "-pix_fmt", "yuv420p",
        save_file_path,
    ]

    ffmpeg_command.extend(command)
    print("开始拉取数据流...")

    result = ' '.join(ffmpeg_command)
    print("result: \n", result)
    _output = subprocess.check_output(ffmpeg_command, stderr=subprocess.STDOUT)
    # 以下代码理论上不会执行
    print(_output)


if __name__ == '__main__':
    url = input("直播的分享链接地址: ")
    parsed_url = urlparse(url)
    # 移除查询参数
    url_without_query = urlunparse(parsed_url._replace(query=""))

    user_agent = "这里替换成您的user-agent"
    
    if url_without_query.startswith("https://v.douyin.com/"):
        room_id = None
        try_times = 0
        while True:
            room_id = get_douyin_live_room_id(user_agent, url_without_query)
            if room_id is not None:
                break
            time.sleep(1)
            try_times += 1
            if try_times > 10:
                print("获取直播间ID失败")
                sys.exit(-1)
        print("room_id: ", room_id)
        url_without_query = f"https://live.douyin.com/{room_id}"

    ac_nonce = get_ac_nonce(user_agent, url_without_query)
    ac_signature = load_ac_signature(url_without_query, ac_nonce, user_agent)

    # 此cookie有效期只有30分钟
    cookie_content = f"__ac_nonce={ac_nonce}; __ac_signature={ac_signature}; ; __ac_referer=__ac_blank"

    live_data = get_douyin_live_data_from_pc(user_agent, url_without_query, cookie_content)

    print("live_data:")
    print(json.dumps(live_data, indent=4, ensure_ascii=False))

    if live_data['status'] == 4:
        # 直播已结束，直接退出
        sys.exit(-1)

    # 获取直播流并保存到本地目录
    stream_urls = get_douyin_live_stream_url(live_data, "原画")
    save_video_slice(user_agent, stream_urls)
