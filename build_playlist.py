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
    # Очищаем название от суффиксов дубликатов (2), (3), FHD, HD для точного поиска в программе передач (EPG)
    t = re.sub(r'\s*\(\d+\)\s*', '', name)
    t = re.sub(r'\s*\b(HD|SD|FHD|50fps)\b\s*', '', t, flags=re.I)
    return t.strip()

def prepare_header(header, group_name):
    title = header.split(',')[-1].strip()
    clean_name = clean_channel_name(title)
    
    # Обновляем или добавляем group-title
    if 'group-title=' in header:
        new_h = re.sub(r'group-title=\"[^\"]+\"', f'group-title="{group_name}"', header)
    else:
        new_h = header.replace('#EXTINF:-1 ', f'#EXTINF:-1 group-title="{group_name}" ')
    
    # Добавляем tvg-name для 100% совпадения с EPG
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
        '🍿 Современное Зарубежное Кино и Кинозалы': [],
        '🎉 Развлекательные': [],
        '⚽ Спорт': [],
        '👶 Мультфильмы и Детские': [],
        '🇱🇻 Латвия': []
    }

    # Черный список: советские фильмы, старое русское кино, ток-шоу, новости, религия, индийское/турецкое
    exclude_keywords = [
        'советск', 'ссср', 'родное кино', 'любимое кино', 'наше кино', 'наше новое',
        'русский бестселлер', 'русский роман', 'русский детектив', 'русский иллюзион',
        'мосфильм', 'золотая коллекция', 'дом кино', 'ретро', 'победа', 'душевное',
        'всё тв', 'viju tv1000 русское', 'нтв сериал', 'нтв хит', 'следствие вели',
        'пёс', 'скорая помощь', 'ты супер', 'индийск', 'bollywood', 'дорама',
        'информацион', 'новост', 'религиоз', 'политик', 'россия 24', 'первый', 'нтв', 'вести',
        'классика кино', 'мы из 90-х', 'vhs forever', 'кассета'
    ]

    for meta, url in ru_chans:
        header = meta[0]
        group_m = re.search(r'group-title=\"([^\"]+)\"', header)
        group = group_m.group(1) if group_m else ''
        title = header.split(',')[-1].strip()
        t_low = title.lower()
        g_low = group.lower()

        # Полная фильтрация по черному списку
        if any(bad in t_low or bad in g_low for bad in exclude_keywords):
            continue

        # 1. СОВРЕМЕННОЕ ЗАРУБЕЖНОЕ КИНО И КИНОЗАЛЫ
        is_movie_channel = (
            any(k in g_low for k in ['кино', 'kinowalk', 'catcast']) or
            any(w in t_low for w in [
                'tv1000', 'viju', 'amedia', 'fx', 'sci-fi', '.red', '.black',
                'hollywood', 'иллюзион', 'остросюжет', 'премиальн', 'шокирующ',
                'кинопремьера', 'кинохит', 'киномикс', 'киносемья', 'киносвидание',
                'киноужас', 'кинокомедия', 'киносерия', 'мужское кино', 'кино тв',
                'еврокино', 'cinema'
            ])
        )

        if is_movie_channel:
            new_header = prepare_header(header, '🍿 Современное Зарубежное Кино и Кинозалы')
            categories['🍿 Современное Зарубежное Кино и Кинозалы'].append(([new_header] + meta[1:], url))
            continue

        # 2. РАЗВЛЕКАТЕЛЬНЫЕ КАНАЛЫ (ТНТ, СТС, Пятница и др.)
        is_ent = (
            any(k in g_low for k in ['развлекательн']) or
            any(t in t_low for t in ['тнт', 'стс', 'пятница', '2х2', 'тнт4', 'суббота', 'че'])
        )
        if is_ent:
            new_header = prepare_header(header, '🎉 Развлекательные')
            categories['🎉 Развлекательные'].append(([new_header] + meta[1:], url))
            continue

        # 3. СПОРТ
        is_sport = any(k in g_low for k in ['спорт']) or 'матч' in t_low or 'sport' in t_low
        if is_sport:
            new_header = prepare_header(header, '⚽ Спорт')
            categories['⚽ Спорт'].append(([new_header] + meta[1:], url))
            continue

        # 4. ДЕТСКИЕ И МУЛЬТФИЛЬМЫ
        is_kids = any(k in g_low for k in ['детск', 'мульт']) or any(m in t_low for m in ['мульт', 'карусель', 'kids', 'disney'])
        if is_kids:
            new_header = prepare_header(header, '👶 Мультфильмы и Детские')
            categories['👶 Мультфильмы и Детские'].append(([new_header] + meta[1:], url))
            continue

    # 5. ЛАТВИЙСКИЕ КАНАЛЫ
    for meta, url in lv_chans:
        header = meta[0]
        new_header = prepare_header(header, '🇱🇻 Латвия')
        categories['🇱🇻 Латвия'].append(([new_header] + meta[1:], url))

    # Сборка итогового M3U с указанием EPG в заголовке
    epg_sources = [
        'https://iptvx.one/epg/epg.xml.gz',
        'http://epg.it999.ru/edem.xml.gz',
        'https://iptv-org.github.io/epg/guides/lv/tet.lv.epg.xml'
    ]
    output_file = 'playlist.m3u'
    total = 0

    with open(output_file, 'w', encoding='utf-8') as f:
        # Указываем EPG телепрограмму для всех каналов
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
