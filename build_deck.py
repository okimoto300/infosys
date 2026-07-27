# -*- coding: utf-8 -*-
"""
SEC-STD-001 v1.3「サービス／ITシステム停止基準」
ポンチ絵中心のプレゼン資料ビルドスクリプト
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.oxml.ns import qn

# ---------- palette ----------
NAVY      = RGBColor(0x1A, 0x2F, 0x52)
NAVY_L    = RGBColor(0x24, 0x40, 0x6E)
ACCENT    = RGBColor(0x2F, 0x6D, 0xB3)
BG        = RGBColor(0xF4, 0xF6, 0xF9)
PAPER     = RGBColor(0xFF, 0xFF, 0xFF)
INK       = RGBColor(0x24, 0x29, 0x2F)
MUTED     = RGBColor(0x6B, 0x72, 0x80)
LINE      = RGBColor(0xD8, 0xDE, 0xE6)
CARD      = RGBColor(0xF7, 0xF9, 0xFC)
L0 = RGBColor(0x8A, 0x94, 0x9E)
L1 = RGBColor(0xD2, 0x9B, 0x00)
L2 = RGBColor(0xE0, 0x7B, 0x00)
L3 = RGBColor(0xD4, 0x3F, 0x3F)
L4 = RGBColor(0x8F, 0x1D, 0x1D)
OK = RGBColor(0x2E, 0x7D, 0x4F)
LIGHT_BLUE = RGBColor(0xE8, 0xEE, 0xF6)
LIGHT_ORG  = RGBColor(0xFD, 0xF3, 0xE7)
LIGHT_RED  = RGBColor(0xFB, 0xEE, 0xEE)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

JP = "Yu Gothic"        # 見出し・本文（Windows想定。無ければ既定に）
JP_MONO = "Consolas"

EMU = 914400
SW, SH = Inches(13.333), Inches(7.5)

prs = Presentation()
prs.slide_width  = SW
prs.slide_height = SH
BLANK = prs.slide_layouts[6]


# ---------- helpers ----------
def slide():
    s = prs.slides.add_slide(BLANK)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, SH)
    bg.fill.solid(); bg.fill.fore_color.rgb = BG
    bg.line.fill.background()
    bg.shadow.inherit = False
    _send_back(s, bg)
    return s

def _send_back(s, shp):
    sp = shp._element
    sp.getparent().remove(sp)
    s.shapes._spTree.insert(2, sp)

def _set_font(run, size, color, bold=False, font=JP, italic=False):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    run.font.name = font
    rPr = run._r.get_or_add_rPr()
    ea = rPr.find(qn('a:ea'))
    if ea is None:
        ea = rPr.makeelement(qn('a:ea'), {}); rPr.append(ea)
    ea.set('typeface', font)

def textbox(s, x, y, w, h, lines, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
            wrap=True, space_after=2):
    """lines: list of (text, size, color, bold[, font]) or list of such -> paragraphs"""
    tb = s.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = wrap
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Pt(2)
    tf.margin_top = tf.margin_bottom = Pt(1)
    first = True
    for ln in lines:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = align
        p.space_after = Pt(space_after)
        p.space_before = Pt(0)
        segs = ln if isinstance(ln, list) else [ln]
        for seg in segs:
            txt, size, color, bold = seg[0], seg[1], seg[2], seg[3]
            font = seg[4] if len(seg) > 4 else JP
            r = p.add_run(); r.text = txt
            _set_font(r, size, color, bold, font)
    return tb

def box(s, x, y, w, h, fill, line_color=None, line_w=1.0, radius=0.08,
        shape=MSO_SHAPE.ROUNDED_RECTANGLE, shadow=False):
    sp = s.shapes.add_shape(shape, x, y, w, h)
    if fill is None:
        sp.fill.background()
    else:
        sp.fill.solid(); sp.fill.fore_color.rgb = fill
    if line_color is None:
        sp.line.fill.background()
    else:
        sp.line.color.rgb = line_color; sp.line.width = Pt(line_w)
    sp.shadow.inherit = False
    if shadow:
        el = sp._element.spPr
        ef = el.makeelement(qn('a:effectLst'), {})
        sh = el.makeelement(qn('a:outerShdw'),
             {'blurRad':'40000','dist':'20000','dir':'5400000','rotWithShape':'0'})
        clr = el.makeelement(qn('a:srgbClr'), {'val':'1A2F52'})
        alpha = el.makeelement(qn('a:alpha'), {'val':'22000'})
        clr.append(alpha); sh.append(clr); ef.append(sh); el.append(ef)
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        try:
            sp.adjustments[0] = radius
        except Exception:
            pass
    return sp

def box_text(s, x, y, w, h, fill, lines, line_color=None, line_w=1.0,
             radius=0.08, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
             shape=MSO_SHAPE.ROUNDED_RECTANGLE, shadow=False):
    sp = box(s, x, y, w, h, fill, line_color, line_w, radius, shape, shadow)
    tf = sp.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Pt(6)
    tf.margin_top = tf.margin_bottom = Pt(4)
    first = True
    for ln in lines:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = align
        p.space_after = Pt(2); p.space_before = Pt(0)
        segs = ln if isinstance(ln, list) else [ln]
        for seg in segs:
            r = p.add_run(); r.text = seg[0]
            _set_font(r, seg[1], seg[2], seg[3], seg[4] if len(seg) > 4 else JP)
    return sp

def arrow(s, x, y, w, h, color=NAVY, direction='right'):
    shp = {'right':MSO_SHAPE.RIGHT_ARROW,'down':MSO_SHAPE.DOWN_ARROW,
           'left':MSO_SHAPE.LEFT_ARROW,'up':MSO_SHAPE.UP_ARROW}[direction]
    a = s.shapes.add_shape(shp, x, y, w, h)
    a.fill.solid(); a.fill.fore_color.rgb = color
    a.line.fill.background()
    a.shadow.inherit = False
    return a

def chevron(s, x, y, w, h, fill, lines):
    sp = box(s, x, y, w, h, fill, shape=MSO_SHAPE.CHEVRON)
    tf = sp.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = Pt(14); tf.margin_right = Pt(4)
    first = True
    for ln in lines:
        p = tf.paragraphs[0] if first else tf.add_paragraph(); first = False
        p.alignment = PP_ALIGN.CENTER; p.space_after = Pt(0)
        for seg in (ln if isinstance(ln, list) else [ln]):
            r = p.add_run(); r.text = seg[0]
            _set_font(r, seg[1], seg[2], seg[3])
    return sp

def circle(s, x, y, d, fill, lines, line_color=None):
    sp = s.shapes.add_shape(MSO_SHAPE.OVAL, x, y, d, d)
    sp.fill.solid(); sp.fill.fore_color.rgb = fill
    if line_color: sp.line.color.rgb = line_color; sp.line.width = Pt(1.5)
    else: sp.line.fill.background()
    sp.shadow.inherit = False
    tf = sp.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    first = True
    for ln in lines:
        p = tf.paragraphs[0] if first else tf.add_paragraph(); first = False
        p.alignment = PP_ALIGN.CENTER; p.space_after = Pt(0)
        for seg in (ln if isinstance(ln, list) else [ln]):
            r = p.add_run(); r.text = seg[0]
            _set_font(r, seg[1], seg[2], seg[3])
    return sp

def title_bar(s, no, title, sub=None):
    box(s, Inches(0), Inches(0), SW, Inches(1.02), NAVY, shape=MSO_SHAPE.RECTANGLE)
    box_text(s, Inches(0.45), Inches(0.24), Inches(0.62), Inches(0.54), ACCENT,
             [[(no, 20, WHITE, True)]], radius=0.2)
    ln = [[(title, 23, WHITE, True)]]
    textbox(s, Inches(1.25), Inches(0.14), Inches(11.4), Inches(0.5), ln,
            anchor=MSO_ANCHOR.MIDDLE)
    if sub:
        textbox(s, Inches(1.27), Inches(0.6), Inches(11.4), Inches(0.36),
                [[(sub, 12, RGBColor(0xB9,0xCB,0xE4), False)]])

def footer(s, n):
    textbox(s, Inches(0.4), Inches(7.08), Inches(9), Inches(0.3),
            [[("SEC-STD-001 v1.3 ｜ サービス／ITシステム停止基準", 9, MUTED, False)]])
    textbox(s, Inches(12.2), Inches(7.08), Inches(0.9), Inches(0.3),
            [[(str(n), 9, MUTED, False)]], align=PP_ALIGN.RIGHT)

PAGE = [0]
def endslide(s):
    PAGE[0] += 1
    if PAGE[0] > 1:
        footer(s, PAGE[0])


# =====================================================================
# 1. COVER
# =====================================================================
s = slide()
box(s, 0, 0, SW, SH, NAVY, shape=MSO_SHAPE.RECTANGLE)
# decorative band
box(s, 0, Inches(5.6), SW, Inches(1.9), NAVY_L, shape=MSO_SHAPE.RECTANGLE)
box(s, Inches(0.9), Inches(1.1), Inches(3.4), Inches(0.42), None,
    line_color=RGBColor(0x9A,0xB4,0xD8), line_w=1.2, radius=0.5)
textbox(s, Inches(0.9), Inches(1.13), Inches(3.4), Inches(0.36),
        [[("規程 ｜ セキュリティ標準", 12, RGBColor(0xDB,0xE6,0xF5), True)]],
        align=PP_ALIGN.CENTER)
textbox(s, Inches(0.85), Inches(2.0), Inches(11.6), Inches(1.5),
        [[("サービス／ITシステム", 40, WHITE, True)],
         [("停止基準", 40, WHITE, True)]])
textbox(s, Inches(0.9), Inches(3.9), Inches(11), Inches(0.9),
        [[("― フロンティアAIによるゼロデイ／Nデイ脅威への", 17, RGBColor(0xB9,0xCB,0xE4), False)],
         [("　能動的な停止判断・停止手順の整備 ―", 17, RGBColor(0xB9,0xCB,0xE4), False)]])
# meta cells
metas = [("文書番号","SEC-STD-001"),("版数","v1.3"),
         ("制定日","2026-07-03"),("見直し","年1回／改定の都度")]
mx = Inches(0.9)
for i,(k,v) in enumerate(metas):
    x = mx + Inches(3.0)*i
    box_text(s, x, Inches(5.9), Inches(2.75), Inches(1.05),
             RGBColor(0x1F,0x37,0x60),
             [[(k, 11, RGBColor(0xA8,0xBD,0xD9), True)],[(v, 17, WHITE, True)]],
             radius=0.1)
textbox(s, Inches(0.9), Inches(6.98), Inches(11), Inches(0.4),
        [[("直感的に理解するためのポンチ絵版プレゼン資料", 12, RGBColor(0x8D,0xA5,0xC9), False)]])
endslide(s)

# =====================================================================
# 2. なぜ今これが必要か（背景：AIによる脅威変化）
# =====================================================================
s = slide()
title_bar(s, "1", "なぜ今、この基準が必要か", "金融庁・日本銀行 連名要請（別添⑧）が背景")
# 上段：AIによる時間軸の圧縮
textbox(s, Inches(0.5), Inches(1.2), Inches(12.3), Inches(0.4),
        [[("フロンティアAIが「脆弱性発見 → 攻撃」の時間を劇的に短縮する", 16, NAVY, True)]])
# before line
box_text(s, Inches(0.5), Inches(1.75), Inches(1.55), Inches(0.9), CARD,
         [[("従来", 14, MUTED, True)]], line_color=LINE, radius=0.12)
chevron(s, Inches(2.15), Inches(1.75), Inches(3.0), Inches(0.9), L0,
        [[("脆弱性の発見", 13, WHITE, True)]])
chevron(s, Inches(5.05), Inches(1.75), Inches(4.2), Inches(0.9), RGBColor(0xB0,0xB7,0xC0),
        [[("攻撃コード化まで数週間〜数ヶ月", 13, WHITE, True)]])
chevron(s, Inches(9.15), Inches(1.75), Inches(3.5), Inches(0.9), ACCENT,
        [[("対策の時間があった", 13, WHITE, True)]])
# after line
box_text(s, Inches(0.5), Inches(2.85), Inches(1.55), Inches(0.9), NAVY,
         [[("AI時代", 14, WHITE, True)]], radius=0.12)
chevron(s, Inches(2.15), Inches(2.85), Inches(3.0), Inches(0.9), L2,
        [[("大量に自動発見", 13, WHITE, True)]])
chevron(s, Inches(5.05), Inches(2.85), Inches(2.7), Inches(0.9), L3,
        [[("数時間で攻撃コード", 13, WHITE, True)]])
chevron(s, Inches(7.65), Inches(2.85), Inches(5.0), Inches(0.9), L4,
        [[("防御が間に合わない／スキル低い攻撃者でも高度な攻撃", 12.5, WHITE, True)]])
# 3つの想定事態
textbox(s, Inches(0.5), Inches(4.05), Inches(12), Inches(0.35),
        [[("要請が想定する3つの事態", 15, NAVY, True)]])
cards = [("🔍","脆弱性の大量発見","従来は困難だった脆弱性が短期間に大量に見つかる"),
         ("⏱","発見→攻撃の短縮","パッチ提供直後に攻撃コードが出現し得る"),
         ("⚔","攻撃の高度化","スキルの低い攻撃者でも高度な攻撃が可能に")]
for i,(ic,t,b) in enumerate(cards):
    x = Inches(0.5)+Inches(4.15)*i
    box(s, x, Inches(4.5), Inches(3.9), Inches(1.55), PAPER, line_color=LINE, shadow=True)
    textbox(s, x+Inches(0.2), Inches(4.62), Inches(3.5), Inches(0.5),
            [[(ic+"  ", 20, ACCENT, True),(t, 14, NAVY, True)]])
    textbox(s, x+Inches(0.25), Inches(5.2), Inches(3.5), Inches(0.8),
            [[(b, 12, INK, False)]])
box_text(s, Inches(0.5), Inches(6.25), Inches(12.3), Inches(0.62), LIGHT_RED,
         [[("前提：各種対策を徹底してもサイバー攻撃を防御できない可能性がある ⇒ ", 13, L4, True),
           ("「誰が・いつ・何を根拠に・どう止めるか」を予め決めておく", 13, NAVY, True)]],
         line_color=RGBColor(0xE5,0xB8,0xB8), align=PP_ALIGN.LEFT, radius=0.1)
endslide(s)

# =====================================================================
# 3. 全体像（プロセスフロー）
# =====================================================================
s = slide()
title_bar(s, "2", "本基準の全体像 ― 認識から復旧までの流れ")
steps = [("認識","事象を組織として\n知った時点\n（検知・当局・ISAC等）",ACCENT),
         ("トリガー判定","第6章 V／A／E の\nどれに該当するか\n該当番号を特定",NAVY),
         ("レベル決定","L0〜L4 と\n遮断／停止 の手段を\n権限者が決定",L2),
         ("停止実行","第9章の順序で\n証拠保全→停止\n到達不能を検証",L3),
         ("復旧","第10章の5要件を\nすべて満たしてから\n逆順で段階復旧",OK)]
n = len(steps); gap = Inches(0.18)
bw = (SW - Inches(1.0) - gap*(n-1)) / n
for i,(t,b,c) in enumerate(steps):
    x = Inches(0.5) + (bw+gap)*i
    box_text(s, x, Inches(1.7), bw, Inches(0.6), c,
             [[(t, 15, WHITE, True)]], radius=0.12)
    box_text(s, x, Inches(2.35), bw, Inches(1.55), PAPER,
             [[(l, 11.5, INK, False)] for l in b.split("\n")],
             line_color=c, line_w=1.5, radius=0.08, anchor=MSO_ANCHOR.MIDDLE)
    if i < n-1:
        arrow(s, x+bw-Inches(0.02), Inches(2.9), Inches(0.22), Inches(0.45),
              color=MUTED, direction='right')
# 貫く原則
textbox(s, Inches(0.5), Inches(4.15), Inches(12), Inches(0.35),
        [[("全工程を貫く2つの判断軸", 15, NAVY, True)]])
box(s, Inches(0.5), Inches(4.55), Inches(6.05), Inches(2.1), LIGHT_BLUE, line_color=ACCENT, radius=0.06)
textbox(s, Inches(0.75), Inches(4.68), Inches(5.6), Inches(1.9),
        [[("① どのレベルまで止めるか", 14, NAVY, True)],
         [("　縮退 → 外部遮断 → 全面停止", 12.5, INK, False)],
         [("　迷ったら強い停止側へ倒す", 12.5, L3, True)],
         [("", 4, INK, False)],
         [("② どの手段で止めるか", 14, NAVY, True)],
         [("　侵害痕跡なし → 遮断・隔離を優先", 12.5, OK, True)],
         [("　痕跡あり → 隔離・停止まで踏み込む", 12.5, L3, True)]])
box(s, Inches(6.75), Inches(4.55), Inches(6.05), Inches(2.1), LIGHT_ORG, line_color=L2, radius=0.06)
textbox(s, Inches(7.0), Inches(4.68), Inches(5.6), Inches(1.9),
        [[("時間との勝負（AI時代の前提）", 14, RGBColor(0x8A,0x52,0x00), True)],
         [("・「PoC未公開」「スコア低い」を見送りの", 12.5, INK, False)],
         [("　根拠にしない", 12.5, INK, False)],
         [("・攻撃成立の ", 12.5, INK, False),("蓋然性", 12.5, L3, True),("で評価する", 12.5, INK, False)],
         [("・パッチ公開＝攻撃コード出現の起点", 12.5, INK, False)],
         [("・夜間休日でも判断できるよう権限を", 12.5, INK, False)],
         [("　事前委譲（事後報告可）", 12.5, INK, False)]])
endslide(s)

# =====================================================================
# 4. 停止レベル L0-L4（階段図）
# =====================================================================
s = slide()
title_bar(s, "3", "停止レベルの定義 ― 段階的に強くする", "第5章：複数該当時は最も高いレベルを適用")
levels = [("L0","通常運用","通常監視",L0),
          ("L1","警戒","監視強化・ログ保全・仮想パッチ / サービス影響なし",L1),
          ("L2","部分停止（縮退）","該当機能・APIのみ無効化・レート制限",L2),
          ("L3","外部接続遮断","インターネット側を遮断・内部業務は継続",L3),
          ("L4","全面停止","静止点確保・バックアップ後に全停止",L4)]
# staircase
base_y = Inches(6.35)
step_h = Inches(0.62)
bw = Inches(2.15)
for i,(lv,name,desc,c) in enumerate(levels):
    x = Inches(0.7) + Inches(2.35)*i
    h = step_h*(i+1) + Inches(0.55)
    y = base_y - h
    box(s, x, y, bw, h, c, radius=0.06)
    textbox(s, x, y+Inches(0.08), bw, Inches(0.5),
            [[(lv, 22, WHITE, True)]], align=PP_ALIGN.CENTER)
    textbox(s, x, y+Inches(0.6), bw, Inches(0.4),
            [[(name, 13, WHITE, True)]], align=PP_ALIGN.CENTER)
    textbox(s, x, y+h-Inches(0.9), bw, Inches(0.85),
            [[(desc, 10.5, WHITE, False)]], align=PP_ALIGN.CENTER,
            anchor=MSO_ANCHOR.BOTTOM)
# up arrow behind
textbox(s, Inches(0.7), Inches(1.35), Inches(11), Inches(0.4),
        [[("← 弱い（可用性を優先）", 12, MUTED, True),
          ("　　　　　　　　　　　　　　　　　　　　　　　　　　", 12, MUTED, False),
          ("強い（被害防止を優先）→", 12, L4, True)]])
box_text(s, Inches(0.7), Inches(6.55), Inches(12.1), Inches(0.62), LIGHT_ORG,
         [[("証拠保全：L3以上では停止前に揮発性情報を保全（第9.3）。保全と被害拡大防止が両立しない時は ", 12, INK, False),
           ("被害拡大防止（遮断）を優先", 12, L2, True)]],
         line_color=L2, align=PP_ALIGN.LEFT, radius=0.1)
endslide(s)

# =====================================================================
# 5. トリガー（発動基準）と判断期限
# =====================================================================
s = slide()
title_bar(s, "4", "停止発動トリガー ― 3つの起因と判断期限", "第6章：該当したら指定レベル以上を発動（Must）")
groups = [("V","脆弱性起因","ゼロデイ／Nデイ",ACCENT,
           [("V-1","認証不要で悪用可能な重大脆弱性・即時対策不可","L2","4時間",L2),
            ("V-2","KEV登録・EPSS0.5+・PoC公開・悪用観測","L3","2時間",L3),
            ("V-3","自組織製品での実際の悪用を観測","L3","1時間",L3),
            ("V-4","Nデイ期間に攻撃コード出現・仮想パッチ不可","L2","2時間",L2),
            ("V-5","EOL製品に重大脆弱性・恒久対策なし","L2+","24h計画",L2)]),
          ("A","攻撃検知起因","痕跡を検知",L3,
           [("A-1","既存シグネチャ外の不審挙動・ゼロデイ疑い","L2","即時",L2),
            ("A-2","Webシェル・権限昇格の痕跡","L3","即時",L3),
            ("A-3","不正クエリ成功・機微情報の外部送信兆候","L4","即時",L4),
            ("A-4","認証基盤の侵害（クレデンシャル不正利用）","L4","即時",L4),
            ("A-5","ランサムウェア・ワイパー等の破壊挙動","L4","即時",L4)]),
          ("E","外部要因起因","外からの契機",MUTED,
           [("E-1","当局・日銀・警察からの停止要請","L2+","―",L2),
            ("E-2","利用中SaaS・外部APIの侵害公表","L3","―",L3),
            ("E-3","サプライチェーン攻撃（OSS等混入）","L3","―",L3),
            ("E-4","共同運営システムの他機関で侵害","L3","―",L3)]),]
colw = Inches(4.05)
for gi,(gk,gt,gsub,gc,rows) in enumerate(groups):
    x = Inches(0.45) + Inches(4.28)*gi
    box_text(s, x, Inches(1.28), colw, Inches(0.66), gc,
             [[(gk+"  "+gt, 15, WHITE, True)],[(gsub, 10.5, WHITE, False)]], radius=0.1)
    for ri,(code,cond,lv,dl,lc) in enumerate(rows):
        y = Inches(2.02) + Inches(0.92)*ri
        box(s, x, y, colw, Inches(0.85), PAPER, line_color=LINE, line_w=1)
        textbox(s, x+Inches(0.08), y+Inches(0.05), Inches(0.9), Inches(0.35),
                [[(code, 12, gc, True, JP_MONO)]])
        # level & deadline badges
        box_text(s, x+colw-Inches(1.4), y+Inches(0.06), Inches(0.6), Inches(0.3),
                 lc, [[(lv, 11, WHITE, True)]], radius=0.2)
        if dl != "―":
            textbox(s, x+colw-Inches(0.78), y+Inches(0.08), Inches(0.72), Inches(0.3),
                    [[(dl, 10, L3, True)]], align=PP_ALIGN.CENTER)
        textbox(s, x+Inches(0.08), y+Inches(0.36), colw-Inches(0.18), Inches(0.48),
                [[(cond, 10.5, INK, False)]])
box_text(s, Inches(0.45), Inches(6.72), Inches(12.4), Inches(0.5), LIGHT_RED,
         [[("AI補正ルール：CVSSスコアだけで判断しない／パッチ公開＝攻撃コード出現の起点とみなす", 12, L4, True)]],
         line_color=RGBColor(0xE5,0xB8,0xB8), radius=0.1)
endslide(s)

# =====================================================================
# 6. 遮断 vs 停止 の使い分け（キー概念）
# =====================================================================
s = slide()
title_bar(s, "5", "遮断 vs システム停止の使い分け", "基本方針④ 遮断優先の原則（第9.2）")
# 分岐図
circle(s, Inches(5.7), Inches(1.35), Inches(1.9), NAVY,
       [[("侵害痕跡は", 14, WHITE, True)],[("あるか？", 14, WHITE, True)]])
# 左：痕跡なし
arrow(s, Inches(4.7), Inches(2.45), Inches(1.0), Inches(0.35), color=OK, direction='left')
textbox(s, Inches(3.0), Inches(2.05), Inches(2.4), Inches(0.4),
        [[("痕跡なし（V系）", 13, OK, True)]], align=PP_ALIGN.RIGHT)
box(s, Inches(0.5), Inches(2.95), Inches(5.9), Inches(3.05), RGBColor(0xEC,0xF6,0xF0),
    line_color=OK, line_w=1.5, radius=0.05)
textbox(s, Inches(0.75), Inches(3.08), Inches(5.5), Inches(0.5),
        [[("→ 遮断・隔離を第一選択", 16, OK, True)]])
textbox(s, Inches(0.8), Inches(3.6), Inches(5.4), Inches(2.3),
        [[("外部からの悪用が脅威 ⇒ 攻撃経路（外部到達性）を断てば", 12.5, INK, False)],
         [("停止と同等のリスク低減。加えて──", 12.5, INK, False)],
         [("  ✓ 停止・再起動に伴う障害リスクがない", 12.5, NAVY, True)],
         [("  ✓ メモリ・プロセスが保全され調査しやすい", 12.5, NAVY, True)],
         [("  ✓ 内部業務を継続できる", 12.5, NAVY, True)],
         [("  ✓ 復旧は遮断解除のみで速い", 12.5, NAVY, True)],
         [("", 5, INK, False)],
         [("前提：経路の網羅（専用線・SaaS・保守回線・帯域外通信）。", 11.5, L2, True)],
         [("網羅の確証がなければ確実な「停止」側へ倒す。", 11.5, L2, True)]])
# 右：痕跡あり
arrow(s, Inches(7.6), Inches(2.45), Inches(1.0), Inches(0.35), color=L3, direction='right')
textbox(s, Inches(7.9), Inches(2.05), Inches(2.6), Inches(0.4),
        [[("痕跡あり（A系）", 13, L3, True)]])
box(s, Inches(6.9), Inches(2.95), Inches(5.9), Inches(3.05), LIGHT_RED,
    line_color=L3, line_w=1.5, radius=0.05)
textbox(s, Inches(7.15), Inches(3.08), Inches(5.5), Inches(0.5),
        [[("→ 隔離・停止まで踏み込む", 16, L3, True)]])
textbox(s, Inches(7.2), Inches(3.6), Inches(5.4), Inches(2.3),
        [[("攻撃者が内部に足場を持つと、境界遮断だけでは", 12.5, INK, False)],
         [("横展開・時限起動・内部破壊が継続し得る。", 12.5, INK, False)],
         [("  ✓ 対象セグメントを内外両方向で隔離", 12.5, NAVY, True)],
         [("  ✓ 破壊活動が進行中ならホスト停止まで", 12.5, NAVY, True)],
         [("　　（サスペンド・電源断を含む）", 12, NAVY, False)],
         [("", 6, INK, False)],
         [("手段の階層：ネットワーク隔離 → 正常停止 →", 11.5, L4, True)],
         [("ハイバネーション/サスペンド → 強制電源断（最終手段）", 11.5, L4, True)]])
endslide(s)

# =====================================================================
# 7. 判断権限と緊急単独発動
# =====================================================================
s = slide()
title_bar(s, "6", "誰が止めるか ― 判断権限と緊急単独発動", "第8章：夜間・休日でも判断できるよう事前委譲")
# 権限ピラミッド（レベルごと）
rows = [("L1","警戒","当直運用責任者","→ システム管理責任者",L1),
        ("L2","部分停止","CSIRT責任者／システム管理責任者","→ CISO",L2),
        ("L3","外部遮断","CISO","→ 経営トップ（速やかに）",L3),
        ("L4","全面停止","CISO（経営トップへ即時報告）","→ 経営トップ・取締役会",L4)]
textbox(s, Inches(0.5), Inches(1.2), Inches(7), Inches(0.35),
        [[("レベルが上がるほど判断者も上位へ", 14, NAVY, True)]])
for i,(lv,nm,who,report,c) in enumerate(rows):
    y = Inches(1.65) + Inches(1.02)*i
    box_text(s, Inches(0.5), y, Inches(0.95), Inches(0.9), c,
             [[(lv, 20, WHITE, True)]], radius=0.12)
    box(s, Inches(1.55), y, Inches(6.2), Inches(0.9), PAPER, line_color=c, line_w=1.5)
    textbox(s, Inches(1.7), y+Inches(0.1), Inches(6), Inches(0.4),
            [[(nm+"： ", 12, MUTED, True),(who, 13.5, NAVY, True)]])
    textbox(s, Inches(1.7), y+Inches(0.5), Inches(6), Inches(0.35),
            [[("事後報告 "+report, 11.5, INK, False)]])
# 右：緊急単独発動
box(s, Inches(8.1), Inches(1.65), Inches(4.75), Inches(2.85), LIGHT_RED,
    line_color=L3, line_w=1.5, radius=0.05)
textbox(s, Inches(8.35), Inches(1.8), Inches(4.4), Inches(0.6),
        [[("⚡ 緊急時の単独発動", 16, L4, True)]])
textbox(s, Inches(8.4), Inches(2.35), Inches(4.3), Inches(2.1),
        [[("A-3〜A-5（データ流出進行中・認証基盤", 12, INK, False)],
         [("侵害・破壊的攻撃）に該当する場合──", 12, INK, False)],
         [("検知者は上位承認を待たず", 13, L4, True)],
         [("L4相当の遮断を実施してよい", 13, L4, True)],
         [("", 5, INK, False)],
         [("✓ 承認待ちによる被害拡大の責任は", 11.5, NAVY, True)],
         [("　発動者に帰さない（免責）", 11.5, NAVY, True)],
         [("✓ 誤検知による停止も懲戒対象外", 11.5, NAVY, True)]])
box(s, Inches(8.1), Inches(4.65), Inches(4.75), Inches(1.75), LIGHT_BLUE,
    line_color=ACCENT, radius=0.05)
textbox(s, Inches(8.35), Inches(4.78), Inches(4.4), Inches(1.55),
        [[("👔 経営トップの関与", 15, NAVY, True)],
         [("能動的停止は経営判断事項。", 12, INK, False)],
         [("経営トップは本基準と各シナリオを", 12, INK, False)],
         [("事前了知し、L4発動を遅滞なく", 12, INK, False)],
         [("追認できる状態を保つ。", 12, INK, False)]])
endslide(s)

# =====================================================================
# 8. 停止順序（末端 → 認証基盤は最後）
# =====================================================================
s = slide()
title_bar(s, "7", "停止の順序 ― 末端から、認証基盤は最後", "第9.1：停止作業自体が依存する基盤を最後まで残す")
order = [("1","新規受付の停止","入口で新規セッション遮断（既存処理は継続）",ACCENT),
         ("2","業務アプリケーション","仕掛かり取引の完了/取消を待ち静止点を確保",ACCENT),
         ("3","ジョブ・バッチ・連携基盤","実行中ジョブの再開点を記録して停止",ACCENT),
         ("4","データベース","静止点確認・バックアップ取得後に正常停止",ACCENT),
         ("5","監視・ログ基盤","停止完了を見届けてから停止",ACCENT),
         ("6","認証基盤（AD/SSO/IDaaS/特権ID）","必ず最後。復旧は逆順で最初に立ち上げ",L4)]
for i,(no,t,b,c) in enumerate(order):
    y = Inches(1.35) + Inches(0.7)*i
    circle(s, Inches(0.55), y, Inches(0.5), c, [[(no, 16, WHITE, True)]])
    fill = LIGHT_RED if i==5 else PAPER
    box(s, Inches(1.2), y, Inches(6.55), Inches(0.56), fill, line_color=c, line_w=1.3)
    textbox(s, Inches(1.35), y+Inches(0.02), Inches(6.3), Inches(0.3),
            [[(t, 12.5, NAVY, True)]])
    textbox(s, Inches(1.35), y+Inches(0.29), Inches(6.3), Inches(0.26),
            [[(b, 10.5, INK, False)]])
    if i<5:
        arrow(s, Inches(0.72), y+Inches(0.5), Inches(0.16), Inches(0.22), color=MUTED, direction='down')
# 右：理由と例外
box(s, Inches(8.05), Inches(1.35), Inches(4.8), Inches(2.55), LIGHT_BLUE,
    line_color=ACCENT, radius=0.05)
textbox(s, Inches(8.28), Inches(1.48), Inches(4.4), Inches(2.4),
        [[("なぜ認証基盤が最後か", 15, NAVY, True)],
         [("各システムの停止操作・管理コンソール", 12, INK, False)],
         [("へのログイン自体が認証基盤に依存。", 12, INK, False)],
         [("先に止めると停止作業そのものが", 12, INK, False)],
         [("実行不能になる。", 12, INK, False)],
         [("", 4, INK, False)],
         [("→ ブレークグラスアカウント（各システムの", 11.5, NAVY, True)],
         [("　ローカル緊急ID）と帯域外管理経路で担保", 11.5, NAVY, True)]])
box(s, Inches(8.05), Inches(4.05), Inches(4.8), Inches(2.35), LIGHT_RED,
    line_color=L3, radius=0.05)
textbox(s, Inches(8.28), Inches(4.18), Inches(4.4), Inches(2.2),
        [[("⚠ 例外：認証基盤自体が侵害（シナリオ5）", 13.5, L4, True)],
         [("停止ではなく ネットワーク隔離 を先行。", 12, INK, False)],
         [("停止作業はブレークグラスIDで継続する。", 12, INK, False)],
         [("", 5, INK, False)],
         [("侵害された認証基盤を動かしたまま他を", 12, INK, False)],
         [("止めると、攻撃者に停止作業を妨害・", 12, INK, False)],
         [("監視される恐れがある。", 12, INK, False)]])
endslide(s)

# =====================================================================
# 9. 揮発性情報の保全（証拠保全）
# =====================================================================
s = slide()
title_bar(s, "8", "揮発性情報の保全 ― 消えやすい順に取る", "第9.3：RFC 3227に準拠（L3以上は停止前に取得）")
vol = [("1","メモリダンプ","暗号鍵・ファイルレスマルウェアはメモリにしか無い場合あり。仮想はハイパーバイザのスナップショット/サスペンドで",L4),
       ("2","ネットワーク状態","アクティブ接続・ARP/ルーティング・DNSキャッシュ",L3),
       ("3","プロセス・セッション","実行中プロセスの親子関係・ログオン中セッション・オープンファイル",L2),
       ("4","ディスクイメージ","隔離後に書き込み防止措置のうえ取得",L1),
       ("5","各種ログ","FW・プロキシ・認証・EDRのログを改ざん不能な別系統へ即時退避",L0)]
# inverted funnel look: widths decreasing
for i,(no,t,b,c) in enumerate(vol):
    y = Inches(1.4) + Inches(0.92)*i
    w = Inches(9.0)
    circle(s, Inches(0.6), y, Inches(0.6), c, [[(no, 18, WHITE, True)]])
    box(s, Inches(1.4), y, w, Inches(0.78), PAPER, line_color=c, line_w=1.5)
    textbox(s, Inches(1.6), y+Inches(0.05), w-Inches(0.4), Inches(0.35),
            [[(t, 13.5, NAVY, True)]])
    textbox(s, Inches(1.6), y+Inches(0.4), w-Inches(0.4), Inches(0.35),
            [[(b, 11, INK, False)]])
# side arrow (volatile high -> low)
arrow(s, Inches(10.75), Inches(1.5), Inches(0.55), Inches(4.5), color=NAVY, direction='down')
textbox(s, Inches(11.4), Inches(1.6), Inches(1.8), Inches(0.6),
        [[("揮発性", 13, NAVY, True)],[("高い", 13, L4, True)]])
textbox(s, Inches(11.4), Inches(5.3), Inches(1.8), Inches(0.6),
        [[("揮発性", 13, NAVY, True)],[("低い", 13, ACCENT, True)]])
box_text(s, Inches(1.4), Inches(6.35), Inches(9.0), Inches(0.55), LIGHT_ORG,
         [[("取得証拠はハッシュ記録・隔離保管し、取扱記録（Chain of Custody）を残す（当局報告・保険請求に使用し得る）", 11.5, INK, True)]],
         line_color=L2, radius=0.1)
endslide(s)

# =====================================================================
# 10. 想定シナリオ集（一覧ポンチ絵）
# =====================================================================
s = slide()
title_bar(s, "9", "想定シナリオ集 ― 年次演習の題材", "第7章：いずれも過去に類似事案。AIで短時間・高頻度化")
scn = [("1","公開WebにゼロデイRCE","Struts2 / Log4Shell","L2→L3",L3),
       ("2","VPN・境界機器の悪用","Fortinet / Ivanti / Citrix","L3",L3),
       ("3","パッチ直後のNデイ攻撃","ProxyLogon / MOVEit","L1→L2",L2),
       ("4","OSSサプライチェーン混入","XZ Utils / Codecov","L3",L3),
       ("5","認証基盤の侵害兆候","AD侵害 / Okta","L4",L4),
       ("6","ランサムウェア展開","国内医療・港湾・製造","L4",L4),
       ("7","大量脆弱性の同時公表","要請が想定する事態","L2〜L3",L2),
       ("8","共同運営/クラウド側侵害","共同センター波及","L3",L3)]
cols=4
cw=Inches(3.0); ch=Inches(2.35)
gx=Inches(0.2); gy=Inches(0.22)
x0=Inches(0.45); y0=Inches(1.3)
for i,(no,t,ex,lv,c) in enumerate(scn):
    r=i//cols; col=i%cols
    x=x0+(cw+gx)*col; y=y0+(ch+gy)*r
    box(s, x, y, cw, ch, PAPER, line_color=LINE, shadow=True)
    box(s, x, y, cw, Inches(0.15), c, radius=0.0, shape=MSO_SHAPE.RECTANGLE)
    circle(s, x+Inches(0.15), y+Inches(0.28), Inches(0.55), c, [[(no,18,WHITE,True)]])
    box_text(s, x+cw-Inches(1.15), y+Inches(0.32), Inches(1.0), Inches(0.42), c,
             [[(lv, 12, WHITE, True)]], radius=0.15)
    textbox(s, x+Inches(0.15), y+Inches(0.95), cw-Inches(0.3), Inches(0.9),
            [[(t, 13, NAVY, True)]])
    textbox(s, x+Inches(0.15), y+ch-Inches(0.55), cw-Inches(0.3), Inches(0.5),
            [[("実例：", 10, MUTED, True),(ex, 10, INK, False)]])
endslide(s)

# =====================================================================
# 11. 復旧基準
# =====================================================================
s = slide()
title_bar(s, "10", "復旧（停止解除）基準", "第10章：5要件をすべて満たすまで引き下げ不可")
checks = ["原因脆弱性へのパッチ／検証済み緩和策の実装が完了",
          "侵害調査完了・バックドア排除・影響範囲のクレデンシャル全数リセット",
          "再発検知手段（シグネチャ・監視ルール）を実装",
          "発動時と同格以上の権限者が再開を承認",
          "再開後24時間はL1相当の警戒を維持"]
for i,c in enumerate(checks):
    y=Inches(1.45)+Inches(0.72)*i
    circle(s, Inches(0.55), y, Inches(0.5), OK, [[("✓",18,WHITE,True)]])
    box(s, Inches(1.2), y, Inches(6.9), Inches(0.56), PAPER, line_color=OK, line_w=1.3)
    textbox(s, Inches(1.4), y+Inches(0.06), Inches(6.6), Inches(0.44),
            [[(c, 12.5, INK, True)]], anchor=MSO_ANCHOR.MIDDLE)
# 復旧順序（停止の逆順）
box(s, Inches(8.4), Inches(1.45), Inches(4.45), Inches(4.15), LIGHT_BLUE,
    line_color=ACCENT, radius=0.05)
textbox(s, Inches(8.65), Inches(1.58), Inches(4), Inches(0.4),
        [[("復旧の順序（停止の逆順）", 14, NAVY, True)]])
rec=[("認証基盤・監視基盤",L4),("データベース",L3),("連携基盤",L2),
     ("業務アプリケーション",L1),("外部公開",ACCENT)]
for i,(t,c) in enumerate(rec):
    y=Inches(2.1)+Inches(0.66)*i
    box_text(s, Inches(8.7), y, Inches(3.85), Inches(0.5), c,
             [[(t, 13, WHITE, True)]], radius=0.1)
    if i<4:
        arrow(s, Inches(10.5), y+Inches(0.5), Inches(0.14), Inches(0.16), color=NAVY, direction='down')
endslide(s)

# =====================================================================
# 12. 平時の準備義務
# =====================================================================
s = slide()
title_bar(s, "11", "平時の準備義務 ― これが無いと発動できない", "第12章：基準を機能させる8つの備え")
prep=[("📋","優先システムの特定と台帳","SBOM・NW構成を最新化。脆弱性公表時に1時間以内で該当判定"),
      ("🧹","技術負債の解消","不要ポート閉塞・不要特権ID削除・未適用パッチ・EOL更改"),
      ("📡","脆弱性情報の常時監視","JVN/NVD/KEV/EPSS/ISAC/当局を日次以上で監視"),
      ("🛡","多層防御の維持","WAF仮想パッチ・EDR・NW分離・特権IDのMFA（停止以外の選択肢）"),
      ("🤝","ベンダー契約の点検","夜間休日の対応可否・SLA・リソース確保状況"),
      ("🎯","停止・復旧演習","年1回以上、経営トップ参加の机上＋実機。BG口座も検証"),
      ("☎","連絡網の維持","権限者・代行・ベンダー・当局窓口を四半期ごと検証"),
      ("💾","バックアップの隔離","オフライン/イミュータブル。L4がデータ全損に直結しない")]
cols=2
cw=Inches(6.1); ch=Inches(1.28); gx=Inches(0.2); gy=Inches(0.16)
for i,(ic,t,b) in enumerate(prep):
    r=i//cols; col=i%cols
    x=Inches(0.45)+(cw+gx)*col; y=Inches(1.35)+(ch+gy)*r
    box(s, x, y, cw, ch, PAPER, line_color=LINE, shadow=True)
    box_text(s, x+Inches(0.12), y+Inches(0.28), Inches(0.7), Inches(0.7), LIGHT_BLUE,
             [[(ic, 20, ACCENT, True)]], radius=0.2)
    textbox(s, x+Inches(0.95), y+Inches(0.12), cw-Inches(1.1), Inches(0.45),
            [[(str(i+1)+". "+t, 13.5, NAVY, True)]])
    textbox(s, x+Inches(0.95), y+Inches(0.55), cw-Inches(1.1), Inches(0.65),
            [[(b, 11, INK, False)]])
endslide(s)

# =====================================================================
# 13. まとめ
# =====================================================================
s = slide()
box(s, 0, 0, SW, SH, NAVY, shape=MSO_SHAPE.RECTANGLE)
box(s, 0, 0, Inches(0.25), SH, ACCENT, shape=MSO_SHAPE.RECTANGLE)
textbox(s, Inches(0.85), Inches(0.7), Inches(11), Inches(0.7),
        [[("まとめ ― 本基準が徹底する5つの考え方", 26, WHITE, True)]])
pts=[("被害防止を可用性より優先","漏えい・改ざん・不正資金移動の蓋然性が高いなら止める。迷ったら強い停止側へ。"),
     ("遮断を停止より優先（手段の選択）","侵害痕跡がなければ遮断・隔離で同等の効果。経路を網羅できない時だけ停止に倒す。"),
     ("AI時代の時間前提","「PoC未公開/スコア低い」を見送りの根拠にしない。パッチ公開＝攻撃出現の起点。"),
     ("止められる態勢を平時に作る","権限の事前委譲・ブレークグラス・帯域外経路・年次演習・台帳整備が発動を支える。"),
     ("説明責任","停止・非停止いずれも判断者/時刻/根拠を記録し、当局報告に耐える形で保全。")]
for i,(t,b) in enumerate(pts):
    y=Inches(1.7)+Inches(1.02)*i
    circle(s, Inches(0.9), y, Inches(0.6), ACCENT, [[(str(i+1),22,WHITE,True)]])
    textbox(s, Inches(1.75), y-Inches(0.02), Inches(11), Inches(0.5),
            [[(t, 17, WHITE, True)]])
    textbox(s, Inches(1.77), y+Inches(0.42), Inches(10.9), Inches(0.55),
            [[(b, 12.5, RGBColor(0xB9,0xCB,0xE4), False)]])
endslide(s)

out = "/home/user/infosys/SEC-STD-001_停止基準_ポンチ絵プレゼン.pptx"
prs.save(out)
print("saved:", out, "slides:", len(prs.slides._sldIdLst))
