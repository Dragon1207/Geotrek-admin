from django.utils.translation import gettext_lazy as _

from django_filters.filters import ModelMultipleChoiceFilter
import django_filters.rest_framework
from django.db.models import Q
from geotrek.authent.filters import StructureRelatedFilterSet
from django import forms
from django.utils.datetime_safe import datetime

from .models import TouristicContent, TouristicEvent, TouristicContentType1, TouristicContentType2
from geotrek.zoning.filters import ZoningFilterSet


class TypeField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return "{} ({})".format(str(obj), str(obj.category))


class TypeFilter(ModelMultipleChoiceFilter):
    field_class = TypeField


class TouristicContentFilterSet(ZoningFilterSet, StructureRelatedFilterSet):
    type1 = TypeFilter(queryset=TouristicContentType1.objects.all())
    type2 = TypeFilter(queryset=TouristicContentType2.objects.all())

    class Meta(StructureRelatedFilterSet.Meta):
        model = TouristicContent
        fields = StructureRelatedFilterSet.Meta.fields + [
            'published', 'category', 'type1', 'type2', 'themes',
            'approved', 'source', 'portal', 'reservation_system',
        ]


class AfterFilter(django_filters.DateFilter):
    def filter(self, qs, value):
        if not value:
            return qs
        return qs.filter(end_date__gte=value)


class BeforeFilter(django_filters.DateFilter):
    def filter(self, qs, value):
        if not value:
            return qs
        return qs.filter(begin_date__lte=value)


class CompletedFilter(django_filters.BooleanFilter):
    """
    Filter events with end_date in past (event completed)
    """
    @property
    def field(self):
        field = super().field
        field.initial = False
        return field

    def filter(self, qs, value):
        queryset = qs

        if value is True:
            queryset = queryset.filter(end_date__lt=datetime.today())

        elif value is False:
            queryset = queryset.exclude(end_date__lt=datetime.today())

        return queryset


class TouristicEventFilterSet(ZoningFilterSet, StructureRelatedFilterSet):
    after = AfterFilter(label=_("After"))
    before = BeforeFilter(label=_("Before"))
    completed = CompletedFilter(label=_("Completed"))

    class Meta(StructureRelatedFilterSet.Meta):
        model = TouristicEvent
        fields = StructureRelatedFilterSet.Meta.fields + [
            'published', 'type', 'themes', 'after',
            'before', 'approved', 'source', 'portal'
        ]


class TouristicEventApiFilterSet(django_filters.rest_framework.FilterSet):
    ends_after = django_filters.DateFilter(method='events_end_after')

    class Meta:
        model = TouristicEvent
        fields = ('ends_after', )

    def events_end_after(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(end_date__isnull=True) | Q(end_date__gte=value)
        )
