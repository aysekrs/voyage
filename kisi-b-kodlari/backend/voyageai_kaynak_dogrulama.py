# -*- coding: utf-8 -*-
"""VoyageAI kaynak koordinat çapraz kontrolü.
Salt okunur: PostgreSQL'den adayları okur, OSM node kimliklerini toplu çeker,
koordinatları karşılaştırır ve CSV raporu oluşturur. Veritabanına yazmaz.
"""
import csv
import math
import re
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path
from difflib import SequenceMatcher
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import requests
from sqlalchemy import text
from database import SessionLocal

OUT = Path(__file__).resolve().parent
OSM_NODE = re.compile(r"(?:www\.)?openstreetmap\.org/node/(\d+)")
OSM_WAY = re.compile(r"(?:www\.)?openstreetmap\.org/way/(\d+)")
OSM_REL = re.compile(r"(?:www\.)?openstreetmap\.org/relation/(\d+)")


def norm(value):
    value = unicodedata.normalize("NFKD", str(value or "").casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def haversine(a, b, c, d):
    p1, p2 = math.radians(a), math.radians(c)
    dp = math.radians(c-a)
    dl = math.radians(d-b)
    h = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 12742 * math.asin(min(1, math.sqrt(h)))


def get_osm_nodes(ids):
    """OSM API ile 60'lık gruplar halinde tek seferlik node koordinat kontrolü."""
    found = {}
    session = requests.Session()
    session.headers.update({"User-Agent": "VoyageAI-EducationalCoordinateAudit/1.0 (local one-off audit)",
                            "Accept": "application/xml"})
    for offset in range(0, len(ids), 60):
        chunk = ids[offset:offset+60]
        url = "https://api.openstreetmap.org/api/0.6/nodes"
        try:
            response = session.get(url, params={"nodes": ",".join(chunk)}, timeout=40)
            response.raise_for_status()
            root = ET.fromstring(response.content)
            for node in root.findall("node"):
                tags = {tag.get("k"): tag.get("v") for tag in node.findall("tag")}
                found[node.get("id")] = {
                    "lat": float(node.get("lat")), "lon": float(node.get("lon")),
                    "name": tags.get("name", "") or tags.get("name:en", "") or tags.get("name:tr", ""),
                    "tags": tags,
                }
        except (requests.RequestException, ET.ParseError, ValueError) as exc:
            print(f"UYARI: OSM kaynak sorgusu basarisiz ({offset+1}-{offset+len(chunk)}): {exc}")
        if offset + 60 < len(ids):
            time.sleep(1.1)
    return found


def main():
    db = SessionLocal()
    try:
        rows = db.execute(text("""
            SELECT y.yer_id, y.ad AS yer_adi, s.ad AS sehir, s.ulke,
                   k.enlem, k.boylam, k.durum, k.kaynak
            FROM koordinat_adaylari k
            JOIN yerler y ON y.yer_id = k.yer_id
            JOIN sehirler s ON s.sehir_id = y.sehir_id
            WHERE k.enlem IS NOT NULL AND k.boylam IS NOT NULL
            ORDER BY y.yer_id
        """)).mappings().all()
    finally:
        db.close()

    print(f"Toplam koordinat adayi: {len(rows)}")
    ids = sorted(set(m.group(1) for r in rows if (m := OSM_NODE.search(str(r["kaynak"] or "")))))
    print(f"OSM node bağlantisi: {len(ids)} (toplu kaynak koordinat kontrolu)")
    osm = get_osm_nodes(ids)
    print(f"OSM'den alinan kaynak kaydi: {len(osm)}")

    results = []
    for r in rows:
        src = str(r["kaynak"] or "").strip()
        n = OSM_NODE.search(src)
        w = OSM_WAY.search(src)
        rel = OSM_REL.search(src)
        status = "KAYNAK_ELLE_INCELENECEK"
        dist = ""
        source_name = ""
        similarity = ""
        source_lat, source_lon = "", ""
        explanation = "Kaynak bağlantısı bağımsız koordinat doğrulaması için uygun değil"
        if n:
            node = osm.get(n.group(1))
            if node is None:
                status = "OSM_KAYNAGI_ALINAMADI"
                explanation = "OSM node bulunamadı veya ağ erişimi başarısız"
            else:
                source_lat, source_lon = node["lat"], node["lon"]
                dist_val = haversine(float(r["enlem"]), float(r["boylam"]), node["lat"], node["lon"])
                dist = round(dist_val * 1000, 1)
                source_name = node["name"]
                if source_name:
                    similarity = round(SequenceMatcher(None, norm(r["yer_adi"]), norm(source_name)).ratio(), 2)
                status = "KAYNAK_KOORDINATI_ESLESIYOR" if dist_val <= .1 else "KAYNAK_KOORDINATI_FARKLI"
                explanation = ("Koordinat OSM node ile 100 metre içinde eşleşiyor; yer kimliği ayrıca doğrulanmalı"
                               if dist_val <= .1 else "Veritabanı koordinatı OSM kaynak node koordinatından 100 metreden uzak")
        elif w or rel:
            status = "OSM_WAY_RELATION_INCELE"
            explanation = "OSM alan/ilişki bağlantısı: tek bir node noktası yok, geometrisi ayrıca incelenmeli"
        elif not src:
            status = "KAYNAK_BOS"
            explanation = "Kaynak belirtilmemiş"
        elif urlparse(src).scheme in ("http", "https"):
            status = "DIGER_KAYNAK_BAGLANTISI"
            explanation = "Kaynak URL'si var, koordinat karşılaştırması bu programda otomatik yapılamıyor"
        elif any(x in norm(src) for x in ("temsil noktasi", "temsil", "approx", "tahmin")):
            status = "TEMSILI_KONUM_INCELE"
            explanation = "Temsili konum, gerçek giriş noktası olarak sunulmamalı"
        results.append({
            "yer_id": r["yer_id"], "ulke": r["ulke"], "sehir": r["sehir"],
            "gezilecek_yer": r["yer_adi"], "aday_enlem": r["enlem"],
            "aday_boylam": r["boylam"], "aday_durum": r["durum"],
            "kaynak": src, "kaynak_enlem": source_lat, "kaynak_boylam": source_lon,
            "kaynak_yer_adi": source_name, "isim_benzerligi": similarity,
            "koordinat_farki_metre": dist, "kontrol_sonucu": status,
            "aciklama": explanation,
        })

    path = OUT / "VoyageAI_Kaynak_Kontrol_364.csv"
    if results:
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(results[0]), delimiter=";")
            writer.writeheader()
            writer.writerows(results)

    summary = Counter(r["kontrol_sonucu"] for r in results)
    print("\n--- KAYNAK KONTROL SONUCLARI ---")
    for key, count in summary.most_common():
        print(f"{key}: {count}")
    print(f"\nCSV: {path}")
    print("NOT: Koordinat kaynağıyla eşleşme, turistik yerin doğru olduğunun kesin kanıtı değildir.")
    print("Veritabaninda hiçbir değişiklik yapılmadı.")


if __name__ == "__main__":
    main()
