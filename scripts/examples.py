import json
import sqlite3
import time

# translate.py ile aynı gerekçe: sabit sürüm değil kayan takma ad.
MODEL_NAME = "gemini-flash-latest"


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
            'WHERE id NOT IN (SELECT DISTINCT word FROM "examples") '
            "ORDER BY id ASC"
        )
        rows = cursor.fetchall()
    except sqlite3.OperationalError as e:
        print(f"❌ 'words'/'examples' tablosu okunamadı: {e}")
        print("   Önce 'oxford3000.py sqlite' komutuyla oluşturun.")
        conn.close()
        return

    total = len(rows)
    print(f"📊 Örnek cümle üretilecek kayıt sayısı: {total}")

    if total == 0:
        print("✅ Tüm kelimeler için örnek cümleler zaten oluşturulmuş.")
        conn.close()
        return

    print("İşlem başlıyor... (Durdurmak için Ctrl+C)")

    generated = 0
    for index, (word_id, word_text, pos, cefr) in enumerate(rows, start=1):
        prompt = (
            f"Write exactly 3 simple example sentences in English using the word '{word_text}' "
            f"which functions as a '{pos}'. "
            f"The sentences must be suitable for CEFR level {cefr}. "
            'Return ONLY a raw JSON array of strings. Example: ["Sentence 1.", "Sentence 2.", "Sentence 3."]'
        )

        retry_count = 0
        while True:
            try:
                response = client.models.generate_content(model=MODEL_NAME, contents=prompt)

                if not response.text:
                    print(f"[{index}/{total}] ❌ Boş yanıt: {word_text!r}. Atlanıyor.")
                    break

                try:
                    sentences = json.loads(clean_json_text(response.text))
                except json.JSONDecodeError:
                    print(f"[{index}/{total}] ❌ JSON hatası: {word_text!r}. Atlanıyor.")
                    break

                if not isinstance(sentences, list) or not sentences:
                    print(f"[{index}/{total}] ❌ Liste dönmedi: {word_text!r}. Atlanıyor.")
                    break

                cursor.executemany(
                    'INSERT INTO "examples" (word, sentence) VALUES (?, ?)',
                    [(word_id, str(s)) for s in sentences],
                )
                conn.commit()
                generated += len(sentences)

                percent = (index / total) * 100
                print(f"[{index}/{total}] %{percent:.1f} - Eklendi: {word_text} ({pos}, {cefr})")
                break

            except errors.ClientError as e:
                if e.code == 429:
                    wait_time = 70 + (retry_count * 10)
                    print(f"⏳ Kota doldu ({word_text}). {wait_time}s bekleniyor... (deneme {retry_count + 1})")
                    time.sleep(wait_time)
                    retry_count += 1
                    continue
                # Geçersiz anahtar, artık kullanılamayan model vb. hatalar her
                # kelimede aynı şekilde başarısız olur; kelime kelime tekrar
                # denemek yerine temiz bir mesajla hemen durduruyoruz.
                print(f"\n❌ API hatası: {e.message}")
                print("   'GEMINI_API_KEY' değerinin doğru ve modelin ("
                      f"{MODEL_NAME}) kullanılabilir olduğundan emin olun.")
                conn.close()
                return

            except errors.ServerError as e:
                retry_count += 1
                if retry_count > 3:
                    print(f"[{index}/{total}] ⛔ {word_text!r} atlanıyor: {e}")
                    break
                print(f"[{index}/{total}] ❌ Sunucu hatası ({word_text}): {e}. 10s bekleyip tekrar denenecek.")
                time.sleep(10)
                continue

        time.sleep(4)

    conn.close()
    print(f"✅ Tamamlandı. Toplam {generated} örnek cümle eklendi: {db_path}")


if __name__ == "__main__":
    print("Bu script 'oxford3000.py examples' komutu ile çalıştırılmalıdır.")
