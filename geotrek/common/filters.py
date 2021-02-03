from django.utils.translation import gettext_lazy as _

from django_filters import RangeFilter, Filter, ModelChoiceFilter


class OptionalRangeFilter(RangeFilter):
    def __init__(self, *args, **kwargs):
        super(OptionalRangeFilter, self).__init__(*args, **kwargs)
        self.field.fields[0].label = _('min %s') % self.field.label
        self.field.fields[1].label = _('max %s') % self.field.label


class YearFilter(Filter):
    def do_filter(self, qs, year):
        return qs.filter(**{
            '%s__year' % self.field_name: year,
        }).distinct()

    def filter(self, qs, value):
        try:
            year = int(value)
        except (ValueError, TypeError):
            year = -1
        return qs if year < 0 else self.do_filter(qs, year)


class ValueFilter(Filter):
    def do_filter(self, qs, value):
        return qs.filter(**{
            '%s' % self.field_name: value,
        }).distinct()

    def filter(self, qs, value):
        try:
            new_value = int(value)
        except (ValueError, TypeError):
            new_value = -1
        return qs if new_value < 0 else self.do_filter(qs, new_value)


class YearBetweenFilter(YearFilter):
    def __init__(self, *args, **kwargs):
        assert len(kwargs['field_name']) == 2
        super(YearBetweenFilter, self).__init__(*args, **kwargs)

    def do_filter(self, qs, year):
        begin, end = self.field_name
        qs = qs.filter(**{
            '%s__lte' % begin: year,
            '%s__gte' % end: year,
        })
        return qs


class RightFilter(ModelChoiceFilter):
    model = None
    queryset = None

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('queryset', self.get_queryset())
        super(RightFilter, self).__init__(*args, **kwargs)
        self.field.widget.attrs['class'] = self.field.widget.attrs.get('class', '') + 'right-filter'
        self.field.widget.renderer = None

    def get_queryset(self, request=None):
        if self.queryset is not None:
            return self.queryset
        return self.model.objects.all()
