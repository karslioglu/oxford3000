"""Kaynak Oxford 3000 PDF'ini (kelime, sözcük türü, CEFR seviyesi) satırlarına ayrıştırır.

Bu modül export_csv.py, export_xlsx.py ve export_sqlite.py tarafından ortak
kullanılır; PDF ayrıştırma mantığının tek doğru kaynağı burasıdır. Çıktı
formatına özgü kod (CSV/XLSX/SQLite yazma) burada değil, ilgili export_*.py
dosyasında yer alır.
"""

import re
from collections import defaultdict

import pdfplumber

# Homograph üst simge rakamı doğrudan kelimeye (harfler bitince) ekleniyor;
# ardından varsa parantez içi açıklama notu geliyor (ör. "last1 (final)").
HOMOGRAPH_DIGIT_RE = re.compile(r"^([A-Za-z]+)([0-9]+)(\s\(.+\))?$")

# Kaynak PDF'te gövde metni sadece bu 3 fontla yazılıyor:
#   MyriadPro-Regular   (9.0pt)  -> kelime (headword)
#   MyriadPro-Regular   (5.2pt)  -> homograph üst simge rakamı (ör. "close" + "1")
#   MyriadPro-LightIt   (9.0pt)  -> sözcük türü (italik, ör. "n.", "adv.")
#   MyriadPro-Light     (9.0pt)  -> CEFR seviyesi (ör. "A1")
# Başlık/altbilgi/sayfa numarası farklı font veya boyut kullandığı için bu
# filtreyle otomatik olarak elenir.
WORD_FONT = "MyriadPro-Regular"
WORD_SIZE = 9.0
SUPERSCRIPT_SIZE = 5.2
POS_FONT = "MyriadPro-LightIt"
LEVEL_FONT = "MyriadPro-Light"
BODY_SIZE = 9.0
SIZE_TOLERANCE = 0.3

# Var olan words tablosundaki parts_of_speech değerleriyle aynı stili
# kullanıyoruz (çoğu Title Case, "definite article"/"infinitive marker" ise
# kaynak PDF'teki gibi küçük harfle). "noun." kaynak PDF'te "n." yerine iki
# kez geçen bir dizgi hatası, o yüzden "n."yle aynı şeye eşleniyor.
POS_FULL_NAMES = {
    "n.": "Noun",
    "noun.": "Noun",
    "v.": "Verb",
    "adj.": "Adjective",
    "adv.": "Adverb",
    "prep.": "Preposition",
    "conj.": "Conjunction",
    "pron.": "Pronoun",
    "det.": "Determiner",
    "exclam.": "Exclamation",
    "number": "Number",
    "modal v.": "Modal Verb",
    "auxiliary v.": "Auxiliary Verb",
    "indefinite article": "indefinite article",
    "definite article": "definite article",
    "infinitive marker": "infinitive marker",
}


def classify(word):
    """Bir pdfplumber kelimesini (word/sup/pos/level/None) rolüne ayırır."""
    fontname = word["fontname"].split("+")[-1]
    size = word["size"]

    if fontname == WORD_FONT and abs(size - WORD_SIZE) < SIZE_TOLERANCE:
        return "word"
    if fontname == WORD_FONT and abs(size - SUPERSCRIPT_SIZE) < SIZE_TOLERANCE:
        return "sup"
    if fontname == POS_FONT and abs(size - BODY_SIZE) < SIZE_TOLERANCE:
        return "pos"
    if fontname == LEVEL_FONT and abs(size - BODY_SIZE) < SIZE_TOLERANCE:
        return "level"
    return None


def cluster_columns(x0_values, gap=60):
    """Headword x0 değerlerinden sütun sol kenarlarını bulur.

    Sütunlar sayfa genelinde ~130pt aralıklarla eşit yerleşmiş durumda, ama
    bazı sayfalarda tek bir kelime birkaç punto daha girintili başlayıp
    (ör. 20pt fark) küçük bir eşikle yanlışlıkla ayrı bir sütun sanılabiliyor
    ve o sütuna ait pos/seviye verisi başka bir kelimeye kayabiliyor. 60pt'lik
    eşik bu tür sapmaları asıl sütuna dahil ederken gerçek sütunları (aralarında
    ~130pt olan) hâlâ ayırt ediyor.
    """
    values = sorted(set(round(x, 1) for x in x0_values))
    columns = []
    for x in values:
        if not columns or x - columns[-1] > gap:
            columns.append(x)
    return columns


def assign_column(x0, columns):
    idx = 0
    for i, left in enumerate(columns):
        if x0 >= left - 1:
            idx = i
    return idx


def extract_page_entries(page):
    """Bir sayfadaki tüm kelimeleri (kelime, [(pos, seviye), ...]) olarak döner."""
    raw_words = page.extract_words(extra_attrs=["fontname", "size"])

    tagged = []
    for w in raw_words:
        role = classify(w)
        if role:
            tagged.append({**w, "role": role})

    if not tagged:
        return []

    columns = cluster_columns(w["x0"] for w in tagged if w["role"] == "word")

    by_column = {i: [] for i in range(len(columns))}
    for w in tagged:
        col = assign_column(w["x0"], columns)
        by_column[col].append(w)

    entries = []
    for col in sorted(by_column):
        stream = order_by_line(by_column[col])
        entries.extend(parse_column_stream(stream))

    return entries


def order_by_line(words, line_gap=3):
    """Kelimeleri satır satır (yukarıdan aşağı, soldan sağa) sıraya koyar.

    Homograph üst simge rakamı (ör. "close" + üst simge "1") kelimenin
    biraz üstünde konumlanır, bu yüzden ham 'top' değerine göre basitçe
    sıralamak onu bir önceki satırın sonuna kaydırabilir. Satırları önce
    büyük boşluklara (line_gap) göre kümeleyip, satır içinde x0'a göre
    sıralamak bunu önler.
    """
    by_top = sorted(words, key=lambda w: w["top"])

    lines = []
    prev_top = None
    for w in by_top:
        if prev_top is None or w["top"] - prev_top > line_gap:
            lines.append([])
        lines[-1].append(w)
        prev_top = w["top"]

    ordered = []
    for line in lines:
        ordered.extend(sorted(line, key=lambda w: w["x0"]))
    return ordered


def parse_column_stream(stream):
    """(word, [(pos, seviye), ...]) demetlerini üretir."""
    entries = []
    i = 0
    n = len(stream)

    while i < n:
        if stream[i]["role"] != "word":
            i += 1
            continue

        word_parts = [stream[i]["text"]]
        i += 1
        while i < n and stream[i]["role"] in ("word", "sup"):
            if stream[i]["role"] == "sup":
                word_parts[-1] += stream[i]["text"]
            else:
                word_parts.append(stream[i]["text"])
            i += 1
        headword = " ".join(word_parts)

        # Bazı homograph çiftleri rakamla değil, parantez içi bir açıklamayla
        # ayrılıyor: "last1 (final)" / "last1 (taking time)", ya da hiç rakam
        # olmadan "bank (money)" / "bank (river)". Bu açıklama kimi zaman
        # seviye fontuyla kimi zaman sözcük türü fontuyla yazıldığından fonta
        # değil, "(" ile başlayıp ")" ile biten token dizisine bakıyoruz.
        note_words = []
        if i < n and stream[i]["text"].startswith("("):
            while i < n and stream[i]["role"] != "word":
                note_words.append(stream[i]["text"])
                ends_note = stream[i]["text"].endswith(")")
                i += 1
                if ends_note:
                    break
        if note_words:
            headword = f"{headword} {' '.join(note_words)}"

        pending_pos = []
        current_words = []
        pairs = []

        while i < n and stream[i]["role"] != "word":
            tok = stream[i]
            if tok["role"] == "pos":
                had_comma = tok["text"].endswith(",")
                core = tok["text"].rstrip(",")
                if core:
                    if current_words and current_words[-1].endswith(("/", "-")):
                        current_words[-1] += core
                    else:
                        current_words.append(core)
                if had_comma and current_words:
                    pending_pos.append(" ".join(current_words))
                    current_words = []
            elif tok["role"] == "level":
                if current_words:
                    pending_pos.append(" ".join(current_words))
                    current_words = []
                level = tok["text"].rstrip(",")
                for pos in pending_pos:
                    # "/" gerçekten farklı sözcük türlerini kısaca yan yana
                    # yazmak için kullanılıyor (ör. "conj./adv.", "det./pron."),
                    # bu yüzden virgül gibi ayrı satırlara bölünmeli. Çok
                    # kelimeli tek bir etiket olan "modal v." gibi durumlar
                    # boşlukla ayrıldığından bundan etkilenmiyor.
                    for part in pos.split("/"):
                        part = part.strip()
                        if part:
                            pairs.append((part, level))
                pending_pos = []
            i += 1

        entries.append((headword, pairs))

    return entries


def fix_known_source_quirks(rows):
    """Kaynak PDF'teki tek seferlik dizgi tuhaflığını düzeltir.

    "according to" ifadesinin ikinci kelimesi ("to") kaynak PDF'te kelime
    değil sözcük türü fontuyla (italik) basılmış, bu yüzden ayrıştırıcı onu
    yanlışlıkla pos'un başına ekliyor ("according" / "to prep." yerine
    "according to" / "prep." olması gerekiyor). Belgede bu tarz tek örnek.
    """
    fixed = []
    for word, pos, cefr in rows:
        if word == "according" and pos == "to prep.":
            word, pos = "according to", "prep."
        fixed.append((word, pos, cefr))
    return fixed


def drop_safe_homograph_digits(rows):
    """Çakışmaya yol açmayan homograph üst simge rakamlarını kaldırır.

    "close1"/"close2" gibi çiftlerde rakam olmadan da sözcük türü zaten
    ayrımı koruyor (Verb/Adjective vb.), o yüzden rakamı kaldırmak güvenli.
    Ama "tear1"/"tear2" gibi bazı çiftlerde iki farklı anlam AYNI sözcük
    türü + seviyeye sahip (ikisi de Noun/B2); rakamı kaldırırsak bu iki
    farklı anlam birbirinin aynı, ayırt edilemez satıra dönüşür — bu
    durumda rakam korunur. Karar, her bir kök kelime için (pos, cefr)
    çiftlerinin gerçekten çakışıp çakışmadığına bakılarak veriden
    hesaplanır, sabit bir liste kullanılmaz.
    """
    groups = defaultdict(set)
    bases = {}
    for word, pos, cefr in rows:
        match = HOMOGRAPH_DIGIT_RE.match(word)
        if not match:
            continue
        base = match.group(1) + (match.group(3) or "")
        bases[word] = base
        groups[base].add((pos, cefr))

    # Bir kök için toplam (pos, cefr) çift sayısı, o kökü paylaşan
    # kelimelerin satır sayısından azsa demek ki bir çakışma var.
    unsafe_bases = set()
    counts = defaultdict(int)
    for word, pos, cefr in rows:
        if word in bases:
            counts[bases[word]] += 1
    for base, pairs in groups.items():
        if len(pairs) < counts[base]:
            unsafe_bases.add(base)

    result = []
    for word, pos, cefr in rows:
        base = bases.get(word)
        if base is not None and base not in unsafe_bases:
            word = base
        result.append((word, pos, cefr))
    return result


def parse_pdf(pdf_path):
    """Kaynak PDF'i (word, parts_of_speech, cefr) demetleri listesine dönüştürür.

    Sözcük türleri kısaltma değil tam ad olarak döner (ör. "n." -> "Noun").
    Tam adı bilinmeyen bir kısaltmayla karşılaşılırsa uyarı basılır ve
    kısaltma olduğu gibi bırakılır.
    """
    rows = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            for word, pairs in extract_page_entries(page):
                for pos, cefr in pairs:
                    rows.append((word, pos, cefr))

    rows = fix_known_source_quirks(rows)

    unknown_pos = sorted({pos for _, pos, _ in rows if pos not in POS_FULL_NAMES})
    if unknown_pos:
        print(f"⚠️ Tam adı bilinmeyen sözcük türü kısaltmaları (olduğu gibi bırakıldı): {unknown_pos}")

    rows = [(word, POS_FULL_NAMES.get(pos, pos), cefr) for word, pos, cefr in rows]
    return drop_safe_homograph_digits(rows)
