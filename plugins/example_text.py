"""Small offline example: no network, no subprocesses, no external dependencies."""
API_VERSION = 1


def validate(item, context):
    context.target(item['path'])
    if not isinstance(item.get('text'), str):
        raise ValueError('text must be a string')


def inspect(item, context):
    present = context.target(item['path']).is_file()
    return {'status': 'present' if present else 'missing', 'message': 'Example text file'}


def verify(item, context):
    path = context.target(item['path'])
    if not path.is_file() or path.read_text(encoding='utf-8') != item['text']:
        raise ValueError('Example text is missing or differs')
    return {'status': 'complete', 'message': 'Text verified'}


def restore(item, context):
    path = context.target(item['path'])
    if path.is_file() and path.read_text(encoding='utf-8') == item['text']:
        return {'status': 'present', 'message': 'Matching text reused'}
    context.checkpoint('writing')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.part')
    if temporary.is_symlink():
        raise ValueError('Staging file cannot be a symlink')
    temporary.write_text(item['text'], encoding='utf-8')
    context.checkpoint('publishing')
    temporary.replace(path)
    return verify(item, context)
