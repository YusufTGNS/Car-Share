from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Arac:
    arac_id: Optional[int]
    marka: str
    model: str
    kilometre: int
    musait_mi: bool = True

    def arac_durumu_guncelle(self, musait: bool) -> None:
        self.musait_mi = musait

    def kilometre_guncelle(self, yeni_kilometre: int) -> None:
        if yeni_kilometre < self.kilometre:
            raise ValueError("Kilometre geri alınamaz.")
        self.kilometre = yeni_kilometre


@dataclass
class Kullanici:
    kullanici_id: Optional[int]
    ad: str
    ehliyet_no: str

    def kiralama_gecmisi(self) -> str:
        return f"{self.ad} için kiralama geçmişi servis katmanından alınmalıdır."


@dataclass
class Kiralama:
    kiralama_id: Optional[int]
    arac_id: int
    kullanici_id: int
    baslangic_saati: datetime
    bitis_saati: Optional[datetime] = None

    def kiralama_baslat(self) -> None:
        self.baslangic_saati = datetime.now()

    def kiralama_bitir(self) -> None:
        self.bitis_saati = datetime.now()

    def kiralama_bilgisi(self) -> str:
        bitis = self.bitis_saati.isoformat(sep=" ", timespec="minutes") if self.bitis_saati else "-"
        return (
            f"Kiralama#{self.kiralama_id} | Arac: {self.arac_id} | Kullanici: {self.kullanici_id} | "
            f"Baslangic: {self.baslangic_saati.isoformat(sep=' ', timespec='minutes')} | Bitis: {bitis}"
        )

