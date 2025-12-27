# specify project GUID
# specify list of excluded_users GUIDs if necessary (ex. excluding OSF personnel)
def get_project_metrics(project_id, excluded_users=None):
    from osf.metrics import CountedAuthUsage
    import csv
    import io
    filename = '/tmp/project_metrics.csv'
    COL_HEADERS = ['project_name', 'component_name', 'component_guid', 'component_type', 'contributors', 'permissions']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()
    
    project = Node.objects.get(guids___id=project_id)
    
    excluded_users = list(OSFUser.objects.filter(guids___id__in=excluded_users).values_list('id', flat=True))

    for descendant in project.descendants.all():
        if excluded_users:
            # get contributors excluding the specified users
            contributors = descendant.contributors.exclude(id__in=excluded_users).distinct()
        else:
            contributors = descendant.contributors.distinct()

        # get permissions for each contributor
        permissions = [','.join(descendant.get_permissions(contributor)) for contributor in contributors]

        writer.writerow({
            'project_name': project.title,
            'component_name': descendant.title,
            'component_guid': descendant._id,
            'component_type': descendant.type,
            'contributors': list(contributors.values_list('guids___id', flat=True)),
            'permissions': permissions
        })

    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())