# Przewodnik po Uczeniu ze Wzmocnieniem w Optymalizacji Załadunku Palet

## Spis treści
1. [Wprowadzenie do uczenia ze wzmocnieniem](#wprowadzenie-do-uczenia-ze-wzmocnieniem)
2. [Zastosowanie w optymalizacji załadunku palet](#zastosowanie-w-optymalizacji-załadunku-palet)
3. [Architektura implementacji](#architektura-implementacji)
4. [Trenowanie modelu](#trenowanie-modelu)
5. [Korzystanie z wytrenowanego modelu](#korzystanie-z-wytrenowanego-modelu)
6. [Parametry i dostrajanie](#parametry-i-dostrajanie)
7. [Wizualizacja i monitorowanie](#wizualizacja-i-monitorowanie)
8. [Przewagi i ograniczenia](#przewagi-i-ograniczenia)
9. [Przyszłe rozszerzenia](#przyszłe-rozszerzenia)

## Wprowadzenie do uczenia ze wzmocnieniem

Uczenie ze wzmocnieniem (Reinforcement Learning, RL) to jedna z gałęzi uczenia maszynowego, w której agent uczy się podejmować optymalne decyzje poprzez interakcję ze środowiskiem. W przeciwieństwie do uczenia nadzorowanego, agent nie otrzymuje gotowych par wejście-wyjście, lecz sam odkrywa, które działania prowadzą do największych nagród.

### Kluczowe pojęcia:

- **Agent** - system podejmujący decyzje (w naszym przypadku algorytm załadunku palet)
- **Środowisko** - kontekst, w którym działa agent (naczepa i zestaw palet)
- **Stan** - reprezentacja aktualnej sytuacji środowiska (wypełnienie naczepy, cechy palety)
- **Akcja** - decyzja podejmowana przez agenta (gdzie i jak umieścić paletę)
- **Nagroda** - informacja zwrotna o jakości podjętej akcji (efektywność załadunku, rozkład masy)
- **Polityka** - strategia wybierania akcji przez agenta

### Algorytm Q-learning

W naszej implementacji wykorzystujemy algorytm Q-learning, który jest metodą uczenia ze wzmocnieniem bez modelu (model-free). Algorytm ten uczy się funkcji wartości Q(s, a), która określa oczekiwaną łączną nagrodę za wykonanie akcji "a" w stanie "s", a następnie postępowanie zgodnie z optymalną polityką.

Funkcja Q jest aktualizowana według wzoru:

```
Q(s, a) := Q(s, a) + α [r + γ max Q(s', a') - Q(s, a)]
```

gdzie:
- α (alfa) - współczynnik uczenia
- r - nagroda za wykonanie akcji
- γ (gamma) - współczynnik dyskontowania przyszłych nagród
- s' - następny stan
- a' - możliwa akcja w następnym stanie

## Zastosowanie w optymalizacji załadunku palet

Problemy optymalizacji załadunku palet są złożone i trudne do rozwiązania za pomocą tradycyjnych algorytmów, szczególnie gdy chcemy uwzględnić wiele czynników jednocześnie:

1. Maksymalizacja wykorzystania przestrzeni
2. Optymalizacja rozkładu masy
3. Uwzględnienie ograniczeń fizycznych (stackability, fragility)
4. Adaptacja do różnych konfiguracji palet

Uczenie ze wzmocnieniem jest idealne do rozwiązywania takich problemów, ponieważ:

- Pozwala agentowi odkrywać nieoczywiste, ale optymalne strategie
- Adaptuje się do różnych zestawów danych bez przeprogramowywania
- Może równoważyć wiele sprzecznych celów (wykorzystanie przestrzeni vs. rozkład masy)
- Ulepsza się wraz z ilością danych treningowych

## Architektura implementacji

Nasza implementacja składa się z dwóch głównych klas:

### ReinforcementLearningAgent

Jest to właściwy agent uczenia ze wzmocnieniem, odpowiedzialny za:
- Reprezentację stanów (dyskretyzacja ciągłej przestrzeni stanów)
- Wybór akcji (strategia epsilon-greedy)
- Aktualizację tablicy Q wartości
- Obliczanie nagród
- Trenowanie modelu
- Zapisywanie i wczytywanie modelu

### ReinforcementLearningLoading

Klasa algorytmu załadunku, która dziedziczy po klasie bazowej `LoadingAlgorithm` i:
- Inicjalizuje i wykorzystuje agenta RL
- Implementuje logikę załadunku palet z wykorzystaniem decyzji agenta
- Zapewnia interfejs do treningu i wizualizacji

## Trenowanie modelu

Proces treningu agenta RL składa się z następujących kroków:

1. **Generowanie epizodów treningowych**: Każdy epizod polega na próbie załadunku jednego zestawu palet.
2. **Eksploracja vs eksploatacja**: Na początku agent eksploruje (wybiera losowe akcje), aby poznać przestrzeń stanów. Z czasem coraz częściej wybiera akcje, które nauczył się uznawać za optymalne.
3. **Aktualizacja wiedzy**: Po każdej akcji agent aktualizuje swoją tabelę Q-wartości na podstawie otrzymanej nagrody.
4. **Zmniejszanie współczynnika eksploracji**: Wraz z postępem treningu agent coraz rzadziej eksploruje, a częściej wykorzystuje zdobytą wiedzę.

### Jak trenować model:

1. Wybierz algorytm "Uczenie ze wzmocnieniem" z rozwijanej listy.
2. Panel treningu RL powinien stać się widoczny.
3. Ustaw liczbę epizodów treningowych (zalecane minimum 1000 dla uzyskania sensownych rezultatów).
4. Kliknij "Trenuj model".
5. Monitoruj postęp treningu na wykresie nagród.
6. Po zakończeniu treningu model zostanie automatycznie zapisany.

**Uwaga**: Trening może zajmować dużo czasu, szczególnie dla dużej liczby epizodów. Możesz w każdej chwili przerwać trening, a model zachowa dotychczas zdobytą wiedzę.

## Korzystanie z wytrenowanego modelu

Po wytrenowaniu modelu możesz go używać tak samo jak innych algorytmów załadunku:

1. Wybierz algorytm "Uczenie ze wzmocnieniem".
2. Wybierz zestaw palet do załadunku.
3. Kliknij "Uruchom algorytm".

Agent wykorzysta swoją nauczoną politykę do optymalizacji załadunku. Jeśli model nie był jeszcze trenowany lub nie został znaleziony plik modelu, agent będzie podejmował domyślne lub losowe decyzje.

## Parametry i dostrajanie

Algorytm uczenia ze wzmocnieniem można dostroić poprzez modyfikację następujących parametrów:

- **learning_rate (alfa)**: Określa jak szybko agent aktualizuje swoją wiedzę. Wyższe wartości prowadzą do szybszej adaptacji, ale mogą powodować niestabilność. (Domyślnie: 0.1)
- **discount_factor (gamma)**: Określa wartość przyszłych nagród względem natychmiastowych. Wyższe wartości oznaczają większą wagę długoterminowych korzyści. (Domyślnie: 0.95)
- **exploration_rate (epsilon)**: Początkowe prawdopodobieństwo wyboru losowej akcji zamiast najlepszej znanej. (Domyślnie: 1.0 podczas treningu, 0.1 podczas normalnego działania)
- **exploration_decay**: Określa jak szybko maleje współczynnik eksploracji. (Domyślnie: 0.995)
- **exploration_min**: Minimalna wartość współczynnika eksploracji. (Domyślnie: 0.01)

Parametry te można modyfikować w kodzie w pliku `reinforcement_learning.py` lub przekazać w konfiguracji algorytmu.

## Wizualizacja i monitorowanie

Podczas treningu modelu możesz monitorować następujące informacje:

1. **Postęp treningu**: Procentowe ukończenie zadanej liczby epizodów.
2. **Wykres nagród**: Pokazuje, jak zmieniają się nagrody w kolejnych epizodach, co wskazuje na postęp uczenia.
3. **Status modelu**: Po treningu możesz zobaczyć statystyki modelu, takie jak liczba epizodów treningowych, aktualny współczynnik eksploracji i rozmiar tablicy Q.

W trybie załadunku możesz obserwować standardowe wizualizacje i statystyki:

1. **Wizualizacja 3D załadunku**: Pokazuje rozmieszczenie palet w naczepie.
2. **Rozkład masy**: Wykres przedstawiający rozkład masy w naczepie.
3. **Efektywność załadunku**: Metryki takie jak wykorzystanie przestrzeni i ładowności.
4. **Statystyki ogólne**: Podsumowanie wykonanego załadunku.

## Przewagi i ograniczenia

### Przewagi:
- **Adaptacyjność**: Model dostosowuje się do różnorodnych zestawów palet.
- **Odkrywanie nieoczywistych strategii**: Może znaleźć rozwiązania, które nie są oczywiste dla algorytmów deterministycznych.
- **Równoważenie wielu celów**: Może optymalizować jednocześnie wykorzystanie przestrzeni i rozkład masy.
- **Ulepszanie się z czasem**: Im więcej danych treningowych, tym lepsze wyniki.

### Ograniczenia:
- **Czas treningu**: Wymaga znacznego czasu treningu przed osiągnięciem dobrych wyników.
- **Duża przestrzeń stanów**: Dla złożonych problemów przestrzeń stanów może być zbyt duża do efektywnego przeszukania.
- **Niekoniecznie optymalne rozwiązania**: Nie gwarantuje znalezienia globalnie optymalnego rozwiązania.
- **Wymaga dostrojenia parametrów**: Efektywność zależy od właściwego doboru parametrów.

## Przyszłe rozszerzenia

Obecna implementacja może być rozszerzona na wiele sposobów:

1. **Zaawansowane techniki RL**: Zastosowanie głębokiego uczenia ze wzmocnieniem (Deep Q-Network, DQN) zamiast tabelarycznego Q-learningu.
2. **Bardziej szczegółowa reprezentacja stanów**: Uwzględnienie dodatkowych cech palet i naczepy.
3. **Priorytetyzacja doświadczeń**: Częstsze uczenie się z bardziej informatywnych doświadczeń.
4. **Transfer Learning**: Wykorzystanie wiedzy zdobytej na jednym typie zestawów palet do innych typów.
5. **Multi-agent RL**: Wiele agentów współpracujących przy załadunku.
6. **Obsługa ograniczeń czasu dostawy**: Uwzględnienie kolejności rozładunku w optymalizacji.
7. **Interfejs do ręcznej modyfikacji parametrów treningu**: Umożliwienie użytkownikowi dostrajania parametrów bez modyfikacji kodu. 