{% set cfg = salt['mc_project.get_configuration'](project) %}
{% set data = cfg.data %}
from .prod import *


# Adjustments PDF exports
ALTIMETRIC_PROFILE_COLOR = '#33b652'
ALTIMETRIC_PROFILE_FONT = 'Archer-Book'

# Asked by J.Atche :
LEAFLET_CONFIG['MAX_ZOOM'] = 20
PATH_SNAPPING_DISTANCE = 3  # meters

# Necessary block of config when maps are not from Geotrek Tilecache :
LEAFLET_CONFIG['SRID'] = 3857
LEAFLET_CONFIG['TILES'] = [
    (gettext_noop('Scan'), 'http://gpp3-wxs.ign.fr/ilbpmecqb9rugpmbx4ojtt98/geoportail/wmts?LAYER=GEOGRAPHICALGRIDSYSTEMS.MAPS.SCAN-EXPRESS.CLASSIQUE&EXCEPTIONS=image/jpeg&FORMAT=image/jpeg&SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&STYLE=normal&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}',
     '&copy; IGN - GeoPortail'),
    (gettext_noop('Ortho'), 'http://gpp3-wxs.ign.fr/ilbpmecqb9rugpmbx4ojtt98/geoportail/wmts?LAYER=ORTHOIMAGERY.ORTHOPHOTOS&EXCEPTIONS=image/jpeg&FORMAT=image/jpeg&SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&STYLE=normal&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}',
     '&copy; IGN - GeoPortail'),
]

LEAFLET_CONFIG['OVERLAYS'] = [
    (gettext_noop('Cadastre'), 'http://gpp3-wxs.ign.fr/ilbpmecqb9rugpmbx4ojtt98/geoportail/wmts?LAYER=CADASTRALPARCELS.PARCELS&STYLE=bdparcellaire&EXCEPTIONS=image/jpeg&FORMAT=image/png&SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&STYLE=normal&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}',
     '&copy; IGN - GeoPortail'),
]
