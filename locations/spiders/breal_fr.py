from locations.storefinders.beaumanoir import BeaumanoirSpider


class BrealFRSpider(BeaumanoirSpider):
    name = "breal_fr"
    item_attributes = {"brand": "Bréal", "brand_wikidata": "Q117235747", "name": "Bréal"}
    start_urls = [
        "https://www.breal.net/on/demandware.store/Sites-BRL_FR_SFRA-Site/fr_FR/Stores-FindStores?lat=46.6&long=2.4&radius=20000&showMap=false"
    ]
    # Cloudflare challenges plain requests.
    requires_proxy = "FR"

    def include_store(self, store: dict) -> bool:
        # The locator also lists multi-brand Vib's shops.
        return store["custom"]["BMNR_libBrand"] == "BREAL"
