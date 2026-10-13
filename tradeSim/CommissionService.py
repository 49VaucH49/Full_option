import bisect


class commissionService:

    comm = 0.00157
    vat = 0.07
    slippages = [0.01, 0.02, 0.05, 0.10, 0.25, 0.50, 1.00, 2.00]
    price_range = [    2,    5,    10,   25,   100,  200,  400]

    @classmethod
    def _get_slippage(cls, price: float) -> float:
        index = bisect.bisect(cls.price_range, price)
        return cls.slippages[index]

    @classmethod
    def market_fill_price(cls, last_price, side):
        """What a market order pays (Buy) or receives (Sell): the last price
        one price step against you, standing in for the other side's best quote."""
        step = cls._get_slippage(last_price)
        return last_price + step if side == "Buy" else last_price - step

    @classmethod
    def cal_unit_cost(cls, volume, match_price, side):
        """Per-share cash paid (Buy) or received (Sell) for a fill at
        match_price, commission and VAT included."""
        amount = match_price * volume
        comm_amount = amount * cls.comm
        vat = comm_amount * cls.vat
        if side == "Buy":
            return (amount + comm_amount + vat) / volume
        elif side == "Sell":
            return (amount - comm_amount - vat) / volume

    @classmethod
    def verify_transaction(cls, volume, price, cashBalance, slippage=True):
        """Whether cashBalance covers buying `volume` at `price`, fees included.
        slippage=True prices it like a market order (one step up); a limit
        order passes False, since it never pays more than its own price."""
        if slippage:
            total = cls.cal_All_Volume_commissionAndVat(volume, price)
        else:
            total = cls.cal_unit_cost(volume, price, "Buy") * volume
        return cashBalance >= total

    @classmethod
    def cal_All_Volume_commissionAndVat(cls, volume, price):
        match_price = price + cls._get_slippage(price)
        amount = match_price * volume
        comm_amount = amount * cls.comm
        vat = comm_amount * cls.vat
        return amount + comm_amount + vat

    @classmethod
    def cal_commissionAndVat(cls, volume, price, side):
        """Per-share cost of a market order at last price `price`: one step of
        slippage, then commission and VAT."""
        if side not in ("Buy", "Sell"):
            return None
        return cls.cal_unit_cost(volume, cls.market_fill_price(price, side), side)
