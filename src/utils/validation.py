"""
Moduł zawierający funkcje do walidacji załadunku palet.
"""

from typing import List, Dict, Tuple, Any
import numpy as np

from src.data.pallet import Pallet
from src.data.trailer import Trailer
from src.config import CONSTRAINTS


def check_collision(pallets: List[Pallet]) -> List[Tuple[str, str]]:
    """
    Sprawdza, czy między paletami występują kolizje.
    
    Args:
        pallets: Lista palet do sprawdzenia
        
    Returns:
        List[Tuple[str, str]]: Lista par ID palet, które ze sobą kolidują
    """
    collisions = []
    
    # Sprawdzenie kolizji dla każdej pary palet
    for i, pallet1 in enumerate(pallets):
        for j, pallet2 in enumerate(pallets[i+1:], i+1):
            if pallet1.collides_with(pallet2):
                collisions.append((pallet1.pallet_id, pallet2.pallet_id))
    
    return collisions


def check_weight_distribution(pallets: List[Pallet], trailer: Trailer) -> Dict[str, Any]:
    """
    Sprawdza, czy rozkład masy palet jest zgodny z ograniczeniami.
    
    Args:
        pallets: Lista załadowanych palet
        trailer: Naczepa
        
    Returns:
        Dict: Słownik z informacjami o poprawności rozkładu masy
    """
    # Wykorzystanie metody z klasy Trailer
    trailer.loaded_pallets = pallets
    trailer._update_weight_distribution()
    
    return trailer.is_weight_distribution_valid()


def check_space_utilization(pallets: List[Pallet], trailer: Trailer) -> Dict[str, float]:
    """
    Oblicza metryki wykorzystania przestrzeni naczepy.
    
    Args:
        pallets: Lista załadowanych palet
        trailer: Naczepa
        
    Returns:
        Dict: Słownik z metrykami wykorzystania przestrzeni
    """
    # Wykorzystanie metody z klasy Trailer
    trailer.loaded_pallets = pallets
    
    return trailer.get_loading_efficiency()


def check_stacking_validity(pallets: List[Pallet]) -> List[str]:
    """
    Sprawdza, czy palety są poprawnie ułożone na sobie.
    
    Args:
        pallets: Lista załadowanych palet
        
    Returns:
        List[str]: Lista ID palet, które są niepoprawnie ułożone
    """
    invalid_stacking = []
    
    # Mapa pozycji palet na podłodze (z=0)
    floor_positions = {}
    stacked_pallets = {}
    
    # Sortowanie palet wg wysokości (od najniższej)
    sorted_pallets = sorted(pallets, key=lambda p: p.position[2])
    
    for pallet in sorted_pallets:
        x, y, z = pallet.position
        l, w, _ = pallet.dimensions
        
        # Jeśli paleta nie stoi na podłodze
        if z > 0:
            is_supported = False
            
            # Sprawdzenie, czy pod paletą jest inna paleta
            for other_pallet in pallets:
                if other_pallet.pallet_id == pallet.pallet_id:
                    continue
                
                ox, oy, oz = other_pallet.position
                ol, ow, oh = other_pallet.dimensions
                
                # Sprawdzenie, czy paleta znajduje się bezpośrednio pod sprawdzaną paletą
                if (ox <= x < ox + ol or ox < x + l <= ox + ol) and \
                   (oy <= y < oy + ow or oy < y + w <= oy + ow) and \
                   oz + oh == z:
                    
                    # Sprawdzenie, czy paleta pod spodem może być obciążana
                    if not other_pallet.stackable:
                        invalid_stacking.append(pallet.pallet_id)
                        break
                    
                    # Sprawdzenie maksymalnej masy obciążenia palety pod spodem
                    if other_pallet.max_stack_weight is not None and \
                       pallet.total_weight > other_pallet.max_stack_weight:
                        invalid_stacking.append(pallet.pallet_id)
                        break
                    
                    is_supported = True
                    break
            
            # Jeśli paleta nie jest podparta przez inną paletę
            if not is_supported:
                invalid_stacking.append(pallet.pallet_id)
        
        # Jeśli paleta ma kruchy ładunek, sprawdź czy nic na niej nie stoi
        if pallet.fragile:
            for other_pallet in pallets:
                if other_pallet.pallet_id == pallet.pallet_id:
                    continue
                
                ox, oy, oz = other_pallet.position
                ol, ow, oh = other_pallet.dimensions
                
                # Sprawdzenie, czy paleta znajduje się bezpośrednio na sprawdzanej palecie
                if (ox <= x < ox + ol or ox < x + l <= ox + ol) and \
                   (oy <= y < oy + ow or oy < y + w <= oy + ow) and \
                   z + pallet.height == oz:
                    
                    invalid_stacking.append(pallet.pallet_id)
                    break
    
    return invalid_stacking


def validate_loading(pallets: List[Pallet], trailer: Trailer = None) -> Dict[str, Any]:
    """
    Przeprowadza pełną walidację załadunku palet.
    
    Args:
        pallets: Lista załadowanych palet
        trailer: Naczepa (opcjonalnie)
        
    Returns:
        Dict: Słownik z wynikami walidacji
    """
    if trailer is None:
        trailer = Trailer()
    
    # Sprawdzenie kolizji
    collisions = check_collision(pallets)
    
    # Sprawdzenie rozkładu masy
    weight_distribution = check_weight_distribution(pallets, trailer)
    
    # Sprawdzenie wykorzystania przestrzeni
    space_utilization = check_space_utilization(pallets, trailer)
    
    # Sprawdzenie poprawności układania w stosy
    invalid_stacking = check_stacking_validity(pallets)
    
    # Sprawdzenie, czy palety mieszczą się w naczepie
    out_of_bounds_pallets = []
    for pallet in pallets:
        if not trailer._check_bounds(pallet):
            out_of_bounds_pallets.append(pallet.pallet_id)
    
    # Obliczenie łącznej masy załadunku
    total_weight = sum(pallet.total_weight for pallet in pallets)
    weight_exceeded = total_weight > trailer.max_load
    
    return {
        "valid": len(collisions) == 0 and weight_distribution["overall_valid"] and \
                 len(invalid_stacking) == 0 and len(out_of_bounds_pallets) == 0 and \
                 not weight_exceeded,
        "collisions": collisions,
        "weight_distribution": weight_distribution,
        "space_utilization": space_utilization,
        "invalid_stacking": invalid_stacking,
        "out_of_bounds": out_of_bounds_pallets,
        "weight": {
            "total": total_weight,
            "max_allowed": trailer.max_load,
            "exceeded": weight_exceeded
        }
    } 