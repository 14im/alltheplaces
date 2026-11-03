import re
from collections.abc import AsyncIterator, Iterable
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from scrapy import Selector, Spider
from scrapy.http import FormRequest, Request, Response, TextResponse

from locations.categories import Categories, Sport, add_sport, apply_category
from locations.geo import bbox_contains
from locations.items import Feature

# Exact postcodes take precedence: Saint-Martin and Saint-Barthélemy share the 971 prefix.
NON_FR_POSTCODE_COUNTRIES = {
    "97150": "MF",
    "97133": "BL",
    "971": "GP",
    "972": "MQ",
    "973": "GF",
    "974": "RE",
    "975": "PM",
    "976": "YT",
    "980": "MC",
    "986": "WF",
    "987": "PF",
    "988": "NC",
}

# Committee codes (characters 2-4 of the club number) of overseas territories, for halls without a postcode.
NON_FR_COMMITTEE_COUNTRIES = {
    "9A": "GP",
    "9B": "MQ",
    "9C": "GF",
    "9D": "RE",
    "9E": "NC",
    "9F": "NC",
    "9G": "YT",
    "9H": "PF",
    "9W": "WF",
}

# (min lon, min lat, max lon, max lat): France with Corsica, then each overseas territory.
TERRITORY_BOUNDS = [
    (-5.5, 41.0, 9.8, 51.5),
    (-63.3, 14.2, -60.7, 18.2),
    (-56.5, 46.7, -56.0, 47.2),
    (-54.7, 2.0, -51.5, 6.0),
    (55.1, -21.5, 55.9, -20.8),
    (44.9, -13.1, 45.4, -12.5),
    (163.5, -23.0, 168.2, -19.5),
    (-155.0, -28.0, -134.0, -7.0),
    (-178.5, -14.5, -176.0, -13.0),
]


class FfttFRSpider(Spider):
    name = "fftt_fr"
    allowed_domains = ["carte.fftt.com"]

    async def start(self) -> AsyncIterator[Request]:
        yield Request("https://carte.fftt.com/organismes", callback=self.parse_committees)

    def parse_committees(self, response: Response, **kwargs: Any) -> Iterable[Request]:
        for label in response.xpath('//select[@id="organization-committee"]/option/text()').getall():
            if match := re.match(r"\s*D(\w{2})\s*·", label):
                yield FormRequest(
                    "https://carte.fftt.com/ajax_get_data",
                    formdata={"structures_department": match.group(1)},
                    headers={"X-Requested-With": "XMLHttpRequest"},
                    callback=self.parse,
                )

    def parse(self, response: TextResponse, **kwargs: Any) -> Iterable[Feature]:
        data = response.json()
        club_cards = Selector(text=data.get("clubs") or "")

        for name, halls in (data.get("clubsCoords") or {}).items():
            if not halls or halls[0].get("type") not in ("libre", "mixte") or halls[0].get("affilie") == 0:
                continue

            # Main halls first; the first hall with usable coordinates is the club's position.
            halls.sort(key=lambda hall: not hall.get("mainHall"))
            hall = halls[0]
            position = None
            for candidate in halls:
                lat, lon = candidate.get("latitude"), candidate.get("longitude")
                if lat is None or lon is None:
                    continue
                if any(bbox_contains(bounds, (lon, lat)) for bounds in TERRITORY_BOUNDS):
                    hall, position = candidate, (lat, lon)
                    break
                # Some halls have latitude and longitude swapped.
                if any(bbox_contains(bounds, (lat, lon)) for bounds in TERRITORY_BOUNDS):
                    hall, position = candidate, (lon, lat)
                    break

            if not position and not hall.get("street_address"):
                continue

            item = Feature()
            item["ref"] = hall["numero"]
            item["name"] = name
            if position:
                item["lat"], item["lon"] = position
            item["street_address"] = hall.get("street_address")
            item["city"] = hall.get("address_locality")
            if postcode := hall.get("postal_code"):
                item["postcode"] = postcode
                if country := NON_FR_POSTCODE_COUNTRIES.get(postcode) or NON_FR_POSTCODE_COUNTRIES.get(postcode[:3]):
                    item["country"] = country
            elif country := NON_FR_COMMITTEE_COUNTRIES.get(item["ref"][2:4]):
                item["country"] = country

            links = club_cards.xpath(
                '//div[@id=$id]//div[@class="col-description"][div[normalize-space()="Liens"]]//a/@href',
                id=f"club-{item['ref']}",
            ).getall()
            for link in links:
                # The field is free text: it holds emails, bare domains and social pages.
                match = re.fullmatch(r"(?:(https?)://)?([\w-]+(?:\.[\w-]+)+(?:[/?#]\S*)?)", link.strip(), re.I)
                if match and not re.search(r"facebook\.com|instagram\.com", link, re.I):
                    url = urlsplit(f"{(match.group(1) or 'http').lower()}://{match.group(2)}")
                    query = "&".join(
                        param
                        for param in url.query.split("&")
                        if param and not re.match(r"(?:utm_|_ga|fbclid|gclid)", param, re.I)
                    )
                    item["website"] = urlunsplit(url._replace(netloc=url.netloc.lower(), query=query))
                    break

            apply_category(Categories.CLUB_SPORT, item)
            add_sport(Sport.TABLE_TENNIS, item)

            yield item
