"""
Główny moduł aplikacji Dash z logiką obsługi interfejsu i wizualizacji.
"""

import os
import json
import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State, ClientsideFunction
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import plotly.graph_objs as go
import threading
import time
from typing import Dict, List, Any, Optional, Tuple

from src.visualization.dashboard import (
    create_layout, 
    create_rl_rewards_graph, 
    create_rl_model_status
)
from src.visualization.plotter import create_3d_visualization, create_weight_distribution_plot
from src.utils.data_loader import generate_pallet_sets
from src.algorithms.algorithm_factory import get_algorithm, list_available_algorithms
from src.algorithms.reinforcement_learning import ReinforcementLearningLoading


# Inicjalizacja aplikacji Dash
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)
server = app.server

# Ustawienie tytułu
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

# Ustawienie layoutu
app.layout = create_layout()


# Callbacks

@app.callback(
    Output("algorithm-description", "children"),
    Input("algorithm-dropdown", "value")
)
def update_algorithm_description(algorithm_name: str) -> str:
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
def toggle_rl_panel(algorithm_name: str) -> Dict[str, str]:
    """
    Pokazuje lub ukrywa panel treningu RL w zależności od wybranego algorytmu.
    
    Args:
        algorithm_name: Nazwa wybranego algorytmu
        
    Returns:
        Dict: Styl CSS dla panelu
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
def update_rl_model_info(algorithm_name: str) -> Tuple[html.Div, go.Figure]:
    """
    Aktualizuje informacje o modelu RL.
    
    Args:
        algorithm_name: Nazwa wybranego algorytmu
        
    Returns:
        Tuple: Status modelu i wykres nagród
    """
    if algorithm_name != "RL_Loading":
        raise PreventUpdate
    
    # Tworzenie instancji algorytmu
    algorithm = get_algorithm(algorithm_name)
    
    if not isinstance(algorithm, ReinforcementLearningLoading):
        return html.P("Nieprawidłowy typ algorytmu", className="mb-0"), {}
    
    # Pobieranie informacji o modelu
    model_info = algorithm.get_model_info()
    
    # Aktualizacja historii nagród
    fig = create_rl_rewards_graph(app_state["rl_rewards_history"] if app_state.get("rl_rewards_history") else None)
    
    return create_rl_model_status(model_info), fig


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
    train_clicks: int, 
    stop_clicks: int, 
    episodes: int, 
    algorithm_name: str
) -> Tuple[bool, bool, int, str]:
    """
    Obsługuje przyciski do treningu modelu RL.
    
    Args:
        train_clicks: Liczba kliknięć przycisku treningu
        stop_clicks: Liczba kliknięć przycisku zatrzymania
        episodes: Liczba epizodów treningowych
        algorithm_name: Nazwa wybranego algorytmu
        
    Returns:
        Tuple: Stany przycisków i wartość paska postępu
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


@app.callback(
    [
        Output("pallet-table", "data"),
        Output("pallet-set-stats", "children")
    ],
    Input("pallet-set-dropdown", "value")
)
def update_pallet_set(pallet_set_name: str) -> Tuple[List[Dict[str, Any]], html.Div]:
    """
    Aktualizuje tabelę palet i statystyki po wyborze zestawu.
    
    Args:
        pallet_set_name: Nazwa wybranego zestawu palet
        
    Returns:
        Tuple: Dane do tabeli i statystyki
    """
    if not pallet_set_name:
        raise PreventUpdate
    
    # Pobieranie zestawu palet
    pallet_sets = generate_pallet_sets()
    pallets = pallet_sets.get(pallet_set_name, [])
    
    # Formatowanie danych do tabeli
    table_data = []
    for pallet in pallets:
        table_data.append({
            "pallet_id": pallet.pallet_id,
            "pallet_type": pallet.pallet_type,
            "dimensions": f"{pallet.length} x {pallet.width} x {pallet.height}",
            "weight": pallet.weight,
            "cargo_weight": pallet.cargo_weight,
            "stackable": "Tak" if pallet.stackable else "Nie",
            "fragile": "Tak" if pallet.fragile else "Nie"
        })
    
    # Statystyki
    total_weight = sum(p.total_weight for p in pallets)
    total_volume = sum(p.volume for p in pallets)
    
    stats = html.Div([
        html.P(f"Liczba palet: {len(pallets)}", className="mb-1"),
        html.P(f"Łączna masa: {total_weight} kg", className="mb-1"),
        html.P(f"Łączna objętość: {total_volume / 1_000_000:.2f} m³", className="mb-1")
    ])
    
    return table_data, stats


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
def run_algorithm(n_clicks: int, pallet_set_name: str, algorithm_name: str) -> Tuple[dcc.Graph, dcc.Graph, html.Div, html.Div]:
    """
    Uruchamia wybrany algorytm załadunku i aktualizuje wizualizacje.
    
    Args:
        n_clicks: Liczba kliknięć przycisku
        pallet_set_name: Nazwa wybranego zestawu palet
        algorithm_name: Nazwa wybranego algorytmu
        
    Returns:
        Tuple: Komponenty wizualizacji
    """
    if not n_clicks or not pallet_set_name or not algorithm_name:
        raise PreventUpdate
    
    # Pobieranie zestawu palet
    pallet_sets = generate_pallet_sets()
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
            html.P(f"Czas wykonania: {algorithm.run_time:.2f} s" if hasattr(algorithm, 'run_time') else "", className="mb-0")
        ])
        
        return visualization, weight_distribution, efficiency_component, overall_stats
    except Exception as e:
        print(f"Błąd podczas uruchamiania algorytmu: {e}")
        # W przypadku błędu zwracamy puste komponenty
        return html.Div(f"Wystąpił błąd: {str(e)}"), html.Div(), html.Div(), html.Div()


def start_rl_training(episodes: int, algorithm_name: str) -> None:
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
        pallet_sets = generate_pallet_sets()
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
        
        # Callback do aktualizacji postępu
        def progress_callback(episode, total_episodes, reward, exploration_rate, efficiency):
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
        
        # Uruchomienie treningu
        try:
            # Dostosuj parametry treningu do liczby epizodów dla przyspieszenia
            save_interval = max(10, min(50, episodes // 5))  # Rzadziej zapisuj model dla dużej liczby epizodów
            algorithm.train(
                pallet_sets=training_sets,
                episodes=episodes,
                max_steps_per_episode=100,
                save_interval=save_interval,
                callback=progress_callback
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
    app.run_server(debug=True) 