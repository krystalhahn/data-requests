# pass kwarg to exclude system logs
def get_gfs_regs_with_active_nodes(exclude_system_logs=False):
    import csv
    import io
    from django.utils import timezone
    import datetime
    from tqdm import tqdm

    filename = '/tmp/gfs_regs_with_active_nodes.csv'
    COL_HEADERS = ['reg_id', 'reg_is_public', 'reg_moderation_state', 'reg_embargo_state', 'linked_node_id', 'linked_node_is_public', 'node_is_active_3_mo', 'node_is_active_1_yr']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    now = timezone.now()
    three_mo_ago = now - datetime.timedelta(days=90)
    one_yr_ago = now - datetime.timedelta(days=365)

    gfs_regs = Registration.objects.filter(provider___id="gfs")

    pbar = tqdm(total = gfs_regs.count())

    for reg in gfs_regs:
        
        linked_node = reg.registered_from

        if linked_node:
            logs = linked_node.logs.all()
            if exclude_system_logs:
                logs = logs.filter(user__isnull=False)
            latest_log = logs.order_by('-created').first()
        else:
            latest_log = None

        writer.writerow({
            'reg_id': reg._id,
            'reg_is_public': reg.is_public,
            'reg_moderation_state': reg.moderation_state,
            'reg_embargo_state': reg.embargo.state if reg.embargo else None,
            'linked_node_id': linked_node._id if linked_node else None,
            'linked_node_is_public': linked_node.is_public if linked_node else None,
            'node_is_active_3_mo': latest_log.created >= three_mo_ago if latest_log else None,
            'node_is_active_1_yr': latest_log.created >= one_yr_ago if latest_log else None
        })
        pbar.update()

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")
