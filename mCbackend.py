"""MarktComparator compares products and markets to return what market is best to buy what products.

This is the back-end module.

Features:
    Parse file to get list of markets and their products.
    Retrieve a list of market: price couples for each product.
    Insert, edit and delete product entries.
    Available in various languages.

The JSON file containing the data should look something like this:
{
   "Market name":
   {
       "Product name"   : 3.59,
       [etc]
   },
   [etc]
}
"""
# TODO: Reinsert all data from receipts in JSON to avoid errors.
from typing import Tuple, List, Optional, Union
import json

json_file = "products.json"
with open(json_file, "r",  encoding="UTF-8") as database:
    markets = json.load(database)  # Access with markets["Market name"]["Product name"] = 3.59.


class Lang:  # TODO: Rework this shite. https://docs.wxpython.org/internationalization.html
    """Singleton for handling localisation.

    Invoke localisation strings with loc.lan["section"].
    """

    def __init__(self, file: str):
        """Load localisation file and create shorthands for its usage."""
        self.loc_file = file
        with open(self.loc_file, "r", encoding="UTF-8") as local:
            self.la = json.load(local)

        if self.la["selected"] in self.la and self.la["selected"] != "selected":  # Check if valid language.
            self.o = self.la["selected"]
        else:
            self.o = "English"  # Default to English if invalid

        self.lan = self.la[self.o]  # Create shorthand for selected language.

    def change(self, selection: str):
        """Update localisation shorthand and localisation file."""
        file_copy = self.la
        file_copy["selected"] = selection

        with open(self.loc_file, "w", encoding="UTF-8") as outgoing:
            json.dump(file_copy, outgoing, indent=4, ensure_ascii=False)  # Overwrite file with new dictionary.


loc = Lang("localisation.json")  # Access localised strings with loc.lan["section"].


def update_json():
    """Rewrite database with updated dictionary."""
    with open(json_file, "w", encoding="UTF-8") as outgoing:
        json.dump(markets, outgoing, indent=4, ensure_ascii=False)


def list_products() -> Optional[list]:
    """List all products from a given market.

    Returns:
        List of strings containing the name of each unique product.
        None, if the list would be empty.
    """

    listed = []
    for market_name, market_products in markets.items():
        for product in market_products:
            if product not in listed:
                listed.append(product)

    if len(listed) == 0:
        return None
    else:
        return listed


def delete_product(product: str, in_market: Union[str, List[str]]="all") -> bool:
    """Delete a product from one or more markets.

    If the market doesn't contain any other product, delete the market as well.

    Parameters:
        product: a str containing the name of the product to delete.
        in_market: a str or a list of str containing the name of the market(s) from which to delete the product.
                   Defaults to "all", which deletes the product from all markets it appears in.

    Returns:
        True if the deletion was successful.
        False if the deletion raised an exception (product or market not found).
    """
    if in_market.lower() == "all":
        for market in markets:
            if product in market:
                del markets[market][product]  # Delete the product for each market it appears in.
                if not markets[market]:
                    del markets[market]  # If, after product deletion, the market is empty, delete it.
        return True

    try:
        if isinstance(in_market, list):  # If input is a list (of market names).
            for market in in_market:
                if product in market:
                    del markets[market][product]  # Delete the product for each entered market it appears in.
                    if not markets[market]:
                        del markets[market]  # If, after product deletion, the market is empty, delete it.
        else:  # If input is a string (market name).
            del markets[in_market][product]
            if not markets[in_market]:
                del markets[in_market]
        update_json()  # Save edits.
        return True
    except KeyError:
        return False


def update_product(product: str, in_market: str, cost: float):
    """Insert an entry in the json file at database[market][product] = price or modify existing.

    If the market doesn't exist, create the market too.

    Parameters:
        product: a str containing the name of the product.
        in_market: a str containing the market to insert the product in.
        cost: a float containing the price of the product.
    """

    if in_market not in markets:
        markets[in_market] = {}  # Create the market if it doesn't exist yet.

    markets[in_market][product] = cost  # Add the entry.

    update_json()  # Update database.


def find_product(product: str) -> List[Optional[Tuple[str, float]]]:
    """List the markets and prices for a product and sort them by cheapest.

    Returns:
        A list of (market: str, price: float) tuples sorted by lowest float.
        An empty list if no result was found.
    """

    found_in = []

    for (current_market, its_products) in markets.items():
        for (product_name, product_price) in its_products.items():
            if product_name == product:
                found_in.append((current_market, product_price))

    return found_in
