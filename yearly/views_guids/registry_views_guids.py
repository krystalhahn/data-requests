registries = ['dam', 'rwe', 'youthstudy']
    
def get_registry_guids(registries):
    import io
    import csv
    from tqdm import tqdm
    from django.db.models import Q

    filename = '/tmp/registry_guids_from_ctguid.csv'
    COL_HEADERS = ['registry', 'guid']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    target_rps = RegistrationProvider.objects.filter(_id__in=registries)

    guid_filter = Q()

    from django.apps import apps

    registry_models = []

    for model in apps.get_models():
        for field in model._meta.get_fields():
            if (
                field.name == "provider"
                and getattr(field, "is_relation", False)
                and field.related_model == RegistrationProvider
            ):
                registry_models.append(model)
                break

    for model in registry_models:
        ct = ContentType.objects.get_for_model(model)

        object_ids = model.objects.filter(
            provider__in=target_rps
        ).values("pk")

        guid_filter |= Q(
            content_type=ct,
            object_id__in=object_ids
        )

    rp_guids = Guid.objects.filter(guid_filter)

    pbar = tqdm(total = rp_guids.count())

    for guid in rp_guids:
        writer.writerow({
            'registry': guid.referent.provider._id,
            'guid': guid._id
        })
        pbar.update()

    pbar.close()
    
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")