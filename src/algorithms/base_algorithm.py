"""
Moduł zawierający definicję klasy bazowej dla algorytmów załadunku palet.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional

from src.data.pallet import Pallet
from src.data.trailer import Trailer
from src.config import TRAILER_CONFIG


class LoadingAlgorithm(ABC):
    """
    Klasa bazowa dla wszystkich algorytmów załadunku palet.
    
    Attributes:
        name: Nazwa algorytmu
        trailer: Obiekt naczepy, która ma być załadowana
        config: Konfiguracja algorytmu
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Inicjalizuje nowy algorytm załadunku.
        
        Args:
            name: Nazwa algorytmu
            config: Słownik konfiguracyjny algorytmu (opcjonalny)
        """
        self.name = name
        self.trailer = Trailer()
        self.config = config or {}
    
    @abstractmethod
    def load_pallets(self, pallets: List[Pallet]) -> List[Pallet]:
        """
        Przeprowadza załadunek palet do naczepy.
        
        Args:
            pallets: Lista palet do załadunku
            
        Returns:
            List[Pallet]: Lista załadowanych palet z przypisanymi pozycjami
        """
        pass
    
    def run(self, pallets: List[Pallet], reset: bool = True) -> List[Pallet]:
        """
        Uruchamia algorytm załadunku palet.
        
        Args:
            pallets: Lista palet do załadunku
            reset: Czy zresetować naczepę przed załadunkiem
            
        Returns:
            List[Pallet]: Lista załadowanych palet z przypisanymi pozycjami
        """
        # Resetowanie naczepy jeśli wymagane
        if reset:
            self.trailer.reset()
        
        # Głęboka kopia palet, aby nie modyfikować oryginałów
        pallets_to_load = [
            Pallet(
                pallet_id=p.pallet_id,
                pallet_type=p.pallet_type,
                length=p.length,
                width=p.width,
                height=p.height,
                weight=p.weight,
                cargo_weight=p.cargo_weight,
                max_stack_weight=p.max_stack_weight,
                stackable=p.stackable,
                fragile=p.fragile,
                color=p.color
            ) for p in pallets
        ]
        
        # Przeprowadzenie załadunku
        loaded_pallets = self.load_pallets(pallets_to_load)
        
        # Aktualizacja naczepy
        self.trailer.loaded_pallets = loaded_pallets
        
        return loaded_pallets
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Zwraca statystyki załadunku dla bieżącego stanu naczepy.
        
        Returns:
            Dict[str, Any]: Słownik ze statystykami
        """
        return {
            "efficiency": self.trailer.get_loading_efficiency(),
            "weight_distribution": self.trailer.weight_distribution,
            "weight_distribution_valid": self.trailer.is_weight_distribution_valid(),
            "pallets_count": len(self.trailer.loaded_pallets)
        }
    
    def _sort_pallets_by_volume(self, pallets: List[Pallet], reverse: bool = True) -> List[Pallet]:
        """
        Sortuje palety według objętości.
        
        Args:
            pallets: Lista palet do posortowania
            reverse: Czy sortować malejąco (domyślnie True)
            
        Returns:
            List[Pallet]: Posortowana lista palet
        """
        return sorted(pallets, key=lambda p: p.volume, reverse=reverse)
    
    def _sort_pallets_by_weight(self, pallets: List[Pallet], reverse: bool = True) -> List[Pallet]:
        """
        Sortuje palety według masy.
        
        Args:
            pallets: Lista palet do posortowania
            reverse: Czy sortować malejąco (domyślnie True)
            
        Returns:
            List[Pallet]: Posortowana lista palet
        """
        return sorted(pallets, key=lambda p: p.total_weight, reverse=reverse)
    
    def _sort_pallets_by_footprint(self, pallets: List[Pallet], reverse: bool = True) -> List[Pallet]:
        """
        Sortuje palety według powierzchni podstawy.
        
        Args:
            pallets: Lista palet do posortowania
            reverse: Czy sortować malejąco (domyślnie True)
            
        Returns:
            List[Pallet]: Posortowana lista palet
        """
        return sorted(pallets, key=lambda p: p.footprint[0] * p.footprint[1], reverse=reverse)
    
    def _try_rotate_pallet(self, pallet: Pallet, trailer: Trailer) -> bool:
        """
        Próbuje obrócić paletę, jeśli to możliwe, aby lepiej pasowała do naczepy.
        
        Args:
            pallet: Paleta do obrócenia
            trailer: Naczepa, w której ma być umieszczona paleta
            
        Returns:
            bool: True jeśli obrócenie poprawiło dopasowanie, False w przeciwnym razie
        """
        # Zapamiętaj oryginalną rotację
        original_rotation = pallet.rotation
        
        # Obróć paletę
        pallet.rotate()
        
        # Sprawdź, czy teraz lepiej pasuje (czy ma więcej dostępnych pozycji)
        available_positions_after = trailer.get_available_positions(pallet)
        
        # Przywróć oryginalną rotację
        if original_rotation != pallet.rotation:
            pallet.rotate()
        
        # Obróć ponownie tylko jeśli to poprawia dopasowanie
        if len(available_positions_after) > 0:
            pallet.rotate()
            return True
        
        return False 