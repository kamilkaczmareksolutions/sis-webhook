# Logowanie zdarzeń z Brevo do Notion dla Joli

Ten projekt zastępuje workflow z n8n, który przestał działać. Jego celem jest nasłuchiwanie na zdarzenia e-mailowe z **Brevo** (np. otwarcia, kliknięcia) za pomocą webhooka i logowanie tych informacji w czasie rzeczywistym w dedykowanej bazie danych w **Notion**. Dzięki temu Jola ma zawsze aktualną listę interakcji klientów i wie, do kogo powinna zadzwonić.

Aplikacja została napisana w Pythonie przy użyciu frameworka Flask.

## Wymagania wstępne

1.  **Konto Brevo**: Potrzebujesz konta z dostępem do kluczy API i możliwością konfiguracji webhooków.
2.  **Konto Notion**: Potrzebujesz konta z możliwością tworzenia integracji i baz danych.
3.  **Python 3**: Upewnij się, że masz zainstalowanego Pythona w wersji 3.6 lub nowszej.

---

## 1. Konfiguracja Bazy Danych w Notion

Zanim uruchomisz aplikację, Twoja baza danych w Notion musi być odpowiednio przygotowana.

1.  **Stwórz nową integrację Notion**:
    *   Przejdź do [My Integrations](https://www.notion.so/my-integrations).
    *   Kliknij "New integration", nadaj jej nazwę (np. "Logi dla Joli") i skopiuj **Internal Integration Token**. Będzie to Twój `NOTION_API_KEY`.
2.  **Stwórz nową bazę danych w Notion**:
    *   Utwórz nową, pustą stronę w Notion i wybierz opcję "Database - Full page".
    *   Nadaj jej nazwę, np. "Baza dla Joli".
3.  **Udostępnij bazę danych integracji**:
    *   W prawym górnym rogu bazy danych kliknij ikonę trzech kropek (`...`), a następnie "Add connections" i wybierz swoją nowo utworzoną integrację.
4.  **Skonfiguruj kolumny w bazie danych**:
    Struktura bazy danych musi być **DOKŁADNIE** taka jak poniżej. Skrypt jest od niej w pełni zależny i będzie szukał kolumn o tych konkretnych nazwach i typach.

| Nazwa Kolumny   | Typ Danych (Type) | Opis                                                                       |
| --------------- | ----------------- | -------------------------------------------------------------------------- |
| **Contact**     | `Title`           | Główna kolumna, będzie tu imię i nazwisko lub email kontaktu.              |
| **EMAIL**       | `Email`           | Adres e-mail kontaktu (kluczowy do wyszukiwania).                          |
| **FIRSTNAME**   | `Rich text`       | Imię kontaktu (automatycznie pobierane z Brevo).                           |
| **LASTNAME**    | `Rich text`       | Nazwisko kontaktu (automatycznie pobierane z Brevo).                       |
| **SMS**         | `Phone`           | Numer telefonu (automatycznie pobierany z Brevo).                          |
| **DOSTARCZONO** | `Date`            | Wypełniane datą, gdy mail zostanie dostarczony.                            |
| **OTWARCIE**    | `Date`            | Wypełniane datą, gdy kontakt otworzy maila.                                |
| **KLIKNIĘTO**   | `Date`            | Wypełniane datą, gdy kontakt kliknie link w mailu.                         |
| **BŁĘDNY EMAIL**| `Date`            | Wypełniane datą, gdy mail zostanie trwale odrzucony (hard bounce).         |
| **ZREZYGNOWAŁ** | `Date`            | Wypełniane datą, gdy kontakt wypisze się z listy.                          |
| **NOTATKI**     | `Rich text`       | Pole na dodatkowe notatki (nie jest używane przez ten skrypt).             |

5.  **Pobierz ID bazy danych**:
    *   Skopiuj link do swojej bazy danych. Będzie wyglądał mniej więcej tak: `https://www.notion.so/twoja-nazwa/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx?v=...`
    *   Ciąg 32 znaków (`xxxxxxxx...`) to Twoje **ID bazy danych**. Będzie to Twój `NOTION_DATABASE_ID`.

---

## 2. Instalacja i uruchomienie lokalne (do testów)

1.  **Pobierz pliki**:
    Upewnij się, że masz wszystkie pliki z tego projektu w jednym folderze:
    *   `jola_webhook_handler.py`
    *   `requirements.txt`
    *   `.env.example`

2.  **Utwórz środowisko wirtualne** (zalecane):
    ```bash
    python -m venv venv
    venv\Scripts\activate  # Na Windows
    # source venv/bin/activate  # Na macOS/Linux
    ```

3.  **Zainstaluj zależności**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Skonfiguruj zmienne środowiskowe**:
    *   Zmień nazwę pliku `.env.example` na `.env`.
    *   Otwórz plik `.env` i wklej swoje klucze API oraz ID bazy danych, które uzyskałeś w poprzednich krokach.
      ```
      NOTION_API_KEY="secret_xxxxxxxxxxxxxxxxxxxxxxxxxx"
      NOTION_DATABASE_ID="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
      BREVO_API_KEY="xkeysib-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
      ```

5.  **Uruchom serwer testowy**:
    ```bash
    python jola_webhook_handler.py
    ```
    Jeśli wszystko poszło dobrze, zobaczysz informację, że serwer działa pod adresem `http://127.0.0.1:5000`.

---

## 3. Wdrożenie na PythonAnywhere

Aby webhook był dostępny publicznie i działał 24/7, musimy go umieścić na serwerze. PythonAnywhere jest do tego idealny.

1.  **Załóż konto na PythonAnywhere**:
    Wybierz darmowy plan "Beginner".

2.  **Prześlij pliki na serwer**:
    *   W panelu PythonAnywhere przejdź do zakładki "Files".
    *   Prześlij pliki: `jola_webhook_handler.py` i `requirements.txt`.

3.  **Skonfiguruj aplikację webową**:
    *   Przejdź do zakładki "Web".
    *   Kliknij "Add a new web app".
    *   Wybierz "Flask" jako framework oraz wersję Pythona (np. 3.10).
    *   PythonAnywhere automatycznie utworzy plik konfiguracyjny. Ścieżka do niego będzie widoczna na ekranie (np. `/var/www/twojanazwa_pythonanywhere_com_wsgi.py`). Kliknij na nią.

4.  **Edytuj plik konfiguracyjny WSGI**:
    *   Treść pliku będzie podobna do poniższej. Musisz upewnić się, że importuje on obiekt `app` z Twojego pliku. Zmień `flask_app` na `jola_webhook_handler` (nazwa Twojego pliku bez `.py`).

    ```python
    # Ten plik zawiera konfigurację do serwowania Twojej aplikacji przez serwer WSGI
    import sys

    # Dodaj ścieżkę do Twojego projektu do ścieżek systemowych
    path = '/home/TwojaNazwaUzytkownika/mysite'  # ZMIEŃ 'mysite' jeśli pliki są w innym folderze
    if path not in sys.path:
        sys.path.insert(0, path)

    # ZMIEŃ 'flask_app' na nazwę Twojego pliku (bez .py)
    from jola_webhook_handler import app as application
    ```

5.  **Zainstaluj zależności na serwerze**:
    *   Otwórz nową konsolę "Bash" w zakładce "Consoles".
    *   Wpisz komendę (dostosowując wersję Pythona, jeśli trzeba):
      ```bash
      pip3.10 install --user -r requirements.txt
      ```

6.  **Ustaw zmienne środowiskowe**:
    *   **To najważniejszy krok! Nie przesyłaj pliku `.env`!**
    *   W zakładce "Web" znajdź sekcję "Code" i podsekcję "Environment variables".
    *   Dodaj trzy zmienne, jedna po drugiej:
      *   `NOTION_API_KEY` = `secret_xxxxxxxx...`
      *   `NOTION_DATABASE_ID` = `xxxxxxxx...`
      *   `BREVO_API_KEY` = `xkeysib-xxxxxxxx...`

7.  **Przeładuj aplikację**:
    *   Wróć na górę zakładki "Web" i kliknij duży, zielony przycisk "Reload ...".

Twoja aplikacja jest teraz dostępna online pod adresem `http://TwojaNazwaUzytkownika.pythonanywhere.com`. Adres URL webhooka to `http://TwojaNazwaUzytkownika.pythonanywhere.com/webhook`.

---

## 4. Konfiguracja Webhooka w Brevo

Ostatni krok to poinformowanie Brevo, gdzie ma wysyłać dane.

1.  W panelu Brevo przejdź do "Settings" -> "Webhooks" (lub znajdź przez wyszukiwarkę w ustawieniach).
2.  Kliknij "Add a new webhook".
3.  W polu "URL" wklej pełny adres Twojego webhooka na PythonAnywhere:
    `http://TwojaNazwaUzytkownika.pythonanywhere.com/webhook`
4.  W sekcji "When an event occurs on your **transactional emails**", zaznacz zdarzenia, które chcesz śledzić (np. `Delivered`, `Opened`, `Clicked`, `Hard-bounce`, `Unsubscribed`).
5.  Zapisz webhooka.

Od teraz wszystkie zaznaczone zdarzenia będą wysyłane do Twojej aplikacji i logowane w Notion. Możesz sprawdzić logi w PythonAnywhere (w zakładce "Web" są linki do "error log" i "server log"), aby monitorować, czy wszystko działa poprawnie. 