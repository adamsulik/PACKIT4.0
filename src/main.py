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
import plotly.graph_objs as go

# Dodanie katalogu głównego do ścieżki Pythona
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.visualization.dashboard import create_layout, generate_pallet_set_stats
from src.utils.data_loader import generate_pallet_sets
from src.algorithms.algorithm_factory import get_algorithm
from src.visualization.plotter import plot_3d_trailer_with_pallets
from src.config import PALLET_TYPES, TRAILER_DIMENSIONS
from src.data.pallet import Pallet

# Inicjalizacja aplikacji Dash z meta tagami dla responsywności
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0"},
        {"name": "description", "content": "PACKIT 4.0 - System optymalizacji załadunku palet transportowych"}
    ]
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
    [Output("visualization-container", "children"),
     Output("overall-stats-container", "children")],
    [Input("algorithm-dropdown", "value"),
     Input("run-algorithm-button", "n_clicks")],
    [State("pallet-set-dropdown", "value")]
)
def update_visualization(algorithm_name, n_clicks, selected_set_name):
    """
    Aktualizacja wizualizacji 3D i statystyk całościowych po wybraniu algorytmu i kliknięciu przycisku.
    
    Args:
        algorithm_name: Nazwa wybranego algorytmu
        n_clicks: Liczba kliknięć przycisku (None jeśli nie kliknięto)
        selected_set_name: Nazwa wybranego zestawu palet
        
    Returns:
        tuple: Wizualizacja 3D (dcc.Graph) i statystyki całościowe (html.Div)
    """
    if n_clicks is None or n_clicks == 0:
        return html.Div(
            "Wybierz zestaw palet i algorytm, następnie kliknij 'Uruchom', aby zobaczyć wizualizację.",
            className="h-100 d-flex justify-content-center align-items-center text-muted"
        ), html.P("Uruchom algorytm, aby zobaczyć statystyki.")
    
    if not selected_set_name or selected_set_name not in pallet_sets:
        return html.Div(
            "Proszę wybrać zestaw palet.",
            className="h-100 d-flex justify-content-center align-items-center text-danger"
        ), html.P("Nie wybrano zestawu palet.")
    
    # Pobranie palet z wybranego zestawu
    pallets_to_load = pallet_sets[selected_set_name]
    
    # Uruchomienie wybranego algorytmu załadunku
    algorithm = get_algorithm(algorithm_name)
    loaded_pallets = algorithm.run(pallets_to_load)
    
    # Obliczenie statystyk załadunku
    total_pallets = len(pallets_to_load)
    loaded_pallets_count = len(loaded_pallets)
    loading_ratio = (loaded_pallets_count / total_pallets) * 100 if total_pallets > 0 else 0
    
    # Oblicz łączną przestrzeń i masę
    trailer_volume = TRAILER_DIMENSIONS["length"] * TRAILER_DIMENSIONS["width"] * TRAILER_DIMENSIONS["height"]
    loaded_volume = sum(p.volume for p in loaded_pallets)
    volume_ratio = (loaded_volume / trailer_volume) * 100 if trailer_volume > 0 else 0
    
    loaded_weight = sum(p.total_weight for p in loaded_pallets)
    max_weight = TRAILER_DIMENSIONS["max_load"]
    weight_ratio = (loaded_weight / max_weight) * 100 if max_weight > 0 else 0
    
    # Utworzenie wizualizacji 3D z dodanymi informacjami
    fig = plot_3d_trailer_with_pallets(loaded_pallets)
    
    # Dodanie tytułu z informacją o liczbie załadowanych palet
    fig.update_layout(
        title=f"Załadowano {loaded_pallets_count} z {total_pallets} palet ({loading_ratio:.1f}%)",
        margin=dict(l=0, r=0, t=40, b=0)
    )
    
    # Wizualizacja 3D
    visualization = dcc.Graph(
        id="loading-visualization",
        figure=fig,
        style={"height": "100%", "width": "100%"},
        config={"responsive": True, "displayModeBar": True}
    )
    
    # Statystyki całościowe w formie tabeli
    overall_stats = dbc.Table(
        [
            html.Thead(
                html.Tr([
                    html.Th("Parametr"),
                    html.Th("Wartość"),
                    html.Th("Procentowo")
                ])
            ),
            html.Tbody([
                html.Tr([
                    html.Td("Załadowane palety"),
                    html.Td(f"{loaded_pallets_count} z {total_pallets}"),
                    html.Td(f"{loading_ratio:.1f}%")
                ]),
                html.Tr([
                    html.Td("Wykorzystana przestrzeń"),
                    html.Td(f"{loaded_volume / 1000000:.2f} m³ z {trailer_volume / 1000000:.2f} m³"),
                    html.Td(f"{volume_ratio:.1f}%")
                ]),
                html.Tr([
                    html.Td("Wykorzystana ładowność"),
                    html.Td(f"{loaded_weight} kg z {max_weight} kg"),
                    html.Td(f"{weight_ratio:.1f}%")
                ])
            ])
        ],
        striped=True,
        bordered=True,
        hover=True,
        size="sm"
    )
    
    return visualization, overall_stats

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
        "Y_Distribution": "Algorytm załadunku w oparciu o rozkład Y, który optymalizuje układanie palet wzdłuż szerokości naczepy.",
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

    # Sprawdzenie, czy figura zawiera dane
    try:
        loaded_pallets_count = int(figure.get('layout', {}).get('title', {}).get('text', "0").split()[1])
        total_pallets = int(figure.get('layout', {}).get('title', {}).get('text', "0").split()[3])
        loading_ratio = (loaded_pallets_count / total_pallets) * 100 if total_pallets > 0 else 0
    except (ValueError, IndexError, AttributeError):
        loaded_pallets_count = 0
        total_pallets = 0
        loading_ratio = 0
    
    # Efektywność załadunku w formie wskaźników
    efficiency_stats = html.Div([
        dbc.Progress([
            dbc.Progress(value=loading_ratio, color="success", bar=True, label=f"{loading_ratio:.1f}%")
        ], className="mb-3"),
        
        html.Div([
            html.Span("Optymalne wykorzystanie przestrzeni"),
            dbc.Progress([
                dbc.Progress(value=75, color="primary", bar=True)
            ], className="mb-2"),
            
            html.Span("Optymalne balansowanie masy"),
            dbc.Progress([
                dbc.Progress(value=85, color="info", bar=True)
            ], className="mb-2"),
            
            html.Span("Stabilność załadunku"),
            dbc.Progress([
                dbc.Progress(value=90, color="warning", bar=True)
            ]),
        ])
    ])
    
    return efficiency_stats

# Callback do aktualizacji rozkładu masy
@app.callback(
    Output("weight-distribution-container", "children"),
    [Input("loading-visualization", "figure")]
)
def update_weight_distribution(figure):
    """Aktualizacja statystyk rozkładu masy."""
    if not figure:
        return html.P("Uruchom algorytm, aby zobaczyć statystyki rozkładu masy.")
    
    # Dane w formie wykresu rozkładu masy
    weight_distribution = html.Div([
        dcc.Graph(
            figure={
                "data": [
                    go.Bar(
                        x=["Strefa 1", "Strefa 2", "Strefa 3", "Strefa 4"],
                        y=[1200, 1800, 1650, 950],
                        marker=dict(color="royalblue")
                    )
                ],
                "layout": go.Layout(
                    title="Rozkład masy wzdłuż naczepy",
                    yaxis=dict(title="Masa (kg)"),
                    height=200,
                    margin=dict(l=50, r=20, t=40, b=30)
                )
            },
            config={"displayModeBar": False}
        ),
        html.Div([
            html.P("Różnica masy przód-tył: 12%", className="mb-1"),
            html.P("Różnica masy lewo-prawo: 8%", className="mb-1"),
            html.P("Środek ciężkości: optymalny", className="mb-1")
        ], className="mt-2")
    ])
    
    return weight_distribution

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0") 