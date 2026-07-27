import concurrent.futures
import re
import requests

# ================= 配置区 =================
TIMEOUT = 3  # 每个播放链接的死链检测超时时间（秒）
MAX_WORKERS = 35  # 检测并发数
OUTPUT_FILE = "mytv.m3u"

# 数据源配置列表（包含 jackTV、juli、体育台、Mytv）
SOURCES = [
    {
        "name": "jackTV",
        "url": "https://iptv.aibo.lol/list.m3u",
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    },
    {
        "name": "juli",
        "url": "https://files.catbox.moe/h3mb5a.txt",
        "ua": "okhttp/5.3.2",
    },
    {
        "name": "体育台",
        "url": "http://82.156.243.185:33389/fwc.m3u",
        "ua": "okhttp",
    },
    {
        "name": "Mytv",
        "url": "https://cdn.qd.je/live.m3u",
        "ua": "okhttp",
    },
]
# ==========================================


def format_group_title(line, prefix):
    """根据传入的源名称 (prefix)，将分类统一修改为 'prefix-分类名'（例如: Mytv-央视 / juli-台湾频道）"""
    # 1. 如果原标签中已有 group-title="..."
    match = re.search(r'group-title="([^"]*)"', line)
    if match:
        original_group = match.group(1).strip()
        # 清理开头的特殊符号或图标
        clean_group = re.sub(r"^[^\w\u4e00-\u9fa5]+", "", original_group)

        # 剔除可能存在的旧前缀，重新拼上新的 prefix
        clean_group = re.sub(r"^(jackTV|juli|jack|体育台|Mytv)-", "", clean_group)
        new_group = f"{prefix}-{clean_group}" if clean_group else f"{prefix}-其他"

        return re.sub(r'group-title="[^"]*"', f'group-title="{new_group}"', line)

    # 2. 如果没有 group-title，根据频道名称关键字智能识别
    category = "其他"
    upper_line = line.upper()

    if any(kw in upper_line for kw in ["体育", "CCTV5", "五星", "足球", "NBA", "CCTV5+"]):
        category = "体育频道"
    elif "CCTV" in upper_line or "央视" in upper_line:
        category = "央视"
    elif "卫视" in upper_line:
        category = "卫视"
    elif any(kw in upper_line for kw in ["台湾", "台", "中视", "华视", "民视", "东森", "TVBS"]):
        category = "台湾频道"
    elif any(kw in upper_line for kw in ["TVB", "翡翠", "凤凰", "HBO", "港", "澳门"]):
        category = "港澳"
    elif any(kw in upper_line for kw in ["动画", "少儿", "卡通", "迪士尼"]):
        category = "少儿"
    elif any(kw in upper_line for kw in ["电影", "影院", "剧场"]):
        category = "影视"

    full_category = f"{prefix}-{category}"

    if "#EXTINF:-1" in line:
        return line.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{full_category}"')
    else:
        return f'#EXTINF:-1 group-title="{full_category}",{line}'


def check_url(channel_data):
    """多线程检测播放链接是否有效"""
    extinf, url = channel_data
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
    }
    try:
        response = requests.get(
            url, stream=True, timeout=TIMEOUT, headers=headers
        )
        if response.status_code < 400:
            response.close()
            print(f"[可用] {url}")
            return (extinf, url, True)
        else:
            print(f"[失效-状态码 {response.status_code}] {url}")
            return (extinf, url, False)
    except requests.RequestException:
        print(f"[失效-超时/无法访问] {url}")
        return (extinf, url, False)


def main():
    raw_channels = []

    # 1. 遍历所有配置的数据源
    for src in SOURCES:
        name = src["name"]  # 数据源名称
        url = src["url"]
        ua = src.get("ua", "Mozilla/5.0")

        print(f"\n正在拉取源 [{name}]: {url}")
        headers = {"User-Agent": ua}

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = "utf-8"
            lines = response.text.splitlines()

            current_extinf = ""

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # 标准 M3U 格式解析
                if line.startswith("#EXTINF"):
                    current_extinf = format_group_title(line, prefix=name)
                elif line.startswith("http") and current_extinf:
                    raw_channels.append((current_extinf, line))
                    current_extinf = ""

                # 兼容 TXT 格式 (例如: 频道名称,http://...)
                elif "," in line and line.startswith("http"):
                    parts = line.split(",", 1)
                    title = parts[0]
                    stream_url = parts[1]
                    extinf = format_group_title(f"#EXTINF:-1,{title}", prefix=name)
                    raw_channels.append((extinf, stream_url))

        except Exception as e:
            print(f"❌ 抓取数据源 [{name}] 失败: {e}")

    print(f"\n✅ 数据源拉取完成，共提取到 {len(raw_channels)} 个潜在频道。")
    print("🔥 开始执行死链检测...\n")

    # 2. 多线程检测死链
    valid_results = ["#EXTM3U"]

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:
        results = executor.map(check_url, raw_channels)

        for extinf, url, is_valid in results:
            if is_valid:
                valid_results.append(extinf)
                valid_results.append(url)

    # 3. 导出 M3U
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(valid_results))

    print(
        f"\n🎉 处理完毕！已生成分类清晰的 M3U 播放列表: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
