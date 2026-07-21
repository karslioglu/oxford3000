import json
import math
import sqlite3
import time

# Sabit bir sürüme (ör. "gemini-2.0-flash") değil kayan bir takma ada
# bağlanıyoruz; sabit sürümler zamanla "artık kullanılamıyor" hatası
# vermeye başlıyor (bu tam olarak başımıza geldi), takma ad Google
# tarafında güncel bir modele yönlendirilmeye devam ediyor.
MODEL_NAME = "gemini-flash-latest"

BATCH_SIZE = 30


def clean_json_text(text):
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


def translate_batch(client, items):
    """Bir grup kelimeyi tek seferde API'ye gönderip Türkçe çeviri ister."""
    prompt = (
        "You are a linguistic expert building a dictionary database. Translate the "
        "following English words to Turkish. STRICT INSTRUCTIONS:\n"
        "1. Each item has a 'pos' (part of speech, e.g. Noun, Verb, Adjective) and a "
        "'cefr' level. The SAME word can appear multiple times with a DIFFERENT pos — "
        "treat each one as a separate sense and give a translation that matches that "
        "exact part of speech, not a generic one.\n"
        "   - Example: 'close' as Verb -> 'kapatmak'; 'close' as Adjective -> 'yakın'.\n"
        "   - Example: 'book' as Noun -> 'kitap'; 'book' as Verb -> 'yer ayırtmak'.\n"
        "2. Keep translations concise (1-2 words mostly).\n"
        "3. Return ONLY a valid JSON array. Format: "
        '[{"id": 123, "translate_tr": "türkçe_karşılık"}]\n\n'
        f"Input Data: {json.dumps(items)}"
    )

    # Kota/geçersiz-anahtar hataları kasıtlı olarak burada yutulmuyor;
    # main()'daki yeniden deneme döngüsünün onları yakalaması gerekiyor.
    response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
    if not response.text:
        return None
    return json.loads(clean_json_text(response.text))


def main(api_key, db_path):
    try:
        from google import genai
        from google.genai import errors
    except ImportError:
        print("❌ 'google-genai' kütüphanesi eksik.")
        return

    if not db_path.exists():
        print(f"❌ Veritabanı bulunamadı: {db_path}")
        print("   Önce 'oxford3000.py sqlite' komutuyla oluşturun.")
        return

    client = genai.Client(api_key=api_key)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        cursor.execute(
            'SELECT id, word, parts_of_speech, cefr FROM "words" '
            "WHERE translate_tr IS NULL OR translate_tr = ''"
        )
        rows = cursor.fetchall()
    except sqlite3.OperationalError as e:
        print(f"❌ 'words' tablosu okunamadı: {e}")
        print("   Önce 'oxford3000.py sqlite' komutuyla oluşturun.")
        conn.close()
        return

    total = len(rows)
    print(f"📊 Çevrilecek kayıt sayısı: {total}")

    if total == 0:
        print("✅ Tüm kelimeler zaten çevrilmiş.")
        conn.close()
        return

    data = [{"id": r[0], "word": r[1], "pos": r[2], "cefr": r[3]} for r in rows]
    num_batches = math.ceil(total / BATCH_SIZE)

    translated = 0
    for i in range(num_batches):
        batch = data[i * BATCH_SIZE : (i + 1) * BATCH_SIZE]
        print(f"🔄 Batch {i + 1}/{num_batches} işleniyor ({len(batch)} kelime)...", end=" ")

        retry_count = 0
        while True:
            try:
                translations = translate_batch(client, batch)
                break
            except errors.ClientError as e:
                if e.code == 429:
                    # Kota doldu — bekleyip tekrar dene.
                    wait_time = 70 + (retry_count * 10)
                    print(f"⏳ kota doldu, {wait_time}s bekleniyor...", end=" ")
                    time.sleep(wait_time)
                    retry_count += 1
                    if retry_count > 3:
                        translations = None
                        break
                    continue
                # Geçersiz anahtar, artık kullanılamayan model vb. hatalar her
                # batch'te aynı şekilde başarısız olur; tekrar tekrar denemek
                # yerine temiz bir mesajla hemen durduruyoruz.
                print(f"\n❌ API hatası: {e.message}")
                print("   'GEMINI_API_KEY' değerinin doğru ve modelin ("
                      f"{MODEL_NAME}) kullanılabilir olduğundan emin olun.")
                conn.close()
                return
            except errors.ServerError as e:
                # Geçici bir sunucu tarafı hata olabilir, birkaç kez dene.
                retry_count += 1
                if retry_count > 3:
                    print(f"\n⛔ Sunucu hatası devam ediyor, durduruluyor: {e}")
                    conn.close()
                    return
                print(f"\n❌ Sunucu hatası: {e}. 10s bekleyip tekrar denenecek.", end=" ")
                time.sleep(10)
                continue

        if translations:
            update_count = 0
            for item in translations:
                tr_text = item.get("translate_tr")
                row_id = item.get("id")
                if tr_text and row_id:
                    cursor.execute(
                        'UPDATE "words" SET translate_tr = ? WHERE id = ?', (tr_text, row_id)
                    )
                    update_count += 1
            conn.commit()
            translated += update_count
            print(f"✅ {update_count} kayıt güncellendi.")
        else:
            print("❌ Başarısız (boş yanıt).")

        time.sleep(1.5)

    conn.close()
    print(f"✅ Tamamlandı. Toplam {translated} kayıt çevrildi: {db_path}")


if __name__ == "__main__":
    print("Bu script 'oxford3000.py translate' komutu ile çalıştırılmalıdır.")
