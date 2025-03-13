import os
import re
import pandas as pd
import PyPDF2
from collections import defaultdict

class PitchDeckScraper:
    def __init__(self):
        self.results = defaultdict(dict)
        
    def extract_text_from_pdf(self, pdf_path):
        """Extract all text from a PDF file."""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page_num in range(len(reader.pages)):
                text += reader.pages[page_num].extract_text() + "\n"
            return text
    
    def extract_company_name(self, text):
        """Try to extract company name from the pitch deck."""
        # Look for common patterns in pitch decks
        patterns = [
            r"(?:About|Company:?|About Us:?)\s+([A-Z][A-Za-z0-9\s]{2,30}(?:Inc\.?|LLC|Corp\.?|Co\.?)?)",
            r"([A-Z][A-Za-z0-9\s]{2,30}(?:Inc\.?|LLC|Corp\.?|Co\.?))\s+(?:Pitch|Deck|Presentation)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        return None
    
    def extract_funding_amount(self, text):
        """Extract funding amounts mentioned in the deck."""
        funding_pattern = r"(?:raising|raise|seeking|investment of|funding of|looking for)?\s*\$?(\d+(?:\.\d+)?)\s*(?:M|MM|Million|million|K|k|thousand|Thousand)"
        funding_matches = re.finditer(funding_pattern, text)
        
        funding_amounts = []
        for match in funding_matches:
            amount = match.group(1)
            unit = match.group(0).split(amount)[1].strip()
            
            amount = float(amount)
            # Normalize to millions
            if 'k' in unit.lower() or 'thousand' in unit.lower():
                amount /= 1000
            
            funding_amounts.append(amount)
            
        return funding_amounts if funding_amounts else None
    
    def extract_valuation(self, text):
        """Extract company valuation from the deck."""
        valuation_pattern = r"(?:valuation|valued at|worth|post-money|pre-money).*?\$?(\d+(?:\.\d+)?)\s*(?:M|MM|Million|million|B|billion|Billion)"
        valuation_match = re.search(valuation_pattern, text, re.IGNORECASE)
        
        if valuation_match:
            amount = float(valuation_match.group(1))
            unit = valuation_match.group(0).split(valuation_match.group(1))[1].strip()
            
            # Normalize to millions
            if 'b' in unit.lower() or 'billion' in unit.lower():
                amount *= 1000
                
            return amount
        
        return None
    
    def extract_founders(self, text):
        """Extract founder information."""
        founder_section = re.search(r"(?:Team|Founders|Management).*?(?:Market|Product|Traction|Financials|Competition)", text, re.DOTALL | re.IGNORECASE)
        
        if founder_section:
            founder_text = founder_section.group(0)
            # Look for names followed by titles
            founders = re.findall(r"([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,2})(?:,|\.|\n|\s)?\s*(?:CEO|CTO|CFO|COO|Founder|Co-Founder)", founder_text)
            return founders if founders else None
        
        return None
    
    def extract_market_size(self, text):
        """Extract market size information."""
        market_pattern = r"(?:TAM|Total Addressable Market|Market Size|Market Opportunity).*?\$?(\d+(?:\.\d+)?)\s*(?:B|billion|Billion|T|trillion|Trillion)"
        market_match = re.search(market_pattern, text, re.IGNORECASE)
        
        if market_match:
            amount = float(market_match.group(1))
            unit = market_match.group(0).split(market_match.group(1))[1].strip()
            
            # Normalize to billions
            if 't' in unit.lower() or 'trillion' in unit.lower():
                amount *= 1000
                
            return amount
        
        return None
    
    def process_pitch_deck(self, pdf_path):
        """Process a single pitch deck and extract key information."""
        filename = os.path.basename(pdf_path)
        text = self.extract_text_from_pdf(pdf_path)
        
        company_name = self.extract_company_name(text) or "Unknown"
        
        self.results[filename] = {
            "company_name": company_name,
            "funding_sought": self.extract_funding_amount(text),
            "valuation": self.extract_valuation(text),
            "founders": self.extract_founders(text),
            "market_size_billions": self.extract_market_size(text)
        }
        
        return self.results[filename]
    
    def process_directory(self, directory_path):
        """Process all PDF files in a directory."""
        for filename in os.listdir(directory_path):
            if filename.lower().endswith('.pdf'):
                pdf_path = os.path.join(directory_path, filename)
                self.process_pitch_deck(pdf_path)
        
        return self.results
    
    def to_dataframe(self):
        """Convert results to a pandas DataFrame."""
        return pd.DataFrame.from_dict(self.results, orient='index')
    
    def export_to_csv(self, output_path="pitch_deck_data.csv"):
        """Export the results to a CSV file."""
        df = self.to_dataframe()
        df.to_csv(output_path, index_label="filename")
        print(f"Data exported to {output_path}")

# Example usage
if __name__ == "__main__":
    scraper = PitchDeckScraper()
    
    # Process a single PDF
    # result = scraper.process_pitch_deck("path/to/pitch_deck.pdf")
    # print(result)
    
    # Process a directory of PDFs
    # directory_results = scraper.process_directory("path/to/pitch_decks")
    # df = scraper.to_dataframe()
    # print(df)
    
    # Export to CSV
    # scraper.export_to_csv("startup_data.csv")
