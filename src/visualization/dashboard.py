"""
Moduł zawierający komponenty interfejsu użytkownika dla aplikacji Dash.
"""

from typing import Dict, List, Any

import dash
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State

from src.config import PALLET_TYPES
from src.utils.data_loader import generate_pallet_sets


# Pobierz nazwy zestawów palet
PALLET_SET_NAMES = list(generate_pallet_sets().keys())


def create_layout() -> html.Div:
    """
    Tworzy główny layout aplikacji.
    
    Returns:
        html.Div: Kontener z layoutem aplikacji
    """
    return html.Div([
        # Nagłówek
        html.Div([
            html.H1("PACKIT 4.0 - Optymalizacja załadunku palet", className="display-4 text-center"),
            html.Hr(),
            html.P(
                "System do optymalizacji załadunku palet transportowych z wykorzystaniem metod uczenia maszynowego",
                className="lead text-center"
            )
        ], className="jumbotron p-3 mb-4"),
        
        # Główny kontener
        dbc.Container([
            dbc.Row([
                # Panel kontrolny po lewej
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("Panel sterowania", className="text-center")),
                        dbc.CardBody([
                            # Wybór zestawu palet
                            html.H5("Wybierz zestaw palet:", className="mb-2"),
                            dcc.Dropdown(
                                id="pallet-set-dropdown",
                                options=[
                                    {"label": name, "value": name}
                                    for name in PALLET_SET_NAMES
                                ],
                                value=PALLET_SET_NAMES[0] if PALLET_SET_NAMES else None,
                                clearable=False,
                                className="mb-4"
                            ),
                            
                            # Wybór algorytmu
                            html.H5("Wybierz metodę załadunku:", className="mb-2"),
                            dcc.Dropdown(
                                id="algorithm-dropdown",
                                options=[
                                    {"label": "Załadunek wzdłuż osi X i Z", "value": "XZ_Axis_Loading"},
                                    {"label": "Załadunek w oparciu o rozkład X", "value": "X_Distribution"},
                                    {"label": "Załadunek w oparciu o rozkład Y", "value": "Y_Distribution"},
                                    {"label": "Uczenie ze wzmocnieniem", "value": "RL_Loading"}
                                ],
                                value="XZ_Axis_Loading",
                                clearable=False,
                                className="mb-4"
                            ),
                            
                            # Opis wybranego algorytmu
                            html.Div(id="algorithm-description", className="alert alert-info mb-4"),
                            
                            # Przycisk uruchomienia algorytmu
                            dbc.Button(
                                "Uruchom algorytm",
                                id="run-algorithm-button",
                                color="primary",
                                className="mb-4 w-100"
                            ),
                            
                            # Lista palet w zestawie
                            html.H5("Palety w zestawie:", className="mb-2"),
                            dash_table.DataTable(
                                id='pallet-table',
                                columns=[
                                    {"name": "ID", "id": "pallet_id"},
                                    {"name": "Typ", "id": "pallet_type"},
                                    {"name": "Wymiary (mm)", "id": "dimensions"},
                                    {"name": "Masa (kg)", "id": "weight"},
                                    {"name": "Ładunek (kg)", "id": "cargo_weight"},
                                    {"name": "Stackable", "id": "stackable"},
                                    {"name": "Fragile", "id": "fragile"}
                                ],
                                data=[],
                                page_size=5,
                                style_cell={
                                    'whiteSpace': 'normal',
                                    'height': 'auto',
                                    'textAlign': 'left',
                                    'fontSize': '12px',
                                    'padding': '5px'
                                },
                                style_data_conditional=[
                                    {
                                        'if': {'row_index': 'odd'},
                                        'backgroundColor': 'rgb(248, 248, 248)'
                                    }
                                ],
                                style_header={
                                    'backgroundColor': 'rgb(230, 230, 230)',
                                    'fontWeight': 'bold',
                                    'fontSize': '12px',
                                    'padding': '5px'
                                },
                                style_table={'overflowX': 'auto'}
                            ),
                            
                            # Statystyki zestawu palet
                            html.H5("Statystyki zestawu:", className="mt-4 mb-2"),
                            html.Div(id="pallet-set-stats", className="mb-2")
                        ])
                    ], className="h-100 shadow")
                ], xs=12, sm=12, md=4, lg=3, xl=3, className="mb-4"),
                
                # Wizualizacja na środku
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("Wizualizacja załadunku", className="text-center")),
                        dbc.CardBody([
                            html.Div(id="visualization-container", style={"height": "70vh"})
                        ])
                    ], className="h-100 shadow")
                ], xs=12, sm=12, md=8, lg=9, xl=9, className="mb-4")
            ]),
            
            # Statystyki pod wizualizacją ułożone poziomo
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("Rozkład masy", className="text-center")),
                        dbc.CardBody([
                            html.Div(id="weight-distribution-container")
                        ])
                    ], className="h-100 shadow")
                ], xs=12, sm=12, md=4, className="mb-4"),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("Efektywność załadunku", className="text-center")),
                        dbc.CardBody([
                            html.Div(id="efficiency-container")
                        ])
                    ], className="h-100 shadow")
                ], xs=12, sm=12, md=4, className="mb-4"),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("Statystyki całościowe", className="text-center")),
                        dbc.CardBody([
                            html.Div(id="overall-stats-container")
                        ])
                    ], className="h-100 shadow")
                ], xs=12, sm=12, md=4, className="mb-4")
            ])
        ], fluid=True, className="mb-5")
    ])


def create_pallet_controls() -> html.Div:
    """
    Tworzy panel kontrolny do zarządzania widocznością palet w wizualizacji 3D.
    
    Returns:
        html.Div: Panel kontrolny
    """
    return html.Div([
        html.H5("Kontrola widoczności palet:"),
        dbc.Card([
            dbc.CardBody([
                html.Div(id="pallet-visibility-controls")
            ])
        ])
    ])


def generate_pallet_visibility_controls(pallets: List[Dict[str, Any]]) -> List[dbc.Checklist]:
    """
    Generuje kontrolki do przełączania widoczności palet w wizualizacji 3D.
    
    Args:
        pallets: Lista załadowanych palet
        
    Returns:
        List[dbc.Checklist]: Lista kontrolek dla palet
    """
    controls = []
    
    # Grupowanie palet według typu
    pallet_types = {}
    for pallet in pallets:
        pallet_type = pallet["pallet_type"]
        if pallet_type not in pallet_types:
            pallet_types[pallet_type] = []
        pallet_types[pallet_type].append(pallet)
    
    # Tworzenie kontrolek dla każdego typu palet
    for pallet_type, type_pallets in pallet_types.items():
        controls.append(
            dbc.Checklist(
                options=[
                    {"label": f"{pallet_type} ({len(type_pallets)} palet)", "value": pallet_type}
                ],
                value=[pallet_type],
                id=f"visibility-{pallet_type}",
                switch=True,
                className="mb-2"
            )
        )
    
    return controls


def generate_pallet_set_stats(pallets: List[Dict[str, Any]]) -> html.Div:
    """
    Generuje statystyki dla zestawu palet.
    
    Args:
        pallets: Lista palet
        
    Returns:
        html.Div: Statystyki zestawu palet
    """
    if not pallets:
        return html.P("Brak danych o paletach.")
    
    # Obliczenie statystyk
    total_pallets = len(pallets)
    total_weight = sum(p.get('cargo_weight', 0) + p.get('weight', 0) for p in pallets)
    total_ldm = sum(PALLET_TYPES[p.get('pallet_type', '')].get('ldm', 0) for p in pallets)
    
    # Liczba palet według typu
    pallet_types_count = {}
    for p in pallets:
        pallet_type = p.get('pallet_type', '')
        if pallet_type not in pallet_types_count:
            pallet_types_count[pallet_type] = 0
        pallet_types_count[pallet_type] += 1
    
    # Tworzenie komponentu statystyk w formie tabeli
    stats_table = dbc.Table(
        [
            html.Thead(
                html.Tr([
                    html.Th("Parametr"),
                    html.Th("Wartość")
                ])
            ),
            html.Tbody([
                html.Tr([html.Td("Liczba palet"), html.Td(f"{total_pallets}")]),
                html.Tr([html.Td("Łączna masa"), html.Td(f"{total_weight} kg")]),
                html.Tr([html.Td("Łączny LDM"), html.Td(f"{total_ldm:.2f}")])
            ])
        ],
        striped=True,
        bordered=True,
        hover=True,
        size="sm",
        className="mb-0"
    )
    
    # Dodanie wykresu typu palet
    pallet_types_stats = html.Div([
        html.H6("Rozkład typów palet:", className="mt-3 mb-2"),
        dbc.Table(
            [
                html.Thead(
                    html.Tr([
                        html.Th("Typ"),
                        html.Th("Ilość")
                    ])
                ),
                html.Tbody([
                    html.Tr([html.Td(ptype), html.Td(count)])
                    for ptype, count in pallet_types_count.items()
                ])
            ],
            striped=True,
            bordered=True,
            hover=True,
            size="sm",
            className="mb-0"
        )
    ])
    
    return html.Div([stats_table, pallet_types_stats]) 