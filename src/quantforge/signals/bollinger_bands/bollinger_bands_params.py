from dataclasses import dataclass


@dataclass(frozen=True)
class BollingerBandsParams:
    window: int
    window_dev: int  # Number of standard deviations

    def __post_init__(self):
        """Validate parameters."""
        if self.window <= 0:
            raise ValueError("window must be greater than 0")
        if self.window_dev <= 0:
            raise ValueError("window_dev (standard deviations) must be greater than 0")

    @classmethod
    def default(cls) -> "BollingerBandsParams":
        """Return a default instance with common defaults."""
        return cls(window=20, window_dev=2) 