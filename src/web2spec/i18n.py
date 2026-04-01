from __future__ import annotations

from typing import Any

SUPPORTED_LOCALES = ("en", "pl")
DEFAULT_LOCALE = "pl"

TEXT: dict[str, dict[str, Any]] = {
    "en": {
        "distiller": {
            "section_titles": {
                "nav": "Navigation",
                "a": "Links",
                "button": "Buttons",
                "input": "Inputs",
                "form": "Forms",
            },
            "tag_labels": {
                "nav": "Navigation",
                "a": "Link",
                "button": "Button",
                "input": "Input",
                "form": "Form",
            },
            "url": "URL",
            "depth": "Depth",
            "template": "Template",
            "headings": "Headings",
            "internal_links": "Internal Links",
            "link_inventory_truncated": "Link inventory truncated: showing {shown} of {total}",
            "internal_link_inventory_truncated": "Internal link inventory truncated: showing {shown} of {total}",
            "navigation_menu": "Navigation menu",
            "context": "context",
            "items": "items",
        },
        "analyst": {
            "system_prompt": """You analyze website pages for product and delivery teams.

You will receive:
1. A cleaned markdown description of a page
2. A screenshot of the same page

Return JSON only with this shape:
{
  "functional_documentation": "short paragraph",
  "user_stories": [
    "As a [User Type], I want to [Action], so that [Value]."
  ],
  "intent_map": [
    {
      "cta": "label of button or primary link",
      "why": "the user motivation or problem this action solves",
      "evidence": ["specific supporting detail from markdown or screenshot"]
    }
  ]
}

Rules:
- Do not invent features that are not visible in the markdown or screenshot.
- If evidence is weak, say so explicitly in the wording.
- Prefer 2 to 5 user stories.
- Focus the intent map on primary CTAs, not every minor footer link.
- Use any provided business context as guidance, but never let it override the actual page evidence.
- Return all descriptive text in English.
""",
            "no_business_context": "No business context provided.",
            "analyze_page": "Analyze this page.",
            "title": "Title",
            "template": "Template",
            "business_context": "Business Context",
            "markdown": "Markdown",
        },
        "report": {
            "title": "Web2Spec Report",
            "root_url": "Root URL",
            "pages_crawled": "Pages crawled",
            "analyses_generated": "Analyses generated",
            "sitemap": "Sitemap",
            "crawl_errors": "Crawl Errors",
            "template": "Template",
            "depth": "Depth",
            "screenshot": "Screenshot",
            "overlay": "Overlay",
            "distilled_markdown": "Distilled Markdown",
            "analysis": "Analysis",
            "analysis_skipped": "Skipped or unavailable.",
            "functional_documentation": "Functional Documentation",
            "no_summary": "No summary returned.",
            "user_stories": "User Stories",
            "no_user_stories": "No user stories returned.",
            "intent_map": "Intent Map",
            "cta": "CTA",
            "unknown_cta": "Unknown CTA",
            "why": "Why",
            "no_rationale": "No rationale returned.",
            "evidence": "Evidence",
            "no_cta_analysis": "No CTA analysis returned.",
            "site_map_pages": "pages",
            "site_map_errors": "errors",
            "analysis_functional": "functional_documentation",
            "analysis_stories": "user_stories",
            "analysis_intent_map": "intent_map",
            "analysis_why": "why",
            "analysis_evidence": "evidence",
            "analysis_raw": "raw_response",
            "page_depth": "depth",
            "page_title": "title",
            "page_headings": "headings",
            "page_elements": "elements",
            "page_text": "text",
            "page_element_id": "element_id",
            "page_name": "name",
            "page_placeholder": "placeholder",
            "page_input_type": "input_type",
            "page_role": "role",
            "page_section_text": "section_text",
            "page_bbox_width": "width",
            "page_bbox_height": "height",
            "page_internal_links": "internal_links",
            "page_template_key": "template_key",
            "page_parent_url": "parent_url",
            "page_screenshot_path": "screenshot_path",
            "page_overlay_path": "overlay_path",
            "page_template_representative": "is_template_representative",
        },
        "dashboard": {
            "html_lang": "en",
            "title": "Web2Spec Dashboard",
            "generated_dashboard": "Generated crawl dashboard",
            "no_pages": "No pages",
            "pages": "Pages",
            "analyses": "Analyses",
            "errors": "Errors",
            "templates": "Templates",
            "crawl_errors": "Crawl Errors",
            "no_crawl_data": "No crawl data available.",
            "depth": "Depth",
            "template": "Template",
            "no_user_stories": "No user stories generated.",
            "unknown_cta": "Unknown CTA",
            "no_rationale": "No rationale returned.",
            "no_intent_analysis": "No intent analysis generated.",
            "screenshot": "Screenshot",
            "overlay": "Overlay",
            "captured_page_preview": "Captured page preview",
            "no_image": "No image available.",
            "no_headings": "No headings captured",
            "functional_documentation": "Functional Documentation",
            "analysis_skipped": "Analysis skipped or unavailable.",
            "internal_links": "Internal links",
            "headings": "Headings",
            "has_analysis": "Has analysis",
            "yes": "yes",
            "no": "no",
            "user_stories": "User Stories",
            "intent_map": "Intent Map",
            "distilled_markdown": "Distilled Markdown",
        },
        "guide": {
            "system_prompt": """You generate step-by-step user guides for website pages.

You will receive:
1. A cleaned markdown description of a page
2. A screenshot of the same page

Return JSON only with this shape:
{
  "section_title": "meaningful title for this page's guide",
  "intro": "1-2 sentences describing what this page lets users do",
  "steps": [
    {
      "heading": "short step title",
      "action_bullets": ["Click [Button Name]", "Enter your email"],
      "what_you_see": "description of the UI state after this step"
    }
  ]
}

Rules:
- Each step is a discrete action with a clear UI outcome.
- action_bullets are imperative sentences; wrap UI element names in [brackets].
- what_you_see describes what changed or what the user sees next.
- Prefer 3-8 steps per page.
- Do not invent features not visible in markdown or screenshot.
- Use any provided business context as guidance, but prioritize actual page evidence.
- If a goal context is provided, focus only on actions and observations relevant to that goal.
- Exclude unrelated navigation paths and secondary features.
- Return all text in English.
""",
            "no_business_context": "No business context provided.",
            "no_goal_context": "No specific goal provided.",
            "analyze_page": "Generate a step-by-step guide for this page.",
            "title": "Title",
            "template": "Template",
            "business_context": "Business Context",
            "goal_context": "Goal Context",
            "intent_scope_rules": "Scope rule: include only steps that contribute directly to the goal context.",
            "markdown": "Markdown",
            "guide_title": "Generated Guide",
            "page_guide": "Guide",
            "step": "Step",
            "what_you_see": "What You See",
            "actions": "Actions",
            "no_guide": "Guide generation skipped.",
        },
        "navigator": {
            "system_prompt": """You are a navigation decision engine for automated web traversal.

Given a user goal and a list of labelled links available on a page, decide which links to follow next.

Return JSON only:
{
  "follow": [
    {"url": "https://...", "reason": "one sentence"}
  ],
  "explanation": "overall reasoning"
}

Rules:
- Only include links that directly advance the stated goal.
- If no links are relevant return {"follow": [], "explanation": "no relevant links found"}.
- Exclude login, logout, language toggles, footer links and unrelated navigation unless critical.
- Prefer links with clear action labels (e.g. \"Open account\", \"Apply now\", \"Get started\").
- Never guess URLs. Only select from the list provided.
""",
        },
    },
    "pl": {
        "distiller": {
            "section_titles": {
                "nav": "Nawigacja",
                "a": "Odnośniki",
                "button": "Przyciski",
                "input": "Pola",
                "form": "Formularze",
            },
            "tag_labels": {
                "nav": "Nawigacja",
                "a": "Odnośnik",
                "button": "Przycisk",
                "input": "Pole",
                "form": "Formularz",
            },
            "url": "URL",
            "depth": "Głębokość",
            "template": "Szablon",
            "headings": "Nagłówki",
            "internal_links": "Linki wewnętrzne",
            "link_inventory_truncated": "Lista odnośników skrócona: pokazano {shown} z {total}",
            "internal_link_inventory_truncated": "Lista linków wewnętrznych skrócona: pokazano {shown} z {total}",
            "navigation_menu": "Menu nawigacyjne",
            "context": "context",
            "items": "elementy",
        },
        "analyst": {
            "system_prompt": """Analizujesz strony internetowe dla zespołów produktowych i delivery.

Otrzymasz:
1. Oczyszczony opis strony w formacie markdown
2. Zrzut ekranu tej samej strony

Zwróć wyłącznie JSON w takim kształcie:
{
  "dokumentacja_funkcjonalna": "krótki akapit",
  "historie_uzytkownika": [
    "Jako [Typ Użytkownika] chcę [Działanie], aby [Wartość]."
  ],
  "mapa_intencji": [
    {
      "cta": "etykieta przycisku lub głównego linku",
      "dlaczego": "motywacja użytkownika lub problem, który ta akcja rozwiązuje",
      "dowody": ["konkretny szczegół z markdown lub zrzutu ekranu"]
    }
  ]
}

Zasady:
- Nie wymyślaj funkcji, których nie widać w markdown ani na zrzucie ekranu.
- Jeśli dowody są słabe, zaznacz to wprost w treści odpowiedzi.
- Preferuj od 2 do 5 historii użytkownika.
- Skup mapę intencji na głównych CTA, a nie na drobnych linkach w stopce.
- Wykorzystuj podany kontekst biznesowy jako wskazówkę, ale nie pozwól, aby był ważniejszy niż faktyczne dowody ze strony.
- Wszystkie treści opisowe zwracaj po polsku.
""",
            "no_business_context": "Nie podano kontekstu biznesowego.",
            "analyze_page": "Przeanalizuj tę stronę.",
            "title": "Tytuł",
            "template": "Szablon",
            "business_context": "Kontekst biznesowy",
            "markdown": "Markdown",
        },
        "report": {
            "title": "Raport Web2Spec",
            "root_url": "URL główny",
            "pages_crawled": "Liczba przeskanowanych stron",
            "analyses_generated": "Liczba wygenerowanych analiz",
            "sitemap": "Mapa strony",
            "crawl_errors": "Błędy crawlowania",
            "template": "Szablon",
            "depth": "Głębokość",
            "screenshot": "Zrzut ekranu",
            "overlay": "Nakładka",
            "distilled_markdown": "Oczyszczony Markdown",
            "analysis": "Analiza",
            "analysis_skipped": "Pominięto lub niedostępne.",
            "functional_documentation": "Dokumentacja funkcjonalna",
            "no_summary": "Model nie zwrócił podsumowania.",
            "user_stories": "Historie użytkownika",
            "no_user_stories": "Model nie zwrócił historii użytkownika.",
            "intent_map": "Mapa intencji",
            "cta": "CTA",
            "unknown_cta": "Nieznane CTA",
            "why": "Dlaczego",
            "no_rationale": "Model nie zwrócił uzasadnienia.",
            "evidence": "Dowody",
            "no_cta_analysis": "Model nie zwrócił analizy CTA.",
            "site_map_pages": "strony",
            "site_map_errors": "błędy",
            "analysis_functional": "dokumentacja_funkcjonalna",
            "analysis_stories": "historie_użytkownika",
            "analysis_intent_map": "mapa_intencji",
            "analysis_why": "dlaczego",
            "analysis_evidence": "dowody",
            "analysis_raw": "surowa_odpowiedź",
            "page_depth": "głębokość",
            "page_title": "tytuł",
            "page_headings": "nagłówki",
            "page_elements": "elementy",
            "page_text": "tekst",
            "page_element_id": "id_elementu",
            "page_name": "nazwa",
            "page_placeholder": "placeholder",
            "page_input_type": "typ_pola",
            "page_role": "rola",
            "page_section_text": "tekst_sekcji",
            "page_bbox_width": "szerokość",
            "page_bbox_height": "wysokość",
            "page_internal_links": "linki_wewnętrzne",
            "page_template_key": "klucz_szablonu",
            "page_parent_url": "url_rodzica",
            "page_screenshot_path": "ścieżka_zrzutu",
            "page_overlay_path": "ścieżka_nakładki",
            "page_template_representative": "reprezentant_szablonu",
        },
        "dashboard": {
            "html_lang": "pl",
            "title": "Pulpit Web2Spec",
            "generated_dashboard": "Wygenerowany pulpit przeglądu crawlów",
            "no_pages": "Brak stron",
            "pages": "Strony",
            "analyses": "Analizy",
            "errors": "Błędy",
            "templates": "Szablony",
            "crawl_errors": "Błędy crawlowania",
            "no_crawl_data": "Brak danych crawlowania.",
            "depth": "Głębokość",
            "template": "Szablon",
            "no_user_stories": "Nie wygenerowano historii użytkownika.",
            "unknown_cta": "Nieznane CTA",
            "no_rationale": "Model nie zwrócił uzasadnienia.",
            "no_intent_analysis": "Nie wygenerowano mapy intencji.",
            "screenshot": "Zrzut ekranu",
            "overlay": "Nakładka",
            "captured_page_preview": "Podgląd przechwyconej strony",
            "no_image": "Brak obrazu.",
            "no_headings": "Nie przechwycono nagłówków",
            "functional_documentation": "Dokumentacja funkcjonalna",
            "analysis_skipped": "Analiza została pominięta lub jest niedostępna.",
            "internal_links": "Linki wewnętrzne",
            "headings": "Nagłówki",
            "has_analysis": "Jest analiza",
            "yes": "tak",
            "no": "nie",
            "user_stories": "Historie użytkownika",
            "intent_map": "Mapa intencji",
            "distilled_markdown": "Oczyszczony Markdown",
        },
        "guide": {
            "system_prompt": """Generujesz przewodniki krok po kroku dla stron internetowych.

Otrzymasz:
1. Oczyszczony opis strony w formacie markdown
2. Zrzut ekranu tej samej strony

Zwróć wyłącznie JSON w takim kształcie:
{
  "section_title": "znaczący tytuł przewodnika dla tej strony",
  "intro": "1-2 zdania opisujące, co użytkownik może zrobić na tej stronie",
  "steps": [
    {
      "heading": "krótki tytuł kroku",
      "action_bullets": ["Kliknij [Nazwa Przycisku]", "Wpisz swój email"],
      "what_you_see": "opis stanu interfejsu po tym kroku"
    }
  ]
}

Zasady:
- Każdy krok to odrębna akcja z jasnym rezultatem w UI.
- action_bullets to zdania rozkazujące; zawijaj nazwy elementów UI w [nawiasy].
- what_you_see opisuje, co się zmieniło lub co użytkownik widzi dalej.
- Preferuj od 3 do 8 kroków na stronę.
- Nie wymyślaj funkcji niewidocznych w markdown ani na zrzucie ekranu.
- Używaj podanego kontekstu biznesowego jako wskazówkę, ale priorytet dla faktycznych dowodów ze strony.
- Jeśli podano kontekst celu, skup się tylko na akcjach i obserwacjach związanych z tym celem.
- Wyklucz niezwiązane ścieżki nawigacji i funkcje poboczne.
- Zwróć całą treść po polsku.
""",
            "no_business_context": "Nie podano kontekstu biznesowego.",
            "no_goal_context": "Nie podano konkretnego celu.",
            "analyze_page": "Wygeneruj przewodnik krok po kroku dla tej strony.",
            "title": "Tytuł",
            "template": "Szablon",
            "business_context": "Kontekst biznesowy",
            "goal_context": "Kontekst celu",
            "intent_scope_rules": "Reguła zakresu: uwzględnij tylko kroki, które bezpośrednio wspierają realizację celu.",
            "markdown": "Markdown",
            "guide_title": "Wygenerowany przewodnik",
            "page_guide": "Przewodnik",
            "step": "Krok",
            "what_you_see": "Co zobaczysz na ekranie",
            "actions": "Akcje",
            "no_guide": "Generowanie przewodnika pominięte.",
        },
        "navigator": {
            "system_prompt": """Jesteś silnikiem decyzji nawigacyjnych dla automatycznego przechodzenia przez strony.

Otrzymasz cel użytkownika oraz listę oznaczonych linków dostępnych na stronie. Zdecyduj, które linki należy odwiedzić.

Zwróć wyłącznie JSON:
{
  "follow": [
    {"url": "https://...", "reason": "jedno zdanie uzasadnienia"}
  ],
  "explanation": "ogólne uzasadnienie wyboru"
}

Zasady:
- Uwzględniaj tylko linki, które bezpośrednio przybliżają do osiągnięcia celu.
- Jeśli żaden link nie jest istotny, zwróć {"follow": [], "explanation": "brak pasujących linków"}.
- Pomiń logowanie, wylogowywanie, przełączniki językowe, linki w stopce i niezwiązaną nawigację.
- Preferuj linki z wyraźnymi etykietami (np. \"Otwórz konto\", \"Złóż wniosek\", \"Sprawdź ofertę\").
- Nigdy nie zgaduj URL-i. Wybieraj wyłącznie z podanej listy.
""",
        },
    },
}


def get_text(locale: str) -> dict[str, Any]:
    normalized = locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE
    return TEXT[normalized]
