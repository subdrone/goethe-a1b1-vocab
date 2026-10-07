import os, re, csv, json, glob

BASE = '/tmp/opencode'
A2DIR = BASE + '/A2repo/A2_Wortliste_Goethe'

def field(md, name):
    m = re.search(r'^###[ \t]+' + re.escape(name) + r'[ \t]*\r?\n(.*?)(?=^###[ \t]|\Z)',
                  md, re.S | re.M)
    return (m.group(1).strip() if m else '')

def letter_of(de):
    w = de.strip()
    w = re.sub(r'^(der/die|der|die|das)\s+', '', w)
    while True:
        w2 = re.sub(r'^\([^)]*\)[\s\-]*', '', w)
        if w2 == w:
            break
        w = w2
    w = re.sub(r'^[^0-9A-Za-zÄÖÜäöüß]+', '', w)
    if not w:
        return '?'
    c = w[0].upper()
    return {'Ä':'A','Ö':'O','Ü':'U'}.get(c, c)

# ---------------- A2 ----------------
a2 = []
for path in sorted(glob.glob(A2DIR + '/*.md')):
    md = open(path, encoding='utf-8').read()
    wort = field(md, 'Wort_DE')
    if not wort:
        continue
    art = field(md, 'Artikel')
    plural = field(md, 'Plural')
    verb = field(md, 'Verbformen')
    en = field(md, 'Wort_EN')
    order = field(md, 'Original_Order')
    ex = []
    for i in range(1, 5):
        s = field(md, 'Satz%d_DE' % i)
        if s:
            ex.append(s)
    de = (art + ' ' + wort).strip() if art else wort
    # noun: show plural like A1 (", -en")
    if art and plural:
        de = de + ', ' + plural
    forms = ''
    if verb:
        parts = [wort] + [p.strip() for p in verb.split(',') if p.strip()]
        forms = ' · '.join(parts)
    a2.append({
        'level': 'A2', 'de': de, 'raw': wort, 'g': art, 'en': en,
        'forms': forms, 'ex': ex, 'order': int(order) if order.isdigit() else 99999,
        'letter': '',  # set after de built
    })
# fallback gender from article if empty
for e in a2:
    if e['g'] == 'der/die':
        e['g'] = 'mf'
for e in a2: e['letter'] = letter_of(e['de'])
a2.sort(key=lambda e: (e['letter'], e['order']))

# ---------------- B1 ----------------
def parse_b1_word(w):
    """return (de, forms)"""
    w = w.strip()
    lines = [l.strip() for l in w.split('\n') if l.strip()]
    if not lines:
        return '', ''
    first = lines[0]
    # noun: der/die/das X, plural
    m = re.match(r'^(der|die|das)\s+([^,]+)(?:,\s*(.*))?$', first)
    if m:
        art, noun, rest = m.group(1), m.group(2).strip(), (m.group(3) or '').strip()
        de = art + ' ' + noun + (', ' + rest if rest else '')
        return de, ''
    # verb / other: "abbiegen, biegt ab, bog ab, ist abgebogen"
    parts = [p.strip() for p in first.split(',') if p.strip()]
    de = parts[0]
    forms = ' · '.join(parts) if len(parts) > 1 else ''
    return de, forms

b1 = []
with open(BASE + '/B1.csv', encoding='utf-8') as f:
    rows = list(csv.reader(f))
# skip header line
for row in rows[1:]:
    if not row or not row[0].strip():
        continue
    de, forms = parse_b1_word(row[0])
    if not de:
        continue
    exraw = row[1] if len(row) > 1 else ''
    ex = []
    for s in re.split(r'\n', exraw):
        s = re.sub(r'^\s*\d+\.\s*', '', s).strip()
        if s:
            ex.append(s)
    g = de.split(' ')[0] if de.split(' ')[0] in ('der','die','das') else ''
    b1.append({'level': 'B1', 'de': de, 'g': g, 'forms': forms, 'ex': ex,
               'letter': letter_of(de)})
for e in b1: e['letter'] = letter_of(e['de'])
b1.sort(key=lambda e: (e['letter'], e['de'].lower()))

json.dump(a2, open(BASE + '/a2.json', 'w'), ensure_ascii=False, indent=0)
json.dump(b1, open(BASE + '/b1.json', 'w'), ensure_ascii=False, indent=0)
print('A2 entries', len(a2), 'with examples', sum(1 for e in a2 if e['ex']))
print('B1 entries', len(b1), 'with examples', sum(1 for e in b1 if e['ex']))
print('A2 sample:'); [print(' ', e) for e in a2[:3]]
print('B1 sample:'); [print(' ', e) for e in b1[:3]]
print('A2 no-example sample:', [e['de'] for e in a2 if not e['ex']][:10])
print('B1 no-example sample:', [e['de'] for e in b1 if not e['ex']][:10])
