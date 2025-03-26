"""
Moduł zawierający implementację algorytmu załadunku w oparciu o rozkład wzdłuż osi Y.
"""

from typing import List, Dict, Any, Tuple, Optional
import logging
import math

from src.algorithms.base_algorithm import LoadingAlgorithm
from src.data.pallet import Pallet
from src.data.trailer import Trailer
from src.config import ALGORITHM_DEFAULTS

# Konfiguracja loggera
logger = logging.getLogger(__name__)


class YDistributionLoading(LoadingAlgorithm):
    """
    Algorytm załadunku w oparciu o rozkład wzdłuż osi Y (szerokość).
    
    Algorytm dzieli naczepę na strefy wzdłuż osi Y i optymalizuje załadunek
    w sposób zapewniający równomierne rozłożenie palet na szerokości naczepy,
    co poprawia stabilność ładunku i umożliwia efektywne wykorzystanie przestrzeni.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicjalizuje algorytm załadunku w oparciu o rozkład Y.
        
        Args:
            config: Słownik konfiguracyjny algorytmu (opcjonalny)
        """
        # Domyślna konfiguracja
        default_config = ALGORITHM_DEFAULTS.get("Y_Distribution", {})
        
        # Połączenie domyślnej konfiguracji z konfiguracją dostarczoną przez użytkownika
        merged_config = {**default_config, **(config or {})}
        
        super().__init__("Y Distribution Loading", merged_config)
    
    def load_pallets(self, pallets: List[Pallet]) -> List[Pallet]:
        """
        Przeprowadza załadunek palet do naczepy z optymalizacją wzdłuż osi Y.
        
        Args:
            pallets: Lista palet do załadunku
            
        Returns:
            List[Pallet]: Lista załadowanych palet z przypisanymi pozycjami
        """
        logger.info(f"Rozpoczynam załadunek {len(pallets)} palet metodą Y_Distribution")
        
        # Obracanie palet (z wyjątkiem L10) do układania wzdłuż osi Y
        for pallet in pallets:
            # Sprawdzamy, czy to nie jest paleta L10 (której nie można obrócić)
            if pallet.pallet_type != "L10" and pallet.rotation == 0:
                # Obracamy paletę o 90 stopni, aby była ułożona wzdłuż osi Y
                pallet.rotate()
                logger.debug(f"Obrócono paletę {pallet.pallet_id} typu {pallet.pallet_type} wzdłuż osi Y")
        
        # Sortowanie palet według objętości (od największej)
        sorted_pallets = self._sort_pallets_by_volume(pallets)
        
        # Liczba stref wzdłuż osi Y
        zones_count = self.config.get("zones", 2)
        
        # Podzielenie szerokości naczepy na strefy
        zone_width = self.trailer.width // zones_count
        
        # Załadunek palet w każdej strefie
        loaded_pallets = []
        for zone_idx in range(zones_count):
            y_start = zone_idx * zone_width
            y_end = (zone_idx + 1) * zone_width if zone_idx < zones_count - 1 else self.trailer.width
            
            # Uzyskanie palet dla tej strefy
            zone_pallets = self._sort_pallets_by_weight(sorted_pallets[zone_idx::zones_count])
            
            # Załadunek palet w strefie
            zone_loaded_pallets = self._load_zone(zone_pallets, y_start, y_end)
            loaded_pallets.extend(zone_loaded_pallets)
        
        logger.info(f"Zakończono załadunek, załadowano {len(loaded_pallets)} palet")
        return loaded_pallets
    
    def _load_zone(self, pallets: List[Pallet], y_start: int, y_end: int) -> List[Pallet]:
        """
        Ładuje palety w określonej strefie Y.
        
        Args:
            pallets: Lista palet do załadunku
            y_start: Początek strefy Y
            y_end: Koniec strefy Y
            
        Returns:
            List[Pallet]: Lista załadowanych palet w strefie
        """
        loaded_pallets = []
        
        # Algorytm załadunku dla strefy Y
        for pallet in pallets:
            # Zapamiętaj pierwotną rotację palety
            original_rotation = pallet.rotation
            
            # Próba znalezienia pozycji dla palety w strefie Y
            position = self._find_position_in_zone(pallet, y_start, y_end)
            
            if position:
                # Ustawienie pozycji palety
                x, y, z = position
                pallet.set_position(x, y, z)
                
                # Dodanie palety do naczepy
                if self.trailer.add_pallet(pallet):
                    loaded_pallets.append(pallet)
                    logger.debug(f"Załadowano paletę {pallet.pallet_id} na pozycji {position}")
            else:
                # Jeśli nie udało się umieścić palety, spróbuj zmienić jej orientację
                pallet.rotate()
                
                position = self._find_position_in_zone(pallet, y_start, y_end)
                
                if position:
                    # Ustawienie pozycji palety
                    x, y, z = position
                    pallet.set_position(x, y, z)
                    
                    # Dodanie palety do naczepy
                    if self.trailer.add_pallet(pallet):
                        loaded_pallets.append(pallet)
                        logger.debug(f"Załadowano paletę {pallet.pallet_id} w alternatywnej orientacji na pozycji {position}")
                else:
                    # Przywróć oryginalną rotację, jeśli nie udało się załadować w żadnej orientacji
                    if pallet.rotation != original_rotation:
                        pallet.rotate()
                    
                    logger.debug(f"Nie udało się załadować palety {pallet.pallet_id} w strefie")
        
        return loaded_pallets
    
    def _find_position_in_zone(self, pallet: Pallet, y_start: int, y_end: int) -> Optional[Tuple[int, int, int]]:
        """
        Znajduje pozycję dla palety w określonej strefie Y.
        
        Args:
            pallet: Paleta do umieszczenia
            y_start: Początek strefy Y
            y_end: Koniec strefy Y
            
        Returns:
            Optional[Tuple[int, int, int]]: Pozycja (x, y, z) lub None, jeśli nie znaleziono miejsca
        """
        best_position = None
        min_distance = float('inf')
        
        # Zawsze ustawiamy z=0 (palety nie są piętrowane)
        z = 0
        
        # Przeszukanie potencjalnych pozycji w strefie Y
        for x in range(0, self.trailer.length - pallet.dimensions[0] + 1, 100):
            # Szukamy pozycji y w zakresie strefy Y, uwzględniając szerokość palety
            for y in range(y_start, y_end - pallet.dimensions[1] + 1, 100):
                # Sprawdzenie, czy ta pozycja jest najlepsza (najbliżej środka strefy Y)
                # Preferujemy pozycje bliżej środka strefy dla lepszego rozkładu
                center_y = (y_start + y_end) / 2
                
                # Odległość od środka strefy Y
                distance = abs(y + pallet.dimensions[1]/2 - center_y)
                
                if distance < min_distance:
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
                    
                    # Sprawdzenie kolizji
                    if not self.trailer._check_collision(temp_pallet):
                        best_position = (x, y, z)
                        min_distance = distance
        
        return best_position 