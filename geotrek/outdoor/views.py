from django.conf import settings
from django.contrib.gis.db.models.functions import Transform
from django.db.models import Q
from mapentity.helpers import alphabet_enumeration
from mapentity.views import (MapEntityLayer, MapEntityList, MapEntityDetail, MapEntityDocument, MapEntityCreate,
                             MapEntityUpdate, MapEntityDelete, MapEntityFormat)

from geotrek.authent.decorators import same_structure_required
from geotrek.common.mixins.api import APIViewSet
from geotrek.common.mixins.views import CompletenessMixin, CustomColumnsMixin
from geotrek.common.views import DocumentBookletPublic, DocumentPublic, MarkupPublic
from geotrek.common.viewsets import GeotrekMapentityViewSet
from geotrek.outdoor.filters import SiteFilterSet, CourseFilterSet
from geotrek.outdoor.forms import SiteForm, CourseForm
from geotrek.outdoor.models import Site, Course
from geotrek.outdoor.serializers import SiteSerializer, CourseSerializer, CourseAPISerializer, \
    CourseAPIGeojsonSerializer, SiteAPISerializer, SiteAPIGeojsonSerializer


class SiteLayer(MapEntityLayer):
    properties = ['name']
    filterform = SiteFilterSet
    queryset = Site.objects.all()


class SiteList(CustomColumnsMixin, MapEntityList):
    queryset = Site.objects.all()
    filterform = SiteFilterSet
    mandatory_columns = ['id', 'name']
    default_extra_columns = ['super_practices', 'date_update']
    searchable_columns = ['id', 'name']


class SiteDetail(CompletenessMixin, MapEntityDetail):
    queryset = Site.objects.all()

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['can_edit'] = self.get_object().same_structure(self.request.user)
        return context


class SiteCreate(MapEntityCreate):
    model = Site
    form_class = SiteForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['site'] = self.request.GET.get('site')
        return kwargs


class SiteUpdate(MapEntityUpdate):
    queryset = Site.objects.all()
    form_class = SiteForm

    @same_structure_required('outdoor:site_detail')
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class SiteDelete(MapEntityDelete):
    model = Site

    @same_structure_required('outdoor:site_detail')
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class SiteDocumentPublicMixin:
    queryset = Site.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        site = self.get_object()

        context['headerimage_ratio'] = settings.EXPORT_HEADER_IMAGE_SIZE['site']
        context['object'] = context['content'] = site
        pois = list(site.all_pois.filter(published=True))
        if settings.TREK_EXPORT_POI_LIST_LIMIT > 0:
            pois = pois[:settings.TREK_EXPORT_POI_LIST_LIMIT]
        letters = alphabet_enumeration(len(pois))
        for i, poi in enumerate(pois):
            poi.letter = letters[i]
        context['pois'] = pois
        return context


class SiteDocument(MapEntityDocument):
    queryset = Site.objects.all()


class SiteDocumentPublic(SiteDocumentPublicMixin, DocumentPublic):
    pass


class SiteDocumentBookletPublic(SiteDocumentPublicMixin, DocumentBookletPublic):
    pass


class SiteMarkupPublic(SiteDocumentPublicMixin, MarkupPublic):
    pass


class SiteFormatList(MapEntityFormat, SiteList):
    mandatory_columns = ['id']
    default_extra_columns = [
        'structure', 'name', 'practice', 'description',
        'description_teaser', 'ambiance', 'advice', 'period', 'labels', 'themes',
        'portal', 'source', 'information_desks', 'web_links', 'accessibility', 'eid',
        'orientation', 'wind', 'ratings', 'managers', 'uuid',
    ]


class SiteViewSet(GeotrekMapentityViewSet):
    model = Site
    serializer_class = SiteSerializer
    filterset_class = SiteFilterSet

    def get_columns(self):
        return SiteList.mandatory_columns + settings.COLUMNS_LISTS.get('site_view',
                                                                       SiteList.default_extra_columns)

    def get_queryset(self):
        return self.model.objects.all()


class SiteAPIViewSet(APIViewSet):
    model = Site
    serializer_class = SiteAPISerializer
    geojson_serializer_class = SiteAPIGeojsonSerializer

    def get_queryset(self):
        qs = Site.objects.filter(published=True)
        if 'source' in self.request.GET:
            qs = qs.filter(source__name__in=self.request.GET['source'].split(','))
        if 'portal' in self.request.GET:
            qs = qs.filter(Q(portal__name=self.request.GET['portal']) | Q(portal=None))
        return qs.annotate(api_geom=Transform("geom", settings.API_SRID))


class CourseLayer(MapEntityLayer):
    properties = ['name']
    filterform = CourseFilterSet
    queryset = Course.objects.prefetch_related('type').all()


class CourseList(CustomColumnsMixin, MapEntityList):
    queryset = Course.objects.select_related('type').prefetch_related('parent_sites').all()
    filterform = CourseFilterSet
    mandatory_columns = ['id', 'name']
    default_extra_columns = ['parent_sites', 'date_update']
    searchable_columns = ['id', 'name']


class CourseDetail(CompletenessMixin, MapEntityDetail):
    queryset = Course.objects.prefetch_related('type').all()

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['can_edit'] = self.get_object().same_structure(self.request.user)
        return context


class CourseCreate(MapEntityCreate):
    model = Course
    form_class = CourseForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['parent_sites'] = self.request.GET.get('parent_sites')
        return kwargs


class CourseUpdate(MapEntityUpdate):
    queryset = Course.objects.all()
    form_class = CourseForm

    @same_structure_required('outdoor:course_detail')
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class CourseDelete(MapEntityDelete):
    model = Course

    @same_structure_required('outdoor:course_detail')
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class CourseDocumentPublicMixin:
    queryset = Course.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.get_object()

        context['headerimage_ratio'] = settings.EXPORT_HEADER_IMAGE_SIZE['course']
        context['object'] = context['content'] = course
        pois = list(course.all_pois.filter(published=True))
        if settings.TREK_EXPORT_POI_LIST_LIMIT > 0:
            pois = pois[:settings.TREK_EXPORT_POI_LIST_LIMIT]
        letters = alphabet_enumeration(len(pois))
        for i, poi in enumerate(pois):
            poi.letter = letters[i]
        context['pois'] = pois
        return context


class CourseDocument(MapEntityDocument):
    queryset = Course.objects.all()


class CourseDocumentPublic(CourseDocumentPublicMixin, DocumentPublic):
    pass


class CourseDocumentBookletPublic(CourseDocumentPublicMixin, DocumentBookletPublic):
    pass


class CourseMarkupPublic(CourseDocumentPublicMixin, MarkupPublic):
    pass


class CourseFormatList(MapEntityFormat, CourseList):
    mandatory_columns = ['id']
    default_extra_columns = [
        'structure', 'name', 'parent_sites', 'description', 'advice', 'equipment', 'accessibility',
        'eid', 'height', 'ratings', 'ratings_description', 'points_reference', 'uuid',
    ]


class CourseViewSet(GeotrekMapentityViewSet):
    model = Course
    serializer_class = CourseSerializer
    filterset_class = CourseFilterSet

    def get_columns(self):
        return CourseList.mandatory_columns + settings.COLUMNS_LISTS.get('course_view',
                                                                         CourseList.default_extra_columns)

    def get_queryset(self):
        return self.model.objects.all().prefetch_related('parent_sites')


class CourseAPIViewSet(APIViewSet):
    model = Course
    serializer_class = CourseAPISerializer
    geojson_serializer_class = CourseAPIGeojsonSerializer

    def get_queryset(self):
        qs = Course.objects.filter(published=True)
        if 'source' in self.request.GET:
            qs = qs.filter(parent_sites__source__name__in=self.request.GET['source'].split(','))
        if 'portal' in self.request.GET:
            qs = qs.filter(Q(parent_sites__portal__name=self.request.GET['portal']) | Q(parent_sites__portal=None))
        return qs.annotate(api_geom=Transform("geom", settings.API_SRID))
