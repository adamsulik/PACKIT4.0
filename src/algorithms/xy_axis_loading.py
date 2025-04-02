"""
Moduł zawierający implementację algorytmu załadunku wzdłuż osi X oraz Y.
"""

from typing import List, Dict, Any, Tuple, Optional
import logging

from src.algorithms.base_algorithm import LoadingAlgorithm
from src.data.pallet import Pallet
from src.data.trailer import Trailer
from src.config import ALGORITHM_DEFAULTS

# Konfiguracja loggera
logger = logging.getLogger(__name__)


class XYAxisLoading(LoadingAlgorithm):
    """
    Algorytm załadunku wzdłuż osi X oraz Y.
    
    Algorytm załadunku optymalizujący wykorzystanie przestrzeni naczepy
    poprzez układanie palet warstwami wzdłuż osi X (długość) i Y (szerokość).
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicjalizuje algorytm załadunku wzdłuż osi X oraz Y.
        
        Args:
            config: Słownik konfiguracyjny algorytmu (opcjonalny)
        """
        # Domyślna konfiguracja
        default_config = ALGORITHM_DEFAULTS.get("XY_Axis_Loading", {})
        
        # Połączenie domyślnej konfiguracji z konfiguracją dostarczoną przez użytkownika
        merged_config = {**default_config, **(config or {})}
        
        super().__init__("XY Axis Loading", merged_config)
    
    def load_pallets(self, pallets: List[Pallet]) -> List[Pallet]:
        """
        Przeprowadza załadunek palet do naczepy wzdłuż osi X oraz Y.
        
        Args:
            pallets: Lista palet do załadunku
            
        Returns:
            List[Pallet]: Lista załadowanych palet z przypisanymi pozycjami
        """
        logger.info(f"Rozpoczynam załadunek {len(pallets)} palet metodą XY_Axis_Loading")
        
        # Sortowanie palet według określonej strategii
        if self.config.get("prioritize_heavy_pallets", True):
            # Najpierw ładujemy cięższe palety
            sorted_pallets = self._sort_pallets_by_weight(pallets)
        else:
            # Najpierw ładujemy palety o największej objętości
            sorted_pallets = self._sort_pallets_by_volume(pallets)
        
        loaded_pallets = []
        
        # Określenie kierunku załadunku
        start_position = self.config.get("start_position", "front")
        
        # Załadunek palet
        for pallet in sorted_pallets:
            # Próba znalezienia najlepszej pozycji dla palety
            position = self._find_best_position(pallet, start_position)
            
            if position:
                # Ustawienie pozycji palety
                x, y, z = position
                pallet.set_position(x, y, z)
                
                # Dodanie palety do naczepy
                if self.trailer.add_pallet(pallet):
                    loaded_pallets.append(pallet)
                    logger.debug(f"Załadowano paletę {pallet.pallet_id} na pozycji {position}")
            else:
                # Próba obrócenia palety i ponownego załadunku
                original_rotation = pallet.rotation
                pallet.rotate()
                
                position = self._find_best_position(pallet, start_position)
                
                if position:
                    # Ustawienie pozycji palety
                    x, y, z = position
                    pallet.set_position(x, y, z)
                    
                    # Dodanie palety do naczepy
                    if self.trailer.add_pallet(pallet):
                        loaded_pallets.append(pallet)
                        logger.debug(f"Załadowano obróconą paletę {pallet.pallet_id} na pozycji {position}")
                else:
                    # Przywróć oryginalną rotację, jeśli nie udało się załadować
                    if pallet.rotation != original_rotation:
                        pallet.rotate()
                    
                    logger.debug(f"Nie udało się załadować palety {pallet.pallet_id}")
        
        logger.info(f"Zakończono załadunek, załadowano {len(loaded_pallets)} palet")
        return loaded_pallets
    
    def _find_best_position(self, pallet: Pallet, start_position: str) -> Optional[Tuple[int, int, int]]:
        """
        Znajduje najlepszą pozycję dla palety według strategii załadunku wzdłuż osi X oraz Y.
        
        Args:
            pallet: Paleta do umieszczenia
            start_position: Punkt startowy załadunku ('front' lub 'back')
            
        Returns:
            Optional[Tuple[int, int, int]]: Pozycja (x, y, z) lub None, jeśli nie znaleziono miejsca
        """
        # Ustawiamy palety zawsze na poziomie z=0 (bez piętrowania)
        z = 0
        
        # Dostępne pozycje dla palety (przeszukujemy tylko przy z=0)
        available_positions = []
        
        # Krok przeszukiwania (co 100 mm)
        step = 100
        
        # Przeszukiwanie pozycji na poziomie z=0
        for x in range(0, self.trailer.length - pallet.dimensions[0] + 1, step):
            for y in range(0, self.trailer.width - pallet.dimensions[1] + 1, step):
                # Utworzenie tymczasowej palety w badanej pozycji
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
                    available_positions.append((x, y, z))
        
        if not available_positions:
            return None
        
        # Sortowanie pozycji według strategii
        if start_position == "front":
            # Zacznij od przodu naczepy (niskie X)
            available_positions.sort(key=lambda pos: (pos[0], pos[1]))
        else:
            # Zacznij od tyłu naczepy (wysokie X)
            available_positions.sort(key=lambda pos: (-pos[0], pos[1]))
        
        # Zwróć najlepszą pozycję
        return available_positions[0] if available_positions else None 