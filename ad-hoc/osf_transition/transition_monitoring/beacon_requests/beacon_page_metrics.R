get_beacon_metrics <- function(
    conversations_data_path,
    cadence,
    start,
    end,
    cumulative = FALSE
) {
  
  library(jsonlite)
  library(readr)
  library(dplyr)
  library(tidyr)
  library(purrr)
  library(stringr)
  library(lubridate)
  library(rvest)
  library(cld3)
  
  conversations_all <- fromJSON(
    conversations_data_path,
    flatten = TRUE
  ) %>%
    mutate(
      created = as.POSIXct(createdAt, tz = "UTC"),
      
      # count customer vs. desk messages in each thread
      customer_threads = map_int(
        threads,
        ~ sum(.x$type == "customer", na.rm = TRUE)
      ),
      desk_threads = map_int(
        threads,
        ~ sum(.x$type == "message", na.rm = TRUE)
      ),
      
      # convert tags list to character vector
      tags = map_chr(
        tags,
        ~ if (length(.x) == 0) {
          NA_character_
        } else {
          paste(.x, collapse = "; ")
        }
      )
    ) %>%
    select(-createdAt)
  
  
  # unnest customFields
  custom_fields_wide <- conversations_all %>%
    select(id, customFields) %>%
    unnest_longer(customFields) %>%
    unnest_wider(customFields) %>%
    pivot_wider(
      names_from = name,
      values_from = text
    )
  
  
  conversations_all <- conversations_all %>%
    select(-customFields) %>%
    left_join(
      custom_fields_wide,
      by = "id"
    ) %>%
    filter(
      Product != "Other",
      Product != "N/a",
      `Main Themes` != "Other",
      `Main Themes` != "N/A",
      !str_detect(tags, "remove_report") | is.na(tags)
    )
  
  
  # helper function: aggregate metrics by page
  aggregate_metric <- function(
    data,
    page_var,
    metric_name
  ) {
    
    data %>%
      group_by(.data[[page_var]]) %>%
      summarise(
        total_count = n(),
        transition_count = sum(
          `OSF Transition` == "OSF Transition",
          na.rm = TRUE
        ),
        transition_percent = round(
          transition_count / total_count * 100,
          2
        ),
        .groups = "drop"
      ) %>%
      rename(
        attribute = all_of(page_var)
      ) %>%
      pivot_longer(
        cols = c(
          total_count,
          transition_count,
          transition_percent
        ),
        names_to = "measure",
        values_to = "value"
      ) %>%
      mutate(
        metric = metric_name,
        attribute_2 = NA_character_
      ) %>%
      select(
        metric,
        attribute,
        attribute_2,
        measure,
        value
      )
  }
  
  
  # helper function: extract a beacon field
  get_beacon_field <- function(html, field) {
    
    cells <- html %>%
      rvest::html_elements("td") %>%
      rvest::html_text2()
    
    value <- cells[match(field, cells) + 1]
    
    if (length(value) == 0 || is.na(value)) {
      return(NA_character_)
    }
    
    value
  }
  
  
  # helper function: extract Beacon History events
  get_history_events <- function(html) {
    
    html %>%
      rvest::html_elements(
        ".c-BeaconHistoryTimelineListItem"
      ) %>%
      rvest::html_text2()
  }
  
  
  # helper function: get the first matching History event
  get_first_history_event <- function(html, pattern) {
    
    events <- get_history_events(html) %>%
      stringr::str_subset(pattern)
    
    if (length(events) == 0) {
      return(NA_character_)
    }
    
    first(events)
  }
  
  
  # helper function: get the last matching History event
  get_last_history_event <- function(html, pattern) {
    
    events <- get_history_events(html) %>%
      stringr::str_subset(pattern)
    
    if (length(events) == 0) {
      return(NA_character_)
    }
    
    last(events)
  }
  
  
  # helper function: extract page name
  get_page_name <- function(x, prefix = NULL) {
    
    if (!is.null(prefix)) {
      x <- stringr::str_remove(x, paste0("^", prefix))
    }
    
    stringr::str_extract(
      x,
      ".*?(?= / https?://)"
    )
  }
  
  
  # helper function: extract page link
  get_page_link <- function(x) {
    
    stringr::str_extract(
      x,
      "https?://\\S+"
    )
  }
  
  
  # helper function: standardize search page names
  clean_search_page_name <- function(name) {
    dplyr::if_else(
      stringr::str_detect(name, "Search results"),
      "Search results...",
      name
    )
  }
  
  
  # extract beacon page info
  cl_beacon_pages <- conversations_all %>%
    filter(source_type == "beacon-v2") %>%
    mutate(
      
      # get the first note body
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
        rvest::read_html
      ),
      
      # page where the beacon was opened
      beacon_opened = purrr::map_chr(
        beacon_html,
        get_first_history_event,
        pattern = "^Beacon opened on"
      ),
      
      beacon_page_name = get_page_name(
        beacon_opened,
        prefix = "Beacon opened on "
      ),
      
      beacon_page_link = get_page_link(
        beacon_opened
      ),
      
      # Site Information
      beacon_id = purrr::map_chr(
        beacon_html,
        get_beacon_field,
        field = "Beacon ID"
      ),
      
      beacon_current_page = purrr::map_chr(
        beacon_html,
        get_beacon_field,
        field = "Current Page"
      ),
      
      beacon_current_page_name = get_page_name(
        beacon_current_page
      ),
      
      beacon_current_page_link = get_page_link(
        beacon_current_page
      ),
      
      # last page viewed in Beacon History
      beacon_last_page = purrr::map_chr(
        beacon_html,
        get_last_history_event,
        pattern = "^Viewed "
      ),
      
      beacon_last_page_name = get_page_name(
        beacon_last_page
      ),
      
      beacon_last_page_link = get_page_link(
        beacon_last_page
      )
    ) %>%
    select(-beacon_html)
  
  
  # build page name/link lookup
  page_name_link_key <- cl_beacon_pages %>%
    select(
      beacon_page_name,
      beacon_page_link,
      beacon_current_page_name,
      beacon_current_page_link,
      beacon_last_page_name,
      beacon_last_page_link
    ) %>%
    pivot_longer(
      everything(),
      names_to = c("page_type", ".value"),
      names_pattern = "beacon_(page|current_page|last_page)_(name|link)"
    ) %>%
    select(
      page_name = name,
      page_link = link
    ) %>%
    distinct() %>%
    mutate(
      cleaned_page_link = stringr::str_extract(
        page_link,
        "https?://[^#?\\s]+"
      ),
      lang = detect_language(page_name)
    ) %>%
    distinct(
      page_name,
      cleaned_page_link,
      lang
    ) %>%
    group_by(cleaned_page_link) %>%
    mutate(
      eng_page_name = page_name[lang == "en"][1]
    ) %>%
    ungroup()
  
  
  # clean beacon page data
  beacon_pages_cleaned <- cl_beacon_pages %>%
    select(
      -beacon_page_link,
      -beacon_current_page_link,
      -beacon_last_page_link
    ) %>%
    left_join(
      page_name_link_key %>%
        rename(
          beacon_page_link = cleaned_page_link,
          beacon_page_name_eng = eng_page_name
        ),
      by = c(
        "beacon_page_name" = "page_name"
      )
    ) %>%
    left_join(
      page_name_link_key %>%
        rename(
          beacon_current_page_link = cleaned_page_link,
          beacon_current_page_name_eng = eng_page_name
        ),
      by = c(
        "beacon_current_page_name" = "page_name"
      )
    ) %>%
    left_join(
      page_name_link_key %>%
        rename(
          beacon_last_page_link = cleaned_page_link,
          beacon_last_page_name_eng = eng_page_name
        ),
      by = c(
        "beacon_last_page_name" = "page_name"
      )
    ) %>%
    mutate(
      beacon_page_name_eng = clean_search_page_name(
        beacon_page_name_eng
      ),
      beacon_current_page_name_eng = clean_search_page_name(
        beacon_current_page_name_eng
      ),
      beacon_last_page_name_eng = clean_search_page_name(
        beacon_last_page_name_eng
      )
    ) %>%
    select(
      -beacon_page_name,
      -beacon_current_page_name,
      -beacon_last_page_name,
      -lang,
      -lang.x,
      -lang.y
    )
  
  
  # weekly metrics
  if (cadence == "weekly") {
    
    start_week <- as.POSIXct(
      start,
      tz = "UTC"
    )
    
    end_week <- as.POSIXct(
      end,
      tz = "UTC"
    )
    
    # Generate weekly start dates
    week_starts <- seq(
      from = start_week,
      to = end_week - lubridate::days(7),
      by = "1 week"
    )
    
    
    # Calculate metrics for one week
    get_one_week <- function(week_start) {
      
      week_end <- week_start + days(7)
      
      
      # Weekly vs. cumulative data
      if (cumulative) {
        
        conversations <- beacon_pages_cleaned %>%
          filter(
            created >= start_week,
            created < week_end
          )
        
      } else {
        
        conversations <- beacon_pages_cleaned %>%
          filter(
            created >= week_start,
            created < week_end
          )
      }
      
      
      # page beacon was opened on ----
      opened_pages <- aggregate_metric(
        conversations,
        "beacon_page_name_eng",
        "page_beacon_opened"
      )
      
      
      # page beacon request was submitted on ----
      submitted_pages <- aggregate_metric(
        conversations,
        "beacon_last_page_name_eng",
        "page_beacon_submitted"
      )
      
      
      # Combine metrics
      bind_rows(
        opened_pages,
        submitted_pages
      ) %>%
        mutate(
          week = format(
            week_start,
            "%Y-%m-%d"
          )
        )
    }
    
    
    # calculate metrics for every week
    weekly_metrics <- bind_rows(
      lapply(
        week_starts,
        get_one_week
      )
    ) %>%
      select(
        metric,
        attribute,
        attribute_2,
        measure,
        week,
        value
      ) %>%
      pivot_wider(
        names_from = week,
        values_from = value
      ) %>%
      mutate(
        metric = factor(
          metric,
          levels = c(
            "page_beacon_opened",
            "page_beacon_submitted"
          )
        )
      ) %>%
      arrange(
        metric,
        attribute
      )
    
    return(weekly_metrics)
  }
}

# generate weekly metrics ----
beacon_metrics <- get_beacon_metrics(
  conversations_data_path = "~/Desktop/helpscout_conversations_0825.json",
  cadence = "weekly",
  start = "2026-08-09",
  end = "2026-08-23",
  cumulative = FALSE
)

# generate cumulative metrics ----
beacon_metrics_0831 <- get_beacon_metrics(
  conversations_data_path = "~/Desktop/helpscout_conversations_0825.json",
  cadence = "weekly",
  start = "2026-08-09",
  end = "2026-08-23",
  cumulative = TRUE
)
