#!/usr/bin/env python3
"""Offline SVG renderer. --refresh fetches the GitHub GraphQL snapshot first."""
import argparse, base64, calendar, datetime as dt, html, json, os
from pathlib import Path
import re, subprocess, tempfile, textwrap, urllib.request

ROOT = Path(__file__).resolve().parents[1]
STATIC = os.getenv('STATIC') == '1'
# Transparent panels inherit GitHub's exact background, including dimmed themes.
LIGHT = ('none', '#1f2328', '#59636e', '#d1d9e0', '#59684d')
DARK = ('none', '#f0f6fc', '#9198a1', '#3d444d', '#a9bf8e')
PAPER, INK, MUTED, LINE, ACCENT = LIGHT
FEATURED = ['stock-auction', 'hate-tweets-detector', 'human-motion-prediction', 'webpage-downloader', 'query-builder', 'Weather-App']

def refresh():
    token = os.environ['GITHUB_TOKEN']
    fields = ' '.join(f'r{i}: repository(owner:"eshanvaid",name:"{name}") {{ name description url primaryLanguage {{ name }} stargazerCount }}' for i, name in enumerate(FEATURED))
    query = '{ user(login:"eshanvaid") { contributionsCollection { contributionCalendar { weeks { contributionDays { date contributionCount } } } } } ' + fields + ' }'
    req = urllib.request.Request('https://api.github.com/graphql', data=json.dumps({'query': query}).encode(), headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json', 'User-Agent': 'profile-cards'})
    with urllib.request.urlopen(req, timeout=45) as response:
        payload = json.load(response)
    if payload.get('errors'):
        raise RuntimeError(payload['errors'])
    data = payload['data']
    days = [{'date': d['date'], 'count': d['contributionCount']} for w in data['user']['contributionsCollection']['contributionCalendar']['weeks'] for d in w['contributionDays']]
    snapshot = {'as_of': dt.datetime.now(dt.timezone.utc).date().isoformat(), 'source': 'GitHub GraphQL contributionCalendar', 'days': days, 'repos': [data[f'r{i}'] for i in range(len(FEATURED)) if data[f'r{i}']]}
    validate(snapshot)
    path = ROOT / 'data/contributions.json'
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(snapshot, indent=2) + '\n')
    temporary.replace(path)

def validate(data):
    dates = [dt.date.fromisoformat(d['date']) for d in data['days']]
    assert dates and dates == sorted(set(dates)), 'Calendar must have unique ordered days'
    assert all(isinstance(d['count'], int) and d['count'] >= 0 for d in data['days'])
    assert all((b-a).days == 1 for a,b in zip(dates,dates[1:])), 'Calendar has gaps'

def font_css():
    result = ''
    for family, name in [('Body', 'manrope.woff2'), ('Display', 'cormorant.woff')]:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'subset.woff'
            subprocess.run(['pyftsubset', str(ROOT/'assets/fonts'/name), '--unicodes=U+0020-007E,U+00B7,U+2013-2014,U+2197', '--flavor=woff', f'--output-file={output}', '--no-hinting', '--recalc-timestamp'], check=True)
            encoded = base64.b64encode(output.read_bytes()).decode()
        result += f"@font-face{{font-family:{family};src:url(data:font/woff;base64,{encoded}) format('woff');font-weight:200 800;}}"
    return result

def text(x,y,value,size=16,display=False,fill=None,extra=''):
    fill = INK if fill is None else fill
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-family="{"Display" if display else "Body"}" {extra}>{html.escape(str(value))}</text>'

def card(name, height, body, delay, title, width=960):
    # SMIL is confined to a motion layer. Reduced motion displays its final-state twin.
    css = FONTS + f'''.enter{{animation:arrive .8s ease {delay}s both}}@keyframes arrive{{from{{opacity:0;transform:translateY(12px)}}to{{opacity:1;transform:translateY(0)}}}}.final{{display:none}}@media(prefers-reduced-motion:reduce){{*{{animation:none!important;transition:none!important}}.motion{{display:none}}.final{{display:inline}}}}'''
    if STATIC:
        css += '*{animation:none!important;transition:none!important}.motion{display:none}.final{display:inline}'
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img"><title>{html.escape(title)}</title><style>{css}</style><rect x=".5" y=".5" width="{width-1}" height="{height-1}" rx="18" fill="{PAPER}" stroke="{LINE}"/><g class="enter">{body}</g></svg>'
    (OUT/f'{name}.svg').write_text(svg)

def animated_line(path, delay):
    base = f'<path d="{path}" fill="none" stroke="{ACCENT}" stroke-width="3" pathLength="1"'
    if STATIC:
        return base + '/>'
    return base + f' class="final"/>' + base + f' class="motion"><animate attributeName="stroke-dasharray" values="0 1;1 0" dur="1.2s" begin="{delay}s" fill="freeze"/></path>'

def render(data):
    validate(data)
    body = text(480,112,'Eshan Vaid',78,True,extra='text-anchor="middle"')
    card('hero',180,body,0,'Eshan Vaid')
    for i,(name,label,sub) in enumerate([('website','The pavilion','Explore eshan.fyi'),('linkedin','Let’s connect'.replace('’',"'"),'Find me on LinkedIn'),('github','Open source','Browse my repositories')]):
        card(name,142,text(23,31,f'0{i+1}  /',11,fill=MUTED)+text(23,78,label,32,True)+text(23,116,sub,12)+text(275,32,'↗',20,fill=ACCENT),.35+i*.15,label,312)
    days = data['days']; as_of = dt.date.fromisoformat(data['as_of'])
    eligible = [d for d in days if d['date'] <= as_of.isoformat()]
    lookup = {d['date']:d['count'] for d in eligible}
    cursor = as_of if lookup.get(as_of.isoformat(),0) else as_of-dt.timedelta(days=1)
    streak = 0
    while lookup.get(cursor.isoformat(),0):
        streak += 1; cursor -= dt.timedelta(days=1)
    active = sum(d['count']>0 for d in eligible); busiest = max(eligible,key=lambda d:d['count'])
    months = {}
    for d in eligible: months[d['date'][:7]] = months.get(d['date'][:7],0)+d['count']
    body = text(36,43,'A year in motion',36,True)+text(36,73,f"{eligible[0]['date']} — {eligible[-1]['date']} · UTC",12,fill=MUTED)
    for i,(value,label) in enumerate([(f'{streak} day' + ('s' if streak != 1 else ''),'CURRENT STREAK'),(str(active),'ACTIVE DAYS'),(str(busiest['count']),f"BUSIEST · {busiest['date']}" if busiest['count'] else 'BUSIEST · NO ACTIVITY')]):
        body += text(36+i*305,123,value,30,True)+text(36+i*305,148,label,10,fill=MUTED)
    peak = max(max(months.values()),1)
    for i,(month,count) in enumerate(months.items()):
        x = 45+i* (865/len(months)); h = count/peak*125
        body += f'<rect x="{x}" y="{305-h}" width="38" height="{max(h,1)}" rx="4" fill="{ACCENT}"/>'
        body += text(x+19,325,calendar.month_abbr[int(month[-2:])],11,fill=MUTED,extra='text-anchor="middle"')+text(x+19,295-h,count,11,extra='text-anchor="middle"')
    card('activity',350,body,.9,'Monthly contributions, current streak, active days and busiest day')
    for i,repo in enumerate(data['repos']):
        body = text(24,30,f'0{i+1} / FEATURED REPOSITORY',10,fill=MUTED)
        body += text(24,72,repo['name'],28,True)+text(432,32,'↗',19,fill=ACCENT)
        description = repo.get('description') or 'Explore the source on GitHub.'
        lines = textwrap.wrap(description, 52)
        if len(lines) > 3:
            lines = lines[:3]
            lines[-1] = lines[-1].rstrip(' .,;') + '...'
        for j,line in enumerate(lines):
            body += text(24,104+j*20,line,13)
        language = (repo.get('primaryLanguage') or {}).get('name','Source')
        stars = repo['stargazerCount']
        body += text(24,190,f"{language}   ·   {stars} star{'s' if stars != 1 else ''}",12,fill=ACCENT)
        card('repo-'+repo['name'],215,body,1.3+i*.2,repo['name'],470)
    body = text(36,43,'Small steps, over time.',36,True)+text(36,72,f"{sum(d['count'] for d in eligible)} contributions · updated {data['as_of']} · UTC",12,fill=MUTED)
    start = dt.date.fromisoformat(days[0]['date']); origin = start-dt.timedelta(days=(start.weekday()+1)%7)
    peak = max(max(d['count'] for d in days),1)
    for d in eligible:
        date = dt.date.fromisoformat(d['date']); offset = (date-origin).days; x=38+offset//7*16.5; y=101+(offset%7)*18
        opacity = .25+.75*d['count']/peak if d['count'] else 1
        body += f'<rect x="{x}" y="{y}" width="12" height="12" rx="3" fill="{ACCENT if d["count"] else LINE}" opacity="{opacity}"><title>{d["date"]}: {d["count"]} contributions</title></rect>'
    body += animated_line('M38 247H915',3)
    body += text(38,275,'EVERY SQUARE IS A DAY. EVERY DAY IS A CHANCE TO BUILD.',10,fill=MUTED)
    card('contributions',300,body,2.8,'Contribution calendar in olive green')
    links = [('website','https://eshan.fyi','Explore my website'),('linkedin','https://www.linkedin.com/in/eshanvaid/','Connect on LinkedIn'),('github','https://github.com/eshanvaid?tab=repositories','Browse repositories')]
    readme = '<!-- Generated by scripts/render_cards.py. -->\n<p><a href="https://eshan.fyi"><img src="cards/hero.svg" width="100%" alt="Eshan Vaid" /></a></p>\n<p>\n'
    readme += '\n'.join(f'<a href="{url}"><img src="cards/{name}.svg" width="32.5%" alt="{alt}" /></a>' for name,url,alt in links)+'\n</p>\n\n'
    readme += '<p><img src="cards/activity.svg" width="100%" alt="Monthly contribution totals, streak, active days and busiest day" /></p>\n'
    for i,repo in enumerate(data['repos']):
        if i % 2 == 0:
            readme += '<p>\n'
        readme += f'<a href="{html.escape(repo["url"],quote=True)}"><img src="cards/repo-{repo["name"]}.svg" width="49%" alt="{html.escape(repo["name"],quote=True)}" /></a>\n'
        if i % 2 == 1 or i == len(data['repos'])-1:
            readme += '</p>\n'
    readme += '<p><img src="cards/contributions.svg" width="100%" alt="My contribution calendar in olive green" /></p>\n'
    readme = re.sub(r'<img src="cards/([^"]+)"([^>]+)>', lambda m: f'<picture><source media="(prefers-color-scheme: dark)" srcset="cards/dark/{m[1]}" /><img src="cards/{m[1]}"{m[2]}></picture>', readme)
    if not STATIC: (ROOT/'README.md').write_text(readme)
    preview = readme.replace('<a href=', '<a target="_blank" rel="noopener noreferrer" href=')
    (OUT/'preview.html').write_text('<!doctype html><meta charset="utf-8"><title>Profile preview</title><style>body{max-width:960px;margin:24px auto;background:#ffffff}@media(prefers-color-scheme:dark){body{background:#0d1117}}img{vertical-align:top}p{margin:0 0 14px}</style>'+preview.replace('cards/',''))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--refresh', action='store_true'); args=parser.parse_args()
    if args.refresh: refresh()
    destination = ROOT / ('preview-static' if STATIC else 'cards')
    FONTS = font_css()
    data = json.loads((ROOT/'data/contributions.json').read_text())
    for palette, folder in [(DARK, destination/'dark'), (LIGHT, destination)]:
        PAPER, INK, MUTED, LINE, ACCENT = palette
        OUT = folder; OUT.mkdir(parents=True, exist_ok=True)
        render(data)
    (destination/'dark/preview.html').unlink(missing_ok=True)
