"""Compatibility adapter: existing recipes use the same API as added types."""
API_VERSION = 1


def validate(item, context):
    if item.get('id') != context.options.get('recipe'):
        raise ValueError('Recipe identifier does not match the registered handler options')


def restore(item, context):
    from tools.content_profile import _legacy_recipe
    _legacy_recipe(item, context.profile, context.content_root, context.profile_folder)
    return {'status': 'complete', 'message': 'Collection restoration completed'}
