
from polars import time_range

import sys
from datetime import datetime, timezone, timedelta
from dateutil import parser
card_symbols = ["♠", "♥", "♦", "♣"]
card_values = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

startdateTime = datetime.now()
enddateTime = datetime.now() - timedelta(days=1)

pipeline = None

params = {'database': 'ods', 'successCollection': 'mmisEncounters', 'failureCollection': 'mmisEncounters-failed', 'pipeline': 'eps', 'cardsNames': ['MMIS Encounters Collection Data', 'Success Records', 'Failed Records']}

params = [(params['database'], params['successCollection']),(params['database'], params['successCollection'], str(startdateTime), str(enddateTime), 'total', pipeline),(params['database'], params['failureCollection'], str(startdateTime), str(enddateTime), 'total', pipeline),(params['database'], params['successCollection'], str(startdateTime), str(enddateTime), '837P', pipeline),(params['database'], params['successCollection'], str(startdateTime), str(enddateTime), '837P', pipeline),(params['database'], params['successCollection'], str(startdateTime), str(enddateTime), 'NCPDP', pipeline)]


def get_new_deck():
    new_deck = [values +" | "+ symbols  for values in card_values for symbols in card_symbols]
    print("New Deck of Cards total:" + str(len(new_deck)))
    for eachpair in new_deck:
        print(eachpair) 
        sys.exit() 

    return new_deck




get_new_deck()