from django.contrib.gis.db.models.functions import GeoFunc, GeomOutputGeoFunc
from django.db.models import FloatField


class Length(GeoFunc):
    """ ST_Length postgis function """
    output_field = FloatField()


class SimplifyPreserveTopology(GeomOutputGeoFunc):
    pass
