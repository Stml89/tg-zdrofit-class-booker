"""Configuration module for the Zdrofit bot."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not set in .env file")

# API settings
ZDROFIT_API_BASE_URL = "https://zdrofit.perfectgym.pl"

# Database settings
BASE_DIR = Path(__file__).parent.parent
PROJECT_ROOT = BASE_DIR
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "data" / "zdrofit.db"))

# Logging settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = os.getenv("LOG_DIR", str(BASE_DIR / "logs"))

# Search window (hours from now)
SEARCH_WINDOW_HOURS = int(os.getenv("SEARCH_WINDOW_HOURS", "48"))

# Available clubs mapping: city -> {club_name -> club_id}
AVAILABLE_CLUBS = {
    "Banino": {
        "Zdrofit Banino Pszenna": 167,
    },
    "Białystok": {
        "Zdrofit Białystok Wrocławska": 94,
    },
    "Bydgoszcz": {
        "Zdrofit Bydgoszcz Balaton": 173,
        "Zdrofit Bydgoszcz Focus": 179,
        "Zdrofit Bydgoszcz Immobile K3": 177,
    },
    "Częstochowa": {
        "Zdrofit Częstochowa Piastowska": 101,
    },
    "Dawidy Bankowe": {
        "Zdrofit Dawidy Bankowe": 170,
    },
    "Elbląg": {
        "Zdrofit Elbląg Nowowiejska": 176,
    },
    "Gdańsk": {
        "Zdrofit Gdańsk Alchemia": 31,
        "Zdrofit Gdańsk CH Manhattan": 32,
        "Zdrofit Gdańsk CH Rental Park": 34,
        "Zdrofit Gdańsk Chełm": 35,
        "Zdrofit Gdańsk Garnizon": 238,
        "Zdrofit Gdańsk Grunwaldzka": 149,
        "Zdrofit Gdańsk Kowale": 84,
        "Zdrofit Gdańsk Madison": 82,
        "Zdrofit Gdańsk Morena": 85,
        "Zdrofit Gdańsk Nieborowska": 151,
        "Zdrofit Gdańsk Orzechowa": 164,
        "Zdrofit Gdańsk Przymorze": 33,
        "Zdrofit Gdańsk Przymorze Obrońców Wybrzeża": 81,
        "Zdrofit Gdańsk Rzeczypospolitej": 150,
        "Zdrofit Gdańsk Suchanino": 36,
        "Zdrofit Gdańsk Zaspa": 83,
    },
    "Pruszcz Gdański": {
        "Zdrofit Pruszcz Gdański Domeyki": 165,
        "Zdrofit Pruszcz Gdański Kasprowicza": 166,
    },
    "Gdynia": {
        "Zdrofit Gdynia CH Riviera": 37,
        "Zdrofit Gdynia Chwarzno": 43,
        "Zdrofit Gdynia Karwiny": 65,
        "Zdrofit Gdynia Klif": 80,
        "Zdrofit Gdynia Plac Kaszubski": 76,
        "Zdrofit Gdynia Witawa": 79,
    },
    "Kielce": {
        "Zdrofit Kielce Galeria Echo": 26,
        "Zdrofit Kielce Galeria Korona": 20,
    },
    "Koszalin": {
        "Zdrofit Koszalin Atrium Koszalin": 24,
        "Zdrofit Koszalin Galeria Kosmos": 30,
    },
    "Legionowo": {
        "Zdrofit Legionowo DH Maxim": 1,
        "Zdrofit Legionowo Zegrzyńska": 22,
    },
    "Lublin": {
        "Zdrofit Lublin Batory": 169,
        "Zdrofit Lublin Galeria Gala": 178,
        "Zdrofit Lublin Galeria Olimp": 168,
    },
    "Olsztyn": {
        "Zdrofit Olsztyn Wilczyńskiego": 234,
    },
    "Otwock": {
        "Zdrofit Otwock": 14,
    },
    "Piaseczno": {
        "Zdrofit Piaseczno Pawia": 53,
        "Zdrofit Piaseczno Puławska": 249,
    },
    "Piastów": {
        "Zdrofit Piastów Pasaż Warszawska": 57,
    },
    "Pruszków": {
        "Zdrofit Pruszków CH Nowa Stacja": 42,
        "Zdrofit Pruszków Miry Zimińskiej Sygietyńskiego": 247,
    },
    "Płock": {
        "Zdrofit Płock Mazovia": 21,
    },
    "Radom": {
        "Zdrofit Radom Wernera": 148,
    },
    "Sopot": {
        "Zdrofit Sopot Sopot Centrum": 39,
    },
    "Stara Iwiczna": {
        "Zdrofit NPark Stara Iwiczna": 74,
    },
    "Stargard": {
        "Zdrofit Stargard Starówka": 180,
        "Zdrofit Stargard Zodiak": 175,
    },
    "Szczecin": {
        "Zdrofit Szczecin Galaxy": 86,
        "Zdrofit Szczecin Kaskada": 87,
        "Zdrofit Szczecin Outlet Park": 89,
        "Zdrofit Szczecin Piastów Office Center": 88,
    },
    "Toruń": {
        "Zdrofit Toruń Galeria Copernicus": 99,
        "Zdrofit Toruń Rydygiera": 97,
    },
    "Warszawa": {
        "Bemowo": {
            "Zdrofit Bemowo Dywizjonu 303": 7,
            "Zdrofit Bemowo Warszawska": 248,
            "Zdrofit Bemowo Świetlików": 95,
            "Zdrofit Lazurowa": 75,
        },
        "Białołęka": {
            "Zdrofit Białołęka Modlińska": 140,
            "Zdrofit Białołęka Modlińska 168": 242,
            "Zdrofit Białołęka Skarbka z Gór": 153,
            "Zdrofit Tarchomin Galeria Północna": 45,
            "Zdrofit Tarchomin Światowida": 19,
        },
        "Bielany": {
            "Zdrofit Bielany Dąbrowskiej": 98,
            "Zdrofit Bielany Marymoncka": 9,
            "Zdrofit Bielany Przy Agorze": 46,
            "Zdrofit Galeria Młociny": 60,
        },
        "Centrum": {
            "Zdrofit Centrum Krucza": 25,
            "Zdrofit Centrum Rondo ONZ": 66,
            "Zdrofit The Warsaw HUB": 72,
            "Zdrofit Varso": 70,
            "Zdrofit Śródmieście Metro Politechnika": 40,
            "Zdrofit Śródmieście Metro Świętokrzyska": 181,
        },
        "Gocław": {
            "Zdrofit Gocław Atrium Promenada": 23,
            "Zdrofit Gocław Gen. Fieldorfa Nila": 244,
            "Zdrofit Gocław Ostrobramska": 2,
        },
        "Mokotów": {
            "Zdrofit Mokotów Adgar Plaza": 90,
            "Zdrofit Mokotów Al. Wilanowska": 55,
            "Zdrofit Mokotów Bobrowiecka": 59,
            "Zdrofit Mokotów Bukowińska": 4,
            "Zdrofit Mokotów CH Plac Unii": 50,
            "Zdrofit Mokotów Europlex": 51,
            "Zdrofit Mokotów Konstruktorska": 10,
            "Zdrofit Mokotów Mangalia 2a": 237,
            "Zdrofit Mokotów Marynarska": 15,
            "Zdrofit Mokotów Puławska": 93,
            "Zdrofit Mokotów Warszawianka": 44,
            "Zdrofit Mokotów Westfield Mokotów": 54,
            "Zdrofit Stegny": 5,
            "Zdrofit Sadyba Nałęczowska": 91,
        },
        "Ochota": {
            "Zdrofit Ochota Adgar": 139,
            "Zdrofit Ochota Aleje Jerozolimskie": 29,
            "Zdrofit Ochota Bohaterów Września": 241,
            "Zdrofit Ochota Grójecka": 17,
        },
        "Praga": {
            "Zdrofit Praga Pn. Koneser": 41,
            "Zdrofit Praga Południe Arabska": 172,
            "Zdrofit Grochów Kobielska": 240,
            "Zdrofit PZO": 77,
        },
        "Targówek": {
            "Zdrofit Targówek Atrium": 63,
            "Zdrofit Targówek Dalanowska": 100,
            "Zdrofit Targówek Galeria Renova": 18,
            "Zdrofit Targówek Homepark Targówek": 144,
        },
        "Ursus": {
            "Zdrofit Ursus Dzieci W-wy": 61,
            "Zdrofit Ursus Leszczyńskiego": 171,
            "Zdrofit Ursus Pużaka": 96,
        },
        "Ursynów": {
            "Zdrofit Ursynów Koński Jar": 92,
            "Zdrofit Ursynów Puszczyka": 239,
            "Zdrofit Ursynów Puławska": 52,
        },
        "Wawer": {
            "Zdrofit Wawer CH Ferio": 56,
        },
        "Wilanów": {
            "Studio Zdrofit Wilanów Klimczaka": 142,
            "Zdrofit Wilanów Rzeczypospolitej": 11,
            "Zdrofit Wilanów Rzeczypospolitej 14": 245,
            "Zdrofit Wilanów Syta": 236,
        },
        "Wola": {
            "Zdrofit Fort Wola": 141,
            "Zdrofit Wola CH Wola Park": 49,
            "Zdrofit Wola Jana Kazimierza": 67,
            "Zdrofit Wola Skierniewicka": 62,
            "Zdrofit Wola Warsaw Spire": 48,
            "Zdrofit Wola Wolska": 3,
            "Zdrofit Wola Wolska 88": 246,
            "Zdrofit Mennica": 73,
        },
        "Włochy": {
            "Zdrofit Włochy Krakowiaków": 64,
            "Zdrofit Włochy Żwirki i Wigury": 27,
        },
        "Żoliborz": {
            "Zdrofit CH Arkadia": 47,
            "Zdrofit Żoliborz Hubnera": 152,
            "Zdrofit Żoliborz Szamocka": 16,
            "Zdrofit Żoliborz Wojska Polskiego": 146,
            "Zdrofit Metro Dw. Gdański": 12,
        },
    },
    "Wołomin": {
        "Zdrofit Wołomin": 13,
    },
    "Włocławek": {
        "Zdrofit Włocławek Wzorcownia": 28,
    },
}

# Telegram connection pool settings
TELEGRAM_CONNECT_TIMEOUT = int(os.getenv("TELEGRAM_CONNECT_TIMEOUT", "15"))
TELEGRAM_READ_TIMEOUT = int(os.getenv("TELEGRAM_READ_TIMEOUT", "15"))
TELEGRAM_WRITE_TIMEOUT = int(os.getenv("TELEGRAM_WRITE_TIMEOUT", "15"))
TELEGRAM_POOL_TIMEOUT = int(os.getenv("TELEGRAM_POOL_TIMEOUT", "30"))
TELEGRAM_POOL_SIZE = int(os.getenv("TELEGRAM_POOL_SIZE", "32"))
