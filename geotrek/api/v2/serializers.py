import json

from django.conf import settings
from django.contrib.gis.db.models.functions import Transform
from django.contrib.gis.geos import MultiLineString, Point
from django.db.models import F
from django.urls import reverse
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from drf_dynamic_fields import DynamicFieldsMixin
from easy_thumbnails.alias import aliases
from easy_thumbnails.exceptions import InvalidImageFormatError
from easy_thumbnails.files import get_thumbnailer
from PIL.Image import DecompressionBombError
from rest_framework import serializers
from rest_framework.relations import HyperlinkedIdentityField
from rest_framework_gis import serializers as geo_serializers

from geotrek.api.v2.functions import Length3D
from geotrek.common.functions import Length
from geotrek.api.v2.mixins import PDFSerializerMixin
from geotrek.api.v2.utils import build_url, get_translation_or_dict
from geotrek.authent import models as authent_models
from geotrek.common import models as common_models
from geotrek.core.models import simplify_coords

if 'geotrek.core' in settings.INSTALLED_APPS:
    from geotrek.core import models as core_models
if 'geotrek.feedback' in settings.INSTALLED_APPS:
    from geotrek.feedback import models as feedback_models
if 'geotrek.tourism' in settings.INSTALLED_APPS:
    from geotrek.tourism import models as tourism_models
if 'geotrek.trekking' in settings.INSTALLED_APPS:
    from geotrek.trekking import models as trekking_models
if 'geotrek.sensitivity' in settings.INSTALLED_APPS:
    from geotrek.sensitivity import models as sensitivity_models
if 'geotrek.zoning' in settings.INSTALLED_APPS:
    from geotrek.zoning import models as zoning_models
if 'geotrek.outdoor' in settings.INSTALLED_APPS:
    from geotrek.outdoor import models as outdoor_models
if 'geotrek.flatpages' in settings.INSTALLED_APPS:
    from geotrek.flatpages import models as flatpages_models
if 'geotrek.infrastructure' in settings.INSTALLED_APPS:
    from geotrek.infrastructure import models as infrastructure_models
if 'geotrek.signage' in settings.INSTALLED_APPS:
    from geotrek.signage import models as signage_models


class BaseGeoJSONSerializer(geo_serializers.GeoFeatureModelSerializer):
    """
    Mixin used to serialize geojson
    """

    def to_representation(self, instance):
        """Round bbox coordinates"""
        feature = super().to_representation(instance)
        feature['bbox'] = simplify_coords(feature['bbox'])
        return feature

    class Meta:
        geo_field = 'geometry'
        auto_bbox = True


def override_serializer(format_output, base_serializer_class):
    """
    Override Serializer switch output format and dimension data
    """
    if format_output == 'geojson':
        class GeneratedGeoSerializer(BaseGeoJSONSerializer,
                                     base_serializer_class):
            class Meta(BaseGeoJSONSerializer.Meta,
                       base_serializer_class.Meta):
                pass

        final_class = GeneratedGeoSerializer
    else:
        final_class = base_serializer_class

    return final_class


if 'geotrek.trekking' in settings.INSTALLED_APPS:
    class NetworkSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        label = serializers.SerializerMethodField()

        def get_label(self, obj):
            return get_translation_or_dict('network', self, obj)

        class Meta:
            model = trekking_models.TrekNetwork
            fields = ('id', 'label', 'pictogram')

    class PracticeSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        name = serializers.SerializerMethodField()

        def get_name(self, obj):
            return get_translation_or_dict('name', self, obj)

        class Meta:
            model = trekking_models.Practice
            fields = ('id', 'name', 'order', 'pictogram',)

    class TrekRatingScaleSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        name = serializers.SerializerMethodField()

        def get_name(self, obj):
            return get_translation_or_dict('name', self, obj)

        class Meta:
            model = trekking_models.RatingScale
            fields = ('id', 'name', 'practice')

    class TrekRatingSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        name = serializers.SerializerMethodField()
        description = serializers.SerializerMethodField()

        def get_name(self, obj):
            return get_translation_or_dict('name', self, obj)

        def get_description(self, obj):
            return get_translation_or_dict('description', self, obj)

        class Meta:
            model = trekking_models.Rating
            fields = ('id', 'name', 'description', 'scale', 'order', 'color')

    class TrekDifficultySerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        label = serializers.SerializerMethodField()

        def get_label(self, obj):
            return get_translation_or_dict('difficulty', self, obj)

        class Meta:
            model = trekking_models.DifficultyLevel
            fields = ('id', 'cirkwi_level', 'label', 'pictogram')

    class RouteSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        route = serializers.SerializerMethodField()

        def get_route(self, obj):
            return get_translation_or_dict('route', self, obj)

        class Meta:
            model = trekking_models.Route
            fields = ('id', 'pictogram', 'route')

    class WebLinkCategorySerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        label = serializers.SerializerMethodField()

        def get_label(self, obj):
            return get_translation_or_dict('label', self, obj)

        class Meta:
            model = trekking_models.WebLinkCategory
            fields = ('label', 'id', 'pictogram')

    class WebLinkSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        name = serializers.SerializerMethodField()
        category = WebLinkCategorySerializer()

        def get_name(self, obj):
            return get_translation_or_dict('name', self, obj)

        class Meta:
            model = trekking_models.WebLink
            fields = ('name', 'url', 'category')

    class ServiceTypeSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        name = serializers.SerializerMethodField()

        def get_name(self, obj):
            return get_translation_or_dict('name', self, obj)

        class Meta:
            model = trekking_models.ServiceType
            fields = ('id', 'name', 'practices', 'pictogram')

    class ServiceSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        geometry = geo_serializers.GeometryField(read_only=True, source="geom3d_transformed", precision=7)
        structure = serializers.CharField(source='structure.name')

        class Meta:
            model = trekking_models.Service
            fields = ('id', 'eid', 'geometry', 'structure', 'type', 'uuid')


class ReservationSystemSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = common_models.ReservationSystem
        fields = ('id', 'name')


class StructureSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = authent_models.Structure
        fields = (
            'id', 'name'
        )


class TargetPortalSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    facebook_image_url = serializers.SerializerMethodField()

    def get_title(self, obj):
        return get_translation_or_dict('title', self, obj)

    def get_description(self, obj):
        return get_translation_or_dict('description', self, obj)

    def get_facebook_image_url(self, obj):
        return build_url(self, obj.facebook_image_url) if obj.facebook_image_url else ""

    class Meta:
        model = common_models.TargetPortal
        fields = (
            'id', 'description', 'facebook_id',
            'facebook_image_height', 'facebook_image_url',
            'facebook_image_width', 'name', 'title', 'website'
        )


class OrganismSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    name = serializers.CharField(source='organism')

    class Meta:
        model = common_models.Organism
        fields = (
            'id', 'name'
        )


class RecordSourceSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = common_models.RecordSource
        fields = ('id', 'name', 'pictogram', 'website')


class AttachmentsSerializerMixin(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()
    license = serializers.SlugRelatedField(
        read_only=True,
        slug_field='label'
    )

    def get_attachment_file(self, obj):
        return obj.attachment_file

    def get_thumbnail(self, obj):
        thumbnailer = get_thumbnailer(self.get_attachment_file(obj))
        try:
            thumbnail = thumbnailer.get_thumbnail(aliases.get('apiv2'))
        except (IOError, InvalidImageFormatError, DecompressionBombError):
            return ""
        thumbnail.author = obj.author
        thumbnail.legend = obj.legend
        return build_url(self, thumbnail.url)

    def get_url(self, obj):
        if obj.attachment_file:
            return build_url(self, obj.attachment_file.url)
        if obj.attachment_video:
            return obj.attachment_video
        if obj.attachment_link:
            return obj.attachment_link
        return ""

    class Meta:
        model = common_models.Attachment
        fields = (
            'author', 'license', 'thumbnail', 'legend', 'title', 'url', 'uuid'
        )


class AttachmentSerializer(DynamicFieldsMixin, AttachmentsSerializerMixin):
    type = serializers.SerializerMethodField()
    backend = serializers.SerializerMethodField()

    def get_type(self, obj):
        if obj.is_image or obj.attachment_link:
            return "image"
        if obj.attachment_video != '':
            return "video"
        return "file"

    def get_backend(self, obj):
        if obj.attachment_video != '':
            return type(obj).__name__.replace('Backend', '')
        return ""

    class Meta:
        model = common_models.Attachment
        fields = (
            'backend', 'type'
        ) + AttachmentsSerializerMixin.Meta.fields


class AttachmentAccessibilitySerializer(DynamicFieldsMixin, AttachmentsSerializerMixin):
    def get_attachment_file(self, obj):
        return obj.attachment_accessibility_file

    def get_url(self, obj):
        return build_url(self, obj.attachment_accessibility_file.url)

    class Meta:
        model = common_models.AccessibilityAttachment
        fields = (
            'info_accessibility',
        ) + AttachmentsSerializerMixin.Meta.fields


class LabelSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    advice = serializers.SerializerMethodField()

    def get_name(self, obj):
        return get_translation_or_dict('name', self, obj)

    def get_advice(self, obj):
        return get_translation_or_dict('advice', self, obj)

    class Meta:
        model = common_models.Label
        fields = ('id', 'advice', 'filter', 'name', 'pictogram')


if 'geotrek.tourism' in settings.INSTALLED_APPS:
    class LabelAccessibilitySerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        label = serializers.SerializerMethodField()

        def get_label(self, obj):
            return get_translation_or_dict('label', self, obj)

        class Meta:
            model = tourism_models.LabelAccessibility
            fields = ('id', 'label', 'pictogram')

    class TouristicContentCategorySerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        types = serializers.SerializerMethodField()
        label = serializers.SerializerMethodField()

        class Meta:
            model = tourism_models.TouristicContentCategory
            fields = ('id', 'label', 'order', 'pictogram', 'types')

        def get_types(self, obj):
            request = self.context['request']
            portals = request.GET.get('portals')
            if portals:
                portals = portals.split(',')
            language = request.GET.get('language')
            return [{
                'id': obj.id * 100 + i,
                'label': get_translation_or_dict('type{}_label'.format(i), self, obj),
                'values': [{
                    'id': t.id,
                    'label': get_translation_or_dict('label', self, t),
                    'pictogram': t.pictogram.url if t.pictogram else None,
                } for t in obj.types.has_content_published_not_deleted_in_list(i, obj.pk, portals, language)]
            } for i in (1, 2)]

        def get_label(self, obj):
            return get_translation_or_dict('label', self, obj)

    class TouristicEventTypeSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        type = serializers.SerializerMethodField()

        def get_type(self, obj):
            return get_translation_or_dict('type', self, obj)

        class Meta:
            model = tourism_models.TouristicEventType
            fields = ('id', 'pictogram', 'type')

    class TouristicModelSerializer(PDFSerializerMixin, DynamicFieldsMixin, serializers.ModelSerializer):
        geometry = geo_serializers.GeometryField(read_only=True, source="geom_transformed", precision=7)
        accessibility = serializers.SerializerMethodField()
        create_datetime = serializers.DateTimeField(source='date_insert')
        update_datetime = serializers.DateTimeField(source='date_update')
        external_id = serializers.CharField(source='eid')
        cities = serializers.SerializerMethodField()
        name = serializers.SerializerMethodField()
        description = serializers.SerializerMethodField()
        description_teaser = serializers.SerializerMethodField()
        practical_info = serializers.SerializerMethodField()
        pdf = serializers.SerializerMethodField('get_pdf_url')

        def get_accessibility(self, obj):
            return get_translation_or_dict('accessibility', self, obj)

        def get_practical_info(self, obj):
            return get_translation_or_dict('practical_info', self, obj)

        def get_cities(self, obj):
            return [city.code for city in obj.published_cities]

        def get_name(self, obj):
            return get_translation_or_dict('name', self, obj)

        def get_description(self, obj):
            return get_translation_or_dict('description', self, obj)

        def get_description_teaser(self, obj):
            return get_translation_or_dict('description_teaser', self, obj)

    class TouristicContentSerializer(TouristicModelSerializer):
        attachments = AttachmentSerializer(many=True, source='sorted_attachments')
        departure_city = serializers.SerializerMethodField()
        types = serializers.SerializerMethodField()
        url = HyperlinkedIdentityField(view_name='apiv2:touristiccontent-detail')

        class Meta:
            model = tourism_models.TouristicContent
            fields = (
                'id', 'accessibility', 'attachments', 'approved', 'category', 'description',
                'description_teaser', 'departure_city', 'geometry', 'label_accessibility',
                'practical_info', 'url', 'cities', 'create_datetime',
                'external_id', 'name', 'pdf', 'portal', 'published',
                'source', 'structure', 'themes',
                'update_datetime', 'types', 'contact', 'email',
                'website', 'reservation_system', 'reservation_id', 'uuid'
            )

        def get_types(self, obj):
            return {
                obj.category.id * 100 + i: [
                    t.id for t in getattr(obj, 'type{}'.format(i)).all()
                ] for i in (1, 2)
            }

        def get_departure_city(self, obj):
            city = zoning_models.City.objects.all().filter(geom__contains=obj.geom).first()
            return city.code if city else None

    class TouristicEventSerializer(TouristicModelSerializer):
        attachments = AttachmentSerializer(many=True, source='sorted_attachments')
        url = HyperlinkedIdentityField(view_name='apiv2:touristicevent-detail')
        begin_date = serializers.DateField()
        end_date = serializers.DateField()
        type = serializers.SerializerMethodField()

        def get_type(self, obj):
            obj_type = obj.type
            if obj_type:
                return obj_type.pk
            return None

        class Meta:
            model = tourism_models.TouristicEvent
            fields = (
                'id', 'accessibility', 'approved', 'attachments', 'begin_date', 'booking',
                'cities', 'contact', 'create_datetime', 'description', 'description_teaser',
                'duration', 'email', 'end_date', 'external_id', 'geometry', 'meeting_point',
                'meeting_time', 'name', 'organizer', 'participant_number', 'pdf', 'portal',
                'practical_info', 'published', 'source', 'speaker', 'structure',
                'target_audience', 'themes', 'type', 'update_datetime', 'url', 'uuid', 'website'
            )

    class InformationDeskTypeSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        label = serializers.SerializerMethodField()

        def get_label(self, obj):
            return get_translation_or_dict('label', self, obj)

        class Meta:
            model = tourism_models.InformationDeskType
            fields = ('id', 'label', 'pictogram')

    class InformationDeskSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        accessibility = serializers.SerializerMethodField()
        description = serializers.SerializerMethodField()
        name = serializers.SerializerMethodField()
        photo_url = serializers.SerializerMethodField()
        type = InformationDeskTypeSerializer()

        def get_accessibility(self, obj):
            return get_translation_or_dict('accessibility', self, obj)

        def get_description(self, obj):
            return get_translation_or_dict('description', self, obj)

        def get_name(self, obj):
            return get_translation_or_dict('name', self, obj)

        def get_photo_url(self, obj):
            return build_url(self, obj.photo_url) if obj.photo_url else ""

        class Meta:
            model = tourism_models.InformationDesk
            geo_field = 'geom'
            fields = (
                'id', 'accessibility', 'description', 'email', 'label_accessibility', 'latitude', 'longitude',
                'municipality', 'name', 'phone', 'photo_url',
                'postal_code', 'street', 'type', 'website'
            )


if 'geotrek.core' in settings.INSTALLED_APPS:
    class PathSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        url = HyperlinkedIdentityField(view_name='apiv2:trek-detail')
        geometry = geo_serializers.GeometryField(read_only=True, source="geom3d_transformed", precision=7)
        length_2d = serializers.SerializerMethodField()
        length_3d = serializers.SerializerMethodField()

        def get_length_2d(self, obj):
            return round(obj.length_2d_m, 1)

        def get_length_3d(self, obj):
            return round(obj.length_3d_m, 1)

        class Meta:
            model = core_models.Path
            fields = (
                'id', 'comments', 'geometry', 'length_2d', 'length_3d',
                'name', 'url', 'uuid'
            )


if 'geotrek.trekking' in settings.INSTALLED_APPS:
    class TrekSerializer(PDFSerializerMixin, DynamicFieldsMixin, serializers.ModelSerializer):
        url = HyperlinkedIdentityField(view_name='apiv2:trek-detail')
        published = serializers.SerializerMethodField()
        geometry = geo_serializers.GeometryField(read_only=True, source="geom3d_transformed", precision=7)
        length_2d = serializers.SerializerMethodField()
        length_3d = serializers.SerializerMethodField()
        name = serializers.SerializerMethodField()
        access = serializers.SerializerMethodField()
        accessibility_advice = serializers.SerializerMethodField()
        accessibility_covering = serializers.SerializerMethodField()
        accessibility_exposure = serializers.SerializerMethodField()
        accessibility_signage = serializers.SerializerMethodField()
        accessibility_slope = serializers.SerializerMethodField()
        accessibility_width = serializers.SerializerMethodField()
        ambiance = serializers.SerializerMethodField()
        description = serializers.SerializerMethodField()
        description_teaser = serializers.SerializerMethodField()
        departure = serializers.SerializerMethodField()
        disabled_infrastructure = serializers.SerializerMethodField()
        departure_geom = serializers.SerializerMethodField()
        arrival = serializers.SerializerMethodField()
        external_id = serializers.CharField(source='eid')
        second_external_id = serializers.CharField(source='eid2')
        create_datetime = serializers.SerializerMethodField()
        update_datetime = serializers.SerializerMethodField()
        attachments = AttachmentSerializer(many=True, source='sorted_attachments')
        attachments_accessibility = AttachmentAccessibilitySerializer(many=True)
        gear = serializers.SerializerMethodField()
        gpx = serializers.SerializerMethodField('get_gpx_url')
        kml = serializers.SerializerMethodField('get_kml_url')
        pdf = serializers.SerializerMethodField('get_pdf_url')
        advice = serializers.SerializerMethodField()
        advised_parking = serializers.SerializerMethodField()
        parking_location = serializers.SerializerMethodField()
        ratings_description = serializers.SerializerMethodField()
        children = serializers.ReadOnlyField(source='children_id')
        parents = serializers.ReadOnlyField(source='parents_id')
        public_transport = serializers.SerializerMethodField()
        elevation_area_url = serializers.SerializerMethodField()
        elevation_svg_url = serializers.SerializerMethodField()
        altimetric_profile = serializers.SerializerMethodField('get_altimetric_profile_url')
        points_reference = serializers.SerializerMethodField()
        previous = serializers.ReadOnlyField(source='previous_id')
        next = serializers.ReadOnlyField(source='next_id')
        cities = serializers.SerializerMethodField()
        departure_city = serializers.SerializerMethodField()
        web_links = WebLinkSerializer(many=True)

        def get_gear(self, obj):
            return get_translation_or_dict('gear', self, obj)

        def get_update_datetime(self, obj):
            return obj.topo_object.date_update

        def get_create_datetime(self, obj):
            return obj.topo_object.date_insert

        def get_published(self, obj):
            return get_translation_or_dict('published', self, obj)

        def get_name(self, obj):
            return get_translation_or_dict('name', self, obj)

        def get_description(self, obj):
            return get_translation_or_dict('description', self, obj)

        def get_access(self, obj):
            return get_translation_or_dict('access', self, obj)

        def get_accessibility_advice(self, obj):
            return get_translation_or_dict('accessibility_advice', self, obj)

        def get_accessibility_covering(self, obj):
            return get_translation_or_dict('accessibility_covering', self, obj)

        def get_accessibility_exposure(self, obj):
            return get_translation_or_dict('accessibility_exposure', self, obj)

        def get_accessibility_signage(self, obj):
            return get_translation_or_dict('accessibility_signage', self, obj)

        def get_accessibility_slope(self, obj):
            return get_translation_or_dict('accessibility_slope', self, obj)

        def get_accessibility_width(self, obj):
            return get_translation_or_dict('accessibility_width', self, obj)

        def get_ambiance(self, obj):
            return get_translation_or_dict('ambiance', self, obj)

        def get_disabled_infrastructure(self, obj):
            return get_translation_or_dict('accessibility_infrastructure', self, obj)

        def get_departure(self, obj):
            return get_translation_or_dict('departure', self, obj)

        def get_first_point(self, geom):
            if isinstance(geom, Point):
                return geom
            if isinstance(geom, MultiLineString):
                return Point(geom[0][0])
            return Point(geom[0])

        def get_departure_geom(self, obj):
            return self.get_first_point(obj.geom3d_transformed)[:2]

        def get_arrival(self, obj):
            return get_translation_or_dict('arrival', self, obj)

        def get_description_teaser(self, obj):
            return get_translation_or_dict('description_teaser', self, obj)

        def get_length_2d(self, obj):
            return round(obj.length_2d_m, 1)

        def get_length_3d(self, obj):
            return round(obj.length_3d_m, 1)

        def get_gpx_url(self, obj):
            return build_url(self, reverse('trekking:trek_gpx_detail', kwargs={'lang': get_language(), 'pk': obj.pk, 'slug': obj.slug}))

        def get_kml_url(self, obj):
            return build_url(self, reverse('trekking:trek_kml_detail', kwargs={'lang': get_language(), 'pk': obj.pk, 'slug': obj.slug}))

        def get_advice(self, obj):
            return get_translation_or_dict('advice', self, obj)

        def get_advised_parking(self, obj):
            return get_translation_or_dict('advised_parking', self, obj)

        def get_parking_location(self, obj):
            if not obj.parking_location:
                return None
            point = obj.parking_location.transform(settings.API_SRID, clone=True)
            return [round(point.x, 7), round(point.y, 7)]

        def get_ratings_description(self, obj):
            return get_translation_or_dict('ratings_description', self, obj)

        def get_public_transport(self, obj):
            return get_translation_or_dict('public_transport', self, obj)

        def get_elevation_area_url(self, obj):
            return build_url(self, reverse('apiv2:trek-dem', args=(obj.pk,)))

        def get_elevation_svg_url(self, obj):
            return build_url(self, reverse('apiv2:trek-profile', args=(obj.pk,)) + f"?language={get_language()}&format=svg")

        def get_altimetric_profile_url(self, obj):
            return build_url(self, reverse('apiv2:trek-profile', args=(obj.pk,)))

        def get_points_reference(self, obj):
            if not obj.points_reference:
                return None
            geojson = obj.points_reference.transform(settings.API_SRID, clone=True).geojson
            return json.loads(geojson)

        def get_cities(self, obj):
            return [city.code for city in obj.published_cities]

        def get_departure_city(self, obj):
            geom = self.get_first_point(obj.geom)
            city = zoning_models.City.objects.all().filter(geom__contains=geom).first()
            return city.code if city else None

        class Meta:
            model = trekking_models.Trek
            fields = (
                'id', 'access', 'accessibilities', 'accessibility_advice', 'accessibility_covering',
                'accessibility_exposure', 'accessibility_level', 'accessibility_signage', 'accessibility_slope',
                'accessibility_width', 'advice', 'advised_parking', 'altimetric_profile', 'ambiance', 'arrival',
                'ascent', 'attachments', 'attachments_accessibility', 'children', 'cities', 'create_datetime',
                'departure', 'departure_city', 'departure_geom', 'descent',
                'description', 'description_teaser', 'difficulty',
                'disabled_infrastructure', 'duration', 'elevation_area_url',
                'elevation_svg_url', 'external_id', 'gear', 'geometry', 'gpx',
                'information_desks', 'kml', 'labels', 'length_2d', 'length_3d',
                'max_elevation', 'min_elevation', 'name', 'networks', 'next',
                'parents', 'parking_location', 'pdf', 'points_reference',
                'portal', 'practice', 'ratings', 'ratings_description', 'previous', 'public_transport',
                'published', 'reservation_system', 'reservation_id', 'route', 'second_external_id',
                'source', 'structure', 'themes', 'update_datetime', 'url', 'uuid', 'web_links'
            )

    class TourSerializer(TrekSerializer):
        url = HyperlinkedIdentityField(view_name='apiv2:tour-detail')
        count_children = serializers.SerializerMethodField()
        steps = serializers.SerializerMethodField()

        def get_count_children(self, obj):
            return obj.count_children

        def get_steps(self, obj):
            qs = obj.children \
                .select_related('topo_object', 'difficulty') \
                .prefetch_related('topo_object__aggregations', 'themes', 'networks', 'attachments') \
                .annotate(geom3d_transformed=Transform(F('geom_3d'), settings.API_SRID),
                          length_2d_m=Length('geom'),
                          length_3d_m=Length3D('geom_3d'))
            FinalClass = override_serializer(self.context.get('request').GET.get('format'),
                                             TrekSerializer)
            return FinalClass(qs, many=True, context=self.context).data

        class Meta(TrekSerializer.Meta):
            fields = TrekSerializer.Meta.fields + ('count_children', 'steps')

    class POITypeSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        label = serializers.SerializerMethodField()

        def get_label(self, obj):
            return get_translation_or_dict('label', self, obj)

        class Meta:
            model = trekking_models.POIType
            fields = ('id', 'label', 'pictogram')

    class POISerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        url = HyperlinkedIdentityField(view_name='apiv2:poi-detail')
        type_label = serializers.SerializerMethodField()
        type_pictogram = serializers.FileField(source='type.pictogram')
        name = serializers.SerializerMethodField()
        description = serializers.SerializerMethodField()
        external_id = serializers.CharField(source='eid')
        published = serializers.SerializerMethodField()
        create_datetime = serializers.DateTimeField(source='topo_object.date_insert')
        update_datetime = serializers.DateTimeField(source='topo_object.date_update')
        geometry = geo_serializers.GeometryField(read_only=True, source="geom3d_transformed", precision=7)
        attachments = AttachmentSerializer(many=True, source='sorted_attachments')

        def get_type_label(self, obj):
            return get_translation_or_dict('label', self, obj.type)

        def get_published(self, obj):
            return get_translation_or_dict('published', self, obj)

        def get_name(self, obj):
            return get_translation_or_dict('name', self, obj)

        def get_description(self, obj):
            return get_translation_or_dict('description', self, obj)

        class Meta:
            model = trekking_models.POI
            fields = (
                'id', 'description', 'external_id',
                'geometry', 'name', 'attachments', 'published', 'type',
                'type_label', 'type_pictogram', 'url', 'uuid',
                'create_datetime', 'update_datetime',
            )

    class ThemeSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        label = serializers.SerializerMethodField()

        def get_label(self, obj):
            return get_translation_or_dict('label', self, obj)

        class Meta:
            model = trekking_models.Theme
            fields = ('id', 'label', 'pictogram')

    class AccessibilitySerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        name = serializers.SerializerMethodField()

        def get_name(self, obj):
            return get_translation_or_dict('name', self, obj)

        class Meta:
            model = trekking_models.Accessibility
            fields = ('id', 'name', 'pictogram')

    class AccessibilityLevelSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        name = serializers.SerializerMethodField()

        def get_name(self, obj):
            return get_translation_or_dict('name', self, obj)

        class Meta:
            model = trekking_models.AccessibilityLevel
            fields = ('id', 'name')

if 'geotrek.sensitivity' in settings.INSTALLED_APPS:
    class SensitiveAreaSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        url = HyperlinkedIdentityField(view_name='apiv2:sensitivearea-detail')
        name = serializers.SerializerMethodField()
        elevation = serializers.SerializerMethodField()
        description = serializers.SerializerMethodField()
        period = serializers.SerializerMethodField()
        practices = serializers.SerializerMethodField()
        info_url = serializers.URLField(source='species.url')
        structure = serializers.CharField(source='structure.name')
        create_datetime = serializers.DateTimeField(source='date_insert')
        update_datetime = serializers.DateTimeField(source='date_update')
        published = serializers.BooleanField()
        geometry = geo_serializers.GeometryField(read_only=True, source="geom_transformed", precision=7)
        species_id = serializers.SerializerMethodField()
        kml_url = serializers.SerializerMethodField()

        def get_name(self, obj):
            return get_translation_or_dict('name', self, obj.species)

        def get_description(self, obj):
            return get_translation_or_dict('description', self, obj)

        def get_period(self, obj):
            return [getattr(obj.species, 'period{:02}'.format(p)) for p in range(1, 13)]

        def get_practices(self, obj):
            return obj.species.practices.values_list('id', flat=True)

        def get_elevation(self, obj):
            return obj.species.radius

        def get_species_id(self, obj):
            if obj.species.category == sensitivity_models.Species.SPECIES:
                return obj.species.id
            return None

        def get_kml_url(self, obj):
            url = reverse('sensitivity:sensitivearea_kml_detail', kwargs={'lang': get_language(), 'pk': obj.pk})
            return build_url(self, url)

        class Meta:
            model = sensitivity_models.SensitiveArea
            fields = (
                'id', 'contact', 'create_datetime', 'description', 'elevation',
                'geometry', 'info_url', 'kml_url', 'name', 'period',
                'practices', 'published', 'species_id', 'structure',
                'update_datetime', 'url'
            )

    class BubbleSensitiveAreaSerializer(SensitiveAreaSerializer):
        radius = serializers.SerializerMethodField()

        def get_radius(self, obj):
            if obj.species.category == sensitivity_models.Species.SPECIES and obj.geom.geom_typeid == 0:
                return obj.species.radius
            else:
                return None

        class Meta:
            model = SensitiveAreaSerializer.Meta.model
            fields = SensitiveAreaSerializer.Meta.fields + ('radius', )

    class SportPracticeSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        name = serializers.SerializerMethodField()

        def get_name(self, obj):
            return get_translation_or_dict('name', self, obj)

        class Meta:
            model = sensitivity_models.SportPractice
            fields = (
                'id', 'name'
            )

    class SpeciesSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        name = serializers.SerializerMethodField()
        period01 = serializers.BooleanField(read_only=True)
        period02 = serializers.BooleanField(read_only=True)
        period03 = serializers.BooleanField(read_only=True)
        period04 = serializers.BooleanField(read_only=True)
        period05 = serializers.BooleanField(read_only=True)
        period06 = serializers.BooleanField(read_only=True)
        period07 = serializers.BooleanField(read_only=True)
        period08 = serializers.BooleanField(read_only=True)
        period09 = serializers.BooleanField(read_only=True)
        period10 = serializers.BooleanField(read_only=True)
        period11 = serializers.BooleanField(read_only=True)
        period12 = serializers.BooleanField(read_only=True)
        url = serializers.URLField(read_only=True)
        radius = serializers.IntegerField(read_only=True)
        practices = serializers.SerializerMethodField()

        def get_name(self, obj):
            return get_translation_or_dict('name', self, obj)

        def get_practices(self, obj):
            return obj.practices.values_list('id', flat=True)

        class Meta:
            model = sensitivity_models.Species
            fields = (
                'id', 'name', 'period01', 'period02', 'period03',
                'period04', 'period05', 'period06', 'period07',
                'period08', 'period09', 'period10', 'period11',
                'period12', 'practices', 'radius', 'url'
            )


if 'geotrek.zoning' in settings.INSTALLED_APPS:
    class CitySerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        geometry = geo_serializers.GeometryField(read_only=True, source="geom", precision=7)
        id = serializers.ReadOnlyField(source='code')

        class Meta:
            model = zoning_models.City
            fields = ('id', 'geometry', 'name', 'published')

    class DistrictsSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        geometry = geo_serializers.GeometryField(read_only=True, source="geom", precision=7)

        class Meta:
            model = zoning_models.District
            fields = ('id', 'geometry', 'name', 'published')


if 'geotrek.outdoor' in settings.INSTALLED_APPS:
    class OutdoorRatingScaleSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        name = serializers.SerializerMethodField()

        def get_name(self, obj):
            return get_translation_or_dict('name', self, obj)

        class Meta:
            model = outdoor_models.RatingScale
            fields = ('id', 'name', 'practice')

    class OutdoorRatingSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        name = serializers.SerializerMethodField()
        description = serializers.SerializerMethodField()

        def get_name(self, obj):
            return get_translation_or_dict('name', self, obj)

        def get_description(self, obj):
            return get_translation_or_dict('description', self, obj)

        class Meta:
            model = outdoor_models.Rating
            fields = ('id', 'name', 'description', 'scale', 'order', 'color')

    class OutdoorPracticeSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        name = serializers.SerializerMethodField()

        def get_name(self, obj):
            return get_translation_or_dict('name', self, obj)

        class Meta:
            model = outdoor_models.Practice
            fields = ('id', 'name', 'sector', 'pictogram')

    class SiteTypeSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        name = serializers.SerializerMethodField()

        def get_name(self, obj):
            return get_translation_or_dict('name', self, obj)

        class Meta:
            model = outdoor_models.SiteType
            fields = ('id', 'name', 'practice')

    class CourseTypeSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        name = serializers.SerializerMethodField()

        def get_name(self, obj):
            return get_translation_or_dict('name', self, obj)

        class Meta:
            model = outdoor_models.CourseType
            fields = ('id', 'name', 'practice')

    class SectorSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        name = serializers.SerializerMethodField()

        def get_name(self, obj):
            return get_translation_or_dict('name', self, obj)

        class Meta:
            model = outdoor_models.Practice
            fields = ('id', 'name')

    class SiteSerializer(PDFSerializerMixin, DynamicFieldsMixin, serializers.ModelSerializer):
        url = HyperlinkedIdentityField(view_name='apiv2:site-detail')
        geometry = geo_serializers.GeometryField(read_only=True, source="geom_transformed", precision=7)
        attachments = AttachmentSerializer(many=True)
        sector = serializers.SerializerMethodField()
        courses = serializers.SerializerMethodField()
        children = serializers.SerializerMethodField()
        parent = serializers.SerializerMethodField()
        pdf = serializers.SerializerMethodField('get_pdf_url')
        cities = serializers.SerializerMethodField()
        web_links = WebLinkSerializer(many=True)

        def get_cities(self, obj):
            return [city.code for city in obj.published_cities]

        def get_courses(self, obj):
            courses = []
            request = self.context['request']
            language = request.GET.get('language')
            for course in obj.children_courses.all():
                if language:
                    if getattr(course, f"published_{language}"):
                        courses.append(course.pk)
                else:
                    if course.published:
                        courses.append(course.pk)
            return courses

        def get_parent(self, obj):
            parent = None
            request = self.context['request']
            language = request.GET.get('language')
            if obj.parent:
                if language:
                    if getattr(obj.parent, f"published_{language}"):
                        parent = obj.parent.pk
                else:
                    if obj.parent.published:
                        parent = obj.parent.pk
            return parent

        def get_children(self, obj):
            children = []
            request = self.context['request']
            language = request.GET.get('language')
            if language:
                for site in obj.get_children():
                    if getattr(site, f"published_{language}"):
                        children.append(site.pk)
            else:
                for site in obj.get_children():
                    if site.published:
                        children.append(site.pk)
            return children

        def get_sector(self, obj):
            if obj.practice and obj.practice.sector:
                return obj.practice.sector_id
            return None

        class Meta:
            model = outdoor_models.Site
            fields = (
                'id', 'accessibility', 'advice', 'ambiance', 'attachments', 'cities', 'children', 'description',
                'description_teaser', 'eid', 'geometry', 'information_desks', 'labels', 'managers',
                'name', 'orientation', 'pdf', 'period', 'parent', 'portal', 'practice',
                'ratings', 'sector', 'source', 'structure', 'themes',
                'type', 'url', 'uuid', 'courses', 'web_links', 'wind',
            )

    class CourseSerializer(PDFSerializerMixin, DynamicFieldsMixin, serializers.ModelSerializer):
        url = HyperlinkedIdentityField(view_name='apiv2:course-detail')
        geometry = geo_serializers.GeometryField(read_only=True, source="geom_transformed", precision=7)
        children = serializers.ReadOnlyField(source='children_id')
        parents = serializers.ReadOnlyField(source='parents_id')
        accessibility = serializers.SerializerMethodField()
        attachments = AttachmentSerializer(many=True, source='sorted_attachments')
        equipment = serializers.SerializerMethodField()
        gear = serializers.SerializerMethodField()
        ratings_description = serializers.SerializerMethodField()
        sites = serializers.SerializerMethodField()
        points_reference = serializers.SerializerMethodField()
        pdf = serializers.SerializerMethodField('get_pdf_url')
        cities = serializers.SerializerMethodField()

        def get_accessibility(self, obj):
            return get_translation_or_dict('accessibility', self, obj)

        def get_cities(self, obj):
            return [city.code for city in obj.published_cities]

        def get_equipment(self, obj):
            return get_translation_or_dict('equipment', self, obj)

        def get_gear(self, obj):
            return get_translation_or_dict('gear', self, obj)

        def get_ratings_description(self, obj):
            return get_translation_or_dict('ratings_description', self, obj)

        def get_sites(self, obj):
            sites = []
            request = self.context['request']
            language = request.GET.get('language')
            if language:
                for site in obj.parent_sites.all():
                    if getattr(site, f"published_{language}"):
                        sites.append(site.pk)
            else:
                for site in obj.parent_sites.all():
                    if getattr(site, "published"):
                        sites.append(site.pk)
            return sites

        def get_points_reference(self, obj):
            if not obj.points_reference:
                return None
            geojson = obj.points_reference.transform(settings.API_SRID, clone=True).geojson
            return json.loads(geojson)

        class Meta:
            model = outdoor_models.Course
            fields = (
                'id', 'accessibility', 'advice', 'attachments', 'children', 'cities', 'description', 'duration', 'eid',
                'equipment', 'gear', 'geometry', 'height', 'length', 'max_elevation',
                'min_elevation', 'name', 'parents', 'pdf', 'points_reference', 'ratings', 'ratings_description',
                'sites', 'structure', 'type', 'url', 'uuid'
            )

if 'geotrek.feedback' in settings.INSTALLED_APPS:
    class ReportStatusSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        label = serializers.SerializerMethodField()

        def get_label(self, obj):
            return get_translation_or_dict('label', self, obj)

        class Meta:
            model = feedback_models.ReportStatus
            fields = ('color', 'id', 'label', 'identifier')

    class ReportCategorySerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        label = serializers.SerializerMethodField()

        def get_label(self, obj):
            return get_translation_or_dict('label', self, obj)

        class Meta:
            model = feedback_models.ReportCategory
            fields = ('id', 'label')

    class ReportActivitySerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        label = serializers.SerializerMethodField()

        def get_label(self, obj):
            return get_translation_or_dict('label', self, obj)

        class Meta:
            model = feedback_models.ReportActivity
            fields = ('id', 'label')

    class ReportProblemMagnitudeSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        label = serializers.SerializerMethodField()

        def get_label(self, obj):
            return get_translation_or_dict('label', self, obj)

        class Meta:
            model = feedback_models.ReportProblemMagnitude
            fields = ('id', 'label')


if 'geotrek.flatpages' in settings.INSTALLED_APPS:
    class FlatPageSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        title = serializers.SerializerMethodField()
        content = serializers.SerializerMethodField()
        published = serializers.SerializerMethodField()
        attachments = AttachmentSerializer(many=True)

        class Meta:
            model = flatpages_models.FlatPage
            fields = (
                'id', 'title', 'external_url', 'content', 'target', 'source', 'portal', 'order',
                'published', 'attachments',
            )

        def get_title(self, obj):
            return get_translation_or_dict('title', self, obj)

        def get_content(self, obj):
            return get_translation_or_dict('content', self, obj)

        def get_published(self, obj):
            return get_translation_or_dict('published', self, obj)

if "geotrek.infrastructure" in settings.INSTALLED_APPS:

    class InfrastructureTypeSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        type = serializers.SerializerMethodField()

        def get_type(self, obj):
            type_label = infrastructure_models.INFRASTRUCTURE_TYPES.for_value(obj.type).display
            return _(type_label)

        class Meta:
            model = infrastructure_models.InfrastructureType
            fields = ('id', 'label', 'pictogram', 'structure', 'type')

    class InfrastructureSerializer(serializers.ModelSerializer):
        geometry = geo_serializers.GeometryField(read_only=True, source="geom3d_transformed", precision=7)
        structure = serializers.CharField(source='structure.name')
        attachments = AttachmentSerializer(many=True)

        class Meta:
            model = infrastructure_models.Infrastructure
            fields = ('id', 'attachments', 'condition', 'description', 'eid', 'geometry', 'name', 'implantation_year',
                      'maintenance_difficulty', 'structure', 'type', 'usage_difficulty', 'uuid')

    class InfrastructureConditionSerializer(DynamicFieldsMixin, serializers.ModelSerializer):

        class Meta:
            model = infrastructure_models.InfrastructureType
            fields = ('id', 'label', 'structure')

    class InfrastructureMaintenanceDifficultyLevelSerializer(DynamicFieldsMixin, serializers.ModelSerializer):

        class Meta:
            model = infrastructure_models.InfrastructureMaintenanceDifficultyLevel
            fields = ('id', 'label', 'structure')

    class InfrastructureUsageDifficultyLevelSerializer(DynamicFieldsMixin, serializers.ModelSerializer):

        class Meta:
            model = infrastructure_models.InfrastructureUsageDifficultyLevel
            fields = ('id', 'label', 'structure')

if 'geotrek.signage' in settings.INSTALLED_APPS:

    class LineSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        pictogram = serializers.CharField(source='pictogram_name')

        class Meta:
            model = signage_models.Line
            fields = ('id', 'text', 'pictogram', 'distance', 'time')

    class BladeSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        lines = LineSerializer(many=True)

        class Meta:
            model = signage_models.Blade
            fields = ('id', 'number', 'color', 'direction', 'lines')

    class SignageSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        geometry = geo_serializers.GeometryField(read_only=True, source="geom3d_transformed", precision=7)
        structure = serializers.CharField(source='structure.name')
        attachments = AttachmentSerializer(many=True)
        blades = BladeSerializer(source='blades_set', many=True)

        class Meta:
            model = signage_models.Signage
            fields = ('id', 'attachments', 'blades', 'code', 'condition', 'description', 'eid',
                      'geometry', 'implantation_year', 'name', 'printed_elevation', 'sealing',
                      'structure', 'type', 'uuid')

    class SignageTypeSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        class Meta:
            model = signage_models.SignageType
            fields = ('id', 'label', 'pictogram', 'structure')

    class DirectionSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        class Meta:
            model = signage_models.Direction
            fields = ('id', 'label')

    class SealingSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        class Meta:
            model = signage_models.Sealing
            fields = ('id', 'label', 'structure')

    class ColorSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        class Meta:
            model = signage_models.Color
            fields = ('id', 'label')

    class BladeTypeSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
        class Meta:
            model = signage_models.BladeType
            fields = ('id', 'label', 'structure')
