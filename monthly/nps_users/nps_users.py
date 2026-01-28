# Optimized: Aggregates log entries to reduce memory overload
# Needs to be merged with output of write_nps_users_insts() in nps_users_institutions.py
def write_nps_users_csv(n=None):
    import io
    import csv
    from tqdm import tqdm
    from django.db.models import OuterRef, Subquery, F, Func, Max
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
