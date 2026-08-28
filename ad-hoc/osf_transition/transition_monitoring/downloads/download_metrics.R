# parameterized function to pull weekly or cumulative metrics ----
get_download_metrics <- function(
    download_data_path,
    cadence,
    start,
    end,
    cumulative = FALSE
) {
  
  library(readr)
  library(dplyr)
  library(tidyr)
  library(lubridate)
  
  downloads_all <- read_csv(download_data_path)
  
  # helper function for aggregating a download metric
  aggregate_download_metric <- function(
    data,
    group_var,
    metric_name,
    complete_combinations = FALSE,
    include_percent = FALSE
  ) {
    
    result <- data %>%
      mutate(
        zip_completed = factor(
          zip_completed,
          levels = c(TRUE, FALSE, NA)
        )
      ) %>%
      group_by(.data[[group_var]], zip_completed) %>%
      summarise(
        count = n(),
        size_gb = round(sum(size_bytes, na.rm = TRUE) / 1e9, 2),
        .groups = "drop"
      )
    
    if (complete_combinations) {
      result <- result %>%
        complete(
          !!sym(group_var),
          zip_completed,
          fill = list(
            count = 0,
            size_gb = 0
          )
        )
    }
    
    if (include_percent) {
      result <- result %>%
        mutate(
          percent_total = round(count / sum(count) * 100, 2)
        )
    }
    
    result %>%
      rename(attribute = all_of(group_var)) %>%
      mutate(
        metric = metric_name,
        attribute_2 = case_when(
          zip_completed == TRUE ~ "zip_completed",
          zip_completed == FALSE ~ "zip_not_completed",
          is.na(zip_completed) ~ NA_character_
        )
      ) %>%
      select(
        metric,
        attribute,
        attribute_2,
        count,
        size_gb,
        any_of("percent_total")
      )
  }
  
  if (cadence == "weekly") {
    
    start_week <- as.POSIXct(start, tz = "UTC")
    end_week <- as.POSIXct(end, tz = "UTC")
    
    week_starts <- seq(
      from = start_week,
      to = end_week - days(7),
      by = "1 week"
    )
    
    get_one_week <- function(week_start) {
      
      week_end <- week_start + days(7)
      
      # choose weekly vs. cumulative data
      if (cumulative) {
        downloads <- downloads_all %>%
          filter(
            created >= start_week,
            created < week_end
          )
      } else {
        downloads <- downloads_all %>%
          filter(
            created >= week_start,
            created < week_end
          )
      }
      
      # calculate metrics
      by_download_type <- aggregate_download_metric(
        downloads,
        "download_type",
        "download_type",
        include_percent = TRUE
      )
      
      by_user_type <- downloads %>%
        mutate(
          user_type = case_when(
            is.na(user_guid) ~ "non-user",
            !is.na(user_guid) ~ "user"
          )
        ) %>%
        aggregate_download_metric(
          "user_type",
          "user_type",
          include_percent = TRUE
        )
      
      by_resource_type <- downloads %>%
        mutate(
          resource_type = case_when(
            resource_type == "osf.node" ~ "node",
            resource_type == "osf.registration" ~ "registration",
            resource_type == "osf.preprint" ~ "preprint"
          )
        )%>%
        aggregate_download_metric(
          "resource_type",
          "resource_type",
          include_percent = TRUE
        )
      
      by_storage_region <- aggregate_download_metric(
        downloads,
        "storage_region",
        "storage_region",
        include_percent = TRUE
      )
      
      by_storage_provider <- aggregate_download_metric(
        downloads,
        "storage_provider",
        "storage_provider",
        complete_combinations = TRUE,
        include_percent = TRUE
      )
      
      bind_rows(
        by_download_type,
        by_user_type,
        by_resource_type,
        by_storage_region,
        by_storage_provider
      ) %>%
        pivot_longer(
          cols = c(count, size_gb, percent_total),
          names_to = "measure",
          values_to = "value"
        ) %>%
        mutate(
          week = format(week_start, "%Y-%m-%d")
        )
    }
    
    bind_rows(
      lapply(week_starts, get_one_week)
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
      )
  }
}