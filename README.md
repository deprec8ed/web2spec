# Web2Spec

Web2Spec to proof-of-concept pipeline, który crawluje żywą stronę internetową, wyciąga z niej maszynowo czytelną mapę interakcji, przekształca każdą stronę do formy przyjaznej dla LLM i używa modeli multimodalnych do generowania dokumentacji produktowej.

## Co robi ten PoC

1. Używa Playwright do crawlowania dynamicznych stron w trybie headless.
2. Wyciąga semantyczną strukturę UI z elementów `<a>`, `<button>`, `<input>`, `<form>` i `<nav>`.
3. Buduje ograniczoną mapę wewnętrznych linków.
4. Generuje oczyszczony markdown i zrzuty ekranu dla każdej odwiedzonej strony.
5. Opcjonalnie rysuje obramowania elementów na zrzutach ekranu.
6. Przyjmuje opcjonalny kontekst biznesowy, aby lepiej ukierunkować analizę LLM.
7. Wysyła markdown i zrzut ekranu do Azure OpenAI, OpenAI lub Claude w celu wygenerowania:
   - dokumentacji funkcjonalnej
   - historii użytkownika
   - mapy intencji CTA
8. Składa finalne artefakty `report.md`, `dashboard.html`, `site_map.json` i `analysis.json`.

## Instalacja

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python -m playwright install chromium
```

Jeżeli pobranie przeglądarki przez Playwright nie działa na Twojej maszynie, crawler może użyć lokalnie zainstalowanej przeglądarki. Repo automatycznie wykrywa `/Applications/Google Chrome.app` i `/Applications/Chromium.app` na macOS. Możesz też jawnie ustawić `--browser-channel chrome`.

## Zmienne środowiskowe

Przed uruchomieniem analizy ustaw jedną z poniższych konfiguracji:

```bash
export AZURE_API_KEY=...
export AZURE_BASE_URL="https://<resource>.openai.azure.com/openai/v1"
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...
```

Azure OpenAI jest domyślnym dostawcą. Domyślny model to `gpt-5.4`, co powinno odpowiadać nazwie wdrożenia w Azure. Jeżeli chcesz użyć drugiego deploymentu, ustaw `--model gpt-5`.

## Użycie

```bash
source .venv/bin/activate
export AZURE_API_KEY="key-here"
export AZURE_BASE_URL="https://oai-hackathon-tst-swecen-001.openai.azure.com/openai/v1"

web2spec https://example.com \
  --depth-limit 2 \
  --provider azure-openai \
  --model gpt-5.4 \
  --locale pl \
  --business-context "Platforma SaaS B2B do planowania produktu i analizy." \
  --output-dir outputs/example
```

Przydatne flagi:

- `--skip-analysis`: pomija fazę analizy przez LLM.
- `--provider openai`: używa publicznego OpenAI API.
- `--provider anthropic`: używa Anthropic.
- `--model ...`: nadpisuje nazwę modelu.
- `--locale pl|en`: przełącza język wygenerowanych artefaktów i odpowiedzi modelu.
- `--browser-channel chrome`: używa lokalnie zainstalowanego Chrome zamiast przeglądarki zarządzanej przez Playwright.
- `--browser-executable-path /path/to/browser`: jawna ścieżka do przeglądarki.
- `--no-overlay`: pomija generowanie nakładek z obramowaniami.
- `--max-pages 20`: ogranicza liczbę stron w kolejce dla PoC.
- `--business-context-file site_context.md`: wczytuje kontekst biznesowy z pliku.
- `--quiet`: ukrywa logi postępu.

## Układ wyników

```text
outputs/example/
  analysis.json
  dashboard.html
  report.md
  site_map.json
  markdown/
  screenshots/
  overlays/
```

## Uwagi

- Crawler pozostaje wewnątrz domeny startowej.
- Głębokość liczona jest od adresu startowego jako poziom `0`.
- Prompt LLM wymusza odpowiedź w formacie JSON i zabrania wymyślania funkcji niewidocznych na stronie.
- Generowanie overlay jest opcjonalne i działa tylko wtedy, gdy dostępny jest Pillow.

## Jak uruchomić crawl

1. Utwórz i aktywuj środowisko wirtualne:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Zainstaluj zależności:

```bash
python -m pip install -e .[dev]
python -m playwright install chromium
```

3. Ustaw dane dostępowe Azure OpenAI:

```bash
export AZURE_API_KEY="key-here"
export AZURE_BASE_URL="https://oai-hackathon-tst-swecen-001.openai.azure.com/openai/v1"
```

4. Przygotuj krótki kontekst biznesowy. Możesz zacząć od `site_context.example.md`.

5. Uruchom crawler:

```bash
web2spec https://target-site.example \
  --provider azure-openai \
  --model gpt-5.4 \
  --depth-limit 2 \
  --max-pages 15 \
  --business-context-file site_context.example.md \
  --output-dir outputs/target-site
```

6. Sprawdź wyniki:

- `outputs/target-site/dashboard.html`
- `outputs/target-site/report.md`
- `outputs/target-site/site_map.json`
- `outputs/target-site/analysis.json`

Jeżeli Playwright-managed Chromium jest niedostępny, możesz dalej działać na lokalnym Chrome lub Chromium.

## Sugerowany workflow

1. Napisz krótki `site_context.md`, który opisuje czym zajmuje się firma, kim są użytkownicy i jakie są cele konwersji.
2. Uruchom crawler na małej głębokości.
3. Przejrzyj `report.md` lub `dashboard.html` pod kątem halucynacji, brakujących flow i jakości interpretacji CTA.
4. Zwiększ głębokość albo doprecyzuj kontekst biznesowy, jeżeli pierwszy przebieg jest zbyt ogólny.

## Który plik traktować jako bazowy artefakt dokumentacyjny?

Każdy wynik ma inne zastosowanie:

- `site_map.json`: strukturalne źródło prawdy. Tu znajduje się surowy wynik crawla, semantyczne elementy, linki, nagłówki i ścieżki do obrazów.
- `markdown/*.md`: najlepsza strona-baza przed analizą LLM. To właśnie ten oczyszczony markdown trafia do modelu.
- `analysis.json`: najlepszy ustrukturyzowany artefakt po analizie LLM. Używaj go, jeśli chcesz dalej programowo konsumować wygenerowaną dokumentację.
- `report.md`: najlepsza czytelna forma tekstowa dla człowieka.
- `dashboard.html`: najlepsza forma wizualnego przeglądu.

Jeżeli pytanie brzmi: „jaki jeden strukturalny artefakt powinien być bazą dalszej dokumentacji?”, to zwykle odpowiedź jest taka:

1. `analysis.json`, jeśli chcesz korzystać z już wygenerowanej dokumentacji.
2. `site_map.json`, jeśli chcesz używać surowego wyniku crawla jako źródła prawdy i budować własną warstwę dokumentacyjną.

## Gdzie zmieniać to, co jest analizowane?

Są trzy główne miejsca:

- `src/web2spec/cartographer.py`
  Steruje tym, co jest wyciągane z żywej strony.
  Edytuj `EXTRACTION_SCRIPT`, jeśli chcesz pobierać więcej elementów DOM, inne atrybuty albo dodatkowe metadane strony.

- `src/web2spec/distiller.py`
  Steruje tym, jak surowa struktura jest zamieniana na oczyszczony markdown.
  Edytuj ten plik, jeśli chcesz:
  - zachować więcej lub mniej linków
  - dołączyć więcej kontekstu tekstowego
  - inaczej streszczać nawigację
  - zmienić układ i sekcje markdownu

- `src/web2spec/analyst.py`
  Steruje etapem rozumowania przez LLM.
  Edytuj `SYSTEM_PROMPT`, jeśli chcesz zmienić to, co model ma wywnioskować i w jakiej formie ma to zwrócić.
  Edytuj `_build_prompt()`, jeśli chcesz dosłać modelowi dodatkowy kontekst.

## Gdzie zmieniać to, co jest zwracane?

Jeżeli chcesz dodać nową sekcję do zwracanej dokumentacji, na przykład:

- kryteria akceptacji
- ryzyka
- notatki deweloperskie
- sugestie testów
- inwentaryzację komponentów

to zmień te miejsca razem:

1. `src/web2spec/models.py`
   Dodaj nowe pole do `PageAnalysis` i, jeśli trzeba, nowy dataclass podobny do `CTAIntent`.

2. `src/web2spec/analyst.py`
   Zaktualizuj `SYSTEM_PROMPT`, aby model wiedział, że ma zwrócić nowe pole.
   Zaktualizuj `analyze()`, aby parser potrafił odczytać to pole z JSON-a.

3. `src/web2spec/report.py`
   Zaktualizuj `build_report()`, aby nowe pole pojawiło się w `report.md`.
   Zaktualizuj `write_dashboard()`, jeśli ma się też pojawić w `dashboard.html`.

4. Opcjonalnie `tests/`
   Dodaj lub popraw testy, żeby nowy kształt odpowiedzi był objęty weryfikacją.

Krótko: schema modelu, parser i renderery wyników muszą pozostać ze sobą zgodne.

## Guardrail przeciw analizie tej samej strony dwa razy

Pipeline ma już zabezpieczenie przed podwójną analizą tej samej strony.

Działa ono w trzech krokach:

1. `src/web2spec/utils.py`
   `canonicalize_url()` normalizuje URL przed użyciem go w pętli crawla.
   To właśnie scala przypadki takie jak `https://docs.qmk.fm` i `https://docs.qmk.fm/`.

2. `src/web2spec/pipeline.py`
   Pętla utrzymuje zbiór `visited`. Jeżeli kanoniczny URL został już przetworzony, nie zostanie przetworzony drugi raz.

3. `src/web2spec/pipeline.py`
   Przed dodaniem nowo znalezionych linków do kolejki pipeline sprawdza też `queued_urls`, więc ta sama strona nie zostanie dodana wielokrotnie zanim zostanie odwiedzona.

Ważne ograniczenie:

- Różne query stringi są obecnie traktowane jako różne strony.
- Jeśli ten sam content jest dostępny pod wieloma rzeczywiście różnymi URL-ami, mogą one nadal zostać przeskanowane osobno, dopóki nie dodasz mocniejszych zasad kanonikalizacji.

## Szczegółowy przebieg procesu

Poniżej pełny pipeline krok po kroku.

### 1. Parsowanie wejścia CLI

Plik:

- `src/web2spec/cli.py`

Co się dzieje:

- Użytkownik podaje URL startowy i opcjonalne flagi, takie jak głębokość, provider, model, katalog wynikowy i kontekst biznesowy.
- CLI buduje obiekt `RunConfig`.
- Konfiguracja trafia do głównego pipeline.

Dlaczego to ważne:

- To tutaj kontrolujesz zachowanie programu bez zmiany kodu.

### 2. Inicjalizacja stanu pipeline

Plik:

- `src/web2spec/pipeline.py`

Co się dzieje:

- Startowy URL jest kanonikalizowany.
- Tworzony jest katalog wynikowy.
- Pipeline inicjalizuje:
  - kolejkę oczekujących URL-i
  - zbiór odwiedzonych stron
  - kolekcję stron
  - kolekcję analiz
  - listę błędów

Dlaczego to ważne:

- To warstwa orkiestracji.
- Kontroluje pętlę crawlowania, deduplikację i generowanie wyników.

### 3. Playwright uruchamia kontekst przeglądarki

Plik:

- `src/web2spec/cartographer.py`

Co się dzieje:

- Startuje Playwright.
- Uruchamiana jest kompatybilna przeglądarka Chromium.
- Projekt preferuje lokalnie zainstalowane Chromium lub Chrome, jeśli są dostępne.
- Tworzony jest kontekst przeglądarki z określonym viewportem.

Dlaczego to ważne:

- To pozwala obsługiwać dynamiczne SPA, zamiast tylko pobierać statyczny HTML.

### 4. Przejście na stronę

Plik:

- `src/web2spec/cartographer.py`

Co się dzieje:

- Crawler otwiera stronę z kolejki.
- Nawigacja używa bardziej odpornej strategii niż ścisłe `networkidle`:
  - najpierw `domcontentloaded`
  - potem `load`
  - na końcu krótki `networkidle`, jeśli jest osiągalny

Dlaczego to ważne:

- Wiele stron nigdy nie osiąga stabilnego `networkidle`.
- To poprawia odporność na realnych stronach dokumentacyjnych i SPA.

### 5. Semantyczna ekstrakcja w przeglądarce

Plik:

- `src/web2spec/cartographer.py`

Co się dzieje:

- `EXTRACTION_SCRIPT` wykonuje się w kontekście strony.
- Wyciąga:
  - tytuł
  - nagłówki
  - semantyczne elementy interaktywne
  - metadane takie jak `aria-label`, `id`, `name`, `placeholder`, `type`
  - przybliżone współrzędne DOM przez bounding boxy

Dlaczego to ważne:

- To surowa warstwa strukturalna crawla.
- Ignoruje większość stylowania i skupia się na elementach istotnych behawioralnie.

### 6. Normalizacja i filtrowanie linków wewnętrznych

Pliki:

- `src/web2spec/cartographer.py`
- `src/web2spec/utils.py`

Co się dzieje:

- Linki są rozwijane względem bieżącej strony.
- Fragmenty są usuwane.
- Linki zewnętrzne nie są używane do rekursji.
- Kanoniczne URL-e są używane do unikania duplikatów w kolejce.

Dlaczego to ważne:

- W ten sposób budowana jest mapa strony.
- To też główny guardrail przeciw recrawlowaniu tej samej strony pod trywialnie różnymi URL-ami.

### 7. Generowanie zrzutu ekranu i opcjonalnej nakładki

Pliki:

- `src/web2spec/cartographer.py`
- `src/web2spec/distiller.py`

Co się dzieje:

- Zapisywany jest pełny zrzut ekranu strony.
- Jeśli overlay jest włączony, obramowania elementów semantycznych są rysowane na kopii zrzutu.

Dlaczego to ważne:

- Zrzut ekranu daje modelowi multimodalnemu kontekst wizualny.
- Nakładka pomaga człowiekowi zweryfikować, czy ekstrakcja mniej więcej odpowiada temu, co widać.

### 8. Distiller zamienia surową strukturę na markdown przyjazny dla LLM

Plik:

- `src/web2spec/distiller.py`

Co się dzieje:

- Surowe elementy są oczyszczane i deduplikowane.
- Duże bloki nawigacji są kompresowane.
- Liczba linków jest ograniczana, aby zmniejszyć szum tokenowy.
- Powstaje ustrukturyzowany markdown zapisywany do katalogu `markdown/`.

Dlaczego to ważne:

- To główna warstwa kontroli tokenów.
- Lepsza distylacja zwykle poprawia jakość analizy bardziej niż samo grzebanie w promptach.

### 9. Analyst wysyła markdown i zrzut ekranu do LLM

Plik:

- `src/web2spec/analyst.py`

Co się dzieje:

- Prompt jest budowany z:
  - URL-a strony
  - tytułu
  - klucza szablonu
  - opcjonalnego kontekstu biznesowego
  - oczyszczonego markdownu
- Do promptu dołączany jest zrzut ekranu.
- Model jest instruowany, by zwrócić wyłącznie JSON.

Dlaczego to ważne:

- To warstwa rozumowania.
- Jeśli chcesz innego rodzaju wyników dokumentacyjnych, to jest główne miejsce zmian.

### 10. Odpowiedź JSON jest parsowana do typu analizy

Pliki:

- `src/web2spec/analyst.py`
- `src/web2spec/models.py`

Co się dzieje:

- Odpowiedź modelu jest parsowana jako JSON.
- Zostaje zamieniona na obiekt `PageAnalysis`, który zawiera:
  - `functional_documentation`
  - `user_stories`
  - `intent_map`
  - `raw_response`

Dlaczego to ważne:

- To kontrakt między LLM a resztą aplikacji.
- Jeśli schema się zmienia, parser i renderery też muszą się zmienić.

### 11. Pętla crawla dodaje kolejne strony

Plik:

- `src/web2spec/pipeline.py`

Co się dzieje:

- Pipeline bierze linki wewnętrzne z aktualnej strony.
- Dodaje nowe kanoniczne URL-e do kolejki, jeśli:
  - nie są już odwiedzone
  - nie są już w kolejce
  - nie przekraczają limitu głębokości
  - nie przekraczają limitu `max-pages`

Dlaczego to ważne:

- W ten sposób działa rekursja.
- W ten sposób PoC pozostaje ograniczony i przewidywalny.

### 12. Zapisywane są finalne artefakty

Pliki:

- `src/web2spec/report.py`
- `src/web2spec/pipeline.py`

Co się dzieje:

- `site_map.json` powstaje z surowych snapshotów stron.
- `analysis.json` powstaje z sparsowanych wyników LLM.
- `report.md` powstaje jako czytelne podsumowanie tekstowe.
- `dashboard.html` powstaje jako wizualny interfejs przeglądowy.

Dlaczego to ważne:

- To warstwa przekazania wyników użytkownikowi i ewentualnym systemom downstream.

## Mapa plików

Jeśli chcesz coś szybko zmienić, to najkrótsza mapa wygląda tak:

- `src/web2spec/cli.py`: flagi runtime i wejście użytkownika
- `src/web2spec/config.py`: domyślne ustawienia konfiguracji
- `src/web2spec/utils.py`: normalizacja URL-i i współdzielone helpery
- `src/web2spec/cartographer.py`: crawl przeglądarkowy i ekstrakcja semantyczna
- `src/web2spec/distiller.py`: kształt markdownu i redukcja szumu
- `src/web2spec/analyst.py`: prompty, wywołania modeli i parser odpowiedzi
- `src/web2spec/models.py`: kontrakty danych
- `src/web2spec/pipeline.py`: pętla crawla, deduplikacja, rekursja, logi postępu
- `src/web2spec/report.py`: końcowe pliki wynikowe i generowanie dashboardu
