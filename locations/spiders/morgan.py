import re
from typing import Iterable

from locations.categories import Categories, apply_category
from locations.items import Feature
from locations.storefinders.beaumanoir import BeaumanoirSpider


class MorganSpider(BeaumanoirSpider):
    name = "morgan"
    item_attributes = {"brand": "Morgan", "brand_wikidata": "Q6911563", "name": "Morgan"}
    start_urls = [
        "https://www.morgandetoi.fr/on/demandware.store/Sites-M2T_FR_SFRA-Site/fr_FR/Stores-FindStores?lat=46.6&long=2.4&radius=20000&showMap=false"
    ]
    # Cloudflare challenges plain requests.
    requires_proxy = "FR"

    def include_store(self, store: dict) -> bool:
        custom = store["custom"]
        # Department store corners, multi-brand Sarenza Studio shops and pop-ups are out of scope.
        return (
            custom["BMNR_Type"] != "Grands Magasins and MarketPlace"
            and not custom["BMNR_Multi"]
            and "pop-up" not in store["name"].lower()
        )

    def post_process_feature(self, item: Feature, feature: dict) -> Iterable[Feature]:
        # Store pages without a slug (Switzerland) are empty shells.
        if not re.search(r"/magasins-.+-\d+\.html$", item["website"]):
            del item["website"]
        # NSI's Morgan entry doesn't cover Belgium or Spain.
        apply_category(Categories.SHOP_CLOTHES, item)
        yield item
