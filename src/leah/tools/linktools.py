from datetime import datetime
from typing import List, Dict, Any, Callable
from selenium.webdriver.common.by import By
from langchain_core.tools import tool


from datetime import datetime
from typing import List, Dict, Any, Callable
import lxml.html
from lxml_html_clean import Cleaner
import html2text
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import requests 
from selenium.webdriver.remote.webdriver import WebDriver

def extract_main_content(html: bytes, base_url: str) -> str:
    """Extract the main content as markdown from HTML content, using lxml.html.clean."""
    try:
        # Parse the HTML content with explicit encoding
        if isinstance(html, str):
            html = html.encode('utf-8')
        document = lxml.html.fromstring(html.decode('utf-8'))
        
        # Use lxml's Cleaner to clean the document
        cleaner = Cleaner()
        cleaner.javascript = True  # Remove JavaScript
        cleaner.style = True       # Remove styles
        cleaner.links = False      # Remove links
        cleaned_content = cleaner.clean_html(document)
        
        # Convert cleaned content to string with explicit UTF-8 encoding
        main_content = lxml.html.tostring(cleaned_content, encoding='utf-8', pretty_print=True).decode('utf-8')
                
        # Limit the number of tokens to 1024
        tokens = main_content.split()
        print("Tokens: ", len(tokens))
        limited_content = ' '.join(tokens[:15000])
        
        # Convert limited content to markdown
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.body_width = 0  # Don't wrap text
        markdown_content = h.handle(limited_content)
        
        return markdown_content
    except Exception as e:
        print(f"Error in extract_main_content: {e}")
        return str(e)

def fetch_url_with_selenium(url: str, find_element: Callable = None, user_driver: WebDriver = None):
    if not user_driver:
        # Set up Selenium WebDriver with Chrome
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run headless Chrome
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--lang=en-US')
        chrome_options.add_argument('--accept-charset=utf-8')
        # Initialize the WebDriver
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    else:
        driver = user_driver
    
    try:
        # Fetch the URL
        driver.get(url)
        
        # Attempt to find the main content section
        if find_element:
            main_content_elements = find_element(driver)
            if main_content_elements:
                return "\n".join([extract_main_content(element.get_attribute('innerHTML'), url) for element in main_content_elements])
        
        try:
            main_content_element = driver.find_element(By.TAG_NAME, 'main')
        except:
            try:
                main_content_element = driver.find_element(By.TAG_NAME, 'article')
            except:
                try:
                    main_content_element = driver.find_element(By.CLASS_NAME, 'content')
                except:
                    main_content_element = driver.find_element(By.TAG_NAME, 'body')
        
        # Extract the page source from the main content with proper encoding
        html = main_content_element.get_attribute('innerHTML')
        
        # Extract main content
        main_content = extract_main_content(html, url)
        return main_content
    finally:
        # Close the WebDriver
        if not user_driver:
            driver.quit()

   
    
def context_template(context: str, extracted_url: str) -> str:
        now = datetime.now()
        today = now.strftime("%B %d, %Y")
        return f"""
I have downloaded the contents of the url {extracted_url} and found the following:

{context}

----
"""


@tool
def fetch_stock_info(symbol: str):
    """
    Fetches stock info for a given symbol
    """
    try:
        return fetch_url_with_selenium({"url": f"https://finance.yahoo.com/quote/{symbol}"})
    except Exception as e:
        return context_template("Error fetching the stock info", symbol)
        
@tool
def fetch_weather_info(latitude: str, longitude: str):
    """
    Fetches weather info for a given latitude and longitude
    """
    def find_weather_element(driver):
        try:
            current_conditions_body = driver.find_element(By.ID, 'current-conditions')
            seven_day_forecast = driver.find_element(By.ID, 'seven-day-forecast')
            return [current_conditions_body, seven_day_forecast]
        except:
            return None

    if not latitude or not longitude:
        return context_template("Error fetching weather data, try giving a more specific location", url)
    url = f"https://forecast.weather.gov/MapClick.php?lat={latitude}&lon={longitude}"
    return fetch_url_with_selenium(url, find_element=find_weather_element)
    
    
@tool
def fetch_link_with_selenium(url: str):
    """
    Fetches the contents of a given url using Selenium
    """
    return fetch_url_with_selenium(url)
    