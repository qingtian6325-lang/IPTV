import requests
import re
import concurrent.futures

# ================= 配置区 =================
TIMEOUT = 10          # 每个链接的超时时间（秒），越短过滤越严格
MAX_WORKERS = 20     # 多线程数量（并发数），数值越大检测越快，但不要设置过高以免被服务器拉黑
OUTPUT_FILE = "mytv.m3u"

sources = {
    "guovin": "https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/ipv4/result.m3u",
    "my1": "https://iptv-org.github.io/iptv/countries/my.m3u",
    "sg1": "https://iptv-org.github.io/iptv/countries/sg.m3u",
    "my2": "https://epg.pw/test_channels_malaysia.m3u",
    "sg2": "https://epg.pw/test_channels_singapore.m3u",
    "backup1": "https://cdn.qd.je/live.m3u",
    "backup2": "https://php.946985.filegear-sg.me/jackTV.m3u"
}
# ==========================================

def check_url(channel_data):
    """
    🔥 核心过滤器：多线程检测 URL 是否存活
    """
    extinf, url = channel_data
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        # stream=True 避免下载视频流，只需拿到响应头即可判断存活
        response = requests.get(url, stream=True, timeout=TIMEOUT, headers=headers)
        if response.status_code < 400:
            response.close()
            print(f"[可用] {url}")
            return (extinf, url, True)
        else:
            print(f"[失效-状态码异常] {url}")
            return (extinf, url, False)
    except requests.RequestException:
        print(f"[失效-超时或无法访问] {url}")
        return (extinf, url, False)

def main():
    raw_channels = [] # 暂存所有提取到的频道 (extinf, url)
    
    # 1. 抓取并解析所有源
    for source, url in sources.items():
        try:
            print(f"\n正在拉取数据源: {url}")
            response = requests.get(url, timeout=30)
            response.encoding = "utf-8"
            lines = response.text.splitlines()
            
            keep = False
            current_extinf = ""

            for line in lines:
                if line.startswith("#EXTINF"):
                    # ===== Guovin：只保留央视频道 =====
                    if source == "guovin":
                        if 'group-title="📺央视频道"' in line:
                            keep = True
                            current_extinf = re.sub(r'group-title="[^"]*"', 'group-title="📺央视"', line)
                        else:
                            keep = False

                    # ===== Malaysia =====
                    elif source in ["my1", "my2"]:
                        keep = True
                        if 'group-title=' in line:
                            current_extinf = re.sub(r'group-title="[^"]*"', 'group-title="Malaysia"', line)
                        else:
                            current_extinf = line.replace("#EXTINF:-1", '#EXTINF:-1 group-title="Malaysia"')

                    # ===== Singapore =====
                    elif source in ["sg1", "sg2"]:
                        keep = True
                        if 'group-title=' in line:
                            current_extinf = re.sub(r'group-title="[^"]*"', 'group-title="Singapore"', line)
                        else:
                            current_extinf = line.replace("#EXTINF:-1", '#EXTINF:-1 group-title="Singapore"')
                            
                    # ===== Backup =====
                    elif source in ["backup1", "backup2"]:
                        keep = True
                        if 'group-title=' in line:
                            current_extinf = re.sub(r'group-title="[^"]*"', 'group-title="backup"', line)
                        else:
                            current_extinf = line.replace("#EXTINF:-1", '#EXTINF:-1 group-title="backup"')

                elif keep and line.startswith("http"):
                    # 抓取到完整信息，暂存到列表中准备并发测试
                    raw_channels.append((current_extinf, line))

        except Exception as e:
            print(f"处理源 {source} 时出错: {e}")

    print(f"\n✅ 数据源解析完成，共提取到 {len(raw_channels)} 个频道。")
    print("🔥 开始执行多线程死链过滤，这可能需要一点时间...\n")

    # 2. 多线程并发过滤死链
    valid_results = ["#EXTM3U"]
    
    # 使用线程池并发执行检测
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # executor.map 会按原顺序返回结果
        results = executor.map(check_url, raw_channels)
        
        for extinf, url, is_valid in results:
            if is_valid:
                valid_results.append(extinf)
                valid_results.append(url)

    # 3. 写入最终可用文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(valid_results))

    print(f"\n🎉 过滤完毕！已自动剔除死链。生成的可用频道已保存到 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
