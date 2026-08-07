import csv
from functools import wraps
import sys
import time

from django.db.models import OuterRef, Q, Subquery, F, Func, Max, Value
import io
from tqdm import tqdm


def timeit(func):
    """Decorator to measure the execution time of a function (in minutes)."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        elapsed = end - start
        print(f"Function '{func.__name__}' executed in {elapsed / 60:.2f} mins")
        return result

    return wrapper


@timeit
def get_content_subjects(include_spam=True, n=None):
    from osf.models import Subject, Node, Registration, Preprint

    filename = f"/tmp/content_subjects{'_nonspam' if not include_spam else ''}.csv"
    fieldnames = [
        "subject",
        "public_projects",
        "private_projects",
        "public_registrations",
        "withdrawn_registrations",
        "embargoed_registrations",
        "published_preprints",
        "withdrawn_preprints",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()

    # top level of bepress taxonomy
    subject_names = [
        "Architecture",
        "Arts and Humanities",
        "Business",
        "Education",
        "Engineering",
        "Law",
        "Life Sciences",
        "Medicine and Health Sciences",
        "Physical Sciences and Mathematics",
        "Social and Behavioral Sciences",
    ]

    pbar = tqdm(total=len(subject_names))

    # spam filter
    spam_filter = Q() if include_spam else ~Q(spam_status__in=[1, 2])

    for subject in subject_names:
        subject_objs = Subject.objects.filter(text=subject)

        writer.writerow(
            {
                "subject": subject,
                "public_projects": Node.objects.filter(
                    subjects__in=subject_objs, is_public=True, deleted__isnull=True
                )
                .filter(spam_filter)
                .distinct()
                .count(),
                "private_projects": Node.objects.filter(
                    subjects__in=subject_objs, is_public=False, deleted__isnull=True
                )
                .filter(spam_filter)
                .distinct()
                .count(),
                "public_registrations": Registration.objects.filter(
                    subjects__in=subject_objs, is_public=True, deleted__isnull=True
                )
                .exclude(retraction__state="approved")
                .filter(spam_filter)
                .distinct()
                .count(),
                "withdrawn_registrations": Registration.objects.filter(
                    subjects__in=subject_objs,
                    is_public=True,
                    deleted__isnull=True,
                    retraction__state="approved",
                )
                .filter(spam_filter)
                .distinct()
                .count(),
                "embargoed_registrations": Registration.objects.filter(
                    subjects__in=subject_objs,
                    is_public=False,
                    deleted__isnull=True,
                    embargo__state="approved",
                )
                .filter(spam_filter)
                .distinct()
                .count(),
                "published_preprints": Preprint.objects.filter(
                    subjects__in=subject_objs,
                    is_public=True,
                    is_published=True,
                    deleted__isnull=True,
                )
                .exclude(machine_state="withdrawn")
                .filter(spam_filter)
                .distinct()
                .count(),
                "withdrawn_preprints": Preprint.objects.filter(
                    subjects__in=subject_objs,
                    is_public=True,
                    is_published=True,
                    deleted__isnull=True,
                    machine_state="withdrawn",
                )
                .filter(spam_filter)
                .distinct()
                .count(),
            }
        )

        pbar.update(1)
    pbar.close()

    with open(filename, "w") as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")


@timeit
def generate_cedar_metadata_csv():
    from osf.models import CedarMetadataRecord
    from osf.utils.outcomes import ArtifactTypes

    filename = "/tmp/cedar_metadata.csv"
    COL_HEADERS = [
        "community_schema",
        "type",
        "resourceType",
        "deleted",
        "guid",
        "title",
        "created",
        "subjects",
        "institutions",
        "hasConnectedResource",
        "visible_contributors",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    # fetch all CedarMetadataRecord objects
    qs = CedarMetadataRecord.objects.all()

    pbar = tqdm(total=qs.count())

    for cmr in qs:
        # retrieve the GUID associated with the CedarMetadataRecord
        guid = cmr.guid

        # retrieve the associated GuidMetadataRecord through the metadata_record field
        gmr = getattr(guid, "metadata_record", None)

        # retrieve the referent associated with the GUID
        ref = guid.referent

        # skip records based on privacy or publication status
        if hasattr(ref, "is_public") and not ref.is_public:
            continue
        if ref.type == "osf.preprint" and not ref.is_published:
            continue
        if "file" in ref.type and not ref.target.is_public:
            continue

        # retrieve identifiers and artifacts
        idents = (
            ref.identifiers.all()
            if "file" not in ref.type
            else ref.target.identifiers.all()
        )
        partifacts = sum(
            [
                list(
                    i.artifact_metadata.filter(
                        artifact_type=ArtifactTypes.PRIMARY.value
                    )
                )
                for i in idents
            ],
            [],
        )
        outcomes = [pa.outcome for pa in partifacts]

        # check for connected resources
        has_artifacts = any(
            o.artifact_metadata.exclude(artifact_type=ArtifactTypes.PRIMARY.value)
            .filter(finalized=True, deleted__isnull=True)
            .exists()
            for o in outcomes
        )

        writer.writerow(
            {
                "community_schema": cmr.template.schema_name,
                "type": ref.type,
                "resourceType": getattr(gmr, "resource_type_general", None),
                "deleted": ref.is_deleted,
                "guid": guid._id,
                "title": getattr(ref, "title", None) or getattr(ref, "name", None),
                "created": ref.created,
                "subjects": list(ref.subjects.values_list("text", flat=True))
                if hasattr(ref, "subjects")
                else [],
                "institutions": list(
                    ref.affiliated_institutions.values_list("name", flat=True)
                )
                if hasattr(ref, "affiliated_institutions")
                else [],
                "hasConnectedResource": has_artifacts,
                "visible_contributors": list(
                    ref.contributor_set.filter(visible=True).values_list(
                        "user__guids___id", flat=True
                    )
                )
                if hasattr(ref, "contributor_set")
                else [],
            }
        )

        pbar.update(1)
    pbar.close()

    with open(filename, "w") as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")


@timeit
def generate_funder_metadata_csv(mapping_path=mapping_path):
    from osf.models import GuidMetadataRecord
    from osf.utils.outcomes import ArtifactTypes

    funder_map = {}
    with open(mapping_path, newline='\r\n') as mapfile:
        mapreader = csv.reader(mapfile, delimiter=',', quotechar='"')
        for row in mapreader:
            funder_map[row[0]] = row[1]

    filename = "/tmp/funder_metadata.csv"
    COL_HEADERS = [
        "funder",
        "type",
        "resourceType",
        "guid",
        "title",
        "created",
        "subjects",
        "institutions",
        "hasConnectedResource",
        "visible_contributors",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    qs = GuidMetadataRecord.objects.exclude(funding_info=[])

    pbar = tqdm(total=qs.count())

    for gmr in qs:
        ref = gmr.guid.referent
        if hasattr(ref, "is_public") and not ref.is_public:
            continue
        if ref.type == "osf.preprint" and not ref.is_published:
            continue
        if "file" in ref.type and not ref.target.is_public:
            continue

        idents = (
            ref.identifiers.all()
            if "file" not in ref.type
            else ref.target.identifiers.all()
        )
        partifacts = sum(
            [
                list(
                    i.artifact_metadata.filter(
                        artifact_type=ArtifactTypes.PRIMARY.value
                    )
                )
                for i in idents
            ],
            [],
        )
        outcomes = [pa.outcome for pa in partifacts]
        has_artifacts = any(
            [
                o.artifact_metadata.exclude(artifact_type=ArtifactTypes.PRIMARY.value)
                .filter(finalized=True, deleted__isnull=True)
                .exists()
                for o in outcomes
            ]
        )

        for fund_dict in gmr.funding_info:
            
            funder_id_type = fund_dict['funder_identifier_type']
            funder_id = fund_dict['funder_identifier']
            funder_name = fund_dict['funder_name']
            if funder_id_type == 'ROR' and funder_id in funder_map:
                funder_name = funder_map[funder_id]

            writer.writerow(
                {
                    "funder": fund_dict["funder_name"],
                    "type": ref.type,
                    "resourceType": gmr.resource_type_general,
                    "guid": gmr.guid._id,
                    "title": getattr(ref, "title", None) or getattr(ref, "name", None),
                    "created": ref.created,
                    "subjects": list(ref.subjects.values_list("text", flat=True))
                    if hasattr(ref, "subjects")
                    else [],
                    "institutions": list(
                        ref.affiliated_institutions.values_list("name", flat=True)
                    )
                    if hasattr(ref, "affiliated_institutions")
                    else [],
                    "hasConnectedResource": has_artifacts,
                    "visible_contributors": list(
                        ref.contributor_set.filter(visible=True).values_list(
                            "user__guids___id", flat=True
                        )
                    )
                    if hasattr(ref, "contributor_set")
                    else [],
                }
            )

        pbar.update(1)
    pbar.close()

    with open(filename, "w") as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")


@timeit
# Optimized: Aggregates log entries to reduce memory overload
# Needs to be merged with output of write_nps_users_insts() in nps_users_institutions.py
def write_nps_users_csv(n=None):
    import io
    import csv
    from tqdm import tqdm

    from osf.models import OSFUser, Node, Registration, Preprint, NodeLog, PreprintLog

    filename = "/tmp/nps_users.csv"
    fieldnames = [
        "u._id",
        "u.username",
        "u.date_confirmed",
        "u.date_last_login",
        "u.date_last_action",
        "public_projects_created",
        "private_projects_created",
        "public_registrations_created",
        "withdrawn_registrations_created",
        "embargoed_registrations_created",
        "published_preprints_created",
        "withdrawn_preprints_created",
        "public_projects_contributor",
        "private_projects_contributor",
        "public_registrations_contributor",
        "withdrawn_registrations_contributor",
        "embargoed_registrations_contributor",
        "published_preprints_contributor",
        "withdrawn_preprints_contributor",
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()

    # aggregate logs once (one row per user, not per log)
    print("Aggregating NodeLog last actions...")
    node_last = dict(
        NodeLog.objects.values("user_id")
        .annotate(last=Max("created"))
        .values_list("user_id", "last")
    )

    print("Aggregating PreprintLog last actions...")
    preprint_last = dict(
        PreprintLog.objects.values("user_id")
        .annotate(last=Max("created"))
        .values_list("user_id", "last")
    )

    # subqueries for project/registration/preprint counts based on creators and contributors
    def count_subq(qs):
        return qs.annotate(count=Func(F("id"), function="Count")).values("count")

    pubn_subq_created = count_subq(
        Node.objects.filter(
            creator_id=OuterRef("pk"), is_public=True, deleted__isnull=True
        )
    )
    privn_subq_created = count_subq(
        Node.objects.filter(
            creator_id=OuterRef("pk"), is_public=False, deleted__isnull=True
        )
    )
    pubr_subq_created = count_subq(
        Registration.objects.filter(
            creator_id=OuterRef("pk"), is_public=True, deleted__isnull=True
        ).exclude(retraction__state="approved")
    )
    withr_subq_created = count_subq(
        Registration.objects.filter(
            creator_id=OuterRef("pk"),
            is_public=True,
            deleted__isnull=True,
            retraction__state="approved",
        )
    )
    embr_subq_created = count_subq(
        Registration.objects.filter(
            creator_id=OuterRef("pk"),
            is_public=False,
            deleted__isnull=True,
            embargo__state="approved",
        )
    )
    pubp_subq_created = count_subq(
        Preprint.objects.filter(
            creator_id=OuterRef("pk"),
            is_public=True,
            is_published=True,
            deleted__isnull=True,
        ).exclude(machine_state="withdrawn")
    )
    withp_subq_created = count_subq(
        Preprint.objects.filter(
            creator_id=OuterRef("pk"),
            is_public=True,
            is_published=True,
            deleted__isnull=True,
            machine_state="withdrawn",
        )
    )
    pubn_subq_contributor = count_subq(
        Node.objects.filter(
            _contributors=OuterRef("pk"), is_public=True, deleted__isnull=True
        )
    )
    privn_subq_contributor = count_subq(
        Node.objects.filter(
            _contributors=OuterRef("pk"), is_public=False, deleted__isnull=True
        )
    )
    pubr_subq_contributor = count_subq(
        Registration.objects.filter(
            _contributors=OuterRef("pk"), is_public=True, deleted__isnull=True
        ).exclude(retraction__state="approved")
    )
    withr_subq_contributor = count_subq(
        Registration.objects.filter(
            _contributors=OuterRef("pk"),
            is_public=True,
            deleted__isnull=True,
            retraction__state="approved",
        )
    )
    embr_subq_contributor = count_subq(
        Registration.objects.filter(
            _contributors=OuterRef("pk"),
            is_public=False,
            deleted__isnull=True,
            embargo__state="approved",
        )
    )
    pubp_subq_contributor = count_subq(
        Preprint.objects.filter(
            _contributors=OuterRef("pk"),
            is_public=True,
            is_published=True,
            deleted__isnull=True,
        ).exclude(machine_state="withdrawn")
    )
    withp_subq_contributor = count_subq(
        Preprint.objects.filter(
            _contributors=OuterRef("pk"),
            is_public=True,
            is_published=True,
            deleted__isnull=True,
            machine_state="withdrawn",
        )
    )

    # main queryset
    qs = (
        OSFUser.objects.filter(is_active=True)
        .exclude(spam_status__in=[1, 2])
        .annotate(
            public_projects_created=Subquery(pubn_subq_created),
            private_projects_created=Subquery(privn_subq_created),
            public_registrations_created=Subquery(pubr_subq_created),
            withdrawn_registrations_created=Subquery(withr_subq_created),
            embargoed_registrations_created=Subquery(embr_subq_created),
            published_preprints_created=Subquery(pubp_subq_created),
            withdrawn_preprints_created=Subquery(withp_subq_created),
            public_projects_contributor=Subquery(pubn_subq_contributor),
            private_projects_contributor=Subquery(privn_subq_contributor),
            public_registrations_contributor=Subquery(pubr_subq_contributor),
            withdrawn_registrations_contributor=Subquery(withr_subq_contributor),
            embargoed_registrations_contributor=Subquery(embr_subq_contributor),
            published_preprints_contributor=Subquery(pubp_subq_contributor),
            withdrawn_preprints_contributor=Subquery(withp_subq_contributor),
        )
    )

    if n:
        qs = qs[:n]

    total = qs.count()
    pbar = tqdm(total=total)

    # streaming write (no per-row DB hits)
    for u in qs.values(
        "id",
        "guids___id",
        "username",
        "date_confirmed",
        "date_last_login",
        "public_projects_created",
        "private_projects_created",
        "public_registrations_created",
        "withdrawn_registrations_created",
        "embargoed_registrations_created",
        "published_preprints_created",
        "withdrawn_preprints_created",
        "public_projects_contributor",
        "private_projects_contributor",
        "public_registrations_contributor",
        "withdrawn_registrations_contributor",
        "embargoed_registrations_contributor",
        "published_preprints_contributor",
        "withdrawn_preprints_contributor",
    ).iterator(chunk_size=1000):
        uid = u["id"]

        last_action = max(
            filter(None, [node_last.get(uid), preprint_last.get(uid)]), default=None
        )

        row = {
            "u._id": u["guids___id"],
            "u.username": u["username"],
            "u.date_confirmed": u["date_confirmed"].date().isoformat()
            if u["date_confirmed"]
            else None,
            "u.date_last_login": u["date_last_login"].date().isoformat()
            if u["date_last_login"]
            else None,
            "u.date_last_action": last_action.date().isoformat()
            if last_action
            else None,
            **{k: u.get(k) for k in fieldnames if k in u},
        }

        writer.writerow(row)
        pbar.update()

    pbar.close()

    with open(filename, "w") as f:
        f.write(output.getvalue())

    print(f"Output written to {filename}")


@timeit
def write_nps_users_insts(n=None):
    from osf.models import OSFUser, Institution

    filename = "/tmp/nps_users_insts.csv"
    fieldnames = ["u._id", "u.username", "institution_name"]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames)
    writer.writeheader()

    insts = Institution.objects.all()

    pbar = tqdm(total=insts.count())

    for i in insts:
        qs = (
            OSFUser.objects.filter(
                institutionaffiliation__institution__id=i.id, is_active=True
            )
            .exclude(spam_status__in=[1, 2])
            .annotate(institution_name=Value(i.name))
        )

        if n:
            qs = qs[:n]

        for udict in qs.values("guids___id", "username", "institution_name"):
            udict["u._id"] = udict.pop("guids___id")
            udict["u.username"] = udict.pop("username")
            udict["institution_name"] = udict.pop("institution_name")

            writer.writerow(udict)

        pbar.update(1)
    pbar.close()

    with open(filename, "w") as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")


@timeit
def main():
    print("Starting monthly data extraction...\n")

    print("Generating content subjects CSV (including spam)...")
    get_content_subjects(include_spam=True)

    print("\nGenerating content subjects CSV (excluding spam)...")
    get_content_subjects(include_spam=False)
    
    print("\nGenerating CEDAR metadata CSV...")
    generate_cedar_metadata_csv()

    print("\nGenerating funder metadata CSV...")
    generate_funder_metadata_csv(mapping_path)

    print("\nGenerating NPS users CSV...")
    write_nps_users_csv()

    print("\nGenerating NPS users institutions CSV...")
    write_nps_users_insts()

    print("\nMonthly data extraction completed.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted!")
