#!/usr/bin/env python3
"""
UK Lotto Real Data Scraper
Fetches actual historical lottery results from lottery.co.uk
Run this script on your own computer to get real data!
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import re
import time

def fetch_year_data(year):
    """Fetch lottery results for a specific year"""
    url = f"https://www.lottery.co.uk/lotto/results/archive-{year}"
    print(f"Fetching {year}...", end=" ")
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        results = []
        rows = soup.find_all('tr')
        
        for row in rows:
            try:
                # Find date link
                date_link = row.find('a', href=lambda h: h and '/lotto/results-' in h)
                if not date_link:
                    continue
                
                date_text = date_link.get_text(strip=True)
                clean_date = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_text)
                
                try:
                    draw_date = datetime.strptime(clean_date, '%A %d %B %Y')
                except ValueError:
                    continue
                
                # Only include from October 10, 2015 onwards (59-ball format)
                if draw_date < datetime(2015, 10, 10):
                    continue
                
                # Find results cell
                results_cell = row.find('td', class_='results')
                if not results_cell:
                    continue
                
                # Extract numbers
                numbers_text = results_cell.get_text(strip=True)
                # Remove extra text after numbers
                numbers_text = numbers_text.split('There were')[0].strip()
                
                # Extract all numbers
                numbers = re.findall(r'\b(\d+)\b', numbers_text)
                numbers = [int(n) for n in numbers if 1 <= int(n) <= 59]
                
                if len(numbers) >= 7:
                    results.append({
                        'date': draw_date.strftime('%Y-%m-%d'),
                        'day_of_week': draw_date.strftime('%A'),
                        'ball_1': numbers[0],
                        'ball_2': numbers[1],
                        'ball_3': numbers[2],
                        'ball_4': numbers[3],
                        'ball_5': numbers[4],
                        'ball_6': numbers[5],
                        'bonus_ball': numbers[6]
                    })
            except Exception as e:
                continue
        
        print(f"✓ Found {len(results)} draws")
        return results
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return []

def main():
    print("=" * 70)
    print("UK LOTTO REAL DATA SCRAPER")
    print("=" * 70)
    print("\nFetching actual lottery results from lottery.co.uk...")
    print("This may take a few minutes...\n")
    
    all_results = []
    
    # Fetch data for each year from 2015 to 2025
    for year in range(2015, 2026):
        results = fetch_year_data(year)
        all_results.extend(results)
        time.sleep(1)  # Be polite to the server
    
    if not all_results:
        print("\n✗ No results fetched. Please check your internet connection.")
        return
    
    # Create DataFrame
    df = pd.DataFrame(all_results)
    df = df.sort_values('date')
    df = df.drop_duplicates(subset=['date'])
    
    # Save to CSV
    output_file = 'uk_lotto_real_data_oct2015_onwards.csv'
    df.to_csv(output_file, index=False)
    
    print("\n" + "=" * 70)
    print("SUCCESS! Real lottery data downloaded")
    print("=" * 70)
    print(f"\nTotal draws: {len(df)}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"Output file: {output_file}")
    print("\nFirst few draws:")
    print(df.head(10).to_string(index=False))
    print("\nLast few draws:")
    print(df.tail(5).to_string(index=False))
    print("\n" + "=" * 70)
    print("✓ CSV file created successfully!")
    print("=" * 70)

if __name__ == "__main__":
    # Check if required packages are installed
    try:
        import requests
        from bs4 import BeautifulSoup
        import pandas as pd
    except ImportError:
        print("Please install required packages:")
        print("pip install requests beautifulsoup4 pandas lxml")
        exit(1)
    
    main()
