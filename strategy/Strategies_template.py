from abc import ABC, abstractmethod
from datetime import timedelta

class Strategy_template(ABC):
    def __init__(self, owner, strategy_name, handler, timeframe):
        self.owner = owner
        self.strategy_name = strategy_name
        self.handler = handler
        self.timeframe = timeframe

    @abstractmethod
    def on_data(self, bar):
        """
        Called once per tick with the CURRENT (live-updating) OHLCV bar
        for this.timeframe -- {"ShareCode", "Timestamp", "Open", "High",
        "Low", "Close", "Volume"}. Never waits for the bar to close.
        MUST be implemented by subclass.
        DO NOT EDIT THIS CLASS.
        """
        pass
