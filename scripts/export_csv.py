import csv

from scripts import pdf_parser


def main(pdf_path, csv_path):
    if not pdf_path.exists():
        print(f"❌ PDF bulunamadı: {pdf_path}")
        print("   Önce 'oxford3000.py download' komutuyla indirin.")
        return

    print(f"📖 PDF okunuyor: {pdf_path}")
    rows = pdf_parser.parse_pdf(pdf_path)

    if not rows:
        print("❌ Hiçbir satır ayrıştırılamadı.")
        return

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["word", "parts_of_speech", "cefr"])
        writer.writerows(rows)

    unique_words = len({r[0] for r in rows})
    print(f"✅ {len(rows)} satır ({unique_words} benzersiz kelime) yazıldı: {csv_path}")


if __name__ == "__main__":
    print("Bu script 'oxford3000.py csv' komutu ile çalıştırılmalıdır.")
