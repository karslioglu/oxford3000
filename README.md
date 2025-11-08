# Oxford 3000
Bu depo Oxford 3000 kelime listesinin seviye ve sözcük türüne göre ayrıştırılmış listelerini tutar. Toplam 2988 benzersiz kelime içerir. Fakat listelerde aynı kelime farklı sözcük türleri (parts of speech) için tekrarlanır. Bunun sebebi kelimelerin farklı sözcük türleri için farklı anlamları olmasıdır.

> Kelimelerin Türkçe çevirileri henüz yapılmamıştır.

**_Örnek:_**

|Word|Parts of Speech|CEFR Level|Translate (TR)             |
|----|---------------|:--------:|---------------------------|
|key |            n. |      A1  | anahtar                   |
|key |          adj. |      A1  | en önemli, temel, kilit   |
|key |            v. |      B1  | (klavyede) yazmak, girmek |

## Dosyalar
Farklı amaçlarla kulanılabilmesi için dosyalar farklı formatlara dönüştürülmüştür.

* **American_Oxford_3000_CEFR.pdf:** Oxford 3000 orijinal dosyası
* **oxford3000.db:** SQLite veritabanı
* **oxford3000.ods:** LibreOffice hesap tablosu. İstenirse Excel için XLSX formatına çevirilebilir.
* **words.txt:** Benzersiz (tekrarlanmayan) kelime listesi

## Araçlar
**_sounds.py_** uygulaması bir Python betiğidir. Çalıştırıldığında eğer yoksa **_sounds_** adında bir dizin oluşturur. Ardından **_words.txt_** içerisinde bulunan her kelimenin **_mp3_** formatında ses dosyasını indirir. Eğer ses dosyası varsa bu kelimeyi atlar. Böylece, eğer dosya varsa tekrar indirmeye çalışmaz. Ayrıca, istenildiği zaman uygulama durdurulup daha sonra tekrar başlatılabilir. Tekrar başlatıldığında sadece indirlmemiş ses dosyalarını indirecektir.