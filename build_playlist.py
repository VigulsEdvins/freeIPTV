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
        '🍿 Кинозалы и Фильмы': [],
        '🎉 Развлекательные (ТНТ, СТС)': [],
        '⚽ Спорт': [],
        '👶 Мультфильмы и Детские': [],
        '🇱🇻 Латвия': []
    }

    # Фильтрация и классификация русскоязычных каналов
    for meta, url in ru_chans:
        header = meta[0]
        group_m = re.search(r'group-title=\"([^\"]+)\"', header)
        group = group_m.group(1) if group_m else ''

        # Полностью исключаем новости и политику
        if any(n in group.lower() for n in ['информацион', 'новост', 'религиоз']):
            continue

        title = header.split(',')[-1].strip()

        # Кинозалы и фильмы (огромный блок)
        if any(k in group.lower() for k in ['кино', 'сериал']) or 'фильм' in title.lower():
            new_header = re.sub(r'group-title=\"[^\"]+\"', 'group-title="🍿 Кинозалы и Фильмы"', header)
            categories['🍿 Кинозалы и Фильмы'].append(([new_header] + meta[1:], url))
        
        # Развлекательные каналы
        elif any(k in group.lower() for k in ['развлекательн']) or any(t.lower() in title.lower() for t in ['тнт', 'стс', 'пятница', '2х2', 'тнт4', 'суббота', 'че']):
            new_header = re.sub(r'group-title=\"[^\"]+\"', 'group-title="🎉 Развлекательные"', header)
            categories['🎉 Развлекательные (ТНТ, СТС)'].append(([new_header] + meta[1:], url))
        
        # Спорт
        elif any(k in group.lower() for k in ['спорт']) or 'матч' in title.lower():
            new_header = re.sub(r'group-title=\"[^\"]+\"', 'group-title="⚽ Спорт"', header)
            categories['⚽ Спорт'].append(([new_header] + meta[1:], url))
        
        # Детские и мультфильмы
        elif any(k in group.lower() for k in ['детск', 'мульт']) or any(m in title.lower() for m in ['мульт', 'карусель', 'kids']):
            new_header = re.sub(r'group-title=\"[^\"]+\"', 'group-title="👶 Мультфильмы и Детские"', header)
            categories['👶 Мультфильмы и Детские'].append(([new_header] + meta[1:], url))

    # Латвийские каналы
    for meta, url in lv_chans:
        header = meta[0]
        if 'group-title=' in header:
            new_header = re.sub(r'group-title=\"[^\"]+\"', 'group-title="🇱🇻 Латвия"', header)
        else:
            new_header = header.replace('#EXTINF:-1 ', '#EXTINF:-1 group-title="🇱🇻 Латвия" ')
        categories['🇱🇻 Латвия'].append(([new_header] + meta[1:], url))

    # Сборка итогового файла
    output_file = 'playlist.m3u'
    total = 0
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
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
