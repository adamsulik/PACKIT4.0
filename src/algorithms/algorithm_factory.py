"""
Moduł zawierający fabrykę algorytmów załadunku palet.
"""

from typing import Dict, Any, Optional

from src.algorithms.base_algorithm import LoadingAlgorithm
from src.algorithms.xy_axis_loading import XYAxisLoading
from src.algorithms.x_distribution import XDistributionLoading
from src.algorithms.y_distribution import YDistributionLoading
# Import algorytmu uczenia ze wzmocnieniem
from src.algorithms.reinforcement_learning import ReinforcementLearningLoading


def get_algorithm(algorithm_name: str, config: Optional[Dict[str, Any]] = None) -> LoadingAlgorithm:
    """
    Zwraca instancję algorytmu załadunku na podstawie nazwy.
    
    Args:
        algorithm_name: Nazwa algorytmu
        config: Konfiguracja algorytmu (opcjonalnie)
        
    Returns:
        LoadingAlgorithm: Instancja wybranego algorytmu
        
    Raises:
        ValueError: Gdy podana nazwa algorytmu jest nieznana
    """
    # Mapowanie nazw algorytmów do klas
    algorithm_map = {
        "XY_Axis_Loading": XYAxisLoading,
        "X_Distribution": XDistributionLoading,
        "Y_Distribution": YDistributionLoading,
        "RL_Loading": ReinforcementLearningLoading
    }
    
    # Sprawdzenie, czy algorytm istnieje
    if algorithm_name not in algorithm_map:
        raise ValueError(f"Nieznany algorytm: {algorithm_name}. Dostępne algorytmy: {', '.join(algorithm_map.keys())}")
    
    # Utworzenie instancji algorytmu
    algorithm_class = algorithm_map[algorithm_name]
    return algorithm_class(config)


def list_available_algorithms() -> Dict[str, str]:
    """
    Zwraca listę dostępnych algorytmów załadunku.
    
    Returns:
        Dict[str, str]: Słownik zawierający nazwę algorytmu i jego opis
    """
    algorithms = {
        "XY_Axis_Loading": "Metoda załadunku wzdłuż osi X oraz osi Y, która optymalizuje wykorzystanie przestrzeni naczepy.",
        "X_Distribution": "Metoda załadunku optymalizująca rozkład masy wzdłuż osi X naczepy.",
        "Y_Distribution": "Metoda załadunku optymalizująca rozkład masy wzdłuż osi Y naczepy.",
        "RL_Loading": "Metoda załadunku wykorzystująca algorytm uczenia ze wzmocnieniem (reinforcement learning)."
    }
    
    return algorithms 