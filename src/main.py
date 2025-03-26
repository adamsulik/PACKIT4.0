"""
Główny plik aplikacji PACKIT 4.0.
"""

import os
import sys
import uuid

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import pandas as pd

# Dodanie katalogu głównego do ścieżki Pythona
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.visualization.dashboard import create_layout, generate_pallet_set_stats
from src.utils.data_loader import generate_pallet_sets
from src.algorithms.algorithm_factory import get_algorithm
from src.visualization.plotter import plot_3d_trailer_with_pallets
from src.config import PALLET_TYPES
from src.data.pallet import Pallet

# Inicjalizacja aplikacji Dash
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)
app.title = "PACKIT 4.0 - Optymalizacja załadunku palet"

# Ustawienie layoutu aplikacji
app.layout = create_layout()

# Załadowanie predefiniowanych zestawów palet
pallet_sets = generate_pallet_sets()

# Funkcja pomocnicza do konwersji obiektu Pallet na słownik dla tabeli
def pallet_to_dict(pallet: Pallet) -> dict:
    """
    Konwertuje obiekt Pallet na słownik dla tabeli danych.
    
    Args:
        pallet: Obiekt Pallet
        
    Returns:
        dict: Słownik z danymi palety
    """
    dimensions = f"{pallet.length}x{pallet.width}x{pallet.height}"
    
    return {
        "pallet_id": pallet.pallet_id,
        "pallet_type": pallet.pallet_type,
        "dimensions": dimensions,
        "weight": pallet.weight,
        "cargo_weight": pallet.cargo_weight,
        "stackable": "Tak" if pallet.stackable else "Nie",
        "fragile": "Tak" if pallet.fragile else "Nie"
    }

# Callback do aktualizacji tabeli palet na podstawie wybranego zestawu
@app.callback(
    Output("pallet-table", "data"),
    [Input("pallet-set-dropdown", "value")]
)
def update_pallet_table(selected_set_name):
    """
    Aktualizuje tabelę palet na podstawie wybranego zestawu.
    
    Args:
        selected_set_name: Nazwa wybranego zestawu palet
        
    Returns:
        list: Lista słowników z danymi palet
    """
    if not selected_set_name or selected_set_name not in pallet_sets:
        return []
    
    # Pobranie palet z wybranego zestawu
    pallets = pallet_sets[selected_set_name]
    
    # Konwersja obiektów Pallet na słowniki dla tabeli
    pallet_data = [pallet_to_dict(pallet) for pallet in pallets]
    
    return pallet_data

# Callback do aktualizacji statystyk zestawu palet
@app.callback(
    Output("pallet-set-stats", "children"),
    [Input("pallet-table", "data")]
)
def update_pallet_set_stats(pallet_data):
    """
    Aktualizuje statystyki zestawu palet.
    
    Args:
        pallet_data: Dane o paletach z tabeli
        
    Returns:
        html.Div: Komponent z statystykami
    """
    return generate_pallet_set_stats(pallet_data)

# Callback do aktualizacji wizualizacji
@app.callback(
    Output("visualization-container", "children"),
    [Input("algorithm-dropdown", "value"),
     Input("run-algorithm-button", "n_clicks")],
    [State("pallet-set-dropdown", "value")]
)
def update_visualization(algorithm_name, n_clicks, selected_set_name):
    """Aktualizacja wizualizacji 3D po wybraniu algorytmu i kliknięciu przycisku."""
    if n_clicks is None or n_clicks == 0:
        return html.Div("Wybierz zestaw palet i algorytm, następnie kliknij 'Uruchom', aby zobaczyć wizualizację.")
    
    if not selected_set_name or selected_set_name not in pallet_sets:
        return html.Div("Proszę wybrać zestaw palet.")
    
    # Pobranie palet z wybranego zestawu
    pallets_to_load = pallet_sets[selected_set_name]
    
    # Uruchomienie wybranego algorytmu załadunku
    algorithm = get_algorithm(algorithm_name)
    loaded_pallets = algorithm.run(pallets_to_load)
    
    # Utworzenie wizualizacji 3D
    fig = plot_3d_trailer_with_pallets(loaded_pallets)
    
    # Obliczenie statystyk załadunku
    total_pallets = len(pallets_to_load)
    loaded_pallets_count = len(loaded_pallets)
    loading_efficiency = (loaded_pallets_count / total_pallets) * 100 if total_pallets > 0 else 0
    
    # Dodanie tytułu z informacją o liczbie załadowanych palet
    fig.update_layout(
        title=f"Załadowano {loaded_pallets_count} z {total_pallets} palet ({loading_efficiency:.1f}%)"
    )
    
    return dcc.Graph(
        id="loading-visualization",
        figure=fig,
        style={"height": "80vh"}
    )

# Callback do aktualizacji opisu algorytmu
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

# Callback do aktualizacji efektywności załadunku
@app.callback(
    Output("efficiency-container", "children"),
    [Input("loading-visualization", "figure")]
)
def update_efficiency(figure):
    """Aktualizacja statystyk efektywności załadunku."""
    if not figure:
        return html.P("Uruchom algorytm, aby zobaczyć statystyki efektywności.")
    
    # Przykładowe statystyki - w przyszłości można rozbudować
    return html.Div([
        html.P("Statystyki efektywności załadunku:"),
        html.Ul([
            html.Li("Wykorzystanie przestrzeni: 78%"),
            html.Li("Wykorzystanie ładowności: 65%"),
            html.Li("Średni LDM na paletę: 0.52")
        ])
    ])

# Callback do aktualizacji rozkładu masy
@app.callback(
    Output("weight-distribution-container", "children"),
    [Input("loading-visualization", "figure")]
)
def update_weight_distribution(figure):
    """Aktualizacja statystyk rozkładu masy."""
    if not figure:
        return html.P("Uruchom algorytm, aby zobaczyć statystyki rozkładu masy.")
    
    # Przykładowe statystyki - w przyszłości można rozbudować
    return html.Div([
        html.P("Statystyki rozkładu masy:"),
        html.Ul([
            html.Li("Różnica masy przód-tył: 12%"),
            html.Li("Różnica masy lewo-prawo: 8%"),
            html.Li("Środek ciężkości: optymalny")
        ])
    ])

if __name__ == "__main__":
    app.run(debug=True) 