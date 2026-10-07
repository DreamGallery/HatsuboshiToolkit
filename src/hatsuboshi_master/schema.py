"""Load the exported descriptor set without generated module import side effects."""
from pathlib import Path
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory

SCHEMA = Path(__file__).with_name('proto') / 'schema.pb'

def load_pool(path=SCHEMA):
    files = descriptor_pb2.FileDescriptorSet.FromString(Path(path).read_bytes())
    pool = descriptor_pool.DescriptorPool()
    pending = list(files.file)
    while pending:
        progress = False
        for file in pending[:]:
            try:
                pool.Add(file)
            except TypeError:
                continue
            pending.remove(file)
            progress = True
        if not progress:
            raise ValueError('Unresolved protobuf dependencies')
    return pool

def message(pool, name, **kwargs):
    return message_factory.GetMessageClass(pool.FindMessageTypeByName(name))(**kwargs)
