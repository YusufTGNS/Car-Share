from __future__ import annotations

from datetime import datetime
import hashlib
from pathlib import Path

from .repository import Database


SYSTEM_ADMIN_EMAIL = "admin@carshare.local"


class CarSharingService:
    def __init__(self, db_path: Path) -> None:
        self.db = Database(db_path)
        self.db_path = db_path

    def _now(self) -> str:
        return datetime.now().isoformat(sep=" ", timespec="seconds")

    def _hash(self, raw: str) -> str:
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def register(self, ad: str, email: str, sifre: str, ehliyet_no: str, rol: str = "user") -> int:
        ad = ad.strip()
        email = email.strip().lower()
        ehliyet_no = ehliyet_no.strip().upper()
        if not ad:
            raise ValueError("Ad zorunludur.")
        if "@" not in email:
            raise ValueError("Email gecersiz.")
        if len(sifre) < 6:
            raise ValueError("Sifre en az 6 karakter olmali.")
        if len(ehliyet_no) < 5:
            raise ValueError("Ehliyet no en az 5 karakter olmali.")
        if rol not in {"admin", "user"}:
            raise ValueError("Rol gecersiz.")
        return self.db.execute(
            """
            INSERT INTO kullanicilar (ad, email, sifre_hash, ehliyet_no, rol, bakiye, aktif_mi, created_at)
            VALUES (?, ?, ?, ?, ?, 0, 1, ?)
            """,
            (ad, email, self._hash(sifre), ehliyet_no, rol, self._now()),
        )

    def login(self, email: str, sifre: str) -> dict:
        row = self.db.fetchone("SELECT * FROM kullanicilar WHERE email = ?", (email.strip().lower(),))
        if not row:
            raise ValueError("Kullanici bulunamadi.")
        user = dict(row)
        if user["aktif_mi"] != 1:
            raise ValueError("Hesap pasif.")
        if user["sifre_hash"] != "legacy" and user["sifre_hash"] != self._hash(sifre):
            raise ValueError("Sifre hatali.")
        if user["sifre_hash"] == "legacy":
            self.db.execute(
                "UPDATE kullanicilar SET sifre_hash = ? WHERE kullanici_id = ?",
                (self._hash(sifre), user["kullanici_id"]),
            )
        current = self.db.fetchone("SELECT * FROM kullanicilar WHERE kullanici_id = ?", (user["kullanici_id"],))
        return dict(current) if current else user

    def kullanici_getir(self, kullanici_id: int) -> dict:
        row = self.db.fetchone("SELECT * FROM kullanicilar WHERE kullanici_id = ?", (kullanici_id,))
        if not row:
            raise ValueError("Kullanici bulunamadi.")
        return dict(row)

    def admin_seed(self) -> None:
        row = self.db.fetchone(
            "SELECT kullanici_id FROM kullanicilar WHERE email = ? LIMIT 1",
            (SYSTEM_ADMIN_EMAIL,),
        )
        if not row:
            self.register("System Admin", SYSTEM_ADMIN_EMAIL, "admin123", "ADMIN1", "admin")

    def kullanicilar_listesi(self) -> list[dict]:
        rows = self.db.fetchall(
            "SELECT kullanici_id, ad, email, ehliyet_no, rol, bakiye, aktif_mi FROM kullanicilar ORDER BY kullanici_id DESC"
        )
        return [dict(r) for r in rows]

    def kullanici_rol_durum_guncelle(self, kullanici_id: int, rol: str, aktif_mi: int) -> None:
        if rol not in {"admin", "user"}:
            raise ValueError("Rol gecersiz.")
        self.db.execute(
            "UPDATE kullanicilar SET rol = ?, aktif_mi = ? WHERE kullanici_id = ?",
            (rol, 1 if aktif_mi else 0, kullanici_id),
        )

    def bakiye_yukle(self, kullanici_id: int, tutar: float, aciklama: str = "Bakiye yukleme") -> None:
        if tutar <= 0:
            raise ValueError("Tutar pozitif olmali.")
        now = self._now()
        self.db.execute("UPDATE kullanicilar SET bakiye = bakiye + ? WHERE kullanici_id = ?", (tutar, kullanici_id))
        self.db.execute(
            "INSERT INTO bakiye_hareketleri (kullanici_id, tutar, aciklama, created_at) VALUES (?, ?, ?, ?)",
            (kullanici_id, tutar, aciklama, now),
        )

    def arac_ekle(self, sahip_id: int, marka: str, model: str, kilometre: int, gorsel_yolu: str = "") -> int:
        if kilometre < 0:
            raise ValueError("Kilometre negatif olamaz.")
        return self.db.execute(
            """
            INSERT INTO araclar (sahip_id, marka, model, kilometre, musait_mi, gorsel_yolu, created_at)
            VALUES (?, ?, ?, ?, 1, ?, ?)
            """,
            (sahip_id, marka.strip(), model.strip(), kilometre, gorsel_yolu.strip(), self._now()),
        )

    def kullanici_araclari_getir(self, kullanici_id: int) -> list[dict]:
        rows = self.db.fetchall(
            "SELECT arac_id, marka, model, kilometre, musait_mi, gorsel_yolu FROM araclar WHERE sahip_id = ? ORDER BY arac_id DESC",
            (kullanici_id,),
        )
        return [dict(r) for r in rows]

    def ilan_olustur(
        self, ilan_sahibi_id: int, arac_id: int, baslik: str, aciklama: str, saatlik_ucret: float, konum: str
    ) -> int:
        if saatlik_ucret <= 0:
            raise ValueError("Saatlik ucret pozitif olmali.")
        arac = self.db.fetchone("SELECT sahip_id FROM araclar WHERE arac_id = ?", (arac_id,))
        if not arac:
            raise ValueError("Arac bulunamadi.")
        if int(arac["sahip_id"]) != ilan_sahibi_id:
            raise ValueError("Sadece kendi araciniz icin ilan olusturabilirsiniz.")
        return self.db.execute(
            """
            INSERT INTO ilanlar (arac_id, ilan_sahibi_id, baslik, aciklama, saatlik_ucret, konum, durum, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            """,
            (arac_id, ilan_sahibi_id, baslik.strip(), aciklama.strip(), saatlik_ucret, konum.strip(), self._now()),
        )

    def ilan_durum_guncelle(self, ilan_id: int, durum: str) -> None:
        if durum not in {"pending", "approved", "rejected"}:
            raise ValueError("Durum gecersiz.")
        self.db.execute("UPDATE ilanlar SET durum = ? WHERE ilan_id = ?", (durum, ilan_id))

    def kullanici_ilanlari_getir(self, kullanici_id: int) -> list[dict]:
        rows = self.db.fetchall(
            """
            SELECT i.ilan_id, i.baslik, i.aciklama, i.saatlik_ucret, i.konum, i.durum, i.created_at,
                   a.arac_id, a.marka, a.model, a.kilometre, a.musait_mi, a.gorsel_yolu
            FROM ilanlar i
            JOIN araclar a ON a.arac_id = i.arac_id
            WHERE i.ilan_sahibi_id = ?
            ORDER BY i.ilan_id DESC
            """,
            (kullanici_id,),
        )
        return [dict(r) for r in rows]

    def ilan_guncelle(
        self,
        ilan_id: int,
        sahip_id: int,
        baslik: str,
        aciklama: str,
        saatlik_ucret: float,
        konum: str,
    ) -> None:
        baslik = (baslik or "").strip()
        aciklama = (aciklama or "").strip()
        konum = (konum or "").strip()
        if not baslik:
            raise ValueError("Baslik bos olamaz.")
        if not aciklama:
            raise ValueError("Aciklama bos olamaz.")
        if saatlik_ucret <= 0:
            raise ValueError("Saatlik ucret pozitif olmalidir.")
        ilan = self.db.fetchone(
            "SELECT ilan_sahibi_id, durum FROM ilanlar WHERE ilan_id = ?",
            (ilan_id,),
        )
        if not ilan:
            raise ValueError("Ilan bulunamadi.")
        if int(ilan["ilan_sahibi_id"]) != sahip_id:
            raise ValueError("Sadece kendi ilaninizi guncelleyebilirsiniz.")
        active = self.db.fetchone(
            "SELECT 1 FROM kiralamalar WHERE ilan_id = ? AND bitis_saati IS NULL LIMIT 1",
            (ilan_id,),
        )
        if active:
            raise ValueError("Aktif kiralamasi olan ilan duzenlenemez. Once kiralamayi sonlandirin.")
        self.db.execute(
            """
            UPDATE ilanlar
            SET baslik = ?, aciklama = ?, saatlik_ucret = ?, konum = ?, durum = 'pending'
            WHERE ilan_id = ?
            """,
            (baslik, aciklama, saatlik_ucret, konum, ilan_id),
        )
        self.bildirim_ekle(
            sahip_id,
            "Ilan guncellendi",
            f"Ilan #{ilan_id} guncellendi ve yeniden admin onayina dustu.",
        )
        admin_rows = self.db.fetchall(
            "SELECT kullanici_id FROM kullanicilar WHERE rol = 'admin' AND aktif_mi = 1"
        )
        for adm in admin_rows:
            self.bildirim_ekle(
                int(adm["kullanici_id"]),
                "Ilan guncellendi - onay bekliyor",
                f"Ilan #{ilan_id} sahibi tarafindan duzenlendi, yeniden onayinizi bekliyor.",
            )

    def ilanlar_getir(self, sadece_onayli: bool = False) -> list[dict]:
        where = "WHERE i.durum = 'approved'" if sadece_onayli else ""
        rows = self.db.fetchall(
            f"""
            SELECT i.ilan_id, i.baslik, i.aciklama, i.saatlik_ucret, i.konum, i.durum, i.created_at,
                   a.arac_id, a.marka, a.model, a.kilometre, a.musait_mi, a.gorsel_yolu,
                   ku.kullanici_id AS sahip_id, ku.ad AS sahip_ad
            FROM ilanlar i
            JOIN araclar a ON a.arac_id = i.arac_id
            JOIN kullanicilar ku ON ku.kullanici_id = i.ilan_sahibi_id
            {where}
            ORDER BY i.ilan_id DESC
            """
        )
        return [dict(r) for r in rows]

    def kira_tutar_hesapla(self, ilan_id: int, saat: int) -> float:
        if saat <= 0:
            raise ValueError("Saat pozitif olmali.")
        ilan = self.db.fetchone("SELECT saatlik_ucret FROM ilanlar WHERE ilan_id = ?", (ilan_id,))
        if not ilan:
            raise ValueError("Ilan bulunamadi.")
        return float(ilan["saatlik_ucret"]) * float(saat)

    def kiralama_baslat(self, ilan_id: int, kiralayan_id: int, saat: int) -> int:
        if saat <= 0:
            raise ValueError("Kiralama suresi en az 1 saat olmali.")
        if saat > 24 * 30:
            raise ValueError("Kiralama suresi 30 gunu asamaz.")
        with self.db.transaction() as conn:
            ilan_row = conn.execute(
                """
                SELECT i.ilan_id, i.saatlik_ucret, i.durum, i.ilan_sahibi_id,
                       a.arac_id, a.musait_mi, a.sahip_id
                FROM ilanlar i JOIN araclar a ON a.arac_id = i.arac_id
                WHERE i.ilan_id = ?
                """,
                (ilan_id,),
            ).fetchone()
            if not ilan_row:
                raise ValueError("Ilan bulunamadi.")
            if ilan_row["durum"] != "approved":
                raise ValueError("Sadece onayli ilan kiralanabilir.")
            if ilan_row["sahip_id"] == kiralayan_id:
                raise ValueError("Kendi ilaninizi kiralayamazsiniz.")
            if ilan_row["musait_mi"] == 0:
                raise ValueError("Arac musait degil.")
            active_for_user = conn.execute(
                """
                SELECT 1 FROM kiralamalar
                WHERE ilan_id = ? AND kiralayan_id = ? AND durum = 'active' LIMIT 1
                """,
                (ilan_id, kiralayan_id),
            ).fetchone()
            if active_for_user:
                raise ValueError("Bu ilan icin zaten aktif bir kiralamaniz var.")
            kiralayan = conn.execute(
                "SELECT bakiye FROM kullanicilar WHERE kullanici_id = ?",
                (kiralayan_id,),
            ).fetchone()
            if not kiralayan:
                raise ValueError("Kullanici bulunamadi.")
            toplam_tutar = round(float(ilan_row["saatlik_ucret"]) * float(saat), 2)
            if float(kiralayan["bakiye"]) < toplam_tutar:
                raise ValueError("Yetersiz bakiye.")

            now = self._now()
            cur = conn.execute(
                """
                INSERT INTO kiralamalar
                    (ilan_id, kiralayan_id, baslangic_saati, kira_saat, toplam_tutar, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (ilan_id, kiralayan_id, now, int(saat), toplam_tutar, now),
            )
            rental_id = cur.lastrowid
            conn.execute(
                "UPDATE araclar SET musait_mi = 0 WHERE arac_id = ?",
                (ilan_row["arac_id"],),
            )
            conn.execute(
                "UPDATE kullanicilar SET bakiye = bakiye - ? WHERE kullanici_id = ?",
                (toplam_tutar, kiralayan_id),
            )
            conn.execute(
                "UPDATE kullanicilar SET bakiye = bakiye + ? WHERE kullanici_id = ?",
                (toplam_tutar, ilan_row["ilan_sahibi_id"]),
            )
            conn.execute(
                """
                INSERT INTO bildirimler (kullanici_id, baslik, mesaj, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    ilan_row["ilan_sahibi_id"],
                    "Yeni kiralama",
                    f"Ilan #{ilan_id} araciniz {saat} saatlik kiralandi. Kazanc: {toplam_tutar:.2f} TL",
                    now,
                ),
            )
            conn.execute(
                """
                INSERT INTO bildirimler (kullanici_id, baslik, mesaj, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    kiralayan_id,
                    "Kiralama baslatildi",
                    f"Ilan #{ilan_id} icin {saat} saatlik kiralama olusturuldu. Toplam: {toplam_tutar:.2f} TL",
                    now,
                ),
            )
            return int(rental_id)

    def kiralama_bitir(self, kiralama_id: int, kullanici_id: int | None = None) -> None:
        with self.db.transaction() as conn:
            row = conn.execute(
                "SELECT * FROM kiralamalar WHERE kiralama_id = ?",
                (kiralama_id,),
            ).fetchone()
            if not row:
                raise ValueError("Kiralama bulunamadi.")
            if row["durum"] != "active":
                raise ValueError("Kiralama zaten tamamlanmis.")
            if kullanici_id is not None and int(row["kiralayan_id"]) != int(kullanici_id):
                raise ValueError("Sadece kendi kiralamanizi sonlandirabilirsiniz.")
            ilan = conn.execute(
                "SELECT arac_id, ilan_sahibi_id FROM ilanlar WHERE ilan_id = ?",
                (row["ilan_id"],),
            ).fetchone()
            if not ilan:
                raise ValueError("Ilan bulunamadi.")
            now = self._now()
            conn.execute(
                """
                UPDATE kiralamalar
                SET bitis_saati = ?, durum = 'completed',
                    toplam_tutar = COALESCE(toplam_tutar, 0)
                WHERE kiralama_id = ?
                """,
                (now, kiralama_id),
            )
            conn.execute(
                "UPDATE araclar SET musait_mi = 1 WHERE arac_id = ?",
                (ilan["arac_id"],),
            )
            conn.execute(
                """
                INSERT INTO bildirimler (kullanici_id, baslik, mesaj, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    int(row["kiralayan_id"]),
                    "Kiralama tamamlandi",
                    f"Kiralama #{kiralama_id} sonlandirildi.",
                    now,
                ),
            )

    def kullanici_kiralamalari(
        self, kullanici_id: int, sadece_aktif: bool = False
    ) -> list[dict]:
        where = "WHERE k.kiralayan_id = ?"
        if sadece_aktif:
            where += " AND k.durum = 'active'"
        rows = self.db.fetchall(
            f"""
            SELECT k.kiralama_id, k.ilan_id, k.baslangic_saati, k.bitis_saati,
                   k.kira_saat, k.toplam_tutar, k.durum,
                   i.baslik, i.aciklama, i.saatlik_ucret, i.konum,
                   a.arac_id, a.marka, a.model, a.kilometre, a.gorsel_yolu,
                   ku.kullanici_id AS sahip_id, ku.ad AS sahip_ad
            FROM kiralamalar k
            JOIN ilanlar i ON i.ilan_id = k.ilan_id
            JOIN araclar a ON a.arac_id = i.arac_id
            JOIN kullanicilar ku ON ku.kullanici_id = i.ilan_sahibi_id
            {where}
            ORDER BY k.kiralama_id DESC
            """,
            (kullanici_id,),
        )
        return [dict(r) for r in rows]

    def aktif_kiralamalari_getir(self) -> list[dict]:
        rows = self.db.fetchall(
            """
            SELECT k.kiralama_id, i.baslik, u.ad AS kiralayan, k.baslangic_saati
            FROM kiralamalar k
            JOIN ilanlar i ON i.ilan_id = k.ilan_id
            JOIN kullanicilar u ON u.kullanici_id = k.kiralayan_id
            WHERE k.durum = 'active'
            ORDER BY k.kiralama_id DESC
            """
        )
        return [dict(r) for r in rows]

    def kullanici_kiraladi_mi(self, ilan_id: int, kullanici_id: int) -> bool:
        row = self.db.fetchone(
            "SELECT 1 FROM kiralamalar WHERE ilan_id = ? AND kiralayan_id = ? LIMIT 1",
            (ilan_id, kullanici_id),
        )
        return row is not None

    def kullanici_yorumladi_mi(self, ilan_id: int, kullanici_id: int) -> bool:
        row = self.db.fetchone(
            "SELECT 1 FROM yorumlar WHERE ilan_id = ? AND kullanici_id = ? LIMIT 1",
            (ilan_id, kullanici_id),
        )
        return row is not None

    def yorum_ekle(self, ilan_id: int, kullanici_id: int, yorum: str) -> int:
        text = yorum.strip()
        if not text:
            raise ValueError("Yorum bos olamaz.")
        if len(text) > 500:
            raise ValueError("Yorum en fazla 500 karakter olabilir.")
        if not self.kullanici_kiraladi_mi(ilan_id, kullanici_id):
            raise ValueError("Yorum yapmak icin once bu ilanin aracini kiralamalisiniz.")
        if self.kullanici_yorumladi_mi(ilan_id, kullanici_id):
            raise ValueError("Bu ilana zaten bir yorum yaptiniz. Her ilana yalnizca 1 yorum hakkiniz vardir.")
        return self.db.execute(
            "INSERT INTO yorumlar (ilan_id, kullanici_id, yorum, created_at) VALUES (?, ?, ?, ?)",
            (ilan_id, kullanici_id, text, self._now()),
        )

    def yorumlari_getir(self, ilan_id: int) -> list[dict]:
        rows = self.db.fetchall(
            """
            SELECT y.yorum_id, y.yorum, y.created_at, k.ad,
                   (SELECT p.puan FROM puanlar p WHERE p.ilan_id = y.ilan_id AND p.kullanici_id = y.kullanici_id) AS puan
            FROM yorumlar y
            JOIN kullanicilar k ON k.kullanici_id = y.kullanici_id
            WHERE y.ilan_id = ?
            ORDER BY y.yorum_id DESC
            """,
            (ilan_id,),
        )
        return [dict(r) for r in rows]

    def puan_ver(self, ilan_id: int, kullanici_id: int, puan: int) -> None:
        if puan < 1 or puan > 5:
            raise ValueError("Puan 1-5 araliginda olmali.")
        if not self.kullanici_kiraladi_mi(ilan_id, kullanici_id):
            raise ValueError("Puan vermek icin once bu ilanin aracini kiralamalisiniz.")
        existing = self.db.fetchone(
            "SELECT puan_id FROM puanlar WHERE ilan_id = ? AND kullanici_id = ?",
            (ilan_id, kullanici_id),
        )
        if existing:
            raise ValueError("Bu ilana zaten puan verdiniz. Her ilana yalnizca 1 puan hakkiniz vardir.")
        self.db.execute(
            "INSERT INTO puanlar (ilan_id, kullanici_id, puan, created_at) VALUES (?, ?, ?, ?)",
            (ilan_id, kullanici_id, puan, self._now()),
        )

    def puan_ozeti(self, ilan_id: int) -> dict:
        row = self.db.fetchone(
            "SELECT AVG(puan) AS ortalama, COUNT(*) AS adet FROM puanlar WHERE ilan_id = ?",
            (ilan_id,),
        )
        if not row or row["adet"] == 0:
            return {"ortalama": 0.0, "adet": 0}
        return {"ortalama": float(row["ortalama"] or 0.0), "adet": int(row["adet"])}

    def kullanici_puani(self, ilan_id: int, kullanici_id: int) -> int:
        row = self.db.fetchone(
            "SELECT puan FROM puanlar WHERE ilan_id = ? AND kullanici_id = ?",
            (ilan_id, kullanici_id),
        )
        return int(row["puan"]) if row else 0

    def begen_toggle(self, ilan_id: int, kullanici_id: int) -> None:
        row = self.db.fetchone("SELECT begeni_id FROM begeniler WHERE ilan_id = ? AND kullanici_id = ?", (ilan_id, kullanici_id))
        if row:
            self.db.execute("DELETE FROM begeniler WHERE begeni_id = ?", (row["begeni_id"],))
            return
        self.db.execute(
            "INSERT INTO begeniler (ilan_id, kullanici_id, created_at) VALUES (?, ?, ?)",
            (ilan_id, kullanici_id, self._now()),
        )

    def begeni_sayisi(self, ilan_id: int) -> int:
        row = self.db.fetchone("SELECT COUNT(*) AS cnt FROM begeniler WHERE ilan_id = ?", (ilan_id,))
        return int(row["cnt"]) if row else 0

    def ticket_olustur(self, kullanici_id: int, baslik: str, mesaj: str) -> int:
        b = baslik.strip()
        m = mesaj.strip()
        if not b or not m:
            raise ValueError("Ticket baslik ve mesaj zorunludur.")
        now = self._now()
        return self.db.execute(
            """
            INSERT INTO ticketler (acan_kullanici_id, baslik, mesaj, durum, created_at, updated_at)
            VALUES (?, ?, ?, 'open', ?, ?)
            """,
            (kullanici_id, b, m, now, now),
        )

    def ticketleri_getir(self, sadece_kullanici_id: int | None = None) -> list[dict]:
        base_query = (
            """
            SELECT t.ticket_id, t.baslik, t.mesaj, t.durum, t.yanit, t.yanit_tarihi,
                   t.created_at, t.updated_at,
                   k.ad,
                   yk.ad AS yanitlayan_ad,
                   yk.rol AS yanitlayan_rol
            FROM ticketler t
            JOIN kullanicilar k ON k.kullanici_id = t.acan_kullanici_id
            LEFT JOIN kullanicilar yk ON yk.kullanici_id = t.yanitlayan_id
            """
        )
        if sadece_kullanici_id is not None:
            rows = self.db.fetchall(
                base_query + " WHERE t.acan_kullanici_id = ? ORDER BY t.ticket_id DESC",
                (sadece_kullanici_id,),
            )
        else:
            rows = self.db.fetchall(base_query + " ORDER BY t.ticket_id DESC")
        return [dict(r) for r in rows]

    def ticket_getir(self, ticket_id: int) -> dict:
        row = self.db.fetchone(
            """
            SELECT t.ticket_id, t.baslik, t.mesaj, t.durum, t.yanit, t.yanit_tarihi,
                   t.created_at, t.updated_at,
                   k.ad, k.email,
                   yk.ad AS yanitlayan_ad,
                   yk.rol AS yanitlayan_rol
            FROM ticketler t
            JOIN kullanicilar k ON k.kullanici_id = t.acan_kullanici_id
            LEFT JOIN kullanicilar yk ON yk.kullanici_id = t.yanitlayan_id
            WHERE t.ticket_id = ?
            """,
            (ticket_id,),
        )
        if not row:
            raise ValueError("Ticket bulunamadi.")
        return dict(row)

    def ticket_yanitla(self, ticket_id: int, yanit: str, durum: str, yanitlayan_id: int) -> None:
        if durum not in {"open", "in_progress", "closed"}:
            raise ValueError("Ticket durum gecersiz.")
        ticket = self.db.fetchone(
            "SELECT acan_kullanici_id FROM ticketler WHERE ticket_id = ?",
            (ticket_id,),
        )
        now = self._now()
        self.db.execute(
            """
            UPDATE ticketler
            SET yanit = ?, durum = ?, yanitlayan_id = ?, yanit_tarihi = ?, updated_at = ?
            WHERE ticket_id = ?
            """,
            (yanit.strip(), durum, yanitlayan_id, now, now, ticket_id),
        )
        if ticket:
            self.bildirim_ekle(
                int(ticket["acan_kullanici_id"]),
                "Ticket guncellendi",
                f"Ticket #{ticket_id} durumu: {durum}",
            )

    def bildirim_ekle(self, kullanici_id: int, baslik: str, mesaj: str) -> int:
        return self.db.execute(
            "INSERT INTO bildirimler (kullanici_id, baslik, mesaj, okundu_mu, created_at) VALUES (?, ?, ?, 0, ?)",
            (kullanici_id, baslik.strip(), mesaj.strip(), self._now()),
        )

    def bildirimleri_getir(self, kullanici_id: int) -> list[dict]:
        rows = self.db.fetchall(
            """
            SELECT bildirim_id, baslik, mesaj, okundu_mu, created_at
            FROM bildirimler
            WHERE kullanici_id = ?
            ORDER BY bildirim_id DESC
            """,
            (kullanici_id,),
        )
        return [dict(r) for r in rows]

    def bildirim_okundu_yap(self, bildirim_id: int, kullanici_id: int) -> None:
        self.db.execute(
            "UPDATE bildirimler SET okundu_mu = 1 WHERE bildirim_id = ? AND kullanici_id = ?",
            (bildirim_id, kullanici_id),
        )

    def reset_database(self) -> None:
        self.db.reset_data(SYSTEM_ADMIN_EMAIL)
        self.admin_seed()

    def backup_database(self, target_path: Path) -> Path:
        return self.db.backup_to(Path(target_path))

    def dashboard_stats(self) -> dict:
        users = self.db.fetchone("SELECT COUNT(*) AS cnt FROM kullanicilar")
        listings = self.db.fetchone("SELECT COUNT(*) AS cnt FROM ilanlar")
        active = self.db.fetchone("SELECT COUNT(*) AS cnt FROM kiralamalar WHERE durum = 'active'")
        tickets = self.db.fetchone("SELECT COUNT(*) AS cnt FROM ticketler WHERE durum != 'closed'")
        return {
            "users": int(users["cnt"]) if users else 0,
            "listings": int(listings["cnt"]) if listings else 0,
            "active_rentals": int(active["cnt"]) if active else 0,
            "open_tickets": int(tickets["cnt"]) if tickets else 0,
        }
