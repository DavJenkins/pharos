"""Version 1 content-handler contract and configuration-selected registry.

Registry inspection never imports handler code. Loading/executing a handler is a
trusted local operation, used by the approved restoration worker.
"""
from dataclasses import dataclass, field
import importlib.util
import inspect
import hashlib
import sys
from pathlib import Path, PurePosixPath
from typing import Callable
import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / 'config/content-types.yaml'
OPERATIONS = {'restore', 'inspect', 'verify', 'update', 'remove'}


def source_path(root, name):
    relative = PurePosixPath(name)
    if not name or relative.is_absolute() or '\\' in name or '..' in relative.parts:
        raise ValueError('Handler must use a repository-relative path')
    path = Path(root).joinpath(*relative.parts).resolve()
    if not path.is_relative_to(Path(root).resolve()) or path.suffix != '.py' or not path.is_file():
        raise ValueError('Handler must be an existing Python file within the repository')
    return path


def read_registry(path=REGISTRY, root=ROOT):
    class UniqueLoader(yaml.SafeLoader):
        pass
    def mapping(loader, node):
        result = {}
        for key, value in node.value:
            key = loader.construct_object(key)
            if not isinstance(key, str) or key in result:
                raise ValueError('Registry keys must be unique strings')
            result[key] = loader.construct_object(value)
        return result
    UniqueLoader.add_constructor('tag:yaml.org,2002:map', mapping)
    registry = yaml.load(Path(path).read_text(encoding='utf-8'), Loader=UniqueLoader)
    if not isinstance(registry, dict) or set(registry) != {'schema', 'types'} or type(registry['schema']) is not int or registry['schema'] != 1:
        raise ValueError('Unsupported content type registry schema')
    if not isinstance(registry['types'], dict):
        raise ValueError('types must be a mapping')
    for name, spec in registry['types'].items():
        if not isinstance(spec, dict) or set(spec) != {'api', 'handler', 'operations', 'options'}:
            raise ValueError('Each type requires api, handler, operations and options: ' + name)
        if type(spec['api']) is not int or spec['api'] != 1:
            raise ValueError('Unsupported handler API: ' + name)
        operations = spec['operations']
        if not isinstance(operations, list) or not operations or any(not isinstance(op, str) or op not in OPERATIONS for op in operations) or len(set(operations)) != len(operations):
            raise ValueError('Invalid operations: ' + name)
        if not isinstance(spec['options'], dict) or not isinstance(spec['handler'], str):
            raise ValueError('Invalid handler/options: ' + name)
        source_path(root, spec['handler'])
    return registry


@dataclass
class Context:
    content_root: Path
    profile: dict
    profile_folder: Path
    options: dict = field(default_factory=dict)
    progress: Callable[[str], None] = lambda phase: None
    cancelled: Callable[[], bool] = lambda: False

    def checkpoint(self, phase):
        if self.cancelled():
            raise InterruptedError('Content operation cancelled')
        self.progress(phase)

    def target(self, relative):
        from tools.content_profile import inside
        return inside(self.content_root, relative)


def load_handler(spec, root=ROOT):
    path = source_path(root, spec['handler'])
    module_name = 'dataark_handler_' + hashlib.sha256(str(path).encode()).hexdigest()
    module_spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_name] = module
    try:
        # Execute current reviewed source, never a stale timestamp-based .pyc.
        exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    if type(getattr(module, 'API_VERSION', None)) is not int or module.API_VERSION != 1:
        raise ValueError('Handler API_VERSION must be 1')
    for name, count in [('validate', 2)] + [(operation, 2) for operation in spec['operations']]:
        function = getattr(module, name, None)
        if not callable(function):
            raise ValueError('Handler missing callable: ' + name)
        try:
            inspect.signature(function).bind(*([None] * count))
        except TypeError as error:
            raise ValueError('Handler signature must accept (item, context): ' + name) from error
    return module


def dispatch(type_name, operation, item, context, registry_path=REGISTRY, root=ROOT):
    registry = read_registry(registry_path, root)
    if type_name not in registry['types']:
        raise ValueError('Unknown content type: ' + type_name)
    spec = registry['types'][type_name]
    if operation not in spec['operations']:
        raise ValueError('Operation not supported by content type: ' + operation)
    context.options = dict(spec['options'])
    context.checkpoint('validating')
    handler = load_handler(spec, root)
    handler.validate(item, context)
    context.checkpoint(operation)
    result = getattr(handler, operation)(item, context)
    if not isinstance(result, dict) or result.get('status') not in {'complete', 'present', 'missing'} or not isinstance(result.get('message'), str):
        raise ValueError('Handler must return {status: complete|present|missing, message: string}')
    if operation != 'inspect' and result['status'] == 'missing':
        raise RuntimeError('Handler did not complete ' + operation + ': ' + result['message'])
    return result


def portable_sources(path=REGISTRY, root=ROOT):
    """Includes registry and all declared handlers, without importing them."""
    registry = read_registry(path, root)
    yield Path(path), 'config/content-types.yaml'
    for name in sorted({spec['handler'] for spec in registry['types'].values()}):
        yield source_path(root, name), name
