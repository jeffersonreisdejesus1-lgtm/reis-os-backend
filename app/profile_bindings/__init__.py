"""R2 bindings for ten distinct OCS profiles over the frozen R1 kernel."""

from .profiles import OCSProfile, PROFILES, get_profile, validate_profiles

__all__ = ["OCSProfile", "PROFILES", "get_profile", "validate_profiles"]
