"""
Moduł zawierający funkcje do ładowania i zapisywania danych o paletach.
"""

import os
import json
import random
import uuid
from typing import List, Dict, Any

from src.data.pallet import Pallet
from src.config import PALLET_TYPES


def generate_pallet_sets() -> Dict[str, List[Pallet]]:
    """
    Generuje predefiniowane zestawy palet do testowania różnych algorytmów.
    
    Returns:
        Dict[str, List[Pallet]]: Słownik zawierający predefiniowane listy palet
    """
    pallet_sets = {}
    
    # Zestaw 1: Równomierny rozkład typów palet
    set1_pallets = []
    pallet_types = list(PALLET_TYPES.keys())
    for i in range(20):
        pallet_type = pallet_types[i % len(pallet_types)]
        specs = PALLET_TYPES[pallet_type]
        
        # Losowa masa ładunku między 50 a 500 kg
        cargo_weight = random.randint(50, 500)
        
        pallet = Pallet(
            pallet_id=f"S1_{uuid.uuid4().hex[:6]}",
            pallet_type=pallet_type,
            length=specs["length"],
            width=specs["width"],
            height=specs["height"],
            weight=specs["weight"],
            cargo_weight=cargo_weight,
            color=specs["color"],
            stackable=False,
            fragile=False,
        )
        
        set1_pallets.append(pallet)
    
    pallet_sets["Zestaw 1: Równomierny rozkład"] = set1_pallets
    
    # Zestaw 2: Duże palety z ciężkimi ładunkami
    set2_pallets = []
    large_pallet_types = ["L3", "L4", "L5", "L8", "L10"]
    
    for i in range(20):
        pallet_type = large_pallet_types[i % len(large_pallet_types)]
        specs = PALLET_TYPES[pallet_type]
        
        # Ciężkie ładunki między 300 a 800 kg
        cargo_weight = random.randint(300, 800)
        
        pallet = Pallet(
            pallet_id=f"S2_{uuid.uuid4().hex[:6]}",
            pallet_type=pallet_type,
            length=specs["length"],
            width=specs["width"],
            height=specs["height"],
            weight=specs["weight"],
            cargo_weight=cargo_weight,
            color=specs["color"],
            stackable=False,  # Ciężkie ładunki nie powinny być układane w stosy
            fragile=random.random() < 0.3,  # 30% szans na kruchy ładunek
        )
        
        set2_pallets.append(pallet)
    
    pallet_sets["Zestaw 2: Duże, ciężkie palety"] = set2_pallets
    
    # Zestaw 3: Małe palety z lekkimi ładunkami
    set3_pallets = []
    small_pallet_types = ["L1", "L2", "L7"]
    
    for i in range(20):
        pallet_type = small_pallet_types[i % len(small_pallet_types)]
        specs = PALLET_TYPES[pallet_type]
        
        # Lekkie ładunki między 50 a 200 kg
        cargo_weight = random.randint(50, 200)
        
        pallet = Pallet(
            pallet_id=f"S3_{uuid.uuid4().hex[:6]}",
            pallet_type=pallet_type,
            length=specs["length"],
            width=specs["width"],
            height=specs["height"],
            weight=specs["weight"],
            cargo_weight=cargo_weight,
            color=specs["color"],
            stackable=False,  # Lekkie ładunki też nie mogą być układane w stosy
            fragile=random.random() < 0.2,  # 20% szans na kruchy ładunek
        )
        
        set3_pallets.append(pallet)
    
    pallet_sets["Zestaw 3: Małe, lekkie palety"] = set3_pallets
    
    # Zestaw 4: Mieszane palety z różną wysokością i masą
    set4_pallets = []
    
    for i in range(20):
        pallet_type = random.choice(pallet_types)
        specs = PALLET_TYPES[pallet_type]
        
        # Zróżnicowane masy ładunków
        cargo_weight = random.randint(100, 600)
        
        pallet = Pallet(
            pallet_id=f"S4_{uuid.uuid4().hex[:6]}",
            pallet_type=pallet_type,
            length=specs["length"],
            width=specs["width"],
            height=specs["height"],
            weight=specs["weight"],
            cargo_weight=cargo_weight,
            color=specs["color"],
            stackable=False,  # Żadne palety nie mogą być układane w stosy
            fragile=random.random() < 0.25,  # 25% szans na kruchy ładunek
        )
        
        set4_pallets.append(pallet)
    
    pallet_sets["Zestaw 4: Mieszane palety"] = set4_pallets
    
    # Zestaw 5: Palety optymalizowane pod kątem LDM
    set5_pallets = []
    
    # Sortowanie typów palet według LDM (od najniższego)
    ldm_sorted_types = sorted(pallet_types, key=lambda t: PALLET_TYPES[t]["ldm"])
    
    for i in range(20):
        pallet_type = ldm_sorted_types[i % len(ldm_sorted_types)]
        specs = PALLET_TYPES[pallet_type]
        
        # Zróżnicowane masy ładunków
        cargo_weight = random.randint(100, 400)
        
        pallet = Pallet(
            pallet_id=f"S5_{uuid.uuid4().hex[:6]}",
            pallet_type=pallet_type,
            length=specs["length"],
            width=specs["width"],
            height=specs["height"],
            weight=specs["weight"],
            cargo_weight=cargo_weight,
            color=specs["color"],
            stackable=False,  # Wszystkie palety nie mogą być układane w stosy
            fragile=False,   # Żadna nie jest krucha
        )
        
        set5_pallets.append(pallet)
    
    pallet_sets["Zestaw 5: Optymalizacja LDM"] = set5_pallets
    
    return pallet_sets


def load_sample_data() -> List[Pallet]:
    """
    Ładuje przykładowe dane palet.
    
    Returns:
        List[Pallet]: Lista przykładowych palet
    """
    # Używamy pierwszego zestawu palet jako przykładowych danych
    return list(generate_pallet_sets().values())[0]


def load_pallets_from_file(filepath: str) -> List[Pallet]:
    """
    Ładuje dane o paletach z pliku JSON.
    
    Args:
        filepath: Ścieżka do pliku JSON
        
    Returns:
        List[Pallet]: Lista palet
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Nie znaleziono pliku: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        pallets_data = json.load(f)
    
    pallets = []
    for pallet_data in pallets_data:
        pallet = Pallet.from_dict(pallet_data)
        pallets.append(pallet)
    
    return pallets


def save_pallets_to_file(pallets: List[Pallet], filepath: str) -> None:
    """
    Zapisuje dane o paletach do pliku JSON.
    
    Args:
        pallets: Lista palet do zapisania
        filepath: Ścieżka do pliku JSON
    """
    pallets_data = [pallet.to_dict() for pallet in pallets]
    
    # Upewnij się, że katalog docelowy istnieje
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(pallets_data, f, indent=2, ensure_ascii=False)


def generate_test_dataset(num_pallets: int = 50, output_path: str = "data/test_pallets.json") -> None:
    """
    Generuje zestaw testowy palet i zapisuje go do pliku.
    
    Args:
        num_pallets: Liczba palet do wygenerowania
        output_path: Ścieżka do pliku wyjściowego
    """
    test_pallets = []
    pallet_types = list(PALLET_TYPES.keys())
    
    for i in range(num_pallets):
        # Losowy typ palety
        pallet_type = random.choice(pallet_types)
        specs = PALLET_TYPES[pallet_type]
        
        # Losowa masa ładunku między 50 a 1000 kg
        cargo_weight = random.randint(50, 1000)
        
        pallet = Pallet(
            pallet_id=f"TEST_{uuid.uuid4().hex[:8]}",
            pallet_type=pallet_type,
            length=specs["length"],
            width=specs["width"],
            height=specs["height"],
            weight=specs["weight"],
            cargo_weight=cargo_weight,
            color=specs["color"],
            stackable=random.random() > 0.2,
            fragile=random.random() < 0.3,
        )
        
        test_pallets.append(pallet)
    
    # Zapisz do pliku
    save_pallets_to_file(test_pallets, output_path)
    
    print(f"Wygenerowano {num_pallets} palet testowych i zapisano do {output_path}")


if __name__ == "__main__":
    # Przykład użycia
    generate_test_dataset(50, "data/test_pallets.json") 