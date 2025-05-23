"""
Moduł do tworzenia wizualizacji 3D załadunku palet.
"""

from typing import List, Dict, Any, Optional, Union
import plotly.graph_objects as go
import numpy as np
from dash import dcc

from src.data.pallet import Pallet
from src.data.trailer import Trailer
from src.config import TRAILER_CONFIG, VISUALIZATION


def plot_3d_trailer_with_pallets(pallets: List[Pallet], trailer: Optional[Trailer] = None) -> go.Figure:
    """
    Tworzy wizualizację 3D naczepy z załadowanymi paletami.
    
    Args:
        pallets: Lista załadowanych palet
        trailer: Naczepa (opcjonalnie)
        
    Returns:
        go.Figure: Figura z wizualizacją 3D
    """
    # Jeśli nie podano naczepy, utwórz domyślną
    if trailer is None:
        trailer = Trailer()
    
    # Tworzenie figury
    fig = go.Figure()
    
    # Dodanie naczepy
    _add_trailer_to_figure(fig, trailer)
    
    # Dodanie palet
    for pallet in pallets:
        _add_pallet_to_figure(fig, pallet)
    
    # Konfiguracja wyglądu
    _configure_figure_layout(fig, trailer)
    
    return fig


def create_3d_visualization(trailer: Trailer, pallets: List[Pallet]) -> dict:
    """
    Tworzy interaktywną wizualizację 3D naczepy z załadowanymi paletami.
    Wersja dostosowana do nowego interfejsu aplikacji.
    
    Args:
        trailer: Naczepa z załadunkiem
        pallets: Lista załadowanych palet
        
    Returns:
        dict: Dane dla komponentu dcc.Graph
    """
    # Tworzenie figury
    fig = go.Figure()
    
    # Dodanie naczepy
    _add_trailer_to_figure(fig, trailer)
    
    # Dodanie palet
    for pallet in pallets:
        _add_pallet_to_figure(fig, pallet)
    
    # Konfiguracja wyglądu
    _configure_figure_layout(fig, trailer)
    
    # Dodanie tytułu z informacją o liczbie załadowanych palet
    total_pallets = len(trailer.loaded_pallets)
    loaded_pallets_count = len(pallets)
    loading_ratio = (loaded_pallets_count / total_pallets) * 100 if total_pallets > 0 else 0
    
    fig.update_layout(
        title=f"Załadowano {loaded_pallets_count} palet",
        margin=dict(l=0, r=0, t=40, b=0)
    )
    
    # Konwertuj go.Figure na słownik
    return fig.to_dict()


def create_weight_distribution_plot(trailer: Trailer) -> dict:
    """
    Tworzy wykres rozkładu masy w naczepie.
    
    Args:
        trailer: Naczepa z załadunkiem
        
    Returns:
        dict: Dane dla komponentu dcc.Graph
    """
    # Pobierz rozkład masy
    weight_dist = trailer.weight_distribution
    
    # Utwórz wykres słupkowy
    fig = go.Figure()
    
    # Dodaj słupki dla różnych stref
    fig.add_trace(go.Bar(
        x=["Przód", "Tył", "Lewo", "Prawo"],
        y=[weight_dist["front"], weight_dist["back"], weight_dist["left"], weight_dist["right"]],
        marker_color=['rgba(50, 171, 96, 0.7)', 'rgba(50, 171, 96, 0.7)', 
                     'rgba(128, 128, 255, 0.7)', 'rgba(128, 128, 255, 0.7)'],
        name="Rozkład masy"
    ))
    
    # Skonfiguruj układ
    fig.update_layout(
        title="Rozkład masy w naczepie",
        yaxis_title="Masa (kg)",
        xaxis_title="Strefa naczepy",
        bargap=0.2,
        bargroupgap=0.1,
        height=300,
        margin=dict(l=40, r=20, t=60, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    # Dodaj adnotacje z wartościami procentowymi
    front_back_ratio = weight_dist["front"] / (weight_dist["front"] + weight_dist["back"]) if (weight_dist["front"] + weight_dist["back"]) > 0 else 0
    left_right_ratio = weight_dist["left"] / (weight_dist["left"] + weight_dist["right"]) if (weight_dist["left"] + weight_dist["right"]) > 0 else 0
    
    fig.add_annotation(
        x=0.5,
        y=1.05,
        xref="paper",
        yref="paper",
        text=f"Rozkład przód-tył: {front_back_ratio:.2f} (optymalnie: 0.6)",
        showarrow=False,
        font=dict(size=12)
    )
    
    fig.add_annotation(
        x=0.5,
        y=0.95,
        xref="paper",
        yref="paper",
        text=f"Rozkład lewo-prawo: {left_right_ratio:.2f} (optymalnie: 0.5)",
        showarrow=False,
        font=dict(size=12)
    )
    
    # Konwertuj go.Figure na słownik
    return fig.to_dict()


def create_weight_distribution_chart(pallets: List[Pallet], trailer: Optional[Trailer] = None) -> go.Figure:
    """
    Tworzy wykres rozkładu masy w naczepie.
    
    Args:
        pallets: Lista załadowanych palet
        trailer: Naczepa (opcjonalnie)
        
    Returns:
        go.Figure: Figura z wykresem rozkładu masy
    """
    # Jeśli nie podano naczepy, utwórz domyślną
    if trailer is None:
        trailer = Trailer()
    
    # Aktualizacja rozkładu masy
    trailer.loaded_pallets = pallets
    trailer._update_weight_distribution()
    
    # Pobranie danych o rozkładzie masy
    weight_data = trailer.weight_distribution
    
    # Tworzenie wykresu słupkowego dla rozkładu masy
    fig = go.Figure()
    
    # Rozkład bok do boku
    fig.add_trace(go.Bar(
        x=["Lewa strona", "Prawa strona"],
        y=[weight_data["left"], weight_data["right"]],
        text=[f"{weight_data['left']:.1f} kg", f"{weight_data['right']:.1f} kg"],
        textposition="auto",
        name="Rozkład bok do boku",
        marker_color=["rgba(31, 119, 180, 0.8)", "rgba(255, 127, 14, 0.8)"]
    ))
    
    # Rozkład przód-tył
    fig.add_trace(go.Bar(
        x=["Przód", "Tył"],
        y=[weight_data["front"], weight_data["back"]],
        text=[f"{weight_data['front']:.1f} kg", f"{weight_data['back']:.1f} kg"],
        textposition="auto",
        name="Rozkład przód-tył",
        marker_color=["rgba(44, 160, 44, 0.8)", "rgba(214, 39, 40, 0.8)"],
        visible=False
    ))
    
    # Dodanie przycisków przełączających między rozkładami
    fig.update_layout(
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                buttons=[
                    dict(
                        label="Bok do boku",
                        method="update",
                        args=[{"visible": [True, False]}]
                    ),
                    dict(
                        label="Przód-tył",
                        method="update",
                        args=[{"visible": [False, True]}]
                    )
                ],
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.1,
                y=1.15,
                xanchor="left",
                yanchor="top"
            )
        ],
        title="Rozkład masy w naczepie",
        yaxis_title="Masa (kg)",
        template="plotly_white"
    )
    
    return fig


def create_loading_efficiency_chart(pallets: List[Pallet], trailer: Optional[Trailer] = None) -> go.Figure:
    """
    Tworzy wykres efektywności załadunku.
    
    Args:
        pallets: Lista załadowanych palet
        trailer: Naczepa (opcjonalnie)
        
    Returns:
        go.Figure: Figura z wykresem efektywności załadunku
    """
    # Jeśli nie podano naczepy, utwórz domyślną
    if trailer is None:
        trailer = Trailer()
    
    # Obliczenie metryk efektywności
    trailer.loaded_pallets = pallets
    efficiency = trailer.get_loading_efficiency()
    
    # Tworzenie wykresu słupkowego dla metryk efektywności
    fig = go.Figure()
    
    # Dodanie słupków
    fig.add_trace(go.Bar(
        x=["Wykorzystanie przestrzeni", "Wykorzystanie ładowności"],
        y=[efficiency["space_utilization"], efficiency["weight_utilization"]],
        text=[f"{efficiency['space_utilization']:.1f}%", f"{efficiency['weight_utilization']:.1f}%"],
        textposition="auto",
        marker_color=["rgba(31, 119, 180, 0.8)", "rgba(255, 127, 14, 0.8)"]
    ))
    
    # Konfiguracja wykresu
    fig.update_layout(
        title="Efektywność załadunku",
        yaxis_title="Procent wykorzystania (%)",
        template="plotly_white",
        yaxis=dict(range=[0, 100])
    )
    
    return fig


def _add_trailer_to_figure(fig: go.Figure, trailer: Trailer) -> None:
    """
    Dodaje reprezentację naczepy do figury.
    
    Args:
        fig: Figura Plotly
        trailer: Naczepa
    """
    # Pobranie wymiarów naczepy
    length = trailer.length
    width = trailer.width
    height = trailer.height
    
    # Kolor naczepy
    trailer_color = VISUALIZATION["trailer_color"]
    trailer_outline_color = VISUALIZATION["trailer_outline_color"]
    
    # Dodanie podłogi naczepy
    fig.add_trace(go.Mesh3d(
        x=[0, length, length, 0, 0, length, length, 0],
        y=[0, 0, width, width, 0, 0, width, width],
        z=[0, 0, 0, 0, 0, 0, 0, 0],
        i=[0, 0, 0, 0],
        j=[1, 2, 3, 7],
        k=[2, 3, 7, 6],
        color=trailer_color,
        flatshading=True,
        name="Trailer Floor"
    ))
    
    # Dodanie ścian naczepy
    # Ściana przednia (x = 0)
    fig.add_trace(go.Mesh3d(
        x=[0, 0, 0, 0],
        y=[0, width, width, 0],
        z=[0, 0, height, height],
        i=[0, 0],
        j=[1, 3],
        k=[2, 2],
        color=trailer_color,
        flatshading=True,
        name="Trailer Front Wall"
    ))
    
    # Ściana tylna (x = length)
    fig.add_trace(go.Mesh3d(
        x=[length, length, length, length],
        y=[0, width, width, 0],
        z=[0, 0, height, height],
        i=[0, 0],
        j=[1, 3],
        k=[2, 2],
        color=trailer_color,
        flatshading=True,
        name="Trailer Back Wall"
    ))
    
    # Ściana lewa (y = 0)
    fig.add_trace(go.Mesh3d(
        x=[0, length, length, 0],
        y=[0, 0, 0, 0],
        z=[0, 0, height, height],
        i=[0, 0],
        j=[1, 3],
        k=[2, 2],
        color=trailer_color,
        flatshading=True,
        name="Trailer Left Wall"
    ))
    
    # Ściana prawa (y = width)
    fig.add_trace(go.Mesh3d(
        x=[0, length, length, 0],
        y=[width, width, width, width],
        z=[0, 0, height, height],
        i=[0, 0],
        j=[1, 3],
        k=[2, 2],
        color=trailer_color,
        flatshading=True,
        name="Trailer Right Wall"
    ))
    
    # Dodanie obrysu naczepy
    _add_trailer_outline(fig, trailer, trailer_outline_color)


def _add_trailer_outline(fig: go.Figure, trailer: Trailer, color: str) -> None:
    """
    Dodaje obrys naczepy do figury.
    
    Args:
        fig: Figura Plotly
        trailer: Naczepa
        color: Kolor obrysu
    """
    # Pobranie wymiarów naczepy
    length = trailer.length
    width = trailer.width
    height = trailer.height
    
    # Linie obrysu - podłoga
    fig.add_trace(go.Scatter3d(
        x=[0, length, length, 0, 0],
        y=[0, 0, width, width, 0],
        z=[0, 0, 0, 0, 0],
        mode='lines',
        line=dict(color=color, width=3),
        name="Trailer Outline Floor"
    ))
    
    # Linie obrysu - sufit
    fig.add_trace(go.Scatter3d(
        x=[0, length, length, 0, 0],
        y=[0, 0, width, width, 0],
        z=[height, height, height, height, height],
        mode='lines',
        line=dict(color=color, width=3),
        name="Trailer Outline Ceiling"
    ))
    
    # Linie obrysu - pionowe krawędzie
    for x, y in [(0, 0), (length, 0), (length, width), (0, width)]:
        fig.add_trace(go.Scatter3d(
            x=[x, x],
            y=[y, y],
            z=[0, height],
            mode='lines',
            line=dict(color=color, width=3),
            name=f"Trailer Outline Edge ({x}, {y})"
        ))


def _add_pallet_to_figure(fig: go.Figure, pallet: Pallet) -> None:
    """
    Dodaje paletę do figury.
    
    Args:
        fig: Figura Plotly
        pallet: Paleta
    """
    # Pobranie pozycji i wymiarów palety
    x, y, z = pallet.position
    length, width, height = pallet.dimensions
    
    # Kolor palety (bez przezroczystości)
    color_base = pallet.color
    if "rgba" in color_base:
        # Zamień rgba na rgb, całkowicie usuwając przezroczystość
        color_parts = color_base.replace("rgba(", "").replace(")", "").split(",")
        color_base = f"rgb({color_parts[0]},{color_parts[1]},{color_parts[2]})"
    
    # Wierzchołki palety
    vertices_x = [
        x, x + length, x + length, x,
        x, x + length, x + length, x
    ]
    vertices_y = [
        y, y, y + width, y + width,
        y, y, y + width, y + width
    ]
    vertices_z = [
        z, z, z, z,
        z + height, z + height, z + height, z + height
    ]
    
    # Dodanie ścian palety z różnymi kolorami
    # Ściana dolna (podłoga) - ciemniejsza
    floor_color = color_base
    fig.add_trace(go.Mesh3d(
        x=[x, x + length, x + length, x],
        y=[y, y, y + width, y + width],
        z=[z, z, z, z],
        i=[0, 0],
        j=[1, 3],
        k=[2, 2],
        color=floor_color,
        flatshading=True,
        name=f"Pallet {pallet.pallet_id} Floor"
    ))
    
    # Ściana górna (sufit) - jaśniejsza
    ceiling_color = color_base
    fig.add_trace(go.Mesh3d(
        x=[x, x + length, x + length, x],
        y=[y, y, y + width, y + width],
        z=[z + height, z + height, z + height, z + height],
        i=[0, 0],
        j=[1, 3],
        k=[2, 2],
        color=ceiling_color,
        flatshading=True,
        name=f"Pallet {pallet.pallet_id} Ceiling"
    ))
    
    # Ściana przednia
    front_color = color_base
    fig.add_trace(go.Mesh3d(
        x=[x, x + length, x + length, x],
        y=[y, y, y, y],
        z=[z, z, z + height, z + height],
        i=[0, 0],
        j=[1, 3],
        k=[2, 2],
        color=front_color,
        flatshading=True,
        name=f"Pallet {pallet.pallet_id} Front"
    ))
    
    # Ściana tylna
    back_color = color_base
    fig.add_trace(go.Mesh3d(
        x=[x, x + length, x + length, x],
        y=[y + width, y + width, y + width, y + width],
        z=[z, z, z + height, z + height],
        i=[0, 0],
        j=[1, 3],
        k=[2, 2],
        color=back_color,
        flatshading=True,
        name=f"Pallet {pallet.pallet_id} Back"
    ))
    
    # Ściana lewa
    left_color = color_base
    fig.add_trace(go.Mesh3d(
        x=[x, x, x, x],
        y=[y, y + width, y + width, y],
        z=[z, z, z + height, z + height],
        i=[0, 0],
        j=[1, 3],
        k=[2, 2],
        color=left_color,
        flatshading=True,
        name=f"Pallet {pallet.pallet_id} Left"
    ))
    
    # Ściana prawa
    right_color = color_base
    fig.add_trace(go.Mesh3d(
        x=[x + length, x + length, x + length, x + length],
        y=[y, y + width, y + width, y],
        z=[z, z, z + height, z + height],
        i=[0, 0],
        j=[1, 3],
        k=[2, 2],
        color=right_color,
        flatshading=True,
        name=f"Pallet {pallet.pallet_id} Right"
    ))
    
    # Dodanie konturów palety
    # Dolny prostokąt
    fig.add_trace(go.Scatter3d(
        x=[x, x + length, x + length, x, x],
        y=[y, y, y + width, y + width, y],
        z=[z, z, z, z, z],
        mode='lines',
        line=dict(color='black', width=3),
        name=f"Pallet {pallet.pallet_id} Bottom Edge"
    ))
    
    # Górny prostokąt
    fig.add_trace(go.Scatter3d(
        x=[x, x + length, x + length, x, x],
        y=[y, y, y + width, y + width, y],
        z=[z + height, z + height, z + height, z + height, z + height],
        mode='lines',
        line=dict(color='black', width=3),
        name=f"Pallet {pallet.pallet_id} Top Edge"
    ))
    
    # Pionowe krawędzie
    for dx, dy in [(0, 0), (length, 0), (length, width), (0, width)]:
        fig.add_trace(go.Scatter3d(
            x=[x + dx, x + dx],
            y=[y + dy, y + dy],
            z=[z, z + height],
            mode='lines',
            line=dict(color='black', width=3),
            name=f"Pallet {pallet.pallet_id} Vertical Edge"
        ))
    
    # Dodanie tekstu informacyjnego na hover
    hover_text = f"ID: {pallet.pallet_id}<br>Typ: {pallet.pallet_type}<br>Wymiary: {length}x{width}x{height} mm<br>Masa: {pallet.total_weight} kg<br>Pozycja: ({x}, {y}, {z})"
    
    # Dodanie punktu centralnego dla hovertekstu
    fig.add_trace(go.Scatter3d(
        x=[x + length/2],
        y=[y + width/2],
        z=[z + height/2],
        mode='markers',
        marker=dict(size=1, opacity=0),
        hoverinfo='text',
        hovertext=hover_text,
        name=f"Pallet {pallet.pallet_id} Info"
    ))


def _configure_figure_layout(fig: go.Figure, trailer: Trailer) -> None:
    """
    Konfiguruje wygląd figury.
    
    Args:
        fig: Figura Plotly
        trailer: Naczepa
    """
    # Pobranie wymiarów naczepy
    length = trailer.length
    width = trailer.width
    height = trailer.height
    
    # Dodatkowa przestrzeń wokół naczepy
    padding = VISUALIZATION["scene_padding"]
    
    # Konfiguracja osi
    axis_config = dict(
        showgrid=True,
        showbackground=True,
        backgroundcolor="rgba(240, 240, 240, 0.5)",
        gridcolor="rgba(120, 120, 120, 0.2)",
        zerolinecolor="rgba(0, 0, 0, 0.1)"
    )
    
    # Konfiguracja figury
    fig.update_layout(
        scene=dict(
            xaxis=dict(
                range=[-padding, length + padding],
                title="Długość (mm)",
                **axis_config
            ),
            yaxis=dict(
                range=[-padding, width + padding],
                title="Szerokość (mm)",
                **axis_config
            ),
            zaxis=dict(
                range=[-padding, height + padding],
                title="Wysokość (mm)",
                **axis_config
            ),
            aspectmode='data',
            camera=dict(
                eye=dict(
                    x=VISUALIZATION["camera_position"]["x"],
                    y=VISUALIZATION["camera_position"]["y"],
                    z=VISUALIZATION["camera_position"]["z"]
                )
            )
        ),
        title=dict(
            text="Wizualizacja 3D załadunku palet",
            xanchor="center",
            x=0.5
        ),
        margin=dict(l=0, r=0, t=50, b=0),
        legend=dict(
            title="Elementy",
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255, 255, 255, 0.8)"
        ),
        template="plotly_white"
    ) 