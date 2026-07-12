import json
import math
import sqlite3
import time

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


def translate_batch(model, items):
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

    # ResourceExhausted (kota) hatası kasıtlı olarak burada yutulmuyor;
    # main()'daki yeniden deneme döngüsünün onu yakalayıp beklemesi gerekiyor.
    response = model.generate_content(prompt)
    if not response.text:
        return None
    return json.loads(clean_json_text(response.text))


def main(api_key, db_path):
    try:
        import google.generativeai as genai
        from google.api_core import exceptions
    except ImportError:
        print("❌ 'google-generativeai' kütüphanesi eksik.")
        return

    if not db_path.exists():
        print(f"❌ Veritabanı bulunamadı: {db_path}")
        print("   Önce 'oxford3000.py sqlite' komutuyla oluşturun.")
        return

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

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
                translations = translate_batch(model, batch)
                break
            except exceptions.ResourceExhausted:
                wait_time = 70 + (retry_count * 10)
                print(f"⏳ kota doldu, {wait_time}s bekleniyor...", end=" ")
                time.sleep(wait_time)
                retry_count += 1
                if retry_count > 3:
                    translations = None
                    break

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
