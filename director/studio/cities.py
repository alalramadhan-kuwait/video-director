"""Cities: where each one is, its colours, its sound, and its landmarks drawn as paper layers (far, middle, near).

The `city_zoom` template flies the map from the country into the city, then the map gives way to the city's own
colours and its skyline rises like a pop-up book: hills or mountains, roofs, then the landmarks everyone knows.
Each skyline is drawn on a 720 x 440 card whose bottom edge is the ground. Silhouettes only: an icon of the place,
never presented as a photograph or a historical record.
"""
from __future__ import annotations

SKY_W, SKY_H = 720, 440


def _rects(*rs, fill):
    return ''.join(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"/>' for x, y, w, h in rs)


def _windows(x0, y0, cols, rows, dx, dy, w=8, h=14, fill='#000', op=.18):
    return ''.join(f'<rect x="{x0 + c * dx}" y="{y0 + r * dy}" width="{w}" height="{h}" fill="{fill}" fill-opacity="{op}"/>'
                   for c in range(cols) for r in range(rows))


def _roofs(y, color, seed=3, step=46):
    out, x, k = [], -10, seed
    while x < SKY_W + 10:
        k = (k * 7 + 5) % 11; w = step + k * 3; h = 40 + k * 4
        out.append(f'<rect x="{x}" y="{y - h}" width="{w}" height="{SKY_H - y + h}" fill="{color}"/>'
                   f'<path d="M{x - 4} {y - h} L{x + w / 2} {y - h - 18 - k} L{x + w + 4} {y - h} Z" fill="{color}"/>')
        x += w + 2
    return ''.join(out)


def _cypress(x, base, h, fill):
    return f'<ellipse cx="{x}" cy="{base - h / 2}" rx="{h * .12:.0f}" ry="{h / 2}" fill="{fill}"/>'


def _pine(x, base, h, fill):
    return ''.join(f'<path d="M{x - h * (.34 - i * .07):.0f} {base - i * h * .28:.0f} L{x} {base - h * (.48 + i * .26):.0f} '
                   f'L{x + h * (.34 - i * .07):.0f} {base - i * h * .28:.0f} Z" fill="{fill}"/>' for i in range(3))


def _umbrella_pine(x, base, h, fill):
    return (f'<rect x="{x - 4}" y="{base - h}" width="8" height="{h}" fill="{fill}"/>'
            f'<ellipse cx="{x}" cy="{base - h}" rx="{h * .7:.0f}" ry="{h * .2:.0f}" fill="{fill}"/>')


def _palm(x, base, h, fill):
    fronds = ''.join(f'<path d="M{x} {base - h} q {dx * .5} {-18} {dx} {dy}" stroke="{fill}" stroke-width="7" fill="none" stroke-linecap="round"/>'
                     for dx, dy in ((-46, 22), (-30, 34), (46, 22), (30, 34), (0, -10)))
    return f'<path d="M{x - 4} {base} Q {x + 6} {base - h / 2} {x} {base - h}" stroke="{fill}" stroke-width="8" fill="none"/>{fronds}'


# ------------------------------------------------------------------------------------------------- the skylines
def florence(c):
    far = f'<path d="M0 440 L0 330 Q 120 280 240 318 Q 380 268 520 306 Q 640 276 720 300 L720 440 Z" fill="{c["far"]}"/>'
    mid = _roofs(380, c['mid']) + _cypress(36, 380, 120, c['near']) + _cypress(690, 380, 140, c['near'])
    duomo = (f'<rect x="250" y="292" width="180" height="148" fill="{c["near"]}"/>'
             f'<path d="M262 296 Q 262 190 340 166 Q 418 190 418 296 Z" fill="{c["near"]}"/>'
             + ''.join(f'<path d="M{340 + d} 296 Q {340 + d * .7} 210 340 168" stroke="{c["line"]}" stroke-width="3" fill="none"/>' for d in (-52, -18, 18, 52))
             + f'<rect x="330" y="140" width="20" height="30" fill="{c["near"]}"/><path d="M326 140 L340 108 L354 140 Z" fill="{c["near"]}"/>'
             + _windows(266, 320, 6, 2, 26, 46, 10, 22, c['line'], .5))
    campanile = (f'<rect x="452" y="118" width="40" height="322" fill="{c["near"]}"/><rect x="446" y="110" width="52" height="12" fill="{c["near"]}"/>'
                 + _windows(462, 150, 2, 4, 14, 70, 6, 34, c['line'], .55))
    vecchio = (f'<rect x="80" y="282" width="134" height="158" fill="{c["near"]}"/><rect x="136" y="162" width="26" height="122" fill="{c["near"]}"/>'
               f'<rect x="128" y="146" width="42" height="20" fill="{c["near"]}"/><rect x="142" y="112" width="14" height="36" fill="{c["near"]}"/>'
               + ''.join(f'<rect x="{80 + i * 14}" y="272" width="8" height="12" fill="{c["near"]}"/>' for i in range(10))
               + _windows(94, 310, 5, 3, 24, 40, 9, 18, c['line'], .5))
    return far, mid, duomo + campanile + vecchio


def geneva(c):
    peaks = 'M0 440 L0 330 L80 292 L150 322 L250 236 L330 300 L420 258 L520 310 L600 272 L720 320 L720 440 Z'
    snow = 'M226 258 L250 236 L274 262 L258 256 L250 264 L240 254 Z M402 272 L420 258 L440 276 L428 272 L420 278 Z'
    far = f'<path d="{peaks}" fill="{c["far"]}"/><path d="{snow}" fill="#F6F4EE"/>'
    lake = f'<rect x="0" y="392" width="720" height="48" fill="{c["water"]}"/>'
    cathedral = (f'<rect x="70" y="300" width="150" height="100" fill="{c["mid"]}"/><rect x="86" y="244" width="32" height="70" fill="{c["mid"]}"/>'
                 f'<rect x="172" y="244" width="32" height="70" fill="{c["mid"]}"/><path d="M136 300 L145 206 L154 300 Z" fill="{c["accent"]}"/>')
    mid = lake + _roofs(392, c['mid'], seed=5, step=60).replace('<rect x="-10"', '<rect x="-10"') + cathedral
    jet = (f'<path d="M514 398 L519 120 Q 523 82 529 120 Q 566 220 552 398 Z" fill="#F4F7F8" fill-opacity=".85"/>'
           f'<path d="M519 130 Q 560 150 590 260" stroke="#F4F7F8" stroke-opacity=".5" stroke-width="10" fill="none" stroke-linecap="round"/>')
    boats = ''.join(f'<path d="M{x} 412 L{x + 40} 412 L{x + 32} 422 L{x + 8} 422 Z" fill="{c["near"]}"/><path d="M{x + 18} 410 L{x + 18} 360 L{x + 40} 408 Z" fill="#F6F4EE"/>'
                    for x in (300, 620))
    return far, mid, jet + boats


def vallee_de_joux(c):
    far = f'<path d="M0 440 L0 300 Q 180 240 360 280 Q 540 236 720 286 L720 440 Z" fill="{c["far"]}"/>'
    mid = (f'<path d="M0 440 L0 352 Q 200 316 400 350 Q 560 326 720 352 L720 440 Z" fill="{c["mid"]}"/>'
           f'<rect x="0" y="396" width="720" height="44" fill="{c["water"]}"/>')
    pines = ''.join(_pine(x, 404, h, c['near']) for x, h in ((40, 150), (90, 120), (600, 160), (660, 130), (700, 110)))
    chalet = (f'<rect x="290" y="330" width="150" height="74" fill="{c["near"]}"/><path d="M276 334 L365 270 L454 334 Z" fill="{c["near"]}"/>'
              + _windows(306, 346, 5, 1, 26, 0, 14, 20, '#F1E6C8', .85))
    return far, mid, pines + chalet


def kuwait(c):
    far = f'<rect x="0" y="372" width="720" height="68" fill="{c["water"]}"/>'
    mid = (''.join(f'<rect x="{x}" y="{372 - h}" width="{w}" height="{h}" fill="{c["mid"]}"/>' for x, w, h in
                   ((0, 60, 60), (64, 40, 96), (108, 70, 50), (250, 50, 80), (304, 70, 40), (640, 80, 70)))
           + f'<path d="M300 382 L380 382 L370 398 L314 398 Z" fill="{c["near"]}"/><path d="M336 380 L336 318 L384 372 Z" fill="#F6F0E2"/>')
    def tower(x, top, base_w, spheres):
        t = f'<path d="M{x - base_w / 2} 440 L{x - 3} {top} L{x + 3} {top} L{x + base_w / 2} 440 Z" fill="{c["near"]}"/>'
        for y, r in spheres:
            t += (f'<circle cx="{x}" cy="{y}" r="{r}" fill="{c["near"]}"/>'
                  + ''.join(f'<circle cx="{x + (i - 2) * r * .3:.0f}" cy="{y - r * .2 + (i % 2) * r * .4:.0f}" r="{r * .09:.1f}" fill="{c["accent"]}"/>'
                            for i in range(5)))
        return t
    towers = tower(530, 40, 30, ((210, 50), (148, 22))) + tower(612, 150, 24, ((268, 36),)) + tower(470, 250, 14, ())
    liberation = (f'<rect x="168" y="96" width="22" height="344" fill="{c["near"]}"/><ellipse cx="179" cy="150" rx="42" ry="12" fill="{c["near"]}"/>'
                  f'<rect x="176" y="40" width="6" height="58" fill="{c["near"]}"/>')
    return far, mid, towers + liberation + _palm(60, 440, 110, c['near']) + _palm(690, 440, 90, c['near'])


def paris(c):
    far = _roofs(360, c['far'], seed=2, step=56)
    mansards = ''.join(f'<path d="M{x} 440 L{x} 380 L{x + 8} 356 L{x + 82} 356 L{x + 90} 380 L{x + 90} 440 Z" fill="{c["mid"]}"/>'
                       + _windows(x + 10, 386, 4, 2, 20, 26, 9, 14, c['line'], .4) for x in (0, 96, 470, 566, 662))
    eiffel = (f'<path d="M282 440 Q 318 330 344 200 L350 92 L356 38 L362 92 L368 200 Q 394 330 430 440 L404 440 Q 384 384 356 372 '
              f'Q 328 384 308 440 Z" fill="{c["near"]}"/>'
              f'<rect x="318" y="300" width="76" height="9" fill="{c["near"]}"/><rect x="338" y="196" width="36" height="7" fill="{c["near"]}"/>')
    arc = (f'<path fill-rule="evenodd" d="M60 440 L60 330 L210 330 L210 440 Z M110 440 L110 386 Q 135 360 160 386 L160 440 Z" fill="{c["near"]}"/>'
           f'<rect x="54" y="320" width="162" height="14" fill="{c["near"]}"/>')
    return far, mansards, eiffel + arc


def london(c):
    far = (_roofs(372, c['far'], seed=4, step=52)
           + f'<path d="M590 372 Q 590 300 630 290 Q 670 300 670 372 Z" fill="{c["far"]}"/><rect x="626" y="262" width="8" height="30" fill="{c["far"]}"/>')
    river = f'<rect x="0" y="404" width="720" height="36" fill="{c["water"]}"/>'
    bridge = (''.join(f'<rect x="{x}" y="232" width="40" height="208" fill="{c["mid"]}"/><path d="M{x - 4} 236 L{x + 20} 196 L{x + 44} 236 Z" fill="{c["mid"]}"/>'
                      for x in (140, 270))
              + f'<rect x="180" y="250" width="90" height="12" fill="{c["mid"]}"/><rect x="60" y="356" width="330" height="14" fill="{c["mid"]}"/>'
              + f'<path d="M60 356 Q 110 300 140 250 M310 250 Q 340 300 390 356" stroke="{c["mid"]}" stroke-width="5" fill="none"/>')
    big_ben = (f'<rect x="480" y="150" width="44" height="290" fill="{c["near"]}"/><rect x="472" y="172" width="60" height="62" fill="{c["near"]}"/>'
               f'<circle cx="502" cy="203" r="21" fill="#F3EEDF"/><path d="M502 203 L502 189 M502 203 L512 207" stroke="{c["near"]}" stroke-width="3"/>'
               f'<path d="M474 172 L502 74 L530 172 Z" fill="{c["near"]}"/>')
    return far, river + bridge, big_ben


def rome(c):
    far = (f'<path d="M560 380 Q 560 296 612 284 Q 664 296 664 380 Z" fill="{c["far"]}"/><rect x="606" y="256" width="12" height="30" fill="{c["far"]}"/>'
           + _roofs(380, c['far'], seed=6, step=70).replace(c['far'], c['far']))
    pines = ''.join(_umbrella_pine(x, 400, h, c['mid']) for x, h in ((60, 120), (130, 96), (650, 110)))
    arches = ''.join(f'<path d="M{x} {y + 46} L{x} {y + 14} Q {x + 13} {y} {x + 26} {y + 14} L{x + 26} {y + 46} Z" fill="{c["line"]}" fill-opacity=".45"/>'
                     for y in (310, 360) for x in range(214, 500, 36))
    colosseum = (f'<path d="M200 440 L200 296 Q 360 270 520 296 L520 330 L500 300 L490 440 Z" fill="{c["near"]}"/>{arches}'
                 + ''.join(f'<rect x="{x}" y="268" width="14" height="22" fill="{c["near"]}"/>' for x in range(210, 470, 28)))
    return far, pines, colosseum


def new_york(c):
    far = ''.join(f'<rect x="{x}" y="{440 - h}" width="{w}" height="{h}" fill="{c["far"]}"/>' for x, w, h in
                  ((0, 50, 180), (56, 40, 230), (100, 60, 160), (440, 50, 210), (494, 70, 170), (570, 46, 250), (620, 100, 150)))
    mid = ''.join(f'<rect x="{x}" y="{440 - h}" width="{w}" height="{h}" fill="{c["mid"]}"/>' + _windows(x + 6, 450 - h, w // 14, h // 30, 14, 30, 6, 12, '#F2E6C4', .5)
                  for x, w, h in ((20, 70, 120), (150, 60, 150), (480, 64, 130), (640, 70, 110)))
    empire = (f'<rect x="300" y="190" width="80" height="250" fill="{c["near"]}"/><rect x="314" y="140" width="52" height="52" fill="{c["near"]}"/>'
              f'<rect x="326" y="100" width="28" height="42" fill="{c["near"]}"/><rect x="336" y="60" width="8" height="42" fill="{c["near"]}"/>'
              f'<rect x="339" y="20" width="2" height="42" fill="{c["near"]}"/>' + _windows(308, 206, 5, 7, 14, 32, 6, 14, '#F2E6C4', .55))
    liberty = (f'<rect x="580" y="380" width="60" height="60" fill="{c["near"]}"/><path d="M596 380 L604 290 L616 290 L624 380 Z" fill="{c["accent"]}"/>'
               f'<circle cx="610" cy="280" r="11" fill="{c["accent"]}"/><path d="M616 292 L640 230 L646 232 L624 294 Z" fill="{c["accent"]}"/>'
               f'<path d="M638 214 L648 214 L643 230 Z" fill="#E7B45A"/>')
    return far, mid, empire + liberty


def tokyo(c):
    far = (f'<path d="M0 440 L0 360 L250 160 Q 290 130 330 160 L620 360 L720 380 L720 440 Z" fill="{c["far"]}"/>'
           f'<path d="M250 160 Q 290 130 330 160 L316 182 L300 168 L286 186 L270 170 Z" fill="#F6F4EE"/>')
    mid = _roofs(390, c['mid'], seed=1, step=50)
    tower = (f'<path d="M460 440 Q 488 340 506 220 L510 110 L514 50 L518 110 L522 220 Q 540 340 568 440 L548 440 Q 530 396 514 388 Q 498 396 480 440 Z" fill="{c["accent"]}"/>'
             + ''.join(f'<rect x="{514 - w / 2}" y="{y}" width="{w}" height="8" fill="#F3EEDF"/>' for y, w in ((300, 64), (210, 26), (140, 12))))
    pagoda = ''.join(f'<rect x="{150 - w / 2 + 16}" y="{y}" width="{w - 32}" height="34" fill="{c["near"]}"/>'
                     f'<path d="M{150 - w / 2} {y + 4} Q 150 {y - 16} {150 + w / 2} {y + 4} L{150 + w / 2 - 10} {y + 10} L{150 - w / 2 + 10} {y + 10} Z" fill="{c["near"]}"/>'
                     for y, w in ((400, 150), (360, 128), (320, 108), (280, 88), (240, 70)))
    return far, mid, tower + pagoda + f'<rect x="147" y="196" width="6" height="46" fill="{c["near"]}"/>'


def dubai(c):
    far = f'<path d="M0 440 L0 380 Q 160 340 320 370 Q 520 334 720 372 L720 440 Z" fill="{c["far"]}"/>'
    mid = ''.join(f'<rect x="{x}" y="{440 - h}" width="{w}" height="{h}" fill="{c["mid"]}"/>' for x, w, h in
                  ((20, 40, 160), (70, 34, 210), (110, 50, 120), (430, 40, 190), (476, 30, 140), (660, 50, 170)))
    burj = (f'<path d="M318 440 L318 360 L332 360 L332 280 L344 280 L344 190 L352 190 L352 100 L358 100 L360 10 L362 100 L368 100 L368 190 '
            f'L376 190 L376 280 L388 280 L388 360 L402 360 L402 440 Z" fill="{c["near"]}"/>')
    arab = (f'<path d="M560 440 L560 150 Q 650 210 660 440 Z" fill="{c["near"]}"/><path d="M552 440 L552 128 L560 128 L560 440 Z" fill="{c["near"]}"/>'
            f'<path d="M560 230 Q 618 260 630 300" stroke="#F3EEDF" stroke-width="3" fill="none"/>')
    return far, mid, burj + arab + _palm(230, 440, 100, c['near'])


# span is how close the zoom ends (degrees of longitude): inland cities stop where a coast or a neighbour is still in view;
# country is the Natural Earth name the map highlights; tint is the city's wash; bed is its ambience (make-sfx.py)
CITIES = {
    'florence': {'name_ar': 'فلورنسا', 'country': 'Italy', 'lon': 11.2558, 'lat': 43.7696, 'span': 3.6, 'from_span': 24, 'draw': florence, 'bed': 'bell_far',
                 'sky': '#F0D3A6', 'far': '#D9B38A', 'mid': '#C08A62', 'near': '#8E5A3A', 'line': '#5E3A24', 'accent': '#8E5A3A', 'water': '#9FB8BC'},
    'geneva': {'name_ar': 'جنيف', 'country': 'Switzerland', 'lon': 6.1432, 'lat': 46.2044, 'span': 3.0, 'from_span': 16, 'draw': geneva, 'bed': 'wind',
               'sky': '#DCE7EA', 'far': '#B7C6CC', 'mid': '#6F8790', 'near': '#3E5560', 'line': '#2C3D45', 'accent': '#5E8C6A', 'water': '#7FA4B3'},
    'vallee_de_joux': {'name_ar': 'وادي جو', 'country': 'Switzerland', 'lon': 6.2333, 'lat': 46.6167, 'span': 3.0, 'from_span': 14, 'draw': vallee_de_joux, 'bed': 'wind',
                       'sky': '#E2E8DA', 'far': '#A9B9A0', 'mid': '#7D9273', 'near': '#3F5640', 'line': '#2A3A2B', 'accent': '#3F5640', 'water': '#8FAEB4'},
    'kuwait': {'name_ar': 'الكويت', 'country': 'Kuwait', 'lon': 47.9783, 'lat': 29.3759, 'span': 1.5, 'from_span': 24, 'draw': kuwait, 'bed': 'sea',
               'sky': '#F2E2C2', 'far': '#7FA9BC', 'mid': '#C9B28C', 'near': '#3C5A6E', 'line': '#26394A', 'accent': '#2F7D8E', 'water': '#6E9FB4'},
    'paris': {'name_ar': 'باريس', 'country': 'France', 'lon': 2.3522, 'lat': 48.8566, 'span': 3.6, 'from_span': 16, 'draw': paris, 'bed': 'crowd',
              'sky': '#E3E4E2', 'far': '#BFC3C6', 'mid': '#8E979E', 'near': '#4C5660', 'line': '#2E353C', 'accent': '#4C5660', 'water': '#8FA6B0'},
    'london': {'name_ar': 'لندن', 'country': 'United Kingdom', 'lon': -0.1276, 'lat': 51.5072, 'span': 3.2, 'from_span': 14, 'draw': london, 'bed': 'crowd',
               'sky': '#DEDAD2', 'far': '#B9B1A6', 'mid': '#8C7D70', 'near': '#5A3A33', 'line': '#3A2520', 'accent': '#5A3A33', 'water': '#8A9EA4'},
    'rome': {'name_ar': 'روما', 'country': 'Italy', 'lon': 12.4964, 'lat': 41.9028, 'span': 3.2, 'from_span': 20, 'draw': rome, 'bed': 'bell_far',
             'sky': '#F1DDB8', 'far': '#D8B88E', 'mid': '#6F7550', 'near': '#A9784A', 'line': '#5E3E22', 'accent': '#A9784A', 'water': '#9FB8BC'},
    'new_york': {'name_ar': 'نيويورك', 'country': 'United States of America', 'lon': -74.006, 'lat': 40.7128, 'span': 1.6, 'from_span': 40, 'draw': new_york, 'bed': 'crowd',
                 'sky': '#DDE2E6', 'far': '#B5BEC6', 'mid': '#7D8994', 'near': '#3E4A56', 'line': '#26303A', 'accent': '#5E8C7E', 'water': '#7F9EAE'},
    'tokyo': {'name_ar': 'طوكيو', 'country': 'Japan', 'lon': 139.6917, 'lat': 35.6895, 'span': 1.6, 'from_span': 20, 'draw': tokyo, 'bed': 'crowd',
              'sky': '#EFE1D6', 'far': '#C9C0BA', 'mid': '#8C8580', 'near': '#4E4846', 'line': '#2F2A28', 'accent': '#B5483C', 'water': '#8FA6B0'},
    'dubai': {'name_ar': 'دبي', 'country': 'United Arab Emirates', 'lon': 55.2708, 'lat': 25.2048, 'span': 1.6, 'from_span': 20, 'draw': dubai, 'bed': 'wind',
              'sky': '#F3E3C4', 'far': '#E1C79A', 'mid': '#B9A27C', 'near': '#5D5446', 'line': '#3A332A', 'accent': '#5D5446', 'water': '#7FA9BC'},
}


def skyline(city: str) -> tuple[str, str, str]:
    """The three layers (far, middle, near) as complete SVG documents on the 720 x 440 card."""
    c = CITIES[city]
    wrap = lambda body: f'<svg xmlns="http://www.w3.org/2000/svg" width="{SKY_W}" height="{SKY_H}" viewBox="0 0 {SKY_W} {SKY_H}">{body}</svg>'
    return tuple(wrap(b) for b in c['draw'](c))
