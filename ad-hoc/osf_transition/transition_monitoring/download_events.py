def get_download_events():
    import csv
    from django.db import connection

    filename = "/tmp/download_events.csv"

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM osf_downloadevent
            ORDER BY id;
        """)

        # get column names from the query
        fieldnames = [column[0] for column in cursor.description]

        with open(filename, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(fieldnames)

            processed = 0

            while True:
                rows = cursor.fetchmany(10000)

                if not rows:
                    break

                writer.writerows(rows)
                processed += len(rows)

                print(
                    f"Processed {processed:,} rows",
                    end="\r"
                )

    print(f"\nOutput written to {filename}")