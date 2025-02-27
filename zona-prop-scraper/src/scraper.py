import re
import time
import csv
from functools import reduce

from bs4 import BeautifulSoup

PAGE_URL_SUFFIX = '-pagina-'
HTML_EXTENSION = '.html'

FEATURE_UNIT_DICT = {
    'm²': 'square_meters_area',
    'amb': 'rooms',
    'dorm': 'bedrooms',
    'baño': 'bathrooms',
    'baños': 'bathrooms',
    'coch': 'parking',
}

LABEL_DICT = {
    'POSTING_CARD_PRICE': 'price',
    'expensas': 'expenses',
    'POSTING_CARD_LOCATION': 'location',
    'POSTING_CARD_DESCRIPTION': 'description',
}

class Scraper:
    def __init__(self, browser, base_url):
        self.browser = browser
        self.base_url = base_url

    def scrap_page(self, page_number):
        """
        Para una página en particular (1,2,3...), obtiene la lista
        de 'estates' y además intenta extraer el teléfono principal 
        desde el HTML completo si encuentra la cadena "mainPhone":"xxxx".
        """
        if page_number == 1:
            page_url = f'{self.base_url}{HTML_EXTENSION}'
        else:
            page_url = f'{self.base_url}{PAGE_URL_SUFFIX}{page_number}{HTML_EXTENSION}'

        print(f'URL: {page_url}')
        page_response = self.browser.get_text(page_url)

        # Parseamos con BeautifulSoup
        soup = BeautifulSoup(page_response, 'lxml')

        # Buscamos cada "div" que contenga data-posting-type
        estate_posts = soup.find_all('div', attrs={'data-posting-type': True})
        estates = []
        for estate_post in estate_posts:
            estate = self.parse_estate(estate_post)
            # Extraemos el teléfono para cada anuncio individualmente
            estate_phone = self.parse_phone(str(estate_post))
            estate['phone'] = estate_phone
            estates.append(estate)

        print(f'Estates on page {page_number}: {estates}')
        return estates

    def scrap_website(self):
        page_number = 1
        estates = []
        estates_scraped = 0
        estates_quantity = self.get_estates_quantity()

        while estates_quantity > estates_scraped:
            print(f'Page: {page_number}')
            estates_page = self.scrap_page(page_number)
            estates += estates_page
            estates_scraped = len(estates)
            page_number += 1
            time.sleep(3)

        print(f'Total estates scraped: {estates}')
        write_to_csv(estates)
        return estates

    def get_estates_quantity(self):
        """
        Busca la cantidad total de propiedades para controlar el while.
        Ajustar la forma de extraer el número según tu HTML real.
        """
        page_url = f'{self.base_url}{HTML_EXTENSION}'
        page = self.browser.get_text(page_url)
        soup = BeautifulSoup(page, 'lxml')
        estates_quantity_text = soup.find_all('h1')[0].text

        found = re.findall(r'\d+\.?\d+', estates_quantity_text)
        if not found:
            # fallback si no encuentra
            return 0
        estates_quantity = found[0].replace('.', '')
        estates_quantity = int(estates_quantity)
        return estates_quantity

    def parse_phone(self, page_text):
        """
        Busca en el texto completo de la página algo como "mainPhone":"1151020499"
        y devuelve el número. Si no lo encuentra, retorna None.
        """
        phone_match = re.search(r'"mainPhone":"(\d+)"', page_text)
        if phone_match:
            return phone_match.group(1)
        return None

    def parse_estate(self, estate_post):
        """
        Extrae los datos de un 'div' con data-posting-type:
        - url
        - price, location, description
        - address
        - features (m2, amb, etc.)
        """
        data_qa = estate_post.find_all(attrs={'data-qa': True})
        url_list = estate_post.get_attribute_list('data-to-posting')
        url = url_list[0] if url_list else None
        estate = {'url': url}

        # Recorrer data-qa y filtrar price, expensas, location, etc.
        for data in data_qa:
            label = data.get('data-qa')
            if label in ['POSTING_CARD_PRICE', 'expensas']:
                currency_value, currency_type = self.parse_currency_value(data.get_text())
                estate[LABEL_DICT[label] + '_value'] = currency_value
                estate[LABEL_DICT[label] + '_type'] = currency_type
            elif label in ['POSTING_CARD_LOCATION', 'POSTING_CARD_DESCRIPTION']:
                text = self.parse_text(data.get_text())
                estate[LABEL_DICT[label]] = text
            else:
                # para no perder otros data-qa
                text = self.parse_text(data.get_text())
                estate[label] = text

        # Extraer la dirección (Maure al 1700, p.ej.)
        address_div = estate_post.select_one(
            'div.postingLocations-module__location-address.postingLocations-module__location-address-in-listing'
        )
        if address_div:
            address_text = self.parse_text(address_div.get_text())
            estate['address'] = address_text

        # Extraer features (m², amb, dorm, baños, coch.)
        feature_spans = estate_post.select(
            'span.postingMainFeatures-module__posting-main-features-span.postingMainFeatures-module__posting-main-features-listing'
        )
        raw_features_text = ' '.join(span.get_text(strip=True) for span in feature_spans)

        if raw_features_text:
            print("Texto de features capturado:", raw_features_text)
            features = self.parse_features(raw_features_text)
            estate.update(features)

        print(f'Parsed estate: {estate}')
        return estate

    def parse_currency_value(self, text):
        """
        Intenta capturar algo como '330.000 USD' -> currency_value=330000, currency_type='USD'
        """
        try:
            currency_value = re.findall(r'\d+\.?\d+', text)[0]
            currency_value = currency_value.replace('.', '')
            currency_value = int(currency_value)
            currency_type = re.findall(r'(USD)|(ARS)|(\$)', text)[0]
            currency_type = [x for x in currency_type if x][0]
            return currency_value, currency_type
        except:
            return text, None

    def parse_text(self, text):
        # Limpia saltos y tabs
        text = text.replace('\n', '')
        text = text.replace('\t', '')
        return text.strip()

    def parse_features(self, text):
        """
        Ejemplo: "215 m² tot. 5 amb. 4 dorm. 2 baños 1 coch."
        Devuelve: { 'square_meters_area': '215', 'rooms': '5', 'bedrooms': '4', ... }
        """
        print("Texto completo de features:", text)
        pattern = re.compile(
            r'(\d+\.?\d*)\s?(m2\.?|m²\.?|amb\.?|dorm\.?|bañ[oo]s?\.?|coch\.?)',
            re.IGNORECASE
        )
        matches = pattern.findall(text)
        print("Coincidencias (raw):", matches)

        features = {}
        for (num_str, raw_unit) in matches:
            unit_clean = raw_unit.lower().rstrip('.')
            if unit_clean in ['m2', 'm²']:
                unit_clean = 'm²'
            elif unit_clean.startswith('amb'):
                unit_clean = 'amb'
            elif unit_clean.startswith('dorm'):
                unit_clean = 'dorm'
            elif unit_clean.startswith('bañ'):
                unit_clean = 'baños'
            elif unit_clean.startswith('coch'):
                unit_clean = 'coch'

            key = FEATURE_UNIT_DICT.get(unit_clean, unit_clean)
            features[key] = num_str

        print("features parseados:", features)
        return features


def write_to_csv(estates, filename='estates.csv'):
    if not estates:
        print("No hay estates para guardar en CSV.")
        return

    # 1) Recolectar todas las claves de todos los diccionarios
    all_keys = set()
    for e in estates:
        all_keys.update(e.keys())

    # Convertir a lista para mantener un orden
    fieldnames = list(all_keys)

    with open(filename, 'w', newline='', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        dict_writer.writeheader()
        dict_writer.writerows(estates)