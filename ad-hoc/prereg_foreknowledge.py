def check_prereg_foreknowledge():
    import csv
    import io
    import datetime
    from osf.utils.outcomes import ArtifactTypes
    from osf.models import Identifier, OutcomeArtifact
    from tqdm import tqdm
    import json
    filename = '/tmp/prereg_foreknowledge.csv'
    COL_HEADERS = ['reg_guid', 'is_first_two', 'foreknowledge_option']
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()

    FOREKNOWLEDGE_OPTION_1 = "Data does not yet exist. No part of the data that will be used for this analysis plan exists, and no part will be generated until after this plan is registered."
    FOREKNOWLEDGE_OPTION_2 = "Data exists but the authors cannot observe it yet. At least some of the data that will be used for this analysis plan exists but is inaccessible to the authors and will remain so until after this plan is registered."

    preregs = []
    with open('/tmp/april_preregs.csv', newline='') as mapfile:
        mapreader = csv.reader(mapfile, delimiter=',', quotechar='"')
        next(mapreader)
        for row in mapreader:
            if row:
                preregs.append(row[0])

    pbar = tqdm(total=len(preregs))

    for reg_guid in preregs:
        reg = Registration.objects.get(guids___id=reg_guid)

        foreknowledge_response = reg.registration_responses.get('344-4') if reg.registration_responses else None
        if foreknowledge_response == FOREKNOWLEDGE_OPTION_1:
            is_first_two_foreknowledge = True
            foreknowledge_option = 1
        elif foreknowledge_response == FOREKNOWLEDGE_OPTION_2:
            is_first_two_foreknowledge = True
            foreknowledge_option = 2
        else:
            is_first_two_foreknowledge = False
            foreknowledge_option = None

        writer.writerow({
            'reg_guid': reg._id,
            'is_first_two': is_first_two_foreknowledge,
            'foreknowledge_option': foreknowledge_option,
        })
        pbar.update()

    pbar.close()
    with open(filename, 'w') as writeFile:
        writeFile.write(output.getvalue())

    print(f"Output written to {filename}")