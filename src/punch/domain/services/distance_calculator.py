from math import asin, cos, radians, sin, sqrt


class DistanceCalculator:
    """Calculate the distance between two GPS coordinates."""

    EARTH_RADIUS_METERS = 6_371_000

    @classmethod
    def calculate(
        cls,
        latitude_1: float,
        longitude_1: float,
        latitude_2: float,
        longitude_2: float,
    ) -> float:
        """
        Return the distance between two GPS coordinates in meters.
        """

        latitude_1 = radians(latitude_1)
        latitude_2 = radians(latitude_2)

        delta_latitude = radians(latitude_2 - latitude_1)
        delta_longitude = radians(longitude_2 - longitude_1)

        a = (
            sin(delta_latitude / 2) ** 2
            + cos(latitude_1)
            * cos(latitude_2)
            * sin(delta_longitude / 2) ** 2
        )

        c = 2 * asin(sqrt(a))

        return cls.EARTH_RADIUS_METERS * c