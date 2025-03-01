import errno
from io import StringIO

import json
from landez.sources import DownloadError
from unittest import mock
import os
from PIL import Image
import shutil
from unittest import skipIf
import zipfile

from django.conf import settings
from django.contrib.gis.geos import MultiLineString, LineString
from django.core import management
from django.core.management.base import CommandError
from django.db.models import Q
from django.http import HttpResponse, StreamingHttpResponse
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import translation

from geotrek.common.tests.factories import RecordSourceFactory, TargetPortalFactory, AttachmentFactory
from geotrek.common.tests import TranslationResetMixin
from geotrek.common.utils.testdata import get_dummy_uploaded_image_svg, get_dummy_uploaded_image, get_dummy_uploaded_file
from geotrek.core.tests.factories import PathFactory
from geotrek.flatpages.tests.factories import FlatPageFactory
from geotrek.flatpages.models import FlatPage
from geotrek.trekking.models import Trek, OrderedTrekChild
from geotrek.trekking.tests.factories import TrekFactory, TrekWithPublishedPOIsFactory, PracticeFactory
from geotrek.tourism.tests.factories import (InformationDeskFactory, InformationDeskTypeFactory,
                                             TouristicContentFactory, TouristicEventFactory)
from geotrek.tourism.models import TouristicEventType


class VarTmpTestCase(TestCase):
    def setUp(self):
        if os.path.exists(os.path.join('var', 'tmp_sync_mobile')):
            shutil.rmtree(os.path.join('var', 'tmp_sync_mobile'))
        if os.path.exists(os.path.join('var', 'tmp')):
            shutil.rmtree(os.path.join('var', 'tmp'))

    def tearDown(self):
        if os.path.exists(os.path.join('var', 'tmp_sync_mobile')):
            shutil.rmtree(os.path.join('var', 'tmp_sync_mobile'))
        if os.path.exists(os.path.join('var', 'tmp')):
            shutil.rmtree(os.path.join('var', 'tmp'))


@mock.patch('landez.TilesManager.tileslist', return_value=[(9, 258, 199)])
class SyncMobileTilesTest(VarTmpTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        translation.deactivate()

    @mock.patch('landez.TilesManager.tile', return_value=b'I am a png')
    def test_tiles(self, mock_tiles, mock_tileslist):
        output = StringIO()
        management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000', verbosity=2, stdout=output)
        zfile = zipfile.ZipFile('var/tmp/nolang/global.zip')
        for finfo in zfile.infolist():
            ifile = zfile.open(finfo)
            self.assertEqual(ifile.readline(), b'I am a png')
        self.assertIn("nolang/global.zip", output.getvalue())

    @mock.patch('landez.TilesManager.tile', return_value='Error')
    def test_tile_fail(self, mock_tiles, mock_tileslist):
        mock_tiles.side_effect = DownloadError
        output = StringIO()
        management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000', verbosity=2, stdout=output)
        zfile = zipfile.ZipFile('var/tmp/nolang/global.zip')
        for finfo in zfile.infolist():
            ifile = zfile.open(finfo)
            self.assertEqual(ifile.readline(), b'I am a png')
        self.assertIn("nolang/global.zip", output.getvalue())

    @override_settings(MOBILE_TILES_URL=['http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
                                         'http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'])
    @mock.patch('landez.TilesManager.tile', return_value='Error')
    def test_multiple_tiles(self, mock_tiles, mock_tileslist):
        mock_tiles.side_effect = DownloadError
        output = StringIO()
        management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000', verbosity=2, stdout=output)
        zfile = zipfile.ZipFile('var/tmp/nolang/global.zip')
        for finfo in zfile.infolist():
            ifile = zfile.open(finfo)
            self.assertEqual(ifile.readline(), b'I am a png')

    @override_settings(MOBILE_TILES_URL='http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png')
    @mock.patch('landez.TilesManager.tile', return_value='Error')
    def test_mobile_tiles_url_str(self, mock_tiles, mock_tileslist):
        mock_tiles.side_effect = DownloadError
        output = StringIO()
        management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000', verbosity=2, stdout=output)
        zfile = zipfile.ZipFile('var/tmp/nolang/global.zip')
        for finfo in zfile.infolist():
            ifile = zfile.open(finfo)
            self.assertEqual(ifile.readline(), b'I am a png')

    @mock.patch('geotrek.trekking.models.Trek.prepare_map_image')
    @mock.patch('landez.TilesManager.tile', return_value=b'I am a png')
    def test_tiles_with_treks(self, mock_tiles, mock_prepare, mock_tileslist):
        output = StringIO()
        portal_a = TargetPortalFactory()
        portal_b = TargetPortalFactory()
        trek = TrekWithPublishedPOIsFactory.create(published=True)
        trek_not_same_portal = TrekWithPublishedPOIsFactory.create(published=True, portals=(portal_a, ))
        p = PathFactory.create(geom=LineString((0, 0), (0, 10)))
        trek_multi = TrekFactory.create(published=True, paths=[(p, 0, 0.1), (p, 0.2, 0.3)])
        management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000', verbosity=2, stdout=output,
                                portal=portal_b.name)

        zfile_global = zipfile.ZipFile('var/tmp/nolang/global.zip')
        for finfo in zfile_global.infolist():
            ifile_global = zfile_global.open(finfo)
            if ifile_global.name.startswith('tiles/'):
                self.assertEqual(ifile_global.readline(), b'I am a png')
        zfile_trek = zipfile.ZipFile('var/tmp/nolang/{}.zip'.format(trek.pk))
        for finfo in zfile_trek.infolist():
            ifile_trek = zfile_trek.open(finfo)
            if ifile_trek.name.startswith('tiles/'):
                self.assertEqual(ifile_trek.readline(), b'I am a png')
        self.assertIn("nolang/global.zip", output.getvalue())
        self.assertIn("nolang/{pk}.zip".format(pk=trek.pk), output.getvalue())

        self.assertFalse(os.path.exists(os.path.join('var/tmp', 'nolang', '{}.zip'.format(trek_not_same_portal.pk))))
        self.assertTrue(os.path.exists(os.path.join('var/tmp', 'nolang', '{}.zip'.format(trek_multi.pk))))


class SyncMobileFailTest(VarTmpTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        translation.deactivate()

    def test_fail_directory_not_empty(self):
        os.makedirs('var/tmp/other')
        with self.assertRaisesRegex(CommandError, "Destination directory contains extra data"):
            management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000',
                                    skip_tiles=True, verbosity=2)

    def test_fail_sync_already_running(self):
        os.makedirs('var/tmp_sync_mobile')
        msg = "The var/tmp_sync_mobile/ directory already exists. " \
              "Please check no other sync_mobile command is already running. " \
              "If not, please delete this directory."
        with self.assertRaisesRegex(CommandError, msg):
            management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000',
                                    skip_tiles=True, verbosity=2)

    @mock.patch('os.mkdir')
    def test_fail_sync_tmp_sync_rando_permission_denied(self, mkdir):
        mkdir.side_effect = OSError(errno.EACCES, 'Permission Denied')
        with self.assertRaisesRegex(OSError, r"\[Errno 13\] Permission Denied"):
            management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000',
                                    skip_tiles=True, verbosity=2)

    def test_fail_url_ftp(self):
        with self.assertRaisesRegex(CommandError, "url parameter should start with http:// or https://"):
            management.call_command('sync_mobile', 'var/tmp', url='ftp://localhost:8000',
                                    skip_tiles=True, verbosity=2)

    def test_language_not_in_db(self):
        with self.assertRaisesRegex(CommandError,
                                    r"Language cat doesn't exist. Select in these one : \('en', 'es', 'fr', 'it'\)"):
            management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000',
                                    skip_tiles=True, languages='cat', verbosity=2)

    @mock.patch('geotrek.trekking.models.Trek.prepare_map_image')
    def test_attachments_missing_from_disk(self, mocke):
        mocke.side_effect = Exception()
        trek_1 = TrekWithPublishedPOIsFactory.create(published_fr=True)
        attachment = AttachmentFactory(content_object=trek_1, attachment_file=get_dummy_uploaded_image())
        os.remove(attachment.attachment_file.path)
        management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000',
                                skip_tiles=True, languages='fr', verbosity=2, stdout=StringIO())
        self.assertFalse(os.path.exists(os.path.join('var/tmp/nolang', 'media', 'trekking_trek')))

    @override_settings(MEDIA_URL=9)
    def test_bad_settings(self):
        output = StringIO()
        TrekWithPublishedPOIsFactory.create(published_fr=True)
        with self.assertRaisesRegex(AttributeError, "'int' object has no attribute 'strip'"):
            management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000',
                                    skip_tiles=True, languages='fr', verbosity=2, stdout=output, stderr=StringIO())
            self.assertIn("Exception raised in callable attribute", output.getvalue())

    @mock.patch('geotrek.api.mobile.views.common.SettingsView.get')
    def test_response_view_exception(self, mocke):
        output = StringIO()
        mocke.side_effect = Exception('This is a test')
        TrekWithPublishedPOIsFactory.create(published_fr=True)
        with self.assertRaisesRegex(CommandError, 'Some errors raised during synchronization.'):
            management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000', portal='portal',
                                    skip_tiles=True, languages='fr', verbosity=2, stdout=output)

        self.assertIn("failed (This is a test)", output.getvalue())

    @mock.patch('geotrek.api.mobile.views.common.SettingsView.get')
    def test_response_500(self, mocke):
        output = StringIO()
        mocke.return_value = HttpResponse(status=500)
        TrekWithPublishedPOIsFactory.create(published_fr=True)
        with self.assertRaisesRegex(CommandError, 'Some errors raised during synchronization.'):
            management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000', portal='portal',
                                    skip_tiles=True, languages='fr', verbosity=2, stdout=output)
        self.assertIn("failed (HTTP 500)", output.getvalue())


class SyncMobileSpecificOptionsTest(TranslationResetMixin, VarTmpTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        FlatPageFactory.create(published_fr=True)
        FlatPageFactory.create(published_en=True)

    def test_lang(self):
        management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000',
                                skip_tiles=True, verbosity=0, languages='fr')
        with open('var/tmp/fr/flatpages.json', 'r') as f:
            flatpages = json.load(f)
            self.assertEqual(len(flatpages), 1)
        with self.assertRaises(IOError):
            open('var/tmp/en/flatpages.json', 'r')

    def test_sync_https(self):
        management.call_command('sync_mobile', 'var/tmp', url='https://localhost:8000',
                                skip_tiles=True, verbosity=0)
        with open('var/tmp/fr/flatpages.json', 'r') as f:
            flatpages = json.load(f)
            self.assertEqual(len(flatpages), 1)


class SyncMobileFlatpageTest(TranslationResetMixin, VarTmpTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        translation.deactivate()

        cls.portals = []

        cls.portal_a = TargetPortalFactory()
        cls.portal_b = TargetPortalFactory()

        cls.source_a = RecordSourceFactory()
        cls.source_b = RecordSourceFactory()

        FlatPageFactory.create(published=True)
        FlatPageFactory.create(portals=(cls.portal_a, cls.portal_b),
                               published=True)
        FlatPageFactory.create(published=True)
        FlatPageFactory.create(portals=(cls.portal_a,),
                               published=True)

    def test_sync_flatpage(self):
        '''
        Test synced flatpages
        '''
        output = StringIO()
        management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000',
                                skip_tiles=True, verbosity=2, stdout=output)
        for lang in settings.MODELTRANSLATION_LANGUAGES:
            with open(os.path.join('var/tmp', lang, 'flatpages.json'), 'r') as f:
                flatpages = json.load(f)
                self.assertEqual(len(flatpages),
                                 FlatPage.objects.filter(**{'published_{}'.format(lang): True}).count())
        self.assertIn('en/flatpages.json', output.getvalue())

    def test_sync_filtering_portal(self):
        '''
        Test if synced flatpages are filtered by portal
        '''
        output = StringIO()
        management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000',
                                portal=self.portal_b.name, skip_tiles=True, verbosity=2, stdout=output)
        with open('var/tmp/fr/flatpages.json', 'r') as f_file:
            flatpages = json.load(f_file)
            self.assertEqual(len(flatpages), 0)
        with open('var/tmp/en/flatpages.json', 'r') as f_file:
            flatpages = json.load(f_file)
            self.assertEqual(len(flatpages), 3)
        self.assertIn('en/flatpages.json', output.getvalue())

    def test_sync_flatpage_lang(self):
        output = StringIO()
        FlatPageFactory.create(published_fr=True)
        FlatPageFactory.create(published_en=True)
        FlatPageFactory.create(published_es=True)
        management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000',
                                skip_tiles=True, verbosity=2, stdout=output)
        for lang in settings.MODELTRANSLATION_LANGUAGES:
            with open(os.path.join('var/tmp', lang, 'flatpages.json'), 'r') as f:
                flatpages = json.load(f)
                self.assertEqual(len(flatpages),
                                 FlatPage.objects.filter(**{'published_{}'.format(lang): True}).count())
        self.assertIn('en/flatpages.json', output.getvalue())

    def test_sync_flatpage_content(self):
        output = StringIO()
        management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000',
                                skip_tiles=True, verbosity=2, stdout=output)
        for lang in settings.MODELTRANSLATION_LANGUAGES:
            with open(os.path.join('var/tmp', lang, 'flatpages.json'), 'r') as f:
                flatpages = json.load(f)
                self.assertEqual(len(flatpages),
                                 FlatPage.objects.filter(**{'published_{}'.format(lang): True}).count())
        self.assertIn('en/flatpages.json', output.getvalue())


class SyncMobileSettingsTest(TranslationResetMixin, VarTmpTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        translation.deactivate()

    def test_sync_settings(self):
        output = StringIO()
        management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000',
                                skip_tiles=True, verbosity=2, stdout=output)
        for lang in settings.MODELTRANSLATION_LANGUAGES:
            with open(os.path.join('var/tmp', lang, 'settings.json'), 'r') as f:
                settings_json = json.load(f)
                self.assertEqual(len(settings_json), 2)
                self.assertEqual(len(settings_json['data']), 16)

        self.assertIn('en/settings.json', output.getvalue())

    def test_sync_settings_with_picto_svg(self):
        output = StringIO()
        practice = PracticeFactory.create(pictogram=get_dummy_uploaded_image_svg())
        self.trek = TrekFactory.create(practice=practice, published_fr=True, published_it=True, published_es=True, published_en=True)
        information_desk_type = InformationDeskTypeFactory.create(pictogram=get_dummy_uploaded_image())
        InformationDeskFactory.create(type=information_desk_type)
        pictogram_png = practice.pictogram.url.replace('.svg', '.png')
        pictogram_desk_png = information_desk_type.pictogram.url
        management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000',
                                skip_tiles=True, verbosity=2, stdout=output)
        for lang in settings.MODELTRANSLATION_LANGUAGES:
            with open(os.path.join('var/tmp', lang, 'settings.json'), 'r') as f:
                settings_json = json.load(f)
                self.assertEqual(len(settings_json), 2)
                self.assertEqual(len(settings_json['data']), 16)
                self.assertEqual(settings_json['data'][4]['values'][0]['pictogram'], pictogram_png)
                self.assertEqual(settings_json['data'][9]['values'][0]['pictogram'], pictogram_desk_png)

        image_practice = Image.open(os.path.join('var/tmp/nolang', pictogram_png[1:]))
        image_desk = Image.open(os.path.join('var/tmp/nolang', pictogram_desk_png[1:]))
        self.assertEqual(image_practice.size, (32, 32))
        self.assertEqual(image_desk.size, (32, 32))
        self.assertIn('en/settings.json', output.getvalue())


class SyncMobileTreksTest(TranslationResetMixin, VarTmpTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_a = TargetPortalFactory()
        cls.portal_b = TargetPortalFactory()
        picto_desk = get_dummy_uploaded_image()
        information_desk_type = InformationDeskTypeFactory.create(pictogram=picto_desk)
        cls.info_desk = InformationDeskFactory.create(type=information_desk_type)
        info_desk_no_picture = InformationDeskFactory.create(photo=None)

        cls.trek_1 = TrekWithPublishedPOIsFactory.create()
        cls.trek_1.information_desks.set((cls.info_desk, info_desk_no_picture))
        cls.trek_2 = TrekWithPublishedPOIsFactory.create(portals=(cls.portal_a,))
        cls.trek_3 = TrekWithPublishedPOIsFactory.create(portals=(cls.portal_b,))
        cls.trek_4 = TrekFactory.create()
        OrderedTrekChild.objects.create(parent=cls.trek_1, child=cls.trek_4, order=1)
        cls.desk = InformationDeskFactory.create()

        cls.trek_4.information_desks.add(cls.desk)

        cls.attachment_1 = AttachmentFactory.create(content_object=cls.trek_1,
                                                    attachment_file=get_dummy_uploaded_image())
        AttachmentFactory.create(content_object=cls.trek_1,
                                 attachment_file=get_dummy_uploaded_image())

        cls.poi_1 = cls.trek_1.published_pois.first()
        cls.attachment_poi_image_1 = AttachmentFactory.create(content_object=cls.poi_1,
                                                              attachment_file=get_dummy_uploaded_image())
        cls.attachment_poi_image_2 = AttachmentFactory.create(content_object=cls.poi_1,
                                                              attachment_file=get_dummy_uploaded_image())
        cls.attachment_poi_file = AttachmentFactory.create(content_object=cls.poi_1,
                                                           attachment_file=get_dummy_uploaded_file())
        cls.attachment_trek_image = AttachmentFactory.create(content_object=cls.trek_4,
                                                             attachment_file=get_dummy_uploaded_image())

        cls.touristic_content = TouristicContentFactory(geom='SRID=%s;POINT(700001 6600001)' % settings.SRID,
                                                        published=True)
        cls.touristic_event = TouristicEventFactory(geom='SRID=%s;POINT(700001 6600001)' % settings.SRID,
                                                    published=True)
        cls.touristic_content_portal_a = TouristicContentFactory(geom='SRID=%s;POINT(700001 6600001)' % settings.SRID,
                                                                 published=True, portals=[cls.portal_a])
        cls.touristic_event_portal_a = TouristicEventFactory(geom='SRID=%s;POINT(700001 6600001)' % settings.SRID,
                                                             published=True, portals=[cls.portal_a])
        cls.touristic_content_portal_b = TouristicContentFactory(geom='SRID=%s;POINT(700001 6600001)' % settings.SRID,
                                                                 published=True, portals=[cls.portal_b])
        cls.touristic_event_portal_b = TouristicEventFactory(geom='SRID=%s;POINT(700001 6600001)' % settings.SRID,
                                                             published=True, portals=[cls.portal_b])
        cls.attachment_content_1 = AttachmentFactory.create(content_object=cls.touristic_content,
                                                            attachment_file=get_dummy_uploaded_image())
        cls.attachment_event_1 = AttachmentFactory.create(content_object=cls.touristic_event,
                                                          attachment_file=get_dummy_uploaded_image())
        translation.deactivate()

    def test_sync_treks(self):
        output = StringIO()
        management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000',
                                skip_tiles=True, verbosity=2, stdout=output)
        for lang in settings.MODELTRANSLATION_LANGUAGES:
            with open(os.path.join('var/tmp', lang, 'treks.geojson'), 'r') as f:
                trek_geojson = json.load(f)
                self.assertEqual(len(trek_geojson['features']),
                                 Trek.objects.filter(**{'published_{}'.format(lang): True}).count())
        self.assertIn('en/treks.geojson', output.getvalue())

    def test_sync_treks_by_pk(self):
        output = StringIO()
        management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000',
                                skip_tiles=True, verbosity=2, stdout=output)
        with open(os.path.join('var/tmp/en', '{pk}'.format(pk=str(self.trek_1.pk)),
                               'trek.geojson'), 'r') as f:
            trek_geojson = json.load(f)
            self.assertEqual(len(trek_geojson['properties']), 34)

        self.assertIn('en/{pk}/trek.geojson'.format(pk=str(self.trek_1.pk)), output.getvalue())
        self.assertIn('en/{pk}/treks/{child_pk}.geojson'.format(pk=self.trek_1.pk, child_pk=self.trek_4.pk),
                      output.getvalue())

    def test_sync_treks_with_portal(self):
        output = StringIO()
        management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000',
                                skip_tiles=True, verbosity=2, portal=self.portal_a.name, stdout=output)
        self.assertFalse(os.path.exists(
            os.path.join('var', 'tmp', 'en', str(self.trek_3.pk), 'trek.geojson')
        ))
        for lang in settings.MODELTRANSLATION_LANGUAGES:
            with open(os.path.join('var', 'tmp', lang, 'treks.geojson'), 'r') as f:
                trek_geojson = json.load(f)
                self.assertEqual(len(trek_geojson['features']),
                                 Trek.objects.filter(**{'published_{}'.format(lang): True})
                                 .filter(Q(portal__name__in=(self.portal_a,)) | Q(portal=None)).count())
        with open(os.path.join('var', 'tmp', 'en', str(self.trek_1.pk), 'touristic_contents.geojson'), 'r') as f:
            tc_geojson = json.load(f)
            self.assertEqual(len(tc_geojson['features']), 1)
            # Only one because factory generate a portal for touristic contents
        with open(os.path.join('var', 'tmp', 'en', str(self.trek_1.pk), 'touristic_events.geojson'), 'r') as f:
            te_geojson = json.load(f)
            # Two because factory do not generate a portal for touristic events
            self.assertEqual(len(te_geojson['features']), 2)

    def test_sync_pois_by_treks(self):
        output = StringIO()
        management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000',
                                skip_tiles=True, verbosity=2, stdout=output)
        with open(os.path.join('var/tmp/en', str(self.trek_1.pk), 'pois.geojson'), 'r') as f:
            trek_geojson = json.load(f)
            if settings.TREKKING_TOPOLOGY_ENABLED:
                self.assertEqual(len(trek_geojson['features']), 2)
            else:
                # Without dynamic segmentation it used a buffer so we get all the pois normally linked
                # with the other treks.
                self.assertEqual(len(trek_geojson['features']), 6)
        self.assertIn('en/{pk}/pois.geojson'.format(pk=str(self.trek_1.pk)), output.getvalue())

    def test_medias_treks(self):
        output = StringIO()
        management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000',
                                skip_tiles=True, verbosity=2, stdout=output)
        self.assertTrue(os.path.exists(os.path.join('var/tmp/nolang', str(self.trek_1.pk),
                                                    'media/paperclip/trekking_trek')))
        self.assertTrue(os.path.exists(os.path.join('var/tmp/nolang', str(self.trek_1.pk),
                                                    'media/paperclip/trekking_poi')))
        self.assertTrue(os.path.exists(os.path.join('var/tmp/nolang', str(self.trek_1.pk),
                                                    'media/paperclip/tourism_touristiccontent')))
        self.assertTrue(os.path.exists(os.path.join('var/tmp/nolang', str(self.trek_1.pk),
                                                    'media/paperclip/tourism_touristicevent')))
        # Information desk picture
        self.assertTrue(os.path.exists(os.path.join('var/tmp/nolang', str(self.trek_1.pk), 'media',
                                                    'upload')))

    def test_medias_treks_multiple_picture(self):
        output = StringIO()
        management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000',
                                skip_tiles=True, verbosity=2, stdout=output)
        self.assertEqual(2, len(os.listdir(os.path.join('var/tmp/nolang', str(self.trek_1.pk),
                                                        'media/paperclip/trekking_trek', str(self.trek_1.pk)))))
        self.assertEqual(2, len(os.listdir(os.path.join('var/tmp/nolang', str(self.trek_1.pk),
                                                        'media/paperclip/trekking_poi', str(self.poi_1.pk)))))
        self.assertEqual(1, len(os.listdir(os.path.join('var/tmp/nolang', str(self.trek_1.pk),
                                                        'media/paperclip/tourism_touristiccontent',
                                                        str(self.touristic_content.pk)))))
        self.assertEqual(1, len(os.listdir(os.path.join('var/tmp/nolang', str(self.trek_1.pk),
                                                        'media/paperclip/tourism_touristicevent',
                                                        str(self.touristic_event.pk)))))
        # Information desk picture (2 here because 1 from parent and 1 from child)
        self.assertEqual(2, len(os.listdir(os.path.join('var/tmp/nolang', str(self.trek_1.pk), 'media/upload'))))
        with open(os.path.join('var/tmp/en', str(self.trek_1.pk), 'trek.geojson'), 'r') as f:
            trek_geojson = json.load(f)
            # Check inside file generated we have 2 pictures
            self.assertEqual(len(trek_geojson['properties']['pictures']), 2)

        with open(os.path.join('var/tmp/en', str(self.trek_1.pk), 'pois.geojson'), 'r') as f:
            poi_geojson = json.load(f)
            # Check inside file generated we have 2 pictures
            self.assertEqual(len(poi_geojson['features'][0]['properties']['pictures']), 2)

    @override_settings(MOBILE_NUMBER_PICTURES_SYNC=1)
    def test_medias_treks_configuration_number_picture(self):
        output = StringIO()
        management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000',
                                skip_tiles=True, verbosity=2, stdout=output)
        self.assertEqual(1, len(os.listdir(os.path.join('var/tmp/nolang', str(self.trek_1.pk),
                                                        'media/paperclip/trekking_trek', str(self.trek_1.pk)))))
        self.assertEqual(1, len(os.listdir(os.path.join('var/tmp/nolang', str(self.trek_1.pk),
                                                        'media/paperclip/trekking_poi', str(self.poi_1.pk)))))
        with open(os.path.join('var/tmp/en', str(self.trek_1.pk), 'trek.geojson'), 'r') as f:
            trek_geojson = json.load(f)
            # Check inside file generated we have only one picture
            self.assertEqual(len(trek_geojson['properties']['pictures']), 1)

        with open(os.path.join('var/tmp/en', str(self.trek_1.pk), 'pois.geojson'), 'r') as f:
            poi_geojson = json.load(f)
            # Check inside file generated we have only one picture
            self.assertEqual(len(poi_geojson['features'][0]['properties']['pictures']), 1)

    @mock.patch('geotrek.api.mobile.views.TrekViewSet.list')
    def test_streaminghttpresponse(self, mocke):
        output = StringIO()
        mocke.return_value = StreamingHttpResponse()
        TrekWithPublishedPOIsFactory.create(published_fr=True)
        management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000',
                                skip_tiles=True, verbosity=2, stdout=output)
        self.assertTrue(os.path.exists(os.path.join('var/tmp/en', 'treks.geojson')))

    def test_indent(self):
        indent = 3
        output = StringIO()
        TrekWithPublishedPOIsFactory.create(published_fr=True)
        management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000',
                                skip_tiles=True, verbosity=2, indent=indent, stdout=output)
        with open(os.path.join('var/tmp/en', 'treks.geojson')) as f:
            # without indent the json is in one line
            json_file = f.readlines()
            # with indent the json is stocked in more than one line
            self.assertGreater(len(json_file), 1)
            # there are 3 spaces in the second line because the indent is 3
            self.assertEqual(json_file[1][:indent], indent * ' ')

    def test_object_without_pictogram(self):
        pictogram_name_before = os.path.basename(self.touristic_event.type.pictogram.name)
        management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000',
                                skip_tiles=True, verbosity=0)
        self.assertIn(pictogram_name_before, os.listdir('var/tmp/nolang/media/upload'))

        for event_type in TouristicEventType.objects.all():
            event_type.pictogram = None
            event_type.save()

        management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000',
                                skip_tiles=True, verbosity=0)
        self.assertNotIn(pictogram_name_before, os.listdir('var/tmp/nolang/media/upload'))

    @skipIf(settings.TREKKING_TOPOLOGY_ENABLED, 'Test without dynamic segmentation only')
    def test_multilinestring(self):
        TrekFactory.create(geom=MultiLineString(LineString((0, 0), (0, 1)), LineString((100, 100), (100, 101))))
        management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000', skip_tiles=True,
                                verbosity=0)
        for lang in settings.MODELTRANSLATION_LANGUAGES:
            with open(os.path.join('var/tmp', lang, 'treks.geojson'), 'r') as f:
                trek_geojson = json.load(f)
                self.assertEqual(len(trek_geojson['features']),
                                 Trek.objects.filter(**{'published_{}'.format(lang): True}).count())

    def test_sync_treks_informationdesk_photo_missing(self):
        os.remove(self.info_desk.photo.path)
        output = StringIO()
        management.call_command('sync_mobile', 'var/tmp', url='http://localhost:8000',
                                skip_tiles=True, verbosity=2, stdout=output)
        self.assertIn('Done', output.getvalue())
