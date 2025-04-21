from dataclasses import dataclass


@dataclass(frozen=True)
class StochasticOscillatorParams:
    k_period: int
    d_period: int
    smooth_k: int
    oversold_threshold: int
    overbought_threshold: int

    def __post_init__(self):
        """Validate parameters."""
        if self.k_period <= 0:
            raise ValueError("k_period must be greater than 0")
        if self.d_period <= 0:
            raise ValueError("d_period must be greater than 0")
        if self.smooth_k <= 0:
            raise ValueError("smooth_k must be greater than 0")
        if not (0 <= self.oversold_threshold <= 100):
            raise ValueError("oversold_threshold must be between 0 and 100")
        if not (0 <= self.overbought_threshold <= 100):
            raise ValueError("overbought_threshold must be between 0 and 100")
        if self.oversold_threshold >= self.overbought_threshold:
            raise ValueError("oversold_threshold must be less than overbought_threshold")

    @classmethod
    def default(cls) -> "StochasticOscillatorParams":
        """Return a default instance with common defaults."""
        return cls(
            k_period=14,
            d_period=3,
            smooth_k=3,
            oversold_threshold=20,
            overbought_threshold=80,
        ) 