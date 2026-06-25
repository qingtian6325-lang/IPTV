import requests
import re

sources = {
    "guovin": "https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/ipv4/result.m3u",
    "my1": "https://iptv-org.github.io/iptv/countries/my.m3u",
    "sg1": "https://iptv-org.github.io/iptv/countries/sg.m3u",
    "my2": "https://epg.pw/test_channels_malaysia.m3u",
    "sg2": "https://epg.pw/test_channels_singapore.m3u"
}

result = ["#EXTM3U"]

for source, url in sources.items():
    try:
        print("Downloading:", url)

        response = requests.get(url, timeout=30)
        response.encoding = "utf-8"

        lines = response.text.splitlines()
        keep = False

        for line in lines:

            if line.startswith("#EXTINF"):

                # ===== Guovin：只保留央视频道 =====
                if source == "guovin":
                    if 'group-title="📺央视频道"' in line:
                        keep = True

                        line = re.sub(
                            r'group-title="[^"]*"',
                            'group-title="📺央视"',
                            line
                        )

                        result.append(line)
                    else:
                        keep = False

                # ===== Malaysia =====
                elif source in ["my1", "my2"]:
                    keep = True

                    if 'group-title=' in line:
                        line = re.sub(
                            r'group-title="[^"]*"',
                            'group-title="Malaysia"',
                            line
                        )
                    else:
                        line = line.replace(
                            "#EXTINF:-1",
                            '#EXTINF:-1 group-title="Malaysia"'
                        )

                    result.append(line)

                # ===== Singapore =====
                elif source in ["sg1", "sg2"]:
                    keep = True

                    if 'group-title=' in line:
                        line = re.sub(
                            r'group-title="[^"]*"',
                            'group-title="Singapore"',
                            line
                        )
                    else:
                        line = line.replace(
                            "#EXTINF:-1",
                            '#EXTINF:-1 group-title="Singapore"'
                        )

                    result.append(line)

            elif keep and line.startswith("http"):
                result.append(line)

    except Exception as e:
        print(e)

with open("mytv.m3u", "w", encoding="utf-8") as f:
    f.write("\n".join(result))

print("Done.")
