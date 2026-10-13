import csv
import os

# One row per fill. "Price" is what was actually paid/received per share
# before fees (PortSummarize reads Symbol/Side/Volume/Price by name);
# "Order Price" is what was asked for, so the two side by side show what
# happened at the time -- a limit filled at its price or better, a market
# order one price step past the last price.
FIELDNAMES = [
    'Order Number', 'owner', 'Type', 'Side', 'Symbol', 'Volume',
    'Order Price', 'Market Price', 'Price', 'Placed', 'Timestamp',
]


class Transaction:
    def __init__(self, team_name, filename_suffix="transaction_log.csv"):
        self.transaction_log = []
        self.team_name = team_name

        folder = os.path.join("result", team_name)
        os.makedirs(folder, exist_ok=True)
        self.csv_file = os.path.join(folder, f"{team_name}_{filename_suffix}")

        if not os.path.exists(self.csv_file):
            with open(self.csv_file, mode='w', newline='') as file:
                csv.DictWriter(file, fieldnames=FIELDNAMES).writeheader()
        else:
            self._upgrade_header()

    def _upgrade_header(self):
        """A log carried over from an older engine has fewer columns. Rewrite
        it under the current header (old rows get blanks in the new columns)
        so today's rows don't land under the wrong column names."""
        with open(self.csv_file, mode='r', newline='') as file:
            reader = csv.DictReader(file)
            if reader.fieldnames == FIELDNAMES:
                return
            rows = list(reader)
        with open(self.csv_file, mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=FIELDNAMES, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)

    def create_transaction_log(self, order):
        self.transaction_log.append({
            'Order Number': order.get_order_number(),
            'owner': order.get_ownerPortfolio().get_owner(),
            'Type': order.get_order_type(),
            'Side': order.get_side(),
            'Symbol': order.get_symbol(),
            'Volume': order.get_volume(),
            'Order Price': order.get_price(),
            'Market Price': order.get_fill_market_price(),
            'Price': order.get_fill_price(),
            'Placed': order.get_formatted_placed_timestamp(),
            'Timestamp': order.get_formatted_timestamp(),
        })

    def flush_logs(self):
        with open(self.csv_file, mode='a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
            writer.writerows(self.transaction_log)
