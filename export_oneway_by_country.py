import overpass
from utils import sparql
import os
import json
import logging

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")

api = overpass.API(timeout=4000)
# api._GEOJSON_QUERY_TEMPLATE = "[out:json][timeout:600]{date};{query}out {verbosity};"

# get all countries in Europe from Wikidata
# get list of swiss municipalities incl. zip code
query = """
SELECT DISTINCT ?countryLabel ?country ?isoCode
{
  ?country wdt:P31/wdt:P279* wd:Q6256 .
  ?country wdt:P30 wd:Q46 .
  ?country wdt:P297 ?isoCode FILTER(?isoCode != "FR") .  # exclude France, since we use a separate script for France
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
}
ORDER BY ?isoCode
"""

result = sparql.query(query, endpoint="https://query.wikidata.org/sparql")
european_countries = [{k: v["value"] for k, v in m.items()} for m in result]
for country in european_countries:
    logging.debug(f"* Query overpass for {country['countryLabel']}...")
    gj_path = os.path.join(
        __location__, "oneway_countries", f"Oneway_{country['isoCode']}.geojson"
    )
    if os.path.exists(gj_path):
        continue
    query = f"""
    rel["ISO3166-1:alpha2"="{country['isoCode']}"]["boundary"="administrative"];
    map_to_area;
    way["highway"!="motorway"]["highway"!="trunk"]["highway"!="primary_link"]["highway"!="motorway_link"]["highway"!="path"]["highway"!="cycleway"]["highway"!="service"]["highway"!="steps"][!"lanes"][!"tramway"][!"railway"]["oneway"="yes"](area);
    """
    logging.debug(f" -> Query: {query}")
    try:
        response = api.get(query, responseformat="geojson", verbosity="body geom")
    except overpass.OverpassError:
        logging.exception(f"Error from Overpass for {country['countryLabel']}")
        pause = input("**** PRESS ANY KEY TO CONTINUE ****")
        continue
    logging.debug(f" -> Found {len(response['features'])} features.")
    with open(gj_path, "w") as f:
        f.write(json.dumps(response, indent=4))
    logging.debug(f" -> Save GeoJSON at {gj_path}.")
