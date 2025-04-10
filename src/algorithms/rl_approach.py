import numpy as np
import random
import gymnasium as gym       # modified import
from gymnasium import spaces   # modified import
import matplotlib.pyplot as plt
from tqdm import tqdm
from pathlib import Path

from stable_baselines3 import PPO   # changed from DQN to PPO
from stable_baselines3.common.callbacks import BaseCallback

from src.data.pallet import Pallet
from src.data.trailer import Trailer
from src.config import PALLET_TYPES, TRAILER_CONFIG
from src.utils import generate_pallet_sets
import argparse

# Założenia algorytmu:
# - training_data to lista scenariuszy (lista palet) do załadowania.
# - Liczba typów palet jest ograniczona (PALLET_TYPES).
# - Akcja definiowana jest jako [choose, place]:
#     * choose: wybierz jedną z niezaładowanych palet i usuń ją z listy.
#     * place: wybierz wartość (0,1) i przemnóż przez szerokość naczepy,
#              aby określić docelową pozycję. Paleta zostanie wsunięta do ostatniego
#              wolnego miejsca, o ile nie wystąpi kolizja.
# - Rotacja palety nie jest uwzględniana.
# - Obserwacja uwzględnia m.in. stan naczepy i liczbę pozostałych palet (inventory).
# - Nie dopuszczamy układania palet jeden na drugim (osi Z).
# - Jeśli paleta nie zmieści się lub zostanie złamany warunek rozkładu masy,
#   brak jest przyznawanej nagrody.

# Ustalony porządek typów – klucze posortowane alfabetycznie:
PALLET_TYPE_ORDER = sorted(PALLET_TYPES.keys())


class TrailerLoadingEnv(gym.Env):
    """
    Środowisko symulujące załadunek naczepy paletami.
    
    Ulepszenia:
      - Obserwacja zawiera wektor stanowiący liczbę niezaładowanych palet dla poszczególnych typów.
      - Środowisko umożliwia trenowanie na wielu (np. 20) różnych listach palet.
      - Wewnętrznie korzysta z obiektu Trailer (z metodami _check_bounds, _check_collision, etc.)
    
    Akcja (Box(2)):
      - a[0]: wybór palety (skalowanie do rozmiaru listy palet dostępnych w danej liście)
      - a[1]: wybór pozycji x w naczepie (jako ułamek szerokości naczepy)
    """
    def __init__(self, training_data, trailer_config):
        """
        training_data: lista list palet. Każdy element (lista palet) reprezentuje jeden scenariusz załadunku.
        trailer_config: słownik konfiguracyjny dla obiektu Trailer.
        """
        super(TrailerLoadingEnv, self).__init__()
        
        self.trailer_config = trailer_config
        self.trailer = Trailer(**trailer_config)
        self.training_data = training_data  # lista scenariuszy do trenowania
        # Lista wszystkich palet do załadunku wybrana dla bieżącego epizodu
        self.all_pallets = []
        self.unloaded_pallets = []
        self.loaded_pallets = []
        
        # Akcja to wektor 2-elementowy z wartościami ciągłymi [0, 1]
        self.action_space = spaces.Box(low=0, high=1, shape=(2,), dtype=np.float32)
        
        # Obserwacja składa się z:
        # - 3 elementy jak wcześniej (np. occupancy, mass_util, znormalizowana liczba palet)
        # - Dodatkowo vector o wymiarze równym liczbie typów palet (ile każdego typu pozostało)
        obs_vector_length = 5 + len(PALLET_TYPE_ORDER)
        self.observation_space = spaces.Box(low=0, high=1, shape=(obs_vector_length,), dtype=np.float32)
        
        self.current_episode = 0
        self.reset()

    def reset(self, seed=None, options=None):  # modified signature to accept seed and options
        """
        Resetuje środowisko: wybiera losowo jeden scenariusz z training_data, resetuje trailer oraz inwentarz palet.
        """
        self.trailer.reset()
        scenario = random.choice(self.training_data)
        if not isinstance(scenario, list):
            scenario = [scenario]
        self.all_pallets = scenario.copy()
        self.unloaded_pallets = self.all_pallets.copy()
        self.loaded_pallets = []
        self.update_inventory()
        return self._get_observation(), {}  # modified to return info dict

    def update_inventory(self):
        """
        Aktualizuje wektor inwentarza (liczba niezaładowanych palet dla każdego typu).
        Zakładamy, że obiekty Pallet posiadają pole pallet_type.
        """
        self.inventory = np.zeros(len(PALLET_TYPE_ORDER), dtype=np.float32)
        for pallet in self.unloaded_pallets:
            idx = PALLET_TYPE_ORDER.index(pallet.pallet_type)
            self.inventory[idx] += 1

    def _get_observation(self):
        """
        Konstruuje obserwację środowiska.
        Elementy:
          - occupancy: wykorzystanie przestrzeni naczepy (wartość [0,1])
          - mass_util: wykorzystanie ładowności (wartość [0,1])
          - num_remaining: liczba pozostałych palet (znormalizowana)
          - inventory: wektor liczby palet każdego typu (znormalizowany do maksymalnej liczby palet danego typu obserwowanych w treningu)
        """
        efficiency = self.trailer.get_loading_efficiency()  # powinna zwracać m.in. "space_utilization", "load_utilization"
        occupancy = efficiency.get("space_utilization", 0.0)
        mass_util = efficiency.get("load_utilization", 0.0)
        weight_balance_side = efficiency.get("weight_balance_side", 0.0)
        weight_balance_front_back = efficiency.get("weight_balance_front", 0.0)
        num_remaining = len(self.unloaded_pallets) / len(self.all_pallets)

        # Normalizacja inwentarza – zakładamy, że maksymalna liczba jakiegokolwiek typu palet w treningu nie przekroczy np. 20.
        norm_inventory = self.inventory / 20.0
        obs = np.concatenate(([occupancy, mass_util, num_remaining, weight_balance_side, weight_balance_front_back], norm_inventory))
        return obs.astype(np.float32)

    def step(self, action):
        """
        Wykonanie akcji:
          - a[0]: wybór palety (skalowany do liczby palet w unlaoded_pallets)
          - a[1]: wybór pozycji y w naczepie (jako ułamek szerokości naczepy)
        Reguły:
          - Jeżeli lista unloaded_pallets pusta => episode done.
          - Jeśli pozycja wybrana dla palety jest nieprawidłowa (kolizja, poza granicami, złamanie warunku rozkładu masy),
            przyznawana jest kara (-10) i paleta NIE jest ładowana.
          - W przeciwnym razie paleta jest ładowana i przyznawana jest nagroda zależna od efektywności załadunku.
        """
        done = False
        reward = 0
        info = {}
        
        # Koniec epizodu, gdy nie ma więcej palet do załadunku.
        if len(self.unloaded_pallets) == 0:
            done = True
            return self._get_observation(), reward, done, False, info  # modified for gymnasium
        
        # Dekodowanie akcji:
        # a[0]: wybór palety – skalujemy wartość do rozmiaru listy niezaładowanych palet.
        pallet_index = int(action[0] * len(self.unloaded_pallets))
        pallet_index = np.clip(pallet_index, 0, len(self.unloaded_pallets) - 1)
        selected_pallet = self.unloaded_pallets.pop(pallet_index)
        
        # a[1]: wybór pozycji y – przeliczony jako ułamek szerokości naczepy.
        target_y = action[1] * self.trailer.width
        
        # Pobierz dostępne pozycje dla palety
        available_positions = self.trailer.get_available_positions(selected_pallet, stacking=False)
        valid_position = None
        if available_positions:
            # Sortuj wg odległości od target_y, a następnie wg najmniejszego x
            sorted_positions = sorted(available_positions, key=lambda pos: (abs(pos[1] - target_y), pos[0]))
            for pos in sorted_positions:
                selected_pallet.set_position(*pos)
                # Sprawdź, czy pozycja mieści się w obrębie naczepy i nie powoduje kolizji
                if self.trailer._check_bounds(selected_pallet) and not self.trailer._check_collision(selected_pallet):
                    valid_position = pos
                    break
        
        if valid_position is None:
            reward = -1000
        else:
            selected_pallet.set_position(*valid_position)
            self.trailer.add_pallet(selected_pallet)
            self.loaded_pallets.append(selected_pallet)
            efficiency = self.trailer.get_loading_efficiency().get('space_utilization', 0.0) 
            efficiency += self.trailer.get_loading_efficiency().get('weight_utilization', 0.0)
            # reward = efficiency * 100
            reward = 10 * efficiency * (1 - len(self.unloaded_pallets) / len(self.all_pallets))

        # Aktualizacja inwentarza.
        self.update_inventory()
        
        if len(self.unloaded_pallets) == 0:
            balance_validation = self.trailer.is_weight_distribution_valid()
            if not balance_validation['overall_valid']:
                reward -= 50 * int(balance_validation['side_balanced'])
                reward -= 50 * int(balance_validation['front_back_balanced'])
            done = True
        
        return self._get_observation(), reward, done, False, info  # modified to include truncated flag

    def _parse_color(self, color):
        # Konwertuje format "rgb(r, g, b)" na tuple RGBA
        if isinstance(color, str) and color.startswith("rgb("):
            parts = color[4:-1].split(',')
            r, g, b = [int(x.strip())/255.0 for x in parts]
            return (r, g, b, 1.0)
        return color

    def render(self, mode="human"):
        """
        Wizualizacja stanu naczepy.
        Możemy tutaj użyć dowolnej biblioteki graficznej.
        Przykładowo, rysujemy prostokątną reprezentację naczepy i zaznaczamy umieszczone palety.
        """
        # Wypisanie w terminalu informacji o załadowanych paletach
        print("Załadowane palety:")
        for pallet in self.trailer.loaded_pallets:
            print(pallet)
            
        # Prosty przykład wizualizacji przy użyciu matplotlib.
        plt.figure(figsize=(10, 4))
        plt.title("Widok naczepy")
        # Rysujemy obrys naczepy
        plt.gca().add_patch(plt.Rectangle((0, 0), self.trailer.width, self.trailer.length, fill=False, edgecolor="black"))
        for pallet in self.trailer.loaded_pallets:
            # Rysujemy paletę jako prostokąt
            pos = pallet.position  # zakładamy, że pozycja to (x, y, z)
            # Konwersja koloru, jeśli potrzebna
            color = PALLET_TYPES[pallet.pallet_type]["color"]
            color = self._parse_color(color)
            rect = plt.Rectangle((pos[1], pos[0]), pallet.width, pallet.length,
                                 color=color, alpha=0.7)
            plt.gca().add_patch(rect)
        plt.xlim(0, self.trailer.width)
        plt.ylim(0, self.trailer.length)
        plt.xlabel("Szerokość [mm]")
        plt.ylabel("Długość [mm]")
        plt.show()


# -----------------------------------------------------------------------------
# Przykładowy szkic treningu z wykorzystaniem PPO (stable-baselines3)
# -----------------------------------------------------------------------------
def get_pallets(num_of_all_sets: int = 1):
    """
    Generates and returns a list of pallets by combining multiple sets of pallet data.
    This function calls `generate_pallet_sets` to create pallet sets, extracts the 
    pallet data from each set, and combines them into a single list. It is useful 
    for scenarios where multiple sets of pallets need to be processed or analyzed.
    Args:
        num_of_all_sets (int): The number of pallet sets to generate. Defaults to 1.
    Returns:
        list: A list containing all pallets from the generated sets.
    """
    final_palletes = []
    for i in range(num_of_all_sets):    
        palletes = generate_pallet_sets()
        palletes = [palletes[key] for key in palletes.keys()]
        final_palletes.extend(palletes)
    return final_palletes
    # return [final_palletes[0]] # !! Overfitting parameter for testing purposes
    
if __name__ == '__main__':

    # Definicja argumentów z linii poleceń
    parser = argparse.ArgumentParser(description="Trening modelu PPO dla środowiska TrailerLoadingEnv.")
    parser.add_argument('-t', "--time_steps", type=int, default=10000, help="Liczba kroków treningowych (timesteps).")
    parser.add_argument('-n', "--num_pallet_sets", type=int, default=10, help="Liczba zestawów palet do wygenerowania.")
    parser.add_argument("--model-savedir", type=Path, default=Path("models")/"ppo_trailer_loading_model", help="Ścieżka do katalogu, w którym zapisany będzie model.")
    args = parser.parse_args()

    # Pobranie wartości argumentów
    total_timesteps = args.time_steps
    num_pallet_sets = args.num_pallet_sets

    # Zmodyfikowany callback z zapisem epizodowych nagród jako metryki adaptacji
    class TrainProgressCallback(BaseCallback):
        def __init__(self, total_timesteps, verbose=0):
            super(TrainProgressCallback, self).__init__(verbose)
            self.total_timesteps = total_timesteps
            self.pbar = None
            self.episode_rewards = []  # suma nagród z zakończonych epizodów

        def _on_training_start(self) -> None:
            self.pbar = tqdm(total=self.total_timesteps, desc="Trening modelu")

        def _on_step(self) -> bool:
            self.pbar.update(1)
            # Pobieramy informację o zakończeniu epizodu, jeśli dostępna
            infos = self.locals.get("infos")
            if infos is not None:
                for info in infos:
                    if "episode" in info:
                        self.episode_rewards.append(info["episode"]["r"])
            if self.num_timesteps >= self.total_timesteps:
                return False
            return True

        def _on_training_end(self) -> None:
            if self.pbar is not None:
                self.pbar.close()
            plt.figure()
            plt.plot(self.episode_rewards, label="Episode Rewards", alpha=0.6)
            plt.xlabel("Numer epizodu")
            plt.ylabel("Suma nagród epizodowych")
            plt.title("Ewolucja adaptacji modelu (nagroda epizodowa) w czasie")
            plt.legend()
            plt.show()

    # Generujemy 20 różnych zestawów palet.
    training_data = get_pallets(num_pallet_sets)
    
    # Konfiguracja naczepy (Trailer)
    trailer_config = TRAILER_CONFIG
    
    # Inicjalizacja środowiska
    env = TrailerLoadingEnv(training_data, trailer_config)
    
    # Konfiguracja modelu PPO z biblioteką stable-baselines3
    # Zmiana: dodanie policy_kwargs do ustawienia głębszej sieci neuronowej [128, 64, 32]
    model = PPO("MlpPolicy", env, policy_kwargs=dict(net_arch=[128, 64, 32]), verbose=1)
    
    # Ustal całkowitą liczbę timestepów i utwórz callback z paskiem progresu.
    progress_callback = TrainProgressCallback(total_timesteps=total_timesteps)
    
    # Wywołanie metody learn z callbackiem
    model.learn(total_timesteps=total_timesteps, callback=progress_callback)
    
    # Zapis modelu do pliku:
    model.save(args.model_savedir)
