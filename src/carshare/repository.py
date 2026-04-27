from __future__ import annotations

import shutil
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


class Database:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS kullanicilar (
                    kullanici_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ad TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    sifre_hash TEXT NOT NULL,
                    ehliyet_no TEXT NOT NULL UNIQUE,
                    rol TEXT NOT NULL DEFAULT 'user',
                    bakiye REAL NOT NULL DEFAULT 0,
                    aktif_mi INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS araclar (
                    arac_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sahip_id INTEGER NOT NULL,
                    marka TEXT NOT NULL,
                    model TEXT NOT NULL,
                    kilometre INTEGER NOT NULL CHECK (kilometre >= 0),
                    musait_mi INTEGER NOT NULL DEFAULT 1,
                    gorsel_yolu TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (sahip_id) REFERENCES kullanicilar(kullanici_id)
                );

                CREATE TABLE IF NOT EXISTS ilanlar (
                    ilan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    arac_id INTEGER NOT NULL,
                    ilan_sahibi_id INTEGER NOT NULL,
                    baslik TEXT NOT NULL,
                    aciklama TEXT NOT NULL,
                    saatlik_ucret REAL NOT NULL CHECK (saatlik_ucret >= 0),
                    konum TEXT NOT NULL,
                    durum TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (arac_id) REFERENCES araclar(arac_id),
                    FOREIGN KEY (ilan_sahibi_id) REFERENCES kullanicilar(kullanici_id)
                );

                CREATE TABLE IF NOT EXISTS kiralamalar (
                    kiralama_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ilan_id INTEGER NOT NULL,
                    kiralayan_id INTEGER NOT NULL,
                    baslangic_saati TEXT NOT NULL,
                    bitis_saati TEXT,
                    kira_saat INTEGER NOT NULL DEFAULT 1,
                    toplam_tutar REAL,
                    durum TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (ilan_id) REFERENCES ilanlar(ilan_id),
                    FOREIGN KEY (kiralayan_id) REFERENCES kullanicilar(kullanici_id)
                );

                CREATE TABLE IF NOT EXISTS yorumlar (
                    yorum_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ilan_id INTEGER NOT NULL,
                    kullanici_id INTEGER NOT NULL,
                    yorum TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(ilan_id, kullanici_id),
                    FOREIGN KEY (ilan_id) REFERENCES ilanlar(ilan_id),
                    FOREIGN KEY (kullanici_id) REFERENCES kullanicilar(kullanici_id)
                );

                CREATE TABLE IF NOT EXISTS begeniler (
                    begeni_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ilan_id INTEGER NOT NULL,
                    kullanici_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(ilan_id, kullanici_id),
                    FOREIGN KEY (ilan_id) REFERENCES ilanlar(ilan_id),
                    FOREIGN KEY (kullanici_id) REFERENCES kullanicilar(kullanici_id)
                );

                CREATE TABLE IF NOT EXISTS ticketler (
                    ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    acan_kullanici_id INTEGER NOT NULL,
                    baslik TEXT NOT NULL,
                    mesaj TEXT NOT NULL,
                    durum TEXT NOT NULL DEFAULT 'open',
                    yanit TEXT,
                    yanitlayan_id INTEGER,
                    yanit_tarihi TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (acan_kullanici_id) REFERENCES kullanicilar(kullanici_id),
                    FOREIGN KEY (yanitlayan_id) REFERENCES kullanicilar(kullanici_id)
                );

                CREATE TABLE IF NOT EXISTS bakiye_hareketleri (
                    hareket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kullanici_id INTEGER NOT NULL,
                    tutar REAL NOT NULL,
                    aciklama TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (kullanici_id) REFERENCES kullanicilar(kullanici_id)
                );

                CREATE TABLE IF NOT EXISTS bildirimler (
                    bildirim_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kullanici_id INTEGER NOT NULL,
                    baslik TEXT NOT NULL,
                    mesaj TEXT NOT NULL,
                    okundu_mu INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (kullanici_id) REFERENCES kullanicilar(kullanici_id)
                );

                CREATE TABLE IF NOT EXISTS puanlar (
                    puan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ilan_id INTEGER NOT NULL,
                    kullanici_id INTEGER NOT NULL,
                    puan INTEGER NOT NULL CHECK (puan BETWEEN 1 AND 5),
                    created_at TEXT NOT NULL,
                    UNIQUE(ilan_id, kullanici_id),
                    FOREIGN KEY (ilan_id) REFERENCES ilanlar(ilan_id),
                    FOREIGN KEY (kullanici_id) REFERENCES kullanicilar(kullanici_id)
                );

                """
            )
            conn.commit()
            self._migrate_legacy(conn)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ilan_durum ON ilanlar(durum)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ticket_durum ON ticketler(durum)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kiralama_durum ON kiralamalar(durum)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_bildirim_user ON bildirimler(kullanici_id, okundu_mu)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_puan_ilan ON puanlar(ilan_id)")
            conn.execute(
                """
                DELETE FROM yorumlar
                WHERE yorum_id NOT IN (
                    SELECT MIN(yorum_id)
                    FROM yorumlar
                    GROUP BY ilan_id, kullanici_id
                )
                """
            )
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_yorum_unique ON yorumlar(ilan_id, kullanici_id)"
            )
            conn.commit()

    def _migrate_legacy(self, conn: sqlite3.Connection) -> None:
        user_cols = {row["name"] for row in conn.execute("PRAGMA table_info(kullanicilar)").fetchall()}
        legacy_steps: list[str] = []
        if "email" not in user_cols:
            legacy_steps.append("ALTER TABLE kullanicilar ADD COLUMN email TEXT")
        if "sifre_hash" not in user_cols:
            legacy_steps.append("ALTER TABLE kullanicilar ADD COLUMN sifre_hash TEXT")
        if "rol" not in user_cols:
            legacy_steps.append("ALTER TABLE kullanicilar ADD COLUMN rol TEXT DEFAULT 'user'")
        if "bakiye" not in user_cols:
            legacy_steps.append("ALTER TABLE kullanicilar ADD COLUMN bakiye REAL DEFAULT 0")
        if "aktif_mi" not in user_cols:
            legacy_steps.append("ALTER TABLE kullanicilar ADD COLUMN aktif_mi INTEGER DEFAULT 1")
        if "created_at" not in user_cols:
            legacy_steps.append("ALTER TABLE kullanicilar ADD COLUMN created_at TEXT DEFAULT ''")
        for step in legacy_steps:
            conn.execute(step)
        if legacy_steps:
            conn.commit()

        arac_cols = {row["name"] for row in conn.execute("PRAGMA table_info(araclar)").fetchall()}
        arac_steps: list[str] = []
        if "sahip_id" not in arac_cols:
            arac_steps.append("ALTER TABLE araclar ADD COLUMN sahip_id INTEGER DEFAULT 1")
        if "gorsel_yolu" not in arac_cols:
            arac_steps.append("ALTER TABLE araclar ADD COLUMN gorsel_yolu TEXT")
        if "created_at" not in arac_cols:
            arac_steps.append("ALTER TABLE araclar ADD COLUMN created_at TEXT DEFAULT ''")
        for step in arac_steps:
            conn.execute(step)
        if arac_steps:
            conn.commit()

        ticket_cols = {row["name"] for row in conn.execute("PRAGMA table_info(ticketler)").fetchall()}
        ticket_steps: list[str] = []
        if "yanitlayan_id" not in ticket_cols:
            ticket_steps.append("ALTER TABLE ticketler ADD COLUMN yanitlayan_id INTEGER")
        if "yanit_tarihi" not in ticket_cols:
            ticket_steps.append("ALTER TABLE ticketler ADD COLUMN yanit_tarihi TEXT")
        for step in ticket_steps:
            conn.execute(step)
        if ticket_steps:
            conn.commit()

        rental_cols = {row["name"] for row in conn.execute("PRAGMA table_info(kiralamalar)").fetchall()}
        rental_steps: list[str] = []
        if "ilan_id" not in rental_cols:
            rental_steps.append("ALTER TABLE kiralamalar ADD COLUMN ilan_id INTEGER")
        if "kiralayan_id" not in rental_cols:
            rental_steps.append("ALTER TABLE kiralamalar ADD COLUMN kiralayan_id INTEGER")
        if "toplam_tutar" not in rental_cols:
            rental_steps.append("ALTER TABLE kiralamalar ADD COLUMN toplam_tutar REAL")
        if "durum" not in rental_cols:
            rental_steps.append("ALTER TABLE kiralamalar ADD COLUMN durum TEXT DEFAULT 'active'")
        if "created_at" not in rental_cols:
            rental_steps.append("ALTER TABLE kiralamalar ADD COLUMN created_at TEXT DEFAULT ''")
        if "kira_saat" not in rental_cols:
            rental_steps.append("ALTER TABLE kiralamalar ADD COLUMN kira_saat INTEGER NOT NULL DEFAULT 1")
        for step in rental_steps:
            conn.execute(step)
        if rental_steps:
            conn.commit()

        rental_cols = {row["name"] for row in conn.execute("PRAGMA table_info(kiralamalar)").fetchall()}
        legacy_present = ("arac_id" in rental_cols) or ("kullanici_id" in rental_cols)
        if legacy_present:
            conn.execute("DROP TABLE IF EXISTS kiralamalar_new")
            conn.execute(
                """
                CREATE TABLE kiralamalar_new (
                    kiralama_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ilan_id INTEGER NOT NULL,
                    kiralayan_id INTEGER NOT NULL,
                    baslangic_saati TEXT NOT NULL,
                    bitis_saati TEXT,
                    kira_saat INTEGER NOT NULL DEFAULT 1,
                    toplam_tutar REAL,
                    durum TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (ilan_id) REFERENCES ilanlar(ilan_id),
                    FOREIGN KEY (kiralayan_id) REFERENCES kullanicilar(kullanici_id)
                )
                """
            )
            old_arac = "k.arac_id" if "arac_id" in rental_cols else "NULL"
            old_kul = "k.kullanici_id" if "kullanici_id" in rental_cols else "NULL"
            conn.execute(
                f"""
                INSERT INTO kiralamalar_new
                    (kiralama_id, ilan_id, kiralayan_id, baslangic_saati, bitis_saati,
                     kira_saat, toplam_tutar, durum, created_at)
                SELECT
                    k.kiralama_id,
                    COALESCE(
                        k.ilan_id,
                        (SELECT i.ilan_id FROM ilanlar i WHERE i.arac_id = {old_arac}
                         ORDER BY i.ilan_id DESC LIMIT 1)
                    ) AS ilan_id,
                    COALESCE(k.kiralayan_id, {old_kul}) AS kiralayan_id,
                    k.baslangic_saati,
                    k.bitis_saati,
                    COALESCE(k.kira_saat, 1) AS kira_saat,
                    k.toplam_tutar,
                    COALESCE(NULLIF(k.durum, ''), 'active') AS durum,
                    COALESCE(NULLIF(k.created_at, ''), k.baslangic_saati) AS created_at
                FROM kiralamalar k
                WHERE COALESCE(
                    k.ilan_id,
                    (SELECT i.ilan_id FROM ilanlar i WHERE i.arac_id = {old_arac}
                     ORDER BY i.ilan_id DESC LIMIT 1)
                ) IS NOT NULL
                  AND COALESCE(k.kiralayan_id, {old_kul}) IS NOT NULL
                """
            )
            conn.execute("DROP TABLE kiralamalar")
            conn.execute("ALTER TABLE kiralamalar_new RENAME TO kiralamalar")
            conn.commit()

        conn.execute("UPDATE kullanicilar SET email = COALESCE(NULLIF(email, ''), ehliyet_no || '@legacy.local')")
        conn.execute("UPDATE kullanicilar SET sifre_hash = COALESCE(NULLIF(sifre_hash, ''), 'legacy')")
        conn.execute("UPDATE kullanicilar SET created_at = COALESCE(NULLIF(created_at, ''), datetime('now'))")
        conn.execute("UPDATE araclar SET created_at = COALESCE(NULLIF(created_at, ''), datetime('now'))")
        conn.execute("UPDATE kiralamalar SET created_at = COALESCE(NULLIF(created_at, ''), datetime('now'))")
        conn.execute("UPDATE kiralamalar SET durum = COALESCE(NULLIF(durum, ''), 'active')")
        conn.commit()

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> int:
        with self._connect() as conn:
            cur = conn.execute(query, params)
            conn.commit()
            return cur.lastrowid

    def fetchall(self, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        with self._connect() as conn:
            cur = conn.execute(query, params)
            return cur.fetchall()

    def fetchone(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        with self._connect() as conn:
            cur = conn.execute(query, params)
            return cur.fetchone()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def reset_data(self, keep_email: str) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute("DELETE FROM puanlar")
            conn.execute("DELETE FROM begeniler")
            conn.execute("DELETE FROM yorumlar")
            conn.execute("DELETE FROM kiralamalar")
            conn.execute("DELETE FROM ilanlar")
            conn.execute("DELETE FROM araclar")
            conn.execute("DELETE FROM ticketler")
            conn.execute("DELETE FROM bildirimler")
            conn.execute("DELETE FROM bakiye_hareketleri")
            conn.execute(
                "DELETE FROM kullanicilar WHERE email != ?",
                (keep_email.strip().lower(),),
            )
            conn.execute(
                "UPDATE kullanicilar SET bakiye = 0, aktif_mi = 1 WHERE email = ?",
                (keep_email.strip().lower(),),
            )
            for table in (
                "puanlar",
                "begeniler",
                "yorumlar",
                "kiralamalar",
                "ilanlar",
                "araclar",
                "ticketler",
                "bildirimler",
                "bakiye_hareketleri",
            ):
                conn.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table,))
            conn.commit()

    def backup_to(self, target_path: Path) -> Path:
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.db_path, target)
        return target

