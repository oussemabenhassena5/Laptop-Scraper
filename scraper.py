from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import json


driver = webdriver.Chrome()


def get_titles(page_url):
    driver.get(page_url)
    titles = driver.find_elements(By.CLASS_NAME, "product-title")

    titles_list = []
    for i in range(len(titles)):
        titles_list.append(titles[i].text)
    return titles_list


def get_references(page_url):
    driver.get(page_url)
    references = driver.find_elements(By.CLASS_NAME, "product-reference")

    references_list = []
    for i in range(len(references)):
        references_list.append(references[i].text)
    return references_list


def get_descriptions(page_url):
    driver.get(page_url)
    descriptions = driver.find_elements(By.CLASS_NAME, "listds")

    descriptions_list = []
    for i in range(len(descriptions)):
        descriptions_list.append(descriptions[i].text)
    return descriptions_list


def get_prices(page_url):
    driver.get(page_url)
    prices = driver.find_elements(By.CLASS_NAME, "price")

    prices_list = []
    for i in range(len(prices)):
        prices_list.append(prices[i].text)
        new_list = [x for x in prices_list if x != ""]
    return new_list


def get_availabilities(page_url):
    driver.get(page_url)
    availabilities = driver.find_elements(By.ID, "stock_availability")

    availabilities_list = []
    for i in range(len(availabilities)):
        availabilities_list.append(availabilities[i].text)
        new_list = [x for x in availabilities_list if x != ""]
    return new_list


def get_imgs(page_url):
    driver.get(page_url)
    imgs = driver.find_elements(By.CSS_SELECTOR, "img.center-block")
    imgs_list = []
    for img in imgs:
        imgs_list.append(img.get_attribute("src"))
    return imgs_list


driver.get("https://www.tunisianet.com.tn/702-ordinateur-portable")
n_pages = int(driver.find_elements(By.CLASS_NAME, "js-search-link")[-2].text)


for i in range(1, n_pages + 1):
    link = (
        "https://www.tunisianet.com.tn/702-ordinateur-portable?order=product.price.asc&page="
        + str(i)
    )
    titles = get_titles(link)
    references = get_references(link)
    descriptions = get_descriptions(link)
    prices = get_prices(link)
    availabilities = get_availabilities(link)
    imgs = get_imgs(link)


all_products = []
for i in range(len(titles)):
    dictionnary = {
        "title": str(titles[i]),
        "reference": str(references[i]),
        "description": str(descriptions[i]),
        "price": str(prices[i]),
        "availability": str(availabilities[i]),
        "imgs": str(imgs[i]),
    }
    all_products.append(dictionnary)


json_object = json.dumps(all_products, indent=4)
with open("products.json", "a+") as products:
    products.write(json_object)
