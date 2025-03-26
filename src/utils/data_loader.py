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


def load_sample_data() -> List[Pallet]:
    """
    Generuje przykładowe dane o paletach do testowania.
    
    Returns:
        List[Pallet]: Lista przykładowych palet
    """
    sample_pallets = []
    
    # Generowanie różnych typów palet
    for pallet_type, specs in PALLET_TYPES.items():
        for i in range(random.randint(3, 10)):
            cargo_weight = random.randint(50, 800)  # Losowa masa ładunku
            
            pallet = Pallet(
                pallet_id=f"{pallet_type}_{uuid.uuid4().hex[:8]}",
                pallet_type=pallet_type,
                length=specs["length"],
                width=specs["width"],
                height=specs["height"],
                weight=specs["weight"],
                cargo_weight=cargo_weight,
                color=specs["color"],
                stackable=random.random() > 0.2,  # 80% palet może być układana w stosy
                fragile=random.random() < 0.3,    # 30% palet ma kruchy ładunek
            )
            
            sample_pallets.append(pallet)
    
    return sample_pallets


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