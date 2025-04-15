import requests
from bs4 import BeautifulSoup
import csv
import time
import re
import os

# Create CSV file with headers
csv_filename = "supreme_court_decisions.csv"
headers = ["Case Number", "Case Title", "Facts", "Decision", "Ruling", "Verdict"]

def create_csv():
    if not os.path.exists(csv_filename):
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
        print(f"Created new CSV file: {csv_filename}")

# Base URL
base_url = "https://elibrary.judiciary.gov.ph"

# Function to get all case links from a listing page
def get_case_links(url):
    print(f"Accessing listing page: {url}")
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        case_links = []
        
        # Based on your screenshots, look for G.R. No. entries
        # This gets all the links in the page
        links = soup.find_all('a', href=lambda href: href and '/thebookshelf/showdocs/' in href)
        
        # Process each link
        for link in links:
            # Check if the href already starts with http
            if link['href'].startswith('http'):
                case_url = link['href']  # Use as-is if it's already a full URL
            else:
                case_url = base_url + link['href']  # Only prepend base_url if needed
                
            # Store case title from the link text or nearby text
            case_title = link.text.strip()
            # Print for debugging
            print(f"Found case link: {case_title}")
            # Add to our list
            case_links.append(case_url)
        
        return case_links
    except Exception as e:
        print(f"Error accessing listing page: {e}")
        return []
    
# Function to parse content from a case page
def parse_case_page(url):
    print(f"Processing case: {url}")
    try:
        # Validate URL first
        if not url.startswith('http'):
            raise ValueError(f"Invalid URL format: {url}")
            
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract case number
        case_number = ""
        case_number_element = soup.find(string=re.compile(r'G\.R\. Nos?\. \d+-?\d*'))
        if case_number_element:
            case_number = case_number_element.strip()
        else:
            # Try finding it in the header section
            header_section = soup.find('h1') or soup.find('h2') or soup.find('div', class_='case-header')
            if header_section and 'G.R.' in header_section.text:
                case_number = re.search(r'G\.R\. Nos?\. \d+-?\d*', header_section.text).group(0)
        
        # Extract case title
        case_title = ""
        # Look for text matching the pattern of parties (often in uppercase)
        case_title_pattern = re.compile(r'([A-Z][A-Z\s.,]+\s+VS\.\s+[A-Z][A-Z\s.,]+)', re.IGNORECASE)
        case_title_match = soup.find(string=case_title_pattern)
        if case_title_match:
            case_title = case_title_pattern.search(case_title_match).group(0)
        
        # Find Facts section
        facts_section = ""
        facts_header = soup.find(string=re.compile(r'Factual Antecedents', re.IGNORECASE))
        if facts_header:
            # Get the parent container
            facts_container = facts_header.parent
            # Get the next sibling elements until we hit another heading
            current = facts_container.find_next_sibling()
            while current and not (current.name in ['h2', 'h3', 'h4'] or 
                                  current.find(string=re.compile(r'DECISION|Our Ruling', re.IGNORECASE))):
                facts_section += current.text.strip() + "\n"
                current = current.find_next_sibling()
        
        # Find Decision section
        decision_section = ""
        decision_header = soup.find(string=re.compile(r'DECISION', re.IGNORECASE))
        if decision_header:
            decision_container = decision_header.parent
            current = decision_container.find_next_sibling()
            while current and not (current.name in ['h2', 'h3', 'h4'] or 
                                  current.find(string=re.compile(r'Our Ruling|WHEREFORE', re.IGNORECASE))):
                decision_section += current.text.strip() + "\n"
                current = current.find_next_sibling()
        
        # Find Ruling section
        ruling_section = ""
        ruling_header = soup.find(string=re.compile(r'Our Ruling', re.IGNORECASE))
        if ruling_header:
            ruling_container = ruling_header.parent
            current = ruling_container.find_next_sibling()
            while current and not (current.name in ['h2', 'h3', 'h4'] or 
                                  current.find(string=re.compile(r'WHEREFORE', re.IGNORECASE))):
                ruling_section += current.text.strip() + "\n"
                current = current.find_next_sibling()
        
        # Find Verdict section
        verdict_section = ""
        verdict_header = soup.find(string=re.compile(r'WHEREFORE', re.IGNORECASE))
        if verdict_header:
            # The verdict is usually the paragraph containing "WHEREFORE"
            verdict_container = verdict_header.parent
            verdict_section = verdict_container.text.strip()
            
            # Also include "SO ORDERED" if it exists
            so_ordered = soup.find(string=re.compile(r'SO ORDERED', re.IGNORECASE))
            if so_ordered:
                verdict_section += "\n" + so_ordered.strip()
        
        return {
            "Case Number": case_number,
            "Case Title": case_title,
            "Facts": facts_section.strip(),
            "Decision": decision_section.strip(),
            "Ruling": ruling_section.strip(),
            "Verdict": verdict_section.strip()
        }
    except Exception as e:
        print(f"Error processing case page: {e}")
        return {header: f"Error retrieving data: {str(e)[:100]}" for header in headers}

# Main function to run the scraper
def scrape_cases(starting_url, max_cases=10):
    create_csv()
    
    # Get case links from the listing page
    case_links = get_case_links(starting_url)
    
    # Limit the number of cases to scrape if needed
    if max_cases > 0 and len(case_links) > max_cases:
        case_links = case_links[:max_cases]
    
    print(f"Found {len(case_links)} cases to process")
    
    # Process each case and save to CSV
    with open(csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        
        for link in case_links:
            try:
                case_data = parse_case_page(link)
                writer.writerow(case_data)
                print(f"Successfully scraped case: {case_data['Case Number']}")
                
                # Add a delay between requests to be respectful to the server
                time.sleep(2)
            except Exception as e:
                print(f"Error processing {link}: {e}")
    
    print(f"Scraping complete. Data saved to {csv_filename}")

if __name__ == "__main__":
    # URL from your screenshot
    starting_url = "https://elibrary.judiciary.gov.ph/thebookshelf/docmonth/Jan/2025/1"
    
    # Run the scraper
    scrape_cases(starting_url, max_cases=5)  # Start with 5 cases as a test