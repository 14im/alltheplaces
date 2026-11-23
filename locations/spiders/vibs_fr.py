from locations.storefinders.beaumanoir import BeaumanoirSpider


class VibsFRSpider(BeaumanoirSpider):
    name = "vibs_fr"
    item_attributes = {"brand": "Vib's", "brand_wikidata": "Q121322478", "name": "Vib's"}
    start_urls = [
        "https://www.vibs.com/on/demandware.store/Sites-VIB_FR_SFRA-Site/fr_FR/Stores-FindStores?lat=46.6&long=2.4&radius=20000&showMap=false"
    ]
    # Cloudflare challenges plain requests.
    requires_proxy = "FR"

    def include_store(self, store: dict) -> bool:
        # The locator also lists the group's single-brand shops (Bonobo, Bréal, Cache Cache).
        return store["custom"]["BMNR_libBrand"] == "VIB'S"
