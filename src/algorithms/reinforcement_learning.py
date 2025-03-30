"""
Moduł zawierający implementację algorytmu uczenia ze wzmocnieniem do optymalizacji załadunku palet.
"""

import random
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import os
import pickle
import time

from src.data.pallet import Pallet
from src.data.trailer import Trailer
from src.algorithms.base_algorithm import LoadingAlgorithm
from src.config import TRAILER_CONFIG, CONSTRAINTS


class ReinforcementLearningAgent:
    """
    Agent uczenia ze wzmocnieniem do optymalizacji załadunku palet.
    
    Agent wykorzystuje algorytm Q-learning do podejmowania decyzji
    o umieszczeniu palet w naczepie w celu maksymalizacji wykorzystania
    przestrzeni oraz zapewnienia właściwego rozkładu masy.
    
    Attributes:
        q_table: Tablica Q-wartości dla par stan-akcja
        learning_rate: Współczynnik uczenia (alfa)
        discount_factor: Współczynnik dyskontowania przyszłych nagród (gamma)
        exploration_rate: Prawdopodobieństwo eksploracji (epsilon)
        exploration_decay: Współczynnik zmniejszania eksploracji z czasem
        exploration_min: Minimalna wartość współczynnika eksploracji
        state_size: Rozmiar wektora stanu
        action_size: Liczba możliwych akcji
        training_episodes: Liczba epizodów treningowych
        model_path: Ścieżka do pliku modelu
    """
    
    def __init__(self, 
                 learning_rate: float = 0.1, 
                 discount_factor: float = 0.95, 
                 exploration_rate: float = 1.0, 
                 exploration_decay: float = 0.995, 
                 exploration_min: float = 0.01):
        """
        Inicjalizuje agenta RL.
        
        Args:
            learning_rate: Współczynnik uczenia (alfa)
            discount_factor: Współczynnik dyskontowania przyszłych nagród (gamma)
            exploration_rate: Początkowa wartość współczynnika eksploracji (epsilon)
            exploration_decay: Współczynnik zmniejszania eksploracji z czasem
            exploration_min: Minimalna wartość współczynnika eksploracji
        """
        self.q_table = {}  # Słownik zamiast tabeli dla ciągłej przestrzeni stanów
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.exploration_rate = exploration_rate
        self.exploration_decay = exploration_decay
        self.exploration_min = exploration_min
        
        # Parametry przestrzeni stanów i akcji
        self.state_size = 8  # Wymiary dyskretyzowanego stanu
        self.action_size = 6  # Możliwe akcje (x, y, z, rotacja)
        self.training_episodes = 0
        
        # Ścieżka do zapisywania/odczytywania modelu
        self.model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'rl_model.pkl')
    
    def get_state_representation(self, trailer: Trailer, pallet: Pallet) -> Tuple:
        """
        Tworzy dyskretną reprezentację stanu dla aktualnego stanu naczepy i palety.
        
        Args:
            trailer: Aktualny stan naczepy
            pallet: Paleta do załadowania
            
        Returns:
            Tuple: Krotka reprezentująca stan
        """
        # Obliczamy wypełnienie naczepy w różnych regionach
        space_utilization = trailer.get_loading_efficiency()["space_utilization"] / 100.0
        weight_balance_side = trailer.get_loading_efficiency()["weight_balance_side"]
        weight_balance_front_back = trailer.get_loading_efficiency()["weight_balance_front_back"]
        
        # Czynniki palety
        pallet_volume_ratio = pallet.volume / (trailer.length * trailer.width * trailer.height)
        pallet_weight_ratio = pallet.total_weight / trailer.max_load
        
        # Znormalizowane wymiary palety
        norm_length = pallet.length / trailer.length
        norm_width = pallet.width / trailer.width
        norm_height = pallet.height / trailer.height
        
        # Dyskretyzacja stanu
        state = (
            self._discretize(space_utilization, 5),
            self._discretize(weight_balance_side, 5),
            self._discretize(weight_balance_front_back, 5),
            self._discretize(pallet_volume_ratio, 5),
            self._discretize(pallet_weight_ratio, 5),
            self._discretize(norm_length, 3),
            self._discretize(norm_width, 3),
            self._discretize(norm_height, 3)
        )
        
        return state
    
    def _discretize(self, value: float, bins: int) -> int:
        """
        Dyskretyzuje wartość do określonej liczby przedziałów.
        
        Args:
            value: Wartość do dyskretyzacji
            bins: Liczba przedziałów
            
        Returns:
            int: Indeks przedziału
        """
        return min(int(value * bins), bins - 1)
    
    def get_action(self, state: Tuple, available_positions: List[Tuple[int, int, int]], 
                   rotation_options: List[int], training: bool = False) -> Tuple[Tuple[int, int, int], int]:
        """
        Wybiera akcję (pozycję i rotację) dla danego stanu.
        
        Args:
            state: Reprezentacja stanu
            available_positions: Lista dostępnych pozycji (x, y, z)
            rotation_options: Lista możliwych rotacji (0 lub 90)
            training: Czy agent jest w trybie treningowym
            
        Returns:
            Tuple: Wybrana pozycja (x, y, z) i rotacja
        """
        if not available_positions:
            return None, 0
        
        # Eksploracja: losowy wybór - przyspieszona
        if training and np.random.random() < self.exploration_rate:
            # Optymalizacja: szybszy losowy wybór dla dużych zestawów pozycji
            if len(available_positions) > 50:
                # Wybierz spośród podzbioru dostępnych pozycji dla przyspieszenia
                sample_size = min(20, len(available_positions))
                sampled_positions = random.sample(available_positions, sample_size)
                position = random.choice(sampled_positions)
            else:
                position = random.choice(available_positions)
                
            rotation = random.choice(rotation_options)
            return position, rotation
        
        # Eksploatacja: wybór najlepszej akcji - zoptymalizowana
        if state not in self.q_table:
            self.q_table[state] = {}
        
        # Optymalizacja: Ograniczenie liczby pozycji do sprawdzenia dla dużych zestawów
        positions_to_check = available_positions
        if len(available_positions) > 50 and not training:
            # Ograniczamy liczbę pozycji do sprawdzenia
            sample_size = min(30, len(available_positions))
            positions_to_check = random.sample(available_positions, sample_size)
        
        # Dla każdej możliwej akcji (pozycja + rotacja)
        best_q_value = float('-inf')
        best_action = (random.choice(available_positions), random.choice(rotation_options))
        
        # Sprawdzamy najpierw czy mamy już znane akcje dla tego stanu
        if len(self.q_table[state]) > 0:
            # Dla pozycji w naszym zbiorze do sprawdzenia
            for position in positions_to_check:
                for rotation in rotation_options:
                    action = (position, rotation)
                    action_key = str(action)
                    
                    # Jeśli akcja była już oceniana wcześniej
                    if action_key in self.q_table[state]:
                        q_value = self.q_table[state][action_key]
                        if q_value > best_q_value:
                            best_q_value = q_value
                            best_action = action
            
            # Jeśli znaleźliśmy akcję o dobrej wartości Q, zwróć ją
            if best_q_value > -0.1:  # Wartość progowa dla "dobrej" akcji
                return best_action
        
        # Jeśli nie znaleźliśmy dobrej akcji wśród znanych, inicjalizujemy nowe
        for position in positions_to_check:
            for rotation in rotation_options:
                action = (position, rotation)
                action_key = str(action)
                
                # Jeśli akcja nie ma jeszcze wartości Q, zainicjuj ją
                if action_key not in self.q_table[state]:
                    self.q_table[state][action_key] = 0.0
                
                # Wybierz akcję z najwyższą wartością Q
                if self.q_table[state][action_key] > best_q_value:
                    best_q_value = self.q_table[state][action_key]
                    best_action = action
        
        return best_action
    
    def update_q_table(self, state: Tuple, action: Tuple, reward: float, next_state: Tuple) -> None:
        """
        Aktualizuje tabelę Q-wartości na podstawie nagrody i następnego stanu.
        
        Args:
            state: Aktualny stan
            action: Wybrana akcja
            reward: Otrzymana nagroda
            next_state: Następny stan
        """
        # Konwersja akcji na string dla użycia jako klucz
        action_key = str(action)
        
        # Inicjalizacja Q-wartości jeśli nie istnieją
        if state not in self.q_table:
            self.q_table[state] = {}
        if action_key not in self.q_table[state]:
            self.q_table[state][action_key] = 0.0
        
        # Obliczenie maksymalnej Q-wartości dla następnego stanu
        if next_state in self.q_table:
            max_next_q = max(self.q_table[next_state].values()) if self.q_table[next_state] else 0
        else:
            max_next_q = 0
        
        # Aktualizacja Q-wartości
        self.q_table[state][action_key] += self.learning_rate * (
            reward + self.discount_factor * max_next_q - self.q_table[state][action_key]
        )
    
    def calculate_reward(self, trailer: Trailer, loaded_successfully: bool) -> float:
        """
        Oblicza nagrodę za wykonaną akcję.
        
        Args:
            trailer: Aktualny stan naczepy
            loaded_successfully: Czy paleta została pomyślnie załadowana
            
        Returns:
            float: Wartość nagrody
        """
        if not loaded_successfully:
            return -10.0  # Kara za nieudany załadunek
        
        # Podstawowa nagroda za pomyślny załadunek
        reward = 5.0
        
        # Nagroda za efektywność wykorzystania przestrzeni
        efficiency = trailer.get_loading_efficiency()
        reward += efficiency["space_utilization"] / 10.0
        
        # Nagroda za dobry rozkład masy
        weight_valid = trailer.is_weight_distribution_valid()
        if weight_valid["overall_valid"]:
            reward += 5.0
        else:
            # Kara za zły rozkład masy
            if not weight_valid["side_balanced"]:
                reward -= 2.0
            if not weight_valid["front_back_balanced"]:
                reward -= 2.0
        
        # Bonus za liczbę załadowanych palet
        reward += len(trailer.loaded_pallets) * 0.2
        
        # Sprawdzenie i kara za piętrowanie palet - modyfikacja
        stacked_pallets = self._count_stacked_pallets(trailer.loaded_pallets)
        if stacked_pallets > 0:
            reward -= stacked_pallets * 5.0  # Znacząca kara za piętrowanie
        
        return reward
    
    def _count_stacked_pallets(self, pallets: List[Pallet]) -> int:
        """
        Liczy ilość spiętrowanych palet.
        
        Args:
            pallets: Lista załadowanych palet
            
        Returns:
            int: Liczba spiętrowanych palet
        """
        if not pallets:
            return 0
            
        stacked_count = 0
        pallet_positions = {}
        
        # Grupuj palety według pozycji x,y
        for pallet in pallets:
            # Używamy atrybutów pozycji z obiektu Pallet
            pos_key = (pallet.position[0], pallet.position[1])  # Używamy tuple pozycji (x, y)
            if pos_key not in pallet_positions:
                pallet_positions[pos_key] = []
            pallet_positions[pos_key].append(pallet)
        
        # Sprawdź, czy mamy więcej niż jedną paletę na tej samej pozycji x,y
        for pos, pos_pallets in pallet_positions.items():
            if len(pos_pallets) > 1:
                stacked_count += len(pos_pallets) - 1  # Liczymy tylko dodatkowe palety
                
        return stacked_count
    
    def train(self, episodes: int, pallet_sets: List[List[Pallet]], 
              max_steps_per_episode: int = 100, save_interval: int = 50, 
              callback=None) -> Dict[str, List[float]]:
        """
        Przeprowadza trening agenta.
        
        Args:
            episodes: Liczba epizodów treningowych
            pallet_sets: Lista zestawów palet do treningu
            max_steps_per_episode: Maksymalna liczba kroków w jednym epizodzie
            save_interval: Co ile epizodów zapisywać model
            callback: Opcjonalna funkcja zwrotna do raportowania postępu
            
        Returns:
            Dict: Słownik z historią nagrody i efektywności
        """
        rewards_history = []
        efficiency_history = []
        
        # Zoptymalizowane: predefiniujemy rotacje dla szybszego dostępu
        rotation_options = [0, 90]
        
        # Zoptymalizowane: Ustaw rzadsze wywołania callbacka dla szybszego treningu
        callback_interval = min(10, max(1, episodes // 20))  # Co najmniej co 10 epizodów, ale częściej dla małej liczby epizodów
        
        # Zoptymalizowane: Rzadziej zapisuj model jeśli mamy dużo epizodów
        actual_save_interval = min(save_interval, max(10, episodes // 10))
        
        start_time = time.time()
        
        for episode in range(episodes):
            # Wybierz losowy zestaw palet
            pallets = random.choice(pallet_sets).copy()
            random.shuffle(pallets)  # Losowa kolejność palet
            
            # Zresetuj stan środowiska
            trailer = Trailer()
            total_reward = 0
            
            # Wykonaj kroki w epizodzie
            for step in range(min(len(pallets), max_steps_per_episode)):
                pallet = pallets[step]
                
                # Pobierz stan
                state = self.get_state_representation(trailer, pallet)
                
                # Pobierz dostępne pozycje
                available_positions = trailer.get_available_positions(pallet)
                
                # Wybierz akcję
                position, rotation = self.get_action(state, available_positions, rotation_options, training=True)
                
                # Wykonaj akcję
                loaded_successfully = False
                if position:
                    pallet.set_position(*position)
                    if pallet.rotation != rotation:
                        pallet.rotate()
                    loaded_successfully = trailer.add_pallet(pallet)
                
                # Oblicz nagrodę
                reward = self.calculate_reward(trailer, loaded_successfully)
                total_reward += reward
                
                # Pobierz następny stan
                if step < len(pallets) - 1:
                    next_pallet = pallets[step + 1]
                    next_state = self.get_state_representation(trailer, next_pallet)
                else:
                    next_state = state  # Ostatni stan w epizodzie
                
                # Aktualizuj tabelę Q
                self.update_q_table(state, (position, rotation), reward, next_state)
                
                # Jeśli nie udało się załadować, przejdź do następnej palety
                if not loaded_successfully:
                    continue
            
            # Aktualizacja współczynnika eksploracji
            self.exploration_rate = max(self.exploration_min, 
                                        self.exploration_rate * self.exploration_decay)
            
            # Zapisz historię
            rewards_history.append(total_reward)
            efficiency_history.append(trailer.get_loading_efficiency()["space_utilization"])
            
            # Raportowanie postępu - zoptymalizowane, aby było wywoływane rzadziej
            if callback and (episode % callback_interval == 0 or episode == episodes - 1):
                result = callback(episode, episodes, total_reward, self.exploration_rate, 
                        trailer.get_loading_efficiency())
                # Sprawdź czy callback zwrócił False (zatrzymanie treningu)
                if result is False:
                    print(f"Trening zatrzymany na epiziodzie {episode}/{episodes}")
                    break  # Przerwij trening
            
            # Zapisz model - rzadziej dla szybszego treningu
            if (episode + 1) % actual_save_interval == 0 or episode == episodes - 1:
                self.save_model()
                
            self.training_episodes += 1
            
            # Wyświetl postęp co 10% treningu
            if episode % max(1, episodes // 10) == 0 or episode == episodes - 1:
                elapsed = time.time() - start_time
                estimated_total = elapsed / (episode + 1) * episodes if episode > 0 else 0
                remaining = estimated_total - elapsed
                print(f"Trening: {episode + 1}/{episodes} ({(episode + 1)/episodes*100:.1f}%) " +
                      f"Czas: {elapsed:.1f}s, Pozostało: {remaining:.1f}s")
        
        # Zapisz finalny model
        self.save_model()
        
        print(f"Trening zakończony. Czas: {time.time() - start_time:.1f}s")
        
        return {
            "rewards": rewards_history,
            "efficiency": efficiency_history
        }
    
    def save_model(self) -> None:
        """Zapisuje model do pliku."""
        # Utwórz katalog, jeśli nie istnieje
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        
        # Zapisz model
        with open(self.model_path, 'wb') as f:
            pickle.dump({
                'q_table': self.q_table,
                'training_episodes': self.training_episodes,
                'exploration_rate': self.exploration_rate
            }, f)
    
    def load_model(self) -> bool:
        """
        Wczytuje model z pliku.
        
        Returns:
            bool: True jeśli model został wczytany pomyślnie, False w przeciwnym razie
        """
        if not os.path.exists(self.model_path):
            return False
        
        try:
            with open(self.model_path, 'rb') as f:
                data = pickle.load(f)
                self.q_table = data['q_table']
                self.training_episodes = data['training_episodes']
                self.exploration_rate = data['exploration_rate']
            return True
        except Exception as e:
            print(f"Błąd podczas wczytywania modelu: {e}")
            return False


class ReinforcementLearningLoading(LoadingAlgorithm):
    """
    Algorytm załadunku palet wykorzystujący uczenie ze wzmocnieniem.
    
    Attributes:
        agent: Agent uczenia ze wzmocnieniem
        training_mode: Czy algorytm jest w trybie treningowym
        visualization_callback: Funkcja zwrotna do wizualizacji procesu załadunku
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicjalizuje nowy algorytm załadunku oparty na RL.
        
        Args:
            config: Słownik konfiguracyjny algorytmu (opcjonalny)
        """
        super().__init__("RL_Loading", config)
        
        # Konfiguracja
        self.config = config or {}
        self.training_mode = self.config.get("training_mode", False)
        self.visualization_callback = self.config.get("visualization_callback", None)
        
        # Inicjalizacja agenta RL
        self.agent = ReinforcementLearningAgent(
            learning_rate=self.config.get("learning_rate", 0.1),
            discount_factor=self.config.get("discount_factor", 0.95),
            exploration_rate=self.config.get("exploration_rate", 0.1),
            exploration_decay=self.config.get("exploration_decay", 0.995),
            exploration_min=self.config.get("exploration_min", 0.01)
        )
        
        # Wczytaj model jeśli istnieje
        self.agent.load_model()
    
    def load_pallets(self, pallets: List[Pallet]) -> List[Pallet]:
        """
        Przeprowadza załadunek palet do naczepy za pomocą algorytmu uczenia ze wzmocnieniem.
        
        Args:
            pallets: Lista palet do załadunku
            
        Returns:
            List[Pallet]: Lista załadowanych palet z przypisanymi pozycjami
        """
        loaded_pallets = []
        rotation_options = [0, 90]  # Możliwe rotacje palety
        
        # Sortowanie palet według objętości (malejąco)
        pallets_to_load = self._sort_pallets_by_volume(pallets.copy())
        
        # Śledzenie zajętych pozycji na podłodze (zapobieganie piętrowaniu)
        occupied_floor_positions = set()
        
        for pallet in pallets_to_load:
            # Pobranie aktualnego stanu
            state = self.agent.get_state_representation(self.trailer, pallet)
            
            # Pobranie dostępnych pozycji z uwzględnieniem zajętych miejsc na podłodze
            available_positions = self.trailer.get_available_positions(pallet)
            
            # Filtrujemy pozycje, aby uniknąć piętrowania - tylko jeśli nie jesteśmy w trybie treningowym
            if not self.training_mode:
                available_positions = [pos for pos in available_positions if 
                                     (pos[0], pos[1]) not in occupied_floor_positions]
            
            if not available_positions:
                continue  # Brak dostępnych pozycji, przejdź do następnej palety
            
            # Wybór akcji (pozycji i rotacji)
            position, rotation = self.agent.get_action(state, available_positions, rotation_options)
            
            if not position:
                continue  # Nie udało się wybrać pozycji, przejdź do następnej palety
            
            # Ustawienie pozycji i rotacji palety
            pallet.set_position(*position)
            if pallet.rotation != rotation:
                pallet.rotate()
            
            # Próba dodania palety
            if self.trailer.add_pallet(pallet):
                loaded_pallets.append(pallet)
                
                # Dodaj pozycję do zajętych miejsc na podłodze (używamy x, y z pozycji)
                occupied_floor_positions.add((position[0], position[1]))
                
                # Wywołanie funkcji zwrotnej wizualizacji (jeśli istnieje)
                if self.visualization_callback:
                    self.visualization_callback(self.trailer, loaded_pallets)
                    # Krótkie opóźnienie dla lepszej wizualizacji procesu
                    if not self.training_mode:
                        time.sleep(0.2)
        
        return loaded_pallets
    
    def train(self, pallet_sets: List[List[Pallet]], episodes: int = 1000, 
              max_steps_per_episode: int = 100, save_interval: int = 50, 
              callback=None) -> Dict[str, List[float]]:
        """
        Przeprowadza trening agenta RL.
        
        Args:
            pallet_sets: Lista zestawów palet do treningu
            episodes: Liczba epizodów treningowych
            max_steps_per_episode: Maksymalna liczba kroków w jednym epizodzie
            save_interval: Co ile epizodów zapisywać model
            callback: Funkcja zwrotna do raportowania postępu
            
        Returns:
            Dict: Słownik z historią nagrody i efektywności
        """
        self.training_mode = True
        
        # Funkcja zwrotna do raportowania postępu
        def progress_callback(episode, total_episodes, reward, exploration_rate, efficiency):
            # Wywołaj przekazany callback
            if callback:
                result = callback(episode, total_episodes, reward, exploration_rate, efficiency)
                # Przekazujemy wartość zwróconą z głównego callbacka, jeśli istnieje
                if result is False:
                    return False
            # Wywołaj wizualizację, jeśli została skonfigurowana
            elif self.visualization_callback:
                self.visualization_callback(
                    episode=episode,
                    total_episodes=total_episodes,
                    reward=reward,
                    exploration_rate=exploration_rate,
                    efficiency=efficiency
                )
            return True
        
        # Przeprowadzenie treningu
        training_results = self.agent.train(
            episodes=episodes,
            pallet_sets=pallet_sets,
            max_steps_per_episode=max_steps_per_episode,
            save_interval=save_interval,
            callback=progress_callback
        )
        
        self.training_mode = False
        return training_results
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Zwraca informacje o modelu.
        
        Returns:
            Dict: Słownik z informacjami o modelu
        """
        return {
            "training_episodes": self.agent.training_episodes,
            "exploration_rate": self.agent.exploration_rate,
            "q_table_size": len(self.agent.q_table),
            "model_path": self.agent.model_path
        } 