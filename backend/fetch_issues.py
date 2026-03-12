import urllib.request
import json
req = urllib.request.Request('https://api.github.com/search/issues?q=repo:open-webui/open-webui+"blank+page"+windows', headers={'User-Agent': 'Mozilla/5.0'})
try:
    data = json.loads(urllib.request.urlopen(req).read())
    for i in data['items'][:5]:
        print(f"{i['title']} - {i['html_url']}")
except Exception as e:
    print(e)
