import pandas as pd
import os


class summarize:

    @staticmethod
    def create_transaction_summarize(team_name):
        base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "result", team_name)
        )
        os.makedirs(base_dir, exist_ok=True)

        input_csv = f"{team_name}_transaction_log.csv"
        output_csv = f"{team_name}_portfolios_transaction_summary.csv"

        input_csv = os.path.join(base_dir, input_csv)
        output_csv = os.path.join(base_dir, output_csv)

        if not os.path.exists(input_csv):
            raise FileNotFoundError(
                f"[ERROR] Cannot find transaction log at '{input_csv}'"
            )

        df = pd.read_csv(input_csv)

        comm_rate = 0.00157
        vat_rate = 0.07

        grouped = df.groupby("Symbol")

        summary_rows = []

        total_buy_comm = total_sell_comm = 0.0
        total_buy_vat = total_sell_vat = 0.0
        total_paid = total_received = 0.0
        total_buy_count = total_sell_count = 0
        total_buy_volume = total_sell_volume = 0

        for symbol, group in grouped:
            buy_df = group[group["Side"] == "Buy"]
            sell_df = group[group["Side"] == "Sell"]

            # Buy calculations
            buy_volume = buy_df["Volume"].sum()
            avg_buy_price = buy_df["Price"].mean() if not buy_df.empty else 0.0
            buy_amount = buy_volume * avg_buy_price
            buy_comm = buy_amount * comm_rate
            buy_vat = buy_comm * vat_rate
            paid_amount = buy_amount + buy_comm + buy_vat
            buy_count = len(buy_df)

            # Sell calculations
            sell_volume = sell_df["Volume"].sum()
            avg_sell_price = sell_df["Price"].mean() if not sell_df.empty else 0.0
            sell_amount = sell_volume * avg_sell_price
            sell_comm = sell_amount * comm_rate
            sell_vat = sell_comm * vat_rate
            received_amount = sell_amount - sell_comm - sell_vat
            sell_count = len(sell_df)

            # Totals
            total_buy_comm += buy_comm
            total_sell_comm += sell_comm
            total_buy_vat += buy_vat
            total_sell_vat += sell_vat
            total_paid += paid_amount
            total_received += received_amount
            total_buy_count += buy_count
            total_sell_count += sell_count
            total_buy_volume += buy_volume
            total_sell_volume += sell_volume

            summary_rows.append(
                {
                    "Symbol": symbol,
                    "Buy Count": buy_count,
                    "Buy Volume": buy_volume,
                    "Buy Avg Price": round(avg_buy_price, 2),
                    "Buy Amount": round(buy_amount, 2),
                    "Buy Comm": round(buy_comm, 2),
                    "Buy VAT": round(buy_vat, 2),
                    "Paid Amount": round(paid_amount, 2),
                    "Sell Count": sell_count,
                    "Sell Volume": sell_volume,
                    "Sell Avg Price": round(avg_sell_price, 2),
                    "Sell Amount": round(sell_amount, 2),
                    "Sell Comm": round(sell_comm, 2),
                    "Sell VAT": round(sell_vat, 2),
                    "Received Amount": round(received_amount, 2),
                }
            )

        # Append total row
        summary_rows.append(
            {
                "Symbol": "TOTAL",
                "Buy Count": total_buy_count,
                "Buy Volume": total_buy_volume,
                "Buy Comm": round(total_buy_comm, 2),
                "Buy VAT": round(total_buy_vat, 2),
                "Paid Amount": round(total_paid, 2),
                "Sell Count": total_sell_count,
                "Sell Volume": total_sell_volume,
                "Sell Comm": round(total_sell_comm, 2),
                "Sell VAT": round(total_sell_vat, 2),
                "Received Amount": round(total_received, 2),
            }
        )

        summary_df = pd.DataFrame(summary_rows)
        summary_df.to_csv(output_csv, index=False)
        print(f"[OK] Summary saved to {output_csv}")
