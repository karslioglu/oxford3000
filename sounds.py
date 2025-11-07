import requests
import time
import os
from pathlib import Path

API_URL = "https://api.soundoftext.com/sounds"

WORDS_FILE = "words.txt"
OUTPUT_DIR = Path("sounds")
OUTPUT_DIR.mkdir(exist_ok=True)


def create_sound(text, voice="en-US", engine="Google"):
    payload = {
        "engine": engine,
        "data": {
            "text": text,
            "voice": voice
        }
    }
    resp = requests.post(API_URL, json=payload, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    sound_id = data.get("id")
    if not sound_id:
        raise RuntimeError(f"Ses oluşturulamadı: {data}")
    return sound_id


def wait_for_sound(sound_id, poll_interval=1.0, max_wait=60):
    start_time = time.time()
    while True:
        resp = requests.get(f"{API_URL}/{sound_id}", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")
        if status == "Done":
            url = data.get("location")
            if not url:
                raise RuntimeError(f"Status Done ama URL yok: {data}")
            return url
        elif status == "Error":
            raise RuntimeError(f"Ses oluşturma hatası: {data}")
        if time.time() - start_time > max_wait:
            raise TimeoutError(f"Ses {max_wait} saniyede hazır olmadı (id={sound_id})")
        time.sleep(poll_interval)


def download_file(url, path: Path):
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    path.write_bytes(resp.content)


def sanitize_filename(name: str) -> str:
    bad_chars = r'\/:*?"<>|'
    for ch in bad_chars:
        name = name.replace(ch, "_")
    return name.strip()


def main():
    if not os.path.exists(WORDS_FILE):
        print(f"{WORDS_FILE} bulunamadı!")
        return

    with open(WORDS_FILE, "r", encoding="utf-8") as f:
        words = [line.strip() for line in f if line.strip()]

    print(f"{len(words)} kelime bulundu.")

    for i, word in enumerate(words, start=1):
        filename = sanitize_filename(word) or f"word_{i}"
        out_path = OUTPUT_DIR / f"{filename}.mp3"

        if out_path.exists():
            print(f"[{i}/{len(words)}] Atlaniyor: {word!r} (zaten mevcut)")
            continue

        print(f"[{i}/{len(words)}] İşleniyor: {word!r}")
        try:
            sound_id = create_sound(word, voice="en-US")  # gerekirse 'tr-TR'
            url = wait_for_sound(sound_id)
            download_file(url, out_path)
            print(f"  -> Kaydedildi: {out_path}")
            time.sleep(0.5)
        except Exception as e:
            print(f"  !! Hata: {e}")


if __name__ == "__main__":
    main()
