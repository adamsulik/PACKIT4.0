"""
Moduł zawierający komponenty interfejsu użytkownika dla aplikacji Dash.
"""

from typing import Dict, List, Any

import dash
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State

from src.config import PALLET_TYPES


def create_layout() -> html.Div:
    """
    Tworzy główny layout aplikacji.
    
    Returns:
        html.Div: Kontener z layoutem aplikacji
    """
    return html.Div([
        # Nagłówek
        html.Div([
            html.H1("PACKIT 4.0 - Optymalizacja załadunku palet", className="display-4"),
            html.Hr(),
            html.P(
                "System do optymalizacji załadunku palet transportowych z wykorzystaniem metod uczenia maszynowego",
                className="lead"
            )
        ], className="jumbotron p-4"),
        
        # Główny kontener
        dbc.Container([
            # Przyciski kontrolne i opcje
            dbc.Row([
                dbc.Col([
                    # Wybór algorytmu
                    html.H5("Wybierz metodę załadunku:"),
                    dcc.Dropdown(
                        id="algorithm-dropdown",
                        options=[
                            {"label": "Załadunek wzdłuż osi X i Z", "value": "XZ_Axis_Loading"},
                            {"label": "Załadunek w oparciu o rozkład X", "value": "X_Distribution"},
                            {"label": "Załadunek w oparciu o rozkład Z", "value": "Z_Distribution"},
                            {"label": "Uczenie ze wzmocnieniem", "value": "RL_Loading"}
                        ],
                        value="XZ_Axis_Loading",
                        clearable=False,
                        className="mb-3"
                    ),
                    
                    # Opis wybranego algorytmu
                    html.Div(id="algorithm-description", className="alert alert-info"),
                    
                    # Przycisk uruchomienia algorytmu
                    dbc.Button(
                        "Uruchom algorytm",
                        id="run-algorithm-button",
                        color="primary",
                        className="mt-3 mb-4 w-100"
                    )
                ], md=4),
                
                dbc.Col([
                    # Lista palet do załadunku
                    html.H5("Palety do załadunku:"),
                    html.Div([
                        # Tabela palet
                        dbc.Card([
                            dbc.CardHeader("Lista palet"),
                            dbc.CardBody([
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
                                    row_selectable="multi",
                                    selected_rows=[],
                                    page_size=10,
                                    style_cell={
                                        'whiteSpace': 'normal',
                                        'height': 'auto',
                                        'textAlign': 'left'
                                    },
                                    style_data_conditional=[
                                        {
                                            'if': {'row_index': 'odd'},
                                            'backgroundColor': 'rgb(248, 248, 248)'
                                        }
                                    ],
                                    style_header={
                                        'backgroundColor': 'rgb(230, 230, 230)',
                                        'fontWeight': 'bold'
                                    }
                                )
                            ])
                        ])
                    ]),
                    
                    # Przyciski do zarządzania paletami
                    dbc.Row([
                        dbc.Col([
                            dbc.Button(
                                "Dodaj paletę",
                                id="add-pallet-button",
                                color="success",
                                className="mt-3 w-100"
                            )
                        ], width=6),
                        dbc.Col([
                            dbc.Button(
                                "Usuń zaznaczone",
                                id="remove-pallet-button",
                                color="danger",
                                className="mt-3 w-100"
                            )
                        ], width=6)
                    ])
                ], md=8)
            ], className="mb-4"),
            
            # Modal do dodawania nowej palety
            dbc.Modal([
                dbc.ModalHeader("Dodaj nową paletę"),
                dbc.ModalBody([
                    dbc.Form([
                        dbc.Row([
                            dbc.Label("Typ palety:"),
                            dcc.Dropdown(
                                id="new-pallet-type",
                                options=[
                                    {"label": f"{ptype} ({specs['length']}x{specs['width']}x{specs['height']} mm)", 
                                     "value": ptype}
                                    for ptype, specs in PALLET_TYPES.items()
                                ],
                                value="EUR",
                                clearable=False
                            )
                        ], className="mb-3"),
                        dbc.Row([
                            dbc.Label("Masa ładunku (kg):"),
                            dbc.Input(
                                id="new-pallet-cargo-weight",
                                type="number",
                                min=0,
                                max=2000,
                                value=100
                            )
                        ], className="mb-3"),
                        dbc.Row([
                            dbc.Label("Czy można układać w stosy:"),
                            dbc.Checklist(
                                options=[
                                    {"label": "Tak", "value": 1}
                                ],
                                value=[1],
                                id="new-pallet-stackable",
                                switch=True
                            )
                        ], className="mb-3"),
                        dbc.Row([
                            dbc.Label("Czy ładunek jest kruchy:"),
                            dbc.Checklist(
                                options=[
                                    {"label": "Tak", "value": 1}
                                ],
                                value=[],
                                id="new-pallet-fragile",
                                switch=True
                            )
                        ], className="mb-3")
                    ])
                ]),
                dbc.ModalFooter([
                    dbc.Button("Anuluj", id="cancel-add-pallet", className="ml-auto"),
                    dbc.Button("Dodaj", id="confirm-add-pallet", color="primary")
                ])
            ], id="add-pallet-modal"),
            
            # Kontener na wizualizację 3D
            dbc.Row([
                dbc.Col([
                    html.H3("Wizualizacja załadunku:", className="mb-3"),
                    dbc.Card([
                        dbc.CardBody([
                            html.Div(id="visualization-container", style={"height": "80vh"})
                        ])
                    ])
                ], width=12)
            ]),
            
            # Sekcja statystyk
            dbc.Row([
                dbc.Col([
                    html.H3("Statystyki załadunku:", className="mt-4 mb-3"),
                    dbc.Card([
                        dbc.CardHeader(html.H5("Rozkład masy")),
                        dbc.CardBody([
                            html.Div(id="weight-distribution-container")
                        ])
                    ])
                ], md=6),
                dbc.Col([
                    html.H3("\u00A0", className="mt-4 mb-3"),  # Niewidoczny nagłówek dla wyrównania
                    dbc.Card([
                        dbc.CardHeader(html.H5("Efektywność załadunku")),
                        dbc.CardBody([
                            html.Div(id="efficiency-container")
                        ])
                    ])
                ], md=6)
            ], className="mb-5")
        ], fluid=True)
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