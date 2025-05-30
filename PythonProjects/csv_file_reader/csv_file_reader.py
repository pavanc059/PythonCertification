import os
# csv_file_reader.py
print(f'path {os.path.dirname(os.path.abspath(__file__))}')

file_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nyc_tlc_yellow_trips_2018_subset_1.csv")
lines = (line for line in open(file_name))
list_line = (s.rstrip().split(",") for s in lines)
cols = next(list_line)
print(f"Columns: {cols}")
company_dicts = (dict(zip(cols, data)) for data in list_line)
funding = (
    float(company_dict["tolls_amount"])
    for company_dict in company_dicts
    if int(company_dict["vendor_id"]) == 1
)
total_series_a = sum(funding)
print(f"Total series A fundraising: ${total_series_a}")