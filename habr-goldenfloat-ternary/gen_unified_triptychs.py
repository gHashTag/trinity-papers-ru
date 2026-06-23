import json, os

# Russian-text variant. NOTE: deliberate canon deviation approved by user:
# panel titles/captions in Cyrillic (article language). Formulas stay ASCII math.
# Footer SHORT FORM unchanged per canon (TRINITY S3AI – φ² + φ⁻² = 3).

STYLE = (
"Recreate the EXACT visual style of image 1 and image 2 (a three-panel "
"decorative triptych in a vintage scientific engraving / 17th-century "
"natural-philosophy plate aesthetic). CRITICAL BACKGROUND OVERRIDE: the "
"background must be PURE WHITE #FFFFFF, NOT cream, NOT off-white, NOT aged "
"paper, NOT ivory, NOT beige. Plain bright white #FFFFFF only. Ignore the "
"cream paper tone of the reference images; copy everything ELSE from them but "
"force the background to pure white #FFFFFF. Style rules to copy 1:1 from the "
"reference images: (1) three vertical panels separated by thin double rules, "
"each panel topped with an identical ornate baroque cartouche frame containing "
"a centered serif title; (2) the same hand-drawn cross-hatch engraving texture "
"for every illustration in pure black ink on white; (3) a small left-corner "
"xyz coordinate axis gizmo in each panel; (4) one centered mathematical formula "
"in italic serif under each illustration; (5) one italic-serif single-line "
"caption sentence centered under each panel ending with a small fleuron "
"ornament; (6) a horizontal banner footer across the full bottom containing the "
"SHORT FORM text TRINITY S3AI \u2013 \u03c6\u00b2 + \u03c6\u207b\u00b2 = 3 "
"(Unicode em-dash and Unicode superscripts, italic serif, flanked by tiny "
"diamond/sparkle fleurons) \u2014 DO NOT add any long-form gloss; the in-project "
"plates use ONLY the short form; (7) PURE WHITE #FFFFFF background, only black "
"ink, no color, no shading washes besides hatch, NO paper texture, NO yellow "
"tint, NO cream tone. "
"CRITICAL LOGO OVERRIDE: do NOT draw any logo mark, emblem, triangle, inverted "
"triangle, badge or corner symbol anywhere in the image. The top-right corner "
"and all other corners must stay EMPTY (only the plain panel border). Ignore "
"any corner triangle/logo present in the reference images; remove it entirely."
)

# Cyrillic instruction
LANG = (
"IMPORTANT LANGUAGE RULE: all panel TITLES and all panel CAPTION sentences must "
"be rendered in RUSSIAN (Cyrillic script), spelled EXACTLY as given below, in "
"the same engraved serif lettering. Render the Cyrillic letters cleanly and "
"legibly. The mathematical FORMULA lines stay in ASCII math notation as given. "
"The footer banner stays exactly TRINITY S3AI \u2013 \u03c6\u00b2 + \u03c6\u207b\u00b2 = 3 (do not translate the footer)."
)

CLOSER = (
"Footer banner: same TRINITY S3AI line as in the references, unchanged. The "
"whole figure must be visually indistinguishable in style from image 1 and "
"image 2 EXCEPT for the background which must be PURE WHITE #FFFFFF instead of "
"cream paper, the titles/captions which are in Russian Cyrillic, and the ABSENCE "
"of any corner logo/triangle mark (corners stay empty). No color anywhere. "
"Aspect ratio is wide landscape."
)

REFS = [
 "/home/user/workspace/skills/user/canon-image-style/assets/renders/numcat-triptych-v1.png",
 "/home/user/workspace/skills/user/canon-image-style/assets/style-ref-1-triptych.jpg",
 "/home/user/workspace/skills/user/canon-image-style/assets/style-ref-2-ornament.jpg",
]

FIGS = {
 # 1. phi anchor
 "uni_1_anchor": (
   "REPLACE THE CONTENT of the three panels with this subject: the golden-ratio "
   "anchor of the GoldenFloat number formats. "
   "PANEL 1 title (Russian) ЯКОРЬ: illustration is an engraved golden-ratio "
   "spiral over a divided line segment; formula reads phi^2 + phi^-2 = 3; caption "
   "(Russian) reads Одно тождество держит всю конструкцию. "
   "PANEL 2 title (Russian) ЧИСЛА ЛЮКА: illustration is an engraved row of integer "
   "tokens 3, 7, 18, 47; formula reads L_2 = 3; caption (Russian) reads В числах "
   "Люка золотое сечение ведёт себя как целое. "
   "PANEL 3 title (Russian) СЕМЯ В ЖЕЛЕЗЕ: illustration is an engraved silicon chip "
   "die stamped with a hex constant; formula reads dot4 = 0x47C0; caption (Russian) "
   "reads Константа-семя, зашитая в Verilog."
 ),
 # 2. GF ladder
 "uni_2_ladder": (
   "REPLACE THE CONTENT of the three panels with this subject: one law generates "
   "the whole ladder of GoldenFloat formats. "
   "PANEL 1 title (Russian) ТРИ ПОЛЯ: illustration is an engraved horizontal bit "
   "ruler split into labelled regions S, E, M; formula reads S + E + M = N; caption "
   "(Russian) reads Любой float это знак, экспонента и мантисса. "
   "PANEL 2 title (Russian) ЕДИНЫЙ ЗАКОН: illustration is an engraved gear coupling "
   "exponent bits to mantissa bits; formula reads E / M -> 1 / phi; caption (Russian) "
   "reads Сплит выводится из золотого сечения, а не вкусом. "
   "PANEL 3 title (Russian) ЛЕСТНИЦА: illustration is an engraved ascending staircase "
   "whose steps are labelled GF4 GF8 GF16 GF32; formula reads N = 4 .. 1024 bits; "
   "caption (Russian) reads Один закон порождает все ширины формата."
 ),
 # 3. GF16 measured
 "uni_3_gf16": (
   "REPLACE THE CONTENT of the three panels with this subject: the one format "
   "measured end to end, GF16. "
   "PANEL 1 title (Russian) ЭТАЛОН: illustration is an engraved frozen anchor "
   "stamped 1+6+9; formula reads GF16 = 1 + 6 + 9; caption (Russian) reads "
   "Единственная ступень, доведённая до конца. "
   "PANEL 2 title (Russian) ЗАМЕР: illustration is an engraved bar chart of four "
   "bars of slightly different height labelled f32 f16 GF16 bf16; formula reads "
   "val_bpb, меньше лучше; caption (Russian) reads GF16 измеримо обходит bfloat16 "
   "на этой задаче. "
   "PANEL 3 title (Russian) ЧЕСТНАЯ РАМКА: illustration is an engraved hand holding "
   "a small label tag reading status; formula reads только один результат; caption "
   "(Russian) reads Не победа над всеми, а один честный замер."
 ),
 # 4. Setun / balanced ternary
 "uni_4_setun": (
   "REPLACE THE CONTENT of the three panels with this subject: the Setun ternary "
   "computer and balanced ternary. "
   "PANEL 1 title (Russian) СЕТУНЬ 1958: illustration is an engraved 1950s mainframe "
   "cabinet with ferrite cores and punched tape; formula reads digits in {-1, 0, +1}; "
   "caption (Russian) reads Первая в мире электронная троичная ЭВМ, МГУ. "
   "PANEL 2 title (Russian) ТРИТ: illustration is three engraved toggle switches each "
   "set to minus, zero, plus; formula reads weight = 3^i; caption (Russian) reads "
   "Трит несёт три состояния там, где бит несёт два. "
   "PANEL 3 title (Russian) ИЗЯЩЕСТВО: illustration is an engraved beam balance scale "
   "leaning left centre right beside a mirror; formula reads знак = старший трит; "
   "caption (Russian) reads Смена знака это просто инверсия разрядов."
 ),
 # 5. Return / BitNet + golden limit
 "uni_5_return": (
   "REPLACE THE CONTENT of the three panels with this subject: the modern return of "
   "ternary logic and its place as the golden two-bit limit. "
   "PANEL 1 title (Russian) ВЕСА LLM: illustration is an engraved grid of neural "
   "network weights each marked minus zero plus; formula reads log2(3) = 1.585 bits; "
   "caption (Russian) reads Современные модели хранят веса в трёх состояниях. "
   "PANEL 2 title (Russian) БЕЗ УМНОЖЕНИЯ: illustration is an engraved hand choosing "
   "between three levers labelled add skip subtract; formula reads x*w in {-x, 0, +x}; "
   "caption (Russian) reads Умножение на троичный вес не требует умножителя. "
   "PANEL 3 title (Russian) ЗОЛОТОЙ ПРЕДЕЛ: illustration is an engraved ruler whose "
   "smallest mark is labelled phi, beside a triangle of three points; formula reads "
   "{-phi, 0, +phi}; caption (Russian) reads Та же идея как 2-битный предел φ-семейства."
 ),
}

os.makedirs("/tmp/uni", exist_ok=True)
for slug, content in FIGS.items():
    payload = {
        "prompt": STYLE + "\n\n" + LANG + "\n\n" + content + "\n\n" + CLOSER,
        "images": REFS,
        "aspect_ratio": "16:9",
        "model": "gpt_image_2",
        "filename": slug,
    }
    p = f"/tmp/uni/{slug}.json"
    json.dump(payload, open(p, "w"), ensure_ascii=False)
    print("WROTE", p)
