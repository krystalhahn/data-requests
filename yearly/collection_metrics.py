# collection submissions
# include all resource types

collection_submissions_all = pd.DataFrame()
collection_count = 0
submission_count = 0

# start timing
start_time = time.time()

# cycle through collections
url = 'https://api.osf.io/v2/collections/'

while url:
    response = requests.get(url)
    json = response.json()

    # cycle through collections
    for collection in json['data']:
        collection_id = collection['id']

        sub_url = f'https://api.osf.io/v2/collections/{collection_id}/collection_submissions/'

        # increment collection count by 1
        collection_count += 1
        
        while sub_url:
            sub_response = requests.get(sub_url)
            sub_json = sub_response.json()

            # only process if there are collection submissions ('data' is present in sub_json)
            if 'data' in sub_json:
                
                for sub in sub_json['data']:
                    sub_data = {
                        'collection_id': collection_id, 
                        'collection_title': collection['attributes']['title'], 
                        'collection_created': pd.to_datetime(collection['attributes']['date_created']).date(), 
                        'collection_status_choices': ", ".join(collection['attributes']['status_choices']), 
                        'sub_id': sub['id'], 
                        'sub_title': sub['attributes']['title'], 
                        'sub_created': pd.to_datetime(sub['attributes']['date_created']).date(), 
                        'sub_reviews_state': sub['attributes']['reviews_state'],
                        'sub_status': sub['attributes']['status'],
                        'sub_type': sub['embeds']['guid']['data']['type'],
                        'sub_category': sub['embeds']['guid']['data']['attributes']['category'],
                        'sub_public': sub['embeds']['guid']['data']['attributes']['public']
                    }
                    # add collection and sub data to output dataframe
                    sub_df = pd.DataFrame([sub_data])
                    collection_submissions_all = pd.concat([collection_submissions_all, sub_df], ignore_index=True)
                    # increment sub count by 1
                    submission_count += 1

                    # usually takes a second: print partial results every 10th submission recorded
                    if submission_count >= 10 and submission_count % 10 == 0:
                        elapsed_time = time.time() - start_time
                        print(f"Recorded {collection_count} collections")
                        print(f"Recorded {submission_count} submissions")
                        print(f"Elapsed time: {elapsed_time:.2f} seconds\n")

            # update url to move to the next page
            sub_url = sub_json.get('links', {}).get('next')

    url = json['links'].get('next')

# collection linked nodes
# include all resource types

collection_nodes = pd.DataFrame()
collection_count = 0
node_count = 0

# start timing
start_time = time.time()

# cycle through collections
url = 'https://api.osf.io/v2/collections/'

while url:
    response = requests.get(url)
    json = response.json()

    # cycle through collections
    for collection in json['data']:
        collection_id = collection['id']

        node_url = f'https://api.osf.io/v2/collections/{collection_id}/linked_nodes/'

        # increment collection count by 1
        collection_count += 1
        
        while node_url:
            node_response = requests.get(node_url)
            node_json = node_response.json()

            # only process if there are linked nodes ('data' is present in node_json)
            if 'data' in node_json:
                
                for node in node_json['data']:
                    node_data = {
                        'collection_id': collection_id, 
                        'collection_title': collection['attributes']['title'], 
                        'collection_created': pd.to_datetime(collection['attributes']['date_created']).date(), 
                        'collection_status': ", ".join(collection['attributes']['status_choices']), 
                        'node_id': node['id'], 
                        'node_title': node['attributes']['title'], 
                        'node_created': pd.to_datetime(node['attributes']['date_created']).date(), 
                        'node_type': node['type'], 
                        'node_category': node['attributes']['category'],
                        'node_public': node['attributes']['public']
                    }
                    # add collection and node data to output dataframe
                    node_df = pd.DataFrame([node_data])
                    collection_nodes = pd.concat([collection_nodes, node_df], ignore_index=True)
                    # increment node count by 1
                    node_count += 1

                    # usually takes a second: print partial results every 50th project recorded
                    if node_count >= 50 and node_count % 50 == 0:
                        elapsed_time = time.time() - start_time
                        print(f"Recorded {collection_count} collections")
                        print(f"Recorded {node_count} projects")
                        print(f"Elapsed time: {elapsed_time:.2f} seconds\n")

            # update url to move to the next page
            node_url = node_json.get('links', {}).get('next')

    url = json['links'].get('next')