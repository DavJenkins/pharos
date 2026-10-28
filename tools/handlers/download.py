"""Use the established verified, resumable downloader through handler API v1."""
API_VERSION = 1


def validate(item, context):
    from urllib.parse import urlsplit
    context.target(item['path'])
    url = urlsplit(item['url'])
    if url.scheme != 'https' or not url.hostname or url.username or url.password:
        raise ValueError('A public HTTPS download URL is required')


def restore(item, context):
    from tools.content_profile import download
    message = download(item, context.content_root, context.profile, verify_existing=True,
                       progress=context.checkpoint)
    return {'status': 'complete', 'message': message}
