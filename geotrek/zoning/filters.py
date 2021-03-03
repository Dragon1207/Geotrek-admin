from django_filters import FilterSet
from django.conf import settings
from django.db.models import Q
from django.contrib.gis.geos import GeometryCollection
from django.utils.translation import gettext_lazy as _


from geotrek.common.filters import RightFilter
from geotrek.zoning.models import City, District, RestrictedArea, RestrictedAreaType


class IntersectionFilter(RightFilter):
    """Inherit from ``RightFilter``, just to make sure the widgets
    will be initialized the same way.
    """

    def filter(self, qs, value):
        q = Q()
        for subvalue in value:
            q |= Q(geom__intersects=subvalue.geom)
        return qs.filter(q)


class IntersectionFilterCity(IntersectionFilter):
    model = City


class IntersectionFilterDistrict(IntersectionFilter):
    model = District


class IntersectionFilterRestrictedArea(RightFilter):
    model = RestrictedAreaType

    def filter(self, qs, value):
        if not value:
            return qs

        areas_geom = RestrictedArea.objects.filter(area_type__in=value).values_list('geom', flat=True)
        if areas_geom:
            geom = GeometryCollection(*areas_geom, srid=settings.SRID)
            return qs.filter(geom__intersects=geom)
        else:
            return qs.none()


class ZoningFilterSet(FilterSet):
    city = IntersectionFilterCity(label=_('City'), required=False)
    district = IntersectionFilterDistrict(label=_('District'), required=False)
    area_type = IntersectionFilterRestrictedArea(label=_('Restricted area'), required=False)
