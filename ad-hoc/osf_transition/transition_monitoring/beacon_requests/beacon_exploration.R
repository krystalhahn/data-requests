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
    beacon_history = purrr::map_chr(
      threads,
      ~ .x %>%
        filter(type == "note") %>%
        slice_min(createdAt, n = 1) %>%
        pull(body)
    ),
    beacon_opened = str_extract(
      beacon_history,
      "Beacon opened on .*"
    ),
    beacon_page_name = str_extract(
      beacon_opened,
      "(?<=Beacon opened on ).*?(?= / https?://)"
    ),
    beacon_page_link = str_extract(
      beacon_opened,
      "https?://\\S+"
    )
  )