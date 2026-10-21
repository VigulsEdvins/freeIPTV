#!/usr/bin/env python3
import urllib.request
import re
import sys

def parse_m3u(content):
    channels = []
    current_meta = []
    for line in content.splitlines():
        line_clean = line.strip()
        if not line_clean:
            continue
        if line_clean.startswith('#EXTINF:'):
            current_meta = [line_clean]
        elif line_clean.startswith('#') and current_meta:
            current_meta.append(line_clean)
        elif not line_clean.startswith('#'):
            if current_meta:
                channels.append((current_meta, line_clean))
                current_meta = []
    return channels

def fetch(url):
    print(f"Загрузка: {url}...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode('utf-8', errors='ignore')

def clean_channel_name(name):
    t = re.sub(r'\s*\(\d+\)\s*', '', name)
    t = re.sub(r'\s*\b(HD|SD|FHD|50fps|International)\b\s*', '', t, flags=re.I)
    return t.strip()

def prepare_header(header, group_name):
    title = header.split(',')[-1].strip()
    clean_name = clean_channel_name(title)
    
    # Обновляем group-title
    if 'group-title=' in header:
        new_h = re.sub(r'group-title=\"[^\"]+\"', f'group-title="{group_name}"', header)
    else:
        new_h = header.replace('#EXTINF:-1 ', f'#EXTINF:-1 group-title="{group_name}" ')
    
    # Добавляем эталонный tvg-name для точной привязки EPG программы
    if 'tvg-name=' not in new_h:
        new_h = new_h.replace('#EXTINF:-1 ', f'#EXTINF:-1 tvg-name="{clean_name}" ')
        
    return new_h

def main():
    try:
        ru_raw = fetch('https://ngrch.github.io/iptv/ru.m3u')
    except Exception as e:
        print(f"Ошибка загрузки RU: {e}")
        ru_raw = ""

    try:
        lv_raw = fetch('https://iptv-org.github.io/iptv/countries/lv.m3u')
    except Exception as e:
        print(f"Ошибка загрузки LV: {e}")
        lv_raw = ""

    ru_chans = parse_m3u(ru_raw)
    lv_chans = parse_m3u(lv_raw)

    categories = {
        '😂 Ситкомы, Юмор и Шоу (Comedy, ТНТ4)': [],
        '🍿 Современное Зарубежное Кино и Сериалы': [],
        '🎉 Развлекательные (ТНТ, СТС, Пятница)': [],
        '⚽ Спорт': [],
        '👶 Мультфильмы и Детские': [],
        '🇱🇻 Латвия': []
    }

    # Добавляем круглосуточный канал КВН ТВ
    kvn_meta = ['#EXTINF:-1 tvg-name="КВН ТВ" tvg-id="kvn-tv" tvg-logo="https://epg.iptvx.one/picons/kvn-tv.png" group-title="😂 Ситкомы, Юмор и Шоу (Comedy, ТНТ4)",КВН ТВ']
    kvn_url = 'https://fs.uplink.kz/kvn_tv/tracks-v1a1/mono.ts.m3u8?token=onlinetv'
    categories['😂 Ситкомы, Юмор и Шоу (Comedy, ТНТ4)'].append((kvn_meta, kvn_url))

    # Жесткий черный список: советские фильмы, "Кинозалы 1,2..", любительские стримы, новости, религия
    exclude_patterns = [
        r'кинозал[ыа]?\s*\d+',
        r'кино\s*\d+',
        r'вхс|vhs',
        r'ссср|ussr',
        r'90[-‑]?[хx]',
        r'кассет[аы]',
        r'ретро',
        r'retrovision',
        r'классик',
        r'советск',
        r'русск',
        r'родное',
        r'любимое',
        r'наше',
        r'мосфильм',
        r'побед[аы]',
        r'душевн',
        r'дом кино',
        r'следствие вели',
        r'пёс',
        r'скорая помощь',
        r'ты супер',
        r'индийск',
        r'bollywood',
        r'дорама',
        r'информацион',
        r'новост',
        r'религиоз',
        r'фильмоскоп',
        r'тоха',
        r'модерн',
        r'ostorozhnomodern',
        r'durkalive',
        r'dimpon',
        r'нтв сериал',
        r'нтв хит',
        r'start air',
        r'старт',
        r'мистер бин',
        r'бенни хилл',
        r'медздрав',
        r'гурман',
        r'новелла',
        r'tvboom',
        r'андийцы',
        r'hgtn',
        r'dunyo',
        r'tv12',
        r'смотрим',
        r'всё тв',
        r'igrocomp',
        r'kycman',
        r'zour',
        r'priest',
        r'nezabudka',
        r'frxnkl1n',
        r'х-tv',
        r'kira_freak',
        r'aisman',
        r'swat2k',
        r'wfliq',
        r'chowamigo',
        r'inmuna',
        r'у края бездны',
        r'1st_witch',
        r'мир ехо',
        r'аpricus',
        r'россия 24',
        r'первый',
        r'нтв',
        r'вести'
    ]

    for meta, url in ru_chans:
        header = meta[0]
        group_m = re.search(r'group-title=\"([^\"]+)\"', header)
        group = group_m.group(1) if group_m else ''
        title = header.split(',')[-1].strip()
        t_low = title.lower()
        combined = f"{title} {group}".lower()

        # Проверка по черному списку
        if any(re.search(pat, combined, flags=re.I) for pat in exclude_patterns):
            continue

        # 1. СИТКОМЫ, ЮМОР И ШОУ (ТНТ4, СТС Love, КВН, Суббота, Че, 2х2)
        is_comedy_show = (
            any(k in t_low for k in ['тнт4', 'стс love', 'квн', 'юмор', 'comedy', 'анекдот']) or
            bool(re.search(r'\b(че|суббота|2х2)\b', t_low))
        )
        if is_comedy_show:
            new_header = prepare_header(header, '😂 Ситкомы, Юмор и Шоу (Comedy, ТНТ4)')
            categories['😂 Ситкомы, Юмор и Шоу (Comedy, ТНТ4)'].append(([new_header] + meta[1:], url))
            continue

        # 2. СОВРЕМЕННОЕ ЗАРУБЕЖНОЕ КИНО И СЕРИАЛЫ
        is_movie = (
            any(k in group.lower() for k in ['кино', 'kinowalk']) or
            any(w in t_low for w in [
                'tv1000', 'viju', 'amedia', 'fx', 'sci-fi', '.red', '.black',
                'hollywood', 'иллюзион', 'премиальн', 'шокирующ', 'остросюжет',
                'кинопремьера', 'кинохит', 'киномикс', 'киносемья', 'киносвидание',
                'киноужас', 'кинокомедия', 'киносерия', 'мужское кино', 'кино тв',
                'еврокино', 'cinema', 'blockbuster', 'timeto', 'serial', 'movie'
            ])
        )
        if is_movie and not any(k in group.lower() for k in ['спорт', 'детск']):
            new_header = prepare_header(header, '🍿 Современное Зарубежное Кино и Сериалы')
            categories['🍿 Современное Зарубежное Кино и Сериалы'].append(([new_header] + meta[1:], url))
            continue

        # 3. РАЗВЛЕКАТЕЛЬНЫЕ КАНАЛЫ (ТНТ, СТС, Пятница)
        is_ent = (
            any(k in group.lower() for k in ['развлекательн', 'популярные', 'основные']) and
            any(t in t_low for t in ['тнт', 'стс', 'пятница'])
        )
        if is_ent:
            new_header = prepare_header(header, '🎉 Развлекательные (ТНТ, СТС, Пятница)')
            categories['🎉 Развлекательные (ТНТ, СТС, Пятница)'].append(([new_header] + meta[1:], url))
            continue

        # 4. СПОРТ
        is_sport = any(k in group.lower() for k in ['спорт']) or 'матч' in t_low or 'sport' in t_low
        if is_sport:
            new_header = prepare_header(header, '⚽ Спорт')
            categories['⚽ Спорт'].append(([new_header] + meta[1:], url))
            continue

        # 5. ДЕТСКИЕ И МУЛЬТФИЛЬМЫ
        is_kids = any(k in group.lower() for k in ['детск', 'мульт']) or any(m in t_low for m in ['мульт', 'карусель', 'kids', 'disney'])
        if is_kids:
            new_header = prepare_header(header, '👶 Мультфильмы и Детские')
            categories['👶 Мультфильмы и Детские'].append(([new_header] + meta[1:], url))
            continue

    # 6. ЛАТВИЙСКИЕ КАНАЛЫ
    for meta, url in lv_chans:
        header = meta[0]
        new_header = prepare_header(header, '🇱🇻 Латвия')
        categories['🇱🇻 Латвия'].append(([new_header] + meta[1:], url))

    # Сборка итогового файла с программой передач (EPG)
    epg_sources = [
        'https://iptvx.one/epg/epg.xml.gz',
        'http://epg.it999.ru/edem.xml.gz',
        'https://iptv-org.github.io/epg/guides/lv/tet.lv.epg.xml'
    ]
    output_file = 'playlist.m3u'
    total = 0

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f'#EXTM3U url-tvg="{",".join(epg_sources)}"\n')
        for cat_name, items in categories.items():
            print(f"{cat_name}: {len(items)} каналов")
            total += len(items)
            for meta, url in items:
                for m in meta:
                    f.write(m + '\n')
                f.write(url + '\n')

    print(f"\nГотово! Всего каналов: {total}. Сохранено в {output_file}")

if __name__ == '__main__':
    main()
