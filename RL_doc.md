# Dokumentacja modelu RL

## Cel projektu

Celem projektu było wytrenowanie agenta uczenia ze wzmocnieniem (Reinforcement Learning) z wykorzystaniem algorytmu **Proximal Policy Optimization** (PPO), którego zadaniem jest automatyczny, efektywny i zrównoważony załadunek różnych palet na naczepę ciężarówki.

## Podejście

Agent uczy się ładować palety w taki sposób, aby:

- zmaksymalizować wykorzystanie przestrzeni i masy naczepy,
- zapewnić równomierny rozkład masy (zarówno boczny, jak i przód–tył),
- unikać kolizji oraz błędnych pozycji,
- jak najszybciej i najefektywniej zakończyć proces załadunku.

## Struktura środowiska

### Akcje

Agent wykonuje dwuwymiarową akcję `action = [a[0], a[1]]`, gdzie:

- $a[0] \in [0.0, 1.0]$: indeks wybranego rodzaju palety — przekształcany na indeks poprzez:

```python
pallet_index = int(a[0] * len(self.unloaded_pallets))
pallet_index = np.clip(pallet_index, 0, len(self.unloaded_pallets) - 1)
selected_pallet = self.unloaded_pallets.pop(pallet_index)
```

- $a[1] \in [0.0, 1.0]$: docelowa pozycja w osi Y (szerokość naczepy), wyznaczana przez:

```python
target_y = a[1] * self.trailer.width
```

Jeśli wybrana pozycja jest nieprawidłowa (kolizja, poza granicami, zaburzenie balansu), agent otrzymuje wysoką karę i paleta nie jest ładowana. W przeciwnym razie nagradzany jest za poprawny i efektywny załadunek.

### Obserwacja

Obserwacja zwracana przez środowisko to wektor zawierający informacje o aktualnym stanie naczepy i inwentarza:

| Składnik              |   Opis                                                        |
| --------------------- | -----------------------------------------------------------   |
| `space_utilization`     | Stopień wykorzystania przestrzeni ładunkowej                |
| `load_utilization`      | Stopień wykorzystania dopuszczalnej masy                    |
| `weight_balance_side`   | Wskaźnik równowagi masy lewo-prawo                          |
| `weight_balance_front`  | Wskaźnik równowagi masy przód–tył                           |
| `num_remaining`         | Procent niezaładowanych palet                               |
| `inventory`             | Liczność pozostałych palet każdego typu (znormalizowana)    |

Jest to wykonane wykorzystjąc poniższą operację:

```python
obs = np.concatenate((
    [
        space_utilization, load_utilization, num_remaining,
        weight_balance_side, weight_balance_front
    ],
    norm_inventory
))
```

### Funkcja nagrody

| Sytuacja | Nagroda |
| ----------------------------------------------|---|
| Nieprawidłowa pozycja/kolizja                 | - 1000 |
| Poprawny załadunek                            | `reward = 10 * efficiency * progress_factor` |
| Niezrównowaony rozkład masy po zakończeniu    | -50 za kadą niespełnioną oś (przód-tył, lewo-prawo) |

Gdzie:

- `efficiency = space_utilization + load_utilization`
- `progress_factor = 1 - (liczba pozostałych palet / liczba wszystkich palet)`ś

### Reprezentacja palet

W środowisku występuje kilka rodzajów palet, różniących się:

- *masą własną* – stałą dla danego typu palety,
- *śmasą towaru* – zmienną w obrębie danego typu, ustalaną losowo w danym epizodzie.

Podczas wyboru palety agent wskazuje tylko rodzaj, a środowisko ładuje pierwszą dostępną paletę tego typu. Oznacza to, że agent nie ma bezpośredniego wpływu na wybór konkretnej palety (o konkretnej masie) spośród wielu tego samego typu.

Warto dodać, że podczas treningu losowano palety, w których masa jest losowa, jednak wartości masy losowano z różnych rozkładów - cięższe palety średnio dźwigają cięższy ładunek.

### Ograniczenia i obserwowane problemy

- Agent nie ma dostępu do informacji o masie pozostałych palet – przez co jego decyzje są często nieprzewidywalne i lokalnie zoptymalizowane.
- Wysoki poziom szumu w treningu sugeruje, że brak kontekstu masowego może prowadzić do nieefektywnego planowania rozkładu.

## Propozycja usprawnienia

Aby umożliwić agentowi bardziej świadomy wybór rodzaju palety, zaleca się rozszerzenie obserwacji o informacje agregujące masę pozostałych palet. Może to przybrać formę, np. dodania do wektora obserwacji sumarycznej masy pozostałej dla każdego typu palety.

Takie rozszerzenie mogłoby pomóc agentowi lepiej planować, który typ palety wybrać w danym momencie, biorąc pod uwagę przyszły wpływ masy na balans całej naczepy.

## Podsumowanie

Projekt z sukcesem implementuje zaawansowane środowisko do załadunku palet, uwzględniające wiele fizycznych i logistycznych ograniczeń. Jednak w celu dalszej poprawy stabilności treningu i jakości decyzji agenta, warto wzbogacić obserwację o masowe cechy niezaładowanych palet, co pozwoli na bardziej globalnie optymalne decyzje.

## Dyskusja nad alternatywnymi metodami RL

W projekcie rozważono możliwość zastosowania algorytmu DQN, jednak jego klasyczna forma zakłada dyskretną przestrzeń akcji. W analizowanym środowisku agent operuje na zmiennych ciągłych – wybiera typ palety oraz pozycję w naczepie – co powoduje, że zastosowanie DQN wymagałoby wcześniejszej dyskretyzacji akcji. Taka dyskretyzacja prowadzi jednak do utraty precyzji, wzrostu liczby możliwych akcji oraz znacznie utrudnia proces uczenia.

Z kolei algorytmy typu policy gradient, takie jak PPO, lepiej nadają się do pracy w przestrzeniach ciągłych, ponieważ bezpośrednio uczą rozkładów prawdopodobieństwa nad możliwymi akcjami. PPO nie wymaga dyskretyzowania przestrzeni akcji i pozwala agentowi działać bardziej płynnie i adaptacyjnie, co jest szczególnie ważne przy zadaniach takich jak pozycjonowanie palet w naczepie.

Choć możliwe byłoby przekształcenie środowiska do wersji zgodnej z DQN, wiązałoby się to z kompromisami w zakresie precyzji i złożoności przestrzeni decyzyjnej. W związku z tym decyzja o zastosowaniu PPO jako algorytmu uczącego wydaje się uzasadniona i najlepiej dopasowana do specyfiki problemu.
