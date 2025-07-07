import asyncio
import csv
import time
from playwright.async_api import async_playwright

SEARCH_URL = "https://www.olx.ua/uk/list/q-%D0%B2%D1%8B%D0%BA%D0%B0%D1%87%D0%BA%D0%B0-%D0%B2%D1%8B%D0%B3%D1%80%D0%B5%D0%B1%D0%BD%D1%8B%D1%85-%D1%8F%D0%BC/#892824047"

async def get_ad_links(page):
    await page.goto(SEARCH_URL)
    await page.wait_for_selector('div[data-cy="l-card"] a[href^="/d/uk/obyavlenie/"]', timeout=5000)

    ad_links = await page.eval_on_selector_all(
        'div[data-cy="l-card"] a[href^="/d/uk/obyavlenie/"]',
        'elements => elements.map(el => el.href)'
    )
    ad_links = list(set(ad_links))
    full_links = [f"https://www.olx.ua{link}" if link.startswith('/') else link for link in ad_links]
    return full_links

async def get_phone_from_ad(page, url):
    try:
        await page.goto(url)
        await page.wait_for_selector('button[data-testid="show-phone"]', timeout=4000)
        await page.wait_for_timeout(1000)
        await page.click('button[data-testid="show-phone"]')

        await page.click('button[data-testid="show-phone"]')
        await page.wait_for_timeout(1000)

        desc_container = await page.query_selector('div[data-testid="ad_description"]')
        description_el = await desc_container.query_selector('div') if desc_container else None
        description = await description_el.inner_text() if description_el else "Нет описания"
        phone_el = await page.query_selector('a[data-testid="contact-phone"]')
        title_el = await page.query_selector('[data-testid="offer_title"] h4')
        name_el = await page.query_selector('h4[data-testid="user-profile-user-name"]')
        map_section = await page.query_selector('div[data-testid="map-aside-section"]')

        if map_section:
            p_elements = await map_section.query_selector_all('p')
            city_text = await p_elements[1].inner_text() if len(p_elements) > 1 else "Город не найден"
            region_text = await p_elements[2].inner_text() if len(p_elements) > 2 else "Область не найдена"
            city_text = city_text.strip().rstrip(',').strip()
            region_text = region_text.strip()
        else:
            city_text = "Город не найден"
            region_text = "Область не найдена"

        title = await title_el.inner_text() if title_el else "Без заголовка"
        name = await name_el.inner_text() if name_el else "Без имени"

        if phone_el:
            phone = await phone_el.inner_text()
            return [url, phone.strip(), name.strip(), title.strip(), description.strip(), city_text, region_text]

        return [url, "Не найден", name.strip(), title.strip(), description.strip(), city_text, region_text]
    except Exception as e:
        print(f"[!] Ошибка на {url}: {e}")
        return [url, "Ошибка", "", "", "", "", ""]

async def main():
    start_time = time.perf_counter()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print("[*] Собираем ссылки с поисковой выдачи...")
        ad_links = await get_ad_links(page)
        ad_links = ad_links[:10]
        print(f"[*] Найдено {len(ad_links)} объявлений")

        results = []
        for i, url in enumerate(ad_links):
            print(f"\n[{i + 1}] Обрабатываем: {url}")
            result = await get_phone_from_ad(page, url)
            results.append(result)
            print(f"📞 Номер: {result[1]}\n👤 Имя: {result[2]}\n📌 Заголовок: {result[3]}\n📝 Описание: {result[4]}\n🏙 Город: {result[5]}\n🌍 Область: {result[6]}")

        await browser.close()

    # Сохраняем в CSV
    filename = "olx_ads.csv"
    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["URL", "Телефон", "Имя", "Заголовок", "Описание", "Город", "Область"])
        writer.writerows(results)

    elapsed_time = time.perf_counter() - start_time
    print(f"\n[*] Скрипт завершён. Время выполнения: {elapsed_time / 60:.2f} минут")
    print(f"[*] Результаты сохранены в файл: {filename}")

if __name__ == "__main__":
    asyncio.run(main())
