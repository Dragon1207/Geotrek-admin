import factory

from django.conf import settings
from django.contrib.gis.geos import Polygon, MultiPolygon

from mapentity.helpers import bbox_split_srid_2154

from . import models


# Don't intersect with geom from PathFactory
SPATIAL_EXTENT = (200000, 300000, 1100000, 1200000)

# Create 16 cities and 4 districts distinct same-area zone covering the spatial_extent and cycle on it
geom_city_iter = bbox_split_srid_2154(SPATIAL_EXTENT, by_x=4, by_y=4, cycle=True)
geom_district_iter = bbox_split_srid_2154(SPATIAL_EXTENT, by_x=2, by_y=2, cycle=True)
geom_area_iter = bbox_split_srid_2154(SPATIAL_EXTENT, by_x=2, by_y=2, cycle=True)


class CityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.City

    code = factory.Sequence(lambda n: "#%s" % n)  # id (!) with max_length=6
    name = factory.Sequence(lambda n: "City name %s" % n)
    geom = factory.Sequence(lambda _: MultiPolygon(Polygon.from_bbox(next(geom_city_iter)), srid=settings.SRID))


class DistrictFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.District

    name = factory.Sequence(lambda n: "District name %s" % n)
    geom = factory.Sequence(lambda _: MultiPolygon(Polygon.from_bbox(next(geom_district_iter)), srid=settings.SRID))


class RestrictedAreaTypeFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.RestrictedAreaType

    name = factory.Sequence(lambda n: "Restricted name %s" % n)


class RestrictedAreaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.RestrictedArea

    name = factory.Sequence(lambda n: "Restricted area name %s" % n)
    geom = factory.Sequence(lambda _: MultiPolygon(Polygon.from_bbox(next(geom_area_iter)), srid=settings.SRID))
    area_type = factory.SubFactory(RestrictedAreaTypeFactory)
