# Fetches NodeSettings for each node to get when a Boa addon was created, modified

import io
import csv
from tqdm import tqdm

from django.db.models import Prefetch
from osf.models import Node


def get_boa_addon_projects(n=None):
    filename = '/tmp/boa_addon_projects.csv'
    fieldnames = ['n._id', 'n.title', 'n.type', 'n.created', 'n.admin_contributors', 'boa_addon', 'addon_created', 'addon_modified', 'addon_deleted']
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()

    # prefetch related Boa addon settings
    qs = Node.objects.filter(deleted__isnull=True).exclude(spam_status__in=[1, 2]).prefetch_related(
        Prefetch('addons_boa_node_settings', queryset=NodeSettings.objects.only('created', 'modified', 'is_deleted'))
    )
    if n:
        qs = qs[:n]

    pbar = tqdm(total=qs.count())
    # for n in qs.exclude(addons_boa_node_settings__isnull=True).filter(addons_boa_node_settings__is_deleted__isnull=True):
    for n in qs:
        # get related Boa addon settings if available
        boa_settings = getattr(n, 'addons_boa_node_settings', None)
        writer.writerow({
            'n._id': n._id,
            'n.title': n.title,
            'n.type': n.type,
            'n.created': n.created,
            'n.admin_contributors': list(n.contributors.filter(admin_profile__isnull=False).distinct().values_list('guids___id', flat=True)),
            'boa_addon': True if boa_settings and not boa_settings.is_deleted else False,
            'addon_created': boa_settings.created.isoformat() if boa_settings else None,
            'addon_modified': boa_settings.modified.isoformat() if boa_settings else None,
            'addon_deleted': boa_settings.is_deleted if boa_settings else None
        })
        pbar.update()

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())