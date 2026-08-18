#!/usr/bin/env python3
"""Rebuild the evaluation corpora byte-for-byte checkable against the SHA-256 values in README_ru.md.

We do not redistribute the corpus text: Wikipedia article text is CC BY-SA 4.0 and the
English slice comes from Project Gutenberg. This script fetches the sources and applies
the exact same slicing, so anyone can regenerate the file and compare its hash.

Usage:  python3 build_corpus.py en   -> /tmp/eval_en.txt
        python3 build_corpus.py ru2  -> /tmp/eval_ru_v2.txt
"""
import sys, hashlib, urllib.request

EN_URL = "https://www.gutenberg.org/cache/epub/2600/pg2600.txt"   # War and Peace, public domain
EN_START_MARK = "CHAPTER I"
EN_CHARS = 300_000

RU_V1 = ["Троичная_логика", "Сетунь_(компьютер)", "Число_с_плавающей_запятой", "Нейронная_сеть"]
RU_V2_EXTRA = ["Троичная_система_счисления", "Квантование_(обработка_сигналов)",
               "Программируемая_пользователем_вентильная_матрица",
               "Трансформер_(модель_машинного_обучения)", "Машинное_обучение",
               "Оперативная_память", "Золотое_сечение", "Verilog"]

def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "trinity-measurement/1.0"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "ru2"
    if which == "en":
        txt = get(EN_URL)
        i = txt.index(EN_START_MARK)
        out = txt[i:i + EN_CHARS]
        path = "/tmp/eval_en.txt"
    else:
        # NOTE: the numbers in README_ru.md were produced from plain-text article renderings.
        # Any extractor change alters the bytes, so always compare the printed SHA-256 before
        # citing a perplexity value as reproduced.
        parts = []
        for title in (RU_V1 + RU_V2_EXTRA):
            parts.append(get(f"https://ru.wikipedia.org/api/rest_v1/page/html/{title}"))
        out = "\n\n".join(parts)
        path = "/tmp/eval_ru_v2.txt"
    open(path, "w").write(out)
    print(path, len(out), "chars, sha256 =", sha(path))
