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
    def from_wkt(cls, wkt_str: any, srid: int = 4326) -> "Location":
        """
        Crée un objet Location à partir d'un WKT, d'un objet GeoAlchemy2 ou d'une chaîne WKB hexadécimale.
        """
        # 1. Si c'est un objet GeoAlchemy2 (WKBElement)
        if hasattr(wkt_str, "desc") or type(wkt_str).__name__ == "WKBElement":
            try:
                from geoalchemy2.shape import to_shape
                geom = to_shape(wkt_str)
                return cls(latitude=geom.y, longitude=geom.x, srid=srid)
            except ImportError:
                pass

        text_val = str(wkt_str).strip()

        # 2. Si c'est une chaîne hexadécimale WKB/EWKB (ex: '0101000000...')
        if text_val.startswith("01") and all(c in "0123456789abcdefABCDEF" for c in text_val):
            try:
                from shapely import wkb
                geom = wkb.loads(bytes.fromhex(text_val))
                return cls(latitude=geom.y, longitude=geom.x, srid=srid)
            except Exception:
                pass

        # 3. Format WKT classique ('POINT (lon lat)')
        coords_str = text_val.replace("POINT", "").replace("point", "").strip(" ()")
        parts = coords_str.split()
        if len(parts) != 2:
            raise ValueError(f"Format de localisation invalide : {wkt_str}")

        # Rappel : WKT stocke (Longitude Latitude)
        longitude = float(parts[0])
        latitude = float(parts[1])

        return cls(latitude=latitude, longitude=longitude, srid=srid)
