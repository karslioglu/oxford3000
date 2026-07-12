from openpyxl import Workbook

from scripts import pdf_parser


def main(pdf_path, xlsx_path):
    if not pdf_path.exists():
        print(f"❌ PDF bulunamadı: {pdf_path}")
        print("   Önce 'oxford3000.py download' komutuyla indirin.")
        return

    print(f"📖 PDF okunuyor: {pdf_path}")
    rows = pdf_parser.parse_pdf(pdf_path)

    if not rows:
        print("❌ Hiçbir satır ayrıştırılamadı.")
        return

    xlsx_path.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "Oxford 3000"
    ws.append(["word", "parts_of_speech", "cefr"])
    for row in rows:
        ws.append(row)
    wb.save(xlsx_path)

    unique_words = len({r[0] for r in rows})
    print(f"✅ {len(rows)} satır ({unique_words} benzersiz kelime) yazıldı: {xlsx_path}")


if __name__ == "__main__":
    print("Bu script 'oxford3000.py xlsx' komutu ile çalıştırılmalıdır.")
