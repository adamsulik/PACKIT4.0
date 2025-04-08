import time
import random
import uuid
from src.algorithms.rl_approach import TrailerLoadingEnv
from src.data.pallet import Pallet
from src.config import PALLET_TYPES


def main():
    # Utwórz trzy palety używając podanego podejścia
    set1_pallets = []
    pallet_types = list(PALLET_TYPES.keys())
    for i in range(3):
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
    
    # Utwórz scenariusz: lista trzech palet
    scenario = set1_pallets
    training_data = [scenario]  # opakowujemy w listę scenariuszy

    # Konfiguracja naczepy (podobnie jak w innych plikach)
    trailer_config = {
        "length": 13000,  # mm
        "width": 2450,
        "height": 2700,
        "max_load": 24000,
    }
    
    # Inicjalizacja środowiska
    env = TrailerLoadingEnv(training_data, trailer_config)
    obs, _ = env.reset()

    done = False
    step_count = 0

    # Wykonujemy kroki do momentu zakończenia epizodu
    while not done:
        # Akcja: wybierz pierwszą paletę oraz target_y=0, aby wybrać pozycję z minimalnym x.
        action = [0.0, 0.0]
        obs, reward, done, truncated, info = env.step(action)
        print(f"Krok {step_count}: reward={reward}")
        step_count += 1
        time.sleep(0.5)  # krótka pauza dla czytelności outputu

    # Wizualizacja końcowego stanu naczepy
    env.render()

if __name__ == "__main__":
    main()
