"""Render standalone structural overview cards for the three flagship records."""
from html import escape
from pathlib import Path


INK = "#262522"
PAPER = "#f8f4ea"
ORANGE = "#bf451d"
LABELS = {
    "xiaomi-glasses": ("小米 AI 眼镜", "重建示意", "依据公开拆解整理位置关系，形状与比例为近似。", [
        ("frame", "镜框与铰链", 273, 224), ("left-arm", "左镜腿壳体", 109, 111),
        ("right-arm", "右镜腿壳体", 563, 111), ("camera", "摄像头模组", 485, 212),
        ("board", "左镜腿主板", 165, 148), ("battery", "右镜腿电池组", 518, 148),
        ("flex", "镜框排线", 347, 196), ("speakers", "镜腿扬声器", 158, 194),
    ]),
    "xiaozhi-esp32": ("小智 ESP32 语音样机", "原创概念", "依据参考板资料构思装配，外壳尺寸与固定点待实物验证。", [
        ("shell", "原创外壳", 133, 257), ("board", "立创实战派 S3", 276, 195),
        ("mic", "双模拟麦克风", 435, 186), ("speaker", "音腔喇叭", 470, 247),
        ("display", "IPS 彩屏", 331, 110),
    ]),
    "xiaomi-speaker-pro": ("Xiaomi 智能音箱 Pro", "重建示意", "依据 OH2P 公开拆解整理位置关系，音腔与零件比例为近似。", [
        ("shell", "外壳与织物罩", 154, 167), ("top", "顶部副板与盖板", 348, 103),
        ("board", "音频主板", 524, 198), ("speaker", "全频扬声器", 318, 219),
        ("radiators", "两侧无源辐射器", 409, 218),
    ]),
}

GLASSES = """
<g class="trace">
  <path d="M154 170L184 228M532 170l-48 58M135 197l49 40M541 194l-58 44"/>
  <path d="M159 107l30 96M507 107l-32 94"/>
</g>
<g class="object" fill="#dfd7c9">
  <path d="M85 104l107 6 15 16-34 3-88-12q-10-6 0-13Z"/>
  <path d="M585 104l-107 6-15 16 34 3 88-12q10-6 0-13Z"/>
</g>
<g class="object">
  <path d="M142 139h58l11 7-8 11h-61l-8-7Z" fill="#f0c6b2"/>
  <path d="M148 144h11v7h-11m20-7h18v7h-18m25-7h7" fill="none"/>
  <rect x="475" y="140" width="63" height="16" rx="7" fill="#dfd7c9"/>
  <path d="M485 144v8m45-8v8" class="detail"/>
  <rect x="128" y="184" width="26" height="15" rx="6" fill="#d9d0c0"/>
  <rect x="523" y="184" width="26" height="15" rx="6" fill="#d9d0c0"/>
  <path d="M134 190h14m381 0h14" class="detail"/>
</g>
<path d="M182 221h-19l-12 12m33-19 27-18h102l24 11 24-11h99l30 17 25 16" fill="none" stroke="#bf451d" stroke-width="3" stroke-dasharray="4 4"/>
<path class="object" fill="#e4dbcc" fill-rule="evenodd"
 d="M177 226q4-13 20-15 43-6 92 0 29 3 47 18 18-15 47-18 49-6 92 0 17 2 20 15l-9 39q-5 16-22 19-38 6-78 0-26-4-35-26l-8-14q-7-8-14 0l-8 14q-9 22-35 26-40 6-78 0-17-3-22-19Zm19 2q-6 2-5 8l6 24q3 12 14 13 37 5 72 0 19-3 26-18l7-14q-11-11-29-13-51-7-91 0Zm280 0q-40-7-91 0-18 2-29 13l7 14q7 15 26 18 35 5 72 0 11-1 14-13l6-24q1-6-5-8Z"/>
<g class="object" fill="#f1c2ad">
  <rect x="481" y="207" width="17" height="16" rx="4"/>
  <circle cx="489.5" cy="215" r="4.5" fill="#f8f4ea"/>
</g>
"""

TOY = """
<g class="trace">
  <path d="M202 238V130m241 98V128M223 202v54m221-51v42m34-36v38"/>
</g>
<path class="object" d="M129 244q0-10 10-10h320q12 0 12 12v37q0 15-15 15H145q-16 0-16-15Z" fill="#d8cebd"/>
<path class="object" d="M137 244q0-6 9-6h310q8 0 8 7v27q0 7-9 7H147q-10 0-10-7Z" fill="#eee6d7"/>
<path class="detail" d="M156 280h291m-258-28h64m-64 6h64m-64 6h64"/>
<g class="object" fill="#e7ded0">
  <path d="M190 180h230l16 8-13 21H204l-14-8Z"/>
  <path d="M200 184h218l8 5-7 13H206l-6-5Z" fill="#f2c6b2"/>
  <rect x="262" y="187" width="47" height="11" rx="2" fill="#f7e3d7"/>
  <path d="M212 188h10m-10 7h22m86-8h26m-26 7h34" class="detail"/>
</g>
<g class="object" fill="#d4c8b6">
  <circle cx="448" cy="183" r="6"/><circle cx="462" cy="183" r="6"/>
  <circle cx="448" cy="183" r="2" fill="#f8f4ea"/><circle cx="462" cy="183" r="2" fill="#f8f4ea"/>
  <ellipse cx="481" cy="248" rx="25" ry="16"/>
  <ellipse cx="481" cy="247" rx="18" ry="11" fill="#f8f4ea"/>
  <ellipse cx="481" cy="247" rx="8" ry="4" fill="#e1d5c3"/>
</g>
<g class="object">
  <rect x="174" y="92" width="299" height="48" rx="13" fill="#e4dbcc"/>
  <rect x="225" y="99" width="194" height="31" rx="6" fill="#363735"/>
  <rect x="236" y="105" width="172" height="20" rx="3" fill="#5d625c"/>
  <path d="M242 115h39l7-5 7 9 8-6 8 2h89" fill="none" stroke="#e7d5bb"/>
</g>
"""

SPEAKER = """
<g class="trace">
  <path d="M177 134H531m-338 115h341M279 128v17m101-15v18m58 19h58m-52 54h56"/>
</g>
<g class="object">
  <path d="M124 145q0-13 17-16h62q17 2 17 17v117q-1 16-19 18h-60q-17-3-17-17Z" fill="#dfd6c7"/>
  <path d="M124 145q6 10 23 10h49q16-1 24-9m-96 117q6 8 22 8h49q17-1 25-8" class="detail"/>
  <path d="M138 159v103m9-100v103m10-103v103m10-103v103m10-103v103m10-103v103m10-103v103m9-106v103" class="detail"/>
</g>
<g class="object">
  <path d="M274 162q0-13 15-16h70q13 2 15 13v108q0 15-15 18h-70q-15-3-15-16Z" fill="#dfd6c7"/>
  <path d="M274 163q8 9 22 10h55q15-2 23-11" class="detail"/>
  <circle cx="324" cy="218" r="34" fill="#f0c6b2"/>
  <circle cx="324" cy="218" r="28" fill="#e5ab90"/>
  <circle cx="324" cy="218" r="15" fill="#cf8666"/>
  <circle cx="324" cy="218" r="7" fill="#b96646"/>
  <rect x="376" y="174" width="22" height="91" rx="10" fill="#d4c8b6"/>
  <rect x="415" y="174" width="22" height="91" rx="10" fill="#d4c8b6"/>
  <path d="M382 184v70m39-70v70" class="detail"/>
</g>
<g class="object">
  <rect x="497" y="154" width="59" height="113" rx="5" fill="#e0d5c3"/>
  <rect x="511" y="180" width="28" height="26" rx="3" fill="#f4eadb"/>
  <path d="M508 164h36m-37 48h39m-37 9h22m-21 11h23m-25 18h39" class="detail"/>
</g>
<g class="object">
  <path d="M279 100q0-12 14-12h67q13 0 14 12v10q-2 10-16 11h-66q-13-2-13-11Z" fill="#e7ddca"/>
  <path d="M279 100q5 9 15 9h63q11-1 17-9" class="detail"/>
  <path d="M299 98h55" stroke="#bf451d" stroke-width="2"/>
  <circle cx="311" cy="102" r="2.5" fill="#262522"/>
  <circle cx="325" cy="102" r="2.5" fill="#262522"/>
  <circle cx="339" cy="102" r="2.5" fill="#262522"/>
</g>
"""

PLATES = {"xiaomi-glasses": GLASSES, "xiaozhi-esp32": TOY, "xiaomi-speaker-pro": SPEAKER}


def render(slug, number):
    title, evidence_type, note, entries = LABELS[slug]
    marks = []
    legends = []
    for index, (part_id, name, x, y) in enumerate(entries, 1):
        marks.append(f'<g data-part-id="{part_id}" class="pin"><title>{escape(name)}</title>'
                     f'<circle cx="{x}" cy="{y}" r="10"/><text x="{x}" y="{y+3.8}">{index:02d}</text></g>')
        ly = 110 + (index - 1) * 27
        legends.append(f'<g><text class="serial" x="635" y="{ly}">{index:02d}</text>'
                       f'<text class="legend" x="664" y="{ly}">{escape(name)}</text></g>')

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" id="{slug}-root" viewBox="0 0 850 347" role="img"
     aria-labelledby="{slug}-title {slug}-desc">
<title id="{slug}-title">{escape(title)}结构总览</title>
<desc id="{slug}-desc">{escape(note)} 图例编号对应档案部件。</desc>
<defs>
  <pattern id="{slug}-grid" width="18" height="18" patternUnits="userSpaceOnUse">
    <path d="M18 0H0v18" fill="none" stroke="#e6dfd0" stroke-width="0.8"/>
  </pattern>
  <style>
    #{slug}-root text {{ font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif; fill: {INK}; }}
    #{slug}-root .legend {{ font-size: 16px; }}
    #{slug}-root .serial {{ fill: {ORANGE}; font-family: "Consolas", monospace; font-size: 13px; font-weight: 700; }}
    #{slug}-root .pin circle {{ fill: {PAPER}; stroke: {ORANGE}; stroke-width: 1.4; }}
    #{slug}-root .pin text {{ fill: {ORANGE}; font-family: "Consolas", monospace; font-size: 9px; font-weight: 700; text-anchor: middle; }}
    #{slug}-root .object {{ stroke: {INK}; stroke-width: 1.6; stroke-linecap: round; stroke-linejoin: round; }}
    #{slug}-root .detail {{ fill: none; stroke: #80766b; stroke-width: 0.8; }}
    #{slug}-root .trace {{ fill: none; stroke: #9a8d7b; stroke-width: 1; stroke-dasharray: 4 4; }}
  </style>
</defs>
<rect width="850" height="347" fill="{PAPER}"/>
<text x="26" y="29" class="serial">FIG. {number:02d}</text>
<text x="112" y="30" font-size="21" font-weight="700">{escape(title)}</text>
<text x="823" y="29" text-anchor="end" font-size="13" font-weight="700" fill="{ORANGE}">{evidence_type}</text>
<path d="M26 46H824M26 308H824M615 59V296" stroke="#d8cbb8" fill="none"/>
<rect x="26" y="61" width="574" height="236" fill="url(#{slug}-grid)"/>
<g aria-hidden="true">
{PLATES[slug]}
</g>
{"".join(marks)}
<text x="635" y="79" font-size="14" font-weight="700">部件索引</text>
{"".join(legends)}
<text x="26" y="330" font-size="13" fill="#625b50">{escape(note)}</text>
<text x="824" y="330" text-anchor="end" class="serial">HARDWARE ATLAS</text>
</svg>
"""


def main():
    target = Path(__file__).resolve().parents[1] / "web/public/assets/diagrams"
    target.mkdir(parents=True, exist_ok=True)
    for index, slug in enumerate(LABELS, 1):
        (target / f"{slug}.svg").write_text(render(slug, index), encoding="utf-8")


if __name__ == "__main__":
    main()
