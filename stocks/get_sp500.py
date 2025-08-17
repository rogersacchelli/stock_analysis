import requests
from bs4 import BeautifulSoup
import json


def fetch_sp500_data(url):
    try:
        # Send HTTP request to fetch the webpage
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise exception for bad status codes
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching webpage: {e}")
        return None


def parse_table(html_content):
    if not html_content:
        return []

    # Parse HTML content with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', {'id': 'constituents'})  # Target the S&P 500 table
    if not table:
        print("No table found with id 'constituents'")
        return []

    # Extract table headers
    headers = [th.text.strip() for th in table.find('tr').find_all('th')]

    # Extract table rows
    data = []
    for row in table.find_all('tr')[1:]:  # Skip header row
        cells = [td.text.strip() for td in row.find_all('td')]
        if cells:  # Only process non-empty rows
            row_data = dict(zip(headers, cells))
            data.append(row_data)

    return data


def save_to_json(data, filename='sp500_data.json'):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Data saved to {filename}")
    except IOError as e:
        print(f"Error saving JSON: {e}")


def main():
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    html_content = fetch_sp500_data(url)
    sp500_data = parse_table(html_content)

    if sp500_data:
        save_to_json(sp500_data)
        return sp500_data
    return []


if __name__ == '__main__':
    main()