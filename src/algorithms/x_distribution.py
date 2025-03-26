"""
Moduł zawierający implementację algorytmu załadunku w oparciu o rozkład wzdłuż osi X.
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


class XDistributionLoading(LoadingAlgorithm):
    """
    Algorytm załadunku w oparciu o rozkład wzdłuż osi X (długość naczepy).
    
    Algorytm dzieli naczepę na strefy wzdłuż osi X i balansuje masę
    ładunku między strefami, zapewniając równomierny rozkład masy.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicjalizuje algorytm załadunku w oparciu o rozkład X.
        
        Args:
            config: Słownik konfiguracyjny algorytmu (opcjonalny)
        """
        # Domyślna konfiguracja
        default_config = ALGORITHM_DEFAULTS.get("X_Distribution", {})
        
        # Połączenie domyślnej konfiguracji z konfiguracją dostarczoną przez użytkownika
        merged_config = {**default_config, **(config or {})}
        
        super().__init__("X Distribution Loading", merged_config)
    
    def load_pallets(self, pallets: List[Pallet]) -> List[Pallet]:
        """
        Przeprowadza załadunek palet do naczepy z balansowaniem masy wzdłuż osi X.
        
        Args:
            pallets: Lista palet do załadunku
            
        Returns:
            List[Pallet]: Lista załadowanych palet z przypisanymi pozycjami
        """
        logger.info(f"Rozpoczynam załadunek {len(pallets)} palet metodą X_Distribution")
        
        # Sortowanie palet według masy (od najcięższej)
        sorted_pallets = self._sort_pallets_by_weight(pallets)
        
        # Liczba stref wzdłuż osi X
        zones_count = self.config.get("zones", 3)
        
        # Podział naczepy na strefy wzdłuż osi X
        zone_length = self.trailer.length // zones_count
        
        # Inicjalizacja słowników stref i ich obciążenia
        zones = {i: [] for i in range(zones_count)}  # Lista palet w strefie
        zone_weights = {i: 0.0 for i in range(zones_count)}  # Całkowita masa w strefie
        
        loaded_pallets = []
        
        # Współczynnik balansowania wagi
        balancing_factor = self.config.get("balancing_factor", 0.8)
        
        # Załadunek palet z balansowaniem masy
        for pallet in sorted_pallets:
            # Wybór optymalnej strefy dla palety
            best_zone = self._select_best_zone(pallet, zones, zone_weights, zone_length, balancing_factor)
            
            if best_zone is not None:
                # Próba umieszczenia palety w wybranej strefie
                position = self._find_position_in_zone(pallet, best_zone, zone_length)
                
                if position:
                    # Ustawienie pozycji palety
                    x, y, z = position
                    pallet.set_position(x, y, z)
                    
                    # Dodanie palety do naczepy
                    if self.trailer.add_pallet(pallet):
                        loaded_pallets.append(pallet)
                        zones[best_zone].append(pallet)
                        zone_weights[best_zone] += pallet.total_weight
                        
                        logger.debug(f"Załadowano paletę {pallet.pallet_id} w strefie {best_zone} na pozycji {position}")
                else:
                    # Próba obrócenia palety
                    original_rotation = pallet.rotation
                    pallet.rotate()
                    
                    position = self._find_position_in_zone(pallet, best_zone, zone_length)
                    
                    if position:
                        # Ustawienie pozycji palety
                        x, y, z = position
                        pallet.set_position(x, y, z)
                        
                        # Dodanie palety do naczepy
                        if self.trailer.add_pallet(pallet):
                            loaded_pallets.append(pallet)
                            zones[best_zone].append(pallet)
                            zone_weights[best_zone] += pallet.total_weight
                            
                            logger.debug(f"Załadowano obróconą paletę {pallet.pallet_id} w strefie {best_zone} na pozycji {position}")
                    else:
                        # Przywróć oryginalną rotację, jeśli nie udało się załadować
                        if pallet.rotation != original_rotation:
                            pallet.rotate()
                        
                        logger.debug(f"Nie udało się załadować palety {pallet.pallet_id} w strefie {best_zone}")
            else:
                logger.debug(f"Nie znaleziono odpowiedniej strefy dla palety {pallet.pallet_id}")
        
        logger.info(f"Zakończono załadunek, załadowano {len(loaded_pallets)} palet")
        return loaded_pallets
    
    def _select_best_zone(self, pallet: Pallet, zones: Dict[int, List[Pallet]], 
                          zone_weights: Dict[int, float], zone_length: int, 
                          balancing_factor: float) -> Optional[int]:
        """
        Wybiera najlepszą strefę dla palety, biorąc pod uwagę balansowanie masy.
        
        Args:
            pallet: Paleta do umieszczenia
            zones: Słownik mapujący numery stref na listy palet w tych strefach
            zone_weights: Słownik mapujący numery stref na całkowitą masę w strefie
            zone_length: Długość jednej strefy
            balancing_factor: Współczynnik balansowania masy
            
        Returns:
            Optional[int]: Numer wybranej strefy lub None, jeśli nie znaleziono odpowiedniej
        """
        total_weight = sum(zone_weights.values()) + pallet.total_weight
        
        # Idealny rozkład masy między strefami
        ideal_zone_weight = total_weight / len(zones)
        
        # Posortowanie stref według różnicy między aktualną a idealną masą
        sorted_zones = sorted(
            zones.keys(),
            key=lambda zone_idx: abs(zone_weights[zone_idx] - ideal_zone_weight)
        )
        
        # Próba umieszczenia palety w najlepszej strefie
        for zone_idx in sorted_zones:
            # Sprawdzenie, czy paleta zmieści się w strefie
            x_start = zone_idx * zone_length
            x_end = (zone_idx + 1) * zone_length
            
            # Utworzenie tymczasowej palety do sprawdzenia
            temp_pallet = Pallet(
                pallet_id=pallet.pallet_id,
                pallet_type=pallet.pallet_type,
                length=pallet.length,
                width=pallet.width,
                height=pallet.height,
                weight=pallet.weight,
                cargo_weight=pallet.cargo_weight,
                position=(x_start, 0, 0),  # Tymczasowa pozycja w strefie
                rotation=pallet.rotation
            )
            
            # Sprawdzenie, czy są dostępne pozycje w strefie
            available_in_zone = False
            for x in range(x_start, x_end - temp_pallet.dimensions[0] + 1, 100):
                for y in range(0, self.trailer.width - temp_pallet.dimensions[1] + 1, 100):
                    # Sprawdzenie, czy paleta zmieści się na tej pozycji
                    temp_pallet.set_position(x, y, 0)
                    if not any(temp_pallet.collides_with(loaded_pallet) for loaded_pallet in self.trailer.loaded_pallets):
                        available_in_zone = True
                        break
                
                if available_in_zone:
                    break
            
            # Sprawdzenie dodatkowych kryteriów balansu
            if available_in_zone:
                # Obliczanie nowej masy strefy
                new_zone_weight = zone_weights[zone_idx] + pallet.total_weight
                
                # Obliczanie współczynnika balansu
                balance_ratio = new_zone_weight / (ideal_zone_weight * len(zones))
                
                # Sprawdzenie, czy balans jest akceptowalny
                if balance_ratio <= 1.0 + balancing_factor:
                    return zone_idx
        
        # Jeśli nie znaleziono odpowiedniej strefy, zwróć None
        return None
    
    def _find_position_in_zone(self, pallet: Pallet, zone_idx: int, zone_length: int) -> Optional[Tuple[int, int, int]]:
        """
        Znajduje pozycję dla palety w określonej strefie.
        
        Args:
            pallet: Paleta do umieszczenia
            zone_idx: Indeks strefy
            zone_length: Długość jednej strefy
            
        Returns:
            Optional[Tuple[int, int, int]]: Pozycja (x, y, z) lub None, jeśli nie znaleziono miejsca
        """
        # Granice strefy
        x_start = zone_idx * zone_length
        x_end = min((zone_idx + 1) * zone_length, self.trailer.length)
        
        best_position = None
        lowest_z = float('inf')
        
        # Przeszukanie potencjalnych pozycji w strefie
        for x in range(x_start, x_end - pallet.dimensions[0] + 1, 100):
            for y in range(0, self.trailer.width - pallet.dimensions[1] + 1, 100):
                # Sprawdzenie najniższej dostępnej wysokości
                z = self.trailer._find_lowest_available_height(x, y, pallet.dimensions[0], pallet.dimensions[1])
                
                if z is not None and z + pallet.dimensions[2] <= self.trailer.height:
                    # Sprawdzenie, czy ta pozycja jest niżej niż poprzednia najlepsza
                    if z < lowest_z:
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
                            lowest_z = z
        
        return best_position 