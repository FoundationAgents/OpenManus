class EventSystemConfig:
    """Configuration class for the event system."""

    def __init__(
        self,
        bus_type: str = "simple",  # "simple" or "chainable"
        max_concurrent_events: int = 100,
        enable_logging: bool = False,
        enable_retry: bool = True,
        enable_error_isolation: bool = True,
        enable_metrics: bool = True,
        log_level: str = "INFO",
    ):
        self.bus_type = bus_type
        self.max_concurrent_events = max_concurrent_events
        self.enable_logging = enable_logging
        self.enable_retry = enable_retry
        self.enable_error_isolation = enable_error_isolation
        self.enable_metrics = enable_metrics
        self.log_level = log_level
