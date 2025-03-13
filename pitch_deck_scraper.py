import streamlit as st
import os
import re
import pandas as pd
import PyPDF2
import tempfile
from collections import defaultdict

class PitchDeckScraper:
    def __init__(self):
        self.results = defaultdict(dict)
        
    def extract_text_from_pdf(self, pdf_file):
        """Extract all text from a PDF file."""
        reader = PyPDF2.PdfReader(pdf_file)
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
    
    def process_pitch_deck(self, pdf_file, filename):
        """Process a single pitch deck and extract key information."""
        text = self.extract_text_from_pdf(pdf_file)
        
        company_name = self.extract_company_name(text) or "Unknown"
        
        self.results[filename] = {
            "company_name": company_name,
            "funding_sought": self.extract_funding_amount(text),
            "valuation": self.extract_valuation(text),
            "founders": self.extract_founders(text),
            "market_size_billions": self.extract_market_size(text)
        }
        
        return self.results[filename]
    
    def to_dataframe(self):
        """Convert results to a pandas DataFrame."""
        return pd.DataFrame.from_dict(self.results, orient='index')

# Streamlit app
def main():
    st.set_page_config(page_title="Pitch Deck Analyzer", layout="wide")
    
    st.title("Startup Pitch Deck Analyzer")
    st.write("""
    Upload startup pitch decks in PDF format to extract key information such as company name, 
    funding sought, valuation, founders, and market size.
    """)
    
    # Initialize session state for storing results
    if 'scraped_data' not in st.session_state:
        st.session_state.scraped_data = defaultdict(dict)
    
    # File uploader
    uploaded_files = st.file_uploader("Upload Pitch Deck PDFs", type=["pdf"], accept_multiple_files=True)
    
    if uploaded_files:
        scraper = PitchDeckScraper()
        
        with st.spinner('Processing PDFs...'):
            # Process each uploaded file
            for uploaded_file in uploaded_files:
                # Create a temporary file
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_file.write(uploaded_file.getvalue())
                    temp_path = temp_file.name
                
                try:
                    # Process the file
                    with open(temp_path, 'rb') as file:
                        result = scraper.process_pitch_deck(file, uploaded_file.name)
                        st.session_state.scraped_data[uploaded_file.name] = result
                finally:
                    # Clean up the temporary file
                    os.unlink(temp_path)
        
        # Convert results to DataFrame
        if st.session_state.scraped_data:
            df = pd.DataFrame.from_dict(st.session_state.scraped_data, orient='index')
            df = df.reset_index().rename(columns={"index": "filename"})
            
            # Display the DataFrame
            st.subheader("Extracted Data")
            st.dataframe(df)
            
            # Allow CSV download
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download as CSV",
                data=csv,
                file_name="pitch_deck_analysis.csv",
                mime="text/csv",
            )
            
            # Display some visualizations if we have enough data
            if len(df) > 1:
                st.subheader("Analysis")
                
                # Funding sought analysis
                st.write("### Funding Sought (in $ millions)")
                # Extract funding amounts from lists
                funding_data = []
                for idx, row in df.iterrows():
                    company = row['company_name']
                    if row['funding_sought'] and isinstance(row['funding_sought'], list):
                        for amount in row['funding_sought']:
                            funding_data.append({
                                'Company': company,
                                'Amount ($ millions)': amount
                            })
                
                if funding_data:
                    funding_df = pd.DataFrame(funding_data)
                    st.bar_chart(funding_df.set_index('Company'))
                
                # Market size analysis if available
                market_sizes = df[df['market_size_billions'].notna()]
                if not market_sizes.empty:
                    st.write("### Market Size (in $ billions)")
                    st.bar_chart(market_sizes.set_index('company_name')['market_size_billions'])

if __name__ == "__main__":
    main()
