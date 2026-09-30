def get_osfi_project_components(osfi_id):
    import io
    import csv
    from tqdm import tqdm
    from django.db.models import Exists, OuterRef

    filename = f'/tmp/{osfi_id}_project_components.csv'
    COL_HEADERS = ['component_guid', 'project_guid', 'title', 'admin_user_names', 'admin_user_guids', 'date_created', 'date_modified', 'resource_type', 'license']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    osfi_projects = Institution.objects.get(_id=osfi_id).nodes

    pbar = tqdm(total = osfi_projects.count())

    for project in osfi_projects.all():

        for component in project.descendants.all():

            admin_users = [
                contributor
                for contributor in component.contributors
                if 'admin' in component.get_permissions(contributor)
            ]

            writer.writerow({
                'component_guid': component._id,
                'project_guid': project._id, 
                'title': component.title,
                'admin_user_names': [user.fullname for user in admin_users],
                'admin_user_guids': [user._id for user in admin_users],
                'date_created': component.created,
                'date_modified': component.modified,
                'resource_type': component.type,
                'license': component.node_license.name if component.node_license else None
            })

        pbar.update()

    pbar.close()

    with open(filename, 'w') as writeFile:
            writeFile.write(output.getvalue())

    print(f'Output written to {filename}')