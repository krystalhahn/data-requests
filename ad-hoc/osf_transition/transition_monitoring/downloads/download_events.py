def get_download_events():
    import csv
    from tqdm import tqdm
    from django.db import connection
    from django.contrib.contenttypes.models import ContentType

    filename = "/tmp/download_events.csv"

    user_content_type_id = ContentType.objects.get_for_model(OSFUser).id
    abstractnode_content_type_id = ContentType.objects.get_for_model(AbstractNode).id

    with connection.cursor() as cursor:

        # get total number of download events for pbar
        cursor.execute("""
            SELECT COUNT(*)
            FROM osf_downloadevent;
        """)
        total = cursor.fetchone()[0]

        # get all download events and corresponding user/resource information
        cursor.execute("""
            SELECT
                de.*,
                ug._id AS user_guid,
                CASE
                    WHEN an.id IS NOT NULL THEN an.type
                    ELSE 'osf.preprint'
                END AS resource_type
            FROM osf_downloadevent de

            LEFT JOIN osf_osfuser u
                ON de.user_id = u.id

            LEFT JOIN osf_guid ug
                ON u.id = ug.object_id
                AND ug.content_type_id = %s

            LEFT JOIN osf_guid rg
                ON de.resource_guid = rg._id
                AND rg.content_type_id = %s

            LEFT JOIN osf_abstractnode an
                ON rg.object_id = an.id

            ORDER BY de.id;
        """, [
            user_content_type_id,
            abstractnode_content_type_id,
        ])

        # get column names
        fieldnames = [column[0] for column in cursor.description]

        with open(filename, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(fieldnames)

            # process rows in batches
            with tqdm(total=total, desc="Writing download events") as pbar:
                while True:
                    rows = cursor.fetchmany(10000)

                    if not rows:
                        break

                    writer.writerows(rows)
                    pbar.update(len(rows))

    print(f"Output written to {filename}")