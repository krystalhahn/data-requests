def get_download_events():
    import csv
    from tqdm import tqdm
    from django.db import connection

    filename = "/tmp/download_events.csv"

    with connection.cursor() as cursor:

        # get total number of download events for pbar
        cursor.execute("""
            SELECT COUNT(*)
            FROM osf_downloadevent;
        """)
        total = cursor.fetchone()[0]

        # get all download events
        cursor.execute("""
            SELECT *
            FROM osf_downloadevent
            ORDER BY id;
        """)

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