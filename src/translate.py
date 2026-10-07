import json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = '/tmp/opencode'
KEY = os.environ.get('DEEPSEEK_API_KEY', '')
URL = 'https://api.deepseek.com/chat/completions'
MODEL = 'deepseek-chat'
BATCH = int(os.environ.get('BATCH', '20'))
WORKERS = int(os.environ.get('WORKERS', '5'))
LIMIT = int(os.environ.get('LIMIT', '0'))  # 0 = all

SYS = (
    "你是德语到简体中文的专业翻译，正在处理歌德学院词汇表。"
    "对每个条目：1) 给出简洁准确的中文词义（名词带上性/复数含义可从词形判断；动词、形容词、副词给出对应词义）；"
    "2) 将每个德语例句翻译成自然通顺的简体中文。"
    "只输出 JSON，不要任何解释。格式严格为："
    "{\"items\":[{\"i\":<整数>,\"zh\":\"<词义>\",\"ex\":[\"<例句译文>\", ...]}]}"
    "，items 的顺序、i 的值、ex 数组的长度必须与输入完全一致。"
)

def call(payload_items, tries=5):
    body = json.dumps({
        'model': MODEL,
        'messages': [
            {'role': 'system', 'content': SYS},
            {'role': 'user', 'content': json.dumps({'items': payload_items}, ensure_ascii=False)},
        ],
        'temperature': 0,
        'response_format': {'type': 'json_object'},
    }).encode('utf-8')
    last = None
    for t in range(tries):
        try:
            req = urllib.request.Request(URL, data=body, headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + KEY,
            })
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read().decode('utf-8'))
            content = data['choices'][0]['message']['content']
            out = json.loads(content)
            return out.get('items', [])
        except Exception as e:
            last = e
            time.sleep(2 * (t + 1))
    raise RuntimeError('call failed: %r' % last)

def translate_file(src, dst):
    entries = json.load(open(os.path.join(BASE, src), encoding='utf-8'))
    done = {}
    if os.path.exists(os.path.join(BASE, dst)):
        try:
            done = json.load(open(os.path.join(BASE, dst), encoding='utf-8'))
        except Exception:
            done = {}
    todo = [i for i in range(len(entries)) if str(i) not in done]
    if LIMIT:
        todo = todo[:LIMIT]
    print('%s: total=%d done=%d todo=%d' % (src, len(entries), len(done), len(todo)))
    batches = []
    for k in range(0, len(todo), BATCH):
        idxs = todo[k:k + BATCH]
        payload = [{'i': i, 'de': entries[i]['de'], 'ex': entries[i]['ex']} for i in idxs]
        batches.append((idxs, payload))

    def work(b):
        idxs, payload = b
        items = call(payload)
        got = {it['i']: it for it in items if isinstance(it, dict) and 'i' in it}
        res = {}
        for i in idxs:
            it = got.get(i)
            if not it:
                raise RuntimeError('missing i=%d' % i)
            ex = it.get('ex') or []
            # normalize ex length
            ex = [str(x) for x in ex]
            if len(ex) != len(entries[i]['ex']):
                ex = (ex + [''] * len(entries[i]['ex']))[:len(entries[i]['ex'])]
            res[i] = {'zh': str(it.get('zh', '')).strip(), 'ex': ex}
        return res

    lock = __import__('threading').Lock()
    n = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex_:
        futs = {ex_.submit(work, b): b for b in batches}
        for f in as_completed(futs):
            try:
                res = f.result()
            except Exception as e:
                print('  batch failed:', e)
                continue
            with lock:
                for i, v in res.items():
                    done[str(i)] = v
                n += len(res)
                if n % (BATCH * 5) < BATCH:
                    json.dump(done, open(os.path.join(BASE, dst), 'w'), ensure_ascii=False)
                    print('  saved', len(done))
    json.dump(done, open(os.path.join(BASE, dst), 'w'), ensure_ascii=False)
    print('%s -> %s : %d/%d' % (src, dst, len(done), len(entries)))

if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if which in ('a2', 'all'):
        translate_file('a2.json', 'a2_zh.json')
    if which in ('b1', 'all'):
        translate_file('b1.json', 'b1_zh.json')
