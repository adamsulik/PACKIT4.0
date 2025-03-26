"""
Plik zawierający konfigurację i parametry dla symulacji załadunku palet.
"""

# Parametry naczepy standardowej (w mm)
TRAILER_CONFIG = {
    "length": 13620,  # Długość naczepy wewnątrz (1362 cm)
    "width": 2450,    # Szerokość naczepy wewnątrz (245 cm)
    "height": 2940,   # Wysokość naczepy wewnątrz (294 cm)
    "max_load": 24000 # Maksymalna masa ładunku w kg
}

# Alias dla TRAILER_CONFIG, używany w interfejsie
TRAILER_DIMENSIONS = TRAILER_CONFIG

# Specyfikacja palet transportowych (w mm i kg)
PALLET_TYPES = {
    "L1": {
        "length": 1400,
        "width": 720,
        "height": 950,
        "weight": 36,
        "ldm": 0.42,
        "color": "rgb(31, 119, 180)"
    },
    "L2": {
        "length": 1200,
        "width": 720,
        "height": 950,
        "weight": 34,
        "ldm": 0.36,
        "color": "rgb(255, 127, 14)"
    },
    "L3": {
        "length": 1800,
        "width": 620,
        "height": 1220,
        "weight": 50,
        "ldm": 0.47,
        "color": "rgb(44, 160, 44)"
    },
    "L4": {
        "length": 2250,
        "width": 720,
        "height": 1220,
        "weight": 58,
        "ldm": 0.67,
        "color": "rgb(214, 39, 40)"
    },
    "L5": {
        "length": 2150,
        "width": 710,
        "height": 1730,
        "weight": 100,
        "ldm": 0.64,
        "color": "rgb(148, 103, 189)"
    },
    "L7": {
        "length": 1300,
        "width": 370,
        "height": 450,
        "weight": 20,
        "ldm": 0.20,
        "color": "rgb(140, 86, 75)"
    },
    "L8": {
        "length": 2400,
        "width": 620,
        "height": 1420,
        "weight": 60,
        "ldm": 0.62,
        "color": "rgb(227, 119, 194)"
    },
    "L10": {
        "length": 2870,
        "width": 790,
        "height": 1460,
        "weight": 110,
        "ldm": 0.94,
        "color": "rgb(127, 127, 127)"
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
    "trailer_color": "rgba(220, 220, 230, 0.3)",
    "trailer_outline_color": "rgba(50, 50, 120, 1)"
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
    "Y_Distribution": {
        "zones": 2,  # Liczba stref podziału wzdłuż osi Y
        "balancing_factor": 0.7  # Współczynnik równoważenia masy
    },
    "Reinforcement_Learning": {
        "discount_factor": 0.95,
        "learning_rate": 0.001,
        "exploration_rate": 0.1
    }
} 