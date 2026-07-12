import sqlite3

from scripts import pdf_parser


def main(pdf_path, db_path):
    if not pdf_path.exists():
        print(f"❌ PDF bulunamadı: {pdf_path}")
        print("   Önce 'oxford3000.py download' komutuyla indirin.")
        return

    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    # Şema, eski oxford3000_.db ile uyumlu olacak şekilde birebir eşleşiyor
    # (words/examples/reading_texts), böylece bu DB o projedeki sentences.py,
    # reading_texts.py, translator.py gibi scriptlerle de kullanılabilir.
    # "description" ve "translate_tr" bu script tarafından doldurulmuyor,
    # NULL bırakılıyor; translate_tr'yi 'oxford3000.py translate' dolduruyor.
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS "words" (
            "id" INTEGER,
            "word" TEXT NOT NULL,
            "description" TEXT,
            "parts_of_speech" TEXT,
            "cefr" TEXT NOT NULL,
            "translate_tr" TEXT,
            PRIMARY KEY("id" AUTOINCREMENT)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS "examples" (
            "id" INTEGER,
            "word" INTEGER,
            "sentence" TEXT,
            PRIMARY KEY("id" AUTOINCREMENT)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS "reading_texts" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT,
            "title" TEXT,
            "content" TEXT,
            "cefr_level" TEXT,
            "related_word_ids" TEXT
        )
        """
    )
    conn.commit()

    print(f"📖 PDF okunuyor: {pdf_path}")
    rows = pdf_parser.parse_pdf(pdf_path)

    if not rows:
        print("❌ Hiçbir satır ayrıştırılamadı.")
        conn.close()
        return

    # "words" tablosunda zaten olan (word, parts_of_speech, cefr) satırlarına
    # dokunmuyoruz (ör. translate_tr üzerinde çalışılmış olabilir); sadece
    # PDF'te olup tabloda henüz bulunmayan satırları ekliyoruz.
    cursor.execute('SELECT word, parts_of_speech, cefr FROM "words"')
    existing = set(cursor.fetchall())

    new_rows = [row for row in rows if row not in existing]

    if not new_rows:
        print(f"✅ 'words' tablosu zaten güncel ({len(existing)} kayıt), eklenecek yeni satır yok: {db_path}")
        conn.close()
        return

    cursor.executemany(
        'INSERT INTO "words" (word, parts_of_speech, cefr) VALUES (?, ?, ?)', new_rows
    )
    conn.commit()
    conn.close()

    total = len(existing) + len(new_rows)
    print(f"✅ {len(new_rows)} yeni satır eklendi (toplam {total} kayıt): {db_path}")


if __name__ == "__main__":
    print("Bu script 'oxford3000.py sqlite' komutu ile çalıştırılmalıdır.")
