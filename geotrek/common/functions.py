from django.contrib.gis.db.models.functions import GeoFunc, GeomOutputGeoFunc
from django.db.models import CharField, FloatField


class Length(GeoFunc):
    """ ST_Length postgis function """
    output_field = FloatField()


class SimplifyPreserveTopology(GeomOutputGeoFunc):
    """ ST_SimplifyPreserveTopology postgis function """


class GeometryType(GeoFunc):
    """ GeometryType postgis function """
    output_field = CharField()
    function = 'GeometryType'
