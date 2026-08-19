def get_download_events():
    import io
    import csv
    from tqdm import tqdm
    from django.db import connection

    filename = "/tmp/download_events.csv"

    output = io.StringIO()

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM osf_downloadevent
            ORDER BY id;
        """)

        # get column names from the query
        fieldnames = [column[0] for column in cursor.description]

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        # fetch rows
        rows = cursor.fetchall()

        for row in tqdm(rows, total=len(rows)):
            writer.writerow(dict(zip(fieldnames, row)))

    with open(filename, "w") as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")