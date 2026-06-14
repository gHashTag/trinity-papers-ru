const fs = require('fs');
const docx = require('docx');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, HeadingLevel, BorderStyle, WidthType, ShadingType,
  VerticalAlign, PageNumber, Header, Footer, ExternalHyperlink, LevelFormat,
} = docx;

const FONT = 'Times New Roman';
const SIZE = 22; // 11pt = 22 half-points (требование «ИИ и принятие решений»)
const LINE = 360;  // 1.5 интервал (240 = single, 360 = 1.5)
const REDLINE = 283; // красная строка 0.5 см

// ---------- helpers ----------
const thin = { style: BorderStyle.SINGLE, size: 4, color: '000000' };
const borders = { top: thin, bottom: thin, left: thin, right: thin };

function P(text, opts = {}) {
  const runs = Array.isArray(text) ? text : [new TextRun({ text: String(text), font: FONT, size: SIZE, ...opts.run })];
  return new Paragraph({
    spacing: { after: opts.after !== undefined ? opts.after : 120, line: LINE, ...opts.spacing },
    alignment: opts.alignment,
    children: runs,
    ...opts.p,
  });
}

// body paragraph supporting inline runs (array of TextRun) — красная строка 0.5см, 1.5 интервал
function body(runs, opts = {}) {
  return new Paragraph({
    spacing: { after: 120, line: LINE },
    alignment: opts.alignment || AlignmentType.JUSTIFIED,
    indent: opts.noindent ? undefined : { firstLine: REDLINE },
    children: runs,
  });
}

// quick text run
function t(text, o = {}) { return new TextRun({ text, font: FONT, size: SIZE, ...o }); }
// monospace-ish (keep latin terms) -> use Consolas
function mono(text, o = {}) { return new TextRun({ text, font: 'Consolas', size: 22, ...o }); }
function b(text, o = {}) { return new TextRun({ text, font: FONT, size: SIZE, bold: true, ...o }); }
function it(text, o = {}) { return new TextRun({ text, font: FONT, size: SIZE, italics: true, ...o }); }

function H1(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 280, after: 140 },
    children: [new TextRun({ text, font: FONT, size: 30, bold: true, color: '000000' })] });
}
function H2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 220, after: 110 },
    children: [new TextRun({ text, font: FONT, size: 26, bold: true, color: '000000' })] });
}

function bullet(runs) {
  return new Paragraph({ numbering: { reference: 'bullets', level: 0 }, spacing: { after: 80, line: 276 },
    alignment: AlignmentType.JUSTIFIED, children: runs });
}
function num(runs, ref = 'steps') {
  return new Paragraph({ numbering: { reference: ref, level: 0 }, spacing: { after: 80, line: 276 },
    alignment: AlignmentType.JUSTIFIED, children: runs });
}

// Table builder. headers: array of strings. rows: array of arrays of (string | {runs}).
function makeTable(colWidths, headers, rows, opts = {}) {
  const total = colWidths.reduce((a, c) => a + c, 0);
  const headerRow = new TableRow({
    tableHeader: true,
    children: headers.map((h, i) => new TableCell({
      borders, width: { size: colWidths[i], type: WidthType.DXA },
      shading: { fill: 'FFFFFF', type: ShadingType.CLEAR },
      margins: { top: 50, bottom: 50, left: 80, right: 80 },
      verticalAlign: VerticalAlign.CENTER,
      children: [new Paragraph({ spacing: { after: 0, line: 240 }, children: [new TextRun({ text: h, font: FONT, size: opts.fs || 20, bold: true })] })],
    })),
  });
  const bodyRows = rows.map((r, ri) => new TableRow({
    children: r.map((cell, i) => {
      let children;
      if (typeof cell === 'string') {
        children = [new Paragraph({ spacing: { after: 0, line: 240 }, children: [new TextRun({ text: cell, font: FONT, size: opts.fs || 20 })] })];
      } else if (cell.mono) {
        children = [new Paragraph({ spacing: { after: 0, line: 240 }, children: [new TextRun({ text: cell.text, font: 'Consolas', size: (opts.fs || 20) - 2 })] })];
      } else {
        children = [new Paragraph({ spacing: { after: 0, line: 240 }, children: cell.runs })];
      }
      return new TableCell({
        borders, width: { size: colWidths[i], type: WidthType.DXA },
        margins: { top: 40, bottom: 40, left: 80, right: 80 },
        verticalAlign: VerticalAlign.CENTER,
        shading: undefined,
        children,
      });
    }),
  }));
  return new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: colWidths, rows: [headerRow, ...bodyRows] });
}

function caption(text) {
  return new Paragraph({ spacing: { before: 60, after: 160 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text, font: FONT, size: 20, italics: true })] });
}

const PAGE_W = 9360; // letter usable

// ============================ CONTENT ============================
const children = [];

const hr = () => new Paragraph({
  spacing: { before: 120, after: 120 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: '000000', space: 1 } },
  children: [new TextRun({ text: '', size: 2 })],
});

// ---- Шапка для редакции (титульный лист рукописи) ----
children.push(new Paragraph({ alignment: AlignmentType.LEFT, spacing: { after: 40, line: LINE },
  children: [it('В редакцию журнала «Искусственный интеллект и принятие решений»')] }));
children.push(new Paragraph({ alignment: AlignmentType.LEFT, spacing: { after: 40, line: LINE },
  children: [t('ФИЦ «Информатика и управление» РАН · научная специальность 1.2.1', { size: 20 })] }));
children.push(new Paragraph({ alignment: AlignmentType.LEFT, spacing: { after: 40, line: LINE },
  children: [t('УДК 004.222', { size: 20 })] }));
children.push(hr());

// ---- Title ----
children.push(new Paragraph({ spacing: { after: 80, before: 200 }, alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: 'Каталог из 83 численных форматов с битоточными векторами соответствия:', font: FONT, size: 32, bold: true })] }));
children.push(new Paragraph({ spacing: { after: 240 }, alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: 'вендор-нейтральный справочник для FP8, BF16, MXFP4 и микромасштабируемых форматов', font: FONT, size: 30, bold: true })] }));

// ---- Author ----
children.push(new Paragraph({ spacing: { after: 40 }, alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: 'Дмитрий Васильев (Dmitrii Vasilev)', font: FONT, size: 26, bold: true })] }));
children.push(new Paragraph({ spacing: { after: 40 }, alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: 'Независимый исследователь, Trinity S³AI', font: FONT, size: 22, italics: true })] }));
children.push(new Paragraph({ spacing: { after: 40 }, alignment: AlignmentType.CENTER,
  children: [
    new TextRun({ text: 'Контакт: ', font: FONT, size: 22 }),
    new TextRun({ text: 'admin@t27.ai', font: 'Consolas', size: 20 }),
    new TextRun({ text: '   ·   GitHub: ', font: FONT, size: 22 }),
    new TextRun({ text: 'github.com/gHashTag', font: 'Consolas', size: 20 }),
  ] }));
children.push(new Paragraph({ spacing: { after: 40 }, alignment: AlignmentType.CENTER,
  children: [
    new TextRun({ text: 'ORCID: ', font: FONT, size: 22 }),
    new ExternalHyperlink({ children: [new TextRun({ text: '0009-0008-4294-6159', style: 'Hyperlink', font: 'Consolas', size: 20 })], link: 'https://orcid.org/0009-0008-4294-6159' }),
  ] }));
children.push(new Paragraph({ spacing: { after: 240 }, alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: 'Препринт v4 · 8 июня 2026 г.', font: FONT, size: 20, italics: true })] }));

// ---- Abstract ----
children.push(new Paragraph({ spacing: { before: 120, after: 100 }, alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: 'АННОТАЦИЯ', font: FONT, size: 24, bold: true })] }));

children.push(body([
  t('Распространение численных форматов в аппаратном обеспечении для машинного обучения — FP8 (E4M3 и E5M2), BF16, MXFP4, блочные микромасштабируемые форматы и десятки исследовательских вариантов — опередило доступность вендор-нейтральных битоточных справочных материалов. Инженеры, переносящие модели между ускорителями, сталкиваются с незаметными расхождениями, которые трудно диагностировать без общей измерительной линейки.'),
]));
children.push(body([
  t('В настоящей статье описаны: каталог из 83 численных форматов, охватывающий 13 семейств; полный набор пакетов соответствия (conformance packs), покрывающий все 83 формата каталога (49 битоточных пакетов с круговой проверкой кодирования-декодирования и 34 структурных пакета для форматов без фиксированной раскладки S:E:M по основанию 2); углублённое референсное подмножество из шести пакетов уровня Tier-1 для GF16, элемента MXFP4, BF16, FP8 E4M3, FP8 E5M2 и блочного масштаба E8M0, перекрёстно проверенных относительно внешнего оракула; а также кросс-уолк к IEEE P3109 v3.2.0, сопоставляющий каждый пакет Tier-1 с соответствующей конфигурируемой формой стандарта. Каждый пакет представляет собой самодостаточный документ JSON с отпечатком SHA-256, общей схемой строк и якорным вектором, кодирующим значение 3,0 — тождество '),
  it('φ² + 1/φ² = 3'),
  t(' — в качестве межпакетной проверки корректности. Пакеты подмножества Tier-1 перекрёстно проверяются относительно '),
  mono('ml_dtypes'),
  t(' 0.5.4 (Google/JAX); любое расхождение документируется явно и интерпретируется как разрешённый спецификацией интерпретационный разрыв, а не скрывается. Работа позиционируется как заполнение реестра: она не предлагает новых форматов, не делает утверждений о точности моделей и не заявляет о превосходстве над какой-либо вендорской реализацией. Все артефакты публично доступны по адресу '),
  mono('github.com/gHashTag/t27'),
  t(' под открытой лицензией.'),
]));

// ---- Keywords ----
children.push(body([
  b('Ключевые слова: '),
  t('численные форматы, форматы с плавающей точкой, conformance, IEEE P3109, золотое сечение, машинное обучение, битоточные векторы, микромасштабирование, FP8, BF16, MXFP4.'),
]));


// === ENGLISH BLOCK (journal requirement: title/author/abstract/keywords in English) ===
children.push(new Paragraph({ spacing: { before: 200, after: 80 }, alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: 'An 83-format numeric catalog with catalog-wide conformance vectors:', font: FONT, size: 28, bold: true })] }));
children.push(new Paragraph({ spacing: { after: 160 }, alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: 'a vendor-neutral reference for FP8, BF16, MXFP4 and microscaling formats', font: FONT, size: 26, bold: true })] }));
children.push(new Paragraph({ spacing: { after: 40 }, alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: 'Dmitrii Vasilev', font: FONT, size: 24, bold: true })] }));
children.push(new Paragraph({ spacing: { after: 160 }, alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: 'Independent researcher, Trinity S\u00b3AI \u00b7 ORCID 0009-0008-4294-6159', font: FONT, size: 20, italics: true })] }));
children.push(new Paragraph({ spacing: { before: 80, after: 80 }, alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: 'ABSTRACT', font: FONT, size: 22, bold: true })] }));
children.push(body([
  t('The proliferation of numeric formats in machine-learning hardware \u2014 FP8 (E4M3 and E5M2), BF16, MXFP4, block microscaling formats and dozens of research variants \u2014 has outpaced the availability of vendor-neutral, bit-exact reference material. This paper presents: a catalog of 83 numeric formats spanning 13 families; a complete conformance-pack set covering all 83 catalog formats (49 bit-exact packs with encode-decode round-trip checking and 34 structural packs for formats that have no fixed radix-2 S:E:M layout); a deeply validated Tier-1 reference subset of six packs for GF16, the MXFP4 element, BF16, FP8 E4M3, FP8 E5M2 and the E8M0 block scale, cross-checked against an external oracle; and a crosswalk to IEEE P3109 v3.2.0 mapping each Tier-1 pack to its configurable form of the standard. Every pack is a self-contained JSON document with a SHA-256 fingerprint, a shared row schema and an anchor vector encoding the value 3.0 \u2014 the identity phi^2 + 1/phi^2 = 3 \u2014 as a cross-pack correctness check. The Tier-1 packs are cross-checked against ml_dtypes 0.5.4 (Google/JAX); any discrepancy is documented explicitly and interpreted as a specification-permitted interpretive gap rather than hidden. The work is positioned as registry-filling: it proposes no new formats, makes no model-accuracy claim and asserts no superiority over any vendor implementation. All artefacts are publicly available at github.com/gHashTag/t27 under an open license.'),
], { noindent: true }));
children.push(body([
  b('Keywords: '),
  t('numeric formats, floating point, conformance, IEEE P3109, golden ratio, machine learning, bit-exact vectors, microscaling, FP8, BF16, MXFP4.'),
], { noindent: true }));

// ---- Сведения для редакции (завершает титульный лист) ----
children.push(hr());
children.push(body([ b('Сведения для редакции. ', { size: 20 }),
  t('Статья оригинальна, ранее не публиковалась и не подавалась в другие издания. Конфликт интересов отсутствует, внешнее финансирование не привлекалось. Рукопись оформлена единым файлом MS Word (.docx) и содержит русско- и англоязычные версии названия, сведений об авторе, аннотации и ключевых слов; текст чёрно-белый, формат А4. По требованию редакции автор готов предоставить лицензионный договор (скан) и экспертное заключение о возможности открытого опубликования. Тема письма при подаче: «ИИПР Васильев». Контактная эл. почта: admin@t27.ai.', { size: 20 }) ], { noindent: true }));

// =================== 1. Introduction ===================
children.push(H1('1. Введение'));
children.push(body([
  t('Представьте себе механика, которому нужно подогнать деталь под спецификацию токарного станка, но линейка в его руках использует единицы, слегка отличающиеся от тех, что указаны на чертеже. Деталь может выглядеть правильной; расхождение проявляется только под нагрузкой. Тот же сценарий разыгрывается в прошивках ML-ускорителей: два чипа могут одновременно заявлять о «поддержке FP8 E4M3», однако незаметно различаться в обработке случая переполнения для входного значения вроде 1000,0 — один насыщается до максимального конечного значения 448,0, другой переходит в NaN. Спецификация OCP Microscaling допускает оба варианта. Без общего битоточного эталона перенесённая модель может выдавать численно различающиеся результаты, которые трудно локализовать.'),
]));
children.push(body([ t('В настоящей статье описаны два артефакта, призванные служить такой общей линейкой.') ]));

children.push(body([ b('Вклад 1: каталог из 83 численных форматов. '),
  t('Каталог '), mono('t27'), t(' перечисляет 83 численных формата в 13 семействах (раздел 3). Каждая запись несёт единообразную схему: разрядную раскладку, смещение порядка (bias), политику бесконечности/NaN, политику насыщения, максимальное конечное значение, минимальное нормальное значение, минимальное субнормальное число и метку статуса утверждения (Verified / Empirical_fit / Open_conjecture / Risk / Retracted). Каталог хранится как единый источник истины и кросс-компилируется в Markdown, JSON, Python, Rust, C и TypeScript посредством шаблонного инструмента.') ]));

children.push(body([ b('Вклад 2: полный набор пакетов соответствия на весь каталог. '),
  t('Набор пакетов (раздел 5) покрывает все 83 формата каталога — по одному пакету на формат, без пропусков. Из них 49 пакетов битоточны (нативные биты декодируются в f64 точно, с проверкой кругового кодирования-декодирования), а 34 — структурны (форматы без единой фиксированной раскладки S:E:M по основанию 2 — параметрические, табличные, по основанию 16, тейперированно-логарифмические, расширенной точности или с открытыми ИОКР-параметрами), помеченные '), mono('bitexact: false'), t(' и несущие явное поле обоснования. Внутри этого набора выделено референсное подмножество из шести пакетов уровня Tier-1, наиболее часто встречающихся в современном промышленном оборудовании и дополнительно перекрёстно проверенных относительно внешнего оракула: GoldenFloat 16 (GF16), элемент MXFP4, BF16, FP8 E4M3, FP8 E5M2 и блочный масштаб E8M0 (раздел 5, таблица 4). Два из этих пакетов (GF16 и MXFP4) уже доступны в PyPI-пакете '),
  mono('tt-lang-t27'), t(' v0.3.1; остальные четыре пакета Tier-1 и полный каталоговый набор представлены в текущем предварительном выпуске по адресу '),
  mono('github.com/gHashTag/tt-lang-t27/pull/6'), t('.') ]));

children.push(body([ b('Чем эта статья не является. '),
  t('В работе не приводятся бенчмарки точности моделей, не предлагаются новые форматы и не проводятся сравнения производительности между вендорами. Читателям, которым нужен анализ пропускной способности FLOP или результаты по точности квантования, следует обратиться к отдельной литературе.') ]));

children.push(body([ b('Структура статьи. '),
  t('Раздел 2 рассматривает соответствующий ландшафт стандартов. Раздел 3 описывает устройство каталога. Раздел 4 определяет методологию пакетов соответствия и политику покрытия всех 83 форматов. Раздел 5 представляет полный каталоговый набор и поочерёдно подробно разбирает шесть пакетов уровня Tier-1. Раздел 6 предоставляет кросс-уолк к IEEE P3109. Раздел 7 обсуждает интерпретационный разрыв как проектную особенность. Раздел 8 охватывает воспроизводимость и происхождение. Раздел 9 намечает будущую работу. Раздел 10 формулирует ограничения.') ]));

children.push(body([ b('Историческая преемственность. '),
  t('Один из шести пакетов уровня Tier-1 — GoldenFloat 16 (GF16) — относится к отечественной линии исследований оригинальных систем представления чисел, начатой троичной ЭВМ «Сетунь» под руководством Н. П. Брусенцова (Вычислительный центр МГУ, 1958) — первой в мире машиной на симметричном троичном коде (−1, 0, +1), а в «Сетунь-70» (1970) — с введённым троичным форматом «трайт» и оптимизированным диапазоном мантиссы нормализованного числа. По доступным открытым источникам, GF16 — один из первых именованных числовых форматов российского авторства, доведённых до уровня публикации и аппаратной реализации (FPGA).') ]));

// =================== 2. Background ===================
children.push(H1('2. Предпосылки и предшествующие работы'));
children.push(body([
  t('Распространение низкоточных форматов с плавающей точкой в аппаратном обеспечении для машинного обучения было охарактеризовано — ещё в популярном эссе 2017 года — как «дикий запад компьютерной арифметики». Почти десятилетие спустя ландшафт стал богаче (больше вендоров, больше блочных форматов, больше исследовательских вариантов), однако вендор-нейтральные битоточные справочные материалы не поспевают за ним.'),
]));

children.push(H2('2.1. Стандарты с плавающей точкой'));
children.push(body([
  t('IEEE 754-2019 определяет двоичные форматы обмена (binary16, binary32, binary64, binary128) и правила округления, переполнения и обработки NaN, которые ими управляют. BF16 (brain float 16) отсутствует в редакции 2019 года; он возник неформально в Google Brain и теперь поддерживается аппаратурой Intel, AMD, ARM и NVIDIA, разделяя диапазон порядка FP32 (8 бит порядка, смещение порядка = 127) с 7-битной мантиссой.'),
]));
children.push(body([
  t('Форматы FP8 прошли схожую траекторию «сначала неформально, затем формально». Нун (Noune) и др. в 2022 году провели обзор 8-битных численных форматов для глубоких нейронных сетей, мотивировав варианты E4M3 и E5M2, впоследствии принятые в OCP MX и IEEE P3109.'),
]));
children.push(body([
  t('Спецификация OCP Microscaling (MX) v1.0 вводит блочные форматы, в которых группы из 32 элементов разделяют общий масштабный множитель E8M0. Типы элементов включают MXFP4 (S1E2M1), MXFP6 (E2M3 и E3M2), MXFP8 (E4M3 и E5M2) и MXINT8. OCP MX явно допускает две политики переполнения для FP8 E4M3: насыщение до максимального конечного значения (используется в реализациях tt-metal и AMD) и переполнение в NaN (используется в JAX/TPU).'),
]));
children.push(body([
  t('NVFP4 от NVIDIA — недавний 4-битный вариант, сочетающий элемент в стиле MXFP4 (S1E2M1) с 16-элементным блоком (меньшим, чем 32-элементный блок OCP MX) и использующий блочный масштаб FP8 E4M3 вместо E8M0. На момент написания NVFP4 задокументирован в форме технического блога NVIDIA и программных стеков Blackwell/Rubin; он пока не охвачен открытой межвендорной спецификацией. M²XFP далее обобщает микромасштабирование, допуская смешанные точности элементов внутри блока, причём аппаратная реализуемость исследуется в горизонте ASPLOS ’26.'),
]));
children.push(body([
  t('IEEE P3109 — активная рабочая группа, стандартизирующая 8-битные и 4-битные форматы с плавающей точкой для задач ИИ. Её промежуточный отчёт v3.2.0 определяет Binary8p3se и Binary4p1sf (среди прочих) и каталог '),
  mono('StandardOperations.yaml'), t(' из приблизительно 80 операций в семи категориях.'),
]));

children.push(H2('2.2. Существующие эталонные реализации'));
children.push(body([ b('ml_dtypes '), t('(Google/JAX) — библиотека Python/C++, предоставляющая эталонные реализации '),
  mono('bfloat16'), t(', '), mono('float8_e4m3fn'), t(', '), mono('float8_e5m2'), t(', '), mono('float8_e8m0fnu'),
  t(' и нескольких других форматов. Она служит эталонным оракулом на протяжении всей настоящей работы.') ]));
children.push(body([ b('P3109 FLoPS '), t('— формализация семантики P3109 на Lean 4, обеспечивающая доказательно проверенное покрытие ключевых операций.') ]));
children.push(body([ b('Pychop '), t('(Carson & Chen, 2025) эмулирует широкое семейство низкоточных арифметик в Python, включая варианты FP8, posit и настраиваемые кортежи (E, M, смещение порядка). Она ориентирована на задачи ML и научных вычислений и дополняет настоящий каталог: Pychop эмулирует поведение на уровне операций, тогда как пакеты в этой статье фиксируют битовые паттерны на уровне представления.') ]));
children.push(body([ b('libtakum '), t('— эталонная C-библиотека для семейства арифметики takum (Хунхольд), обеспечивающая пригодную базу для кросс-реализации кластера Posit/Unum III каталога относительно независимого оракула.') ]));
children.push(body([ b('torch.float8 '), t('(PyTorch) и '), b('jax.dtypes '), t('предоставляют типы FP8 на уровне фреймворка, но не публикуют наборы тестов с битовыми векторами, независимые от аппаратного исполнения.') ]));
children.push(body([ b('Исследования по оценке MX '), t('измеряют влияние микромасштабируемого квантования на точность в трансформерных задачах.') ]));

children.push(H2('2.3. Разрыв'));
children.push(body([
  t('Ни один отдельный вендор-нейтральный артефакт в настоящее время не охватывает FP8 E4M3, FP8 E5M2, BF16, элемент MXFP4, элемент NVFP4, GoldenFloat 16 и блочный масштаб E8M0 в единой схеме, обладая при этом: (а) битоточными векторами кодирования/декодирования; (б) происхождением, привязанным к SHA-256; (в) явной документацией каждого расхождения с эталонной реализацией; и (г) удобочитаемым кросс-уолком к IEEE P3109. Настоящая работа заполняет этот пробел реестра на уровне всего каталога: набор пакетов соответствия покрывает все 83 формата (49 битоточных + 34 структурных), а шесть наиболее немедленно развёртываемых форматов уровня представления выделены как углублённо проверенное подмножество Tier-1 (раздел 5); NVFP4 обсуждается как ближайший кандидат на включение в Tier-1 (раздел 9) и как второй интерпретационный разрыв (раздел 7).'),
]));

// =================== 3. Catalog Design ===================
children.push(H1('3. Устройство каталога'));
children.push(H2('3.1. 83 формата в 13 кластерах'));
children.push(body([
  t('Каталог '), mono('t27'), t(' содержит 83 формата, организованных в 13 именованных кластеров. Таблица 1 показывает названия кластеров и количество форматов. Сумма количеств равна ровно 83; это непрерывно контролируемый инвариант каталога (CI-01, раздел 3.4).'),
]));

children.push(makeTable([3000, 4760, 1600],
  ['Кластер', 'Представительные форматы', 'Кол-во'],
  [
    ['IEEE754 binary', 'binary16, binary32, binary64, binary128, binary256', '5'],
    ['IEEE754 decimal', 'decimal32, decimal64, decimal128', '3'],
    ['Extended', 'x87 FP80, double-double, quad-double', '3'],
    ['ML low-precision', 'BF16, TF32, FP8 E4M3, FP8 E5M2, FP6 E3M2/E2M3, FP4 E2M1', '7'],
    ['Microscaling (MX)', 'MXFP8, MXFP6, MXFP4', '3'],
    ['Posit / Unum III', 'Posit8/16/32/64, takum8/16/32/64', '8'],
    ['LNS', 'LNS-8, LNS-16, LNS-32, LNS-64', '4'],
    ['GoldenFloat', 'GFTernary, GF4 … GF1024 (с привязкой к φ), MXGF6/MXGF4', '22'],
    ['IntegerFixed', 'INT4/8/16/32/64/128, Q-format, BCD', '8'],
    ['QuantTuned', 'NF4 (NormalFloat), AFP (Adaptive FP)', '2'],
    ['Compression/scaling', 'block FP (BFP), shared-exponent, INT8 per-channel, stochastic rounding', '4'],
    ['HistoricalVendor', 'IBM HFP, Microsoft MBF, VAX F/D/G/H-float, Cray float', '10'],
    ['Theoretical', 'minifloat, Unum I, Unum II (SORN), tapered FP', '4'],
    [{ runs: [b('Итого', { size: 20 })] }, '', { runs: [b('83', { size: 20 })] }],
  ]));
children.push(caption('Таблица 1. 83 формата в 13 кластерах (T1).'));

children.push(H2('3.2. Схема «одна строка на формат»'));
children.push(body([ t('Каждая запись каталога несёт следующие поля:') ]));
const fields = [
  [mono('name'), ' — канонический идентификатор (ASCII, без пробелов)'],
  [mono('bits'), ' — общая разрядность'],
  [mono('exp'), ' — ширина поля порядка в битах'],
  [mono('mant'), ' — ширина поля мантиссы в битах (0 для форматов в стиле E8M0)'],
  [mono('bias'), ' — смещение порядка'],
  [mono('has_inf'), ' — булево значение'],
  [mono('has_nan'), ' — булево значение'],
  [mono('saturation_policy'), { v: ' — ', code: 'SatFinite', tail: ', ' }, { code: 'OvfInf', tail: ' или ' }, { code: 'OvfNaN', tail: '' }],
  [mono('max_finite'), ' — наибольшее представимое конечное значение (f64)'],
  [mono('min_normal'), ' — наименьшее положительное нормальное значение (f64)'],
  [mono('min_subnormal'), { v: ' — наименьшее положительное субнормальное число (f64; ', code: 'null', tail: ', если отсутствует)' }],
  [mono('cluster'), ' — одна из 13 меток кластеров'],
  [mono('claim_status'), ' — Verified / Empirical_fit / Open_conjecture / Risk / Retracted'],
];
for (const f of fields) {
  const runs = [];
  for (const part of f) {
    if (typeof part === 'string') runs.push(t(part));
    else if (part instanceof TextRun) runs.push(part);
    else if (part.v !== undefined) { runs.push(t(part.v)); runs.push(mono(part.code)); runs.push(t(part.tail)); }
    else { runs.push(mono(part.code)); runs.push(t(part.tail)); }
  }
  children.push(bullet(runs));
}

children.push(H2('3.3. Таксономия статусов утверждений'));
children.push(body([ b('Verified: '), t('спецификация формата подкреплена опубликованным стандартом (IEEE, OCP) или доказательно проверенным эталоном (P3109 FLoPS Lean).') ]));
children.push(body([ b('Empirical_fit: '), t('выведена путём подгонки наблюдаемой битовой раскладки аппаратного продукта без независимо опубликованной спецификации.') ]));
children.push(body([ b('Open_conjecture: '), t('предложенное обобщение, ожидающее внешней проверки.') ]));
children.push(body([ b('Risk: '), t('ссылка на спецификацию существует, но кодировка в каталоге может содержать ошибки, ещё не выявленные набором тестов.') ]));
children.push(body([ b('Retracted: '), t('ранее была включена; удалена после выявления противоречащего авторитетного источника.') ]));

children.push(H2('3.4. Инварианты каталога'));
children.push(body([ t('Пятнадцать инвариантов проверяются при каждом коммите. Отдельные инварианты перечислены в таблице 2.') ]));

children.push(makeTable([1100, 3500, 4760],
  ['ID', 'Инвариант', 'Проверка'],
  [
    ['CI-01', 'Общее число форматов равно 83', { runs: [mono('sum(cluster_counts) == 83')] }],
    ['CI-02', 'Нет коллизий имён', { runs: [mono('len(names) == len(set(names))')] }],
    ['CI-03', 'Согласованность разрядности', { runs: [mono('1 + exp + mant == bits'), t(' для стандартной раскладки', { size: 20 })] }],
    ['CI-04', 'Диапазон смещения порядка', { runs: [mono('bias <= 2**(exp-1) - 1')] }],
    ['CI-05', 'Наличие политики насыщения', 'поле не равно null для каждой записи'],
    ['CI-06', 'Положительное max-finite', { runs: [mono('max_finite > 0')] }],
    ['CI-07', 'min-normal ≤ max-finite', 'порядок сохранён'],
    ['CI-08', 'Метка кластера из перечисления', 'нет неперечисленных имён кластеров'],
    ['CI-09', 'Статус утверждения из перечисления', 'нет неперечисленных значений статуса'],
    ['CI-10', 'Нет формата с 0 бит', { runs: [mono('bits >= 2')] }],
    ['CI-11', 'Наличие якоря SHA-256', 'заголовок каждого пакета несёт поле отпечатка'],
    ['CI-12', 'Наличие якорного вектора', { runs: [t('каждый пакет содержит вектор ', { size: 20 }), mono('anchor_*')] }],
    ['CI-13', 'Якорь декодируется в 3,0', { runs: [mono('decode(anchor_bits) == 3.0')] }],
    ['CI-14', 'Цели кодогенерации компилируются', 'CI-матрица запускает тесты импорта Python + Rust'],
    ['CI-15', 'Нет дублирующихся SHA-256', 'отпечатки пакетов глобально уникальны'],
  ], { fs: 19 }));
children.push(caption('Таблица 2. 15 инвариантов каталога (контролируемые CI) (T2).'));

children.push(H2('3.5. Путь кодогенерации'));
children.push(body([
  t('Единый шаблонный инструмент на Jinja2 читает канонический JSON-каталог и порождает выходные файлы для каждого языка: Markdown (удобочитаемая таблица), JSON (экспорт для API), классы данных Python, структуры Rust с производными '),
  mono('serde'), t(', заголовок C (константы '), mono('#define'), t(') и литералы перечислений TypeScript. Все сгенерированные файлы фиксируются в репозитории '),
  mono('github.com/gHashTag/t27'), t(' и пересобираются при каждом push посредством матрицы GitHub Actions.'),
]));

// =================== 4. Methodology ===================
children.push(H1('4. Методология пакетов соответствия'));
children.push(H2('4.1. Общая схема строк'));
children.push(body([ t('Каждый пакет соответствия представляет собой JSON-массив векторов, причём каждая строка соответствует схеме, показанной в таблице 3.') ]));

children.push(makeTable([2400, 1300, 5660],
  ['Поле', 'Тип', 'Описание'],
  [
    [{ mono: true, text: 'name' }, 'string', 'удобочитаемый идентификатор тест-случая'],
    [{ mono: true, text: 'input_f64' }, 'number', 'входное значение как число двойной точности'],
    [{ mono: true, text: 'input_f64_hex' }, 'string', 'шестнадцатеричная кодировка IEEE 754 входа (f32 или f64)'],
    [{ mono: true, text: '<fmt>_bits_hex' }, 'string', 'битовый паттерн целевого формата, hex'],
    [{ mono: true, text: '<fmt>_bits_int' }, 'integer', 'тот же битовый паттерн как беззнаковое целое'],
    [{ mono: true, text: 'decoded_f64' }, 'number', 'результат decode(encode(input))'],
    [{ mono: true, text: 'decoded_f64_hex' }, 'string', 'шестнадцатеричная кодировка IEEE 754 декодированного значения'],
    [{ mono: true, text: 'abs_error' }, 'number', '|вход − декодированное|; всегда показывается (никогда не скрывается)'],
    [{ mono: true, text: 'category' }, 'string', 'zero / normal / subnormal / inf / nan / overflow / underflow / rounding / anchor / transcendental'],
  ], { fs: 19 }));
children.push(caption('Таблица 3. Общая схема строк для всех пакетов соответствия (T3).'));

children.push(H2('4.2. Заголовок пакета'));
children.push(body([ t('Помимо массива векторов, каждый файл пакета несёт объект-заголовок со следующими полями:') ]));
children.push(bullet([ t('Четвёрка спецификации формата: (E, M, смещение порядка, политика inf/NaN)') ]));
children.push(bullet([ t('Политика насыщения') ]));
children.push(bullet([ t('Максимальное конечное значение') ]));
children.push(bullet([ t('Самоотпечаток SHA-256 (вычисленный по канонической JSON-сериализации)') ]));
children.push(bullet([ t('Якорь версии '), mono('ml_dtypes') ]));
children.push(bullet([ t('Ссылка на якорное тождество: '), mono('phi^2 + 1/phi^2 = 3 (arXiv:2606.05017)') ]));

children.push(H2('4.3. Якорный вектор'));
children.push(body([
  t('Каждый пакет содержит как минимум один вектор с именем '), mono('anchor_*'),
  t(', кодирующий значение 3,0. Мотивацией служит тождество'),
]));
children.push(new Paragraph({ spacing: { before: 80, after: 80 }, alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: 'φ² + 1/φ² = 3,     (1)', font: FONT, size: 26, italics: true })] }));
children.push(body([
  t('где φ = (1 + √5)/2 — золотое сечение. Это тождество представлено и контекстуализировано в препринте GoldenFloat как численно обоснованный L₂-якорь. Значение 3,0 точно представимо во всех шести форматах подмножества Tier-1 (оно попадает в нормальный диапазон с нулевой ошибкой мантиссы для всех шести раскладок), что делает его надёжной однострочной проверкой корректности между пакетами. В полном каталоговом наборе 3,0 точно попадает на сетку в 43 из 49 битоточных пакетов; шесть исключений (логарифмические LNS-8/16/32/64 и 4-битные GF4, MXGF4) честно фиксируют ближайшее представимое значение и истинную '), mono('abs_error'), t(', поскольку log₂(3) не представим точно в LNS, а 4-битные сетки слишком грубы.'),
]));
children.push(body([
  t('Формально: для любого формата пакета F, если decode_F(encode_F(3,0)) ≠ 3,0, присутствует фундаментальная ошибка реализации.'),
]));

children.push(H2('4.4. Шаги верификации'));
children.push(body([ t('Каждый пакет проверяется двумя независимыми процедурами:') ]));
children.push(num([ b('Самопроверка циклическим кодированием-декодированием (round-trip). '),
  t('Для каждого вектора: decode(encode(input)) = decoded, причём сохранённое значение '), mono('abs_error'), t(' согласовано с отклонением.') ]));
children.push(num([ b('Перекрёстная проверка относительно ml_dtypes 0.5.4. '),
  t('Там, где существует соответствующий тип ml_dtypes, битовые паттерны пакета сравниваются с кодировкой ml_dtypes тех же входов. Каждое расхождение записывается в список '),
  mono('divergences'), t(' заголовка пакета и описывается в настоящей статье.') ]));
children.push(body([
  t('Честная трактовка абсолютной ошибки — непреложный принцип проектирования. Каждый вектор, в котором декодированное значение отличается от входного, несёт ненулевое значение '),
  mono('abs_error'), t('; никакое значение не подавляется и не округляется до нуля ради улучшения статистики совпадений.'),
]));

children.push(H2('4.5. Политика покрытия всех 83 форматов'));
children.push(body([ t('Набор пакетов покрывает весь каталог — по одному пакету на каждый из 83 форматов — по детерминированной и воспроизводимой политике:') ]));
children.push(bullet([ b('Форматы ≤ 8 бит: '), t('исчерпывающее перечисление всех кодов формата.') ]));
children.push(bullet([ b('Форматы > 8 бит: '), t('курируемый набор именованных векторов (нуль, единица, два, три, половина, четыре, отрицательные и специальные значения формата) через явные кодеры — без перебора всех кодов и без многомегабайтных файлов.') ]));
children.push(bullet([ b('Форматы без радикс-2 раскладки S:E:M: '), t('структурный пакет с полными метаданными каталога, пометкой '), mono('bitexact: false'), t(' и явным полем '), mono('structural_reason'), t('. Это честные плейсхолдеры, а не утверждения о битоточности.') ]));
children.push(body([ t('Итог: 49 битоточных пакетов и 34 структурных пакета (всего 83). Перекрёстная проверка относительно внешнего оракула ml_dtypes применяется к подмножеству Tier-1 (раздел 4.4, пункт 2); остальные битоточные пакеты на данный момент верифицируются самопроверкой кругового кодирования-декодирования, а внешняя перекрёстная проверка по мере появления эталонных реализаций расширяет Tier-1 (раздел 9).') ]));
children.push(body([ t('Машиночитаемый индекс '), mono('INDEX_all_formats.json'), t(' перечисляет все 83 пакета с итогами ('), mono('total_packs: 83, bitexact_packs: 49, structural_packs: 34'), t('), якорным тождеством и ссылкой на SSOT.') ]));

// =================== 5. Catalog-wide set + Tier-1 packs ===================
children.push(H1('5. Полный набор пакетов и шесть пакетов Tier-1'));
children.push(body([ t('Набор пакетов соответствия покрывает все 83 формата каталога — 49 битоточных пакетов и 34 структурных пакета (раздел 4.5, полный перечень и отпечатки SHA-256 — в README каталога '), mono('conformance/vectors'), t(' репозитория gHashTag/t27). Далее подробно разбираются шесть пакетов уровня Tier-1, для которых выполнена дополнительная перекрёстная проверка относительно внешнего оракула. Таблица 4 даёт сводку по этим шести пакетам.') ]));

children.push(makeTable([1300, 2300, 800, 2300, 1500, 1160],
  ['Пакет', 'Раскладка', 'Век-ры', 'Совпадение ml_dtypes', 'Статус', 'SHA-256 (16)'],
  [
    ['GF16', 'S1E5M10, привязка к φ', '21', 'н/п (нет аналога в ml_dtypes)', 'LIVE v0.3.1', 'см. репозиторий'],
    ['MXFP4', 'S1E2M1, элемент блока', '12', 'н/п', 'LIVE v0.3.1', { mono: true, text: '86c99d6f72375d75' }],
    ['BF16', 'S1E8M7 bias=127, RTE', '21', '21/21', 'NEW v0.4.0-pre', { mono: true, text: '320c1850b4846745' }],
    ['FP8 E4M3', 'S1E4M3 bias=7, SatMax', '16', '15/16 (раздел 7)', 'NEW v0.4.0-pre', { mono: true, text: 'fff0c30f8e6bee22' }],
    ['FP8 E5M2', 'S1E5M2 bias=15, OvfInf', '17', '17/17', 'NEW v0.4.0-pre', { mono: true, text: '66cd7be1500ec800' }],
    ['E8M0 block', 'E8M0 только масштаб, без знака', '11', 'согласован с OCP MX v1.0', 'NEW v0.4.0-pre', { mono: true, text: 'b211f1a863f71fd7' }],
  ], { fs: 18 }));
children.push(caption('Таблица 4. Шесть пакетов Tier-1 с первого взгляда (T4).'));

children.push(body([ t('Полные отпечатки SHA-256 (дословно из манифеста):') ]));
const shas = [
  ['GF16', 'см. репозиторий (SHA-256 пока не закреплён в манифесте v0.4.0-pre)'],
  ['MXFP4', '86c99d6f72375d751df4c74897904a0a36cff52e8d60cbfef5d58b71625d4b2f'],
  ['BF16', '320c1850b484674546785791b1c22d76feb4ea748c6669ffb633e5455d822b8a'],
  ['FP8 E4M3', 'fff0c30f8e6bee22b1a7d0e0e1cff65edde9d2b17ebf97dba0539973f0a5e89d'],
  ['FP8 E5M2', '66cd7be1500ec8003eb5dee7532bb4e954b7bc0084b6f22a75d02f7842f23a56'],
  ['E8M0 block', 'b211f1a863f71fd7c5e02e512efff0255ebcc51521311186e01cb9992e4464bd'],
];
for (const [n, h] of shas) {
  children.push(bullet([ b(n + ': '), mono(h, { size: 18 }) ]));
}

children.push(H2('5.1. GF16 — GoldenFloat 16-бит'));
children.push(body([
  t('GF16 — это 16-битный формат с раскладкой S1E5M10 и φ-поворотом представимого диапазона. Он описан и обоснован в препринте GoldenFloat. Пакет содержит 21 вектор, охватывающий нуль, нормальные значения, якорь 3,0 (кодирующий тождество '),
  it('φ² + 1/φ² = 3'), t(', ур. (1)), субнормальные числа и поведение при переполнении. Поскольку ml_dtypes не реализует тип GF16, у этого пакета нет партнёра для перекрёстной проверки; его векторы верифицируются только самопроверкой циклическим кодированием-декодированием. GF16 доступен в PyPI-пакете '),
  mono('tt-lang-t27'), t(' начиная с версии v0.3.1.'),
]));

children.push(H2('5.2. Элемент MXFP4 — OCP Microscaling 4-бит'));
children.push(body([
  t('Элемент MXFP4 использует раскладку S1E2M1 (1 бит знака, 2 бита порядка, 1 бит мантиссы) с политикой переполнения «насыщение до конечного», как указано в OCP MX v1.0. В пределах блока 32 таких элемента разделяют масштабный множитель E8M0. Пакет элемента охватывает 12 векторов, выбранных из представимых конечных значений элемента, включая нуль и случай насыщения. На момент написания ml_dtypes не предоставляет тип элемента MXFP4; пакет верифицируется самопроверкой циклическим кодированием-декодированием и сравнивается с таблицей значений OCP MX v1.0. SHA-256: '),
  mono('86c99d6f72375d751df4c74897904a0a36cff52e8d60cbfef5d58b71625d4b2f', { size: 18 }), t('.'),
]));

children.push(H2('5.3. BF16 — Brain Float 16'));
children.push(body([
  t('BF16 использует раскладку S1E8M7 со смещением порядка = 127, округлением к ближайшему чётному (RTE) и обработкой бесконечности и NaN в стиле IEEE 754. Он занимает старшие 16 бит FP32-слова, так что преобразование в/из FP32 — это простое усечение (с округлением). Пакет содержит 21 вектор, включая:'),
]));
[
  'Положительный и отрицательный нуль',
  'Положительную и отрицательную бесконечность (сохраняются точно)',
  'Тихий NaN (сохраняется с полезной нагрузкой)',
  'Наименьшее положительное нормальное и субнормальное',
  'Наибольшее конечное BF16 (≈ 3,39 × 10³⁸)',
  'Два случая середины RTE (поведение округления к чётному)',
  'Переполнение FP32-максимума в BF16 +∞ (abs_error = +∞)',
  'Потеря значимости FP32-минимума-субнормали в BF16 +0',
  'Неточные константы φ и 1/φ с ненулевой abs_error',
  'Якорный вектор при 3,0 (точно, abs_error = 0)',
].forEach(x => children.push(bullet([ t(x) ])));
children.push(body([
  t('Все 21 вектор совпадают с '), mono('ml_dtypes.bfloat16'), t(' (Google/JAX 0.5.4): 21/21. SHA-256: '),
  mono('320c1850b484674546785791b1c22d76feb4ea748c6669ffb633e5455d822b8a', { size: 18 }), t('.'),
]));
children.push(body([
  t('BF16 демонстрирует высокое межвендорное согласие; Google bfloat16, Intel BFLOAT16, ARM BFloat16 и BF16, сопряжённый с NVIDIA TF32, разделяют одну и ту же семантику sub/inf/NaN в стиле IEEE 754 с округлением к ближайшему чётному на младших 16 битах FP32. В 21 протестированном граничном случае заметных расхождений не наблюдалось.'),
]));

children.push(H2('5.4. FP8 E4M3 — восьмибитный float с четырёхбитным порядком'));
children.push(body([
  t('FP8 E4M3 использует раскладку S1E4M3 со смещением порядка = 7. В варианте OCP MX (используемом здесь) бесконечность заменена дополнительными конечными значениями, а NaN кодируется битовым паттерном '),
  mono('0x7F'), t(' (или '), mono('0xFF'), t(' для отрицательных). Таким образом, формат не имеет +∞, что даёт максимальное конечное значение 448,0.'),
]));
children.push(body([
  t('Пакет содержит 16 векторов. 15 из 16 точно совпадают с '), mono('ml_dtypes.float8_e4m3fn'),
  t('. Единственное задокументированное расхождение — случай переполнения для входа 1000,0, подробно описанный в таблице 5 и обсуждаемый в разделе 7. SHA-256: '),
  mono('fff0c30f8e6bee22b1a7d0e0e1cff65edde9d2b17ebf97dba0539973f0a5e89d', { size: 18 }), t('.'),
]));

children.push(makeTable([1200, 3000, 1100, 2030, 2030],
  ['Вход', 'Реализация', 'Биты', 'Декодировано', 'Политика'],
  [
    ['1000,0', 'этот пакет (конвенция tt-metal/AMD)', { mono: true, text: '0x7E' }, '448,0 (max-finite)', 'насыщение до максимума'],
    ['1000,0', 'ml_dtypes 0.5.4 (конвенция JAX/TPU)', { mono: true, text: '0x7F' }, 'NaN', 'переполнение в NaN'],
  ], { fs: 19 }));
children.push(body([ it('Оба варианта разрешены OCP MX v1.0. См. раздел 7.', { size: 18 }) ]));
children.push(caption('Таблица 5. Интерпретационный разрыв при переполнении FP8 E4M3 для входа 1000,0 (T5).'));

children.push(H2('5.5. FP8 E5M2 — восьмибитный float с пятибитным порядком'));
children.push(body([
  t('FP8 E5M2 использует раскладку S1E5M2 со смещением порядка = 15 и сохраняет полноценные бесконечность и NaN в стиле IEEE 754. Максимальное конечное значение — 57344,0. Пакет содержит 17 векторов, охватывающих полный набор граничных случаев (нуль, нормальные, субнормальные, ±∞, NaN, переполнение, потеря значимости, середины RTE и якорь 3,0). Все 17 векторов точно совпадают с '),
  mono('ml_dtypes.float8_e5m2'), t(': 17/17. SHA-256: '),
  mono('66cd7be1500ec8003eb5dee7532bb4e954b7bc0084b6f22a75d02f7842f23a56', { size: 18 }), t('.'),
]));

children.push(H2('5.6. Блочный масштаб E8M0 — масштабный формат OCP Microscaling'));
children.push(body([
  t('E8M0 — формат «только масштаб», используемый как общий блочный порядок в блоках OCP MX. Он не несёт ни бита знака, ни мантиссы — только 8 бит порядка, представляющих степени 2 в диапазоне [2⁻¹²⁷, 2¹²⁷]. Специальный паттерн '),
  mono('0xFF'), t(' кодирует NaN (используется для обозначения неинициализированного или недопустимого масштаба). Пакет содержит 11 векторов, охватывающих представительные значения масштаба, сторожевое значение NaN и якорь 3,0 (который кодируется в ближайший представимый масштаб-степень-двойки, 2¹ = 2, с задокументированной ненулевой abs_error). Векторы были перегенерированы относительно '),
  mono('ml_dtypes.float8_e8m0fnu'), t(' (Google/JAX 0.5.4) по семантике OCP MX v1.0. SHA-256: '),
  mono('b211f1a863f71fd7c5e02e512efff0255ebcc51521311186e01cb9992e4464bd', { size: 18 }), t('.'),
]));

// =================== 6. P3109 Cross-Walk ===================
children.push(H1('6. Кросс-уолк к IEEE P3109'));
children.push(body([
  t('IEEE P3109 — активная рабочая группа, стандартизирующая арифметику с плавающей точкой для приложений ИИ. Её промежуточный отчёт v3.2.0 определяет семейство конфигурируемых форматов, параметризованных тройкой (E, M, насыщение). Более широкое обоснование явного побитового тестирования соответствия в промышленной практике с плавающей точкой приводит Винтерстайгер (Wintersteiger) на ARITH 2025; пакеты в этой статье — конкретный пример такого подхода, нацеленный именно на реестр численных форматов ИИ. Там, где существует машинно-проверяемая семантика, например разработка P3109 FLoPS на Lean 4, кросс-уолк в таблице 6 служит мостом между доказательно проверенной спецификацией и битоточными тестовыми данными.'),
]));
children.push(body([ t('Таблица 6 сопоставляет шесть пакетов с конфигурируемыми форматами P3109 v3.2.0.') ]));

children.push(makeTable([1400, 1500, 1300, 3360, 1800],
  ['Наш формат', 'Имя P3109', 'Совпадение', 'Ключевое различие', 'Пакет'],
  [
    ['FP8 E4M3', 'Binary8p3se', 'Близкое', 'Насыщение: у нас SatMax против OvfInf в P3109; кодирование NaN только конечными', { mono: true, text: 'fp8_e4m3' }],
    ['MXFP4 элемент', 'Binary4p1sf', 'Прямое', 'Блочная структура ортогональна; элемент совпадает', { mono: true, text: 'mxfp4' }],
    ['GF16', '(нет)', 'Нет совпадения', 'P3109 не охватывает 16-битные форматы с привязкой к φ', { mono: true, text: 'gf16' }],
    ['BF16', '(нет)', 'Нет совпадения', 'P3109 фокусируется на 4/8-битных; BF16 — 16-битный', { mono: true, text: 'bf16' }],
    ['FP8 E5M2', '(нет)', 'Нет совпадения', 'Binary8p2se соответствовал бы, но отсутствует в v3.2.0', { mono: true, text: 'fp8_e5m2' }],
    ['E8M0 block', '(нет)', 'Ортогонально', 'P3109 не определяет формат «только масштаб»', { mono: true, text: 'e8m0_block' }],
  ], { fs: 18 }));
children.push(caption('Таблица 6. Кросс-уолк P3109 v3.2.0 для шести пакетов (T6).'));

children.push(H2('6.1. Прямые совпадения'));
children.push(body([ b('Binary8p3se ↔ FP8 E4M3. '),
  t('P3109 Binary8p3se специфицирует S1E4M3 с насыщением OvfInf. Вариант FP8 E4M3 из OCP MX v1.0, используемый в этом пакете, применяет вместо этого SatMax. Различие — ровно тот интерпретационный разрыв при переполнении, что задокументирован в таблице 5. За исключением выбора политики насыщения, битовые раскладки и смещение порядка идентичны.') ]));
children.push(body([ b('Binary4p1sf ↔ MXFP4 элемент. '),
  t('P3109 Binary4p1sf специфицирует S1E2M1 с SatFinite — идентично раскладке элемента MXFP4 в OCP MX v1.0. Единственное структурное различие в том, что OCP MX оборачивает элементы в 32-элементные блоки, разделяющие масштабный множитель E8M0 — блочное измерение, которое P3109 не рассматривает в v3.2.0.') ]));

children.push(H2('6.2. Частичные совпадения и несовпадения'));
children.push(body([
  t('FP8 E5M2 отображался бы в гипотетический Binary8p2se, который отсутствует в профилях P3109 v3.2.0. GF16 и BF16 находятся вне 4/8-битной области, которую P3109 в настоящее время охватывает. E8M0 — формат «только масштаб», ортогональный уровню представления P3109.'),
]));

children.push(H2('6.3. Охват операций'));
children.push(body([
  t('Файл '), mono('StandardOperations.yaml'), t(' стандарта P3109 перечисляет приблизительно 80 операций в семи категориях: классификация (8), сравнение (7), экстремумы (10+), округление проекцией (6 режимов), арифметика (10), трансцендентные функции (≈25) и блочные операции (40+).'),
]));
children.push(body([
  t('Текущий набор (v0.1) охватывает только уровень представления — битоточность кодирования/декодирования. Трек 2 (целевой срок III кв. 2026) расширит охват до уровня операций, как минимум округление NearestTiesToEven для сложения, умножения и FMA по всем шести форматам, с доказательно проверенной семантикой, взятой из P3109 FLoPS в качестве формального якоря.'),
]));

// =================== 7. Discussion ===================
children.push(H1('7. Обсуждение: интерпретационный разрыв как ценность линейки'));
children.push(body([
  t('Набор тестов соответствия оправдывает себя не тогда, когда все векторы совпадают, а когда он вскрывает расхождение, которое иначе было бы невидимым. Два таких случая заслуживают явного упоминания: разрыв при переполнении FP8 E4M3 (раздел 7.1) и разрыв блочной структуры между MXFP4 и NVFP4 (раздел 7.2).'),
]));

children.push(H2('7.1. Разрыв A: политика переполнения FP8 E4M3'));
children.push(body([ t('Случай переполнения FP8 E4M3 (вход = 1000,0) — канонический пример.') ]));
children.push(body([
  t('Спецификация OCP MX v1.0 утверждает, что для входов, превышающих максимальное конечное значение (448,0 для E4M3), реализации могут либо насыщаться до максимального конечного, либо выдавать NaN. Две зрелые реализации промышленного качества делают разный выбор:'),
]));
children.push(bullet([ b('Конвенция tt-metal (Tenstorrent) / AMD: '), t('насыщение до максимального конечного. Битовый паттерн '), mono('0x7E'), t(', декодированное значение 448,0. Этот пакет принимает данную конвенцию.') ]));
children.push(bullet([ b('Конвенция JAX/TPU (ml_dtypes 0.5.4): '), t('переполнение в NaN. Битовый паттерн '), mono('0x7F'), t(', декодированное значение NaN.') ]));
children.push(body([ t('Ни один из вариантов не является ошибкой. Оба соответствуют OCP MX v1.0. Расхождение — задокументированный разрешённый спецификацией интерпретационный разрыв.') ]));
children.push(body([
  t('Практическое следствие значимо для авторов компиляторов и тестовых стендов. Любой межвендорный перенос вычисления FP8 E4M3 должен либо: (а) явно выбрать одну политику и задокументировать её, либо (б) нести оба вектора в своём эталонном наборе тестов, принимая, что входы из диапазона переполнения будут давать разные результаты на разном оборудовании.'),
]));
children.push(body([
  t('Именно это и призван вскрывать пакет соответствия. Набор тестов, который сравнивает лишь «совпадают ли выходы на этом оборудовании?», никогда не увидел бы этого расхождения — обе реализации проходят собственные тесты. Общий битоточный эталон делает разрыв видимым.'),
]));

children.push(H2('7.2. Разрыв B: 4-битная блочная структура (MXFP4 против NVFP4)'));
children.push(body([
  t('Второй класс интерпретационного разрыва возникает уровнем выше — на уровне блочной структуры, а не битового паттерна элемента. OCP MX MXFP4 и NVIDIA NVFP4 разделяют одну и ту же раскладку элемента S1E2M1 (так что пакеты элементов битоидентичны на 4-битном уровне), однако оборачивают этот элемент в блоки разной формы с по-разному квантованными полями масштаба. Таблица 7 резюмирует расхождение параметров.'),
]));

children.push(makeTable([3360, 3000, 3000],
  ['Параметр', 'OCP MX MXFP4', 'NVIDIA NVFP4'],
  [
    ['Раскладка элемента', 'S1E2M1 (4 бита)', 'S1E2M1 (4 бита)'],
    ['Биты мантиссы (элемент)', '1', '1'],
    ['Размер блока', '32 элемента', '16 элементов'],
    ['Формат масштаба', 'E8M0 (8-бит)', 'FP8 E4M3 (8-бит)'],
    ['Биты порядка масштаба', '8 (чистый порядок)', '4'],
    ['Биты мантиссы масштаба', '0', '3'],
    ['Динамический диапазон масштаба', '2⁻¹²⁷ … 2¹²⁷', '≈ 2⁻⁹ … 448'],
    ['Гранулярность масштаба на декаду', '1 (только степени двойки)', '8 (3-битная мантисса)'],
    ['Бит/элемент с учётом масштаба', '4 + 8/32 = 4,25', '4 + 8/16 = 4,50'],
  ], { fs: 19 }));
children.push(caption('Таблица 7. Параметры блочной структуры MXFP4 против NVFP4.'));

children.push(body([ t('Из таблицы параметров вытекают три структурных следствия:') ]));
children.push(num([ b('Различное разрешение масштаба. '), t('E8M0 (MXFP4) квантует блочный масштаб до степени двойки; масштаб FP8 E4M3 в NVFP4 предлагает 2³ = 8 кодов мантиссы на двоичный порядок и потому разрешает внутриблочный динамический диапазон в восемь раз тоньше в пределах своего представимого диапазона.') ], 'cons'));
children.push(num([ b('Различный диапазон масштаба. '), t('E8M0 охватывает приблизительно 2²⁵⁴ двоичных порядков (с учётом зарезервированных кодов); FP8 E4M3 насыщается при 448 и теряет значимость ниже ≈ 2⁻⁹. Тензор, чей поблочный масштаб естественно лежит вне диапазона FP8, представим в MXFP4, но не в NVFP4 без перемасштабирования на более высоком уровне.') ], 'cons'));
children.push(num([ b('Различный эффективный бюджет битов. '), t('Поэлементное хранение составляет 4,25 бита для MXFP4 (32-элементный блок) против 4,50 бита для NVFP4 (16-элементный блок). Два формата не сравнимы напрямую по битам; любое сравнение коэффициентов сжатия должно учитывать эту разницу накладных расходов в 5,9 % у NVFP4.') ], 'cons'));
children.push(body([
  t('Поэтому тензор, сохранённый как MXFP4, и тот же тензор, сохранённый как NVFP4, могут совпадать по каждому битовому паттерну элемента, но различаться по декодированному значению, поскольку поблочный масштаб, на который они умножаются, использует другой (и по-другому квантованный) формат масштаба. Это структурный интерпретационный разрыв, а не разрыв значений: битоточность элемента не влечёт равенства декодированного тензора.'),
]));
children.push(body([
  t('Показание линейки симметрично разрыву A. И MXFP4, и NVFP4 — соответствующие реализации разумно спроектированного 4-битного блочного формата; они просто делают разный выбор блочной структуры. Межвендорное развёртывание 4-битных весов требует явного объявления используемого блочного формата (размер блока + формат масштаба), а не только раскладки элемента. Объявлений только об элементе («модель использует 4-битные веса в форме MXFP4») недостаточно.'),
]));
children.push(body([
  t('Настоящий каталог охватывает сторону MXFP4 этой пары как пакет уровня Tier-1 и перечисляет NVFP4 как ближайшего кандидата Трека 2 (раздел 9.1). Документирование структурного разрыва — первый шаг; парный пакет NVFP4 с совпадающей схемой и намеренным межпакетным вектором расхождения на представительной границе квантования масштаба закроет его.'),
]));

children.push(H2('7.3. Общий паттерн: разрешённый спецификацией выбор как показание линейки'));
children.push(body([
  t('Норма честности: каждый вектор в каждом пакете, где декодированное значение отличается от входного, несёт ненулевое значение '),
  mono('abs_error'), t('. Переполнение в ±∞ показывает '), mono('abs_error = Inf'),
  t('; потеря значимости до нуля показывает фактическую величину утраченного значения. Никакое поле abs_error не подавляется и не округляется до нуля ради улучшения статистики совпадений.'),
]));

// =================== 8. Reproducibility ===================
children.push(H1('8. Воспроизводимость и происхождение'));
children.push(H2('8.1. Исходные репозитории'));
children.push(bullet([ b('gHashTag/t27 '), t('('), mono('github.com/gHashTag/t27'), t('): единый источник истины (SSOT) для каталога и полного набора пакетов соответствия на все 83 формата. Каталог '), mono('conformance/vectors'), t(' содержит все файлы пакетов, машиночитаемый индекс '), mono('INDEX_all_formats.json'), t(', README с полными отпечатками SHA-256 и каталоговый генератор '), mono('gen_all_formats.py'), t('; рядом — JSON-файлы каталога, проверки инвариантов и шаблоны кодогенерации.') ]));
children.push(bullet([ b('gHashTag/tt-lang-t27 '), t('('), mono('github.com/gHashTag/tt-lang-t27'), t('): зеркало на PyPI. Версия 0.3.1 доступна на PyPI (включает пакеты GF16 и MXFP4). Версия 0.4.0-pre, добавляющая четыре новых пакета, описанных в этой статье, доступна в PR #6.') ]));
children.push(bullet([ b('gHashTag/tt-trinity-corona '), t('('), mono('github.com/gHashTag/tt-trinity-corona'), t('): контекст кремниевого оракула уровня Tier-2 для постсиликонного аудита на GF180MCU; упоминается здесь одной строкой для полноты.') ]));

children.push(H2('8.2. Эталонный инструмент'));
children.push(body([
  t('Основной оракул для всей перекрёстной проверки — '), mono('ml_dtypes'), t(' 0.5.4 (Google/JAX), доступный по адресу '),
  mono('github.com/jax-ml/ml_dtypes'), t('. Конкретные используемые типы: '),
  mono('ml_dtypes.bfloat16'), t(', '), mono('ml_dtypes.float8_e4m3fn'), t(', '), mono('ml_dtypes.float8_e5m2'), t(' и '), mono('ml_dtypes.float8_e8m0fnu'), t('.'),
]));

children.push(H2('8.3. Отпечаток якоря'));
children.push(body([
  t('Якорное тождество '), it('φ² + 1/φ² = 3'), t(' (ур. (1)), формализованное в препринте GoldenFloat, имеет следующий канонический отпечаток SHA-256:'),
]));
children.push(new Paragraph({ spacing: { before: 60, after: 120 }, alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: '218403e344779c890f302ad2c70af21fb765060dd794d793c7eacc1ef8f80e6b', font: 'Consolas', size: 18 })] }));
children.push(body([
  t('Этот отпечаток покрывает каноническую UTF-8-кодировку строки тождества и служит внеполосной проверкой того, что цитируется правильная якорная статья.'),
]));

children.push(H2('8.4. Таблица происхождения пакетов'));
children.push(body([ t('Таблица 8 перечисляет путь в репозитории, ветку/PR и полный SHA-256 для каждого пакета.') ]));
children.push(makeTable([1300, 1700, 1900, 4460],
  ['Пакет', 'Репозиторий', 'Ветка / PR', 'Полный SHA-256'],
  [
    ['GF16', 'gHashTag/t27', 'main (v0.3.1)', 'см. репозиторий (не закреплён в манифесте v0.4.0-pre)'],
    ['MXFP4', 'gHashTag/t27', 'main (v0.3.1)', { mono: true, text: '86c99d6f72375d751df4c74897904a0a36cff52e8d60cbfef5d58b71625d4b2f' }],
    ['BF16', 'gHashTag/t27', 'PR #6 (v0.4.0-pre)', { mono: true, text: '320c1850b484674546785791b1c22d76feb4ea748c6669ffb633e5455d822b8a' }],
    ['FP8 E4M3', 'gHashTag/t27', 'PR #6 (v0.4.0-pre)', { mono: true, text: 'fff0c30f8e6bee22b1a7d0e0e1cff65edde9d2b17ebf97dba0539973f0a5e89d' }],
    ['FP8 E5M2', 'gHashTag/t27', 'PR #6 (v0.4.0-pre)', { mono: true, text: '66cd7be1500ec8003eb5dee7532bb4e954b7bc0084b6f22a75d02f7842f23a56' }],
    ['E8M0 block', 'gHashTag/t27', 'PR #6 (v0.4.0-pre)', { mono: true, text: 'b211f1a863f71fd7c5e02e512efff0255ebcc51521311186e01cb9992e4464bd' }],
  ], { fs: 16 }));
children.push(caption('Таблица 8. Сопоставление пакетов с происхождением (T7).'));

children.push(H2('8.5. Манифест'));
children.push(body([
  t('Файл '), mono('MANIFEST_v0.4.0-pre.json'), t(' в репозитории '), mono('gHashTag/t27'),
  t(' фиксирует шесть значений SHA-256 пакетов Tier-1, якорь версии ml_dtypes и ссылку на согласование с P3109; отпечатки всех 83 пакетов перечислены в README каталога '), mono('conformance/vectors'), t(' и в '), mono('INDEX_all_formats.json'), t('. Последующие потребители могут проверить целостность пакета, заново вычислив SHA-256 канонического JSON-файла и сравнив с записью в манифесте/индексе.'),
]));

// =================== 9. Future Work ===================
children.push(H1('9. Будущая работа'));
children.push(H2('9.1. Трек 2: внешняя валидация всех 83 пакетов'));
children.push(body([
  t('Набор пакетов уже покрывает все 83 формата каталога на уровне представления (49 битоточных + 34 структурных; раздел 4.5). Шесть пакетов уровня Tier-1 дополнительно перекрёстно проверены относительно внешнего оракула. Трек 2 (целевой срок III кв. 2026) распространит такую внешнюю валидацию на остальные битоточные пакеты и преобразует структурные пакеты в битоточные по мере появления эталонных реализаций, включая:'),
]));
children.push(bullet([ t('NVIDIA NVFP4 (элемент S1E2M1, 16-элементный блок, блочный масштаб FP8 E4M3) — парный пакет на уровне блока, закрывающий структурный разрыв, задокументированный в разделе 7.2.') ]));
children.push(bullet([ t('Расширение оракульного покрытия ml_dtypes на записи MLLowPrecision (варианты FP6, FP4) и табличный NF4.') ]));
children.push(bullet([ t('Перевод типов Posit/Unum III и тейперированных takum из структурных в битоточные через оракул libtakum.') ]));
children.push(bullet([ t('Закрепление смещений (bias) для широких вариантов GoldenFloat (GF128–GF1024), пока остающихся открытыми ИОКР-параметрами и потому записанных структурно.') ]));

children.push(H2('9.2. Соответствие на уровне операций'));
children.push(body([
  t('Текущий набор охватывает только уровень представления. Трек 2 добавит векторы уровня операций, согласованные с подмножеством '),
  mono('StandardOperations.yaml'), t(' стандарта P3109, начиная с округления NearestTiesToEven для сложения, умножения и FMA по шести форматам Tier-1. Это позволит командам компиляторов и оборудования проверять не только корректность кодирования/декодирования, но и согласие их арифметических операций со стандартом на битовом уровне.'),
]));

children.push(H2('9.3. Фаззинг циклического кодирования-декодирования'));
children.push(body([
  t('Фаззер на основе свойств дополнит созданные вручную граничные векторы. Фаззер будет генерировать случайные входы FP32, применять кодирование/декодирование для каждого формата и проверять свойство циклического кодирования-декодирования и согласованность abs_error. Это особенно ценно для форматов со сложным поведением насыщения.'),
]));

children.push(H2('9.4. Открытые приглашения'));
children.push(body([
  t('Наиболее полезный непосредственный следующий шаг — чтобы независимый сопровождающий взял любой отдельный пакет соответствия, запустил его относительно собственной реализации и сообщил о расхождениях в виде задач (issues) на GitHub в '),
  mono('gHashTag/t27'), t('. В частности:'),
]));
children.push(bullet([ b('ml_dtypes: '), t('подтвердить совпадение 21/21 по BF16 и результаты 15/16 + 17/17 по FP8 относительно последнего выпуска 0.5.x.') ]));
children.push(bullet([ b('Рабочая группа OCP MX: '), t('проверить векторы элемента MXFP4 и блочного масштаба E8M0 относительно эталонной таблицы MX v1.0.') ]));
children.push(bullet([ b('Редакторы IEEE P3109: '), t('перекрёстно проверить строки Binary8p3se / Binary4p1sf в таблице 6 относительно промежуточного отчёта v3.2.x.') ]));
children.push(bullet([ b('NVIDIA NVFP4: '), t('подтвердить параметры 16-элементного блока / масштаба FP8 E4M3, использованные в разделе 7.2.') ]));
children.push(bullet([ b('Pychop, libtakum: '), t('оракулы для уровня операций Трека 2 и подкомплекта Posit/Unum III соответственно.') ]));
children.push(bullet([ b('IREE, vLLM, llama.cpp, onnxruntime: '), t('интеграторы, наиболее вероятно затрагиваемые разрывом переполнения FP8 E4M3 при межвендорных развёртываниях.') ]));
children.push(body([ t('Любое найденное новое расхождение — это особенность линейки, а не отказ набора тестов.') ]));
children.push(body([
  t('Пакеты соответствия, схема каталога и шаблоны кодогенерации лицензированы открыто с намерением, чтобы они стали общим ресурсом сообщества для вендор-нейтральной работы с реестром численных форматов.'),
]));

// =================== 10. Limitations ===================
children.push(H1('10. Ограничения'));
children.push(body([
  t('Настоящие каталог и набор тестов соответствия намеренно ограничены по охвату, и мы явно формулируем граничные условия, чтобы последующие пользователи могли решить, на какие утверждения полагаться.'),
]));
children.push(body([ b('Уровень элемента, а не уровень операций. '),
  t('Все шесть пакетов уровня Tier-1 проверяют поведение циклического кодирования-декодирования на уровне элемента: значение кодируется в битовый паттерн, декодируется обратно, и результат сравнивается с эталонным оракулом. Пакеты не проверяют семантику уровня операций — умножение, накопление, активацию или ядра слитного умножения-накопления (FMA). Соответствие уровня операций (Трек 2, раздел 9.2) признаётся естественным следующим слоем, но выходит за рамки настоящего препринта.') ]));
children.push(body([ b('Единственный эталонный оракул. '),
  t('Пакеты уровня Tier-1 используют '), mono('ml_dtypes'), t(' как эталонную реализацию, с одним хорошо задокументированным расхождением по переполнению FP8 E4M3 (раздел 7.1). Независимо реализованный оракул — например, libtakum для Posit/Unum III или Pychop для уровня операций Трека 2 — пока не подключён к стенду верификации. Расхождения, прослеживаемые к смещению одного оракула, в настоящее время нельзя исключить для форматов вне подмножества BF16 / FP8 / MXFP4 / E8M0.') ]));
children.push(body([ b('Покрытие каталога асимметрично. '),
  t('Каталог из 83 строк (раздел 3) охватывает 13 кластеров форматов, но глубина покрытия неравномерна. IEEE 754 binary, BF16, FP8 (E4M3/E5M2), MXFP4 и семейство GoldenFloat GFN покрыты полными схемами строк, таксономией статусов утверждений и соответствующими пакетами Tier-1, где применимо. Строки Posit/Unum III, логарифмические системы счисления (LNS), NF4, BitNet, TF32 и FP6 присутствуют, но в настоящее время лишены пакетов Tier-1; их поля статуса утверждений заполнены, но ещё не проверены сквозным образом относительно оракула. Это сделано намеренно — каталог в первую очередь реестр, а во вторую — стенд верификации — но это означает, что отсутствие пакета соответствия не следует трактовать как утверждение о качестве.') ]));
children.push(body([ b('NVFP4 задокументирован, но не упакован. '),
  t('Разрыв B (раздел 7.2) задокументирован на структурном уровне таблицей параметров, но соответствующий пакет NVFP4 уровня Tier-1 пока не включён в этот препринт. Количественные межпакетные векторы расхождений на представительных границах квантования масштаба перечислены как первый результат Трека 2 (раздел 9.1).') ]));
children.push(body([ b('Никаких утверждений об оптимальности. '),
  t('Каталог не утверждает, что какой-либо включённый формат является наилучшим для какой-либо последующей задачи. Сравнения касаются интерпретации в рамках спецификации, а не точности, пропускной способности, энергопотребления или качества модели. Бенчмарки, ранжирующие форматы по точности или перплексии, выходят за рамки этой работы; настоящий вклад — это вендор-нейтральный справочник, а не конкурентная оценка.') ]));
children.push(body([ b('Честная abs_error, а не нулевая abs_error. '),
  t('Норма честности из раздела 7.3 требует, чтобы каждый вектор с ненулевой ошибкой декодирования сообщал фактическую величину. Это заставляет набор выглядеть хуже, чем набор, маскирующий переполнение-в-Inf или потерю-значимости-в-ноль как «совпадение». Потребители, сравнивающие настоящие результаты с наборами, подавляющими такие поля, должны нормализовать сравнение перед выводами.') ]));
children.push(body([ b('Конверт воспроизводимости. '),
  t('Все якоря SHA-256, коммиты репозиториев и манифесты пакетов, приведённые в разделе 8, были проверены на момент написания. Долгосрочная воспроизводимость зависит от доступности вышестоящих источников '),
  mono('ml_dtypes'), t(', спецификации OCP MX и промежуточного документа IEEE P3109; если какой-либо из них станет недоступен, стенду верификации потребуется слой зеркалирования, который в настоящее время не реализован.') ]));
children.push(body([ b('Отсутствие зависимости от неопубликованных работ. '),
  t('Результаты этой статьи — каталог из 83 форматов, полный набор пакетов соответствия на все 83 формата (49 битоточных + 34 структурных) с углублённо проверенным подмножеством Tier-1 из шести пакетов, кросс-уолк к P3109 v3.2.0 и два задокументированных интерпретационных разрыва — зависят только от артефактов, процитированных в библиографии и публично доступных (репозитории с открытой лицензией, опубликованные стандарты и препринт arXiv GoldenFloat). Ни одно утверждение, таблица или теорема в этой статье не опирается на неопубликованные или находящиеся на рецензировании рукописи. Предстоящие последующие работы по смежным темам упоминаются только как направление будущей работы в разделе 9 и явно выходят за рамки настоящего изложения.') ]));
children.push(body([
  t('Ни одно из этих ограничений не меняет центрального утверждения статьи: каталог из 83 форматов с полным набором пакетов соответствия на все 83 формата (49 битоточных + 34 структурных), углублённо проверенным подмножеством Tier-1 из шести пакетов, кросс-уолком к IEEE P3109 и двумя задокументированными интерпретационными разрывами теперь является пригодным, воспроизводимым вендор-нейтральным справочником. Они очерчивают то, чем артефакт является, в отличие от того, чем он не является.'),
]));

// =================== Acknowledgments ===================
children.push(H1('Благодарности'));
children.push(body([
  t('Автор благодарит сопровождающих '), mono('ml_dtypes'), t(' (Google/JAX) за предоставление эталонной реализации, а рабочую группу OCP Microscaling — за публикацию спецификации MX v1.0 в открытом доступе. Эта работа была выполнена в Trinity S³AI автором (ORCID 0009-0008-4294-6159). Автор благодарит рецензентов Tenstorrent tt-metal '),
  mono('@amahmudTT'), t(' и '), mono('@rtawfik01'), t(' за содержательную обратную связь по смежным веткам соответствия FP8, которая повлияла на постановку раздела 7. Никакой внешней финансовой поддержки в подготовке этого препринта не использовалось.'),
]));

// =================== References ===================
children.push(H1('Список литературы'));
const refs = [
  ['[1] ', 'D. Vasilev, «GoldenFloat: A phi-anchored numeric format family and the identity φ² + 1/φ² = 3», arXiv:2606.05017, 2026. https://arxiv.org/abs/2606.05017'],
  ['[2] ', 'C. Hunhold, «Takum arithmetic: A new paradigm for low-precision numerics», arXiv:2412.20273, 2024. https://arxiv.org/abs/2412.20273'],
  ['[3] ', 'C. Park, J.-H. Lim, S. Nagarakatte, «ProofWright: Towards verified floating-point arithmetic», arXiv:2511.12294v2, 2025. https://arxiv.org/abs/2511.12294'],
  ['[4] ', 'C. Chang, C. Park, J.-H. Lim, S. Nagarakatte, «P3109 FLoPS: A Lean 4 formalization of IEEE P3109 floating-point semantics», arXiv:2602.15965, 2026. https://arxiv.org/abs/2602.15965'],
  ['[5] ', 'B. Rouhani et al., «Microscaling data formats for deep learning», arXiv:2310.10537, 2023. https://arxiv.org/abs/2310.10537'],
  ['[6] ', 'A. Ouyang et al., «KernelBench: Can LLMs write efficient GPU kernels?», arXiv:2502.10517, 2025. https://arxiv.org/abs/2502.10517'],
  ['[7] ', 'NVIDIA, «Introducing NVFP4 for efficient and accurate low-precision inference», NVIDIA Technical Blog, 2025. https://developer.nvidia.com/blog/introducing-nvfp4-for-efficient-and-accurate-low-precision-inference/'],
  ['[8] ', 'M. Wang et al., «M²XFP: A unified mixed-precision microscaling floating-point representation for next-generation AI accelerators», arXiv:2601.19213, 2026 (to appear, ASPLOS \u201926). https://arxiv.org/abs/2601.19213'],
  ['[9] ', 'N. J. Higham, «Low-precision floating-point formats: The wild west of computer arithmetic», SIAM News, 2017. https://www.siam.org/publications/siam-news/'],
  ['[10] ', 'E. Carson, X. Chen, «Pychop: Emulating low-precision arithmetic in Python for ML and scientific computing», arXiv:2504.07835, 2025. https://arxiv.org/abs/2504.07835'],
  ['[11] ', 'C. M. Wintersteiger, «Floating-point conformance testing in industrial practice», Proc. IEEE ARITH 2025. https://arith2025.org/proceedings/215900a157.pdf'],
  ['[12] ', 'C. Hunhold, «libtakum: A reference C library for takum arithmetic», GitHub, 2024\u20132025. https://github.com/takum-arithmetic/libtakum'],
  ['[13] ', 'C. Hunhold, T. Quinlan, «Takum arithmetic in sparse iterative solvers: A precision-vs-storage study», arXiv:2412.20268, 2024. https://arxiv.org/abs/2412.20268'],
  ['[14] ', 'B. Noune et al., «8-bit numerical formats for deep neural networks», arXiv:2206.02915, 2022. https://arxiv.org/abs/2206.02915'],
  ['[15] ', 'IEEE Std 754-2019, IEEE Standard for Floating-Point Arithmetic, IEEE, New York, NY, 2019. https://standards.ieee.org/ieee/754/6210/'],
  ['[16] ', 'Open Compute Project, OCP Microscaling Formats (MX) Specification v1.0, OCP Foundation, 2023. https://www.opencompute.org/documents/ocp-microscaling-formats-mx-v1-0-spec-final-pdf'],
  ['[17] ', 'Google/JAX, ml_dtypes version 0.5.4: Low-precision float types for NumPy and JAX, 2024. https://github.com/jax-ml/ml_dtypes'],
  ['[18] ', 'IEEE P3109 Working Group, IEEE SA P3109 Interim Report v3.2.0: Standard for Floating-Point Arithmetic for AI, IEEE Standards Association, 2026. https://github.com/P3109/Public'],
];
for (const [n, txt] of refs) {
  children.push(new Paragraph({ spacing: { after: 80, line: 264 }, alignment: AlignmentType.JUSTIFIED,
    indent: { left: 480, hanging: 480 },
    children: [new TextRun({ text: n, font: FONT, size: 21, bold: true }), new TextRun({ text: txt, font: FONT, size: 21 })] }));
}

// Пояснение о списке References (журнал публикует единый список латиницей)
children.push(body([
  it('References (English transliteration) is produced by the editorial office from the entries above; all sources are cited in Latin script.'),
], { noindent: true }));

// =================== ОБ АВТОРЕ / ABOUT THE AUTHOR (требование журнала) ===================
children.push(H1('Об авторе'));
children.push(body([
  b('Васильев Дмитрий Владимирович '),
  t('— независимый исследователь (Trinity S³AI), г. Ко Самуи, Королевство Таиланд. Область научных интересов: численные форматы, арифметика пониженной точности, нейросимвольный ИИ, верифицируемые вычисления. ORCID: 0009-0008-4294-6159. Эл. почта: admin@t27.ai.'),
], { noindent: true }));
children.push(body([
  b('Vasilev Dmitrii Vladimirovich '),
  t('— independent researcher (Trinity S³AI), Ko Samui, Kingdom of Thailand. Research interests: numeric formats, low-precision arithmetic, neurosymbolic AI, verifiable computing. ORCID: 0009-0008-4294-6159. E-mail: admin@t27.ai.'),
], { noindent: true }));

// ============================ DOC ============================
const doc = new Document({
  creator: 'Dmitrii Vasilev',
  title: 'Каталог из 83 численных форматов с битоточными векторами соответствия',
  styles: {
    default: {
      document: { run: { font: FONT, size: SIZE }, paragraph: { spacing: { line: LINE } } },
    },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 30, bold: true, font: FONT, color: '000000' }, paragraph: { spacing: { before: 280, after: 140 }, outlineLevel: 0, keepNext: true } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 26, bold: true, font: FONT, color: '000000' }, paragraph: { spacing: { before: 220, after: 110 }, outlineLevel: 1, keepNext: true } },
    ],
  },
  numbering: {
    config: [
      { reference: 'bullets', levels: [{ level: 0, format: LevelFormat.BULLET, text: '\u2022', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 600, hanging: 300 } } } }] },
      { reference: 'steps', levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 600, hanging: 300 } } } }] },
      { reference: 'cons', levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 600, hanging: 300 } } } }] },
    ],
  },
  sections: [{
    // A4 (21×29.7см); поля: верх/низ 3.5см (1985 twips), лев/прав 2.5см (1417 twips)
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1985, right: 1417, bottom: 1985, left: 1417 } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
      children: [new TextRun({ text: 'Искусственный интеллект и принятие решений', italics: true, color: '888888', size: 16, font: FONT })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: 'Стр. ', size: 18, font: FONT }), new TextRun({ children: [PageNumber.CURRENT], size: 18, font: FONT }),
        new TextRun({ text: ' из ', size: 18, font: FONT }), new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 18, font: FONT })] })] }) },
    children,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync('/tmp/trinity-papers-ru/paper2-catalog/statya2_ru.docx', buf);
  console.log('WROTE statya2_ru.docx', buf.length, 'bytes; children=', children.length);
});
