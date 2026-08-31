library(jsonlite)
library(dplyr)
library(tidyr)
library(purrr)

# help desk conversations
conversations <- fromJSON(
  "~/Desktop/helpscout_conversations_0825.json",
  flatten = TRUE
)

# count how many messages in the thread were from the customer vs from the desk
# two new columns: customer_threads, desk_threads
conversations <- conversations %>%
  mutate(
    customer_threads = map_int(
      threads,
      ~ sum(.x$type == "customer", na.rm = TRUE)
    ),
    desk_threads = map_int(
      threads,
      ~ sum(.x$type == "message", na.rm = TRUE)
    )
  ) %>%
  # convert tags list to character vector
  mutate(
    tags = purrr::map_chr(
      tags,
      ~ if (length(.x) == 0) NA_character_ else paste(.x, collapse = "; ")
    )
  )

custom_fields_wide <- conversations %>%
  select(id, customFields) %>%
  unnest_longer(customFields) %>%
  unnest_wider(customFields) %>%
  pivot_wider(
    names_from = name,
    values_from = text
  )

conversations_wide <- conversations %>%
  select(-customFields) %>%
  left_join(custom_fields_wide, by = "id")

beacon_pages <- conversations %>%
  filter(source_type == "beacon-v2") %>%
  mutate(
    
    # get the first note body with Site Information and Beacon History
    beacon_history = purrr::map_chr(
      threads,
      ~ .x %>%
        filter(type == "note") %>%
        slice_min(createdAt, n = 1) %>%
        pull(body) %>%
        first()
    ),
    
    # parse beacon HTML
    beacon_html = purrr::map(
      beacon_history,
      ~ rvest::read_html(.x)
    ),
    
    # page where the beacon was opened
    beacon_opened = purrr::map_chr(
      beacon_html,
      ~ .x %>%
        rvest::html_elements(".c-BeaconHistoryTimelineListItem") %>%
        rvest::html_text2() %>%
        stringr::str_subset("^Beacon opened on") %>%
        first()
    ),
    
    beacon_page_name = stringr::str_extract(
      beacon_opened,
      "(?<=Beacon opened on ).*?(?= / https?://)"
    ),
    
    beacon_page_link = stringr::str_extract(
      beacon_opened,
      "https?://\\S+"
    ),
    
    # Site Information
    beacon_id = purrr::map_chr(
      beacon_html,
      ~ {
        cells <- .x %>%
          rvest::html_elements("td") %>%
          rvest::html_text2()
        
        cells[match("Beacon ID", cells) + 1]
      }
    ),
    
    beacon_current_page = purrr::map_chr(
      beacon_html,
      ~ {
        cells <- .x %>%
          rvest::html_elements("td") %>%
          rvest::html_text2()
        
        cells[match("Current Page", cells) + 1]
      }
    ),
    
    beacon_current_page_name = stringr::str_extract(
      beacon_current_page,
      ".*?(?= / https?://)"
    ),
    
    beacon_current_page_link = stringr::str_extract(
      beacon_current_page,
      "https?://\\S+"
    ),
    
    # last page viewed in Beacon History
    beacon_last_page = purrr::map_chr(
      beacon_html,
      ~ .x %>%
        rvest::html_elements(".c-BeaconHistoryTimelineListItem") %>%
        rvest::html_text2() %>%
        stringr::str_subset("^Viewed ") %>%
        last()
    ),
    
    beacon_last_page_name = stringr::str_extract(
      beacon_last_page,
      "(?<=Viewed ).*?(?= / https?://)"
    ),
    
    beacon_last_page_link = stringr::str_extract(
      beacon_last_page,
      "https?://\\S+"
    )
  ) %>%
  select(-beacon_html)