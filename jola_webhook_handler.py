import os
import requests
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from datetime import datetime
import pytz

# Załaduj zmienne środowiskowe z pliku .env
load_dotenv()

# --- Konfiguracja ---
# Pobierz zmienne środowiskowe
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
BREVO_API_KEY = os.getenv("BREVO_API_KEY")

# Sprawdź, czy kluczowe zmienne są ustawione
if not NOTION_API_KEY or not NOTION_DATABASE_ID:
    raise ValueError("Brak klucza NOTION_API_KEY lub NOTION_DATABASE_ID w zmiennych środowiskowych.")

# Nagłówki dla zapytań do Notion API
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# Nagłówki dla zapytań do Brevo API
BREVO_HEADERS = {
    "accept": "application/json",
    "api-key": BREVO_API_KEY
}

# DOKŁADNE mapowanie zdarzeń Brevo na nazwy kolumn w Notion
EVENT_TO_COLUMN_MAP = {
    'delivered': 'DOSTARCZONO',
    'unique_opened': 'OTWARCIE',
    'opened': 'OTWARCIE',
    'click': 'KLIKNIĘTO',
    'clicked': 'KLIKNIĘTO',
    'hard_bounce': 'BŁĘDNY EMAIL',
    'unsubscribed': 'ZREZYGNOWAŁ',
}

app = Flask(__name__)

# --- Dodatkowy endpoint dla weryfikacji ---
@app.route('/', methods=['GET'])
def index():
    """Wyświetla prosty komunikat, aby potwierdzić, że serwer działa."""
    return "<h1>WERSJA 3 - UPROSZCZONA.</h1><p>Webhook działa bez logiki scoringu.</p>"

# --- Funkcje pomocnicze dla Notion ---

def search_contact_in_notion(email):
    """Wyszukuje kontakt w bazie Notion po adresie email w kolumnie 'EMAIL'."""
    search_url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    query = {
        "filter": {
            "property": "EMAIL",
            "email": {
                "equals": email
            }
        }
    }
    try:
        response = requests.post(search_url, headers=NOTION_HEADERS, json=query)
        response.raise_for_status()
        data = response.json()
        return data["results"][0] if data.get("results") else None
    except requests.exceptions.RequestException as e:
        print(f"Błąd podczas wyszukiwania w Notion: {e}")
        return None

def create_contact_in_notion(contact_details):
    """Tworzy nowy kontakt w bazie Notion zgodnie z Twoją strukturą."""
    create_url = "https://api.notion.com/v1/pages"
    
    properties = {
        "EMAIL": {"email": contact_details.get("email")},
        "Contact": {"title": [{"text": {"content": contact_details.get("name", contact_details.get("email"))}}]}
    }
    
    if contact_details.get("firstname"):
        properties["FIRSTNAME"] = {"rich_text": [{"text": {"content": contact_details.get("firstname")}}]}
    if contact_details.get("lastname"):
        properties["LASTNAME"] = {"rich_text": [{"text": {"content": contact_details.get("lastname")}}]}
    
    phone_number = contact_details.get("phone")
    if phone_number:
        # Upewnij się, że numer telefonu ma prawidłowy format międzynarodowy
        if not phone_number.startswith('+'):
            cleaned_number = phone_number.replace(" ", "").replace("-", "")
            # Jeśli to 9-cyfrowy polski numer, dodaj +48
            if len(cleaned_number) == 9 and cleaned_number.isdigit():
                phone_number = f"+48{cleaned_number}"
            # W przeciwnym razie, po prostu dodaj +
            else:
                phone_number = f"+{cleaned_number}"
        properties["SMS"] = {"phone_number": phone_number}

    new_page_data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": properties
    }

    try:
        response = requests.post(create_url, headers=NOTION_HEADERS, json=new_page_data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Błąd podczas tworzenia kontaktu w Notion: {e}")
        return None

def update_notion_page(page_id, event_type, event_date_iso, template_id=None):
    """
    Aktualizuje dedykowaną kolumnę z datą dla danego zdarzenia.
    Dynamicznie dopasowuje kolumnę dla otwarć/kliknięć na podstawie ID szablonu.
    """
    update_url = f"https://api.notion.com/v1/pages/{page_id}"
    
    column_to_update = EVENT_TO_COLUMN_MAP.get(event_type)
    if not column_to_update:
        print(f"Pominięto zdarzenie bez mapowania: {event_type}")
        return None

    if event_type in ['unique_opened', 'opened', 'click', 'clicked']:
        if template_id == 6:
            column_to_update += '1'
        elif template_id == 7:
            column_to_update += '2'
        elif template_id == 8:
            column_to_update += '3'

    properties_to_update = {
        column_to_update: {"date": {"start": event_date_iso}}
    }
    update_data = {"properties": properties_to_update}

    try:
        response = requests.patch(update_url, headers=NOTION_HEADERS, json=update_data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Błąd podczas aktualizacji strony w Notion: {e}")
        if e.response:
            print(f"  --> Odpowiedź z serwera Notion: {e.response.text}")
        return None

# --- Funkcja pomocnicza dla Brevo ---
def get_brevo_contact_details(email):
    """Pobiera szczegóły kontaktu z Brevo."""
    if not BREVO_API_KEY:
        return {"email": email, "name": email}

    url = f"https://api.brevo.com/v3/contacts/{email}"
    try:
        response = requests.get(url, headers=BREVO_HEADERS)
        response.raise_for_status()
        brevo_data = response.json()
        
        attributes = brevo_data.get("attributes", {})
        firstname = attributes.get("FIRSTNAME", "")
        lastname = attributes.get("LASTNAME", "")
        name = f"{firstname} {lastname}".strip()
        
        return {
            "email": brevo_data.get("email"),
            "name": name or email,
            "firstname": firstname,
            "lastname": lastname,
            "phone": attributes.get("SMS")
        }
    except requests.exceptions.RequestException as e:
        print(f"Błąd podczas pobierania danych z Brevo dla {email}: {e}")
        return {"email": email, "name": email}

# --- Funkcje i endpoint dla rezygnacji z SMS ---

def update_brevo_sms_blacklist(email):
    """Aktualizuje kontakt w Brevo, ustawiając smsBlacklisted na true."""
    url = f"https://api.brevo.com/v3/contacts/{email}"
    payload = {"smsBlacklisted": True}
    
    try:
        response = requests.put(url, headers=BREVO_HEADERS, json=payload, timeout=15)
        response.raise_for_status()
        print(f"Sukces: Pomyślnie zaktualizowano (smsBlacklisted) kontakt {email} w Brevo.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Błąd podczas aktualizacji kontaktu {email} w Brevo: {e}")
        if e.response:
            print(f"  --> Odpowiedź z serwera Brevo: {e.response.text}")
        return False

@app.route('/wypisz-sms', methods=['GET'])
def unsubscribe_sms_handler():
    """Obsługuje dwuetapowy proces wypisywania z komunikacji SMS."""
    email = request.args.get('email')
    confirm = request.args.get('confirm')

    if not email:
        return "<h1>Błąd</h1><p>Brak adresu e-mail w zapytaniu.</p>", 400

    if confirm == 'true':
        update_brevo_sms_blacklist(email)
        return """
        <!DOCTYPE html><html lang="pl"><head><meta charset="UTF-8"><title>Potwierdzenie</title></head>
        <body style="font-family: sans-serif; text-align: center; padding: 40px;">
        <h1>Rezygnacja przyjęta</h1><p>Twój numer został pomyślnie wypisany z komunikacji SMS.</p>
        </body></html>
        """
    else:
        confirmation_url = f"/wypisz-sms?email={email}&confirm=true"
        return f"""
        <!DOCTYPE html><html lang="pl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Potwierdzenie rezygnacji</title></head>
        <body style="font-family: sans-serif; text-align: center; padding: 40px;">
        <h1>Potwierdzenie rezygnacji</h1>
        <p>Czy na pewno chcesz zrezygnować z otrzymywania od nas wiadomości SMS?</p>
        <a href="{confirmation_url}" style="display: inline-block; background-color: #c0392b; color: white; padding: 15px 30px; border-radius: 5px; font-size: 16px; text-decoration: none; margin-top: 20px;">
            Tak, wypisz mnie
        </a>
        </body></html>
        """

# --- Główny Endpoint Webhooka ---
@app.route('/webhook', methods=['GET', 'POST'])
def webhook_handler():
    """Odbiera i przetwarza webhooki z Brevo."""
    if request.method == 'GET':
        return jsonify({"status": "ok"}), 200

    events = request.get_json()
    if not isinstance(events, list):
        events = [events]

    for event_data in events:
        event_type = event_data.get("event")
        email = event_data.get("email")
        template_id = event_data.get("template_id")

        if not event_type or not email:
            continue

        notion_page = search_contact_in_notion(email)
        page_id = None

        if notion_page:
            page_id = notion_page["id"]
        else:
            contact_details = get_brevo_contact_details(email)
            new_page = create_contact_in_notion(contact_details)
            if new_page:
                page_id = new_page["id"]
            else:
                continue

        if page_id:
            ts_event = event_data.get("ts_event") or event_data.get("ts")
            if ts_event:
                utc_dt = datetime.fromtimestamp(ts_event, tz=pytz.utc)
                warsaw_tz = pytz.timezone('Europe/Warsaw')
                event_date_iso = utc_dt.astimezone(warsaw_tz).isoformat()
            else:
                warsaw_tz = pytz.timezone('Europe/Warsaw')
                event_date_iso = datetime.now(warsaw_tz).isoformat()

            update_notion_page(page_id, event_type, event_date_iso, template_id)
    
    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False, port=5000)