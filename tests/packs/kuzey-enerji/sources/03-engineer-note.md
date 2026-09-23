# Saha Calisma Notu - Kuzey Enerji Holding
**Microsoft Confidential** (basili damga - MIP etiketi uygulanmamistir)
Hazirlayan: Mert Yildizhan (CSA)
Tarih: 12 Eylul 2026
Dosya: \\fileshare\csa\kuzey-enerji\2026-09-saha-notu.md
Kaynak pano: https://internal-dashboard.contoso-test.invalid/kuzey/health

## 1. Kapsam
19 Agustos 2026 kimlik dogrulama kesintisi sonrasi yapilan teknik inceleme.
Inceleme 25 Agustos - 10 Eylul arasinda yapildi.

## 2. Bulgular (dogrulanmis)
| # | Bulgu | Kanit | Siddet |
|---|-------|-------|--------|
| B1 | Kimlik altyapisi tek bolgede, otomatik devretme yok | Mimari inceleme, bolum 3.2 | Yuksek |
| B2 | 14 ayricalikli hesapta MFA zorunlu degil; 6'si kalici yonetici | Erisim envanteri, bolum 4.1 | Yuksek |
| B3 | Son 11 ayda geri donus tatbikati yok | Yedekleme kayitlari, bolum 5.4 | Orta |
| B4 | Uyari var, operasyonel takip yok (MTTD 53 dk) | Olay zaman cizelgesi, bolum 2.3 | Orta |

## 3. Saat durumu (Delivery kayitlarindan)
- Sozlesme toplam proaktif: 400 saat
- 1 Eylul itibariyla tuketilen: 268 saat
- Q4 icin takvimlenmis (planli): 90 saat
- Planlanmamis kalan: 48 saat

> NOT: Bu rakam 1 Eylul kesitidir. Eylul icinde acilan 6 saatlik reaktif
> vaka bu tabloya islenmedi; CSAM'in 42 saatlik rakami o vakayi dusuyor.
> Musteriye giden dokumanda hangi kesitin kullanildigi yazilmali.

## 4. Onerilen calismalar
- Kimlik icin coklu bolge tasarimi calistayi -> Unified proaktif kapsaminda.
- Ayricalikli erisim icin zaman sinirli yukseltme modeli -> Unified proaktif
  kapsaminda.
- Yedek geri donus tatbikati -> ayri bakim penceresi gerekir.

## 5. IC DEGERLENDIRME (musteriyle paylasilmaz)
Musteri tarafindaki altyapi ekibi zayif, Onur tek basina tasiyor. Selin'in
yonetim kurulunda pozisyonu sikisik, Agustos kesintisi CIO tarafindan
sorgulaniyor. Hesap acisindan bu bizim icin 2027 yenileme riskini
azaltacak bir firsat; iyi yonetilirse Unified Enhanced'dan bir ust
kademeye gecis konusulabilir. Rakip tedarikci de ayni kapiyi caliyor.
Fiyat pazarligi icin yil sonuna kadar beklememiz lehimize.

## 6. Kisisel gorusum
Belki Copilot for Security de satarizdir, henuz musteriyle konusmadim,
teknik uygunlugunu da dogrulamadim.
