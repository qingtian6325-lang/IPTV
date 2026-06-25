import requests

sources = [
    "https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/ipv4/result.m3u",
    "https://iptv-org.github.io/iptv/countries/my.m3u",
    "https://iptv-org.github.io/iptv/countries/sg.m3u",
    "https://epg.pw/test_channels_malaysia.m3u",
    "https://epg.pw/test_channels_singapore.m3u"
]

result = ["#EXTM3U"]

for url in sources:
    try:
        print("Downloading:", url)

        response = requests.get(url, timeout=30)
        response.encoding = "utf-8"
        lines = response.text.splitlines()

        keep = False

        for line in lines:

            # Guovin：只保留 📺央视频道
            if url.startswith(
                "https://raw.githubusercontent.com/Guovin"
            ):

                if line.startswith("#EXTINF"):
                    if 'group-title="📺央视频道"' in line:
                        keep = True
                        result.append(line)
                    else:
                        keep = False

                elif keep and line.startswith("http"):
                    result.append(line)

            # 其他 4 个来源：全部保留
            else:
                result.append(line)

    except Exception as e:
        print("Error:", e)

with open("mytv.m3u", "w", encoding="utf-8") as f:
    f.write("\n".join(result))

print("Done!")
