"""VoyageAI: import Nominatim candidates into previously empty candidate slots.
Reads CSV, makes no changes without typed EVET confirmation.
Never overwrites non-empty coordinates and never marks candidates verified.
"""
import csv
from pathlib import Path
from sqlalchemy import text
from database import SessionLocal

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "VoyageAI_30_OSM_Alternatif_Ad_Kontrol.csv"
if not SOURCE.exists():
    raise SystemExit(f"CSV bulunamadi: {SOURCE}")

with SOURCE.open(encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f, delimiter=";"))
if not rows:
    raise SystemExit("CSV bos.")
print('CSV sutunlari:', ', '.join(rows[0]))
required = {"yer_id", "enlem", "boylam"}
if not required.issubset(rows[0]):
    raise SystemExit(f"Eksik sutunlar: {sorted(required - set(rows[0]))}")

valid = {}
invalid = 0
ambiguous = set()
for row in rows:
    try:
        ident = int((row.get('yer_id') or '').strip())
        lat = float((row.get('enlem') or '').strip().replace(',', '.'))
        lon = float((row.get('boylam') or '').strip().replace(',', '.'))
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            invalid += 1
            continue
    except (ValueError, TypeError):
        invalid += 1
        continue
    if ident in valid and (valid[ident]['lat'], valid[ident]['lon']) != (lat, lon):
        ambiguous.add(ident)
        continue
    valid.setdefault(ident, {'lat': lat, 'lon': lon})
for ident in ambiguous:
    valid.pop(ident, None)
print(f"CSV satir: {len(rows)} | Tekil kullanilabilir aday: {len(valid)} | Bos/gecersiz satir: {invalid} | Birden fazla farkli koordinati olan yer: {len(ambiguous)}")
if ambiguous:
    print('Belirsiz IDler (aktarilmayacak):', ', '.join(map(str, sorted(ambiguous))))
if not valid:
    raise SystemExit('Aktarilabilecek aday yok.')

# Candidate coordinates are provisional, not verified visitor entrances.
with SessionLocal() as db:
    existing = db.execute(text("""
        SELECT yer_id, enlem, boylam, durum
        FROM koordinat_adaylari WHERE yer_id IN :ids
    """).bindparams(__import__('sqlalchemy').bindparam('ids', expanding=True)), {'ids': list(valid)}).mappings().all()
    by_id = {int(r['yer_id']): r for r in existing}
    eligible = [ident for ident in valid if ident in by_id and (by_id[ident]['enlem'] is None or by_id[ident]['boylam'] is None)]
    skipped = len(valid) - len(eligible)
    print(f"Bos aday kaydina yazilabilecek: {len(eligible)} | Var olan veya bulunamayan kayit, atlanacak: {skipped}")
    print('Kayıtlar EK_INCELEME olarak isaretlenecek. Ana yerler tablosu degismeyecek.')
    if input('Aktarimi onayliyorsan EVET yaz: ').strip() != 'EVET':
        raise SystemExit('Iptal edildi; veritabani degismedi.')
    count = 0
    try:
        for ident in eligible:
            result = db.execute(text("""
                UPDATE koordinat_adaylari
                   SET enlem = :lat, boylam = :lon,
                       durum = 'EK_INCELEME',
                       kaynak = 'OpenStreetMap Nominatim - alternatif isim (dogrulanmamis)',
                       guncelleme_zamani = NOW()
                 WHERE yer_id = :ident
                   AND (enlem IS NULL OR boylam IS NULL)
            """), {'ident': ident, 'lat': valid[ident]['lat'], 'lon': valid[ident]['lon']})
            count += result.rowcount
        db.commit()
    except Exception:
        db.rollback()
        raise
    print(f'BASARILI: {count} aday koordinat kaydedildi (EK_INCELEME).')
    print('Ana yerler tablosunda degisiklik yapilmadi.')
