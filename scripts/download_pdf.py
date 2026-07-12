import requests


def main(url, pdf_path):
    if pdf_path.exists():
        print(f"✅ PDF zaten mevcut, indirme atlanıyor: {pdf_path}")
        return

    print(f"⬇️  PDF indiriliyor: {url}")
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ İndirme hatası: {e}")
        return

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(resp.content)

    print(f"✅ {len(resp.content)} bayt indirildi: {pdf_path}")


if __name__ == "__main__":
    print("Bu script 'oxford3000.py download' komutu ile çalıştırılmalıdır.")
