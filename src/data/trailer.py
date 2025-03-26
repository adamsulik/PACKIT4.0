"""
Moduł zawierający definicję klasy Trailer do reprezentacji naczepy transportowej.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import numpy as np

from src.data.pallet import Pallet
from src.config import TRAILER_CONFIG, CONSTRAINTS


@dataclass
class Trailer:
    """
    Klasa reprezentująca naczepę transportową.

    Attributes:
        length: Długość naczepy w mm
        width: Szerokość naczepy w mm
        height: Wysokość naczepy w mm
        max_load: Maksymalna masa ładunku w kg
        loaded_pallets: Lista załadowanych palet
        space_map: Trójwymiarowa macierz reprezentująca zajętość przestrzeni
        weight_distribution: Rozkład masy w naczepie
    """

    length: int = TRAILER_CONFIG["length"]
    width: int = TRAILER_CONFIG["width"]
    height: int = TRAILER_CONFIG["height"]
    max_load: int = TRAILER_CONFIG["max_load"]
    loaded_pallets: List[Pallet] = field(default_factory=list)
    space_map: Optional[np.ndarray] = None
    weight_distribution: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        """Inicjalizacja mapy przestrzeni i rozkładu masy."""
        # Inicjalizacja mapy przestrzeni (0 = wolne, 1 = zajęte)
        # Używamy nizskiej rozdzielczości dla efektywności (1 jednostka = 100mm)
        self.resolution = 100  # mm
        self.space_map = np.zeros((
            self.length // self.resolution + 1,
            self.width // self.resolution + 1,
            self.height // self.resolution + 1
        ), dtype=np.int8)
        
        # Inicjalizacja rozkładu masy
        self.weight_distribution = {
            "left": 0.0,    # Lewa strona naczepy
            "right": 0.0,   # Prawa strona naczepy
            "front": 0.0,   # Przód naczepy
            "back": 0.0,    # Tył naczepy
            "total": 0.0    # Łączna masa załadunku
        }

    def add_pallet(self, pallet: Pallet) -> bool:
        """
        Dodaje paletę do naczepy i aktualizuje mapę przestrzeni.
        
        Args:
            pallet: Paleta do dodania
            
        Returns:
            bool: True jeśli paleta została dodana pomyślnie, False w przeciwnym razie
        """
        # Sprawdź, czy paleta mieści się w naczepie
        if not self._check_bounds(pallet):
            return False
        
        # Sprawdź, czy paleta koliduje z innymi paletami
        if self._check_collision(pallet):
            return False
        
        # Sprawdź, czy nie przekraczamy maksymalnej masy
        if self._current_load() + pallet.total_weight > self.max_load:
            return False
        
        # Aktualizacja mapy przestrzeni
        self._update_space_map(pallet, 1)  # 1 = zajęte
        
        # Dodaj paletę do listy
        self.loaded_pallets.append(pallet)
        
        # Aktualizacja rozkładu masy
        self._update_weight_distribution()
        
        return True

    def remove_pallet(self, pallet_id: str) -> bool:
        """
        Usuwa paletę z naczepy i aktualizuje mapę przestrzeni.
        
        Args:
            pallet_id: ID palety do usunięcia
            
        Returns:
            bool: True jeśli paleta została usunięta pomyślnie, False w przeciwnym razie
        """
        # Znajdź paletę po ID
        for i, pallet in enumerate(self.loaded_pallets):
            if pallet.pallet_id == pallet_id:
                # Aktualizacja mapy przestrzeni
                self._update_space_map(pallet, 0)  # 0 = wolne
                
                # Usuń paletę z listy
                self.loaded_pallets.pop(i)
                
                # Aktualizacja rozkładu masy
                self._update_weight_distribution()
                
                return True
        
        return False

    def get_loading_efficiency(self) -> Dict[str, float]:
        """
        Zwraca metryki efektywności załadunku.
        
        Returns:
            Dict: Słownik zawierający różne metryki efektywności
        """
        # Obliczanie objętości wszystkich palet
        total_pallet_volume = sum(pallet.volume for pallet in self.loaded_pallets)
        
        # Obliczanie całkowitej objętości naczepy
        trailer_volume = self.length * self.width * self.height
        
        # Obliczanie wykorzystania przestrzeni
        space_utilization = total_pallet_volume / trailer_volume * 100 if trailer_volume > 0 else 0
        
        # Obliczanie wykorzystania ładowności
        weight_utilization = self._current_load() / self.max_load * 100 if self.max_load > 0 else 0
        
        # Obliczanie liczby palet na metr sześcienny
        pallets_per_cubic_meter = len(self.loaded_pallets) / (trailer_volume / 1_000_000) if trailer_volume > 0 else 0
        
        return {
            "space_utilization": space_utilization,  # Procentowe wykorzystanie przestrzeni
            "weight_utilization": weight_utilization,  # Procentowe wykorzystanie ładowności
            "pallets_loaded": len(self.loaded_pallets),  # Liczba załadowanych palet
            "pallets_per_cubic_meter": pallets_per_cubic_meter,  # Liczba palet na metr sześcienny
            "weight_balance_side": self._calculate_weight_balance_side(),  # Balans masy bok do boku (0-1, gdzie 0.5 to idealne zrównoważenie)
            "weight_balance_front_back": self._calculate_weight_balance_front_back()  # Balans masy przód-tył (0-1, gdzie docelowo ok. 0.6)
        }

    def is_weight_distribution_valid(self) -> Dict[str, bool]:
        """
        Sprawdza, czy rozkład masy jest zgodny z ograniczeniami.
        
        Returns:
            Dict: Słownik z informacjami o poprawności rozkładu masy
        """
        # Pobranie progu różnicy rozkładu masy
        threshold = CONSTRAINTS["weight_distribution_threshold"]
        front_to_back_target = CONSTRAINTS["front_to_back_weight_distribution"]
        
        # Sprawdzenie balansu bok do boku
        side_balance = self._calculate_weight_balance_side()
        side_balanced = abs(side_balance - 0.5) <= threshold
        
        # Sprawdzenie balansu przód-tył
        front_back_balance = self._calculate_weight_balance_front_back()
        front_back_balanced = abs(front_back_balance - front_to_back_target) <= threshold
        
        return {
            "side_balanced": side_balanced,
            "front_back_balanced": front_back_balanced,
            "overall_valid": side_balanced and front_back_balanced
        }

    def get_available_positions(self, pallet: Pallet) -> List[Tuple[int, int, int]]:
        """
        Zwraca listę dostępnych pozycji dla palety.
        
        Args:
            pallet: Paleta do umieszczenia
            
        Returns:
            List: Lista dostępnych pozycji (x, y, z)
        """
        available_positions = []
        
        # Wymiary palety
        pallet_length, pallet_width, pallet_height = pallet.dimensions
        
        # Przeszukiwanie przestrzeni naczepy
        for x in range(0, self.length - pallet_length + 1, self.resolution):
            for y in range(0, self.width - pallet_width + 1, self.resolution):
                # Znajdź najniższą możliwą wysokość z
                z = self._find_lowest_available_height(x, y, pallet_length, pallet_width)
                
                if z is not None and z + pallet_height <= self.height:
                    # Sprawdź, czy przestrzeń jest dostępna
                    temp_pallet = Pallet(
                        pallet_id=pallet.pallet_id,
                        pallet_type=pallet.pallet_type,
                        length=pallet.length,
                        width=pallet.width,
                        height=pallet.height,
                        weight=pallet.weight,
                        cargo_weight=pallet.cargo_weight,
                        position=(x, y, z),
                        rotation=pallet.rotation
                    )
                    
                    if not self._check_collision(temp_pallet):
                        available_positions.append((x, y, z))
        
        return available_positions

    def reset(self) -> None:
        """Resetuje naczepę do stanu początkowego."""
        self.loaded_pallets = []
        self.space_map = np.zeros((
            self.length // self.resolution + 1,
            self.width // self.resolution + 1,
            self.height // self.resolution + 1
        ), dtype=np.int8)
        
        self.weight_distribution = {
            "left": 0.0,
            "right": 0.0,
            "front": 0.0,
            "back": 0.0,
            "total": 0.0
        }

    def _check_bounds(self, pallet: Pallet) -> bool:
        """Sprawdza, czy paleta mieści się w granicach naczepy."""
        x, y, z = pallet.position
        length, width, height = pallet.dimensions
        
        return (
            0 <= x and x + length <= self.length and
            0 <= y and y + width <= self.width and
            0 <= z and z + height <= self.height
        )

    def _check_collision(self, pallet: Pallet) -> bool:
        """Sprawdza, czy paleta koliduje z innymi paletami."""
        for loaded_pallet in self.loaded_pallets:
            if pallet.collides_with(loaded_pallet):
                return True
        return False

    def _update_space_map(self, pallet: Pallet, value: int) -> None:
        """Aktualizuje mapę przestrzeni dla podanej palety."""
        x, y, z = pallet.position
        length, width, height = pallet.dimensions
        
        # Konwersja do indeksów mapy przestrzeni
        x_start = x // self.resolution
        y_start = y // self.resolution
        z_start = z // self.resolution
        
        x_end = (x + length) // self.resolution + 1
        y_end = (y + width) // self.resolution + 1
        z_end = (z + height) // self.resolution + 1
        
        # Ustaw zajętość w mapie przestrzeni
        x_end = min(x_end, self.space_map.shape[0])
        y_end = min(y_end, self.space_map.shape[1])
        z_end = min(z_end, self.space_map.shape[2])
        
        self.space_map[x_start:x_end, y_start:y_end, z_start:z_end] = value

    def _update_weight_distribution(self) -> None:
        """Aktualizuje rozkład masy dla załadowanych palet."""
        # Reset rozkładu masy
        self.weight_distribution = {
            "left": 0.0,
            "right": 0.0,
            "front": 0.0,
            "back": 0.0,
            "total": 0.0
        }
        
        # Podział naczepy na strefy
        middle_width = self.width / 2
        middle_length = self.length / 2
        
        # Obliczanie rozkładu masy
        for pallet in self.loaded_pallets:
            x, y, z = pallet.position
            length, width, _ = pallet.dimensions
            
            # Określenie, w której strefie znajduje się środek palety
            center_x = x + length / 2
            center_y = y + width / 2
            
            # Lewa/prawa strona
            if center_y < middle_width:
                self.weight_distribution["left"] += pallet.total_weight
            else:
                self.weight_distribution["right"] += pallet.total_weight
            
            # Przód/tył
            if center_x < middle_length:
                self.weight_distribution["front"] += pallet.total_weight
            else:
                self.weight_distribution["back"] += pallet.total_weight
            
            # Łączna masa
            self.weight_distribution["total"] += pallet.total_weight

    def _current_load(self) -> float:
        """Zwraca aktualną masę załadunku."""
        return sum(pallet.total_weight for pallet in self.loaded_pallets)

    def _calculate_weight_balance_side(self) -> float:
        """Oblicza balans masy bok do boku (0-1, gdzie 0.5 to idealne zrównoważenie)."""
        left = self.weight_distribution["left"]
        right = self.weight_distribution["right"]
        total = left + right
        
        if total == 0:
            return 0.5  # Brak załadunku, przyjmujemy idealny balans
        
        return right / total

    def _calculate_weight_balance_front_back(self) -> float:
        """Oblicza balans masy przód-tył (0-1, gdzie docelowo ok. 0.6)."""
        front = self.weight_distribution["front"]
        back = self.weight_distribution["back"]
        total = front + back
        
        if total == 0:
            return 0.0  # Brak załadunku
        
        return front / total

    def _find_lowest_available_height(self, x: int, y: int, length: int, width: int) -> Optional[int]:
        """Znajduje najniższą dostępną wysokość dla palety o podanych wymiarach."""
        # Konwersja do indeksów mapy przestrzeni
        x_start = x // self.resolution
        y_start = y // self.resolution
        
        x_end = (x + length) // self.resolution + 1
        y_end = (y + width) // self.resolution + 1
        
        # Sprawdź, czy indeksy są w granicach mapy
        if (x_end >= self.space_map.shape[0] or 
            y_end >= self.space_map.shape[1]):
            return None
        
        # Znajdź najwyższą zajętą wysokość
        max_height = 0
        for x_idx in range(x_start, x_end):
            for y_idx in range(y_start, y_end):
                # Znajdź najwyższy zajęty blok
                occupied_heights = np.where(self.space_map[x_idx, y_idx, :] == 1)[0]
                if len(occupied_heights) > 0:
                    block_height = (occupied_heights[-1] + 1) * self.resolution
                    max_height = max(max_height, block_height)
        
        return max_height 