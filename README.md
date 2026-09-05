# KAP-YORUM (R1)

Bu repository, BIST şirketlerinin KAP (Kamuyu Aydınlatma Platformu) bildirimlerini okuyup ekonomik yorumlarını yapmak üzere tasarlanan sistemin temel altyapısını içerir.

## Mevcut Durum: R1 - Kaynak ve Veri Bütünlüğü Altyapısı

**DİKKAT:** Bu sistem henüz production-ready bir KAP yorumlayıcısı **değildir**.

Şu anki (R1) durumuyla sistemin amacı, ileriki aşamalarda (R2-R14) kurulacak olan gerçek parser, NLP, analiz ve sentez motorlarının üzerinde koşacağı **güvenli, tipli ve hatalara karşı dirençli altyapıyı (integrity foundation)** sağlamaktır.

Sistem, kaynak verinin gerçekliği ve tamlığı doğrulanmadan ("Readiness" modeli) yanlışlıkla uydurma veya eksik bir analiz raporu üretmemesi için **FAIL-CLOSED** olarak kilitlenmiştir.

### R1 İle Sağlanan Yetenekler:
1. **Source State Model:** Başarılı erişim, onaylanmış boş sonuç, erişilememezlik, kısmi veri veya hatalı yanıt (SUCCESS, EMPTY_CONFIRMED, UNAVAILABLE vb.) durumlarının type-safe olarak ayrılması.
2. **Error Taxonomy:** Ağ hataları, schema uyuşmazlıkları ve timeout'lar için kesin hata sınıflandırması.
3. **Temporal ve Identity Sözleşmeleri:** Zaman dilimi (timezone) farkındalığı ve aynı canonical ID'ye sahip verilerin deduplikasyonu.
4. **Retry/Timeout Sınırları:** Sonsuz döngü ve kilitlenmeleri engelleyen deterministic hata kurtarma.
5. **Readiness Gate:** Gerçek KAP motoru R2'de eklenene kadar üretim hattının sahte/prototip verilerle çalışmasını engelleyen güvenlik kalkanı.

## Kurulum ve Test

Bağımlılıklar `pyproject.toml` ile yönetilmektedir. Minimum Python 3.10 gereklidir.

```bash
# Sanal ortam oluşturma
python3 -m venv venv
source venv/bin/activate

# Geliştirme bağımlılıklarıyla birlikte kurulum
pip install -e .[dev]

# Statik tip kontrolü
mypy src

# Testlerin çalıştırılması
pytest
```
