"""Öneri hesabı için veritabanında ne kadar veri var? (sadece okur)

Çalıştırmak için backend klasöründe:  py veri_kontrol.py
"""
import os

import psycopg
from dotenv import load_dotenv

load_dotenv()

with psycopg.connect(os.environ["DATABASE_URL"]) as db:
    def say(sql):
        return db.execute(sql).fetchone()[0]

    print("sehirler tablosundaki şehir   :", say("SELECT COUNT(*) FROM sehirler"))
    print("yerler tablosundaki yer       :", say("SELECT COUNT(*) FROM yerler"))
    print("koordinatı dolu yer           :", say(
        "SELECT COUNT(*) FROM yerler WHERE enlem IS NOT NULL AND boylam IS NOT NULL"))
    print("ziyaret süresi dolu yer       :", say(
        "SELECT COUNT(*) FROM yerler WHERE ziyaret_suresi > 0"))
    print("en az 1 yeri olan şehir       :", say(
        "SELECT COUNT(DISTINCT sehir_id) FROM yerler"))
    print("rotaya girebilecek yeri olan şehir:", say(
        """SELECT COUNT(DISTINCT sehir_id) FROM yerler
           WHERE enlem IS NOT NULL AND boylam IS NOT NULL AND ziyaret_suresi > 0"""))
