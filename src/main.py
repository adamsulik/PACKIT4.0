"""
Główny plik aplikacji PACKIT 4.0.
"""

import os
import sys
import uuid
import time
import threading

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import pandas as pd
import plotly.graph_objs as go
import numpy as np

# Dodanie katalogu głównego do ścieżki Pythona
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.visualization.dashboard import (
    create_layout, 
    generate_pallet_set_stats, 
    create_rl_rewards_graph, 
    create_rl_model_status
)
from src.utils.data_loader import generate_pallet_sets
from src.algorithms.algorithm_factory import get_algorithm, list_available_algorithms
from src.visualization.plotter import plot_3d_trailer_with_pallets, create_3d_visualization, create_weight_distribution_plot
from src.config import PALLET_TYPES, TRAILER_DIMENSIONS
from src.data.pallet import Pallet
from src.algorithms.reinforcement_learning import ReinforcementLearningLoading

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

# Globalny stan aplikacji
app_state = {
    "rl_training_active": False,
    "rl_training_thread": None,
    "rl_rewards_history": [],
    "rl_efficiency_history": [],
    "rl_current_episode": 0,
    "rl_total_episodes": 0
}

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
    [Output("pallet-table", "data"),
     Output("pallet-set-stats", "children")],
    [Input("pallet-set-dropdown", "value")]
)
def update_pallet_set(pallet_set_name):
    """
    Aktualizuje tabelę palet i statystyki po wyborze zestawu.
    
    Args:
        pallet_set_name: Nazwa wybranego zestawu palet
        
    Returns:
        tuple: (dane tabeli, statystyki zestawu)
    """
    if not pallet_set_name or pallet_set_name not in pallet_sets:
        return [], html.P("Wybierz zestaw palet.")
    
    # Pobranie palet z wybranego zestawu
    pallets = pallet_sets[pallet_set_name]
    
    # Konwersja obiektów Pallet na słowniki dla tabeli
    pallet_data = [pallet_to_dict(pallet) for pallet in pallets]
    
    # Statystyki
    total_weight = sum(p.total_weight for p in pallets)
    total_volume = sum(p.volume for p in pallets)
    
    stats = html.Div([
        html.P(f"Liczba palet: {len(pallets)}", className="mb-1"),
        html.P(f"Łączna masa: {total_weight} kg", className="mb-1"),
        html.P(f"Łączna objętość: {total_volume / 1_000_000:.2f} m³", className="mb-1")
    ])
    
    return pallet_data, stats

@app.callback(
    Output("algorithm-description", "children"),
    Input("algorithm-dropdown", "value")
)
def update_algorithm_description(algorithm_name):
    """
    Aktualizuje opis wybranego algorytmu.
    
    Args:
        algorithm_name: Nazwa wybranego algorytmu
        
    Returns:
        str: Opis algorytmu
    """
    algorithms = list_available_algorithms()
    return algorithms.get(algorithm_name, "Brak opisu dla wybranego algorytmu.")

@app.callback(
    Output("rl-training-panel", "style"),
    Input("algorithm-dropdown", "value")
)
def toggle_rl_panel(algorithm_name):
    """
    Pokazuje lub ukrywa panel treningu RL w zależności od wybranego algorytmu.
    
    Args:
        algorithm_name: Nazwa wybranego algorytmu
        
    Returns:
        dict: Styl CSS dla panelu
    """
    if algorithm_name == "RL_Loading":
        return {"display": "block"}
    return {"display": "none"}

@app.callback(
    [
        Output("rl-model-status", "children"),
        Output("rl-rewards-graph", "figure")
    ],
    [Input("algorithm-dropdown", "value")],
    prevent_initial_call=True
)
def update_rl_model_info(algorithm_name):
    """
    Aktualizuje informacje o modelu RL.
    
    Args:
        algorithm_name: Nazwa wybranego algorytmu
        
    Returns:
        tuple: Status modelu i wykres nagród
    """
    if algorithm_name != "RL_Loading":
        raise PreventUpdate
    
    # Tworzenie instancji algorytmu
    algorithm = get_algorithm(algorithm_name)
    
    if not isinstance(algorithm, ReinforcementLearningLoading):
        return html.P("Nieprawidłowy typ algorytmu", className="mb-0"), create_rl_rewards_graph()
    
    # Pobieranie informacji o modelu
    model_info = algorithm.get_model_info()
    
    # Aktualizacja historii nagród
    if hasattr(app_state, "rl_rewards_history") and app_state["rl_rewards_history"]:
        return create_rl_model_status(model_info), create_rl_rewards_graph(app_state["rl_rewards_history"])
    
    return create_rl_model_status(model_info), create_rl_rewards_graph()

@app.callback(
    [
        Output("train-rl-button", "disabled"),
        Output("stop-rl-button", "disabled"),
        Output("rl-training-progress", "value"),
        Output("rl-training-progress", "label")
    ],
    [
        Input("train-rl-button", "n_clicks"),
        Input("stop-rl-button", "n_clicks")
    ],
    [
        State("rl-episodes-input", "value"),
        State("algorithm-dropdown", "value")
    ],
    prevent_initial_call=True
)
def handle_rl_training_buttons(
    train_clicks, 
    stop_clicks, 
    episodes, 
    algorithm_name
):
    """
    Obsługuje przyciski do treningu modelu RL.
    
    Args:
        train_clicks: Liczba kliknięć przycisku treningu
        stop_clicks: Liczba kliknięć przycisku zatrzymania
        episodes: Liczba epizodów treningowych
        algorithm_name: Nazwa wybranego algorytmu
        
    Returns:
        tuple: Stany przycisków i wartość paska postępu
    """
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if button_id == "train-rl-button" and not app_state["rl_training_active"]:
        # Rozpocznij trening w osobnym wątku
        start_rl_training(episodes, algorithm_name)
        return True, False, 0, "0%"
    
    elif button_id == "stop-rl-button" and app_state["rl_training_active"]:
        # Zatrzymaj trening
        app_state["rl_training_active"] = False
        if app_state["rl_training_thread"] and app_state["rl_training_thread"].is_alive():
            app_state["rl_training_thread"].join(timeout=1.0)
        
        progress = 100 if app_state["rl_current_episode"] >= app_state["rl_total_episodes"] else \
                  int((app_state["rl_current_episode"] / app_state["rl_total_episodes"]) * 100)
        
        return False, True, progress, f"{progress}% (Przerwano)"
    
    # Oblicz aktualny postęp
    if app_state["rl_training_active"]:
        progress = int((app_state["rl_current_episode"] / app_state["rl_total_episodes"]) * 100)
        return True, False, progress, f"{progress}%"
    else:
        return False, True, 100, "Gotowe"

# Callback do aktualizacji wizualizacji
@app.callback(
    [
        Output("visualization-container", "children"),
        Output("weight-distribution-container", "children"),
        Output("efficiency-container", "children"),
        Output("overall-stats-container", "children")
    ],
    Input("run-algorithm-button", "n_clicks"),
    [
        State("pallet-set-dropdown", "value"),
        State("algorithm-dropdown", "value")
    ],
    prevent_initial_call=True
)
def run_algorithm(n_clicks, pallet_set_name, algorithm_name):
    """
    Uruchamia wybrany algorytm załadunku i aktualizuje wizualizacje.
    
    Args:
        n_clicks: Liczba kliknięć przycisku
        pallet_set_name: Nazwa wybranego zestawu palet
        algorithm_name: Nazwa wybranego algorytmu
        
    Returns:
        tuple: Komponenty wizualizacji
    """
    if not n_clicks or not pallet_set_name or not algorithm_name:
        raise PreventUpdate
    
    # Pobieranie zestawu palet
    pallets = pallet_sets.get(pallet_set_name, []).copy()
    
    # Tworzenie instancji algorytmu
    algorithm = get_algorithm(algorithm_name)
    
    # Mierzenie czasu wykonania
    start_time = time.time()
    
    # Uruchomienie algorytmu
    if isinstance(algorithm, ReinforcementLearningLoading):
        # Dla RL wyłączamy callback, żeby nie spowalniać wizualizacji
        algorithm.config["visualization_callback"] = None
        
        # Wyłączamy tryb treningowy, aby używać wyuczonego modelu
        algorithm.training_mode = False
    
    # Uruchomienie algorytmu
    try:
        loaded_pallets = algorithm.run(pallets)
        end_time = time.time()
        
        # Zapisz czas wykonania
        algorithm.run_time = end_time - start_time
        
        # Wizualizacja 3D
        visualization_fig = create_3d_visualization(algorithm.trailer, loaded_pallets)
        visualization = dcc.Graph(
            id="loading-visualization-3d",
            figure=visualization_fig,
            style={"height": "65vh"},
            config={"responsive": True, "displayModeBar": True}
        )
        
        # Wykres rozkładu masy
        weight_distribution_fig = create_weight_distribution_plot(algorithm.trailer)
        weight_distribution = dcc.Graph(
            id="weight-distribution-plot",
            figure=weight_distribution_fig,
            config={"displayModeBar": False}
        )
        
        # Efektywność załadunku
        efficiency = algorithm.get_statistics()
        efficiency_component = html.Div([
            html.Div([
                html.Label("Wykorzystanie przestrzeni:"),
                dbc.Progress(
                    value=efficiency["efficiency"]["space_utilization"],
                    color="success",
                    className="mb-3",
                    label=f"{efficiency['efficiency']['space_utilization']:.1f}%"
                )
            ]),
            html.Div([
                html.Label("Wykorzystanie ładowności:"),
                dbc.Progress(
                    value=efficiency["efficiency"]["weight_utilization"],
                    color="info",
                    className="mb-3",
                    label=f"{efficiency['efficiency']['weight_utilization']:.1f}%"
                )
            ]),
            html.Div([
                html.Label("Balans boczny:"),
                dbc.Progress(
                    value=efficiency["efficiency"]["weight_balance_side"] * 100,
                    color="warning" if abs(efficiency["efficiency"]["weight_balance_side"] - 0.5) > 0.1 else "success",
                    className="mb-3",
                    label=f"{efficiency['efficiency']['weight_balance_side']:.2f}"
                )
            ]),
            html.Div([
                html.Label("Balans przód-tył:"),
                dbc.Progress(
                    value=efficiency["efficiency"]["weight_balance_front_back"] * 100,
                    color="warning" if abs(efficiency["efficiency"]["weight_balance_front_back"] - 0.6) > 0.1 else "success",
                    className="mb-0",
                    label=f"{efficiency['efficiency']['weight_balance_front_back']:.2f}"
                )
            ])
        ])
        
        # Statystyki ogólne
        overall_stats = html.Div([
            html.P(f"Załadowano palet: {len(loaded_pallets)} z {len(pallets)}", className="mb-2"),
            html.P(f"Palet na m³: {efficiency['efficiency']['pallets_per_cubic_meter']:.2f}", className="mb-2"),
            html.P(f"Rozkład masy: {'✓ Poprawny' if algorithm.trailer.is_weight_distribution_valid()['overall_valid'] else '✗ Niepoprawny'}", 
                className="mb-2 text-success" if algorithm.trailer.is_weight_distribution_valid()['overall_valid'] else "mb-2 text-danger"),
            html.Hr(className="my-2"),
            html.P(f"Algorytm: {algorithm.name}", className="font-weight-bold mb-2"),
            html.P(f"Czas wykonania: {algorithm.run_time:.2f} s", className="mb-0")
        ])
        
        return visualization, weight_distribution, efficiency_component, overall_stats
    except Exception as e:
        print(f"Błąd podczas uruchamiania algorytmu: {e}")
        # W przypadku błędu zwracamy puste komponenty
        return html.Div(f"Wystąpił błąd: {str(e)}"), html.Div(), html.Div(), html.Div()

def start_rl_training(episodes, algorithm_name):
    """
    Rozpoczyna trening modelu RL w osobnym wątku.
    
    Args:
        episodes: Liczba epizodów treningowych
        algorithm_name: Nazwa algorytmu
    """
    # Resetowanie stanu
    app_state["rl_training_active"] = True
    app_state["rl_rewards_history"] = []
    app_state["rl_efficiency_history"] = []
    app_state["rl_current_episode"] = 0
    app_state["rl_total_episodes"] = episodes
    
    # Utworzenie funkcji treningowej
    def training_job():
        # Pobieranie danych treningowych
        training_sets = list(pallet_sets.values())
        
        # Tworzenie instancji algorytmu z konfiguracją treningową
        config = {
            "exploration_rate": 1.0,  # Wyższy exploration_rate dla treningu
            "training_mode": True,    # Ustaw tryb treningowy
            "learning_rate": 0.2,     # Szybsze uczenie dla krótkich treningów
            "discount_factor": 0.95,  # Standardowy współczynnik dyskontowania
            "exploration_decay": 0.99 # Wolniejszy spadek eksploracji dla lepszego uczenia
        }
        algorithm = get_algorithm(algorithm_name, config)
        
        if not isinstance(algorithm, ReinforcementLearningLoading):
            app_state["rl_training_active"] = False
            return
        
        # Optymalizacja: Dodajemy limit czasu dla treningu
        max_training_time = 300  # Maksymalnie 5 minut treningu
        start_time = time.time()
        
        # Funkcja zwrotna do aktualizacji postępu
        def custom_callback(episode, total_episodes, reward, exploration_rate, efficiency):
            # Aktualizuj stan aplikacji
            app_state["rl_current_episode"] = episode
            app_state["rl_rewards_history"].append(reward)
            app_state["rl_efficiency_history"].append(efficiency["space_utilization"])
            
            # Wyświetl informacje
            print(f"Epizod {episode}/{total_episodes}, nagroda: {reward:.2f}, eksploracja: {exploration_rate:.4f}, wykorzystanie: {efficiency['space_utilization']:.2f}%")
            
            # Sprawdzenie czy trening został zatrzymany przez użytkownika lub przekroczono limit czasu
            if not app_state["rl_training_active"] or (time.time() - start_time > max_training_time):
                if time.time() - start_time > max_training_time:
                    print(f"Trening przerwany ze względu na przekroczenie limitu czasu ({max_training_time}s)")
                    app_state["rl_training_active"] = False  # Zatrzymaj trening
                return False  # Sygnalizuj zatrzymanie treningu
            return True
        
        # Uruchomienie treningu z bezpośrednim przekazaniem callback
        try:
            # Dostosuj parametry treningu do liczby epizodów dla przyspieszenia
            save_interval = max(10, min(50, episodes // 5))  # Rzadziej zapisuj model dla dużej liczby epizodów
            algorithm.train(
                pallet_sets=training_sets,
                episodes=episodes,
                max_steps_per_episode=100,
                save_interval=save_interval,
                callback=custom_callback
            )
        except Exception as e:
            print(f"Błąd podczas treningu: {e}")
        finally:
            app_state["rl_training_active"] = False
    
    # Uruchomienie wątku treningowego z wyższym priorytetem
    app_state["rl_training_thread"] = threading.Thread(target=training_job)
    app_state["rl_training_thread"].daemon = True
    app_state["rl_training_thread"].start()


# Uruchomienie aplikacji
if __name__ == "__main__":
    app.run(debug=True) 