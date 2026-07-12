import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

try:
    from scripts import download_pdf, examples, export_csv, export_sqlite, export_xlsx, sounds, translate
except ImportError as e:
    print(f"❌ Modül import hatası: {e}")
    print("Lütfen 'scripts' klasöründe '__init__.py' dosyasının olduğundan emin olun.")
    sys.exit(1)

# --- KONFİGÜRASYON ---
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)
API_KEY = os.getenv("GEMINI_API_KEY")

PDF_URL = "https://www.oxfordlearnersdictionaries.com/external/pdf/wordlists/oxford-3000-5000/American_Oxford_3000.pdf"
PDF_PATH = BASE_DIR / "data" / "raw" / "American_Oxford_3000_CEFR.pdf"
CSV_PATH = BASE_DIR / "data" / "oxford3000.csv"
XLSX_PATH = BASE_DIR / "data" / "oxford3000.xlsx"
DB_PATH = BASE_DIR / "data" / "oxford3000.db"
SOUNDS_DIR = BASE_DIR / "data" / "sounds"


def require_api_key():
    if not API_KEY:
        print(f"❌ 'GEMINI_API_KEY' bulunamadı! Lütfen '{ENV_PATH}' dosyasını kontrol edin.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Oxford 3000 - İçerik Yönetim Aracı",
        epilog="Örnek: python oxford3000.py csv",
    )

    subparsers = parser.add_subparsers(dest="command", help="Kullanılabilir Komutlar")
    subparsers.add_parser("download", help="Kaynak PDF'i Oxford Learner's Dictionaries'ten indirir")
    subparsers.add_parser("csv", help="Kaynak PDF'i (kelime, sözcük türü, seviye) CSV'sine dönüştürür")
    subparsers.add_parser("xlsx", help="Kaynak PDF'i (kelime, sözcük türü, seviye) Excel dosyasına dönüştürür")
    subparsers.add_parser("sqlite", help="Kaynak PDF'i (kelime, sözcük türü, seviye) SQLite veritabanına dönüştürür")
    subparsers.add_parser("sounds", help="Kelimelerin telaffuz MP3 dosyalarını indirir")
    subparsers.add_parser("translate", help="SQLite'daki kelimeleri sözcük türü/seviyeye göre Türkçeye çevirir")
    subparsers.add_parser("examples", help="Her kelime/sözcük türü/seviye için 3 örnek cümle üretip examples tablosuna yazar")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "download":
            download_pdf.main(PDF_URL, PDF_PATH)
        elif args.command == "csv":
            export_csv.main(PDF_PATH, CSV_PATH)
        elif args.command == "xlsx":
            export_xlsx.main(PDF_PATH, XLSX_PATH)
        elif args.command == "sqlite":
            export_sqlite.main(PDF_PATH, DB_PATH)
        elif args.command == "sounds":
            sounds.main(PDF_PATH, SOUNDS_DIR)
        elif args.command == "translate":
            require_api_key()
            translate.main(API_KEY, DB_PATH)
        elif args.command == "examples":
            require_api_key()
            examples.main(API_KEY, DB_PATH)
    except KeyboardInterrupt:
        print("\n⛔ İşlem kullanıcı tarafından durduruldu.")
        sys.exit(0)


if __name__ == "__main__":
    main()
