import sys
import asyncio
sys.path.append('.')
from src.scraper.menu_url_scraper import MenuUrlScraper
from src.scraper.pdf_downloader import PDFDownloader

async def main():
    try:
        scraper = MenuUrlScraper()
        latest = await scraper.get_latest_pdf()
        print(f"URL found: {latest.url}")
        
        downloader = PDFDownloader()
        pdf_bytes = await downloader.download(latest.url)
        
        dest = "tests/fixtures/CARDAPIO-UFCA-MARÇO-SEGUNDA-SEMANA-2026.pdf"
        with open(dest, 'wb') as f:
            f.write(pdf_bytes)
        print("Success: File saved.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    asyncio.run(main())
