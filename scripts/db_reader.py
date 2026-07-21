"""oxford3000.db'deki 'words' tablosunu okumak için tek doğru kaynak.

export_csv.py, export_xlsx.py ve sounds.py bu modülü ortak kullanır; PDF'i
ayrıştırıp veritabanını oluşturan tek yer export_sqlite.py'dir (pdf_parser.py
üzerinden) — bu üçü artık PDF'i değil, veritabanını okur.
"""

import sqlite3


def fetch_words(db_path):
    """(word, parts_of_speech, cefr, translate_tr) satırlarını döner."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute('SELECT word, parts_of_speech, cefr, translate_tr FROM "words" ORDER BY word ASC')
    rows = cursor.fetchall()
    conn.close()
    return rows
