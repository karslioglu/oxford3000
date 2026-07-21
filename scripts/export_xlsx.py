from openpyxl import Workbook

from scripts import db_reader


def main(db_path, xlsx_path):
    if not db_path.exists():
        print(f"❌ Veritabanı bulunamadı: {db_path}")
        print("   Önce 'oxford3000.py sqlite' komutuyla oluşturun.")
        return

    rows = db_reader.fetch_words(db_path)
    if not rows:
        print("❌ Veritabanında hiç kelime yok.")
        return

    xlsx_path.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "Oxford 3000"
    ws.append(["word", "parts_of_speech", "cefr", "translate_tr"])
    for row in rows:
        ws.append(row)
    wb.save(xlsx_path)

    unique_words = len({r[0] for r in rows})
    print(f"✅ {len(rows)} satır ({unique_words} benzersiz kelime) yazıldı: {xlsx_path}")


if __name__ == "__main__":
    print("Bu script 'oxford3000.py xlsx' komutu ile çalıştırılmalıdır.")
