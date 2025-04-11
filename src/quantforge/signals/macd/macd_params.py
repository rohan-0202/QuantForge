from dataclasses import dataclass


@dataclass(frozen=True)
class MacdParams:
    fast_period: int
    slow_period: int
    signal_period: int

    def __post_init__(self):
        """Validate that all period parameters are greater than 0."""
        if self.fast_period <= 0:
            raise ValueError("fast_period must be greater than 0")
        if self.slow_period <= 0:
            raise ValueError("slow_period must be greater than 0")
        if self.signal_period <= 0:
            raise ValueError("signal_period must be greater than 0")
        if self.fast_period >= self.slow_period:
            raise ValueError("fast_period must be less than slow_period")

    @classmethod
    def default(cls) -> "MacdParams":
        """Return a default instance of MacdParams with common defaults."""
        return cls(
            fast_period=12,
            slow_period=26,
            signal_period=9,
        ) 