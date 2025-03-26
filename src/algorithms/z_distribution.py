"""
Moduł zawierający implementację algorytmu załadunku w oparciu o rozkład wzdłuż osi Z.
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


class ZDistributionLoading(LoadingAlgorithm):
    """
    Algorytm załadunku w oparciu o rozkład wzdłuż osi Z (wysokość).
    
    Algorytm dzieli naczepę na warstwy wzdłuż osi Z i optymalizuje załadunek
    w sposób zapewniający stabilność ładunku oraz umożliwiający efektywne
    wykorzystanie przestrzeni.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicjalizuje algorytm załadunku w oparciu o rozkład Z.
        
        Args:
            config: Słownik konfiguracyjny algorytmu (opcjonalny)
        """
        # Domyślna konfiguracja
        default_config = ALGORITHM_DEFAULTS.get("Z_Distribution", {})
        
        # Połączenie domyślnej konfiguracji z konfiguracją dostarczoną przez użytkownika
        merged_config = {**default_config, **(config or {})}
        
        super().__init__("Z Distribution Loading", merged_config)
    
    def load_pallets(self, pallets: List[Pallet]) -> List[Pallet]:
        """
        Przeprowadza załadunek palet do naczepy z optymalizacją wzdłuż osi Z.
        
        Args:
            pallets: Lista palet do załadunku
            
        Returns:
            List[Pallet]: Lista załadowanych palet z przypisanymi pozycjami
        """
        logger.info(f"Rozpoczynam załadunek {len(pallets)} palet metodą Z_Distribution")
        
        # Liczba warstw wzdłuż osi Z
        layers_count = self.config.get("zones", 2)
        
        # Sortowanie palet według objętości (od największej)
        sorted_pallets = self._sort_pallets_by_volume(pallets)
        
        # Grupowanie palet według wysokości
        pallets_by_height = self._group_pallets_by_height(sorted_pallets)
        
        loaded_pallets = []
        
        # Załadunek palet, zaczynając od najniższej warstwy
        for layer_idx in range(layers_count):
            # Obliczenie zakresu wysokości dla warstwy
            layer_height = self.trailer.height // layers_count
            z_start = layer_idx * layer_height
            z_end = (layer_idx + 1) * layer_height
            
            # Wybór palet odpowiednich dla tej warstwy
            layer_pallets = self._select_pallets_for_layer(pallets_by_height, layer_idx, layers_count, layer_height)
            
            # Załadunek palet w warstwie
            loaded_layer_pallets = self._load_layer(layer_pallets, z_start, layer_height)
            loaded_pallets.extend(loaded_layer_pallets)
        
        logger.info(f"Zakończono załadunek, załadowano {len(loaded_pallets)} palet")
        return loaded_pallets
    
    def _group_pallets_by_height(self, pallets: List[Pallet]) -> Dict[int, List[Pallet]]:
        """
        Grupuje palety według wysokości.
        
        Args:
            pallets: Lista palet do pogrupowania
            
        Returns:
            Dict[int, List[Pallet]]: Słownik mapujący wysokości na listy palet
        """
        grouped = {}
        
        for pallet in pallets:
            height = pallet.height
            if height not in grouped:
                grouped[height] = []
            grouped[height].append(pallet)
        
        return grouped
    
    def _select_pallets_for_layer(self, pallets_by_height: Dict[int, List[Pallet]], 
                                layer_idx: int, total_layers: int, layer_height: int) -> List[Pallet]:
        """
        Wybiera palety odpowiednie dla danej warstwy.
        
        Args:
            pallets_by_height: Słownik grupujący palety według wysokości
            layer_idx: Indeks warstwy
            total_layers: Całkowita liczba warstw
            layer_height: Wysokość warstwy
            
        Returns:
            List[Pallet]: Lista palet wybranych dla danej warstwy
        """
        selected_pallets = []
        
        # Balansowanie faktora
        balancing_factor = self.config.get("balancing_factor", 0.7)
        
        if layer_idx == 0:
            # Dla najniższej warstwy wybieramy najcięższe palety
            pallets_list = []
            for height, height_pallets in pallets_by_height.items():
                if height <= layer_height:
                    pallets_list.extend(height_pallets)
            
            # Sortowanie według masy (od najcięższej)
            pallets_list = self._sort_pallets_by_weight(pallets_list)
            
            # Wybieramy palety nieprzekraczające wysokości warstwy
            selected_pallets = [p for p in pallets_list if p.height <= layer_height]
        else:
            # Dla wyższych warstw wybieramy lżejsze palety
            pallets_list = []
            for height, height_pallets in pallets_by_height.items():
                if height <= layer_height:
                    pallets_list.extend(height_pallets)
            
            # Sortowanie według masy (od najlżejszej dla wyższych warstw)
            pallets_list = self._sort_pallets_by_weight(pallets_list, reverse=False)
            
            # Im wyższa warstwa, tym lżejsze palety
            weight_threshold = self.trailer.max_load * balancing_factor * (1 - layer_idx / total_layers)
            
            # Wybieramy palety nieprzekraczające wysokości warstwy i progu wagowego
            selected_pallets = [p for p in pallets_list if p.height <= layer_height and p.total_weight <= weight_threshold]
        
        return selected_pallets
    
    def _load_layer(self, pallets: List[Pallet], z_start: int, layer_height: int) -> List[Pallet]:
        """
        Załadunek palet w określonej warstwie.
        
        Args:
            pallets: Lista palet do załadunku w warstwie
            z_start: Początkowa wysokość warstwy
            layer_height: Wysokość warstwy
            
        Returns:
            List[Pallet]: Lista załadowanych palet w warstwie
        """
        loaded_pallets = []
        
        # Algorytm załadunku dla warstwy
        for pallet in pallets:
            # Próba znalezienia pozycji dla palety w warstwie
            position = self._find_position_in_layer(pallet, z_start, layer_height)
            
            if position:
                # Ustawienie pozycji palety
                x, y, z = position
                pallet.set_position(x, y, z)
                
                # Dodanie palety do naczepy
                if self.trailer.add_pallet(pallet):
                    loaded_pallets.append(pallet)
                    logger.debug(f"Załadowano paletę {pallet.pallet_id} na pozycji {position}")
            else:
                # Próba obrócenia palety
                original_rotation = pallet.rotation
                pallet.rotate()
                
                position = self._find_position_in_layer(pallet, z_start, layer_height)
                
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
                    
                    logger.debug(f"Nie udało się załadować palety {pallet.pallet_id} w warstwie")
        
        return loaded_pallets
    
    def _find_position_in_layer(self, pallet: Pallet, z_start: int, layer_height: int) -> Optional[Tuple[int, int, int]]:
        """
        Znajduje pozycję dla palety w określonej warstwie.
        
        Args:
            pallet: Paleta do umieszczenia
            z_start: Początkowa wysokość warstwy
            layer_height: Wysokość warstwy
            
        Returns:
            Optional[Tuple[int, int, int]]: Pozycja (x, y, z) lub None, jeśli nie znaleziono miejsca
        """
        best_position = None
        min_distance = float('inf')
        
        # Przeszukanie potencjalnych pozycji w warstwie
        for x in range(0, self.trailer.length - pallet.dimensions[0] + 1, 100):
            for y in range(0, self.trailer.width - pallet.dimensions[1] + 1, 100):
                # Sprawdzenie najniższej dostępnej wysokości
                z = self.trailer._find_lowest_available_height(x, y, pallet.dimensions[0], pallet.dimensions[1])
                
                if z is not None and z >= z_start and z + pallet.dimensions[2] <= z_start + layer_height:
                    # Sprawdzenie, czy ta pozycja jest najlepsza (najbliżej środka naczepy)
                    # Preferujemy pozycje bliżej środka dla lepszej stabilności
                    center_x = self.trailer.length / 2
                    center_y = self.trailer.width / 2
                    
                    # Odległość od środka
                    distance = math.sqrt((x + pallet.dimensions[0]/2 - center_x)**2 + 
                                        (y + pallet.dimensions[1]/2 - center_y)**2)
                    
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