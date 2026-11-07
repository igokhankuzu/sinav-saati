"""ÖSYM sınav takviminden YDS, ALES ve KPSS tarihlerini okuyup tarihler.json'a yazar.

GitHub otomasyonu (.github/workflows/tarihler.yml) bunu her gün çalıştırır.
Elle çalıştırmak için: python3 araclar/tarihleri_guncelle.py

Güvenlik kuralları:
- Bilinen tarihler silinmez, yeniler eklenir (ÖSYM eski yılı sayfadan kaldırsa da kaybolmaz).
- Sayfadan hiç tarih okunamazsa dosyaya dokunulmaz ve program hata ile biter;
  GitHub bu durumda depo sahibine e-posta gönderir.
"""

import datetime
import html
import json
import pathlib
import re
import sys
import urllib.request

TAKVIM_ADRESI = "https://www.osym.gov.tr/Sayfa/SinavTakvimi"
DOSYA = pathlib.Path(__file__).resolve().parent.parent / "tarihler.json"

# ÖSYM'deki adı → uygulamadaki sınav adı
def uygulamadaki_ad(osym_adi):
    if re.match(r"20\d\d-YDS/", osym_adi):
        return "YDS"
    if re.match(r"20\d\d-ALES/", osym_adi):
        return "ALES"
    if "KPSS" in osym_adi and "Genel Yetenek-Genel Kültür" in osym_adi:
        return "KPSS Genel Yetenek - Genel Kültür"
    if "KPSS" in osym_adi and "Eğitim Bilimleri" in osym_adi:
        return "KPSS Eğitim Bilimleri"
    return None


def sayfayi_indir():
    istek = urllib.request.Request(TAKVIM_ADRESI, headers={"User-Agent": "Mozilla/5.0 (sinav-saati takvim okuyucu)"})
    with urllib.request.urlopen(istek, timeout=60) as yanit:
        return yanit.read().decode("utf-8", errors="ignore")


def tarihleri_bul(sayfa):
    # Etiketleri at, düz yazıya çevir
    yazi = re.sub(r"<script.*?</script>|<style.*?</style>", " ", sayfa, flags=re.S)
    yazi = html.unescape(re.sub(r"<[^>]+>", " ", yazi))
    yazi = re.sub(r"\s+", " ", yazi)

    bulunan = {}
    # Örnek: "2026-YDS/2 Sınav Tarihi: 22.11.2026"
    # Ad kısmında ":" olamaz; böylece bir önceki kaydın tarihine taşmaz.
    for osym_adi, gun in re.findall(r"(20\d\d-[^:]{1,120}?) Sınav Tarihi:\s*(\d\d\.\d\d\.\d{4})", yazi):
        ad = uygulamadaki_ad(osym_adi.strip())
        if not ad:
            continue
        g, a, y = (int(p) for p in gun.split("."))
        try:
            tarih = datetime.date(y, a, g)
        except ValueError:
            continue
        if 2020 <= tarih.year <= 2100:
            bulunan.setdefault(ad, set()).add(tarih.isoformat())
    return bulunan


def main():
    try:
        bulunan = tarihleri_bul(sayfayi_indir())
    except Exception as hata:
        print(f"ÖSYM sayfası okunamadı: {hata}")
        return 1

    if not bulunan:
        print("Sayfada hiç sınav tarihi bulunamadı; sayfa yapısı değişmiş olabilir. Dosyaya dokunulmadı.")
        return 1

    eski = json.loads(DOSYA.read_text(encoding="utf-8")) if DOSYA.exists() else {"sinavlar": {}}
    # Çok eski tarihleri (1 yıldan eski) temizle, gerisini koru
    sinir = (datetime.date.today() - datetime.timedelta(days=365)).isoformat()
    sinavlar = {}
    for ad in set(eski.get("sinavlar", {})) | set(bulunan):
        hepsi = set(eski.get("sinavlar", {}).get(ad, [])) | bulunan.get(ad, set())
        sinavlar[ad] = sorted(t for t in hepsi if t >= sinir)

    if sinavlar == eski.get("sinavlar"):
        print("Tarihler aynı, değişiklik yok.")
        return 0

    yeni = {"guncelleme": datetime.date.today().isoformat(), "kaynak": TAKVIM_ADRESI, "sinavlar": dict(sorted(sinavlar.items()))}
    DOSYA.write_text(json.dumps(yeni, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for ad, tarihler in yeni["sinavlar"].items():
        print(f"{ad}: {', '.join(tarihler)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
