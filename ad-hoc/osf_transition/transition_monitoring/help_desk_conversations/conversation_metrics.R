get_conversation_metrics <- function(
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
  
  conversations_all <- fromJSON(
    conversations_data_path,
    flatten = TRUE
  ) %>%
    mutate(
      createdAt = as.POSIXct(createdAt, tz = "UTC"),
      
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
        ~ if (length(.x) == 0) NA_character_
        else paste(.x, collapse = "; ")
      )
    )
  
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
    left_join(custom_fields_wide, by = "id") %>%
    filter(
      Product != "Other", 
      Product != "N/a", 
      `Main Themes` != "Other", 
      `Main Themes` != "N/A",
      !str_detect(tags, "remove_report") | is.na(tags)
    )
  
  # helper function for aggregating a conversation metric
  aggregate_conversation_metric <- function(
    data,
    group_var,
    metric_name,
    levels = NULL
  ) {
    
    # apply factor levels if specified
    if (!is.null(levels)) {
      data <- data %>%
        mutate(
          "{group_var}" := factor(
            .data[[group_var]],
            levels = levels
          )
        )
    }
    
    data %>%
      group_by(.data[[group_var]]) %>%
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
      rename(attribute = all_of(group_var)) %>%
      mutate(
        metric = metric_name,
        attribute_2 = NA_character_
      ) %>%
      select(
        metric,
        attribute,
        attribute_2,
        total_count,
        transition_count,
        transition_percent
      )
  }
  
  if (cadence == "weekly") {
    
    start_week <- as.POSIXct(start, tz = "UTC")
    end_week <- as.POSIXct(end, tz = "UTC")
    
    # generate weekly start dates
    week_starts <- seq(
      from = start_week,
      to = end_week - lubridate::days(7),
      by = "1 week"
    )
    
    # function to calculate metrics for one week
    get_one_week <- function(week_start) {
      
      week_end <- week_start + days(7)
      
      # weekly vs. cumulative data
      if (cumulative) {
        conversations <- conversations_all %>%
          filter(
            createdAt >= start_week,
            createdAt < week_end
          )
      } else {
        conversations <- conversations_all %>%
          filter(
            createdAt >= week_start,
            createdAt < week_end
          )
      }
      
      # overall ----
      
      overall <- conversations %>%
        summarise(
          total_count = n(),
          transition_count = sum(`OSF Transition` == "OSF Transition", na.rm = TRUE),
          transition_percent = round(transition_count / total_count * 100, 2)) %>%
        mutate(
          metric = "overall",
          attribute = NA_character_,
          attribute_2 = NA_character_,
        ) %>%
        select(metric, attribute, attribute_2, total_count, transition_count, transition_percent)
      
      # by Attitude towards OSF ----
      
      by_attitude <- aggregate_conversation_metric(
        conversations,
        "Attitude towards OSF",
        "attitude",
        levels = c("Positive", "Neutral", "Negative")
      )
      
      # by Product ----
      
      by_product <- conversations %>%
        mutate(
          Product = case_when(
            Product == "API/ Integrations" ~ "API/Integrations",
            Product == "Support/ Help Center" ~ "Support/Help Center",
            .default = Product
          )
        ) %>%
        aggregate_conversation_metric(
          "Product",
          "product"
        )
      
      # by Main Themes ----
      
      by_main_theme <- aggregate_conversation_metric(
        conversations,
        "Main Themes",
        "main_theme"
      )
      
      # by OSF Transition Theme ----
      
      by_transition_theme <- aggregate_conversation_metric(
        conversations,
        "OSF Transition Theme",
        "transition_theme"
      )

      # combine metrics ----
      
      bind_rows(
        overall,
        by_attitude,
        by_product,
        by_main_theme,
        by_transition_theme
      ) %>%
        pivot_longer(
          cols = c(total_count, transition_count, transition_percent),
          names_to = "measure",
          values_to = "value"
        ) %>%
        mutate(
          week = format(week_start, "%Y-%m-%d")
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
            "overall",
            "attitude",
            "product",
            "main_theme",
            "transition_theme"
          )
        ),
        attribute = if_else(
          metric == "attitude",
          factor(
            attribute,
            levels = c("Positive", "Neutral", "Negative")
          ),
          factor(attribute)
        )
      ) %>%
      arrange(metric, attribute)
    
    return(weekly_metrics)
  }
}

# generate weekly metrics ----
conversation_metrics <- get_conversation_metrics(
  conversations_data_path = "~/Desktop/helpscout_conversations_0825.json",
  cadence = "weekly",
  start = "2026-08-09",
  end = "2026-08-23",
  cumulative = FALSE
)

# generate cumulative metrics ----
conversation_metrics_cumulative <- get_conversation_metrics(
  conversations_data_path = "~/Desktop/helpscout_conversations_0825.json",
  cadence = "weekly",
  start = "2026-08-09",
  end = "2026-08-23",
  cumulative = TRUE
)

# write to sheet ----
## set transition_sheet_url
existing_conv_master <- read_sheet(transition_sheet_url, sheet = "Help desk conversations")

new_rows <- conversation_metrics %>%
  anti_join(existing_conv_master, by = key_cols)

existing_rows <- conversation_metrics %>%
  semi_join(existing_conv_master, by = key_cols)

current_week <- as.character(floor_date(Sys.Date(), "week", week_start = 7) - weeks(1))

existing_cols <- names(existing_conv_master)
week_col_index <- which(sheet_cols == current_week)

# get current week's column for existing rows
# backfill NA values with 0
existing_column <- existing_conv_master %>%
  left_join(existing_rows, by = key_cols) %>%
  select(!!current_week) %>%
  mutate(
    across(
      everything(),
      ~ replace_na(.x, 0)
    )
  )

# get current week's new rows
# backfill NA values with 0
new_rows_to_write <- existing_conv_master[0, ] %>%
  mutate(attribute_2 = as.character(attribute_2)) %>%
  bind_rows(
    new_rows %>%
      mutate(attribute_2 = as.character(attribute_2))
  ) %>%
  mutate(
    across(
      -all_of(key_cols),
      ~ tidyr::replace_na(.x, 0)
    )
  )

# helper function to generate column letter
col_to_letter <- function(n) {
  paste0(LETTERS[(n - 1) %% 26 + 1])  # works for single letter columns
}

first_empty_col <- ncol(existing_conv_master) + 1

# write current week values to existing rows only
#  same order as the sheet (so previous steps are crucial)
range_write(
  transition_sheet_url,
  existing_column,
  sheet = "Help desk conversations",
  range = paste0(col_to_letter(first_empty_col), "1"), 
  col_names = TRUE
)

# append new rows at the bottom
if (nrow(new_rows) > 0) {
  last_row <- nrow(existing_conv_master) + 1
  range_write(
    transition_sheet_url,
    new_rows_to_write,
    sheet = "Help desk conversations",
    range = paste0("A", last_row + 1),
    col_names = FALSE
  )
}