# GoldenFloat φ-ladder + Сетунь/Брусенцов (научно-популярная статья для Habr)

Научно-популярная статья (на русском): семейство числовых форматов GoldenFloat от 2 до 1024 бит, выведенное из золотого сечения, и его нижний 2-битный предел — балансная троичность «Сетуни» Н. П. Брусенцова. Посвящается памяти Н. П. Брусенцова (1925–2014).

Препринт по GoldenFloat: [arXiv:2606.05017](https://arxiv.org/abs/2606.05017).

## Файлы

- `habr_article_unified.md` — статья с относительными ссылками на картинки (`images/...`).
- `habr_article_unified_github_links.md` — та же статья с **постоянными raw-ссылками** на картинки (можно вставлять прямо в редактор Habr, картинки подтянутся с GitHub).
- `images/uni_1..5_*.png` — пять иллюстраций-триптихов.
- `gen_unified_triptychs.py` — генератор триптихов.

## Постоянные ссылки на картинки (raw)

| № | Раздел | Постоянная ссылка |
|---|--------|-------------------|
| 1 | φ-якорь / числа Люка | https://raw.githubusercontent.com/gHashTag/trinity-papers-ru/main/habr-goldenfloat-ternary/images/uni_1_anchor.png |
| 2 | Лестница форматов | https://raw.githubusercontent.com/gHashTag/trinity-papers-ru/main/habr-goldenfloat-ternary/images/uni_2_ladder.png |
| 3 | Замер GF16 | https://raw.githubusercontent.com/gHashTag/trinity-papers-ru/main/habr-goldenfloat-ternary/images/uni_3_gf16.png |
| 4 | Сетунь 1958 | https://raw.githubusercontent.com/gHashTag/trinity-papers-ru/main/habr-goldenfloat-ternary/images/uni_4_setun.png |
| 5 | Возвращение троичности (BitNet) | https://raw.githubusercontent.com/gHashTag/trinity-papers-ru/main/habr-goldenfloat-ternary/images/uni_5_return.png |

## Как опубликовать на Habr

1. Открыть `habr_article_unified_github_links.md` — в нём картинки уже идут постоянными raw-ссылками.
2. Скопировать тело статьи в редактор Habr (Markdown).
3. При желании заменить raw-ссылки на загрузку в Habrastorage — но и raw-ссылки GitHub работают как постоянные.

## Честная рамка

End-to-end измерен только GF16 (паритет с float16, измеримо лучше bfloat16 на одной задаче). Остальные ступени — спецификация и, где-то, RTL. Чип-каталог Corona — submission-ready дизайн (RTL + GDS + формальные доказательства + cocotb), проверенный в симуляции и формально; изготовленного кристалла нет. Все утверждения под статус-метками `Verified` / `Empirical fit` / `Open conjecture`.

— Dmitrii Vasilev, Trinity S³AI. ORCID [0009-0008-4294-6159](https://orcid.org/0009-0008-4294-6159). Связь: admin@t27.ai
