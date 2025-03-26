"""
Moduł zawierający fabrykę algorytmów załadunku palet.
"""

from typing import Dict, Any, Optional

from src.algorithms.base_algorithm import LoadingAlgorithm
from src.algorithms.xz_axis_loading import XZAxisLoading
from src.algorithms.x_distribution import XDistributionLoading
from src.algorithms.y_distribution import YDistributionLoading
# Import algorytmu uczenia ze wzmocnieniem w przyszłości
# from src.algorithms.reinforcement_learning import ReinforcementLearningLoading


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
        "XZ_Axis_Loading": XZAxisLoading,
        "X_Distribution": XDistributionLoading,
        "Y_Distribution": YDistributionLoading,
        # "RL_Loading": ReinforcementLearningLoading
    }
    
    # Sprawdzenie, czy algorytm istnieje
    if algorithm_name not in algorithm_map:
        raise ValueError(f"Nieznany algorytm: {algorithm_name}. Dostępne algorytmy: {', '.join(algorithm_map.keys())}")
    
    # Utworzenie instancji algorytmu
    algorithm_class = algorithm_map[algorithm_name]
    return algorithm_class(config)


def list_available_algorithms() -> Dict[str, str]:
    """
    Zwraca listę dostępnych algorytmów wraz z ich opisami.
    
    Returns:
        Dict[str, str]: Słownik mapujący nazwy algorytmów na ich opisy
    """
    return {
        "XZ_Axis_Loading": "Metoda załadunku wzdłuż osi X oraz osi Z, która optymalizuje wykorzystanie przestrzeni naczepy.",
        "X_Distribution": "Algorytm załadunku w oparciu o rozkład X, który balansuje masę ładunku wzdłuż długości naczepy.",
        "Y_Distribution": "Algorytm załadunku w oparciu o rozkład Y, który optymalizuje układanie palet wzdłuż szerokości naczepy.",
        "RL_Loading": "Zastosowanie uczenia ze wzmocnieniem do optymalizacji załadunku, dostosowując się do różnych scenariuszy."
    } 