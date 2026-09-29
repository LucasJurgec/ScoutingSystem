# Football API contains a list of all nations including urls for the nation flags
# But in the csv files each nation is represented by a 3-letter code
# So we need to map the two together

import os
import requests
import mysql.connector
from dotenv import load_dotenv
 
load_dotenv()  # reads API_KEY, DB_PASSWORD from .env
 
API_KEY = os.getenv("API_KEY")
BASE_URL = "https://v3.football.api-sports.io"
headers = {"x-apisports-key": API_KEY}
 
conn = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT")),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
)
cursor = conn.cursor()

# Nation to 3-letter code mapping
NATIONS = {
    # UK + Ireland
    "ENG": ("England", "GB-ENG"), "SCO": ("Scotland", "GB-SCT"),
    "WAL": ("Wales", "GB-WLS"), "NIR": ("Northern Ireland", "GB-NIR"),
    "IRL": ("Republic of Ireland", "IE"),
    # Western Europe
    "FRA": ("France", "FR"), "GER": ("Germany", "DE"), "ESP": ("Spain", "ES"),
    "ITA": ("Italy", "IT"), "POR": ("Portugal", "PT"), "NED": ("Netherlands", "NL"),
    "BEL": ("Belgium", "BE"), "SUI": ("Switzerland", "CH"), "AUT": ("Austria", "AT"),
    "LUX": ("Luxembourg", "LU"), "AND": ("Andorra", "AD"), "LIE": ("Liechtenstein", "LI"),
    "MLT": ("Malta", "MT"), "GIB": ("Gibraltar", "GI"), "SMR": ("San Marino", "SM"),
    # Nordics
    "DEN": ("Denmark", "DK"), "SWE": ("Sweden", "SE"), "NOR": ("Norway", "NO"),
    "FIN": ("Finland", "FI"), "ISL": ("Iceland", "IS"), "FRO": ("Faroe Islands", "FO"),
    # Central / Eastern Europe
    "POL": ("Poland", "PL"), "CZE": ("Czech Republic", "CZ"), "SVK": ("Slovakia", "SK"),
    "HUN": ("Hungary", "HU"), "ROU": ("Romania", "RO"), "BUL": ("Bulgaria", "BG"),
    "UKR": ("Ukraine", "UA"), "RUS": ("Russia", "RU"), "BLR": ("Belarus", "BY"),
    "MDA": ("Moldova", "MD"), "LTU": ("Lithuania", "LT"), "LVA": ("Latvia", "LV"),
    "EST": ("Estonia", "EE"),
    # Balkans / South-East Europe
    "GRE": ("Greece", "GR"), "TUR": ("Turkey", "TR"), "CRO": ("Croatia", "HR"),
    "SRB": ("Serbia", "RS"), "BIH": ("Bosnia and Herzegovina", "BA"),
    "MNE": ("Montenegro", "ME"), "SVN": ("Slovenia", "SI"), "MKD": ("North Macedonia", "MK"),
    "ALB": ("Albania", "AL"), "KVX": ("Kosovo", "XK"), "CYP": ("Cyprus", "CY"),
    # Caucasus / Middle East / Central Asia
    "GEO": ("Georgia", "GE"), "ARM": ("Armenia", "AM"), "AZE": ("Azerbaijan", "AZ"),
    "KAZ": ("Kazakhstan", "KZ"), "UZB": ("Uzbekistan", "UZ"), "ISR": ("Israel", "IL"),
    "IRN": ("Iran", "IR"), "IRQ": ("Iraq", "IQ"), "KSA": ("Saudi Arabia", "SA"),
    "QAT": ("Qatar", "QA"), "UAE": ("United Arab Emirates", "AE"), "SYR": ("Syria", "SY"),
    "LIB": ("Lebanon", "LB"), "JOR": ("Jordan", "JO"), "PLE": ("Palestine", "PS"),
    # North Africa
    "MAR": ("Morocco", "MA"), "ALG": ("Algeria", "DZ"), "TUN": ("Tunisia", "TN"),
    "EGY": ("Egypt", "EG"), "LBY": ("Libya", "LY"), "SUD": ("Sudan", "SD"),
    "MTN": ("Mauritania", "MR"),
    # West Africa
    "NGA": ("Nigeria", "NG"), "GHA": ("Ghana", "GH"), "CIV": ("Ivory Coast", "CI"),
    "SEN": ("Senegal", "SN"), "MLI": ("Mali", "ML"), "GUI": ("Guinea", "GN"),
    "GNB": ("Guinea-Bissau", "GW"), "BFA": ("Burkina Faso", "BF"), "TOG": ("Togo", "TG"),
    "BEN": ("Benin", "BJ"), "GAM": ("Gambia", "GM"), "SLE": ("Sierra Leone", "SL"),
    "LBR": ("Liberia", "LR"), "CPV": ("Cape Verde", "CV"), "NIG": ("Niger", "NE"),
    # Central / East / Southern Africa
    "CMR": ("Cameroon", "CM"), "GAB": ("Gabon", "GA"), "CGO": ("Congo", "CG"),
    "COD": ("DR Congo", "CD"), "EQG": ("Equatorial Guinea", "GQ"),
    "CTA": ("Central African Republic", "CF"), "CHA": ("Chad", "TD"),
    "ANG": ("Angola", "AO"), "ZAM": ("Zambia", "ZM"), "ZIM": ("Zimbabwe", "ZW"),
    "RSA": ("South Africa", "ZA"), "MOZ": ("Mozambique", "MZ"), "NAM": ("Namibia", "NA"),
    "MWI": ("Malawi", "MW"), "KEN": ("Kenya", "KE"), "UGA": ("Uganda", "UG"),
    "TAN": ("Tanzania", "TZ"), "ETH": ("Ethiopia", "ET"), "MAD": ("Madagascar", "MG"),
    "COM": ("Comoros", "KM"), "BDI": ("Burundi", "BI"), "RWA": ("Rwanda", "RW"),
    # North / Central America + Caribbean
    "USA": ("United States", "US"), "CAN": ("Canada", "CA"), "MEX": ("Mexico", "MX"),
    "JAM": ("Jamaica", "JM"), "HON": ("Honduras", "HN"), "CRC": ("Costa Rica", "CR"),
    "PAN": ("Panama", "PA"), "HAI": ("Haiti", "HT"), "TRI": ("Trinidad and Tobago", "TT"),
    "SLV": ("El Salvador", "SV"), "GUA": ("Guatemala", "GT"), "NCA": ("Nicaragua", "NI"),
    "DOM": ("Dominican Republic", "DO"), "CUB": ("Cuba", "CU"), "BER": ("Bermuda", "BM"),
    "GRN": ("Grenada", "GD"), "ATG": ("Antigua and Barbuda", "AG"), "MSR": ("Montserrat", "MS"),
    "CUW": ("Curacao", "CW"), "SUR": ("Suriname", "SR"), "GUY": ("Guyana", "GY"),
    "GUF": ("French Guiana", "GF"), "GLP": ("Guadeloupe", "GP"), "MTQ": ("Martinique", "MQ"),
    # South America
    "ARG": ("Argentina", "AR"), "BRA": ("Brazil", "BR"), "URU": ("Uruguay", "UY"),
    "PAR": ("Paraguay", "PY"), "CHI": ("Chile", "CL"), "COL": ("Colombia", "CO"),
    "PER": ("Peru", "PE"), "ECU": ("Ecuador", "EC"), "VEN": ("Venezuela", "VE"),
    "BOL": ("Bolivia", "BO"),
    # Asia / Oceania
    "JPN": ("Japan", "JP"), "KOR": ("South Korea", "KR"), "PRK": ("North Korea", "KP"),
    "CHN": ("China", "CN"), "AUS": ("Australia", "AU"), "NZL": ("New Zealand", "NZ"),
    "IDN": ("Indonesia", "ID"), "PHI": ("Philippines", "PH"), "THA": ("Thailand", "TH"),
    "VIE": ("Vietnam", "VN"), "IND": ("India", "IN"), "NCL": ("New Caledonia", "NC"),
}
 
 
# flip the dict so we can go ISO code -> (FBref code, name)
ISO_TO_NATION = {iso: (code, name) for code, (name, iso) in NATIONS.items()}
 
 
def insert_nations():
    response = requests.get(f"{BASE_URL}/countries", headers=headers)
    data = response.json()
 
    inserted, skipped = 0, []
 
    for country in data["response"]:
        iso = (country.get("code") or "").upper()
 
        if iso not in ISO_TO_NATION:
            skipped.append(country["name"])  # e.g. "World", or a country not in the dict
            continue
 
        nation_code, nation_name = ISO_TO_NATION[iso]
 
        cursor.execute("""
            INSERT INTO nation (nation_code, nation_name, nation_flag)
            VALUES (%s, %s, %s) AS new
            ON DUPLICATE KEY UPDATE
                nation_name = new.nation_name,
                nation_flag = new.nation_flag
        """, (nation_code, nation_name, country["flag"]))
        inserted += 1
 
    conn.commit()
    print(f"{inserted} nations inserted/updated")
    if skipped:
        print("SKIPPED (no 3-letter code in NATIONS):", ", ".join(sorted(skipped)))
 
 
insert_nations()
 
cursor.close()
conn.close()
print("Done!")