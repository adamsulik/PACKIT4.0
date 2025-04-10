import numpy as np
import gymnasium as gym
import matplotlib.pyplot as plt
from stable_baselines3 import PPO
from pathlib import Path

from src.algorithms.rl_approach import TrailerLoadingEnv, get_pallets
from src.config import TRAILER_CONFIG

trailer_config = TRAILER_CONFIG

def run_inference():
    # Create images folder if it doesn't exist
    images_dir = Path.cwd() / "images"
    images_dir.mkdir(exist_ok=True)
    
    # Load the trained PPO model once
    model = PPO.load("ppo_trailer_loading_model.zip")

    num_runs = 5  # number of sample sets to visualize
    training_data_palletes = get_pallets(5)
    for run_idx in range(num_runs):
        # Generate a single sample set of pallets.
        idx = np.random.randint(0, len(training_data_palletes))
        training_data = [training_data_palletes[idx]]
        
        # Create the environment with the sample data.
        env = TrailerLoadingEnv(training_data, trailer_config)
        obs, info = env.reset(seed=42)
        
        done = False
        total_reward = 0
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, done, truncated, info = env.step(action)
            total_reward += reward

        print(f"Run {run_idx}: Episode completed. Total reward:", total_reward)
        
        # Override plt.show to avoid blocking and then save the resulting figure.
        original_show = plt.show
        plt.show = lambda: None
        
        env.render()
        image_path = images_dir / f"inference_run_{idx}.png"
        plt.savefig(image_path)
        plt.close("all")
        
        plt.show = original_show

if __name__ == '__main__':
    run_inference()
