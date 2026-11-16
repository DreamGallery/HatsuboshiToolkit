#!/usr/bin/env python3
"""Validate an exported descriptor set and reject incompatible replacements."""
import argparse
import json
from pathlib import Path
import sys

from google.protobuf import descriptor_pb2, descriptor_pool

FILES = ('penum.proto', 'pcommon.proto', 'pmaster.proto',
         'ptransaction.proto', 'papicommon.proto', 'papi.proto')


def descriptors(path):
    data = Path(path).read_bytes()
    if not data or len(data) > 32 * 1024 * 1024:
        raise ValueError('Invalid descriptor set size')
    schema = descriptor_pb2.FileDescriptorSet.FromString(data)
    if len(schema.file) != len(FILES) or {f.name for f in schema.file} != set(FILES):
        raise ValueError('Descriptor set must contain all six game protocol files')
    pool = descriptor_pool.DescriptorPool()
    pending = list(schema.file)
    while pending:
        ready = []
        for file in pending:
            try:
                pool.Add(file)
            except TypeError:
                continue
            ready.append(file)
        if not ready:
            raise ValueError('Invalid descriptors or unresolved protocol dependencies')
        pending = [f for f in pending if f not in ready]
    for name in ('pmaster.Story', 'client.api.MasterGetResponse'):
        pool.FindMessageTypeByName(name)
    return schema


def definitions(schema):
    messages, enums = {}, {}

    def walk(prefix, message_types, enum_types):
        for enum in enum_types:
            enums[prefix + enum.name] = {v.name: v.number for v in enum.value}
        for message in message_types:
            name = prefix + message.name
            messages[name] = {
                f.number: (f.name, f.type, f.type_name, f.label, f.proto3_optional,
                           message.oneof_decl[f.oneof_index].name if f.HasField('oneof_index') else '')
                for f in message.field
            }
            walk(name + '.', message.nested_type, message.enum_type)

    for file in schema.file:
        walk(file.package + '.', file.message_type, file.enum_type)
    return messages, enums


def validate(candidate, baseline):
    new_messages, new_enums = definitions(descriptors(candidate))
    old_messages, old_enums = definitions(descriptors(baseline))
    errors = []
    for name, fields in old_messages.items():
        current = new_messages.get(name)
        if current is None:
            errors.append(f'Removed message: {name}')
            continue
        for number, field in fields.items():
            if current.get(number) != field:
                errors.append(f'Removed or changed field: {name}.{field[0]} ({number})')
    for name, values in old_enums.items():
        for value, number in values.items():
            if new_enums.get(name, {}).get(value) != number:
                errors.append(f'Removed or changed enum value: {name}.{value}')
    if errors:
        raise ValueError('Schema needs manual compatibility review:\n' + '\n'.join(errors[:30]))
    return {
        'messages': len(new_messages),
        'added_messages': sorted(set(new_messages) - set(old_messages)),
        'added_fields': sum(len(set(fields) - set(old_messages.get(name, {})))
                            for name, fields in new_messages.items() if name in old_messages),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--baseline', required=True, type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = validate(args.candidate, args.baseline)
    text = json.dumps(report, indent=2) + '\n'
    if args.report:
        args.report.write_text(text)
    print(text, end='')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
