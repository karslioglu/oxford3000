import re
import time
from collections import Counter

import requests

from scripts import db_reader

API_URL = "https://api.soundoftext.com/sounds"


def create_sound(text, voice="en-US", engine="Google"):
    payload = {
        "engine": engine,
        "data": {
            "text": text,
            "voice": voice,
        },
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


def download_file(url, path):
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    path.write_bytes(resp.content)


def sanitize_filename(name):
    bad_chars = r'\/:*?"<>|'
    for ch in bad_chars:
        name = name.replace(ch, "_")
    return name.strip()


def spoken_text(word):
    """TTS'e gönderilecek metni hazırlar.

    pdf_parser çıktısındaki homograph rakamı (ör. "close1") ve parantez içi
    açıklama notu (ör. "last1 (final)") gerçek kelimenin bir parçası değil;
    TTS bunları harfiyen okumasın diye temizleniyor. Dosya adında ayrımın
    korunması için ORİJİNAL word metni (rakam/not dahil) kullanılmaya devam
    ediyor, sadece seslendirilecek metin sadeleştiriliyor.
    """
    text = re.sub(r"\s*\([^)]*\)\s*$", "", word)
    text = re.sub(r"\d+$", "", text)
    return text.strip()


def build_filename(word, pos, ambiguous):
    """(word, pos) çifti için dosya adını üretir.

    pdf_parser artık çakışmayan homograph rakamlarını kaldırdığından aynı
    yazılış birden fazla sözcük türü altında görünebilir (ör. "close" hem
    Verb hem Adjective). Böyle bir kelimede dosya adına türü de ekleyip
    ayırıyoruz; tek türlü kelimelerde sade "kelime.mp3" yeterli.
    """
    base = sanitize_filename(word)
    if ambiguous:
        base = f"{base}_{sanitize_filename(pos)}"
    return base


def main(db_path, output_dir):
    if not db_path.exists():
        print(f"❌ Veritabanı bulunamadı: {db_path}")
        print("   Önce 'oxford3000.py sqlite' komutuyla oluşturun.")
        return

    rows = db_reader.fetch_words(db_path)
    if not rows:
        print("❌ Veritabanında hiç kelime yok.")
        return

    # Benzersizlik anahtarı sadece "word" değil (word, pos) olmalı: aynı
    # yazılışa sahip ama farklı sözcük türüne (dolayısıyla muhtemelen farklı
    # telaffuza) sahip kelimeler var. Sadece word'e göre tekilleştirseydik bu
    # çiftlerden biri hiç seslendirilmezdi.
    items = sorted({(word, pos) for word, pos, _cefr, _tr in rows})
    pos_counts = Counter(word for word, _ in items)

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"🔊 {len(items)} benzersiz (kelime, sözcük türü) çifti için ses indirme işlemi başlıyor...")

    downloaded = 0
    for i, (word, pos) in enumerate(items, start=1):
        ambiguous = pos_counts[word] > 1
        filename = build_filename(word, pos, ambiguous) or f"word_{i}"
        out_path = output_dir / f"{filename}.mp3"
        label = f"{word} ({pos})" if ambiguous else word

        if out_path.exists():
            print(f"[{i}/{len(items)}] Atlanıyor: {label!r} (zaten mevcut)")
            continue

        print(f"[{i}/{len(items)}] İşleniyor: {label!r}")
        try:
            sound_id = create_sound(spoken_text(word))
            url = wait_for_sound(sound_id)
            download_file(url, out_path)
            print(f"  -> Kaydedildi: {out_path}")
            downloaded += 1
            time.sleep(0.5)
        except Exception as e:
            print(f"  !! Hata: {e}")

    print(f"✅ Tamamlandı. {downloaded} yeni dosya indirildi: {output_dir}")


if __name__ == "__main__":
    print("Bu script 'oxford3000.py sounds' komutu ile çalıştırılmalıdır.")
