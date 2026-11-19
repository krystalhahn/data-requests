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
    web_base = 'https://osf.io'

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

                nid = node._id

                # serialize datetimes
                created = node.created.isoformat().replace('+00:00', '') if node.created else None
                modified = node.last_logged.isoformat().replace('+00:00', '') if node.last_logged else None

                # build subject taxonomy for subjects selected
                node_subject_rows = list(node.subjects.all())
                subject_parent_ids = {
                    row.parent_id for row in node_subject_rows
                    if row.parent_id is not None
                }
                node_subjects = []
                for subject in node_subject_rows:
                    if subject.pk in subject_parent_ids:
                        continue
                    subject_path = []
                    current = subject_lookup.get(subject.pk)
                    while current:
                        subject_path.append({
                            'id': current['id'],
                            'text': current['text'],
                        })
                        current = subject_lookup.get(current['parent_id'])
                    node_subjects.append(list(reversed(subject_path)))

                attributes = {
                        'title': node.title,
                        'description': node.description,
                        'category': node.category,
                        'custom_citation': getattr(node, 'custom_citation', None),
                        'date_created': created,
                        'date_modified': modified,
                        'registration': node.is_registration,
                        'preprint': node.pk in preprint_node_ids,
                        'fork': node.is_fork,
                        'collection': node.is_collection,
                        'tags': list(node.tags.values_list('name', flat=True)),
                        'access_requests_enabled': getattr(node, 'access_requests_enabled', True),
                        'node_license': None,
                        'analytics_key': getattr(node, 'analytics_key', '') or '',
                        'current_user_can_comment': False,
                        'current_user_permissions': ['read'],
                        'current_user_is_contributor': False,
                        'current_user_is_contributor_or_group_member': False,
                        'wiki_enabled': False,
                        'public': node.is_public,
                        'subjects': node_subjects,
                    }

                relationships = {
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
                }

                license_obj = node.license.node_license if node.license else None
                license_id = getattr(license_obj, '_id', str(license_obj.pk)) if license_obj else None
                if license_id:
                    relationships['license'] = {
                        'links': {'related': {'href': f'{api_base}/licenses/{license_id}/', 'meta': {}}},
                        'data': {'id': license_id, 'type': 'licenses'},
                    }

                embeds = {}
                if license_obj:
                    embeds['license'] = {
                        'data': {
                            'id': license_id,
                            'type': 'licenses',
                            'attributes': {
                                'name': license_obj.name,
                                'text': license_obj.text,
                                'url': license_obj.url,
                                'required_fields': [],
                            },
                            'links': {'self': f'{api_base}/licenses/{license_id}/'},
                        }
                    }

                institution_data = []
                
                for institution in node.affiliated_institutions.all():
                    institution_url = f'{web_base}/institutions/{institution._id}/'
                    institution_assets = {}
                    for asset in institution.asset_files.all():
                        asset_name = asset.name
                        if asset_name == 'logo_rounded_corners':
                            asset_name = 'logo_rounded'
                        asset_url = asset.file.url
                        if asset_url.startswith('http://localhost:5000'):
                            asset_url = (
                                'https://storage.googleapis.com/'
                                f'cos-osf-prod-cdn-us/{asset.file.name}'
                            )
                        institution_assets[asset_name] = asset_url

                    institution_iris = [
                        iri.replace('http://localhost:5000', web_base)
                        for iri in institution.get_semantic_iris()
                    ]
                    institution_data.append({
                        'id': institution._id,
                        'type': 'institutions',
                        'attributes': {
                            'name': institution.name,
                            'sso_availability': institution.sso_availability,
                            'description': institution.description,
                            'iri': institution.identifier_domain,
                            'ror_iri': institution.ror_uri,
                            'iris': institution_iris,
                            'assets': institution_assets,
                            'institutional_request_access_enabled':
                                institution.institutional_request_access_enabled,
                            'logo_path': institution_assets.get('logo'),
                        },
                        'relationships': {
                            'nodes': {'links': {'related': {
                                'href': f'{api_base}/institutions/{institution._id}/nodes/',
                                'meta': {},
                            }}},
                            'registrations': {'links': {'related': {
                                'href': f'{api_base}/institutions/{institution._id}/registrations/',
                                'meta': {},
                            }}},
                            'users': {'links': {'related': {
                                'href': f'{api_base}/institutions/{institution._id}/users/',
                                'meta': {},
                            }}},
                        },
                        'links': {
                            'self': f'{api_base}/institutions/{institution._id}/',
                            'html': institution_url,
                            'iri': institution.ror_uri,
                        },
                    })

                embeds['affiliated_institutions'] = {
                    'data': institution_data,
                    '_count': len(institution_data),
                    '_complete': True,
                }

                result = {
                    'id': nid,
                    'type': 'nodes',
                    'attributes': attributes,
                    'relationships': relationships,
                    'embeds': embeds,
                    'links': {
                        'self': f'{api_base}/nodes/{nid}/',
                        'html': f'{web_base}/{nid}/',
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