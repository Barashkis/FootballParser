from faker import Faker

from selenium import webdriver


def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--start-maximized')
    options.add_argument('--headless')
    options.add_argument('disable-notifications')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(f'user-agent={Faker().chrome()}')

    driver = webdriver.Chrome(options=options)

    return driver
