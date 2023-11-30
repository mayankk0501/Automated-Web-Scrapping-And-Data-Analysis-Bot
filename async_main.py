import asyncio
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from seleniumwire import webdriver as swd
from selenium.webdriver.common.action_chains import ActionChains
import time
import json
import logging
import csv
import random
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

#------------------------------------------------------------------------------------------------------------------------------

logging.basicConfig(filename='test_log.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info("Script started")

#------------------------------------------------------------------------------------------------------------------------------

async def get_urls_async(driver, keywords):
    url_list = []
    for word in keywords:
        try:
            input_product = driver.find_element("xpath", '//*[@id="twotabsearchtextbox"]')
            for _ in range(15):
                input_product.send_keys(Keys.BACKSPACE)
            input_product.send_keys(word)
            input_product.send_keys(Keys.ENTER)
            await asyncio.sleep(3)
            page_html = driver.page_source
            soup = BeautifulSoup(page_html, 'html.parser')
            url_class = soup.select('div.a-section.a-spacing-base')
            for _ in url_class:
                pcode = _.select_one('a.a-link-normal.s-no-outline')['href'].split('dp/')[-1].split('/')[0]
                if pcode:
                    url_list.append("https://www.amazon.in/dp/" + pcode)
            logging.info(word + " search successful - Keyword search successful")
            await asyncio.sleep(1)
        except Exception as e:
            logging.error(f"Error in {word} search: {e}")
    if len(url_list)>1:
        logging.info("Url list generated")
    else:
        logging.error("Error in generating url list")
    return url_list

#------------------------------------------------------------------------------------------------------------------------------

async def get_product_data_async(driver, url):
    driver.get(url)
    page_html = driver.page_source
    soup = BeautifulSoup(page_html, 'html.parser')
    try:
        Title = soup.select_one('span#productTitle').text
    except:
        Title = ''
    try:
        Brand = soup.select_one('a#bylineInfo').text.replace('Brand: ','')
        if 'tore' in Brand:
            Brand = soup.select_one('span.a-size-base.po-break-word').text
    except:
        Brand = ''
    try:
        MRP = soup.select_one('div.a-section.a-spacing-small.aok-align-center').select_one('span.a-offscreen').text.replace('₹','')
    except:
        MRP = '' 
    try:
        ASP = soup.select_one('div.a-section.a-spacing-none.aok-align-center').select_one('span.a-price-whole').text
    except:
        ASP = ''
    if ASP == '':
        ASP = MRP
    if MRP == '':
        MRP = ASP
    try:
        Availability = soup.select_one('div#availability-string').text
    except:
        Availability = 'Out of stock'
    try:
        Image_url = soup.select_one('img#landingImage')['src']
    except:
        Image_url = ''
    try:
        About_this_item = soup.select_one('div#feature-bullets').text
    except:
        About_this_item = ''
    try:
        Rating = soup.select_one('div#averageCustomerReviews').select_one('span.a-size-base.a-color-base').text
    except:
        Rating = ''
    try:
        Total_rating = soup.select_one('span#acrCustomerReviewText').text.replace('ratings','').replace(',','')
    except:
        Total_rating = ''
    try:
        if (soup.select_one('img.alm-mod-logo')):
            On_fresh = 'Yes'
        else:
            On_fresh = 'No'
    except:
        On_fresh = ''
    # ... (rest of your data extraction logic)
    return {'Product_url': url, 'Title': Title, 'Brand': Brand, 'MRP': MRP,
            'ASP': ASP, 'Availability': Availability, 'Image_url': Image_url,
            'About_this_item': About_this_item, 'Rating': Rating,
            'Total_rating': Total_rating, 'On_fresh': On_fresh }

#------------------------------------------------------------------------------------------------------------------------------

async def main():
    # Set up the WebDriver with Selenium-Wire
    options = Options()
    prefs = {"download.default_directory": r"F:\Task2"}
    options.add_experimental_option("prefs", prefs)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-infobars")
    # options.add_argument("--incognito")
    # options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")
    options.page_load_strategy = 'normal'

    proxy_pool = ['http://localhost:8080', 'http://localhost:8888', 'http://localhost:0000']
    proxy = random.choice(proxy_pool)
    wire_options = {
            'proxy': {
                'http': proxy,
                'https': proxy,
            }
        }

    # driver = swd.Chrome(options=options, seleniumwire_options=wire_options)
    driver = webdriver.Chrome(options=options)
    # driver.maximize_window()
    driver.get('https://www.amazon.in/')

    # Add cookies to the WebDriver instance
    try:
        logging.info("Adding Cookies")
        with open('cookies.json', 'r') as file:
            cookies = json.load(file)
        for cookie in cookies:
            driver.add_cookie(cookie)
        await asyncio.sleep(2)
        driver.refresh()
        await asyncio.sleep(2)
        logging.info("Cookies addition successful")
        logging.info("Login successful")
    except Exception as e:
        logging.error(f"Error in adding cookies")

    keywords = ['cold drinks', 'soft drinks', 'drink']
    url_list = await get_urls_async(driver, keywords)
    product_data_list = []

    try:
        logging.info("Collecting products data")
        tasks = [get_product_data_async(driver, url) for url in url_list]
        product_data_list = await asyncio.gather(*tasks)
        logging.info("Data collection successful")
    except Exception as e:
        logging.error("Error in collecting products data")

    try:
        logging.info("Generating CSV")
        generate_csv(product_data_list)
        logging.info("CSV generated successfully")
    except Exception as e:
        logging.error("Error in generating CSV")

    await asyncio.sleep(1)
    driver.quit()

    logging.info("Generating insights from data")
    # Load your data from the CSV file
    df = pd.read_csv('data.csv')

    # Visualization 1: Brand Market Share
    plt.figure(figsize=(5, 5))
    brand_counts = df['Brand'].value_counts()
    brand_percentages = brand_counts / brand_counts.sum() * 100
    filtered_brands = brand_percentages[brand_percentages >= 2]
    s = filtered_brands.sum()
    filtered_brands['Others'] = (100.000000-s)
    plt.pie(filtered_brands, labels=filtered_brands.index, autopct='%1.1f%%', startangle=140)
    plt.title('Distribution of Products by Brand')
    plt.savefig('Brand distribution.png')
    # plt.show()

    # Visualization 2: Availability Status
    plt.figure(figsize=(5, 5))
    status_counts = df['Availability'].value_counts()
    plt.pie(status_counts, labels=status_counts.index, autopct='%1.1f%%', startangle=140)
    plt.title('Availability Count')
    plt.savefig('Availability Count.png')
    # plt.show()

    # Visualization 3: Availability Analysis
    plt.figure(figsize=(5, 5))
    sns.countplot(x='Availability', data=df)
    plt.title('Availability Analysis')
    plt.xlabel('Availability')
    plt.ylabel('Count')
    plt.savefig('Availability.png')
    # plt.show()

    # Visualization 4: Rating Analysis
    plt.figure(figsize=(5, 5))
    sns.histplot(df['Rating'], bins=30, kde=True)
    plt.title('Distribution of Ratings')
    plt.xlabel('Rating')
    plt.ylabel('Frequency')
    plt.savefig('Rating Distribution.png')
    # plt.show()

    # Visualization 5: Availability on Amazon Fresh
    plt.figure(figsize=(5, 5))
    On_fresh_counts = df['On_fresh'].value_counts()
    plt.pie(On_fresh_counts, labels=On_fresh_counts.index, autopct='%1.1f%%', startangle=140)
    plt.title('Availability on Amazon Fresh')
    plt.savefig('Availability on amazon fresh.png')
    # plt.show()

    logging.info("Insights generation successful")

    logging.info("Script finished")

#------------------------------------------------------------------------------------------------------------------------------

def generate_csv(product_data_list):
    csv_columns = ['Product_url', 'Title', 'Brand', 'MRP', 'ASP', 'Availability', 'Image_url', 'About_this_item',
                   'Rating', 'Total_rating', 'On_fresh']
    csv_file_path = 'data.csv'
    with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=csv_columns)
        writer.writeheader()
        for data in product_data_list:
            writer.writerow(data)
    print(f"Product data saved to {csv_file_path}")

#------------------------------------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(main())
