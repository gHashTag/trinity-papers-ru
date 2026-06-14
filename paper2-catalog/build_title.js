// Титульный лист статьи 2 по правилам «Искусственный интеллект и принятие решений»
const docx = require('docx');
const {
  Document, Packer, Paragraph, TextRun, AlignmentType, BorderStyle,
} = docx;

const FONT = 'Times New Roman';
const SIZE = 22;   // 11pt
const LINE = 360;  // 1.5
const REDLINE = 283;

function run(text, opts = {}) { return new TextRun({ text, font: FONT, size: SIZE, ...opts }); }
function center(children, opts = {}) {
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: opts.after ?? 80, line: LINE }, children });
}
function body(children, opts = {}) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED, spacing: { after: opts.after ?? 120, line: LINE },
    indent: opts.noindent ? undefined : { firstLine: REDLINE }, children,
  });
}
const hr = () => new Paragraph({
  spacing: { before: 120, after: 120 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: '000000', space: 1 } },
  children: [new TextRun({ text: '', size: 2 })],
});

const children = [];

// --- шапка ---
children.push(new Paragraph({ alignment: AlignmentType.LEFT, spacing: { after: 40, line: LINE },
  children: [run('В редакцию журнала «Искусственный интеллект и принятие решений»', { italics: true })] }));
children.push(new Paragraph({ alignment: AlignmentType.LEFT, spacing: { after: 40, line: LINE },
  children: [run('ФИЦ «Информатика и управление» РАН · научная специальность 1.2.1', { size: 20 })] }));
children.push(new Paragraph({ alignment: AlignmentType.LEFT, spacing: { after: 40, line: LINE },
  children: [run('УДК 004.222', { size: 20 })] }));
children.push(hr());

// --- русский блок ---
children.push(center([run('Каталог из 83 численных форматов с битоточными векторами соответствия:', { bold: true, size: 28 })], { after: 0 }));
children.push(center([run('вендор-нейтральный справочник для FP8, BF16, MXFP4 и микромасштабируемых форматов', { bold: true, size: 28 })], { after: 160 }));
children.push(center([run('© 2026 г.   Д. В. Васильев', { bold: true, size: 24 })], { after: 60 }));
children.push(center([run('Независимый исследователь (Trinity S³AI), Ко Самуи, Королевство Таиланд', { italics: true, size: 22 })], { after: 40 }));
children.push(center([run('e-mail: admin@t27.ai   |   ORCID: 0009-0008-4294-6159', { size: 22 })], { after: 160 }));

children.push(body([run('Аннотация. ', { bold: true }),
  run('В статье описаны: каталог из 83 численных форматов, охватывающий 13 семейств; набор из шести битоточных пакетов соответствия (conformance packs) для GF16, элемента MXFP4, BF16, FP8 E4M3, FP8 E5M2 и блочного масштаба E8M0; а также кросс-уолк к IEEE P3109 v3.2.0. Каждый пакет — самодостаточный документ JSON с отпечатком SHA-256, общей схемой строк и якорным вектором, кодирующим тождество φ² + 1/φ² = 3 как межпакетную проверку корректности. Пакеты перекрёстно проверены относительно эталонной реализации ml_dtypes 0.5.4 (Google/JAX); каждое расхождение документировано явно и интерпретируется как разрешённый спецификацией интерпретационный разрыв. Работа позиционируется как заполнение реестра: она не предлагает новых форматов, не делает утверждений о точности моделей и не заявляет о превосходстве над вендорскими реализациями. Все артефакты публично доступны (github.com/gHashTag/t27) под открытой лицензией.')]));
children.push(body([run('Ключевые слова: ', { bold: true }),
  run('численные форматы, форматы с плавающей точкой, conformance, IEEE P3109, золотое сечение, машинное обучение, битоточные векторы, микромасштабирование, FP8, BF16, MXFP4.')]));

children.push(hr());

// --- английский блок ---
children.push(center([run('An 83-format numeric catalog with bit-exact conformance vectors:', { bold: true, size: 28 })], { after: 0 }));
children.push(center([run('a vendor-neutral reference for FP8, BF16, MXFP4 and microscaling formats', { bold: true, size: 28 })], { after: 160 }));
children.push(center([run('© 2026   D. V. Vasilev', { bold: true, size: 24 })], { after: 60 }));
children.push(center([run('Independent researcher (Trinity S³AI), Ko Samui, Kingdom of Thailand', { italics: true, size: 22 })], { after: 40 }));
children.push(center([run('e-mail: admin@t27.ai   |   ORCID: 0009-0008-4294-6159', { size: 22 })], { after: 160 }));

children.push(body([run('Abstract. ', { bold: true }),
  run('This paper presents: a catalog of 83 numeric formats spanning 13 families; a set of six bit-exact conformance packs for GF16, the MXFP4 element, BF16, FP8 E4M3, FP8 E5M2 and the E8M0 block scale; and a crosswalk to IEEE P3109 v3.2.0 mapping each pack to its configurable form of the standard. Every pack is a self-contained JSON document with a SHA-256 fingerprint, a shared row schema and an anchor vector encoding the value 3.0 — the identity phi^2 + 1/phi^2 = 3 — as a cross-pack correctness check. Packs are cross-checked against ml_dtypes 0.5.4 (Google/JAX); any discrepancy is documented explicitly and interpreted as a specification-permitted interpretive gap. The work is positioned as registry-filling: it proposes no new formats, makes no model-accuracy claim and asserts no superiority over any vendor implementation. All artefacts are publicly available at github.com/gHashTag/t27 under an open license.')]));
children.push(body([run('Keywords: ', { bold: true }),
  run('numeric formats, floating point, conformance, IEEE P3109, golden ratio, machine learning, bit-exact vectors, microscaling, FP8, BF16, MXFP4.')]));

children.push(hr());

// --- сведения для редакции ---
children.push(body([run('Сведения для редакции. ', { bold: true }),
  run('Статья оригинальна, ранее не публиковалась и не подавалась в другие издания. Конфликт интересов отсутствует, внешнее финансирование не привлекалось. Рукопись оформлена единым файлом MS Word (.docx) и содержит русско- и англоязычные версии названия, сведений об авторе, аннотации и ключевых слов; текст чёрно-белый, формат А4. По требованию редакции автор готов предоставить лицензионный договор (скан) и экспертное заключение о возможности открытого опубликования (с открытой печатью). Тема письма при подаче: «ИИПР Васильев».', { size: 20 })]));

const doc = new Document({
  creator: 'Dmitrii Vasilev',
  title: 'Титульный лист — Каталог 83 форматов',
  styles: { default: { document: { run: { font: FONT, size: SIZE }, paragraph: { spacing: { line: LINE } } } } },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1985, right: 1417, bottom: 1985, left: 1417 } } },
    children,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  require('fs').writeFileSync('title_page_aidt.docx', buf);
  console.log('WROTE title_page_aidt.docx', buf.length, 'bytes; children=', children.length);
});
