from dataclasses import dataclass


@dataclass(frozen=True)
class RsiParams:
    rsi_period: int
    oversold_threshold: int
    overbought_threshold: int

    def __post_init__(self):
        """Validate that all parameters are greater than 0."""
        if self.rsi_period <= 0:
            raise ValueError("rsi_period must be greater than 0")
        if self.oversold_threshold <= 0:
            raise ValueError("oversold_threshold must be greater than 0")
        if self.overbought_threshold <= 0:
            raise ValueError("overbought_threshold must be greater than 0")

    @classmethod
    def default(cls) -> "RsiParams":
        """Return a default instance of RsiParams with reasonable defaults."""
        return cls(
            rsi_period=14,
            oversold_threshold=30,
            overbought_threshold=70,
        )
