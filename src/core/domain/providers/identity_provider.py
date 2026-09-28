from cuid2 import cuid_wrapper

_generator = cuid_wrapper()


class IdentityProvider:
    """The domain's single source of new identity values.

    Wraps cuid2: 24 lowercase alphanumeric characters, letter-first — always
    a valid :class:`~socialcrm.core.domain.value_objects.entity_id.EntityId`
    value. Centralizing generation here (instead of each VO wrapping cuid2
    itself) keeps id format decisions in one place and gives tests one seam
    to fake.
    """

    @staticmethod
    def next() -> str:
        """Return a fresh id string."""
        return _generator()
