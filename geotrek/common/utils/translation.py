from django.conf import settings

if 'modeltranslation' in settings.INSTALLED_APPS:
    from modeltranslation.fields import TranslationField
    from modeltranslation.translator import translator, NotRegistered


def get_translated_fields(model):
    """Get translated fields from a model"""
    try:
        mto = translator.get_options_for_model(model)
    except NotRegistered:
        translated_fields = []
    else:
        translated_fields = mto.fields.keys()
    return translated_fields
