def get_download_events():
    import csv
    from tqdm import tqdm
    from django.db import connection
    from django.contrib.contenttypes.models import ContentType

    filename = "/tmp/download_events.csv"

    user_content_type_id = ContentType.objects.get_for_model(OSFUser).id

    with connection.cursor() as cursor:

        # get total number of download events for pbar
        cursor.execute("""
            SELECT COUNT(*)
            FROM osf_downloadevent;
        """)
        total = cursor.fetchone()[0]

        # get all download events and corresponding user GUID
        cursor.execute("""
            SELECT
                de.*,
                g._id AS user_guid
            FROM osf_downloadevent de
            LEFT JOIN osf_osfuser u
                ON de.user_id = u.id
            LEFT JOIN osf_guid g
                ON u.id = g.object_id
                AND g.content_type_id = %s
            ORDER BY de.id;
        """, [user_content_type_id])

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