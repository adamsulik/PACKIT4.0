"""
Plik zawierający konfigurację i parametry dla symulacji załadunku palet.
"""

# Parametry naczepy standardowej (w mm)
TRAILER_CONFIG = {
    "length": 13600,  # Długość naczepy wewnątrz
    "width": 2450,    # Szerokość naczepy wewnątrz
    "height": 2700,   # Wysokość naczepy wewnątrz
    "max_load": 24000 # Maksymalna masa ładunku w kg
}

# Specyfikacja palet transportowych (w mm i kg)
PALLET_TYPES = {
    "EUR": {
        "length": 1200,
        "width": 800,
        "height": 144,
        "weight": 25,
        "max_stack_height": 2700, # Maksymalna wysokość składowania
        "color": "rgba(31, 119, 180, 0.7)"
    },
    "EUR2": {
        "length": 1200,
        "width": 1000,
        "height": 144,
        "weight": 30,
        "max_stack_height": 2700,
        "color": "rgba(255, 127, 14, 0.7)"
    },
    "INDUSTRIAL": {
        "length": 1200,
        "width": 1200,
        "height": 150,
        "weight": 35,
        "max_stack_height": 2700,
        "color": "rgba(44, 160, 44, 0.7)"
    },
    "HALF_EUR": {
        "length": 800,
        "width": 600,
        "height": 144,
        "weight": 15,
        "max_stack_height": 2700,
        "color": "rgba(214, 39, 40, 0.7)"
    }
}

# Ograniczenia przestrzenne i fizyczne
CONSTRAINTS = {
    "min_distance_between_pallets": 0,  # Minimalna odległość między paletami
    "weight_distribution_threshold": 0.1, # Maksymalna różnica w rozkładzie masy między lewą a prawą stroną (%)
    "front_to_back_weight_distribution": 0.6 # Procentowy rozkład masy przód-tył (60% z przodu)
}

# Parametry wizualizacji
VISUALIZATION = {
    "scene_padding": 500,  # Dodatkowa przestrzeń wokół naczepy w wizualizacji (mm)
    "camera_position": {"x": 1.5, "y": 1.5, "z": 1.5},
    "trailer_color": "rgba(200, 200, 200, 0.2)",
    "trailer_outline_color": "rgba(100, 100, 100, 1)"
}

# Domyślne ustawienia dla algorytmów
ALGORITHM_DEFAULTS = {
    "XZ_Axis_Loading": {
        "start_position": "front",  # Rozpoczęcie załadunku od przodu naczepy
        "prioritize_heavy_pallets": True  # Priorytetowanie cięższych palet
    },
    "X_Distribution": {
        "zones": 3,  # Liczba stref podziału wzdłuż osi X
        "balancing_factor": 0.8  # Współczynnik równoważenia masy
    },
    "Z_Distribution": {
        "zones": 2,  # Liczba stref podziału wzdłuż osi Z
        "balancing_factor": 0.7  # Współczynnik równoważenia masy
    },
    "Reinforcement_Learning": {
        "discount_factor": 0.95,
        "learning_rate": 0.001,
        "exploration_rate": 0.1
    }
} 