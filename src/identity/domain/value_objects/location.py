"""Branded value objects for geographic location."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Location:
    """Geographic location representation bound to WGS84 (SRID 4326)."""

    latitude: float
    longitude: float
    srid: int = 4326

    def __post_init__(self) -> None:
        """Enforce domain validation rules for geographic coordinates."""
        if not (-90.0 <= self.latitude <= 90.0):
            raise ValueError(
                f"Invalid latitude: {self.latitude}. Must be between -90 and 90."
            )
        if not (-180.0 <= self.longitude <= 180.0):
            raise ValueError(
                f"Invalid longitude: {self.longitude}. Must be between -180 and 180."
            )

    def to_wkt(self) -> str:
        """
        Returns the Well-Known Text (WKT) representation for PostGIS.
        Note: WKT standard expects (Longitude Latitude).
        """
        return f"POINT({self.longitude} {self.latitude})"

    def to_sql_parameters(self) -> dict:
        """
        Prepares parameters for raw SQL queries involving PostGIS functions.
        """
        return {
            "wkt": self.to_wkt(),
            "srid": self.srid,
        }

    @classmethod
    def from_wkt(cls, wkt_str: str, srid: int = 4326) -> "Location":
        """
        Crée un objet Location à partir d'une chaîne WKT (ex: 'POINT(6.43 5.32)').
        """
        # Nettoyage simple de la chaîne WKT
        coords_str = wkt_str.replace("POINT", "").strip(" ()")
        parts = coords_str.split()
        if len(parts) != 2:
            raise ValueError(f"Format WKT invalide pour un Point : {wkt_str}")

        # Rappel : WKT stocke (Longitude Latitude)
        longitude = float(parts[0])
        latitude = float(parts[1])

        return cls(latitude=latitude, longitude=longitude, srid=srid)
