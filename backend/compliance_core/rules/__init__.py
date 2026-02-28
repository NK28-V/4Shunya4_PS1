from .gdpr import GdprEncryptionFlagsRule
from .soc2 import Soc2MfaEnabledRule, Soc2RbacPresentRule

DEFAULT_RULES = [
    Soc2MfaEnabledRule(),
    Soc2RbacPresentRule(),
    GdprEncryptionFlagsRule(),
]

__all__ = [
    "DEFAULT_RULES",
    "GdprEncryptionFlagsRule",
    "Soc2MfaEnabledRule",
    "Soc2RbacPresentRule",
]

