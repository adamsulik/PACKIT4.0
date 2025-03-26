"""
Główny plik aplikacji PACKIT 4.0.
"""

import os
import sys

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State

# Dodanie katalogu głównego do ścieżki Pythona
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.visualization.dashboard import create_layout
from src.utils.data_loader import load_sample_data
from src.algorithms.algorithm_factory import get_algorithm
from src.visualization.plotter import plot_3d_trailer_with_pallets

# Inicjalizacja aplikacji Dash
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)
app.title = "PACKIT 4.0 - Optymalizacja załadunku palet"

# Ustawienie layoutu aplikacji
app.layout = create_layout()

# Załadowanie przykładowych danych
sample_pallets = load_sample_data()

# Definicja callbacków
@app.callback(
    Output("visualization-container", "children"),
    [Input("algorithm-dropdown", "value"),
     Input("run-algorithm-button", "n_clicks")],
    [State("pallet-list", "data")]
)
def update_visualization(algorithm_name, n_clicks, pallet_data):
    """Aktualizacja wizualizacji 3D po wybraniu algorytmu i kliknięciu przycisku."""
    if n_clicks is None or n_clicks == 0:
        return html.Div("Wybierz algorytm i kliknij 'Uruchom', aby zobaczyć wizualizację.")
    
    # Jeśli nie ma danych, użyj przykładowych
    pallets_to_load = pallet_data if pallet_data else sample_pallets
    
    # Uruchomienie wybranego algorytmu załadunku
    algorithm = get_algorithm(algorithm_name)
    loaded_pallets = algorithm.run(pallets_to_load)
    
    # Utworzenie wizualizacji 3D
    fig = plot_3d_trailer_with_pallets(loaded_pallets)
    
    return dcc.Graph(
        id="loading-visualization",
        figure=fig,
        style={"height": "80vh"}
    )

@app.callback(
    Output("algorithm-description", "children"),
    [Input("algorithm-dropdown", "value")]
)
def update_algorithm_description(algorithm_name):
    """Aktualizacja opisu algorytmu po jego wybraniu."""
    descriptions = {
        "XZ_Axis_Loading": "Metoda załadunku wzdłuż osi X oraz osi Z, która optymalizuje wykorzystanie przestrzeni naczepy.",
        "X_Distribution": "Algorytm załadunku w oparciu o rozkład X, który balansuje masę ładunku wzdłuż długości naczepy.",
        "Z_Distribution": "Algorytm załadunku w oparciu o rozkład Z, który optymalizuje stabilność ładunku.",
        "RL_Loading": "Zastosowanie uczenia ze wzmocnieniem do optymalizacji załadunku, dostosowując się do różnych scenariuszy."
    }
    
    return descriptions.get(algorithm_name, "Wybierz algorytm, aby zobaczyć jego opis.")

if __name__ == "__main__":
    app.run(debug=True) 