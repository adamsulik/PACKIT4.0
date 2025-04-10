import matplotlib.pyplot as plt
from pathlib import Path

from typing import List, Dict, Any, Optional
from stable_baselines3 import PPO

from src.config import TRAILER_CONFIG
from src.algorithms.base_algorithm import LoadingAlgorithm
from src.data.pallet import Pallet
from src.algorithms.rl_approach import TrailerLoadingEnv

class ReinforcementLearningLoading(LoadingAlgorithm):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        default_config = {}  # ewentualne domyślne ustawienia
        merged_config = {**default_config, **(config or {})}
        super().__init__("RL Loading", merged_config)
        self.model = PPO.load(Path("models")/"ppo_trailer_loading_model")  # Wczytanie modelu

    def load_pallets(self, pallets: List[Pallet]) -> List[Pallet]:
        # Utworzenie środowiska RL z danymi palet
        env = TrailerLoadingEnv([pallets], TRAILER_CONFIG)
        obs, info = env.reset(seed=42)
        total_reward = 0
        done = False
        
        while not done:
            action, _ = self.model.predict(obs, deterministic=True)
            obs, reward, done, truncated, info = env.step(action)
            total_reward += reward
        
        print(env.trailer.loaded_pallets)

        return getattr(env, "loaded_pallets", [])
