# Oxford 3000

Bu depo, Oxford 3000 (Amerikan İngilizcesi) kelime listesini kaynak PDF'ten
ayrıştırıp kelime + sözcük türü + CEFR seviyesi kırılımında bir SQLite
veritabanına yazan, ardından bu veritabanını Türkçe çeviri ve İngilizce
örnek cümlelerle zenginleştiren, ve sonucu CSV/Excel'e aktarıp telaffuz
(MP3) indirebilen bir komut satırı aracıdır.

Aynı kelime, farklı sözcük türleri için birden fazla satır olarak listelenir
(bir kelimenin farklı türler için farklı anlamları olabildiğinden).

**_Örnek (`csv`/`xlsx` çıktısı):_**

| word | parts_of_speech | cefr | translate_tr |
|------|------------------|:----:|--------------|
| key  | Noun             | A1   | anahtar      |
| key  | Adjective        | A1   | en önemli    |
| key  | Verb             | B1   | girmek       |

## Kurulum

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # sadece 'translate' komutu için: GEMINI_API_KEY'i doldurun
```

## Kullanım

Her şey `oxford3000.py` üzerinden çalışır. Sadece `sqlite` kaynak PDF'i
ayrıştırır; `csv`/`xlsx`/`sounds` PDF'e değil, veritabanına bakar — yani
akış her zaman bu sırayla ilerler:

```bash
# Ana akış
python oxford3000.py download   # Kaynak PDF'i Oxford Learner's Dictionaries'ten indirir
python oxford3000.py sqlite     # PDF'i ayrıştırıp data/oxford3000.db'yi oluşturur/günceller
python oxford3000.py translate  # data/oxford3000.db'deki kelimeleri Türkçeye çevirir
python oxford3000.py examples   # data/oxford3000.db'ye her kayıt için 3 örnek cümle ekler

# Yardımcı komutlar: veritabanından dışa aktarım
python oxford3000.py csv        # data/oxford3000.csv üretir (word, parts_of_speech, cefr, translate_tr)
python oxford3000.py xlsx       # data/oxford3000.xlsx üretir (aynı sütunlar)
python oxford3000.py sounds     # data/sounds/ altına telaffuz MP3'lerini indirir
```

`download`, `sqlite`, `csv`, `xlsx`, `sounds` komutları API anahtarı
gerektirmez; `translate` ve `examples` için `.env` içinde `GEMINI_API_KEY`
gerekir. `csv`/`xlsx`/`sounds` çalışmadan önce `sqlite`'ın en az bir kez
çalıştırılmış (veritabanının var) olması gerekir.

Tüm komutlar tekrar çalıştırılabilir (idempotent):
- `download` PDF zaten varsa indirmeyi atlar.
- `sqlite`, tablo boşsa PDF'ten doldurur; doluysa sadece eksik satırları
  ekler, var olan kayıtlara (ör. üzerine yazılmış çeviriye) dokunmaz.
- `sounds`, dosyası zaten var olan kelimeleri atlar.
- `translate`, sadece `translate_tr` alanı boş olan kayıtları işler.
- `examples`, sadece `examples` tablosunda hiç satırı olmayan `words.id`'leri
  işler.
- `csv`/`xlsx`, her çalıştığında veritabanının o anki tam halini yeniden
  yazar (üzerine yazar) — bu yüzden `translate`/`examples`'ı çalıştırdıktan
  sonra tekrar çalıştırırsanız güncel çevirileri/içeriği yansıtırlar.

## Mimari

**PDF'i ayrıştırıp veritabanını oluşturan tek yer:**

- **`scripts/pdf_parser.py`** — PDF ayrıştırmanın tek doğru kaynağı, sadece
  `export_sqlite.py` tarafından kullanılır. Kaynak PDF'te kelime/sözcük
  türü/CEFR seviyesi farklı fontlarla (Regular/Italic/Light) yazıldığından,
  ayrıştırma bu font bilgisine bakarak yapılıyor. Ayrıca çakışmaya yol
  açmayan homograph üst simge rakamlarını (ör. `close1`/`close2` → `close`)
  kaldırır; gerçek bir çakışma varsa (ör. `tear1`/`tear2`, ikisi de Noun/B2
  ama farklı anlamda) rakamı korur. `parse_pdf(pdf_path)` fonksiyonu
  `(word, parts_of_speech, cefr)` demetlerinin son halini döner; sözcük
  türleri kısaltma değil tam ad olarak (`n.` → `Noun`) gelir.
- **`scripts/export_sqlite.py`** — `pdf_parser.parse_pdf()`'i çağırıp
  `data/oxford3000.db`'yi oluşturur/günceller (bkz. Şema).
- **`scripts/download_pdf.py`** — kaynak PDF'i indirir.

**Veritabanından okuyan yardımcı komutlar:**

- **`scripts/db_reader.py`** — `words` tablosunu okumanın tek doğru kaynağı;
  `export_csv.py`, `export_xlsx.py` ve `sounds.py` PDF'i değil bu modülü
  kullanır, böylece PDF ayrıştırma mantığı `pdf_parser.py` dışında hiçbir
  yerde tekrarlanmaz.
- **`scripts/export_csv.py` / `export_xlsx.py`** — `db_reader.fetch_words()`
  ile `(word, parts_of_speech, cefr, translate_tr)` satırlarını okuyup
  kendi formatına yazan ince bir katman.
- **`scripts/sounds.py`** — `soundoftext.com` (Google TTS) üzerinden telaffuz
  MP3'lerini indirir. Benzersizlik anahtarı `(word, pos)` çiftidir (sadece
  `word` değil), çünkü aynı yazılış farklı sözcük türlerinde tekrar edebilir
  (ör. `close` hem Verb hem Adjective); böyle kelimelerde dosya adına tür de
  eklenir (`close_Verb.mp3`, `close_Adjective.mp3`).
- **`scripts/translate.py`** — Gemini API ile kelimeleri `word + parts_of_speech
  + cefr` bağlamıyla toplu halde (30'ar) çevirip `oxford3000.db`'deki
  `translate_tr` sütununu doldurur; aynı kelimenin farklı sözcük türü için
  farklı çeviri alması prompt'ta özellikle isteniyor.
- **`scripts/examples.py`** — Gemini API ile her `words` satırı (yani her
  kelime/sözcük türü/CEFR kombinasyonu) için 3 örnek cümle üretip
  `examples` tablosuna (`word` = `words.id`) yazar. `translate.py`'nin
  aksine kelime başına ayrı çağrı yapılır (toplu değil), çünkü tam cümle
  üretimi çeviriye göre daha ağır ve tek seferde çok kelime istemek kaliteyi
  düşürüyor.

## Şema (`oxford3000.db`)

- `words(id, word, description, parts_of_speech, cefr, translate_tr)` — `sqlite`
  komutu `word`, `parts_of_speech`, `cefr` alanlarını dolduruyor; `description`
  ve `translate_tr` (henüz çevrilmemişse) `NULL` bırakılıyor.
- `examples(id, word, sentence)` — `word`, `words.id`'ye referans verir;
  `examples` komutu her kayıt için 3 satır ekler.
- `reading_texts(id, title, content, cefr_level, related_word_ids)` — şema
  uyumluluğu için oluşturuluyor, bu araçlardan hiçbiri henüz doldurmuyor.

## Dosyalar

- `data/raw/American_Oxford_3000_CEFR.pdf` — kaynak PDF (gitignore'da,
  `download` komutuyla indirilir).
- `data/oxford3000.csv`, `data/oxford3000.xlsx`, `data/oxford3000.db` —
  üretilen çıktılar (gitignore'da, her zaman yeniden üretilebilir).
- `data/sounds/*.mp3` — telaffuz dosyaları (gitignore'da).

## Yapılacaklar

- [ ] `sounds.py`'de aynı yazılışlı ama farklı sözcük türüne sahip kelimeler
  (ör. `close` Verb vs Adjective) şu an TTS'e aynı düz metni gönderiyor, bu
  yüzden muhtemelen aynı sesi üretiyorlar. Gerçekten farklı telaffuz elde
  etmek için sözcük türüne göre bağlam cümlesi/ifadesi kullanılmalı (ör.
  "to close" / "very close" gibi, eski projedeki `HOMOGRAPH_MAP`'e benzer
  bir mekanizma).
