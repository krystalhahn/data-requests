def get_total_users_since_transition(backup_cutoff):
    import pytz
    from django.utils import timezone
    import time
    from django.db.models import Count, Q

    end_y, end_m, end_d = map(int, backup_cutoff.split("-"))
    end = timezone.datetime(end_y, end_m, end_d, tzinfo=pytz.utc)
    start = timezone.datetime(2026, 8, 9, tzinfo=pytz.utc)

    print("Counting users that have logged in since...")
    t0 = time.time()

    total_logged_in_users = OSFUser.objects.filter(
        date_last_login__gte=start,
        date_last_login__lt=end
    ).annotate(
        total_project_count=Count(
            "nodes",
            filter=Q(nodes__type="osf.node"),
            distinct=True
        ),
        private_project_count=Count(
            "nodes",
            filter=Q(
                nodes__type="osf.node",
                nodes__is_public=False
            ),
            distinct=True
        )
    )

    total_login_count = total_logged_in_users.count()

    print(f"Total users who logged in: {total_login_count} (took {time.time() - t0:.2f}s)")

    print("Counting total users by project count...")
    t0 = time.time()

    total_users = OSFUser.objects.filter(
        created__lt=end
    ).annotate(
        total_project_count=Count(
            "nodes",
            filter=Q(nodes__type="osf.node"),
            distinct=True
        ),
        private_project_count=Count(
            "nodes",
            filter=Q(
                nodes__type="osf.node",
                nodes__is_public=False
            ),
            distinct=True
        )
    )

    print(f"Total users with projects: {total_users.filter(total_project_count__gt=0).count()}")
    print(f"Total users with >5 projects: {total_users.filter(total_project_count__gt=5).count()}")
    print(f"Total users with private projects: {total_users.filter(private_project_count__gt=0).count()}")
    print(f"Total users with >5 private projects: {total_users.filter(private_project_count__gt=5).count()} (took {time.time() - t0:.2f}s)")

    print("Calculating logged-in user percentages...")
    t0 = time.time()

    logged_in_any_projects = total_logged_in_users.filter(
        total_project_count__gt=0
    ).count()
    total_any_projects = total_users.filter(
        total_project_count__gt=0
    ).count()

    logged_in_more_than_5_projects = total_logged_in_users.filter(
        total_project_count__gt=5
    ).count()
    total_more_than_5_projects = total_users.filter(
        total_project_count__gt=5
    ).count()

    logged_in_any_private_projects = total_logged_in_users.filter(
        private_project_count__gt=0
    ).count()
    total_any_private_projects = total_users.filter(
        private_project_count__gt=0
    ).count()

    logged_in_more_than_5_private_projects = total_logged_in_users.filter(
        private_project_count__gt=5
    ).count()
    total_more_than_5_private_projects = total_users.filter(
        private_project_count__gt=5
    ).count()

    print(
        f">0 projects: {logged_in_any_projects} / "
        f"{total_any_projects} = "
        f"{logged_in_any_projects / total_any_projects * 100:.2f}%"
    )
    print(
        f">5 projects: {logged_in_more_than_5_projects} / "
        f"{total_more_than_5_projects} = "
        f"{logged_in_more_than_5_projects / total_more_than_5_projects * 100:.2f}%"
    )
    print(
        f">0 private projects: {logged_in_any_private_projects} / "
        f"{total_any_private_projects} = "
        f"{logged_in_any_private_projects / total_any_private_projects * 100:.2f}%"
    )
    print(
        f">5 private projects: {logged_in_more_than_5_private_projects} / "
        f"{total_more_than_5_private_projects} = "
        f"{logged_in_more_than_5_private_projects / total_more_than_5_private_projects * 100:.2f}%"
        f" (took {time.time() - t0:.2f}s)"
    )

def get_admin_users_since_transition(backup_cutoff):
    import pytz
    import time
    from django.utils import timezone
    from tqdm import tqdm

    end_y, end_m, end_d = map(int, backup_cutoff.split("-"))
    end = timezone.datetime(end_y, end_m, end_d, tzinfo=pytz.utc)
    start = timezone.datetime(2026, 8, 9, tzinfo=pytz.utc)

    print("Counting admin users that have logged in since...")
    t0 = time.time()

    logged_in_users = OSFUser.objects.filter(
        date_last_login__gte=start,
        date_last_login__lt=end
    )

    users_any_admin_projects = 0
    users_more_than_5_admin_projects = 0
    users_any_private_admin_projects = 0
    users_more_than_5_private_admin_projects = 0

    pbar = tqdm(total=logged_in_users.count())

    for user in logged_in_users.iterator(chunk_size=1000):
        nodes = Node.objects.filter(
            _contributors=user,
            type="osf.node"
        ).only(
            "id",
            "is_public"
        )

        admin_project_count = 0
        private_admin_project_count = 0

        for node in nodes:
            permissions = node.get_permissions(user)

            if "admin" in permissions:
                admin_project_count += 1

                if not node.is_public:
                    private_admin_project_count += 1

        if admin_project_count > 0:
            users_any_admin_projects += 1

        if admin_project_count > 5:
            users_more_than_5_admin_projects += 1

        if private_admin_project_count > 0:
            users_any_private_admin_projects += 1

        if private_admin_project_count > 5:
            users_more_than_5_private_admin_projects += 1

        pbar.update(1)

    pbar.close()

    print(f"Logged-in users with >0 admin projects: {users_any_admin_projects}")
    print(f"Logged-in users with >5 admin projects: {users_more_than_5_admin_projects}")
    print(f"Logged-in users with >0 private admin projects: {users_any_private_admin_projects}")
    print(f"Logged-in users with >5 private admin projects: {users_more_than_5_private_admin_projects}")
    print(f"(took {time.time() - t0:.2f}s)")

    print("Counting total users by admin project count...")
    t0 = time.time()

    total_users = OSFUser.objects.filter(
        created__lt=end
    )

    total_any_admin_projects = 0
    total_more_than_5_admin_projects = 0
    total_any_private_admin_projects = 0
    total_more_than_5_private_admin_projects = 0

    pbar = tqdm(total=total_users.count())

    for user in total_users.iterator(chunk_size=1000):
        nodes = Node.objects.filter(
            _contributors=user,
            type="osf.node"
        ).only(
            "id",
            "is_public"
        )

        admin_project_count = 0
        private_admin_project_count = 0

        for node in nodes:
            permissions = node.get_permissions(user)

            if "admin" in permissions:
                admin_project_count += 1

                if not node.is_public:
                    private_admin_project_count += 1

        if admin_project_count > 0:
            total_any_admin_projects += 1

        if admin_project_count > 5:
            total_more_than_5_admin_projects += 1

        if private_admin_project_count > 0:
            total_any_private_admin_projects += 1

        if private_admin_project_count > 5:
            total_more_than_5_private_admin_projects += 1

        pbar.update(1)

    pbar.close()

    print(f"Total users with >0 admin projects: {total_any_admin_projects}")
    print(f"Total users with >5 admin projects: {total_more_than_5_admin_projects}")
    print(f"Total users with >0 private admin projects: {total_any_private_admin_projects}")
    print(f"Total users with >5 private admin projects: {total_more_than_5_private_admin_projects}")
    print(f"(took {time.time() - t0:.2f}s)")

    print("Calculating logged-in user percentages...")
    t0 = time.time()

    print(
        f">0 admin projects: {users_any_admin_projects} / "
        f"{total_any_admin_projects} = "
        f"{users_any_admin_projects / total_any_admin_projects * 100:.2f}%"
    )

    print(
        f">5 admin projects: {users_more_than_5_admin_projects} / "
        f"{total_more_than_5_admin_projects} = "
        f"{users_more_than_5_admin_projects / total_more_than_5_admin_projects * 100:.2f}%"
    )

    print(
        f">0 private admin projects: {users_any_private_admin_projects} / "
        f"{total_any_private_admin_projects} = "
        f"{users_any_private_admin_projects / total_any_private_admin_projects * 100:.2f}%"
    )

    print(
        f">5 private admin projects: {users_more_than_5_private_admin_projects} / "
        f"{total_more_than_5_private_admin_projects} = "
        f"{users_more_than_5_private_admin_projects / total_more_than_5_private_admin_projects * 100:.2f}%"
        f" (took {time.time() - t0:.2f}s)"
    )