import csv

from scripts import db_reader


def main(db_path, csv_path):
    if not db_path.exists():
        print(f"❌ Veritabanı bulunamadı: {db_path}")
        print("   Önce 'oxford3000.py sqlite' komutuyla oluşturun.")
        return

    rows = db_reader.fetch_words(db_path)
    if not rows:
        print("❌ Veritabanında hiç kelime yok.")
        return

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["word", "parts_of_speech", "cefr", "translate_tr"])
        writer.writerows(rows)

    unique_words = len({r[0] for r in rows})
    print(f"✅ {len(rows)} satır ({unique_words} benzersiz kelime) yazıldı: {csv_path}")


if __name__ == "__main__":
    print("Bu script 'oxford3000.py csv' komutu ile çalıştırılmalıdır.")
