"""
Moduł zawierający definicję klasy Pallet do reprezentacji palet transportowych.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List


@dataclass
class Pallet:
    """
    Klasa reprezentująca paletę transportową.

    Attributes:
        pallet_id: Unikalny identyfikator palety
        pallet_type: Typ palety (np. EUR, EUR2, INDUSTRIAL)
        length: Długość palety w mm
        width: Szerokość palety w mm
        height: Wysokość palety w mm
        weight: Masa palety w kg
        cargo_weight: Masa ładunku na palecie w kg
        max_stack_weight: Maksymalna masa, którą paleta może unieść w kg
        stackable: Czy paleta może być układana w stosy
        fragile: Czy ładunek jest kruchy
        position: Pozycja palety w przestrzeni (x, y, z) w mm
        rotation: Rotacja palety (0 lub 90 stopni w płaszczyźnie XZ)
        color: Kolor palety w formacie rgba dla wizualizacji
    """

    pallet_id: str
    pallet_type: str
    length: int
    width: int
    height: int
    weight: int
    cargo_weight: int = 0
    max_stack_weight: Optional[int] = None
    stackable: bool = True
    fragile: bool = False
    position: Tuple[int, int, int] = (0, 0, 0)
    rotation: int = 0  # 0 lub 90 stopni
    color: str = "rgba(31, 119, 180, 0.7)"

    def __post_init__(self):
        # Upewnij się, że rotacja to 0 lub 90
        if self.rotation not in [0, 90]:
            raise ValueError("Rotacja musi wynosić 0 lub 90 stopni")

    @property
    def total_weight(self) -> int:
        """Zwraca całkowitą masę palety wraz z ładunkiem."""
        return self.weight + self.cargo_weight

    @property
    def dimensions(self) -> Tuple[int, int, int]:
        """Zwraca wymiary palety z uwzględnieniem rotacji."""
        if self.rotation == 0:
            return (self.length, self.width, self.height)
        else:  # 90 stopni
            return (self.width, self.length, self.height)

    @property
    def footprint(self) -> Tuple[int, int]:
        """Zwraca powierzchnię podstawy palety z uwzględnieniem rotacji."""
        if self.rotation == 0:
            return (self.length, self.width)
        else:  # 90 stopni
            return (self.width, self.length)

    @property
    def volume(self) -> int:
        """Zwraca objętość palety w mm³."""
        return self.length * self.width * self.height

    @property
    def corners(self) -> List[Tuple[int, int, int]]:
        """Zwraca współrzędne wszystkich 8 rogów palety."""
        x, y, z = self.position
        dx, dy, dz = self.dimensions
        
        return [
            (x, y, z),  # Róg początkowy
            (x + dx, y, z),  # Przód prawy dół
            (x, y + dy, z),  # Tył lewy dół
            (x + dx, y + dy, z),  # Tył prawy dół
            (x, y, z + dz),  # Przód lewy góra
            (x + dx, y, z + dz),  # Przód prawy góra
            (x, y + dy, z + dz),  # Tył lewy góra
            (x + dx, y + dy, z + dz),  # Tył prawy góra
        ]

    def rotate(self) -> None:
        """Obraca paletę o 90 stopni w płaszczyźnie XZ."""
        self.rotation = 0 if self.rotation == 90 else 90

    def set_position(self, x: int, y: int, z: int) -> None:
        """Ustawia pozycję palety w przestrzeni."""
        self.position = (x, y, z)

    def collides_with(self, other: 'Pallet') -> bool:
        """Sprawdza, czy paleta koliduje z inną paletą."""
        x1, y1, z1 = self.position
        l1, w1, h1 = self.dimensions
        
        x2, y2, z2 = other.position
        l2, w2, h2 = other.dimensions
        
        # Sprawdzenie kolizji w każdym wymiarze
        x_collision = x1 < x2 + l2 and x1 + l1 > x2
        y_collision = y1 < y2 + w2 and y1 + w1 > y2
        z_collision = z1 < z2 + h2 and z1 + h1 > z2
        
        return x_collision and y_collision and z_collision

    @classmethod
    def from_dict(cls, data: Dict) -> 'Pallet':
        """Tworzy instancję palety z danych słownikowych."""
        return cls(**data)

    def to_dict(self) -> Dict:
        """Konwertuje paletę do słownika."""
        return {
            "pallet_id": self.pallet_id,
            "pallet_type": self.pallet_type,
            "length": self.length,
            "width": self.width,
            "height": self.height,
            "weight": self.weight,
            "cargo_weight": self.cargo_weight,
            "max_stack_weight": self.max_stack_weight,
            "stackable": self.stackable,
            "fragile": self.fragile,
            "position": self.position,
            "rotation": self.rotation,
            "color": self.color
        } 