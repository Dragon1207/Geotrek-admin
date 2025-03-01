import json

import datetime

from mimetypes import guess_type

from django.conf import settings
from django.contrib.gis.geos import Point
from django.db import models
from django.utils.translation import gettext as _

from geotrek.common.parsers import (AttachmentParserMixin, Parser,
                                    TourInSoftParser)
from geotrek.tourism.models import TouristicContent, TouristicEvent, TouristicContentType1, TouristicContentType2


class TouristicContentMixin:
    # Mixin which handle multiple type1/2 with the same name in different categories
    def get_to_delete_kwargs(self):
        # FIXME: use mapping if it exists
        kwargs = {}
        for dst, val in self.constant_fields.items():
            field = self.model._meta.get_field(dst)
            if isinstance(field, models.ForeignKey):
                natural_key = self.natural_keys[dst]
                try:
                    kwargs[dst] = field.remote_field.model.objects.get(**{natural_key: val})
                except field.remote_field.model.DoesNotExist:
                    return None
            else:
                kwargs[dst] = val
        for dst, val in self.m2m_constant_fields.items():
            assert not self.separator or self.separator not in val
            field = self.model._meta.get_field(dst)
            natural_key = self.natural_keys[dst]
            filters = {natural_key: subval for subval in val}
            if not filters:
                continue
            if dst in ('type1', 'type2'):
                filters['category'] = kwargs['category'].pk
            try:
                kwargs[dst] = field.remote_field.model.objects.get(**filters)
            except field.remote_field.model.DoesNotExist:
                return None
        return kwargs


class ApidaeParser(AttachmentParserMixin, Parser):
    """Parser to import "anything" from APIDAE"""
    separator = None
    api_key = None
    project_id = None
    selection_id = None
    url = 'http://api.apidae-tourisme.com/api/v002/recherche/list-objets-touristiques/'
    model = None
    eid = 'eid'
    fields = {
        'name': 'nom.libelleFr',
    }
    constant_fields = {
        'published': True,
    }
    non_fields = {
        'attachments': 'illustrations',
    }
    # Use for foreign keys. When the key is a foreign key, it will try to get the key's value.
    # In django : 'category' : 'label' -> category.label
    field_options = {
        'name': {'required': True},
        'geom': {'required': True},
    }
    size = 100
    skip = 0
    responseFields = [
        'id',
        'nom',
        'presentation.descriptifCourt',
        'presentation.descriptifDetaille',
        'localisation.adresse',
        'localisation.geolocalisation.geoJson.coordinates',
        'localisation.geolocalisation.complement.libelleFr',
        'informations.moyensCommunication',
        'ouverture.periodeEnClair',
        'informationsHebergementCollectif.capacite.capaciteTotale',
        'informationsHebergementCollectif.hebergementCollectifType.libelleFr',
        'descriptionTarif.tarifsEnClair',
        'descriptionTarif.modesPaiement',
        'prestations.services',
        'gestion.dateModification',
        'gestion.membreProprietaire.nom',
        'illustrations'
    ]

    @property
    def items(self):
        if self.nb == 0:
            return []
        return self.root['objetsTouristiques']

    def next_row(self):
        while True:
            params = {
                'apiKey': self.api_key,
                'projetId': self.project_id,
                'selectionIds': [self.selection_id],
                'count': self.size,
                'first': self.skip,
                'responseFields': self.responseFields
            }
            response = self.request_or_retry(self.url, params={'query': json.dumps(params)})
            self.root = response.json()
            self.nb = int(self.root['numFound'])
            for row in self.items:
                yield row
            self.skip += self.size
            if self.skip >= self.nb:
                return

    def normalize_field_name(self, name):
        return name

    def filter_eid(self, src, val):
        return str(val)

    def filter_geom(self, src, val):
        lng, lat = val
        geom = Point(float(lng), float(lat), srid=4326)  # WGS84
        geom.transform(settings.SRID)
        return geom


class AttachmentApidaeParserMixin(object):
    def filter_attachments(self, src, val):
        result = []
        for subval in val or []:
            copyright_attachment = subval.get('copyright', {}).get('libelleFr')
            legend_attachment = subval.get('legende', {}).get('libelleFr')
            name_attachment = subval.get('nom', {}).get('libelleFr')
            if legend_attachment:
                legend = legend_attachment
                if guess_type(legend)[0] in ['image/jpeg', 'image/png', 'image/x-ms-bmp']:
                    legend = name_attachment
            else:
                legend = name_attachment
            result.append((subval['traductionFichiers'][0]['url'], legend, copyright_attachment))
        return result


class TouristicEventApidaeParser(AttachmentApidaeParserMixin, ApidaeParser):
    """Parser to import touristic events from APIDAE"""
    type = None
    themes = None
    source = None
    portal = None
    model = TouristicEvent
    fields = {
        'description_teaser': 'presentation.descriptifCourt.libelleFr',
        'description': 'presentation.descriptifDetaille.libelleFr',
        'geom': 'localisation.geolocalisation.geoJson.coordinates',
        'begin_date': 'ouverture.periodesOuvertures.0.dateDebut',
        'end_date': 'ouverture.periodesOuvertures.0.dateFin',
        'duration': ('ouverture.periodesOuvertures.0.horaireOuverture',
                     'ouverture.periodesOuvertures.-1.horaireFermeture'),
        'meeting_time': 'ouverture.periodesOuvertures.0.horaireOuverture',
        'contact': (
            'localisation.adresse.adresse1',
            'localisation.adresse.adresse2',
            'localisation.adresse.adresse3',
            'localisation.adresse.codePostal',
            'localisation.adresse.commune.nom',
            'informations.moyensCommunication',
        ),
        'email': 'informations.moyensCommunication',
        'website': 'informations.moyensCommunication',
        'organizer': 'informations.structureGestion.nom.libelleFr',
        'type': 'informationsFeteEtManifestation.typesManifestation.0.libelleFr',
        'participant_number': 'informationsFeteEtManifestation.nbParticipantsAttendu',
        'practical_info': (
            'ouverture.periodeEnClair.libelleFr',
            'informationsFeteEtManifestation.nbParticipantsAttendu',
            'descriptionTarif.tarifsEnClair.libelleFr',
            'descriptionTarif.modesPaiement',
            'prestations.services',
            'prestations.languesParlees',
            'localisation.geolocalisation.complement.libelleFr',
            'gestion.dateModification',
            'gestion.membreProprietaire.nom',
        ),
        'eid': 'id',
        'name': 'nom.libelleFr',
    }
    responseFields = [
        'id',
        'nom',
        'ouverture.periodeEnClair',
        'ouverture.periodesOuvertures',
        'informationsFeteEtManifestation',
        'presentation.descriptifCourt',
        'presentation.descriptifDetaille',
        'localisation.adresse',
        'localisation.geolocalisation.geoJson.coordinates',
        'localisation.geolocalisation.complement.libelleFr',
        'informations.moyensCommunication',
        'informations.structureGestion.nom.libelleFr',
        'descriptionTarif.tarifsEnClair',
        'descriptionTarif.modesPaiement',
        'prestations',
        'gestion.dateModification',
        'gestion.membreProprietaire.nom',
        'illustrations'
    ]
    m2m_fields = {
        'themes': 'informationsFeteEtManifestation.themes.*.libelleFr'
    }
    natural_keys = {
        'themes': 'label',
        'type': 'type',
        'source': 'name',
        'portal': 'name',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.constant_fields = self.constant_fields.copy()
        self.m2m_constant_fields = self.m2m_constant_fields.copy()
        self.field_options = self.field_options.copy()
        self.field_options['themes'] = {'create': True}
        self.field_options['type'] = {'create': True}
        if self.type is not None:
            self.constant_fields['type'] = self.type
        if self.themes is not None:
            self.m2m_constant_fields['themes'] = self.themes
        if self.source is not None:
            self.m2m_constant_fields['source'] = self.source
        if self.portal is not None:
            self.m2m_constant_fields['portal'] = self.portal

    def filter_description_teaser(self, src, val):
        return '<br>'.join(val.splitlines())

    def filter_description(self, src, val):
        return '<br>'.join(val.splitlines())

    def filter_duration(self, src, val):
        begin, end = val
        try:
            date_begin = datetime.datetime.strptime(begin, '%H:%M:%S')
            date_fin = datetime.datetime.strptime(end, '%H:%M:%S')
            return str(date_fin - date_begin)
        except TypeError:
            return None

    def filter_contact(self, src, val):
        (address1, address2, address3, zipCode, commune, comm) = val
        tel = self.filter_comm(comm, 201, multiple=True)
        if tel:
            tel = "Tél. " + tel
        lines = [line for line in [
            address1,
            address2,
            address3,
            ' '.join([part for part in [zipCode, commune] if part]),
            tel,
        ] if line]
        return '<br>'.join(lines)

    def filter_email(self, src, val):
        return self.filter_comm(val, 204, multiple=False)

    def filter_website(self, src, val):
        return self.filter_comm(val, 205, multiple=False)

    def filter_practical_info(self, src, val):
        (ouverture, capacite, tarifs, paiement, services, langues, localisation, datemodif, proprio) = val
        if ouverture:
            ouverture = "<b>Ouverture:</b><br>" + "<br>".join(ouverture.splitlines()) + "<br>"
        if capacite:
            capacite = "<b>Capacité totale:</b><br>" + str(capacite) + "<br>"
        if tarifs:
            tarifs = "<b>Tarifs:</b><br>" + "<br>".join(tarifs.splitlines()) + "<br>"
        if paiement:
            paiement = "<b>Modes de paiement:</b><br>" + ", ".join([i['libelleFr'] for i in paiement]) + "<br>"
        if services:
            services = "<b>Services:</b><br>" + ", ".join([i['libelleFr'] for i in services]) + "<br>"
        if langues:
            langues = "<b>Langues Parlées:</b><br>" + ", ".join([i['libelleFr'] for i in langues]) + "<br>"
        if localisation:
            localisation = "<b>Accès:</b><br>" + "<br>".join(localisation.splitlines()) + "<br>"
        datemodif = datetime.datetime.strptime(datemodif[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        modif = "<i>Fiche mise à jour par " + proprio + " le " + datemodif + "</i>"
        lines = [line for line in [
            ouverture,
            capacite,
            tarifs,
            paiement,
            services,
            langues,
            localisation,
            modif,
        ] if line]
        return '<br>'.join(lines)

    def filter_comm(self, val, code, multiple=True):
        if not val:
            return None
        vals = [subval['coordonnees']['fr'] for subval in val if subval['type']['id'] == code]
        if multiple:
            return ' / '.join(vals)
        if vals:
            return vals[0]
        return None


class TouristicContentApidaeParser(AttachmentApidaeParserMixin, TouristicContentMixin, ApidaeParser):
    """Parser to import touristic contents from APIDAE"""
    separator = None
    api_key = None
    project_id = None
    selection_id = None
    category = None
    type1 = None
    type2 = None
    source = None
    portal = None
    themes = None
    url = 'http://api.apidae-tourisme.com/api/v002/recherche/list-objets-touristiques/'
    model = TouristicContent
    eid = 'eid'
    fields = {
        'eid': 'id',
        'name': 'nom.libelleFr',
        'description': 'presentation.descriptifDetaille.libelleFr',
        'description_teaser': 'presentation.descriptifCourt.libelleFr',
        'contact': (
            'localisation.adresse.adresse1',
            'localisation.adresse.adresse2',
            'localisation.adresse.adresse3',
            'localisation.adresse.codePostal',
            'localisation.adresse.commune.nom',
            'informations.moyensCommunication',
        ),
        'email': 'informations.moyensCommunication',
        'website': 'informations.moyensCommunication',
        'geom': 'localisation.geolocalisation.geoJson.coordinates',
        'practical_info': (
            'ouverture.periodeEnClair.libelleFr',
            'informationsHebergementCollectif.capacite.capaciteTotale',
            'descriptionTarif.tarifsEnClair.libelleFr',
            'descriptionTarif.modesPaiement',
            'prestations.services',
            'localisation.geolocalisation.complement.libelleFr',
            'gestion.dateModification',
            'gestion.membreProprietaire.nom',
        ),
    }
    natural_keys = {
        'themes': 'label',
        'category': 'label',
        'type1': 'label',
        'type2': 'label',
        'source': 'name',
        'portal': 'name',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.constant_fields = self.constant_fields.copy()
        self.m2m_constant_fields = self.m2m_constant_fields.copy()
        if self.category:
            self.constant_fields['category'] = self.category
        if self.type1 is not None:
            self.m2m_constant_fields['type1'] = self.type1
        if self.type2 is not None:
            self.m2m_constant_fields['type2'] = self.type2
        if self.themes is not None:
            self.m2m_constant_fields['themes'] = self.themes
        if self.source is not None:
            self.m2m_constant_fields['source'] = self.source
        if self.portal is not None:
            self.m2m_constant_fields['portal'] = self.portal

    def filter_comm(self, val, code, multiple=True):
        if not val:
            return None
        vals = [subval['coordonnees']['fr'] for subval in val if subval['type']['id'] == code]
        if multiple:
            return ' / '.join(vals)
        if vals:
            return vals[0]
        return None

    def filter_email(self, src, val):
        return self.filter_comm(val, 204, multiple=False)

    def filter_website(self, src, val):
        return self.filter_comm(val, 205, multiple=False)

    def filter_contact(self, src, val):
        (address1, address2, address3, zipCode, commune, comm) = val
        tel = self.filter_comm(comm, 201, multiple=True)
        if tel:
            tel = "Tél. " + tel
        lines = [line for line in [
            address1,
            address2,
            address3,
            ' '.join([part for part in [zipCode, commune] if part]),
            tel,
        ] if line]
        return '<br>'.join(lines)

    def filter_practical_info(self, src, val):
        (ouverture, capacite, tarifs, paiement, services, localisation, datemodif, proprio) = val
        if ouverture:
            ouverture = "<b>Ouverture:</b><br>" + "<br>".join(ouverture.splitlines()) + "<br>"
        if capacite:
            capacite = "<b>Capacité totale:</b><br>" + str(capacite) + "<br>"
        if tarifs:
            tarifs = "<b>Tarifs:</b><br>" + "<br>".join(tarifs.splitlines()) + "<br>"
        if paiement:
            paiement = "<b>Modes de paiement:</b><br>" + ", ".join([i['libelleFr'] for i in paiement]) + "<br>"
        if services:
            services = "<b>Services:</b><br>" + ", ".join([i['libelleFr'] for i in services]) + "<br>"
        if localisation:
            localisation = "<b>Accès:</b><br>" + "<br>".join(localisation.splitlines()) + "<br>"
        datemodif = datetime.datetime.strptime(datemodif[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        modif = "<i>Fiche mise à jour par " + proprio + " le " + datemodif + "</i>"
        lines = [line for line in [
            ouverture,
            capacite,
            tarifs,
            paiement,
            services,
            localisation,
            modif,
        ] if line]
        return '<br>'.join(lines)

    def filter_description(self, src, val):
        return '<br>'.join(val.splitlines())

    def filter_description_teaser(self, src, val):
        return '<br>'.join(val.splitlines())


class HebergementsApidaeParser(TouristicContentApidaeParser):
    category = "Hébergements"
    m2m_fields = {
        'type1': 'informationsHebergementCollectif.hebergementCollectifType.libelleFr',
    }

    def filter_type1(self, src, val):
        return self.apply_filter('type1', src, [val])


class EspritParcParser(AttachmentParserMixin, Parser):
    model = TouristicContent
    eid = 'eid'
    separator = None
    delete = True
    fields = {
        'eid': 'eid',
        'name': 'nomCommercial',
        'description': 'descriptionDetaillee',
        'practical_info': 'informationsPratiques',
        'category': 'type.label',
        'contact': (
            'contact.adresse',
            'contact.codePostal',
            'contact.commune',
            'contact.telephone',
            'contact.gsm',
            'contact.fax',
            'contact.facebook',
            'contact.twitter'
        ),
        'email': 'contact.courriel',
        'website': 'contact.siteWeb',
        'geom': 'geo',
    }

    constant_fields = {
        'published': True,
        'approved': True,
        'deleted': False,
    }

    field_options = {
        'name': {'required': True, },
        'geom': {'required': True, },
        'category': {'create': True},
    }

    natural_keys = {
        'category': 'label',
        'type1': 'label',
        'type2': 'label'
    }

    m2m_fields = {
        'type1': 'sousType.label',
        'type2': 'classement',
    }

    non_fields = {
        'attachments': 'photo',
    }

    def filter_attachments(self, src, val):
        result = []
        for subval in val or []:
            if 'url' in subval:
                result.append((subval['url'],
                               subval.get('legende', None),
                               subval.get('credits', None)))
        return result

    @property
    def items(self):
        return self.root['responseData']

    def next_row(self):
        response = self.request_or_retry(self.url)
        self.root = response.json()
        self.nb = int(self.root['numFound'])

        for row in self.items:
            yield row

    def normalize_field_name(self, name):
        return name

    def filter_eid(self, src, val):
        return "{}".format(val)

    def filter_contact(self, src, val):
        (address, zipCode, commune, telephone, gsm, fax, facebook, twitter) = val
        cp_com = ' '.join([part for part in (zipCode, commune) if part])
        return '<br>'.join([part for part in (address, cp_com, telephone, gsm, fax, facebook, twitter) if part])

    def filter_geom(self, src, val):
        lng = val['lon']
        lat = val['lat']
        geom = Point(float(lng), float(lat), srid=4326)  # WGS84
        geom.transform(settings.SRID)
        return geom

    def filter_name(self, src, val):
        return val[:128]

    def filter_category(self, src, val):
        if not val:
            return None

        return self.apply_filter('category', src, val)

    def filter_type1(self, src, val):
        dst = []
        if val:
            try:
                dst.append(TouristicContentType1.objects.get(category=self.obj.category, label=val))
            except TouristicContentType1.DoesNotExist:
                self.add_warning(
                    _("Type 1 '{subval}' does not exist for category '{cat}'. Please add it").format(
                        subval=val, cat=self.obj.category.label))
        return dst

    def filter_type2(self, src, val):
        dst = []
        if val:
            try:
                dst.append(TouristicContentType2.objects.get(category=self.obj.category, label=val))
            except TouristicContentType2.DoesNotExist:
                self.add_warning(_("Type 2 '{subval}' does not exist for category '{cat}'. Please add it").format(
                    subval=val, cat=self.obj.category.label))
        return dst


# Deprecated: for compatibility only
TouristicContentSitraParser = TouristicContentApidaeParser
HebergementsSitraParser = HebergementsApidaeParser


class TouristicContentTourInSoftParser(TouristicContentMixin, TourInSoftParser):
    eid = 'eid'
    model = TouristicContent
    delete = True
    category = None
    type1 = None
    type2 = None
    themes = None
    source = None
    portal = None

    constant_fields = {
        'published': True,
        'deleted': False,
    }

    fields = {
        'eid': 'SyndicObjectID',
        'name': 'SyndicObjectName',
        'description_teaser': 'DescriptionCommerciale',
        'geom': ('GmapLongitude', 'GmapLatitude'),
        'practical_info': (
            'LanguesParlees',
            'PeriodeOuverture',
            'PrestationsEquipements',
        ),
        'contact': ('MoyenDeCom', 'AdresseComplete'),
        'email': 'MoyenDeCom',
        'website': 'MoyenDeCom',
    }

    non_fields = {
        'attachments': 'Photos',
    }

    field_options = {
        'geom': {'required': True},
        'type1': {'create': True, 'fk': 'category'},
        'type2': {'create': True, 'fk': 'category'},
    }

    natural_keys = {
        'category': 'label',
        'type1': 'label',
        'type2': 'label',
        'source': 'name',
        'portal': 'name',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.constant_fields = self.constant_fields.copy()
        self.m2m_constant_fields = self.m2m_constant_fields.copy()
        if self.category:
            self.constant_fields['category'] = self.category
        if self.type1 is not None:
            self.m2m_constant_fields['type1'] = self.type1
        if self.type2 is not None:
            self.m2m_constant_fields['type2'] = self.type2
        if self.themes is not None:
            self.m2m_constant_fields['themes'] = self.themes
        if self.source is not None:
            self.m2m_constant_fields['source'] = self.source
        if self.portal is not None:
            self.m2m_constant_fields['portal'] = self.portal

    def filter_practical_info(self, src, val):
        langues, periodes, equipements = val
        infos = []

        if langues:
            infos.append(
                "<strong>Langues parlées :</strong><br>"
                + "<br>".join(langues.split(self.separator))
            )

        if periodes:
            periode_infos = ["<strong>Période d'ouverture :</strong>"]
            for periode in periodes.split(self.separator):
                items = periode.split(self.separator2)
                if len(items) >= 2 and items[0] and items[1]:
                    periode_infos.append(
                        "du %s au %s" % (items[0], items[1])
                    )
            infos.append("<br>".join(periode_infos))

        if equipements:
            infos.append(
                "<strong>Équipements :</strong><br>"
                + "<br>".join(equipements.split(self.separator))
            )

        return "<br><br>".join(infos)


class TouristicContentTourInSoftParserV3(TouristicContentTourInSoftParser):
    version_tourinsoft = 3


class TouristicContentTourInSoftParserV3withMedias(TouristicContentTourInSoftParserV3):

    non_fields = {
        'attachments': 'MediaPhotoss',
    }

    def get_nb(self):
        return int(len(self.root['value']))

    def filter_attachments(self, src, val):
        if not val:
            return []
        else:
            return [
                (entry["Photo"]["Url"], entry["Photo"]["Titre"], entry["Photo"]["Credit"])
                for entry in val if entry["Photo"] is not None
            ]


class TouristicEventTourInSoftParser(TourInSoftParser):
    eid = 'eid'
    model = TouristicEvent
    delete = True
    type = None
    themes = None
    source = None
    portal = None

    constant_fields = {
        'published': True,
        'deleted': False,
    }

    fields = {
        'eid': 'SyndicObjectID',
        'name': 'SyndicObjectName',
        'description': 'DescriptionCommerciale2',
        'description_teaser': 'DescriptionCommerciale',
        'geom': ('GmapLongitude', 'GmapLatitude'),
        'practical_info': (
            'LanguesParlees',
            'PrestationsEquipements',
        ),
        'contact': ('MoyenDeCom', 'AdresseComplete'),
        'email': 'MoyenDeCom',
        'website': 'MoyenDeCom',
        'begin_date': 'PeriodeOuverture',
        'end_date': 'PeriodeOuverture'
    }

    non_fields = {
        'attachments': 'Photos',
    }

    field_options = {
        'geom': {'required': True},
    }

    natural_keys = {
        'type': 'type',
        'source': 'name',
        'portal': 'name',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.constant_fields = self.constant_fields.copy()
        self.m2m_constant_fields = self.m2m_constant_fields.copy()
        if self.type is not None:
            self.constant_fields['type'] = self.type
        if self.themes is not None:
            self.m2m_constant_fields['themes'] = self.themes
        if self.source is not None:
            self.m2m_constant_fields['source'] = self.source
        if self.portal is not None:
            self.m2m_constant_fields['portal'] = self.portal

    def filter_practical_info(self, src, val):
        langues, equipements = val
        infos = []

        if langues:
            infos.append(
                "<strong>Langues parlées :</strong><br>"
                + "<br>".join(langues.split(self.separator))
            )

        if equipements:
            infos.append(
                "<strong>Équipements :</strong><br>"
                + "<br>".join(equipements.split(self.separator))
            )

        return "<br><br>".join(infos)

    def filter_begin_date(self, src, val):
        if val:
            for subval in val.split(self.separator):
                values = subval.split(self.separator2)
                if values and values[1]:
                    day, month, year = values[1].split('/')
                    if datetime.date(int(year), int(month), int(day)) < datetime.date.today():
                        continue
                if values and values[0]:
                    day, month, year = values[0].split('/')
                    return '{year}-{month}-{day}'.format(year=year, month=month, day=day)

    def filter_end_date(self, src, val):
        if val:
            for subval in val.split(self.separator):
                values = subval.split(self.separator2)
                if values and values[1]:
                    day, month, year = values[1].split('/')
                    if datetime.date(int(year), int(month), int(day)) < datetime.date.today():
                        continue
                    return '{year}-{month}-{day}'.format(year=year, month=month, day=day)


class TouristicEventTourInSoftParserV3(TouristicEventTourInSoftParser):
    version_tourinsoft = 3
