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

    api_base = 'https://api.osf.io/v2'

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
                        'date_created': (
                            node.created.isoformat().replace('+00:00', '')
                            if node.created else None
                        ),
                        'date_modified': (
                            node.last_logged.isoformat().replace('+00:00', '')
                            if node.last_logged else None
                        ),
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
                    'relationships': {
                        'children': {
                            'links': {
                                'related': {
                                    'href': f'{api_base}/nodes/{nid}/children/',
                                    'meta': {}
                                }
                            }
                        },
                        'comments': {
                            'links': {
                                'related': {
                                    'href': f'{api_base}/nodes/{nid}/comments/?filter%5Btarget%5D={nid}',
                                    'meta': {}
                                }
                            }
                        },
                        'contributors': {
                            'links': {
                                'related': {
                                    'href': f'{api_base}/nodes/{nid}/contributors/',
                                    'meta': {}
                                }
                            }
                        },
                        'bibliographic_contributors': {
                            'links': {
                                'related': {
                                    'href': f'{api_base}/nodes/{nid}/bibliographic_contributors/',
                                    'meta': {}
                                }
                            }
                        },
                        'files': {
                            'links': {
                                'related': {
                                    'href': f'{api_base}/nodes/{nid}/files/',
                                    'meta': {}
                                }
                            }
                        },
                        'settings': {
                            'links': {
                                'related': {
                                    'href': f'{api_base}/nodes/{nid}/settings/',
                                    'meta': {}
                                }
                            },
                            'data': {
                                'id': nid,
                                'type': 'node-setting'
                            }
                        },
                        'registrations': {
                            'links': {
                                'related': {
                                    'href': f'{api_base}/nodes/{nid}/registrations/',
                                    'meta': {}
                                }
                            }
                        },
                        'identifiers': {
                            'links': {
                                'related': {
                                    'href': f'{api_base}/nodes/{nid}/identifiers/',
                                    'meta': {}
                                }
                            }
                        },
                        'affiliated_institutions': {
                            'links': {
                                'related': {
                                    'href': f'{api_base}/nodes/{nid}/institutions/',
                                    'meta': {}
                                }
                            }
                        },
                        'region': {
                            'links': {
                                'related': {
                                    'href': f'{api_base}/nodes/{nid}/region/',
                                    'meta': {}
                                }
                            }
                        },
                        'root': {
                            'links': {
                                'related': {
                                    'href': f'{api_base}/nodes/{node.root._id}/',
                                    'meta': {}
                                }
                            },
                            'data': {
                                'id': node.root._id,
                                'type': 'nodes'
                            }
                        },
                        'citation': {
                            'links': {
                                'related': {
                                    'href': f'{api_base}/nodes/{nid}/citation/',
                                    'meta': {}
                                }
                            },
                            'data': {
                                'id': nid,
                                'type': 'citation'
                            }
                        },
                        'storage': {
                            'links': {
                                'related': {
                                    'href': f'{api_base}/nodes/{nid}/storage/',
                                    'meta': {}
                                }
                            },
                            'data': {
                                'id': nid,
                                'type': 'node-storage'
                            }
                        },
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