import json, re, sys
sys.path.insert(0, '/tmp/opencode')
from forms_data import FORMS

BASE = '/tmp/opencode'
def load(n): return json.load(open(BASE + '/' + n, encoding='utf-8'))

def split_ex(de, zh):
    d = re.split(r'(?<=[.!?])\s+(?=[A-ZÄÖÜ0-9„"(–-])', de.strip()) if de else []
    z = re.split(r'(?<=[。！？；])\s*', zh.strip()) if zh else []
    d = [x for x in d if x]; z = [x for x in z if x]
    # 德/中句数不一致（如含 z. B.、… 的条目）时不拆，整段作为一条，避免出现空译文
    if not d or len(d) != len(z):
        return [{'de': de.strip(), 'zh': zh.strip()}]
    return [{'de': d[i], 'zh': z[i]} for i in range(len(d))]

def norm_de(s):
    return re.sub(r'\s+', ' ', (s or '').strip())

def clean_ex(ex):
    out, have = [], set()
    for p in ex:
        de = norm_de(p.get('de', '')); zh = (p.get('zh') or '').strip()
        if not de:
            continue
        k = de.lower()
        if k in have:
            continue
        have.add(k); out.append({'de': de, 'zh': zh})
        if len(out) >= 5:
            break
    return out

entries = []

# ---------- A1 ----------
a1 = load('wordlist.json')
for e in a1['entries']:
    entries.append({
        'level': 'A1', 'de': e['de'], 'zh': e['zh'], 'g': e.get('g', ''),
        'forms': FORMS.get(e['de'], ''), 'under': e.get('under', []),
        'sub': e.get('sub', 0), 'letter': e.get('letter', '?'),
        'ex': split_ex(e.get('ex_de', ''), e.get('ex_zh', '')),
    })

# ---------- A2 ----------
a2 = load('a2.json'); a2z = load('a2_zh.json')
for i, e in enumerate(a2):
    z = a2z.get(str(i), {})
    ex = [{'de': d, 'zh': zz} for d, zz in zip(e['ex'], z.get('ex', []))]
    entries.append({
        'level': 'A2', 'de': e['de'], 'zh': z.get('zh', ''),
        'g': e.get('g', ''), 'forms': e.get('forms', ''), 'under': [],
        'sub': 0, 'letter': e.get('letter', '?'), 'ex': ex,
    })

# ---------- B1 ----------
b1 = load('b1.json'); b1z = load('b1_zh.json')
for i, e in enumerate(b1):
    z = b1z.get(str(i), {})
    ex = [{'de': d, 'zh': zz} for d, zz in zip(e['ex'], z.get('ex', []))]
    entries.append({
        'level': 'B1', 'de': e['de'], 'zh': z.get('zh', ''),
        'g': e.get('g', ''), 'forms': e.get('forms', ''), 'under': [],
        'sub': 0, 'letter': e.get('letter', '?'), 'ex': ex,
    })

# normalize gender codes to m/f/n/mf (A2/B1 currently der/die/das)
GMAP = {'der': 'm', 'die': 'f', 'das': 'n', 'der/die': 'mf', 'm': 'm', 'f': 'f', 'n': 'n', 'mf': 'mf'}
for e in entries:
    e['g'] = GMAP.get(e.get('g', ''), '')

def merge_into(tgt, e):
    have = {(p.get('de', ''), p.get('zh', '')) for p in tgt['ex']}
    for p in e['ex']:
        if (p.get('de', ''), p.get('zh', '')) not in have and len(tgt['ex']) < 5:
            tgt['ex'].append(p); have.add((p.get('de', ''), p.get('zh', '')))
    if not tgt.get('forms') and e.get('forms'): tgt['forms'] = e['forms']
    if not tgt.get('zh') and e.get('zh'): tgt['zh'] = e['zh']

def word_key(e):
    de = e['de']
    art = re.match(r'^(der/die|der|die|das)\s+', de)
    s = re.sub(r'^(der/die|der|die|das)\s+', '', de)
    s = re.sub(r'\([^)]*\)', '', s)          # 去掉括号补充
    s = s.split(',')[0].strip().lower()      # 去掉逗号后的复数/变位
    s = re.sub(r'[^0-9a-zäöüß]+', '', s)     # 去掉箭头、连字符等
    pos = 'N' if (art or e.get('g')) else 'X'  # 名词 / 其他，避免名词与动形混淆
    return pos + ':' + (s or de.lower())

# 1) 先把每个级别内部的完全相同词条合并
out = []
for lv in ['A1', 'A2', 'B1']:
    le = [e for e in entries if e['level'] == lv]
    seen_exact = {}
    for e in le:
        if e['de'] in seen_exact:
            merge_into(seen_exact[e['de']], e)
        else:
            seen_exact[e['de']] = e; out.append(e)

# 2) 保留全部词条；用 dup 标记“该词在更低级别已出现过”，由前端开关决定是否隐藏
ORDER = {'A1': 0, 'A2': 1, 'B1': 2}
first_lv = {}
for e in out:
    k = word_key(e)
    if k not in first_lv or ORDER[e['level']] < ORDER[first_lv[k]]:
        first_lv[k] = e['level']
for e in out:
    k = word_key(e)
    e['mk'] = k                                   # 跨级别统一标记键（同一个词共享颜色）
    e['dup'] = 1 if first_lv[k] != e['level'] else 0
    e['ex'] = clean_ex(e['ex'])
entries = out
print('跨级别重复词条(dup=1):', sum(e['dup'] for e in entries), '；总计', len(entries))

# global ids
for i, e in enumerate(entries):
    e['id'] = i

# thematic groups (A1) + level
groups = []
for g in a1['groups']:
    if g.get('type') == 'cat':
        groups.append({'level': 'A1', 'type': 'cat', 'cat': g['cat']})
    elif g['de'].startswith('Länder/Ländernamen'):
        # merged category header split by the table parser -> merge back
        groups.append({'level': 'A1', 'type': 'cat', 'cat': (g['de'] + g['zh']).strip()})
    else:
        groups.append({'level': 'A1', 'type': 'item', 'de': g['de'], 'zh': g['zh']})

data = {'entries': entries, 'groups': groups,
        'levels': ['A1', 'A2', 'B1']}
json.dump(data, open(BASE + '/data.json', 'w'), ensure_ascii=False, separators=(',', ':'))
from collections import Counter
print('entries', len(entries), dict(Counter(e['level'] for e in entries)))
print('groups', len(groups))
print('A1 ex sample', entries[0]['de'], entries[0]['ex'][:1])
print('A2 sample', next(e for e in entries if e['level'] == 'A2'))
print('B1 sample', next(e for e in entries if e['level'] == 'B1'))
