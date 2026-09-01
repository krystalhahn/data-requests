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
  left_join(custom_fields_wide, by = "id") %>%
  filter(
    Product != "Other",
    Product != "N/a",
    `Main Themes` != "Other",
    `Main Themes` != "N/A",
    !str_detect(tags, "remove_report") | is.na(tags)
  )

# extract beacon pages from Site Information and Beacon History ----
beacon_pages <- conversations_wide %>%
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

# cleaning up non-EN page names ----
page_name_link_key <- beacon_pages %>%
  select(
    beacon_page_name, beacon_page_link,
    beacon_current_page_name, beacon_current_page_link,
    beacon_last_page_name, beacon_last_page_link
  ) %>%
  pivot_longer(
    everything(),
    names_to = c("page_type", ".value"),
    names_pattern = "beacon_(page|current_page|last_page)_(name|link)"
  ) %>%
  select(page_name = name, page_link = link) %>%
  distinct() %>%
  mutate(
    cleaned_page_link = str_extract(page_link, "https?://[^#?\\s]+"),
    lang = detect_language(page_name)) %>%
  distinct(page_name, cleaned_page_link, lang) %>%
  group_by(cleaned_page_link) %>%
  mutate(
    eng_page_name = page_name[lang == "en"][1]
  ) %>%
  ungroup()

beacon_pages_cleaned <- beacon_pages %>%
  select(-beacon_page_link, -beacon_current_page_link, -beacon_last_page_link) %>%
  left_join(
    page_name_link_key %>%
      rename(
        beacon_page_link = cleaned_page_link,
        beacon_page_name_eng = eng_page_name
      ),
    by = c("beacon_page_name" = "page_name")
  ) %>%
  left_join(
    page_name_link_key %>%
      rename(
        beacon_current_page_link = cleaned_page_link,
        beacon_current_page_name_eng = eng_page_name
      ),
    by = c("beacon_current_page_name" = "page_name")
  ) %>%
  left_join(
    page_name_link_key %>%
      rename(
        beacon_last_page_link = cleaned_page_link,
        beacon_last_page_name_eng = eng_page_name
      ),
    by = c("beacon_last_page_name" = "page_name")
  ) %>%
  mutate(
    across(
      ends_with("_page_name_eng"),
      ~ if_else(
        get(sub("_name_eng$", "_link", cur_column())) == "https://help.osf.io/search",
        "Search results...",
        .x
      )
    )
  ) %>%
  select(-beacon_page_name, -beacon_current_page_name, -beacon_last_page_name,
         -lang, -lang.x, -lang.y)

# weekly beacon pages ----
## pages the beacon was opened on ----
opened_pages <- beacon_pages_cleaned %>%
  mutate(
    created = as.POSIXct(createdAt, tz = "UTC"),
    week = case_when(
      created >= as.POSIXct("2026-08-09 00:00:00", tz = "UTC") &
        created < as.POSIXct("2026-08-16 00:00:00", tz = "UTC") ~ "8/9-8/15",
      created >= as.POSIXct("2026-08-16 00:00:00", tz = "UTC") &
        created < as.POSIXct("2026-08-23 00:00:00", tz = "UTC") ~ "8/16-8/22",
      .default = NA_character_
    )
  ) %>%
  filter(!is.na(week)) %>%
  group_by(week, beacon_page_name_eng) %>%
  summarise(count = n(),
            .groups = "drop") %>%
  pivot_wider(
    names_from = week,
    values_from = count
  ) %>%
  rename(page_name = beacon_page_name_eng) %>%
  select(page_name, `8/9-8/15`, `8/16-8/22`) %>%
  arrange(
    page_name == "Search results...",
    desc(`8/9-8/15`)
  )

## pages beacon requests were submitted on ----
submit_pages <- beacon_pages_cleaned %>%
  mutate(
    created = as.POSIXct(createdAt, tz = "UTC"),
    week = case_when(
      created >= as.POSIXct("2026-08-09 00:00:00", tz = "UTC") &
        created < as.POSIXct("2026-08-16 00:00:00", tz = "UTC") ~ "8/9-8/15",
      created >= as.POSIXct("2026-08-16 00:00:00", tz = "UTC") &
        created < as.POSIXct("2026-08-23 00:00:00", tz = "UTC") ~ "8/16-8/22",
      .default = NA_character_
    )
  ) %>%
  filter(!is.na(week)) %>%
  group_by(week, beacon_last_page_name_eng) %>%
  summarise(count = n(),
            .groups = "drop") %>%
  pivot_wider(
    names_from = week,
    values_from = count
  ) %>%
  rename(page_name = beacon_last_page_name_eng) %>%
  select(page_name, `8/9-8/15`, `8/16-8/22`) %>%
  arrange(
    page_name == "Search results...",
    desc(`8/9-8/15`)
  )