from core.domain.events import BaseEvent

from ..value_objects.ids import SiteId


class SiteCreated(BaseEvent[SiteId]):
    """A site was created."""

    def __init__(self, site_id: SiteId) -> None:
        super().__init__()
        self._site_id = site_id

    def get_aggregate_id(self) -> SiteId:
        return self._site_id

    def get_event_name(self) -> str:
        return "users.site.created"


class SiteActivated(BaseEvent[SiteId]):
    """A site was (re)activated."""

    def __init__(self, site_id: SiteId) -> None:
        super().__init__()
        self._site_id = site_id

    def get_aggregate_id(self) -> SiteId:
        return self._site_id

    def get_event_name(self) -> str:
        return "users.site.activated"


class SiteDeactivated(BaseEvent[SiteId]):
    """A site was deactivated."""

    def __init__(self, site_id: SiteId) -> None:
        super().__init__()
        self._site_id = site_id

    def get_aggregate_id(self) -> SiteId:
        return self._site_id

    def get_event_name(self) -> str:
        return "users.site.deactivated"
