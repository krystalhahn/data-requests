# Differentiating between all nodes and non-deleted nodes (resolves discrepancy)
# Total, not only for the quarter
def get_regional_storage_metrics_for_insts(iids=None):
    import csv
    import io
    from tqdm import tqdm

    filename = f'/tmp/regional_storage_metrics.csv'
    COL_HEADERS = ['institution.name', 'region.name', 'public_nodes_all', 'private_nodes_all', 'public_storage_all', 'private_storage_all', 'public_nodes', 'private_nodes', 'public_storage', 'private_storage']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    if not iids:
        target_insts = list(Institution.objects.all())
    elif isinstance(iids, str):
        i = Institution.load(inst)
        if not i:
            print(f'Unable to find Inst {iids}')
            return
        target_insts = [i]
    elif isinstance(iids, list):
        target_insts = list(Institution.objects.filter(_id__in=iids))
    else:
        print(f'Unable to parse iids {iids}')
        return
    
    pbar = tqdm(total=len(target_insts))

    for i in target_insts:
        for r in Region.objects.all():
            ns = i.nodes.filter(addons_osfstorage_node_settings__region=r).exclude(spam_status=2)
            domain_metrics = {
                'institution.name': i.name,
                'region.name': r.name,
                'public_nodes_all': ns.filter(is_public=True).count(),
                'private_nodes_all': ns.filter(is_public=False).count(),
                'public_storage_all': sum([sum([s for s in n.files.values_list('versions__size', flat=True) if isinstance(s, int)]) for n in ns.filter(is_public=True)]),
                'private_storage_all': sum([sum([s for s in n.files.values_list('versions__size', flat=True) if isinstance(s, int)]) for n in ns.filter(is_public=False)]),
                # excluding deleted
                'public_nodes': ns.filter(is_public=True, deleted__isnull=True).count(),
                'private_nodes': ns.filter(is_public=False, deleted__isnull=True).count(),
                'public_storage': sum([sum([s for s in n.files.values_list('versions__size', flat=True) if isinstance(s, int)]) for n in ns.filter(is_public=True, deleted__isnull=True)]),
                'private_storage': sum([sum([s for s in n.files.values_list('versions__size', flat=True) if isinstance(s, int)]) for n in ns.filter(is_public=False, deleted__isnull=True)])
            }
            # skip if public_nodes_all and private_nodes_all are 0, in case there are deleted nodes in a regions
            if domain_metrics.get('public_nodes_all', 0) or domain_metrics.get('private_nodes_all', 0):
                writer.writerow(domain_metrics)
        pbar.update(1)

    pbar.close()
    
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")