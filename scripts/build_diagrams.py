"""Render standalone structural overview cards for the three flagship records."""
from html import escape
from pathlib import Path


INK = "#262522"
PAPER = "#f8f4ea"
ORANGE = "#bf451d"
LABELS = {
    "xiaomi-glasses": ("小米 AI 眼镜", "重建示意", "佩戴者左右已标明，模块位置依据公开拆解，尺寸与比例为近似。", [
        ("frame", "镜框与铰链", 332, 251), ("left-arm", "左镜腿壳体", 539, 111),
        ("right-arm", "右镜腿壳体", 132, 111), ("camera", "左侧摄像头", 495, 210),
        ("board", "左镜腿主板", 491, 145), ("battery", "右镜腿电池组", 166, 146),
        ("flex", "镜框排线", 349, 188), ("speakers", "镜腿扬声器", 143, 181),
    ]),
    "xiaozhi-esp32": ("小智 ESP32 语音样机", "重建示意", "依据立创白色套件实物及开发板资料，内部模块位置为示意。", [
        ("shell", "原配白色外壳", 162, 92), ("board", "立创实战派 S3", 348, 221),
        ("mic", "模拟麦克风", 495, 216), ("speaker", "扬声器", 109, 224),
        ("display", "IPS 彩屏", 395, 115), ("camera", "GC0308 摄像头", 209, 102),
    ]),
    "xiaomi-speaker-pro": ("Xiaomi 智能音箱 Pro", "重建示意", "依据 OH2P 实物拆解，前后和两侧部件分开绘制，比例为近似。", [
        ("shell", "织物外壳", 114, 166), ("top", "顶盖与副板", 344, 98),
        ("board", "背面音频主板", 520, 179), ("speaker", "正面全频扬声器", 300, 167),
        ("radiators", "两侧无源辐射器", 421, 222), ("chamber", "独立音腔", 347, 239),
        ("io", "底部接口小板", 367, 275),
    ]),
}

GLASSES = """
<g class="caption" text-anchor="middle">
  <text x="150" y="85">佩戴者右侧</text>
  <text x="520" y="85">佩戴者左侧</text>
</g>
<g class="trace">
  <path d="M155 174l31 43m339-43-33 43M149 195l34 37m351-37-43 37"/>
  <path d="M160 108l29 94m315-94-32 94"/>
</g>
<g class="object" fill="#454544">
  <path d="M85 104l107 6 15 16-34 3-88-12q-10-6 0-13Z"/>
  <path d="M585 104l-107 6-15 16 34 3 88-12q10-6 0-13Z"/>
</g>
<g class="object">
  <rect x="143" y="139" width="61" height="16" rx="5" fill="#8a8884"/>
  <path d="M181 141v12m8-12v12" class="detail"/>
  <path d="M475 139h58l11 7-8 11h-61l-8-7Z" fill="#78919a"/>
  <path d="M482 144h11v7h-11m18-7h16v7h-16m21-7h9" class="detail"/>
  <rect x="129" y="174" width="27" height="15" rx="6" fill="#d9d0c0"/>
  <rect x="522" y="174" width="27" height="15" rx="6" fill="#d9d0c0"/>
  <path d="M134 181h16m377 0h16" class="detail"/>
</g>
<path d="M180 209l31-18h102l24 11 24-11h99l30 17" fill="none" stroke="#bf451d" stroke-width="3" stroke-dasharray="4 4"/>
<path class="object" fill="#383938" fill-rule="evenodd"
 d="M176 224q5-13 20-15 42-7 92 0 29 3 49 18 18-15 47-18 49-7 92 0 15 3 19 15l-9 42q-4 15-22 18-38 6-78 0-26-4-35-25l-8-15q-7-8-14 0l-8 15q-9 21-35 25-40 6-78 0-18-3-22-18Zm20 3q-6 2-5 8l6 24q3 12 14 13 37 5 72 0 19-3 26-18l7-14q-11-11-29-13-51-7-91 0Zm280 0q-40-7-91 0-18 2-29 13l7 14q7 15 26 18 35 5 72 0 11-1 14-13l6-24q1-6-5-8Z"/>
<g class="object">
  <circle cx="188" cy="221" r="5" fill="#dfd9c5"/>
  <circle cx="487" cy="221" r="7" fill="#252925"/>
  <circle cx="487" cy="221" r="3.5" fill="#78919a"/>
</g>
<text x="86" y="254" class="caption">录制指示灯</text>
<path d="M146 249l26-8 13-16" class="trace"/>
"""

TOY = """
<g class="trace">
  <path d="M161 172l33 27m219-28-15 24M120 210l71-9m229 7 52 6"/>
</g>
<g class="object">
  <rect x="147" y="85" width="284" height="102" rx="13" fill="#d7d9d5"/>
  <rect x="147" y="81" width="284" height="96" rx="13" fill="#f1f2ee"/>
  <rect x="228" y="91" width="188" height="75" rx="5" fill="#242627"/>
  <rect x="237" y="97" width="169" height="62" rx="3" fill="#434951"/>
  <circle cx="181" cy="106" r="9" fill="#262f32"/>
  <circle cx="181" cy="106" r="4" fill="#75928f"/>
  <rect x="226" y="179" width="29" height="4" rx="1" fill="#555853"/>
  <rect x="267" y="179" width="24" height="4" rx="1" fill="#555853"/>
</g>
<g fill="#777a75">
  <circle cx="170" cy="129" r="1.5"/><circle cx="177" cy="129" r="1.5"/><circle cx="184" cy="129" r="1.5"/><circle cx="191" cy="129" r="1.5"/>
  <circle cx="170" cy="136" r="1.5"/><circle cx="177" cy="136" r="1.5"/><circle cx="184" cy="136" r="1.5"/><circle cx="191" cy="136" r="1.5"/>
  <circle cx="170" cy="143" r="1.5"/><circle cx="177" cy="143" r="1.5"/><circle cx="184" cy="143" r="1.5"/><circle cx="191" cy="143" r="1.5"/>
  <circle cx="170" cy="150" r="1.5"/><circle cx="177" cy="150" r="1.5"/><circle cx="184" cy="150" r="1.5"/><circle cx="191" cy="150" r="1.5"/>
</g>
<g class="object">
  <path d="M191 204h203l29 22-27 23H215l-24-17Z" fill="#5e7875"/>
  <rect x="249" y="211" width="54" height="23" rx="2" fill="#d4d7d1"/>
  <rect x="314" y="218" width="23" height="13" rx="2" fill="#323835"/>
  <path d="M203 212h24m-16 23h25m125-22h26m-27 19h34" class="detail"/>
  <rect x="92" y="209" width="62" height="33" rx="8" fill="#565a55"/>
  <rect x="99" y="216" width="48" height="20" rx="8" fill="#888985"/>
  <rect x="466" y="215" width="18" height="13" rx="3" fill="#b7b5a6"/>
  <rect x="502" y="215" width="18" height="13" rx="3" fill="#b7b5a6"/>
</g>
<text x="174" y="278" class="caption">开发板及音频模块 · 相对布局示意</text>
"""

SPEAKER = """
<defs>
  <pattern id="speaker-weave" width="5" height="5" patternUnits="userSpaceOnUse">
    <rect width="5" height="5" fill="#464847"/>
    <path d="M0 0l5 5m0-5-5 5" stroke="#85847c" stroke-opacity=".4" stroke-width=".55"/>
  </pattern>
</defs>
<g class="trace">
  <path d="M180 130h65m-64 117h65m142-80h87m-88 62h87M273 105v25m90-24v24m-87 126v15m89-16v16"/>
</g>
<g class="object">
  <rect x="86" y="122" width="99" height="142" rx="17" fill="url(#speaker-weave)"/>
  <path d="M87 139q0-18 18-18h60q18 0 19 18q-18 6-49 6-26 0-48-6Z" fill="#535655"/>
  <path d="M99 138h73" fill="none" stroke="#ab9281"/>
</g>
<g class="object">
  <path d="M251 128h123l20 19v89l-18 18H249l-7-10V140Z" fill="#535654"/>
  <path d="M255 141h101v101H255Z" fill="#6e706b"/>
  <path d="M356 141l18-13 20 19v89l-18 18-20-12Z" fill="#3b3f3d"/>
  <circle cx="302" cy="172" r="29" fill="#a58e81"/>
  <circle cx="302" cy="172" r="23" fill="#393d3c"/>
  <circle cx="302" cy="172" r="15" fill="#777a77"/>
  <circle cx="302" cy="172" r="8" fill="#3b3c3a"/>
</g>
<g class="object">
  <rect x="214" y="174" width="22" height="61" rx="10" fill="#686b66"/>
  <rect x="219" y="181" width="12" height="47" rx="6" fill="#a5a097"/>
  <rect x="410" y="174" width="22" height="61" rx="10" fill="#686b66"/>
  <rect x="415" y="181" width="12" height="47" rx="6" fill="#a5a097"/>
</g>
<g class="object">
  <rect x="485" y="144" width="75" height="93" rx="5" fill="#456c82"/>
  <rect x="504" y="161" width="35" height="28" rx="2" fill="#e1dace"/>
  <rect x="499" y="198" width="14" height="16" rx="2" fill="#bfc5bf"/>
  <path d="M493 151h15m31 41h13m-30 27h29m-57 9h29" class="detail"/>
</g>
<g class="object">
  <rect x="261" y="85" width="113" height="24" rx="10" fill="#d8d6cd"/>
  <path d="M266 100h102" fill="none" stroke="#a17063" stroke-width="2"/>
  <circle cx="298" cy="93" r="1.8" fill="#373834"/>
  <circle cx="311" cy="93" r="1.8" fill="#373834"/>
  <circle cx="324" cy="93" r="1.8" fill="#373834"/>
  <rect x="262" y="266" width="110" height="16" rx="5" fill="#444846"/>
  <rect x="279" y="271" width="26" height="6" rx="2" fill="#b8b8ab"/>
  <circle cx="328" cy="274" r="3.5" fill="#b8b8ab"/>
</g>
<g class="caption" text-anchor="middle">
  <text x="132" y="281">整机轮廓</text>
  <text x="318" y="299">音腔正面</text>
  <text x="522" y="255">背面</text>
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
    #{slug}-root .caption {{ font-size: 12px; fill: #6d6257; }}
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
