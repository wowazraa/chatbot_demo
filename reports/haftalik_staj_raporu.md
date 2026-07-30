# HAFTALIK ÇALIŞMA RAPORU

**Dönem:** 13.07.2026 – 17.07.2026  
**Stajyer:** Azra İrem DERİN

Haftanın ilk günlerinde, kullanıcının yazdığı yazılım ihtiyacını doğru sektöre (sağlık, turizm, savunma, eğitim vb.) yönlendirecek altyapıyı kurmak için model araştırması yaptım. Birkaç modeli denedikten sonra Kaan Bey ile birlikte projemize en uygun olanı seçtik. Sistemin ana iskeletini hazırladım, ardından çalıştığını görmek için basit bir demo açtım. Eksikleri adım adım ekleyerek demoyu geliştirmeye devam ettim.

Haftanın başında kelime bazlı kontrol (K1/regex) tarafına epey zaman ayırdım. “İstemiyoruz”, “değiliz” gibi olumsuz cümleleri yakalamak ve “sağlıklı bir iş ortaklığı” gibi mecazi kullanımlardaki kelime tuzaklarını çözmek için kurallar yazdım. Ama her uç senaryo için yeni if/else yazmanın uzun vadede yürümediğini gördük. Bu yüzden asıl kararı BGE embedding modeline ve veri setine bıraktık. Regex tarafı arkada bir emniyet gibi duruyor; canlıda asıl işi embedding, güvenlik eşiği ve veri yapıyor.

Sistemin kelimeleri daha iyi anlaması için veriyi epey büyüttüm. Sektörel kök ifadeler, ön ek–son ek kombinasyonları, hatalı yazıma karşı ASCII varyasyonlar ve LMS, HBYS, TSK gibi kurumsal kısaltmaları sözlük mantığıyla ekledim. Corpus yaklaşık 8500 kayda çıktı, vektör indeksini yeniledim. Güvenlik eşiğini 0.80’de tuttuk. Girişteki selamlaşmaları baştan temizleyen bir filtre koydum; bot belirsiz kaldığında da selama veya teşekküre göre biraz daha doğal cevap versin diye mesajları güncelledim.

Üstünkörü denemek yerine sistemi zorlayan bir stres seti hazırladım: 9 kategori, yaklaşık 90 senaryo (negasyon, yazım hatası, uzun cümle, tuzak sorular vb.). İyi giden yerleri de zayıf kalanları da not ettim:

- **Çok turlu konuşma (session):** İkinci tura geçince bazen bağlam kopuyor.
- **Çoklu niyet:** Aynı cümlede iki sektör birden geçince şimdilik net çözüm yok.
- **Eşik sınırı:** 0.80 eşiği tuzakları iyi eleyiyor ama çok bozuk yazımlı bazı cümlelerde skor düşüyor; bunu ASCII ve veri artırma ile kısmen toparladım.

Özetle sistem daha kararlı. Emin olmadığı yerde rastgele sektör uydurmak yerine “belirsiz” deyip kendini koruyor. Gelecek hafta session bağlamı ve çoklu niyet üzerine gideceğim.
