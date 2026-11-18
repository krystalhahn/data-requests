def export_nodes(
    output_path='/tmp/node_data.json', 
    batch_size=500,
    n=None
):
    import json
    import sys
    from django.contrib.contenttypes.models import ContentType
    from django.db.models import Max
    from osf.models import Node
    from tqdm import tqdm

    qs = Node.objects.filter(
        is_public=True,
        deleted__isnull=True
    ).exclude(spam_status__in=[1, 2]).order_by('pk')

    total = qs.count() if n is None else min(qs.count(), n)
    processed = 0

    with open(output_path, 'w', encoding='utf-8') as outfile, tqdm(
        total=total,
        desc='Exporting nodes',
        file=sys.stdout
    ) as pbar:

        outfile.write('[\n')
        first_record = True

        while True:
            limit = batch_size if n is None else min(batch_size, n - processed)

            if limit <= 0:
                break

            nodes = list(qs[processed:processed + limit])

            if not nodes:
                break

            for node in nodes:
                result = {
                    'id': node._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': node.title,
                        'description': node.description,
                        'category': node.category,
                        'custom_citation': getattr(node, 'custom_citation', None),
                        'date_created': node.created,
                        'date_modified': node.last_logged,
                        'registration': node.is_registration,
                        'preprint': False,
                        'fork': node.is_fork,
                        'collection': node.is_collection,
                        'tags': list(node.tags.values_list('name', flat=True)),
                        'public': node.is_public,
                        'subjects': [
                            [{'id': subject._id, 'text': subject.text}]
                            for subject in node.subjects.all()
                        ],
                    },
                }

                if not first_record:
                    outfile.write(',\n')

                json.dump(
                    result,
                    outfile,
                    indent=2,
                    default=str,
                    ensure_ascii=False
                )
                first_record = False

            processed += len(nodes)
            pbar.update(len(nodes))

        outfile.write('\n]\n')

    print(f'Export complete: {output_path}')